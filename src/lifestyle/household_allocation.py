"""Whose footprint it is, which this app answers by dividing by headcount.

``src.lifestyle.household.py`` collects household size, and every per-person
figure in this app is a household total divided by it.
``src.carbon.carbon_benchmarking.py`` compares that figure against per-capita
averages and ``src.carbon.carbon_budget_equity.py`` allocates a fair share on
the same basis.

Equal division is wrong, and it is wrong in a direction that consistently
penalises people who live in small households. One occupant heats a whole
dwelling, runs a fridge and boils a kettle for one. Four people share all
three. Household footprint does not scale linearly with occupancy, and
dividing as though it does makes a person living alone look profligate and a
member of a large household look virtuous, when most of the difference is
arithmetic.

The benchmark comparison is unfair by construction
----------------------------------------------------
Someone living alone is measured against a national per-capita average
dominated by multi-person households and told they are doing badly at
something they cannot change without acquiring housemates. That is not a
finding, it is a division.

An equity module that penalises single occupancy is not an equity module
-------------------------------------------------------------------------
``src.carbon.carbon_budget_equity.py`` is one of the more careful things in
this repository and it divides by headcount. Single occupancy correlates with
age, bereavement and low income, so a per-capita allocation redistributes away
from exactly the households an equity framing exists to protect.

Sharing is not uniform across categories, and one scale for all of them is crude
---------------------------------------------------------------------------------
Heating is close to a pure household public good - a second occupant adds
almost nothing. Food is close to purely private. Applying a single equivalence
scale to both gets both wrong, in opposite directions. Each category here
carries its own sharing elasticity with a note saying why.

Consumption, benefit and control are three different questions
----------------------------------------------------------------
A child consumes some heating, benefits from all of it, and controls none of
it. Those three attributions genuinely disagree, and silently picking one is
how this feature would go wrong. All three are computed. Reduction advice
should be routed by control and benchmarking by consumption, and the module
says so rather than leaving it implied.

Double counting between people is not caught anywhere
-------------------------------------------------------
Two people in a car both log the trip. ``src.utils.boundary_reconciliation.py``
catches double counting between modules; nothing catches it between members of
a household, and the sum of individual footprints is inflated by exactly the
shared portion.

Where this connects to code already merged
--------------------------------------------
*   ``src.lifestyle.household.py`` already collects size and tenure. Nothing
    consumes them as anything but a divisor.
*   ``src.carbon.carbon_budget_equity.py`` and
    ``src.carbon.carbon_benchmarking.py`` both inherit the per-capita error.
*   ``src.utils.boundary_reconciliation.py`` - same class of problem, between
    modules rather than between people.
*   ``src.lifestyle.household_competitions.py`` compares households of
    different composition, which is currently not a meaningful comparison.

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


class AllocationError(ValueError):
    """Raised when an allocation was asked for something incoherent."""


# The age at which the equivalence scales stop treating a person as a child.
# Fourteen is the convention in both OECD scales and is used here for the same
# reason: it is where consumption patterns converge on adult ones, not where
# anybody becomes an adult.
CHILD_AGE_THRESHOLD = 14

FULL_YEAR_DAYS = 365.0


# ---------------------------------------------------------------------------
# Equivalence scales
#
# The choice between these is normative, not technical. It changes results
# materially and the module offers it rather than burying one option in a
# constant, because a household that would be judged differently under a
# different scale is entitled to know that.
# ---------------------------------------------------------------------------
EQUIVALENCE_SCALES = {
    "oecd_modified": {
        "label": "OECD-modified (1 / 0.5 / 0.3)",
        "first_adult": 1.0,
        "other_adult": 0.5,
        "child": 0.3,
        "note": "The current standard for European income statistics. Assumes "
                "substantial economies of scale. The default here because it "
                "is the most widely used, not because it is the most correct.",
    },
    "oecd_original": {
        "label": "OECD original (1 / 0.7 / 0.5)",
        "first_adult": 1.0,
        "other_adult": 0.7,
        "child": 0.5,
        "note": "Assumes weaker economies of scale, so it penalises large "
                "households less than the modified version. Preferred where "
                "the shared component is genuinely small.",
    },
    "square_root": {
        "label": "Square root of household size",
        "first_adult": None,
        "other_adult": None,
        "child": None,
        "note": "Equivalised size is the square root of headcount, with no "
                "distinction between adults and children. Blunt but "
                "transparent, and widely used in comparative work precisely "
                "because it has no parameters to argue about.",
    },
    "per_capita": {
        "label": "Per capita (no adjustment)",
        "first_adult": 1.0,
        "other_adult": 1.0,
        "child": 1.0,
        "note": "The degenerate case, included so the app's current behaviour "
                "is visible as a choice rather than as the absence of one. It "
                "asserts that a household of four shares nothing, which is "
                "false for every category in the table below.",
    },
}

DEFAULT_SCALE = "oecd_modified"

# A reference household used to calibrate the fair-share reallocation, so that
# a household of this composition receives the same budget under the
# equivalised allocation as under the per-capita one. Without a calibration
# point, switching scales would silently change the total allocated across all
# households rather than only its distribution.
REFERENCE_HOUSEHOLD = ({"name": "Adult 1", "age": 40},
                       {"name": "Adult 2", "age": 38},
                       {"name": "Child 1", "age": 10},
                       {"name": "Child 2", "age": 7})


# ---------------------------------------------------------------------------
# Categories and their sharing elasticity
#
# The elasticity is the exponent relating equivalised household size to the
# footprint of that category: 0 is a pure household public good (a second
# occupant adds nothing), 1 is purely private (a second occupant adds a full
# share). Applying one number to heating and to food gets both wrong, in
# opposite directions.
# ---------------------------------------------------------------------------
CATEGORIES = {
    "space_heating": {
        "label": "Space heating and cooling",
        "sharing_elasticity": 0.12,
        "note": "The closest thing here to a pure public good. The dwelling is "
                "heated whether one person or four are in it, and the marginal "
                "occupant adds only their own hot water and a little "
                "ventilation loss. This is where per-capita division does most "
                "of its damage.",
    },
    "lighting_and_standby": {
        "label": "Lighting and standby",
        "sharing_elasticity": 0.25,
        "note": "Rooms are lit for whoever is in them, and the always-on load "
                "- router, fridge, standby - does not scale with occupancy at "
                "all.",
    },
    "appliances": {
        "label": "Appliances and laundry",
        "sharing_elasticity": 0.55,
        "note": "A dishwasher or washing machine runs on a load rather than "
                "per person, so larger households fill them more efficiently. "
                "Partly shared, partly not.",
    },
    "water": {
        "label": "Water and sanitation",
        "sharing_elasticity": 0.75,
        "note": "Mostly private - showers, drinking, laundry volume - with a "
                "modest shared component in cleaning and garden use.",
    },
    "food": {
        "label": "Food",
        "sharing_elasticity": 0.92,
        "note": "Very close to private. The small saving from cooking in "
                "quantity and wasting proportionally less is real but minor, "
                "and treating food as shared would be as wrong as treating "
                "heating as private.",
    },
    "personal_transport": {
        "label": "Personal transport",
        "sharing_elasticity": 0.7,
        "note": "A car journey with three passengers costs what a journey with "
                "one costs, which is a genuine shared saving. Journeys taken "
                "separately are not shared at all, so the elasticity sits "
                "between.",
    },
    "goods_and_clothing": {
        "label": "Goods and clothing",
        "sharing_elasticity": 0.85,
        "note": "Mostly individual, with real sharing in durables - one "
                "television, one lawnmower, one set of kitchen equipment.",
    },
    "waste": {
        "label": "Waste",
        "sharing_elasticity": 0.88,
        "note": "Tracks consumption closely, with a small shared component in "
                "packaging bought in bulk.",
    },
    "digital": {
        "label": "Digital and connectivity",
        "sharing_elasticity": 0.6,
        "note": "One connection serves the household; devices and streaming "
                "are individual. The split is roughly even.",
    },
}


# ---------------------------------------------------------------------------
# Attribution bases
# ---------------------------------------------------------------------------
ATTRIBUTION_BASES = {
    "consumption": {
        "label": "Consumption",
        "note": "Who used it, weighted by the equivalence scale and by how "
                "much of the year they were present. The right basis for "
                "benchmarking, because it is the one national averages are "
                "built on.",
    },
    "benefit": {
        "label": "Benefit",
        "note": "Who gained from it, counting every member fully. A child "
                "benefits from a heated house as much as an adult does, "
                "whatever the equivalence scale says about their consumption. "
                "The right basis for questions about fairness within the "
                "household.",
    },
    "control": {
        "label": "Control",
        "note": "Who could change it. The right basis for reduction advice, "
                "and the one that differs most from the other two: attributing "
                "heating equally to someone with no say over the thermostat "
                "produces advice aimed at a person who cannot act on it.",
    },
}


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------
def build_member(name, age, person_days=FULL_YEAR_DAYS, agency=None):
    """One household member, with the occupancy and agency the app never held.

    ``person_days`` covers visitors, part-time residents and shared custody,
    all of which are common and none of which the current headcount can
    express. ``agency`` maps a category to a share of decision authority
    between 0 and 1.
    """
    if not name or not str(name).strip():
        raise AllocationError("A household member needs a name.")
    try:
        years = float(age)
    except (TypeError, ValueError):
        raise AllocationError(f"{age!r} is not an age.")
    if years < 0 or years > 130:
        raise AllocationError(f"{age!r} is not a plausible age.")

    days = float(person_days)
    if days <= 0:
        raise AllocationError(
            "A member present for no days of the year is not a member of the "
            "household. Remove them rather than giving them zero occupancy."
        )
    if days > FULL_YEAR_DAYS:
        raise AllocationError(
            f"{days} person-days exceeds a year. Occupancy is measured within "
            f"a single year; a longer stay is still a full year."
        )

    cleaned_agency = {}
    for category, share in (agency or {}).items():
        if category not in CATEGORIES:
            raise AllocationError(
                f"{category!r} is not a known category."
            )
        value = float(share)
        if not 0.0 <= value <= 1.0:
            raise AllocationError(
                f"Agency over {category!r} must be between 0 and 1."
            )
        cleaned_agency[category] = value

    return {
        "name": str(name).strip(),
        "age": years,
        "is_child": years < CHILD_AGE_THRESHOLD,
        "person_days": days,
        "occupancy": round(days / FULL_YEAR_DAYS, 6),
        "agency": cleaned_agency,
    }


def _check_members(members):
    if not members:
        raise AllocationError("A household needs at least one member.")
    for member in members:
        if not isinstance(member, dict) or "occupancy" not in member:
            raise AllocationError(
                "Members must be built with build_member() so occupancy and "
                "child status are set consistently."
            )
    return list(members)


# ---------------------------------------------------------------------------
# Equivalent adults
# ---------------------------------------------------------------------------
def equivalent_adults(members, scale=DEFAULT_SCALE):
    """The equivalised size of a household under one scale."""
    members = _check_members(members)
    if scale not in EQUIVALENCE_SCALES:
        raise AllocationError(
            f"{scale!r} is not a known equivalence scale. Known scales: "
            f"{', '.join(EQUIVALENCE_SCALES)}."
        )

    headcount = sum(member["occupancy"] for member in members)

    if scale == "square_root":
        weights = [
            {"name": member["name"],
             "weight": round(member["occupancy"] * math.sqrt(headcount) / headcount, 6)
             if headcount else 0.0,
             "occupancy": member["occupancy"],
             "is_child": member["is_child"]}
            for member in members
        ]
        equivalised = math.sqrt(headcount) if headcount > 0 else 0.0
        return {
            "scale": scale,
            "label": EQUIVALENCE_SCALES[scale]["label"],
            "headcount": round(headcount, 4),
            "equivalent_adults": round(equivalised, 6),
            "members": weights,
            "economies_of_scale": round(
                1.0 - equivalised / headcount, 4
            ) if headcount else 0.0,
        }

    parameters = EQUIVALENCE_SCALES[scale]

    # The first adult carries the full weight. Where there is no adult, the
    # oldest member takes that position: a household of children is not a
    # household of zero equivalent adults, and the scales are silent on the
    # case because they were built for income statistics rather than for
    # footprint accounting.
    ordered = sorted(
        members, key=lambda m: (m["is_child"], -m["age"], -m["occupancy"])
    )
    weights = []
    for index, member in enumerate(ordered):
        if index == 0:
            base = parameters["first_adult"]
        elif member["is_child"]:
            base = parameters["child"]
        else:
            base = parameters["other_adult"]
        weights.append({
            "name": member["name"],
            "weight": round(base * member["occupancy"], 6),
            "base_weight": base,
            "occupancy": member["occupancy"],
            "is_child": member["is_child"],
        })

    equivalised = sum(row["weight"] for row in weights)
    return {
        "scale": scale,
        "label": parameters["label"],
        "headcount": round(headcount, 4),
        "equivalent_adults": round(equivalised, 6),
        "members": weights,
        "economies_of_scale": round(
            1.0 - equivalised / headcount, 4
        ) if headcount else 0.0,
    }


def category_units(members, category, scale=DEFAULT_SCALE):
    """Equivalised size for one category, after its sharing elasticity.

    An elasticity of zero collapses this to one unit however many people are
    present, which is the correct treatment of a dwelling that is heated
    whether one person or four are in it.
    """
    if category not in CATEGORIES:
        raise AllocationError(f"{category!r} is not a known category.")
    base = equivalent_adults(members, scale)["equivalent_adults"]
    if base <= 0:
        return 0.0
    elasticity = CATEGORIES[category]["sharing_elasticity"]
    return base ** elasticity


# ---------------------------------------------------------------------------
# Per-person footprints
# ---------------------------------------------------------------------------
def per_person_footprint(footprint, members, scale=DEFAULT_SCALE):
    """The household footprint expressed per equivalent adult, per category.

    The naive per-capita figure is computed alongside so the correction is
    visible rather than asserted. For a single-occupant household the two
    differ by a large factor, and that factor is the misattribution the module
    exists to remove.
    """
    members = _check_members(members)
    if not footprint:
        raise AllocationError("There is no footprint to divide.")

    rows = []
    total = 0.0
    equivalised_total = 0.0
    for category, value in footprint.items():
        if category not in CATEGORIES:
            raise AllocationError(
                f"{category!r} is not a known category. Known categories: "
                f"{', '.join(CATEGORIES)}."
            )
        amount = float(value)
        if amount < 0:
            raise AllocationError(
                f"{category!r} cannot have a negative footprint."
            )
        units = category_units(members, category, scale)
        per_unit = amount / units if units > 0 else 0.0
        total += amount
        equivalised_total += per_unit
        rows.append({
            "category": category,
            "label": CATEGORIES[category]["label"],
            "household_total": round(amount, 3),
            "sharing_elasticity": CATEGORIES[category]["sharing_elasticity"],
            "units": round(units, 4),
            "per_equivalent_adult": round(per_unit, 3),
        })

    headcount = sum(member["occupancy"] for member in members)
    equivalised_size = equivalent_adults(members, scale)["equivalent_adults"]
    naive = total / headcount if headcount else 0.0
    flat = total / equivalised_size if equivalised_size else 0.0
    rows.sort(key=lambda row: row["household_total"], reverse=True)

    # Three figures, because they answer three questions and conflating them is
    # how this module would go wrong in its turn.
    #
    #   per_capita              total / headcount. What the app does now.
    #   per_equivalent_adult    total / equivalised size. One scale for
    #                           everything, which is better than headcount and
    #                           still applies heating's sharing to food.
    #   comparable_footprint    each category divided by its own equivalised
    #                           size and summed. The figure to compare between
    #                           households of different composition. It does
    #                           not multiply back to the household total and is
    #                           not meant to: it is the footprint a
    #                           one-equivalent-adult household would have at
    #                           these per-unit intensities.
    return {
        "scale": scale,
        "household_total": round(total, 3),
        "headcount": round(headcount, 4),
        "equivalent_adults": round(equivalised_size, 4),
        "per_capita": round(naive, 3),
        "per_equivalent_adult": round(flat, 3),
        "comparable_footprint": round(equivalised_total, 3),
        "difference": round(flat - naive, 3),
        "difference_share": (
            round((flat - naive) / naive, 4) if naive else 0.0
        ),
        "category_resolved_difference": round(equivalised_total - flat, 3),
        "categories": rows,
    }


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------
def _member_shares(members, category, basis, scale):
    """Each member's share of one category under one attribution basis."""
    elasticity = CATEGORIES[category]["sharing_elasticity"]
    weights = {
        row["name"]: row for row in
        equivalent_adults(members, scale)["members"]
    }

    raw = {}
    for member in members:
        name = member["name"]
        if basis == "consumption":
            # Interpolates between an equal split by presence for a public
            # good and a full equivalence-weighted split for a private one.
            scale_weight = weights[name]["weight"] / member["occupancy"] \
                if member["occupancy"] else 0.0
            raw[name] = (scale_weight ** elasticity) * member["occupancy"]
        elif basis == "benefit":
            raw[name] = member["occupancy"]
        elif basis == "control":
            declared = member["agency"].get(category)
            if declared is not None:
                raw[name] = declared
            else:
                raw[name] = 0.0 if member["is_child"] else member["occupancy"]
        else:
            raise AllocationError(
                f"{basis!r} is not a known attribution basis. Known bases: "
                f"{', '.join(ATTRIBUTION_BASES)}."
            )

    total = sum(raw.values())
    if total <= 0:
        # Nobody holds control over this category. That is a real answer, not
        # an error, and it is exactly the case worth surfacing: reduction
        # advice about it has nowhere in this household to go.
        return {name: 0.0 for name in raw}, False
    return {name: value / total for name, value in raw.items()}, True


