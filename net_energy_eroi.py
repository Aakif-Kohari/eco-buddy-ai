"""Energy that is generated, and energy that is actually available afterwards.

``carbon_payback.py`` answers how long an investment takes to repay its embodied
carbon. Nothing in this app answers the prior question: how long it takes to
repay its embodied *energy*, and how much surplus it delivers once it has.

Every energy module here reports gross output. Gross output is not the quantity
that matters. What matters is what is left after the energy sector has taken
its own cut, and the gap between the two is neither small nor constant.

The cliff is a non-linearity, which is why gross figures cannot show it
--------------------------------------------------------------------------
The share of gross energy that has to be reinvested to keep the supply running
is one over the return on investment. At a ratio of thirty that is three
percent; at ten, ten percent; at five, twenty; at two, half. The curve is flat
and then it is not, and a difference that looks like a rounding error at the top
end is decisive at the bottom. Advice framed in kilowatt-hours cannot show that
falling from ten to five costs far more than falling from thirty to twenty.

The boundary is the argument, and published figures rarely state it
--------------------------------------------------------------------
At the wellhead, at the point of use, and extended to include grid, storage and
the energy embodied in labour, the same technology gives answers differing by
more than a factor of two. A ratio quoted without its boundary is not a number,
it is a rhetorical device - and it is used as one from both directions. So the
boundary is a required argument here and there is no function that returns a
single unqualified figure.

Storage is an energy cost, not a free capability
-------------------------------------------------
``renewable_microgrid_vpp.py`` models batteries as something that makes
intermittent supply dispatchable. They do, and they consume energy to build and
lose energy every cycle. The buffered ratio of a solar-plus-storage system sits
materially below the panel's own, and reporting the panel's figure for the
system is the standard way the cost of dispatchability disappears.

Energy quality is a choice this module refuses to make silently
----------------------------------------------------------------
A joule of electricity and a joule of low-grade heat are not interchangeable,
and the two conventions for handling that - counting joules, or weighting them
by what they can do - reverse the ranking of electric against thermal options.
Both are computed, both are reported, and neither is presented as the answer.

Where this connects to code already merged
-------------------------------------------
*   ``carbon_payback.py`` does the carbon half. A panel built on a coal grid and
    deployed on a clean one has a short carbon payback and an unchanged energy
    payback, so the two numbers are not substitutes.
*   ``renewable_microgrid_vpp.py`` and ``grid_scheduler.py`` treat a kilowatt-
    hour as a kilowatt-hour. This is where they differ.
*   ``material_footprint.py`` shows falling ore grades increasing the material
    moved per kilogram. The same declining-grade dynamic drives falling returns
    across extractive energy, and the app had the input side without this one.
*   ``abatement_curve.py`` prices options in money per tonne; this prices them
    in energy per energy, which is a different scarcity.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

HOURS_PER_YEAR = 8760.0


class NetEnergyError(ValueError):
    """Raised when a net energy calculation was asked for nonsense."""


# ---------------------------------------------------------------------------
# Boundaries
#
# Required on every call. The spread between them for a single technology is
# larger than the spread between technologies at a fixed boundary, which is why
# a boundary-free figure is worse than no figure.
# ---------------------------------------------------------------------------
BOUNDARIES = {
    "standard": {
        "label": "Standard (at the wellhead or mine mouth)",
        "note": "Only the energy used to extract or generate. The most "
                "flattering boundary and the one most often quoted without "
                "qualification, because it excludes everything needed to turn "
                "the output into something usable.",
    },
    "point_of_use": {
        "label": "Point of use (delivered, refined, transmitted)",
        "note": "Adds refining, processing and transmission. Roughly halves "
                "the figure for liquid fuels and takes a smaller bite out of "
                "electricity. This is the boundary most decisions actually "
                "need.",
    },
    "extended": {
        "label": "Extended (grid, storage, and supporting infrastructure)",
        "note": "Adds the grid reinforcement, storage and supporting "
                "infrastructure a source requires to be useful at scale. The "
                "least flattering boundary, the most contested, and the only "
                "one at which intermittent and dispatchable sources are "
                "genuinely comparable.",
    },
}

DEFAULT_BOUNDARY = "point_of_use"


# ---------------------------------------------------------------------------
# Energy carriers and quality
#
# The exergy factor is what a joule of this carrier can actually do. The primary
# equivalent is how much primary energy a joule of it represents. They point in
# opposite directions for electricity, which is why the convention chosen
# changes the ranking rather than just the numbers.
# ---------------------------------------------------------------------------
CARRIERS = {
    "electricity": {
        "label": "Electricity",
        "exergy_factor": 1.00,
        "primary_equivalent": 2.60,
        "note": "Fully convertible to work. Counting joules treats it as "
                "equal to low-grade heat, which is why the thermal-equivalent "
                "convention understates it by roughly a factor of three.",
    },
    "liquid_fuel": {
        "label": "Liquid fuel",
        "exergy_factor": 0.95,
        "primary_equivalent": 1.10,
        "note": "Nearly all available as work in principle and much less than "
                "that in a heat engine. Its real advantage is energy density "
                "and storability, which no ratio here captures.",
    },
    "heat_high_grade": {
        "label": "High-grade heat",
        "exergy_factor": 0.55,
        "primary_equivalent": 1.05,
        "note": "Industrial process heat. Usable for a great deal and not for "
                "everything.",
    },
    "heat_low_grade": {
        "label": "Low-grade heat",
        "exergy_factor": 0.20,
        "primary_equivalent": 1.00,
        "note": "Space heating and hot water. A joule of it is worth a fifth "
                "of a joule of electricity in work terms, and the two are "
                "routinely added together as though they were the same thing.",
    },
}


# ---------------------------------------------------------------------------
# Sources
#
# Embodied energy is per kilowatt of capacity and covers manufacture,
# installation and decommissioning. Capacity factor is annual average. The
# carbon figure is carried only so the module can show where energy and carbon
# rankings disagree; it is not this module's contribution.
# ---------------------------------------------------------------------------
SOURCES = {
    "conventional_oil": {
        "label": "Conventional oil",
        "family": "fossil",
        "carrier": "liquid_fuel",
        "eroi": {"standard": 20.0, "point_of_use": 9.0, "extended": 6.5},
        "embodied_energy_kwh_per_kw": 1900.0,
        "capacity_factor": 0.85,
        "lifetime_years": 30.0,
        "intermittent": False,
        "co2_g_per_kwh": 270.0,
        "note": "The ratio has fallen by more than half over a century as the "
                "easy fields were produced out - the same declining-grade "
                "dynamic material_footprint.py finds in ore. Refining takes "
                "most of what is left between the wellhead and the tank.",
    },
    "oil_sands": {
        "label": "Oil sands",
        "family": "fossil",
        "carrier": "liquid_fuel",
        "eroi": {"standard": 4.0, "point_of_use": 2.6, "extended": 2.1},
        "embodied_energy_kwh_per_kw": 6800.0,
        "capacity_factor": 0.82,
        "lifetime_years": 30.0,
        "intermittent": False,
        "co2_g_per_kwh": 390.0,
        "note": "Below the range in which an industrial society can run on a "
                "single source. Included because it shows that a resource can "
                "be abundant, commercially viable and still close to the "
                "energetic floor.",
    },
    "coal": {
        "label": "Coal",
        "family": "fossil",
        "carrier": "electricity",
        "eroi": {"standard": 46.0, "point_of_use": 27.0, "extended": 22.0},
        "embodied_energy_kwh_per_kw": 2400.0,
        "capacity_factor": 0.55,
        "lifetime_years": 40.0,
        "intermittent": False,
        "co2_g_per_kwh": 980.0,
        "note": "One of the highest ratios in the table and the worst carbon "
                "figure in it. The clearest demonstration that energy return "
                "and climate impact are separate questions and that neither "
                "can substitute for the other.",
    },
    "natural_gas": {
        "label": "Natural gas",
        "family": "fossil",
        "carrier": "electricity",
        "eroi": {"standard": 30.0, "point_of_use": 15.0, "extended": 12.0},
        "embodied_energy_kwh_per_kw": 1100.0,
        "capacity_factor": 0.50,
        "lifetime_years": 30.0,
        "intermittent": False,
        "co2_g_per_kwh": 490.0,
        "note": "Cheap to build and expensive to run in energy terms, so the "
                "payback is fast and the lifetime ratio is middling.",
    },
    "nuclear_lwr": {
        "label": "Nuclear (light water reactor)",
        "family": "low_carbon_firm",
        "carrier": "electricity",
        "eroi": {"standard": 40.0, "point_of_use": 30.0, "extended": 24.0},
        "embodied_energy_kwh_per_kw": 4800.0,
        "capacity_factor": 0.90,
        "lifetime_years": 60.0,
        "intermittent": False,
        "co2_g_per_kwh": 12.0,
        "note": "The widest published range of anything here, driven almost "
                "entirely by the enrichment method assumed - centrifuge or "
                "diffusion changes the answer by a factor of three, and "
                "studies from different decades are not comparable.",
    },
    "hydro": {
        "label": "Hydroelectric",
        "family": "low_carbon_firm",
        "carrier": "electricity",
        "eroi": {"standard": 84.0, "point_of_use": 60.0, "extended": 48.0},
        "embodied_energy_kwh_per_kw": 3600.0,
        "capacity_factor": 0.42,
        "lifetime_years": 80.0,
        "intermittent": False,
        "co2_g_per_kwh": 24.0,
        "note": "The best ratio in the table by a wide margin, and the least "
                "expandable. Reservoir methane and displacement are real costs "
                "that an energy ratio does not see at all.",
    },
    "wind_onshore": {
        "label": "Wind, onshore",
        "family": "renewable_variable",
        "carrier": "electricity",
        "eroi": {"standard": 24.0, "point_of_use": 19.0, "extended": 13.0},
        "embodied_energy_kwh_per_kw": 1800.0,
        "capacity_factor": 0.35,
        "lifetime_years": 25.0,
        "intermittent": True,
        "co2_g_per_kwh": 11.0,
        "note": "The best unbuffered ratio among the variable sources and the "
                "one most affected by the extended boundary, because the grid "
                "and storage it needs are a large share of the total.",
    },
    "wind_offshore": {
        "label": "Wind, offshore",
        "family": "renewable_variable",
        "carrier": "electricity",
        "eroi": {"standard": 16.0, "point_of_use": 13.0, "extended": 9.0},
        "embodied_energy_kwh_per_kw": 2900.0,
        "capacity_factor": 0.48,
        "lifetime_years": 25.0,
        "intermittent": True,
        "co2_g_per_kwh": 13.0,
        "note": "More embodied energy per kilowatt and a much better capacity "
                "factor, so it pays back faster than the ratio alone suggests. "
                "Payback time and lifetime ratio are different questions.",
    },
    "solar_pv_utility": {
        "label": "Solar PV, utility scale, high insolation",
        "family": "renewable_variable",
        "carrier": "electricity",
        "eroi": {"standard": 14.0, "point_of_use": 11.0, "extended": 6.0},
        "embodied_energy_kwh_per_kw": 2300.0,
        "capacity_factor": 0.24,
        "lifetime_years": 30.0,
        "intermittent": True,
        "co2_g_per_kwh": 37.0,
        "note": "Manufacturing energy has fallen steadily and the sun has not "
                "moved, so almost all of the improvement in this figure over "
                "twenty years is on the invested side.",
    },
    "solar_pv_rooftop_temperate": {
        "label": "Solar PV, rooftop, temperate",
        "family": "renewable_variable",
        "carrier": "electricity",
        "eroi": {"standard": 7.0, "point_of_use": 5.5, "extended": 3.0},
        "embodied_energy_kwh_per_kw": 2600.0,
        "capacity_factor": 0.11,
        "lifetime_years": 30.0,
        "intermittent": True,
        "co2_g_per_kwh": 68.0,
        "note": "The same panel as the row above with less than half the sun "
                "on it. Where a household installation actually sits, and far "
                "enough down the curve that the reinvestment fraction starts "
                "to be visible.",
    },
    "geothermal": {
        "label": "Geothermal",
        "family": "low_carbon_firm",
        "carrier": "electricity",
        "eroi": {"standard": 13.0, "point_of_use": 10.0, "extended": 8.5},
        "embodied_energy_kwh_per_kw": 3100.0,
        "capacity_factor": 0.75,
        "lifetime_years": 30.0,
        "intermittent": False,
        "co2_g_per_kwh": 38.0,
        "note": "Firm and geographically constrained. Barely affected by the "
                "extended boundary because it needs almost no storage, which "
                "is the advantage that a same-boundary comparison hides.",
    },
    "corn_ethanol": {
        "label": "Corn ethanol",
        "family": "biofuel",
        "carrier": "liquid_fuel",
        "eroi": {"standard": 1.5, "point_of_use": 1.25, "extended": 1.1},
        "embodied_energy_kwh_per_kw": 9500.0,
        "capacity_factor": 0.70,
        "lifetime_years": 25.0,
        "intermittent": False,
        "co2_g_per_kwh": 210.0,
        "note": "Barely returns more energy than it consumes. Passable on "
                "carbon by some accounting and close to worthless as an energy "
                "source, which is the divergence this module exists to make "
                "visible.",
    },
    "biodiesel_rapeseed": {
        "label": "Biodiesel, rapeseed",
        "family": "biofuel",
        "carrier": "liquid_fuel",
        "eroi": {"standard": 2.8, "point_of_use": 2.2, "extended": 1.9},
        "embodied_energy_kwh_per_kw": 7200.0,
        "capacity_factor": 0.70,
        "lifetime_years": 25.0,
        "intermittent": False,
        "co2_g_per_kwh": 160.0,
        "note": "Better than corn ethanol and still inside the range where the "
                "energy sector would have to consume a third of its own output "
                "to keep going.",
    },
    "efficiency_insulation": {
        "label": "Insulation retrofit (energy saved)",
        "family": "efficiency",
        "carrier": "heat_low_grade",
        "eroi": {"standard": 42.0, "point_of_use": 38.0, "extended": 36.0},
        "embodied_energy_kwh_per_kw": 900.0,
        "capacity_factor": 0.30,
        "lifetime_years": 40.0,
        "intermittent": False,
        "co2_g_per_kwh": 0.0,
        "note": "A negawatt has a return on investment like any other source "
                "and beats almost all of them, which is the case for treating "
                "efficiency as supply. It is also low-grade heat, so the "
                "quality convention chosen changes how it ranks.",
    },
    "heat_pump_displacement": {
        "label": "Heat pump (delivered heat per unit electricity)",
        "family": "efficiency",
        "carrier": "heat_low_grade",
        "eroi": {"standard": 22.0, "point_of_use": 18.0, "extended": 15.0},
        "embodied_energy_kwh_per_kw": 1300.0,
        "capacity_factor": 0.25,
        "lifetime_years": 20.0,
        "intermittent": False,
        "co2_g_per_kwh": 0.0,
        "note": "Included specifically because the quality convention decides "
                "the answer: it turns one joule of electricity into three of "
                "low-grade heat, which looks like a gain counting joules and a "
                "loss weighting them by what they can do.",
    },
}


# ---------------------------------------------------------------------------
# Storage
#
# Embodied energy per kilowatt-hour of capacity, and what a cycle costs.
# ---------------------------------------------------------------------------
STORAGE = {
    "lithium_ion": {
        "label": "Lithium-ion battery",
        "embodied_energy_kwh_per_kwh": 400.0,
        "round_trip_efficiency": 0.88,
        "cycle_life": 4000,
        "note": "High round-trip efficiency and substantial embodied energy. "
                "The cycle life matters as much as either, because a pack "
                "replaced twice over a panel's life is charged three times.",
    },
    "pumped_hydro": {
        "label": "Pumped hydro",
        "embodied_energy_kwh_per_kwh": 55.0,
        "round_trip_efficiency": 0.78,
        "cycle_life": 40000,
        "note": "An order of magnitude less embodied energy per kilowatt-hour "
                "and a lower round-trip efficiency. Geographically limited, "
                "which is why it does not simply win.",
    },
    "hydrogen": {
        "label": "Hydrogen (electrolysis and fuel cell)",
        "embodied_energy_kwh_per_kwh": 130.0,
        "round_trip_efficiency": 0.38,
        "cycle_life": 12000,
        "note": "The round-trip efficiency is the whole story. Storing energy "
                "this way and returning it to the grid costs nearly two thirds "
                "of it, which no amount of cheap electrolysis changes.",
    },
    "none": {
        "label": "No storage",
        "embodied_energy_kwh_per_kwh": 0.0,
        "round_trip_efficiency": 1.0,
        "cycle_life": 1,
        "note": "The unbuffered case, reported alongside every buffered one so "
                "the cost of dispatchability is explicit rather than absorbed.",
    },
}


# Below this ratio a supply cannot sustain an industrial society with a
# meaningful non-energy sector. Contested, and stated as contested wherever it
# is used, because the exact threshold is an argument and the shape of the
# curve underneath it is not.
SOCIETAL_MINIMUM_EROI = 7.0


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def list_sources(family=None):
    """Source keys, optionally filtered to one family."""
    if family is None:
        return sorted(SOURCES)
    return sorted(k for k, v in SOURCES.items() if v["family"] == family)


def list_families():
    """The distinct source families present in the table."""
    return sorted({spec["family"] for spec in SOURCES.values()})


def get_source(key):
    """One source specification."""
    try:
        return SOURCES[key]
    except KeyError:
        raise NetEnergyError(
            f"Unknown source '{key}'. Known sources: "
            f"{', '.join(list_sources())}."
        )


def list_boundaries():
    """Boundaries, most flattering first."""
    return ["standard", "point_of_use", "extended"]


def get_boundary(key):
    """One boundary specification."""
    if key is None:
        raise NetEnergyError(
            "A system boundary is required. The same technology differs by "
            "more than a factor of two between the wellhead and the extended "
            "boundary, so a figure without one is not a number."
        )
    try:
        return BOUNDARIES[key]
    except KeyError:
        raise NetEnergyError(
            f"Unknown boundary '{key}'. Known boundaries: "
            f"{', '.join(list_boundaries())}."
        )


def list_storage():
    """Storage technology keys."""
    return sorted(STORAGE)


def get_storage(key):
    """One storage specification."""
    try:
        return STORAGE[key]
    except KeyError:
        raise NetEnergyError(
            f"Unknown storage '{key}'. Known options: "
            f"{', '.join(list_storage())}."
        )


def list_carriers():
    """Energy carrier keys."""
    return sorted(CARRIERS)


def get_carrier(key):
    """One carrier specification."""
    try:
        return CARRIERS[key]
    except KeyError:
        raise NetEnergyError(f"Unknown carrier '{key}'.")


# ---------------------------------------------------------------------------
# The ratio, always with its boundary
# ---------------------------------------------------------------------------
def eroi(source, boundary):
    """Energy returned over energy invested, at a stated boundary."""
    spec = get_source(source)
    get_boundary(boundary)
    return spec["eroi"][boundary]


def eroi_across_boundaries(source):
    """The same source at every boundary, so the spread is visible.

    The spread here is usually larger than the spread between technologies at
    a fixed boundary, which is the case for making the boundary required.
    """
    spec = get_source(source)
    rows = [
        {
            "boundary": boundary,
            "label": BOUNDARIES[boundary]["label"],
            "eroi": spec["eroi"][boundary],
        }
        for boundary in list_boundaries()
    ]
    values = [row["eroi"] for row in rows]
    return {
        "source": source,
        "label": spec["label"],
        "rows": rows,
        "spread_ratio": max(values) / min(values),
        "note": (
            f"{spec['label']} returns {max(values):.1f} times its energy "
            f"investment at the most flattering boundary and {min(values):.1f} "
            f"at the least - a factor of {max(values) / min(values):.1f} from "
            f"nothing but where the accounting stops."
        ),
    }


# ---------------------------------------------------------------------------
# The cliff
# ---------------------------------------------------------------------------
def reinvestment_fraction(ratio):
    """Share of gross output the energy sector must keep to sustain itself."""
    if ratio <= 0:
        raise NetEnergyError("A return on investment must be positive.")
    return 1.0 / ratio


def net_energy_cliff(ratios=None):
    """The reinvestment curve, which is the point of the whole module.

    Flat, and then it is not. A fall from thirty to twenty costs three
    percentage points of society's energy; a fall from five to three costs
    thirteen. Gross figures cannot express that.
    """
    ratios = ratios or [1.5, 2, 3, 5, 7, 10, 15, 20, 30, 50, 80]
    rows = []
    for ratio in ratios:
        reinvested = reinvestment_fraction(ratio)
        rows.append({
            "eroi": ratio,
            "reinvestment_fraction": reinvested,
            "surplus_fraction": 1.0 - reinvested,
            "below_societal_minimum": ratio < SOCIETAL_MINIMUM_EROI,
        })
    return {
        "rows": rows,
        "societal_minimum": SOCIETAL_MINIMUM_EROI,
        "minimum_caveat": (
            "The exact threshold below which an industrial society cannot "
            "sustain a meaningful non-energy sector is contested and is "
            "stated here as one figure for orientation only. The shape of the "
            "curve is not contested, and the shape is the finding."
        ),
    }


def societal_position(source, boundary):
    """Where one source sits against the cliff."""
    ratio = eroi(source, boundary)
    reinvested = reinvestment_fraction(ratio)
    return {
        "source": source,
        "label": get_source(source)["label"],
        "boundary": boundary,
        "boundary_label": get_boundary(boundary)["label"],
        "eroi": ratio,
        "reinvestment_fraction": reinvested,
        "surplus_fraction": 1.0 - reinvested,
        "below_societal_minimum": ratio < SOCIETAL_MINIMUM_EROI,
        "note": (
            f"At a ratio of {ratio:.1f}, {reinvested:.1%} of gross output has "
            f"to go back into producing energy, leaving {1 - reinvested:.1%} "
            f"for everything else."
        ),
    }


# ---------------------------------------------------------------------------
# Payback, which is a different question from the ratio
# ---------------------------------------------------------------------------
def energy_payback(source, capacity_factor=None):
    """Years to repay embodied energy, and how that differs from the ratio.

    A source can pay back quickly and still have a mediocre lifetime ratio, or
    the reverse. Offshore wind and rooftop solar are the pair that shows it.
    """
    spec = get_source(source)
    factor = (
        capacity_factor if capacity_factor is not None
        else spec["capacity_factor"]
    )
    if not 0 < factor <= 1:
        raise NetEnergyError("Capacity factor must be between 0 and 1.")

    annual_kwh_per_kw = HOURS_PER_YEAR * factor
    if annual_kwh_per_kw <= 0:
        raise NetEnergyError("A source with no output cannot pay back.")

    payback_years = spec["embodied_energy_kwh_per_kw"] / annual_kwh_per_kw
    lifetime_kwh = annual_kwh_per_kw * spec["lifetime_years"]

    return {
        "source": source,
        "label": spec["label"],
        "capacity_factor": factor,
        "embodied_energy_kwh_per_kw": spec["embodied_energy_kwh_per_kw"],
        "annual_output_kwh_per_kw": annual_kwh_per_kw,
        "payback_years": payback_years,
        "lifetime_years": spec["lifetime_years"],
        "lifetime_output_kwh_per_kw": lifetime_kwh,
        "lifetime_ratio": lifetime_kwh / spec["embodied_energy_kwh_per_kw"],
        "payback_share_of_life": payback_years / spec["lifetime_years"],
        "carbon_payback_note": (
            "This is energy payback, not carbon payback. A panel manufactured "
            "on a coal-heavy grid and deployed on a clean one has a short "
            "carbon payback and an unchanged energy payback - carbon_payback.py "
            "reports the first and cannot report the second."
        ),
    }


def payback_sensitivity(source, capacity_factors=None):
    """Payback across a range of yields, since location drives it entirely."""
    spec = get_source(source)
    base = spec["capacity_factor"]
    factors = capacity_factors or [
        round(base * m, 4) for m in (0.5, 0.75, 1.0, 1.25, 1.5)
    ]
    return [
        {
            "capacity_factor": factor,
            "payback_years": energy_payback(source, factor)["payback_years"],
            "is_reference": abs(factor - base) < 1e-9,
        }
        for factor in factors if 0 < factor <= 1
    ]


# ---------------------------------------------------------------------------
# Buffering: what dispatchability costs in energy
# ---------------------------------------------------------------------------
def buffered_eroi(source, boundary, storage="lithium_ion",
                  storage_hours=4.0, buffered_share=0.35,
                  curtailment=0.05):
    """Return on investment once storage is included, against the unbuffered one.

    ``buffered_share`` is the fraction of output that has to be cycled through
    storage rather than used directly. ``curtailment`` is the fraction spilled
    because it arrived when nothing wanted it. Both are losses that a
    generation-only figure never sees.

    A dispatchable source returns unchanged, and says so, rather than being
    quietly penalised for a cost it does not incur.
    """
    spec = get_source(source)
    store = get_storage(storage)
    unbuffered = eroi(source, boundary)

    if not 0 <= buffered_share <= 1:
        raise NetEnergyError("Buffered share must be between 0 and 1.")
    if not 0 <= curtailment < 1:
        raise NetEnergyError("Curtailment must be between 0 and 1.")
    if storage_hours < 0:
        raise NetEnergyError("Storage hours cannot be negative.")

    if not spec["intermittent"] or storage == "none":
        return {
            "source": source,
            "label": spec["label"],
            "boundary": boundary,
            "storage": storage,
            "unbuffered_eroi": unbuffered,
            "buffered_eroi": unbuffered,
            "penalty_fraction": 0.0,
            "crosses_societal_minimum": False,
            "intermittent": spec["intermittent"],
            "note": (
                "Dispatchable, so there is no buffering cost to add."
                if not spec["intermittent"] else
                "No storage specified, so this is the unbuffered figure. It is "
                "not a system figure and should not be quoted as one."
            ),
        }

    annual_kwh_per_kw = HOURS_PER_YEAR * spec["capacity_factor"]
    lifetime_kwh = annual_kwh_per_kw * spec["lifetime_years"]
    generation_invested = lifetime_kwh / unbuffered

    # Storage sized in hours of rated capacity, replaced when cycles run out.
    storage_kwh_per_kw = storage_hours
    cycles_over_life = (
        annual_kwh_per_kw * buffered_share * spec["lifetime_years"]
        / storage_kwh_per_kw
    ) if storage_kwh_per_kw > 0 else 0.0
    replacements = max(1.0, cycles_over_life / store["cycle_life"])
    storage_invested = (
        storage_kwh_per_kw * store["embodied_energy_kwh_per_kwh"] * replacements
    )

    # Delivered energy loses what was curtailed and what the round trip ate.
    round_trip_loss = buffered_share * (1.0 - store["round_trip_efficiency"])
    delivered = lifetime_kwh * (1.0 - curtailment) * (1.0 - round_trip_loss)

    total_invested = generation_invested + storage_invested
    buffered = delivered / total_invested if total_invested else 0.0

    return {
        "source": source,
        "label": spec["label"],
        "boundary": boundary,
        "storage": storage,
        "storage_label": store["label"],
        "storage_hours": storage_hours,
        "buffered_share": buffered_share,
        "curtailment": curtailment,
        "round_trip_efficiency": store["round_trip_efficiency"],
        "lifetime_output_kwh_per_kw": lifetime_kwh,
        "delivered_kwh_per_kw": delivered,
        "generation_invested_kwh_per_kw": generation_invested,
        "storage_invested_kwh_per_kw": storage_invested,
        "storage_replacements": replacements,
        "unbuffered_eroi": unbuffered,
        "buffered_eroi": buffered,
        "penalty_fraction": (
            (unbuffered - buffered) / unbuffered if unbuffered else 0.0
        ),
        "crosses_societal_minimum": (
            unbuffered >= SOCIETAL_MINIMUM_EROI
            and buffered < SOCIETAL_MINIMUM_EROI
        ),
        "intermittent": True,
        "note": (
            f"Storage costs {(unbuffered - buffered) / unbuffered:.0%} of this "
            f"source's return - partly the energy embodied in the pack, partly "
            f"the {1 - store['round_trip_efficiency']:.0%} lost every round "
            f"trip. Reporting the unbuffered figure for a system that needs "
            f"storage is how that cost disappears."
        ),
    }


# ---------------------------------------------------------------------------
# Energy quality, offered as two conventions rather than one answer
# ---------------------------------------------------------------------------
def quality_weighted(source, boundary, convention="thermal_equivalent"):
    """The ratio under a stated energy quality convention.

    ``thermal_equivalent`` counts every joule the same. ``exergy`` weights each
    by how much work it can do. ``primary_equivalent`` counts what it took to
    make. These reverse the ranking of electric against thermal options, so the
    convention is a required argument and both are always reported alongside.
    """
    valid = ("thermal_equivalent", "exergy", "primary_equivalent")
    if convention not in valid:
        raise NetEnergyError(f"Convention must be one of {valid}.")

    spec = get_source(source)
    carrier = get_carrier(spec["carrier"])
    base = eroi(source, boundary)

    if convention == "thermal_equivalent":
        weight = 1.0
    elif convention == "exergy":
        weight = carrier["exergy_factor"]
    else:
        weight = carrier["primary_equivalent"]

    return {
        "source": source,
        "label": spec["label"],
        "carrier": spec["carrier"],
        "carrier_label": carrier["label"],
        "boundary": boundary,
        "convention": convention,
        "weight": weight,
        "unweighted_eroi": base,
        "weighted_eroi": base * weight,
    }


def quality_comparison(sources, boundary):
    """Several sources under all three conventions, with reversals flagged.

    The output worth reading is not any single ranking but whether they agree.
    """
    if len(sources) < 2:
        raise NetEnergyError("A quality comparison needs at least two sources.")

    conventions = ("thermal_equivalent", "exergy", "primary_equivalent")
    rankings = {}
    rows = []

    for source in sources:
        entry = {"source": source, "label": get_source(source)["label"]}
        for convention in conventions:
            entry[convention] = quality_weighted(
                source, boundary, convention
            )["weighted_eroi"]
        rows.append(entry)

    for convention in conventions:
        rankings[convention] = [
            r["source"]
            for r in sorted(rows, key=lambda r: -r[convention])
        ]

    disagree = len({tuple(v) for v in rankings.values()}) > 1

    return {
        "boundary": boundary,
        "rows": rows,
        "rankings": rankings,
        "conventions_disagree": disagree,
        "note": (
            "The three conventions rank these sources differently. There is no "
            "fact of the matter that resolves that: counting joules and "
            "weighting them by what they can do are both defensible and they "
            "are answering different questions."
            if disagree else
            "All three conventions agree on the ordering here, so the quality "
            "question does not affect this particular choice."
        ),
    }


# ---------------------------------------------------------------------------
# A household
# ---------------------------------------------------------------------------
def household_position(installations, boundary, storage="none",
                       storage_hours=0.0):
    """A household's net energy position across its own installations.

    ``installations`` maps source keys to installed kilowatts. Efficiency
    measures count as supply, because a negawatt has a return on investment
    like anything else and usually a better one.
    """
    if not installations:
        raise NetEnergyError("A household position needs at least one measure.")

    rows = []
    gross = 0.0
    invested = 0.0

    for source, kw in installations.items():
        if kw <= 0:
            raise NetEnergyError(f"Installed capacity for {source} must be positive.")
        spec = get_source(source)
        annual = HOURS_PER_YEAR * spec["capacity_factor"] * kw

        if storage != "none" and spec["intermittent"]:
            ratio = buffered_eroi(
                source, boundary, storage,
                storage_hours=storage_hours or 4.0,
            )["buffered_eroi"]
        else:
            ratio = eroi(source, boundary)

        source_invested = annual / ratio
        rows.append({
            "source": source,
            "label": spec["label"],
            "family": spec["family"],
            "kw": kw,
            "annual_kwh": annual,
            "eroi": ratio,
            "annual_invested_kwh": source_invested,
            "annual_net_kwh": annual - source_invested,
        })
        gross += annual
        invested += source_invested

    combined = gross / invested if invested else 0.0

    return {
        "boundary": boundary,
        "storage": storage,
        "installations": sorted(rows, key=lambda r: -r["annual_net_kwh"]),
        "gross_annual_kwh": gross,
        "invested_annual_kwh": invested,
        "net_annual_kwh": gross - invested,
        "combined_eroi": combined,
        "reinvestment_fraction": (
            reinvestment_fraction(combined) if combined > 0 else 1.0
        ),
        "below_societal_minimum": combined < SOCIETAL_MINIMUM_EROI,
        "note": (
            f"Across these measures the household's supply returns "
            f"{combined:.1f} times what it takes to provide, so "
            f"{reinvestment_fraction(combined):.0%} of the gross is consumed "
            f"getting the rest."
            if combined > 0 else "No net energy position could be computed."
        ),
    }


# ---------------------------------------------------------------------------
# Where energy and carbon disagree
# ---------------------------------------------------------------------------
def energy_versus_carbon(sources=None, boundary=DEFAULT_BOUNDARY):
    """Rank on energy return and on carbon, and report the disagreements.

    Coal is near the top on energy and at the bottom on carbon. Corn ethanol is
    passable on carbon by some accounting and close to worthless on energy.
    Neither ranking substitutes for the other, and no combined score is offered.
    """
    sources = sources or list_sources()
    rows = []
    for source in sources:
        spec = get_source(source)
        rows.append({
            "source": source,
            "label": spec["label"],
            "family": spec["family"],
            "eroi": eroi(source, boundary),
            "co2_g_per_kwh": spec["co2_g_per_kwh"],
        })

    by_energy = [r["source"] for r in sorted(rows, key=lambda r: -r["eroi"])]
    by_carbon = [
        r["source"] for r in sorted(rows, key=lambda r: r["co2_g_per_kwh"])
    ]

    conflicts = []
    for row in rows:
        energy_rank = by_energy.index(row["source"])
        carbon_rank = by_carbon.index(row["source"])
        if abs(energy_rank - carbon_rank) >= max(3, len(rows) // 3):
            conflicts.append({
                "source": row["source"],
                "label": row["label"],
                "energy_rank": energy_rank + 1,
                "carbon_rank": carbon_rank + 1,
                "eroi": row["eroi"],
                "co2_g_per_kwh": row["co2_g_per_kwh"],
            })

    return {
        "boundary": boundary,
        "rows": rows,
        "ranking_by_energy": by_energy,
        "ranking_by_carbon": by_carbon,
        "conflicts": sorted(
            conflicts, key=lambda c: -abs(c["energy_rank"] - c["carbon_rank"])
        ),
        "no_composite_note": (
            "No combined score is produced. A ratio of energies and a mass of "
            "CO2 per kilowatt-hour are different scarcities, and weighting one "
            "against the other is a political question rather than an "
            "accounting one."
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_net_energy_insights(source, boundary):
    """Plain sentences about one source at one boundary."""
    insights = []
    spec = get_source(source)
    position = societal_position(source, boundary)
    spread = eroi_across_boundaries(source)
    payback = energy_payback(source)

    insights.append(position["note"])
    insights.append(spread["note"])

    insights.append(
        f"It repays the energy used to build it in "
        f"{payback['payback_years']:.2f} years, which is "
        f"{payback['payback_share_of_life']:.1%} of its "
        f"{payback['lifetime_years']:.0f}-year life. Payback and lifetime "
        f"ratio are different questions and a source can be good at one and "
        f"middling at the other."
    )

    if position["below_societal_minimum"]:
        insights.append(
            f"At this boundary the ratio is below the level usually taken as "
            f"the minimum for sustaining an industrial society with a "
            f"meaningful non-energy sector. That threshold is contested; the "
            f"shape of the curve beneath it is not."
        )

    if spec["intermittent"]:
        buffered = buffered_eroi(source, boundary)
        insights.append(
            f"Buffered with storage the ratio falls from "
            f"{buffered['unbuffered_eroi']:.1f} to "
            f"{buffered['buffered_eroi']:.1f}. That gap is the energy cost of "
            f"dispatchability, and the modules that model storage as a "
            f"capability do not currently carry it."
        )
        if buffered["crosses_societal_minimum"]:
            insights.append(
                "Buffering takes this source from above the societal minimum "
                "to below it. Whether it clears that bar depends entirely on "
                "whether the storage is counted."
            )

    carrier = get_carrier(spec["carrier"])
    if carrier["exergy_factor"] < 0.6:
        insights.append(
            f"This delivers {carrier['label'].lower()}, worth "
            f"{carrier['exergy_factor']:.2f} of a joule of electricity in work "
            f"terms. Counting joules and weighting them by what they can do "
            f"give different answers here, and this module reports both rather "
            f"than choosing."
        )

    insights.append(
        f"This says nothing about carbon. {spec['label']} emits "
        f"{spec['co2_g_per_kwh']:.0f} g CO2 per kWh, and energy return and "
        f"climate impact are separate questions - coal ranks near the top on "
        f"one and the bottom on the other."
    )

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS net_energy_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            boundary TEXT NOT NULL,
            combined_eroi REAL NOT NULL,
            net_annual_kwh REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_net_energy_positions_user
        ON net_energy_positions (user_id)
        """
    )


