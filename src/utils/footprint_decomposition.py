"""Why a footprint changed, which this app has never been able to say.

The app can tell a user their footprint went from 6,400 kg to 5,700 kg.
``src.utils.sustainability_trends.py``, ``pages/Assessment_History.py`` and
``src.carbon.carbon_footprint_replay.py`` all present that delta. None of them
can say what produced it, and the difference between the available explanations
is the difference between useful feedback and flattery.

The app currently credits users for the grid's work
-----------------------------------------------------
Grid intensity in most of Europe has been falling several percent a year. A
user who changed nothing sees their electricity footprint drop, and
``src.carbon.carbon_benchmarking.py`` and the streak modules congratulate them
for it. That is the most common way a personal carbon tool misleads people, and
this repository does it today. Separating what the user did from what happened
to them is the reason this module exists.

Doing less and doing better are not the same achievement
---------------------------------------------------------
A footprint that fell because someone lost their job is not a footprint that
fell because they insulated a loft. ``src.lifestyle.lifestyle_optimizer.py``
treats both as progress. Only one survives the user's circumstances improving.

The naive attribution does not add up, and the remainder is not innocent
-------------------------------------------------------------------------
Vary one factor, hold the others, subtract: that leaves an interaction residual
that grows with the size of the change, so it is largest exactly when the user
most wants an answer. Reporting four effects and an unexplained remainder
invites the user to assume the remainder was theirs.

The Log-Mean Divisia Index is used here for one specific property: it is
*perfectly decomposing*. The effects sum to the observed change with no
residual, by construction rather than by luck. That is a testable claim and
there are tests pinning it.

Categories that appear and disappear are most of the data, not an edge case
----------------------------------------------------------------------------
The log-mean function is undefined when a term is zero, and in personal data
terms are zero constantly - someone buys their first EV, someone stops flying.
This module uses the analytical-limit treatment (Ang and Liu, 2007): zeros are
replaced by a vanishingly small positive value, under which a newly-appearing
category's emissions land predominantly in the structure effect. That is also
the intuitively right answer, because a category appearing is a change in the
composition of what a person does. The convergence towards that limit is
logarithmic in the substituted value, so the residual attributed to the other
effects shrinks slowly and never quite reaches zero; additivity, which is the
property that matters, holds exactly regardless.

What this module does not claim
---------------------------------
LMDI attributes, it does not establish causation, and the effect labels mean
only as much as the category split fed into them. Decomposing a footprint split
into "good things" and "bad things" produces arithmetic that is perfectly
additive and completely uninformative. The module says so on the page as well
as here.

Where this connects to code already merged
--------------------------------------------
*   ``src.utils.weather_normalised_energy.py`` already removes one confounder
    for one domain. This generalises that treatment across every category the
    app tracks.
*   ``src.carbon.ghg_inventory.py`` tracks against a base year and
    ``src.carbon.emissions_gap_analyzer.py`` measures distance to a target.
    Both consume a delta whose composition was previously unknown.
*   ``src.carbon.marginal_emissions.py`` explains why the emission factor moves.
    This measures how much of the user's change that movement accounts for.

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


class DecompositionError(ValueError):
    """Raised when a decomposition was asked for something it cannot answer."""


# ---------------------------------------------------------------------------
# The analytical-limit constant
#
# Ang and Liu (2007) recommend substituting a small positive value for zero
# terms and report that results are stable for substitutions between 1e-10 and
# 1e-20. The bottom of that band is used here because the attribution of an
# appearing category converges towards its limit only logarithmically in this
# value, and the smaller substitution gets visibly closer. It is deliberately
# not exposed as a tuning knob on the page: a user who changes it is not making
# a modelling choice, they are making a numerical error.
# ---------------------------------------------------------------------------
ANALYTICAL_LIMIT = 1e-20

# Below this relative difference the closed form for the logarithmic mean loses
# precision to cancellation and the series expansion is used instead.
SERIES_THRESHOLD = 1e-4


# ---------------------------------------------------------------------------
# Effects
#
# The split between the first three and the fourth is the substance of the
# module. Activity, structure and intensity are things a person did. The
# emission factor effect is something that happened to them.
# ---------------------------------------------------------------------------
EFFECTS = {
    "activity": {
        "label": "Activity",
        "short": "how much",
        "attributable": True,
        "note": "The scale of what the user did - total distance, total "
                "consumption, total spend. A reduction here is real, but it "
                "is the effect most likely to reflect circumstances rather "
                "than intent: illness, unemployment and a house move all show "
                "up here and none of them is an achievement.",
    },
    "structure": {
        "label": "Structure",
        "short": "what mix",
        "attributable": True,
        "note": "The composition of the activity at constant total - rail "
                "instead of road, legumes instead of beef. This is where a "
                "durable choice usually appears, and it is invisible in a net "
                "figure because the total need not move at all.",
    },
    "intensity": {
        "label": "Intensity",
        "short": "how efficiently",
        "attributable": True,
        "note": "Energy or resource used per unit of activity. Insulation, a "
                "more efficient vehicle, a lower wash temperature. Usually "
                "the effect a user has worked hardest for.",
    },
    "factor": {
        "label": "Emission factor",
        "short": "how clean the supply was",
        "attributable": False,
        "note": "Emissions per unit of energy supplied. Grid decarbonisation "
                "lives here. It is a genuine reduction in the world and it is "
                "not the user's doing, and reporting it as theirs is the "
                "specific error this module exists to prevent.",
    },
}

ATTRIBUTABLE_EFFECTS = tuple(
    key for key, meta in EFFECTS.items() if meta["attributable"]
)
EXOGENOUS_EFFECTS = tuple(
    key for key, meta in EFFECTS.items() if not meta["attributable"]
)


DECOMPOSITION_MODES = {
    "four_factor": {
        "label": "Four factor (activity, structure, intensity, factor)",
        "effects": ("activity", "structure", "intensity", "factor"),
        "note": "Requires an energy or throughput figure per category. Only "
                "this mode can separate what the user did from what the grid "
                "did, which is the reason to collect the extra column.",
    },
    "three_factor": {
        "label": "Three factor (activity, structure, intensity)",
        "effects": ("activity", "structure", "intensity"),
        "note": "Used when no energy figure is available. Intensity then "
                "carries emissions per unit of activity, which merges genuine "
                "efficiency gains with supply-side decarbonisation. The merge "
                "is stated wherever a three-factor result is reported, "
                "because a reader who assumes otherwise will over-credit "
                "themselves.",
    },
}


# ---------------------------------------------------------------------------
# Numerics
# ---------------------------------------------------------------------------
def logarithmic_mean(first, second):
    """The logarithmic mean L(a, b) = (a - b) / (ln a - ln b).

    This is the weight function that makes LMDI perfectly decomposing. Two
    branches matter and both are exercised by real data:

    *   ``a == b`` exactly, where the closed form is 0/0 and the limit is a;
    *   ``a`` very close to ``b``, where the closed form loses most of its
        significant figures to cancellation in both numerator and denominator.

    The second branch uses ``L = m / (1 + r^2/3 + r^4/5 + ...)`` with
    ``m = (a + b) / 2`` and ``r = (a - b) / (a + b)``, which follows from
    ``L = m * r / atanh(r)`` and is accurate to machine precision in the region
    where the direct form is not.
    """
    a = float(first)
    b = float(second)
    if a <= 0.0 or b <= 0.0:
        raise DecompositionError(
            "The logarithmic mean is only defined for positive values. Zero "
            "terms are handled by the analytical-limit substitution before "
            "they reach this function."
        )
    if a == b:
        return a

    total = a + b
    ratio = (a - b) / total
    if abs(ratio) < SERIES_THRESHOLD:
        r2 = ratio * ratio
        correction = 1.0 + r2 / 3.0 + (r2 * r2) / 5.0 + (r2 * r2 * r2) / 7.0
        return (total / 2.0) / correction

    return (a - b) / (math.log(a) - math.log(b))


def _positive(value, name):
    """Coerce to float and substitute the analytical limit for zero."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise DecompositionError(f"{name} must be a number, got {value!r}.")
    if math.isnan(number) or math.isinf(number):
        raise DecompositionError(f"{name} must be finite, got {value!r}.")
    if number < 0.0:
        raise DecompositionError(
            f"{name} cannot be negative. A negative emission belongs in a "
            f"removals inventory, not in a decomposition of gross emissions - "
            f"see src.carbon.permanence_accounting.py."
        )
    if number == 0.0:
        return ANALYTICAL_LIMIT
    return number


