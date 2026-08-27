"""Reactive nitrogen and phosphorus, which climate accounting cannot see.

Every impact this app reports is denominated in kg CO2e. For food that is the
wrong single number more often than it is the right one. Agriculture crosses the
nutrient boundaries harder than it crosses the climate one, and a household that
optimises its diet on carbon alone will regularly move damage from the
atmosphere into groundwater without any indicator changing.

Why a carbon number hides this
------------------------------
Roughly 1% of applied nitrogen leaves as nitrous oxide. That 1% is a greenhouse
gas with a GWP100 of 273, so it is large enough to matter and it *is* already
inside the CO2e figure elsewhere in this app. The other 99% is ammonia, nitrate
and inert N2 - and of those, the ammonia and the nitrate are the ones doing the
damage to air quality and to water. Carbon accounting sees the 1% and is blind
to the part that dominates.

The consequence is a specific piece of bad advice this app can currently give.
Pork beats beef on carbon by a wide margin and loses to pasture beef on reactive
nitrogen per gram of protein, because pig feed runs through fertilised cereal
while a grazing animal recycles most of its own. Told only the carbon number, a
user switches and believes they have improved something.

A loss is not a loss until you say where it went
------------------------------------------------
The same kilogram of applied nitrogen splits four ways, and the split is decided
more by *how* it was applied than by *what* was applied:

*   **Volatilisation** to ammonia - an air quality problem, and a large one for
    surface-broadcast urea.
*   **Leaching** of nitrate to groundwater and rivers - the eutrophication
    pathway.
*   **Nitrous oxide** - the climate pathway, and the one already counted.
*   **Denitrification** to N2 - genuinely harmless, the atmosphere is 78% of it.

Collapsing these into one "nitrogen footprint" would repeat exactly the mistake
that carbon-only accounting makes, so this module keeps them apart at every
stage and only aggregates where the receiving system is the same.

Two waters, two limiting nutrients
-----------------------------------
Freshwater eutrophication is phosphorus-limited. Marine eutrophication is
nitrogen-limited. They are different receiving systems responding to different
inputs, and a single "eutrophication score" tells a user nothing about which one
they are loading. Both are reported, in their own conventional units.

The overlap is stated, never netted
------------------------------------
The N2O share of the nitrogen loss is already inside the CO2e total reported by
``emissions.py``. This module computes it and labels it as overlapping. Adding
this module's climate figure to the app's carbon figure would double-count, and
the only reliable defence against that is to say so wherever the number appears.

Boundaries that are already crossed
------------------------------------
For climate there is at least a positive per-capita budget left to spend. For
nitrogen and phosphorus there is not: current global flows run several times the
proposed safe operating space. A per-capita share is still the most legible
comparison available, so it is reported - with the transgression stated plainly
rather than left for a user to infer from a bar that is off the end of a chart.

Where this connects to code already merged
-------------------------------------------
*   ``meal_planner.py`` ranks diets on carbon alone.
*   ``garden_Assistant.py`` has no representation of fertiliser at all, though
    domestic over-application at three to four times crop requirement is common.
*   ``climate_metrics.py`` holds the GWP values this module reuses for the N2O
    overlap.
*   ``water_scarcity.py`` handles the quantity of water; this handles what is
    dissolved in it.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class NutrientError(ValueError):
    """Raised when a nutrient calculation was asked for something meaningless."""


# ---------------------------------------------------------------------------
# Constants
#
# GWP100 for N2O on the AR6 basis. Held here rather than imported so the engine
# stays importable without the rest of the app, but deliberately the same number
# ``climate_metrics.py`` uses - a disagreement between the two would show up as
# an unexplained gap between this module's climate figure and the app's.
# ---------------------------------------------------------------------------
N2O_GWP100 = 273.0

# Mass ratio of N2O to the nitrogen it contains: 44/28.
N2O_N_TO_N2O = 44.0 / 28.0

# Mass ratio of PO4 to the phosphorus it contains: 95/31.
P_TO_PO4 = 95.0 / 31.0

# Proposed safe operating space, per capita per year, on a world population of
# 8 billion. The global boundaries are ~62 Tg N/yr for intentional fixation and
# ~6.2 Tg P/yr for flow to the ocean. Current flows are roughly 150 Tg N and
# 22 Tg P, which is why the ratios below exceed one for almost every diet.
WORLD_POPULATION = 8.0e9
BOUNDARY_N_PER_CAPITA = 62.0e9 / WORLD_POPULATION * 1000.0   # kg N/cap/yr
BOUNDARY_P_PER_CAPITA = 6.2e9 / WORLD_POPULATION * 1000.0    # kg P/cap/yr

# Current global per-capita flows, for the "where the world actually is" line.
CURRENT_N_PER_CAPITA = 150.0e9 / WORLD_POPULATION * 1000.0
CURRENT_P_PER_CAPITA = 22.0e9 / WORLD_POPULATION * 1000.0


# ---------------------------------------------------------------------------
# Virtual nutrient factors
#
# ``n_applied`` and ``p_applied`` are kilograms of reactive nutrient applied to
# the land per kilogram of product at the farm gate, carrying the feed chain for
# animal products. They are *applied*, not lost - the loss depends on method and
# is computed separately, because that is where a household actually has
# leverage.
#
# ``protein_g`` is there because comparing a kilogram of lentils with a kilogram
# of beef by mass is not a comparison worth showing anyone. The protein-
# normalised view reverses several rankings and is the honest one.
# ---------------------------------------------------------------------------
FOOD_NUTRIENT_FACTORS = {
    "beef_pasture": {
        "label": "Beef (pasture raised)",
        "category": "meat",
        "n_applied": 0.140, "p_applied": 0.019, "protein_g": 260.0,
        "note": "Low applied nitrogen per kilogram because the nitrogen comes "
                "largely from grazed grass and recycled manure rather than from "
                "synthetic fertiliser. Its carbon footprint is the worst on this "
                "list; its nitrogen footprint is not.",
    },
    "beef_feedlot": {
        "label": "Beef (feedlot finished)",
        "category": "meat",
        "n_applied": 0.310, "p_applied": 0.045, "protein_g": 260.0,
        "note": "Grain finishing moves the nitrogen burden onto fertilised "
                "cereal, roughly doubling the applied nitrogen relative to "
                "pasture for a modest carbon saving.",
    },
    "lamb": {
        "label": "Lamb and mutton",
        "category": "meat",
        "n_applied": 0.155, "p_applied": 0.021, "protein_g": 250.0,
        "note": "Mostly extensive grazing, so the nitrogen profile resembles "
                "pasture beef more than it resembles pork.",
    },
    "pork": {
        "label": "Pork",
        "category": "meat",
        "n_applied": 0.185, "p_applied": 0.038, "protein_g": 270.0,
        "note": "Feed conversion around 3:1 on fertilised cereal, plus slurry "
                "that volatilises heavily. Beats beef on carbon and loses to "
                "pasture beef on reactive nitrogen per gram of protein.",
    },
    "chicken": {
        "label": "Chicken",
        "category": "meat",
        "n_applied": 0.135, "p_applied": 0.029, "protein_g": 290.0,
        "note": "The best feed conversion of any land animal, so the lowest "
                "nitrogen of the meats - but still several times any legume "
                "once normalised for protein.",
    },
    "eggs": {
        "label": "Eggs",
        "category": "animal_product",
        "n_applied": 0.095, "p_applied": 0.021, "protein_g": 125.0,
        "note": "Layer feed is cereal and soy; the nitrogen follows the feed.",
    },
    "milk": {
        "label": "Milk",
        "category": "animal_product",
        "n_applied": 0.021, "p_applied": 0.0035, "protein_g": 33.0,
        "note": "Low per kilogram because milk is mostly water. Per gram of "
                "protein it is comparable to chicken.",
    },
    "cheese": {
        "label": "Cheese",
        "category": "animal_product",
        "n_applied": 0.190, "p_applied": 0.031, "protein_g": 250.0,
        "note": "Around ten litres of milk per kilogram, so ten times the "
                "nitrogen. Cheese is where dairy stops being a low-impact food.",
    },
    "wheat": {
        "label": "Wheat and wheat flour",
        "category": "cereal",
        "n_applied": 0.024, "p_applied": 0.0042, "protein_g": 110.0,
        "note": "The reference crop for temperate fertiliser use. Around "
                "180 kg N/ha at a 7.5 t/ha yield.",
    },
    "rice": {
        "label": "Rice",
        "category": "cereal",
        "n_applied": 0.028, "p_applied": 0.0048, "protein_g": 71.0,
        "note": "Flooded paddies make rice the worst cereal on methane and only "
                "an ordinary one on nitrogen. A good example of why one number "
                "cannot rank foods.",
    },
    "maize": {
        "label": "Maize",
        "category": "cereal",
        "n_applied": 0.021, "p_applied": 0.0039, "protein_g": 92.0,
        "note": "High yielding, so the per-kilogram figure is low despite heavy "
                "field application.",
    },
    "lentils": {
        "label": "Lentils and pulses",
        "category": "legume",
        "n_applied": 0.005, "p_applied": 0.0037, "protein_g": 250.0,
        "note": "Legumes fix their own nitrogen. The applied figure covers a "
                "starter dressing only, and it is an order of magnitude below "
                "any animal protein.",
    },
    "soy": {
        "label": "Soybeans",
        "category": "legume",
        "n_applied": 0.006, "p_applied": 0.0058, "protein_g": 360.0,
        "note": "Nitrogen fixing, but a meaningful phosphorus demand. The "
                "lowest reactive nitrogen per gram of protein of any food here.",
    },
    "tofu": {
        "label": "Tofu",
        "category": "legume",
        "n_applied": 0.012, "p_applied": 0.0110, "protein_g": 160.0,
        "note": "Processing losses mean roughly two kilograms of soybean per "
                "kilogram of tofu.",
    },
    "vegetables_field": {
        "label": "Field vegetables",
        "category": "produce",
        "n_applied": 0.009, "p_applied": 0.0018, "protein_g": 18.0,
        "note": "Low in absolute terms, but vegetables are not a protein source "
                "and the protein-normalised view should not be read for them.",
    },
    "vegetables_greenhouse": {
        "label": "Greenhouse vegetables",
        "category": "produce",
        "n_applied": 0.016, "p_applied": 0.0031, "protein_g": 14.0,
        "note": "Fertigation is efficient in application but generous in dose; "
                "the carbon footprint is where greenhouse produce really loses.",
    },
    "potatoes": {
        "label": "Potatoes",
        "category": "produce",
        "n_applied": 0.007, "p_applied": 0.0016, "protein_g": 20.0,
        "note": "A high-yielding crop, so a low figure per kilogram.",
    },
    "fruit": {
        "label": "Fruit (orchard and field)",
        "category": "produce",
        "n_applied": 0.008, "p_applied": 0.0015, "protein_g": 8.0,
        "note": "Perennial systems generally apply less than annual arable.",
    },
    "nuts": {
        "label": "Nuts",
        "category": "produce",
        "n_applied": 0.045, "p_applied": 0.0088, "protein_g": 200.0,
        "note": "Irrigated orchard nuts carry a real nitrogen and water burden "
                "that their reputation as a low-carbon protein tends to hide.",
    },
    "farmed_fish": {
        "label": "Farmed fish",
        "category": "seafood",
        "n_applied": 0.070, "p_applied": 0.0180, "protein_g": 200.0,
        "note": "Feed-derived, plus direct nutrient release from cages straight "
                "into the receiving water with no soil buffer at all.",
    },
    "wild_fish": {
        "label": "Wild caught fish",
        "category": "seafood",
        "n_applied": 0.0, "p_applied": 0.0, "protein_g": 200.0,
        "note": "No applied nutrient - which says nothing about stock status or "
                "fuel use, both of which are outside this module.",
    },
}


# ---------------------------------------------------------------------------
# Loss pathway partitions
#
# Fractions of applied nitrogen leaving by each route. They sum to one with crop
# uptake, and the differences between methods are larger than the differences
# between fertiliser products - which is the practical finding this table exists
# to make visible.
# ---------------------------------------------------------------------------
APPLICATION_METHODS = {
    "broadcast_surface": {
        "label": "Surface broadcast, not incorporated",
        "volatilisation": 0.220, "leaching": 0.190, "n2o": 0.012,
        "denitrification": 0.058, "uptake": 0.520,
        "note": "Urea left on the surface hydrolyses and the ammonia goes "
                "straight up. The single worst thing a gardener can do with a "
                "bag of fertiliser, and the most common.",
    },
    "broadcast_incorporated": {
        "label": "Broadcast then incorporated",
        "volatilisation": 0.060, "leaching": 0.185, "n2o": 0.011,
        "denitrification": 0.074, "uptake": 0.670,
        "note": "Working it into the soil within a day cuts volatilisation by "
                "roughly three quarters at no cost beyond the effort.",
    },
    "split_dose": {
        "label": "Split dose, matched to growth",
        "volatilisation": 0.048, "leaching": 0.105, "n2o": 0.009,
        "denitrification": 0.058, "uptake": 0.780,
        "note": "Applying when the crop can take it up is the largest single "
                "improvement available, and it uses less fertiliser overall.",
    },
    "fertigation": {
        "label": "Fertigation or drip",
        "volatilisation": 0.030, "leaching": 0.080, "n2o": 0.008,
        "denitrification": 0.042, "uptake": 0.840,
        "note": "The most efficient method per kilogram applied. Efficiency in "
                "application is not the same as restraint in dose.",
    },
    "injected_slurry": {
        "label": "Injected slurry or manure",
        "volatilisation": 0.075, "leaching": 0.150, "n2o": 0.014,
        "denitrification": 0.091, "uptake": 0.670,
        "note": "Injection avoids most of the ammonia loss that surface-spread "
                "slurry suffers, at some cost in nitrous oxide.",
    },
    "surface_slurry": {
        "label": "Surface spread slurry or manure",
        "volatilisation": 0.400, "leaching": 0.140, "n2o": 0.010,
        "denitrification": 0.070, "uptake": 0.380,
        "note": "Forty percent of the nitrogen is in the air within days. "
                "Organic does not mean well retained.",
    },
    "compost_topdress": {
        "label": "Compost, surface applied",
        "volatilisation": 0.045, "leaching": 0.035, "n2o": 0.006,
        "denitrification": 0.034, "uptake": 0.880,
        "note": "Nitrogen in compost is bound in organic matter and released "
                "slowly, so very little is available to leach at any one time.",
    },
}

# Phosphorus does not volatilise. It is lost by runoff and erosion, and the
# controlling variable is whether the particle moves, not what the fertiliser
# was. Rates are fractions of applied P.
P_LOSS_BY_SLOPE = {
    "flat_stable": {
        "label": "Flat, vegetated, stable soil",
        "runoff": 0.020,
        "note": "Phosphorus binds tightly to soil. If the soil stays put, so "
                "does the phosphorus.",
    },
    "gentle": {
        "label": "Gentle slope, some bare periods",
        "runoff": 0.055,
        "note": "Bare soil over winter is where most annual phosphorus loss "
                "from arable land actually happens.",
    },
    "steep_bare": {
        "label": "Steep or frequently bare",
        "runoff": 0.130,
        "note": "Erosion-driven. Cover cropping addresses this directly and "
                "changing fertiliser product does not.",
    },
    "hydroponic": {
        "label": "Hydroponic or contained",
        "runoff": 0.005,
        "note": "Contained systems leak very little, provided the spent "
                "solution is not simply poured away.",
    },
}


# ---------------------------------------------------------------------------
# Fertiliser products
#
# ``n_fraction`` and ``p_fraction`` are mass fractions of elemental nutrient.
# Note that bag labels quote P as P2O5, which is 43.6% phosphorus - a discrepancy
# that silently inflates domestic phosphorus estimates by more than a factor of
# two if it is not handled, so it is handled here.
# ---------------------------------------------------------------------------
P2O5_TO_P = 0.4364
K2O_TO_K = 0.8301

FERTILISERS = {
    "urea": {
        "label": "Urea (46-0-0)",
        "n_fraction": 0.460, "p_fraction": 0.0, "organic": False,
        "default_method": "broadcast_surface",
        "note": "The cheapest nitrogen per kilogram and the most volatile. "
                "Incorporating it changes its loss profile more than switching "
                "product would.",
    },
    "ammonium_nitrate": {
        "label": "Ammonium nitrate (34.5-0-0)",
        "n_fraction": 0.345, "p_fraction": 0.0, "organic": False,
        "default_method": "broadcast_incorporated",
        "note": "Half the nitrogen is immediately available as nitrate, which "
                "means it is immediately available to leach.",
    },
    "npk_growmore": {
        "label": "General purpose NPK (7-7-7)",
        "n_fraction": 0.070, "p_fraction": 0.070 * P2O5_TO_P, "organic": False,
        "default_method": "broadcast_surface",
        "note": "The default domestic product. The 7 on the bag is P2O5, so the "
                "actual phosphorus is 3.1%.",
    },
    "poultry_manure": {
        "label": "Pelleted poultry manure",
        "n_fraction": 0.045, "p_fraction": 0.020, "organic": True,
        "default_method": "compost_topdress",
        "note": "Genuinely a fertiliser and not a soil conditioner - the "
                "nutrient concentration is high enough to over-apply easily.",
    },
    "garden_compost": {
        "label": "Garden compost",
        "n_fraction": 0.005, "p_fraction": 0.0012, "organic": True,
        "default_method": "compost_topdress",
        "note": "Low concentration, slow release, and the nutrient was already "
                "in your food system - so it is recovery rather than new input.",
    },
    "cattle_slurry": {
        "label": "Cattle slurry",
        "n_fraction": 0.0035, "p_fraction": 0.0007, "organic": True,
        "default_method": "surface_slurry",
        "note": "Mostly water. The ammonia loss on surface spreading is the "
                "dominant term.",
    },
    "bone_meal": {
        "label": "Bone meal",
        "n_fraction": 0.035, "p_fraction": 0.080, "organic": True,
        "default_method": "broadcast_incorporated",
        "note": "A phosphorus product. Most domestic soils that have been "
                "manured for years already have more phosphorus than they need.",
    },
}


# ---------------------------------------------------------------------------
# Eutrophication characterisation
#
# Freshwater responds to phosphorus, marine to nitrogen. Two indicators, two
# units, and the module refuses to add them together anywhere.
# ---------------------------------------------------------------------------
FRESHWATER_PO4_PER_KG_P = P_TO_PO4          # kg PO4-eq per kg P reaching water
MARINE_N_EQ_PER_KG_N = 1.0                  # kg N-eq per kg N reaching water

# Fraction of a leached or run-off load that actually reaches a water body
# rather than being retained in soil, riparian strips or groundwater with a long
# residence time. Sometimes called the delivery ratio; it is the least certain
# number in the whole module.
DEFAULT_DELIVERY_RATIO_N = 0.65
DEFAULT_DELIVERY_RATIO_P = 0.45


def list_foods(category: str | None = None) -> list:
    """Food keys, optionally filtered to one category, in a stable order."""
    keys = sorted(FOOD_NUTRIENT_FACTORS)
    if category is None:
        return keys
    return [k for k in keys if FOOD_NUTRIENT_FACTORS[k]["category"] == category]


def list_categories() -> list:
    """The distinct food categories present in the factor table."""
    return sorted({v["category"] for v in FOOD_NUTRIENT_FACTORS.values()})


def get_food(key: str) -> dict:
    """One food's factors.

    Refuses an unknown key rather than substituting an average. A category
    average across this table spans more than an order of magnitude, so the
    average would be worse than no answer.
    """
    try:
        return dict(FOOD_NUTRIENT_FACTORS[key])
    except KeyError:
        raise NutrientError(
            f"No nutrient factors for '{key}'. This table spans more than an "
            f"order of magnitude between legumes and feedlot beef, so no "
            f"average would be meaningful. Known foods: "
            f"{', '.join(list_foods())}"
        ) from None


def list_methods() -> list:
    """Application methods, worst retention first."""
    return sorted(
        APPLICATION_METHODS,
        key=lambda k: APPLICATION_METHODS[k]["uptake"],
    )


def get_method(key: str) -> dict:
    """One application method's loss partition."""
    try:
        return dict(APPLICATION_METHODS[key])
    except KeyError:
        raise NutrientError(
            f"Unknown application method '{key}'. Method changes the answer "
            f"more than product choice does, so it cannot be defaulted "
            f"silently. Known methods: {', '.join(sorted(APPLICATION_METHODS))}"
        ) from None


