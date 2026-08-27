"""Whole-life carbon for a renovation, counted against a real starting debt.

``carbon_payback.py`` tells a user how much operational carbon a measure saves.
It does not count what the measure costs to build. Insulation, glazing, a heat
pump, a floor slab - all of it carries manufacturing and installation emissions
that land in the atmosphere the moment the work is done, while the savings
arrive slowly over the following decades.

Computing payback against zero makes every retrofit look worth doing. Some are
not. Replacing serviceable double glazing with triple glazing on a house already
heated by a heat pump takes longer to pay back than the units themselves last,
which means it never pays back at all - it moves emissions forward in time and
calls it an improvement.

The functional unit is the job, not the kilogram
-------------------------------------------------
Insulation compared per kilogram is meaningless, because the materials have
different conductivities and you need different thicknesses of each to do the
same job. Everything here is compared at a **target U-value over a square
metre**, with the thickness derived from the conductivity rather than assumed.
Mineral wool and PIR look very different per kilogram and much closer per unit
of thermal performance.

Stages kept apart, per EN 15978
--------------------------------
*   **A1-A3** product stage, cradle to factory gate.
*   **A4** transport to site. Negligible for local mineral wool, not negligible
    for imported stone.
*   **A5** construction, including installation waste. A 10% cut-and-fit waste
    rate on a rigid board is a real 10% addition to A1-A3, not a rounding error.
*   **B4** replacement over the assessment period. A component with a 20-year
    life inside a 60-year study is manufactured three times, and a "low carbon"
    material replaced twice as often is not low carbon.
*   **C3-C4** end of life.
*   **D** benefits beyond the system boundary.

Module D is reported and never netted
--------------------------------------
Module D is where optimistic recycling assumptions get smuggled into a total. A
steel section credited with its future recycling looks better than a timber one,
on the strength of a recycling market that has to still exist in sixty years. It
is computed here, shown separately, and excluded from every total this module
calls a total.

Timing, which the app is currently inconsistent about
------------------------------------------------------
Upfront carbon is emitted now; the savings accrue later. ``climate_metrics.py``
implements GWP* precisely because when a forcing happens matters. Flat payback
arithmetic contradicts that. Both views are reported: undiscounted tonnes, and a
time-weighted figure that does not treat a tonne saved in 2065 as equal to a
tonne emitted today.

Biogenic carbon, both ways
---------------------------
Timber stores carbon. Whether that counts depends on the convention: -1/+1
credits the sequestration and charges the release, 0/0 does neither. They give
different answers for timber and identical answers for everything else. Both are
shown, following the precedent set by ``lca_allocation.py``, because presenting
one as settled would be the real error.

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


class BuildingLCAError(ValueError):
    """Raised when a whole-life calculation was asked for something incoherent."""


# ---------------------------------------------------------------------------
# Assessment period
#
# EN 15978 uses 60 years for a dwelling by convention. The choice is not
# neutral: a short period flatters short-lived materials by hiding their
# replacements, and a long one flatters durable ones. It is a parameter.
# ---------------------------------------------------------------------------
DEFAULT_ASSESSMENT_PERIOD = 60
ASSESSMENT_PERIODS = (30, 60, 100)

# Mass fraction of carbon in dry timber, and the CO2 it represents.
CARBON_FRACTION_DRY_TIMBER = 0.50
CO2_PER_CARBON = 44.0 / 12.0


# ---------------------------------------------------------------------------
# Materials
#
# ``a1_a3`` is kg CO2e per kg of product at the factory gate, on the 0/0
# biogenic convention - that is, sequestration is not credited in the headline
# figure. ``biogenic_fraction`` is the dry mass fraction that is biogenic carbon
# feedstock, used to derive the -1/+1 alternative.
#
# ``conductivity`` is W/mK and is what makes a like-for-like comparison
# possible. ``service_life`` drives B4 and is the number most often left out of
# comparisons that flatter cheap materials.
# ---------------------------------------------------------------------------
MATERIALS = {
    "mineral_wool": {
        "label": "Mineral wool (glass or rock)",
        "category": "insulation",
        "density": 32.0, "conductivity": 0.037,
        "a1_a3": 1.28, "biogenic_fraction": 0.0,
        "service_life": 60, "install_waste": 0.05,
        "default_transport_km": 300.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.85, "incineration": 0.10, "recycling": 0.05},
        "note": "Low embodied carbon per kilogram and low density, so a very "
                "low figure per square metre. Needs more thickness than PIR for "
                "the same U-value, which costs space rather than carbon.",
    },
    "wood_fibre": {
        "label": "Wood fibre board",
        "category": "insulation",
        "density": 50.0, "conductivity": 0.040,
        "a1_a3": 0.92, "biogenic_fraction": 0.80,
        "service_life": 60, "install_waste": 0.07,
        "default_transport_km": 700.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.30, "incineration": 0.65, "recycling": 0.05},
        "note": "The material where the biogenic convention matters most. On "
                "the -1/+1 basis it is close to carbon neutral upfront and "
                "gives most of it back at end of life; on 0/0 it is simply a "
                "modest performer.",
    },
    "pir_board": {
        "label": "PIR rigid board",
        "category": "insulation",
        "density": 32.0, "conductivity": 0.022,
        "a1_a3": 4.26, "biogenic_fraction": 0.0,
        "service_life": 40, "install_waste": 0.12,
        "default_transport_km": 300.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.90, "incineration": 0.10, "recycling": 0.0},
        "note": "Roughly three times the embodied carbon per kilogram of "
                "mineral wool, but you need far less of it. High cut-and-fit "
                "waste because it is a rigid board being fitted between joists.",
    },
    "eps": {
        "label": "Expanded polystyrene (EPS)",
        "category": "insulation",
        "density": 20.0, "conductivity": 0.036,
        "a1_a3": 3.29, "biogenic_fraction": 0.0,
        "service_life": 50, "install_waste": 0.10,
        "default_transport_km": 250.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.80, "incineration": 0.18, "recycling": 0.02},
        "note": "Very low density, so the per-square-metre figure is better "
                "than the per-kilogram figure suggests.",
    },
    "cellulose": {
        "label": "Blown cellulose (recycled paper)",
        "category": "insulation",
        "density": 45.0, "conductivity": 0.039,
        "a1_a3": 0.28, "biogenic_fraction": 0.85,
        "service_life": 50, "install_waste": 0.03,
        "default_transport_km": 200.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.50, "incineration": 0.45, "recycling": 0.05},
        "note": "The lowest upfront carbon of any insulation here, because the "
                "feedstock is waste paper. Blown rather than cut, so almost no "
                "installation waste.",
    },
    "sheeps_wool": {
        "label": "Sheep's wool batt",
        "category": "insulation",
        "density": 25.0, "conductivity": 0.038,
        "a1_a3": 0.98, "biogenic_fraction": 0.50,
        "service_life": 50, "install_waste": 0.06,
        "default_transport_km": 500.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.60, "incineration": 0.35, "recycling": 0.05},
        "note": "Allocation-sensitive: whether wool carries any of the sheep's "
                "footprint depends on the co-product split, which is exactly "
                "the choice lca_allocation.py exists to make visible.",
    },
    "aerogel": {
        "label": "Aerogel blanket",
        "category": "insulation",
        "density": 150.0, "conductivity": 0.015,
        "a1_a3": 18.50, "biogenic_fraction": 0.0,
        "service_life": 40, "install_waste": 0.08,
        "default_transport_km": 1500.0, "transport_mode": "sea_container",
        "eol": {"landfill": 1.0, "incineration": 0.0, "recycling": 0.0},
        "note": "The thinnest option by a wide margin and by far the highest "
                "embodied carbon. Justifiable where thickness is genuinely "
                "constrained and indefensible where it is not.",
    },
    "double_glazing": {
        "label": "Double glazed unit (whole window, uPVC)",
        "category": "glazing",
        "density": 1.0, "conductivity": None,
        "unit_u_value": 1.40, "mass_per_m2": 28.0,
        "a1_a3": 3.20, "biogenic_fraction": 0.0,
        "service_life": 30, "install_waste": 0.02,
        "default_transport_km": 200.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.60, "incineration": 0.10, "recycling": 0.30},
        "note": "Priced per square metre of whole window including frame, "
                "because that is the unit a person buys.",
    },
    "triple_glazing": {
        "label": "Triple glazed unit (whole window, uPVC)",
        "category": "glazing",
        "density": 1.0, "conductivity": None,
        "unit_u_value": 0.80, "mass_per_m2": 39.0,
        "a1_a3": 3.40, "biogenic_fraction": 0.0,
        "service_life": 30, "install_waste": 0.02,
        "default_transport_km": 400.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.60, "incineration": 0.10, "recycling": 0.30},
        "note": "Around 40% more mass than a double glazed unit for a 0.6 W/m2K "
                "improvement. Against serviceable double glazing on a gas "
                "boiler the payback runs to about two decades; on a heat pump "
                "it exceeds the unit's own service life and never repays.",
    },
    "concrete_c30": {
        "label": "Concrete C30/37 (CEM I)",
        "category": "structure",
        "density": 2400.0, "conductivity": 1.60,
        "a1_a3": 0.132, "biogenic_fraction": 0.0,
        "service_life": 60, "install_waste": 0.05,
        "default_transport_km": 40.0, "transport_mode": "hgv_rigid",
        "eol": {"landfill": 0.10, "incineration": 0.0, "recycling": 0.90},
        "note": "Low per kilogram and enormous in total, because a slab is "
                "measured in tonnes. Structure is where whole-life carbon is "
                "decided in almost every project.",
    },
    "concrete_ggbs": {
        "label": "Concrete C30/37 (50% GGBS)",
        "category": "structure",
        "density": 2400.0, "conductivity": 1.50,
        "a1_a3": 0.079, "biogenic_fraction": 0.0,
        "service_life": 60, "install_waste": 0.05,
        "default_transport_km": 60.0, "transport_mode": "hgv_rigid",
        "eol": {"landfill": 0.10, "incineration": 0.0, "recycling": 0.90},
        "note": "Cement replacement cuts roughly 40% at no structural cost for "
                "most domestic work. The supply of GGBS is finite and falling, "
                "so this is not a solution that scales indefinitely.",
    },
    "clay_brick": {
        "label": "Clay brick",
        "category": "structure",
        "density": 1900.0, "conductivity": 0.77,
        "a1_a3": 0.213, "biogenic_fraction": 0.0,
        "service_life": 60, "install_waste": 0.08,
        "default_transport_km": 150.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.40, "incineration": 0.0, "recycling": 0.60},
        "note": "Fired, so the kiln fuel dominates. Long-lived enough that "
                "replacement never enters a 60-year study.",
    },
    "structural_timber": {
        "label": "Structural softwood timber",
        "category": "structure",
        "density": 500.0, "conductivity": 0.13,
        "a1_a3": 0.263, "biogenic_fraction": 0.90,
        "service_life": 60, "install_waste": 0.10,
        "default_transport_km": 800.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.20, "incineration": 0.75, "recycling": 0.05},
        "note": "The clearest case for showing both biogenic conventions. On "
                "-1/+1 the upfront figure goes negative; on 0/0 it does not.",
    },
    "structural_steel": {
        "label": "Structural steel section",
        "category": "structure",
        "density": 7850.0, "conductivity": 50.0,
        "a1_a3": 1.55, "biogenic_fraction": 0.0,
        "service_life": 60, "install_waste": 0.02,
        "default_transport_km": 400.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.02, "incineration": 0.0, "recycling": 0.98},
        "note": "The material module D was invented for. Credited with its "
                "future recycling it looks competitive with timber, on the "
                "strength of a market that has to still exist in sixty years.",
    },
    "plasterboard": {
        "label": "Plasterboard",
        "category": "finish",
        "density": 700.0, "conductivity": 0.25,
        "a1_a3": 0.39, "biogenic_fraction": 0.0,
        "service_life": 30, "install_waste": 0.15,
        "default_transport_km": 200.0, "transport_mode": "hgv_articulated",
        "eol": {"landfill": 0.70, "incineration": 0.0, "recycling": 0.30},
        "note": "High installation waste - boards are cut to fit and offcuts "
                "are rarely reused. Replaced once in a 60-year study.",
    },
}

# Categories that are compared at a target U-value rather than by mass.
THERMAL_CATEGORIES = ("insulation",)


# ---------------------------------------------------------------------------
# A4 transport
#
# kg CO2e per tonne-kilometre. The spread between modes is what makes A4 worth
# separating: the same material sourced locally or shipped from another
# continent differs by more than most product substitutions do.
# ---------------------------------------------------------------------------
TRANSPORT_MODES = {
    "hgv_rigid": {
        "label": "Rigid lorry (local delivery)",
        "factor": 0.196,
        "note": "Short runs, part loads, poor tonne-km efficiency - but the "
                "distances are short enough that it rarely matters.",
    },
    "hgv_articulated": {
        "label": "Articulated lorry",
        "factor": 0.087,
        "note": "The default for construction materials moving within a "
                "country.",
    },
    "rail_freight": {
        "label": "Rail freight",
        "factor": 0.028,
        "note": "Roughly a third of road per tonne-km, and rarely available "
                "door to door without a road leg at each end.",
    },
    "sea_container": {
        "label": "Container ship",
        "factor": 0.016,
        "note": "Very low per tonne-km, which is why an imported material can "
                "still have a small A4 despite travelling a long way.",
    },
    "air_freight": {
        "label": "Air freight",
        "factor": 0.602,
        "note": "Thirty-five times sea freight. Essentially never justified for "
                "construction material.",
    },
}


# ---------------------------------------------------------------------------
# C3-C4 end of life
#
# kg CO2e per kg of material by disposal route, excluding the biogenic release
# which is handled by the convention chooser.
# ---------------------------------------------------------------------------
EOL_FACTORS = {
    "landfill": 0.008,
    "incineration": 0.021,
    "recycling": 0.013,
}

# Module D credits, kg CO2e per kg diverted to recycling. Negative because they
# are avoided burdens elsewhere. Never added into a total by this module.
MODULE_D_CREDIT = {
    "structural_steel": -0.68,
    "concrete_c30": -0.004,
    "concrete_ggbs": -0.004,
    "clay_brick": -0.006,
    "plasterboard": -0.012,
    "double_glazing": -0.055,
    "triple_glazing": -0.055,
}


# ---------------------------------------------------------------------------
# Heat supply
#
# Delivered-energy carbon intensity and system efficiency, used to turn a
# U-value improvement into an annual carbon saving. A heat pump on a decarbon-
# ising grid makes fabric measures pay back more slowly, not less - which is a
# genuinely counterintuitive result the module should not hide.
# ---------------------------------------------------------------------------
HEAT_SOURCES = {
    "gas_boiler": {
        "label": "Gas boiler",
        "intensity": 0.183, "efficiency": 0.86,
        "note": "The case where fabric measures pay back fastest, because the "
                "heat being saved is the most carbon-intensive.",
    },
    "oil_boiler": {
        "label": "Oil boiler",
        "intensity": 0.246, "efficiency": 0.84,
        "note": "Worse than gas per kWh, so payback is faster still.",
    },
    "resistive_electric": {
        "label": "Direct electric heating",
        "intensity": 0.207, "efficiency": 1.00,
        "note": "Efficiency of one, so every kWh saved is a kWh of electricity.",
    },
    "heat_pump": {
        "label": "Air source heat pump",
        "intensity": 0.207, "efficiency": 3.00,
        "note": "A seasonal coefficient of performance near three means the "
                "same fabric measure saves a third as much carbon, so it pays "
                "back roughly three times more slowly. Worth doing anyway - "
                "but the number should say so honestly.",
    },
    "district_heat": {
        "label": "District heat network",
        "intensity": 0.150, "efficiency": 0.92,
        "note": "Varies enormously by scheme; this is a mid-range value.",
    },
}

# Degree days for a temperate heating climate, K.day. ``degree_days.py`` holds
# the proper location-specific model; this is a default so the engine stays
# importable on its own.
DEFAULT_HEATING_DEGREE_DAYS = 2100.0


def list_materials(category: str | None = None) -> list:
    """Material keys, optionally filtered by category."""
    keys = sorted(MATERIALS)
    if category is None:
        return keys
    return [k for k in keys if MATERIALS[k]["category"] == category]


def list_categories() -> list:
    """Distinct material categories."""
    return sorted({v["category"] for v in MATERIALS.values()})


def get_material(key: str) -> dict:
    """One material's data, refusing an unknown key.

    There is no sensible average across this table - the insulations alone span
    a factor of sixty in embodied carbon per kilogram - so an unknown key is an
    error rather than an invitation to guess.
    """
    try:
        return dict(MATERIALS[key])
    except KeyError:
        raise BuildingLCAError(
            f"No data for material '{key}'. This table spans a factor of sixty "
            f"in embodied carbon per kilogram, so no average would mean "
            f"anything. Known materials: {', '.join(list_materials())}"
        ) from None


def thickness_for_u_value(
    material: str, target_u: float, existing_u: float
) -> float:
    """Metres of insulation needed to take an element from existing to target U.

    This is what makes a like-for-like comparison possible. Aerogel and mineral
    wool are not comparable per kilogram; they are comparable at a U-value.
    """
    spec = get_material(material)
    conductivity = spec.get("conductivity")
    if not conductivity:
        raise BuildingLCAError(
            f"'{material}' has no conductivity, so it cannot be sized to a "
            f"U-value. Glazing is specified as a whole unit instead."
        )
    if target_u <= 0 or existing_u <= 0:
        raise BuildingLCAError("U-values must be positive.")
    if target_u >= existing_u:
        raise BuildingLCAError(
            f"Target U-value {target_u} is no better than the existing "
            f"{existing_u}. There is nothing to insulate for."
        )

    added_resistance = (1.0 / target_u) - (1.0 / existing_u)
    return added_resistance * conductivity


def u_value_after(material: str, thickness_m: float, existing_u: float) -> float:
    """Resulting U-value from adding a given thickness."""
    spec = get_material(material)
    conductivity = spec.get("conductivity")
    if not conductivity:
        raise BuildingLCAError(f"'{material}' has no conductivity.")
    if thickness_m < 0:
        raise BuildingLCAError("Thickness cannot be negative.")
    if existing_u <= 0:
        raise BuildingLCAError("Existing U-value must be positive.")

    return 1.0 / ((1.0 / existing_u) + (thickness_m / conductivity))


def replacement_count(service_life: int, assessment_period: int) -> int:
    """How many times a component is manufactured again inside the study period.

    A component whose life equals the period is never replaced. One with half
    the period is replaced once. The convention matters because it is the single
    largest source of disagreement between whole-life studies of the same
    building.
    """
    if service_life <= 0:
        raise BuildingLCAError("Service life must be positive.")
    if assessment_period <= 0:
        raise BuildingLCAError("Assessment period must be positive.")

    return max(0, math.ceil(assessment_period / service_life) - 1)


def biogenic_storage(material: str, mass_kg: float) -> float:
    """kg CO2 stored in the biogenic fraction of a material.

    Positive number, representing carbon held out of the atmosphere. Whether it
    counts is the convention question, not a property of the material.
    """
    spec = get_material(material)
    fraction = spec.get("biogenic_fraction", 0.0)
    if mass_kg < 0:
        raise BuildingLCAError("Mass cannot be negative.")
    return mass_kg * fraction * CARBON_FRACTION_DRY_TIMBER * CO2_PER_CARBON


def whole_life_carbon(
    material: str,
    area_m2: float,
    thickness_m: float | None = None,
    assessment_period: int = DEFAULT_ASSESSMENT_PERIOD,
    transport_km: float | None = None,
    transport_mode: str | None = None,
    biogenic_convention: str = "0/0",
) -> dict:
    """Every EN 15978 stage for one element, with module D kept outside.

    ``thickness_m`` is required for materials sized by thickness and ignored for
    those specified per square metre of finished unit.
    """
    spec = get_material(material)
    if area_m2 <= 0:
        raise BuildingLCAError("Area must be positive.")
    if biogenic_convention not in ("0/0", "-1/+1"):
        raise BuildingLCAError(
            "Biogenic convention must be '0/0' or '-1/+1'. Both are defensible "
            "and they disagree for timber, which is why neither is a default "
            "you can ignore."
        )

    if spec.get("mass_per_m2") is not None:
        mass = spec["mass_per_m2"] * area_m2
    else:
        if thickness_m is None or thickness_m <= 0:
            raise BuildingLCAError(
                f"'{material}' is sized by thickness, so a positive thickness "
                f"is required."
            )
        mass = spec["density"] * thickness_m * area_m2

    waste_fraction = spec["install_waste"]
    mass_delivered = mass * (1.0 + waste_fraction)

    mode = transport_mode or spec["transport_mode"]
    if mode not in TRANSPORT_MODES:
        raise BuildingLCAError(
            f"Unknown transport mode '{mode}'. Known modes: "
            f"{', '.join(sorted(TRANSPORT_MODES))}"
        )
    distance = spec["default_transport_km"] if transport_km is None else transport_km
    if distance < 0:
        raise BuildingLCAError("Transport distance cannot be negative.")

    replacements = replacement_count(spec["service_life"], assessment_period)

    # A1-A3 on the installed mass, with the offcuts charged in A5 rather than
    # hidden inside the product stage.
    a1_a3 = mass * spec["a1_a3"]
    a5_waste_product = mass * waste_fraction * spec["a1_a3"]
    a5_waste_disposal = mass * waste_fraction * _eol_rate(spec)
    a5 = a5_waste_product + a5_waste_disposal

    a4 = mass_delivered / 1000.0 * distance * TRANSPORT_MODES[mode]["factor"]

    # Each replacement repeats the product, transport, construction and the
    # disposal of what it replaced.
    single_cycle = a1_a3 + a4 + a5
    b4 = replacements * (single_cycle + mass * _eol_rate(spec))

    c3_c4 = mass * _eol_rate(spec)

    module_d = MODULE_D_CREDIT.get(material, 0.0) * mass * (1 + replacements)

    stored = biogenic_storage(material, mass * (1 + replacements))
    if biogenic_convention == "-1/+1":
        # Sequestration credited at manufacture, release charged at end of life.
        # For anything landfilled or recycled the release is deferred, but the
        # convention charges it within the study period regardless, which is the
        # conservative reading.
        biogenic_upfront = -stored
        biogenic_eol = stored
    else:
        biogenic_upfront = 0.0
        biogenic_eol = 0.0

    upfront = a1_a3 + a4 + a5 + biogenic_upfront
    total = upfront + b4 + c3_c4 + biogenic_eol

    return {
        "material": material,
        "label": spec["label"],
        "category": spec["category"],
        "area_m2": area_m2,
        "thickness_m": thickness_m,
        "mass_kg": mass,
        "mass_delivered_kg": mass_delivered,
        "install_waste_fraction": waste_fraction,
        "assessment_period": assessment_period,
        "replacements": replacements,
        "service_life": spec["service_life"],
        "transport_km": distance,
        "transport_mode": mode,
        "biogenic_convention": biogenic_convention,
        "biogenic_stored_kg_co2": stored,
        "stages": {
            "A1-A3": a1_a3,
            "A4": a4,
            "A5": a5,
            "B4": b4,
            "C3-C4": c3_c4,
        },
        "biogenic_upfront": biogenic_upfront,
        "biogenic_eol": biogenic_eol,
        "upfront_kg_co2e": upfront,
        "total_kg_co2e": total,
        "module_d_kg_co2e": module_d,
        "module_d_excluded_from_total": True,
        "module_d_warning": (
            "Module D is a credit for a benefit that occurs outside this "
            "system boundary, decades from now, in a recycling market that has "
            "to still exist. It is reported and never netted into a total."
        ),
        "note": spec["note"],
    }


def _eol_rate(spec: dict) -> float:
    """Weighted end-of-life factor, kg CO2e per kg, from the disposal split."""
    return sum(
        share * EOL_FACTORS[route] for route, share in spec["eol"].items()
    )


def operational_saving(
    area_m2: float,
    u_before: float,
    u_after: float,
    heat_source: str = "gas_boiler",
    degree_days: float = DEFAULT_HEATING_DEGREE_DAYS,
) -> dict:
    """Annual carbon and energy saved by a U-value improvement.

    Heat loss through an element is U x A x degree days x 24 hours, in watt
    hours. The delivered energy is that divided by the system efficiency, and
    the carbon is the delivered energy times the intensity of the fuel.
    """
    if area_m2 <= 0:
        raise BuildingLCAError("Area must be positive.")
    if u_before <= 0 or u_after <= 0:
        raise BuildingLCAError("U-values must be positive.")
    if u_after >= u_before:
        raise BuildingLCAError(
            "The improved U-value must be lower than the existing one."
        )
    try:
        source = HEAT_SOURCES[heat_source]
    except KeyError:
        raise BuildingLCAError(
            f"Unknown heat source '{heat_source}'. Known sources: "
            f"{', '.join(sorted(HEAT_SOURCES))}"
        ) from None
    if degree_days <= 0:
        raise BuildingLCAError("Heating degree days must be positive.")

    heat_saved_kwh = (u_before - u_after) * area_m2 * degree_days * 24.0 / 1000.0
    delivered_kwh = heat_saved_kwh / source["efficiency"]
    carbon = delivered_kwh * source["intensity"]

    return {
        "heat_saved_kwh": heat_saved_kwh,
        "delivered_kwh": delivered_kwh,
        "annual_kg_co2e": carbon,
        "heat_source": heat_source,
        "heat_source_label": source["label"],
        "efficiency": source["efficiency"],
        "intensity": source["intensity"],
        "degree_days": degree_days,
        "note": source["note"],
    }


def carbon_payback(
    upfront_kg_co2e: float,
    annual_saving_kg_co2e: float,
    service_life: int,
) -> dict:
    """Years to repay the upfront carbon, and whether it repays at all.

    A measure that takes longer to pay back than the component lasts does not
    pay back. It moves emissions forward in time. The result says that in words
    rather than printing a large number and leaving the reader to notice.
    """
    if upfront_kg_co2e < 0:
        # Negative upfront happens on the -1/+1 convention for timber, and it is
        # not a payback question at all.
        return {
            "years": 0.0,
            "pays_back": True,
            "within_service_life": True,
            "verdict": (
                "Upfront carbon is negative under this biogenic convention, so "
                "there is no debt to repay. That result is a property of the "
                "convention, not of the building."
            ),
        }
    if annual_saving_kg_co2e <= 0:
        return {
            "years": None,
            "pays_back": False,
            "within_service_life": False,
            "verdict": (
                "There is no annual saving, so the upfront carbon is never "
                "repaid."
            ),
        }

    years = upfront_kg_co2e / annual_saving_kg_co2e
    within = years <= service_life

    if years <= 2:
        verdict = (
            f"Repaid in {years:.1f} years. On this timescale the upfront carbon "
            f"is close to irrelevant and the measure is unambiguous."
        )
    elif within:
        verdict = (
            f"Repaid in {years:.1f} years, inside the component's {service_life}"
            f"-year service life. The upfront carbon is real and it is repaid."
        )
    else:
        verdict = (
            f"Payback is {years:.1f} years against a {service_life}-year service "
            f"life. This measure does not pay back. It brings emissions forward "
            f"and replaces the component before the saving catches up."
        )

    return {
        "years": years,
        "pays_back": within,
        "within_service_life": within,
        "service_life": service_life,
        "verdict": verdict,
    }


def time_weighted_payback(
    upfront_kg_co2e: float,
    annual_saving_kg_co2e: float,
    assessment_period: int = DEFAULT_ASSESSMENT_PERIOD,
    discount_rate: float = 0.03,
) -> dict:
    """Net whole-life carbon with future savings discounted.

    Flat arithmetic treats a tonne saved in 2065 as equal to a tonne emitted
    today, which contradicts the reasoning GWP* in ``climate_metrics.py`` is
    built on. Both views are returned so the gap is visible.
    """
    if assessment_period <= 0:
        raise BuildingLCAError("Assessment period must be positive.")
    if not 0.0 <= discount_rate < 1.0:
        raise BuildingLCAError("Discount rate must lie between 0 and 1.")

    undiscounted = annual_saving_kg_co2e * assessment_period
    discounted = sum(
        annual_saving_kg_co2e / ((1.0 + discount_rate) ** year)
        for year in range(1, assessment_period + 1)
    )

    return {
        "upfront_kg_co2e": upfront_kg_co2e,
        "undiscounted_saving": undiscounted,
        "discounted_saving": discounted,
        "undiscounted_net": undiscounted - upfront_kg_co2e,
        "discounted_net": discounted - upfront_kg_co2e,
        "discount_rate": discount_rate,
        "assessment_period": assessment_period,
        "weighting_loss": (
            (undiscounted - discounted) / undiscounted if undiscounted else 0.0
        ),
        "note": (
            "Discounting carbon is contested. It is shown because the "
            "alternative - treating a tonne in 2065 as identical to a tonne "
            "today - is a position too, and an unstated one."
        ),
    }


def compare_at_u_value(
    materials: list,
    area_m2: float,
    target_u: float,
    existing_u: float,
    assessment_period: int = DEFAULT_ASSESSMENT_PERIOD,
    biogenic_convention: str = "0/0",
) -> list:
    """The like-for-like comparison: same job, same U-value, different materials.

    Materials without a conductivity are skipped rather than compared on a
    footing that does not exist for them.
    """
    rows = []
    for key in materials:
        spec = get_material(key)
        if not spec.get("conductivity") or spec["category"] not in THERMAL_CATEGORIES:
            continue
        thickness = thickness_for_u_value(key, target_u, existing_u)
        result = whole_life_carbon(
            key,
            area_m2,
            thickness_m=thickness,
            assessment_period=assessment_period,
            biogenic_convention=biogenic_convention,
        )
        rows.append({
            "material": key,
            "label": spec["label"],
            "thickness_mm": thickness * 1000.0,
            "mass_kg": result["mass_kg"],
            "upfront_kg_co2e": result["upfront_kg_co2e"],
            "total_kg_co2e": result["total_kg_co2e"],
            "replacements": result["replacements"],
            "per_m2": result["total_kg_co2e"] / area_m2,
            "note": spec["note"],
        })
    rows.sort(key=lambda row: row["total_kg_co2e"])
    return rows


def renovate_versus_rebuild(
    floor_area_m2: float,
    retrofit_upfront_kg_co2e: float,
    retrofit_annual_saving: float,
    new_build_carbon_per_m2: float = 550.0,
    demolition_carbon_per_m2: float = 60.0,
    new_build_annual_demand_kwh_per_m2: float = 25.0,
    existing_annual_demand_kwh_per_m2: float = 120.0,
    heat_source: str = "gas_boiler",
    assessment_period: int = DEFAULT_ASSESSMENT_PERIOD,
) -> dict:
    """The comparison the app currently cannot make.

    A new build is more efficient in operation and starts several hundred
    kilograms of CO2e per square metre in debt, plus the demolition of whatever
    stood there. The crossover typically lands within the same order as the
    assessment period, which is the real finding: the answer is decided by how
    deep the retrofit goes, not by which option sounds greener. A shallow
    retrofit of a very poor building can genuinely lose to a rebuild, and this
    function will say so.
    """
    if floor_area_m2 <= 0:
        raise BuildingLCAError("Floor area must be positive.")
    try:
        source = HEAT_SOURCES[heat_source]
    except KeyError:
        raise BuildingLCAError(f"Unknown heat source '{heat_source}'.") from None

    intensity_per_kwh = source["intensity"] / source["efficiency"]

    retrofit_demand = max(
        0.0,
        existing_annual_demand_kwh_per_m2
        - (retrofit_annual_saving / intensity_per_kwh / floor_area_m2
           if intensity_per_kwh > 0 else 0.0),
    )

    retrofit_operational = (
        retrofit_demand * floor_area_m2 * intensity_per_kwh * assessment_period
    )
    rebuild_operational = (
        new_build_annual_demand_kwh_per_m2 * floor_area_m2
        * intensity_per_kwh * assessment_period
    )
    # Demolishing the existing structure is part of the cost of rebuilding and
    # is charged to the rebuild option, where it belongs.
    rebuild_upfront = (
        new_build_carbon_per_m2 + demolition_carbon_per_m2
    ) * floor_area_m2

    retrofit_total = retrofit_upfront_kg_co2e + retrofit_operational
    rebuild_total = rebuild_upfront + rebuild_operational

    annual_operational_gap = (
        (retrofit_demand - new_build_annual_demand_kwh_per_m2)
        * floor_area_m2 * intensity_per_kwh
    )
    if annual_operational_gap > 0:
        crossover = (rebuild_upfront - retrofit_upfront_kg_co2e) / annual_operational_gap
    else:
        crossover = None

    return {
        "floor_area_m2": floor_area_m2,
        "assessment_period": assessment_period,
        "retrofit_upfront": retrofit_upfront_kg_co2e,
        "retrofit_operational": retrofit_operational,
        "retrofit_total": retrofit_total,
        "rebuild_upfront": rebuild_upfront,
        "demolition_carbon": demolition_carbon_per_m2 * floor_area_m2,
        "rebuild_operational": rebuild_operational,
        "rebuild_total": rebuild_total,
        "difference": rebuild_total - retrofit_total,
        "crossover_years": crossover,
        "better": "retrofit" if retrofit_total <= rebuild_total else "rebuild",
        "note": (
            "The carbon already embodied in the standing building is sunk under "
            "either option and is not counted on either side. Demolition is "
            "charged to the rebuild. The crossover year is the number to argue "
            "about: if it falls beyond the period anyone is actually planning "
            "for, the rebuild case rests on savings nobody will live to see."
        ),
    }


def get_lca_insights(result: dict) -> list:
    """Plain-language findings, emitted only where the result supports them."""
    insights = []
    stages = result["stages"]
    total = result["total_kg_co2e"]

    if total > 0:
        dominant = max(stages, key=stages.get)
        share = stages[dominant] / total * 100.0
        insights.append(
            f"{dominant} is {share:.0f}% of the whole-life total."
        )

    if result["replacements"] > 0:
        b4_share = stages["B4"] / total * 100.0 if total else 0.0
        insights.append(
            f"Replaced {result['replacements']} time(s) inside the "
            f"{result['assessment_period']}-year period, which is {b4_share:.0f}% "
            f"of the total. A study over a shorter period would hide this."
        )
    else:
        insights.append(
            f"A {result['service_life']}-year service life means no replacement "
            f"inside a {result['assessment_period']}-year study. Durability is "
            f"doing real work in this number."
        )

    waste_share = result["install_waste_fraction"] * 100.0
    if waste_share >= 10.0:
        insights.append(
            f"{waste_share:.0f}% installation waste. That is a real addition to "
            f"the product stage, charged in A5 rather than hidden inside A1-A3."
        )

    if result["module_d_kg_co2e"] < 0:
        insights.append(
            f"Module D would credit {abs(result['module_d_kg_co2e']):.0f} kg "
            f"CO2e. It is excluded from every total above."
        )

    if result["biogenic_stored_kg_co2"] > 0:
        if result["biogenic_convention"] == "0/0":
            insights.append(
                f"This material holds {result['biogenic_stored_kg_co2']:.0f} kg "
                f"of biogenic CO2, uncredited on the 0/0 convention. Switching "
                f"to -1/+1 would change the upfront figure substantially."
            )
        else:
            insights.append(
                f"Biogenic storage of {result['biogenic_stored_kg_co2']:.0f} kg "
                f"CO2 is credited upfront and charged back at end of life. The "
                f"whole-life total is unchanged; only the timing moves."
            )

    return insights


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _connect():
    return sqlite3.connect(DB_NAME)


def _ensure_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS building_lca_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            payload TEXT NOT NULL,
            upfront_kg_co2e REAL NOT NULL,
            total_kg_co2e REAL NOT NULL,
            payback_years REAL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_building_lca_user
        ON building_lca_projects (user_id)
        """
    )


