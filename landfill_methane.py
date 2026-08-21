"""Landfill methane by first order decay, and what diverting waste actually buys.

``waste.py`` estimates landfill methane with one constant::

    LANDFILL_METHANE_FACTOR = 0.5
    landfill_methane = biodegradable_kg * LANDFILL_METHANE_FACTOR

Every kind of biodegradable waste gets the same coefficient, all of it is
emitted in the year the bin went out, and the site is assumed to have no gas
capture. All three are wrong, and they are wrong in different directions.

Waste does not decay on a schedule the calendar year understands
----------------------------------------------------------------
Buried organic matter degrades exponentially, with a half-life from a few years
to several decades depending on what it is and how wet the site is. Food waste
in a wet climate is largely gone within five years; timber is still emitting at
thirty. Booking the whole emission at disposal puts methane in a year it was not
emitted in and takes it out of the twenty years it was.

For a *stable* waste stream the annual total comes out similar, which is exactly
why the error survives. It bites the moment behaviour changes: the flat model
reports the full benefit of composting immediately, when the real benefit
arrives over decades because the site is still emitting last decade's waste.
Promising an instant benefit for an action whose benefit is slow is the specific
failure that makes waste advice untrustworthy, and it is the reason for the
decay model rather than a better constant.

Not all biodegradable waste is equally degradable
--------------------------------------------------
Degradable organic carbon differs by a factor of four across streams, and the
fraction that actually dissimilates differs again. Lignin-bound carbon in timber
and woody garden waste substantially never decomposes on any timescale, which is
genuine permanent sequestration - and a single coefficient cannot express it.

Gas capture is the largest lever and is absent entirely
-------------------------------------------------------
A modern engineered site captures 60-85% of what it generates; of what escapes,
a further tenth or so oxidises crossing the cover soil. Across the site
archetypes here that is a factor of three on identical waste, and against a site
running best-practice capture it is nearly seven - and none of it is a property
of the waste at all. It is a property of where the waste went, which the current
model has no way to express.

Comparing routes needs the avoided burden stated, not netted
-------------------------------------------------------------
Digestion produces biogas that displaces something; incineration produces heat
that displaces something; compost displaces synthetic fertiliser. Leave the
credit out and every route with an output looks worse than it is. Net it into a
single number and a grid intensity assumption ends up buried inside a waste
figure where nobody will find it. Here it is always reported separately.

Biogenic CO2 is tracked apart from the methane. The CO2 from short-cycle biomass
is not a warming contribution; the methane from the same carbon absolutely is,
and confusing the two is the commonest error in waste footprinting.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import math
import sqlite3
import logging
from typing import Any

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

# Fraction of landfill gas that is methane by volume; the rest is mostly CO2,
# which is biogenic and therefore not counted as a warming contribution.
METHANE_FRACTION = 0.5

# Molecular weight ratio CH4/C. Carbon that decomposes anaerobically leaves as
# methane heavier than the carbon it came from.
CH4_C_RATIO = 16.0 / 12.0

# Methane is biogenic here - it came from this year's biomass, not from fossil
# carbon - so the biogenic GWP is the right one. It is a little below the fossil
# value because the CO2 the methane oxidises into was already in the cycle.
METHANE_GWP_100 = 27.0
METHANE_GWP_20 = 79.7

# The IPCC model starts generation part way through the year following disposal.
# Waste tipped in December is not generating in December.
DEFAULT_DELAY_MONTHS = 6.0

DEFAULT_HORIZON_YEARS = 100
DEFAULT_CLIMATE = "wet_temperate"
DEFAULT_SITE = "managed_capture"


class LandfillError(ValueError):
    """Raised when a waste profile or site cannot be evaluated as given."""


# ---------------------------------------------------------------------------
# Waste streams
#
# ``doc`` is degradable organic carbon as a fraction of wet weight - the reason
# one coefficient across all of these cannot work, since it spans a factor of
# four before anything else is considered.
#
# ``docf`` is the fraction of that carbon which actually dissimilates. Timber is
# low because its carbon is lignin-bound and does not decompose on any
# timescale, which is real and permanent sequestration rather than a modelling
# convenience.
# ---------------------------------------------------------------------------

WASTE_STREAMS: dict[str, dict[str, Any]] = {
    "food": {
        "label": "Food waste",
        "doc": 0.15, "docf": 0.70, "moisture": 0.70,
        "note": "Wet, fast, and the largest avoidable fraction of a household bin.",
    },
    "garden": {
        "label": "Garden and green waste",
        "doc": 0.20, "docf": 0.45, "moisture": 0.55,
        "note": "Part woody, so a meaningful share of its carbon never breaks down.",
    },
    "paper": {
        "label": "Paper",
        "doc": 0.40, "docf": 0.50, "moisture": 0.10,
        "note": "High carbon, slow decay - still emitting decades later.",
    },
    "cardboard": {
        "label": "Cardboard",
        "doc": 0.40, "docf": 0.50, "moisture": 0.12,
        "note": "As paper, and the bulkiest thing most households throw away.",
    },
    "textiles": {
        "label": "Textiles",
        "doc": 0.24, "docf": 0.50, "moisture": 0.10,
        "note": "Only the natural fibres degrade; synthetics contribute nothing.",
    },
    "nappies": {
        "label": "Nappies and sanitary waste",
        "doc": 0.24, "docf": 0.60, "moisture": 0.40,
        "note": "Pulp and moisture together, so it degrades faster than paper.",
    },
    "timber": {
        "label": "Timber and wood",
        "doc": 0.43, "docf": 0.15, "moisture": 0.20,
        "note": "The most carbon per tonne and the least of it available. Most "
                "of the carbon stays buried, which is a genuine store.",
    },
}


# ---------------------------------------------------------------------------
# Decay constants
#
# k in reciprocal years, by climate zone and stream. Wet and warm decomposes
# fast; dry and cold does not. These differ by a factor of six or more within a
# single stream, which is why the zone is a parameter rather than a default.
# ---------------------------------------------------------------------------

CLIMATE_ZONES: dict[str, dict[str, Any]] = {
    "dry_temperate": {
        "label": "Dry temperate",
        "k": {"food": 0.06, "garden": 0.05, "paper": 0.04, "cardboard": 0.04,
              "textiles": 0.04, "nappies": 0.06, "timber": 0.02},
    },
    "wet_temperate": {
        "label": "Wet temperate",
        "k": {"food": 0.185, "garden": 0.10, "paper": 0.06, "cardboard": 0.06,
              "textiles": 0.06, "nappies": 0.10, "timber": 0.03},
    },
    "dry_tropical": {
        "label": "Dry tropical",
        "k": {"food": 0.085, "garden": 0.065, "paper": 0.045, "cardboard": 0.045,
              "textiles": 0.045, "nappies": 0.085, "timber": 0.025},
    },
    "wet_tropical": {
        "label": "Wet tropical",
        "k": {"food": 0.40, "garden": 0.17, "paper": 0.07, "cardboard": 0.07,
              "textiles": 0.07, "nappies": 0.17, "timber": 0.035},
    },
}


# ---------------------------------------------------------------------------
# Sites
#
# ``mcf`` is how anaerobic the site is - a shallow unmanaged dump lets air in and
# generates far less methane per tonne of carbon. ``capture`` and ``oxidation``
# then decide how much of what is generated actually reaches the atmosphere.
#
# Between the best and worst row here is a factor of three on identical waste,
# and a site at 85% capture rather than 68% widens it to nearly seven. That is
# the single largest determinant of the answer, and it is invisible to a model
# that has only the waste to work with.
# ---------------------------------------------------------------------------

SITE_ARCHETYPES: dict[str, dict[str, Any]] = {
    "managed_capture": {
        "label": "Engineered site with gas capture",
        "mcf": 1.0, "capture": 0.68, "oxidation": 0.10,
        "note": "Capped, lined, gas collected and flared or burnt for power.",
    },
    "managed_no_capture": {
        "label": "Managed site, no gas collection",
        "mcf": 1.0, "capture": 0.0, "oxidation": 0.10,
        "note": "Compacted and covered, so fully anaerobic, but nothing collected.",
    },
    "semi_aerobic": {
        "label": "Managed semi-aerobic site",
        "mcf": 0.5, "capture": 0.0, "oxidation": 0.10,
        "note": "Vented so air reaches the waste; generates far less methane.",
    },
    "unmanaged_deep": {
        "label": "Unmanaged dump, deep",
        "mcf": 0.8, "capture": 0.0, "oxidation": 0.0,
        "note": "Over five metres. Anaerobic in the middle, nothing captured.",
    },
    "unmanaged_shallow": {
        "label": "Unmanaged dump, shallow",
        "mcf": 0.4, "capture": 0.0, "oxidation": 0.0,
        "note": "Under five metres. Air penetrates, so much of it aerobic.",
    },
}


# ---------------------------------------------------------------------------
# Treatment routes
#
# ``process_kg_per_tonne`` is the fossil emission of running the process.
# ``avoided_*`` are what the route's output displaces, and they are never netted
# into the process figure - the whole point is that the credit is a claim about
# something outside the waste system and has to be visible as one.
# ---------------------------------------------------------------------------

TREATMENT_ROUTES: dict[str, dict[str, Any]] = {
    "landfill": {
        "label": "Landfill",
        "process_kg_per_tonne": 8.0,
        "avoided_kwh_per_tonne": 0.0,
        "avoided_heat_kwh_per_tonne": 0.0,
        "avoided_fertiliser_kg_per_tonne": 0.0,
        "biogenic_co2_share": 0.5,
        "note": "Modelled by first order decay; everything else here is an "
                "annual figure, and that difference is the point.",
    },
    "compost": {
        "label": "Composting",
        "process_kg_per_tonne": 15.0,
        "avoided_kwh_per_tonne": 0.0,
        "avoided_heat_kwh_per_tonne": 0.0,
        "avoided_fertiliser_kg_per_tonne": 4.5,
        "biogenic_co2_share": 1.0,
        "note": "Aerobic, so the carbon leaves as biogenic CO2 rather than "
                "methane. Small methane and nitrous oxide slip is in the "
                "process figure.",
    },
    "anaerobic_digestion": {
        "label": "Anaerobic digestion",
        "process_kg_per_tonne": 12.0,
        "avoided_kwh_per_tonne": 180.0,
        "avoided_heat_kwh_per_tonne": 120.0,
        "avoided_fertiliser_kg_per_tonne": 3.0,
        "biogenic_co2_share": 1.0,
        "note": "Deliberately anaerobic in a sealed vessel, so the methane is "
                "collected instead of escaping.",
    },
    "incineration": {
        "label": "Incineration with energy recovery",
        "process_kg_per_tonne": 25.0,
        "avoided_kwh_per_tonne": 220.0,
        "avoided_heat_kwh_per_tonne": 350.0,
        "avoided_fertiliser_kg_per_tonne": 0.0,
        "biogenic_co2_share": 1.0,
        "note": "Releases the carbon immediately, all of it, and recovers "
                "energy while doing so.",
    },
}

# kg CO2e avoided per unit of displaced output. All three are assumptions about
# a system outside the waste system, which is why they are parameters.
DEFAULT_GRID_INTENSITY = 0.280
DEFAULT_HEAT_INTENSITY = 0.200
FERTILISER_INTENSITY = 5.5


# ---------------------------------------------------------------------------
# Table access
# ---------------------------------------------------------------------------

def list_streams() -> list[str]:
    """Waste stream keys in table order."""
    return list(WASTE_STREAMS)


def list_climate_zones() -> list[str]:
    """Climate zone keys in table order."""
    return list(CLIMATE_ZONES)


def list_sites() -> list[str]:
    """Site archetype keys in table order."""
    return list(SITE_ARCHETYPES)


def list_routes() -> list[str]:
    """Treatment route keys in table order."""
    return list(TREATMENT_ROUTES)


def get_stream(stream: str) -> dict[str, Any]:
    """One stream's parameters."""
    if stream not in WASTE_STREAMS:
        raise LandfillError(f"Unknown waste stream: {stream}")
    entry = dict(WASTE_STREAMS[stream])
    entry["key"] = stream
    return entry