# ---------------------------------------------------------------------------
# Periods
# ---------------------------------------------------------------------------
def build_period(label, categories, activity_unit="activity units",
                 energy_unit="kWh"):
    """Assemble and validate one period of a decomposition.

    ``categories`` maps a category key to a mapping with ``activity``,
    ``emissions`` and optionally ``energy``.

    The activity unit is required and is checked for consistency across
    periods, because the structure effect is a share of a total activity and a
    total across incommensurable units is not a quantity. Summing kilometres
    and kilowatt-hours produces a number that decomposes perfectly and means
    nothing, which is the most likely way to misuse this module.
    """
    if not label or not str(label).strip():
        raise DecompositionError("A period needs a label.")
    if not isinstance(categories, dict) or not categories:
        raise DecompositionError("A period needs at least one category.")

    cleaned = {}
    saw_energy = False
    saw_missing_energy = False

    for key, row in categories.items():
        if not isinstance(row, dict):
            raise DecompositionError(
                f"Category {key!r} must be a mapping with activity and "
                f"emissions."
            )
        if "activity" not in row or "emissions" not in row:
            raise DecompositionError(
                f"Category {key!r} needs both 'activity' and 'emissions'."
            )

        activity = float(row["activity"])
        emissions = float(row["emissions"])
        if activity < 0 or emissions < 0:
            raise DecompositionError(
                f"Category {key!r} has a negative quantity."
            )

        entry = {
            "activity": activity,
            "emissions": emissions,
            "label": str(row.get("label") or key.replace("_", " ").title()),
        }

        energy = row.get("energy")
        if energy is None:
            saw_missing_energy = True
        else:
            energy = float(energy)
            if energy < 0:
                raise DecompositionError(
                    f"Category {key!r} has negative energy."
                )
            entry["energy"] = energy
            saw_energy = True

        cleaned[str(key)] = entry

    if saw_energy and saw_missing_energy:
        raise DecompositionError(
            "Some categories carry an energy figure and some do not. A "
            "decomposition cannot mix the two: the factor effect would be "
            "computed for part of the footprint and folded into intensity for "
            "the rest, and the two subtotals would no longer mean the same "
            "thing. Supply energy for every category or for none."
        )

    return {
        "label": str(label).strip(),
        "categories": cleaned,
        "activity_unit": str(activity_unit),
        "energy_unit": str(energy_unit),
        "has_energy": saw_energy,
        "total_emissions": round(
            sum(row["emissions"] for row in cleaned.values()), 6
        ),
        "total_activity": round(
            sum(row["activity"] for row in cleaned.values()), 6
        ),
    }


