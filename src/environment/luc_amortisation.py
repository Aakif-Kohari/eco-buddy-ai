"""Carbon released when land changed hands, and the choice that sizes it.

``src/carbon/meal_carbon_calculator.py`` gives beef a per-kilogram factor.
``biodiversity_footprint.py`` characterises the land it occupies.
``land_opportunity_cost.py`` asks what that land could otherwise be doing.
``src/carbon/soil_carbon_engine.py`` models soil carbon under management change.

None of them account for the carbon released when the land was cleared to grow
the thing in the first place.

For most of a diet that omission is small. For the handful of commodities that
drive deforestation - beef, soy, palm oil, cocoa, coffee - it is frequently
larger than every other stage of the supply chain combined, and this app
currently reports one number for a kilogram from recently converted forest and
a kilogram from pasture established a century ago.

The amortisation period is a policy choice, not a fact
--------------------------------------------------------
Clearing releases a stock, once. Attributing that stock to a stream of annual
production requires choosing a period over which to spread it, and the choice
moves the per-kilogram figure by more than a factor of two.

PAS 2050 and the IPCC guidelines say twenty years. Some national inventories
use thirty. A discounted attribution front-loads instead, which is the only
scheme that reflects when the carbon is actually in the atmosphere. A pulse
charges the whole stock to the conversion year, which is what physically
happened and is unusable for a per-kilogram figure.

None of these is wrong. The module reports all four side by side and refuses
to nominate one, because nominating one would bury the choice in a constant
exactly as the current emission factors do.

Averaging over a region and tracing a supply chain answer different questions
------------------------------------------------------------------------------
The country-average approach spreads national conversion across national
output, so every kilogram carries a small share. The direct approach charges
the full stock to the land actually used. The ratio between them is reported,
because a large ratio means sourcing matters for this commodity and a small
one means it does not - and that is more actionable than either figure alone.

Both pools change, and only one is usually counted
----------------------------------------------------
Above- and below-ground biomass is the visible term and goes quickly. Soil
organic carbon keeps declining for decades afterwards. A conversion twelve
years ago is still emitting, and this module counts it as still emitting.

Indirect land-use change cannot be handled by omitting it
-----------------------------------------------------------
Displaced production moves somewhere. Published estimates span an order of
magnitude. Setting it to zero is not the neutral choice; it is one end of the
range, selected silently. Here it is available only as an explicitly named
scenario, every total that includes it is labelled with the scenario name, and
the range is printed next to the number.

Foregone sequestration is kept out of the total on purpose
------------------------------------------------------------
Land held as pasture is land not regrowing forest. Whether that belongs in a
footprint is a live methodological argument. It is computed, reported on its
own line, and never folded in.

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

#: Molecular mass ratio for converting carbon to carbon dioxide.
CO2_PER_C = 44.0 / 12.0


class LUCError(ValueError):
    """Raised when a land-use change figure cannot be supported."""


#: IPCC Tier 1 style carbon stocks, tonnes of carbon per hectare. Biomass is
#: above and below ground; soil is the top 30 cm, which is the depth the Tier 1
#: defaults are defined for and shallower than the profile actually affected.
LAND_COVERS = {
    "tropical_moist_forest": {
        "label": "Tropical moist forest",
        "biomass_c": 130.0,
        "soil_c": 60.0,
        "regrowth_c_per_year": 4.0,
        "note": (
            "The highest biomass stock here and the cover behind most of the "
            "commodity-driven conversion in the published data. Clearing one "
            "hectare releases more carbon than a European household emits in "
            "sixty years."
        ),
    },
    "tropical_dry_forest": {
        "label": "Tropical dry forest and woodland",
        "biomass_c": 55.0,
        "soil_c": 40.0,
        "regrowth_c_per_year": 2.0,
        "note": (
            "Lower stocks and far faster conversion rates. Frequently "
            "classified as degraded land before clearing, which makes the "
            "conversion invisible in some accounting frames."
        ),
    },
    "temperate_forest": {
        "label": "Temperate forest",
        "biomass_c": 60.0,
        "soil_c": 80.0,
        "regrowth_c_per_year": 2.5,
        "note": (
            "More carbon in the soil than in the trees, which inverts the "
            "usual assumption that clearing is mostly a biomass event."
        ),
    },
    "boreal_forest": {
        "label": "Boreal forest",
        "biomass_c": 45.0,
        "soil_c": 110.0,
        "regrowth_c_per_year": 1.0,
        "note": (
            "Soil dominates and regrowth is slow enough that the foregone "
            "sequestration term stays small for decades."
        ),
    },
    "peatland": {
        "label": "Peatland and organic soils",
        "biomass_c": 40.0,
        "soil_c": 400.0,
        "regrowth_c_per_year": 0.5,
        "note": (
            "An order of magnitude more soil carbon than anything else here, "
            "and drainage keeps it oxidising for a century. Any conversion "
            "involving peat dominates whatever else is in the assessment."
        ),
    },
    "savanna": {
        "label": "Savanna and shrubland",
        "biomass_c": 15.0,
        "soil_c": 45.0,
        "regrowth_c_per_year": 1.0,
        "note": (
            "Modest biomass, substantial soil carbon, and the cover most "
            "often converted to pasture."
        ),
    },
    "grassland": {
        "label": "Natural grassland",
        "biomass_c": 5.0,
        "soil_c": 55.0,
        "regrowth_c_per_year": 0.5,
        "note": (
            "Almost all of the stock is below ground, so a conversion that "
            "looks like nothing from the air can still be a large release."
        ),
    },
    "cropland_annual": {
        "label": "Annual cropland",
        "biomass_c": 2.5,
        "soil_c": 40.0,
        "regrowth_c_per_year": 0.2,
        "note": (
            "The most common destination cover. Tillage keeps soil carbon "
            "well below the natural equilibrium indefinitely."
        ),
    },
    "cropland_perennial": {
        "label": "Perennial cropland and orchards",
        "biomass_c": 20.0,
        "soil_c": 45.0,
        "regrowth_c_per_year": 0.5,
        "note": (
            "Standing biomass makes this a much softer landing than annual "
            "cropland, which is the basis of most agroforestry arguments."
        ),
    },
    "oil_palm": {
        "label": "Oil palm plantation",
        "biomass_c": 40.0,
        "soil_c": 40.0,
        "regrowth_c_per_year": 1.5,
        "note": (
            "Holds real biomass, which is why the palm industry quotes a "
            "small net stock change against forest. Against peatland the same "
            "arithmetic gives one of the largest figures in this table."
        ),
    },
    "pasture": {
        "label": "Managed pasture",
        "biomass_c": 4.0,
        "soil_c": 50.0,
        "regrowth_c_per_year": 0.3,
        "note": (
            "The destination for most tropical forest conversion by area, and "
            "the cover where the foregone sequestration argument bites "
            "hardest."
        ),
    },
    "degraded_land": {
        "label": "Degraded or abandoned land",
        "biomass_c": 3.0,
        "soil_c": 25.0,
        "regrowth_c_per_year": 0.8,
        "note": (
            "Converting to this releases nearly everything. Converting *from* "
            "it is the only common case in this table that sequesters."
        ),
    },
    "settlement": {
        "label": "Settlement and built land",
        "biomass_c": 2.0,
        "soil_c": 30.0,
        "regrowth_c_per_year": 0.0,
        "note": (
            "Effectively permanent. No regrowth term, because sealed ground "
            "does not come back on any horizon a footprint is written for."
        ),
    },
}

#: The amortisation schemes. Each is defensible and they disagree by more
#: than a factor of two, which is the whole reason all four are reported.
AMORTISATION_SCHEMES = {
    "pas2050_20": {
        "label": "PAS 2050 linear, 20 years",
        "period": 20,
        "kind": "linear",
        "note": (
            "The default in PAS 2050 Annex C, the IPCC guidelines and the EU "
            "Product Environmental Footprint method. Equal share every year "
            "for twenty years, then nothing."
        ),
    },
    "linear_30": {
        "label": "Linear, 30 years",
        "period": 30,
        "kind": "linear",
        "note": (
            "Used in several national inventories. Same arithmetic, a third "
            "less per year, and a per-kilogram figure two thirds the size of "
            "the twenty-year one for no reason to do with the biology."
        ),
    },
    "discounted_20": {
        "label": "Discounted attribution, 20 years",
        "period": 20,
        "kind": "discounted",
        "rate": 0.03,
        "note": (
            "Front-loads the charge, which is the only one of these schemes "
            "that reflects when the carbon is actually in the atmosphere. "
            "Heavier in the first years and lighter later."
        ),
    },
    "pulse": {
        "label": "Full pulse in the conversion year",
        "period": 1,
        "kind": "pulse",
        "note": (
            "What physically happened. Correct for a specific plot and a "
            "specific year, and unusable as a per-kilogram factor, because it "
            "charges the whole stock to whatever was harvested first."
        ),
    },
}

#: Indirect land-use change scenarios. Never a default, always named on any
#: total that includes one. Values are tonnes CO2e per tonne of commodity.
ILUC_SCENARIOS = {
    "none": {
        "label": "Excluded",
        "factors": {},
        "note": (
            "Not the neutral choice. It is the bottom of the published range, "
            "selected silently, and it is what every other module in this app "
            "currently does."
        ),
    },
    "low": {
        "label": "Low end of the published range",
        "factors": {
            "soy": 0.2, "palm_oil": 0.6, "beef": 1.0,
            "maize": 0.1, "sugar": 0.1, "wheat": 0.1,
        },
        "note": "Roughly the low estimates from the market-mediated modelling.",
    },
    "central": {
        "label": "Central",
        "factors": {
            "soy": 0.9, "palm_oil": 2.6, "beef": 4.0,
            "maize": 0.5, "sugar": 0.4, "wheat": 0.3,
        },
        "note": (
            "Mid-range across the published economic models. The spread "
            "between models is larger than the difference between commodities."
        ),
    },
    "high": {
        "label": "High end of the published range",
        "factors": {
            "soy": 2.4, "palm_oil": 6.0, "beef": 9.0,
            "maize": 1.4, "sugar": 1.1, "wheat": 0.8,
        },
        "note": (
            "The upper estimates, which exceed the direct term for several "
            "commodities. Quoted here so the range is visible rather than "
            "argued about."
        ),
    },
}

ATTRIBUTIONS = {
    "direct": (
        "Charge the converted area to what is grown on it. The right frame "
        "when the plot is known."
    ),
    "country_average": (
        "Spread national conversion across national output. The right frame "
        "when the supply chain is unknown, which is usually."
    ),
}

#: Default soil carbon decay constant after conversion, per year. Around a
#: twenty-year time constant, which is the middle of the published range.
DEFAULT_SOIL_DECAY = 0.05


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def _cover(key):
    if key is None:
        raise LUCError("A land cover is required.")
    normalised = str(key).strip().lower()
    if normalised not in LAND_COVERS:
        known = ", ".join(sorted(LAND_COVERS))
        raise LUCError("Unknown land cover '%s'. Known: %s." % (key, known))
    return normalised


def list_land_covers():
    """Every land cover with its stocks, in carbon and in CO2."""
    entries = []
    for key in sorted(LAND_COVERS, key=lambda item: LAND_COVERS[item]["label"]):
        definition = LAND_COVERS[key]
        total_c = definition["biomass_c"] + definition["soil_c"]
        entries.append({
            "key": key,
            "label": definition["label"],
            "biomass_c": definition["biomass_c"],
            "soil_c": definition["soil_c"],
            "total_c": total_c,
            "total_co2_per_ha": total_c * CO2_PER_C,
            "regrowth_c_per_year": definition["regrowth_c_per_year"],
            "note": definition["note"],
        })
    return entries


def get_land_cover(key):
    """One land cover entry, or ``None``."""
    for entry in list_land_covers():
        if entry["key"] == key:
            return entry
    return None


def list_schemes():
    """Every amortisation scheme with the choice it embodies."""
    return [
        dict(AMORTISATION_SCHEMES[key], key=key)
        for key in sorted(AMORTISATION_SCHEMES)
    ]


def list_iluc_scenarios():
    """Every iLUC scenario, including the excluded one, which is also a choice."""
    return [dict(ILUC_SCENARIOS[key], key=key) for key in sorted(ILUC_SCENARIOS)]


# ---------------------------------------------------------------------------
# Stock change
# ---------------------------------------------------------------------------

def stock_change(prior_cover, subsequent_cover, area_ha):
    """Carbon released by converting ``area_ha`` from one cover to another.

    Biomass and soil are kept apart throughout, because they behave completely
    differently in time: biomass goes within a year or two of clearing, soil
    keeps declining for decades.
    """
    before = _cover(prior_cover)
    after = _cover(subsequent_cover)
    area = float(area_ha)
    if area <= 0:
        raise LUCError("Converted area must be positive.")

    before_def = LAND_COVERS[before]
    after_def = LAND_COVERS[after]

    biomass_loss_c = (before_def["biomass_c"] - after_def["biomass_c"]) * area
    soil_loss_c = (before_def["soil_c"] - after_def["soil_c"]) * area
    total_c = biomass_loss_c + soil_loss_c

    return {
        "prior_cover": before,
        "prior_label": before_def["label"],
        "subsequent_cover": after,
        "subsequent_label": after_def["label"],
        "area_ha": area,
        "biomass_loss_c": biomass_loss_c,
        "soil_loss_c": soil_loss_c,
        "total_loss_c": total_c,
        "biomass_co2": biomass_loss_c * CO2_PER_C,
        "soil_co2": soil_loss_c * CO2_PER_C,
        "total_co2": total_c * CO2_PER_C,
        "sequestering": total_c < 0,
        "soil_share": (soil_loss_c / total_c) if total_c else None,
    }


def soil_decay_profile(change, years=60, decay_rate=DEFAULT_SOIL_DECAY):
    """Year-by-year soil carbon release after a conversion.

    An exponential approach to the new equilibrium rather than an
    instantaneous step, so a conversion twelve years ago is reported as still
    emitting - which it is, and which every constant emission factor in this
    app implicitly denies.
    """
    span = int(years)
    if span <= 0:
        raise LUCError("A decay profile needs at least one year.")
    rate = float(decay_rate)
    if rate <= 0:
        raise LUCError(
            "A soil decay rate must be positive. A rate of zero says the "
            "soil never reaches its new equilibrium."
        )

    total = change["soil_co2"]
    rows = []
    for offset in range(span):
        remaining_before = math.exp(-rate * offset)
        remaining_after = math.exp(-rate * (offset + 1))
        rows.append({
            "year_offset": offset,
            "co2": total * (remaining_before - remaining_after),
            "cumulative_share": 1.0 - remaining_after,
        })
    return rows


def soil_released_by(change, years_since_conversion,
                     decay_rate=DEFAULT_SOIL_DECAY):
    """How much of the soil pool has actually gone, this many years in."""
    elapsed = float(years_since_conversion)
    if elapsed < 0:
        raise LUCError("Years since conversion cannot be negative.")
    rate = float(decay_rate)
    if rate <= 0:
        raise LUCError("A soil decay rate must be positive.")
    return change["soil_co2"] * (1.0 - math.exp(-rate * elapsed))


# ---------------------------------------------------------------------------
# Amortisation
# ---------------------------------------------------------------------------

def _scheme(key):
    if key is None:
        raise LUCError("An amortisation scheme is required.")
    normalised = str(key).strip().lower()
    if normalised not in AMORTISATION_SCHEMES:
        known = ", ".join(sorted(AMORTISATION_SCHEMES))
        raise LUCError("Unknown scheme '%s'. Known: %s." % (key, known))
    return normalised


def amortisation_weights(scheme):
    """The share of the stock charged to each year of the window.

    Weights sum to one by construction for every scheme, which is the only
    property that makes the four comparable at all.
    """
    key = _scheme(scheme)
    definition = AMORTISATION_SCHEMES[key]
    period = definition["period"]

    if definition["kind"] == "pulse":
        return [1.0]
    if definition["kind"] == "linear":
        return [1.0 / period] * period

    discount = 1.0 / (1.0 + definition["rate"])
    raw = [discount ** offset for offset in range(period)]
    total = sum(raw)
    return [value / total for value in raw]


def amortise(total_co2, conversion_year, assessment_year, scheme="pas2050_20"):
    """The share of a conversion charged to one particular year.

    A conversion older than the window is a completed obligation, not a
    negative one. It returns zero with a flag saying so, rather than an
    arithmetic result that would credit the user for the passage of time.
    """
    key = _scheme(scheme)
    definition = AMORTISATION_SCHEMES[key]

    try:
        converted = int(conversion_year)
        assessed = int(assessment_year)
    except (TypeError, ValueError):
        raise LUCError("Conversion and assessment years must be whole years.")

    if assessed < converted:
        raise LUCError(
            "The assessment year %d is before the conversion in %d. There is "
            "nothing to amortise yet." % (assessed, converted)
        )

    elapsed = assessed - converted
    weights = amortisation_weights(key)

    if elapsed >= len(weights):
        return {
            "scheme": key,
            "scheme_label": definition["label"],
            "period": definition["period"],
            "years_elapsed": elapsed,
            "weight": 0.0,
            "annual_co2": 0.0,
            "cumulative_co2": float(total_co2),
            "obligation_complete": True,
            "note": (
                "The conversion was %d years ago and the %d-year window has "
                "closed. The obligation is discharged, which is not the same "
                "as the carbon having come back."
                % (elapsed, definition["period"])
            ),
        }

    weight = weights[elapsed]
    return {
        "scheme": key,
        "scheme_label": definition["label"],
        "period": definition["period"],
        "years_elapsed": elapsed,
        "weight": weight,
        "annual_co2": float(total_co2) * weight,
        "cumulative_co2": float(total_co2) * sum(weights[:elapsed + 1]),
        "obligation_complete": False,
        "note": definition["note"],
    }


def compare_schemes(total_co2, conversion_year, assessment_year):
    """Every scheme's answer for the same conversion, side by side.

    The spread between them is the finding. It is a policy choice and it moves
    the number more than most of the biology does.
    """
    rows = []
    for key in sorted(AMORTISATION_SCHEMES):
        rows.append(amortise(total_co2, conversion_year, assessment_year, key))

    live = [row["annual_co2"] for row in rows if not row["obligation_complete"]]
    spread = None
    if live and min(live) > 0:
        spread = max(live) / min(live)

    return {
        "rows": rows,
        "spread": spread,
        "all_complete": all(row["obligation_complete"] for row in rows),
    }


# ---------------------------------------------------------------------------
# Attribution to a commodity
# ---------------------------------------------------------------------------

def _attribution(key):
    normalised = str(key or "").strip().lower()
    if normalised not in ATTRIBUTIONS:
        known = ", ".join(sorted(ATTRIBUTIONS))
        raise LUCError("Unknown attribution '%s'. Known: %s." % (key, known))
    return normalised


def direct_intensity(change, annual_yield_t_per_ha, scheme="pas2050_20"):
    """Stock charged to the land actually used, per tonne of output."""
    yield_rate = float(annual_yield_t_per_ha)
    if yield_rate <= 0:
        raise LUCError("Yield must be positive to attribute anything to it.")

    weights = amortisation_weights(scheme)
    period = len(weights)
    output_over_window = yield_rate * change["area_ha"] * period
    return change["total_co2"] / output_over_window


def country_average_intensity(change_per_ha_co2, national_conversion_ha,
                              national_output_t, scheme="pas2050_20"):
    """Stock spread across a region's whole output of the commodity.

    The right frame when the plot is unknown, which it almost always is, and
    it produces a far smaller per-tonne figure than the direct route.
    """
    converted = float(national_conversion_ha)
    output = float(national_output_t)
    if converted < 0:
        raise LUCError("Converted area cannot be negative.")
    if output <= 0:
        raise LUCError("National output must be positive.")

    weights = amortisation_weights(scheme)
    period = len(weights)
    total_co2 = float(change_per_ha_co2) * converted
    return total_co2 / (output * period)


def iluc_component(commodity, scenario="none"):
    """The indirect term, only ever from a named scenario."""
    key = str(scenario or "none").strip().lower()
    if key not in ILUC_SCENARIOS:
        known = ", ".join(sorted(ILUC_SCENARIOS))
        raise LUCError("Unknown iLUC scenario '%s'. Known: %s." % (scenario, known))

    definition = ILUC_SCENARIOS[key]
    commodity_key = str(commodity or "").strip().lower()
    factor = definition["factors"].get(commodity_key)

    return {
        "scenario": key,
        "scenario_label": definition["label"],
        "commodity": commodity_key,
        "factor_t_co2_per_t": factor,
        "available": factor is not None,
        "note": definition["note"],
        "range": _iluc_range(commodity_key),
    }


def _iluc_range(commodity):
    values = []
    for definition in ILUC_SCENARIOS.values():
        value = definition["factors"].get(commodity)
        if value is not None:
            values.append(value)
    if not values:
        return None
    return {"low": min(values), "high": max(values)}


def foregone_sequestration(prior_cover, area_ha, years):
    """Carbon the land would have taken up had it been left alone.

    Reported on its own line and never folded into a total. Whether it belongs
    in a footprint at all is a live argument, and burying it in a headline
    number would settle that argument by presentation.
    """
    key = _cover(prior_cover)
    area = float(area_ha)
    if area <= 0:
        raise LUCError("Area must be positive.")
    span = float(years)
    if span < 0:
        raise LUCError("Years cannot be negative.")

    rate = LAND_COVERS[key]["regrowth_c_per_year"]
    carbon = rate * area * span
    return {
        "prior_cover": key,
        "prior_label": LAND_COVERS[key]["label"],
        "area_ha": area,
        "years": span,
        "rate_c_per_ha_year": rate,
        "co2": carbon * CO2_PER_C,
        "note": (
            "Not included in any total on this page. It is the sequestration "
            "the land would have performed had it been left alone, and "
            "whether that is an emission is a methodological argument rather "
            "than a measurement."
        ),
    }


# ---------------------------------------------------------------------------
# The composed assessment
# ---------------------------------------------------------------------------

def assess(commodity, prior_cover, subsequent_cover, area_ha,
           annual_yield_t_per_ha, conversion_year, assessment_year,
           scheme="pas2050_20", attribution="direct",
           iluc_scenario="none", annual_consumption_kg=0.0,
           national_conversion_ha=None, national_output_t=None):
    """One commodity, one conversion, one amortisation choice, stated.

    Direct and country-average attribution are never mixed inside a single
    total; the caller picks one and the other is reported alongside for
    comparison where the data allows.
    """
    change = stock_change(prior_cover, subsequent_cover, area_ha)
    scheme_key = _scheme(scheme)
    attribution_key = _attribution(attribution)

    schedule = amortise(
        change["total_co2"], conversion_year, assessment_year, scheme_key
    )

    direct = direct_intensity(change, annual_yield_t_per_ha, scheme_key)

    average = None
    if national_conversion_ha is not None and national_output_t is not None:
        per_ha = change["total_co2"] / change["area_ha"]
        average = country_average_intensity(
            per_ha, national_conversion_ha, national_output_t, scheme_key
        )

    if attribution_key == "country_average":
        if average is None:
            raise LUCError(
                "Country-average attribution needs national conversion area "
                "and national output. Falling back to the direct figure would "
                "silently answer a different question."
            )
        intensity = average
    else:
        intensity = direct

    indirect = iluc_component(commodity, iluc_scenario)
    indirect_intensity = indirect["factor_t_co2_per_t"] or 0.0

    consumption_t = float(annual_consumption_kg) / 1000.0
    if consumption_t < 0:
        raise LUCError("Consumption cannot be negative.")

    direct_annual_kg = intensity * consumption_t * 1000.0
    indirect_annual_kg = indirect_intensity * consumption_t * 1000.0

    ratio = (direct / average) if average and average > 0 else None

    return {
        "commodity": str(commodity).strip().lower(),
        "change": change,
        "schedule": schedule,
        "scheme": scheme_key,
        "attribution": attribution_key,
        "direct_intensity_t_co2_per_t": direct,
        "country_average_intensity_t_co2_per_t": average,
        "attribution_ratio": ratio,
        "intensity_t_co2_per_t": intensity,
        "iluc": indirect,
        "iluc_intensity_t_co2_per_t": indirect_intensity,
        "total_intensity_t_co2_per_t": intensity + indirect_intensity,
        "annual_consumption_kg": float(annual_consumption_kg),
        "direct_annual_kg_co2": direct_annual_kg,
        "iluc_annual_kg_co2": indirect_annual_kg,
        "total_annual_kg_co2": direct_annual_kg + indirect_annual_kg,
        "label": _total_label(scheme_key, attribution_key, indirect),
    }


def _total_label(scheme, attribution, indirect):
    """Every total says which choices produced it. That is the point."""
    parts = [
        AMORTISATION_SCHEMES[scheme]["label"],
        "direct attribution" if attribution == "direct"
        else "country-average attribution",
    ]
    if indirect["scenario"] == "none":
        parts.append("iLUC excluded")
    else:
        parts.append("iLUC %s" % indirect["scenario_label"].lower())
    return "; ".join(parts)


def sourcing_comparison(result, deforestation_free_intensity=0.0):
    """The same commodity from a conversion-linked and a verified-free source.

    Expressed per kilogram and per year of consumption, because a per-tonne
    figure does not change anybody's shopping and an annual one does.
    """
    clean = float(deforestation_free_intensity)
    if clean < 0:
        raise LUCError("A deforestation-free intensity cannot be negative.")

    linked = result["total_intensity_t_co2_per_t"]
    if clean > linked:
        raise LUCError(
            "The deforestation-free option is worse than the linked one, "
            "which means one of the two figures is not what it claims to be."
        )

    consumption_t = result["annual_consumption_kg"] / 1000.0
    return {
        "linked_intensity": linked,
        "free_intensity": clean,
        # Tonnes CO2e per tonne and kilograms CO2e per kilogram are the same
        # number; both are given because the page quotes each in its place.
        "saving_per_tonne": linked - clean,
        "saving_per_kg": linked - clean,
        "annual_saving_kg_co2": (linked - clean) * consumption_t * 1000.0,
        "reduction_share": ((linked - clean) / linked) if linked > 0 else None,
    }


def scheme_sensitivity(result):
    """The same assessment under every scheme, to size the policy choice."""
    yield_rate = _implied_yield(result)
    rows = []
    for key in sorted(AMORTISATION_SCHEMES):
        intensity = direct_intensity(result["change"], yield_rate, key)
        rows.append({
            "scheme": key,
            "label": AMORTISATION_SCHEMES[key]["label"],
            "intensity_t_co2_per_t": intensity,
            "annual_kg_co2": intensity * result["annual_consumption_kg"],
        })

    values = [row["intensity_t_co2_per_t"] for row in rows if row["intensity_t_co2_per_t"] > 0]
    return {
        "rows": rows,
        "spread": (max(values) / min(values)) if values else None,
    }


def _implied_yield(result):
    """Recover the yield the assessment was built with."""
    weights = amortisation_weights(result["scheme"])
    change = result["change"]
    intensity = result["direct_intensity_t_co2_per_t"]
    if intensity <= 0:
        raise LUCError("Cannot recover a yield from a zero intensity.")
    return change["total_co2"] / (intensity * change["area_ha"] * len(weights))


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

def get_luc_insights(result):
    """Plain-language findings, with the choice-dependent ones first."""
    insights = []
    change = result["change"]

    if change["sequestering"]:
        insights.append({
            "level": "info",
            "title": "This conversion accumulates carbon rather than releasing it",
            "body": (
                "Going from %s to %s adds stock. That is a real credit and it "
                "is also the case where the amortisation schemes matter least, "
                "because there is no obligation to spread."
                % (change["prior_label"], change["subsequent_label"])
            ),
        })
    else:
        insights.append({
            "level": "warning",
            "title": "%.0f tonnes of CO2 released per hectare converted"
                     % (change["total_co2"] / change["area_ha"]),
            "body": (
                "%.0f%% of it from soil rather than biomass. Soil is the part "
                "that keeps going for decades after the clearing, and the part "
                "that no emission factor in this app currently represents."
                % ((change["soil_share"] or 0.0) * 100.0)
            ),
        })

    insights.append({
        "level": "info",
        "title": "Every number here is labelled with the choices behind it",
        "body": "This one: %s." % result["label"],
    })

    if result["attribution_ratio"] and result["attribution_ratio"] > 3:
        insights.append({
            "level": "warning",
            "title": "Sourcing matters a great deal for this commodity",
            "body": (
                "The direct figure is %.0f× the country average. That gap is "
                "the value of knowing where this actually came from, and it "
                "is large enough that a country-average factor is close to "
                "uninformative for an individual purchase."
                % result["attribution_ratio"]
            ),
        })
    elif result["attribution_ratio"]:
        insights.append({
            "level": "info",
            "title": "Sourcing barely moves this commodity",
            "body": (
                "Direct and country-average attribution differ by only %.1f×. "
                "Chasing provenance here is not where the reduction is."
                % result["attribution_ratio"]
            ),
        })

    if result["iluc"]["scenario"] == "none":
        range_note = result["iluc"]["range"]
        if range_note:
            insights.append({
                "level": "warning",
                "title": "Indirect land-use change is excluded, which is a choice",
                "body": (
                    "The published range for %s runs from %.1f to %.1f tonnes "
                    "CO2e per tonne. Zero is not the neutral option; it is the "
                    "bottom of that range, selected silently."
                    % (
                        result["commodity"],
                        range_note["low"],
                        range_note["high"],
                    )
                ),
            })
    else:
        insights.append({
            "level": "warning",
            "title": "This total includes a contested indirect term",
            "body": (
                "%.1f tonnes CO2e per tonne under the %s scenario, against a "
                "direct term of %.1f. %s"
                % (
                    result["iluc_intensity_t_co2_per_t"],
                    result["iluc"]["scenario_label"].lower(),
                    result["intensity_t_co2_per_t"],
                    result["iluc"]["note"],
                )
            ),
        })

    if result["schedule"]["obligation_complete"]:
        insights.append({
            "level": "info",
            "title": "The amortisation window has closed",
            "body": result["schedule"]["note"],
        })

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS luc_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            commodity TEXT NOT NULL,
            scheme TEXT NOT NULL,
            attribution TEXT NOT NULL,
            iluc_scenario TEXT NOT NULL,
            payload TEXT NOT NULL,
            intensity REAL NOT NULL,
            annual_kg_co2 REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_luc_assessments_user
        ON luc_assessments (user_id)
        """
    )


