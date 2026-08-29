"""How much of a process-based footprint was never counted.

This repository computes the same kind of quantity by two opposite methods and
never puts them in the same room.

``src/business/eeio_spend.py`` takes the input-output route. It is complete by
construction - the Leontief inverse sums the whole infinite series of upstream
requirements - and coarse, because a sector average is not this product.

``src/environment/building_materials_lca.py`` and
``src/carbon/product_carbon_footprint.py`` take the process route. Bill of
materials, an emission factor per material, sum. Specific, and incomplete,
because somebody drew a boundary and upstream of it sit the accountant who
invoiced the supplier, the insurance on the shipping, the software licence used
to design the part. Each is small. There is an unbounded number of them.

Neither method is wrong. Their disagreement is measurable and is currently
discarded.

The error is one-directional, which is what makes it worth modelling
--------------------------------------------------------------------
Truncation can only understate. A footprint with an unstated cutoff is not
"approximate" in the ordinary sense that it might be high or low; it is biased
low, and every comparison against a target inherits that bias. The empirical
literature puts the typical omission at twenty to fifty percent of the total.

It does not cancel in comparisons either
-----------------------------------------
A steel beam's supply chain converges quickly. A consultancy's does not.
Comparing a material-intensive option against a service-intensive one on
process data alone systematically favours the service - which is the shape of
a great many recommendations this app makes.

The model, and its one real assumption
----------------------------------------
The upstream chain is treated as tiers with a constant pass-through ratio:
each tier contributes ``r`` times the one before it. Sum the tiers there is
data for; the tail is a geometric series and closes to ``t_n * r / (1 - r)``.

The assumption is that ``r`` is constant. It is not exactly, and the module
does not pretend otherwise: where two or more tiers are supplied, ``r`` is
estimated from that data rather than from a sector default, the individual
tier-to-tier ratios are reported, and their dispersion drives a warning when
the geometric model is a poor fit for the chain in front of it.

Why a flat uplift would be worse than nothing
-----------------------------------------------
A blanket +30% is a guess wearing a decimal point, and it would make the
service-versus-material comparison worse rather than better, because it
applies the same correction to chains that converge at different rates. The
correction has to come from the structure of the specific chain, and it has to
be able to say when it does not know.

Where this connects to code already merged
--------------------------------------------
*   ``src/business/eeio_spend.py`` provides the upper bound. Where the process
    figure exceeds it, that is a finding rather than a number to take the max
    of, and this module reports it as one.
*   ``src/carbon/scope3_screener.py`` screens categories in or out with no
    error bound on what "out" costs. ``screening_loss`` supplies one.
*   ``src/utils/footprint_uncertainty.py`` propagates symmetric uncertainty in
    factors and activity data. Truncation is neither symmetric nor random, so
    it needs its own treatment and belongs beside that module, not inside it.

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


class TruncationError(ValueError):
    """Raised when a correction cannot be supported by the data given."""


#: Sector defaults. ``tier_ratio`` is the central pass-through estimate;
#: ``ratio_low`` and ``ratio_high`` bracket the published range and propagate
#: into the output as a band rather than being averaged into a midpoint.
#: ``io_intensity`` is kg CO2e per unit of currency spent, used only for the
#: upper bound and deliberately coarse.
SECTORS = {
    "manufacturing": {
        "label": "Manufacturing",
        "tier_ratio": 0.42,
        "ratio_low": 0.32,
        "ratio_high": 0.52,
        "io_intensity": 0.30,
        "note": (
            "Converges moderately. Physical inputs dominate the first two "
            "tiers and the tail is mostly services, which is exactly the "
            "part a bill of materials does not have a line for."
        ),
    },
    "construction": {
        "label": "Construction and buildings",
        "tier_ratio": 0.38,
        "ratio_low": 0.28,
        "ratio_high": 0.48,
        "io_intensity": 0.25,
        "note": (
            "Converges fastest of the sectors here, because the mass is "
            "concentrated in a handful of materials with short chains. This "
            "is the sector where process LCA is on firmest ground."
        ),
    },
    "transport": {
        "label": "Transport and logistics",
        "tier_ratio": 0.45,
        "ratio_low": 0.34,
        "ratio_high": 0.56,
        "io_intensity": 0.45,
        "note": (
            "Fuel is easy to count and infrastructure is not. Vehicle "
            "manufacture, terminals and track are routinely outside the "
            "boundary and are not small."
        ),
    },
    "services": {
        "label": "Services and professional",
        "tier_ratio": 0.62,
        "ratio_low": 0.50,
        "ratio_high": 0.74,
        "io_intensity": 0.10,
        "note": (
            "Converges slowly and is where truncation does the most damage. "
            "There is no bill of materials to anchor a boundary to, so the "
            "boundary ends up wherever the analyst stopped looking."
        ),
    },
    "agriculture": {
        "label": "Agriculture and food",
        "tier_ratio": 0.40,
        "ratio_low": 0.30,
        "ratio_high": 0.52,
        "io_intensity": 0.55,
        "note": (
            "On-farm emissions dominate and are usually measured directly, "
            "which keeps the truncated share low even though the absolute "
            "footprint is high."
        ),
    },
    "energy": {
        "label": "Energy supply",
        "tier_ratio": 0.30,
        "ratio_low": 0.20,
        "ratio_high": 0.42,
        "io_intensity": 1.20,
        "note": (
            "Combustion is the overwhelming term and is metered. The "
            "smallest truncated share of any sector here, and the one where "
            "a correction changes least."
        ),
    },
    "ict": {
        "label": "ICT and digital services",
        "tier_ratio": 0.58,
        "ratio_low": 0.46,
        "ratio_high": 0.70,
        "io_intensity": 0.12,
        "note": (
            "Operational electricity is easy and hardware manufacture, "
            "network infrastructure and software development are not. "
            "Behaves much more like services than like manufacturing."
        ),
    },
    "retail": {
        "label": "Retail and wholesale",
        "tier_ratio": 0.55,
        "ratio_low": 0.44,
        "ratio_high": 0.68,
        "io_intensity": 0.15,
        "note": (
            "Almost all of the footprint is upstream of the retailer, so "
            "almost all of it is in whichever tier the analyst stopped at."
        ),
    },
}

#: Bases a process figure can already be on. Correcting an already-hybrid
#: figure would double count, and the module refuses rather than warning.
BASES = {
    "process": "Process-based, bottom-up bill of materials",
    "hybrid": "Already hybrid - process data with an input-output tail",
    "io": "Input-output only",
}

MIN_RATIO = 1e-6
MAX_TIER_COUNT = 40


# ---------------------------------------------------------------------------
# Sector reference
# ---------------------------------------------------------------------------

def _sector(key):
    if key is None:
        raise TruncationError(
            "A correction needs a sector. Without one there is no basis for "
            "estimating how fast the chain converges."
        )
    normalised = str(key).strip().lower()
    if normalised not in SECTORS:
        known = ", ".join(sorted(SECTORS))
        raise TruncationError(
            "Unknown sector '%s'. Known sectors: %s." % (key, known)
        )
    return normalised


def list_sectors():
    """Every sector with its ratio range and the truncation it implies."""
    entries = []
    for key in sorted(SECTORS, key=lambda item: SECTORS[item]["label"]):
        definition = SECTORS[key]
        entries.append({
            "key": key,
            "label": definition["label"],
            "tier_ratio": definition["tier_ratio"],
            "ratio_low": definition["ratio_low"],
            "ratio_high": definition["ratio_high"],
            "io_intensity": definition["io_intensity"],
            "note": definition["note"],
            "truncation_at_two_tiers": truncated_share(
                definition["tier_ratio"], 2
            ),
            "truncation_at_three_tiers": truncated_share(
                definition["tier_ratio"], 3
            ),
        })
    return entries


def get_sector(key):
    """One sector entry, or ``None`` if it is not known."""
    for entry in list_sectors():
        if entry["key"] == key:
            return entry
    return None


def _check_ratio(ratio):
    value = float(ratio)
    if not math.isfinite(value):
        raise TruncationError("A pass-through ratio must be finite.")
    if value <= 0:
        raise TruncationError(
            "A pass-through ratio must be positive. A ratio of zero says the "
            "supply chain has no upstream at all, which is a claim rather "
            "than a boundary."
        )
    if value >= 1:
        raise TruncationError(
            "A pass-through ratio of %.3f does not converge: every tier "
            "would contribute at least as much as the one before it and the "
            "total would be unbounded. That is a modelling error, not a "
            "large answer." % value
        )
    return value


def truncated_share(ratio, tiers_counted):
    """Share of the full chain missed after counting ``tiers_counted`` tiers.

    Tier zero is the direct stage, so counting two tiers means direct plus
    tier one, and the omitted share is ``r ** 2``.
    """
    value = _check_ratio(ratio)
    counted = int(tiers_counted)
    if counted < 1:
        raise TruncationError("At least the direct tier must be counted.")
    return value ** counted


def tiers_to_coverage(ratio, coverage):
    """How many tiers are needed before ``coverage`` of the chain is counted."""
    value = _check_ratio(ratio)
    target = float(coverage)
    if not 0 < target < 1:
        raise TruncationError("Coverage must be strictly between 0 and 1.")
    needed = math.log(1.0 - target) / math.log(value)
    return max(1, int(math.ceil(needed)))


def convergence_profile(ratio):
    """How quickly a chain with this ratio closes, and whether it usefully does."""
    value = _check_ratio(ratio)
    return {
        "ratio": value,
        "tiers_to_90": tiers_to_coverage(value, 0.90),
        "tiers_to_95": tiers_to_coverage(value, 0.95),
        "tiers_to_99": tiers_to_coverage(value, 0.99),
        "series_multiplier": 1.0 / (1.0 - value),
        "slow": value >= 0.5,
    }


# ---------------------------------------------------------------------------
# Building an estimate
# ---------------------------------------------------------------------------

def build_tier(tier, co2e_kg, label=""):
    """One tier of a process inventory. Tier zero is the direct stage."""
    try:
        index = int(tier)
    except (TypeError, ValueError):
        raise TruncationError("Tier index must be a whole number.")
    if index < 0:
        raise TruncationError("Tier indices start at zero.")
    try:
        amount = float(co2e_kg)
    except (TypeError, ValueError):
        raise TruncationError("Tier emissions must be a number.")
    if not math.isfinite(amount):
        raise TruncationError("Tier emissions must be finite.")
    if amount < 0:
        raise TruncationError(
            "A tier cannot emit a negative amount. Removals belong in a "
            "separate inventory, not in a convergence series."
        )
    return {
        "tier": index,
        "co2e_kg": amount,
        "label": str(label).strip() or "Tier %d" % index,
    }


def build_process_estimate(name, sector, tiers, basis="process", spend=None):
    """A process-based figure, broken down by supply chain tier.

    Tier indices must be contiguous from zero. A gap would mean the geometric
    fit is being asked to span a tier nobody looked at, and the resulting
    ratio would be the square root of two tiers' worth of decay reported as
    one tier's.
    """
    if not name or not str(name).strip():
        raise TruncationError("An estimate needs a name.")
    key = _sector(sector)

    basis_key = str(basis).strip().lower()
    if basis_key not in BASES:
        raise TruncationError(
            "Unknown basis '%s'. Known: %s." % (basis, ", ".join(sorted(BASES)))
        )

    entries = [build_tier(item["tier"], item["co2e_kg"], item.get("label", ""))
               for item in (tiers or [])]
    if not entries:
        raise TruncationError("An estimate needs at least the direct tier.")

    entries.sort(key=lambda item: item["tier"])
    indices = [item["tier"] for item in entries]
    if len(set(indices)) != len(indices):
        raise TruncationError("Each tier may appear only once.")
    if indices != list(range(len(indices))):
        raise TruncationError(
            "Tier indices must run contiguously from zero. Got %s. A gap "
            "would make one tier's decay look like two." % indices
        )
    if len(entries) > MAX_TIER_COUNT:
        raise TruncationError(
            "More than %d tiers is not a truncation problem." % MAX_TIER_COUNT
        )

    total = sum(item["co2e_kg"] for item in entries)
    if total <= 0:
        raise TruncationError("A process estimate must have some emissions in it.")

    spend_value = None
    if spend is not None:
        spend_value = float(spend)
        if spend_value < 0:
            raise TruncationError("Spend cannot be negative.")

    return {
        "name": str(name).strip(),
        "sector": key,
        "sector_label": SECTORS[key]["label"],
        "basis": basis_key,
        "tiers": entries,
        "tier_count": len(entries),
        "process_total": total,
        "spend": spend_value,
    }


def observed_ratios(estimate):
    """Tier-to-tier ratios present in the data itself.

    Returns an empty list where fewer than two consecutive positive tiers are
    available, which is the common case and is why the sector default exists.
    """
    ratios = []
    tiers = estimate["tiers"]
    for previous, current in zip(tiers, tiers[1:]):
        if previous["co2e_kg"] <= 0:
            continue
        ratios.append({
            "from_tier": previous["tier"],
            "to_tier": current["tier"],
            "ratio": current["co2e_kg"] / previous["co2e_kg"],
        })
    return ratios


def fitted_ratio(estimate):
    """The pass-through ratio implied by the data, or ``None``.

    Uses the geometric mean, because the series is multiplicative and an
    arithmetic mean of ratios would be pulled upward by a single fat tier.
    """
    ratios = [item["ratio"] for item in observed_ratios(estimate)
              if item["ratio"] > 0]
    if not ratios:
        return None
    log_sum = sum(math.log(value) for value in ratios)
    return math.exp(log_sum / len(ratios))


def ratio_dispersion(estimate):
    """Spread of the observed tier ratios, as a max-over-min factor.

    A large spread means the constant-ratio assumption is a poor description
    of this chain, and the correction should be read as an order of magnitude
    rather than a figure.
    """
    ratios = [item["ratio"] for item in observed_ratios(estimate)
              if item["ratio"] > 0]
    if len(ratios) < 2:
        return None
    return max(ratios) / min(ratios)


# ---------------------------------------------------------------------------
# Correction
# ---------------------------------------------------------------------------

def io_upper_bound(spend, sector):
    """A coarse input-output ceiling from spend, in kg CO2e."""
    key = _sector(sector)
    amount = float(spend)
    if amount < 0:
        raise TruncationError("Spend cannot be negative.")
    return amount * SECTORS[key]["io_intensity"]


def _remainder(last_tier_value, ratio):
    """Closed form of the untruncated tail beyond the last counted tier."""
    return last_tier_value * ratio / (1.0 - ratio)


def correct(estimate, ratio=None, io_bound=None):
    """Estimate what the boundary left out, and say how confident that is.

    The remainder is reported as its own number rather than folded into the
    total, because a corrected figure that cannot be taken apart again is not
    much more useful than an uncorrected one.
    """
    if estimate["basis"] == "hybrid":
        raise TruncationError(
            "This figure is already hybrid - it has an input-output tail "
            "attached. Correcting it again would count the tail twice."
        )
    if estimate["basis"] == "io":
        raise TruncationError(
            "An input-output figure is complete by construction. There is no "
            "truncation to correct; the Leontief inverse already sums the "
            "whole series."
        )

    definition = SECTORS[estimate["sector"]]
    fitted = fitted_ratio(estimate)
    dispersion = ratio_dispersion(estimate)

    if ratio is not None:
        chosen = _check_ratio(ratio)
        source = "supplied"
    elif fitted is not None:
        chosen = _check_ratio(fitted)
        source = "fitted from the tier data"
    else:
        chosen = _check_ratio(definition["tier_ratio"])
        source = "sector default"

    last_tier = estimate["tiers"][-1]["co2e_kg"]
    process_total = estimate["process_total"]

    remainder = _remainder(last_tier, chosen)
    corrected = process_total + remainder

    low_ratio = _check_ratio(min(definition["ratio_low"], chosen))
    high_ratio = _check_ratio(max(definition["ratio_high"], chosen))
    corrected_low = process_total + _remainder(last_tier, low_ratio)
    corrected_high = process_total + _remainder(last_tier, high_ratio)

    warnings = []
    exceeds_io = False
    capped = False
    if io_bound is not None:
        bound = float(io_bound)
        if bound <= 0:
            raise TruncationError("An input-output bound must be positive.")
        if process_total > bound:
            exceeds_io = True
            warnings.append(
                "The process figure alone (%.0f kg) is above the "
                "input-output estimate (%.0f kg). Either this product is "
                "genuinely cleaner than its sector average, or one of the two "
                "models is wrong. Nothing here can tell you which, and taking "
                "the larger of the two would hide the question."
                % (process_total, bound)
            )
        elif corrected > bound:
            capped = True
            warnings.append(
                "The correction overshoots the input-output ceiling and has "
                "been capped at it. The tail this chain implies is larger "
                "than the sector average allows, which usually means the "
                "fitted ratio is too high for the last tier supplied."
            )
            corrected = bound
            remainder = corrected - process_total
            corrected_high = min(corrected_high, bound)

    if dispersion is not None and dispersion > 3.0:
        warnings.append(
            "The observed tier ratios differ by a factor of %.1f, so the "
            "constant-ratio assumption fits this chain poorly. Read the "
            "correction as an order of magnitude." % dispersion
        )
    if estimate["tier_count"] < 2:
        warnings.append(
            "Only the direct tier was supplied, so the ratio is a sector "
            "default rather than anything measured here. This is the least "
            "informative case the module handles."
        )

    profile = convergence_profile(chosen)
    if profile["slow"]:
        warnings.append(
            "At a ratio of %.2f this chain needs %d tiers to reach 95%% "
            "coverage. Process data almost never goes that deep, which is "
            "why the correction is the larger part of the answer here."
            % (chosen, profile["tiers_to_95"])
        )

    coverage = process_total / corrected if corrected > 0 else None

    return {
        "name": estimate["name"],
        "sector": estimate["sector"],
        "sector_label": estimate["sector_label"],
        "process_total": process_total,
        "remainder": remainder,
        "corrected_total": corrected,
        "corrected_low": corrected_low,
        "corrected_high": corrected_high,
        "coverage_ratio": coverage,
        "coverage_low": (
            process_total / corrected_high if corrected_high > 0 else None
        ),
        "coverage_high": (
            process_total / corrected_low if corrected_low > 0 else None
        ),
        "ratio": chosen,
        "ratio_source": source,
        "fitted_ratio": fitted,
        "ratio_dispersion": dispersion,
        "observed_ratios": observed_ratios(estimate),
        "tier_count": estimate["tier_count"],
        "counted_tiers": list(estimate["tiers"]),
        "last_tier_value": last_tier,
        "convergence": profile,
        "io_bound": io_bound,
        "exceeds_io": exceeds_io,
        "capped_at_io": capped,
        "warnings": warnings,
        "uplift_percent": (
            (corrected / process_total - 1.0) * 100.0 if process_total else None
        ),
    }


def modelled_tiers(result, tiers=12):
    """The full series, for a chart that shows where the tail actually goes.

    Counted tiers carry their measured values. Everything beyond the last
    counted tier is modelled from the ratio and flagged as modelled, because
    presenting the two identically would be the original problem again in
    miniature.
    """
    count = int(tiers)
    if count < 1:
        raise TruncationError("A modelled series needs at least one tier.")

    counted = result["counted_tiers"]
    ratio = result["ratio"]
    last = result["last_tier_value"]

    rows = []
    for index in range(count):
        if index < len(counted):
            rows.append({
                "tier": index,
                "co2e_kg": counted[index]["co2e_kg"],
                "label": counted[index]["label"],
                "modelled": False,
            })
        else:
            rows.append({
                "tier": index,
                "co2e_kg": last * (ratio ** (index - len(counted) + 1)),
                "label": "Tier %d (modelled)" % index,
                "modelled": True,
            })
    return rows


def screening_loss(estimate, threshold_share, ratio=None):
    """What a screening threshold costs once truncation is accounted for.

    ``src/carbon/scope3_screener.py`` drops categories below a share of the
    total. That share is a share of an already-truncated total, so the
    threshold is quietly stricter than it looks, and the dropped categories
    were themselves undercounted.
    """
    share = float(threshold_share)
    if not 0 < share < 1:
        raise TruncationError("A screening threshold must be between 0 and 1.")

    corrected = correct(estimate, ratio=ratio)
    apparent = estimate["process_total"] * share
    actual_share = (
        apparent / corrected["corrected_total"]
        if corrected["corrected_total"] > 0 else None
    )
    return {
        "threshold_share": share,
        "apparent_cutoff_kg": apparent,
        "effective_share_of_corrected": actual_share,
        "share_shift": (
            share - actual_share if actual_share is not None else None
        ),
        "corrected_total": corrected["corrected_total"],
        "coverage_ratio": corrected["coverage_ratio"],
        "note": (
            "A %.0f%% threshold on the process total is a cutoff of %.0f kg, "
            "which is %.1f%% of the corrected total. Two effects pull in "
            "opposite directions and neither is negligible: the denominator "
            "is too small, which inflates every category's apparent share and "
            "keeps more of them in; and each category is itself truncated, "
            "which pushes its own value down towards the cutoff. The screen's "
            "real strictness is not the number written on it."
            % (share * 100.0, apparent, (actual_share or 0.0) * 100.0)
        ),
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

def compare_options(estimates, ratios=None):
    """Correct several options and report whether the ranking survived.

    This is the output that matters most. A ranking that holds after
    correction is robust; one that flips was an artefact of two options
    having had their boundaries drawn in different places.
    """
    entries = list(estimates or [])
    if len(entries) < 2:
        raise TruncationError("Comparing needs at least two options.")

    supplied = ratios or {}
    corrected = []
    for estimate in entries:
        corrected.append(correct(estimate, ratio=supplied.get(estimate["name"])))

    process_order = [
        item["name"] for item in
        sorted(corrected, key=lambda row: row["process_total"])
    ]
    corrected_order = [
        item["name"] for item in
        sorted(corrected, key=lambda row: row["corrected_total"])
    ]

    flipped = process_order != corrected_order
    winner_changed = process_order[0] != corrected_order[0]

    sectors = {item["sector"] for item in corrected}
    return {
        "results": corrected,
        "process_order": process_order,
        "corrected_order": corrected_order,
        "ranking_flipped": flipped,
        "winner_changed": winner_changed,
        "cross_sector": len(sectors) > 1,
        "note": (
            "The ranking changed once the boundaries were put on the same "
            "footing. The original ordering was partly an artefact of how "
            "deeply each option had been investigated."
            if flipped else
            "The ranking survives correction, which makes it a conclusion "
            "about the options rather than about how far anyone looked."
        ),
    }


def portfolio_coverage(estimates, ratios=None):
    """Coverage across a set of estimates, weighted by size.

    Reported because a portfolio average hides the case that matters: one
    badly truncated service line inside an otherwise well-characterised set
    of physical products.
    """
    entries = list(estimates or [])
    if not entries:
        raise TruncationError("A portfolio needs at least one estimate.")

    supplied = ratios or {}
    rows = [correct(item, ratio=supplied.get(item["name"])) for item in entries]

    process_total = sum(row["process_total"] for row in rows)
    corrected_total = sum(row["corrected_total"] for row in rows)
    worst = min(rows, key=lambda row: row["coverage_ratio"] or 1.0)

    return {
        "process_total": process_total,
        "corrected_total": corrected_total,
        "missing_kg": corrected_total - process_total,
        "coverage_ratio": (
            process_total / corrected_total if corrected_total > 0 else None
        ),
        "worst_covered": worst["name"],
        "worst_coverage": worst["coverage_ratio"],
        "results": rows,
    }


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

def get_truncation_insights(result):
    """Plain-language findings, most load-bearing first."""
    insights = []
    coverage = result["coverage_ratio"]

    if coverage is not None:
        insights.append({
            "level": "warning" if coverage < 0.8 else "info",
            "title": "The process figure covers about %.0f%% of the chain"
                     % (coverage * 100.0),
            "body": (
                "%.0f kg was counted and roughly %.0f kg was not, giving a "
                "best estimate of %.0f kg. The omission is one-directional: "
                "a boundary can only leave things out."
                % (
                    result["process_total"],
                    result["remainder"],
                    result["corrected_total"],
                )
            ),
        })

    insights.append({
        "level": "info",
        "title": "The ratio came from the %s" % result["ratio_source"],
        "body": (
            "A pass-through of %.2f per tier. At that rate the chain needs "
            "%d tiers to reach 95%% coverage and %d to reach 99%%, against "
            "the %d tier%s actually supplied."
            % (
                result["ratio"],
                result["convergence"]["tiers_to_95"],
                result["convergence"]["tiers_to_99"],
                result["tier_count"],
                "" if result["tier_count"] == 1 else "s",
            )
        ),
    })

    if result["exceeds_io"]:
        insights.append({
            "level": "warning",
            "title": "The process figure is above the input-output estimate",
            "body": (
                "That is either a genuinely clean product or a broken model, "
                "and no arithmetic here distinguishes them. It is reported "
                "rather than resolved, because taking the larger of the two "
                "would make the question disappear."
            ),
        })

    if result["ratio_dispersion"] and result["ratio_dispersion"] > 3.0:
        insights.append({
            "level": "warning",
            "title": "The tier ratios are not constant",
            "body": (
                "They span a factor of %.1f, so the geometric model is a poor "
                "fit for this chain. The correction is still directionally "
                "right - the omission is always positive - but the magnitude "
                "should be read loosely."
                % result["ratio_dispersion"]
            ),
        })

    spread = None
    if result["corrected_low"] > 0:
        spread = result["corrected_high"] / result["corrected_low"]
    if spread and spread > 1.3:
        insights.append({
            "level": "info",
            "title": "The correction itself has a wide range",
            "body": (
                "Between %.0f and %.0f kg depending on where in the published "
                "range the sector's pass-through actually sits. The band is "
                "reported instead of a midpoint because the midpoint would "
                "imply a precision the literature does not have."
                % (result["corrected_low"], result["corrected_high"])
            ),
        })

    return insights


def coverage_grade(result):
    """A coarse label for how complete an estimate is."""
    coverage = result["coverage_ratio"]
    if coverage is None:
        return "unknown"
    if coverage >= 0.90:
        return "well characterised"
    if coverage >= 0.75:
        return "usable with a stated correction"
    if coverage >= 0.55:
        return "substantially incomplete"
    return "dominated by what was not counted"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS truncation_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            sector TEXT NOT NULL,
            payload TEXT NOT NULL,
            process_total REAL NOT NULL,
            corrected_total REAL NOT NULL,
            coverage_ratio REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_truncation_corrections_user
        ON truncation_corrections (user_id)
        """
    )


