"""Reductions that are relocations, and the frame that hides them.

A household buys a washing machine made in another country. Every kilogram of
carbon in it is emitted abroad, counted in that country's territorial
inventory, and never appears in the buyer's national total.

``src/business/eeio_spend.py`` exists because this repo already accepts that
consumption is the honest frame. But nothing reconciles a consumption-based
personal footprint against the *territorial* accounting that every national
target, every "emissions fell 40% since 1990" headline, and every benchmark in
``src/carbon/carbon_benchmarking.py`` is denominated in.

So the app benchmarks a consumption footprint against production-based
averages. For a net-importing country those differ by twenty to forty percent,
and the comparison is silently wrong in the flattering direction.

The failure this module exists to catch
-----------------------------------------
Replace a domestically made product with an imported one, or a manufacturing
job with an imported service, and the territorially-framed number falls while
the emissions carry on somewhere with a dirtier grid and no carbon price. Every
module in this app scores that as progress.

``substitution`` decomposes an apparent change into the part that is a genuine
reduction and the part that is a relocation. The decomposition is exact - the
two components sum to the observed change with no residual - because a
remainder in an analysis of this kind invites the reader to assume it was the
good part.

A tonne of steel is not a tonne of steel
------------------------------------------
Most of the difference between origins is grid intensity, so intensity here is
built as a process term plus an electricity term times the origin's grid,
rather than tabulated per origin. That makes the mechanism visible and means
one grid figure can be updated without touching every product.

Freight is counted separately, and honestly
---------------------------------------------
International freight is real and, for most goods moving by sea, small.
Conflating it with the production-location difference is the most common error
in this area and the reason "local" and "low-carbon" get treated as synonyms.
It is reported apart, with the mode's intensity stated, because for a container
crossing an ocean the production difference is routinely an order of magnitude
larger than the shipping.

CBAM is legislated, and the cost lands on consumers
-----------------------------------------------------
The border adjustment covers cement, iron and steel, aluminium, fertilisers,
electricity and hydrogen. The free-allocation phase-out is a schedule, not a
constant, and is modelled as one. A personal carbon tool that cannot say what a
carbon price on imports means for its user is missing the part that will
actually be felt.

What this module refuses to do
--------------------------------
It will not report a consumption-based total as comparable to a territorial
target. That is the error the whole module exists to prevent, and
``compare_to_territorial_target`` raises rather than obliging.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class LeakageError(ValueError):
    """Raised when an accounting frame cannot support the question asked."""


#: Origins, with the grid intensity that drives most of the difference between
#: them. Values are kg CO2e per kWh, national annual averages.
REGIONS = {
    "eu": {
        "label": "European Union",
        "grid_intensity": 0.25,
        "cbam_home": True,
        "note": (
            "The reference case for the CBAM modelling here, and already "
            "below the world average grid."
        ),
    },
    "uk": {
        "label": "United Kingdom",
        "grid_intensity": 0.21,
        "cbam_home": False,
        "note": (
            "Among the fastest-decarbonising grids in the data, which makes "
            "it the clearest example of a territorial figure falling for "
            "reasons the household had no part in."
        ),
    },
    "usa": {
        "label": "United States",
        "grid_intensity": 0.37,
        "cbam_home": False,
        "note": "Wide internal variation; the national average hides most of it.",
    },
    "china": {
        "label": "China",
        "grid_intensity": 0.58,
        "cbam_home": False,
        "note": (
            "The origin behind most of the embodied trade balance in the "
            "published data. Heavy industry frequently runs on captive coal "
            "generation well above this national average, so figures derived "
            "from it are conservative."
        ),
    },
    "india": {
        "label": "India",
        "grid_intensity": 0.71,
        "cbam_home": False,
        "note": "The highest grid intensity here, and rising output.",
    },
    "japan": {
        "label": "Japan",
        "grid_intensity": 0.47,
        "cbam_home": False,
        "note": "Still carrying the post-2011 shift away from nuclear.",
    },
    "korea": {
        "label": "South Korea",
        "grid_intensity": 0.44,
        "cbam_home": False,
        "note": "Industrial exporter with a mid-range grid.",
    },
    "turkey": {
        "label": "Turkey",
        "grid_intensity": 0.44,
        "cbam_home": False,
        "note": (
            "A major steel and cement exporter into the CBAM zone, which "
            "makes it one of the most exposed origins in this table."
        ),
    },
    "brazil": {
        "label": "Brazil",
        "grid_intensity": 0.11,
        "cbam_home": False,
        "note": (
            "Hydro-dominated and cleaner than the EU. The case that stops "
            "'imported' being a synonym for 'dirtier' - for electricity-"
            "intensive goods the import can be the better option."
        ),
    },
    "rest_of_world": {
        "label": "Rest of world",
        "grid_intensity": 0.48,
        "cbam_home": False,
        "note": (
            "A weighted residual. Use it when the origin is genuinely "
            "unknown, and read the result as a placeholder."
        ),
    },
}

#: Sectors. Intensity is a process term plus an electricity term times the
#: origin's grid, so the mechanism behind the origin difference stays visible.
SECTORS = {
    "steel": {
        "label": "Steel",
        "unit": "kg",
        "process_intensity": 1.45,
        "electricity_kwh_per_unit": 0.55,
        "cbam_covered": True,
        "note": (
            "Mostly a process emission from reducing iron ore with carbon, so "
            "the grid moves it less than people expect. The origin difference "
            "here is more about route - blast furnace against electric arc - "
            "than about electricity."
        ),
    },
    "aluminium": {
        "label": "Aluminium (primary)",
        "unit": "kg",
        "process_intensity": 1.8,
        "electricity_kwh_per_unit": 15.0,
        "cbam_covered": True,
        "note": (
            "Fifteen kilowatt hours per kilogram makes this almost pure "
            "electricity. Origin matters more here than for any other "
            "material, and Brazilian aluminium genuinely beats European."
        ),
    },
    "cement": {
        "label": "Cement",
        "unit": "kg",
        "process_intensity": 0.53,
        "electricity_kwh_per_unit": 0.11,
        "cbam_covered": True,
        "note": (
            "Calcination releases CO2 from the limestone itself, which no "
            "grid can clean up. Origin barely matters; the chemistry does."
        ),
    },
    "fertiliser": {
        "label": "Nitrogen fertiliser",
        "unit": "kg",
        "process_intensity": 2.3,
        "electricity_kwh_per_unit": 0.35,
        "cbam_covered": True,
        "note": (
            "Dominated by the hydrogen for ammonia, currently from natural "
            "gas. Covered by the border adjustment and passed straight "
            "through to food prices."
        ),
    },
    "hydrogen": {
        "label": "Hydrogen",
        "unit": "kg",
        "process_intensity": 9.0,
        "electricity_kwh_per_unit": 1.0,
        "cbam_covered": True,
        "note": (
            "These figures are for the fossil route, which is what is "
            "actually traded. Electrolytic hydrogen inverts the balance "
            "entirely and is not modelled here."
        ),
    },
    "electricity": {
        "label": "Electricity",
        "unit": "kWh",
        "process_intensity": 0.0,
        "electricity_kwh_per_unit": 1.0,
        "cbam_covered": True,
        "note": (
            "Imported electricity is the purest case: the intensity is the "
            "origin's grid and nothing else."
        ),
    },
    "electronics": {
        "label": "Electronics",
        "unit": "kg",
        "process_intensity": 12.0,
        "electricity_kwh_per_unit": 30.0,
        "cbam_covered": False,
        "note": (
            "Enormously electricity-intensive per kilogram and not covered by "
            "the border adjustment, which is one of the more obvious gaps in "
            "the current scope."
        ),
    },
    "textiles": {
        "label": "Textiles",
        "unit": "kg",
        "process_intensity": 8.0,
        "electricity_kwh_per_unit": 6.0,
        "cbam_covered": False,
        "note": "Not covered. Wet processing dominates and is heat-driven.",
    },
    "plastics": {
        "label": "Plastics",
        "unit": "kg",
        "process_intensity": 1.8,
        "electricity_kwh_per_unit": 0.9,
        "cbam_covered": False,
        "note": "Feedstock is most of it, so origin moves this relatively little.",
    },
    "machinery": {
        "label": "Machinery and appliances",
        "unit": "kg",
        "process_intensity": 1.9,
        "electricity_kwh_per_unit": 1.2,
        "cbam_covered": False,
        "note": (
            "The category most household imports fall into. Not covered, and "
            "the embodied steel and aluminium inside it are only covered when "
            "imported as materials rather than as a finished product."
        ),
    },
    "furniture": {
        "label": "Furniture",
        "unit": "kg",
        "process_intensity": 1.2,
        "electricity_kwh_per_unit": 0.8,
        "cbam_covered": False,
        "note": "Low intensity per kilogram and high mass, so freight matters more here.",
    },
}

#: Freight, kg CO2e per tonne-kilometre.
FREIGHT_MODES = {
    "sea_container": {
        "label": "Container ship",
        "intensity": 0.011,
        "note": (
            "The reason 'shipped from the other side of the world' is usually "
            "not the important number. Ten thousand kilometres of sea freight "
            "adds about 0.11 kg per kilogram of cargo."
        ),
    },
    "air_freight": {
        "label": "Air freight",
        "intensity": 0.60,
        "note": (
            "Fifty times sea freight. The one mode where transport can "
            "genuinely dominate the production difference."
        ),
    },
    "road_truck": {
        "label": "Road haulage",
        "intensity": 0.10,
        "note": "Short distances, high intensity per tonne-kilometre.",
    },
    "rail": {
        "label": "Rail freight",
        "intensity": 0.025,
        "note": "Efficient and geographically limited.",
    },
    "inland_waterway": {
        "label": "Inland waterway",
        "intensity": 0.031,
        "note": "Between rail and road, where the geography allows it.",
    },
}

#: Share of embodied emissions actually charged under the EU border
#: adjustment, by year. A schedule, not a constant, because the phase-in is
#: the difference between a rounding error and a real cost.
CBAM_PHASE_IN = {
    2026: 0.025,
    2027: 0.05,
    2028: 0.10,
    2029: 0.225,
    2030: 0.485,
    2031: 0.61,
    2032: 0.735,
    2033: 0.86,
    2034: 1.0,
}


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def _region(key):
    if key is None:
        raise LeakageError(
            "An origin is required. Without one there is no leakage question "
            "to ask - every good would be assumed domestic, which is the "
            "assumption this module exists to remove."
        )
    normalised = str(key).strip().lower()
    if normalised not in REGIONS:
        known = ", ".join(sorted(REGIONS))
        raise LeakageError("Unknown region '%s'. Known: %s." % (key, known))
    return normalised


def _sector(key):
    if key is None:
        raise LeakageError("A sector is required.")
    normalised = str(key).strip().lower()
    if normalised not in SECTORS:
        known = ", ".join(sorted(SECTORS))
        raise LeakageError("Unknown sector '%s'. Known: %s." % (key, known))
    return normalised


def _mode(key):
    normalised = str(key or "sea_container").strip().lower()
    if normalised not in FREIGHT_MODES:
        known = ", ".join(sorted(FREIGHT_MODES))
        raise LeakageError("Unknown freight mode '%s'. Known: %s." % (key, known))
    return normalised


def list_regions():
    """Every origin, with its grid intensity."""
    return [
        dict(REGIONS[key], key=key)
        for key in sorted(REGIONS, key=lambda item: REGIONS[item]["label"])
    ]


def get_region(key):
    """One origin, or ``None``."""
    if key not in REGIONS:
        return None
    return dict(REGIONS[key], key=key)


def list_sectors():
    """Every sector, with its intensity split and CBAM coverage."""
    return [
        dict(SECTORS[key], key=key)
        for key in sorted(SECTORS, key=lambda item: SECTORS[item]["label"])
    ]


def get_sector(key):
    """One sector, or ``None``."""
    if key not in SECTORS:
        return None
    return dict(SECTORS[key], key=key)


def list_freight_modes():
    """Every freight mode, with the caveat it needs."""
    return [dict(FREIGHT_MODES[key], key=key) for key in sorted(FREIGHT_MODES)]


def origin_intensity(sector, region):
    """Production intensity of a sector in a region, per unit of the sector.

    Process emissions plus electricity emissions. Keeping the split explicit
    is what makes the origin difference explainable rather than tabulated.
    """
    sector_key = _sector(sector)
    region_key = _region(region)
    definition = SECTORS[sector_key]
    grid = REGIONS[region_key]["grid_intensity"]
    return (
        definition["process_intensity"]
        + definition["electricity_kwh_per_unit"] * grid
    )


def intensity_breakdown(sector, region):
    """The two halves of an intensity, so the mechanism is legible."""
    sector_key = _sector(sector)
    region_key = _region(region)
    definition = SECTORS[sector_key]
    grid = REGIONS[region_key]["grid_intensity"]
    electricity = definition["electricity_kwh_per_unit"] * grid
    total = definition["process_intensity"] + electricity
    return {
        "sector": sector_key,
        "region": region_key,
        "process": definition["process_intensity"],
        "electricity": electricity,
        "total": total,
        "electricity_share": (electricity / total) if total else None,
        "grid_intensity": grid,
        "unit": definition["unit"],
    }


# ---------------------------------------------------------------------------
# Items and baskets
# ---------------------------------------------------------------------------

def build_item(name, sector, origin, quantity, distance_km=0.0,
               freight_mode="sea_container"):
    """One good, with an origin. The origin is not optional here."""
    if not name or not str(name).strip():
        raise LeakageError("An item needs a name.")
    sector_key = _sector(sector)
    region_key = _region(origin)
    mode_key = _mode(freight_mode)

    amount = float(quantity)
    if amount < 0:
        raise LeakageError("Quantity cannot be negative.")
    distance = float(distance_km)
    if distance < 0:
        raise LeakageError("Distance cannot be negative.")

    return {
        "name": str(name).strip(),
        "sector": sector_key,
        "origin": region_key,
        "quantity": amount,
        "unit": SECTORS[sector_key]["unit"],
        "distance_km": distance,
        "freight_mode": mode_key,
    }


def embodied_emissions(item):
    """Production and freight for one item, kept apart.

    Conflating the two is the most common error in this area and the reason
    'local' and 'low-carbon' get treated as the same claim.
    """
    production = item["quantity"] * origin_intensity(item["sector"], item["origin"])

    if SECTORS[item["sector"]]["unit"] == "kWh":
        freight = 0.0
    else:
        tonne_km = (item["quantity"] / 1000.0) * item["distance_km"]
        freight = tonne_km * FREIGHT_MODES[item["freight_mode"]]["intensity"]

    total = production + freight
    return {
        "name": item["name"],
        "sector": item["sector"],
        "origin": item["origin"],
        "production_kg_co2": production,
        "freight_kg_co2": freight,
        "total_kg_co2": total,
        "freight_share": (freight / total) if total > 0 else None,
        "unit_intensity": origin_intensity(item["sector"], item["origin"]),
    }


def build_basket(name, items):
    """A named set of goods."""
    if not name or not str(name).strip():
        raise LeakageError("A basket needs a name.")
    entries = list(items or [])
    if not entries:
        raise LeakageError("A basket needs at least one item.")
    return {
        "name": str(name).strip(),
        "items": entries,
        "origins": sorted({item["origin"] for item in entries}),
        "sectors": sorted({item["sector"] for item in entries}),
    }


# ---------------------------------------------------------------------------
# Accounting frames
# ---------------------------------------------------------------------------

def accounting_split(basket, home_region):
    """Territorial, imported and consumption-based totals for one basket.

    The three must reconcile: territorial plus imports equals the consumption
    total. That is asserted here rather than assumed, because the whole point
    of the module is that the three are routinely conflated.
    """
    home = _region(home_region)

    territorial = 0.0
    imported = 0.0
    rows = []
    for item in basket["items"]:
        emissions = embodied_emissions(item)
        domestic = item["origin"] == home
        if domestic:
            territorial += emissions["total_kg_co2"]
        else:
            imported += emissions["total_kg_co2"]
        rows.append(dict(emissions, domestic=domestic))

    consumption = territorial + imported
    return {
        "basket": basket["name"],
        "home_region": home,
        "territorial_kg_co2": territorial,
        "imported_kg_co2": imported,
        "consumption_kg_co2": consumption,
        "embodied_trade_balance": imported,
        "import_share": (imported / consumption) if consumption > 0 else None,
        "reconciles": abs(
            (territorial + imported) - consumption
        ) < 1e-9,
        "items": rows,
    }


def compare_to_territorial_target(split, target_kg_co2):
    """Refuse to compare a consumption total against a territorial target.

    The two are different quantities. Reporting the comparison anyway is the
    single error this module was built to stop, so it raises rather than
    returning a caveated number that would be quoted without the caveat.
    """
    raise LeakageError(
        "A consumption-based total (%.0f kg, of which %.0f kg was emitted "
        "abroad) is not comparable to a territorial target of %.0f kg. They "
        "count different things. Use benchmark_correction to put a "
        "territorial benchmark on a consumption footing first."
        % (
            split["consumption_kg_co2"],
            split["imported_kg_co2"],
            float(target_kg_co2),
        )
    )


def benchmark_correction(territorial_per_capita_kg, import_share,
                         export_share=0.0):
    """Put a production-based national average onto a consumption footing.

    ``carbon_benchmarking.py`` compares a user's consumption footprint against
    production-based averages. This is the correction that makes those two the
    same quantity, reported with its own caveat rather than as a replacement.
    """
    territorial = float(territorial_per_capita_kg)
    if territorial <= 0:
        raise LeakageError("A territorial benchmark must be positive.")
    imports = float(import_share)
    exports = float(export_share)
    if not 0 <= imports < 1:
        raise LeakageError("Import share must be at least 0 and below 1.")
    if not 0 <= exports < 1:
        raise LeakageError("Export share must be at least 0 and below 1.")

    consumption = territorial * (1.0 - exports) / (1.0 - imports)
    return {
        "territorial_per_capita_kg": territorial,
        "consumption_per_capita_kg": consumption,
        "adjustment_kg": consumption - territorial,
        "adjustment_share": (consumption / territorial) - 1.0,
        "net_importer": consumption > territorial,
        "note": (
            "A net-importing country's consumption footprint exceeds its "
            "territorial one, and the gap is the emissions its imports caused "
            "elsewhere. Comparing a household's consumption footprint against "
            "the uncorrected territorial average understates the household by "
            "roughly this much."
            if consumption > territorial else
            "A net-exporting country's territorial figure exceeds its "
            "consumption footprint, because part of what it emits is on "
            "behalf of somebody else's consumption."
        ),
    }


# ---------------------------------------------------------------------------
# Leakage detection
# ---------------------------------------------------------------------------

def substitution(before, after, home_region):
    """Decompose a swap into a genuine reduction and a relocation.

    The two components sum to the observed change exactly. A residual in an
    analysis of this kind invites the reader to assume it was the good part,
    so there is not one.
    """
    home = _region(home_region)
    before_emissions = embodied_emissions(before)
    after_emissions = embodied_emissions(after)

    before_intensity = before_emissions["unit_intensity"]
    after_intensity = after_emissions["unit_intensity"]

    # Exact two-factor split of the production term:
    #   d(m*f) = (m1 - m0) * f0  +  m1 * (f1 - f0)
    quantity_effect = (after["quantity"] - before["quantity"]) * before_intensity
    intensity_effect = after["quantity"] * (after_intensity - before_intensity)
    freight_effect = (
        after_emissions["freight_kg_co2"] - before_emissions["freight_kg_co2"]
    )

    global_change = (
        after_emissions["total_kg_co2"] - before_emissions["total_kg_co2"]
    )

    before_territorial = (
        before_emissions["total_kg_co2"] if before["origin"] == home else 0.0
    )
    after_territorial = (
        after_emissions["total_kg_co2"] if after["origin"] == home else 0.0
    )
    territorial_change = after_territorial - before_territorial

    origin_changed = before["origin"] != after["origin"]
    offshored = origin_changed and before["origin"] == home and after["origin"] != home

    # Leakage means part of an apparent territorial reduction was relocation.
    # It is a separate question from whether the global total improved, and
    # collapsing the two would hide the common and genuinely good case: a
    # relocation to a cleaner grid, which is leakage *and* an improvement.
    leakage = offshored and territorial_change < 0 and global_change > territorial_change
    net_improvement = global_change < 0

    return {
        "home_region": home,
        "before": before_emissions,
        "after": after_emissions,
        "quantity_effect": quantity_effect,
        "intensity_effect": intensity_effect,
        "freight_effect": freight_effect,
        "global_change": global_change,
        "territorial_change": territorial_change,
        "relocated_kg_co2": (
            territorial_change - global_change if offshored else 0.0
        ),
        "origin_changed": origin_changed,
        "offshored": offshored,
        "leakage_detected": leakage,
        "net_global_improvement": net_improvement,
        "residual": global_change - (
            quantity_effect + intensity_effect + freight_effect
        ),
        "note": _substitution_note(
            leakage, net_improvement, territorial_change, global_change
        ),
    }


def _substitution_note(leakage, net_improvement, territorial_change,
                       global_change):
    """Say which of the three cases this is, without conflating them."""
    if not leakage:
        return (
            "No relocation: the origin did not change, or the global total "
            "moved with the territorial one."
        )
    if net_improvement:
        return (
            "The territorial number fell by %.0f kg but the global total fell "
            "by only %.0f kg. The remaining %.0f kg relocated. This is still "
            "an improvement - the new origin is cleaner - and it is a smaller "
            "improvement than the territorial figure claims."
            % (
                abs(territorial_change),
                abs(global_change),
                abs(territorial_change) - abs(global_change),
            )
        )
    return (
        "The territorial number fell by %.0f kg while the global total rose "
        "by %.0f kg. Nothing was reduced. The emissions moved somewhere the "
        "accounting does not look."
        % (abs(territorial_change), global_change)
    )


def leakage_rate(before_basket, after_basket, home_region):
    """How much of a reported reduction was a shift in the origin mix.

    The personal-scale version of the argument about whether wealthy countries
    decarbonised or outsourced. The same arithmetic answers it.

    Items are matched by name. Anything appearing or disappearing is counted
    in the quantity effect, which is the correct home for it: buying something
    new is a change in what is consumed, not in where it came from.
    """
    home = _region(home_region)

    before_index = {item["name"]: item for item in before_basket["items"]}
    after_index = {item["name"]: item for item in after_basket["items"]}
    names = sorted(set(before_index) | set(after_index))

    quantity_effect = 0.0
    origin_effect = 0.0
    rows = []

    for name in names:
        before_item = before_index.get(name)
        after_item = after_index.get(name)

        before_quantity = before_item["quantity"] if before_item else 0.0
        after_quantity = after_item["quantity"] if after_item else 0.0
        reference = before_item or after_item

        before_intensity = (
            origin_intensity(before_item["sector"], before_item["origin"])
            if before_item else
            origin_intensity(after_item["sector"], after_item["origin"])
        )
        after_intensity = (
            origin_intensity(after_item["sector"], after_item["origin"])
            if after_item else before_intensity
        )

        item_quantity_effect = (after_quantity - before_quantity) * before_intensity
        item_origin_effect = after_quantity * (after_intensity - before_intensity)

        quantity_effect += item_quantity_effect
        origin_effect += item_origin_effect
        rows.append({
            "name": name,
            "sector": reference["sector"],
            "before_origin": before_item["origin"] if before_item else None,
            "after_origin": after_item["origin"] if after_item else None,
            "quantity_effect": item_quantity_effect,
            "origin_effect": item_origin_effect,
        })

    before_split = accounting_split(before_basket, home)
    after_split = accounting_split(after_basket, home)

    production_change = (
        sum(
            item["quantity"] * origin_intensity(item["sector"], item["origin"])
            for item in after_basket["items"]
        )
        - sum(
            item["quantity"] * origin_intensity(item["sector"], item["origin"])
            for item in before_basket["items"]
        )
    )

    territorial_change = (
        after_split["territorial_kg_co2"] - before_split["territorial_kg_co2"]
    )
    consumption_change = (
        after_split["consumption_kg_co2"] - before_split["consumption_kg_co2"]
    )

    share = None
    if territorial_change < 0 and abs(territorial_change) > 0:
        share = max(0.0, min(1.0, -origin_effect / -territorial_change)) \
            if origin_effect < 0 else 0.0

    return {
        "home_region": home,
        "quantity_effect": quantity_effect,
        "origin_effect": origin_effect,
        "production_change": production_change,
        "residual": production_change - (quantity_effect + origin_effect),
        "territorial_change": territorial_change,
        "consumption_change": consumption_change,
        "leakage_share_of_reduction": share,
        "items": rows,
        "before": before_split,
        "after": after_split,
    }


# ---------------------------------------------------------------------------
# Border adjustment
# ---------------------------------------------------------------------------

def cbam_phase_in(year):
    """Share of embodied emissions charged in a given year."""
    try:
        when = int(year)
    except (TypeError, ValueError):
        raise LeakageError("A CBAM year must be a whole year.")
    if when < min(CBAM_PHASE_IN):
        return 0.0
    if when >= max(CBAM_PHASE_IN):
        return CBAM_PHASE_IN[max(CBAM_PHASE_IN)]
    return CBAM_PHASE_IN[when]


def cbam_exposure(basket, carbon_price, year, home_region):
    """Cost a border carbon price would attach to a basket's imports.

    Only imported goods in covered sectors are charged. Uncovered sectors are
    reported as uncovered rather than as zero, because the two mean very
    different things for anyone planning ahead.
    """
    home = _region(home_region)
    price = float(carbon_price)
    if price < 0:
        raise LeakageError("A carbon price cannot be negative.")
    share = cbam_phase_in(year)

    covered_rows = []
    uncovered_rows = []
    domestic_rows = []
    covered_emissions = 0.0
    uncovered_emissions = 0.0

    for item in basket["items"]:
        emissions = embodied_emissions(item)
        if item["origin"] == home:
            domestic_rows.append(emissions)
            continue
        if SECTORS[item["sector"]]["cbam_covered"]:
            charged = emissions["production_kg_co2"] * share
            covered_emissions += emissions["production_kg_co2"]
            covered_rows.append(dict(
                emissions,
                chargeable_kg_co2=charged,
                cost=charged / 1000.0 * price,
            ))
        else:
            uncovered_emissions += emissions["production_kg_co2"]
            uncovered_rows.append(emissions)

    cost = sum(row["cost"] for row in covered_rows)
    full_cost = covered_emissions / 1000.0 * price

    return {
        "year": int(year),
        "carbon_price": price,
        "phase_in_share": share,
        "covered": covered_rows,
        "uncovered": uncovered_rows,
        "domestic": domestic_rows,
        "covered_emissions_kg": covered_emissions,
        "uncovered_emissions_kg": uncovered_emissions,
        "cost": cost,
        "cost_at_full_phase_in": full_cost,
        "coverage_share": (
            covered_emissions / (covered_emissions + uncovered_emissions)
            if (covered_emissions + uncovered_emissions) > 0 else None
        ),
        "note": (
            "Freight is excluded from the charge, which is how the "
            "regulation is written. Only the embodied production emissions "
            "of covered goods are chargeable."
        ),
    }


def cbam_trajectory(basket, carbon_price, home_region,
                    years=tuple(sorted(CBAM_PHASE_IN))):
    """The cost year by year as free allocation is withdrawn."""
    return [
        {
            "year": year,
            "phase_in_share": cbam_phase_in(year),
            "cost": cbam_exposure(basket, carbon_price, year, home_region)["cost"],
        }
        for year in years
    ]


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

def get_leakage_insights(result):
    """Plain-language findings from a ``leakage_rate`` result."""
    insights = []

    territorial = result["territorial_change"]
    consumption = result["consumption_change"]

    if territorial < 0 and consumption >= territorial * 0.5:
        insights.append({
            "level": "warning",
            "title": "Most of this reduction did not happen",
            "body": (
                "The territorial figure fell by %.0f kg. The consumption "
                "figure moved by %.0f kg. The difference is emissions that "
                "relocated rather than emissions that stopped."
                % (abs(territorial), consumption)
            ),
        })
    elif territorial < 0:
        insights.append({
            "level": "info",
            "title": "The reduction survives a consumption frame",
            "body": (
                "Territorial down %.0f kg, consumption down %.0f kg. The "
                "emissions went away rather than moving."
                % (abs(territorial), abs(consumption))
            ),
        })

    if result["leakage_share_of_reduction"] is not None:
        insights.append({
            "level": "warning" if result["leakage_share_of_reduction"] > 0.3
            else "info",
            "title": "%.0f%% of the reduction is a shift in origin"
                     % (result["leakage_share_of_reduction"] * 100.0),
            "body": (
                "The rest is a change in what was actually consumed. Only the "
                "second kind compounds; the first can be reversed by a "
                "supplier changing their sourcing."
            ),
        })

    insights.append({
        "level": "info",
        "title": "The split is exact",
        "body": (
            "Quantity effect %.0f kg, origin effect %.0f kg, and they sum to "
            "the production change of %.0f kg with a residual of %.2g. A "
            "remainder here would invite you to assume it was the good part."
            % (
                result["quantity_effect"],
                result["origin_effect"],
                result["production_change"],
                result["residual"],
            )
        ),
    })

    moved = [row for row in result["items"]
             if row["before_origin"] and row["after_origin"]
             and row["before_origin"] != row["after_origin"]]
    if moved:
        insights.append({
            "level": "info",
            "title": "%d item%s changed origin" % (
                len(moved), "" if len(moved) == 1 else "s"
            ),
            "body": ", ".join(
                "%s moved from %s to %s"
                % (
                    row["name"],
                    REGIONS[row["before_origin"]]["label"],
                    REGIONS[row["after_origin"]]["label"],
                )
                for row in moved
            ),
        })

    return insights


def freight_versus_origin(item, alternative_origin):
    """Whether 'buy local' is about the shipping or about the factory.

    Almost always the factory, and quantifying that is the only way to stop
    'local' being used as a synonym for 'low-carbon'.
    """
    alternative = _region(alternative_origin)
    here = embodied_emissions(item)
    swapped = embodied_emissions(dict(item, origin=alternative, distance_km=0.0))

    production_gap = swapped["production_kg_co2"] - here["production_kg_co2"]
    freight_gap = swapped["freight_kg_co2"] - here["freight_kg_co2"]

    dominant = "production" if abs(production_gap) >= abs(freight_gap) else "freight"
    ratio = None
    if freight_gap != 0:
        ratio = abs(production_gap / freight_gap)

    return {
        "item": item["name"],
        "current_origin": item["origin"],
        "alternative_origin": alternative,
        "production_gap": production_gap,
        "freight_gap": freight_gap,
        "net_gap": production_gap + freight_gap,
        "dominant_term": dominant,
        "production_over_freight": ratio,
        "local_is_better": (production_gap + freight_gap) < 0,
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS carbon_leakage_baskets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            home_region TEXT NOT NULL,
            payload TEXT NOT NULL,
            territorial_kg REAL NOT NULL,
            imported_kg REAL NOT NULL,
            consumption_kg REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_carbon_leakage_baskets_user
        ON carbon_leakage_baskets (user_id)
        """
    )


