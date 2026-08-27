"""Remaining personal carbon budget, and the equity choice behind it.

``src.utils.goals.py`` builds a pathway from the user's own baseline: take what you emit,
pick a percentage, draw a line. ``src.utils.overshoot.py`` reports Earth Overshoot Day from
a lookup table. Neither answers the question that decides whether a target means
anything - how much carbon this person can emit in total, ever, before their
share of a temperature limit is spent.

A percentage target is a statement about the person
----------------------------------------------------
A household emitting 20 tonnes that cuts 40% is at 12. One emitting 4 tonnes that
cuts 40% is at 2.4. Both hit a 40% target; only one is anywhere near a fair
share, and a pathway model that never references an external limit cannot tell
them apart. Percentage targets flatter high emitters by construction: the more
you emit, the easier your percentage is to achieve, and the further from a fair
share you remain when you achieve it.

A budget is cumulative, and that changes how targets work
----------------------------------------------------------
Warming responds to *total* CO2 emitted, near-linearly, not to the rate in any
one year. Two pathways ending at the same 2050 value can differ by a decade of
emissions in the area under them, and the one that delays is the one that
overshoots. So arriving on time is not sufficient, and starting late cannot be
recovered by finishing harder - past some delay the required rate exceeds
anything achievable and the budget is simply gone. That point needs saying
early, and a linear pathway to a target date cannot express it.

Fair share is contested, and pretending otherwise is the failure
-----------------------------------------------------------------
Equal per capita ignores that historical emissions already spent most of the
budget. Grandfathering - everyone cuts the same percentage from today - locks in
existing inequality by construction, and is the principle implicitly used by
every "cut 40%" target in existence, this repository's included. Contraction and
convergence starts from present emissions and converges to per-capita equality
by a chosen date, so the convergence date *is* the negotiation. Ability to pay
weights by income.

These produce personal budgets differing by more than an order of magnitude for
the same person. Silently picking one and reporting it as the answer is making a
political choice while presenting arithmetic, so several are always shown and
each is named.

The global budget is a distribution, not a number
--------------------------------------------------
Remaining budgets are quoted at a probability of staying below a temperature
limit, and the 83% figure is little more than half the 50% one. They also shrink
every year that passes, so the budget here is computed forward from a base year
by subtracting elapsed global emissions rather than stored as a constant that
quietly goes stale.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import math
import sqlite3
import logging
import datetime
from typing import Any

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

KG_PER_TONNE = 1000.0
TONNES_PER_GIGATONNE = 1e9

# The base year every budget below is quoted from. Elapsed global emissions are
# subtracted from it, so the figure ages correctly instead of going stale.
BUDGET_BASE_YEAR = 2020

# No society has sustained a reduction anywhere near this outside a collapse or
# a war. Above it a pathway is not a plan, and the module says so rather than
# printing a number that implies otherwise.
FEASIBLE_ANNUAL_REDUCTION = 0.20

DEFAULT_TARGET = 1.5
DEFAULT_LIKELIHOOD = 67
DEFAULT_CONVERGENCE_YEAR = 2050

EQUAL_PER_CAPITA = "equal_per_capita"
GRANDFATHERING = "grandfathering"
CONTRACTION_CONVERGENCE = "contraction_convergence"
ABILITY_TO_PAY = "ability_to_pay"

PRINCIPLES = (
    EQUAL_PER_CAPITA,
    GRANDFATHERING,
    CONTRACTION_CONVERGENCE,
    ABILITY_TO_PAY,
)

PRINCIPLE_LABELS = {
    EQUAL_PER_CAPITA: "Equal per capita",
    GRANDFATHERING: "Grandfathering",
    CONTRACTION_CONVERGENCE: "Contraction and convergence",
    ABILITY_TO_PAY: "Ability to pay",
}

PRINCIPLE_NOTES = {
    EQUAL_PER_CAPITA: (
        "Everyone alive gets the same remaining share. Simple, and it ignores "
        "that historical emissions already spent most of the budget - so it is "
        "generous to whoever spent it."
    ),
    GRANDFATHERING: (
        "Your share is proportional to what you already emit, so everyone cuts "
        "the same percentage. This is what every 'cut 40%' target implicitly "
        "assumes, and it locks in existing inequality by construction."
    ),
    CONTRACTION_CONVERGENCE: (
        "Starts from what you emit now and converges to equal per capita by a "
        "chosen date. The convergence date is the entire negotiation: set it "
        "far enough out and this becomes grandfathering."
    ),
    ABILITY_TO_PAY: (
        "Weights the per-capita share by income, on the basis that capacity to "
        "cut is not evenly distributed. The elasticity is a value judgement "
        "with no correct answer."
    ),
}

CONSTANT_PERCENTAGE = "constant_percentage"
LINEAR = "linear"
EXPONENTIAL = "exponential"
PATHWAYS = (CONSTANT_PERCENTAGE, LINEAR, EXPONENTIAL)

PATHWAY_LABELS = {
    CONSTANT_PERCENTAGE: "Constant percentage each year",
    LINEAR: "Straight line to zero",
    EXPONENTIAL: "Exponential decay",
}


class BudgetError(ValueError):
    """Raised when a budget or pathway cannot be computed as asked."""


# ---------------------------------------------------------------------------
# Global budgets
#
# Gigatonnes of CO2 remaining from the base year, by temperature target and by
# the probability of staying below it. The likelihood column is not a detail:
# for 1.5 degrees, insisting on 83% rather than 50% removes 40% of the budget.
# ---------------------------------------------------------------------------

GLOBAL_BUDGETS: dict[float, dict[int, float]] = {
    1.5: {50: 500.0, 67: 400.0, 83: 300.0},
    1.7: {50: 850.0, 67: 700.0, 83: 550.0},
    2.0: {50: 1350.0, 67: 1150.0, 83: 900.0},
}

TARGET_NOTES = {
    1.5: "The Paris Agreement's aspiration. On current emissions the budget at "
         "any likelihood is under a decade and a half.",
    1.7: "Between the two Paris limits. Quoted because the gap between 1.5 and "
         "2.0 is where most real pathways actually land.",
    2.0: "The Paris Agreement's outer limit - 'well below' this is the wording, "
         "which is not the same as reaching it.",
}

# Global CO2 emissions in gigatonnes, used to age the budget forward from its
# base year. 2020 is low because of the pandemic, which is a real fact about the
# budget and not an anomaly to be smoothed away.
GLOBAL_EMISSIONS: dict[int, float] = {
    2020: 34.8, 2021: 37.1, 2022: 37.5, 2023: 37.8,
    2024: 38.0, 2025: 38.2, 2026: 38.4,
}

WORLD_POPULATION: dict[int, float] = {
    2020: 7.84e9, 2021: 7.91e9, 2022: 7.98e9, 2023: 8.05e9,
    2024: 8.12e9, 2025: 8.18e9, 2026: 8.24e9,
}

# Used only by the ability-to-pay principle, and only as a reference point.
WORLD_AVERAGE_INCOME = 13000.0
DEFAULT_INCOME_ELASTICITY = 0.7


# ---------------------------------------------------------------------------
# The global budget, aged forward
# ---------------------------------------------------------------------------

def latest_data_year() -> int:
    """The most recent year with global emissions data."""
    return max(GLOBAL_EMISSIONS)


def current_year() -> int:
    """Today's year, clamped to what the tables can support."""
    return min(datetime.date.today().year, latest_data_year())