def _mode_for(before, after):
    if before["activity_unit"] != after["activity_unit"]:
        raise DecompositionError(
            f"The two periods declare different activity units "
            f"({before['activity_unit']!r} and {after['activity_unit']!r}). "
            f"The activity effect would be measuring a change of unit rather "
            f"than a change of behaviour."
        )
    if before["has_energy"] != after["has_energy"]:
        raise DecompositionError(
            "One period carries energy figures and the other does not. The "
            "two would be decomposed into different effect sets and could not "
            "be compared."
        )
    return "four_factor" if before["has_energy"] else "three_factor"


def _factors(period, keys, mode):
    """Per-category factor values, with zeros already substituted."""
    total_activity = _positive(
        sum(period["categories"].get(k, {}).get("activity", 0.0)
            for k in keys),
        "Total activity",
    )

    factors = {}
    for key in keys:
        row = period["categories"].get(key, {})
        activity = _positive(row.get("activity", 0.0), f"{key} activity")
        emissions = _positive(row.get("emissions", 0.0), f"{key} emissions")
        if mode == "four_factor":
            energy = _positive(row.get("energy", 0.0), f"{key} energy")
        else:
            energy = activity

        values = {
            "activity": total_activity,
            "structure": activity / total_activity,
            "intensity": energy / activity,
        }
        if mode == "four_factor":
            values["factor"] = emissions / energy
        else:
            values["intensity"] = emissions / activity
        values["emissions"] = emissions
        factors[key] = values

    return factors