def attribute(footprint, members, basis="consumption", scale=DEFAULT_SCALE):
    """Attribute a household footprint to its members on one basis."""
    members = _check_members(members)
    if basis not in ATTRIBUTION_BASES:
        raise AllocationError(
            f"{basis!r} is not a known attribution basis."
        )

    per_member = {member["name"]: 0.0 for member in members}
    rows = []
    unattributed = []

    for category, value in footprint.items():
        if category not in CATEGORIES:
            raise AllocationError(f"{category!r} is not a known category.")
        amount = float(value)
        shares, attributable = _member_shares(members, category, basis, scale)
        if not attributable:
            unattributed.append(category)
        for name, share in shares.items():
            per_member[name] += amount * share
        rows.append({
            "category": category,
            "label": CATEGORIES[category]["label"],
            "household_total": round(amount, 3),
            "attributable": attributable,
            "shares": {name: round(share, 4) for name, share in shares.items()},
        })

    total = sum(float(value) for value in footprint.values())
    attributed = sum(per_member.values())

    return {
        "basis": basis,
        "basis_label": ATTRIBUTION_BASES[basis]["label"],
        "scale": scale,
        "household_total": round(total, 3),
        "attributed_total": round(attributed, 3),
        "unattributed_total": round(total - attributed, 3),
        "unattributed_categories": unattributed,
        "members": [
            {
                "name": name,
                "attributed": round(value, 3),
                "share": round(value / total, 4) if total else 0.0,
            }
            for name, value in sorted(
                per_member.items(), key=lambda item: -item[1]
            )
        ],
        "categories": rows,
    }


