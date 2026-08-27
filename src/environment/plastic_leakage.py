"""Where plastic actually goes, rather than which bin it went into.

Plastic appears all over this app as a recycling category. ``src.environment.waste_management.py``
sorts it, ``src.environment.ai_waste_sorter.py`` identifies it, ``src.utils.textile_lca_engine.py`` tracks
microplastic shedding per wash. None of them answer the question people actually
ask, which is where it ends up.

The implicit assumption everywhere else is that a correctly sorted item is a
solved problem. The entire issue lives in the gap between "put in the recycling
bin" and "recycled".

Collection is not recycling
----------------------------
A collected item passes a sorting facility, a reprocessor and a market, and it
can be rejected at any of them. PET bottles and HDPE jugs have functioning
streams. PP, PS, multi-layer laminates and anything below about fifty microns
largely do not, whatever symbol is printed on them. So the output of this module
is a **fate split** - mechanically recycled, incinerated, landfilled, leaked -
rather than a yes or no on recyclability.

Leakage is not the same question as disposal
---------------------------------------------
Plastic that escapes into the environment does so through pathways that have
almost nothing to do with bins:

*   **Tyre and road wear**, which for most households in a car-owning country
    exceeds everything they put in their bins combined.
*   **Synthetic textile fibres** shed in the wash, most of which reach soil
    through sewage sludge rather than reaching any ocean.
*   **Mismanaged municipal waste**, which dominates where collection coverage is
    incomplete and is close to zero where it is not.
*   Agricultural film, and personal care microbeads where they are still legal.

Each pathway gets its own compartment split, because most leaked plastic never
reaches the sea and modelling as though it does misdirects effort.

Mass is the wrong ranking
--------------------------
Ranking by mass puts a heavy PET bottle above a light plastic film, which is
backwards on every impact that matters. Leaked mass is reported alongside an
environmental residence time, so a gram of expanded polystyrene and a gram of
uncoated paper are not filed as equivalent litter.

Carbon alongside plastic, never instead of it
-----------------------------------------------
A cotton tote is a large increase in carbon and water for a decrease in plastic
leakage. Every substitution here reports both numbers so the trade is visible as
a trade. It takes roughly fifty uses for a cotton tote to break even on carbon
against the bag it replaced, and a module that only counted plastic would never
say so.

Where this connects to code already merged
-------------------------------------------
*   ``src.environment.waste_management.py`` sorts by category and stops at the bin.
*   ``src.utils.textile_lca_engine.py`` has shedding rates per wash but no fate model.
*   ``src.utils.circular_economy_engine.py`` argues for reuse without a leakage metric.
*   ``src.utils.contamination_simulator.py`` covers stream contamination, which is one of
    the loss mechanisms modelled here.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import math
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class PlasticError(ValueError):
    """Raised when a plastic fate calculation was asked for something meaningless."""


# ---------------------------------------------------------------------------
# Polymers
#
# ``sorting_yield`` is the share of collected material that survives the sorting
# facility; ``reprocessing_yield`` the share of that which becomes usable
# secondary material. Their product is the real recycling rate, and for several
# of these polymers it is close to zero regardless of what the bin says.
#
# ``marine_years`` and ``soil_years`` are order-of-magnitude residence times, and
# they are the reason mass alone is the wrong ranking.
# ---------------------------------------------------------------------------
POLYMERS = {
    "pet": {
        "label": "PET (drinks bottles)",
        "density": 1380.0, "carbon_per_kg": 2.73,
        "sorting_yield": 0.92, "reprocessing_yield": 0.82,
        "marine_years": 450.0, "soil_years": 300.0,
        "fragments": True,
        "note": "The one plastic with a genuinely functioning closed loop, "
                "because it is clear, heavy, uniform and worth money. Coloured "
                "and sleeved bottles do considerably worse than this.",
    },
    "hdpe": {
        "label": "HDPE (milk jugs, detergent bottles)",
        "density": 950.0, "carbon_per_kg": 2.08,
        "sorting_yield": 0.88, "reprocessing_yield": 0.78,
        "marine_years": 400.0, "soil_years": 250.0,
        "fragments": True,
        "note": "Rigid, uniform and identifiable, so it sorts well. Usually "
                "downcycled into pipe or crates rather than back into bottles.",
    },
    "ldpe_film": {
        "label": "LDPE film (bags, wrap)",
        "density": 920.0, "carbon_per_kg": 2.15,
        "sorting_yield": 0.28, "reprocessing_yield": 0.55,
        "marine_years": 300.0, "soil_years": 200.0,
        "fragments": True,
        "note": "Film wraps around sorting machinery and contaminates paper "
                "streams, so most facilities reject it deliberately. A bag in "
                "the recycling bin is usually a problem rather than a "
                "contribution.",
    },
    "pp": {
        "label": "PP (tubs, trays, closures)",
        "density": 905.0, "carbon_per_kg": 1.95,
        "sorting_yield": 0.62, "reprocessing_yield": 0.55,
        "marine_years": 350.0, "soil_years": 220.0,
        "fragments": True,
        "note": "Sorts adequately and has thin end markets, so a high share of "
                "what is separated is later rejected for want of a buyer.",
    },
    "ps": {
        "label": "PS (yoghurt pots, rigid packaging)",
        "density": 1050.0, "carbon_per_kg": 3.43,
        "sorting_yield": 0.24, "reprocessing_yield": 0.35,
        "marine_years": 500.0, "soil_years": 400.0,
        "fragments": True,
        "note": "Low value, brittle, and rejected by most facilities. Widely "
                "labelled recyclable and very rarely recycled.",
    },
    "eps": {
        "label": "EPS (foam packaging)",
        "density": 20.0, "carbon_per_kg": 3.78,
        "sorting_yield": 0.08, "reprocessing_yield": 0.40,
        "marine_years": 500.0, "soil_years": 400.0,
        "fragments": True,
        "note": "98% air, so it costs more to move than it is worth. Fragments "
                "into beads that are effectively unrecoverable once loose, "
                "which is why a gram of it is not comparable to a gram of PET.",
    },
    "pvc": {
        "label": "PVC (pipe, flooring, some packaging)",
        "density": 1400.0, "carbon_per_kg": 2.41,
        "sorting_yield": 0.15, "reprocessing_yield": 0.45,
        "marine_years": 600.0, "soil_years": 500.0,
        "fragments": False,
        "note": "Chlorinated, so it contaminates other streams and is screened "
                "out on purpose. Long-lived in construction, which is the "
                "honest case for it.",
    },
    "multilayer": {
        "label": "Multi-layer laminate (pouches, crisp packets)",
        "density": 1100.0, "carbon_per_kg": 3.10,
        "sorting_yield": 0.03, "reprocessing_yield": 0.10,
        "marine_years": 400.0, "soil_years": 300.0,
        "fragments": True,
        "note": "Several polymers and often aluminium bonded together and not "
                "separable by any mechanical process. Effectively unrecyclable "
                "and used because it protects food with very little material.",
    },
    "pla": {
        "label": "PLA (compostable packaging)",
        "density": 1250.0, "carbon_per_kg": 1.85,
        "sorting_yield": 0.05, "reprocessing_yield": 0.20,
        "marine_years": 150.0, "soil_years": 40.0,
        "fragments": True,
        "note": "Requires industrial composting at sustained high temperature. "
                "In a region without it, PLA is a contaminant in the recycling "
                "stream and behaves close to conventional plastic in a marine "
                "environment.",
    },
    "polyester_fibre": {
        "label": "Polyester textile fibre",
        "density": 1380.0, "carbon_per_kg": 5.55,
        "sorting_yield": 0.12, "reprocessing_yield": 0.30,
        "marine_years": 300.0, "soil_years": 200.0,
        "fragments": True,
        "note": "Blended garments cannot be fibre-to-fibre recycled at scale. "
                "The dominant environmental pathway is not disposal at all - it "
                "is shedding in the wash.",
    },
    "tyre_rubber": {
        "label": "Tyre rubber compound",
        "density": 1150.0, "carbon_per_kg": 3.15,
        "sorting_yield": 0.75, "reprocessing_yield": 0.60,
        "marine_years": 200.0, "soil_years": 150.0,
        "fragments": True,
        "note": "The casing is recovered reasonably well. What matters is the "
                "third of the tread that never reaches end of life because it "
                "abraded onto the road.",
    },
}


# ---------------------------------------------------------------------------
# Regional waste infrastructure
#
# The same sorted item has a different fate depending on what exists downstream.
# ``mismanaged`` is the share of generated waste that is neither collected nor
# formally disposed of, and it is the single biggest determinant of macroplastic
# leakage.
# ---------------------------------------------------------------------------
REGIONS = {
    "high_income_eu": {
        "label": "High income, Europe",
        "collection_rate": 0.98, "mismanaged": 0.008,
        "residual_incineration": 0.62, "residual_landfill": 0.38,
        "industrial_composting": True,
        "note": "High collection, high incineration with energy recovery. "
                "Leakage from bins is genuinely small here, which is why the "
                "non-bin pathways dominate a household's real footprint.",
    },
    "high_income_na": {
        "label": "High income, North America",
        "collection_rate": 0.96, "mismanaged": 0.012,
        "residual_incineration": 0.19, "residual_landfill": 0.81,
        "industrial_composting": False,
        "note": "Landfill-dominated residual, and industrial composting is "
                "rare enough that compostable packaging is usually a "
                "contaminant rather than a solution.",
    },
    "high_income_apac": {
        "label": "High income, Asia-Pacific",
        "collection_rate": 0.97, "mismanaged": 0.010,
        "residual_incineration": 0.74, "residual_landfill": 0.26,
        "industrial_composting": True,
        "note": "Very high incineration share, which removes the plastic and "
                "converts its carbon rather than storing it.",
    },
    "upper_middle": {
        "label": "Upper middle income",
        "collection_rate": 0.84, "mismanaged": 0.09,
        "residual_incineration": 0.22, "residual_landfill": 0.78,
        "industrial_composting": False,
        "note": "Collection covers most people and disposal is often to "
                "uncontrolled sites, so the leakage is downstream of collection "
                "rather than upstream of it.",
    },
    "lower_middle": {
        "label": "Lower middle income",
        "collection_rate": 0.61, "mismanaged": 0.29,
        "residual_incineration": 0.10, "residual_landfill": 0.90,
        "industrial_composting": False,
        "note": "Where the great majority of global macroplastic leakage "
                "actually happens, and where a household's own sorting effort "
                "has the least influence over the outcome.",
    },
}


# ---------------------------------------------------------------------------
# What fraction of mismanaged waste ends up in the environment, and where.
#
# Most of it does not reach the sea. Modelling as though it does concentrates
# attention on ocean-facing interventions and away from the soil and freshwater
# compartments that receive the bulk of it.
# ---------------------------------------------------------------------------
MISMANAGED_TO_ENVIRONMENT = 0.42
MISMANAGED_COMPARTMENTS = {"soil": 0.72, "freshwater": 0.22, "marine": 0.06}


# ---------------------------------------------------------------------------
# Leakage pathways that have nothing to do with bins
#
# ``factor`` is kg of plastic released per unit of the pathway's activity. The
# units differ per pathway and are named, because a single "per person" figure
# would hide which behaviour drives which number.
# ---------------------------------------------------------------------------
LEAKAGE_PATHWAYS = {
    "tyre_wear": {
        "label": "Tyre and road wear",
        "unit": "vehicle-km",
        "factor": 0.00011,
        "polymer": "tyre_rubber",
        "compartments": {"soil": 0.66, "freshwater": 0.20, "marine": 0.02,
                         "air": 0.12},
        "note": "Around 110 mg per vehicle-kilometre across four tyres. For a "
                "car-owning household this normally exceeds everything they "
                "put in their bins, and almost no consumer campaign mentions "
                "it. Driving style and tyre choice both move it materially.",
    },
    "textile_laundry": {
        "label": "Synthetic textile fibres in the wash",
        "unit": "kg of synthetic laundry washed",
        "factor": 0.00030,
        "polymer": "polyester_fibre",
        "compartments": {"soil": 0.68, "freshwater": 0.29, "marine": 0.03},
        "note": "Most of what a treatment works captures ends up in sewage "
                "sludge, and most sludge is spread on farmland. The fibres "
                "mostly reach soil, not the sea - which is the opposite of how "
                "this pathway is usually described.",
    },
    "personal_care": {
        "label": "Microbeads in personal care products",
        "unit": "kg of rinse-off product used",
        "factor": 0.00080,
        "polymer": "pp",
        "compartments": {"soil": 0.60, "freshwater": 0.35, "marine": 0.05},
        "note": "The pathway that got the regulation, and by a wide margin the "
                "smallest of these. Worth keeping in the model precisely to "
                "show how small it is next to tyres.",
    },
    "agricultural_film": {
        "label": "Agricultural mulch film",
        "unit": "kg of film used",
        "factor": 0.09000,
        "polymer": "ldpe_film",
        "compartments": {"soil": 0.94, "freshwater": 0.05, "marine": 0.01},
        "note": "Thin film fragments in place and is essentially never fully "
                "recovered. Almost entirely a soil pathway, and relevant to a "
                "household only through allotment and garden use.",
    },
    "paint": {
        "label": "Architectural and road marking paint",
        "unit": "kg of paint applied",
        "factor": 0.01200,
        "polymer": "pp",
        "compartments": {"soil": 0.55, "freshwater": 0.40, "marine": 0.05},
        "note": "Paint binders are polymer, and weathering releases them. "
                "Consistently one of the larger microplastic sources in "
                "national inventories and consistently absent from consumer "
                "advice.",
    },
}


# ---------------------------------------------------------------------------
# Substitution options
#
# ``carbon`` is kg CO2e per item including manufacture; ``mass`` is kg of the
# item. ``plastic_mass`` is how much of that mass is polymer. The point of this
# table is that swapping one for another trades a plastic number against a
# carbon number, and both have to be on screen for the trade to be visible.
# ---------------------------------------------------------------------------
SUBSTITUTIONS = {
    "ldpe_bag": {
        "label": "LDPE carrier bag",
        "mass": 0.008, "plastic_mass": 0.008, "carbon": 0.033,
        "polymer": "ldpe_film", "reuses": 1,
        "note": "The baseline. Very little material and very little carbon per "
                "use, which is exactly why it is hard to beat on carbon.",
    },
    "paper_bag": {
        "label": "Paper carrier bag",
        "mass": 0.055, "plastic_mass": 0.0, "carbon": 0.080,
        "polymer": None, "reuses": 1,
        "note": "No polymer, roughly two and a half times the carbon, and it "
                "fails in the rain. A real improvement on leakage and not a "
                "free one.",
    },
    "pp_woven_bag": {
        "label": "Woven PP reusable bag",
        "mass": 0.116, "plastic_mass": 0.116, "carbon": 0.290,
        "polymer": "pp", "reuses": 52,
        "note": "Fourteen times the material of a single-use bag and around "
                "nine uses to break even on carbon. Usually the best available "
                "option on both counts if it is actually reused.",
    },
    "cotton_tote": {
        "label": "Cotton tote bag",
        "mass": 0.120, "plastic_mass": 0.0, "carbon": 1.700,
        "polymer": None, "reuses": 52,
        "note": "Fifty-odd uses to break even on carbon against the bag it "
                "replaced, and considerably more on src.environment.water. The tote is a "
                "plastic solution and a carbon problem, and pretending "
                "otherwise is how this substitution became fashionable.",
    },
    "pet_bottle": {
        "label": "Single-use PET water bottle",
        "mass": 0.019, "plastic_mass": 0.019, "carbon": 0.083,
        "polymer": "pet", "reuses": 1,
        "note": "The one item where the recycling stream actually works, and "
                "still worse than not using one.",
    },
    "steel_bottle": {
        "label": "Stainless steel reusable bottle",
        "mass": 0.320, "plastic_mass": 0.010, "carbon": 2.400,
        "polymer": "pp", "reuses": 500,
        "note": "About twenty-nine uses to beat single-use PET on carbon, and "
                "it removes the plastic almost entirely after that.",
    },
}


def list_polymers() -> list:
    """Polymer keys, worst real recycling rate first."""
    return sorted(POLYMERS, key=lambda k: real_recycling_rate(k))


def get_polymer(key: str) -> dict:
    """One polymer's data, refusing an unknown key."""
    try:
        return dict(POLYMERS[key])
    except KeyError:
        raise PlasticError(
            f"No data for polymer '{key}'. Real recycling rates across this "
            f"table run from under 1% to over 70%, so an average would be "
            f"actively misleading. Known polymers: {', '.join(sorted(POLYMERS))}"
        ) from None


