"""When to replace something, which is not the question payback answers.

``src/carbon/carbon_payback.py`` answers "if I buy this now, when does it turn
positive?" That is a useful question and it is not the one a user with a
working boiler is asking. They are asking *when* to replace it, and the two
have different answers because payback silently assumes the only alternative
to acting now is never acting at all.

Three things move while somebody waits, and all three are already modelled
elsewhere in this repository:

*   The grid gets cleaner, so the saving from electrification grows every year
    the decision is deferred (``src/energy/grid_intensity_simulator.py``).
*   The incumbent keeps running and eventually fails anyway, so part of the
    replacement burden is unavoidable and merely dated
    (``src/utils/device_lifecycle.py``).
*   Manufacturing gets cleaner and cheaper, so the cost of waiting falls.

The sign flip, which is the whole point
-----------------------------------------
A decarbonising grid makes waiting *valuable* for electrification and *costly*
for efficiency. Swap a gas boiler for a heat pump and the saving grows every
year, because the thing you are switching to keeps improving. Swap an
inefficient electric appliance for an efficient one and the saving shrinks,
because the emissions being avoided are falling on their own.

Those have opposite signs. Every tool in this app treats them identically, and
a payback figure cannot distinguish them, because a ratio has no time axis.

Early replacement scraps carbon that is already paid for
----------------------------------------------------------
Retiring a functioning appliance discards the remaining service life of an
emission that has already happened. Nothing in this repo charges that to the
decision, which is why the tools here will happily recommend replacing a
five-year-old efficient appliance to gain a marginal improvement.

Failure is stochastic and the decision is not
-----------------------------------------------
An appliance replaced on failure incurs no early-scrappage penalty at all.
Optimal timing has to weigh a planned replacement against a hazard-weighted
forced one, or it will always recommend planning. Failure is modelled with a
Weibull hazard conditioned on the incumbent's current age, because an
appliance that has already survived twelve years is not the same risk as a new
one with the same rated life.

One assumption stated plainly: the planned paths assume the incumbent survives
to the chosen year. That is not certain, so the survival probability is
reported next to every year rather than folded into the total. Mixing the two
would produce a curve that is neither a plan nor an expectation.

The horizon is a boundary, and boundaries leak
------------------------------------------------
The new unit's embodied carbon is charged pro-rata for the share of its life
actually used inside the horizon. That is the consistent treatment - operating
emissions past the horizon are not counted either, so the embodied burden that
buys them should not be - but it does mean a later replacement carries a
smaller embodied charge, and part of any "wait" recommendation is therefore an
artefact of where the horizon was drawn.

``horizon_sensitivity`` re-runs the search at several horizons and reports
whether the optimum moves. A recommendation that survives is about the
appliance; one that does not is about the boundary, and the module says which.

Carbon and cost are not blended
---------------------------------
They frequently disagree, and the disagreement is the most useful thing on the
page. A single combined score would bury it. A shadow carbon price is
available for anyone who wants one, and it is labelled with its value.

Where this connects to code already merged
--------------------------------------------
*   ``src/carbon/carbon_payback.py`` handles the purchase decision, which is a
    different problem. This module refuses to run without an incumbent and
    points there.
*   ``src/carbon/abatement_curve.py`` ranks by cost per tonne with no time
    dimension, so an option that is poor today and excellent in four years
    ranks poor, permanently.
*   ``src/utils/device_lifecycle.py`` already recommends replacements. Adding
    timing does not add a recommendation; it corrects one that exists.

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


class ReplacementTimingError(ValueError):
    """Raised when a timing question cannot be answered from what was given."""


#: Fuels. ``grid_linked`` fuels take the grid trajectory; everything else is
#: constant, which is the asymmetry that produces the sign flip.
FUELS = {
    "electricity": {
        "label": "Electricity",
        "grid_linked": True,
        "intensity": None,
        "price_per_kwh": 0.28,
        "note": (
            "The only fuel here that improves on its own. Everything that "
            "runs on it inherits the grid's trajectory, which is why "
            "electrification and efficiency point in opposite directions "
            "under a decarbonising grid."
        ),
    },
    "natural_gas": {
        "label": "Natural gas",
        "grid_linked": False,
        "intensity": 0.202,
        "price_per_kwh": 0.09,
        "note": (
            "Constant. A gas appliance is exactly as dirty in 2040 as it is "
            "today, which is the entire case for switching off it."
        ),
    },
    "heating_oil": {
        "label": "Heating oil",
        "grid_linked": False,
        "intensity": 0.267,
        "price_per_kwh": 0.11,
        "note": "Constant, and the dirtiest common heating fuel here.",
    },
    "lpg": {
        "label": "LPG",
        "grid_linked": False,
        "intensity": 0.214,
        "price_per_kwh": 0.13,
        "note": "Constant. Between gas and oil on carbon, above both on price.",
    },
}

#: A floor on grid intensity. Extrapolating an exponential decline to zero
#: produces a free grid within a lifetime, which is not a forecast anyone
#: should base a purchase on.
GRID_FLOOR = 0.015

MAX_HORIZON = 60


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

def _fuel(key):
    if key is None:
        raise ReplacementTimingError("A fuel is required.")
    normalised = str(key).strip().lower()
    if normalised not in FUELS:
        known = ", ".join(sorted(FUELS))
        raise ReplacementTimingError(
            "Unknown fuel '%s'. Known: %s." % (key, known)
        )
    return normalised


def list_fuels():
    """Every fuel, with whether it improves on its own."""
    return [
        dict(FUELS[key], key=key)
        for key in sorted(FUELS, key=lambda item: FUELS[item]["label"])
    ]


def get_fuel(key):
    """One fuel, or ``None``."""
    if key not in FUELS:
        return None
    return dict(FUELS[key], key=key)


def build_grid(initial_intensity=0.25, annual_decline=0.04, floor=GRID_FLOOR):
    """A grid trajectory. A declining one is the default because grids decline."""
    initial = float(initial_intensity)
    if initial <= 0:
        raise ReplacementTimingError("Grid intensity must be positive.")
    decline = float(annual_decline)
    if not 0 <= decline < 1:
        raise ReplacementTimingError(
            "Annual decline must be at least 0 and below 1. A decline of 1 "
            "would zero the grid in a single year."
        )
    limit = float(floor)
    if limit < 0:
        raise ReplacementTimingError("The grid floor cannot be negative.")
    if limit > initial:
        raise ReplacementTimingError(
            "The floor is above the starting intensity, which describes a "
            "grid that gets dirtier and is not what this parameter is for."
        )
    return {"initial": initial, "decline": decline, "floor": limit}


def grid_intensity(grid, year):
    """Grid intensity in a given year of the horizon."""
    offset = float(year)
    if offset < 0:
        raise ReplacementTimingError("Year offsets start at zero.")
    projected = grid["initial"] * ((1.0 - grid["decline"]) ** offset)
    return max(projected, grid["floor"])


def fuel_intensity(fuel, grid, year):
    """Emission intensity of a fuel in a given year, kg CO2e per kWh."""
    key = _fuel(fuel)
    if FUELS[key]["grid_linked"]:
        return grid_intensity(grid, year)
    return FUELS[key]["intensity"]


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

def build_unit(label, fuel, annual_energy_kwh, expected_life_years,
               embodied_kg_co2, capital_cost=0.0, age_years=0.0,
               weibull_shape=2.5, annual_maintenance_cost=0.0):
    """One appliance, incumbent or replacement.

    ``weibull_shape`` above 1 means the hazard rises with age, which is what
    wear-out looks like. A shape of 1 is a constant hazard - memoryless, and
    wrong for anything mechanical.
    """
    if not label or not str(label).strip():
        raise ReplacementTimingError("A unit needs a label.")
    key = _fuel(fuel)

    energy = float(annual_energy_kwh)
    if energy < 0:
        raise ReplacementTimingError("Annual energy cannot be negative.")

    life = float(expected_life_years)
    if life <= 0:
        raise ReplacementTimingError("Expected life must be positive.")

    embodied = float(embodied_kg_co2)
    if embodied < 0:
        raise ReplacementTimingError("Embodied carbon cannot be negative.")

    age = float(age_years)
    if age < 0:
        raise ReplacementTimingError("Age cannot be negative.")

    shape = float(weibull_shape)
    if shape <= 0:
        raise ReplacementTimingError("The Weibull shape must be positive.")

    capital = float(capital_cost)
    if capital < 0:
        raise ReplacementTimingError("Capital cost cannot be negative.")

    maintenance = float(annual_maintenance_cost)
    if maintenance < 0:
        raise ReplacementTimingError("Maintenance cost cannot be negative.")

    return {
        "label": str(label).strip(),
        "fuel": key,
        "annual_energy_kwh": energy,
        "expected_life_years": life,
        "embodied_kg_co2": embodied,
        "capital_cost": capital,
        "age_years": age,
        "weibull_shape": shape,
        "annual_maintenance_cost": maintenance,
        "remaining_life_years": max(0.0, life - age),
    }


def weibull_scale(unit):
    """Scale parameter implied by the rated life and shape.

    Derived from the mean rather than taken as an input, because a rated life
    is what product data actually gives you and a scale parameter is not.
    """
    shape = unit["weibull_shape"]
    return unit["expected_life_years"] / math.gamma(1.0 + 1.0 / shape)


def survival_probability(unit, years_from_now):
    """Probability the incumbent is still working after this many more years.

    Conditioned on its current age. An appliance that has already survived
    twelve years is not the same risk as a new one with the same rated life,
    and treating them alike is the usual error here.
    """
    span = float(years_from_now)
    if span < 0:
        raise ReplacementTimingError("Cannot survive backwards.")

    shape = unit["weibull_shape"]
    scale = weibull_scale(unit)
    age = unit["age_years"]

    survives_to_age = math.exp(-((age + span) / scale) ** shape)
    survives_to_now = math.exp(-((age / scale) ** shape)) if age > 0 else 1.0
    if survives_to_now <= 0:
        return 0.0
    return min(1.0, survives_to_age / survives_to_now)


def failure_distribution(unit, horizon_years):
    """Probability the incumbent fails in each year of the horizon."""
    span = int(horizon_years)
    if span <= 0:
        raise ReplacementTimingError("A horizon needs at least one year.")

    rows = []
    for offset in range(span):
        before = survival_probability(unit, offset)
        after = survival_probability(unit, offset + 1)
        rows.append({
            "year": offset,
            "survives_to_start": before,
            "fails_this_year": before - after,
        })
    return rows


def expected_failure_year(unit, horizon_years):
    """Expected year of failure within the horizon, and the chance it survives."""
    distribution = failure_distribution(unit, horizon_years)
    weighted = sum(
        (row["year"] + 0.5) * row["fails_this_year"] for row in distribution
    )
    fails = sum(row["fails_this_year"] for row in distribution)
    survives = survival_probability(unit, horizon_years)
    return {
        "expected_year": (weighted / fails) if fails > 0 else None,
        "probability_fails_within_horizon": fails,
        "probability_survives_horizon": survives,
    }


# ---------------------------------------------------------------------------
# Path evaluation
# ---------------------------------------------------------------------------

def _operating_carbon(unit, grid, year):
    return unit["annual_energy_kwh"] * fuel_intensity(unit["fuel"], grid, year)


def _operating_cost(unit, energy_prices, year):
    price = energy_prices.get(unit["fuel"], FUELS[unit["fuel"]]["price_per_kwh"])
    return unit["annual_energy_kwh"] * price + unit["annual_maintenance_cost"]


def scrappage_charge(incumbent, replacement_year):
    """Embodied carbon discarded by retiring the incumbent early.

    The share of the incumbent's rated life still unused at the moment it is
    thrown away. Zero once it has passed its rated life, because there is
    nothing left to waste.
    """
    remaining = incumbent["remaining_life_years"] - float(replacement_year)
    if remaining <= 0:
        return 0.0
    return incumbent["embodied_kg_co2"] * (
        remaining / incumbent["expected_life_years"]
    )


def _replacement_embodied_used(replacement, years_in_service):
    """Only the share of the new unit's life actually used inside the horizon."""
    used = min(1.0, max(0.0, years_in_service) / replacement["expected_life_years"])
    return replacement["embodied_kg_co2"] * used


