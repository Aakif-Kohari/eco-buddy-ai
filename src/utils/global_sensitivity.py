"""Variance-based global sensitivity analysis for arbitrary footprint models.

`src.utils.footprint_uncertainty.sensitivity_ranking` already answers "which
component causes the spread" and answers it correctly, for the model it owns:
a sum of independent ``amount x factor`` terms. Pin one component to its point
estimate, re-run the same draws, and the drop in variance belongs to that
component. On an additive model with independent terms the shares sum to one
because there is nowhere else for them to go.

That is not the model the rest of this app runs on, and it fails in two ways
that are not edge cases here.

**Parameters are shared.** Grid intensity appears in the electricity term, in
EV charging, in a heat pump, and in the datacenter engine. Pinning "home
electricity" leaves grid intensity varying inside three other components, so
it is charged with a fraction of the variance it actually causes. The unit of
attribution is the component, and the thing the user can go and measure is the
parameter.

**The models are not additive.** `src.carbon.replacement_timing` runs a
backward induction. `src.utils.goal_pathway` compounds. `src.carbon.dynamic_lca`
discounts a series. `src.utils.rebound_effect` multiplies an elasticity through
a saving. None of them have a component column to pin.

This module works on parameters instead, and on any callable::

    total(grid_intensity, kwh, efficiency, ...) -> kg CO2e

The method
----------
Sobol variance decomposition. For a model ``Y = f(X_1..X_k)`` with independent
inputs, the variance of Y splits into contributions from each input alone, each
pair, each triple, and so on::

    V(Y) = sum_i V_i + sum_{i<j} V_ij + ... + V_12..k

Two indices come out of that::

    S_i  = V_i / V(Y)                 first order: X_i acting alone
    S_Ti = 1 - V_{~i} / V(Y)          total effect: X_i and every interaction
                                      it takes part in

`S_i` sums to 1 if and only if the model is additive. `S_Ti` sums to at least
1, and the excess is interaction. The gap ``S_Ti - S_i`` is how much of X_i's
influence only exists in combination with something else — which is precisely
the quantity a one-at-a-time analysis reports as zero.

Estimation is by the Saltelli cross-sampling scheme: two independent sample
matrices A and B, plus one matrix AB_i per parameter in which column i is taken
from B and everything else from A. That is ``N(k+2)`` model evaluations for all
`2k` indices. The estimators used here are Saltelli 2010 for first order and
Jansen for total effect, which are the pair that stay stable when an index is
genuinely near zero — the naive estimators do not, and they produce the
confident-looking negative numbers that make people distrust the method.

What this module refuses to do
------------------------------
Rank two parameters whose bootstrap intervals overlap. Return indices from a
sample that has not converged. Decompose the variance of a model that has none.
Quietly drop model evaluations that came back non-finite. All four are reported
rather than smoothed over, because a sensitivity table is believed far more
readily than it is checked.

Assumes independent inputs, as Sobol analysis does. Correlated inputs need a
different decomposition and this module says so rather than pretending.
"""

from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import statistics
from typing import Any, Callable, Iterable, Sequence

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

ENGINE_VERSION = "1.0.0"

# Sampling ------------------------------------------------------------------
DEFAULT_BASE_SAMPLES = 512
MIN_BASE_SAMPLES = 16
MAX_BASE_SAMPLES = 8192
DEFAULT_SEED = 20240817
MAX_PARAMETERS = 24

# Bootstrap -----------------------------------------------------------------
DEFAULT_BOOTSTRAP = 200
MIN_BOOTSTRAP = 20
MAX_BOOTSTRAP = 2000
CI_LOWER_PCT = 5.0
CI_UPPER_PCT = 95.0

# Verdict thresholds --------------------------------------------------------
NEGLIGIBLE_INDEX = 0.01
SUM_TOLERANCE = 0.15
ADDITIVE_INTERACTION_CEILING = 0.05
STRONG_INTERACTION_FLOOR = 0.20
CONVERGENCE_DRIFT_CEILING = 0.05
FAILURE_RATE_CEILING = 0.02
ZERO_VARIANCE_FLOOR = 1e-12

# Morris screening ----------------------------------------------------------
DEFAULT_TRAJECTORIES = 20
MIN_TRAJECTORIES = 4
MAX_TRAJECTORIES = 200
DEFAULT_LEVELS = 8

# Ishigami validation constants -------------------------------------------
ISHIGAMI_A = 7.0
ISHIGAMI_B = 0.1

DISTRIBUTIONS: dict[str, dict[str, Any]] = {
    "uniform": {
        "label": "Uniform",
        "needs": ("low", "high"),
        "note": "Flat between two bounds. The right default when all you know is a range.",
    },
    "triangular": {
        "label": "Triangular",
        "needs": ("low", "high", "mode"),
        "note": "A range plus a best guess. Cheap way to express 'probably around here'.",
    },
    "normal": {
        "label": "Normal",
        "needs": ("mean", "sigma"),
        "note": "Symmetric additive error. Truncated at zero for quantities that cannot be negative.",
    },
    "lognormal": {
        "label": "Lognormal",
        "needs": ("median", "gsd"),
        "note": "Multiplicative error, strictly positive. Matches how emission factors are quoted.",
    },
}


class SensitivityError(ValueError):
    """Raised when a study is not analysable as specified."""


# ---------------------------------------------------------------------------
# Numerical helpers
# ---------------------------------------------------------------------------