def get_site(site: str) -> dict[str, Any]:
    """One site archetype's parameters."""
    if site not in SITE_ARCHETYPES:
        raise LandfillError(f"Unknown site type: {site}")
    entry = dict(SITE_ARCHETYPES[site])
    entry["key"] = site
    return entry


def decay_constant(stream: str, climate: str = DEFAULT_CLIMATE) -> float:
    """k, in reciprocal years, for a stream in a climate zone."""
    if stream not in WASTE_STREAMS:
        raise LandfillError(f"Unknown waste stream: {stream}")
    if climate not in CLIMATE_ZONES:
        raise LandfillError(f"Unknown climate zone: {climate}")
    return float(CLIMATE_ZONES[climate]["k"][stream])


def half_life_years(stream: str, climate: str = DEFAULT_CLIMATE) -> float:
    """How long until half the available carbon has gone.

    The number that makes the timing problem concrete: food in a wet temperate
    climate is at four years, timber at twenty-three.
    """
    k = decay_constant(stream, climate)
    if k <= 0:
        raise LandfillError(f"Stream {stream} has no decay in {climate}")
    return math.log(2.0) / k


def methane_potential(stream: str, site: str = DEFAULT_SITE) -> float:
    """L0 - kg of methane generatable per tonne of this waste at this site.

    ``DOC x DOCf x MCF x F x 16/12``. The site's methane correction factor is in
    here because a shallow dump lets air in, and carbon that decomposes
    aerobically produces no methane at all.
    """
    entry = get_stream(stream)
    site_entry = get_site(site)
    return (
        1000.0
        * entry["doc"]
        * entry["docf"]
        * site_entry["mcf"]
        * METHANE_FRACTION
        * CH4_C_RATIO
    )