def save_position(user_id, name, position):
    """Persist a household net energy position and return its row id."""
    if not user_id:
        raise NetEnergyError("A position needs a user to belong to.")
    if not name or not name.strip():
        raise NetEnergyError("A position needs a name.")

    payload = json.dumps({
        "boundary": position["boundary"],
        "storage": position["storage"],
        "gross_annual_kwh": position["gross_annual_kwh"],
        "invested_annual_kwh": position["invested_annual_kwh"],
        "reinvestment_fraction": position["reinvestment_fraction"],
        "installations": [
            {
                "source": row["source"],
                "kw": row["kw"],
                "eroi": row["eroi"],
                "annual_net_kwh": row["annual_net_kwh"],
            }
            for row in position["installations"]
        ],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO net_energy_positions
                (user_id, name, payload, boundary, combined_eroi,
                 net_annual_kwh)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload, position["boundary"],
                float(position["combined_eroi"]),
                float(position["net_annual_kwh"]),
            ),
        )
        return int(cursor.lastrowid)


def get_positions(user_id):
    """Saved positions for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, boundary, combined_eroi,
                       net_annual_kwh, created_at
                FROM net_energy_positions
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved net energy positions")
        return []

    positions = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        positions.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "boundary": row[3],
            "combined_eroi": row[4],
            "net_annual_kwh": row[5],
            "created_at": row[6],
        })
    return positions


def delete_position(user_id, position_id):
    """Delete one saved position. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM net_energy_positions WHERE id = ? AND user_id = ?",
                (position_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete net energy position %s", position_id)
        return False