def list_targets() -> list[float]:
    """Temperature targets, coolest first."""
    return sorted(GLOBAL_BUDGETS)


def list_likelihoods(target: float = DEFAULT_TARGET) -> list[int]:
    """Likelihoods available for a target."""
    if target not in GLOBAL_BUDGETS:
        raise BudgetError(f"No budget for a {target} degree target")
    return sorted(GLOBAL_BUDGETS[target])


def remaining_global_budget(
    target: float = DEFAULT_TARGET,
    likelihood: int = DEFAULT_LIKELIHOOD,
    as_of: int | None = None,
) -> dict[str, Any]:
    """What is left of a global budget, computed forward from its base year.

    Storing a remaining budget as a constant makes it correct for one year and
    wrong every year after, in a way nobody notices. This subtracts the
    emissions that have actually happened since the base year instead.
    """
    if target not in GLOBAL_BUDGETS:
        raise BudgetError(
            f"No budget for a {target} degree target; have "
            f"{', '.join(str(value) for value in list_targets())}"
        )
    if likelihood not in GLOBAL_BUDGETS[target]:
        raise BudgetError(
            f"No {likelihood}% budget for {target} degrees; have "
            f"{', '.join(str(value) for value in list_likelihoods(target))}"
        )

    as_of = current_year() if as_of is None else int(as_of)
    if as_of < BUDGET_BASE_YEAR:
        raise BudgetError(f"Cannot look back before the base year {BUDGET_BASE_YEAR}")
    if as_of > latest_data_year():
        raise BudgetError(
            f"No global emissions data past {latest_data_year()}"
        )

    at_base = GLOBAL_BUDGETS[target][likelihood]
    elapsed = sum(
        GLOBAL_EMISSIONS[year] for year in range(BUDGET_BASE_YEAR, as_of)
    )
    remaining = at_base - elapsed

    annual = GLOBAL_EMISSIONS[as_of]
    return {
        "target": target,
        "likelihood": likelihood,
        "base_year": BUDGET_BASE_YEAR,
        "as_of": as_of,
        "at_base_year_gt": at_base,
        "elapsed_gt": round(elapsed, 2),
        "remaining_gt": round(remaining, 2),
        "spent_share": round(elapsed / at_base, 4) if at_base else 0.0,
        "annual_global_gt": annual,
        "years_at_current_rate": (
            round(remaining / annual, 2) if annual > 0 and remaining > 0 else 0.0
        ),
        "exhausted": remaining <= 0,
        "population": WORLD_POPULATION[as_of],
        "note": TARGET_NOTES[target],
    }