def sequestered_carbon(stream: str) -> float:
    """kg of carbon per tonne that never decomposes, on any timescale.

    Lignin-bound carbon in timber and woody garden waste is a real store rather
    than a delayed emission, and a model that only reports what comes out cannot
    say so.
    """
    entry = get_stream(stream)
    return 1000.0 * entry["doc"] * (1.0 - entry["docf"])


# ---------------------------------------------------------------------------
# First order decay
# ---------------------------------------------------------------------------

def decay_profile(
    stream: str,
    tonnes: float,
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
    years: int = DEFAULT_HORIZON_YEARS,
    delay_months: float = DEFAULT_DELAY_MONTHS,
) -> list[dict[str, Any]]:
    """Methane generated each year from a single year's disposal.

    The IPCC recursion: carbon deposited decays exponentially, and the amount
    decomposing in a year is what was left at the start of it, times
    ``1 - e^-k``. The shape is the argument - a single number cannot show that
    most of this arrives long after the bin went out.
    """
    if tonnes < 0:
        raise LandfillError("Tonnage cannot be negative")
    if years < 1:
        raise LandfillError("Need at least one year of profile")
    if not 0.0 <= delay_months <= 12.0:
        raise LandfillError("Delay must be between 0 and 12 months")

    k = decay_constant(stream, climate)
    potential = methane_potential(stream, site) * tonnes
    if potential <= 0 or k <= 0:
        return [
            {"year": n, "generated_kg": 0.0, "remaining_kg": 0.0,
             "cumulative_kg": 0.0}
            for n in range(1, years + 1)
        ]

    decay = math.exp(-k)
    delay = delay_months / 12.0

    remaining = potential
    rows: list[dict[str, Any]] = []
    cumulative = 0.0
    for year in range(1, years + 1):
        if year == 1:
            # Part year: generation starts after the delay.
            fraction = 1.0 - math.exp(-k * (1.0 - delay))
        else:
            fraction = 1.0 - decay
        generated = remaining * fraction
        remaining -= generated
        cumulative += generated
        rows.append({
            "year": year,
            "generated_kg": round(generated, 4),
            "remaining_kg": round(remaining, 4),
            "cumulative_kg": round(cumulative, 4),
        })
    return rows