def get_fertiliser(key: str) -> dict:
    """One fertiliser product, with elemental (not oxide) nutrient fractions."""
    try:
        return dict(FERTILISERS[key])
    except KeyError:
        raise NutrientError(
            f"Unknown fertiliser '{key}'. Known products: "
            f"{', '.join(sorted(FERTILISERS))}"
        ) from None


def list_fertilisers() -> list:
    """Fertiliser keys, strongest nitrogen concentration first."""
    return sorted(
        FERTILISERS, key=lambda k: -FERTILISERS[k]["n_fraction"]
    )


def partition_nitrogen(kg_n_applied: float, method: str) -> dict:
    """Split applied nitrogen across its four fates plus crop uptake.

    Returns kilograms of N by pathway. The four loss pathways plus uptake sum to
    the applied mass, which the tests assert, because a partition that does not
    close is a partition that has lost track of something.
    """
    if kg_n_applied < 0:
        raise NutrientError("Applied nitrogen cannot be negative.")

    partition = get_method(method)
    result = {
        pathway: kg_n_applied * partition[pathway]
        for pathway in ("volatilisation", "leaching", "n2o",
                        "denitrification", "uptake")
    }
    result["applied"] = kg_n_applied
    result["lost_total"] = (
        result["volatilisation"] + result["leaching"]
        + result["n2o"] + result["denitrification"]
    )
    # Denitrified nitrogen returns to the atmosphere as N2, which is inert. It
    # is a loss to the farmer and not a loss to anybody else, and lumping it in
    # with nitrate would overstate the harm by around a third.
    result["reactive_lost"] = (
        result["volatilisation"] + result["leaching"] + result["n2o"]
    )
    result["method"] = method
    return result


