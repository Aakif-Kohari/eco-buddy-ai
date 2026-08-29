"""How long an adopted action actually lasts, which the app assumes is forever.

When a user adopts an action - cycle to work, meat-free Mondays, wash at 30 -
this app multiplies the per-occurrence saving by a year and reports the result.
``src.ai.recommendation_engine.py``, ``src.lifestyle.lifestyle_optimizer.py``,
``src.carbon.abatement_curve.py`` and the pledge modules all do it. The
arithmetic assumes the behaviour lasts twelve months.

Most behaviours do not. Adoption is easy and maintenance is not, and the
majority of self-initiated behaviour changes lapse within months. Nothing in
this codebase represents that, so every annualised saving it reports is an
upper bound presented as an estimate, wrong in a known direction, every time.

The principle is already established here for stored carbon
-------------------------------------------------------------
``src.carbon.permanence_accounting.py`` says a tonne that leaks back is not a
tonne saved, and does ton-year accounting to prove it. The same argument
applies to behaviour. This module is that argument, for habits.

The abatement curve currently ranks fragile options above durable ones
-----------------------------------------------------------------------
``src.carbon.abatement_curve.py`` sorts by cost per tonne on undiscounted
annual savings. Loft insulation delivers for thirty years with no further
effort. A commitment to shorter showers has a half-life measured in weeks.
Ranking them on the same undiscounted figure systematically favours the
fragile option, which is exactly backwards, and the re-ranking here is the most
consequential thing in the module.

A single decay constant cannot express the effect that matters most
--------------------------------------------------------------------
The useful thing to tell someone about a new habit is that the first month is
the hard part. That is a *decreasing* hazard - survive the early period and the
odds improve - and an exponential model, which has constant hazard by
definition, cannot represent it at all. Weibull can, through its shape
parameter, and the shape is where the substance of each action class sits.

Right-censoring is not a detail
---------------------------------
An action still running at the end of the observation window has not lapsed.
Counting it as a lapse biases every estimate downward, and it is the most
common way an empirical persistence estimate goes wrong. The Kaplan-Meier
estimator here handles it properly and there is a test that a fully-censored
history produces a survival curve of one rather than zero.

Lapse and relapse are different events
----------------------------------------
Someone who stops cycling in January and resumes in March has not abandoned
the action. A seasonal pattern and an abandonment produce very different
expected savings from identical raw data, and the module tests for the shape
before reporting either.

Where this connects to code already merged
--------------------------------------------
*   ``src.carbon.permanence_accounting.py`` - same principle, different
    reversal mechanism. That module handles geological and biological
    permanence; this handles human maintenance.
*   ``src.carbon.abatement_curve.py`` - consumes the adjusted savings and
    re-ranks.
*   ``src.lifestyle.sustainability_challenges_streaks.py`` - a streak on a
    high-hazard action and a streak on a structural change carry entirely
    different information about the next forty days.
*   ``src.utils.rebound_effect.py`` - efficiency gains partly returning as
    consumption. This is the other way a projected saving fails to arrive.

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


class PersistenceError(ValueError):
    """Raised when a persistence question cannot be answered as asked."""


PERIODS_PER_YEAR = 52  # The module works in weeks throughout.


# ---------------------------------------------------------------------------
# Action classes
#
# The shape parameter carries the substance and is the reason for Weibull
# rather than a decay constant:
#
#   k < 1  hazard falls with time. Get past the first month and the odds
#          improve. This is the shape of most effortful habits and the effect
#          an exponential model cannot express.
#   k = 1  constant hazard. Memoryless: a year in is no safer than week one.
#   k > 1  hazard rises with time. Something wears out - equipment, novelty,
#          the goodwill of whoever else has to cooperate.
#
# Scale is in weeks and is the characteristic lifetime, not the median. The
# median is derived. Parameters are drawn from the behaviour-change and energy
# feedback literature, are contested, and are stated with what they rest on so
# a reader can disagree with a specific number rather than the whole idea.
# ---------------------------------------------------------------------------
ACTION_CLASSES = {
    "structural_one_off": {
        "label": "Structural one-off",
        "shape": 6.0,
        "scale": 1560.0,
        "requires_effort": False,
        "note": "An appliance replaced, a tariff switched, a standing order "
                "moved to a different supplier. Once done it keeps delivering "
                "with no further attention, and the failure mode is the "
                "equipment reaching end of life rather than the person losing "
                "interest. Modelled with a high shape so the hazard stays near "
                "zero and then rises, which is a wear-out curve rather than a "
                "decay curve.",
        "evidence": "Retrofit and tariff-switching persistence studies "
                    "consistently show near-total retention until physical "
                    "replacement.",
    },
    "equipment_mediated": {
        "label": "Equipment-mediated habit",
        "shape": 0.9,
        "scale": 190.0,
        "requires_effort": True,
        "note": "A habit supported by something bought for the purpose - a "
                "drying rack, a bike, a smart thermostat schedule. The object "
                "acts as a standing reminder and a sunk cost, so these last "
                "considerably longer than bare habits, but they still need a "
                "person to keep using them.",
        "evidence": "Energy feedback and equipment-supported behaviour "
                    "studies report substantially slower decay than "
                    "information-only interventions.",
    },
    "daily_effort": {
        "label": "Daily effort habit",
        "shape": 0.7,
        "scale": 34.0,
        "requires_effort": True,
        "note": "Something that must be decided again every day: shorter "
                "showers, lights off, a specific commute. The shape below one "
                "is the important part - the hazard is highest in the first "
                "weeks and falls for anyone who gets through them, which is "
                "why 'the first month is the hard part' is worth telling "
                "someone and why a constant-hazard model is the wrong tool.",
        "evidence": "Habit formation studies place automaticity at a median "
                    "of roughly two months with very wide spread; attrition "
                    "concentrates well before that point.",
    },
    "periodic_effort": {
        "label": "Periodic effort habit",
        "shape": 0.8,
        "scale": 62.0,
        "requires_effort": True,
        "note": "Weekly or monthly rather than daily - a meal plan, a "
                "batch-cooking routine, a monthly meter reading. Fewer "
                "decisions means fewer chances to stop, which more than "
                "compensates for the weaker cue.",
        "evidence": "Lower decision frequency is associated with slower "
                    "attrition in dietary and household-routine studies.",
    },
    "social_dependent": {
        "label": "Needs someone else to cooperate",
        "shape": 0.85,
        "scale": 24.0,
        "requires_effort": True,
        "note": "A car share, a household-wide thermostat agreement, a "
                "shared meal plan. The shortest-lived class here, because it "
                "fails if any participant stops rather than only if the user "
                "does. Advice that ignores this recommends the most fragile "
                "options to the households least able to sustain them.",
        "evidence": "Multi-person commitments show compounding attrition; the "
                    "scale here reflects joint rather than individual "
                    "survival.",
    },
}


# A saving after this many weeks is discounted so heavily by any sensible rate
# that extending the horizon further changes nothing a user would act on.
DEFAULT_HORIZON_WEEKS = 260
DEFAULT_DISCOUNT_RATE = 0.03  # annual

# Below this share of adopters lapsing inside the horizon, a re-engagement
# window is not a useful object: any prompt scheduled into it reaches almost
# entirely people who were never going to stop.
MINIMUM_LAPSE_SHARE = 0.02


# ---------------------------------------------------------------------------
# Weibull
# ---------------------------------------------------------------------------
def _class_parameters(action_class):
    if action_class not in ACTION_CLASSES:
        raise PersistenceError(
            f"{action_class!r} is not a known action class. Known classes: "
            f"{', '.join(ACTION_CLASSES)}."
        )
    meta = ACTION_CLASSES[action_class]
    return float(meta["shape"]), float(meta["scale"])


def survival(weeks, shape, scale):
    """S(t) = exp(-(t/scale)^shape). The share still doing it at week t."""
    t = float(weeks)
    if t < 0:
        raise PersistenceError("Time cannot be negative.")
    if shape <= 0 or scale <= 0:
        raise PersistenceError(
            "Weibull shape and scale must both be positive."
        )
    if t == 0:
        return 1.0
    return math.exp(-((t / float(scale)) ** float(shape)))


def hazard(weeks, shape, scale):
    """The instantaneous rate of lapse at week t.

    Falling for shape < 1, flat at 1, rising above. The sign of that slope is
    the whole reason this module does not use an exponential.
    """
    t = float(weeks)
    if t < 0:
        raise PersistenceError("Time cannot be negative.")
    if shape <= 0 or scale <= 0:
        raise PersistenceError(
            "Weibull shape and scale must both be positive."
        )
    if t == 0:
        return float("inf") if shape < 1 else (
            float(shape) / float(scale) if shape == 1 else 0.0
        )
    return (float(shape) / float(scale)) * ((t / float(scale)) ** (float(shape) - 1.0))


def median_lifetime(shape, scale):
    """The week by which half of adopters have stopped."""
    if shape <= 0 or scale <= 0:
        raise PersistenceError(
            "Weibull shape and scale must both be positive."
        )
    return float(scale) * (math.log(2.0) ** (1.0 / float(shape)))


def survival_curve(action_class, horizon_weeks=DEFAULT_HORIZON_WEEKS,
                   step=4):
    """The survival curve for one action class, sampled every ``step`` weeks."""
    shape, scale = _class_parameters(action_class)
    points = []
    week = 0
    while week <= horizon_weeks:
        points.append({
            "week": week,
            "survival": round(survival(week, shape, scale), 6),
            "hazard": round(
                hazard(max(week, 0.5), shape, scale), 8
            ),
        })
        week += step
    return points


def class_summary(action_class):
    """Everything a page needs to describe one class."""
    shape, scale = _class_parameters(action_class)
    meta = ACTION_CLASSES[action_class]
    median = median_lifetime(shape, scale)
    return {
        "key": action_class,
        "label": meta["label"],
        "shape": shape,
        "scale_weeks": scale,
        "median_weeks": round(median, 2),
        "median_months": round(median / 4.345, 2),
        "survival_at_13_weeks": round(survival(13, shape, scale), 4),
        "survival_at_26_weeks": round(survival(26, shape, scale), 4),
        "survival_at_52_weeks": round(survival(52, shape, scale), 4),
        "hazard_direction": (
            "falling" if shape < 1 else "flat" if shape == 1 else "rising"
        ),
        "requires_effort": meta["requires_effort"],
        "note": meta["note"],
        "evidence": meta["evidence"],
    }


# ---------------------------------------------------------------------------
# Expected savings
# ---------------------------------------------------------------------------
def expected_savings(weekly_saving, action_class,
                     horizon_weeks=DEFAULT_HORIZON_WEEKS,
                     discount_rate=DEFAULT_DISCOUNT_RATE,
                     shape=None, scale=None):
    """Savings integrated against the survival curve rather than assumed.

    The honest number to put on a recommendation card. For most habit classes
    it is well below the naive annualisation the app currently reports, and the
    gap is the overstatement.
    """
    saving = float(weekly_saving)
    if saving < 0:
        raise PersistenceError(
            "A weekly saving cannot be negative. An action that increases "
            "emissions is not a saving with a minus sign in front of it - it "
            "belongs in a different calculation."
        )
    if horizon_weeks <= 0:
        raise PersistenceError("A horizon must be at least one week.")

    if shape is None or scale is None:
        shape, scale = _class_parameters(action_class)

    weekly_discount = (1.0 + float(discount_rate)) ** (1.0 / PERIODS_PER_YEAR)

    expected = 0.0
    undiscounted = 0.0
    first_year = 0.0
    for week in range(1, int(horizon_weeks) + 1):
        alive = survival(week, shape, scale)
        undiscounted += saving * alive
        discounted = saving * alive / (weekly_discount ** week)
        expected += discounted
        if week <= PERIODS_PER_YEAR:
            first_year += discounted

    naive_year = saving * PERIODS_PER_YEAR
    return {
        "weekly_saving": round(saving, 4),
        "action_class": action_class,
        "horizon_weeks": int(horizon_weeks),
        "expected_lifetime_saving": round(expected, 3),
        "expected_undiscounted": round(undiscounted, 3),
        "expected_first_year": round(first_year, 3),
        "naive_first_year": round(naive_year, 3),
        "first_year_overstatement": round(naive_year - first_year, 3),
        "first_year_overstatement_share": (
            round((naive_year - first_year) / naive_year, 4)
            if naive_year else 0.0
        ),
        "effective_weeks": round(
            expected / saving, 2
        ) if saving else 0.0,
    }


def persistence_adjusted_ranking(options, horizon_weeks=DEFAULT_HORIZON_WEEKS,
                                 discount_rate=DEFAULT_DISCOUNT_RATE):
    """Re-rank a set of options on expected rather than assumed savings.

    The most consequential function here. Ranking on undiscounted annual
    savings favours whichever option is most fragile, because fragility is
    invisible to that measure.
    """
    if not options:
        raise PersistenceError("There are no options to rank.")

    rows = []
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            raise PersistenceError("Each option must be a mapping.")
        name = str(option.get("name") or f"Option {index + 1}")
        weekly = float(option.get("weekly_saving", 0.0))
        action_class = option.get("action_class")
        cost = float(option.get("cost", 0.0))

        result = expected_savings(
            weekly, action_class, horizon_weeks, discount_rate
        )
        naive_annual = weekly * PERIODS_PER_YEAR
        rows.append({
            "name": name,
            "action_class": action_class,
            "class_label": ACTION_CLASSES[action_class]["label"],
            "weekly_saving": round(weekly, 4),
            "cost": round(cost, 2),
            "naive_annual_saving": round(naive_annual, 3),
            "expected_lifetime_saving": result["expected_lifetime_saving"],
            "expected_first_year": result["expected_first_year"],
            "overstatement_share": result["first_year_overstatement_share"],
            "naive_cost_per_unit": (
                round(cost / naive_annual, 4) if naive_annual else None
            ),
            "adjusted_cost_per_unit": (
                round(cost / result["expected_lifetime_saving"], 4)
                if result["expected_lifetime_saving"] else None
            ),
        })

    naive_order = sorted(
        rows, key=lambda r: r["naive_annual_saving"], reverse=True
    )
    adjusted_order = sorted(
        rows, key=lambda r: r["expected_lifetime_saving"], reverse=True
    )

    naive_positions = {row["name"]: i for i, row in enumerate(naive_order)}
    moves = []
    for position, row in enumerate(adjusted_order):
        was = naive_positions[row["name"]]
        row["naive_rank"] = was + 1
        row["adjusted_rank"] = position + 1
        row["rank_change"] = was - position
        if row["rank_change"] != 0:
            moves.append(row)

    return {
        "options": adjusted_order,
        "ranking_changed": bool(moves),
        "moved": sorted(moves, key=lambda r: abs(r["rank_change"]),
                        reverse=True),
        "horizon_weeks": int(horizon_weeks),
        "discount_rate": discount_rate,
    }


# ---------------------------------------------------------------------------
# Re-engagement timing
# ---------------------------------------------------------------------------
def reengagement_window(action_class, horizon_weeks=104):
    """The weeks in which most lapses actually happen.

    Defined on the unconditional density of lapse rather than the hazard rate,
    because for a decreasing-hazard class the hazard is highest at week zero
    and a prompt sent then reaches someone who has not started yet. What a
    notification wants is the window carrying the largest mass of lapses, which
    is a different quantity and is the one computed here.
    """
    shape, scale = _class_parameters(action_class)

    density = []
    for week in range(1, int(horizon_weeks) + 1):
        lapsed = survival(week - 1, shape, scale) - survival(week, shape, scale)
        density.append((week, lapsed))

    total = sum(value for _, value in density)
    if total < MINIMUM_LAPSE_SHARE:
        return {
            "action_class": action_class,
            "peak_week": None,
            "window": None,
            "share_in_window": 0.0,
            "share_lapsing_in_horizon": round(total, 4),
            "note": f"Only {total * 100:.1f}% of adopters lapse inside "
                    f"{horizon_weeks} weeks, so there is no window worth "
                    f"prompting into. Sending a re-engagement nudge here would "
                    f"reach almost entirely people who were never going to "
                    f"stop.",
        }

    peak_week = max(density, key=lambda item: item[1])[0]

    # The interquartile window of lapse times: the middle half of everyone who
    # stops. Reported rather than the peak alone, because for a decreasing
    # hazard the peak is always week one and a window is what a notification
    # schedule actually needs.
    cumulative = 0.0
    low = None
    high = density[-1][0]
    for week, value in density:
        cumulative += value
        if low is None and cumulative >= 0.25 * total:
            low = week
        if cumulative >= 0.75 * total:
            high = week
            break
    if low is None:
        low = density[0][0]
    if low > high:
        low, high = high, low

    in_window = sum(
        value for week, value in density if low <= week <= high
    )

    return {
        "action_class": action_class,
        "peak_week": peak_week,
        "window": [low, high],
        "share_in_window": round(in_window / total, 4),
        "share_lapsing_in_horizon": round(total, 4),
        "note": f"Half of all lapses inside {horizon_weeks} weeks fall between "
                f"week {low} and week {high}. A prompt outside that window "
                f"reaches people who were not going to stop anyway.",
    }


# ---------------------------------------------------------------------------
# Empirical survival
# ---------------------------------------------------------------------------
def kaplan_meier(events):
    """Non-parametric survival from the user's own adoption history.

    ``events`` is a sequence of mappings with ``duration_weeks`` and
    ``censored``. An action still running at the end of the observation window
    is censored, not lapsed, and counting it as a lapse is the most common way
    an empirical persistence estimate goes wrong.
    """
    if not events:
        raise PersistenceError("There is no history to estimate from.")

    cleaned = []
    for event in events:
        if not isinstance(event, dict):
            raise PersistenceError("Each event must be a mapping.")
        if "duration_weeks" not in event:
            raise PersistenceError(
                "Each event needs a duration_weeks."
            )
        duration = float(event["duration_weeks"])
        if duration < 0:
            raise PersistenceError("A duration cannot be negative.")
        cleaned.append({
            "duration": duration,
            "censored": bool(event.get("censored", False)),
        })

    cleaned.sort(key=lambda item: (item["duration"], item["censored"]))
    total = len(cleaned)

    at_risk = total
    curve = [{"week": 0.0, "survival": 1.0, "at_risk": total, "lapses": 0}]
    running = 1.0
    index = 0

    while index < total:
        time = cleaned[index]["duration"]
        lapses = 0
        censored = 0
        while index < total and cleaned[index]["duration"] == time:
            if cleaned[index]["censored"]:
                censored += 1
            else:
                lapses += 1
            index += 1

        if lapses and at_risk > 0:
            running *= (1.0 - lapses / at_risk)
            curve.append({
                "week": time,
                "survival": round(running, 6),
                "at_risk": at_risk,
                "lapses": lapses,
            })
        at_risk -= (lapses + censored)

    observed = sum(1 for item in cleaned if not item["censored"])
    return {
        "curve": curve,
        "events": total,
        "observed_lapses": observed,
        "censored": total - observed,
        "final_survival": round(running, 6),
        "median_weeks": _median_from_curve(curve),
        "fully_censored": observed == 0,
    }


def _median_from_curve(curve):
    for point in curve:
        if point["survival"] <= 0.5:
            return point["week"]
    return None


def blend_with_prior(empirical, action_class, weeks=52):
    """Combine the user's own history with the class prior, weighted by data.

    A user with three lapse events does not have enough history to override a
    class parameter, and one with forty does. The weight is the share of
    observed lapses against a reference count rather than a hand-set constant,
    so the blend moves continuously as history accumulates.
    """
    shape, scale = _class_parameters(action_class)
    prior = survival(weeks, shape, scale)

    observed = empirical.get("observed_lapses", 0)
    reference = 20.0
    weight = min(1.0, observed / reference)

    empirical_value = 1.0
    for point in empirical.get("curve", []):
        if point["week"] <= weeks:
            empirical_value = point["survival"]

    blended = weight * empirical_value + (1.0 - weight) * prior
    return {
        "weeks": weeks,
        "prior_survival": round(prior, 4),
        "empirical_survival": round(empirical_value, 4),
        "weight_on_own_history": round(weight, 4),
        "blended_survival": round(blended, 4),
        "note": (
            f"{observed} observed lapse{'s' if observed != 1 else ''} carries "
            f"{weight * 100:.0f}% of the weight. With fewer than {int(reference)} "
            f"the class prior still dominates, which is the correct behaviour "
            f"for an estimate this noisy."
        ),
    }


# ---------------------------------------------------------------------------
# Seasonality
# ---------------------------------------------------------------------------
def seasonal_reactivation(lapse_months, resume_months=None):
    """Distinguish a seasonal pattern from an abandonment.

    A lapse that recurs on the same calendar boundary each year is not the same
    event as an action being given up, and identical raw data produces very
    different expected savings under the two readings. Concentration is
    measured on the circle, because December and January are adjacent and a
    linear spread would call that pattern diffuse.
    """
    if not lapse_months:
        raise PersistenceError("There are no lapse months to examine.")

    months = []
    for value in lapse_months:
        month = int(value)
        if not 1 <= month <= 12:
            raise PersistenceError(
                f"{value!r} is not a month between 1 and 12."
            )
        months.append(month)

    angles = [2.0 * math.pi * (month - 1) / 12.0 for month in months]
    mean_cos = sum(math.cos(angle) for angle in angles) / len(angles)
    mean_sin = sum(math.sin(angle) for angle in angles) / len(angles)
    concentration = math.sqrt(mean_cos ** 2 + mean_sin ** 2)

    mean_angle = math.atan2(mean_sin, mean_cos)
    if mean_angle < 0:
        mean_angle += 2.0 * math.pi
    mean_month = int(round(mean_angle / (2.0 * math.pi) * 12.0)) % 12 + 1

    seasonal = concentration > 0.6 and len(months) >= 3
    resumed = len(resume_months or [])

    return {
        "lapses": len(months),
        "concentration": round(concentration, 4),
        "typical_month": mean_month,
        "seasonal": seasonal,
        "resumptions": resumed,
        "note": (
            f"Lapses cluster around month {mean_month} with a circular "
            f"concentration of {concentration:.2f}. This reads as a seasonal "
            f"pattern rather than abandonment, and the expected savings should "
            f"be computed as a recurring gap rather than a one-way exit."
            if seasonal else
            f"Lapses are spread across the calendar (concentration "
            f"{concentration:.2f}). Nothing here supports treating them as "
            f"seasonal, so the survival model stands."
        ),
    }


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------
def portfolio_persistence(actions, horizons=(13, 26, 52, 104)):
    """Expected surviving savings across a whole plan.

    Twelve fragile habits and three structural changes can carry identical
    headline totals and completely different year-two realities. This is where
    that shows up.
    """
    if not actions:
        raise PersistenceError("There are no actions in this portfolio.")

    prepared = []
    for index, action in enumerate(actions):
        action_class = action.get("action_class")
        shape, scale = _class_parameters(action_class)
        prepared.append({
            "name": str(action.get("name") or f"Action {index + 1}"),
            "action_class": action_class,
            "class_label": ACTION_CLASSES[action_class]["label"],
            "weekly_saving": float(action.get("weekly_saving", 0.0)),
            "shape": shape,
            "scale": scale,
        })

    naive_weekly = sum(item["weekly_saving"] for item in prepared)

    points = []
    for weeks in horizons:
        surviving = sum(
            item["weekly_saving"] * survival(weeks, item["shape"], item["scale"])
            for item in prepared
        )
        points.append({
            "weeks": weeks,
            "months": round(weeks / 4.345, 1),
            "surviving_weekly_saving": round(surviving, 4),
            "assumed_weekly_saving": round(naive_weekly, 4),
            "retained_share": (
                round(surviving / naive_weekly, 4) if naive_weekly else 0.0
            ),
        })

    per_action = []
    for item in prepared:
        per_action.append({
            "name": item["name"],
            "class_label": item["class_label"],
            "weekly_saving": round(item["weekly_saving"], 4),
            "survival_at_52": round(
                survival(52, item["shape"], item["scale"]), 4
            ),
            "surviving_at_52": round(
                item["weekly_saving"]
                * survival(52, item["shape"], item["scale"]), 4
            ),
        })
    per_action.sort(key=lambda row: row["weekly_saving"], reverse=True)

    fragile = [
        row for row in per_action if row["survival_at_52"] < 0.4
    ]

    return {
        "actions": per_action,
        "horizon_points": points,
        "assumed_weekly_saving": round(naive_weekly, 4),
        "fragile_actions": fragile,
        "fragile_share_of_plan": (
            round(
                sum(row["weekly_saving"] for row in fragile) / naive_weekly, 4
            ) if naive_weekly else 0.0
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_persistence_insights(ranking, portfolio=None):
    """Plain-language findings, ordered by how much they should change a plan."""
    insights = []

    worst = max(
        ranking["options"], key=lambda row: row["overstatement_share"]
    )
    if worst["overstatement_share"] > 0.05:
        insights.append(
            f"{worst['name']} is the most overstated option in this set: the "
            f"naive annual figure of {worst['naive_annual_saving']:,.0f} "
            f"assumes it is still running in twelve months, and on a "
            f"{worst['class_label'].lower()} curve it is worth "
            f"{worst['expected_first_year']:,.0f} in the first year - "
            f"{worst['overstatement_share'] * 100:.0f}% less."
        )

    if ranking["ranking_changed"]:
        promoted = [row for row in ranking["moved"] if row["rank_change"] > 0]
        demoted = [row for row in ranking["moved"] if row["rank_change"] < 0]
        if promoted:
            row = promoted[0]
            insights.append(
                f"{row['name']} moves from rank {row['naive_rank']} to "
                f"{row['adjusted_rank']} once persistence is accounted for. "
                f"It looked worse than it is because the ranking it came from "
                f"cannot see durability."
            )
        if demoted:
            row = demoted[0]
            insights.append(
                f"{row['name']} drops from rank {row['naive_rank']} to "
                f"{row['adjusted_rank']}. It ranked well on a measure that "
                f"treats a habit and a heat pump as equally permanent."
            )
    else:
        insights.append(
            "The ranking is unchanged by persistence. Either the options are "
            "of similar durability or the savings are far enough apart that "
            "decay does not reorder them."
        )

    structural = [
        row for row in ranking["options"]
        if row["action_class"] == "structural_one_off"
    ]
    if structural:
        row = structural[0]
        insights.append(
            f"{row['name']} needs no maintenance once done, so almost none of "
            f"its projected saving is at risk. In a plan of effortful habits "
            f"that is worth more than its headline number suggests."
        )

    if portfolio:
        year_two = next(
            (point for point in portfolio["horizon_points"]
             if point["weeks"] >= 104), None
        )
        if year_two:
            insights.append(
                f"Two years out, this plan is expected to retain "
                f"{year_two['retained_share'] * 100:.0f}% of its weekly "
                f"saving - {year_two['surviving_weekly_saving']:,.1f} of the "
                f"{year_two['assumed_weekly_saving']:,.1f} currently assumed."
            )
        if portfolio["fragile_actions"]:
            names = ", ".join(
                row["name"] for row in portfolio["fragile_actions"][:3]
            )
            insights.append(
                f"{portfolio['fragile_share_of_plan'] * 100:.0f}% of this "
                f"plan's projected saving sits in actions with less than a "
                f"40% chance of surviving a year: {names}. That is not an "
                f"argument against them, but a plan resting mostly on them "
                f"needs re-engagement built in rather than assumed."
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
        CREATE TABLE IF NOT EXISTS action_persistence_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            assumed_weekly_saving REAL NOT NULL,
            expected_year_two_saving REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_action_persistence_plans_user
        ON action_persistence_plans (user_id)
        """
    )


