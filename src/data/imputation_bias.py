"""Missingness mechanism diagnosis and multiple imputation for assessments.

`src.data.data_quality.detect_missing_fields` finds the gaps and flags them.
Then the pipeline moves on, and every consumer downstream fills the gap with a
zero.

Zero is not a neutral filler. A missing `flights` field filled with zero is an
assertion that the user took no flights. A missing `electricity_kwh` filled
with zero is an assertion that the house used no power. The app is not failing
to handle missing data; it is answering the question the missing data was
supposed to answer, and answering it in the one direction that always lowers
the footprint.

That bias compounds. The zero-filled row enters `analyse_trend()` as a real
improvement, enters the leaderboard as a genuinely low footprint, and enters
the forecast as a data point. Nobody downstream can tell it from a measurement.

Three mechanisms, three different answers
-----------------------------------------
**MCAR** — missing completely at random. The gaps carry no information.
Complete-case analysis is unbiased and any sensible imputation works.

**MAR** — missing at random *given the observed data*. Whether a field is
missing depends on things we did record. Recoverable: condition on those
things and impute.

**MNAR** — missing not at random. Whether a field is missing depends on the
value that is missing. Someone skips the flights question in the months they
flew. **This is not testable from the observed data**, by definition, and any
module claiming to detect it is wrong. What can be done is a sensitivity
analysis: shift the imputed values by a stated amount and report how far that
shift has to go before the conclusion flips.

The app currently treats all three identically, which means it treats the
dangerous one as though it were the harmless one.

Why single imputation is not the fix
------------------------------------
Mean-fill and last-value-carried-forward remove the bias in the point estimate
and destroy the variance. One filled value gets treated as a measured value, so
the imputed series looks *more* certain than the measured one, and a trend
fitted through carried-forward values reports a stability that is an artefact
of the fill.

Rubin's rules exist for exactly this. Impute m times, drawing from a predictive
distribution rather than taking its centre; analyse each completed dataset;
pool::

    Q_bar = mean of the m estimates
    U_bar = mean of the m within-imputation variances
    B     = variance between the m estimates
    T     = U_bar + (1 + 1/m) B

`B` is the part single imputation throws away, and the fraction of missing
information that falls out of it is the number that tells a user how much of
their footprint is measured and how much is model.

Statistical machinery
---------------------
Chi-square and Student-t distribution functions are implemented here from the
incomplete gamma and incomplete beta functions, because this repo carries no
scientific stack and the alternative is normal approximations that are wrong
at exactly the small degrees of freedom multiple imputation produces.

Refusals
--------
No imputation of a field missing in every record — there is nothing to learn
from. No pooled estimate above a missingness ceiling, where the output would be
mostly model and barely data. No MNAR verdict, ever.
"""

from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import statistics
from typing import Any, Iterable, Mapping, Sequence

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

ENGINE_VERSION = "1.0.0"

# Imputation ----------------------------------------------------------------
DEFAULT_IMPUTATIONS = 20
MIN_IMPUTATIONS = 2
MAX_IMPUTATIONS = 200
DEFAULT_SEED = 20240930

# Ceilings ------------------------------------------------------------------
MISSINGNESS_CEILING = 0.60
MIN_COMPLETE_CASES = 4
MIN_RECORDS = 3
MAX_FIELDS = 24

# Evidence thresholds -------------------------------------------------------
MCAR_ALPHA = 0.05
MAR_EFFECT_FLOOR = 0.35
HIGH_FMI = 0.5
MODERATE_FMI = 0.2

# Regression ----------------------------------------------------------------
RIDGE = 1e-8
MIN_PREDICTOR_ROWS = 5

STRATEGIES: dict[str, dict[str, str]] = {
    "zero": {
        "label": "Zero fill",
        "note": "What the app does today. Asserts the activity did not happen.",
        "bias": "downward",
    },
    "mean": {
        "label": "Mean fill",
        "note": "Unbiased in the mean, destroys the variance.",
        "bias": "variance",
    },
    "median": {
        "label": "Median fill",
        "note": "Robust centre, same variance problem as mean fill.",
        "bias": "variance",
    },
    "locf": {
        "label": "Last value carried forward",
        "note": "Invents a stability the data does not contain.",
        "bias": "variance",
    },
    "regression": {
        "label": "Regression (single)",
        "note": "Conditions on the observed fields. Still one value, still too certain.",
        "bias": "variance",
    },
    "multiple": {
        "label": "Multiple imputation",
        "note": "Draws with residual noise, pools by Rubin's rules.",
        "bias": "none",
    },
}


class ImputationError(ValueError):
    """Raised when a dataset cannot be analysed as asked."""


# ---------------------------------------------------------------------------
# Small numerics
# ---------------------------------------------------------------------------


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _variance(values: Sequence[float]) -> float:
    return float(statistics.variance(values)) if len(values) > 1 else 0.0


def gamma_upper_regularised(shape: float, value: float) -> float:
    """Regularised upper incomplete gamma Q(a, x), by series or continued
    fraction depending on which converges.

    Needed for chi-square tail probabilities, which Little's MCAR test reports
    and which cannot be approximated by a normal at the degrees of freedom a
    handful of missingness patterns produces.
    """
    if value < 0 or shape <= 0:
        raise ImputationError("Invalid arguments to the incomplete gamma function.")
    if value == 0:
        return 1.0

    if value < shape + 1.0:
        # Series expansion for P(a, x), then complement.
        term = 1.0 / shape
        total = term
        current = shape
        for _ in range(500):
            current += 1.0
            term *= value / current
            total += term
            if abs(term) < abs(total) * 1e-14:
                break
        return 1.0 - total * math.exp(-value + shape * math.log(value) - math.lgamma(shape))

    # Lentz's continued fraction for Q(a, x).
    tiny = 1e-300
    b = value + 1.0 - shape
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for index in range(1, 500):
        an = -index * (index - shape)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return h * math.exp(-value + shape * math.log(value) - math.lgamma(shape))