def partition_phosphorus(kg_p_applied: float, slope: str) -> dict:
    """Split applied phosphorus into runoff and retained.

    Phosphorus does not volatilise and barely leaches; it moves when soil moves.
    That is why the controlling parameter here is slope and cover rather than
    the fertiliser product.
    """
    if kg_p_applied < 0:
        raise NutrientError("Applied phosphorus cannot be negative.")
    try:
        profile = P_LOSS_BY_SLOPE[slope]
    except KeyError:
        raise NutrientError(
            f"Unknown slope and cover class '{slope}'. Known classes: "
            f"{', '.join(sorted(P_LOSS_BY_SLOPE))}"
        ) from None

    runoff = kg_p_applied * profile["runoff"]
    return {
        "applied": kg_p_applied,
        "runoff": runoff,
        "retained": kg_p_applied - runoff,
        "slope": slope,
        "note": profile["note"],
    }


def n2o_climate_overlap(kg_n_as_n2o: float) -> dict:
    """The part of a nitrogen loss that the app's carbon number already counts.

    Returned as its own object with an explicit flag, so that no caller can
    reasonably add it to a CO2e total without noticing.
    """
    if kg_n_as_n2o < 0:
        raise NutrientError("Nitrous oxide nitrogen cannot be negative.")

    kg_n2o = kg_n_as_n2o * N2O_N_TO_N2O
    return {
        "kg_n_as_n2o": kg_n_as_n2o,
        "kg_n2o": kg_n2o,
        "kg_co2e": kg_n2o * N2O_GWP100,
        "gwp100": N2O_GWP100,
        "overlaps_carbon_total": True,
        "warning": (
            "This CO2e figure is already inside the carbon footprint reported "
            "elsewhere in the app. It is shown so the climate share of the "
            "nitrogen loss is visible, not so it can be added on top."
        ),
    }