def save_plan(user_id, name, portfolio):
    """Persist a portfolio assessment and return its row id."""
    if not user_id:
        raise PersistenceError("A plan needs a user to belong to.")
    if not name or not str(name).strip():
        raise PersistenceError("A plan needs a name.")

    year_two = next(
        (point for point in portfolio["horizon_points"]
         if point["weeks"] >= 104),
        portfolio["horizon_points"][-1],
    )

    payload = json.dumps({
        "actions": portfolio["actions"],
        "horizon_points": portfolio["horizon_points"],
        "fragile_actions": portfolio["fragile_actions"],
        "fragile_share_of_plan": portfolio["fragile_share_of_plan"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO action_persistence_plans
                (user_id, name, payload, assumed_weekly_saving,
                 expected_year_two_saving)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(user_id), str(name).strip(), payload,
                float(portfolio["assumed_weekly_saving"]),
                float(year_two["surviving_weekly_saving"]),
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
                SELECT id, name, payload, assumed_weekly_saving,
                       expected_year_two_saving, created_at
                FROM action_persistence_plans
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved persistence plans")
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
            "assumed_weekly_saving": row[3],
            "expected_year_two_saving": row[4],
            "created_at": row[5],
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
                "DELETE FROM action_persistence_plans "
                "WHERE id = ? AND user_id = ?",
                (plan_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete persistence plan %s", plan_id)
        return False


# ---------------------------------------------------------------------------
# Small accessors used by the page
# ---------------------------------------------------------------------------
def list_action_classes():
    return list(ACTION_CLASSES)


def get_action_class(key):
    if key not in ACTION_CLASSES:
        raise PersistenceError(f"{key!r} is not a known action class.")
    return dict(ACTION_CLASSES[key])