# ---------------------------------------------------------------------------
# Additive decomposition
# ---------------------------------------------------------------------------
def decompose(before, after):
    """Additive LMDI-I decomposition of the change between two periods.

    Returns per-effect totals, a per-category breakdown, and the residual. The
    residual is reported rather than discarded: it should be zero to within
    floating point and the analytical-limit substitution, and if it ever is not
    then the result is wrong and the page should say so instead of drawing a
    tidy chart.
    """
    mode = _mode_for(before, after)
    effect_keys = DECOMPOSITION_MODES[mode]["effects"]

    keys = sorted(set(before["categories"]) | set(after["categories"]))
    if not keys:
        raise DecompositionError("There are no categories to decompose.")

    base = _factors(before, keys, mode)
    target = _factors(after, keys, mode)

    totals = {key: 0.0 for key in effect_keys}
    rows = []

    for key in keys:
        weight = logarithmic_mean(
            target[key]["emissions"], base[key]["emissions"]
        )
        contributions = {}
        for effect in effect_keys:
            ratio = math.log(target[key][effect] / base[key][effect])
            value = weight * ratio
            contributions[effect] = value
            totals[effect] += value

        before_row = before["categories"].get(key, {})
        after_row = after["categories"].get(key, {})
        rows.append({
            "category": key,
            "label": (after_row.get("label") or before_row.get("label")
                      or key.replace("_", " ").title()),
            "before_emissions": round(before_row.get("emissions", 0.0), 3),
            "after_emissions": round(after_row.get("emissions", 0.0), 3),
            "change": round(
                after_row.get("emissions", 0.0)
                - before_row.get("emissions", 0.0), 3
            ),
            "appeared": key not in before["categories"]
            or before_row.get("emissions", 0.0) == 0.0,
            "disappeared": key not in after["categories"]
            or after_row.get("emissions", 0.0) == 0.0,
            "effects": {e: round(v, 6) for e, v in contributions.items()},
        })

    observed = after["total_emissions"] - before["total_emissions"]
    explained = sum(totals.values())
    residual = observed - explained

    attributable = sum(
        totals[e] for e in effect_keys if EFFECTS[e]["attributable"]
    )
    exogenous = sum(
        totals[e] for e in effect_keys if not EFFECTS[e]["attributable"]
    )

    rows.sort(key=lambda r: abs(r["change"]), reverse=True)

    return {
        "mode": mode,
        "before_label": before["label"],
        "after_label": after["label"],
        "before_total": before["total_emissions"],
        "after_total": after["total_emissions"],
        "observed_change": round(observed, 3),
        "explained_change": round(explained, 3),
        "residual": round(residual, 9),
        "perfectly_decomposed": abs(residual) < 1e-6,
        "effects": {e: round(totals[e], 3) for e in effect_keys},
        "effect_keys": list(effect_keys),
        "attributable_change": round(attributable, 3),
        "exogenous_change": round(exogenous, 3),
        "attributable_share": (
            round(abs(attributable) / (abs(attributable) + abs(exogenous)), 4)
            if (abs(attributable) + abs(exogenous)) > 0 else 0.0
        ),
        "categories": rows,
        "activity_unit": before["activity_unit"],
    }


