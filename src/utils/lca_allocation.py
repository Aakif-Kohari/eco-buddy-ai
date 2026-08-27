"""Co-product allocation and system expansion, with the choice made visible.

``src.carbon.emission_factors.py`` gives one number per product. A litre of milk has a
footprint; a kilogram of beef has a footprint. Both come out of a system that
produced milk *and* beef from the same herd, and the split between them was a
methodological choice made by whoever built the factor - not a measurement.

There is no physically correct division
----------------------------------------
A dairy herd yields milk, cull beef and hides. A wheat crop yields grain and
straw. A refinery yields petrol, diesel, kerosene and bitumen from one barrel.
In each case a single process emits, and the burden has to be divided among
outputs that were produced together and cannot be produced separately. There are
conventions, and they disagree.

The disagreement is large enough to reverse conclusions
--------------------------------------------------------
Allocate a dairy system by mass and beef looks cheap, because a carcass weighs a
lot. Allocate it economically and beef carries far more, because it is worth far
more per kilogram. Allocate a refinery by mass and bitumen - dense, cheap, and
barely refined - carries a burden its price cannot justify; allocate by value
and it nearly disappears. For co-products with high mass and low value, or the
reverse, the ratio between bases routinely exceeds two, and that ratio is the
honest confidence interval on any co-product footprint.

System expansion is a different kind of answer
-----------------------------------------------
Rather than dividing the burden, a co-product is credited with the emissions of
whatever it displaces. Rapeseed meal displaces soy meal in animal feed; if the
displaced product is carbon-intensive enough, the credit can exceed the burden
and the primary product comes out below zero. That is not a bug - it is the
method saying the co-product does more good elsewhere than the process does
harm. But it makes the result a function of *market* assumptions, so the
displaced product and the displacement ratio are on the face of every result,
and expansion results are never mixed into an allocated total.

Physical allocation is not always defined
------------------------------------------
The standards prefer a physical relationship, and a refinery's outputs are not
comparable by mass in any way that means anything. Hides have no energy content
that is relevant to their function. Where a basis is undefined this refuses to
compute it and says which outputs made it undefined, rather than returning a
number that looks like the others.

Self-contained: standard library only, SQLite tables created lazily, no shared
files modified.
"""

import os
import json
import sqlite3
import logging
from typing import Any

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

MASS = "mass"
ENERGY = "energy"
ECONOMIC = "economic"
SYSTEM_EXPANSION = "system_expansion"

PARTITIONING_BASES = (MASS, ENERGY, ECONOMIC)
ALL_BASES = PARTITIONING_BASES + (SYSTEM_EXPANSION,)

BASIS_LABELS = {
    MASS: "Mass",
    ENERGY: "Energy content",
    ECONOMIC: "Economic value",
    SYSTEM_EXPANSION: "System expansion",
}

# Partitioning must return exactly what went in. Anything above this and the
# module has a bug, and should say so rather than return a plausible number.
CONSERVATION_TOLERANCE = 1e-6

# Recycling allocation methods.
CUT_OFF = "cut_off"
AVOIDED_BURDEN = "avoided_burden"
FIFTY_FIFTY = "fifty_fifty"
RECYCLING_METHODS = (CUT_OFF, AVOIDED_BURDEN, FIFTY_FIFTY)

RECYCLING_METHOD_LABELS = {
    CUT_OFF: "Cut-off (100:0)",
    AVOIDED_BURDEN: "Avoided burden (0:100)",
    FIFTY_FIFTY: "50/50",
}

RECYCLING_METHOD_NOTES = {
    CUT_OFF: (
        "Credits recycled *content*. What happens to the product afterwards "
        "makes no difference at all, so designing for recyclability earns "
        "nothing under this method."
    ),
    AVOIDED_BURDEN: (
        "Credits *recyclability*. Buying recycled content earns nothing, "
        "because the credit goes to whoever recovers the material at the end."
    ),
    FIFTY_FIFTY: (
        "Splits the benefit between the two. Neither lever is fully rewarded "
        "and neither is ignored."
    ),
}


class AllocationError(ValueError):
    """Raised when a process cannot be allocated on the basis requested."""


