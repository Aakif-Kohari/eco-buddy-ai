"""The particles emitted alongside the CO2, which change the answer and are missing.

``src.environment.climate_metrics.py`` does the hard part of multi-gas accounting properly. It
separates CO2 from methane from N2O and applies GWP* so a flow gas is not
mistaken for a stock gas. It covers every well-mixed greenhouse gas this app
emits.

It covers none of the aerosols emitted at the same time out of the same chimney.
Black carbon, organic carbon, sulphur dioxide and the ozone precursors carry a
near-term forcing that is large, that has both signs, and that changes the
ranking of options this app already recommends between.

Both signs, which is why this cannot be a second table of positive numbers
--------------------------------------------------------------------------
Black carbon absorbs and warms. Sulphate and organic carbon scatter and cool.
An activity's net near-term forcing therefore depends on the mix, not on the
fuel's name. This has a consequence people find uncomfortable and which the
module states rather than hides: removing sulphur from marine fuel or from a
coal stack unmasks warming that was previously being suppressed. That is a real
measured effect. It is not an argument for keeping the sulphur - the particles
in question kill people - but a module that reported only the warming species
would be producing propaganda rather than an inventory.

The horizon does not scale the answer, it reorders it
------------------------------------------------------
These species live for days to weeks. On a twenty-year view black carbon
dominates a traditional cookstove's forcing; on a hundred-year view it is a
rounding error beside the CO2. Any module reporting one horizon has silently
taken a side in a live policy argument, so both are reported for every result
and the module says so in words wherever the ranking of two options flips
between them.

The label on the fuel is not the emission factor
-------------------------------------------------
A diesel car with a particulate filter and one without differ by more than an
order of magnitude in black carbon and barely at all in CO2. ``src.lifestyle.transport_planner.py``
and ``src.carbon.vehicle_emissions_data.py`` cannot presently tell them apart on climate
grounds. Emission control technology, not fuel type, is the variable that
matters most here, so it is the axis the source table is organised on.

Deposition on snow is not a refinement
---------------------------------------
Black carbon that lands on snow or ice darkens it and keeps absorbing long after
it has left the air. Its forcing efficacy in those regions is several times the
globally-averaged value, which is why Arctic-adjacent emissions are treated
separately in the literature. Applying one global factor everywhere erases the
case that matters most, so the deposition term is a separate, visible line
rather than something folded into the base factor.

Uncertainty is reported because it is the largest in the field
---------------------------------------------------------------
Aerosol forcing, and the indirect effect on clouds in particular, is the single
biggest uncertainty in the whole forcing budget. Black carbon's hundred-year
GWP has a published range spanning roughly a factor of seventeen. Presenting a
central estimate without that range would be the main way this metric gets
misused, so every result carries low and high bounds and the module will not
produce a point estimate on its own.

An overlay, not a replacement
------------------------------
Nothing here redefines an existing total. Results are additive to what
``src.environment.climate_metrics.py`` reports and are labelled as short-lived throughout, so a
reader always knows which part of a figure will still be there in fifty years.

Where this connects to code already merged
-------------------------------------------
*   ``src.environment.climate_metrics.py`` holds the long-lived half. This is the short-lived
    half, and the two are designed to be read together.
*   ``src.utils.health_cobenefits.py`` already tracks PM2.5 for mortality. The same
    particles have a climate effect the app currently drops, and the unmasking
    trade-off is reported against that health benefit rather than in isolation.
*   ``src.carbon.emission_factors.py``, ``src.carbon.vehicle_emissions_data.py`` and
    ``src.lifestyle.transport_planner.py`` supply the activities; none of them is modified.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class AerosolError(ValueError):
    """Raised when a short-lived forcer calculation was asked for nonsense."""


# ---------------------------------------------------------------------------
# Horizons
#
# Both, always. The twenty-year and hundred-year answers frequently disagree
# about which of two options is better, and that disagreement is the finding.
# ---------------------------------------------------------------------------
HORIZONS = (20, 100)


# ---------------------------------------------------------------------------
# Species
#
# GWP with low and high bounds. The bounds are wide because the underlying
# science is, and a module that reported only the central column would be
# claiming a precision that does not exist.
#
# Sign convention: positive warms, negative cools. Two of the five species
# here are negative, which is the entire reason this module cannot be a list
# of penalties.
# ---------------------------------------------------------------------------
SPECIES = {
    "bc": {
        "label": "Black carbon",
        "formula": "BC",
        "warms": True,
        "gwp": {
            20: {"low": 270.0, "central": 3200.0, "high": 6200.0},
            100: {"low": 100.0, "central": 900.0, "high": 1700.0},
        },
        "lifetime_days": 7.0,
        "deposition_sensitive": True,
        "note": "Absorbs sunlight directly, darkens snow where it lands, and "
                "is probably the second or third largest warming agent after "
                "CO2. Its hundred-year GWP spans a factor of seventeen, which "
                "is why no figure here is offered without a range.",
    },
    "oc": {
        "label": "Organic carbon",
        "formula": "OC",
        "warms": False,
        "gwp": {
            20: {"low": -410.0, "central": -240.0, "high": -75.0},
            100: {"low": -120.0, "central": -69.0, "high": -20.0},
        },
        "lifetime_days": 7.0,
        "deposition_sensitive": False,
        "note": "Scatters light and cools. Emitted from the same incomplete "
                "combustion as black carbon and in a ratio that decides "
                "whether a given fire warms or cools on balance.",
    },
    "so2": {
        "label": "Sulphur dioxide",
        "formula": "SO2",
        "warms": False,
        "gwp": {
            20: {"low": -230.0, "central": -140.0, "high": -50.0},
            100: {"low": -65.0, "central": -38.0, "high": -14.0},
        },
        "lifetime_days": 4.0,
        "deposition_sensitive": False,
        "note": "Forms sulphate, which scatters directly and brightens clouds "
                "indirectly. The cooling that industrial air pollution has "
                "been providing, and that cleaning the air gives back.",
    },
    "nox": {
        "label": "Nitrogen oxides",
        "formula": "NOx",
        "warms": False,
        "gwp": {
            20: {"low": -110.0, "central": -16.0, "high": 40.0},
            100: {"low": -30.0, "central": -11.0, "high": 12.0},
        },
        "lifetime_days": 1.5,
        "deposition_sensitive": False,
        "note": "Three effects with different signs: ozone production warms, "
                "nitrate aerosol cools, and shortening methane's lifetime "
                "cools. The net is small, regionally variable, and the only "
                "species here whose published range crosses zero.",
    },
    "co": {
        "label": "Carbon monoxide",
        "formula": "CO",
        "warms": True,
        "gwp": {
            20: {"low": 3.0, "central": 5.9, "high": 9.0},
            100: {"low": 1.0, "central": 1.8, "high": 2.9},
        },
        "lifetime_days": 60.0,
        "deposition_sensitive": False,
        "note": "Warms indirectly, by consuming the hydroxyl radicals that "
                "would otherwise destroy methane. Small per kilogram and "
                "emitted in large quantities by incomplete combustion.",
    },
}

SPECIES_ORDER = ("bc", "oc", "so2", "nox", "co")


# ---------------------------------------------------------------------------
# Deposition efficacy
#
# Black carbon on snow keeps absorbing after it has left the air. One global
# factor would erase the region where this matters most, so it is a separate
# multiplier applied only to the depositing species.
# ---------------------------------------------------------------------------
DEPOSITION_REGIONS = {
    "arctic": {
        "label": "Arctic / high latitude",
        "bc_efficacy": 3.2,
        "note": "Emissions close to persistent snow and ice. The deposition "
                "term is larger than the atmospheric one here, which is why "
                "flaring and shipping north of the treeline are treated as a "
                "separate policy problem.",
    },
    "high_altitude": {
        "label": "High altitude / glaciated",
        "bc_efficacy": 2.4,
        "note": "Himalayan and Andean valleys, where cookstove and brick kiln "
                "smoke reaches glaciers that feed rivers.",
    },
    "mid_latitude_seasonal_snow": {
        "label": "Mid-latitude with seasonal snow",
        "bc_efficacy": 1.5,
        "note": "Deposition matters for part of the year only, so the "
                "multiplier is modest and the season it applies in is short.",
    },
    "temperate": {
        "label": "Temperate, no persistent snow",
        "bc_efficacy": 1.0,
        "note": "The globally-averaged case. This is what a published GWP "
                "figure assumes when it does not say otherwise.",
    },
    "tropical": {
        "label": "Tropical",
        "bc_efficacy": 1.0,
        "note": "No cryosphere to deposit on. The atmospheric effect is the "
                "whole effect.",
    },
}

DEFAULT_REGION = "temperate"


# ---------------------------------------------------------------------------
# Sources
#
# Organised by emission control technology rather than by fuel, because that is
# the axis on which the numbers actually vary. Co-emissions are grams per unit;
# CO2 is kilograms per unit.
# ---------------------------------------------------------------------------
SOURCES = {
    "wood_stove_traditional": {
        "label": "Wood stove, traditional / open",
        "sector": "residential",
        "unit": "kg fuel",
        "co2_kg_per_unit": 1.75,
        "emissions_g_per_unit": {
            "bc": 0.95, "oc": 4.20, "so2": 0.20, "nox": 1.30, "co": 65.0,
        },
        "note": "Incomplete combustion at low temperature. The black carbon "
                "here is the reason a cookstove looks very different on a "
                "twenty-year view than a hundred-year one.",
    },
    "wood_stove_certified": {
        "label": "Wood stove, certified / secondary burn",
        "sector": "residential",
        "unit": "kg fuel",
        "co2_kg_per_unit": 1.75,
        "emissions_g_per_unit": {
            "bc": 0.18, "oc": 0.75, "so2": 0.20, "nox": 1.45, "co": 18.0,
        },
        "note": "Identical CO2 to the traditional stove, because the wood is "
                "the same. Roughly a fifth of the black carbon, because the "
                "combustion is not. The whole gap is invisible to a CO2-only "
                "inventory.",
    },
    "coal_residential": {
        "label": "Coal, residential stove",
        "sector": "residential",
        "unit": "kg fuel",
        "co2_kg_per_unit": 2.42,
        "emissions_g_per_unit": {
            "bc": 1.20, "oc": 2.60, "so2": 9.50, "nox": 1.80, "co": 42.0,
        },
        "note": "High in both directions: substantial black carbon and a great "
                "deal of sulphur. The net sign depends on the horizon and on "
                "the sulphur content of the particular coal.",
    },
    "lpg_cooking": {
        "label": "LPG cooking",
        "sector": "residential",
        "unit": "kg fuel",
        "co2_kg_per_unit": 3.00,
        "emissions_g_per_unit": {
            "bc": 0.003, "oc": 0.010, "so2": 0.02, "nox": 1.60, "co": 1.40,
        },
        "note": "More CO2 per kilogram than wood and almost no particulate. "
                "The clearest case in the table of an option that looks worse "
                "on carbon alone and better once the co-emissions are counted.",
    },
    "kerosene_lamp": {
        "label": "Kerosene wick lamp",
        "sector": "residential",
        "unit": "kg fuel",
        "co2_kg_per_unit": 2.55,
        "emissions_g_per_unit": {
            "bc": 65.0, "oc": 5.00, "so2": 0.30, "nox": 0.60, "co": 12.0,
        },
        "note": "Converts an extraordinary fraction of its fuel to black "
                "carbon - the highest ratio of any source here. A tiny CO2 "
                "footprint and a climate effect out of all proportion to it.",
    },
    "diesel_no_dpf": {
        "label": "Diesel vehicle, no particulate filter",
        "sector": "transport",
        "unit": "kg fuel",
        "co2_kg_per_unit": 3.17,
        "emissions_g_per_unit": {
            "bc": 1.40, "oc": 0.45, "so2": 0.02, "nox": 12.0, "co": 6.0,
        },
        "note": "The same CO2 per litre as any other diesel and more than an "
                "order of magnitude more black carbon than a filtered one.",
    },
    "diesel_dpf": {
        "label": "Diesel vehicle, particulate filter",
        "sector": "transport",
        "unit": "kg fuel",
        "co2_kg_per_unit": 3.17,
        "emissions_g_per_unit": {
            "bc": 0.03, "oc": 0.02, "so2": 0.02, "nox": 5.5, "co": 1.2,
        },
        "note": "Identical on the CO2 line to the entry above. The pair exists "
                "so the app can show that the fuel label is not the emission "
                "factor.",
    },
    "petrol_car": {
        "label": "Petrol vehicle",
        "sector": "transport",
        "unit": "kg fuel",
        "co2_kg_per_unit": 3.10,
        "emissions_g_per_unit": {
            "bc": 0.04, "oc": 0.09, "so2": 0.01, "nox": 2.2, "co": 14.0,
        },
        "note": "Slightly less CO2 per kilogram than diesel and much less "
                "black carbon than unfiltered diesel, offset by considerably "
                "more carbon monoxide.",
    },
    "shipping_hfo_high_sulphur": {
        "label": "Shipping, heavy fuel oil (pre-2020 sulphur)",
        "sector": "shipping",
        "unit": "kg fuel",
        "co2_kg_per_unit": 3.11,
        "emissions_g_per_unit": {
            "bc": 0.35, "oc": 0.60, "so2": 68.0, "nox": 60.0, "co": 7.4,
        },
        "note": "Enormous sulphur, and therefore an enormous cooling term. The "
                "before case for the single clearest unmasking example "
                "available.",
    },
    "shipping_low_sulphur": {
        "label": "Shipping, low-sulphur fuel (post-2020 cap)",
        "sector": "shipping",
        "unit": "kg fuel",
        "co2_kg_per_unit": 3.11,
        "emissions_g_per_unit": {
            "bc": 0.28, "oc": 0.35, "so2": 3.9, "nox": 58.0, "co": 7.4,
        },
        "note": "The same CO2 and a small fraction of the sulphur. A real "
                "improvement in air quality that removed a real cooling "
                "effect, and the module reports both.",
    },
    "aviation_kerosene": {
        "label": "Aviation kerosene",
        "sector": "aviation",
        "unit": "kg fuel",
        "co2_kg_per_unit": 3.16,
        "emissions_g_per_unit": {
            "bc": 0.03, "oc": 0.02, "so2": 0.80, "nox": 14.0, "co": 2.5,
        },
        "note": "Low particulate. Aviation's non-CO2 forcing is dominated by "
                "contrails and cruise-altitude ozone, which are altitude "
                "effects outside this module's scope and should not be "
                "inferred from the numbers here.",
    },
    "open_agricultural_burning": {
        "label": "Open agricultural burning",
        "sector": "land",
        "unit": "kg biomass",
        "co2_kg_per_unit": 1.52,
        "emissions_g_per_unit": {
            "bc": 0.52, "oc": 3.30, "so2": 0.40, "nox": 2.50, "co": 92.0,
        },
        "note": "Very high organic carbon relative to black carbon, so the "
                "aerosol terms partly cancel. The CO2 is largely biogenic and "
                "recaptured by regrowth, which makes the short-lived species "
                "the dominant climate effect rather than a correction to it.",
    },
    "coal_power_with_fgd": {
        "label": "Coal power, flue gas desulphurisation",
        "sector": "power",
        "unit": "kg fuel",
        "co2_kg_per_unit": 2.42,
        "emissions_g_per_unit": {
            "bc": 0.02, "oc": 0.03, "so2": 1.10, "nox": 3.20, "co": 0.15,
        },
        "note": "Scrubbed. The sulphur cooling that used to accompany the CO2 "
                "is largely gone, which is a straightforward public health "
                "gain and a small near-term climate cost.",
    },
    "coal_power_no_fgd": {
        "label": "Coal power, unscrubbed",
        "sector": "power",
        "unit": "kg fuel",
        "co2_kg_per_unit": 2.42,
        "emissions_g_per_unit": {
            "bc": 0.05, "oc": 0.06, "so2": 19.0, "nox": 4.10, "co": 0.30,
        },
        "note": "The other half of the retrofit comparison, and the reason a "
                "scrubber shows up as near-term warming on a forcing ledger "
                "while being unambiguously the right thing to fit.",
    },
}

# Deaths per tonne of PM2.5 precursor emitted, used only to keep the unmasking
# result honest by showing what the removed cooling bought. Deliberately coarse:
# src.utils.health_cobenefits.py does this properly and this is a cross-reference, not a
# competing estimate.
INDICATIVE_MORTALITY_PER_TONNE_PM = 0.045


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def list_species():
    """Species keys in reporting order."""
    return list(SPECIES_ORDER)


def get_species(key):
    """One species specification."""
    try:
        return SPECIES[key]
    except KeyError:
        raise AerosolError(
            f"Unknown species '{key}'. Known species: "
            f"{', '.join(list_species())}."
        )


def list_sources(sector=None):
    """Source keys, optionally filtered to one sector."""
    if sector is None:
        return sorted(SOURCES)
    return sorted(k for k, v in SOURCES.items() if v["sector"] == sector)


def list_sectors():
    """The distinct sectors present in the source table."""
    return sorted({spec["sector"] for spec in SOURCES.values()})


def get_source(key):
    """One source specification."""
    try:
        return SOURCES[key]
    except KeyError:
        raise AerosolError(
            f"Unknown source '{key}'. Known sources: "
            f"{', '.join(list_sources())}."
        )


def list_regions():
    """Deposition regions, most sensitive first."""
    return sorted(
        DEPOSITION_REGIONS,
        key=lambda k: -DEPOSITION_REGIONS[k]["bc_efficacy"],
    )


def get_region(key):
    """One deposition region specification."""
    try:
        return DEPOSITION_REGIONS[key]
    except KeyError:
        raise AerosolError(
            f"Unknown region '{key}'. Known regions: "
            f"{', '.join(list_regions())}."
        )


# ---------------------------------------------------------------------------
# Characterisation
# ---------------------------------------------------------------------------
def species_gwp(species, horizon, bound="central", region=DEFAULT_REGION):
    """GWP of one species at a horizon, with the deposition term applied.

    ``bound`` selects low, central or high. The three are returned separately
    rather than as a mean because the range for black carbon is a factor of
    seventeen and averaging it away would be the main route to misusing this.
    """
    spec = get_species(species)
    if horizon not in spec["gwp"]:
        raise AerosolError(
            f"GWP for {species} is tabulated at horizons "
            f"{sorted(spec['gwp'])}, not {horizon}. These species live for "
            f"days, so interpolating between horizons would be inventing data."
        )
    if bound not in ("low", "central", "high"):
        raise AerosolError("Bound must be 'low', 'central' or 'high'.")

    value = spec["gwp"][horizon][bound]
    if spec["deposition_sensitive"]:
        value *= get_region(region)["bc_efficacy"]
    return value


def characterise(emissions_kg, horizon, region=DEFAULT_REGION):
    """Turn a dict of species masses into forcing, with the sign preserved.

    Warming and cooling contributions are accumulated separately and only then
    netted, because a single net number conceals that half of it is an air
    quality harm nobody wants to keep.
    """
    if horizon not in HORIZONS:
        raise AerosolError(
            f"Horizon must be one of {HORIZONS}. Both are always reported "
            f"elsewhere in this module for a reason."
        )

    rows = []
    warming = {"low": 0.0, "central": 0.0, "high": 0.0}
    cooling = {"low": 0.0, "central": 0.0, "high": 0.0}

    for species in SPECIES_ORDER:
        mass = emissions_kg.get(species, 0.0)
        if mass < 0:
            raise AerosolError(f"Emission mass for {species} cannot be negative.")
        if mass == 0:
            continue

        bounds = {
            bound: mass * species_gwp(species, horizon, bound, region)
            for bound in ("low", "central", "high")
        }
        # The low/high bounds on a cooling species produce a co2e range whose
        # ends swap over, so order them rather than trusting the label.
        ordered_low = min(bounds.values())
        ordered_high = max(bounds.values())

        rows.append({
            "species": species,
            "label": get_species(species)["label"],
            "mass_kg": mass,
            "co2e_central": bounds["central"],
            "co2e_low": ordered_low,
            "co2e_high": ordered_high,
            "warms": bounds["central"] > 0,
        })

        target = warming if bounds["central"] > 0 else cooling
        target["central"] += bounds["central"]
        target["low"] += ordered_low
        target["high"] += ordered_high

    return {
        "horizon_years": horizon,
        "region": region,
        "region_label": get_region(region)["label"],
        "species": rows,
        "warming_co2e": warming["central"],
        "cooling_co2e": cooling["central"],
        "net_co2e": warming["central"] + cooling["central"],
        "net_co2e_low": warming["low"] + cooling["low"],
        "net_co2e_high": warming["high"] + cooling["high"],
        "sign_note": (
            "Warming and cooling are accumulated separately and netted only "
            "at the end. The cooling half is an air quality harm; reporting "
            "only the net figure would present it as a benefit worth keeping."
        ),
    }


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------
def activity_emissions(source, units):
    """Species masses in kilograms for some quantity of an activity."""
    if units < 0:
        raise AerosolError("Activity quantity cannot be negative.")
    spec = get_source(source)
    return {
        species: grams * units / 1000.0
        for species, grams in spec["emissions_g_per_unit"].items()
    }


def assess_activity(source, units, region=DEFAULT_REGION):
    """Full short-lived forcing assessment of an activity, at both horizons.

    Both horizons are always present in the result. There is no argument to
    request only one, because the disagreement between them is the finding.
    """
    spec = get_source(source)
    emissions = activity_emissions(source, units)
    co2_kg = spec["co2_kg_per_unit"] * units

    horizons = {}
    for horizon in HORIZONS:
        characterised = characterise(emissions, horizon, region)
        characterised["co2_kg"] = co2_kg
        characterised["total_co2e"] = co2_kg + characterised["net_co2e"]
        characterised["slcf_share_of_total"] = (
            characterised["net_co2e"] / characterised["total_co2e"]
            if characterised["total_co2e"] else 0.0
        )
        horizons[horizon] = characterised

    short = horizons[20]
    long = horizons[100]

    return {
        "source": source,
        "label": spec["label"],
        "sector": spec["sector"],
        "unit": spec["unit"],
        "units": units,
        "region": region,
        "co2_kg": co2_kg,
        "emissions_kg": emissions,
        "horizons": horizons,
        "slcf_dominates_near_term": abs(short["net_co2e"]) > co2_kg,
        "sign_flips_between_horizons": (
            (short["net_co2e"] > 0) != (long["net_co2e"] > 0)
        ),
        "near_term_multiple": (
            short["total_co2e"] / co2_kg if co2_kg else 0.0
        ),
        "long_term_multiple": (
            long["total_co2e"] / co2_kg if co2_kg else 0.0
        ),
        "overlay_note": (
            "These figures are additive to the well-mixed gas inventory in "
            "src.environment.climate_metrics.py and do not redefine it. The CO2 line here is "
            "carried only so the short-lived species can be put in proportion."
        ),
    }


# ---------------------------------------------------------------------------
# Comparison, which is where the horizon flip shows up
# ---------------------------------------------------------------------------
def compare_sources(sources, units=1.0, region=DEFAULT_REGION):
    """Several sources on the same basis, at both horizons.

    The ranking is computed at each horizon separately, so a reordering
    between them can be detected rather than assumed away.
    """
    if not sources:
        raise AerosolError("Nothing to compare.")

    results = [assess_activity(source, units, region) for source in sources]

    rankings = {}
    for horizon in HORIZONS:
        ordered = sorted(results, key=lambda r: r["horizons"][horizon]["total_co2e"])
        rankings[horizon] = [r["source"] for r in ordered]

    reorders = rankings[20] != rankings[100]

    return {
        "units": units,
        "region": region,
        "results": [
            {
                "source": r["source"],
                "label": r["label"],
                "co2_kg": r["co2_kg"],
                "total_co2e_20": r["horizons"][20]["total_co2e"],
                "total_co2e_100": r["horizons"][100]["total_co2e"],
                "net_slcf_20": r["horizons"][20]["net_co2e"],
                "net_slcf_100": r["horizons"][100]["net_co2e"],
            }
            for r in results
        ],
        "ranking_20": rankings[20],
        "ranking_100": rankings[100],
        "ranking_changes_with_horizon": reorders,
        "note": (
            "The ranking of these options reverses between the twenty-year "
            "and hundred-year horizons. That reversal, not either ordering, "
            "is the result worth reporting."
            if reorders else
            "The ranking holds at both horizons, so the horizon choice does "
            "not change which option to prefer here."
        ),
    }


def co2_only_error(source, units=1.0, region=DEFAULT_REGION):
    """How wrong a CO2-only inventory is about this activity.

    The point of the module in one number, for each horizon.
    """
    result = assess_activity(source, units, region)
    rows = []
    for horizon in HORIZONS:
        entry = result["horizons"][horizon]
        rows.append({
            "horizon_years": horizon,
            "co2_only_kg": result["co2_kg"],
            "with_slcf_kg": entry["total_co2e"],
            "error_kg": entry["net_co2e"],
            "error_fraction": (
                entry["net_co2e"] / result["co2_kg"] if result["co2_kg"] else 0.0
            ),
            "understated": entry["net_co2e"] > 0,
        })
    return {
        "source": source,
        "label": result["label"],
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Unmasking
# ---------------------------------------------------------------------------
def unmasking(before_source, after_source, units=1.0, region=DEFAULT_REGION,
              mortality_per_tonne_pm=INDICATIVE_MORTALITY_PER_TONNE_PM):
    """A cleanup measure's climate cost, reported against what it buys.

    Removing a cooling aerosol produces near-term warming. That is a real
    result and reporting it alone would be an argument for dirty air, so the
    avoided particulate exposure is reported in the same object. The trade-off
    is the output; neither half of it is.
    """
    before = assess_activity(before_source, units, region)
    after = assess_activity(after_source, units, region)

    horizons = {}
    for horizon in HORIZONS:
        delta = (
            after["horizons"][horizon]["total_co2e"]
            - before["horizons"][horizon]["total_co2e"]
        )
        horizons[horizon] = {
            "before_co2e": before["horizons"][horizon]["total_co2e"],
            "after_co2e": after["horizons"][horizon]["total_co2e"],
            "delta_co2e": delta,
            "is_near_term_warming": delta > 0,
        }

    pm_before = (
        before["emissions_kg"].get("bc", 0.0)
        + before["emissions_kg"].get("oc", 0.0)
    )
    pm_after = (
        after["emissions_kg"].get("bc", 0.0)
        + after["emissions_kg"].get("oc", 0.0)
    )
    so2_avoided = (
        before["emissions_kg"].get("so2", 0.0)
        - after["emissions_kg"].get("so2", 0.0)
    )
    # Sulphate forms secondary particulate, so avoided SO2 counts towards
    # avoided exposure at a reduced conversion.
    pm_avoided_kg = (pm_before - pm_after) + so2_avoided * 0.35

    return {
        "before": before_source,
        "before_label": before["label"],
        "after": after_source,
        "after_label": after["label"],
        "units": units,
        "region": region,
        "horizons": horizons,
        "so2_avoided_kg": so2_avoided,
        "pm_avoided_kg": pm_avoided_kg,
        "indicative_deaths_avoided": (
            pm_avoided_kg / 1000.0 * mortality_per_tonne_pm
        ),
        "is_unmasking": horizons[20]["delta_co2e"] > 0,
        "note": (
            "Removing the cooling aerosol warms in the near term. This is not "
            "an argument against the measure: the same particles cause the "
            "avoided mortality reported alongside. It is a trade-off, and the "
            "module reports it as one rather than picking a side."
            if horizons[20]["delta_co2e"] > 0 else
            "This change reduces both the warming species and the exposure, "
            "so there is no unmasking trade-off to weigh here."
        ),
        "mortality_caveat": (
            "The mortality figure is indicative and coarse. "
            "src.utils.health_cobenefits.py does this properly; this is a cross-"
            "reference to keep the climate result honest, not a competing "
            "estimate."
        ),
    }


# ---------------------------------------------------------------------------
# Uncertainty
# ---------------------------------------------------------------------------
def uncertainty_range(source, units=1.0, region=DEFAULT_REGION):
    """Low, central and high for an activity, at both horizons.

    Aerosol forcing is the largest uncertainty in the forcing budget and this
    module refuses to present a central estimate without its bounds. Where the
    range crosses zero the module says the sign is undetermined rather than
    reporting the central sign.
    """
    result = assess_activity(source, units, region)
    rows = []
    for horizon in HORIZONS:
        entry = result["horizons"][horizon]
        low = result["co2_kg"] + entry["net_co2e_low"]
        high = result["co2_kg"] + entry["net_co2e_high"]
        rows.append({
            "horizon_years": horizon,
            "low": low,
            "central": entry["total_co2e"],
            "high": high,
            "spread_ratio": (
                abs(high / low) if low not in (0,) and (high / low) > 0 else None
            ),
            "sign_determined": (low > 0) == (high > 0),
        })
    return {
        "source": source,
        "label": result["label"],
        "rows": rows,
        "note": (
            "Black carbon's hundred-year GWP spans roughly a factor of "
            "seventeen in the published literature, and the indirect effect "
            "of aerosols on clouds is the single largest uncertainty in the "
            "forcing budget. A central estimate without these bounds would be "
            "claiming a precision nobody has."
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_aerosol_insights(result):
    """Plain sentences about an activity assessment."""
    insights = []
    short = result["horizons"][20]
    long = result["horizons"][100]

    insights.append(
        f"On a twenty-year view the short-lived species add "
        f"{short['net_co2e']:+,.1f} kg CO2e to this activity's "
        f"{result['co2_kg']:,.1f} kg of CO2 — a total "
        f"{result['near_term_multiple']:.2f} times the CO2 alone."
    )
    insights.append(
        f"On a hundred-year view the same species add only "
        f"{long['net_co2e']:+,.1f} kg CO2e, because they have been gone for "
        f"decades while the CO2 has not. Same activity, "
        f"{result['long_term_multiple']:.2f} times the CO2 line."
    )

    if result["sign_flips_between_horizons"]:
        insights.append(
            "The net short-lived effect changes sign between the two horizons. "
            "Any single-horizon figure for this activity is taking a side in a "
            "policy argument without saying so."
        )

    if result["slcf_dominates_near_term"]:
        insights.append(
            "In the near term the short-lived species outweigh the CO2 "
            "entirely. A CO2-only inventory is not slightly incomplete here; "
            "it is measuring the smaller half."
        )

    warming = [row for row in short["species"] if row["warms"]]
    cooling = [row for row in short["species"] if not row["warms"]]
    if warming:
        largest = max(warming, key=lambda r: r["co2e_central"])
        insights.append(
            f"{largest['label']} is the largest warming contributor at "
            f"{largest['co2e_central']:,.1f} kg CO2e over twenty years, from "
            f"{largest['mass_kg'] * 1000:,.1f} g emitted."
        )
    if cooling:
        largest = min(cooling, key=lambda r: r["co2e_central"])
        insights.append(
            f"{largest['label']} offsets {abs(largest['co2e_central']):,.1f} kg "
            f"CO2e of that over the same period. That cooling is a by-product "
            f"of air pollution and is not something to preserve."
        )

    if result["region"] != DEFAULT_REGION:
        region = get_region(result["region"])
        insights.append(
            f"Black carbon here is weighted {region['bc_efficacy']:.1f}× for "
            f"deposition on snow and ice. {region['note']}"
        )

    spread = short["net_co2e_high"] - short["net_co2e_low"]
    insights.append(
        f"The twenty-year figure carries a range of {spread:,.0f} kg CO2e "
        f"between the published low and high bounds. That width is the honest "
        f"state of the science, not a shortcoming of this calculation."
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
        CREATE TABLE IF NOT EXISTS aerosol_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            source TEXT NOT NULL,
            co2_kg REAL NOT NULL,
            net_slcf_20 REAL NOT NULL,
            net_slcf_100 REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_aerosol_assessments_user
        ON aerosol_assessments (user_id)
        """
    )


