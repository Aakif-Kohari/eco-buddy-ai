"""Weighting a self-selected user base back toward a population.

`carbon_benchmarking.get_leaderboard()` ranks whoever is in the database.
`community_dashboard.py` reports community totals. `block_leaderboard.py` does
it by neighbourhood. All of them compute a mean over the people who happen to
be present and present it as a fact about people.

The people in the database are not a sample of any population. They are people
who downloaded a carbon footprint app and finished an assessment, which is
about the most efficiently self-selected group imaginable for this particular
variable. They are younger, richer, more urban and considerably more
climate-engaged than the population they are implicitly standing in for, and
every one of those correlates with footprint — several of them in opposite
directions, which is worse, because it means the bias cannot even be assumed
to be conservative.

So "you are 18% below the community average" is a statement about an unweighted
convenience sample, phrased as a statement about people.

What weighting can and cannot do
--------------------------------
Post-stratification and raking correct for over- and under-representation on
variables we can *observe*. If detached houses are 30% of the population and 8%
of the respondents, their responses get weighted up until they are 30% of the
estimate. That removes the bias attributable to dwelling type.

It does nothing about participation propensity itself. People who install a
carbon app are more climate-engaged than people who do not, and no amount of
weighting on housing and household size will fix that, because engagement was
never measured. That residual is bounded here rather than ignored, and the
bound is reported next to the corrected estimate so a weighted figure never
gets mistaken for a measured one.

Design effect
-------------
Weighting costs precision. Kish's design effect::

    deff = n * sum(w^2) / (sum w)^2
    n_eff = n / deff

A weighted comparison from 200 respondents with an effective sample size of 31
should say 31 everywhere it currently says 200. That number, not the raw count,
is what determines whether a comparison means anything, and it is the reason
this module refuses to publish some aggregates at all.

Refusals
--------
No published aggregate below a minimum effective sample size. No ranking of
groups whose intervals overlap — that is a tie. No weighting to targets that
do not sum to one. No cell with zero respondents silently dropped: an empty
stratum is a coverage hole and must be named, because dropping it is what turns
"we have no data on detached rural houses" into "detached rural houses are like
everyone else".
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import statistics
from typing import Any, Iterable, Mapping, Sequence

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

ENGINE_VERSION = "1.0.0"

# Raking --------------------------------------------------------------------
DEFAULT_MAX_ITERATIONS = 60
MIN_ITERATIONS = 5
MAX_ITERATIONS = 500
CONVERGENCE_TOLERANCE = 1e-6

# Weight trimming -----------------------------------------------------------
DEFAULT_TRIM_RATIO = 5.0
MIN_TRIM_RATIO = 1.5

# Publication thresholds ----------------------------------------------------
MIN_EFFECTIVE_SAMPLE = 20
MIN_RESPONDENTS = 5
MIN_CELL_RESPONDENTS = 1
TARGET_SUM_TOLERANCE = 1e-6
MAX_VARIABLES = 6
MAX_LEVELS = 12

# Coverage bias -------------------------------------------------------------
DEFAULT_PARTICIPATION_CORRELATION = 0.02

CONFIDENCE_Z = {
    0.80: 1.281552,
    0.90: 1.644854,
    0.95: 1.959964,
    0.99: 2.575829,
}


class PopulationError(ValueError):
    """Raised when an estimate cannot be produced as asked."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _z_for(confidence: float) -> float:
    """Normal critical value; only the standard levels are offered.

    A confidence level the caller invented is almost always a mistake, and
    interpolating one silently is how a 93.7% interval ends up in a report.
    """
    key = round(float(confidence), 2)
    if key not in CONFIDENCE_Z:
        raise PopulationError(
            "Confidence must be one of %s." % ", ".join(str(value) for value in sorted(CONFIDENCE_Z))
        )
    return CONFIDENCE_Z[key]


# ---------------------------------------------------------------------------
# Variables and respondents
# ---------------------------------------------------------------------------