def eutrophication_potential(
    kg_n_leached: float,
    kg_p_runoff: float,
    delivery_n: float = DEFAULT_DELIVERY_RATIO_N,
    delivery_p: float = DEFAULT_DELIVERY_RATIO_P,
) -> dict:
    """Freshwater and marine eutrophication, kept in separate units.

    They are not summed, and there is no combined score, because freshwater is
    phosphorus-limited and marine is nitrogen-limited. A single number would
    tell a user nothing about which system they are loading.
    """
    for name, ratio in (("nitrogen", delivery_n), ("phosphorus", delivery_p)):
        if not 0.0 <= ratio <= 1.0:
            raise NutrientError(
                f"Delivery ratio for {name} must lie between 0 and 1."
            )

    n_delivered = max(0.0, kg_n_leached) * delivery_n
    p_delivered = max(0.0, kg_p_runoff) * delivery_p

    return {
        "freshwater_po4_eq": p_delivered * FRESHWATER_PO4_PER_KG_P,
        "marine_n_eq": n_delivered * MARINE_N_EQ_PER_KG_N,
        "n_delivered_kg": n_delivered,
        "p_delivered_kg": p_delivered,
        "delivery_n": delivery_n,
        "delivery_p": delivery_p,
        "limiting_nutrients": {
            "freshwater": "phosphorus",
            "marine": "nitrogen",
        },
        "caveat": (
            "Delivery ratios are the least certain numbers here. Retention in "
            "soil and riparian buffers varies by catchment, and groundwater "
            "residence times mean some of today's leaching arrives decades "
            "from now."
        ),
    }


