"""The footprint a person cannot go below, which the app has never represented.

``carbon_budget_equity.py`` tells a user their fair-share ceiling: how much they
may emit under an equity-based allocation of a remaining global budget. It is
one of the more careful modules in this app, and it answers exactly half of the
question.

The other half is the floor. Below some level a person is not living frugally,
they are going without heat, food or access to work. Nothing in this codebase
represents that level, so every reduction recommendation the app produces is
implicitly bounded by zero.

A ceiling without a floor produces advice that is at best useless
------------------------------------------------------------------
A household in a badly insulated rented flat with no control over its heating
and no viable transit has a large footprint and almost no agency.
``recommendation_engine.py`` and ``lifestyle_optimizer.py`` will hand it the
same list as a frequent flyer with a heat pump budget. The two situations call
for completely different responses, and the app cannot presently tell them
apart.

Some targets are arithmetically impossible, and the app should say so
----------------------------------------------------------------------
Where a fair-share ceiling falls below the decent living floor for someone's
actual circumstances, the gap is a structural problem - housing stock, grid mix,
transit provision - and not a personal failing. This module detects that case,
names the dimensions responsible, and declines to issue a target. Presenting an
infeasible number as a personal shortfall is the specific harm it exists to
prevent.

Constraint is not preference, and there are three states rather than two
-------------------------------------------------------------------------
A renter cannot install a heat pump. A shift worker cannot use a bus that stops
at nine. Between "fixed" and "your choice" sits the category that carries all
the useful information: movable, but only if a stated barrier is removed. A
binary split loses exactly the cases where the right advice is directed at a
landlord or a transport authority rather than at the user.

The floor is context-dependent, and a global constant would be worse than nothing
----------------------------------------------------------------------------------
Decent living energy varies with climate, building stock, settlement density and
grid intensity. One worldwide minimum would make a cold-climate renter's
unavoidable heating look like overconsumption, which is the opposite of what
this module is for.

A footprint below the floor is not a success
---------------------------------------------
It is most likely energy poverty or food insecurity. The module reports
under-provision as a welfare problem and specifically does not congratulate a
user for it. The floor is a right rather than a budget, and that framing is in
the code because the framing is the substance of the feature.

Where this connects to code already merged
-------------------------------------------
*   ``carbon_budget_equity.py`` allocates a global budget downward. This builds
    a requirement upward from human needs. They meet in the middle, and the
    space between them is the corridor a user actually operates in.
*   ``degree_days.py`` supplies the climate context this module needs.
*   ``household.py`` already collects tenure and household size, which nothing
    currently consumes as a constraint.
*   ``rebound_effect.py`` shows efficiency gains partly returning as increased
    consumption. Sufficiency - needs met, then stop - is the response, and the
    app had the diagnosis without it.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


class SufficiencyError(ValueError):
    """Raised when a sufficiency calculation was asked for nonsense."""


# ---------------------------------------------------------------------------
# Agency
#
# Three states, not two. The middle one is where the useful information lives:
# a binary split collapses "you could change this if your landlord agreed" into
# either "immovable" or "your choice", and both readings produce bad advice.
# ---------------------------------------------------------------------------
AGENCY_STATES = {
    "structurally_fixed": {
        "label": "Structurally fixed",
        "note": "A need, or something the user has no route to changing. "
                "Reduction advice aimed here is at best noise and at worst an "
                "instruction to go without something they are entitled to.",
    },
    "conditionally_movable": {
        "label": "Movable if a barrier is removed",
        "note": "The category that carries the information. The advice here is "
                "real but is addressed to a landlord, a lender or a transport "
                "authority as much as to the user, and it should say so.",
    },
    "discretionary": {
        "label": "Discretionary",
        "note": "Where the user actually has leverage. Concentrating "
                "recommendations here is both more effective and more "
                "respectful than a flat percentage target.",
    },
}


# ---------------------------------------------------------------------------
# Decent living standards dimensions
#
# Reference values are per person per year at the reference context defined
# below. They are drawn from the published decent living standards literature
# and are contested at the margins; the module's claim is the structure, not
# the third significant figure.
#
# ``drivers`` names the context variables that move each dimension, which is
# how the floor becomes context-dependent rather than a global constant.
# ---------------------------------------------------------------------------
DLS_DIMENSIONS = {
    "nutrition": {
        "label": "Nutrition",
        "reference_kg_co2e": 600.0,
        "drivers": (),
        "barrier_sensitive": ("food_desert",),
        "note": "Enough food, of adequate quality, reliably. Varies less with "
                "context than anything else here, which is why it is the "
                "cleanest part of the floor.",
    },
    "shelter_thermal": {
        "label": "Thermal comfort",
        "reference_kg_co2e": 550.0,
        "drivers": ("degree_days", "building_efficiency", "grid_intensity",
                    "household_size"),
        "barrier_sensitive": ("tenure_rented", "no_capital", "off_gas_grid",
                              "medical_need"),
        "note": "Heating and cooling to a temperature that does not damage "
                "health. The most context-sensitive dimension by a wide margin "
                "and the one where a global constant does the most harm.",
    },
    "shelter_construction": {
        "label": "Housing (amortised construction)",
        "reference_kg_co2e": 180.0,
        "drivers": ("household_size",),
        "barrier_sensitive": ("tenure_rented",),
        "note": "The embodied carbon of adequate housing, spread over its "
                "life. Falls per person as household size rises, which is one "
                "of the few genuine economies of scale in a footprint.",
    },
    "water_sanitation": {
        "label": "Water and sanitation",
        "reference_kg_co2e": 60.0,
        "drivers": ("grid_intensity",),
        "barrier_sensitive": (),
        "note": "Safe water and sewerage. Small, non-negotiable, and almost "
                "entirely determined by how the pumping and treatment are "
                "powered.",
    },
    "clothing": {
        "label": "Clothing",
        "reference_kg_co2e": 70.0,
        "drivers": ("degree_days",),
        "barrier_sensitive": (),
        "note": "Adequate clothing for the climate. Rises in cold climates, "
                "which is a small effect and is included because leaving it "
                "out would imply the floor is climate-independent.",
    },
    "healthcare": {
        "label": "Healthcare access",
        "reference_kg_co2e": 180.0,
        "drivers": ("grid_intensity",),
        "barrier_sensitive": ("medical_need",),
        "note": "A per-capita share of a functioning health system. Attributed "
                "to individuals because it is a need, not because anyone "
                "chooses it.",
    },
    "education": {
        "label": "Education access",
        "reference_kg_co2e": 90.0,
        "drivers": ("grid_intensity",),
        "barrier_sensitive": (),
        "note": "A per-capita share of schooling. Like healthcare, a "
                "collective provision rather than a personal consumption "
                "choice, and reducible only by providing less of it.",
    },
    "communication": {
        "label": "Communication and information",
        "reference_kg_co2e": 55.0,
        "drivers": ("grid_intensity",),
        "barrier_sensitive": (),
        "note": "Connectivity sufficient to participate in society and reach "
                "services. Now a need rather than a convenience, and treated "
                "as one.",
    },
    "mobility_access": {
        "label": "Mobility for access",
        "reference_kg_co2e": 210.0,
        "drivers": ("density", "grid_intensity"),
        "barrier_sensitive": ("no_transit", "shift_work", "no_capital"),
        "note": "Reaching work, services and community - not travel in "
                "general. Varies more with where someone lives than with "
                "anything they decide, which is why the density driver matters "
                "more here than any behaviour.",
    },
}


# ---------------------------------------------------------------------------
# Context
#
# The reference case every dimension's base figure is quoted at.
# ---------------------------------------------------------------------------
REFERENCE_CONTEXT = {
    "heating_degree_days": 2500.0,
    "cooling_degree_days": 300.0,
    "building_efficiency": "average",
    "density": "urban",
    "grid_intensity_kg_per_kwh": 0.25,
    "household_size": 2.4,
}

BUILDING_EFFICIENCY = {
    "poor": {
        "label": "Poor (uninsulated, single glazed)",
        "multiplier": 1.85,
        "note": "Most of the pre-war housing stock. A household here needs "
                "nearly twice the energy for the same indoor temperature, and "
                "no behaviour change closes that gap.",
    },
    "below_average": {
        "label": "Below average (partial retrofit)",
        "multiplier": 1.35,
        "note": "Some insulation, usually loft but not walls. The most common "
                "state of the stock in temperate countries.",
    },
    "average": {
        "label": "Average (current building standard)",
        "multiplier": 1.00,
        "note": "The reference case. Not a good building, just a typical one.",
    },
    "good": {
        "label": "Good (deep retrofit or modern build)",
        "multiplier": 0.55,
        "note": "Well insulated and reasonably airtight. Roughly halves the "
                "thermal floor, which is the single largest lever on it.",
    },
    "excellent": {
        "label": "Excellent (Passivhaus standard)",
        "multiplier": 0.22,
        "note": "The thermal floor almost disappears. Reached by construction "
                "rather than by anything the occupant does.",
    },
}

SETTLEMENT_DENSITY = {
    "dense_urban": {
        "label": "Dense urban",
        "mobility_multiplier": 0.55,
        "note": "Most destinations reachable on foot or by frequent transit. "
                "The lowest mobility floor available, and it is a property of "
                "the place rather than of the person.",
    },
    "urban": {
        "label": "Urban",
        "mobility_multiplier": 1.00,
        "note": "The reference case: transit exists and does not go "
                "everywhere.",
    },
    "suburban": {
        "label": "Suburban",
        "mobility_multiplier": 1.60,
        "note": "Distances beyond walking and transit too sparse to rely on. "
                "The mobility floor rises with no change in what anyone wants.",
    },
    "rural": {
        "label": "Rural",
        "mobility_multiplier": 2.60,
        "note": "A car is required to reach work, a doctor or a shop. "
                "Recommending against driving here is recommending against "
                "employment.",
    },
}


# ---------------------------------------------------------------------------
# Barriers
#
# Each names something outside the user's control that pushes part of their
# footprint into the conditionally-movable category, and each states who could
# actually remove it. That last field is the point: it turns a reduction target
# into an address.
# ---------------------------------------------------------------------------
BARRIERS = {
    "tenure_rented": {
        "label": "Renting",
        "dimensions": ("shelter_thermal", "shelter_construction"),
        "removed_by": "the landlord, or a minimum energy standard for lettings",
        "note": "The classic split incentive: the tenant pays the bills and "
                "the landlord owns the walls. No advice addressed to the "
                "tenant can resolve it.",
    },
    "no_capital": {
        "label": "No capital for upfront investment",
        "dimensions": ("shelter_thermal", "mobility_access"),
        "removed_by": "a grant, a low-cost loan, or an on-bill finance scheme",
        "note": "Most efficiency measures pay back and almost all of them "
                "require money first. Advice that assumes the money is "
                "available is advice for people who already have it.",
    },
    "no_transit": {
        "label": "No viable public transport",
        "dimensions": ("mobility_access",),
        "removed_by": "a transport authority, not the household",
        "note": "Where there is no service, mode-shift advice is not advice.",
    },
    "shift_work": {
        "label": "Working outside service hours",
        "dimensions": ("mobility_access",),
        "removed_by": "extended service hours, or an employer changing shifts",
        "note": "Transit that stops at nine does not serve someone finishing "
                "at eleven. The route exists and is unusable.",
    },
    "off_gas_grid": {
        "label": "Off the gas grid",
        "dimensions": ("shelter_thermal",),
        "removed_by": "network connection, or a heat pump the household can afford",
        "note": "Oil or electric resistance heating, both of which raise the "
                "thermal floor substantially at no benefit to anyone.",
    },
    "medical_need": {
        "label": "Medical need for higher indoor temperature",
        "dimensions": ("shelter_thermal", "healthcare"),
        "removed_by": "nothing - this is a need and should not be treated as movable",
        "note": "Included so the module can recognise it and stop, rather than "
                "quietly counting it as discretionary heating.",
    },
    "food_desert": {
        "label": "Limited food retail access",
        "dimensions": ("nutrition", "mobility_access"),
        "removed_by": "local retail provision, or a delivery service that reaches the area",
        "note": "Raises both the nutrition floor and the travel needed to meet "
                "it, which is why it appears against two dimensions.",
    },
}


# How much of a dimension's excess above the floor a barrier locks up. Not all
# of it: even a renter can change some of their heating behaviour, and claiming
# otherwise would be as wrong as claiming they can change all of it.
BARRIER_LOCK_SHARE = 0.70

# Household economies of scale on the shelter dimensions. Per-capita shelter
# footprint falls with more people but not proportionally, because a larger
# home is still a larger home.
HOUSEHOLD_SCALE_EXPONENT = 0.40


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
def list_dimensions():
    """Dimension keys, largest reference contribution first."""
    return sorted(
        DLS_DIMENSIONS,
        key=lambda k: -DLS_DIMENSIONS[k]["reference_kg_co2e"],
    )


def get_dimension(key):
    """One dimension specification."""
    try:
        return DLS_DIMENSIONS[key]
    except KeyError:
        raise SufficiencyError(
            f"Unknown dimension '{key}'. Known dimensions: "
            f"{', '.join(list_dimensions())}."
        )


def list_building_efficiencies():
    """Building efficiency bands, worst first."""
    return sorted(
        BUILDING_EFFICIENCY,
        key=lambda k: -BUILDING_EFFICIENCY[k]["multiplier"],
    )


def list_densities():
    """Settlement densities, densest first."""
    return sorted(
        SETTLEMENT_DENSITY,
        key=lambda k: SETTLEMENT_DENSITY[k]["mobility_multiplier"],
    )


def list_barriers():
    """Barrier keys."""
    return sorted(BARRIERS)


def get_barrier(key):
    """One barrier specification."""
    try:
        return BARRIERS[key]
    except KeyError:
        raise SufficiencyError(
            f"Unknown barrier '{key}'. Known barriers: "
            f"{', '.join(list_barriers())}."
        )


def list_agency_states():
    """The three agency states, most constrained first."""
    return ["structurally_fixed", "conditionally_movable", "discretionary"]


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
def build_context(heating_degree_days=None, cooling_degree_days=None,
                  building_efficiency=None, density=None,
                  grid_intensity_kg_per_kwh=None, household_size=None):
    """A validated context, defaulting to the reference case field by field."""
    context = dict(REFERENCE_CONTEXT)

    if heating_degree_days is not None:
        if heating_degree_days < 0:
            raise SufficiencyError("Heating degree days cannot be negative.")
        context["heating_degree_days"] = float(heating_degree_days)
    if cooling_degree_days is not None:
        if cooling_degree_days < 0:
            raise SufficiencyError("Cooling degree days cannot be negative.")
        context["cooling_degree_days"] = float(cooling_degree_days)
    if building_efficiency is not None:
        if building_efficiency not in BUILDING_EFFICIENCY:
            raise SufficiencyError(
                f"Unknown building efficiency '{building_efficiency}'. "
                f"Known bands: {', '.join(list_building_efficiencies())}."
            )
        context["building_efficiency"] = building_efficiency
    if density is not None:
        if density not in SETTLEMENT_DENSITY:
            raise SufficiencyError(
                f"Unknown density '{density}'. Known densities: "
                f"{', '.join(list_densities())}."
            )
        context["density"] = density
    if grid_intensity_kg_per_kwh is not None:
        if grid_intensity_kg_per_kwh < 0:
            raise SufficiencyError("Grid intensity cannot be negative.")
        context["grid_intensity_kg_per_kwh"] = float(grid_intensity_kg_per_kwh)
    if household_size is not None:
        if household_size < 1:
            raise SufficiencyError("A household contains at least one person.")
        context["household_size"] = float(household_size)

    return context


def _driver_multiplier(driver, context):
    """How one context variable scales a dimension against the reference."""
    if driver == "degree_days":
        reference = (
            REFERENCE_CONTEXT["heating_degree_days"]
            + REFERENCE_CONTEXT["cooling_degree_days"]
        )
        actual = (
            context["heating_degree_days"] + context["cooling_degree_days"]
        )
        return actual / reference if reference else 1.0
    if driver == "building_efficiency":
        return BUILDING_EFFICIENCY[context["building_efficiency"]]["multiplier"]
    if driver == "density":
        return SETTLEMENT_DENSITY[context["density"]]["mobility_multiplier"]
    if driver == "grid_intensity":
        reference = REFERENCE_CONTEXT["grid_intensity_kg_per_kwh"]
        return (
            context["grid_intensity_kg_per_kwh"] / reference
            if reference else 1.0
        )
    if driver == "household_size":
        return (
            REFERENCE_CONTEXT["household_size"] / context["household_size"]
        ) ** HOUSEHOLD_SCALE_EXPONENT
    raise SufficiencyError(f"Unknown driver '{driver}'.")


def dimension_floor(dimension, context):
    """The context-adjusted floor for one dimension, kg CO2e per person-year."""
    spec = get_dimension(dimension)
    value = spec["reference_kg_co2e"]
    applied = {}
    for driver in spec["drivers"]:
        multiplier = _driver_multiplier(driver, context)
        applied[driver] = multiplier
        value *= multiplier

    return {
        "dimension": dimension,
        "label": spec["label"],
        "reference_kg_co2e": spec["reference_kg_co2e"],
        "floor_kg_co2e": value,
        "drivers_applied": applied,
        "context_multiplier": (
            value / spec["reference_kg_co2e"]
            if spec["reference_kg_co2e"] else 1.0
        ),
    }


def sufficiency_floor(context=None):
    """The whole decent living floor for a context, dimension by dimension."""
    context = context or build_context()
    rows = [dimension_floor(key, context) for key in list_dimensions()]
    total = sum(row["floor_kg_co2e"] for row in rows)
    reference_total = sum(row["reference_kg_co2e"] for row in rows)

    return {
        "context": context,
        "dimensions": sorted(rows, key=lambda r: -r["floor_kg_co2e"]),
        "floor_kg_co2e": total,
        "reference_floor_kg_co2e": reference_total,
        "context_multiplier": total / reference_total if reference_total else 1.0,
        "basis_note": (
            "Built upward from the decent living standards literature and "
            "adjusted for this context. The structure is the claim; the third "
            "significant figure is not. A single global minimum would make a "
            "cold-climate renter's unavoidable heating look like "
            "overconsumption, which is the opposite of the point."
        ),
        "rights_note": (
            "This is a floor of entitlement, not a budget to spend up to. A "
            "user below it is not to be congratulated."
        ),
    }


# ---------------------------------------------------------------------------
# Agency
# ---------------------------------------------------------------------------
def classify_agency(actual_by_dimension, context=None, barriers=None):
    """Split an actual footprint into fixed, conditionally movable, discretionary.

    Everything up to the floor is a need and is structurally fixed. The excess
    above it is discretionary unless an active barrier locks part of it, in
    which case that part is conditionally movable and carries the name of
    whoever could actually remove the barrier.
    """
    context = context or build_context()
    barriers = list(barriers or [])
    for barrier in barriers:
        get_barrier(barrier)

    floor = sufficiency_floor(context)
    floor_by_dimension = {
        row["dimension"]: row["floor_kg_co2e"] for row in floor["dimensions"]
    }

    rows = []
    totals = {state: 0.0 for state in list_agency_states()}

    for dimension in list_dimensions():
        actual = float(actual_by_dimension.get(dimension, 0.0))
        if actual < 0:
            raise SufficiencyError(
                f"Actual footprint for {dimension} cannot be negative."
            )
        dimension_floor_value = floor_by_dimension[dimension]

        fixed = min(actual, dimension_floor_value)
        excess = max(0.0, actual - dimension_floor_value)

        active = [
            barrier for barrier in barriers
            if dimension in BARRIERS[barrier]["dimensions"]
        ]
        if active and excess > 0:
            conditional = excess * BARRIER_LOCK_SHARE
            discretionary = excess - conditional
        else:
            conditional = 0.0
            discretionary = excess

        rows.append({
            "dimension": dimension,
            "label": get_dimension(dimension)["label"],
            "actual_kg_co2e": actual,
            "floor_kg_co2e": dimension_floor_value,
            "structurally_fixed": fixed,
            "conditionally_movable": conditional,
            "discretionary": discretionary,
            "under_provided": actual < dimension_floor_value,
            "shortfall_kg_co2e": max(0.0, dimension_floor_value - actual),
            "active_barriers": [
                {
                    "barrier": barrier,
                    "label": BARRIERS[barrier]["label"],
                    "removed_by": BARRIERS[barrier]["removed_by"],
                }
                for barrier in active
            ],
        })

        totals["structurally_fixed"] += fixed
        totals["conditionally_movable"] += conditional
        totals["discretionary"] += discretionary

    actual_total = sum(row["actual_kg_co2e"] for row in rows)
    under_provided = [row for row in rows if row["under_provided"]]

    return {
        "context": context,
        "barriers": barriers,
        "dimensions": rows,
        "totals": totals,
        "actual_kg_co2e": actual_total,
        "floor_kg_co2e": floor["floor_kg_co2e"],
        "movable_share": (
            (totals["conditionally_movable"] + totals["discretionary"])
            / actual_total if actual_total else 0.0
        ),
        "discretionary_share": (
            totals["discretionary"] / actual_total if actual_total else 0.0
        ),
        "under_provided_dimensions": [
            row["dimension"] for row in under_provided
        ],
        "three_states_note": (
            "Three states rather than two. A binary fixed-or-chosen split "
            "collapses 'movable if the landlord agrees' into one or the other, "
            "and both readings produce bad advice."
        ),
    }


# ---------------------------------------------------------------------------
# The corridor
# ---------------------------------------------------------------------------
def feasible_corridor(ceiling_kg_co2e, context=None):
    """The space between the decent living floor and a fair-share ceiling.

    Where the corridor is empty the module names the dimensions responsible and
    declines to issue a target. That refusal is the point: an infeasible number
    presented as a personal shortfall is the specific harm this exists to
    prevent.
    """
    if ceiling_kg_co2e <= 0:
        raise SufficiencyError("A fair-share ceiling must be positive.")

    floor = sufficiency_floor(context)
    width = ceiling_kg_co2e - floor["floor_kg_co2e"]
    feasible = width > 0

    responsible = []
    if not feasible:
        overshoot = -width
        for row in floor["dimensions"]:
            excess_over_reference = (
                row["floor_kg_co2e"] - row["reference_kg_co2e"]
            )
            if excess_over_reference > 0:
                responsible.append({
                    "dimension": row["dimension"],
                    "label": row["label"],
                    "reference_kg_co2e": row["reference_kg_co2e"],
                    "floor_kg_co2e": row["floor_kg_co2e"],
                    "context_excess_kg_co2e": excess_over_reference,
                    "share_of_overshoot": (
                        excess_over_reference / overshoot if overshoot else 0.0
                    ),
                    "drivers_applied": row["drivers_applied"],
                })
        responsible.sort(key=lambda r: -r["context_excess_kg_co2e"])

    return {
        "floor_kg_co2e": floor["floor_kg_co2e"],
        "ceiling_kg_co2e": ceiling_kg_co2e,
        "corridor_width_kg_co2e": width,
        "is_feasible": feasible,
        "responsible_dimensions": responsible,
        "verdict": (
            f"The corridor is {width:,.0f} kg CO2e wide. A target inside it is "
            f"achievable without giving up something the user is entitled to."
            if feasible else
            f"This fair-share ceiling sits {-width:,.0f} kg CO2e below the "
            f"decent living floor for these circumstances. No personal target "
            f"can close that gap, and issuing one would present a structural "
            f"problem as a personal failing."
        ),
        "structural_note": (
            None if feasible else
            "The gap is in the housing stock, the grid mix or the transport "
            "provision, and it is closed by changing those rather than by the "
            "household trying harder. The dimensions responsible are listed "
            "so the argument can be addressed to whoever can act on it."
        ),
    }


def consumption_position(actual_kg_co2e, ceiling_kg_co2e, context=None):
    """Where a footprint sits against both bounds, not just the upper one.

    Reports over-consumption relative to the ceiling and under-provision
    relative to the floor. Below the floor is a welfare problem and is reported
    as one; the module will not treat it as an achievement.
    """
    if actual_kg_co2e < 0:
        raise SufficiencyError("An actual footprint cannot be negative.")

    corridor = feasible_corridor(ceiling_kg_co2e, context)
    floor_value = corridor["floor_kg_co2e"]

    if actual_kg_co2e < floor_value:
        position = "below_floor"
    elif actual_kg_co2e > ceiling_kg_co2e:
        position = "above_ceiling"
    else:
        position = "within_corridor"

    return {
        "actual_kg_co2e": actual_kg_co2e,
        "floor_kg_co2e": floor_value,
        "ceiling_kg_co2e": ceiling_kg_co2e,
        "position": position,
        "corridor_is_feasible": corridor["is_feasible"],
        "overshoot_kg_co2e": max(0.0, actual_kg_co2e - ceiling_kg_co2e),
        "shortfall_kg_co2e": max(0.0, floor_value - actual_kg_co2e),
        "is_welfare_concern": position == "below_floor",
        "verdict": {
            "below_floor": (
                f"This footprint is {floor_value - actual_kg_co2e:,.0f} kg CO2e "
                f"below the decent living floor for these circumstances. That "
                f"is very likely energy poverty, food insecurity or restricted "
                f"access rather than an achievement, and it should be treated "
                f"as a welfare problem."
            ),
            "within_corridor": (
                "This footprint sits inside the corridor between what a decent "
                "life requires and what a fair share allows. There is no "
                "reduction obligation here."
            ),
            "above_ceiling": (
                f"This footprint exceeds the fair-share ceiling by "
                f"{actual_kg_co2e - ceiling_kg_co2e:,.0f} kg CO2e. Reduction "
                f"advice is appropriate and belongs in the discretionary "
                f"portion, not spread evenly across everything."
            ),
        }[position],
        "no_congratulation_note": (
            "A footprint below the floor is not a success. The floor is a "
            "right, not a budget, and this module will not congratulate a user "
            "for falling short of it."
            if position == "below_floor" else None
        ),
    }


# ---------------------------------------------------------------------------
# Recommendations, restricted to what a user can actually move
# ---------------------------------------------------------------------------
def reduction_targets(classification, ceiling_kg_co2e):
    """Where a reduction could come from, and who has to act for each.

    Restricted to the discretionary and conditionally-movable portions. If the
    required reduction exceeds what those two can supply, the module says so
    rather than distributing the remainder across needs.
    """
    actual = classification["actual_kg_co2e"]
    required = max(0.0, actual - ceiling_kg_co2e)
    totals = classification["totals"]
    available = totals["discretionary"] + totals["conditionally_movable"]

    targets = []
    for row in classification["dimensions"]:
        if row["discretionary"] > 0:
            targets.append({
                "dimension": row["dimension"],
                "label": row["label"],
                "agency": "discretionary",
                "available_kg_co2e": row["discretionary"],
                "who_acts": "the household",
                "condition": None,
            })
        for barrier in row["active_barriers"]:
            if row["conditionally_movable"] > 0:
                targets.append({
                    "dimension": row["dimension"],
                    "label": row["label"],
                    "agency": "conditionally_movable",
                    "available_kg_co2e": (
                        row["conditionally_movable"] / len(row["active_barriers"])
                    ),
                    "who_acts": barrier["removed_by"],
                    "condition": barrier["label"],
                })

    targets.sort(key=lambda t: -t["available_kg_co2e"])
    achievable = required <= available

    return {
        "required_reduction_kg_co2e": required,
        "available_discretionary_kg_co2e": totals["discretionary"],
        "available_conditional_kg_co2e": totals["conditionally_movable"],
        "available_total_kg_co2e": available,
        "targets": targets,
        "achievable_by_household_alone": required <= totals["discretionary"],
        "achievable_at_all": achievable,
        "unmet_kg_co2e": max(0.0, required - available),
        "verdict": (
            "No reduction is required: this footprint is already at or below "
            "the ceiling."
            if required == 0 else
            "The required reduction fits inside what the household can change "
            "on its own."
            if required <= totals["discretionary"] else
            "The required reduction fits only if barriers outside the "
            "household's control are removed. The advice below is addressed to "
            "whoever can remove them, not to the user."
            if achievable else
            f"Even removing every barrier and eliminating all discretionary "
            f"consumption leaves {required - available:,.0f} kg CO2e "
            f"unaccounted for. That residual sits inside the decent living "
            f"floor and is not a legitimate target."
        ),
        "restriction_note": (
            "Targets are drawn only from the discretionary and conditionally-"
            "movable portions. Advice aimed at the structurally fixed portion "
            "is an instruction to go without something the user is entitled "
            "to, and this module will not generate it."
        ),
    }


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------
def get_sufficiency_insights(classification, corridor):
    """Plain sentences about a household's position."""
    insights = []
    totals = classification["totals"]
    actual = classification["actual_kg_co2e"]

    insights.append(
        f"Of {actual:,.0f} kg CO2e, {totals['structurally_fixed']:,.0f} kg is "
        f"what a decent life requires in these circumstances, "
        f"{totals['conditionally_movable']:,.0f} kg is movable only if a "
        f"barrier is removed, and {totals['discretionary']:,.0f} kg is where "
        f"the household actually has leverage."
    )

    insights.append(
        f"That means {classification['discretionary_share']:.0%} of this "
        f"footprint is genuinely discretionary. A flat percentage reduction "
        f"target ignores that split and lands mostly on things nobody can "
        f"change."
    )

    if not corridor["is_feasible"]:
        insights.append(
            f"The fair-share ceiling here is below the decent living floor by "
            f"{-corridor['corridor_width_kg_co2e']:,.0f} kg CO2e. No personal "
            f"target closes that gap. {corridor['structural_note']}"
        )
        if corridor["responsible_dimensions"]:
            worst = corridor["responsible_dimensions"][0]
            insights.append(
                f"{worst['label']} accounts for most of it: this context "
                f"raises it from {worst['reference_kg_co2e']:,.0f} to "
                f"{worst['floor_kg_co2e']:,.0f} kg CO2e."
            )

    barrier_rows = [
        row for row in classification["dimensions"] if row["active_barriers"]
    ]
    if barrier_rows:
        row = max(barrier_rows, key=lambda r: r["conditionally_movable"])
        if row["conditionally_movable"] > 0:
            barrier = row["active_barriers"][0]
            insights.append(
                f"{row['conditionally_movable']:,.0f} kg CO2e of "
                f"{row['label'].lower()} is locked behind "
                f"{barrier['label'].lower()}. That is removed by "
                f"{barrier['removed_by']} — advice addressed to the household "
                f"cannot reach it."
            )

    if classification["under_provided_dimensions"]:
        names = ", ".join(
            get_dimension(d)["label"].lower()
            for d in classification["under_provided_dimensions"]
        )
        insights.append(
            f"This household is below the floor on {names}. That is a welfare "
            f"signal, not a saving, and nothing in this module treats it as an "
            f"achievement."
        )

    context = classification["context"]
    if context["building_efficiency"] in ("poor", "below_average"):
        band = BUILDING_EFFICIENCY[context["building_efficiency"]]
        insights.append(
            f"The building is {band['label'].lower()}, which multiplies the "
            f"thermal floor by {band['multiplier']:.2f}. {band['note']}"
        )
    if context["density"] in ("suburban", "rural"):
        band = SETTLEMENT_DENSITY[context["density"]]
        insights.append(
            f"Settlement density is {band['label'].lower()}, multiplying the "
            f"mobility floor by {band['mobility_multiplier']:.2f}. "
            f"{band['note']}"
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
        CREATE TABLE IF NOT EXISTS sufficiency_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            floor_kg_co2e REAL NOT NULL,
            actual_kg_co2e REAL NOT NULL,
            discretionary_kg_co2e REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_sufficiency_assessments_user
        ON sufficiency_assessments (user_id)
        """
    )


def save_assessment(user_id, name, classification):
    """Persist an agency classification and return its row id."""
    if not user_id:
        raise SufficiencyError("An assessment needs a user to belong to.")
    if not name or not name.strip():
        raise SufficiencyError("An assessment needs a name.")

    payload = json.dumps({
        "context": classification["context"],
        "barriers": classification["barriers"],
        "totals": classification["totals"],
        "discretionary_share": classification["discretionary_share"],
        "under_provided_dimensions": classification["under_provided_dimensions"],
        "dimensions": [
            {
                "dimension": row["dimension"],
                "actual_kg_co2e": row["actual_kg_co2e"],
                "floor_kg_co2e": row["floor_kg_co2e"],
                "structurally_fixed": row["structurally_fixed"],
                "conditionally_movable": row["conditionally_movable"],
                "discretionary": row["discretionary"],
            }
            for row in classification["dimensions"]
        ],
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO sufficiency_assessments
                (user_id, name, payload, floor_kg_co2e, actual_kg_co2e,
                 discretionary_kg_co2e)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload,
                float(classification["floor_kg_co2e"]),
                float(classification["actual_kg_co2e"]),
                float(classification["totals"]["discretionary"]),
            ),
        )
        return int(cursor.lastrowid)


def get_assessments(user_id):
    """Saved assessments for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, floor_kg_co2e, actual_kg_co2e,
                       discretionary_kg_co2e, created_at
                FROM sufficiency_assessments
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved sufficiency assessments")
        return []

    assessments = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        assessments.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "floor_kg_co2e": row[3],
            "actual_kg_co2e": row[4],
            "discretionary_kg_co2e": row[5],
            "created_at": row[6],
        })
    return assessments


def delete_assessment(user_id, assessment_id):
    """Delete one saved assessment. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM sufficiency_assessments "
                "WHERE id = ? AND user_id = ?",
                (assessment_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception(
            "Could not delete sufficiency assessment %s", assessment_id
        )
        return False