def get_region(key: str) -> dict:
    """One region's waste infrastructure."""
    try:
        return dict(REGIONS[key])
    except KeyError:
        raise PlasticError(
            f"Unknown region '{key}'. Infrastructure decides the fate of a "
            f"correctly sorted item, so it cannot be defaulted silently. Known "
            f"regions: {', '.join(sorted(REGIONS))}"
        ) from None


def real_recycling_rate(polymer: str) -> float:
    """Sorting yield times reprocessing yield.

    The number a symbol on a pack does not tell you. For multi-layer laminate it
    is well under one percent.
    """
    spec = POLYMERS.get(polymer)
    if spec is None:
        raise PlasticError(f"No data for polymer '{polymer}'.")
    return spec["sorting_yield"] * spec["reprocessing_yield"]


def fate(
    polymer: str,
    kg: float,
    region: str = "high_income_eu",
    sorted_correctly: bool = True,
) -> dict:
    """Route a mass of polymer through collection, sorting and reprocessing.

    Returns where it actually goes rather than whether it was recyclable. The
    shares always sum to the input mass, which the tests assert, because a fate
    model that loses mass is not a fate model.
    """
    if kg < 0:
        raise PlasticError("Mass cannot be negative.")

    spec = get_polymer(polymer)
    infra = get_region(region)

    collected = kg * infra["collection_rate"]
    uncollected = kg - collected

    if sorted_correctly:
        into_sorting = collected
        straight_to_residual = 0.0
    else:
        # An item put in the wrong bin is not sorted for recycling at all. It is
        # not destroyed either - it goes to residual treatment.
        into_sorting = 0.0
        straight_to_residual = collected

    survives_sorting = into_sorting * spec["sorting_yield"]
    rejected_at_sorting = into_sorting - survives_sorting
    recycled = survives_sorting * spec["reprocessing_yield"]
    rejected_at_reprocessing = survives_sorting - recycled

    residual = (
        straight_to_residual + rejected_at_sorting + rejected_at_reprocessing
    )
    incinerated = residual * infra["residual_incineration"]
    landfilled = residual * infra["residual_landfill"]

    # Uncollected waste splits between informal disposal that stays put and
    # material that reaches the environment.
    leaked = uncollected * MISMANAGED_TO_ENVIRONMENT
    informally_disposed = uncollected - leaked

    return {
        "polymer": polymer,
        "label": spec["label"],
        "kg": kg,
        "region": region,
        "region_label": infra["label"],
        "sorted_correctly": sorted_correctly,
        "recycled": recycled,
        "incinerated": incinerated,
        "landfilled": landfilled,
        "informally_disposed": informally_disposed,
        "leaked": leaked,
        "rejected_at_sorting": rejected_at_sorting,
        "rejected_at_reprocessing": rejected_at_reprocessing,
        "real_recycling_rate": recycled / kg if kg > 0 else 0.0,
        "nominal_recyclability": spec["sorting_yield"],
        "compartments": {
            compartment: leaked * share
            for compartment, share in MISMANAGED_COMPARTMENTS.items()
        },
        "carbon_kg_co2e": kg * spec["carbon_per_kg"],
        "note": spec["note"],
        "pla_warning": (
            "PLA needs industrial composting at sustained high temperature. "
            "This region has none, so it behaves as a contaminant in the "
            "recycling stream and close to conventional plastic anywhere else."
            if polymer == "pla" and not infra["industrial_composting"] else None
        ),
    }