def evaluate_year(incumbent, replacement, grid, horizon_years,
                  replacement_year, energy_prices=None, discount_rate=0.03,
                  capital_decline=0.0):
    """Total carbon and cost if the swap happens in ``replacement_year``.

    ``replacement_year == horizon_years`` is the do-nothing path: keep the
    incumbent for the whole horizon and never replace within it.
    """
    prices = energy_prices or {}
    horizon = int(horizon_years)
    when = int(replacement_year)
    if not 0 <= when <= horizon:
        raise ReplacementTimingError(
            "Replacement year %d is outside the horizon of %d years."
            % (when, horizon)
        )

    rate = float(discount_rate)
    if not 0 <= rate < 1:
        raise ReplacementTimingError("Discount rate must be at least 0 and below 1.")

    decline = float(capital_decline)
    if not 0 <= decline < 1:
        raise ReplacementTimingError(
            "Capital decline must be at least 0 and below 1."
        )

    carbon = 0.0
    cost = 0.0
    yearly = []

    for year in range(horizon):
        unit = incumbent if year < when else replacement
        year_carbon = _operating_carbon(unit, grid, year)
        year_cost = _operating_cost(unit, prices, year)
        discount = (1.0 + rate) ** -year

        carbon += year_carbon
        cost += year_cost * discount
        yearly.append({
            "year": year,
            "unit": unit["label"],
            "carbon": year_carbon,
            "cost": year_cost,
        })

    embodied = 0.0
    scrapped = 0.0
    capital = 0.0
    if when < horizon:
        embodied = _replacement_embodied_used(replacement, horizon - when)
        scrapped = scrappage_charge(incumbent, when)
        capital = (
            replacement["capital_cost"]
            * ((1.0 - decline) ** when)
            * ((1.0 + rate) ** -when)
        )

    carbon += embodied + scrapped
    cost += capital

    return {
        "replacement_year": when,
        "do_nothing": when == horizon,
        "operating_carbon": carbon - embodied - scrapped,
        "embodied_carbon": embodied,
        "scrappage_carbon": scrapped,
        "total_carbon": carbon,
        "capital_cost": capital,
        "operating_cost": cost - capital,
        "total_cost": cost,
        "survival_probability": survival_probability(incumbent, when),
        "yearly": yearly,
    }