def food_footprint(
    items: dict,
    method: str = "broadcast_incorporated",
    slope: str = "gentle",
) -> dict:
    """Nutrient footprint of a basket of foods, in kilograms consumed.

    ``items`` maps food keys to kilograms. The result carries the applied
    nutrient, the loss partition, both eutrophication indicators, the climate
    overlap, and a protein-normalised view.
    """
    if not items:
        raise NutrientError("An empty basket has no footprint to report.")

    total_n_applied = 0.0
    total_p_applied = 0.0
    total_protein_g = 0.0
    per_item = []

    for key, kg in items.items():
        if kg < 0:
            raise NutrientError(
                f"Negative quantity for '{key}'. Consumption cannot be negative."
            )
        food = get_food(key)
        n_applied = food["n_applied"] * kg
        p_applied = food["p_applied"] * kg
        protein = food["protein_g"] * kg

        total_n_applied += n_applied
        total_p_applied += p_applied
        total_protein_g += protein

        per_item.append({
            "key": key,
            "label": food["label"],
            "category": food["category"],
            "kg": kg,
            "n_applied": n_applied,
            "p_applied": p_applied,
            "protein_g": protein,
            "n_per_100g_protein": (
                n_applied / protein * 100.0 if protein > 0 else None
            ),
            "note": food["note"],
        })

    per_item.sort(key=lambda row: -row["n_applied"])

    n_split = partition_nitrogen(total_n_applied, method)
    p_split = partition_phosphorus(total_p_applied, slope)
    eutro = eutrophication_potential(n_split["leaching"], p_split["runoff"])
    overlap = n2o_climate_overlap(n_split["n2o"])

    return {
        "items": per_item,
        "n_applied_kg": total_n_applied,
        "p_applied_kg": total_p_applied,
        "protein_g": total_protein_g,
        "n_split": n_split,
        "p_split": p_split,
        "eutrophication": eutro,
        "climate_overlap": overlap,
        "reactive_n_lost_kg": n_split["reactive_lost"],
        "n_per_100g_protein": (
            total_n_applied / total_protein_g * 100.0
            if total_protein_g > 0 else None
        ),
        "method": method,
        "slope": slope,
    }