# ---------------------------------------------------------------------------
# Multiplicative decomposition
# ---------------------------------------------------------------------------
def decompose_multiplicative(before, after):
    """The same decomposition in ratio form, for users who think in percent.

    The product of the effect indices reproduces the total ratio, which is the
    multiplicative counterpart of the additive module's zero residual and is
    tested the same way.
    """
    mode = _mode_for(before, after)
    effect_keys = DECOMPOSITION_MODES[mode]["effects"]
    keys = sorted(set(before["categories"]) | set(after["categories"]))

    base = _factors(before, keys, mode)
    target = _factors(after, keys, mode)

    total_weight = logarithmic_mean(
        _positive(after["total_emissions"], "Later total"),
        _positive(before["total_emissions"], "Earlier total"),
    )

    indices = {}
    for effect in effect_keys:
        exponent = 0.0
        for key in keys:
            weight = logarithmic_mean(
                target[key]["emissions"], base[key]["emissions"]
            )
            ratio = math.log(target[key][effect] / base[key][effect])
            exponent += (weight / total_weight) * ratio
        indices[effect] = math.exp(exponent)

    product = 1.0
    for value in indices.values():
        product *= value

    total_ratio = (
        _positive(after["total_emissions"], "Later total")
        / _positive(before["total_emissions"], "Earlier total")
    )

    return {
        "mode": mode,
        "indices": {e: round(v, 6) for e, v in indices.items()},
        "percent_change": {
            e: round((v - 1.0) * 100.0, 2) for e, v in indices.items()
        },
        "product": round(product, 6),
        "total_ratio": round(total_ratio, 6),
        "closes": abs(product - total_ratio) < 1e-6,
    }


# ---------------------------------------------------------------------------
# Chained decomposition over a history
# ---------------------------------------------------------------------------
def decompose_chain(periods):
    """Chain a decomposition period by period across a history.

    The chained totals are compared against a single decomposition of the first
    period against the last. The two need not agree - LMDI is path dependent,
    and a user who went up and then down did something the endpoints cannot
    show. The gap is reported rather than hidden, because it is itself a
    finding: a large gap means the intermediate route mattered.
    """
    if not isinstance(periods, (list, tuple)) or len(periods) < 2:
        raise DecompositionError(
            "Chaining needs at least two periods."
        )

    steps = []
    chained = {}
    for earlier, later in zip(periods, periods[1:]):
        result = decompose(earlier, later)
        steps.append(result)
        for effect, value in result["effects"].items():
            chained[effect] = chained.get(effect, 0.0) + value

    direct = decompose(periods[0], periods[-1])
    path_gap = {
        effect: round(chained.get(effect, 0.0) - direct["effects"].get(effect, 0.0), 3)
        for effect in direct["effects"]
    }
    largest = max(
        (abs(v) for v in path_gap.values()), default=0.0
    )
    span = abs(direct["observed_change"]) or 1.0

    return {
        "steps": steps,
        "chained_effects": {e: round(v, 3) for e, v in chained.items()},
        "direct_effects": direct["effects"],
        "path_dependence": path_gap,
        "path_dependence_share": round(largest / span, 4),
        "path_dependent": largest / span > 0.05,
        "observed_change": direct["observed_change"],
        "first_label": periods[0]["label"],
        "last_label": periods[-1]["label"],
    }


# ---------------------------------------------------------------------------
# Derived views
# ---------------------------------------------------------------------------
def counterfactual_footprint(result):
    """What the later footprint would have been had the supply not changed.

    Removing the exogenous effect gives the number the user actually moved. In
    a four-factor decomposition against a decarbonising grid this is routinely
    higher than the reported footprint, and the difference is the credit the
    app has been handing out for free.
    """
    if result["mode"] != "four_factor":
        raise DecompositionError(
            "A counterfactual needs the factor effect separated, which only "
            "the four-factor mode does. In three-factor mode supply-side "
            "decarbonisation is folded into intensity and cannot be removed "
            "from it."
        )

    exogenous = result["exogenous_change"]
    without = result["after_total"] - exogenous
    return {
        "reported_after": result["after_total"],
        "without_supply_change": round(without, 3),
        "supply_credit": round(-exogenous, 3),
        "supply_credit_share": (
            round(abs(exogenous) / abs(result["observed_change"]), 4)
            if result["observed_change"] else 0.0
        ),
        "own_change": round(result["attributable_change"], 3),
        "own_change_percent": (
            round(result["attributable_change"] / result["before_total"] * 100.0, 2)
            if result["before_total"] else 0.0
        ),
    }