def _finite(value: Any) -> float | None:
    """Coerce to float, returning None for anything not finite."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def norm_ppf(probability: float) -> float:
    """Inverse standard normal CDF (Acklam's rational approximation).

    Accurate to about 1.15e-9 across the open unit interval, which is several
    orders of magnitude better than the sampling error of any study this module
    will ever run. Written out rather than imported because the repo carries no
    scientific stack and this is the only piece of it needed.
    """
    if not 0.0 < probability < 1.0:
        raise SensitivityError("Probability for norm_ppf must lie strictly in (0, 1).")

    a = (
        -3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
        1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
        6.680131188771972e01, -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
        -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
        3.754408661907416e00,
    )

    low, high = 0.02425, 1.0 - 0.02425

    if probability < low:
        q = math.sqrt(-2.0 * math.log(probability))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if probability > high:
        q = math.sqrt(-2.0 * math.log(1.0 - probability))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )

    q = probability - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    )


def percentile(sorted_values: Sequence[float], pct: float) -> float:
    """Linear-interpolated percentile of an already sorted sequence."""
    if not sorted_values:
        raise SensitivityError("Cannot take a percentile of an empty sample.")
    if len(sorted_values) == 1:
        return float(sorted_values[0])
    rank = (pct / 100.0) * (len(sorted_values) - 1)
    lower_index = int(math.floor(rank))
    upper_index = int(math.ceil(rank))
    if lower_index == upper_index:
        return float(sorted_values[lower_index])
    weight = rank - lower_index
    return float(
        sorted_values[lower_index] * (1.0 - weight)
        + sorted_values[upper_index] * weight
    )


def _variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    return float(statistics.pvariance(values))


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


def list_distributions() -> list[dict[str, Any]]:
    """The supported input distributions, for a UI to render."""
    return [
        {
            "key": key,
            "label": spec["label"],
            "needs": list(spec["needs"]),
            "note": spec["note"],
        }
        for key, spec in DISTRIBUTIONS.items()
    ]


def build_parameter(
    name: str,
    distribution: str = "uniform",
    low: float | None = None,
    high: float | None = None,
    mode: float | None = None,
    mean: float | None = None,
    sigma: float | None = None,
    median: float | None = None,
    gsd: float | None = None,
    unit: str = "",
    note: str = "",
) -> dict[str, Any]:
    """Validate and normalise one uncertain input.

    A parameter with no spread is not a sensitivity question — it has no
    variance to contribute — so a degenerate range is refused here rather than
    silently producing an index of exactly zero that looks like a finding.
    """
    label = str(name or "").strip()
    if not label:
        raise SensitivityError("Every parameter needs a name.")

    kind = str(distribution or "").strip().lower()
    if kind not in DISTRIBUTIONS:
        raise SensitivityError(
            "Unknown distribution '%s'. Supported: %s"
            % (distribution, ", ".join(sorted(DISTRIBUTIONS)))
        )

    spec: dict[str, Any] = {
        "name": label,
        "distribution": kind,
        "unit": str(unit or ""),
        "note": str(note or ""),
    }

    if kind in ("uniform", "triangular"):
        lo, hi = _finite(low), _finite(high)
        if lo is None or hi is None:
            raise SensitivityError("'%s' needs finite low and high bounds." % label)
        if hi <= lo:
            raise SensitivityError(
                "'%s' has high (%g) not above low (%g); a parameter with no "
                "spread cannot contribute variance." % (label, hi, lo)
            )
        spec["low"], spec["high"] = lo, hi
        if kind == "triangular":
            peak = _finite(mode)
            if peak is None:
                peak = (lo + hi) / 2.0
            if not lo <= peak <= hi:
                raise SensitivityError(
                    "'%s' has a mode outside its bounds." % label
                )
            spec["mode"] = peak

    elif kind == "normal":
        centre, spread = _finite(mean), _finite(sigma)
        if centre is None or spread is None:
            raise SensitivityError("'%s' needs a finite mean and sigma." % label)
        if spread <= 0:
            raise SensitivityError("'%s' needs a positive sigma." % label)
        spec["mean"], spec["sigma"] = centre, spread

    else:  # lognormal
        centre, spread = _finite(median), _finite(gsd)
        if centre is None or spread is None:
            raise SensitivityError("'%s' needs a finite median and GSD." % label)
        if centre <= 0:
            raise SensitivityError("'%s' needs a positive median." % label)
        if spread <= 1.0:
            raise SensitivityError(
                "'%s' needs a GSD above 1.0; a GSD of 1 is a constant." % label
            )
        spec["median"], spec["gsd"] = centre, spread

    return spec


def parameter_bounds(parameter: dict[str, Any], coverage: float = 0.99) -> tuple[float, float]:
    """Central interval of a parameter, for display and for Morris screening."""
    tail = (1.0 - coverage) / 2.0
    return (
        transform(parameter, tail),
        transform(parameter, 1.0 - tail),
    )


def transform(parameter: dict[str, Any], unit_draw: float) -> float:
    """Map a draw from [0, 1) onto the parameter's own scale.

    Inverse-CDF sampling throughout, which is what keeps the Saltelli
    cross-sampling valid: swapping column i between two matrices has to mean
    swapping that parameter and nothing else, and that only holds if each
    column is transformed independently of the others.
    """
    u = min(max(float(unit_draw), 1e-12), 1.0 - 1e-12)
    kind = parameter["distribution"]

    if kind == "uniform":
        return parameter["low"] + u * (parameter["high"] - parameter["low"])

    if kind == "triangular":
        lo, hi, mode = parameter["low"], parameter["high"], parameter["mode"]
        span = hi - lo
        split = (mode - lo) / span if span > 0 else 0.5
        if u < split:
            return lo + math.sqrt(u * span * (mode - lo))
        return hi - math.sqrt((1.0 - u) * span * (hi - mode))

    if kind == "normal":
        value = parameter["mean"] + parameter["sigma"] * norm_ppf(u)
        return value

    # lognormal, parameterised by median and geometric standard deviation
    sigma_log = math.log(parameter["gsd"])
    return parameter["median"] * math.exp(sigma_log * norm_ppf(u))


def _validate_parameters(parameters: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    if not parameters:
        raise SensitivityError("A sensitivity study needs at least one parameter.")
    if len(parameters) > MAX_PARAMETERS:
        raise SensitivityError(
            "%d parameters exceeds the %d supported; screen with Morris first."
            % (len(parameters), MAX_PARAMETERS)
        )
    seen: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for entry in parameters:
        if not isinstance(entry, dict) or "distribution" not in entry:
            raise SensitivityError(
                "Parameters must be built with build_parameter()."
            )
        name = entry["name"]
        if name in seen:
            raise SensitivityError(
                "Parameter '%s' appears twice; Sobol indices are per distinct "
                "input and duplicates would double-count." % name
            )
        seen.add(name)
        cleaned.append(dict(entry))
    return cleaned


def _clean_base_samples(value: Any) -> int:
    number = _finite(value)
    if number is None:
        return DEFAULT_BASE_SAMPLES
    return int(min(max(int(number), MIN_BASE_SAMPLES), MAX_BASE_SAMPLES))


def _clean_bootstrap(value: Any) -> int:
    number = _finite(value)
    if number is None:
        return DEFAULT_BOOTSTRAP
    return int(min(max(int(number), MIN_BOOTSTRAP), MAX_BOOTSTRAP))


# ---------------------------------------------------------------------------
# Saltelli sampling
# ---------------------------------------------------------------------------


def saltelli_matrices(
    parameters: Sequence[dict[str, Any]],
    base_samples: int = DEFAULT_BASE_SAMPLES,
    seed: int | None = DEFAULT_SEED,
) -> dict[str, Any]:
    """Build the A, B and AB_i design matrices.

    Returns rows as dicts keyed by parameter name, because the model callable
    is user code and positional argument order is exactly the kind of thing
    that goes wrong silently.
    """
    cleaned = _validate_parameters(parameters)
    count = _clean_base_samples(base_samples)
    rng = random.Random(seed)
    k = len(cleaned)

    unit_a = [[rng.random() for _ in range(k)] for _ in range(count)]
    unit_b = [[rng.random() for _ in range(k)] for _ in range(count)]

    def rows(unit_matrix: list[list[float]]) -> list[dict[str, float]]:
        return [
            {
                cleaned[column]["name"]: transform(cleaned[column], draw[column])
                for column in range(k)
            }
            for draw in unit_matrix
        ]

    matrix_a = rows(unit_a)
    matrix_b = rows(unit_b)

    cross: list[list[dict[str, float]]] = []
    for column in range(k):
        swapped = []
        for index in range(count):
            draw = list(unit_a[index])
            draw[column] = unit_b[index][column]
            swapped.append(
                {
                    cleaned[position]["name"]: transform(cleaned[position], draw[position])
                    for position in range(k)
                }
            )
        cross.append(swapped)

    return {
        "parameters": cleaned,
        "base_samples": count,
        "seed": seed,
        "A": matrix_a,
        "B": matrix_b,
        "AB": cross,
        "evaluations": count * (k + 2),
    }


def evaluate_matrix(
    model: Callable[[dict[str, float]], float],
    rows: Sequence[dict[str, float]],
) -> tuple[list[float | None], int]:
    """Run the model over one design matrix, counting non-finite returns.

    A model that fails on part of its input space has a sensitivity answer that
    means very little, so failures are counted and surfaced rather than being
    dropped or replaced with zero.
    """
    if not callable(model):
        raise SensitivityError("The model must be callable.")
    outputs: list[float | None] = []
    failures = 0
    for row in rows:
        try:
            value = _finite(model(dict(row)))
        except Exception:  # noqa: BLE001 - user model, any failure is a failure
            value = None
        if value is None:
            failures += 1
        outputs.append(value)
    return outputs, failures


def _usable_indices(*columns: Sequence[float | None]) -> list[int]:
    """Rows where every column has a finite value.

    Sobol estimators pair f_A with f_B and f_AB_i by row, so a row that failed
    anywhere has to be dropped everywhere or the pairing breaks.
    """
    length = len(columns[0]) if columns else 0
    keep = []
    for index in range(length):
        if all(column[index] is not None for column in columns):
            keep.append(index)
    return keep


# ---------------------------------------------------------------------------
# Sobol estimators
# ---------------------------------------------------------------------------


def first_order_index(
    f_a: Sequence[float],
    f_b: Sequence[float],
    f_ab: Sequence[float],
    variance: float,
) -> float:
    """Saltelli 2010 first-order estimator.

    ``S_i = mean(f_B * (f_AB_i - f_A)) / V``

    Preferred over the naive covariance form because it is unbiased at small
    N and does not blow up when the true index is close to zero.
    """
    if variance <= ZERO_VARIANCE_FLOOR:
        return 0.0
    n = len(f_a)
    total = sum(f_b[i] * (f_ab[i] - f_a[i]) for i in range(n))
    return (total / n) / variance


def total_effect_index(
    f_a: Sequence[float],
    f_ab: Sequence[float],
    variance: float,
) -> float:
    """Jansen total-effect estimator.

    ``S_Ti = mean((f_A - f_AB_i)^2) / (2V)``

    Non-negative by construction, which matters: the alternative estimators
    produce small negative totals that users read as a bug rather than as
    estimator noise.
    """
    if variance <= ZERO_VARIANCE_FLOOR:
        return 0.0
    n = len(f_a)
    total = sum((f_a[i] - f_ab[i]) ** 2 for i in range(n))
    return (total / (2.0 * n)) / variance


def _indices_from_samples(
    f_a: Sequence[float],
    f_b: Sequence[float],
    f_ab_columns: Sequence[Sequence[float]],
    order: Sequence[int] | None = None,
) -> tuple[list[float], list[float], float]:
    """First-order and total indices for one (possibly resampled) row set."""
    if order is None:
        order = range(len(f_a))
    sub_a = [f_a[i] for i in order]
    sub_b = [f_b[i] for i in order]
    combined = sub_a + sub_b
    variance = _variance(combined)

    # Centre the outputs before estimating. The Saltelli first-order estimator
    # is unbiased either way, but the variance of the estimator itself scales
    # with E[f^2] rather than Var[f]. A footprint model with a mean of 5,000
    # and a standard deviation of 700 therefore converges roughly fifty times
    # slower uncentred than centred, purely because of where zero happens to
    # sit — and the symptom is first-order indices that sum to 0.8 on a model
    # that is provably additive. Subtracting the sample mean costs nothing and
    # removes that entirely. The total-effect estimator is a difference and is
    # unaffected, but it is centred too so both read from the same series.
    centre = statistics.fmean(combined) if combined else 0.0
    sub_a = [value - centre for value in sub_a]
    sub_b = [value - centre for value in sub_b]

    first: list[float] = []
    total: list[float] = []
    for column in f_ab_columns:
        sub_ab = [column[i] - centre for i in order]
        first.append(first_order_index(sub_a, sub_b, sub_ab, variance))
        total.append(total_effect_index(sub_a, sub_ab, variance))
    return first, total, variance


# ---------------------------------------------------------------------------
# The study
# ---------------------------------------------------------------------------


def analyse(
    model: Callable[[dict[str, float]], float],
    parameters: Sequence[dict[str, Any]],
    base_samples: int = DEFAULT_BASE_SAMPLES,
    seed: int | None = DEFAULT_SEED,
    bootstrap: int = DEFAULT_BOOTSTRAP,
    label: str = "",
) -> dict[str, Any]:
    """Full variance decomposition of ``model`` over ``parameters``.

    Returns first-order and total-effect indices with bootstrap intervals, the
    interaction structure, and the diagnostics needed to decide whether any of
    it should be believed.
    """
    design = saltelli_matrices(parameters, base_samples, seed)
    cleaned = design["parameters"]
    count = design["base_samples"]
    resamples = _clean_bootstrap(bootstrap)

    raw_a, fail_a = evaluate_matrix(model, design["A"])
    raw_b, fail_b = evaluate_matrix(model, design["B"])
    raw_ab: list[list[float | None]] = []
    fail_ab = 0
    for column in design["AB"]:
        values, failures = evaluate_matrix(model, column)
        raw_ab.append(values)
        fail_ab += failures

    keep = _usable_indices(raw_a, raw_b, *raw_ab)
    evaluations = count * (len(cleaned) + 2)
    failures = fail_a + fail_b + fail_ab
    failure_rate = failures / evaluations if evaluations else 0.0

    if len(keep) < MIN_BASE_SAMPLES:
        raise SensitivityError(
            "Only %d of %d base rows produced finite output on every design "
            "matrix; the model fails across too much of its input space for a "
            "variance decomposition to mean anything."
            % (len(keep), count)
        )

    f_a = [float(raw_a[i]) for i in keep]
    f_b = [float(raw_b[i]) for i in keep]
    f_ab = [[float(column[i]) for i in keep] for column in raw_ab]

    output = f_a + f_b
    variance = _variance(output)
    if variance <= ZERO_VARIANCE_FLOOR:
        raise SensitivityError(
            "The model output has no variance over the given parameter ranges. "
            "There is nothing to decompose — either the ranges are degenerate "
            "or the model ignores its inputs."
        )

    first, total, _ = _indices_from_samples(f_a, f_b, f_ab)
    intervals = bootstrap_intervals(f_a, f_b, f_ab, resamples, seed)

    rows: list[dict[str, Any]] = []
    for position, parameter in enumerate(cleaned):
        si = first[position]
        sti = total[position]
        low, high = parameter_bounds(parameter)
        rows.append(
            {
                "name": parameter["name"],
                "unit": parameter.get("unit", ""),
                "distribution": parameter["distribution"],
                "note": parameter.get("note", ""),
                "range_low": low,
                "range_high": high,
                "first_order": si,
                "total_effect": sti,
                "interaction": max(0.0, sti - si),
                "first_order_low": intervals["first_low"][position],
                "first_order_high": intervals["first_high"][position],
                "total_effect_low": intervals["total_low"][position],
                "total_effect_high": intervals["total_high"][position],
                "is_negligible": sti < NEGLIGIBLE_INDEX,
                "interaction_dominated": si < sti / 2.0 and sti >= NEGLIGIBLE_INDEX,
            }
        )

    rows.sort(key=lambda row: row["total_effect"], reverse=True)

    sum_first = sum(row["first_order"] for row in rows)
    sum_total = sum(row["total_effect"] for row in rows)
    interaction_share = max(0.0, 1.0 - sum_first)

    result: dict[str, Any] = {
        "engine_version": ENGINE_VERSION,
        "label": str(label or ""),
        "parameters": cleaned,
        "rows": rows,
        "base_samples": count,
        "usable_samples": len(keep),
        "evaluations": evaluations,
        "failures": failures,
        "failure_rate": failure_rate,
        "seed": seed,
        "bootstrap": resamples,
        "output_mean": statistics.fmean(output),
        "output_variance": variance,
        "output_stdev": math.sqrt(variance),
        "output_p5": percentile(sorted(output), 5.0),
        "output_p95": percentile(sorted(output), 95.0),
        "sum_first_order": sum_first,
        "sum_total_effect": sum_total,
        "interaction_share": interaction_share,
        "additivity": additivity_verdict(sum_first, interaction_share),
    }
    result["diagnostics"] = diagnose(result)
    result["ranking"] = rank_with_confidence(rows)
    return result


def bootstrap_intervals(
    f_a: Sequence[float],
    f_b: Sequence[float],
    f_ab: Sequence[Sequence[float]],
    resamples: int = DEFAULT_BOOTSTRAP,
    seed: int | None = DEFAULT_SEED,
) -> dict[str, list[float]]:
    """Percentile bootstrap intervals for every index.

    Resampling rows, not re-running the model — the model evaluations are
    already paid for and reusing them is what makes intervals affordable. An
    index without an interval is a point estimate being read as a fact, and
    the ordering of two parameters whose intervals overlap is not an ordering.
    """
    n = len(f_a)
    k = len(f_ab)
    rng = random.Random((seed or 0) + 7919)

    first_draws: list[list[float]] = [[] for _ in range(k)]
    total_draws: list[list[float]] = [[] for _ in range(k)]

    for _ in range(resamples):
        order = [rng.randrange(n) for _ in range(n)]
        first, total, variance = _indices_from_samples(f_a, f_b, f_ab, order)
        if variance <= ZERO_VARIANCE_FLOOR:
            continue
        for column in range(k):
            first_draws[column].append(first[column])
            total_draws[column].append(total[column])

    def bounds(draws: list[list[float]]) -> tuple[list[float], list[float]]:
        lows, highs = [], []
        for column in draws:
            if not column:
                lows.append(0.0)
                highs.append(0.0)
                continue
            ordered = sorted(column)
            lows.append(percentile(ordered, CI_LOWER_PCT))
            highs.append(percentile(ordered, CI_UPPER_PCT))
        return lows, highs

    first_low, first_high = bounds(first_draws)
    total_low, total_high = bounds(total_draws)
    return {
        "first_low": first_low,
        "first_high": first_high,
        "total_low": total_low,
        "total_high": total_high,
    }


def additivity_verdict(sum_first: float, interaction_share: float) -> dict[str, Any]:
    """Say plainly whether the model is additive, and what follows if it is.

    This is the finding that licences every other tool in the app. If the model
    is additive then component-level pinning is valid and
    `footprint_uncertainty.sensitivity_ranking` is the cheaper right answer. If
    it is not, single-driver explanations are misleading and this is the number
    that says by how much.
    """
    if interaction_share <= ADDITIVE_INTERACTION_CEILING:
        return {
            "verdict": "additive",
            "interaction_share": interaction_share,
            "headline": "Effectively additive (%.0f%% interaction)."
            % (interaction_share * 100.0),
            "detail": (
                "First-order indices account for almost all the variance. "
                "One-at-a-time sensitivity and component pinning give the same "
                "answer here, so the simpler tools are safe on this model."
            ),
        }
    if interaction_share >= STRONG_INTERACTION_FLOOR:
        return {
            "verdict": "strongly_interacting",
            "interaction_share": interaction_share,
            "headline": "Strongly interacting (%.0f%% of variance is joint)."
            % (interaction_share * 100.0),
            "detail": (
                "A large share of the spread exists only in combination. A "
                "one-at-a-time analysis would report that share as zero and "
                "rank the inputs wrongly. Read total-effect indices, not "
                "first-order ones."
            ),
        }
    return {
        "verdict": "mildly_interacting",
        "interaction_share": interaction_share,
        "headline": "Mildly interacting (%.0f%% of variance is joint)."
        % (interaction_share * 100.0),
        "detail": (
            "Interactions are present but not dominant. First-order indices "
            "are indicative; total-effect indices remain the ones to act on."
        ),
    }


def rank_with_confidence(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group parameters into rank bands, merging any whose intervals overlap.

    Two parameters whose total-effect intervals overlap have not been
    separated by this study, and printing them as 2nd and 3rd invents a
    distinction the sample cannot support.
    """
    ordered = sorted(rows, key=lambda row: row["total_effect"], reverse=True)
    bands: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    for row in ordered:
        if not current:
            current = [row]
            continue
        band_low = min(item["total_effect_low"] for item in current)
        if row["total_effect_high"] >= band_low:
            current.append(row)
        else:
            bands.append(_band(current, len(bands) + 1))
            current = [row]
    if current:
        bands.append(_band(current, len(bands) + 1))
    return bands


def _band(members: Sequence[dict[str, Any]], position: int) -> dict[str, Any]:
    return {
        "band": position,
        "names": [item["name"] for item in members],
        "total_effect_high": max(item["total_effect"] for item in members),
        "total_effect_low": min(item["total_effect"] for item in members),
        "separated": len(members) == 1,
    }


def diagnose(result: dict[str, Any]) -> list[dict[str, str]]:
    """Reasons to distrust the table above it.

    Every one of these is a condition under which the indices are still
    printable and no longer meaningful, which is the dangerous combination.
    """
    problems: list[dict[str, str]] = []

    sum_first = result["sum_first_order"]
    if sum_first > 1.0 + SUM_TOLERANCE:
        problems.append(
            {
                "severity": "error",
                "code": "first_order_sum_exceeds_one",
                "message": (
                    "First-order indices sum to %.2f. They cannot exceed 1 for "
                    "independent inputs, so this is estimator noise from too "
                    "small a sample. Increase base samples." % sum_first
                ),
            }
        )
    if sum_first < -SUM_TOLERANCE:
        problems.append(
            {
                "severity": "error",
                "code": "first_order_sum_negative",
                "message": (
                    "First-order indices sum to %.2f. A materially negative sum "
                    "means the sample is too small for the estimator."
                    % sum_first
                ),
            }
        )
    if result["sum_total_effect"] < sum_first - SUM_TOLERANCE:
        problems.append(
            {
                "severity": "warning",
                "code": "total_below_first",
                "message": (
                    "Total-effect indices sum below the first-order ones, which "
                    "is impossible in the limit and indicates sampling noise."
                ),
            }
        )
    if result["failure_rate"] > FAILURE_RATE_CEILING:
        problems.append(
            {
                "severity": "warning",
                "code": "model_failures",
                "message": (
                    "%.1f%% of model evaluations returned a non-finite value. "
                    "Those rows were dropped, so the indices describe the part "
                    "of the input space where the model works."
                    % (result["failure_rate"] * 100.0)
                ),
            }
        )
    for row in result["rows"]:
        if row["first_order_low"] < -SUM_TOLERANCE:
            problems.append(
                {
                    "severity": "warning",
                    "code": "negative_index",
                    "message": (
                        "'%s' has a first-order interval reaching %.2f. "
                        "Negative variance shares are estimator noise around "
                        "zero, not a finding." % (row["name"], row["first_order_low"])
                    ),
                }
            )
    if result["base_samples"] < 128:
        problems.append(
            {
                "severity": "info",
                "code": "small_sample",
                "message": (
                    "Only %d base samples. Indices are indicative; anything "
                    "load-bearing wants several hundred."
                    % result["base_samples"]
                ),
            }
        )
    return problems


def convergence(
    model: Callable[[dict[str, float]], float],
    parameters: Sequence[dict[str, Any]],
    base_samples: int = DEFAULT_BASE_SAMPLES,
    seed: int | None = DEFAULT_SEED,
    stages: int = 3,
) -> dict[str, Any]:
    """Recompute the indices on nested prefixes of the same sample.

    A Sobol index is an estimate. Watching it settle across N/4, N/2 and N is
    the cheapest available evidence that it has settled at all, and drift at
    the last step is the honest reason to distrust a table that otherwise
    looks finished.
    """
    design = saltelli_matrices(parameters, base_samples, seed)
    cleaned = design["parameters"]
    count = design["base_samples"]

    raw_a, _ = evaluate_matrix(model, design["A"])
    raw_b, _ = evaluate_matrix(model, design["B"])
    raw_ab = [evaluate_matrix(model, column)[0] for column in design["AB"]]

    keep = _usable_indices(raw_a, raw_b, *raw_ab)
    if len(keep) < MIN_BASE_SAMPLES:
        raise SensitivityError("Too few usable rows to test convergence.")

    f_a = [float(raw_a[i]) for i in keep]
    f_b = [float(raw_b[i]) for i in keep]
    f_ab = [[float(column[i]) for i in keep] for column in raw_ab]

    steps = max(2, min(int(stages), 6))
    usable = len(f_a)
    checkpoints = [max(MIN_BASE_SAMPLES, int(usable * (step + 1) / steps)) for step in range(steps)]

    history: list[dict[str, Any]] = []
    for size in checkpoints:
        order = list(range(size))
        first, total, variance = _indices_from_samples(f_a, f_b, f_ab, order)
        if variance <= ZERO_VARIANCE_FLOOR:
            continue
        history.append(
            {
                "samples": size,
                "first_order": {cleaned[i]["name"]: first[i] for i in range(len(cleaned))},
                "total_effect": {cleaned[i]["name"]: total[i] for i in range(len(cleaned))},
            }
        )

    drift = 0.0
    if len(history) >= 2:
        last, previous = history[-1], history[-2]
        drift = max(
            abs(last["total_effect"][name] - previous["total_effect"][name])
            for name in last["total_effect"]
        )

    return {
        "base_samples": count,
        "usable_samples": usable,
        "history": history,
        "max_drift": drift,
        "converged": drift <= CONVERGENCE_DRIFT_CEILING,
        "threshold": CONVERGENCE_DRIFT_CEILING,
        "verdict": (
            "Total-effect indices moved at most %.3f over the last doubling."
            % drift
            if drift <= CONVERGENCE_DRIFT_CEILING
            else "Total-effect indices are still moving by %.3f. Increase base "
            "samples before reading the ranking." % drift
        ),
    }


# ---------------------------------------------------------------------------
# Morris screening
# ---------------------------------------------------------------------------


def morris_screening(
    model: Callable[[dict[str, float]], float],
    parameters: Sequence[dict[str, Any]],
    trajectories: int = DEFAULT_TRAJECTORIES,
    levels: int = DEFAULT_LEVELS,
    seed: int | None = DEFAULT_SEED,
) -> dict[str, Any]:
    """Elementary-effects screening: cheap triage before a full decomposition.

    Costs ``r(k+1)`` evaluations rather than ``N(k+2)``. It cannot give
    variance shares, and it is not trying to — it separates the parameters that
    plainly do nothing from the ones worth a real study.

    ``mu_star`` is the mean absolute effect; ``sigma`` is its spread across the
    input space. High mu_star with high sigma means the parameter matters and
    matters differently in different regions, which is the signature of an
    interaction or a non-linearity — exactly the parameters to carry forward.
    """
    cleaned = _validate_parameters(parameters)
    k = len(cleaned)
    runs = int(min(max(int(trajectories), MIN_TRAJECTORIES), MAX_TRAJECTORIES))
    grid = max(4, int(levels))
    if grid % 2:
        grid += 1
    delta = grid / (2.0 * (grid - 1))
    rng = random.Random((seed or 0) + 104729)

    effects: list[list[float]] = [[] for _ in range(k)]
    failures = 0
    evaluations = 0

    for _ in range(runs):
        base = [rng.randrange(grid // 2) / (grid - 1.0) for _ in range(k)]
        order = list(range(k))
        rng.shuffle(order)

        point = list(base)
        current = _evaluate_unit(model, cleaned, point)
        evaluations += 1
        if current is None:
            failures += 1
            continue

        for column in order:
            stepped = list(point)
            direction = 1.0 if stepped[column] + delta <= 1.0 else -1.0
            stepped[column] = min(1.0, max(0.0, stepped[column] + direction * delta))
            value = _evaluate_unit(model, cleaned, stepped)
            evaluations += 1
            if value is None:
                failures += 1
                point = stepped
                continue
            effects[column].append((value - current) / (direction * delta))
            current = value
            point = stepped

    rows = []
    for column in range(k):
        sample = effects[column]
        mu_star = statistics.fmean(abs(value) for value in sample) if sample else 0.0
        mu = statistics.fmean(sample) if sample else 0.0
        sigma = statistics.pstdev(sample) if len(sample) > 1 else 0.0
        rows.append(
            {
                "name": cleaned[column]["name"],
                "mu_star": mu_star,
                "mu": mu,
                "sigma": sigma,
                "samples": len(sample),
                "non_linear": sigma > mu_star * 0.5 and mu_star > 0,
                "monotone": abs(mu) > 0.9 * mu_star if mu_star > 0 else True,
            }
        )

    largest = max((row["mu_star"] for row in rows), default=0.0)
    for row in rows:
        row["mu_star_relative"] = (row["mu_star"] / largest) if largest > 0 else 0.0
        row["screen_out"] = row["mu_star_relative"] < 0.1

    rows.sort(key=lambda row: row["mu_star"], reverse=True)
    return {
        "rows": rows,
        "trajectories": runs,
        "levels": grid,
        "delta": delta,
        "evaluations": evaluations,
        "failures": failures,
        "keep": [row["name"] for row in rows if not row["screen_out"]],
        "drop": [row["name"] for row in rows if row["screen_out"]],
    }


def _evaluate_unit(
    model: Callable[[dict[str, float]], float],
    parameters: Sequence[dict[str, Any]],
    unit_point: Sequence[float],
) -> float | None:
    row = {
        parameters[column]["name"]: transform(parameters[column], unit_point[column])
        for column in range(len(parameters))
    }
    try:
        return _finite(model(row))
    except Exception:  # noqa: BLE001 - user model
        return None


# ---------------------------------------------------------------------------
# Reading the result
# ---------------------------------------------------------------------------


def measurement_priorities(result: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    """Which inputs are worth going and measuring, in order.

    The actionable translation of a total-effect index: fixing a parameter to
    a known value removes its share of the variance, and ``1 - S_Ti`` is what
    would be left. That is the number that decides whether reading the gas
    meter is worth an afternoon.
    """
    priorities = []
    for row in result["rows"][: max(1, int(limit))]:
        residual = max(0.0, 1.0 - row["total_effect"])
        priorities.append(
            {
                "name": row["name"],
                "unit": row["unit"],
                "total_effect": row["total_effect"],
                "variance_removed": row["total_effect"],
                "residual_variance_share": residual,
                "residual_stdev": result["output_stdev"] * math.sqrt(residual),
                "current_stdev": result["output_stdev"],
                "worth_measuring": row["total_effect"] >= 0.1,
            }
        )
    return priorities


def get_sensitivity_notes(result: dict[str, Any]) -> list[str]:
    """Plain-language readings of the decomposition."""
    notes: list[str] = []
    rows = result["rows"]
    if not rows:
        return notes

    top = rows[0]
    notes.append(
        "%s carries the largest total effect at %.0f%% of the output variance."
        % (top["name"], top["total_effect"] * 100.0)
    )
    notes.append(result["additivity"]["headline"] + " " + result["additivity"]["detail"])

    interacting = [row for row in rows if row["interaction_dominated"]]
    if interacting:
        notes.append(
            "%s matter(s) almost entirely through interaction — first-order "
            "index near zero, total effect not. A one-at-a-time analysis would "
            "have dropped %s."
            % (
                ", ".join(row["name"] for row in interacting),
                "them" if len(interacting) > 1 else "it",
            )
        )

    negligible = [row["name"] for row in rows if row["is_negligible"]]
    if negligible:
        notes.append(
            "Negligible over the stated ranges (total effect below %.0f%%): %s. "
            "Narrowing these will not narrow the answer."
            % (NEGLIGIBLE_INDEX * 100.0, ", ".join(negligible))
        )

    unseparated = [band for band in result["ranking"] if not band["separated"]]
    if unseparated:
        joined = "; ".join(", ".join(band["names"]) for band in unseparated)
        notes.append(
            "Not separated by this sample: %s. Their intervals overlap, so the "
            "order between them is not a result." % joined
        )

    notes.append(
        "Output spread: mean %.1f, 5th-95th %.1f to %.1f."
        % (result["output_mean"], result["output_p5"], result["output_p95"])
    )
    return notes


def summarise(result: dict[str, Any]) -> str:
    """One-line summary for a log or a saved-study list."""
    top = result["rows"][0] if result["rows"] else None
    return "%s | %d params | top: %s (ST=%.2f) | %s" % (
        result.get("label") or "study",
        len(result["rows"]),
        top["name"] if top else "-",
        top["total_effect"] if top else 0.0,
        result["additivity"]["verdict"],
    )


# ---------------------------------------------------------------------------
# Example models, so the page has something to point at
# ---------------------------------------------------------------------------


def shared_grid_model(row: dict[str, float]) -> float:
    """Household emissions where one grid factor drives three components.

    The case component-pinning cannot express. Grid intensity is multiplied
    into home electricity, EV charging and heat pump heating; pinning any one
    of those components leaves grid intensity varying in the other two.
    """
    grid = row["grid_intensity"]
    home = row["home_kwh"] * grid
    ev = (row["ev_km"] / 100.0) * row["ev_kwh_per_100km"] * grid
    heat = (row["heat_demand_kwh"] / max(row["heat_pump_cop"], 0.5)) * grid
    diet = row["diet_kg_per_day"] * 365.0 * row["diet_factor"]
    return home + ev + heat + diet


def additive_model(row: dict[str, float]) -> float:
    """A plain sum of independent terms, for contrast.

    Included so the additivity verdict can be seen doing its job: on this
    model interaction share should land near zero and the module should say
    that the simpler tools are fine.
    """
    return row["transport"] + row["electricity"] + row["diet"] + row["flights"]


def pathway_model(row: dict[str, float]) -> float:
    """Cumulative emissions along a compounding reduction pathway.

    Non-linear in every input and with no component decomposition at all —
    the shape of `src.utils.goal_pathway` and `src.carbon.replacement_timing`.
    """
    total = 0.0
    level = row["baseline"]
    for year in range(int(row["horizon"])):
        level *= (1.0 - row["reduction_rate"])
        level *= (1.0 + row["rebound"] * row["reduction_rate"])
        total += level / ((1.0 + row["discount"]) ** year)
    return total


def ishigami_model(row: dict[str, float]) -> float:
    """The Ishigami function, which exists to check that this module is right.

    ``f = sin(x1) + a sin^2(x2) + b x3^4 sin(x1)`` with x uniform on [-pi, pi].
    Its Sobol indices are known in closed form, and it is deliberately nasty:
    strongly non-linear, non-monotonic, and x3 has a first-order index of
    exactly zero while carrying a substantial total effect through its
    interaction with x1.

    That last property is the whole reason it is here. A one-at-a-time
    analysis, a tornado chart, or any component-pinning scheme will report x3
    as irrelevant. It is responsible for roughly a quarter of the variance.
    If this module ever agrees that x3 does not matter, it is broken.
    """
    x1, x2, x3 = row["x1"], row["x2"], row["x3"]
    return (
        math.sin(x1)
        + ISHIGAMI_A * math.sin(x2) ** 2
        + ISHIGAMI_B * (x3 ** 4) * math.sin(x1)
    )


def ishigami_parameters() -> list[dict[str, Any]]:
    """The three uniform inputs the analytic indices are defined over."""
    return [
        build_parameter(name, "uniform", low=-math.pi, high=math.pi)
        for name in ("x1", "x2", "x3")
    ]


def ishigami_analytic() -> dict[str, dict[str, float]]:
    """Closed-form Sobol indices for the Ishigami function.

    Derived from the standard variance terms for a = 7, b = 0.1::

        V1 = b pi^4 / 5 + b^2 pi^8 / 50 + 1/2
        V2 = a^2 / 8
        V13 = b^2 pi^8 (1/18 - 1/50)
        V  = V1 + V2 + V13
    """
    a, b = ISHIGAMI_A, ISHIGAMI_B
    v1 = b * math.pi ** 4 / 5.0 + b ** 2 * math.pi ** 8 / 50.0 + 0.5
    v2 = a ** 2 / 8.0
    v13 = b ** 2 * math.pi ** 8 * (1.0 / 18.0 - 1.0 / 50.0)
    total = v1 + v2 + v13
    return {
        "x1": {"first_order": v1 / total, "total_effect": (v1 + v13) / total},
        "x2": {"first_order": v2 / total, "total_effect": v2 / total},
        "x3": {"first_order": 0.0, "total_effect": v13 / total},
    }


def validate_against_ishigami(
    base_samples: int = 4096,
    seed: int | None = DEFAULT_SEED,
) -> dict[str, Any]:
    """Run the engine on a model whose answer is already known.

    Returns the estimated indices next to the analytic ones and the largest
    absolute error. This is the only honest way to present a sensitivity tool:
    show it reproducing a case where the truth is not in dispute.
    """
    result = analyse(
        ishigami_model,
        ishigami_parameters(),
        base_samples=base_samples,
        bootstrap=MIN_BOOTSTRAP,
        label="Ishigami validation",
    )
    truth = ishigami_analytic()

    comparison = []
    worst = 0.0
    for row in result["rows"]:
        expected = truth[row["name"]]
        first_error = abs(row["first_order"] - expected["first_order"])
        total_error = abs(row["total_effect"] - expected["total_effect"])
        worst = max(worst, first_error, total_error)
        comparison.append(
            {
                "name": row["name"],
                "first_order": row["first_order"],
                "first_order_expected": expected["first_order"],
                "first_order_error": first_error,
                "total_effect": row["total_effect"],
                "total_effect_expected": expected["total_effect"],
                "total_effect_error": total_error,
            }
        )

    comparison.sort(key=lambda item: item["name"])
    return {
        "base_samples": result["base_samples"],
        "comparison": comparison,
        "max_error": worst,
        "result": result,
        "note": (
            "x3 has a first-order index of exactly zero and a total effect of "
            "%.3f. Every one-at-a-time method reports it as irrelevant."
            % truth["x3"]["total_effect"]
        ),
    }


DEMO_MODELS: dict[str, dict[str, Any]] = {
    "shared_grid": {
        "label": "Shared grid factor (3 components, 1 parameter)",
        "model": shared_grid_model,
        "note": "One grid intensity drives electricity, EV and heating.",
        "parameters": [
            ("grid_intensity", "lognormal", {"median": 0.23, "gsd": 1.35, "unit": "kg/kWh"}),
            ("home_kwh", "triangular", {"low": 1800.0, "high": 4200.0, "mode": 2700.0, "unit": "kWh"}),
            ("ev_km", "uniform", {"low": 0.0, "high": 18000.0, "unit": "km"}),
            ("ev_kwh_per_100km", "triangular", {"low": 14.0, "high": 24.0, "mode": 18.0, "unit": "kWh/100km"}),
            ("heat_demand_kwh", "triangular", {"low": 4000.0, "high": 16000.0, "mode": 9000.0, "unit": "kWh"}),
            ("heat_pump_cop", "triangular", {"low": 1.8, "high": 4.2, "mode": 3.0, "unit": "COP"}),
            ("diet_kg_per_day", "uniform", {"low": 1.4, "high": 3.2, "unit": "kg/day"}),
            ("diet_factor", "lognormal", {"median": 1.9, "gsd": 1.4, "unit": "kg CO2e/kg"}),
        ],
    },
    "additive": {
        "label": "Additive baseline (independent terms)",
        "model": additive_model,
        "note": "A pure sum — the case where the simpler tools are already right.",
        "parameters": [
            ("transport", "lognormal", {"median": 1800.0, "gsd": 1.3, "unit": "kg"}),
            ("electricity", "lognormal", {"median": 1200.0, "gsd": 1.25, "unit": "kg"}),
            ("diet", "lognormal", {"median": 1400.0, "gsd": 1.35, "unit": "kg"}),
            ("flights", "lognormal", {"median": 600.0, "gsd": 1.8, "unit": "kg"}),
        ],
    },
    "pathway": {
        "label": "Compounding reduction pathway",
        "model": pathway_model,
        "note": "Non-linear, no components to pin, rebound multiplies through.",
        "parameters": [
            ("baseline", "triangular", {"low": 3000.0, "high": 9000.0, "mode": 5200.0, "unit": "kg"}),
            ("reduction_rate", "uniform", {"low": 0.01, "high": 0.12, "unit": "/yr"}),
            ("rebound", "uniform", {"low": 0.0, "high": 0.6, "unit": "share"}),
            ("discount", "uniform", {"low": 0.0, "high": 0.06, "unit": "/yr"}),
            ("horizon", "uniform", {"low": 8.0, "high": 25.0, "unit": "yr"}),
        ],
    },
}


def demo_parameters(key: str) -> list[dict[str, Any]]:
    """Build the parameter list for one of the worked examples."""
    spec = DEMO_MODELS.get(key)
    if not spec:
        raise SensitivityError("Unknown demo model '%s'." % key)
    built = []
    for name, distribution, kwargs in spec["parameters"]:
        built.append(build_parameter(name, distribution, **kwargs))
    return built


def list_demo_models() -> list[dict[str, str]]:
    return [
        {"key": key, "label": spec["label"], "note": spec["note"]}
        for key, spec in DEMO_MODELS.items()
    ]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS global_sensitivity_studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            label TEXT NOT NULL,
            top_parameter TEXT NOT NULL,
            top_total_effect REAL NOT NULL,
            interaction_share REAL NOT NULL,
            base_samples INTEGER NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_global_sensitivity_studies_user
        ON global_sensitivity_studies (user_id)
        """
    )


def _storable(result: dict[str, Any]) -> dict[str, Any]:
    """Strip anything that will not survive a JSON round trip."""
    return {
        "engine_version": result.get("engine_version", ENGINE_VERSION),
        "label": result.get("label", ""),
        "rows": result.get("rows", []),
        "base_samples": result.get("base_samples", 0),
        "usable_samples": result.get("usable_samples", 0),
        "seed": result.get("seed"),
        "sum_first_order": result.get("sum_first_order", 0.0),
        "sum_total_effect": result.get("sum_total_effect", 0.0),
        "interaction_share": result.get("interaction_share", 0.0),
        "additivity": result.get("additivity", {}),
        "output_mean": result.get("output_mean", 0.0),
        "output_stdev": result.get("output_stdev", 0.0),
        "diagnostics": result.get("diagnostics", []),
        "ranking": result.get("ranking", []),
    }


def save_study(user_id: Any, result: dict[str, Any]) -> int | None:
    """Persist a study. Returns the row id, or None if storage is unavailable."""
    if not user_id or not result.get("rows"):
        return None
    top = result["rows"][0]
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                """
                INSERT INTO global_sensitivity_studies
                    (user_id, label, top_parameter, top_total_effect,
                     interaction_share, base_samples, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(user_id),
                    result.get("label") or "study",
                    top["name"],
                    float(top["total_effect"]),
                    float(result["interaction_share"]),
                    int(result["base_samples"]),
                    json.dumps(_storable(result)),
                ),
            )
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def get_studies(user_id: Any, limit: int = 25) -> list[dict[str, Any]]:
    """Most recent saved studies for one user."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, label, top_parameter, top_total_effect,
                       interaction_share, base_samples, payload, created_at
                FROM global_sensitivity_studies
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        return []

    studies = []
    for row in rows:
        try:
            payload = json.loads(row[6])
        except (TypeError, ValueError):
            payload = {}
        studies.append(
            {
                "id": row[0],
                "label": row[1],
                "top_parameter": row[2],
                "top_total_effect": row[3],
                "interaction_share": row[4],
                "base_samples": row[5],
                "payload": payload,
                "created_at": row[7],
            }
        )
    return studies


def delete_study(user_id: Any, study_id: int) -> bool:
    """Remove one saved study belonging to this user."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM global_sensitivity_studies WHERE user_id = ? AND id = ?",
                (str(user_id), int(study_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False