def compare_bases(footprint, members, scale=DEFAULT_SCALE):
    """All three attributions side by side, with the disagreement quantified.

    They are supposed to disagree. Where they do not, the household has no
    dependants and no concentration of decision authority, and picking a basis
    would not have mattered.
    """
    results = {
        basis: attribute(footprint, members, basis, scale)
        for basis in ATTRIBUTION_BASES
    }

    names = [member["name"] for member in members]
    rows = []
    for name in names:
        values = {
            basis: next(
                row["attributed"] for row in results[basis]["members"]
                if row["name"] == name
            )
            for basis in results
        }
        spread = max(values.values()) - min(values.values())
        rows.append({
            "name": name,
            **{f"{basis}": round(values[basis], 3) for basis in values},
            "spread": round(spread, 3),
        })

    rows.sort(key=lambda row: row["spread"], reverse=True)
    household_total = results["consumption"]["household_total"]

    return {
        "results": results,
        "members": rows,
        "largest_spread": rows[0]["spread"] if rows else 0.0,
        "largest_spread_share": (
            round(rows[0]["spread"] / household_total, 4)
            if rows and household_total else 0.0
        ),
        "bases_disagree": bool(rows and rows[0]["spread"] > 0.01),
    }


# ---------------------------------------------------------------------------
# Joint consumption
# ---------------------------------------------------------------------------
def reconcile_joint_activities(logs, household_total=None):
    """Detect activities logged by more than one member of a household.

    Two people in a car both log the trip. The household total is right if one
    of them logged it, and the sum of individual footprints is inflated by
    exactly the shared portion. Nothing else in this app catches that.
    """
    if not logs:
        raise AllocationError("There are no activity logs to reconcile.")

    grouped = {}
    for entry in logs:
        if not isinstance(entry, dict):
            raise AllocationError("Each log must be a mapping.")
        for field in ("member", "activity", "emissions"):
            if field not in entry:
                raise AllocationError(
                    f"Each log needs a {field}."
                )
        amount = float(entry["emissions"])
        if amount < 0:
            raise AllocationError("A logged activity cannot be negative.")
        key = str(entry["activity"])
        grouped.setdefault(key, []).append({
            "member": str(entry["member"]),
            "emissions": amount,
            "shared": bool(entry.get("shared", False)),
        })

    rows = []
    raw_sum = 0.0
    reconciled = 0.0
    for activity, entries in sorted(grouped.items()):
        reported = sum(entry["emissions"] for entry in entries)
        raw_sum += reported
        members = [entry["member"] for entry in entries]
        duplicated = len(entries) > 1 and all(
            entry["shared"] for entry in entries
        )
        if duplicated:
            counted = sum(
                entry["emissions"] for entry in entries
            ) / len(entries)
        else:
            counted = reported
        reconciled += counted
        rows.append({
            "activity": activity,
            "logged_by": members,
            "reported": round(reported, 3),
            "counted": round(counted, 3),
            "double_counted": round(reported - counted, 3),
            "is_duplicate": duplicated,
        })

    duplicates = [row for row in rows if row["is_duplicate"]]
    rows.sort(key=lambda row: row["double_counted"], reverse=True)

    result = {
        "activities": rows,
        "raw_sum": round(raw_sum, 3),
        "reconciled_total": round(reconciled, 3),
        "double_counted": round(raw_sum - reconciled, 3),
        "double_counted_share": (
            round((raw_sum - reconciled) / raw_sum, 4) if raw_sum else 0.0
        ),
        "duplicate_activities": [row["activity"] for row in duplicates],
    }

    if household_total is not None:
        stated = float(household_total)
        result["household_total"] = round(stated, 3)
        result["discrepancy"] = round(reconciled - stated, 3)
        result["reconciles"] = abs(reconciled - stated) < 0.01

    return result