# ---------------------------------------------------------------------------
# Processes
#
# ``mass_kg`` is the physical output; ``energy_mj`` is None where the output has
# no energy function worth allocating on, and ``price`` is per kg. ``displaces``
# and ``displacement_ratio`` are only used by system expansion, and they are
# assumptions about a market rather than about the process.
# ---------------------------------------------------------------------------

PROCESSES: dict[str, dict[str, Any]] = {
    "dairy_herd": {
        "label": "Dairy herd",
        "burden_kg_co2e": 1420.0,
        "note": "Milk and beef from one animal. The single most consequential "
                "allocation choice in food footprinting, because it sets the "
                "relationship between two products people compare directly.",
        "outputs": {
            "milk": {
                "label": "Raw milk", "mass_kg": 1000.0, "energy_mj": 2.7,
                "price": 0.38, "displaces": None, "displacement_ratio": 1.0,
            },
            "cull_beef": {
                "label": "Cull beef", "mass_kg": 62.0, "energy_mj": 10.5,
                "price": 3.20, "displaces": "suckler_beef",
                "displacement_ratio": 1.0,
            },
            "hides": {
                "label": "Hides", "mass_kg": 14.0, "energy_mj": None,
                "price": 1.50, "displaces": None, "displacement_ratio": 1.0,
            },
        },
    },
    "wheat_crop": {
        "label": "Wheat crop",
        "burden_kg_co2e": 480.0,
        "note": "Grain and straw. Straw is heavy and nearly worthless, so mass "
                "and value disagree about as sharply as they ever do.",
        "outputs": {
            "grain": {
                "label": "Wheat grain", "mass_kg": 1000.0, "energy_mj": 13.8,
                "price": 0.22, "displaces": None, "displacement_ratio": 1.0,
            },
            "straw": {
                "label": "Straw", "mass_kg": 900.0, "energy_mj": 14.5,
                "price": 0.045, "displaces": None, "displacement_ratio": 1.0,
            },
        },
    },
    "rapeseed_crush": {
        "label": "Rapeseed crushing",
        "burden_kg_co2e": 610.0,
        "note": "Oil and meal. The meal displaces soy meal in animal feed, and "
                "soy meal is carbon-intensive enough that the credit can swamp "
                "the process - which is how a footprint comes out negative.",
        "outputs": {
            "rape_oil": {
                "label": "Rapeseed oil", "mass_kg": 410.0, "energy_mj": 37.0,
                "price": 0.95, "displaces": None, "displacement_ratio": 1.0,
            },
            "rape_meal": {
                "label": "Rapeseed meal", "mass_kg": 570.0, "energy_mj": 18.0,
                "price": 0.28, "displaces": "soy_meal",
                "displacement_ratio": 0.85,
            },
        },
    },
    "oil_refinery": {
        "label": "Oil refinery",
        "burden_kg_co2e": 300.0,
        "note": "Four products from one barrel. Bitumen is dense, cheap and "
                "barely refined, so mass allocation loads it with a burden its "
                "price cannot justify and value allocation makes it vanish.",
        "outputs": {
            "petrol": {
                "label": "Petrol", "mass_kg": 320.0, "energy_mj": 44.0,
                "price": 0.62, "displaces": None, "displacement_ratio": 1.0,
            },
            "diesel": {
                "label": "Diesel", "mass_kg": 380.0, "energy_mj": 43.0,
                "price": 0.58, "displaces": None, "displacement_ratio": 1.0,
            },
            "kerosene": {
                "label": "Kerosene", "mass_kg": 180.0, "energy_mj": 43.5,
                "price": 0.55, "displaces": None, "displacement_ratio": 1.0,
            },
            "bitumen": {
                "label": "Bitumen", "mass_kg": 120.0, "energy_mj": 40.0,
                "price": 0.12, "displaces": None, "displacement_ratio": 1.0,
            },
        },
    },
    "cheese_making": {
        "label": "Cheese making",
        "burden_kg_co2e": 95.0,
        "note": "Cheese and whey. The second step in a chain that started at "
                "the herd, so whatever was chosen there is carried into here.",
        "outputs": {
            "cheese": {
                "label": "Cheese", "mass_kg": 100.0, "energy_mj": 16.5,
                "price": 5.20, "displaces": None, "displacement_ratio": 1.0,
            },
            "whey": {
                "label": "Whey", "mass_kg": 850.0, "energy_mj": 1.0,
                "price": 0.06, "displaces": None, "displacement_ratio": 1.0,
            },
        },
    },
    "sawmill": {
        "label": "Sawmill",
        "burden_kg_co2e": 78.0,
        "note": "Sawn timber, sawdust and bark. The residues have real energy "
                "content and almost no value.",
        "outputs": {
            "sawn_timber": {
                "label": "Sawn timber", "mass_kg": 600.0, "energy_mj": 19.0,
                "price": 0.42, "displaces": None, "displacement_ratio": 1.0,
            },
            "sawdust": {
                "label": "Sawdust", "mass_kg": 250.0, "energy_mj": 18.5,
                "price": 0.035, "displaces": "wood_pellets",
                "displacement_ratio": 0.9,
            },
            "bark": {
                "label": "Bark", "mass_kg": 150.0, "energy_mj": 17.0,
                "price": 0.02, "displaces": None, "displacement_ratio": 1.0,
            },
        },
    },
}


