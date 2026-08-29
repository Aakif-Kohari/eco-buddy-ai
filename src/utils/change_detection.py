"""Whether a reported change is real, which this app has never asked.

``src.carbon.confidence_scoring.py`` and the footprint uncertainty engine say
how uncertain a single estimate is. Nothing here asks the question that
actually matters when the app announces progress: is this month's number
different from last month's, or is it the same number with different noise on
it?

The app reports a 4% reduction with the same confidence it reports a 40% one.
Household consumption varies month to month by more than ten percent for
reasons that have nothing to do with behaviour - weather, occupancy, billing
periods, a visitor staying a fortnight. Against that background a 4%
improvement is indistinguishable from a coin flip, and the streak modules and
``pages/Sustainability_Trends.py`` celebrate it anyway.

Congratulating a user for noise is not a harmless error
--------------------------------------------------------
It teaches them an action worked when it did not. A user told they cut 6% by
changing detergent will eventually watch the figure bounce back with no
corresponding change, and at that point every other number in the app becomes
suspect too.

The false negative is worse and is entirely invisible
------------------------------------------------------
A real 8% improvement buried in noisy monthly data reads as "no change", and
the user abandons something that was working. This module reports three
verdicts rather than two, and the third one - *underpowered* - is the reason it
exists. "Your data could not have detected an effect this size even if one was
there" is a completely different statement from "it did not work", and the app
has never been able to make it.

Autocorrelation makes the naive test wrong in the unsafe direction
--------------------------------------------------------------------
Consecutive months are not independent draws. Treating them as independent
understates the standard error and therefore *overstates* significance, so the
error points towards more false alarms rather than fewer. Everything downstream
of ``characterise_baseline`` runs on an effective sample size instead.

Uncertainty on a level is not uncertainty on a difference
-----------------------------------------------------------
Two estimates built from the same emission factors share that error almost
entirely, so it largely cancels in the difference. Treating the two intervals
as independent both misses the cancellation and gets the answer wrong, in the
direction of declaring real changes undetectable.

The most useful output here is a number of weeks
--------------------------------------------------
"An effect this size needs about fourteen more weeks before it can be separated
from your normal variation" converts an unanswerable question into a plan.
``required_periods`` is the function most worth putting in front of a user.

Where this connects to code already merged
--------------------------------------------
*   ``src.carbon.confidence_scoring.py`` propagates factor uncertainty through
    one estimate. This compares two, and the shared-factor treatment is what
    makes them different calculations rather than the same one twice.
*   ``src.utils.sustainability_trends.py`` and the streak modules are the
    surfaces that currently report changes without a significance test.
*   ``src.environment.env_anomoly.py`` detects outliers in a series. This asks
    whether the level of the series moved, which is a different question.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import math
import sqlite3
import logging
import statistics

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class ChangeDetectionError(ValueError):
    """Raised when a detection question cannot be answered as asked."""


DEFAULT_ALPHA = 0.05
DEFAULT_POWER = 0.80

# Above this lag-1 autocorrelation the effective sample size collapses far
# enough that a significance test on the raw series is not worth reporting at
# all. The module says so rather than returning a confident number.
SEVERE_AUTOCORRELATION = 0.85

# Fewer observations than this and the residual standard deviation is itself
# too uncertain to build a power calculation on.
MINIMUM_BASELINE = 6


VERDICTS = {
    "detected": {
        "label": "Detected",
        "note": "The change is larger than this series' own noise can "
                "plausibly produce. It is safe to describe as real, within "
                "the stated error rate.",
    },
    "not_detected": {
        "label": "Not detected",
        "note": "The change is within the range this series produces on its "
                "own, and the test had enough power to have found an effect "
                "of the size that would matter. A genuine null result.",
    },
    "underpowered": {
        "label": "Cannot tell yet",
        "note": "The test could not have detected an effect of the size that "
                "matters, even if one were there. Reporting this as 'no "
                "change' would be a false negative dressed as a finding, and "
                "it is the failure mode this module exists to catch.",
    },
}


# ---------------------------------------------------------------------------
# Distributions
#
# Implemented rather than imported so the engine stays standard-library only.
# NormalDist covers the Gaussian; Student's t needs the regularised incomplete
# beta function, which is worth having exactly rather than approximating, since
# personal histories are short and the normal approximation is worst precisely
# where this module will be used.
# ---------------------------------------------------------------------------
_NORMAL = statistics.NormalDist()


def _betacf(a, b, x):
    """Continued fraction for the incomplete beta function (Lentz's method)."""
    tiny = 1e-30
    max_iterations = 300
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d

    for m in range(1, max_iterations + 1):
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
        if abs(delta - 1.0) < 3e-12:
            break
    return h


def regularised_incomplete_beta(a, b, x):
    """I_x(a, b), the regularised incomplete beta function."""
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


def student_t_cdf(t, df):
    """P(T <= t) for Student's t with ``df`` degrees of freedom."""
    if df <= 0:
        raise ChangeDetectionError("Degrees of freedom must be positive.")
    x = df / (df + t * t)
    tail = 0.5 * regularised_incomplete_beta(df / 2.0, 0.5, x)
    return 1.0 - tail if t > 0 else tail


def student_t_sf_two_sided(t, df):
    """The two-sided p-value for a t statistic."""
    return regularised_incomplete_beta(
        df / 2.0, 0.5, df / (df + t * t)
    )


def student_t_quantile(probability, df):
    """The inverse of ``student_t_cdf``, by bisection.

    Bisection rather than a closed-form approximation because this is called a
    handful of times per page load and being exactly right matters more than
    being fast. The normal quantile brackets the search.
    """
    if not 0.0 < probability < 1.0:
        raise ChangeDetectionError(
            "A quantile probability must sit strictly between 0 and 1."
        )
    if df <= 0:
        raise ChangeDetectionError("Degrees of freedom must be positive.")

    low, high = -100.0, 100.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if student_t_cdf(middle, df) < probability:
            low = middle
        else:
            high = middle
        if high - low < 1e-10:
            break
    return (low + high) / 2.0


def normal_quantile(probability):
    if not 0.0 < probability < 1.0:
        raise ChangeDetectionError(
            "A quantile probability must sit strictly between 0 and 1."
        )
    return _NORMAL.inv_cdf(probability)


# ---------------------------------------------------------------------------
# Baseline characterisation
# ---------------------------------------------------------------------------
def _clean_series(values, name="series"):
    if values is None:
        raise ChangeDetectionError(f"The {name} is missing.")
    cleaned = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            raise ChangeDetectionError(
                f"The {name} contains {value!r}, which is not a number."
            )
        if math.isnan(number) or math.isinf(number):
            raise ChangeDetectionError(
                f"The {name} contains a non-finite value."
            )
        cleaned.append(number)
    if not cleaned:
        raise ChangeDetectionError(f"The {name} is empty.")
    return cleaned


def linear_trend(values):
    """Ordinary least squares slope and intercept against the index."""
    n = len(values)
    if n < 2:
        return 0.0, values[0] if values else 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    covariance = sum(
        (index - mean_x) * (value - mean_y)
        for index, value in enumerate(values)
    )
    variance = sum((index - mean_x) ** 2 for index in range(n))
    if variance == 0:
        return 0.0, mean_y
    slope = covariance / variance
    return slope, mean_y - slope * mean_x


def lag1_autocorrelation(values):
    """The lag-1 autocorrelation of a residual series.

    Clamped to [-0.99, 0.99]. A value at the clamp means the series has no
    independent information left in it and the caller is warned rather than
    handed an effective sample size of a fraction of one observation.
    """
    n = len(values)
    if n < 3:
        return 0.0
    mean = sum(values) / n
    numerator = sum(
        (values[index] - mean) * (values[index + 1] - mean)
        for index in range(n - 1)
    )
    denominator = sum((value - mean) ** 2 for value in values)
    if denominator == 0:
        return 0.0
    return max(-0.99, min(0.99, numerator / denominator))


def variance_inflation(autocorrelation):
    """The factor by which AR(1) dependence inflates the variance of a mean."""
    rho = max(-0.99, min(0.99, float(autocorrelation)))
    return (1.0 + rho) / (1.0 - rho)


def effective_sample_size(n, autocorrelation):
    """Independent-equivalent observations in an autocorrelated series."""
    if n <= 0:
        raise ChangeDetectionError("A sample size must be positive.")
    inflation = variance_inflation(autocorrelation)
    return max(2.0, float(n) / inflation) if inflation > 0 else float(n)


def characterise_baseline(values, season_length=None):
    """Describe a series' own noise, which is what any change is judged against.

    Trend and seasonality are removed first. A footprint that rises every
    winter is not noisy, it is seasonal, and charging that variation to the
    error term would make every real change undetectable.
    """
    series = _clean_series(values, "baseline series")
    n = len(series)
    if n < 3:
        raise ChangeDetectionError(
            "A baseline needs at least three observations before anything can "
            "be said about its variation."
        )

    seasonal = {}
    if season_length and season_length > 1:
        if n < 2 * season_length:
            raise ChangeDetectionError(
                f"Removing a seasonal cycle of length {season_length} needs at "
                f"least two full cycles ({2 * season_length} observations); "
                f"this series has {n}. Estimating a seasonal profile from a "
                f"single cycle removes the very variation the test is supposed "
                f"to measure against."
            )
        seasonal = {phase: 0.0 for phase in range(season_length)}

    # Trend and seasonality are estimated by back-fitting rather than in one
    # pass. Removing a trend first biases the seasonal profile and removing
    # seasonality first biases the slope, because a seasonal pattern whose
    # phases are not symmetric about the midpoint induces a spurious trend of
    # its own. Alternating the two until they stop moving converges on the
    # answer that neither ordering reaches, and for a purely seasonal series it
    # drives the residual to zero, which is the behaviour the tests pin.
    slope, intercept = 0.0, 0.0
    for _ in range(50):
        deseasonalised = [
            value - seasonal.get(index % season_length, 0.0)
            if seasonal else value
            for index, value in enumerate(series)
        ]
        slope, intercept = linear_trend(deseasonalised)
        if not seasonal:
            break
        detrended = [
            value - (intercept + slope * index)
            for index, value in enumerate(series)
        ]
        updated = {}
        for phase in range(season_length):
            members = detrended[phase::season_length]
            updated[phase] = sum(members) / len(members)
        centre = sum(updated.values()) / season_length
        updated = {phase: value - centre for phase, value in updated.items()}
        moved = max(
            abs(updated[phase] - seasonal[phase])
            for phase in range(season_length)
        )
        seasonal = updated
        if moved < 1e-12:
            break

    residuals = [
        value - (intercept + slope * index)
        - seasonal.get(index % season_length, 0.0)
        if seasonal else value - (intercept + slope * index)
        for index, value in enumerate(series)
    ]

    residual_sd = (
        statistics.stdev(residuals) if len(residuals) > 1 else 0.0
    )
    rho = lag1_autocorrelation(residuals)
    effective_n = effective_sample_size(n, rho)
    mean = sum(series) / n

    warnings = []
    if n < MINIMUM_BASELINE:
        warnings.append(
            f"Only {n} observations. The noise estimate is itself uncertain "
            f"enough that a power calculation built on it should be read as "
            f"indicative rather than as a threshold."
        )
    if rho > SEVERE_AUTOCORRELATION:
        warnings.append(
            f"Lag-1 autocorrelation is {rho:.2f}. Consecutive periods carry "
            f"almost the same information, so {n} observations are worth about "
            f"{effective_n:.1f} independent ones. A test run on the raw count "
            f"would be badly overconfident."
        )
    if residual_sd == 0.0:
        warnings.append(
            "The residual variation is exactly zero, which in real "
            "consumption data means the series is synthetic, constant, or "
            "carrying a placeholder. No significance test is meaningful here."
        )

    return {
        "n": n,
        "mean": round(mean, 4),
        "residual_sd": round(residual_sd, 6),
        "coefficient_of_variation": (
            round(residual_sd / mean, 4) if mean else 0.0
        ),
        "trend_per_period": round(slope, 6),
        "seasonal_profile": {k: round(v, 4) for k, v in seasonal.items()},
        "season_length": season_length or 0,
        "lag1_autocorrelation": round(rho, 4),
        "variance_inflation": round(variance_inflation(rho), 4),
        "effective_n": round(effective_n, 3),
        "independence_loss": round(1.0 - effective_n / n, 4),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Power
# ---------------------------------------------------------------------------
def minimum_detectable_effect(residual_sd, n_before, n_after,
                              autocorrelation=0.0, alpha=DEFAULT_ALPHA,
                              power=DEFAULT_POWER):
    """The smallest change this much data could have detected.

    The headline number of the module. A user who reads it before reading a
    reported reduction knows immediately whether the reduction was ever within
    reach of their data.
    """
    sd = float(residual_sd)
    if sd < 0:
        raise ChangeDetectionError("A standard deviation cannot be negative.")
    if not 0.0 < alpha < 1.0:
        raise ChangeDetectionError("Alpha must sit strictly between 0 and 1.")
    if not 0.0 < power < 1.0:
        raise ChangeDetectionError("Power must sit strictly between 0 and 1.")

    eff_before = effective_sample_size(n_before, autocorrelation)
    eff_after = effective_sample_size(n_after, autocorrelation)
    df = max(1.0, eff_before + eff_after - 2.0)

    t_alpha = student_t_quantile(1.0 - alpha / 2.0, df)
    t_power = student_t_quantile(power, df)
    standard_error = sd * math.sqrt(1.0 / eff_before + 1.0 / eff_after)

    return {
        "mde": round((t_alpha + t_power) * standard_error, 6),
        "standard_error": round(standard_error, 6),
        "effective_n_before": round(eff_before, 3),
        "effective_n_after": round(eff_after, 3),
        "degrees_of_freedom": round(df, 3),
        "alpha": alpha,
        "power": power,
    }


def required_periods(residual_sd, target_effect, autocorrelation=0.0,
                     alpha=DEFAULT_ALPHA, power=DEFAULT_POWER,
                     max_periods=600):
    """How many periods per arm are needed to detect ``target_effect``.

    The most actionable output in the module: it turns "did it work?" into
    "ask again in N months", which is a question the data can eventually
    answer.
    """
    sd = float(residual_sd)
    effect = abs(float(target_effect))
    if effect <= 0:
        raise ChangeDetectionError(
            "A target effect of zero can never be detected, so no number of "
            "periods would be enough."
        )
    if sd == 0:
        return {
            "periods_per_arm": 2,
            "achievable": True,
            "note": "With no residual variation any non-zero difference is "
                    "detectable immediately. Confirm the series is real "
                    "before relying on that.",
        }

    inflation = variance_inflation(autocorrelation)
    for n in range(2, int(max_periods) + 1):
        effective = max(2.0, n / inflation)
        df = max(1.0, 2.0 * effective - 2.0)
        t_alpha = student_t_quantile(1.0 - alpha / 2.0, df)
        t_power = student_t_quantile(power, df)
        detectable = (t_alpha + t_power) * sd * math.sqrt(2.0 / effective)
        if detectable <= effect:
            return {
                "periods_per_arm": n,
                "effective_periods_per_arm": round(effective, 3),
                "achievable": True,
                "detectable_at_that_n": round(detectable, 6),
                "note": f"{n} periods on each side of the change, given a "
                        f"period-to-period standard deviation of {sd:,.2f} and "
                        f"a lag-1 autocorrelation of {autocorrelation:.2f}.",
            }

    return {
        "periods_per_arm": None,
        "achievable": False,
        "note": f"An effect of {effect:,.2f} is smaller than {max_periods} "
                f"periods of this series could separate from its own noise. "
                f"Measuring it is not a matter of waiting longer; it needs a "
                f"less noisy measurement.",
    }


def achieved_power(residual_sd, observed_effect, n_before, n_after,
                   autocorrelation=0.0, alpha=DEFAULT_ALPHA):
    """The probability this test would have detected the effect it observed."""
    sd = float(residual_sd)
    if sd == 0:
        return 1.0
    eff_before = effective_sample_size(n_before, autocorrelation)
    eff_after = effective_sample_size(n_after, autocorrelation)
    df = max(1.0, eff_before + eff_after - 2.0)
    standard_error = sd * math.sqrt(1.0 / eff_before + 1.0 / eff_after)
    if standard_error == 0:
        return 1.0
    critical = student_t_quantile(1.0 - alpha / 2.0, df)
    non_centrality = abs(float(observed_effect)) / standard_error
    return round(
        max(0.0, min(1.0, _NORMAL.cdf(non_centrality - critical))), 4
    )


# ---------------------------------------------------------------------------
# Shared-factor error
# ---------------------------------------------------------------------------
def combined_standard_error(sampling_error, difference, shared_factor_cv=0.0):
    """Standard error of a difference where both sides share an emission factor.

    The factor's uncertainty multiplies the *difference*, not the two levels,
    because it is the same factor on both sides and cancels. Treating the two
    intervals as independent adds an error term proportional to the levels,
    which for a small change against a large footprint is the difference
    between a detectable effect and an undetectable one.
    """
    sampling = abs(float(sampling_error))
    cv = abs(float(shared_factor_cv))
    if cv > 1.0:
        raise ChangeDetectionError(
            "A coefficient of variation above 1.0 means the factor's "
            "uncertainty exceeds the factor. Check the units."
        )
    shared = cv * abs(float(difference))
    return math.sqrt(sampling ** 2 + shared ** 2)


def naive_standard_error(sampling_error, before_level, after_level,
                         shared_factor_cv=0.0):
    """What the same calculation gives if the shared factor is double counted.

    Kept and reported so the correction is visible rather than asserted.
    """
    sampling = abs(float(sampling_error))
    cv = abs(float(shared_factor_cv))
    return math.sqrt(
        sampling ** 2
        + (cv * abs(float(before_level))) ** 2
        + (cv * abs(float(after_level))) ** 2
    )


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def compare_periods(before, after, meaningful_effect=None,
                    autocorrelation=None, alpha=DEFAULT_ALPHA,
                    power=DEFAULT_POWER, shared_factor_cv=0.0):
    """Compare two stretches of a series and return one of three verdicts.

    ``meaningful_effect`` is the change the user would act on. It is what makes
    the third verdict possible: without a stated effect size there is no way to
    distinguish "no effect" from "no power", and the module would be back to
    the two-verdict behaviour it exists to replace.
    """
    first = _clean_series(before, "before series")
    second = _clean_series(after, "after series")
    if len(first) < 2 or len(second) < 2:
        raise ChangeDetectionError(
            "Each side needs at least two observations. A single reading has "
            "no variation, and a comparison against it would be a difference "
            "with no error bar."
        )

    if autocorrelation is None:
        pooled = [
            value - sum(first) / len(first) for value in first
        ] + [
            value - sum(second) / len(second) for value in second
        ]
        autocorrelation = lag1_autocorrelation(pooled)

    mean_before = sum(first) / len(first)
    mean_after = sum(second) / len(second)
    difference = mean_after - mean_before

    var_before = statistics.variance(first)
    var_after = statistics.variance(second)
    eff_before = effective_sample_size(len(first), autocorrelation)
    eff_after = effective_sample_size(len(second), autocorrelation)

    sampling_error = math.sqrt(
        var_before / eff_before + var_after / eff_after
    )
    standard_error = combined_standard_error(
        sampling_error, difference, shared_factor_cv
    )
    naive = naive_standard_error(
        sampling_error, mean_before, mean_after, shared_factor_cv
    )

    if standard_error == 0:
        t_statistic = 0.0
        p_value = 1.0
        df = max(1.0, eff_before + eff_after - 2.0)
    else:
        term_before = var_before / eff_before
        term_after = var_after / eff_after
        denominator = (
            (term_before ** 2) / max(1.0, eff_before - 1.0)
            + (term_after ** 2) / max(1.0, eff_after - 1.0)
        )
        df = (
            ((term_before + term_after) ** 2) / denominator
            if denominator > 0 else max(1.0, eff_before + eff_after - 2.0)
        )
        df = max(1.0, df)
        t_statistic = difference / standard_error
        p_value = student_t_sf_two_sided(t_statistic, df)

    critical = student_t_quantile(1.0 - alpha / 2.0, df)
    margin = critical * standard_error

    pooled_sd = math.sqrt((var_before + var_after) / 2.0)
    mde = minimum_detectable_effect(
        pooled_sd, len(first), len(second), autocorrelation, alpha, power
    )
    target = (
        abs(float(meaningful_effect)) if meaningful_effect is not None
        else mde["mde"]
    )

    significant = p_value < alpha
    if significant:
        verdict = "detected"
    elif mde["mde"] > target:
        verdict = "underpowered"
    else:
        verdict = "not_detected"

    return {
        "verdict": verdict,
        "verdict_label": VERDICTS[verdict]["label"],
        "verdict_note": VERDICTS[verdict]["note"],
        "mean_before": round(mean_before, 4),
        "mean_after": round(mean_after, 4),
        "difference": round(difference, 4),
        "relative_change": (
            round(difference / mean_before, 4) if mean_before else 0.0
        ),
        "standard_error": round(standard_error, 6),
        "naive_standard_error": round(naive, 6),
        "shared_factor_saving": round(naive - standard_error, 6),
        "t_statistic": round(t_statistic, 4),
        "degrees_of_freedom": round(df, 3),
        "p_value": round(p_value, 6),
        "alpha": alpha,
        "confidence_interval": [
            round(difference - margin, 4), round(difference + margin, 4)
        ],
        "minimum_detectable_effect": mde["mde"],
        "meaningful_effect": round(target, 6),
        "achieved_power": achieved_power(
            pooled_sd, difference, len(first), len(second),
            autocorrelation, alpha
        ),
        "autocorrelation": round(float(autocorrelation), 4),
        "effective_n_before": round(eff_before, 3),
        "effective_n_after": round(eff_after, 3),
        "n_before": len(first),
        "n_after": len(second),
    }


# ---------------------------------------------------------------------------
# Sequential monitoring
# ---------------------------------------------------------------------------
def sequential_boundary(look, total_looks, alpha=DEFAULT_ALPHA):
    """An O'Brien-Fleming style critical value for a repeated look.

    Users check a dashboard constantly. Testing an accumulating series at
    p < 0.05 every time it updates guarantees a false positive eventually - at
    twelve monthly looks the chance of at least one spurious result is roughly
    one in three. The boundary is strict early and relaxes towards the nominal
    level at the final look, which is the standard answer and belongs in the
    code rather than in a footnote nobody reads.
    """
    look = int(look)
    total_looks = int(total_looks)
    if look < 1 or total_looks < 1 or look > total_looks:
        raise ChangeDetectionError(
            "A look must be numbered between one and the total number of "
            "planned looks."
        )
    nominal = normal_quantile(1.0 - alpha / 2.0)
    critical = nominal * math.sqrt(total_looks / look)
    boundary_alpha = 2.0 * (1.0 - _NORMAL.cdf(critical))
    return {
        "look": look,
        "total_looks": total_looks,
        "critical_z": round(critical, 4),
        "boundary_alpha": round(boundary_alpha, 6),
        "nominal_alpha": alpha,
        "naive_family_error": round(
            1.0 - (1.0 - alpha) ** total_looks, 4
        ),
    }


def sequential_verdict(z_statistic, look, total_looks, alpha=DEFAULT_ALPHA):
    """Whether an interim result crosses its boundary."""
    boundary = sequential_boundary(look, total_looks, alpha)
    crossed = abs(float(z_statistic)) >= boundary["critical_z"]
    return {
        **boundary,
        "z": round(float(z_statistic), 4),
        "crossed": crossed,
        "note": (
            "Crosses the boundary for this look, so it survives the fact that "
            "you have been checking repeatedly."
            if crossed else
            "Does not cross the boundary for this look. It may still be "
            "significant at the nominal level, which at this many looks is "
            "not the same as being real."
        ),
    }


# ---------------------------------------------------------------------------
# Multiple comparisons
# ---------------------------------------------------------------------------
def benjamini_hochberg(p_values, false_discovery_rate=DEFAULT_ALPHA):
    """Control the false discovery rate across a set of category tests.

    Testing eight footprint categories at once at p < 0.05 gives roughly a
    one-in-three chance of at least one spurious "significant" result, and the
    app displays exactly that sort of grid.
    """
    if not p_values:
        raise ChangeDetectionError("There are no p-values to correct.")
    if isinstance(p_values, dict):
        labels = list(p_values)
        values = [float(p_values[key]) for key in labels]
    else:
        values = [float(value) for value in p_values]
        labels = list(range(len(values)))

    for value in values:
        if not 0.0 <= value <= 1.0:
            raise ChangeDetectionError(
                f"{value!r} is not a p-value."
            )

    m = len(values)
    order = sorted(range(m), key=lambda index: values[index])

    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m - 1, -1, -1):
        index = order[rank]
        candidate = values[index] * m / (rank + 1)
        running = min(running, candidate)
        adjusted[index] = min(1.0, running)

    rejected = {
        labels[index]: adjusted[index] <= false_discovery_rate
        for index in range(m)
    }

    return {
        "false_discovery_rate": false_discovery_rate,
        "tests": m,
        "adjusted": {
            labels[index]: round(adjusted[index], 6) for index in range(m)
        },
        "rejected": rejected,
        "survivors": [label for label in labels if rejected[label]],
        "naive_significant": [
            labels[index] for index in range(m)
            if values[index] < false_discovery_rate
        ],
        "family_error_if_uncorrected": round(
            1.0 - (1.0 - false_discovery_rate) ** m, 4
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_detection_insights(comparison, baseline=None):
    """Plain-language findings, ordered by how much they should change a view."""
    insights = []

    change = comparison["difference"]
    relative = comparison["relative_change"] * 100.0
    direction = "lower" if change < 0 else "higher"

    if comparison["verdict"] == "detected":
        insights.append(
            f"The later period is {abs(change):,.1f} units {direction} "
            f"({relative:+.1f}%), and that is larger than this series' own "
            f"variation can plausibly produce (p = "
            f"{comparison['p_value']:.4f})."
        )
    elif comparison["verdict"] == "underpowered":
        insights.append(
            f"The observed difference is {abs(change):,.1f} units "
            f"({relative:+.1f}%), but the smallest change this much data could "
            f"have detected is {comparison['minimum_detectable_effect']:,.1f}. "
            f"This is not evidence that nothing happened - it is a "
            f"measurement that was never capable of answering the question."
        )
    else:
        insights.append(
            f"No change detected. The test had enough power to find an effect "
            f"of {comparison['meaningful_effect']:,.1f} units, and the "
            f"observed difference of {abs(change):,.1f} sits inside the range "
            f"this series produces on its own."
        )

    interval = comparison["confidence_interval"]
    insights.append(
        f"The difference is {change:+,.1f} units with a "
        f"{(1 - comparison['alpha']) * 100:.0f}% interval of "
        f"[{interval[0]:+,.1f}, {interval[1]:+,.1f}]. An interval spanning "
        f"zero means the direction itself is not established."
        if interval[0] <= 0 <= interval[1] else
        f"The difference is {change:+,.1f} units with a "
        f"{(1 - comparison['alpha']) * 100:.0f}% interval of "
        f"[{interval[0]:+,.1f}, {interval[1]:+,.1f}], which excludes zero."
    )

    if comparison["autocorrelation"] > 0.3:
        insights.append(
            f"Consecutive periods are correlated at {comparison['autocorrelation']:.2f}, "
            f"so {comparison['n_before']} and {comparison['n_after']} readings "
            f"are worth about {comparison['effective_n_before']:.1f} and "
            f"{comparison['effective_n_after']:.1f} independent ones. Ignoring "
            f"that would have made this result look stronger than it is."
        )

    if comparison["shared_factor_saving"] > 0:
        insights.append(
            f"Both periods use the same emission factors, so that uncertainty "
            f"largely cancels in the difference. Treating the two estimates as "
            f"independent would have inflated the standard error by "
            f"{comparison['shared_factor_saving']:,.2f} units and could have "
            f"buried a real change."
        )

    if comparison["achieved_power"] < 0.5 and comparison["verdict"] != "detected":
        insights.append(
            f"Achieved power against the observed effect is "
            f"{comparison['achieved_power'] * 100:.0f}%. A coin flip has more "
            f"claim to be called a test."
        )

    if baseline:
        for warning in baseline.get("warnings", []):
            insights.append(warning)

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS change_detection_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            verdict TEXT NOT NULL,
            difference REAL NOT NULL,
            p_value REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_change_detection_tests_user
        ON change_detection_tests (user_id)
        """
    )


def save_test(user_id, name, comparison):
    """Persist a comparison and return its row id."""
    if not user_id:
        raise ChangeDetectionError("A test needs a user to belong to.")
    if not name or not str(name).strip():
        raise ChangeDetectionError("A test needs a name.")

    payload = json.dumps({
        key: comparison[key] for key in (
            "verdict", "mean_before", "mean_after", "difference",
            "relative_change", "standard_error", "t_statistic",
            "degrees_of_freedom", "p_value", "confidence_interval",
            "minimum_detectable_effect", "meaningful_effect",
            "achieved_power", "autocorrelation", "n_before", "n_after",
        ) if key in comparison
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO change_detection_tests
                (user_id, name, payload, verdict, difference, p_value)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), str(name).strip(), payload,
                comparison["verdict"], float(comparison["difference"]),
                float(comparison["p_value"]),
            ),
        )
        return int(cursor.lastrowid)


def get_tests(user_id, limit=25):
    """Saved tests for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, verdict, difference, p_value,
                       created_at
                FROM change_detection_tests
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved change detection tests")
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
            "verdict": row[3],
            "difference": row[4],
            "p_value": row[5],
            "created_at": row[6],
        })
    return saved


def delete_test(user_id, test_id):
    """Delete one saved test. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM change_detection_tests "
                "WHERE id = ? AND user_id = ?",
                (test_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete change detection test %s", test_id)
        return False


# ---------------------------------------------------------------------------
# Small accessors used by the page
# ---------------------------------------------------------------------------
def list_verdicts():
    return list(VERDICTS)


def get_verdict(key):
    if key not in VERDICTS:
        raise ChangeDetectionError(f"{key!r} is not a known verdict.")
    return dict(VERDICTS[key])