def evaluate(incumbent, replacement, grid, horizon_years=25,
             energy_prices=None, discount_rate=0.03, capital_decline=0.0,
             shadow_carbon_price=None):
    """Search every replacement year and report where the optimum sits.

    The whole horizon is searched rather than adjacent years compared,
    because the curve is not monotonic: waiting improves the electrification
    case and worsens the efficiency case, and an interior optimum is exactly
    what a pairwise comparison misses.
    """
    if incumbent is None:
        raise ReplacementTimingError(
            "There is no incumbent, so this is a purchase decision rather "
            "than a timing one. src/carbon/carbon_payback.py answers that."
        )
    horizon = int(horizon_years)
    if horizon <= 0:
        raise ReplacementTimingError("A horizon needs at least one year.")
    if horizon > MAX_HORIZON:
        raise ReplacementTimingError(
            "A horizon beyond %d years is longer than the trajectories here "
            "can support." % MAX_HORIZON
        )
    if horizon < replacement["expected_life_years"]:
        raise ReplacementTimingError(
            "A horizon of %d years is shorter than the replacement's %g-year "
            "life. That would cut off part of the new unit's operating "
            "burden and flatter it."
            % (horizon, replacement["expected_life_years"])
        )

    paths = [
        evaluate_year(
            incumbent, replacement, grid, horizon, year,
            energy_prices, discount_rate, capital_decline,
        )
        for year in range(horizon + 1)
    ]

    best_carbon = min(paths, key=lambda row: row["total_carbon"])
    best_cost = min(paths, key=lambda row: row["total_cost"])
    do_nothing = paths[-1]
    act_now = paths[0]

    combined = None
    if shadow_carbon_price is not None:
        price = float(shadow_carbon_price)
        if price < 0:
            raise ReplacementTimingError("A shadow carbon price cannot be negative.")
        for path in paths:
            path["combined_cost"] = (
                path["total_cost"] + path["total_carbon"] / 1000.0 * price
            )
        combined = min(paths, key=lambda row: row["combined_cost"])

    failure = expected_failure_year(incumbent, horizon)
    on_failure = None
    if failure["expected_year"] is not None:
        on_failure = evaluate_year(
            incumbent, replacement, grid, horizon,
            min(horizon, int(round(failure["expected_year"]))),
            energy_prices, discount_rate, capital_decline,
        )

    return {
        "horizon_years": horizon,
        "paths": paths,
        "optimal_carbon_year": best_carbon["replacement_year"],
        "optimal_carbon": best_carbon["total_carbon"],
        "optimal_cost_year": best_cost["replacement_year"],
        "optimal_cost": best_cost["total_cost"],
        "optimal_combined_year": (
            combined["replacement_year"] if combined else None
        ),
        "shadow_carbon_price": shadow_carbon_price,
        "objectives_agree": best_carbon["replacement_year"] == best_cost["replacement_year"],
        "act_now": act_now,
        "do_nothing": do_nothing,
        "acting_now_costs": act_now["total_carbon"] - best_carbon["total_carbon"],
        "failure": failure,
        "replace_on_failure": on_failure,
        "incumbent": incumbent,
        "replacement": replacement,
        "grid": grid,
    }