# ---------------------------------------------------------------------------
# Benchmarking
# ---------------------------------------------------------------------------
def composition_adjusted_benchmark(footprint, members,
                                   reference_per_equivalent_adult,
                                   scale=DEFAULT_SCALE):
    """Compare a household against one of its own composition.

    The naive comparison mixes two entirely different things: how much this
    household consumes and how many people are in it. Separating them is the
    point, because only one of the two is something the household could act on.
    """
    members = _check_members(members)
    if not reference_per_equivalent_adult:
        raise AllocationError(
            "A benchmark needs reference values per equivalent adult."
        )

    expected = 0.0
    rows = []
    for category, value in footprint.items():
        if category not in CATEGORIES:
            raise AllocationError(f"{category!r} is not a known category.")
        reference = float(reference_per_equivalent_adult.get(category, 0.0))
        units = category_units(members, category, scale)
        category_expected = reference * units
        expected += category_expected
        actual = float(value)
        rows.append({
            "category": category,
            "label": CATEGORIES[category]["label"],
            "actual": round(actual, 3),
            "expected": round(category_expected, 3),
            "difference": round(actual - category_expected, 3),
            "ratio": (
                round(actual / category_expected, 4)
                if category_expected else None
            ),
        })

    actual_total = sum(float(value) for value in footprint.values())

    reference_members = [
        build_member(entry["name"], entry["age"])
        for entry in REFERENCE_HOUSEHOLD
    ]
    reference_expected = sum(
        float(reference_per_equivalent_adult.get(category, 0.0))
        * category_units(reference_members, category, scale)
        for category in footprint
    )
    reference_headcount = len(REFERENCE_HOUSEHOLD)
    reference_per_capita = reference_expected / reference_headcount

    headcount = sum(member["occupancy"] for member in members)
    naive_expected = reference_per_capita * headcount

    rows.sort(key=lambda row: abs(row["difference"]), reverse=True)

    return {
        "scale": scale,
        "actual_total": round(actual_total, 3),
        "expected_for_this_composition": round(expected, 3),
        "expected_per_capita_comparison": round(naive_expected, 3),
        "behaviour_effect": round(actual_total - expected, 3),
        "composition_effect": round(expected - naive_expected, 3),
        "naive_verdict": (
            "above average" if actual_total > naive_expected else "below average"
        ),
        "adjusted_verdict": (
            "above average" if actual_total > expected else "below average"
        ),
        "verdict_flips": (
            (actual_total > naive_expected) != (actual_total > expected)
        ),
        "categories": rows,
    }