# Intensity of the things co-products displace, kg CO2e per kg. Every one of
# these is a claim about a market, which is why system expansion results are
# kept apart from allocated ones.
DISPLACED_INTENSITIES: dict[str, float] = {
    "suckler_beef": 22.0,
    "soy_meal": 0.72,
    "wood_pellets": 0.28,
    "synthetic_fertiliser": 5.5,
    "grid_electricity": 0.28,
}

# The plausible range for each, because the central value is not a fact and the
# spread here decides the answer rather than nudging it. Soy meal from cleared
# land carries several times the intensity of soy meal from established
# cropland, and the choice between them is what makes a rapeseed footprint
# positive or negative - see ``displacement_sensitivity``.
DISPLACED_INTENSITY_RANGES: dict[str, dict[str, float]] = {
    "suckler_beef": {"low": 15.0, "central": 22.0, "high": 34.0},
    "soy_meal": {"low": 0.45, "central": 0.72, "high": 3.60},
    "wood_pellets": {"low": 0.12, "central": 0.28, "high": 0.55},
    "synthetic_fertiliser": {"low": 3.2, "central": 5.5, "high": 9.0},
    "grid_electricity": {"low": 0.03, "central": 0.28, "high": 0.82},
}


# ---------------------------------------------------------------------------
# Materials for recycling allocation
# ---------------------------------------------------------------------------

MATERIALS: dict[str, dict[str, Any]] = {
    "aluminium": {
        "label": "Aluminium",
        "virgin_kg_co2e": 11.5, "recycled_kg_co2e": 0.65,
        "recycled_content": 0.35, "recovery_rate": 0.70,
        "note": "The widest gap between virgin and recycled of any common "
                "material, so the choice of method matters most here.",
    },
    "steel": {
        "label": "Steel",
        "virgin_kg_co2e": 2.30, "recycled_kg_co2e": 0.70,
        "recycled_content": 0.40, "recovery_rate": 0.85,
        "note": "Recovered at a high rate, so avoided burden flatters it.",
    },
    "glass": {
        "label": "Glass",
        "virgin_kg_co2e": 1.10, "recycled_kg_co2e": 0.75,
        "recycled_content": 0.45, "recovery_rate": 0.70,
        "note": "A narrow gap, so the methods disagree less.",
    },
    "pet_plastic": {
        "label": "PET plastic",
        "virgin_kg_co2e": 2.70, "recycled_kg_co2e": 1.10,
        "recycled_content": 0.25, "recovery_rate": 0.45,
        "note": "Low recovery, so the two methods pull in different directions.",
    },
    "paper": {
        "label": "Paper and board",
        "virgin_kg_co2e": 1.05, "recycled_kg_co2e": 0.68,
        "recycled_content": 0.60, "recovery_rate": 0.75,
        "note": "High recycled content already, so cut-off already credits it.",
    },
}


# ---------------------------------------------------------------------------
# Table access
# ---------------------------------------------------------------------------

def list_processes() -> list[str]:
    """Process keys in table order."""
    return list(PROCESSES)


def list_materials() -> list[str]:
    """Material keys in table order."""
    return list(MATERIALS)