def save_assessment(user_id, name, result):
    """Persist an activity assessment and return its row id."""
    if not user_id:
        raise AerosolError("An assessment needs a user to belong to.")
    if not name or not name.strip():
        raise AerosolError("An assessment needs a name.")

    payload = json.dumps({
        "source": result["source"],
        "units": result["units"],
        "unit": result["unit"],
        "region": result["region"],
        "emissions_kg": result["emissions_kg"],
        "near_term_multiple": result["near_term_multiple"],
        "long_term_multiple": result["long_term_multiple"],
        "sign_flips_between_horizons": result["sign_flips_between_horizons"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO aerosol_assessments
                (user_id, name, payload, source, co2_kg, net_slcf_20,
                 net_slcf_100)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload, result["source"],
                float(result["co2_kg"]),
                float(result["horizons"][20]["net_co2e"]),
                float(result["horizons"][100]["net_co2e"]),
            ),
        )
        return int(cursor.lastrowid)


def get_assessments(user_id):
    """Saved assessments for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, source, co2_kg, net_slcf_20,
                       net_slcf_100, created_at
                FROM aerosol_assessments
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved aerosol assessments")
        return []

    assessments = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        assessments.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "source": row[3],
            "co2_kg": row[4],
            "net_slcf_20": row[5],
            "net_slcf_100": row[6],
            "created_at": row[7],
        })
    return assessments


def delete_assessment(user_id, assessment_id):
    """Delete one saved assessment. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM aerosol_assessments WHERE id = ? AND user_id = ?",
                (assessment_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete aerosol assessment %s", assessment_id)
        return False