def waterfall(result):
    """Ordered rows for a waterfall chart, opening and closing on the totals."""
    rows = [{
        "label": result["before_label"],
        "kind": "total",
        "value": result["before_total"],
        "running": result["before_total"],
    }]
    running = result["before_total"]
    for effect in result["effect_keys"]:
        value = result["effects"][effect]
        running += value
        rows.append({
            "label": EFFECTS[effect]["label"],
            "kind": "effect",
            "effect": effect,
            "attributable": EFFECTS[effect]["attributable"],
            "value": round(value, 3),
            "running": round(running, 3),
        })
    rows.append({
        "label": result["after_label"],
        "kind": "total",
        "value": result["after_total"],
        "running": result["after_total"],
    })
    return rows


def category_effect_table(result, effect):
    """Per-category contributions to one effect, largest magnitude first."""
    if effect not in result["effects"]:
        raise DecompositionError(
            f"{effect!r} is not one of the effects in this decomposition "
            f"({', '.join(result['effect_keys'])})."
        )
    rows = [
        {
            "category": row["category"],
            "label": row["label"],
            "value": row["effects"][effect],
            "share": (
                round(row["effects"][effect] / result["effects"][effect], 4)
                if result["effects"][effect] else 0.0
            ),
        }
        for row in result["categories"]
    ]
    rows.sort(key=lambda r: abs(r["value"]), reverse=True)
    return rows