def get_process(process: str) -> dict[str, Any]:
    """One process, with its outputs."""
    if process not in PROCESSES:
        raise AllocationError(f"Unknown process: {process}")
    entry = dict(PROCESSES[process])
    entry["key"] = process
    return entry


def get_material(material: str) -> dict[str, Any]:
    """One material's recycling parameters."""
    if material not in MATERIALS:
        raise AllocationError(f"Unknown material: {material}")
    entry = dict(MATERIALS[material])
    entry["key"] = material
    return entry


def list_outputs(process: str) -> list[str]:
    """Output keys for a process."""
    return list(get_process(process)["outputs"])


# ---------------------------------------------------------------------------
# Partitioning
# ---------------------------------------------------------------------------

def _property_values(process: str, basis: str) -> dict[str, float]:
    """The quantity each output is allocated in proportion to.

    Where a basis is undefined for some output this refuses, and names the
    outputs that made it undefined. Returning a number for an undefined basis
    would be worse than returning nothing, because it would look like the
    others.
    """
    entry = get_process(process)
    outputs = entry["outputs"]

    if basis == MASS:
        missing = [
            key for key, output in outputs.items()
            if not output.get("mass_kg") or output["mass_kg"] <= 0
        ]
        if missing:
            raise AllocationError(
                f"Mass allocation is undefined for {process}: "
                f"{', '.join(missing)} has no mass"
            )
        return {key: output["mass_kg"] for key, output in outputs.items()}

    if basis == ENERGY:
        missing = [
            key for key, output in outputs.items()
            if output.get("energy_mj") is None or output["energy_mj"] <= 0
        ]
        if missing:
            raise AllocationError(
                f"Energy allocation is undefined for {process}: "
                f"{', '.join(missing)} has no energy function to allocate on"
            )
        return {
            key: output["mass_kg"] * output["energy_mj"]
            for key, output in outputs.items()
        }

    if basis == ECONOMIC:
        negative = [
            key for key, output in outputs.items()
            if output.get("price") is not None and output["price"] < 0
        ]
        if negative:
            raise AllocationError(
                f"Economic allocation is undefined for {process}: "
                f"{', '.join(negative)} has a negative value, which makes it a "
                "disposal cost rather than a co-product"
            )
        missing = [
            key for key, output in outputs.items() if output.get("price") is None
        ]
        if missing:
            raise AllocationError(
                f"Economic allocation is undefined for {process}: "
                f"{', '.join(missing)} has no price"
            )
        values = {
            key: output["mass_kg"] * output["price"]
            for key, output in outputs.items()
        }
        if sum(values.values()) <= 0:
            raise AllocationError(
                f"Economic allocation is undefined for {process}: "
                "the outputs have no value between them"
            )
        return values

    raise AllocationError(f"Unknown partitioning basis: {basis}")


def allocation_factors(process: str, basis: str) -> dict[str, float]:
    """Each output's share of the burden, summing to exactly 1."""
    values = _property_values(process, basis)
    total = sum(values.values())
    if total <= 0:
        raise AllocationError(
            f"Cannot allocate {process} on {basis}: the shares sum to zero"
        )
    return {key: value / total for key, value in values.items()}


def allocate(process: str, basis: str) -> dict[str, Any]:
    """Partition a process's burden across its outputs.

    Conservation is checked rather than assumed. Mass, energy and economic
    allocation must return exactly the burden they were given; if they do not,
    something is wrong and returning a plausible number would hide it.
    """
    if basis not in PARTITIONING_BASES:
        raise AllocationError(
            f"{basis} is not a partitioning basis; system expansion does not "
            "divide a burden, it subtracts credits from it"
        )

    entry = get_process(process)
    burden = entry["burden_kg_co2e"]
    factors = allocation_factors(process, basis)

    lines = []
    for key, factor in factors.items():
        output = entry["outputs"][key]
        allocated = burden * factor
        lines.append({
            "output": key,
            "label": output["label"],
            "share": round(factor, 6),
            "allocated_kg_co2e": round(allocated, 4),
            "mass_kg": output["mass_kg"],
            "per_kg": round(allocated / output["mass_kg"], 6),
        })
    lines.sort(key=lambda row: row["allocated_kg_co2e"], reverse=True)

    allocated_total = sum(row["allocated_kg_co2e"] for row in lines)
    if abs(allocated_total - burden) > max(CONSERVATION_TOLERANCE, burden * 1e-9):
        raise AllocationError(
            f"Allocation of {process} on {basis} does not conserve the burden: "
            f"{allocated_total} allocated against {burden} available"
        )

    return {
        "process": process,
        "label": entry["label"],
        "basis": basis,
        "basis_label": BASIS_LABELS[basis],
        "burden_kg_co2e": burden,
        "allocated_total": round(allocated_total, 4),
        "conserved": True,
        "lines": lines,
    }