def save_project(
    user_id: str, name: str, result: dict, payback: dict | None = None
) -> int:
    """Persist a whole-life result and return its row id."""
    if not user_id:
        raise BuildingLCAError("A project needs a user to belong to.")
    if not name or not name.strip():
        raise BuildingLCAError("A project needs a name.")

    payload = json.dumps({
        "material": result.get("material"),
        "area_m2": result.get("area_m2"),
        "thickness_m": result.get("thickness_m"),
        "stages": result.get("stages"),
        "assessment_period": result.get("assessment_period"),
        "replacements": result.get("replacements"),
        "module_d_kg_co2e": result.get("module_d_kg_co2e"),
        "biogenic_convention": result.get("biogenic_convention"),
        "payback": payback,
    })

    with _connect() as conn:
        _ensure_tables(conn)
        cursor = conn.execute(
            """
            INSERT INTO building_lca_projects
                (user_id, name, payload, upfront_kg_co2e, total_kg_co2e,
                 payback_years)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, name.strip(), payload,
                float(result["upfront_kg_co2e"]),
                float(result["total_kg_co2e"]),
                float(payback["years"]) if payback and payback.get("years") else None,
            ),
        )
        return int(cursor.lastrowid)


def get_projects(user_id: str) -> list:
    """Saved projects for a user, newest first."""
    if not user_id:
        return []
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            rows = conn.execute(
                """
                SELECT id, name, payload, upfront_kg_co2e, total_kg_co2e,
                       payback_years, created_at
                FROM building_lca_projects
                WHERE user_id = ?
                ORDER BY id DESC
                """,
                (user_id,),
            ).fetchall()
    except sqlite3.Error:
        logger.exception("Could not read saved building LCA projects")
        return []

    projects = []
    for row in rows:
        try:
            payload = json.loads(row[2])
        except (TypeError, ValueError):
            payload = {}
        projects.append({
            "id": row[0],
            "name": row[1],
            "payload": payload,
            "upfront_kg_co2e": row[3],
            "total_kg_co2e": row[4],
            "payback_years": row[5],
            "created_at": row[6],
        })
    return projects


def delete_project(user_id: str, project_id: int) -> bool:
    """Delete one saved project. Returns whether a row was removed."""
    if not user_id:
        return False
    try:
        with _connect() as conn:
            _ensure_tables(conn)
            cursor = conn.execute(
                "DELETE FROM building_lca_projects WHERE id = ? AND user_id = ?",
                (project_id, user_id),
            )
            return cursor.rowcount > 0
    except sqlite3.Error:
        logger.exception("Could not delete building LCA project %s", project_id)
        return False