def compare_by_protein(keys: list | None = None) -> list:
    """Rank foods by reactive nitrogen per 100 g of protein.

    This is the ranking that disagrees with the carbon ranking, and it is the
    reason the module exists. Foods with negligible protein are excluded rather
    than shown with an enormous ratio, because a lettuce is not a failed protein
    source.
    """
    keys = keys or list_foods()
    rows = []
    for key in keys:
        food = get_food(key)
        if food["protein_g"] < 30.0:
            continue
        per_100g = food["n_applied"] / food["protein_g"] * 100.0
        rows.append({
            "key": key,
            "label": food["label"],
            "category": food["category"],
            "n_per_100g_protein": per_100g,
            "n_per_kg": food["n_applied"],
            "protein_g_per_kg": food["protein_g"],
            "note": food["note"],
        })
    rows.sort(key=lambda row: row["n_per_100g_protein"])
    return rows


def fertiliser_application(
    fertiliser: str,
    kg_product: float,
    area_m2: float,
    method: str | None = None,
    slope: str = "gentle",
    crop_requirement_kg_n: float | None = None,
) -> dict:
    """What a bag of fertiliser on a garden bed actually does.

    ``crop_requirement_kg_n`` is optional; supplying it produces an
    over-application ratio, which is the number most likely to change a
    gardener's behaviour. Domestic application at three to four times crop
    requirement is common and the excess leaches almost in full, because there
    is nothing left to take it up.
    """
    if kg_product <= 0:
        raise NutrientError("Fertiliser quantity must be positive.")
    if area_m2 <= 0:
        raise NutrientError("Application area must be positive.")

    product = get_fertiliser(fertiliser)
    method = method or product["default_method"]

    kg_n = kg_product * product["n_fraction"]
    kg_p = kg_product * product["p_fraction"]

    n_split = partition_nitrogen(kg_n, method)
    p_split = partition_phosphorus(kg_p, slope)
    eutro = eutrophication_potential(n_split["leaching"], p_split["runoff"])
    overlap = n2o_climate_overlap(n_split["n2o"])

    result = {
        "fertiliser": fertiliser,
        "label": product["label"],
        "kg_product": kg_product,
        "area_m2": area_m2,
        "kg_n": kg_n,
        "kg_p": kg_p,
        "n_rate_kg_per_ha": kg_n / area_m2 * 10000.0,
        "p_rate_kg_per_ha": kg_p / area_m2 * 10000.0,
        "method": method,
        "method_label": get_method(method)["label"],
        "method_note": get_method(method)["note"],
        "n_split": n_split,
        "p_split": p_split,
        "eutrophication": eutro,
        "climate_overlap": overlap,
        "product_note": product["note"],
    }

    if crop_requirement_kg_n is not None:
        if crop_requirement_kg_n <= 0:
            raise NutrientError("Crop nitrogen requirement must be positive.")
        ratio = kg_n / crop_requirement_kg_n
        result["over_application_ratio"] = ratio
        result["excess_kg_n"] = max(0.0, kg_n - crop_requirement_kg_n)
        result["over_application_verdict"] = _over_application_verdict(ratio)

    return result