def site_emissions(
    generated_kg: float,
    site: str = DEFAULT_SITE,
    capture: float | None = None,
    oxidation: float | None = None,
) -> dict[str, float]:
    """What actually reaches the atmosphere from what was generated.

    Captured gas first, then oxidation across the cover soil of whatever is
    left. Applying oxidation to the gross would double-count the captured
    portion, which is a common enough mistake to be worth stating.
    """
    entry = get_site(site)
    capture = entry["capture"] if capture is None else float(capture)
    oxidation = entry["oxidation"] if oxidation is None else float(oxidation)
    if not 0.0 <= capture <= 1.0:
        raise LandfillError("Capture efficiency must be a fraction between 0 and 1")
    if not 0.0 <= oxidation <= 1.0:
        raise LandfillError("Oxidation must be a fraction between 0 and 1")

    captured = generated_kg * capture
    escaping = generated_kg - captured
    oxidised = escaping * oxidation
    emitted = escaping - oxidised
    return {
        "generated_kg": round(generated_kg, 4),
        "captured_kg": round(captured, 4),
        "oxidised_kg": round(oxidised, 4),
        "emitted_kg": round(emitted, 4),
        "capture": capture,
        "oxidation": oxidation,
    }


def landfill_series(
    disposals: dict[int, dict[str, float]],
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
    years: int = DEFAULT_HORIZON_YEARS,
    capture: float | None = None,
    oxidation: float | None = None,
) -> list[dict[str, Any]]:
    """The whole emission profile from a schedule of disposals.

    ``disposals`` maps a year offset to tonnes per stream. Each year's waste
    starts its own decay curve and they superpose, which is why stopping today
    does not stop the emissions today.
    """
    if not disposals:
        raise LandfillError("No disposals given")
    if years < 1:
        raise LandfillError("Need at least one year of profile")

    generated = [0.0] * (years + 1)
    for start_year, mix in disposals.items():
        if start_year < 1:
            raise LandfillError("Disposal years are 1-based")
        for stream, tonnes in mix.items():
            if tonnes <= 0:
                continue
            profile = decay_profile(
                stream, tonnes, climate=climate, site=site,
                years=years - start_year + 1,
            )
            for row in profile:
                index = start_year + row["year"] - 1
                if index <= years:
                    generated[index] += row["generated_kg"]

    rows: list[dict[str, Any]] = []
    cumulative_emitted = 0.0
    for year in range(1, years + 1):
        split = site_emissions(
            generated[year], site=site, capture=capture, oxidation=oxidation
        )
        cumulative_emitted += split["emitted_kg"]
        rows.append({
            "year": year,
            "generated_kg": split["generated_kg"],
            "captured_kg": split["captured_kg"],
            "oxidised_kg": split["oxidised_kg"],
            "emitted_kg": split["emitted_kg"],
            "cumulative_emitted_kg": round(cumulative_emitted, 4),
            "emitted_co2e": round(split["emitted_kg"] * METHANE_GWP_100, 3),
        })
    return rows