# ---------------------------------------------------------------------------
# Regret and break-even
# ---------------------------------------------------------------------------

def regret(result, objective="carbon"):
    """The penalty for acting a year early and a year late.

    Not symmetric, and the asymmetry is more actionable than the optimal year
    itself. A flat optimum means the timing does not much matter; a sharp one
    means it does, and that distinction is what a user can act on.
    """
    field = "total_carbon" if objective == "carbon" else "total_cost"
    if objective not in {"carbon", "cost"}:
        raise ReplacementTimingError(
            "Objective must be 'carbon' or 'cost'; they are not blended by "
            "default because they frequently disagree."
        )

    best_year = (
        result["optimal_carbon_year"] if objective == "carbon"
        else result["optimal_cost_year"]
    )
    by_year = {row["replacement_year"]: row for row in result["paths"]}
    best = by_year[best_year][field]

    early = by_year.get(best_year - 1)
    late = by_year.get(best_year + 1)

    tolerance = abs(best) * 0.02
    within = [
        row["replacement_year"] for row in result["paths"]
        if abs(row[field] - best) <= tolerance
    ]

    return {
        "objective": objective,
        "optimal_year": best_year,
        "optimal_value": best,
        "one_year_early": (early[field] - best) if early else None,
        "one_year_late": (late[field] - best) if late else None,
        "acting_now": by_year[0][field] - best,
        "never_acting": by_year[result["horizon_years"]][field] - best,
        "years_within_two_percent": sorted(within),
        "flat_optimum": len(within) >= 5,
        "note": (
            "The optimum is flat: %d different years land within two percent "
            "of the best. The timing is not the decision here; whether to act "
            "at all is."
            % len(within)
            if len(within) >= 5 else
            "The optimum is sharp: only %d year%s are within two percent. "
            "Getting the timing wrong has a real cost."
            % (len(within), "" if len(within) == 1 else "s")
        ),
    }