def save_assessment(user_id, result):
    """Persist an assessment with the choices that produced it."""
    if not user_id:
        raise LUCError("A saved assessment needs a user to belong to.")

    payload = json.dumps({
        "label": result["label"],
        "prior_cover": result["change"]["prior_cover"],
        "subsequent_cover": result["change"]["subsequent_cover"],
        "area_ha": result["change"]["area_ha"],
        "total_co2": result["change"]["total_co2"],
        "direct_intensity": result["direct_intensity_t_co2_per_t"],
        "country_average_intensity": result["country_average_intensity_t_co2_per_t"],
        "iluc_intensity": result["iluc_intensity_t_co2_per_t"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO luc_assessments
                (user_id, commodity, scheme, attribution, iluc_scenario,
                 payload, intensity, annual_kg_co2)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), result["commodity"], result["scheme"],
                result["attribution"], result["iluc"]["scenario"], payload,
                float(result["total_intensity_t_co2_per_t"]),
                float(result["total_annual_kg_co2"]),
            ),
        )
        return int(cursor.lastrowid)


def get_assessments(user_id, limit=25):
    """Saved assessments for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, commodity, scheme, attribution, iluc_scenario,
                       payload, intensity, annual_kg_co2, created_at
                FROM luc_assessments
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved land-use change assessments")
        return []

    saved = []
    for row in rows:
        try:
            payload = json.loads(row[5])
        except (TypeError, ValueError):
            payload = {}
        saved.append({
            "id": row[0],
            "commodity": row[1],
            "scheme": row[2],
            "attribution": row[3],
            "iluc_scenario": row[4],
            "payload": payload,
            "intensity": row[6],
            "annual_kg_co2": row[7],
            "created_at": row[8],
        })
    return saved


def delete_assessment(user_id, assessment_id):
    """Delete one saved assessment. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM luc_assessments WHERE id = ? AND user_id = ?",
                (assessment_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete land-use change assessment")
        return False