def methane_series(
    disposals: dict[int, dict[str, float]],
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
    years: int = DEFAULT_HORIZON_YEARS,
) -> list[float]:
    """Annual methane emitted, in kg, as a bare series.

    For ``climate_metrics.py``: GWP* is built for a methane stream whose *rate*
    changes over time, and until now there was no source in the repo producing
    one. A flat factor gives a constant, on which GWP* has nothing to say.
    """
    return [
        row["emitted_kg"]
        for row in landfill_series(disposals, climate, site, years)
    ]


def compare_to_flat_factor(
    stream: str,
    tonnes: float,
    flat_factor: float = 0.5,
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
    years: int = DEFAULT_HORIZON_YEARS,
) -> dict[str, Any]:
    """What the single constant gets right, and what it gets wrong.

    It is not simply high or low. It books everything in year one, so it is
    enormously too high then and too low for the next several decades - and for
    a stream that has been stable for years the annual totals converge, which is
    why the error is so easy to miss.
    """
    rows = landfill_series(
        {1: {stream: tonnes}}, climate=climate, site=site, years=years
    )
    flat_kg = tonnes * 1000.0 * flat_factor
    modelled_total = rows[-1]["cumulative_emitted_kg"]

    # The most methane this waste could ever produce, with no capture and no
    # oxidation - every gram of dissimilable carbon converted. Read as kg of
    # methane per kg of waste, the flat constant sits well above this, which
    # means it cannot be a methane figure at all: it is a CO2e figure with its
    # units lost somewhere. Either way it is not comparable with what the bin
    # actually emits, and the ceiling is the cleanest way to show that.
    ceiling = methane_potential(stream, site) * tonnes

    first_year = rows[0]["emitted_kg"]
    within_ten = sum(row["emitted_kg"] for row in rows[:10])
    return {
        "stream": stream,
        "tonnes": tonnes,
        "flat_factor_kg": round(flat_kg, 3),
        "physical_ceiling_kg": round(ceiling, 3),
        "exceeds_physical_ceiling": flat_kg > ceiling,
        "modelled_total_kg": round(modelled_total, 3),
        "first_year_kg": round(first_year, 3),
        "first_ten_years_kg": round(within_ten, 3),
        "first_year_ratio": (
            round(flat_kg / first_year, 2) if first_year > 0 else None
        ),
        "share_in_first_decade": (
            round(within_ten / modelled_total, 4) if modelled_total > 0 else 0.0
        ),
        "years_to_half": _years_to_share(rows, 0.5),
        "years_to_ninety": _years_to_share(rows, 0.9),
    }