def dominant_effect(result):
    """The effect with the largest magnitude, and whether it was the user's."""
    effect = max(
        result["effects"], key=lambda e: abs(result["effects"][e])
    )
    return {
        "effect": effect,
        "label": EFFECTS[effect]["label"],
        "value": result["effects"][effect],
        "attributable": EFFECTS[effect]["attributable"],
        "note": EFFECTS[effect]["note"],
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_decomposition_insights(result):
    """Plain-language findings, ordered by how much they should change a view."""
    insights = []

    if not result["perfectly_decomposed"]:
        insights.append(
            f"This decomposition did not close: {result['residual']:.6f} kg "
            f"CO2e is unexplained. That should not happen and the numbers "
            f"below should not be trusted until it is fixed."
        )
        return insights

    change = result["observed_change"]
    direction = "fell" if change < 0 else "rose"
    insights.append(
        f"The footprint {direction} by {abs(change):,.0f} kg CO2e between "
        f"{result['before_label']} and {result['after_label']}, and all of it "
        f"is accounted for below - there is no residual to read anything into."
    )

    if result["mode"] == "four_factor":
        exogenous = result["exogenous_change"]
        attributable = result["attributable_change"]
        if exogenous < 0 and change < 0:
            share = abs(exogenous) / abs(change) if change else 0.0
            insights.append(
                f"{abs(exogenous):,.0f} kg of the reduction came from the "
                f"emission factor of the energy supplied - "
                f"{share * 100:.0f}% of the total. That is a real reduction "
                f"in the world and it is not this user's doing."
            )
            if share > 0.5:
                insights.append(
                    "Most of this improvement was the grid, not the "
                    "household. Any congratulation for the headline figure "
                    "would be misplaced."
                )
        if attributable > 0 and change < 0:
            insights.append(
                f"What the household actually did added {attributable:,.0f} kg "
                f"CO2e. The footprint fell anyway because the supply got "
                f"cleaner faster than behaviour got worse, which is not the "
                f"same thing as progress."
            )
    else:
        insights.append(
            "This is a three-factor decomposition, so the intensity effect "
            "merges genuine efficiency gains with supply-side decarbonisation. "
            "Supply an energy figure per category to separate them."
        )

    top = dominant_effect(result)
    insights.append(
        f"The largest single effect is {top['label'].lower()} at "
        f"{top['value']:+,.0f} kg CO2e. {top['note']}"
    )

    structure = result["effects"].get("structure", 0.0)
    activity = result["effects"].get("activity", 0.0)
    if structure < 0 and activity >= 0:
        insights.append(
            f"The reduction is compositional rather than a matter of doing "
            f"less: structure contributed {structure:,.0f} kg while activity "
            f"was {activity:+,.0f} kg. Changes of this shape tend to survive "
            f"a return to normal circumstances."
        )
    elif activity < 0 and structure >= 0 and abs(activity) > abs(structure):
        insights.append(
            f"The reduction came mostly from doing less ({activity:,.0f} kg "
            f"of activity effect), not from doing differently. If the drop in "
            f"activity was involuntary, this will reverse."
        )

    appeared = [r for r in result["categories"] if r["appeared"]
                and r["after_emissions"] > 0]
    if appeared:
        names = ", ".join(r["label"].lower() for r in appeared[:3])
        insights.append(
            f"New in this period: {names}. A category that appears is "
            f"attributed predominantly to the structure effect, which is the "
            f"analytical limit of the method and not a rounding choice."
        )

    gone = [r for r in result["categories"] if r["disappeared"]
            and r["before_emissions"] > 0]
    if gone:
        names = ", ".join(r["label"].lower() for r in gone[:3])
        insights.append(
            f"Gone in this period: {names}. Worth checking whether the "
            f"activity stopped or the logging did - the arithmetic cannot "
            f"tell those apart and will treat both as a reduction."
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
        CREATE TABLE IF NOT EXISTS footprint_decompositions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            observed_change REAL NOT NULL,
            attributable_change REAL NOT NULL,
            exogenous_change REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_footprint_decompositions_user
        ON footprint_decompositions (user_id)
        """
    )


def save_decomposition(user_id, name, result):
    """Persist a decomposition and return its row id."""
    if not user_id:
        raise DecompositionError("A decomposition needs a user to belong to.")
    if not name or not str(name).strip():
        raise DecompositionError("A decomposition needs a name.")

    payload = json.dumps({
        "mode": result["mode"],
        "before_label": result["before_label"],
        "after_label": result["after_label"],
        "before_total": result["before_total"],
        "after_total": result["after_total"],
        "effects": result["effects"],
        "effect_keys": result["effect_keys"],
        "residual": result["residual"],
        "activity_unit": result["activity_unit"],
        "categories": result["categories"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO footprint_decompositions
                (user_id, name, payload, observed_change,
                 attributable_change, exogenous_change)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), str(name).strip(), payload,
                float(result["observed_change"]),
                float(result["attributable_change"]),
                float(result["exogenous_change"]),
            ),
        )
        return int(cursor.lastrowid)


def get_decompositions(user_id, limit=25):
    """Saved decompositions for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, observed_change,
                       attributable_change, exogenous_change, created_at
                FROM footprint_decompositions
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved decompositions")
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
            "observed_change": row[3],
            "attributable_change": row[4],
            "exogenous_change": row[5],
            "created_at": row[6],
        })
    return saved


def delete_decomposition(user_id, decomposition_id):
    """Delete one saved decomposition. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM footprint_decompositions "
                "WHERE id = ? AND user_id = ?",
                (decomposition_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception(
            "Could not delete decomposition %s", decomposition_id
        )
        return False


# ---------------------------------------------------------------------------
# Small accessors used by the page
# ---------------------------------------------------------------------------
def list_effects():
    return list(EFFECTS)


def get_effect(key):
    if key not in EFFECTS:
        raise DecompositionError(f"{key!r} is not a known effect.")
    return dict(EFFECTS[key])


def list_modes():
    return list(DECOMPOSITION_MODES)


def get_mode(key):
    if key not in DECOMPOSITION_MODES:
        raise DecompositionError(f"{key!r} is not a known decomposition mode.")
    return dict(DECOMPOSITION_MODES[key])