def break_even_grid_intensity(incumbent, replacement, horizon_years,
                              decline=0.0, tolerance=1e-6):
    """The constant grid intensity at which acting now equals never acting.

    Turns an opaque recommendation into a condition a user can check against
    their own region. Solved by bisection because the totals are monotone in
    the intensity but not analytically invertible once a floor is involved.
    """
    def difference(intensity):
        grid = build_grid(intensity, decline, floor=min(GRID_FLOOR, intensity))
        now = evaluate_year(
            incumbent, replacement, grid, horizon_years, 0
        )["total_carbon"]
        never = evaluate_year(
            incumbent, replacement, grid, horizon_years, horizon_years
        )["total_carbon"]
        return now - never

    low, high = 0.001, 2.0
    if difference(low) * difference(high) > 0:
        return {
            "break_even_intensity": None,
            "note": (
                "Acting now is better at every plausible grid intensity, or "
                "worse at all of them. There is no threshold to check, which "
                "is itself a stronger answer than a number."
            ),
            "act_now_better_at_clean_grid": difference(low) < 0,
        }

    for _ in range(200):
        middle = (low + high) / 2.0
        if difference(low) * difference(middle) <= 0:
            high = middle
        else:
            low = middle
        if high - low < tolerance:
            break

    threshold = (low + high) / 2.0
    return {
        "break_even_intensity": threshold,
        "note": (
            "Replacing now beats keeping the incumbent while the grid is "
            "above %.3f kg CO2e/kWh, and loses below it. Look up your own "
            "region's figure rather than taking the recommendation."
            % threshold
        ),
        "act_now_better_at_clean_grid": difference(0.001) < 0,
    }