def build_variable(
    name: str,
    targets: Mapping[str, float],
    label: str = "",
) -> dict[str, Any]:
    """One stratifying variable and its population marginal.

    Targets are supplied by the caller, not hardcoded. Census shares differ by
    country and by year, and a wrong hardcoded table would replace a known bias
    with an invisible one.
    """
    key = str(name or "").strip()
    if not key:
        raise PopulationError("Every variable needs a name.")
    if not targets:
        raise PopulationError("Variable '%s' needs population targets." % key)
    if len(targets) > MAX_LEVELS:
        raise PopulationError(
            "Variable '%s' has %d levels; at most %d are supported."
            % (key, len(targets), MAX_LEVELS)
        )

    cleaned: dict[str, float] = {}
    for level, share in targets.items():
        value = _finite(share)
        if value is None or value < 0:
            raise PopulationError(
                "Target for '%s'/'%s' must be a non-negative number." % (key, level)
            )
        cleaned[str(level)] = value

    total = sum(cleaned.values())
    if abs(total - 1.0) > TARGET_SUM_TOLERANCE:
        raise PopulationError(
            "Targets for '%s' sum to %.6f, not 1. A marginal that does not sum "
            "to one is not a marginal, and raking to it would silently rescale "
            "the whole estimate." % (key, total)
        )

    return {
        "name": key,
        "label": str(label or key),
        "levels": list(cleaned),
        "targets": cleaned,
    }