# ---------------------------------------------------------------------------
# Allocation principles
# ---------------------------------------------------------------------------

def _global_path(remaining_gt: float, annual_gt: float) -> tuple[float, float]:
    """A linear global phase-out consistent with the remaining budget.

    Area under a triangle: a straight line from today's emissions to zero over
    T years encloses ``annual * T / 2``, so the budget fixes T. Used by
    contraction and convergence, which needs a global path to converge onto.
    """
    if annual_gt <= 0:
        raise BudgetError("Global emissions must be positive")
    if remaining_gt <= 0:
        return 0.0, 0.0
    years = 2.0 * remaining_gt / annual_gt
    return years, annual_gt


def personal_budget(
    annual_tonnes: float,
    principle: str = EQUAL_PER_CAPITA,
    target: float = DEFAULT_TARGET,
    likelihood: int = DEFAULT_LIKELIHOOD,
    convergence_year: int = DEFAULT_CONVERGENCE_YEAR,
    income: float | None = None,
    elasticity: float = DEFAULT_INCOME_ELASTICITY,
    as_of: int | None = None,
) -> dict[str, Any]:
    """One person's remaining budget in tonnes, under one equity principle."""
    if annual_tonnes <= 0:
        raise BudgetError("Annual emissions must be positive")
    if principle not in PRINCIPLES:
        raise BudgetError(f"Unknown allocation principle: {principle}")

    global_budget = remaining_global_budget(target, likelihood, as_of)
    remaining_gt = global_budget["remaining_gt"]
    population = global_budget["population"]
    annual_global_gt = global_budget["annual_global_gt"]
    year = global_budget["as_of"]

    per_capita_tonnes = (
        remaining_gt * TONNES_PER_GIGATONNE / population if remaining_gt > 0 else 0.0
    )
    global_per_capita_now = annual_global_gt * TONNES_PER_GIGATONNE / population

    detail: dict[str, Any] = {}

    if principle == EQUAL_PER_CAPITA:
        budget = per_capita_tonnes

    elif principle == GRANDFATHERING:
        # Share proportional to current src.carbon.emissions. Someone emitting three times
        # the world average gets three times the budget, which is the whole
        # objection to it.
        share = annual_tonnes / global_per_capita_now
        budget = per_capita_tonnes * share
        detail["share_of_average"] = round(share, 4)

    elif principle == CONTRACTION_CONVERGENCE:
        if convergence_year <= year:
            # Converging today is exactly equal per capita.
            budget = per_capita_tonnes
            detail["converged_immediately"] = True
        else:
            phase_out_years, start = _global_path(remaining_gt, annual_global_gt)
            if phase_out_years <= 0:
                budget = 0.0
            else:
                steps = max(1, int(math.ceil(phase_out_years)))
                allowances = [
                    start * max(0.0, 1.0 - (step / phase_out_years))
                    for step in range(steps)
                ]
                # The triangle's continuous area is the budget, but a discrete
                # sum over whole years is not - it overshoots by about half a
                # year's allowance. Rescaling so the annual allowances add to
                # exactly the remaining budget is what makes this comparable
                # with the other principles; without it, converging "today"
                # would not reproduce the equal per-capita answer, and the
                # blend would be reading off a path that spends more than
                # there is.
                total_allowance = sum(allowances)
                if total_allowance <= 0:
                    budget = 0.0
                else:
                    scale = remaining_gt / total_allowance
                    allowances = [value * scale for value in allowances]

                    # Weight runs from 1 (grandfathered) at the start to 0
                    # (equal per capita) at convergence. Each year's allocation
                    # is that blend of the two shares, applied to the global
                    # allowance for that year.
                    grandfather_share = annual_tonnes / global_per_capita_now
                    span = float(convergence_year - year)
                    budget = 0.0
                    for step, allowance_gt in enumerate(allowances):
                        weight = max(0.0, 1.0 - (step / span))
                        share = weight * grandfather_share + (1.0 - weight)
                        budget += (
                            share * allowance_gt * TONNES_PER_GIGATONNE / population
                        )
                detail["phase_out_years"] = round(phase_out_years, 2)
                detail["convergence_year"] = convergence_year

    else:
        income = WORLD_AVERAGE_INCOME if income is None else float(income)
        if income <= 0:
            raise BudgetError("Income must be positive for ability-to-pay")
        if elasticity < 0:
            raise BudgetError("Income elasticity cannot be negative")
        weight = (WORLD_AVERAGE_INCOME / income) ** elasticity
        budget = per_capita_tonnes * weight
        detail["income"] = income
        detail["elasticity"] = elasticity
        detail["weight"] = round(weight, 4)

    years_left = budget / annual_tonnes if annual_tonnes > 0 else 0.0
    return {
        "principle": principle,
        "principle_label": PRINCIPLE_LABELS[principle],
        "principle_note": PRINCIPLE_NOTES[principle],
        "target": target,
        "likelihood": likelihood,
        "as_of": year,
        "annual_tonnes": annual_tonnes,
        "budget_tonnes": round(budget, 3),
        "equal_share_tonnes": round(per_capita_tonnes, 3),
        "relative_to_equal_share": (
            round(budget / per_capita_tonnes, 4) if per_capita_tonnes > 0 else None
        ),
        "years_at_current_rate": round(years_left, 2),
        "depletion_year": (
            year + years_left if years_left < 500 else None
        ),
        "already_over": budget <= 0,
        "detail": detail,
    }