def grid_sensitivity(incumbent, replacement, horizon_years,
                     initial_intensity=0.25, declines=(0.0, 0.02, 0.04, 0.06)):
    """Where the optimum moves as the grid's trajectory changes.

    The demonstration that matters: the same appliance recommending 'act now'
    under a static grid and 'wait' under a decarbonising one, or the reverse.
    """
    rows = []
    for decline in declines:
        grid = build_grid(initial_intensity, decline)
        result = evaluate(incumbent, replacement, grid, horizon_years)
        rows.append({
            "decline": decline,
            "optimal_carbon_year": result["optimal_carbon_year"],
            "optimal_carbon": result["optimal_carbon"],
            "acting_now_costs": result["acting_now_costs"],
        })
    years = {row["optimal_carbon_year"] for row in rows}
    return {
        "rows": rows,
        "recommendation_moves": len(years) > 1,
        "span": max(row["optimal_carbon_year"] for row in rows)
                - min(row["optimal_carbon_year"] for row in rows),
    }


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

def horizon_sensitivity(incumbent, replacement, grid,
                        horizons=(20, 25, 30, 40)):
    """Whether the recommendation survives a different horizon.

    The new unit's embodied carbon is charged only for the share of its life
    used inside the horizon, so a later replacement carries a smaller charge.
    Part of any "wait" answer is therefore about where the boundary was drawn
    rather than about the appliance, and the only honest response is to move
    the boundary and look.
    """
    usable = [
        int(span) for span in horizons
        if span >= replacement["expected_life_years"] and span <= MAX_HORIZON
    ]
    if not usable:
        raise ReplacementTimingError(
            "No horizon in %s is long enough for a replacement with a "
            "%g-year life." % (list(horizons), replacement["expected_life_years"])
        )

    rows = []
    for span in usable:
        result = evaluate(incumbent, replacement, grid, span)
        rows.append({
            "horizon": span,
            "optimal_carbon_year": result["optimal_carbon_year"],
            "acts_within_horizon": result["optimal_carbon_year"] < span,
        })

    years = {row["optimal_carbon_year"] for row in rows}
    acts = {row["acts_within_horizon"] for row in rows}
    return {
        "rows": rows,
        "optimum_moves": len(years) > 1,
        "decision_flips": len(acts) > 1,
        "note": (
            "The recommendation changes with the horizon, so part of it is "
            "about where the boundary was drawn rather than about the "
            "appliance. Treat the year loosely."
            if len(acts) > 1 else
            "Whether to act at all is the same at every horizon tested, which "
            "makes it a conclusion about the appliance."
        ),
    }


def get_timing_insights(result):
    """Plain-language findings, decision-relevant ones first."""
    insights = []
    best_year = result["optimal_carbon_year"]
    horizon = result["horizon_years"]

    if best_year == 0:
        insights.append({
            "level": "info",
            "title": "Act now",
            "body": (
                "Replacing immediately is the lowest-carbon path over %d "
                "years, and waiting costs %.0f kg CO2e per year of delay at "
                "the start of the curve."
                % (
                    horizon,
                    result["paths"][1]["total_carbon"]
                    - result["paths"][0]["total_carbon"],
                )
            ),
        })
    elif best_year >= horizon:
        insights.append({
            "level": "warning",
            "title": "Do not replace this within the horizon",
            "body": (
                "Keeping the incumbent for the whole %d years is the "
                "lowest-carbon path. Replacing now would add %.0f kg CO2e, "
                "mostly embodied carbon in the new unit and unused life "
                "scrapped from the old one."
                % (horizon, result["acting_now_costs"])
            ),
        })
    else:
        insights.append({
            "level": "info",
            "title": "Wait %d years, then replace" % best_year,
            "body": (
                "An interior optimum. Acting now costs %.0f kg CO2e more than "
                "waiting, and waiting the full horizon costs more still. "
                "A pairwise now-versus-never comparison would have missed "
                "this entirely."
                % result["acting_now_costs"]
            ),
        })

    if not result["objectives_agree"]:
        insights.append({
            "level": "warning",
            "title": "Carbon and cost disagree about when",
            "body": (
                "Lowest carbon at year %d, lowest cost at year %d. There is "
                "no calculation that resolves this; it is a question about "
                "what you are optimising. Blending them into one score would "
                "hide the disagreement, which is why this page does not."
                % (result["optimal_carbon_year"], result["optimal_cost_year"])
            ),
        })

    survival = result["paths"][best_year]["survival_probability"]
    if best_year > 0 and survival < 0.7:
        insights.append({
            "level": "warning",
            "title": "The incumbent probably will not last that long",
            "body": (
                "Only a %.0f%% chance it survives to year %d. The plan "
                "assumes it does; the replace-on-failure path does not, and "
                "on this unit that path is worth comparing against."
                % (survival * 100.0, best_year)
            ),
        })

    if result["replace_on_failure"]:
        on_failure = result["replace_on_failure"]
        difference = on_failure["total_carbon"] - result["optimal_carbon"]
        insights.append({
            "level": "info",
            "title": "Replacing on failure costs %.0f kg CO2e more than the plan"
                     % difference if difference > 0 else
                     "Replacing on failure is as good as any plan",
            "body": (
                "Expected failure around year %.1f, with a %.0f%% chance it "
                "survives the whole horizon. A forced replacement scraps no "
                "unused life, which is why waiting for it is often better "
                "than it sounds."
                % (
                    result["failure"]["expected_year"] or 0.0,
                    result["failure"]["probability_survives_horizon"] * 100.0,
                )
            ),
        })

    scrapped = result["act_now"]["scrappage_carbon"]
    if scrapped > 0:
        insights.append({
            "level": "info",
            "title": "Acting now scraps %.0f kg CO2e of paid-for life" % scrapped,
            "body": (
                "The incumbent has %.1f years of its rated life left. That "
                "embodied carbon has already been emitted and nothing in this "
                "app currently charges it to an early replacement."
                % result["incumbent"]["remaining_life_years"]
            ),
        })

    return insights