# ---------------------------------------------------------------------------
# System expansion
# ---------------------------------------------------------------------------

def system_expansion(
    process: str,
    primary: str,
    intensities: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Credit co-products with what they displace, rather than dividing.

    The whole burden lands on the primary output, less the emissions of
    whatever each co-product displaces on the market. The result can go
    negative, and it is not clipped - a negative footprint here is the method
    saying the co-products do more good elsewhere than the process does harm,
    and hiding that would misrepresent what was computed.
    """
    entry = get_process(process)
    if primary not in entry["outputs"]:
        raise AllocationError(f"{primary} is not an output of {process}")

    intensities = {**DISPLACED_INTENSITIES, **(intensities or {})}
    burden = entry["burden_kg_co2e"]

    credits = []
    total_credit = 0.0
    uncredited = []
    for key, output in entry["outputs"].items():
        if key == primary:
            continue
        displaced = output.get("displaces")
        if not displaced:
            uncredited.append(output["label"])
            continue
        if displaced not in intensities:
            raise AllocationError(
                f"{output['label']} displaces {displaced}, which has no stated "
                "intensity"
            )
        ratio = output.get("displacement_ratio", 1.0)
        if ratio < 0:
            raise AllocationError("A displacement ratio cannot be negative")
        credit = output["mass_kg"] * ratio * intensities[displaced]
        total_credit += credit
        credits.append({
            "output": key,
            "label": output["label"],
            "displaces": displaced,
            "displaced_intensity": intensities[displaced],
            "displacement_ratio": ratio,
            "credit_kg_co2e": round(credit, 4),
        })

    primary_output = entry["outputs"][primary]
    net = burden - total_credit
    return {
        "process": process,
        "label": entry["label"],
        "basis": SYSTEM_EXPANSION,
        "basis_label": BASIS_LABELS[SYSTEM_EXPANSION],
        "primary": primary,
        "primary_label": primary_output["label"],
        "burden_kg_co2e": burden,
        "total_credit_kg_co2e": round(total_credit, 4),
        "net_kg_co2e": round(net, 4),
        "per_kg": round(net / primary_output["mass_kg"], 6),
        "is_negative": net < 0,
        "credits": credits,
        "uncredited_outputs": uncredited,
        "note": (
            "Every credit here is an assumption about what the co-product "
            "displaces on the market. Change the displaced product or the "
            "ratio and the answer changes, which is why this is never added "
            "to an allocated total."
        ),
    }


def displacement_sensitivity(
    process: str,
    primary: str,
) -> dict[str, Any]:
    """System expansion across the plausible range of every displaced product.

    The credit is the whole result under this method, and the credit is a market
    assumption. Rapeseed oil is 0.64 kg per kg if the meal it produces displaces
    soy meal from established cropland, and *below zero* if it displaces soy meal
    from cleared land - same process, same physics, same allocation method,
    opposite sign. Reporting the central value alone would present the most
    contested number in the method as a settled one.
    """
    rows = []
    for level in ("low", "central", "high"):
        overrides = {
            product: values[level]
            for product, values in DISPLACED_INTENSITY_RANGES.items()
        }
        result = system_expansion(process, primary, overrides)
        rows.append({
            "level": level,
            "net_kg_co2e": result["net_kg_co2e"],
            "per_kg": result["per_kg"],
            "total_credit_kg_co2e": result["total_credit_kg_co2e"],
            "is_negative": result["is_negative"],
        })
    values = [row["per_kg"] for row in rows]
    return {
        "process": process,
        "primary": primary,
        "rows": rows,
        "low": round(min(values), 6),
        "high": round(max(values), 6),
        "spread": round(max(values) - min(values), 6),
        "changes_sign": any(row["is_negative"] for row in rows)
        and not all(row["is_negative"] for row in rows),
    }


# ---------------------------------------------------------------------------
# Comparison across bases
# ---------------------------------------------------------------------------

def compare_bases(
    process: str,
    intensities: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Every basis for one process, with the bases that do not apply named.

    A basis that is undefined is reported as undefined with its reason, rather
    than dropped. Silently omitting it would suggest the process only admits the
    bases that happen to work, when the fact that one of them does not work is
    itself the finding.
    """
    entry = get_process(process)
    results: dict[str, Any] = {}
    unavailable: dict[str, str] = {}

    for basis in PARTITIONING_BASES:
        try:
            results[basis] = allocate(process, basis)
        except AllocationError as exc:
            unavailable[basis] = str(exc)

    expansions = {}
    for key in entry["outputs"]:
        try:
            expansions[key] = system_expansion(process, key, intensities)
        except AllocationError as exc:
            unavailable[f"{SYSTEM_EXPANSION}:{key}"] = str(exc)

    rows = []
    for key, output in entry["outputs"].items():
        per_kg = {}
        for basis, result in results.items():
            line = next(row for row in result["lines"] if row["output"] == key)
            per_kg[basis] = line["per_kg"]
        row = {
            "output": key,
            "label": output["label"],
            "mass_kg": output["mass_kg"],
            "per_kg": per_kg,
        }
        if per_kg:
            low, high = min(per_kg.values()), max(per_kg.values())
            row["low"] = round(low, 6)
            row["high"] = round(high, 6)
            row["spread"] = round(high - low, 6)
            row["ratio"] = round(high / low, 3) if low > 0 else None
            row["low_basis"] = min(per_kg, key=per_kg.get)
            row["high_basis"] = max(per_kg, key=per_kg.get)
        rows.append(row)
    rows.sort(key=lambda row: row.get("ratio") or 0.0, reverse=True)

    return {
        "process": process,
        "label": entry["label"],
        "burden_kg_co2e": entry["burden_kg_co2e"],
        "note": entry["note"],
        "available_bases": list(results),
        "unavailable_bases": unavailable,
        "results": results,
        "expansions": {
            key: {
                "net_kg_co2e": value["net_kg_co2e"],
                "per_kg": value["per_kg"],
                "is_negative": value["is_negative"],
            }
            for key, value in expansions.items()
        },
        "rows": rows,
    }


def spread_report(process: str) -> dict[str, Any]:
    """The between-basis ratio for each output.

    This is the honest confidence interval on a co-product footprint, and it is
    not the interval ``src.utils.footprint_uncertainty.py`` produces - that one propagates
    parameter uncertainty, where this is methodological choice, and here the
    methodological term is usually the larger of the two.
    """
    comparison = compare_bases(process)
    rows = [row for row in comparison["rows"] if row.get("ratio")]
    if not rows:
        return {
            "process": process,
            "label": comparison["label"],
            "rows": [],
            "widest": None,
            "widest_ratio": None,
        }
    widest = max(rows, key=lambda row: row["ratio"])
    return {
        "process": process,
        "label": comparison["label"],
        "rows": rows,
        "widest": widest["label"],
        "widest_ratio": widest["ratio"],
        "widest_low_basis": BASIS_LABELS[widest["low_basis"]],
        "widest_high_basis": BASIS_LABELS[widest["high_basis"]],
    }


# ---------------------------------------------------------------------------
# Chains
# ---------------------------------------------------------------------------

def chain(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Carry an allocation basis through a multi-step chain.

    Milk becomes cheese and whey; cheese becomes a topping. Allocate at each
    step and the choices multiply, and a downstream factor cannot be traced back
    to the assumptions that produced it. Each step here records its own basis,
    so the trail survives to the end.
    """
    if not steps:
        raise AllocationError("A chain needs at least one step")

    carried = 0.0
    trail = []
    for n, step in enumerate(steps):
        process = step.get("process")
        basis = step.get("basis", ECONOMIC)
        output = step.get("output")
        quantity = float(step.get("quantity", 1.0))
        if quantity <= 0:
            raise AllocationError(f"Step {n + 1} has a non-positive quantity")

        entry = get_process(process)
        if output not in entry["outputs"]:
            raise AllocationError(f"{output} is not an output of {process}")

        result = allocate(process, basis)
        line = next(row for row in result["lines"] if row["output"] == output)

        # The burden carried in from the step before is added to this step's own
        # burden before it is allocated onwards - it belongs to the input, and
        # the input is being turned into these outputs.
        own = line["per_kg"] * quantity
        inherited = carried
        carried = own + inherited

        trail.append({
            "step": n + 1,
            "process": process,
            "process_label": entry["label"],
            "basis": basis,
            "basis_label": BASIS_LABELS[basis],
            "output": output,
            "output_label": entry["outputs"][output]["label"],
            "quantity": quantity,
            "own_kg_co2e": round(own, 6),
            "inherited_kg_co2e": round(inherited, 6),
            "running_kg_co2e": round(carried, 6),
            "share_at_this_step": round(line["share"], 6),
        })

    bases = {step["basis"] for step in trail}
    return {
        "steps": trail,
        "total_kg_co2e": round(carried, 6),
        "bases_used": sorted(bases),
        "mixed_bases": len(bases) > 1,
        "final_output": trail[-1]["output_label"],
    }


def chain_across_bases(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The same chain under each basis applied consistently throughout."""
    rows = []
    for basis in PARTITIONING_BASES:
        attempt = [dict(step, basis=basis) for step in steps]
        try:
            result = chain(attempt)
        except AllocationError as exc:
            rows.append({
                "basis": basis,
                "basis_label": BASIS_LABELS[basis],
                "total_kg_co2e": None,
                "error": str(exc),
            })
            continue
        rows.append({
            "basis": basis,
            "basis_label": BASIS_LABELS[basis],
            "total_kg_co2e": result["total_kg_co2e"],
            "error": None,
        })
    return rows


# ---------------------------------------------------------------------------
# Recycling allocation
# ---------------------------------------------------------------------------

def recycling_allocation(
    material: str,
    method: str,
    recycled_content: float | None = None,
    recovery_rate: float | None = None,
) -> dict[str, Any]:
    """Distribute the benefit of recycling between producer and next user.

    The three methods give different answers for the same physical system, and
    the difference is not arithmetic - it is about which lever gets rewarded.
    Cut-off rewards buying recycled content and is indifferent to what happens
    afterwards. Avoided burden rewards designing for recovery and is indifferent
    to what the product was made from. Fifty-fifty halves both.
    """
    entry = get_material(material)
    if method not in RECYCLING_METHODS:
        raise AllocationError(f"Unknown recycling method: {method}")

    content = (
        entry["recycled_content"] if recycled_content is None
        else float(recycled_content)
    )
    recovery = (
        entry["recovery_rate"] if recovery_rate is None else float(recovery_rate)
    )
    if not 0.0 <= content <= 1.0:
        raise AllocationError("Recycled content must be a fraction between 0 and 1")
    if not 0.0 <= recovery <= 1.0:
        raise AllocationError("Recovery rate must be a fraction between 0 and 1")

    virgin = entry["virgin_kg_co2e"]
    recycled = entry["recycled_kg_co2e"]
    saving = virgin - recycled

    if method == CUT_OFF:
        burden = (1.0 - content) * virgin + content * recycled
        rewards_content, rewards_recovery = True, False
    elif method == AVOIDED_BURDEN:
        burden = virgin - recovery * saving
        rewards_content, rewards_recovery = False, True
    else:
        blended = (content + recovery) / 2.0
        burden = (1.0 - blended) * virgin + blended * recycled
        rewards_content, rewards_recovery = True, True

    return {
        "material": material,
        "label": entry["label"],
        "method": method,
        "method_label": RECYCLING_METHOD_LABELS[method],
        "method_note": RECYCLING_METHOD_NOTES[method],
        "virgin_kg_co2e": virgin,
        "recycled_kg_co2e": recycled,
        "recycled_content": content,
        "recovery_rate": recovery,
        "burden_kg_co2e": round(burden, 6),
        "saving_vs_virgin": round(virgin - burden, 6),
        "rewards_recycled_content": rewards_content,
        "rewards_recyclability": rewards_recovery,
    }


def compare_recycling_methods(
    material: str,
    recycled_content: float | None = None,
    recovery_rate: float | None = None,
) -> dict[str, Any]:
    """All three methods on one material, with what each one rewards."""
    rows = [
        recycling_allocation(material, method, recycled_content, recovery_rate)
        for method in RECYCLING_METHODS
    ]
    burdens = [row["burden_kg_co2e"] for row in rows]
    return {
        "material": material,
        "label": get_material(material)["label"],
        "note": get_material(material)["note"],
        "rows": rows,
        "low": round(min(burdens), 6),
        "high": round(max(burdens), 6),
        "spread": round(max(burdens) - min(burdens), 6),
        "ratio": round(max(burdens) / min(burdens), 3) if min(burdens) > 0 else None,
    }


def get_allocation_insights(comparison: dict[str, Any]) -> list[str]:
    """Plain-language readings of a basis comparison."""
    if not comparison.get("rows"):
        return ["Nothing to analyse."]

    insights: list[str] = []
    widest = max(
        (row for row in comparison["rows"] if row.get("ratio")),
        key=lambda row: row["ratio"],
        default=None,
    )
    if widest:
        insights.append(
            f"{widest['label']} carries "
            f"{widest['ratio']:.2f} times as much on "
            f"{BASIS_LABELS[widest['high_basis']].lower()} as on "
            f"{BASIS_LABELS[widest['low_basis']].lower()}. That ratio is the "
            "real uncertainty on its footprint, and no measurement will "
            "narrow it."
        )

    if comparison.get("unavailable_bases"):
        for basis, reason in comparison["unavailable_bases"].items():
            if basis in PARTITIONING_BASES:
                insights.append(reason)

    negatives = [
        key for key, value in comparison.get("expansions", {}).items()
        if value.get("is_negative")
    ]
    if negatives:
        labels = ", ".join(
            row["label"] for row in comparison["rows"] if row["output"] in negatives
        )
        insights.append(
            f"Under system expansion, {labels} comes out below zero — the "
            "co-products displace more than the process emits. That is what "
            "the method says, and it is why it cannot be mixed into an "
            "allocated total."
        )

    insights.append(
        "None of these is more correct than the others. The standards prefer "
        "a physical relationship where one exists, and where it does not, the "
        "choice is a judgement that should be stated rather than absorbed."
    )
    return insights


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def init_allocation_db() -> bool:
    """Create the table if it does not exist yet."""
    conn = None
    try:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS allocation_studies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                process TEXT NOT NULL,
                basis TEXT NOT NULL,
                burden_kg_co2e REAL NOT NULL,
                widest_ratio REAL,
                detail_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Unable to initialise allocation table: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_study(
    user_id: int,
    name: str,
    process: str,
    basis: str,
    comparison: dict[str, Any],
) -> int | None:
    """Persist a study. Returns the row id or None."""
    init_allocation_db()
    conn = None
    try:
        conn = _connect()
        ratios = [row["ratio"] for row in comparison.get("rows", []) if row.get("ratio")]
        cursor = conn.execute(
            """
            INSERT INTO allocation_studies (
                user_id, name, process, basis, burden_kg_co2e,
                widest_ratio, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(name),
                str(process),
                str(basis),
                float(comparison.get("burden_kg_co2e", 0.0)),
                max(ratios) if ratios else None,
                json.dumps(comparison),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save allocation study: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_studies(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Saved studies, newest first."""
    init_allocation_db()
    conn = None
    try:
        conn = _connect()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM allocation_studies
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        studies = []
        for row in rows:
            record = dict(row)
            if record.get("detail_json"):
                try:
                    record["detail"] = json.loads(record["detail_json"])
                except (TypeError, ValueError):
                    record["detail"] = None
            studies.append(record)
        return studies
    except sqlite3.Error as exc:
        logger.error("Unable to read allocation studies: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def delete_study(study_id: int, user_id: int) -> bool:
    """Delete a study the user owns."""
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            "DELETE FROM allocation_studies WHERE id = ? AND user_id = ?",
            (int(study_id), int(user_id)),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Unable to delete allocation study: %s", exc)
        return False
    finally:
        if conn:
            conn.close()