def compare_principles(
    annual_tonnes: float,
    target: float = DEFAULT_TARGET,
    likelihood: int = DEFAULT_LIKELIHOOD,
    convergence_year: int = DEFAULT_CONVERGENCE_YEAR,
    income: float | None = None,
    as_of: int | None = None,
) -> dict[str, Any]:
    """All four principles side by side, because one alone is a political claim."""
    rows = [
        personal_budget(
            annual_tonnes, principle, target, likelihood,
            convergence_year, income, as_of=as_of,
        )
        for principle in PRINCIPLES
    ]
    budgets = [row["budget_tonnes"] for row in rows]
    low, high = min(budgets), max(budgets)
    return {
        "annual_tonnes": annual_tonnes,
        "target": target,
        "likelihood": likelihood,
        "rows": sorted(rows, key=lambda row: row["budget_tonnes"]),
        "low_tonnes": round(low, 3),
        "high_tonnes": round(high, 3),
        "spread_tonnes": round(high - low, 3),
        "ratio": round(high / low, 3) if low > 0 else None,
        "note": (
            "These are the same person under four defensible principles. "
            "Reporting one of them as the answer would be presenting a "
            "political choice as arithmetic."
        ),
    }


# ---------------------------------------------------------------------------
# Pathways
#
# The binding constraint is the area under the curve, not the endpoint. Each of
# these has a closed form for the rate that exactly spends a budget, which is
# why none of them needs to be searched for numerically.
# ---------------------------------------------------------------------------