def pathway_leakage(pathway: str, activity: float) -> dict:
    """Leakage from one non-bin pathway, split by receiving compartment.

    The compartments matter: most leaked plastic never reaches the sea, and
    treating every pathway as an ocean pathway sends effort to the wrong place.
    """
    try:
        spec = LEAKAGE_PATHWAYS[pathway]
    except KeyError:
        raise PlasticError(
            f"Unknown leakage pathway '{pathway}'. Known pathways: "
            f"{', '.join(sorted(LEAKAGE_PATHWAYS))}"
        ) from None
    if activity < 0:
        raise PlasticError("Activity cannot be negative.")

    released = activity * spec["factor"]
    return {
        "pathway": pathway,
        "label": spec["label"],
        "unit": spec["unit"],
        "activity": activity,
        "kg_released": released,
        "compartments": {
            compartment: released * share
            for compartment, share in spec["compartments"].items()
        },
        "polymer": spec["polymer"],
        "note": spec["note"],
    }


def household_leakage(
    packaging: dict,
    pathways: dict,
    region: str = "high_income_eu",
    sorting_accuracy: float = 0.85,
) -> dict:
    """Everything a household leaks, from bins and from everything else.

    ``packaging`` maps polymer keys to kilograms per year; ``pathways`` maps
    pathway keys to their own activity src.utils.units. ``sorting_accuracy`` is the share
    of recyclable packaging actually put in the right bin, which is the only
    lever in this whole calculation that a sorting guide addresses.
    """
    if not 0.0 <= sorting_accuracy <= 1.0:
        raise PlasticError("Sorting accuracy must lie between 0 and 1.")
    if not packaging and not pathways:
        raise PlasticError(
            "Nothing to model. Give at least some packaging or one pathway."
        )

    bin_rows = []
    bin_leaked = 0.0
    bin_recycled = 0.0
    bin_mass = 0.0
    bin_carbon = 0.0

    for polymer, kg in (packaging or {}).items():
        if kg < 0:
            raise PlasticError(f"Negative mass for '{polymer}'.")
        correct = fate(polymer, kg * sorting_accuracy, region, True)
        incorrect = fate(polymer, kg * (1 - sorting_accuracy), region, False)
        combined = _merge_fates(correct, incorrect)
        bin_rows.append(combined)
        bin_leaked += combined["leaked"]
        bin_recycled += combined["recycled"]
        bin_mass += kg
        bin_carbon += combined["carbon_kg_co2e"]

    bin_rows.sort(key=lambda row: -row["kg"])

    pathway_rows = []
    pathway_leaked = 0.0
    for pathway, activity in (pathways or {}).items():
        row = pathway_leakage(pathway, activity)
        pathway_rows.append(row)
        pathway_leaked += row["kg_released"]
    pathway_rows.sort(key=lambda row: -row["kg_released"])

    compartments = {"soil": 0.0, "freshwater": 0.0, "marine": 0.0, "air": 0.0}
    for row in bin_rows + pathway_rows:
        for compartment, value in row["compartments"].items():
            compartments[compartment] = compartments.get(compartment, 0.0) + value

    total_leaked = bin_leaked + pathway_leaked

    return {
        "packaging": bin_rows,
        "pathways": pathway_rows,
        "region": region,
        "sorting_accuracy": sorting_accuracy,
        "packaging_mass_kg": bin_mass,
        "packaging_recycled_kg": bin_recycled,
        "packaging_recycled_share": (
            bin_recycled / bin_mass if bin_mass > 0 else 0.0
        ),
        "bin_leakage_kg": bin_leaked,
        "pathway_leakage_kg": pathway_leaked,
        "total_leakage_kg": total_leaked,
        "pathway_share": (
            pathway_leaked / total_leaked if total_leaked > 0 else 0.0
        ),
        "compartments": compartments,
        "carbon_kg_co2e": bin_carbon,
    }