def _years_to_share(rows: list[dict[str, Any]], share: float) -> int | None:
    """The year by which a given share of the total has been emitted."""
    total = rows[-1]["cumulative_emitted_kg"]
    if total <= 0:
        return None
    for row in rows:
        if row["cumulative_emitted_kg"] >= total * share:
            return row["year"]
    return None


# ---------------------------------------------------------------------------
# Treatment routes
# ---------------------------------------------------------------------------

def route_emissions(
    route: str,
    stream: str,
    tonnes: float,
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
    grid_intensity: float = DEFAULT_GRID_INTENSITY,
    heat_intensity: float = DEFAULT_HEAT_INTENSITY,
    years: int = DEFAULT_HORIZON_YEARS,
) -> dict[str, Any]:
    """One route's emissions, with the avoided burden stated separately.

    Gross and credit are never added together into one figure. Netting them
    would bury a grid intensity assumption inside a waste number, and a reader
    who disagreed with it would have no way to see it, let alone change it.
    """
    if route not in TREATMENT_ROUTES:
        raise LandfillError(f"Unknown treatment route: {route}")
    if tonnes < 0:
        raise LandfillError("Tonnage cannot be negative")

    entry = TREATMENT_ROUTES[route]
    process_kg = entry["process_kg_per_tonne"] * tonnes

    if route == "landfill":
        rows = landfill_series(
            {1: {stream: tonnes}}, climate=climate, site=site, years=years
        )
        methane_kg = rows[-1]["cumulative_emitted_kg"]
        methane_co2e = methane_kg * METHANE_GWP_100
        profile = rows
    else:
        methane_kg = 0.0
        methane_co2e = 0.0
        profile = None

    avoided_power = entry["avoided_kwh_per_tonne"] * tonnes * grid_intensity
    avoided_heat = entry["avoided_heat_kwh_per_tonne"] * tonnes * heat_intensity
    avoided_fertiliser = (
        entry["avoided_fertiliser_kg_per_tonne"] * tonnes * FERTILISER_INTENSITY
    )
    avoided = avoided_power + avoided_heat + avoided_fertiliser

    gross = methane_co2e + process_kg
    return {
        "route": route,
        "label": entry["label"],
        "stream": stream,
        "tonnes": tonnes,
        "methane_kg": round(methane_kg, 3),
        "methane_co2e": round(methane_co2e, 3),
        "process_co2e": round(process_kg, 3),
        "gross_co2e": round(gross, 3),
        "avoided_power_co2e": round(avoided_power, 3),
        "avoided_heat_co2e": round(avoided_heat, 3),
        "avoided_fertiliser_co2e": round(avoided_fertiliser, 3),
        "avoided_co2e": round(avoided, 3),
        "net_co2e": round(gross - avoided, 3),
        "sequestered_carbon_kg": (
            round(sequestered_carbon(stream) * tonnes, 3)
            if route == "landfill" else 0.0
        ),
        "note": entry["note"],
        "profile": profile,
    }


def compare_routes(
    stream: str,
    tonnes: float,
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
    grid_intensity: float = DEFAULT_GRID_INTENSITY,
    heat_intensity: float = DEFAULT_HEAT_INTENSITY,
    years: int = DEFAULT_HORIZON_YEARS,
) -> list[dict[str, Any]]:
    """Every route for one stream, best net first."""
    rows = [
        route_emissions(
            route, stream, tonnes, climate=climate, site=site,
            grid_intensity=grid_intensity, heat_intensity=heat_intensity,
            years=years,
        )
        for route in list_routes()
    ]
    rows.sort(key=lambda row: row["net_co2e"])
    return rows


# ---------------------------------------------------------------------------
# Diversion
# ---------------------------------------------------------------------------