def required_rate(
    annual_tonnes: float,
    budget_tonnes: float,
    pathway: str = CONSTANT_PERCENTAGE,
) -> dict[str, Any]:
    """The reduction rate that spends exactly the budget and no more.

    Constant percentage: cumulative emissions of ``e0`` falling by ``r`` a year
    sum to ``e0 / r``, so ``r = e0 / budget``. Linear to zero over ``T`` years
    encloses ``e0 T / 2``, so ``T = 2 budget / e0``. Exponential at continuous
    rate ``k`` integrates to ``e0 / k``, so ``k = e0 / budget``.

    All three are exact. A budget smaller than a single year's emissions has no
    solution at any rate, and that is reported rather than returned as a number
    above 1.
    """
    if annual_tonnes <= 0:
        raise BudgetError("Annual emissions must be positive")
    if pathway not in PATHWAYS:
        raise BudgetError(f"Unknown pathway: {pathway}")

    if budget_tonnes <= 0:
        return {
            "pathway": pathway,
            "pathway_label": PATHWAY_LABELS[pathway],
            "feasible": False,
            "achievable": False,
            "annual_reduction": None,
            "years_to_zero": None,
            "reason": "The budget is already spent; no reduction rate reaches it.",
        }

    if pathway == CONSTANT_PERCENTAGE:
        rate = annual_tonnes / budget_tonnes
        achievable = rate < 1.0
        years = (
            math.log(0.01) / math.log(1.0 - rate) if 0 < rate < 1 else None
        )
    elif pathway == LINEAR:
        years = 2.0 * budget_tonnes / annual_tonnes
        rate = 1.0 / years if years > 0 else None
        achievable = rate is not None and rate < 1.0
    else:
        rate_continuous = annual_tonnes / budget_tonnes
        rate = 1.0 - math.exp(-rate_continuous)
        achievable = rate < 1.0
        years = math.log(100.0) / rate_continuous if rate_continuous > 0 else None

    feasible = achievable and rate is not None and rate <= FEASIBLE_ANNUAL_REDUCTION
    reason = ""
    if not achievable:
        reason = (
            "No reduction rate spends this budget - a single year at current "
            "emissions would already exceed it."
        )
    elif not feasible:
        reason = (
            f"The required {rate:.1%} a year is above the {FEASIBLE_ANNUAL_REDUCTION:.0%} "
            "that anything short of a collapse has ever sustained. This is not "
            "a plan; the gap has to come from somewhere other than reduction."
        )

    return {
        "pathway": pathway,
        "pathway_label": PATHWAY_LABELS[pathway],
        # Rounded finely on purpose: these are the rates that make a pathway
        # spend exactly its budget, and integrating a coarsely rounded rate
        # back over forty years misses by enough to matter.
        "annual_reduction": round(rate, 9) if rate is not None else None,
        "years_to_zero": round(years, 6) if years is not None else None,
        "budget_tonnes": round(budget_tonnes, 3),
        "achievable": achievable,
        "feasible": feasible,
        "reason": reason,
    }


def pathway_series(
    annual_tonnes: float,
    budget_tonnes: float,
    pathway: str = CONSTANT_PERCENTAGE,
    years: int = 40,
) -> list[dict[str, Any]]:
    """Year-by-year emissions and the budget draining underneath them."""
    result = required_rate(annual_tonnes, budget_tonnes, pathway)
    rate = result["annual_reduction"]
    rows: list[dict[str, Any]] = []
    remaining = budget_tonnes
    emissions = annual_tonnes

    for year in range(years):
        if rate is None:
            emissions = annual_tonnes
        elif pathway == CONSTANT_PERCENTAGE:
            emissions = annual_tonnes * ((1.0 - rate) ** year)
        elif pathway == LINEAR:
            span = result["years_to_zero"] or 1.0
            emissions = max(0.0, annual_tonnes * (1.0 - year / span))
        else:
            continuous = annual_tonnes / budget_tonnes if budget_tonnes > 0 else 0.0
            emissions = annual_tonnes * math.exp(-continuous * year)
        remaining -= emissions
        rows.append({
            "year": year,
            "emissions_tonnes": round(emissions, 4),
            "remaining_budget": round(remaining, 4),
            "overspent": remaining < 0,
        })
    return rows