def _merge_fates(first: dict, second: dict) -> dict:
    """Add two fate results for the same polymer into one row."""
    merged = dict(first)
    for key in (
        "kg", "recycled", "incinerated", "landfilled", "informally_disposed",
        "leaked", "rejected_at_sorting", "rejected_at_reprocessing",
        "carbon_kg_co2e",
    ):
        merged[key] = first[key] + second[key]
    merged["compartments"] = {
        compartment: first["compartments"][compartment]
        + second["compartments"][compartment]
        for compartment in first["compartments"]
    }
    merged["real_recycling_rate"] = (
        merged["recycled"] / merged["kg"] if merged["kg"] > 0 else 0.0
    )
    merged["sorted_correctly"] = None
    return merged


def persistence_profile(
    polymer: str, kg_leaked: float, compartment: str = "soil", horizon: int = 100
) -> dict:
    """How much of a leaked mass is still out there, year by year.

    Reported because leaked mass alone files a gram of expanded polystyrene and
    a gram of uncoated paper as equivalent litter. Degradation is modelled as
    first-order against a residence time, which is a simplification - real
    fragmentation is not a clean exponential - and the module says so.
    """
    spec = get_polymer(polymer)
    if kg_leaked < 0:
        raise PlasticError("Leaked mass cannot be negative.")
    if horizon <= 0:
        raise PlasticError("Horizon must be positive.")
    if compartment not in ("soil", "marine"):
        raise PlasticError(
            "Residence times here are given for soil and marine compartments "
            "only. Freshwater residence is dominated by transport out of the "
            "compartment rather than by degradation, and modelling it as decay "
            "would be wrong."
        )

    residence = spec[f"{compartment}_years"]
    years = list(range(0, horizon + 1, max(1, horizon // 20)))
    remaining = [kg_leaked * math.exp(-year / residence) for year in years]

    half_life = residence * math.log(2)
    return {
        "polymer": polymer,
        "label": spec["label"],
        "compartment": compartment,
        "kg_leaked": kg_leaked,
        "residence_years": residence,
        "half_life_years": half_life,
        "years": years,
        "remaining_kg": remaining,
        "remaining_at_horizon": remaining[-1],
        "share_remaining_at_horizon": (
            remaining[-1] / kg_leaked if kg_leaked > 0 else 0.0
        ),
        "fragments": spec["fragments"],
        "caveat": (
            "First-order decay against a residence time. Real plastic does not "
            "disappear so much as fragment: the mass curve falls while the "
            "particle count rises, and the secondary microplastic stock keeps "
            "growing long after the original item is unrecognisable."
        ),
    }


def substitution(option_a: str, option_b: str, uses: int) -> dict:
    """Compare two options over a number of uses, on plastic and on carbon.

    Both numbers are always returned. A comparison that reported only the
    plastic would recommend a cotton tote without mentioning that it takes about
    fifty uses to break even on the carbon of the bag it replaced.
    """
    for key in (option_a, option_b):
        if key not in SUBSTITUTIONS:
            raise PlasticError(
                f"Unknown option '{key}'. Known options: "
                f"{', '.join(sorted(SUBSTITUTIONS))}"
            )
    if uses <= 0:
        raise PlasticError("Number of uses must be positive.")

    rows = []
    for key in (option_a, option_b):
        spec = SUBSTITUTIONS[key]
        units_needed = math.ceil(uses / spec["reuses"])
        rows.append({
            "option": key,
            "label": spec["label"],
            "units_needed": units_needed,
            "plastic_kg": units_needed * spec["plastic_mass"],
            "carbon_kg_co2e": units_needed * spec["carbon"],
            "reuses": spec["reuses"],
            "note": spec["note"],
        })

    a, b = rows
    plastic_delta = b["plastic_kg"] - a["plastic_kg"]
    carbon_delta = b["carbon_kg_co2e"] - a["carbon_kg_co2e"]

    return {
        "uses": uses,
        "options": rows,
        "plastic_delta_kg": plastic_delta,
        "carbon_delta_kg_co2e": carbon_delta,
        "is_a_trade": (plastic_delta * carbon_delta) < 0,
        "carbon_break_even_uses": carbon_break_even(option_a, option_b),
        "verdict": _substitution_verdict(a, b, plastic_delta, carbon_delta),
    }


def carbon_break_even(baseline: str, alternative: str) -> int | None:
    """Uses at which the alternative's carbon falls below the baseline's.

    Returns None where the alternative is better from the first use, and None
    also where it never catches up within a thousand uses - which is itself an
    answer, and the page says which of the two it was.
    """
    for key in (baseline, alternative):
        if key not in SUBSTITUTIONS:
            raise PlasticError(f"Unknown option '{key}'.")

    base = SUBSTITUTIONS[baseline]
    alt = SUBSTITUTIONS[alternative]

    for uses in range(1, 1001):
        base_carbon = math.ceil(uses / base["reuses"]) * base["carbon"]
        alt_carbon = math.ceil(uses / alt["reuses"]) * alt["carbon"]
        if alt_carbon <= base_carbon:
            return uses
    return None


def _substitution_verdict(a: dict, b: dict, plastic_delta: float,
                          carbon_delta: float) -> str:
    """Plain words for a substitution, including when it is a genuine trade."""
    if plastic_delta < 0 and carbon_delta < 0:
        return (
            f"{b['label']} is better on both counts at this number of uses: "
            f"{abs(plastic_delta):.3f} kg less plastic and "
            f"{abs(carbon_delta):.2f} kg less CO2e. No trade involved."
        )
    if plastic_delta > 0 and carbon_delta > 0:
        return (
            f"{b['label']} is worse on both counts at this number of uses. "
            f"There is no case for it here."
        )
    if plastic_delta < 0 < carbon_delta:
        return (
            f"A trade, not an improvement: {abs(plastic_delta):.3f} kg less "
            f"plastic for {carbon_delta:.2f} kg more CO2e. Whether that is "
            f"worth it depends on which impact you are trying to reduce, and "
            f"the honest answer is that the swap does not come free."
        )
    return (
        f"A trade in the other direction: {plastic_delta:.3f} kg more plastic "
        f"for {abs(carbon_delta):.2f} kg less CO2e."
    )


def rank_interventions(household: dict) -> list:
    """Rank a household's options by modelled leakage avoided.

    By effect size, not by how virtuous each one feels. On most inputs this puts
    tyres and laundry a long way above anything to do with straws or bags, which
    is the opposite of where consumer attention goes.
    """
    result = household
    options = []

    by_pathway = {row["pathway"]: row for row in result["pathways"]}

    if "tyre_wear" in by_pathway:
        current = by_pathway["tyre_wear"]["kg_released"]
        options.append({
            "intervention": "Drive 20% fewer kilometres",
            "avoided_kg": current * 0.20,
            "basis": "tyre_wear",
            "note": "Tyre wear scales directly with distance. Nothing else in "
                    "this list is as mechanically certain.",
        })
        options.append({
            "intervention": "Gentler acceleration and braking",
            "avoided_kg": current * 0.12,
            "basis": "tyre_wear",
            "note": "Abrasion rises sharply with lateral and longitudinal "
                    "force. Same distance, less rubber left on the road.",
        })

    if "textile_laundry" in by_pathway:
        current = by_pathway["textile_laundry"]["kg_released"]
        options.append({
            "intervention": "Fit a laundry filter",
            "avoided_kg": current * 0.55,
            "basis": "textile_laundry",
            "note": "Captures roughly half the fibres before they reach the "
                    "drain. Only worth doing if the captured lint goes to "
                    "residual waste rather than back down the sink.",
        })
        options.append({
            "intervention": "Wash full loads, cooler and less often",
            "avoided_kg": current * 0.25,
            "basis": "textile_laundry",
            "note": "Shedding scales with agitation and with the number of "
                    "washes rather than with the mass in the drum.",
        })

    if result["packaging"]:
        film = sum(
            row["kg"] for row in result["packaging"]
            if row["polymer"] in ("ldpe_film", "multilayer")
        )
        if film > 0:
            uncollected = 1.0 - get_region(result["region"])["collection_rate"]
            options.append({
                "intervention": "Avoid film and laminate packaging",
                "avoided_kg": film * uncollected * MISMANAGED_TO_ENVIRONMENT,
                "basis": "packaging",
                "note": "Film and multi-layer laminate have essentially no "
                        "recycling route, so avoiding them removes material "
                        "rather than redirecting it. The leakage avoided is "
                        "only the share that would have gone uncollected, "
                        "which in a high-collection region is small - the "
                        "stronger argument for avoiding them is that the rest "
                        "gets burned or buried, not that it escapes.",
            })

        options.append({
            "intervention": "Sort perfectly instead of at your current rate",
            "avoided_kg": 0.0,
            "basis": "packaging",
            "note": "Included deliberately with a zero. Sorting changes "
                    "whether material is recycled or burned; it does not "
                    "change how much escapes, because leakage happens to "
                    "uncollected waste rather than to badly sorted src.environment.waste. This "
                    "is worth doing and it is not a leakage intervention.",
        })

    options.sort(key=lambda row: -row["avoided_kg"])
    return options


def get_plastic_insights(result: dict) -> list:
    """Plain-language findings, emitted only where the result supports them."""
    insights = []
    total = result["total_leakage_kg"]

    if total <= 0:
        return ["No modelled leakage from these inputs."]

    if result["pathway_share"] > 0.5:
        insights.append(
            f"{result['pathway_share'] * 100:.0f}% of this household's plastic "
            f"leakage comes from pathways that have nothing to do with bins. "
            f"Sorting better will not touch that share."
        )

    if result["pathways"]:
        top = result["pathways"][0]
        share = top["kg_released"] / total * 100.0
        insights.append(
            f"{top['label']} alone is {share:.0f}% of the leakage."
        )

    compartments = result["compartments"]
    if sum(compartments.values()) > 0:
        marine_share = compartments.get("marine", 0.0) / sum(compartments.values())
        insights.append(
            f"Only {marine_share * 100:.0f}% of it reaches a marine "
            f"environment. Most leaked plastic stays in soil, which is where "
            f"the effort should go and almost never does."
        )

    if result["packaging"]:
        worst = min(
            result["packaging"], key=lambda row: row["real_recycling_rate"]
        )
        if worst["real_recycling_rate"] < 0.1 and worst["kg"] > 0:
            insights.append(
                f"{worst['label']} is recycled at "
                f"{worst['real_recycling_rate'] * 100:.1f}% in practice, "
                f"whatever the symbol on the pack says."
            )

        share = result["packaging_recycled_share"] * 100.0
        insights.append(
            f"{share:.0f}% of the packaging mass here actually becomes "
            f"secondary material. The rest is burned, buried or lost, and the "
            f"gap between that figure and the collection rate is the whole "
            f"issue."
        )

        pla_rows = [row for row in result["packaging"] if row.get("pla_warning")]
        if pla_rows:
            insights.append(pla_rows[0]["pla_warning"])

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plastic_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            total_leakage_kg REAL NOT NULL,
            pathway_share REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_plastic_profiles_user
        ON plastic_profiles (user_id)
        """
    )


def save_profile(user_id: str, name: str, result: dict) -> int:
    """Persist a household result and return its row id."""
    if not user_id:
        raise PlasticError("A profile needs a user to belong to.")
    if not name or not name.strip():
        raise PlasticError("A profile needs a name.")

    payload = json.dumps({
        "region": result["region"],
        "sorting_accuracy": result["sorting_accuracy"],
        "packaging": [
            {
                "polymer": row["polymer"],
                "kg": row["kg"],
                "recycled": row["recycled"],
                "leaked": row["leaked"],
            }
            for row in result["packaging"]
        ],
        "pathways": [
            {
                "pathway": row["pathway"],
                "activity": row["activity"],
                "kg_released": row["kg_released"],
            }
            for row in result["pathways"]
        ],
        "compartments": result["compartments"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO plastic_profiles
                (user_id, name, payload, total_leakage_kg, pathway_share)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload,
                float(result["total_leakage_kg"]),
                float(result["pathway_share"]),
            ),
        )
        return int(cursor.lastrowid)


def get_profiles(user_id: str) -> list:
    """Saved profiles for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, total_leakage_kg, pathway_share,
                       created_at
                FROM plastic_profiles
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved plastic profiles")
        return []

    profiles = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        profiles.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "total_leakage_kg": row[3],
            "pathway_share": row[4],
            "created_at": row[5],
        })
    return profiles


def delete_profile(user_id: str, profile_id: int) -> bool:
    """Delete one saved profile. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM plastic_profiles WHERE id = ? AND user_id = ?",
                (profile_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete plastic profile %s", profile_id)
        return False