def _over_application_verdict(ratio: float) -> str:
    """Plain words for an over-application ratio."""
    if ratio <= 1.05:
        return (
            "Matched to what the crop can use. Almost all of the loss here is "
            "unavoidable background rather than waste."
        )
    if ratio <= 1.5:
        return (
            "Modestly over the requirement. The excess has nothing to take it "
            "up and will leach in close to full."
        )
    if ratio <= 3.0:
        return (
            "Two to three times what the crop needs. This is the common "
            "domestic pattern and roughly two thirds of the fertiliser is "
            "money spent on a pollutant."
        )
    return (
        "More than three times the requirement. Halving the dose would cost "
        "nothing in yield and would remove most of the loss."
    )


def compare_methods(kg_n_applied: float) -> list:
    """The same nitrogen applied every way, ranked by reactive loss.

    Runs the comparison the module was built to make: method beats product.
    """
    rows = []
    for key in APPLICATION_METHODS:
        split = partition_nitrogen(kg_n_applied, key)
        rows.append({
            "key": key,
            "label": APPLICATION_METHODS[key]["label"],
            "reactive_lost": split["reactive_lost"],
            "volatilisation": split["volatilisation"],
            "leaching": split["leaching"],
            "n2o": split["n2o"],
            "uptake": split["uptake"],
            "uptake_fraction": APPLICATION_METHODS[key]["uptake"],
            "note": APPLICATION_METHODS[key]["note"],
        })
    rows.sort(key=lambda row: row["reactive_lost"])
    return rows


def planetary_boundary_share(kg_n: float, kg_p: float) -> dict:
    """A per-capita share of the proposed safe operating space.

    Reported with the transgression stated in words. A bar chart running off the
    end of its axis is not an explanation, and for nitrogen and phosphorus the
    global position is not "approaching a limit" but "several times past one".
    """
    if kg_n < 0 or kg_p < 0:
        raise NutrientError("Nutrient totals cannot be negative.")

    n_share = kg_n / BOUNDARY_N_PER_CAPITA
    p_share = kg_p / BOUNDARY_P_PER_CAPITA

    return {
        "n_kg": kg_n,
        "p_kg": kg_p,
        "n_boundary_per_capita": BOUNDARY_N_PER_CAPITA,
        "p_boundary_per_capita": BOUNDARY_P_PER_CAPITA,
        "n_share_of_boundary": n_share,
        "p_share_of_boundary": p_share,
        "world_n_share": CURRENT_N_PER_CAPITA / BOUNDARY_N_PER_CAPITA,
        "world_p_share": CURRENT_P_PER_CAPITA / BOUNDARY_P_PER_CAPITA,
        "context": (
            "Unlike the carbon budget, where a positive per-capita allowance "
            "remains, global reactive nitrogen runs at roughly two and a half "
            "times the proposed boundary and phosphorus flow to the ocean at "
            "roughly three and a half times. A share below one here is not "
            "'within budget' in any collective sense; it is below a level the "
            "world as a whole is nowhere near."
        ),
    }


def household_nutrient_balance(
    food_items: dict,
    compost_kg: float = 0.0,
    compost_returned_to_soil: bool = True,
    method: str = "broadcast_incorporated",
    slope: str = "gentle",
) -> dict:
    """Nutrients in via food, out via compost, and the net import.

    Composting is framed everywhere else in this app as waste diversion. It is
    also nutrient recovery, and the second framing is the one that changes what
    people do, because it turns a bin into a fertiliser supply with a number
    attached.
    """
    if compost_kg < 0:
        raise NutrientError("Compost mass cannot be negative.")

    footprint = food_footprint(food_items, method=method, slope=slope)
    compost = get_fertiliser("garden_compost")

    recovered_n = compost_kg * compost["n_fraction"]
    recovered_p = compost_kg * compost["p_fraction"]

    if not compost_returned_to_soil:
        # Composted but sent away is still diversion from landfill; it is not
        # recovery for this household, and the balance should not pretend it is.
        recovered_n = 0.0
        recovered_p = 0.0

    net_n = footprint["n_applied_kg"] - recovered_n
    net_p = footprint["p_applied_kg"] - recovered_p

    return {
        "footprint": footprint,
        "compost_kg": compost_kg,
        "returned_to_soil": compost_returned_to_soil,
        "recovered_n_kg": recovered_n,
        "recovered_p_kg": recovered_p,
        "net_n_kg": net_n,
        "net_p_kg": net_p,
        "recovery_fraction_n": (
            recovered_n / footprint["n_applied_kg"]
            if footprint["n_applied_kg"] > 0 else 0.0
        ),
        "boundary": planetary_boundary_share(net_n, net_p),
        "note": (
            "Recovery through compost is real but small against the virtual "
            "nutrient embedded upstream in food. Most of the nitrogen behind a "
            "diet was lost in a field before the food was harvested, and no "
            "amount of kitchen composting reaches it. The lever is the diet."
        ),
    }