def chi2_sf(statistic: float, degrees_of_freedom: int) -> float:
    """Upper tail of the chi-square distribution."""
    if degrees_of_freedom <= 0:
        raise ImputationError("Chi-square needs at least one degree of freedom.")
    if statistic <= 0:
        return 1.0
    return gamma_upper_regularised(degrees_of_freedom / 2.0, statistic / 2.0)


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
    """Regularised incomplete beta function I_x(a, b)."""
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
        raise ImputationError("Student-t needs positive degrees of freedom.")
    z = degrees_of_freedom / (degrees_of_freedom + value * value)
    tail = 0.5 * betai(degrees_of_freedom / 2.0, 0.5, z)
    return 1.0 - tail if value > 0 else tail


def t_ppf(probability: float, degrees_of_freedom: float) -> float:
    """Inverse Student-t by bisection on the exact CDF.

    Bisection rather than an expansion because multiple imputation routinely
    produces degrees of freedom in the single digits, where the Cornish-Fisher
    expansions everyone reaches for are worst. Two hundred halvings of a
    [-400, 400] bracket is exact to well past any use this module has.
    """
    if not 0.0 < probability < 1.0:
        raise ImputationError("Probability for t_ppf must lie strictly in (0, 1).")
    if degrees_of_freedom <= 0:
        raise ImputationError("Student-t needs positive degrees of freedom.")

    low, high = -400.0, 400.0
    for _ in range(200):
        middle = (low + high) / 2.0
        if t_cdf(middle, degrees_of_freedom) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    """Gaussian elimination with partial pivoting; None if singular."""
    size = len(vector)
    augmented = [list(matrix[row]) + [vector[row]] for row in range(size)]

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


# ---------------------------------------------------------------------------
# Fields and records
# ---------------------------------------------------------------------------


def build_field(
    name: str,
    factor: float = 1.0,
    unit: str = "",
    floor: float | None = 0.0,
    label: str = "",
) -> dict[str, Any]:
    """One activity field and the emission factor that turns it into kg CO2e."""
    key = str(name or "").strip()
    if not key:
        raise ImputationError("Every field needs a name.")
    multiplier = _finite(factor)
    if multiplier is None:
        raise ImputationError("Field '%s' needs a finite emission factor." % key)
    return {
        "name": key,
        "label": str(label or key),
        "factor": multiplier,
        "unit": str(unit or ""),
        "floor": _finite(floor),
    }