# ---------------------------------------------------------------------------
# Fair share
# ---------------------------------------------------------------------------
def fair_share_reallocation(per_capita_budget, members, scale=DEFAULT_SCALE):
    """Allocate a fair-share budget on equivalent adults rather than headcount.

    Calibrated against a reference household so switching scales redistributes
    the budget without changing how much of it is handed out in total. Without
    that calibration, a scale change would quietly alter the aggregate, which
    is a different and much larger claim than the one this function is making.
    """
    members = _check_members(members)
    budget = float(per_capita_budget)
    if budget <= 0:
        raise AllocationError("A fair-share budget must be positive.")

    reference_members = [
        build_member(entry["name"], entry["age"])
        for entry in REFERENCE_HOUSEHOLD
    ]
    reference_equivalent = equivalent_adults(
        reference_members, scale
    )["equivalent_adults"]
    reference_headcount = float(len(REFERENCE_HOUSEHOLD))

    per_equivalent = budget * reference_headcount / reference_equivalent

    own = equivalent_adults(members, scale)
    headcount = own["headcount"]
    naive_budget = budget * headcount
    adjusted_budget = per_equivalent * own["equivalent_adults"]

    return {
        "scale": scale,
        "per_capita_budget": round(budget, 3),
        "per_equivalent_adult_budget": round(per_equivalent, 3),
        "headcount": round(headcount, 4),
        "equivalent_adults": round(own["equivalent_adults"], 4),
        "naive_budget": round(naive_budget, 3),
        "adjusted_budget": round(adjusted_budget, 3),
        "difference": round(adjusted_budget - naive_budget, 3),
        "difference_share": (
            round((adjusted_budget - naive_budget) / naive_budget, 4)
            if naive_budget else 0.0
        ),
        "direction": (
            "more" if adjusted_budget > naive_budget else
            "less" if adjusted_budget < naive_budget else "unchanged"
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_allocation_insights(division, comparison=None, benchmark=None,
                            reconciliation=None, fair_share=None):
    """Plain-language findings, ordered by how much they should change a view."""
    insights = []

    if division["difference_share"] > 0.02:
        insights.append(
            f"Dividing by headcount gives {division['per_capita']:,.0f} kg "
            f"CO2e per person. Dividing by equivalent adults gives "
            f"{division['per_equivalent_adult']:,.0f} kg - "
            f"{division['difference_share'] * 100:.0f}% higher. The gap is "
            f"economies of scale, which the per-capita figure charges to the "
            f"household as though it were behaviour."
        )
        insights.append(
            f"Resolved category by category, the figure comparable against "
            f"other compositions is {division['comparable_footprint']:,.0f} kg. "
            f"It sits above the single-scale number because one scale applies "
            f"heating's sharing to food, and food is very nearly private."
        )

    if division["headcount"] <= 1.05:
        insights.append(
            "This is a single-occupancy household, which is where per-capita "
            "division does most of its damage. One person heats a whole "
            "dwelling and runs a fridge for one, and none of that is a "
            "lifestyle choice."
        )

    heating = next(
        (row for row in division["categories"]
         if row["category"] == "space_heating"), None
    )
    if heating and division["headcount"] > 1.5:
        insights.append(
            f"Space heating divides across only {heating['units']:.2f} "
            f"equivalent units rather than {division['headcount']:.1f} people, "
            f"because a dwelling is heated whether one person or four are in "
            f"it. Treating it as private is the single largest error in the "
            f"per-capita approach."
        )

    if comparison and comparison["bases_disagree"]:
        row = comparison["members"][0]
        insights.append(
            f"{row['name']}'s share differs by {row['spread']:,.0f} kg CO2e "
            f"depending on whether you ask who consumed it, who benefited from "
            f"it, or who could change it. Reduction advice should follow "
            f"control; benchmarking should follow consumption."
        )

    unattributed = comparison["results"]["control"]["unattributed_categories"] \
        if comparison else []
    if unattributed:
        names = ", ".join(
            CATEGORIES[category]["label"].lower() for category in unattributed
        )
        insights.append(
            f"Nobody in this household holds decision authority over {names}. "
            f"That is a real answer rather than missing data, and it means "
            f"reduction advice about it has nowhere here to go - it belongs "
            f"with a landlord or a provider."
        )

    if reconciliation and reconciliation["double_counted"] > 0:
        insights.append(
            f"{reconciliation['double_counted']:,.0f} kg CO2e is counted twice "
            f"because more than one member logged the same activity "
            f"({', '.join(reconciliation['duplicate_activities'][:3])}). The "
            f"household total is right; the sum of individual footprints is "
            f"inflated by exactly that amount."
        )

    if benchmark:
        if benchmark["verdict_flips"]:
            insights.append(
                f"Against a national per-capita average this household reads "
                f"as {benchmark['naive_verdict']}. Against a household of the "
                f"same composition it reads as {benchmark['adjusted_verdict']}. "
                f"The verdict flips, and only the second one is about anything "
                f"this household did."
            )
        insights.append(
            f"Of the gap against the per-capita benchmark, "
            f"{benchmark['composition_effect']:+,.0f} kg is household "
            f"composition and {benchmark['behaviour_effect']:+,.0f} kg is "
            f"behaviour. Only the second is actionable."
        )

    if fair_share and abs(fair_share["difference_share"]) > 0.02:
        insights.append(
            f"On equivalent adults this household's fair share is "
            f"{fair_share['adjusted_budget']:,.0f} kg rather than "
            f"{fair_share['naive_budget']:,.0f} - "
            f"{abs(fair_share['difference_share']) * 100:.0f}% "
            f"{fair_share['direction']}. Allocating by headcount "
            f"redistributes away from small households, which correlate with "
            f"age, bereavement and low income."
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
        CREATE TABLE IF NOT EXISTS household_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            scale TEXT NOT NULL,
            household_total REAL NOT NULL,
            per_capita REAL NOT NULL,
            per_equivalent_adult REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_household_allocations_user
        ON household_allocations (user_id)
        """
    )


def save_allocation(user_id, name, division):
    """Persist a division and return its row id."""
    if not user_id:
        raise AllocationError("An allocation needs a user to belong to.")
    if not name or not str(name).strip():
        raise AllocationError("An allocation needs a name.")

    payload = json.dumps({
        "scale": division["scale"],
        "headcount": division["headcount"],
        "equivalent_adults": division["equivalent_adults"],
        "categories": division["categories"],
        "difference_share": division["difference_share"],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO household_allocations
                (user_id, name, payload, scale, household_total,
                 per_capita, per_equivalent_adult)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(user_id), str(name).strip(), payload, division["scale"],
                float(division["household_total"]),
                float(division["per_capita"]),
                float(division["per_equivalent_adult"]),
            ),
        )
        return int(cursor.lastrowid)


def get_allocations(user_id, limit=25):
    """Saved allocations for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, scale, household_total,
                       per_capita, per_equivalent_adult, created_at
                FROM household_allocations
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (str(user_id), int(limit)),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved household allocations")
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
            "scale": row[3],
            "household_total": row[4],
            "per_capita": row[5],
            "per_equivalent_adult": row[6],
            "created_at": row[7],
        })
    return saved


def delete_allocation(user_id, allocation_id):
    """Delete one saved allocation. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM household_allocations "
                "WHERE id = ? AND user_id = ?",
                (allocation_id, str(user_id)),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete allocation %s", allocation_id)
        return False


# ---------------------------------------------------------------------------
# Small accessors used by the page
# ---------------------------------------------------------------------------
def list_scales():
    return list(EQUIVALENCE_SCALES)


def get_scale(key):
    if key not in EQUIVALENCE_SCALES:
        raise AllocationError(f"{key!r} is not a known equivalence scale.")
    return dict(EQUIVALENCE_SCALES[key])


def list_categories():
    return list(CATEGORIES)


def get_category(key):
    if key not in CATEGORIES:
        raise AllocationError(f"{key!r} is not a known category.")
    return dict(CATEGORIES[key])


def list_bases():
    return list(ATTRIBUTION_BASES)


def get_basis(key):
    if key not in ATTRIBUTION_BASES:
        raise AllocationError(f"{key!r} is not a known attribution basis.")
    return dict(ATTRIBUTION_BASES[key])
