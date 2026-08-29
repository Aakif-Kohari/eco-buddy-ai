"""Time-explicit LCA: when an emission happens, not only how large it is.

Two modules in this repository already know when emissions occur, and both
throw that information away before it reaches an impact figure.

``src/environment/landfill_methane.py`` implements the IPCC first order decay
model. Its entire purpose is to establish that the methane from food waste
buried this year is released over the following fifty, most of it in the first
fifteen. ``src/environment/building_materials_lca.py`` splits a renovation into
A1-A5 now, B4 replacements at years 15, 25 and 40, and C1-C4 at end of life.
Both produce a time series.

Both then multiply every kilogram by the same GWP100 factor and add. That is
arithmetically identical to asserting the whole lot was emitted this morning.

Why the assertion is not harmless
-----------------------------------
GWP100 is an integral of radiative forcing over the hundred years *following an
emission*. Applied to an emission in year 40 it quietly runs the analysis to
year 140; applied to an emission today it stops at year 100. Adding the two is
adding integrals taken over different intervals and calling the result a total.

For a target with a date on it - 2050, 2100 - the relevant question is what the
emission does *before that date*, and a fixed-horizon factor cannot answer it.
A methane pulse in year 90 of a hundred-year assessment delivers nearly all of
its warming inside the window. The same pulse in year 5 has largely decayed
before the window closes. Static GWP100 scores them identically.

What this module does instead
-------------------------------
Every emission carries a year. Every gas decays according to its own impulse
response function. Forcing is integrated from each emission to one *shared*
target year, which is the only way contributions from different years are
commensurable.

CO2 uses the Joos et al. (2013) multi-exponential response, including the
term that never decays. That non-decaying fraction is what makes CO2 different
in kind from every other gas, and a single-exponential approximation loses
precisely that. Everything else uses single-exponential decay against its AR6
lifetime.

Calibration, so the comparison is about timing and nothing else
-----------------------------------------------------------------
Radiative efficiencies for the non-CO2 gases are back-calculated from the
published AR6 GWP100 values rather than taken from a separate table. The
consequence is an identity worth stating: a CO2 emission in year zero scored to
a target hundred years away returns *exactly* its static GWP100 figure. There
is a test pinning it.

That identity is the point. Any difference this module reports against the
static number is attributable to emission timing, not to a different
parameterisation of the physics. Without the calibration every result would
carry an unattributable offset and the module would be much harder to trust.

The calibration is anchored at one horizon, so it cannot be exact at every
other one. Scored at twenty years the model reproduces the published AR6 GWP20
to within about three percent for N2O, HFC-134a, HFC-32 and SF6, and overshoots
methane by roughly eight percent - because the published methane values apply a
different feedback treatment at each horizon and a single exponential cannot
follow that. ``model_fidelity`` reports every deviation rather than leaving it
to be discovered.

What it deliberately does not do
----------------------------------
No discounting. The atmosphere does not apply one, and a financial rate applied
to physical decay produces a number that is neither.

No climate response. Forcing is not temperature. Converting one to the other
requires a climate model with its own contested parameters, and the ranking
questions this module exists to answer are answerable in forcing terms.

No opinion about which metric is correct. Cumulative forcing to a target year,
forcing at that year, and static GWP100 rank options differently and sometimes
in opposite orders. ``compare_inventories`` reports the disagreement. Resolving
it is a choice about what the user cares about, not a calculation.

Where this connects to code already merged
--------------------------------------------
*   ``src/environment/climate_metrics.py`` resolves the *gas*. This resolves the
    *year*. They are orthogonal and both are needed.
*   ``src/carbon/carbon_payback.py`` compares an upfront burden against a stream
    of savings as undated kilograms. ``dynamic_payback_year`` does the same
    comparison with both sides dated, and the answer is later.
*   ``src/utils/permanence_accounting.py`` handles the *risk* that stored carbon
    comes back. ``temporary_storage_credit`` handles the radiative consequence
    of a delay that is known and intentional. Different questions.
*   ``src/carbon/aerosol_forcing.py`` and ``src/carbon/albedo_forcing.py``
    already work in forcing units, in their own domains.

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


class DynamicLCAError(ValueError):
    """Raised when an inventory or a horizon cannot support a dynamic score."""


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

# Joos et al. (2013) impulse response for a CO2 pulse against a present-day
# background. The first coefficient is the fraction that does not decay on any
# timescale represented here; it is the reason CO2 cannot be modelled with a
# single lifetime.
CO2_IRF_A0 = 0.2173
CO2_IRF_TERMS = (
    (0.2240, 394.4),
    (0.2824, 36.54),
    (0.2763, 4.304),
)

# Radiative efficiency of CO2, W m-2 per kg, at a present-day background.
CO2_RADIATIVE_EFFICIENCY = 1.7517e-15

# The horizon the published GWP values are quoted against, and therefore the
# horizon the calibration is anchored to.
REFERENCE_HORIZON = 100

#: Supported gases. ``gwp100`` is the published AR6 value including
#: carbon-cycle feedbacks; the radiative efficiency used internally is derived
#: from it rather than tabulated separately, so that this module and
#: ``src/environment/climate_metrics.py`` agree at the reference horizon.
GASES = {
    "co2": {
        "label": "Carbon dioxide",
        "formula": "CO2",
        "lifetime": None,
        "gwp100": 1.0,
        "gwp20_published": 1.0,
        "kind": "long-lived",
        "note": (
            "No single lifetime. A pulse decays on several timescales and a "
            "fifth of it is still airborne after a thousand years, which is "
            "why the multi-exponential response is used rather than a mean."
        ),
    },
    "ch4_fossil": {
        "label": "Methane (fossil origin)",
        "formula": "CH4",
        "lifetime": 11.8,
        "gwp100": 29.8,
        "gwp20_published": 82.5,
        "kind": "short-lived",
        "note": (
            "Short-lived and potent. Its score depends more strongly on when "
            "it was emitted than any other gas here, because most of its "
            "effect is delivered within twenty years of release."
        ),
    },
    "ch4_biogenic": {
        "label": "Methane (biogenic origin)",
        "formula": "CH4",
        "lifetime": 11.8,
        "gwp100": 27.0,
        "gwp20_published": 79.7,
        "kind": "short-lived",
        "note": (
            "Lower than fossil methane because oxidising biogenic carbon "
            "returns CO2 that was recently atmospheric. The difference is an "
            "accounting convention about the carbon, not about the methane."
        ),
    },
    "n2o": {
        "label": "Nitrous oxide",
        "formula": "N2O",
        "lifetime": 109.0,
        "gwp100": 273.0,
        "gwp20_published": 273.0,
        "kind": "long-lived",
        "note": (
            "A lifetime close to the reference horizon, so its static and "
            "dynamic scores diverge more slowly than methane's and faster "
            "than CO2's."
        ),
    },
    "hfc134a": {
        "label": "HFC-134a",
        "formula": "CH2FCF3",
        "lifetime": 14.0,
        "gwp100": 1526.0,
        "gwp20_published": 4144.0,
        "kind": "short-lived",
        "note": (
            "The dominant refrigerant in the inventory built by "
            "src/environment/refrigerant_gases.py. Leaks are dated events, "
            "which makes them a natural fit for a time-explicit score."
        ),
    },
    "hfc32": {
        "label": "HFC-32",
        "formula": "CH2F2",
        "lifetime": 5.4,
        "gwp100": 771.0,
        "gwp20_published": 2693.0,
        "kind": "short-lived",
        "note": (
            "The low-GWP retrofit option. Short enough that a leak late in a "
            "system's life scores very differently from one early on."
        ),
    },
    "sf6": {
        "label": "Sulphur hexafluoride",
        "formula": "SF6",
        "lifetime": 3200.0,
        "gwp100": 25200.0,
        "gwp20_published": 18300.0,
        "kind": "long-lived",
        "note": (
            "Effectively permanent on any horizon a person plans against. Its "
            "dynamic and static scores barely differ, which is itself the "
            "useful finding."
        ),
    },
}

#: The metrics this module can report. They are not interchangeable and the
#: module never picks one on the user's behalf.
METRICS = {
    "cumulative_dynamic": {
        "label": "Cumulative forcing to target year",
        "unit": "kg CO2e",
        "question": "How much warming pressure has accumulated by the target?",
        "note": (
            "The default. Integrates each emission from its own year to the "
            "shared target, so late emissions are credited only for the time "
            "they actually had."
        ),
    },
    "forcing_at_target": {
        "label": "Instantaneous forcing at target year",
        "unit": "W/m2",
        "question": "How much warming pressure is still acting at the target?",
        "note": (
            "Favours anything short-lived, because a methane pulse forty "
            "years before the target has largely gone by the time it is read. "
            "Appropriate for a peak-warming question, misleading for a "
            "cumulative one."
        ),
    },
    "static_gwp100": {
        "label": "Static GWP100",
        "unit": "kg CO2e",
        "question": "What does the conventional method say?",
        "note": (
            "What every other module in this app reports. Included so the "
            "size of the timing assumption is visible rather than argued."
        ),
    },
    "static_gwp20": {
        "label": "Static GWP20",
        "unit": "kg CO2e",
        "question": "What does a short-horizon convention say?",
        "note": (
            "Weights short-lived gases far more heavily. Often quoted in "
            "methane debates, and it is a different question rather than a "
            "more urgent version of the same one."
        ),
    },
}

CATEGORY_UNSPECIFIED = "unspecified"


# ---------------------------------------------------------------------------
# Impulse response and horizon integrals
# ---------------------------------------------------------------------------

def _gas(key):
    """Look up a gas definition, or refuse with the list of known keys."""
    if key is None:
        raise DynamicLCAError("An emission needs a gas.")
    normalised = str(key).strip().lower()
    if normalised not in GASES:
        known = ", ".join(sorted(GASES))
        raise DynamicLCAError(
            "Unknown gas '%s'. Known gases: %s." % (key, known)
        )
    return normalised


def impulse_response(gas, years_since_emission):
    """Fraction of a pulse still airborne ``years_since_emission`` after release.

    Returns 0.0 for a negative age, because an emission cannot force the
    climate before it happens and silently returning 1.0 there would let a
    mis-dated inventory produce a plausible number.
    """
    key = _gas(gas)
    age = float(years_since_emission)
    if age < 0:
        return 0.0

    if key == "co2":
        remaining = CO2_IRF_A0
        for weight, tau in CO2_IRF_TERMS:
            remaining += weight * math.exp(-age / tau)
        return remaining

    lifetime = GASES[key]["lifetime"]
    return math.exp(-age / lifetime)


def _shape_integral(gas, horizon):
    """Integral of the impulse response from 0 to ``horizon``, in years.

    This is the only place the two decay forms differ, and separating it out
    keeps every downstream formula identical for CO2 and everything else.
    """
    key = _gas(gas)
    span = float(horizon)
    if span <= 0:
        return 0.0

    if key == "co2":
        total = CO2_IRF_A0 * span
        for weight, tau in CO2_IRF_TERMS:
            total += weight * tau * (1.0 - math.exp(-span / tau))
        return total

    lifetime = GASES[key]["lifetime"]
    return lifetime * (1.0 - math.exp(-span / lifetime))


def radiative_efficiency(gas):
    """Radiative efficiency in W m-2 per kg.

    For CO2 this is the tabulated value. For everything else it is derived
    from the published GWP100 so that ``gwp(gas, 100)`` reproduces that
    published value exactly. See the module docstring for why the calibration
    is done this way round.
    """
    key = _gas(gas)
    if key == "co2":
        return CO2_RADIATIVE_EFFICIENCY

    reference = absolute_gwp("co2", REFERENCE_HORIZON)
    shape = _shape_integral(key, REFERENCE_HORIZON)
    if shape <= 0:
        raise DynamicLCAError(
            "Gas '%s' has a degenerate lifetime and cannot be calibrated." % key
        )
    return GASES[key]["gwp100"] * reference / shape


def absolute_gwp(gas, horizon):
    """Absolute global warming potential, W m-2 yr per kg, over ``horizon``."""
    key = _gas(gas)
    span = float(horizon)
    if span < 0:
        raise DynamicLCAError("A horizon cannot be negative.")
    if key == "co2":
        return CO2_RADIATIVE_EFFICIENCY * _shape_integral("co2", span)
    return radiative_efficiency(key) * _shape_integral(key, span)


def gwp(gas, horizon):
    """Global warming potential of ``gas`` over ``horizon`` years."""
    span = float(horizon)
    if span <= 0:
        raise DynamicLCAError("A GWP horizon must be positive.")
    reference = absolute_gwp("co2", span)
    if reference <= 0:
        raise DynamicLCAError("The CO2 reference integral vanished.")
    return absolute_gwp(gas, span) / reference


def characterisation_factor(gas, emission_year, target_year, base_year=0):
    """Dynamic characterisation factor, in kg CO2e per kg of gas.

    The denominator is the CO2 reference at the standard hundred-year horizon,
    which makes the output directly comparable to every static figure this app
    already reports. The numerator is integrated only over the years the
    emission actually has before the target.

    A CO2 emission in the base year with the target a hundred years later
    therefore returns exactly 1.0, and every other case can be read as a
    departure from that anchor.
    """
    key = _gas(gas)
    emitted = float(emission_year)
    target = float(target_year)
    if target < emitted:
        raise DynamicLCAError(
            "Target year %s is before the emission in %s."
            % (_fmt_year(target), _fmt_year(emitted))
        )
    available = target - emitted
    reference = absolute_gwp("co2", REFERENCE_HORIZON)
    return absolute_gwp(key, available) / reference


def _fmt_year(value):
    numeric = float(value)
    if abs(numeric - round(numeric)) < 1e-9:
        return str(int(round(numeric)))
    return "%.2f" % numeric


# ---------------------------------------------------------------------------
# Building inventories
# ---------------------------------------------------------------------------

def build_emission(year, gas, amount_kg, label="", category=CATEGORY_UNSPECIFIED):
    """One dated emission. Negative amounts are removals and are allowed."""
    key = _gas(gas)
    try:
        when = int(year)
    except (TypeError, ValueError):
        raise DynamicLCAError("Emission year must be a whole year, got %r." % (year,))
    try:
        amount = float(amount_kg)
    except (TypeError, ValueError):
        raise DynamicLCAError("Emission amount must be a number, got %r." % (amount_kg,))
    if not math.isfinite(amount):
        raise DynamicLCAError("Emission amount must be finite.")

    return {
        "year": when,
        "gas": key,
        "amount_kg": amount,
        "label": str(label).strip() or GASES[key]["label"],
        "category": str(category).strip() or CATEGORY_UNSPECIFIED,
    }


def build_inventory(name, emissions, base_year=None):
    """A named collection of dated emissions.

    ``base_year`` defaults to the earliest emission. It is the origin the
    forcing series is drawn from and has no effect on any total.
    """
    if not name or not str(name).strip():
        raise DynamicLCAError("An inventory needs a name.")
    entries = list(emissions or [])
    if not entries:
        raise DynamicLCAError("An inventory needs at least one emission.")

    normalised = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise DynamicLCAError("Every emission must be a mapping.")
        normalised.append(build_emission(
            entry.get("year"),
            entry.get("gas"),
            entry.get("amount_kg"),
            entry.get("label", ""),
            entry.get("category", CATEGORY_UNSPECIFIED),
        ))

    normalised.sort(key=lambda item: (item["year"], item["gas"]))
    earliest = normalised[0]["year"]
    latest = normalised[-1]["year"]

    if base_year is None:
        origin = earliest
    else:
        try:
            origin = int(base_year)
        except (TypeError, ValueError):
            raise DynamicLCAError("Base year must be a whole year.")
        if origin > earliest:
            raise DynamicLCAError(
                "Base year %s is after the first emission in %s."
                % (_fmt_year(origin), _fmt_year(earliest))
            )

    return {
        "name": str(name).strip(),
        "emissions": normalised,
        "base_year": origin,
        "first_year": earliest,
        "last_year": latest,
        "gases": sorted({item["gas"] for item in normalised}),
        "categories": sorted({item["category"] for item in normalised}),
    }


def expand_annual(gas, amount_per_year, start_year, years, label="",
                  category=CATEGORY_UNSPECIFIED):
    """A constant annual burden, as one dated emission per year.

    Use for operational emissions - a boiler running, a commute repeating -
    which the rest of the app stores as a single annualised figure.
    """
    count = int(years)
    if count <= 0:
        raise DynamicLCAError("An annual series needs at least one year.")
    begin = int(start_year)
    return [
        build_emission(begin + offset, gas, amount_per_year, label, category)
        for offset in range(count)
    ]


def expand_first_order_decay(gas, initial_stock_kg, decay_rate, start_year,
                             years, label="", category=CATEGORY_UNSPECIFIED):
    """A stock released under first order decay, as a year-by-year series.

    This is the shape ``src/environment/landfill_methane.py`` already produces
    and then collapses. Release in year i is the difference between the stock
    remaining at the start and end of that year, so the series sums to
    ``initial_stock_kg * (1 - exp(-k * years))`` and never overshoots the stock.
    """
    stock = float(initial_stock_kg)
    if stock < 0:
        raise DynamicLCAError("A decaying stock cannot be negative.")
    rate = float(decay_rate)
    if rate <= 0:
        raise DynamicLCAError(
            "A first order decay rate must be positive; a rate of zero "
            "describes a stock that is never released."
        )
    count = int(years)
    if count <= 0:
        raise DynamicLCAError("A decay series needs at least one year.")

    begin = int(start_year)
    series = []
    for offset in range(count):
        remaining_before = math.exp(-rate * offset)
        remaining_after = math.exp(-rate * (offset + 1))
        released = stock * (remaining_before - remaining_after)
        series.append(build_emission(
            begin + offset, gas, released, label, category
        ))
    return series


def merge_inventories(name, inventories, base_year=None):
    """Combine several inventories into one, preserving every emission year."""
    collected = []
    for inventory in inventories or []:
        collected.extend(inventory.get("emissions", []))
    if not collected:
        raise DynamicLCAError("Nothing to merge.")
    return build_inventory(name, collected, base_year=base_year)


# ---------------------------------------------------------------------------
# Forcing
# ---------------------------------------------------------------------------

def _validate_target(inventory, target_year):
    try:
        target = int(target_year)
    except (TypeError, ValueError):
        raise DynamicLCAError("Target year must be a whole year.")
    if target < inventory["last_year"]:
        raise DynamicLCAError(
            "Target year %s is before the last emission in %s. Scoring an "
            "inventory to a date it has not finished emitting by would report "
            "part of it as free."
            % (_fmt_year(target), _fmt_year(inventory["last_year"]))
        )
    return target


def instantaneous_forcing(inventory, year):
    """Radiative forcing still being exerted in ``year``, in W/m2."""
    when = float(year)
    total = 0.0
    for emission in inventory["emissions"]:
        age = when - emission["year"]
        if age < 0:
            continue
        total += (
            emission["amount_kg"]
            * radiative_efficiency(emission["gas"])
            * impulse_response(emission["gas"], age)
        )
    return total


def cumulative_forcing(inventory, target_year):
    """Radiative forcing accumulated up to ``target_year``, in W m-2 yr."""
    target = _validate_target(inventory, target_year)
    total = 0.0
    for emission in inventory["emissions"]:
        available = target - emission["year"]
        total += emission["amount_kg"] * absolute_gwp(emission["gas"], available)
    return total


def forcing_series(inventory, target_year, step=1):
    """Instantaneous and cumulative forcing, year by year, to the target.

    The cumulative column is built from the closed-form integral at each year
    rather than by summing the instantaneous column, so it does not inherit a
    quadrature error that would grow with the horizon.
    """
    target = _validate_target(inventory, target_year)
    stride = int(step)
    if stride <= 0:
        raise DynamicLCAError("Series step must be positive.")

    start = inventory["base_year"]
    reference = absolute_gwp("co2", REFERENCE_HORIZON)
    rows = []
    for year in range(start, target + 1, stride):
        accumulated = 0.0
        for emission in inventory["emissions"]:
            available = year - emission["year"]
            if available < 0:
                continue
            accumulated += emission["amount_kg"] * absolute_gwp(
                emission["gas"], available
            )
        rows.append({
            "year": year,
            "instantaneous_forcing": instantaneous_forcing(inventory, year),
            "cumulative_forcing": accumulated,
            "cumulative_co2e": accumulated / reference,
        })
    if rows and rows[-1]["year"] != target:
        accumulated = cumulative_forcing(inventory, target)
        rows.append({
            "year": target,
            "instantaneous_forcing": instantaneous_forcing(inventory, target),
            "cumulative_forcing": accumulated,
            "cumulative_co2e": accumulated / reference,
        })
    return rows


def peak_forcing(inventory, target_year):
    """The highest instantaneous forcing reached, and the year it occurs.

    Peak matters because several climate targets are stated as a temperature
    ceiling rather than a budget, and a pathway can satisfy a cumulative
    budget while overshooting on the way.
    """
    series = forcing_series(inventory, target_year)
    best = max(series, key=lambda row: row["instantaneous_forcing"])
    return {
        "year": best["year"],
        "forcing": best["instantaneous_forcing"],
        "forcing_at_target": series[-1]["instantaneous_forcing"],
        "declining_at_target": series[-1]["year"] > best["year"],
    }


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def static_score(inventory, horizon=REFERENCE_HORIZON):
    """The conventional figure: every emission at the same fixed-horizon GWP."""
    total = 0.0
    for emission in inventory["emissions"]:
        total += emission["amount_kg"] * gwp(emission["gas"], horizon)
    return total


def dynamic_score(inventory, target_year):
    """Score an inventory with emission timing carried through to the impact.

    Returns the dynamic and static totals, the per-emission comparison, and
    enough breakdown to say which part of the inventory the difference came
    from. The ratio is the headline: below 1 means the static figure has been
    overstating this inventory, above 1 means understating.
    """
    target = _validate_target(inventory, target_year)
    reference = absolute_gwp("co2", REFERENCE_HORIZON)

    rows = []
    dynamic_total = 0.0
    static_total = 0.0
    by_category = {}
    by_gas = {}

    for emission in inventory["emissions"]:
        available = target - emission["year"]
        factor = absolute_gwp(emission["gas"], available) / reference
        static_factor = gwp(emission["gas"], REFERENCE_HORIZON)
        dynamic_value = emission["amount_kg"] * factor
        static_value = emission["amount_kg"] * static_factor

        dynamic_total += dynamic_value
        static_total += static_value

        category = emission["category"]
        bucket = by_category.setdefault(
            category, {"dynamic": 0.0, "static": 0.0, "amount_kg": 0.0}
        )
        bucket["dynamic"] += dynamic_value
        bucket["static"] += static_value
        bucket["amount_kg"] += emission["amount_kg"]

        gas_bucket = by_gas.setdefault(
            emission["gas"], {"dynamic": 0.0, "static": 0.0, "amount_kg": 0.0}
        )
        gas_bucket["dynamic"] += dynamic_value
        gas_bucket["static"] += static_value
        gas_bucket["amount_kg"] += emission["amount_kg"]

        rows.append({
            "year": emission["year"],
            "gas": emission["gas"],
            "gas_label": GASES[emission["gas"]]["label"],
            "label": emission["label"],
            "category": category,
            "amount_kg": emission["amount_kg"],
            "years_available": available,
            "dynamic_factor": factor,
            "static_factor": static_factor,
            "dynamic_co2e": dynamic_value,
            "static_co2e": static_value,
            "factor_ratio": (factor / static_factor) if static_factor else None,
        })

    ratio = (dynamic_total / static_total) if static_total else None
    peak = peak_forcing(inventory, target)

    return {
        "name": inventory["name"],
        "target_year": target,
        "base_year": inventory["base_year"],
        "first_year": inventory["first_year"],
        "last_year": inventory["last_year"],
        "horizon_years": target - inventory["base_year"],
        "dynamic_total_co2e": dynamic_total,
        "static_total_co2e": static_total,
        "difference_co2e": dynamic_total - static_total,
        "ratio": ratio,
        "cumulative_forcing": dynamic_total * reference,
        "forcing_at_target": peak["forcing_at_target"],
        "peak_forcing": peak["forcing"],
        "peak_year": peak["year"],
        "declining_at_target": peak["declining_at_target"],
        "emissions": rows,
        "by_category": by_category,
        "by_gas": by_gas,
    }


def metric_comparison(inventory, target_year):
    """The same inventory under every metric this module can compute.

    Presented together because the disagreement between them is the finding.
    A conclusion that survives all four is robust; one that flips is a choice
    about which climate question is being asked.
    """
    target = _validate_target(inventory, target_year)
    dynamic = dynamic_score(inventory, target)

    values = {
        "cumulative_dynamic": dynamic["dynamic_total_co2e"],
        "forcing_at_target": dynamic["forcing_at_target"],
        "static_gwp100": dynamic["static_total_co2e"],
        "static_gwp20": static_score(inventory, 20),
    }

    spread = None
    co2e_metrics = [
        values["cumulative_dynamic"],
        values["static_gwp100"],
        values["static_gwp20"],
    ]
    smallest = min(co2e_metrics)
    largest = max(co2e_metrics)
    if smallest > 0:
        spread = largest / smallest

    return {
        "target_year": target,
        "values": values,
        "co2e_spread": spread,
        "metrics": METRICS,
        "dynamic": dynamic,
    }


def compare_inventories(inventories, target_year):
    """Rank several inventories under each metric and flag disagreement.

    Every inventory is scored to the same target year, which is the whole
    reason a comparison is meaningful. Where two metrics produce different
    orderings the comparison reports it rather than picking a winner.
    """
    entries = list(inventories or [])
    if len(entries) < 2:
        raise DynamicLCAError("Comparing needs at least two inventories.")

    scored = []
    for inventory in entries:
        comparison = metric_comparison(inventory, target_year)
        scored.append({
            "name": inventory["name"],
            "values": comparison["values"],
            "dynamic": comparison["dynamic"],
        })

    rankings = {}
    for metric in METRICS:
        ordered = sorted(scored, key=lambda item: item["values"][metric])
        rankings[metric] = [item["name"] for item in ordered]

    baseline = rankings["cumulative_dynamic"]
    disagreements = []
    for metric, order in rankings.items():
        if metric == "cumulative_dynamic":
            continue
        if order != baseline:
            disagreements.append({
                "metric": metric,
                "label": METRICS[metric]["label"],
                "order": order,
                "baseline_order": baseline,
                "best_differs": order[0] != baseline[0],
            })

    return {
        "target_year": int(target_year),
        "scored": scored,
        "rankings": rankings,
        "disagreements": disagreements,
        "robust": not disagreements,
    }


# ---------------------------------------------------------------------------
# Delay and storage
# ---------------------------------------------------------------------------

def delayed_emission_credit(amount_kg, gas, delay_years, target_year,
                            base_year=0):
    """The forcing avoided by emitting later rather than now.

    The credit is real and it is not a removal. Nothing is taken out of the
    atmosphere; the emission simply has fewer years in which to act before the
    target. Past the target the credit is entirely notional, which is why the
    target year is a required argument rather than a default.
    """
    key = _gas(gas)
    amount = float(amount_kg)
    delay = float(delay_years)
    if delay < 0:
        raise DynamicLCAError("A delay cannot be negative.")

    origin = int(base_year)
    target = int(target_year)
    if target < origin:
        raise DynamicLCAError("Target year is before the base year.")
    if target - origin > 1000:
        raise DynamicLCAError(
            "A window of %d years almost certainly means an absolute target "
            "year (2100) was combined with a relative base year (0). Pass "
            "both on the same footing."
            % (target - origin)
        )

    immediate = amount * characterisation_factor(key, origin, target)
    deferred_year = origin + delay
    if deferred_year > target:
        deferred = 0.0
        beyond_target = True
    else:
        deferred = amount * characterisation_factor(key, deferred_year, target)
        beyond_target = False

    credit = immediate - deferred
    return {
        "gas": key,
        "amount_kg": amount,
        "delay_years": delay,
        "target_year": target,
        "immediate_co2e": immediate,
        "deferred_co2e": deferred,
        "credit_co2e": credit,
        "credit_fraction": (credit / immediate) if immediate else None,
        "beyond_target": beyond_target,
        "note": (
            "The delayed emission falls outside the assessment window "
            "entirely, so the credit shown is the whole of it. That is an "
            "artefact of the window, not a removal."
            if beyond_target else
            "Nothing was removed from the atmosphere. The emission simply "
            "has fewer years to act before the target."
        ),
    }


def temporary_storage_credit(amount_kg, storage_years, target_year,
                             gas="co2", base_year=0):
    """Store a quantity of carbon for N years, then release all of it.

    Modelled as two dated events - a removal now and an emission later - which
    is what temporary storage physically is. The net is not zero, because the
    removal acts on the whole period and the release only on what remains.
    """
    amount = float(amount_kg)
    if amount < 0:
        raise DynamicLCAError("Stored quantity cannot be negative.")
    duration = float(storage_years)
    if duration <= 0:
        raise DynamicLCAError("Storage must last at least some time.")

    result = delayed_emission_credit(
        amount, gas, duration, target_year, base_year=base_year
    )
    result["storage_years"] = duration
    result["permanent_equivalent_fraction"] = result["credit_fraction"]
    result["moura_costa_equivalent"] = ton_year_equivalence(
        duration, method="moura_costa"
    )
    result["lashof_equivalent"] = ton_year_equivalence(
        duration, method="lashof", target_year_span=int(target_year) - int(base_year)
    )
    return result


def ton_year_equivalence(storage_years, method="moura_costa",
                         target_year_span=REFERENCE_HORIZON):
    """The two ton-year conventions, for comparison with the forcing result.

    Included because ton-year figures are widely quoted and routinely confused
    with each other. Moura-Costa divides the storage duration by a fixed
    equivalence time. Lashof counts the forcing pushed beyond the horizon,
    which turns out to be algebraically identical to the delayed-emission
    calculation above - a fact worth surfacing, because the two are usually
    presented as competing methods. Moura-Costa is the outlier and is
    consistently the more generous of the two.
    """
    duration = float(storage_years)
    if duration < 0:
        raise DynamicLCAError("Storage duration cannot be negative.")

    convention = str(method).strip().lower()
    if convention == "moura_costa":
        equivalence_time = 46.0
        return min(duration / equivalence_time, 1.0)
    if convention == "lashof":
        span = float(target_year_span)
        if span <= 0:
            raise DynamicLCAError("The Lashof horizon must be positive.")
        if duration >= span:
            return 1.0
        whole = _shape_integral("co2", span)
        if whole <= 0:
            return 0.0
        tail = _shape_integral("co2", span) - _shape_integral("co2", span - duration)
        return tail / whole
    raise DynamicLCAError(
        "Unknown ton-year method '%s'. Use 'moura_costa' or 'lashof'." % method
    )


def dynamic_payback_year(burden, savings, target_year):
    """The first year at which a dated burden is repaid by dated savings.

    ``src/carbon/carbon_payback.py`` divides an upfront figure by an annual one.
    That treats a kilogram emitted at manufacture and a kilogram avoided in
    year twelve as cancelling exactly, which they do not: the first has been
    forcing the climate for twelve years longer.

    Savings are supplied as positive avoided emissions and are negated here, so
    callers can build them with the same helpers used for the burden.
    """
    negated = [
        build_emission(
            item["year"], item["gas"], -item["amount_kg"],
            item["label"], item["category"],
        )
        for item in savings["emissions"]
    ]
    combined = build_inventory(
        "%s net of savings" % burden["name"],
        list(burden["emissions"]) + negated,
        base_year=min(burden["base_year"], savings["base_year"]),
    )

    target = _validate_target(combined, target_year)
    reference = absolute_gwp("co2", REFERENCE_HORIZON)

    naive_burden = static_score(burden)
    naive_annual = static_score(savings) / max(
        1, savings["last_year"] - savings["first_year"] + 1
    )
    naive_years = (naive_burden / naive_annual) if naive_annual > 0 else None

    # Cumulative forcing is zero at the base year by definition - nothing has
    # had any time to act yet. Reading that as a repaid debt would report
    # every purchase as breaking even on the day it was made, so breakeven is
    # only recognised once the net has actually been in deficit.
    breakeven = None
    in_deficit = False
    peak_deficit = 0.0
    peak_year = combined["base_year"]
    trajectory = []
    for year in range(combined["base_year"], target + 1):
        accumulated = 0.0
        for emission in combined["emissions"]:
            available = year - emission["year"]
            if available < 0:
                continue
            accumulated += emission["amount_kg"] * absolute_gwp(
                emission["gas"], available
            )
        net_co2e = accumulated / reference
        trajectory.append({"year": year, "net_co2e": net_co2e})

        if net_co2e > 0:
            in_deficit = True
            if net_co2e > peak_deficit:
                peak_deficit = net_co2e
                peak_year = year
        elif in_deficit and breakeven is None:
            breakeven = year

    return {
        "target_year": target,
        "breakeven_year": breakeven,
        "breakeven_years_from_start": (
            breakeven - combined["base_year"] if breakeven is not None else None
        ),
        "naive_payback_years": naive_years,
        "never_repays": in_deficit and breakeven is None,
        "never_in_deficit": not in_deficit,
        "peak_deficit_co2e": peak_deficit,
        "peak_deficit_year": peak_year,
        "net_at_target": trajectory[-1]["net_co2e"] if trajectory else 0.0,
        "trajectory": trajectory,
        "combined": combined,
    }


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

def dominant_divergence(result):
    """Which gas moved the dynamic total furthest from the static one."""
    worst = None
    for gas, values in result["by_gas"].items():
        difference = values["dynamic"] - values["static"]
        if worst is None or abs(difference) > abs(worst["difference"]):
            worst = {
                "gas": gas,
                "label": GASES[gas]["label"],
                "difference": difference,
                "dynamic": values["dynamic"],
                "static": values["static"],
            }
    return worst


def get_dynamic_insights(result):
    """Plain-language findings, ordered with the load-bearing ones first."""
    insights = []
    ratio = result["ratio"]
    difference = result["difference_co2e"]

    if ratio is None:
        insights.append({
            "level": "warning",
            "title": "No static baseline to compare against",
            "body": (
                "The static total is zero, usually because removals and "
                "emissions cancel. The ratio is undefined; read the forcing "
                "trajectory instead."
            ),
        })
    elif abs(ratio - 1.0) < 0.02:
        insights.append({
            "level": "info",
            "title": "Timing barely matters for this inventory",
            "body": (
                "The dynamic and static totals agree to within two percent. "
                "Either the emissions are concentrated near the start of the "
                "window or they are dominated by long-lived gases. Either way "
                "the conventional figure is fine here, and it is worth knowing "
                "that rather than assuming it."
            ),
        })
    elif ratio < 1.0:
        insights.append({
            "level": "warning",
            "title": "The conventional figure overstates this by %.0f%%" % (
                (1.0 - ratio) * 100.0
            ),
            "body": (
                "Static GWP100 gives every emission a full century to act. "
                "Scored to %s these emissions have less time than that, so "
                "the honest total is %.0f kg CO2e rather than %.0f. The "
                "difference is %.0f kg and it is entirely a timing effect."
                % (
                    result["target_year"],
                    result["dynamic_total_co2e"],
                    result["static_total_co2e"],
                    abs(difference),
                )
            ),
        })
    else:
        insights.append({
            "level": "warning",
            "title": "The conventional figure understates this by %.0f%%" % (
                (ratio - 1.0) * 100.0
            ),
            "body": (
                "The window to %s is longer than the hundred years static "
                "GWP100 assumes, so these emissions have more time to act, "
                "not less. Adding %.0f kg CO2e to the reported total."
                % (result["target_year"], abs(difference))
            ),
        })

    worst = dominant_divergence(result)
    if worst and abs(worst["difference"]) > 1e-9:
        direction = "down" if worst["difference"] < 0 else "up"
        insights.append({
            "level": "info",
            "title": "%s accounts for most of the movement" % worst["label"],
            "body": (
                "It moves the total %s by %.0f kg CO2e on its own. %s"
                % (direction, abs(worst["difference"]), GASES[worst["gas"]]["note"])
            ),
        })

    if result["declining_at_target"]:
        insights.append({
            "level": "info",
            "title": "Forcing peaks in %s and is falling by the target"
                     % result["peak_year"],
            "body": (
                "Peak forcing is %.3g W/m2 and %.3g W/m2 is still acting in "
                "%s. A pathway that satisfies a cumulative budget can still "
                "overshoot a temperature ceiling on the way, which is what "
                "the gap between those two numbers describes."
                % (
                    result["peak_forcing"],
                    result["forcing_at_target"],
                    result["target_year"],
                )
            ),
        })

    late = [row for row in result["emissions"] if row["years_available"] < 20]
    if late:
        share = sum(abs(row["static_co2e"]) for row in late)
        total = sum(abs(row["static_co2e"]) for row in result["emissions"])
        if total > 0 and share / total > 0.1:
            insights.append({
                "level": "warning",
                "title": "%.0f%% of this inventory is emitted in the last "
                         "twenty years of the window" % (share / total * 100.0),
                "body": (
                    "Those emissions are scored on how much they do before "
                    "the target, which is not much. Move the target further "
                    "out and they will score higher. That sensitivity is real "
                    "and it is worth checking a second target year before "
                    "acting on this."
                ),
            })

    return insights


def emission_table(result):
    """The per-emission comparison, newest first, ready to render."""
    return sorted(
        result["emissions"],
        key=lambda row: (row["year"], row["gas"]),
    )


def category_table(result):
    """Category totals under both methods, largest static first."""
    rows = []
    for category, values in result["by_category"].items():
        rows.append({
            "category": category,
            "dynamic_co2e": values["dynamic"],
            "static_co2e": values["static"],
            "difference_co2e": values["dynamic"] - values["static"],
            "amount_kg": values["amount_kg"],
            "ratio": (
                values["dynamic"] / values["static"] if values["static"] else None
            ),
        })
    rows.sort(key=lambda row: abs(row["static_co2e"]), reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dynamic_lca_inventories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            target_year INTEGER NOT NULL,
            dynamic_total REAL NOT NULL,
            static_total REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_dynamic_lca_inventories_user
        ON dynamic_lca_inventories (user_id)
        """
    )