def _validate_fields(fields: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    if not fields:
        raise ImputationError("At least one field is required.")
    if len(fields) > MAX_FIELDS:
        raise ImputationError("At most %d fields are supported." % MAX_FIELDS)
    seen: set[str] = set()
    cleaned = []
    for field in fields:
        if not isinstance(field, dict) or "factor" not in field:
            raise ImputationError("Fields must be built with build_field().")
        if field["name"] in seen:
            raise ImputationError("Field '%s' appears twice." % field["name"])
        seen.add(field["name"])
        cleaned.append(dict(field))
    return cleaned


def normalise_records(
    records: Sequence[Mapping[str, Any]],
    fields: Sequence[dict[str, Any]],
) -> list[dict[str, float | None]]:
    """Coerce raw rows to floats, with None for anything absent or unusable.

    A key that is present with a value of None, a blank string or a non-numeric
    value is missing. A key that is absent is missing. Those are the same thing
    and are represented the same way, because the downstream question is
    identical.
    """
    cleaned_fields = _validate_fields(fields)
    if not records:
        raise ImputationError("No records supplied.")

    rows: list[dict[str, float | None]] = []
    for record in records:
        row: dict[str, float | None] = {}
        for field in cleaned_fields:
            raw = record.get(field["name"]) if isinstance(record, Mapping) else None
            value = _finite(raw)
            if value is not None and field["floor"] is not None:
                value = max(value, field["floor"])
            row[field["name"]] = value
        rows.append(row)
    return rows


def record_footprint(
    row: Mapping[str, float | None],
    fields: Sequence[dict[str, Any]],
) -> float | None:
    """Footprint of one complete row; None if any field is still missing."""
    total = 0.0
    for field in fields:
        value = row.get(field["name"])
        if value is None:
            return None
        total += value * field["factor"]
    return total


# ---------------------------------------------------------------------------
# The missingness map
# ---------------------------------------------------------------------------


def missingness_map(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Where the gaps are, and whether they arrive together.

    Fields that always vanish as a group usually vanish for one reason, and
    knowing that is often more diagnostic than any test statistic.
    """
    names = [field["name"] for field in fields]
    count = len(rows)
    if count < MIN_RECORDS:
        raise ImputationError(
            "Need at least %d records to say anything about missingness." % MIN_RECORDS
        )

    per_field = []
    for name in names:
        missing = sum(1 for row in rows if row.get(name) is None)
        per_field.append(
            {
                "name": name,
                "missing": missing,
                "observed": count - missing,
                "rate": missing / count,
                "all_missing": missing == count,
                "complete": missing == 0,
            }
        )

    patterns: dict[str, int] = {}
    for row in rows:
        key = "".join("0" if row.get(name) is None else "1" for name in names)
        patterns[key] = patterns.get(key, 0) + 1

    co_occurrence: dict[str, dict[str, float]] = {}
    for left in names:
        co_occurrence[left] = {}
        left_missing = [index for index, row in enumerate(rows) if row.get(left) is None]
        for right in names:
            if left == right or not left_missing:
                co_occurrence[left][right] = 0.0
                continue
            both = sum(1 for index in left_missing if rows[index].get(right) is None)
            co_occurrence[left][right] = both / len(left_missing)

    complete_cases = sum(1 for row in rows if all(row.get(name) is not None for name in names))
    ordered_patterns = sorted(patterns.items(), key=lambda item: item[1], reverse=True)

    return {
        "records": count,
        "fields": names,
        "per_field": per_field,
        "patterns": [
            {"pattern": key, "records": value, "share": value / count}
            for key, value in ordered_patterns
        ],
        "pattern_count": len(patterns),
        "co_occurrence": co_occurrence,
        "complete_cases": complete_cases,
        "complete_case_share": complete_cases / count,
        "monotone": _is_monotone(rows, names),
        "overall_rate": sum(entry["missing"] for entry in per_field)
        / (count * len(names)),
    }


def _is_monotone(
    rows: Sequence[Mapping[str, float | None]],
    names: Sequence[str],
) -> bool:
    """True if the fields can be ordered so that missingness is nested.

    Monotone patterns admit a much simpler sequential imputation. Arbitrary
    patterns do not, and the distinction is worth reporting because it changes
    what a correct imputation looks like.
    """
    order = sorted(
        names,
        key=lambda name: sum(1 for row in rows if row.get(name) is None),
    )
    for row in rows:
        seen_missing = False
        for name in order:
            if row.get(name) is None:
                seen_missing = True
            elif seen_missing:
                return False
    return True


# ---------------------------------------------------------------------------
# Mechanism evidence
# ---------------------------------------------------------------------------


def little_mcar_test(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Little's test for missing completely at random.

    The idea is simple even though the full statistic is not: under MCAR, the
    observed values in every missingness pattern are draws from the same
    distribution. So compare each pattern's observed means against the overall
    means, weight by the pattern size and the variance, and sum.

    Implemented here in its diagonal form — the pattern means are compared
    against the grand means using the marginal variances rather than the full
    covariance matrix. That is a conservative simplification: it ignores
    covariance between fields, so it has less power than the full statistic. It
    does not have the opposite failure, which is the one that would matter, and
    it does not require inverting a covariance matrix estimated from a handful
    of assessments.

    A non-significant result is not evidence of MCAR. It is an absence of
    evidence against it, and this returns a verdict phrased that way.
    """
    names = [field["name"] for field in fields]
    count = len(rows)
    if count < MIN_RECORDS:
        raise ImputationError("Too few records for an MCAR test.")

    grand: dict[str, float] = {}
    spread: dict[str, float] = {}
    for name in names:
        observed = [row[name] for row in rows if row.get(name) is not None]
        if len(observed) < 2:
            continue
        grand[name] = _mean(observed)
        spread[name] = _variance(observed)

    groups: dict[str, list[Mapping[str, float | None]]] = {}
    for row in rows:
        key = "".join("0" if row.get(name) is None else "1" for name in names)
        groups.setdefault(key, []).append(row)

    statistic = 0.0
    degrees = 0
    contributions = []
    for key, members in groups.items():
        size = len(members)
        pattern_terms = 0.0
        used = 0
        for name in names:
            if name not in grand or spread.get(name, 0.0) <= 0:
                continue
            values = [row[name] for row in members if row.get(name) is not None]
            if not values:
                continue
            difference = _mean(values) - grand[name]
            pattern_terms += size * (difference ** 2) / spread[name]
            used += 1
        statistic += pattern_terms
        degrees += used
        contributions.append(
            {"pattern": key, "records": size, "contribution": pattern_terms}
        )

    degrees = max(0, degrees - len([name for name in names if name in grand]))
    if degrees <= 0:
        return {
            "statistic": statistic,
            "degrees_of_freedom": 0,
            "p_value": None,
            "verdict": "untestable",
            "headline": "Only one missingness pattern — nothing to compare against.",
            "contributions": contributions,
        }

    p_value = chi2_sf(statistic, degrees)
    rejected = p_value < MCAR_ALPHA
    return {
        "statistic": statistic,
        "degrees_of_freedom": degrees,
        "p_value": p_value,
        "verdict": "mcar_rejected" if rejected else "mcar_not_rejected",
        "headline": (
            "MCAR rejected (chi2=%.2f, df=%d, p=%.4f). The rows with gaps differ "
            "from the rows without them, so dropping incomplete rows changes the "
            "population being described." % (statistic, degrees, p_value)
            if rejected
            else "No evidence against MCAR (chi2=%.2f, df=%d, p=%.3f). That is an "
            "absence of evidence, not evidence of absence — the test has little "
            "power at this sample size." % (statistic, degrees, p_value)
        ),
        "contributions": contributions,
    }


def mar_evidence(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    target: str,
) -> dict[str, Any]:
    """Is `target`'s missingness associated with the other observed fields?

    For each other field, compare its observed values between the rows where
    `target` is present and the rows where it is not, as a standardised mean
    difference with a Welch t-test. A strong association means the missingness
    is predictable from data we hold, which is what makes imputation work.

    This tests MAR *against* MCAR. It cannot rule out MNAR, and nothing can.
    """
    names = [field["name"] for field in fields]
    if target not in names:
        raise ImputationError("Unknown field '%s'." % target)

    present = [row for row in rows if row.get(target) is not None]
    absent = [row for row in rows if row.get(target) is None]

    if not absent:
        return {
            "target": target,
            "missing_records": 0,
            "predictors": [],
            "verdict": "complete",
            "headline": "'%s' is never missing." % target,
        }
    if not present:
        raise ImputationError(
            "'%s' is missing in every record. There is nothing to learn its "
            "distribution from, so it cannot be imputed — it has to be "
            "collected or dropped from the estimand." % target
        )

    predictors = []
    for name in names:
        if name == target:
            continue
        with_values = [row[name] for row in present if row.get(name) is not None]
        without_values = [row[name] for row in absent if row.get(name) is not None]
        if len(with_values) < 2 or len(without_values) < 2:
            continue

        mean_with, mean_without = _mean(with_values), _mean(without_values)
        var_with, var_without = _variance(with_values), _variance(without_values)
        pooled = math.sqrt((var_with + var_without) / 2.0)
        effect = (mean_without - mean_with) / pooled if pooled > 0 else 0.0

        standard_error = math.sqrt(
            var_with / len(with_values) + var_without / len(without_values)
        )
        if standard_error > 0:
            statistic = (mean_without - mean_with) / standard_error
            numerator = (var_with / len(with_values) + var_without / len(without_values)) ** 2
            denominator = (
                (var_with / len(with_values)) ** 2 / max(len(with_values) - 1, 1)
                + (var_without / len(without_values)) ** 2 / max(len(without_values) - 1, 1)
            )
            degrees = numerator / denominator if denominator > 0 else 1.0
            p_value = 2.0 * (1.0 - t_cdf(abs(statistic), max(degrees, 1.0)))
        else:
            statistic, degrees, p_value = 0.0, 1.0, 1.0

        predictors.append(
            {
                "name": name,
                "mean_when_present": mean_with,
                "mean_when_missing": mean_without,
                "standardised_difference": effect,
                "t_statistic": statistic,
                "degrees_of_freedom": degrees,
                "p_value": p_value,
                "informative": abs(effect) >= MAR_EFFECT_FLOOR,
            }
        )

    predictors.sort(key=lambda entry: abs(entry["standardised_difference"]), reverse=True)
    informative = [entry["name"] for entry in predictors if entry["informative"]]

    return {
        "target": target,
        "missing_records": len(absent),
        "missing_rate": len(absent) / len(rows),
        "predictors": predictors,
        "informative_predictors": informative,
        "verdict": "mar_supported" if informative else "no_observed_association",
        "headline": (
            "'%s' goes missing in a way that tracks %s. Conditioning on "
            "%s is what makes imputation work here."
            % (target, ", ".join(informative), "them" if len(informative) > 1 else "it")
            if informative
            else "No observed field predicts whether '%s' is missing. That is "
            "consistent with MCAR and equally consistent with MNAR, which the "
            "observed data cannot distinguish." % target
        ),
    }


def mechanism_report(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """MCAR test plus per-field MAR evidence, plus the MNAR caveat.

    The MNAR entry is not a verdict and never will be. It is a statement that
    the question is unanswerable from this data, and a pointer to the
    sensitivity analysis that is the only honest response to it.
    """
    cleaned = _validate_fields(fields)
    mcar = little_mcar_test(rows, cleaned)

    per_field = []
    for field in cleaned:
        missing = sum(1 for row in rows if row.get(field["name"]) is None)
        if missing == 0 or missing == len(rows):
            continue
        per_field.append(mar_evidence(rows, cleaned, field["name"]))

    return {
        "mcar": mcar,
        "mar": per_field,
        "mnar": {
            "testable": False,
            "headline": (
                "MNAR cannot be tested from observed data. If people skip the "
                "flights question in the months they flew, nothing in this "
                "dataset records that. Use the delta sensitivity analysis and "
                "report the tipping point instead of a verdict."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Imputation strategies
# ---------------------------------------------------------------------------


def _observed(rows: Sequence[Mapping[str, float | None]], name: str) -> list[float]:
    return [row[name] for row in rows if row.get(name) is not None]


def impute_constant(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    value: float = 0.0,
) -> list[dict[str, float]]:
    """Fill every gap with the same number. Zero fill lives here."""
    return [
        {
            field["name"]: (
                row[field["name"]] if row.get(field["name"]) is not None else float(value)
            )
            for field in fields
        }
        for row in rows
    ]


def impute_centre(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    statistic_name: str = "mean",
) -> list[dict[str, float]]:
    """Fill with the observed mean or median of that field."""
    centres: dict[str, float] = {}
    for field in fields:
        observed = _observed(rows, field["name"])
        if not observed:
            raise ImputationError(
                "'%s' is missing in every record and has no centre to fill from."
                % field["name"]
            )
        centres[field["name"]] = (
            _mean(observed) if statistic_name == "mean" else statistics.median(observed)
        )
    return [
        {
            field["name"]: (
                row[field["name"]]
                if row.get(field["name"]) is not None
                else centres[field["name"]]
            )
            for field in fields
        }
        for row in rows
    ]


def impute_locf(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
) -> list[dict[str, float]]:
    """Last value carried forward, falling back to the next value at the start.

    Included so its damage can be measured, not because it is recommended. A
    trend fitted through carried-forward values reports a stability that is an
    artefact of the fill.
    """
    filled: list[dict[str, float]] = []
    last: dict[str, float] = {}
    for field in fields:
        observed = _observed(rows, field["name"])
        if not observed:
            raise ImputationError(
                "'%s' is missing in every record." % field["name"]
            )

    for row in rows:
        current: dict[str, float] = {}
        for field in fields:
            name = field["name"]
            value = row.get(name)
            if value is not None:
                last[name] = value
                current[name] = value
            elif name in last:
                current[name] = last[name]
            else:
                current[name] = None  # filled on the backward pass
        filled.append(current)

    # Backward fill for gaps that precede the first observation.
    for field in fields:
        name = field["name"]
        upcoming: float | None = None
        for index in range(len(filled) - 1, -1, -1):
            if filled[index][name] is None:
                filled[index][name] = upcoming
            else:
                upcoming = filled[index][name]
    return filled


def fit_regression(
    rows: Sequence[Mapping[str, float | None]],
    target: str,
    predictors: Sequence[str],
) -> dict[str, Any] | None:
    """OLS of `target` on `predictors` over the rows where all are observed.

    Returns None when there is not enough complete data to fit, which is the
    common case on short assessment histories and is why every caller has a
    centre-fill fallback.
    """
    usable = [
        row
        for row in rows
        if row.get(target) is not None
        and all(row.get(name) is not None for name in predictors)
    ]
    if len(usable) < max(MIN_PREDICTOR_ROWS, len(predictors) + 2):
        return None

    size = len(predictors) + 1
    xtx = [[0.0] * size for _ in range(size)]
    xty = [0.0] * size

    for row in usable:
        design = [1.0] + [float(row[name]) for name in predictors]
        response = float(row[target])
        for left in range(size):
            xty[left] += design[left] * response
            for right in range(size):
                xtx[left][right] += design[left] * design[right]

    for index in range(size):
        xtx[index][index] += RIDGE

    coefficients = _solve(xtx, xty)
    if coefficients is None:
        return None

    residuals = []
    for row in usable:
        design = [1.0] + [float(row[name]) for name in predictors]
        predicted = sum(coefficients[index] * design[index] for index in range(size))
        residuals.append(float(row[target]) - predicted)

    degrees = max(1, len(usable) - size)
    residual_variance = sum(value ** 2 for value in residuals) / degrees

    return {
        "target": target,
        "predictors": list(predictors),
        "coefficients": coefficients,
        "residual_sd": math.sqrt(max(residual_variance, 0.0)),
        "rows": len(usable),
        "residuals": residuals,
    }


def _predict(model: Mapping[str, Any], row: Mapping[str, float | None]) -> float | None:
    design = [1.0]
    for name in model["predictors"]:
        value = row.get(name)
        if value is None:
            return None
        design.append(float(value))
    coefficients = model["coefficients"]
    return sum(coefficients[index] * design[index] for index in range(len(design)))


def impute_regression(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    noise: bool = False,
    rng: random.Random | None = None,
) -> list[dict[str, float]]:
    """Condition each missing value on the fields observed in the same row.

    With `noise=False` this is single regression imputation: better centred
    than mean fill and just as over-confident, because every filled value sits
    exactly on the fitted line. With `noise=True` a residual is drawn and added,
    which is what makes the m datasets of a multiple imputation differ from
    each other and is the entire source of the between-imputation variance.
    """
    generator = rng or random.Random(DEFAULT_SEED)
    names = [field["name"] for field in fields]
    filled = [
        {name: row.get(name) for name in names}
        for row in rows
    ]

    for field in fields:
        target = field["name"]
        gaps = [index for index, row in enumerate(rows) if row.get(target) is None]
        if not gaps:
            continue
        observed = _observed(rows, target)
        if not observed:
            raise ImputationError("'%s' is missing in every record." % target)

        fallback = _mean(observed)
        spread = math.sqrt(_variance(observed))
        others = [name for name in names if name != target]
        model = fit_regression(rows, target, others) if others else None

        for index in gaps:
            value = _predict(model, rows[index]) if model else None
            residual_sd = model["residual_sd"] if model else spread
            if value is None:
                value = fallback
                residual_sd = spread
            if noise and residual_sd > 0:
                value += generator.gauss(0.0, residual_sd)
            if field["floor"] is not None:
                value = max(value, field["floor"])
            filled[index][target] = value

    return filled


# ---------------------------------------------------------------------------
# Rubin's rules
# ---------------------------------------------------------------------------


def pool(
    estimates: Sequence[float],
    variances: Sequence[float],
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Combine m imputed analyses by Rubin's rules.

    ``T = U_bar + (1 + 1/m) B`` where ``U_bar`` is the average within-imputation
    variance and ``B`` is the variance between the m point estimates. ``B`` is
    the term single imputation throws away, and the fraction of missing
    information derived from it is the honest answer to "how much of this
    number is measured".

    Degrees of freedom by Rubin's 1987 formula. It can become very large when
    B is small, which is correct: with nothing missing there is no extra
    uncertainty and the t interval collapses onto the normal one.
    """
    if len(estimates) != len(variances):
        raise ImputationError("Estimates and variances must be the same length.")
    m = len(estimates)
    if m < MIN_IMPUTATIONS:
        raise ImputationError(
            "Pooling needs at least %d imputations; with one there is no "
            "between-imputation variance to measure." % MIN_IMPUTATIONS
        )

    q_bar = _mean(list(estimates))
    u_bar = _mean(list(variances))
    between = _variance(list(estimates))
    total = u_bar + (1.0 + 1.0 / m) * between

    if total <= 0:
        return {
            "estimate": q_bar,
            "within_variance": u_bar,
            "between_variance": between,
            "total_variance": 0.0,
            "standard_error": 0.0,
            "degrees_of_freedom": float("inf"),
            "fraction_missing_information": 0.0,
            "relative_increase": 0.0,
            "imputations": m,
            "confidence": confidence,
            "lower": q_bar,
            "upper": q_bar,
        }

    relative_increase = ((1.0 + 1.0 / m) * between) / u_bar if u_bar > 0 else float("inf")
    if math.isinf(relative_increase):
        degrees = float(m - 1)
    else:
        degrees = (m - 1) * (1.0 + 1.0 / relative_increase) ** 2 if relative_increase > 0 else 1e9
    degrees = max(1.0, min(degrees, 1e9))

    fmi = ((1.0 + 1.0 / m) * between) / total
    standard_error = math.sqrt(total)
    tail = (1.0 - confidence) / 2.0
    critical = t_ppf(1.0 - tail, degrees)

    return {
        "estimate": q_bar,
        "within_variance": u_bar,
        "between_variance": between,
        "total_variance": total,
        "standard_error": standard_error,
        "degrees_of_freedom": degrees,
        "fraction_missing_information": min(1.0, max(0.0, fmi)),
        "relative_increase": relative_increase,
        "imputations": m,
        "confidence": confidence,
        "critical_value": critical,
        "lower": q_bar - critical * standard_error,
        "upper": q_bar + critical * standard_error,
    }


def _estimand(
    filled: Sequence[Mapping[str, float]],
    fields: Sequence[dict[str, Any]],
) -> tuple[float, float]:
    """Mean footprint per record and its sampling variance."""
    footprints = []
    for row in filled:
        total = 0.0
        for field in fields:
            total += float(row[field["name"]]) * field["factor"]
        footprints.append(total)
    n = len(footprints)
    mean = _mean(footprints)
    variance = _variance(footprints) / n if n > 1 else 0.0
    return mean, variance


def multiple_imputation(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    imputations: int = DEFAULT_IMPUTATIONS,
    seed: int | None = DEFAULT_SEED,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Impute m times with residual noise, analyse each, pool by Rubin.

    Refuses above the missingness ceiling. Past that point the pooled estimate
    is mostly model output, and a confidence interval around it is a statement
    about the imputation rather than about the household.
    """
    cleaned = _validate_fields(fields)
    m = int(min(max(int(imputations), MIN_IMPUTATIONS), MAX_IMPUTATIONS))
    overview = missingness_map(rows, cleaned)

    for entry in overview["per_field"]:
        if entry["all_missing"]:
            raise ImputationError(
                "'%s' is missing in every record. It cannot be imputed — there "
                "is nothing to learn its distribution from." % entry["name"]
            )
    if overview["overall_rate"] > MISSINGNESS_CEILING:
        raise ImputationError(
            "%.0f%% of all values are missing, above the %.0f%% ceiling. A "
            "pooled estimate here would be mostly model and barely data."
            % (overview["overall_rate"] * 100.0, MISSINGNESS_CEILING * 100.0)
        )

    estimates: list[float] = []
    variances: list[float] = []
    datasets: list[list[dict[str, float]]] = []
    for draw in range(m):
        rng = random.Random((seed or 0) + draw * 7919)
        filled = impute_regression(rows, cleaned, noise=True, rng=rng)
        estimate, variance = _estimand(filled, cleaned)
        estimates.append(estimate)
        variances.append(variance)
        datasets.append(filled)

    pooled = pool(estimates, variances, confidence)
    pooled["missingness"] = overview
    pooled["estimates"] = estimates
    pooled["datasets"] = datasets
    pooled["information_verdict"] = _information_verdict(
        pooled["fraction_missing_information"]
    )
    return pooled


def _information_verdict(fmi: float) -> dict[str, Any]:
    """Turn the fraction of missing information into something readable."""
    if fmi >= HIGH_FMI:
        return {
            "level": "high",
            "headline": "%.0f%% of the information in this estimate is missing." % (fmi * 100.0),
            "detail": (
                "More than half the uncertainty comes from values that were "
                "never collected. Treat this as an indication, not a "
                "measurement, and collect the missing fields before comparing "
                "it to anything."
            ),
        }
    if fmi >= MODERATE_FMI:
        return {
            "level": "moderate",
            "headline": "%.0f%% of the information is missing." % (fmi * 100.0),
            "detail": (
                "A meaningful share of the interval comes from imputation. "
                "Year-on-year comparisons should be read against the pooled "
                "interval rather than the point estimate."
            ),
        }
    return {
        "level": "low",
        "headline": "%.0f%% of the information is missing." % (fmi * 100.0),
        "detail": "The estimate is dominated by measured values.",
    }


# ---------------------------------------------------------------------------
# Strategy comparison
# ---------------------------------------------------------------------------


def compare_strategies(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    imputations: int = DEFAULT_IMPUTATIONS,
    seed: int | None = DEFAULT_SEED,
) -> dict[str, Any]:
    """Every fill strategy on the same data, side by side.

    The point is to make the size of the choice visible. On a history with a
    fifth of the flight entries missing, the spread between zero fill and a
    pooled estimate is routinely larger than the year-on-year change the user
    is being congratulated for — and the choice between them is currently made
    implicitly, by whichever module touches the data first.
    """
    cleaned = _validate_fields(fields)
    results: list[dict[str, Any]] = []

    def add(key: str, filled: Sequence[Mapping[str, float]]) -> float:
        estimate, variance = _estimand(filled, cleaned)
        results.append(
            {
                "strategy": key,
                "label": STRATEGIES[key]["label"],
                "note": STRATEGIES[key]["note"],
                "bias": STRATEGIES[key]["bias"],
                "estimate": estimate,
                "standard_error": math.sqrt(variance),
                "lower": estimate - 1.96 * math.sqrt(variance),
                "upper": estimate + 1.96 * math.sqrt(variance),
                "fraction_missing_information": None,
            }
        )
        return estimate

    add("zero", impute_constant(rows, cleaned, 0.0))
    add("mean", impute_centre(rows, cleaned, "mean"))
    add("median", impute_centre(rows, cleaned, "median"))
    add("locf", impute_locf(rows, cleaned))
    add("regression", impute_regression(rows, cleaned, noise=False))

    pooled = multiple_imputation(rows, cleaned, imputations, seed)
    results.append(
        {
            "strategy": "multiple",
            "label": STRATEGIES["multiple"]["label"],
            "note": STRATEGIES["multiple"]["note"],
            "bias": STRATEGIES["multiple"]["bias"],
            "estimate": pooled["estimate"],
            "standard_error": pooled["standard_error"],
            "lower": pooled["lower"],
            "upper": pooled["upper"],
            "fraction_missing_information": pooled["fraction_missing_information"],
        }
    )

    complete_case = [
        row for row in rows
        if all(row.get(field["name"]) is not None for field in cleaned)
    ]
    complete_case_estimate = None
    if len(complete_case) >= MIN_COMPLETE_CASES:
        complete_case_estimate, _ = _estimand(complete_case, cleaned)

    values = [entry["estimate"] for entry in results]
    spread = max(values) - min(values)
    reference = pooled["estimate"]

    for entry in results:
        entry["difference_from_pooled"] = entry["estimate"] - reference
        entry["percent_from_pooled"] = (
            (entry["estimate"] - reference) / reference * 100.0 if reference else 0.0
        )

    return {
        "results": results,
        "pooled": pooled,
        "spread": spread,
        "spread_percent": (spread / reference * 100.0) if reference else 0.0,
        "complete_case_estimate": complete_case_estimate,
        "complete_case_records": len(complete_case),
        "zero_fill_bias": results[0]["estimate"] - reference,
        "headline": (
            "Zero fill puts the estimate %.0f kg (%.1f%%) below the pooled one. "
            "The choice of fill strategy moves the answer by %.0f kg in total."
            % (
                abs(results[0]["estimate"] - reference),
                abs(results[0]["percent_from_pooled"]),
                spread,
            )
        ),
    }


# ---------------------------------------------------------------------------
# MNAR sensitivity
# ---------------------------------------------------------------------------


def delta_sensitivity(
    rows: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    deltas: Sequence[float] = (0.0, 0.1, 0.25, 0.5, 1.0),
    imputations: int = DEFAULT_IMPUTATIONS,
    seed: int | None = DEFAULT_SEED,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Shift the imputed values and see how far it takes to change the answer.

    MNAR is not testable. The honest substitute is to state the assumption
    explicitly — "suppose skipped months were 30% higher than imputed" — and
    report the tipping point at which the conclusion flips. A tipping point of
    5% means the conclusion is fragile; one of 200% means it is not, and that
    distinction is worth more than any single MNAR-blind number.
    """
    cleaned = _validate_fields(fields)
    base = multiple_imputation(rows, cleaned, imputations, seed)
    reference = threshold if threshold is not None else base["estimate"]

    curve = []
    for delta in deltas:
        shifted_estimates = []
        shifted_variances = []
        for index, dataset in enumerate(base["datasets"]):
            adjusted = []
            for position, filled_row in enumerate(dataset):
                row: dict[str, float] = {}
                for field in cleaned:
                    name = field["name"]
                    value = float(filled_row[name])
                    if rows[position].get(name) is None:
                        value *= (1.0 + float(delta))
                        if field["floor"] is not None:
                            value = max(value, field["floor"])
                    row[name] = value
                adjusted.append(row)
            estimate, variance = _estimand(adjusted, cleaned)
            shifted_estimates.append(estimate)
            shifted_variances.append(variance)

        pooled = pool(shifted_estimates, shifted_variances)
        curve.append(
            {
                "delta": float(delta),
                "estimate": pooled["estimate"],
                "lower": pooled["lower"],
                "upper": pooled["upper"],
                "shift_from_base": pooled["estimate"] - base["estimate"],
                "crosses_threshold": pooled["estimate"] > reference,
            }
        )

    tipping = None
    for entry in curve:
        if entry["crosses_threshold"] and entry["delta"] > 0:
            tipping = entry["delta"]
            break

    return {
        "base_estimate": base["estimate"],
        "threshold": reference,
        "curve": curve,
        "tipping_delta": tipping,
        "headline": (
            "The conclusion flips once imputed values are assumed %.0f%% higher "
            "than modelled." % (tipping * 100.0)
            if tipping is not None
            else "No tested departure from the imputation model changes the "
            "conclusion, over deltas up to %.0f%%." % (max(deltas) * 100.0)
        ),
    }


# ---------------------------------------------------------------------------
# Imputation-aware comparison
# ---------------------------------------------------------------------------


def compare_periods(
    earlier: Sequence[Mapping[str, float | None]],
    later: Sequence[Mapping[str, float | None]],
    fields: Sequence[dict[str, Any]],
    imputations: int = DEFAULT_IMPUTATIONS,
    seed: int | None = DEFAULT_SEED,
    confidence: float = 0.95,
) -> dict[str, Any]:
    """Year-on-year change with pooled variance on both sides.

    A change entirely inside the imputation uncertainty is reported as not
    distinguishable, rather than as progress. This is the whole point of
    carrying the between-imputation variance forward: a 5% reduction computed
    from a period with a fifth of its values invented is not a 5% reduction.
    """
    cleaned = _validate_fields(fields)
    first = multiple_imputation(earlier, cleaned, imputations, seed, confidence)
    second = multiple_imputation(later, cleaned, imputations, (seed or 0) + 13, confidence)

    difference = second["estimate"] - first["estimate"]
    variance = first["total_variance"] + second["total_variance"]
    standard_error = math.sqrt(variance) if variance > 0 else 0.0
    degrees = min(first["degrees_of_freedom"], second["degrees_of_freedom"])

    tail = (1.0 - confidence) / 2.0
    critical = t_ppf(1.0 - tail, max(degrees, 1.0)) if standard_error > 0 else 0.0
    lower = difference - critical * standard_error
    upper = difference + critical * standard_error
    # A zero standard error collapses the interval onto the point estimate,
    # which is still a perfectly good answer: a non-zero difference with no
    # estimated uncertainty is distinguishable, and a zero difference is not.
    distinguishable = lower > 0 or upper < 0

    percent = (difference / first["estimate"] * 100.0) if first["estimate"] else 0.0

    return {
        "earlier": first,
        "later": second,
        "difference": difference,
        "percent_change": percent,
        "standard_error": standard_error,
        "degrees_of_freedom": degrees,
        "lower": lower,
        "upper": upper,
        "distinguishable": distinguishable,
        "direction": "down" if difference < 0 else ("up" if difference > 0 else "flat"),
        "headline": (
            "%s of %.0f kg (%.1f%%), interval %.0f to %.0f kg."
            % (
                "Reduction" if difference < 0 else "Increase",
                abs(difference),
                abs(percent),
                lower,
                upper,
            )
            if distinguishable
            else "Change of %.0f kg (%.1f%%) is inside the interval %.0f to "
            "%.0f kg — not distinguishable from no change once the imputation "
            "uncertainty is carried through."
            % (difference, percent, lower, upper)
        ),
    }


def get_imputation_notes(comparison: Mapping[str, Any]) -> list[str]:
    """Plain-language readings of a strategy comparison."""
    notes: list[str] = []
    pooled = comparison["pooled"]
    notes.append(comparison["headline"])
    notes.append(
        "%s %s"
        % (
            pooled["information_verdict"]["headline"],
            pooled["information_verdict"]["detail"],
        )
    )

    zero = next(
        (entry for entry in comparison["results"] if entry["strategy"] == "zero"), None
    )
    if zero and zero["difference_from_pooled"] < 0:
        notes.append(
            "Zero fill is biased downward by construction: every gap is read as "
            "'none of this activity happened', so an incomplete assessment always "
            "looks better than a complete one."
        )

    mean_entry = next(
        (entry for entry in comparison["results"] if entry["strategy"] == "mean"), None
    )
    if mean_entry and mean_entry["standard_error"] < pooled["standard_error"]:
        notes.append(
            "Mean fill reports a standard error of %.0f against the pooled %.0f. "
            "It is not more precise; it has discarded the uncertainty rather "
            "than accounted for it."
            % (mean_entry["standard_error"], pooled["standard_error"])
        )

    if comparison["complete_case_estimate"] is not None:
        notes.append(
            "Complete-case analysis over %d rows gives %.0f kg. That is only "
            "unbiased under MCAR, and it describes a different population from "
            "the one that was asked about."
            % (comparison["complete_case_records"], comparison["complete_case_estimate"])
        )
    return notes


def summarise(comparison: Mapping[str, Any]) -> str:
    """One line for a log or a saved-analysis list."""
    pooled = comparison["pooled"]
    return "pooled %.0f kg (SE %.0f, FMI %.0f%%) | zero fill %+.0f kg | spread %.0f kg" % (
        pooled["estimate"],
        pooled["standard_error"],
        pooled["fraction_missing_information"] * 100.0,
        comparison["zero_fill_bias"],
        comparison["spread"],
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS imputation_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            label TEXT NOT NULL,
            pooled_estimate REAL NOT NULL,
            zero_fill_bias REAL NOT NULL,
            fraction_missing_information REAL NOT NULL,
            records INTEGER NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_imputation_analyses_user
        ON imputation_analyses (user_id)
        """
    )


def _storable(comparison: Mapping[str, Any]) -> dict[str, Any]:
    pooled = comparison["pooled"]
    return {
        "engine_version": ENGINE_VERSION,
        "results": [
            {key: value for key, value in entry.items()}
            for entry in comparison["results"]
        ],
        "spread": comparison["spread"],
        "zero_fill_bias": comparison["zero_fill_bias"],
        "complete_case_estimate": comparison["complete_case_estimate"],
        "complete_case_records": comparison["complete_case_records"],
        "headline": comparison["headline"],
        "pooled": {
            "estimate": pooled["estimate"],
            "standard_error": pooled["standard_error"],
            "lower": pooled["lower"],
            "upper": pooled["upper"],
            "degrees_of_freedom": pooled["degrees_of_freedom"],
            "fraction_missing_information": pooled["fraction_missing_information"],
            "imputations": pooled["imputations"],
            "information_verdict": pooled["information_verdict"],
            "missingness": {
                key: value
                for key, value in pooled["missingness"].items()
                if key != "co_occurrence"
            },
        },
    }


def save_analysis(user_id: Any, comparison: Mapping[str, Any], label: str = "") -> int | None:
    """Persist a strategy comparison. None if storage is unavailable."""
    if not user_id or not comparison.get("results"):
        return None
    pooled = comparison["pooled"]
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                """
                INSERT INTO imputation_analyses
                    (user_id, label, pooled_estimate, zero_fill_bias,
                     fraction_missing_information, records, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(user_id),
                    str(label or "analysis"),
                    float(pooled["estimate"]),
                    float(comparison["zero_fill_bias"]),
                    float(pooled["fraction_missing_information"]),
                    int(pooled["missingness"]["records"]),
                    json.dumps(_storable(comparison)),
                ),
            )
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def get_analyses(user_id: Any, limit: int = 25) -> list[dict[str, Any]]:
    """Most recent saved analyses for one user."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, label, pooled_estimate, zero_fill_bias,
                       fraction_missing_information, records, payload, created_at
                FROM imputation_analyses
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        return []

    analyses = []
    for row in rows:
        try:
            payload = json.loads(row[6])
        except (TypeError, ValueError):
            payload = {}
        analyses.append(
            {
                "id": row[0],
                "label": row[1],
                "pooled_estimate": row[2],
                "zero_fill_bias": row[3],
                "fraction_missing_information": row[4],
                "records": row[5],
                "payload": payload,
                "created_at": row[7],
            }
        )
    return analyses


def delete_analysis(user_id: Any, analysis_id: int) -> bool:
    """Remove one saved analysis belonging to this user."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM imputation_analyses WHERE user_id = ? AND id = ?",
                (str(user_id), int(analysis_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------


def default_fields() -> list[dict[str, Any]]:
    """The four fields the app's own assessment collects."""
    return [
        build_field("transport_km", 0.171, "km", label="Car travel"),
        build_field("electricity_kwh", 0.233, "kWh", label="Electricity"),
        build_field("diet_kg", 2.5, "kg", label="Diet"),
        build_field("flight_hours", 90.0, "hours", label="Flights"),
    ]


def sample_history(
    months: int = 24,
    missing_rate: float = 0.2,
    mnar: bool = True,
    seed: int | None = DEFAULT_SEED,
) -> list[dict[str, float | None]]:
    """A synthetic assessment history with a controllable missingness mechanism.

    With `mnar=True` the flight field goes missing preferentially in the months
    with the most flying — the exact case that no imputation can recover and
    that zero fill turns into a reported improvement.
    """
    rng = random.Random(seed)
    rows: list[dict[str, float | None]] = []
    for month in range(int(months)):
        seasonal = 1.0 + 0.25 * math.sin(2.0 * math.pi * month / 12.0)
        flights = max(0.0, rng.gauss(4.0, 3.0)) * seasonal
        row: dict[str, float | None] = {
            "transport_km": max(0.0, rng.gauss(900.0, 200.0) * seasonal),
            "electricity_kwh": max(0.0, rng.gauss(280.0, 60.0) / seasonal),
            "diet_kg": max(0.0, rng.gauss(62.0, 8.0)),
            "flight_hours": flights,
        }
        if mnar:
            probability = min(0.85, missing_rate * (1.0 + flights / 4.0))
        else:
            probability = missing_rate
        if rng.random() < probability:
            row["flight_hours"] = None
        if rng.random() < missing_rate / 2.0:
            row["electricity_kwh"] = None
        rows.append(row)
    return rows