def save_correction(user_id, result):
    """Persist a correction and return its row id."""
    if not user_id:
        raise TruncationError("A saved correction needs a user to belong to.")

    payload = json.dumps({
        "ratio": result["ratio"],
        "ratio_source": result["ratio_source"],
        "remainder": result["remainder"],
        "corrected_low": result["corrected_low"],
        "corrected_high": result["corrected_high"],
        "tier_count": result["tier_count"],
        "warnings": result["warnings"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO truncation_corrections
                (user_id, name, sector, payload, process_total,
                 corrected_total, coverage_ratio)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), result["name"], result["sector"], payload,
                float(result["process_total"]),
                float(result["corrected_total"]),
                result["coverage_ratio"],
            ),
        )
        return int(cursor.lastrowid)


def get_corrections(user_id, limit=25):
    """Saved corrections for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, sector, payload, process_total,
                       corrected_total, coverage_ratio, created_at
                FROM truncation_corrections
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved truncation corrections")
        return []

    saved = []
    for row in rows:
        try:
            payload = json.loads(row[3])
        except (TypeError, ValueError):
            payload = {}
        saved.append({
            "id": row[0],
            "name": row[1],
            "sector": row[2],
            "payload": payload,
            "process_total": row[4],
            "corrected_total": row[5],
            "coverage_ratio": row[6],
            "created_at": row[7],
        })
    return saved


def delete_correction(user_id, correction_id):
    """Delete one saved correction. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM truncation_corrections WHERE id = ? AND user_id = ?",
                (correction_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete truncation correction")
        return False


def list_bases():
    """The bases a figure can be on, and what each means for correction."""
    return [{"key": key, "label": label} for key, label in sorted(BASES.items())]