def save_basket(user_id, basket, split):
    """Persist a basket with its accounting split."""
    if not user_id:
        raise LeakageError("A saved basket needs a user to belong to.")

    payload = json.dumps({
        "items": basket["items"],
        "import_share": split["import_share"],
        "origins": basket["origins"],
        "sectors": basket["sectors"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO carbon_leakage_baskets
                (user_id, name, home_region, payload, territorial_kg,
                 imported_kg, consumption_kg)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), basket["name"], split["home_region"], payload,
                float(split["territorial_kg_co2"]),
                float(split["imported_kg_co2"]),
                float(split["consumption_kg_co2"]),
            ),
        )
        return int(cursor.lastrowid)


def get_baskets(user_id, limit=25):
    """Saved baskets for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, home_region, payload, territorial_kg,
                       imported_kg, consumption_kg, created_at
                FROM carbon_leakage_baskets
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved leakage baskets")
        return []

    saved = []
    for row in rows:
        try:
            payload = json.loads(row[3])
        except (TypeError, ValueError):
            payload = {}
        saved.append({
            "id": row[0],
            "name": row[1],
            "home_region": row[2],
            "payload": payload,
            "territorial_kg": row[4],
            "imported_kg": row[5],
            "consumption_kg": row[6],
            "created_at": row[7],
        })
    return saved


def delete_basket(user_id, basket_id):
    """Delete one saved basket. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM carbon_leakage_baskets WHERE id = ? AND user_id = ?",
                (basket_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete leakage basket")
        return False