def _validate_variables(variables: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    if not variables:
        raise PopulationError("At least one stratifying variable is required.")
    if len(variables) > MAX_VARIABLES:
        raise PopulationError(
            "At most %d variables are supported; more than that and most cells "
            "are empty." % MAX_VARIABLES
        )
    seen: set[str] = set()
    cleaned = []
    for variable in variables:
        if not isinstance(variable, dict) or "targets" not in variable:
            raise PopulationError("Variables must be built with build_variable().")
        if variable["name"] in seen:
            raise PopulationError("Variable '%s' appears twice." % variable["name"])
        seen.add(variable["name"])
        cleaned.append(dict(variable))
    return cleaned


def build_respondent(
    identifier: Any,
    value: float,
    **levels: Any,
) -> dict[str, Any]:
    """One respondent: an outcome value plus their level on each variable."""
    number = _finite(value)
    if number is None:
        raise PopulationError("Respondent '%s' needs a finite value." % identifier)
    return {
        "id": str(identifier),
        "value": number,
        "levels": {str(key): str(level) for key, level in levels.items()},
    }


def _validate_respondents(
    respondents: Sequence[Mapping[str, Any]],
    variables: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(respondents) < MIN_RESPONDENTS:
        raise PopulationError(
            "Need at least %d respondents; below that the weights are noise."
            % MIN_RESPONDENTS
        )
    cleaned = []
    for respondent in respondents:
        levels = respondent.get("levels", {})
        for variable in variables:
            name = variable["name"]
            level = levels.get(name)
            if level is None:
                raise PopulationError(
                    "Respondent '%s' has no level for '%s'. A respondent who "
                    "cannot be placed in a stratum cannot be weighted."
                    % (respondent.get("id"), name)
                )
            if level not in variable["targets"]:
                raise PopulationError(
                    "Respondent '%s' has level '%s' for '%s', which is not in "
                    "the population targets. Either the targets are incomplete "
                    "or the data needs recoding — both are real problems and "
                    "neither should be smoothed over."
                    % (respondent.get("id"), level, name)
                )
        cleaned.append(dict(respondent))
    return cleaned


# ---------------------------------------------------------------------------
# The sample as it stands
# ---------------------------------------------------------------------------


def sample_marginals(
    respondents: Sequence[Mapping[str, Any]],
    variables: Sequence[dict[str, Any]],
    weights: Sequence[float] | None = None,
) -> dict[str, dict[str, float]]:
    """Observed share of each level, optionally weighted."""
    cleaned = _validate_variables(variables)
    total = sum(weights) if weights else float(len(respondents))
    if total <= 0:
        raise PopulationError("Weights sum to zero.")

    marginals: dict[str, dict[str, float]] = {}
    for variable in cleaned:
        name = variable["name"]
        counts = {level: 0.0 for level in variable["targets"]}
        for index, respondent in enumerate(respondents):
            level = respondent["levels"][name]
            counts[level] += weights[index] if weights else 1.0
        marginals[name] = {level: count / total for level, count in counts.items()}
    return marginals


def representation_gaps(
    respondents: Sequence[Mapping[str, Any]],
    variables: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Where the sample departs from the population, before any correction.

    This is the table that makes the case. It is also the one that shows which
    strata have nobody in them, which no amount of weighting can repair.
    """
    cleaned = _validate_variables(variables)
    observed = sample_marginals(respondents, cleaned)

    gaps = []
    for variable in cleaned:
        name = variable["name"]
        for level, target in variable["targets"].items():
            share = observed[name][level]
            count = sum(
                1 for respondent in respondents if respondent["levels"][name] == level
            )
            gaps.append(
                {
                    "variable": name,
                    "level": level,
                    "sample_share": share,
                    "population_share": target,
                    "difference": share - target,
                    "ratio": (target / share) if share > 0 else None,
                    "respondents": count,
                    "empty": count == 0,
                    "under_represented": share < target,
                }
            )
    gaps.sort(key=lambda entry: abs(entry["difference"]), reverse=True)
    return gaps


def coverage_holes(
    respondents: Sequence[Mapping[str, Any]],
    variables: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Strata with a population share and no respondents.

    Reported rather than dropped. Dropping an empty stratum is what turns "we
    have no data on detached rural houses" into "detached rural houses are like
    everyone else", which is a claim nobody made and everybody reads.
    """
    holes = [entry for entry in representation_gaps(respondents, variables) if entry["empty"]]
    for hole in holes:
        hole["uncovered_population"] = hole["population_share"]
    return holes


# ---------------------------------------------------------------------------
# Raking
# ---------------------------------------------------------------------------


def rake(
    respondents: Sequence[Mapping[str, Any]],
    variables: Sequence[dict[str, Any]],
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    tolerance: float = CONVERGENCE_TOLERANCE,
) -> dict[str, Any]:
    """Iterative proportional fitting of weights to the population marginals.

    Full joint cell targets are rarely available; marginals usually are. Raking
    cycles through the variables, rescaling weights so each marginal matches in
    turn, and repeats until the changes fall below tolerance.

    Convergence is reported, not assumed. A raking run that stopped at the
    iteration cap produces weights that match some marginals and not others,
    and calling those a correction is worse than not correcting at all, because
    the failure is invisible in the output.
    """
    cleaned_variables = _validate_variables(variables)
    cleaned = _validate_respondents(respondents, cleaned_variables)
    count = len(cleaned)
    limit = int(min(max(int(max_iterations), MIN_ITERATIONS), MAX_ITERATIONS))

    holes = coverage_holes(cleaned, cleaned_variables)
    weights = [1.0] * count

    history: list[dict[str, Any]] = []
    converged = False
    for iteration in range(limit):
        largest_change = 0.0
        for variable in cleaned_variables:
            name = variable["name"]
            total = sum(weights)
            for level, target in variable["targets"].items():
                members = [
                    index
                    for index in range(count)
                    if cleaned[index]["levels"][name] == level
                ]
                if not members:
                    # An empty stratum cannot be raked to. It is a coverage
                    # hole, reported separately, and skipping it here is the
                    # only option — the alternative is dividing by zero.
                    continue
                current = sum(weights[index] for index in members) / total
                if current <= 0:
                    continue
                factor = target / current
                largest_change = max(largest_change, abs(factor - 1.0))
                for index in members:
                    weights[index] *= factor

        # Normalise so the weights average one, which keeps them interpretable
        # as "this respondent stands for N people relative to the average".
        scale = count / sum(weights)
        weights = [weight * scale for weight in weights]

        history.append({"iteration": iteration + 1, "max_change": largest_change})
        if largest_change < tolerance:
            converged = True
            break

    achieved = sample_marginals(cleaned, cleaned_variables, weights)
    residuals = []
    for variable in cleaned_variables:
        name = variable["name"]
        for level, target in variable["targets"].items():
            residuals.append(
                {
                    "variable": name,
                    "level": level,
                    "target": target,
                    "achieved": achieved[name][level],
                    "residual": achieved[name][level] - target,
                }
            )

    worst = max((abs(entry["residual"]) for entry in residuals), default=0.0)
    return {
        "weights": weights,
        "converged": converged,
        "iterations": len(history),
        "history": history,
        "residuals": residuals,
        "worst_residual": worst,
        "coverage_holes": holes,
        "verdict": (
            "Converged in %d iterations; worst marginal off by %.4f."
            % (len(history), worst)
            if converged
            else "Did not converge in %d iterations; worst marginal still off "
            "by %.4f. These weights match some marginals and not others."
            % (len(history), worst)
        ),
    }


def post_stratify(
    respondents: Sequence[Mapping[str, Any]],
    variables: Sequence[dict[str, Any]],
    joint_targets: Mapping[tuple, float],
) -> dict[str, Any]:
    """Weight to full joint cell targets, when they are available.

    Exact where raking is iterative, and usually unavailable, because published
    statistics give margins rather than the full cross-tabulation. Cells with a
    population share and no respondents are refused rather than redistributed:
    a cell nobody is in is a hole, and quietly spreading its weight over the
    cells that are populated is precisely the assumption under scrutiny.
    """
    cleaned_variables = _validate_variables(variables)
    cleaned = _validate_respondents(respondents, cleaned_variables)
    names = [variable["name"] for variable in cleaned_variables]

    total_target = sum(joint_targets.values())
    if abs(total_target - 1.0) > 1e-4:
        raise PopulationError(
            "Joint targets sum to %.6f, not 1." % total_target
        )

    membership: dict[tuple, list[int]] = {}
    for index, respondent in enumerate(cleaned):
        key = tuple(respondent["levels"][name] for name in names)
        membership.setdefault(key, []).append(index)

    empty = [
        {"cell": key, "population_share": share}
        for key, share in joint_targets.items()
        if share > 0 and not membership.get(key)
    ]
    if empty:
        uncovered = sum(entry["population_share"] for entry in empty)
        raise PopulationError(
            "%d population cells have no respondents, covering %.1f%% of the "
            "population: %s. Post-stratification cannot weight a cell nobody "
            "is in — rake to the margins instead, and read the coverage holes."
            % (
                len(empty),
                uncovered * 100.0,
                ", ".join("/".join(entry["cell"]) for entry in empty[:5]),
            )
        )

    count = len(cleaned)
    weights = [0.0] * count
    cells = []
    for key, members in membership.items():
        target = joint_targets.get(key, 0.0)
        sample_share = len(members) / count
        weight = (target / sample_share) if sample_share > 0 else 0.0
        for index in members:
            weights[index] = weight
        cells.append(
            {
                "cell": list(key),
                "respondents": len(members),
                "sample_share": sample_share,
                "population_share": target,
                "weight": weight,
            }
        )

    scale = count / sum(weights) if sum(weights) > 0 else 1.0
    weights = [weight * scale for weight in weights]
    return {
        "weights": weights,
        "cells": sorted(cells, key=lambda entry: entry["weight"], reverse=True),
        "converged": True,
        "iterations": 1,
        "coverage_holes": [],
        "verdict": "Post-stratified against %d joint cells." % len(cells),
    }


# ---------------------------------------------------------------------------
# Weight trimming
# ---------------------------------------------------------------------------


def trim_weights(
    weights: Sequence[float],
    ratio: float = DEFAULT_TRIM_RATIO,
) -> dict[str, Any]:
    """Cap extreme weights and redistribute, reporting both sides of the trade.

    Extreme weights are variance disasters. One respondent carrying a weight of
    40 *is* the estimate, and the interval around it is wide enough to be
    useless. Trimming caps that, at the cost of reintroducing some of the bias
    the weighting was meant to remove.

    Both effects are reported. Trimming is a choice between two bad things and
    the caller should be able to see which one they bought.
    """
    if not weights:
        raise PopulationError("No weights to trim.")
    cap_ratio = max(float(ratio), MIN_TRIM_RATIO)
    count = len(weights)
    mean = sum(weights) / count
    ceiling = mean * cap_ratio

    trimmed = [min(weight, ceiling) for weight in weights]
    capped = [index for index, weight in enumerate(weights) if weight > ceiling]
    shortfall = sum(weights) - sum(trimmed)

    if shortfall > 0:
        eligible = [index for index in range(count) if index not in set(capped)]
        base = sum(trimmed[index] for index in eligible)
        if base > 0:
            for index in eligible:
                trimmed[index] += shortfall * (trimmed[index] / base)

    scale = count / sum(trimmed) if sum(trimmed) > 0 else 1.0
    trimmed = [weight * scale for weight in trimmed]

    before = design_effect(weights)
    after = design_effect(trimmed)
    return {
        "weights": trimmed,
        "ceiling": ceiling,
        "ratio": cap_ratio,
        "capped": len(capped),
        "capped_share": len(capped) / count,
        "max_before": max(weights),
        "max_after": max(trimmed),
        "design_effect_before": before["design_effect"],
        "design_effect_after": after["design_effect"],
        "effective_sample_before": before["effective_sample"],
        "effective_sample_after": after["effective_sample"],
        "precision_gained": after["effective_sample"] - before["effective_sample"],
        "headline": (
            "Capped %d weights at %.2f. Effective sample rises from %.1f to "
            "%.1f, at the cost of reintroducing part of the representation gap "
            "those respondents were correcting."
            % (
                len(capped),
                ceiling,
                before["effective_sample"],
                after["effective_sample"],
            )
            if capped
            else "No weight exceeded the cap; nothing trimmed."
        ),
    }


# ---------------------------------------------------------------------------
# Design effect and weighted estimates
# ---------------------------------------------------------------------------


def design_effect(weights: Sequence[float]) -> dict[str, Any]:
    """Kish's design effect and the effective sample size that follows.

    ``deff = n * sum(w^2) / (sum w)^2``. Unweighted data has deff = 1 exactly.
    Everything else is worse, and by how much is the single most important
    number attached to any weighted estimate — 200 respondents with an
    effective sample of 31 should say 31 wherever they currently say 200.
    """
    if not weights:
        raise PopulationError("No weights supplied.")
    count = len(weights)
    total = sum(weights)
    if total <= 0:
        raise PopulationError("Weights sum to zero.")
    squared = sum(weight * weight for weight in weights)
    deff = count * squared / (total * total)
    effective = count / deff if deff > 0 else 0.0
    return {
        "respondents": count,
        "design_effect": deff,
        "effective_sample": effective,
        "loss": count - effective,
        "loss_share": (count - effective) / count if count else 0.0,
        "max_weight": max(weights),
        "min_weight": min(weights),
        "weight_ratio": (max(weights) / min(weights)) if min(weights) > 0 else float("inf"),
    }


def weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    total = sum(weights)
    if total <= 0:
        raise PopulationError("Weights sum to zero.")
    return sum(values[index] * weights[index] for index in range(len(values))) / total


def weighted_quantile(
    values: Sequence[float],
    weights: Sequence[float],
    quantile: float,
) -> float:
    """Weighted quantile by cumulative weight.

    Used for the percentile claims, which are otherwise computed on the
    unweighted sample and inherit its skew entirely.
    """
    if not 0.0 <= quantile <= 1.0:
        raise PopulationError("Quantile must lie in [0, 1].")
    paired = sorted(zip(values, weights), key=lambda item: item[0])
    total = sum(weight for _, weight in paired)
    if total <= 0:
        raise PopulationError("Weights sum to zero.")

    cumulative = 0.0
    for value, weight in paired:
        cumulative += weight
        if cumulative >= quantile * total:
            return float(value)
    return float(paired[-1][0])


def weighted_standard_error(
    values: Sequence[float],
    weights: Sequence[float],
) -> float:
    """Standard error built on the effective sample size, not the raw count.

    Dividing the weighted variance by n rather than n_eff is the standard way
    a weighted estimate ends up with an interval it has not earned.
    """
    effective = design_effect(weights)["effective_sample"]
    if effective < 2:
        return float("inf")
    mean = weighted_mean(values, weights)
    total = sum(weights)
    variance = sum(
        weights[index] * (values[index] - mean) ** 2 for index in range(len(values))
    ) / total
    return math.sqrt(variance / effective)


def coverage_bias_bound(
    estimate: float,
    dispersion: float,
    participation_correlation: float = DEFAULT_PARTICIPATION_CORRELATION,
    sample_fraction: float = 0.01,
) -> dict[str, Any]:
    """Bound the bias that weighting cannot reach.

    Weighting corrects for what we observed. Participation also depends on
    things we never collect — climate engagement above all — and that residual
    is not zero.

    Uses the standard decomposition of the error in a non-probability sample::

        error = rho * sqrt((1 - f) / f) * sigma

    where `rho` is the correlation between the participation indicator and the
    outcome, `f` is the sample as a share of the population, and `sigma` is the
    outcome's own spread.

    The middle term is why the default `rho` here is 0.02 and not something
    that looks more like a normal correlation. At a 1% sample the leverage
    factor is about 10, so a correlation of 0.02 already moves the estimate by
    a fifth of a standard deviation, and a correlation of 0.25 would move it by
    two and a half — which is the point of the decomposition rather than a
    quirk of it. Values above about 0.05 describe a sample so self-selected
    that the estimate has essentially no information in it, and the bound will
    say so by becoming uselessly wide.

    It is a bound, not an estimate, and it should be shown as a range around a
    corrected figure so that figure never reads as a measurement.
    """
    rho = abs(_finite(participation_correlation) or 0.0)
    if rho > 1.0:
        raise PopulationError("A correlation cannot exceed 1.")
    fraction = _finite(sample_fraction) or 0.0
    if not 0.0 < fraction < 1.0:
        raise PopulationError("Sample fraction must lie strictly in (0, 1).")

    leverage = math.sqrt((1.0 - fraction) / fraction)
    bias = rho * leverage * abs(dispersion)
    return {
        "participation_correlation": rho,
        "sample_fraction": fraction,
        "leverage": leverage,
        "bias": bias,
        "lower": estimate - bias,
        "upper": estimate + bias,
        "relative": (bias / abs(estimate)) if estimate else 0.0,
        "note": (
            "Assumes participation correlates %.2f with the outcome. Weighting "
            "cannot touch this term because engagement was never measured; the "
            "bound moves with the assumption and is not a measurement."
            % rho
        ),
    }


# ---------------------------------------------------------------------------
# The estimate
# ---------------------------------------------------------------------------


def estimate_population_mean(
    respondents: Sequence[Mapping[str, Any]],
    variables: Sequence[dict[str, Any]],
    trim_ratio: float = DEFAULT_TRIM_RATIO,
    confidence: float = 0.95,
    participation_correlation: float = DEFAULT_PARTICIPATION_CORRELATION,
    sample_fraction: float = 0.01,
    minimum_effective_sample: int = MIN_EFFECTIVE_SAMPLE,
) -> dict[str, Any]:
    """Raked, trimmed, design-effect-aware population mean, with refusals.

    Returns both the unweighted and the weighted figure, because the size of
    the gap between them is the finding. If they agree, the sample happened to
    be representative on the variables supplied and the leaderboard was fine.
    If they do not, the leaderboard has been reporting the wrong number, and by
    how much.
    """
    cleaned_variables = _validate_variables(variables)
    cleaned = _validate_respondents(respondents, cleaned_variables)
    values = [respondent["value"] for respondent in cleaned]

    raked = rake(cleaned, cleaned_variables)
    trimmed = trim_weights(raked["weights"], trim_ratio)
    weights = trimmed["weights"]

    effect = design_effect(weights)
    unweighted = statistics.fmean(values)
    weighted = weighted_mean(values, weights)
    standard_error = weighted_standard_error(values, weights)
    z = _z_for(confidence)

    dispersion = statistics.pstdev(values) if len(values) > 1 else 0.0
    bound = coverage_bias_bound(
        weighted, dispersion, participation_correlation, sample_fraction
    )

    publishable = effect["effective_sample"] >= minimum_effective_sample
    refusals: list[str] = []
    if not publishable:
        refusals.append(
            "Effective sample size is %.1f, below the minimum of %d. The "
            "weighted estimate is reported for inspection and must not be "
            "published as a community figure."
            % (effect["effective_sample"], minimum_effective_sample)
        )
    if not raked["converged"]:
        refusals.append(
            "Raking did not converge. The weights match some marginals and not "
            "others, so they are not a correction of anything."
        )
    if raked["coverage_holes"]:
        share = sum(hole["population_share"] for hole in raked["coverage_holes"])
        refusals.append(
            "%d strata covering %.1f%% of the population have no respondents. "
            "Weighting cannot reach them and the estimate says nothing about "
            "those people."
            % (len(raked["coverage_holes"]), share * 100.0)
        )

    return {
        "engine_version": ENGINE_VERSION,
        "respondents": len(cleaned),
        "unweighted_mean": unweighted,
        "weighted_mean": weighted,
        "correction": weighted - unweighted,
        "correction_percent": (
            (weighted - unweighted) / unweighted * 100.0 if unweighted else 0.0
        ),
        "standard_error": standard_error,
        "confidence": confidence,
        "lower": weighted - z * standard_error,
        "upper": weighted + z * standard_error,
        "weighted_median": weighted_quantile(values, weights, 0.5),
        "weighted_p25": weighted_quantile(values, weights, 0.25),
        "weighted_p75": weighted_quantile(values, weights, 0.75),
        "unweighted_median": statistics.median(values),
        "design": effect,
        "raking": {
            key: value for key, value in raked.items() if key not in ("weights", "history")
        },
        "trimming": {
            key: value for key, value in trimmed.items() if key != "weights"
        },
        "weights": weights,
        "coverage_bias": bound,
        "gaps": representation_gaps(cleaned, cleaned_variables),
        "publishable": publishable and not refusals,
        "refusals": refusals,
        "headline": _headline(unweighted, weighted, effect, len(cleaned)),
    }


def _headline(
    unweighted: float,
    weighted: float,
    effect: Mapping[str, Any],
    count: int,
) -> str:
    shift = weighted - unweighted
    percent = (shift / unweighted * 100.0) if unweighted else 0.0
    return (
        "Unweighted mean %.0f, weighted %.0f — a correction of %+.0f (%+.1f%%). "
        "%d respondents, effective sample %.1f."
        % (unweighted, weighted, shift, percent, count, effect["effective_sample"])
    )


def percentile_of(
    value: float,
    respondents: Sequence[Mapping[str, Any]],
    weights: Sequence[float],
) -> float:
    """Where one value sits in the weighted distribution.

    The unweighted version of this is what every "you are in the top 20%"
    message in the app is currently computed from.
    """
    total = sum(weights)
    if total <= 0:
        raise PopulationError("Weights sum to zero.")
    below = sum(
        weights[index]
        for index, respondent in enumerate(respondents)
        if respondent["value"] < value
    )
    return below / total * 100.0


# ---------------------------------------------------------------------------
# Comparing groups
# ---------------------------------------------------------------------------


def compare_groups(
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
    variables: Sequence[dict[str, Any]],
    confidence: float = 0.95,
    minimum_effective_sample: int = MIN_EFFECTIVE_SAMPLE,
    **kwargs: Any,
) -> dict[str, Any]:
    """Rank groups, and decline to rank the ones that overlap.

    A leaderboard that says "positions 3 to 7 are indistinguishable" is more
    useful and considerably more truthful than one that orders them. Groups
    below the effective-sample floor are excluded from the ranking entirely
    rather than placed at a position their data cannot support.
    """
    cleaned_variables = _validate_variables(variables)
    entries: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    for name, members in groups.items():
        try:
            result = estimate_population_mean(
                members,
                cleaned_variables,
                confidence=confidence,
                minimum_effective_sample=minimum_effective_sample,
                **kwargs,
            )
        except PopulationError as error:
            excluded.append({"group": str(name), "reason": str(error)})
            continue

        if not result["publishable"]:
            excluded.append(
                {
                    "group": str(name),
                    "reason": "; ".join(result["refusals"]),
                    "effective_sample": result["design"]["effective_sample"],
                }
            )
            continue

        entries.append(
            {
                "group": str(name),
                "mean": result["weighted_mean"],
                "lower": result["lower"],
                "upper": result["upper"],
                "effective_sample": result["design"]["effective_sample"],
                "respondents": result["respondents"],
                "unweighted_mean": result["unweighted_mean"],
            }
        )

    entries.sort(key=lambda entry: entry["mean"])

    bands: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for entry in entries:
        if not current:
            current = [entry]
            continue
        band_upper = max(item["upper"] for item in current)
        if entry["lower"] <= band_upper:
            current.append(entry)
        else:
            bands.append(_band(current, len(bands) + 1))
            current = [entry]
    if current:
        bands.append(_band(current, len(bands) + 1))

    unweighted_order = [
        entry["group"]
        for entry in sorted(entries, key=lambda item: item["unweighted_mean"])
    ]
    weighted_order = [entry["group"] for entry in entries]
    churn = sum(
        1
        for index, name in enumerate(weighted_order)
        if index >= len(unweighted_order) or unweighted_order[index] != name
    )

    return {
        "entries": entries,
        "bands": bands,
        "excluded": excluded,
        "unweighted_order": unweighted_order,
        "weighted_order": weighted_order,
        "rank_churn": churn,
        "headline": (
            "%d group(s) ranked into %d band(s); %d excluded for insufficient "
            "effective sample. Weighting moved %d position(s) relative to the "
            "unweighted ordering."
            % (len(entries), len(bands), len(excluded), churn)
        ),
    }


def _band(members: Sequence[Mapping[str, Any]], position: int) -> dict[str, Any]:
    return {
        "band": position,
        "groups": [item["group"] for item in members],
        "lowest_mean": min(item["mean"] for item in members),
        "highest_mean": max(item["mean"] for item in members),
        "separated": len(members) == 1,
    }


def get_inference_notes(result: Mapping[str, Any]) -> list[str]:
    """Plain-language readings of a weighted estimate."""
    notes: list[str] = [result["headline"]]
    effect = result["design"]

    notes.append(
        "Design effect %.2f — %d respondents carry the information of %.1f. "
        "Every comparison drawn from this should quote the smaller number."
        % (effect["design_effect"], effect["respondents"], effect["effective_sample"])
    )

    worst = result["gaps"][0] if result["gaps"] else None
    if worst:
        notes.append(
            "Largest representation gap: '%s'/'%s' is %.0f%% of respondents "
            "against %.0f%% of the population."
            % (
                worst["variable"],
                worst["level"],
                worst["sample_share"] * 100.0,
                worst["population_share"] * 100.0,
            )
        )

    if result["trimming"]["capped"]:
        notes.append(result["trimming"]["headline"])

    bound = result["coverage_bias"]
    notes.append(
        "Residual coverage bias bound: %.0f to %.0f. %s"
        % (bound["lower"], bound["upper"], bound["note"])
    )

    for refusal in result["refusals"]:
        notes.append("Refused: %s" % refusal)
    return notes


def summarise(result: Mapping[str, Any]) -> str:
    """One line for a log or a saved-estimate list."""
    return "n=%d n_eff=%.1f | unweighted %.0f -> weighted %.0f (%+.1f%%) | %s" % (
        result["respondents"],
        result["design"]["effective_sample"],
        result["unweighted_mean"],
        result["weighted_mean"],
        result["correction_percent"],
        "publishable" if result["publishable"] else "withheld",
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS population_estimates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            label TEXT NOT NULL,
            respondents INTEGER NOT NULL,
            effective_sample REAL NOT NULL,
            unweighted_mean REAL NOT NULL,
            weighted_mean REAL NOT NULL,
            publishable INTEGER NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_population_estimates_user
        ON population_estimates (user_id)
        """
    )


def _storable(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in result.items()
        if key not in ("weights",)
    }


def save_estimate(user_id: Any, result: Mapping[str, Any], label: str = "") -> int | None:
    """Persist an estimate. None if storage is unavailable."""
    if not user_id or not result.get("respondents"):
        return None
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                """
                INSERT INTO population_estimates
                    (user_id, label, respondents, effective_sample,
                     unweighted_mean, weighted_mean, publishable, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(user_id),
                    str(label or "estimate"),
                    int(result["respondents"]),
                    float(result["design"]["effective_sample"]),
                    float(result["unweighted_mean"]),
                    float(result["weighted_mean"]),
                    1 if result["publishable"] else 0,
                    json.dumps(_storable(result)),
                ),
            )
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def get_estimates(user_id: Any, limit: int = 25) -> list[dict[str, Any]]:
    """Most recent saved estimates for one user."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, label, respondents, effective_sample, unweighted_mean,
                       weighted_mean, publishable, payload, created_at
                FROM population_estimates
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        return []

    estimates = []
    for row in rows:
        try:
            payload = json.loads(row[7])
        except (TypeError, ValueError):
            payload = {}
        estimates.append(
            {
                "id": row[0],
                "label": row[1],
                "respondents": row[2],
                "effective_sample": row[3],
                "unweighted_mean": row[4],
                "weighted_mean": row[5],
                "publishable": bool(row[6]),
                "payload": payload,
                "created_at": row[8],
            }
        )
    return estimates


def delete_estimate(user_id: Any, estimate_id: int) -> bool:
    """Remove one saved estimate belonging to this user."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM population_estimates WHERE user_id = ? AND id = ?",
                (str(user_id), int(estimate_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


# ---------------------------------------------------------------------------
# A worked example
# ---------------------------------------------------------------------------


def demo_variables() -> list[dict[str, Any]]:
    """Illustrative population marginals for a mixed urban area."""
    return [
        build_variable(
            "dwelling",
            {"flat": 0.34, "terraced": 0.28, "semi": 0.23, "detached": 0.15},
            label="Dwelling type",
        ),
        build_variable(
            "household_size",
            {"1": 0.30, "2": 0.34, "3+": 0.36},
            label="Household size",
        ),
    ]


def demo_respondents(count: int = 120, seed: int = 20241015) -> list[dict[str, Any]]:
    """A deliberately self-selected sample.

    Flat-dwelling one-person households are heavily over-represented, exactly
    as they are in any consumer sustainability app, and they also have the
    lowest footprints — so the unweighted mean flatters everyone compared
    against it.
    """
    import random

    rng = random.Random(seed)
    dwelling_bias = {"flat": 0.55, "terraced": 0.25, "semi": 0.14, "detached": 0.06}
    size_bias = {"1": 0.46, "2": 0.33, "3+": 0.21}
    base = {"flat": 2100.0, "terraced": 3000.0, "semi": 3900.0, "detached": 5200.0}
    multiplier = {"1": 0.78, "2": 1.0, "3+": 1.35}

    def pick(weights: Mapping[str, float]) -> str:
        draw = rng.random()
        cumulative = 0.0
        for level, share in weights.items():
            cumulative += share
            if draw <= cumulative:
                return level
        return list(weights)[-1]

    respondents = []
    for index in range(int(count)):
        dwelling = pick(dwelling_bias)
        size = pick(size_bias)
        value = max(
            200.0,
            rng.gauss(base[dwelling] * multiplier[size], 600.0),
        )
        respondents.append(
            build_respondent(
                "r%03d" % index, value, dwelling=dwelling, household_size=size
            )
        )
    return respondents