def cost_of_delay(
    annual_tonnes: float,
    budget_tonnes: float,
    delays: tuple[int, ...] = (0, 1, 2, 3, 5, 10),
    pathway: str = CONSTANT_PERCENTAGE,
) -> list[dict[str, Any]]:
    """What waiting costs, expressed as the rate needed afterwards.

    Every year of delay spends a year's emissions out of the budget, and the
    rate required thereafter is inversely proportional to what is left - so the
    cost of delay compounds rather than adding. That is not intuitive, and it is
    the strongest argument this module can make.
    """
    if annual_tonnes <= 0:
        raise BudgetError("Annual emissions must be positive")

    baseline = required_rate(annual_tonnes, budget_tonnes, pathway)
    rows = []
    for delay in delays:
        left = budget_tonnes - annual_tonnes * delay
        result = required_rate(annual_tonnes, left, pathway)
        rows.append({
            "delay_years": delay,
            "budget_left": round(max(0.0, left), 3),
            "annual_reduction": result["annual_reduction"],
            "achievable": result["achievable"],
            "feasible": result["feasible"],
            "multiple_of_acting_now": (
                round(result["annual_reduction"] / baseline["annual_reduction"], 3)
                if result["annual_reduction"] and baseline["annual_reduction"]
                else None
            ),
        })
    return rows


def shortfall(
    annual_tonnes: float,
    budget_tonnes: float,
) -> dict[str, Any]:
    """What is left over when reduction alone cannot close the gap.

    At the fastest sustained rate anyone has managed, cumulative emissions come
    to ``e0 / ceiling``. If that exceeds the budget, the difference has to come
    from removals rather than reduction - and that is where
    ``src.utils.permanence_accounting.py`` becomes relevant, and where the honest answer
    stops being a comfortable one.
    """
    if annual_tonnes <= 0:
        raise BudgetError("Annual emissions must be positive")

    best_case_cumulative = annual_tonnes / FEASIBLE_ANNUAL_REDUCTION
    gap = best_case_cumulative - budget_tonnes
    return {
        "annual_tonnes": annual_tonnes,
        "budget_tonnes": round(budget_tonnes, 3),
        "ceiling_rate": FEASIBLE_ANNUAL_REDUCTION,
        "best_case_cumulative_tonnes": round(best_case_cumulative, 3),
        "shortfall_tonnes": round(max(0.0, gap), 3),
        "closable_by_reduction": gap <= 0,
        "note": (
            "Cutting at the fastest rate anyone has sustained still leaves "
            f"{max(0.0, gap):,.1f} tonnes to be removed rather than avoided."
            if gap > 0 else
            "Reduction alone can stay inside this budget."
        ),
    }


def sensitivity(
    annual_tonnes: float,
    convergence_year: int = DEFAULT_CONVERGENCE_YEAR,
    income: float | None = None,
) -> list[dict[str, Any]]:
    """The parameters that move a personal budget, and by how much."""
    rows: list[dict[str, Any]] = []

    for target in list_targets():
        for likelihood in list_likelihoods(target):
            result = personal_budget(
                annual_tonnes, EQUAL_PER_CAPITA, target, likelihood
            )
            rows.append({
                "parameter": "Budget definition",
                "setting": f"{target}C at {likelihood}% likelihood",
                "budget_tonnes": result["budget_tonnes"],
                "years_left": result["years_at_current_rate"],
            })

    for principle in PRINCIPLES:
        result = personal_budget(
            annual_tonnes, principle, convergence_year=convergence_year,
            income=income,
        )
        rows.append({
            "parameter": "Equity principle",
            "setting": PRINCIPLE_LABELS[principle],
            "budget_tonnes": result["budget_tonnes"],
            "years_left": result["years_at_current_rate"],
        })

    for year in (2030, 2040, 2050, 2070, 2100):
        result = personal_budget(
            annual_tonnes, CONTRACTION_CONVERGENCE, convergence_year=year
        )
        rows.append({
            "parameter": "Convergence date",
            "setting": f"Converge by {year}",
            "budget_tonnes": result["budget_tonnes"],
            "years_left": result["years_at_current_rate"],
        })

    return rows