def compare_objectives(result):
    """Carbon and cost optima side by side, deliberately unblended."""
    by_year = {row["replacement_year"]: row for row in result["paths"]}
    return {
        "carbon_optimum": {
            "year": result["optimal_carbon_year"],
            "carbon": result["optimal_carbon"],
            "cost": by_year[result["optimal_carbon_year"]]["total_cost"],
        },
        "cost_optimum": {
            "year": result["optimal_cost_year"],
            "carbon": by_year[result["optimal_cost_year"]]["total_carbon"],
            "cost": result["optimal_cost"],
        },
        "agree": result["objectives_agree"],
        "carbon_penalty_of_cost_choice": (
            by_year[result["optimal_cost_year"]]["total_carbon"]
            - result["optimal_carbon"]
        ),
        "cost_penalty_of_carbon_choice": (
            by_year[result["optimal_carbon_year"]]["total_cost"]
            - result["optimal_cost"]
        ),
    }


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS replacement_timing_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            incumbent TEXT NOT NULL,
            replacement TEXT NOT NULL,
            payload TEXT NOT NULL,
            optimal_carbon_year INTEGER NOT NULL,
            optimal_cost_year INTEGER NOT NULL,
            optimal_carbon REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_replacement_timing_plans_user
        ON replacement_timing_plans (user_id)
        """
    )


def save_plan(user_id, result):
    """Persist a timing analysis and return its row id."""
    if not user_id:
        raise ReplacementTimingError("A saved plan needs a user to belong to.")

    payload = json.dumps({
        "horizon_years": result["horizon_years"],
        "grid": result["grid"],
        "objectives_agree": result["objectives_agree"],
        "acting_now_costs": result["acting_now_costs"],
        "expected_failure_year": result["failure"]["expected_year"],
        "incumbent_fuel": result["incumbent"]["fuel"],
        "replacement_fuel": result["replacement"]["fuel"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO replacement_timing_plans
                (user_id, incumbent, replacement, payload,
                 optimal_carbon_year, optimal_cost_year, optimal_carbon)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), result["incumbent"]["label"],
                result["replacement"]["label"], payload,
                int(result["optimal_carbon_year"]),
                int(result["optimal_cost_year"]),
                float(result["optimal_carbon"]),
            ),
        )
        return int(cursor.lastrowid)


def get_plans(user_id, limit=25):
    """Saved plans for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, incumbent, replacement, payload,
                       optimal_carbon_year, optimal_cost_year,
                       optimal_carbon, created_at
                FROM replacement_timing_plans
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved replacement timing plans")
        return []

    saved = []
    for row in rows:
        try:
            payload = json.loads(row[3])
        except (TypeError, ValueError):
            payload = {}
        saved.append({
            "id": row[0],
            "incumbent": row[1],
            "replacement": row[2],
            "payload": payload,
            "optimal_carbon_year": row[4],
            "optimal_cost_year": row[5],
            "optimal_carbon": row[6],
            "created_at": row[7],
        })
    return saved


def delete_plan(user_id, plan_id):
    """Delete one saved plan. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM replacement_timing_plans WHERE id = ? AND user_id = ?",
                (plan_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete replacement timing plan")
        return False