def diversion_scenario(
    annual_mix: dict[str, float],
    change_year: int,
    diverted_share: float,
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
    years: int = DEFAULT_HORIZON_YEARS,
) -> dict[str, Any]:
    """What changing behaviour in a given year actually does to the curve.

    This is the output the flat factor gets wrong, and it gets it wrong in the
    flattering direction: it reports the full benefit the year the household
    starts composting. In reality the site is still working through everything
    buried before then, so the benefit arrives over decades, and saying
    otherwise is why nobody believes the second year's advice.
    """
    if not annual_mix:
        raise LandfillError("No waste mix given")
    if change_year < 1:
        raise LandfillError("The change year must be 1 or later")
    if change_year > years:
        raise LandfillError("The change happens after the horizon ends")
    if not 0.0 <= diverted_share <= 1.0:
        raise LandfillError("Diverted share must be a fraction between 0 and 1")

    baseline_disposals = {year: dict(annual_mix) for year in range(1, years + 1)}
    changed_disposals = {
        year: (
            dict(annual_mix) if year < change_year
            else {
                stream: tonnes * (1.0 - diverted_share)
                for stream, tonnes in annual_mix.items()
            }
        )
        for year in range(1, years + 1)
    }

    baseline = landfill_series(baseline_disposals, climate, site, years)
    changed = landfill_series(changed_disposals, climate, site, years)

    rows = []
    for before, after in zip(baseline, changed):
        rows.append({
            "year": before["year"],
            "baseline_kg": before["emitted_kg"],
            "changed_kg": after["emitted_kg"],
            "saved_kg": round(before["emitted_kg"] - after["emitted_kg"], 4),
            "saved_co2e": round(
                (before["emitted_kg"] - after["emitted_kg"]) * METHANE_GWP_100, 3
            ),
        })

    total_saved = sum(row["saved_kg"] for row in rows)
    instant_claim = sum(
        row["baseline_kg"] for row in rows[change_year - 1:change_year]
    ) * diverted_share

    # How long until the diversion is delivering most of what it eventually will
    first_year_saving = rows[change_year - 1]["saved_kg"] if rows else 0.0
    steady_saving = rows[-1]["saved_kg"]
    ramp_year = None
    for row in rows[change_year - 1:]:
        if steady_saving > 0 and row["saved_kg"] >= steady_saving * 0.9:
            ramp_year = row["year"] - change_year
            break

    return {
        "change_year": change_year,
        "diverted_share": diverted_share,
        "total_saved_kg": round(total_saved, 3),
        "total_saved_co2e": round(total_saved * METHANE_GWP_100, 3),
        "first_year_saving_kg": round(first_year_saving, 4),
        "steady_saving_kg": round(steady_saving, 4),
        "instant_model_claim_kg": round(instant_claim, 4),
        "years_to_ninety_percent_effect": ramp_year,
        "rows": rows,
    }


def sensitivity(
    stream: str,
    tonnes: float,
    years: int = DEFAULT_HORIZON_YEARS,
) -> list[dict[str, Any]]:
    """The parameters that genuinely move the answer."""
    rows: list[dict[str, Any]] = []

    for climate in list_climate_zones():
        series = landfill_series(
            {1: {stream: tonnes}}, climate=climate, years=years
        )
        rows.append({
            "parameter": "Climate",
            "setting": CLIMATE_ZONES[climate]["label"],
            "total_kg": series[-1]["cumulative_emitted_kg"],
            "years_to_half": _years_to_share(series, 0.5),
        })

    for site in list_sites():
        series = landfill_series({1: {stream: tonnes}}, site=site, years=years)
        rows.append({
            "parameter": "Site",
            "setting": SITE_ARCHETYPES[site]["label"],
            "total_kg": series[-1]["cumulative_emitted_kg"],
            "years_to_half": _years_to_share(series, 0.5),
        })

    for capture in (0.0, 0.4, 0.68, 0.85):
        series = landfill_series(
            {1: {stream: tonnes}}, years=years, capture=capture
        )
        rows.append({
            "parameter": "Gas capture",
            "setting": f"{capture:.0%} captured",
            "total_kg": series[-1]["cumulative_emitted_kg"],
            "years_to_half": _years_to_share(series, 0.5),
        })

    for horizon in (20, 50, 100):
        series = landfill_series({1: {stream: tonnes}}, years=horizon)
        rows.append({
            "parameter": "Accounting horizon",
            "setting": f"{horizon} years",
            "total_kg": series[-1]["cumulative_emitted_kg"],
            "years_to_half": _years_to_share(series, 0.5),
        })

    return rows