def save_inventory(user_id, inventory, result):
    """Persist an inventory with the score it produced. Returns the row id."""
    if not user_id:
        raise DynamicLCAError("A saved inventory needs a user to belong to.")

    payload = json.dumps({
        "emissions": inventory["emissions"],
        "base_year": inventory["base_year"],
        "target_year": result["target_year"],
        "ratio": result["ratio"],
        "peak_year": result["peak_year"],
        "peak_forcing": result["peak_forcing"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO dynamic_lca_inventories
                (user_id, name, payload, target_year, dynamic_total, static_total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), inventory["name"], payload,
                int(result["target_year"]),
                float(result["dynamic_total_co2e"]),
                float(result["static_total_co2e"]),
            ),
        )
        return int(cursor.lastrowid)


def get_inventories(user_id, limit=25):
    """Saved inventories for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, target_year, dynamic_total,
                       static_total, created_at
                FROM dynamic_lca_inventories
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved dynamic LCA inventories")
        return []

    saved = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        saved.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "target_year": row[3],
            "dynamic_total": row[4],
            "static_total": row[5],
            "created_at": row[6],
        })
    return saved


def delete_inventory(user_id, inventory_id):
    """Delete one saved inventory. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM dynamic_lca_inventories WHERE id = ? AND user_id = ?",
                (inventory_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete dynamic LCA inventory")
        return False


# ---------------------------------------------------------------------------
# Reference helpers
# ---------------------------------------------------------------------------

def list_gases():
    """Every supported gas with its published and derived parameters."""
    entries = []
    for key in sorted(GASES, key=lambda item: GASES[item]["label"]):
        definition = GASES[key]
        entries.append({
            "key": key,
            "label": definition["label"],
            "formula": definition["formula"],
            "lifetime": definition["lifetime"],
            "gwp100": definition["gwp100"],
            "gwp20": gwp(key, 20),
            "gwp20_published": definition["gwp20_published"],
            "gwp20_deviation": (
                gwp(key, 20) / definition["gwp20_published"] - 1.0
                if definition["gwp20_published"] else None
            ),
            "gwp500": gwp(key, 500),
            "kind": definition["kind"],
            "note": definition["note"],
            "radiative_efficiency": radiative_efficiency(key),
        })
    return entries


def model_fidelity():
    """How far the calibrated model lands from the published GWP20 values.

    The calibration is anchored at a hundred years, so agreement at twenty is
    a property of the decay model rather than an input. Reporting the gap is
    the only way a reader can tell which results are limited by the model and
    which are limited by the data.
    """
    rows = []
    for entry in list_gases():
        if entry["key"] == "co2" or not entry["gwp20_published"]:
            continue
        rows.append({
            "key": entry["key"],
            "label": entry["label"],
            "modelled_gwp20": entry["gwp20"],
            "published_gwp20": entry["gwp20_published"],
            "deviation": entry["gwp20_deviation"],
            "within_tolerance": abs(entry["gwp20_deviation"]) <= 0.05,
        })
    rows.sort(key=lambda row: abs(row["deviation"]), reverse=True)
    return rows


def get_gas(key):
    """One gas entry, or ``None`` if it is not supported."""
    for entry in list_gases():
        if entry["key"] == key:
            return entry
    return None


def list_metrics():
    """Every metric, with the question it actually answers."""
    return [dict(value, key=key) for key, value in METRICS.items()]


def describe_metric(key):
    """One metric definition, or ``None``."""
    if key not in METRICS:
        return None
    return dict(METRICS[key], key=key)
