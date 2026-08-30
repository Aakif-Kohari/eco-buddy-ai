"""Did the action cause the saving, or did the season?

`src.utils.intervention_effectiveness` is careful. Its own docstring says it
"does not claim causal certainty", and it is right to say so, because what it
computes is a before-and-after difference with an evidence score attached.

The trouble is that a before-and-after difference on a seasonal, trending,
weather-driven series does not measure the intervention. It measures the
intervention plus the season plus the trend plus whatever else changed in the
same month, and hands the whole sum to the action the user happened to log.
Someone who installs a smart thermostat in April and compares May against March
will be told it saved 22%. Spring did that.

The disclaimer does not fix it, because the number is still the one on the
screen and it still feeds the effectiveness score and the recommendation
ranking.

What this module does instead
-----------------------------
**A comparison group.** Difference-in-differences: treated units against
control units, pre-period against post-period. The controls absorb everything
common to both — season, weather, tariff, national trend — and what survives
is the part the intervention plausibly did.

**The assumption, tested, and reported first.** DiD is valid only if treated
and control were moving in parallel beforehand. That is checkable and checking
it is what separates a causal claim from a hopeful one. If the pre-trends
diverge, this module says the estimate is not usable rather than printing it
with a caveat underneath.

**Standard errors that survive serial correlation.** Consecutive months are
correlated, so treating 24 monthly observations as 24 independent draws
understates the standard error substantially — Bertrand, Duflo and
Mullainathan put the understatement at a factor of two to three on typical
panels. Two different fixes are used, in the two places they belong:

*   *Panel path.* Collapse each unit to a single pre and post mean, then
    cluster by unit. Two observations per unit cannot be serially correlated
    with themselves, which removes the problem rather than modelling it.
*   *Single-unit path.* Newey-West with a Bartlett kernel, because a lone time
    series has nothing to cluster over and the autocorrelation has to be
    estimated.

**What the design could have found.** A user with six months of noisy data
cannot detect a 5% saving no matter what they install. Reporting "no
significant change" without reporting the minimum detectable effect is a
misleading answer to a reasonable question, so both are returned together,
always.

**Placebo tests.** Re-run with the intervention date shifted into the
pre-period, where the effect must be zero. A placebo that finds a large saving
is telling you the design is picking up something else.

Refusals
--------
No DiD without a pre-period on both sides. No estimate from a comparison group
that fails parallel trends. No effect without its interval and its minimum
detectable effect. No causal language on the single-unit path, which is a
weaker design and is labelled as one.

Self-contained by design: the distribution functions below are duplicated in
other engines in this repo rather than shared, because there is no common
numerics module and adding one would mean touching files other work depends on.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import statistics
from typing import Any, Mapping, Sequence

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

ENGINE_VERSION = "1.0.0"

# Design requirements -------------------------------------------------------
MIN_PRE_PERIODS = 3
MIN_POST_PERIODS = 2
MIN_UNITS_PER_ARM = 2
MAX_UNITS = 500
MAX_PERIODS = 240

# Inference -----------------------------------------------------------------
DEFAULT_ALPHA = 0.05
DEFAULT_POWER = 0.80
PARALLEL_TRENDS_ALPHA = 0.10
POWER_Z = {0.80: 0.841621, 0.90: 1.281552, 0.95: 1.644854}

# Newey-West ----------------------------------------------------------------
MIN_LAGS = 1
MAX_LAGS = 24


class VerificationError(ValueError):
    """Raised when a design cannot support the estimate being asked for."""


# ---------------------------------------------------------------------------
# Distribution functions
# ---------------------------------------------------------------------------


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta function."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def t_cdf(value: float, degrees_of_freedom: float) -> float:
    """Student-t cumulative distribution function."""
    if degrees_of_freedom <= 0:
        raise VerificationError("Student-t needs positive degrees of freedom.")
    z = degrees_of_freedom / (degrees_of_freedom + value * value)
    tail = 0.5 * betai(degrees_of_freedom / 2.0, 0.5, z)
    return 1.0 - tail if value > 0 else tail


def t_ppf(probability: float, degrees_of_freedom: float) -> float:
    """Inverse Student-t by bisection on the exact CDF.

    Bisection rather than an expansion because household panels routinely give
    single-digit degrees of freedom, where the usual expansions are worst.
    """
    if not 0.0 < probability < 1.0:
        raise VerificationError("Probability must lie strictly in (0, 1).")
    if degrees_of_freedom <= 0:
        raise VerificationError("Student-t needs positive degrees of freedom.")
    low, high = -400.0, 400.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if t_cdf(middle, degrees_of_freedom) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def two_sided_p(statistic: float, degrees_of_freedom: float) -> float:
    return 2.0 * (1.0 - t_cdf(abs(statistic), max(degrees_of_freedom, 1.0)))


# ---------------------------------------------------------------------------
# Observations and panels
# ---------------------------------------------------------------------------


def build_observation(
    unit: Any,
    period: int,
    value: float,
    treated: bool,
    **drivers: Any,
) -> dict[str, Any]:
    """One unit-period reading.

    `treated` describes the *unit*, not the period. Whether a given reading is
    before or after the intervention comes from the treatment period on the
    panel, which is the only place it should be decided.
    """
    number = _finite(value)
    if number is None:
        raise VerificationError("Observation for '%s' needs a finite value." % unit)
    index = _finite(period)
    if index is None:
        raise VerificationError("Observation for '%s' needs a numeric period." % unit)
    cleaned_drivers = {}
    for key, raw in drivers.items():
        driver = _finite(raw)
        if driver is None:
            raise VerificationError(
                "Driver '%s' for unit '%s' is not numeric." % (key, unit)
            )
        cleaned_drivers[str(key)] = driver
    return {
        "unit": str(unit),
        "period": int(index),
        "value": number,
        "treated": bool(treated),
        "drivers": cleaned_drivers,
    }


def build_panel(
    observations: Sequence[Mapping[str, Any]],
    treatment_period: int,
) -> dict[str, Any]:
    """Index observations into a balanced-enough panel and check the design.

    Every refusal here is a design that cannot support a DiD estimate, so it is
    better to say why than to return a number computed from half of one.
    """
    if not observations:
        raise VerificationError("No observations supplied.")

    start = int(treatment_period)
    units: dict[str, dict[str, Any]] = {}
    for observation in observations:
        unit = observation["unit"]
        entry = units.setdefault(
            unit, {"unit": unit, "treated": bool(observation["treated"]), "readings": []}
        )
        if entry["treated"] != bool(observation["treated"]):
            raise VerificationError(
                "Unit '%s' is marked both treated and control. Treatment is a "
                "property of the unit, not of the reading." % unit
            )
        entry["readings"].append(dict(observation))

    if len(units) > MAX_UNITS:
        raise VerificationError("At most %d units are supported." % MAX_UNITS)

    for entry in units.values():
        entry["readings"].sort(key=lambda item: item["period"])
        periods = [item["period"] for item in entry["readings"]]
        if len(set(periods)) != len(periods):
            raise VerificationError(
                "Unit '%s' has two readings for the same period." % entry["unit"]
            )
        entry["pre"] = [item for item in entry["readings"] if item["period"] < start]
        entry["post"] = [item for item in entry["readings"] if item["period"] >= start]

    treated = [entry for entry in units.values() if entry["treated"]]
    control = [entry for entry in units.values() if not entry["treated"]]

    if len(treated) < MIN_UNITS_PER_ARM:
        raise VerificationError(
            "Need at least %d treated units; with fewer, the clustered standard "
            "error has nothing to cluster over." % MIN_UNITS_PER_ARM
        )
    if len(control) < MIN_UNITS_PER_ARM:
        raise VerificationError(
            "Need at least %d control units. Without a comparison group this is "
            "a before-and-after study, which is what the module exists to "
            "replace — use the Option C path and read it as the weaker design "
            "it is." % MIN_UNITS_PER_ARM
        )

    for entry in units.values():
        if len(entry["pre"]) < MIN_PRE_PERIODS:
            raise VerificationError(
                "Unit '%s' has %d pre-period readings; %d are needed to test "
                "parallel trends, and an untested parallel-trends assumption is "
                "not an assumption, it is a hope."
                % (entry["unit"], len(entry["pre"]), MIN_PRE_PERIODS)
            )
        if len(entry["post"]) < MIN_POST_PERIODS:
            raise VerificationError(
                "Unit '%s' has %d post-period readings; %d are needed."
                % (entry["unit"], len(entry["post"]), MIN_POST_PERIODS)
            )

    all_periods = sorted({item["period"] for entry in units.values() for item in entry["readings"]})
    if len(all_periods) > MAX_PERIODS:
        raise VerificationError("At most %d periods are supported." % MAX_PERIODS)

    return {
        "units": list(units.values()),
        "treated": treated,
        "control": control,
        "treatment_period": start,
        "periods": all_periods,
        "pre_periods": [period for period in all_periods if period < start],
        "post_periods": [period for period in all_periods if period >= start],
    }


def _unit_means(entry: Mapping[str, Any]) -> tuple[float, float]:
    pre = statistics.fmean(item["value"] for item in entry["pre"])
    post = statistics.fmean(item["value"] for item in entry["post"])
    return pre, post


def _slope(points: Sequence[tuple[float, float]]) -> float | None:
    """OLS slope of y on x."""
    if len(points) < 2:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    mean_x, mean_y = statistics.fmean(xs), statistics.fmean(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator <= 0:
        return None
    numerator = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(len(xs)))
    return numerator / denominator


# ---------------------------------------------------------------------------
# Parallel trends — tested before the effect, deliberately
# ---------------------------------------------------------------------------


def parallel_trends(panel: Mapping[str, Any], alpha: float = PARALLEL_TRENDS_ALPHA) -> dict[str, Any]:
    """Were treated and control moving together before the intervention?

    Fit a pre-period slope per unit, compare the treated and control slope
    distributions with a Welch test. Divergence beforehand means the two arms
    were on different paths for reasons unrelated to the intervention, and
    whatever DiD produces afterwards inherits that difference.

    Note on the alpha: 0.10 rather than 0.05, on purpose. This is a test the
    analysis wants to *pass*, so the conventional threshold is the wrong way
    round — a lenient threshold here makes it easier to proceed, which is the
    opposite of what a validity check is for. A stricter one blocks more
    analyses and that is the intended direction of the error.
    """
    def slopes(units: Sequence[Mapping[str, Any]]) -> list[float]:
        collected = []
        for entry in units:
            points = [(float(item["period"]), item["value"]) for item in entry["pre"]]
            slope = _slope(points)
            if slope is not None:
                collected.append(slope)
        return collected

    treated_slopes = slopes(panel["treated"])
    control_slopes = slopes(panel["control"])

    if len(treated_slopes) < 2 or len(control_slopes) < 2:
        return {
            "testable": False,
            "treated_slope": statistics.fmean(treated_slopes) if treated_slopes else 0.0,
            "control_slope": statistics.fmean(control_slopes) if control_slopes else 0.0,
            "difference": 0.0,
            "p_value": None,
            "passes": False,
            "headline": (
                "Not enough units per arm to test parallel trends. Without that "
                "test a difference-in-differences estimate is not a causal claim."
            ),
        }

    treated_mean = statistics.fmean(treated_slopes)
    control_mean = statistics.fmean(control_slopes)
    treated_var = statistics.variance(treated_slopes)
    control_var = statistics.variance(control_slopes)

    standard_error = math.sqrt(
        treated_var / len(treated_slopes) + control_var / len(control_slopes)
    )
    difference = treated_mean - control_mean

    if standard_error <= 0:
        statistic = 0.0 if abs(difference) < 1e-12 else float("inf")
        degrees = float(len(treated_slopes) + len(control_slopes) - 2)
        p_value = 1.0 if abs(difference) < 1e-12 else 0.0
    else:
        statistic = difference / standard_error
        numerator = (
            treated_var / len(treated_slopes) + control_var / len(control_slopes)
        ) ** 2
        denominator = (
            (treated_var / len(treated_slopes)) ** 2 / max(len(treated_slopes) - 1, 1)
            + (control_var / len(control_slopes)) ** 2 / max(len(control_slopes) - 1, 1)
        )
        degrees = numerator / denominator if denominator > 0 else 1.0
        p_value = two_sided_p(statistic, degrees)

    passes = p_value >= alpha
    return {
        "testable": True,
        "treated_slope": treated_mean,
        "control_slope": control_mean,
        "difference": difference,
        "standard_error": standard_error,
        "t_statistic": statistic,
        "degrees_of_freedom": degrees,
        "p_value": p_value,
        "alpha": alpha,
        "passes": passes,
        "headline": (
            "Pre-trends are parallel (treated %.2f/period, control %.2f/period, "
            "p=%.3f). The comparison group is usable."
            % (treated_mean, control_mean, p_value)
            if passes
            else "Pre-trends diverge (treated %.2f/period, control %.2f/period, "
            "p=%.3f). The two arms were already on different paths, so a "
            "difference-in-differences estimate would attribute that divergence "
            "to the intervention."
            % (treated_mean, control_mean, p_value)
        ),
    }


# ---------------------------------------------------------------------------
# Difference-in-differences
# ---------------------------------------------------------------------------


def naive_standard_error(panel: Mapping[str, Any]) -> float:
    """Standard error from a four-group comparison of raw readings.

    Every reading treated as an independent draw, with nothing absorbing the
    season. Computed only so it can be shown next to the clustered one. On a
    seasonal series this is usually *larger* than the clustered error, because
    the seasonal swing is being counted as noise — which is a different error
    from the famous one and is equally not the number to report.
    """
    treated_post, treated_pre, control_post, control_pre = [], [], [], []
    for entry in panel["units"]:
        target_pre = treated_pre if entry["treated"] else control_pre
        target_post = treated_post if entry["treated"] else control_post
        target_pre.extend(item["value"] for item in entry["pre"])
        target_post.extend(item["value"] for item in entry["post"])

    parts = []
    for sample in (treated_post, treated_pre, control_post, control_pre):
        if len(sample) < 2:
            return float("inf")
        parts.append(statistics.variance(sample) / len(sample))
    return math.sqrt(sum(parts))


def unclustered_standard_error(panel: Mapping[str, Any]) -> float:
    """Standard error from treating every post-period reading as its own
    observation.

    This is the specification most savings analyses actually run: period
    effects absorb the season, and then each unit-period residual is counted as
    an independent observation. Twelve households observed for twelve months
    become a hundred and forty-four observations.

    They are not a hundred and forty-four observations. A household whose
    consumption is high this month is likely to be high next month, so the
    readings within a unit carry much less independent information than their
    count suggests. Bertrand, Duflo and Mullainathan put the resulting
    understatement at a factor of two to three on typical monthly panels.

    Clustering removes the problem instead of modelling it: collapse each unit
    to one pre mean and one post mean, and there is nothing left for the serial
    correlation to act on.

    Some gap between the two remains even with genuinely independent shocks,
    because every post-period deviation is measured against the same estimated
    baseline and therefore shares its error. On the worked example that floor
    is about 1.3x; at a realistic serial correlation of 0.85 it is 2.8x. The
    size of the gap is the diagnostic — a small one says the readings really
    were close to independent, a large one says they were nothing of the kind.
    """
    period_means: dict[int, list[float]] = {}
    for entry in panel["units"]:
        for item in entry["readings"]:
            period_means.setdefault(item["period"], []).append(item["value"])
    centres = {
        period: statistics.fmean(values) for period, values in period_means.items()
    }

    treated_deviations: list[float] = []
    control_deviations: list[float] = []
    for entry in panel["units"]:
        pre_values = [item["value"] - centres[item["period"]] for item in entry["pre"]]
        if not pre_values:
            continue
        baseline = statistics.fmean(pre_values)
        target = treated_deviations if entry["treated"] else control_deviations
        for item in entry["post"]:
            target.append(item["value"] - centres[item["period"]] - baseline)

    if len(treated_deviations) < 2 or len(control_deviations) < 2:
        return float("inf")
    return math.sqrt(
        statistics.variance(treated_deviations) / len(treated_deviations)
        + statistics.variance(control_deviations) / len(control_deviations)
    )


def estimate_did(
    panel: Mapping[str, Any],
    alpha: float = DEFAULT_ALPHA,
    require_parallel_trends: bool = True,
) -> dict[str, Any]:
    """Difference-in-differences with unit-clustered standard errors.

    Each unit is collapsed to one pre mean and one post mean, and the estimate
    is the difference between the treated and control changes. Collapsing is
    what handles serial correlation: two numbers per unit cannot be
    autocorrelated with themselves, so the problem is removed rather than
    modelled. The clustered standard error then treats each unit as the
    independent observation it actually is.

    The parallel-trends test runs first and blocks the estimate by default,
    because an estimate printed with a failed validity check underneath it gets
    read as an estimate.
    """
    trends = parallel_trends(panel)
    if require_parallel_trends and not trends["passes"]:
        return {
            "usable": False,
            "parallel_trends": trends,
            "headline": trends["headline"],
            "effect": None,
        }

    treated_changes = []
    control_changes = []
    for entry in panel["units"]:
        pre, post = _unit_means(entry)
        change = post - pre
        (treated_changes if entry["treated"] else control_changes).append(change)

    treated_mean = statistics.fmean(treated_changes)
    control_mean = statistics.fmean(control_changes)
    effect = treated_mean - control_mean

    treated_var = statistics.variance(treated_changes) if len(treated_changes) > 1 else 0.0
    control_var = statistics.variance(control_changes) if len(control_changes) > 1 else 0.0
    clustered = math.sqrt(
        treated_var / len(treated_changes) + control_var / len(control_changes)
    )
    degrees = max(1, len(treated_changes) + len(control_changes) - 2)

    if clustered > 0:
        statistic = effect / clustered
        p_value = two_sided_p(statistic, degrees)
        critical = t_ppf(1.0 - alpha / 2.0, degrees)
    else:
        statistic = 0.0 if abs(effect) < 1e-12 else float("inf")
        p_value = 1.0 if abs(effect) < 1e-12 else 0.0
        critical = 0.0

    naive = naive_standard_error(panel)
    unclustered = unclustered_standard_error(panel)
    baseline = statistics.fmean(
        item["value"]
        for entry in panel["treated"]
        for item in entry["pre"]
    )

    mde = minimum_detectable_effect(panel, alpha=alpha)
    before_after = treated_mean

    return {
        "usable": True,
        "effect": effect,
        "percent_effect": (effect / baseline * 100.0) if baseline else 0.0,
        "treated_change": treated_mean,
        "control_change": control_mean,
        "baseline": baseline,
        "clustered_standard_error": clustered,
        "naive_standard_error": naive,
        "unclustered_standard_error": unclustered,
        "clustered_over_unclustered": (clustered / unclustered) if unclustered > 0 else float("inf"),
        "clustered_over_naive": (clustered / naive) if naive > 0 else float("inf"),
        "t_statistic": statistic,
        "p_value": p_value,
        "degrees_of_freedom": degrees,
        "alpha": alpha,
        "lower": effect - critical * clustered,
        "upper": effect + critical * clustered,
        "significant": p_value < alpha,
        "treated_units": len(treated_changes),
        "control_units": len(control_changes),
        "parallel_trends": trends,
        "minimum_detectable_effect": mde,
        "before_after_estimate": before_after,
        "confounded_share": (
            (before_after - effect) / before_after * 100.0 if before_after else 0.0
        ),
        "headline": _did_headline(effect, before_after, p_value, alpha, mde),
    }


def _did_headline(
    effect: float,
    before_after: float,
    p_value: float,
    alpha: float,
    mde: Mapping[str, Any],
) -> str:
    if p_value < alpha:
        return (
            "Estimated effect %.1f per period (p=%.3f). A plain before-and-after "
            "on the treated units alone would have reported %.1f — the "
            "difference is what the comparison group absorbed."
            % (effect, p_value, before_after)
        )
    return (
        "No detectable effect (estimate %.1f, p=%.3f). This design could only "
        "have found an effect of %.1f or larger at %.0f%% power, so a null "
        "result here is not evidence of no effect."
        % (effect, p_value, mde["effect"], mde["power"] * 100.0)
    )


def minimum_detectable_effect(
    panel: Mapping[str, Any],
    power: float = DEFAULT_POWER,
    alpha: float = DEFAULT_ALPHA,
) -> dict[str, Any]:
    """The smallest effect this design could have found.

    Reported alongside every null result without exception. "No significant
    change" and "this study could never have detected the change you care
    about" look identical on a dashboard and mean entirely different things.
    """
    if power not in POWER_Z:
        raise VerificationError(
            "Power must be one of %s." % ", ".join(str(value) for value in sorted(POWER_Z))
        )

    treated_changes, control_changes = [], []
    for entry in panel["units"]:
        pre, post = _unit_means(entry)
        (treated_changes if entry["treated"] else control_changes).append(post - pre)

    treated_var = statistics.variance(treated_changes) if len(treated_changes) > 1 else 0.0
    control_var = statistics.variance(control_changes) if len(control_changes) > 1 else 0.0
    standard_error = math.sqrt(
        treated_var / len(treated_changes) + control_var / len(control_changes)
    )
    degrees = max(1, len(treated_changes) + len(control_changes) - 2)

    critical = t_ppf(1.0 - alpha / 2.0, degrees)
    detectable = (critical + POWER_Z[power]) * standard_error

    baseline = statistics.fmean(
        item["value"] for entry in panel["treated"] for item in entry["pre"]
    )
    return {
        "effect": detectable,
        "percent": (detectable / baseline * 100.0) if baseline else 0.0,
        "power": power,
        "alpha": alpha,
        "standard_error": standard_error,
        "note": (
            "With %d treated and %d control units and this much period-to-period "
            "noise, nothing smaller than %.1f (%.1f%% of baseline) could have "
            "been detected."
            % (
                len(treated_changes),
                len(control_changes),
                detectable,
                (detectable / baseline * 100.0) if baseline else 0.0,
            )
        ),
    }


# ---------------------------------------------------------------------------
# Event study
# ---------------------------------------------------------------------------


def event_study(panel: Mapping[str, Any]) -> dict[str, Any]:
    """Treated-minus-control gap by period relative to the intervention.

    Normalised to the period immediately before treatment. Two things become
    visible that a single averaged number hides: an effect that appears *before*
    the intervention, which is anticipation or a mis-dated event rather than an
    effect; and an effect that decays, which is decay rather than a smaller
    flat effect. The second connects directly to `action_persistence`, which
    models decay and currently has no way to measure it.
    """
    start = panel["treatment_period"]
    by_period: dict[int, dict[str, list[float]]] = {}
    for entry in panel["units"]:
        for item in entry["readings"]:
            bucket = by_period.setdefault(item["period"], {"treated": [], "control": []})
            bucket["treated" if entry["treated"] else "control"].append(item["value"])

    gaps: dict[int, float] = {}
    for period, bucket in by_period.items():
        if not bucket["treated"] or not bucket["control"]:
            continue
        gaps[period] = statistics.fmean(bucket["treated"]) - statistics.fmean(bucket["control"])

    reference_period = max(
        (period for period in gaps if period < start), default=None
    )
    if reference_period is None:
        raise VerificationError(
            "No pre-treatment period with both arms present to normalise against."
        )
    reference = gaps[reference_period]

    points = []
    for period in sorted(gaps):
        points.append(
            {
                "period": period,
                "relative": period - start,
                "gap": gaps[period],
                "effect": gaps[period] - reference,
                "post": period >= start,
            }
        )

    pre_effects = [point["effect"] for point in points if not point["post"]]
    post_effects = [point["effect"] for point in points if point["post"]]
    largest_pre = max((abs(value) for value in pre_effects), default=0.0)

    decaying = (
        len(post_effects) >= 3
        and abs(post_effects[-1]) < abs(post_effects[0]) * 0.7
    )

    return {
        "points": points,
        "reference_period": reference_period,
        "largest_pre_effect": largest_pre,
        "mean_post_effect": statistics.fmean(post_effects) if post_effects else 0.0,
        "decaying": decaying,
        "anticipation_warning": (
            largest_pre > abs(statistics.fmean(post_effects)) * 0.5
            if post_effects
            else False
        ),
        "headline": (
            "Effect decays across the post period — the last observed effect is "
            "under 70%% of the first. A single averaged number would have "
            "reported the mean of a declining curve as a flat saving."
            if decaying
            else "Effect is broadly stable across the post period."
        ),
    }


# ---------------------------------------------------------------------------
# Placebo
# ---------------------------------------------------------------------------


def placebo_test(
    observations: Sequence[Mapping[str, Any]],
    true_treatment_period: int,
    placebo_period: int | None = None,
    alpha: float = DEFAULT_ALPHA,
) -> dict[str, Any]:
    """Re-run the estimator on a date where the effect must be zero.

    Only pre-period observations are used, with a fake intervention date part
    way through them. A placebo that finds a large "saving" is telling you the
    design is picking up something other than the intervention, and it is the
    cheapest honesty check available.
    """
    pre_only = [
        observation
        for observation in observations
        if observation["period"] < true_treatment_period
    ]
    if not pre_only:
        raise VerificationError("No pre-period observations to run a placebo on.")

    periods = sorted({observation["period"] for observation in pre_only})
    fake = placebo_period if placebo_period is not None else periods[len(periods) // 2]

    try:
        panel = build_panel(pre_only, fake)
        result = estimate_did(panel, alpha=alpha, require_parallel_trends=False)
    except VerificationError as error:
        return {
            "ran": False,
            "reason": str(error),
            "headline": (
                "Placebo could not be run: %s. That is a limitation of the "
                "pre-period, not a pass." % error
            ),
        }

    passed = not result["significant"]
    return {
        "ran": True,
        "placebo_period": fake,
        "effect": result["effect"],
        "p_value": result["p_value"],
        "significant": result["significant"],
        "passed": passed,
        "headline": (
            "Placebo finds no effect (%.1f, p=%.3f), as it should."
            % (result["effect"], result["p_value"])
            if passed
            else "Placebo finds a significant 'effect' of %.1f (p=%.3f) at a date "
            "where nothing happened. The design is picking up something other "
            "than the intervention and the main estimate should not be trusted."
            % (result["effect"], result["p_value"])
        ),
    }


# ---------------------------------------------------------------------------
# IPMVP Option C — the single-unit fallback
# ---------------------------------------------------------------------------


def _ols(design: Sequence[Sequence[float]], response: Sequence[float]) -> list[float] | None:
    """Normal-equations OLS with partial pivoting; None if singular."""
    size = len(design[0])
    xtx = [[0.0] * size for _ in range(size)]
    xty = [0.0] * size
    for row_index, row in enumerate(design):
        for left in range(size):
            xty[left] += row[left] * response[row_index]
            for right in range(size):
                xtx[left][right] += row[left] * row[right]

    augmented = [list(xtx[row]) + [xty[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        for row in range(column + 1, size):
            factor = augmented[row][column] / augmented[column][column]
            for position in range(column, size + 1):
                augmented[row][position] -= factor * augmented[column][position]

    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        total = augmented[row][size]
        for column in range(row + 1, size):
            total -= augmented[row][column] * solution[column]
        solution[row] = total / augmented[row][row]
    return solution


def newey_west_variance(
    design: Sequence[Sequence[float]],
    residuals: Sequence[float],
    lags: int | None = None,
) -> list[float] | None:
    """Bartlett-kernel HAC variance of OLS coefficients.

    Used on the single-unit path, where there is nothing to cluster over and
    the autocorrelation has to be estimated rather than removed. Lag length
    defaults to the usual ``floor(4 (T/100)^(2/9))`` rule.

    Returns the diagonal of the sandwich estimator, which is all the callers
    here need.
    """
    n = len(residuals)
    size = len(design[0])
    if n <= size:
        return None
    if lags is None:
        lags = int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0)))
    lags = int(min(max(lags, MIN_LAGS), min(MAX_LAGS, n - 1)))

    xtx = [[0.0] * size for _ in range(size)]
    for row in design:
        for left in range(size):
            for right in range(size):
                xtx[left][right] += row[left] * row[right]

    # Meat of the sandwich: S = sum_t u_t^2 x_t x_t' + weighted cross terms.
    meat = [[0.0] * size for _ in range(size)]
    for index in range(n):
        weight = residuals[index] ** 2
        for left in range(size):
            for right in range(size):
                meat[left][right] += weight * design[index][left] * design[index][right]

    for lag in range(1, lags + 1):
        kernel = 1.0 - lag / (lags + 1.0)
        for index in range(lag, n):
            product = residuals[index] * residuals[index - lag]
            for left in range(size):
                for right in range(size):
                    meat[left][right] += kernel * product * (
                        design[index][left] * design[index - lag][right]
                        + design[index - lag][left] * design[index][right]
                    )

    inverse = _invert(xtx)
    if inverse is None:
        return None

    variance = []
    for position in range(size):
        total = 0.0
        for left in range(size):
            for right in range(size):
                total += inverse[position][left] * meat[left][right] * inverse[right][position]
        variance.append(max(total, 0.0))
    return variance


def _invert(matrix: Sequence[Sequence[float]]) -> list[list[float]] | None:
    """Gauss-Jordan inversion; None if singular."""
    size = len(matrix)
    augmented = [
        list(matrix[row]) + [1.0 if row == column else 0.0 for column in range(size)]
        for row in range(size)
    ]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            return None
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][position] - factor * augmented[column][position]
                for position in range(2 * size)
            ]
    return [row[size:] for row in augmented]


def durbin_watson(residuals: Sequence[float]) -> float:
    """Durbin-Watson statistic: near 2 is no autocorrelation, near 0 is strong.

    Reported next to the Option C result because it is the fastest way to see
    whether the naive standard error on that path is defensible.
    """
    if len(residuals) < 2:
        return 2.0
    numerator = sum(
        (residuals[index] - residuals[index - 1]) ** 2 for index in range(1, len(residuals))
    )
    denominator = sum(value ** 2 for value in residuals)
    return numerator / denominator if denominator > 0 else 2.0


def option_c_regression(
    observations: Sequence[Mapping[str, Any]],
    treatment_period: int,
    driver_names: Sequence[str],
    alpha: float = DEFAULT_ALPHA,
) -> dict[str, Any]:
    """IPMVP Option C whole-facility measurement and verification.

    Fit a baseline regression on the pre-period drivers — degree days,
    occupancy — project it into the reporting period, and take the avoided
    consumption as the residual.

    Two things routine M&V write-ups leave out and this does not: the
    uncertainty from the baseline *fit* itself, and a HAC standard error that
    survives the serial correlation in a monthly series. Neither makes the
    answer better; they make the interval honest.

    This path never uses causal language. It has no comparison group, so it
    cannot separate the intervention from anything else that changed at the
    same time and does not correlate with the drivers.
    """
    readings = sorted(observations, key=lambda item: item["period"])
    pre = [item for item in readings if item["period"] < treatment_period]
    post = [item for item in readings if item["period"] >= treatment_period]

    if len(pre) < len(driver_names) + 3:
        raise VerificationError(
            "Need at least %d baseline periods to fit %d driver(s) with any "
            "residual degrees of freedom." % (len(driver_names) + 3, len(driver_names))
        )
    if len(post) < MIN_POST_PERIODS:
        raise VerificationError(
            "Need at least %d reporting periods." % MIN_POST_PERIODS
        )

    def row_of(item: Mapping[str, Any]) -> list[float]:
        design_row = [1.0]
        for name in driver_names:
            if name not in item["drivers"]:
                raise VerificationError(
                    "Period %d has no value for driver '%s'." % (item["period"], name)
                )
            design_row.append(item["drivers"][name])
        return design_row

    design = [row_of(item) for item in pre]
    response = [item["value"] for item in pre]
    coefficients = _ols(design, response)
    if coefficients is None:
        raise VerificationError(
            "The baseline regression is singular — the drivers are collinear."
        )

    fitted = [
        sum(coefficients[index] * design[row][index] for index in range(len(coefficients)))
        for row in range(len(design))
    ]
    residuals = [response[row] - fitted[row] for row in range(len(response))]
    degrees = max(1, len(pre) - len(coefficients))
    residual_variance = sum(value ** 2 for value in residuals) / degrees

    total_ss = sum(
        (value - statistics.fmean(response)) ** 2 for value in response
    )
    r_squared = 1.0 - (sum(value ** 2 for value in residuals) / total_ss) if total_ss > 0 else 0.0
    cv_rmse = (
        math.sqrt(residual_variance) / statistics.fmean(response) * 100.0
        if statistics.fmean(response)
        else 0.0
    )

    hac = newey_west_variance(design, residuals)
    watson = durbin_watson(residuals)

    projected = []
    avoided = []
    for item in post:
        row = row_of(item)
        prediction = sum(coefficients[index] * row[index] for index in range(len(coefficients)))
        projected.append(prediction)
        avoided.append(prediction - item["value"])

    total_avoided = sum(avoided)
    mean_avoided = statistics.fmean(avoided)

    # Uncertainty in the total comes from the residual scatter and from the
    # baseline fit. Ignoring the second is the usual omission.
    scatter_variance = residual_variance * len(post)
    fit_variance = (
        sum(hac) * len(post) ** 2 / max(len(pre), 1) if hac else residual_variance * len(post)
    )
    total_variance = scatter_variance + fit_variance
    standard_error = math.sqrt(total_variance)
    critical = t_ppf(1.0 - alpha / 2.0, degrees)

    baseline_mean = statistics.fmean(response)
    return {
        "coefficients": coefficients,
        "drivers": list(driver_names),
        "baseline_periods": len(pre),
        "reporting_periods": len(post),
        "r_squared": r_squared,
        "cv_rmse": cv_rmse,
        "durbin_watson": watson,
        "autocorrelated": watson < 1.5,
        "projected": projected,
        "avoided_per_period": avoided,
        "total_avoided": total_avoided,
        "mean_avoided": mean_avoided,
        "percent_avoided": (mean_avoided / baseline_mean * 100.0) if baseline_mean else 0.0,
        "standard_error": standard_error,
        "lower": total_avoided - critical * standard_error,
        "upper": total_avoided + critical * standard_error,
        "significant": abs(total_avoided) > critical * standard_error,
        "design": "option_c",
        "causal": False,
        "headline": (
            "Avoided consumption %.1f over %d reporting periods, interval %.1f "
            "to %.1f. This is an association, not a causal estimate — there is "
            "no comparison group, so anything else that changed at the same "
            "time and is uncorrelated with the drivers is in this number."
            % (total_avoided, len(post), total_avoided - critical * standard_error,
               total_avoided + critical * standard_error)
        ),
    }


# ---------------------------------------------------------------------------
# Reading the result
# ---------------------------------------------------------------------------


def verify(
    observations: Sequence[Mapping[str, Any]],
    treatment_period: int,
    alpha: float = DEFAULT_ALPHA,
    require_parallel_trends: bool = True,
) -> dict[str, Any]:
    """The full panel workflow: assumption, effect, event study, placebo."""
    panel = build_panel(observations, treatment_period)
    trends = parallel_trends(panel)
    result = estimate_did(panel, alpha, require_parallel_trends)

    report: dict[str, Any] = {
        "engine_version": ENGINE_VERSION,
        "treatment_period": treatment_period,
        "parallel_trends": trends,
        "did": result,
        "design": "difference_in_differences",
        "causal": result.get("usable", False) and trends["passes"],
    }
    if result.get("usable"):
        report["event_study"] = event_study(panel)
        report["placebo"] = placebo_test(observations, treatment_period, alpha=alpha)
    return report


def get_verification_notes(report: Mapping[str, Any]) -> list[str]:
    """Plain-language readings of a verification report."""
    notes: list[str] = [report["parallel_trends"]["headline"]]
    result = report["did"]

    if not result.get("usable"):
        notes.append(
            "No effect is reported, because the design cannot support one. That "
            "is the result, not a missing result."
        )
        return notes

    notes.append(result["headline"])
    notes.append(
        "Before-and-after on the treated units alone gives %.1f; the "
        "difference-in-differences estimate is %.1f. The gap of %.1f is what "
        "the comparison group absorbed — season, weather, trend and anything "
        "else common to both arms."
        % (
            result["before_after_estimate"],
            result["effect"],
            result["before_after_estimate"] - result["effect"],
        )
    )
    notes.append(
        "Clustered standard error %.2f. Counting every post-period reading as "
        "its own observation gives %.2f — the clustered error is %.1fx %s, "
        "because consecutive months within a household are not independent and "
        "the unclustered version does not know that. A raw four-group "
        "comparison with no period effects gives %.2f, wrong in the other "
        "direction because it counts the season as noise."
        % (
            result["clustered_standard_error"],
            result["unclustered_standard_error"],
            result["clustered_over_unclustered"],
            "larger" if result["clustered_over_unclustered"] > 1 else "smaller",
            result["naive_standard_error"],
        )
    )
    notes.append(result["minimum_detectable_effect"]["note"])

    if "event_study" in report:
        notes.append(report["event_study"]["headline"])
        if report["event_study"]["anticipation_warning"]:
            notes.append(
                "A sizeable gap opens before the intervention date. That is "
                "anticipation or a mis-dated event, and either way part of the "
                "measured effect is not the intervention."
            )
    if "placebo" in report:
        notes.append(report["placebo"]["headline"])
    return notes


def summarise(report: Mapping[str, Any]) -> str:
    """One line for a log or a saved-report list."""
    result = report["did"]
    if not result.get("usable"):
        return "not usable | %s" % report["parallel_trends"]["headline"][:80]
    return "effect %.1f (%.1f%%) p=%.3f | before/after would say %.1f | MDE %.1f" % (
        result["effect"],
        result["percent_effect"],
        result["p_value"],
        result["before_after_estimate"],
        result["minimum_detectable_effect"]["effect"],
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS savings_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            label TEXT NOT NULL,
            design TEXT NOT NULL,
            usable INTEGER NOT NULL,
            effect REAL,
            p_value REAL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_savings_verifications_user
        ON savings_verifications (user_id)
        """
    )