def get_landfill_insights(comparison: dict[str, Any]) -> list[str]:
    """Plain-language readings of a flat-factor comparison."""
    if not comparison:
        return ["Nothing to analyse."]

    insights: list[str] = []
    stream = get_stream(comparison["stream"])

    if comparison.get("exceeds_physical_ceiling"):
        insights.append(
            f"Read as kilograms of methane, the flat constant gives "
            f"{comparison['flat_factor_kg']:,.0f} kg from waste that can "
            f"generate at most {comparison['physical_ceiling_kg']:,.0f} kg even "
            "with nothing captured and nothing oxidised. A constant above the "
            "physical ceiling is not a methane figure with the wrong value; it "
            "is a figure whose units went missing."
        )

    if comparison.get("first_year_ratio"):
        insights.append(
            f"A flat factor books all {comparison['flat_factor_kg']:,.0f} kg of "
            f"methane in the year the bin went out. Only "
            f"{comparison['first_year_kg']:,.0f} kg is actually generated that "
            f"year — it overstates the first year by "
            f"{comparison['first_year_ratio']:.0f} times."
        )

    if comparison.get("years_to_half"):
        insights.append(
            f"Half of the methane from this {stream['label'].lower()} arrives "
            f"after year {comparison['years_to_half']}, and ninety percent "
            f"after year {comparison['years_to_ninety']}."
        )

    insights.append(
        f"{comparison['share_in_first_decade']:.0%} of the total is emitted in "
        "the first ten years. The rest keeps arriving long after anyone has "
        "stopped thinking about that particular bin bag."
    )

    stored = sequestered_carbon(comparison["stream"]) * comparison["tonnes"]
    if stored > 0:
        insights.append(
            f"{stored:,.0f} kg of carbon in this stream never decomposes at "
            "all. That is a real store, not a delayed emission — and it is "
            "invisible to a model that only counts what comes out."
        )

    return insights


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def init_landfill_db() -> bool:
    """Create the table if it does not exist yet."""
    conn = None
    try:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS landfill_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                climate TEXT NOT NULL,
                site TEXT NOT NULL,
                total_tonnes REAL NOT NULL,
                methane_kg REAL NOT NULL,
                methane_co2e REAL NOT NULL,
                detail_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Unable to initialise landfill table: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_profile(
    user_id: int,
    name: str,
    mix: dict[str, float],
    result: dict[str, Any],
    climate: str = DEFAULT_CLIMATE,
    site: str = DEFAULT_SITE,
) -> int | None:
    """Persist a waste profile. Returns the row id or None."""
    init_landfill_db()
    conn = None
    try:
        conn = _connect()
        methane_kg = float(result.get("total_emitted_kg", 0.0))
        cursor = conn.execute(
            """
            INSERT INTO landfill_profiles (
                user_id, name, climate, site, total_tonnes,
                methane_kg, methane_co2e, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(name),
                str(climate),
                str(site),
                float(sum(mix.values())),
                methane_kg,
                methane_kg * METHANE_GWP_100,
                json.dumps({"mix": mix, "result": result}),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save landfill profile: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_profiles(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Saved profiles, newest first."""
    init_landfill_db()
    conn = None
    try:
        conn = _connect()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM landfill_profiles
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        profiles = []
        for row in rows:
            record = dict(row)
            if record.get("detail_json"):
                try:
                    record["detail"] = json.loads(record["detail_json"])
                except (TypeError, ValueError):
                    record["detail"] = None
            profiles.append(record)
        return profiles
    except sqlite3.Error as exc:
        logger.error("Unable to read landfill profiles: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def delete_profile(profile_id: int, user_id: int) -> bool:
    """Delete a profile the user owns."""
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            "DELETE FROM landfill_profiles WHERE id = ? AND user_id = ?",
            (int(profile_id), int(user_id)),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Unable to delete landfill profile: %s", exc)
        return False
    finally:
        if conn:
            conn.close()