def get_nutrient_insights(result: dict) -> list:
    """Plain-language findings from a footprint result.

    Each insight is only emitted when the result actually supports it, so the
    page never prints generic advice dressed up as an analysis.
    """
    insights = []
    split = result["n_split"]
    reactive = split["reactive_lost"]

    if reactive > 0:
        dominant = max(
            ("volatilisation", "leaching", "n2o"),
            key=lambda pathway: split[pathway],
        )
        share = split[dominant] / reactive * 100.0
        labels = {
            "volatilisation": (
                "ammonia to air - an air quality problem, and the pathway most "
                "responsive to how the nutrient was applied"
            ),
            "leaching": (
                "nitrate to water - the eutrophication pathway, and the one "
                "responsive to dose and timing rather than method"
            ),
            "n2o": (
                "nitrous oxide - the climate pathway, and the only part of this "
                "already visible in the app's carbon number"
            ),
        }
        insights.append(
            f"{share:.0f}% of the reactive nitrogen loss is {labels[dominant]}."
        )

    denit_share = split["denitrification"] / split["applied"] * 100.0 \
        if split["applied"] > 0 else 0.0
    if denit_share > 4.0:
        insights.append(
            f"{denit_share:.0f}% of the applied nitrogen is denitrified to inert "
            f"N2. That is a loss to the grower and harmless to everyone else, "
            f"which is why it is excluded from the reactive total."
        )

    overlap = result["climate_overlap"]
    if overlap["kg_co2e"] > 0:
        insights.append(
            f"The nitrous oxide share is worth {overlap['kg_co2e']:.1f} kg CO2e "
            f"at GWP100 {overlap['gwp100']:.0f} - already counted in the app's "
            f"carbon total, so do not add it on."
        )

    eutro = result["eutrophication"]
    if eutro["freshwater_po4_eq"] > 0 or eutro["marine_n_eq"] > 0:
        insights.append(
            f"Freshwater loading is {eutro['freshwater_po4_eq']:.2f} kg PO4-eq "
            f"and marine loading {eutro['marine_n_eq']:.2f} kg N-eq. These are "
            f"different receiving systems with different limiting nutrients and "
            f"there is deliberately no combined score."
        )

    items = result.get("items") or []
    if len(items) > 1:
        top = items[0]
        share = top["n_applied"] / result["n_applied_kg"] * 100.0 \
            if result["n_applied_kg"] > 0 else 0.0
        if share > 35.0:
            insights.append(
                f"{top['label']} alone accounts for {share:.0f}% of the applied "
                f"nitrogen in this basket."
            )

    ratio = result.get("n_per_100g_protein")
    if ratio is not None and result["protein_g"] > 0:
        soy = get_food("soy")
        best = soy["n_applied"] / soy["protein_g"] * 100.0
        if ratio > best * 3:
            insights.append(
                f"Per 100 g of protein this basket applies {ratio / best:.0f} "
                f"times the nitrogen that soybeans do. Protein source, not "
                f"food miles or packaging, is where this number is decided."
            )

    return insights


# ---------------------------------------------------------------------------
# Persistence
#
# Tables are created lazily on first write so importing this module never
# touches the database, and nothing here modifies a table another module owns.
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS nutrient_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            n_applied_kg REAL NOT NULL,
            p_applied_kg REAL NOT NULL,
            reactive_n_lost_kg REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_nutrient_scenarios_user
        ON nutrient_scenarios (user_id)
        """
    )


def save_scenario(user_id: str, name: str, result: dict) -> int:
    """Persist a footprint result and return its row id."""
    if not user_id:
        raise NutrientError("A scenario needs a user to belong to.")
    if not name or not name.strip():
        raise NutrientError("A scenario needs a name.")

    payload = json.dumps({
        "items": result.get("items"),
        "method": result.get("method"),
        "slope": result.get("slope"),
        "n_split": result.get("n_split"),
        "p_split": result.get("p_split"),
        "eutrophication": result.get("eutrophication"),
        "climate_overlap": result.get("climate_overlap"),
        "protein_g": result.get("protein_g"),
        "n_per_100g_protein": result.get("n_per_100g_protein"),
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO nutrient_scenarios
                (user_id, name, payload, n_applied_kg, p_applied_kg,
                 reactive_n_lost_kg)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload,
                float(result["n_applied_kg"]),
                float(result["p_applied_kg"]),
                float(result["reactive_n_lost_kg"]),
            ),
        )
        return int(cursor.lastrowid)


def get_scenarios(user_id: str) -> list:
    """Saved scenarios for a user, newest first. Empty list if none."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, n_applied_kg, p_applied_kg,
                       reactive_n_lost_kg, created_at
                FROM nutrient_scenarios
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved nutrient scenarios")
        return []

    scenarios = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        scenarios.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "n_applied_kg": row[3],
            "p_applied_kg": row[4],
            "reactive_n_lost_kg": row[5],
            "created_at": row[6],
        })
    return scenarios


def delete_scenario(user_id: str, scenario_id: int) -> bool:
    """Delete one scenario. Returns whether a row was actually removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM nutrient_scenarios WHERE id = ? AND user_id = ?",
                (scenario_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete nutrient scenario %s", scenario_id)
        return False