def save_verification(user_id: Any, report: Mapping[str, Any], label: str = "") -> int | None:
    """Persist a verification report. None if storage is unavailable."""
    if not user_id or "did" not in report:
        return None
    result = report["did"]
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                """
                INSERT INTO savings_verifications
                    (user_id, label, design, usable, effect, p_value, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(user_id),
                    str(label or "verification"),
                    str(report.get("design", "unknown")),
                    1 if result.get("usable") else 0,
                    float(result["effect"]) if result.get("effect") is not None else None,
                    float(result["p_value"]) if result.get("p_value") is not None else None,
                    json.dumps(report, default=str),
                ),
            )
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def get_verifications(user_id: Any, limit: int = 25) -> list[dict[str, Any]]:
    """Most recent saved reports for one user."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, label, design, usable, effect, p_value, payload, created_at
                FROM savings_verifications
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        return []

    reports = []
    for row in rows:
        try:
            payload = json.loads(row[6])
        except (TypeError, ValueError):
            payload = {}
        reports.append(
            {
                "id": row[0],
                "label": row[1],
                "design": row[2],
                "usable": bool(row[3]),
                "effect": row[4],
                "p_value": row[5],
                "payload": payload,
                "created_at": row[7],
            }
        )
    return reports


def delete_verification(user_id: Any, verification_id: int) -> bool:
    """Remove one saved report belonging to this user."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM savings_verifications WHERE user_id = ? AND id = ?",
                (str(user_id), int(verification_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------


def seasonal_panel(
    treated_units: int = 12,
    control_units: int = 12,
    periods: int = 24,
    treatment_period: int = 14,
    true_effect: float = -40.0,
    seasonal_amplitude: float = 180.0,
    noise: float = 25.0,
    autocorrelation: float = 0.7,
    seed: int = 555,
) -> list[dict[str, Any]]:
    """A panel where the season is far larger than the intervention.

    The intervention lands in month 14, which is the start of spring on this
    calendar. Consumption falls by 180 for seasonal reasons and by 40 because
    of the intervention, so a plain before-and-after on the treated units
    reports roughly five times the true effect.

    That is the whole demonstration, and the default parameters are chosen so
    that a naive analysis is not merely imprecise but wrong by a multiple.

    The idiosyncratic shocks are AR(1) with rho = 0.7 by default, because that
    is what household consumption actually looks like — a cold month is
    followed by a cold month — and it is the property that makes an unclustered
    standard error understate. Set `autocorrelation=0.0` for iid shocks, at
    which point clustering stops buying anything and the two errors converge.
    """
    import random

    rng = random.Random(seed)
    observations: list[dict[str, Any]] = []

    for index in range(treated_units + control_units):
        treated = index < treated_units
        unit = "%s%02d" % ("T" if treated else "C", index)
        level = rng.gauss(1200.0, 90.0)
        shock = rng.gauss(0.0, noise)
        for period in range(periods):
            season = seasonal_amplitude * math.cos(2.0 * math.pi * period / 12.0)
            shock = autocorrelation * shock + math.sqrt(
                max(0.0, 1.0 - autocorrelation ** 2)
            ) * rng.gauss(0.0, noise)
            value = level + season + shock
            if treated and period >= treatment_period:
                value += true_effect
            observations.append(
                build_observation(
                    unit,
                    period,
                    value,
                    treated,
                    degree_days=max(0.0, season + 200.0),
                )
            )
    return observations


def single_unit_series(
    periods: int = 30,
    treatment_period: int = 18,
    true_effect: float = -60.0,
    seed: int = 20241102,
) -> list[dict[str, Any]]:
    """One meter with a degree-day driver, for the Option C path."""
    import random

    rng = random.Random(seed)
    observations = []
    for period in range(periods):
        degree_days = max(0.0, 220.0 + 190.0 * math.cos(2.0 * math.pi * period / 12.0))
        value = 400.0 + 1.6 * degree_days + rng.gauss(0.0, 30.0)
        if period >= treatment_period:
            value += true_effect
        observations.append(
            build_observation(
                "meter", period, value, period >= treatment_period, degree_days=degree_days
            )
        )
    return observations