def get_budget_insights(comparison: dict[str, Any]) -> list[str]:
    """Plain-language readings of a principle comparison."""
    if not comparison.get("rows"):
        return ["Nothing to analyse."]

    insights: list[str] = []
    rows = comparison["rows"]
    lowest, highest = rows[0], rows[-1]

    if comparison.get("ratio"):
        insights.append(
            f"The same person, the same target: "
            f"{lowest['budget_tonnes']:,.0f} tonnes under "
            f"{lowest['principle_label'].lower()} and "
            f"{highest['budget_tonnes']:,.0f} under "
            f"{highest['principle_label'].lower()} — a factor of "
            f"{comparison['ratio']:.1f}. The choice between them is not "
            "arithmetic."
        )

    equal = next(
        (row for row in rows if row["principle"] == EQUAL_PER_CAPITA), None
    )
    if equal:
        if equal["years_at_current_rate"] < 1:
            insights.append(
                "On an equal per-capita share, this year's emissions alone "
                "spend the whole remaining budget."
            )
        else:
            insights.append(
                f"On an equal per-capita share there are "
                f"{equal['years_at_current_rate']:.1f} years left at the "
                "current rate — which is a statement about arithmetic, not "
                "about what happens next."
            )

    grandfathered = next(
        (row for row in rows if row["principle"] == GRANDFATHERING), None
    )
    if grandfathered and equal and grandfathered["budget_tonnes"] > equal["budget_tonnes"]:
        insights.append(
            "Grandfathering gives this person more than an equal share, "
            "because they already emit more than the average. Every "
            "percentage-reduction target makes that assumption without "
            "stating it."
        )

    insights.append(
        "A budget is cumulative, so the area under the pathway is what binds, "
        "not the value it ends at. Two plans reaching the same number in 2050 "
        "are not equivalent."
    )
    return insights


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def init_budget_db() -> bool:
    """Create the table if it does not exist yet."""
    conn = None
    try:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS carbon_budget_scenarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                annual_tonnes REAL NOT NULL,
                target REAL NOT NULL,
                likelihood INTEGER NOT NULL,
                principle TEXT NOT NULL,
                budget_tonnes REAL NOT NULL,
                years_left REAL,
                detail_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Unable to initialise carbon budget table: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_scenario(user_id: int, name: str, result: dict[str, Any]) -> int | None:
    """Persist a scenario. Returns the row id or None."""
    init_budget_db()
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            """
            INSERT INTO carbon_budget_scenarios (
                user_id, name, annual_tonnes, target, likelihood,
                principle, budget_tonnes, years_left, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(name),
                float(result.get("annual_tonnes", 0.0)),
                float(result.get("target", DEFAULT_TARGET)),
                int(result.get("likelihood", DEFAULT_LIKELIHOOD)),
                str(result.get("principle", EQUAL_PER_CAPITA)),
                float(result.get("budget_tonnes", 0.0)),
                float(result.get("years_at_current_rate", 0.0)),
                json.dumps(result),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save budget scenario: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_scenarios(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Saved scenarios, newest first."""
    init_budget_db()
    conn = None
    try:
        conn = _connect()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM carbon_budget_scenarios
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        scenarios = []
        for row in rows:
            record = dict(row)
            if record.get("detail_json"):
                try:
                    record["detail"] = json.loads(record["detail_json"])
                except (TypeError, ValueError):
                    record["detail"] = None
            scenarios.append(record)
        return scenarios
    except sqlite3.Error as exc:
        logger.error("Unable to read budget scenarios: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def delete_scenario(scenario_id: int, user_id: int) -> bool:
    """Delete a scenario the user owns."""
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            "DELETE FROM carbon_budget_scenarios WHERE id = ? AND user_id = ?",
            (int(scenario_id), int(user_id)),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Unable to delete budget scenario: %s", exc)
        return False
    finally:
        if conn:
            conn.close()
