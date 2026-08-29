"""Fugitive refrigerant emissions, with TEWI and low-GWP retrofit comparison.

``src.carbon.ghg_inventory.py`` carries ``refrigerant_leakage`` as a single line item:
enter a quantity, multiply by a factor. That is the right shape for a category
where the user knows the number. Nobody knows how much refrigerant their fridge
leaked last year, so the category reads zero, and a zero in the largest
unreported scope 1 household source is not a small error.

Estimating it the other way round
---------------------------------
Commercial operators estimate leakage by mass balance - gas purchased minus gas
in stock. A household has no such record. The estimate has to run from what the
household *can* state: what the machine is, and roughly how big. Charge size and
a leak rate characteristic of the equipment class, which is a different
calculation rather than a rearrangement of the same one.

A domestic heat pump holds 1.5-3 kg of R-410A at a GWP of 2088. At a 3.5% annual
leak rate that is 200 kg CO2e a year from a machine bought to reduce src.carbon.emissions.

Lifetime is not annual times lifetime
-------------------------------------
There is an installation loss, an annual operating leak, and a disposal event
whose size depends entirely on whether the unit was degassed by someone
qualified or crushed with the charge still in it. The disposal event often
exceeds the whole operating life's leakage, and it is the one the owner
controls - but only at the moment of disposal, which is the moment nobody is
thinking about it.

Whether service top-ups count is a real choice and it is a parameter here. A
machine that is topped up holds its full charge to the end, so it leaks more in
total and has more left to recover; one that is not slowly empties and performs
worse while doing it.

Why direct emissions alone give wrong advice
--------------------------------------------
Propane has a GWP of 3 against R-410A's 2088, so direct emissions nearly vanish
on a swap. But if the replacement runs less efficiently the machine draws more
electricity, and on a carbon-intensive grid the indirect term dominates so
completely that a small efficiency penalty outweighs the entire direct saving.
On a clean grid it cannot. **The answer depends on grid intensity**, which is
what TEWI exists to express, and the useful output is not yes or no but the grid
intensity at which the answer changes.

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

DEFAULT_VINTAGE = "ar6"
DEFAULT_HORIZON = 100
VINTAGES = ("ar4", "ar5", "ar6")
HORIZONS = (20, 100)

# What a competent recovery achieves at end of life. Skip disposal recovers
# nothing; this is the default because it is neither, and the gap between the
# two is the point.
DEFAULT_RECOVERY = 0.70

# kg CO2e per kWh. The indirect half of TEWI is entirely at the mercy of this.
GRID_INTENSITIES: dict[str, float] = {
    "coal_heavy": 0.820,
    "gas_heavy": 0.490,
    "world_average": 0.475,
    "mixed": 0.280,
    "low_carbon": 0.120,
    "near_zero": 0.030,
}
DEFAULT_GRID_INTENSITY = 0.280


class RefrigerantError(ValueError):
    """Raised when equipment or a gas cannot be evaluated as given."""


# ---------------------------------------------------------------------------
# Refrigerant properties
#
# GWPs are given per assessment report and per horizon because both change the
# answer and neither is a detail. AR4 and AR6 disagree on R-410A by 21%, which
# is larger than several of the differences this module is used to src.reporting.report.
#
# The 20-year column matters more here than it does for CO2: this is a family of
# gases whose lifetimes run from days to decades, so the horizon does not
# rescale them, it reorders them.
# ---------------------------------------------------------------------------

REFRIGERANTS: dict[str, dict[str, Any]] = {
    "R-410A": {
        "label": "R-410A",
        "gwp": {"ar4": {100: 1725, 20: 4340}, "ar5": {100: 1924, 20: 4360},
                "ar6": {100: 2088, 20: 4705}},
        "lifetime_years": 17.0,
        "safety_class": "A1",
        "flammable": False,
        "phase_down": "restricted",
        "note": "The default in split air conditioning and most heat pumps.",
    },
    "R-32": {
        "label": "R-32",
        "gwp": {"ar4": {100: 675, 20: 2330}, "ar5": {100: 677, 20: 2430},
                "ar6": {100: 771, 20: 2693}},
        "lifetime_years": 5.4,
        "safety_class": "A2L",
        "flammable": True,
        "phase_down": "transitional",
        "note": "The common drop-in for R-410A. Mildly flammable, so it is not "
                "a straight swap in every installation.",
    },
    "R-134a": {
        "label": "R-134a",
        "gwp": {"ar4": {100: 1430, 20: 3830}, "ar5": {100: 1300, 20: 3710},
                "ar6": {100: 1526, 20: 4144}},
        "lifetime_years": 14.0,
        "safety_class": "A1",
        "flammable": False,
        "phase_down": "restricted",
        "note": "Vehicle air conditioning, dehumidifiers, heat pump dryers.",
    },
    "R-404A": {
        "label": "R-404A",
        "gwp": {"ar4": {100: 3922, 20: 6010}, "ar5": {100: 3943, 20: 6380},
                "ar6": {100: 4728, 20: 7258}},
        "lifetime_years": 15.0,
        "safety_class": "A1",
        "flammable": False,
        "phase_down": "banned_new",
        "note": "Commercial refrigeration. The highest GWP still in wide use.",
    },
    "R-407C": {
        "label": "R-407C",
        "gwp": {"ar4": {100: 1774, 20: 4160}, "ar5": {100: 1624, 20: 4110},
                "ar6": {100: 1908, 20: 4460}},
        "lifetime_years": 13.0,
        "safety_class": "A1",
        "flammable": False,
        "phase_down": "restricted",
        "note": "Older air conditioning and some heat pumps.",
    },
    "R-290": {
        "label": "R-290 (propane)",
        "gwp": {"ar4": {100: 3, 20: 3}, "ar5": {100: 3, 20: 3},
                "ar6": {100: 0.02, 20: 0.07}},
        "lifetime_years": 0.04,
        "safety_class": "A3",
        "flammable": True,
        "phase_down": "unrestricted",
        "note": "Highly flammable, so charge size is capped by regulation. "
                "AR6 revised its GWP from the conventional 3 to effectively "
                "zero, which is the largest vintage disagreement in the table.",
    },
    "R-600a": {
        "label": "R-600a (isobutane)",
        "gwp": {"ar4": {100: 3, 20: 3}, "ar5": {100: 3, 20: 3},
                "ar6": {100: 0.006, 20: 0.02}},
        "lifetime_years": 0.02,
        "safety_class": "A3",
        "flammable": True,
        "phase_down": "unrestricted",
        "note": "Already standard in domestic fridges and freezers.",
    },
    "R-1234yf": {
        "label": "R-1234yf",
        "gwp": {"ar4": {100: 4, 20: 4}, "ar5": {100: 1, 20: 4},
                "ar6": {100: 0.501, 20: 1.81}},
        "lifetime_years": 0.03,
        "safety_class": "A2L",
        "flammable": True,
        "phase_down": "unrestricted",
        "note": "Replacing R-134a in vehicle air conditioning.",
    },
    "R-744": {
        "label": "R-744 (carbon dioxide)",
        "gwp": {"ar4": {100: 1, 20: 1}, "ar5": {100: 1, 20: 1},
                "ar6": {100: 1, 20: 1}},
        "lifetime_years": 0.0,
        "safety_class": "A1",
        "flammable": False,
        "phase_down": "unrestricted",
        "note": "Runs at very high pressure and loses efficiency in hot "
                "climates, so the indirect term is where it is judged.",
    },
    "R-717": {
        "label": "R-717 (ammonia)",
        "gwp": {"ar4": {100: 0, 20: 0}, "ar5": {100: 0, 20: 0},
                "ar6": {100: 0, 20: 0}},
        "lifetime_years": 0.0,
        "safety_class": "B2L",
        "flammable": True,
        "phase_down": "unrestricted",
        "note": "Toxic. Industrial use only, included for comparison.",
    },
}

PHASE_DOWN_LABELS = {
    "banned_new": "Banned in new equipment",
    "restricted": "Being phased down; servicing gas is getting scarce",
    "transitional": "Permitted for now, under review",
    "unrestricted": "Not subject to phase-down",
}


# ---------------------------------------------------------------------------
# Equipment classes
#
# ``charge_kg`` and ``leak_rate`` are what turn "I have a heat pump" into a
# number. ``annual_kwh`` is what makes the comparison honest, because a
# refrigerant choice that saves gas and costs electricity is not a saving until
# the grid is clean.
# ---------------------------------------------------------------------------

EQUIPMENT_CLASSES: dict[str, dict[str, Any]] = {
    "domestic_fridge": {
        "label": "Fridge or fridge-freezer",
        "charge_kg": 0.10, "leak_rate": 0.005, "install_loss": 0.010,
        "lifetime_years": 14.0, "annual_kwh": 250.0, "default_gas": "R-600a",
    },
    "chest_freezer": {
        "label": "Chest freezer",
        "charge_kg": 0.12, "leak_rate": 0.005, "install_loss": 0.010,
        "lifetime_years": 15.0, "annual_kwh": 300.0, "default_gas": "R-600a",
    },
    "wine_cooler": {
        "label": "Wine cooler or drinks fridge",
        "charge_kg": 0.06, "leak_rate": 0.010, "install_loss": 0.010,
        "lifetime_years": 12.0, "annual_kwh": 180.0, "default_gas": "R-600a",
    },
    "split_ac": {
        "label": "Split air conditioner",
        "charge_kg": 1.20, "leak_rate": 0.050, "install_loss": 0.020,
        "lifetime_years": 12.0, "annual_kwh": 600.0, "default_gas": "R-410A",
    },
    "multi_split_ac": {
        "label": "Multi-split air conditioner",
        "charge_kg": 3.00, "leak_rate": 0.060, "install_loss": 0.030,
        "lifetime_years": 12.0, "annual_kwh": 1400.0, "default_gas": "R-410A",
    },
    "air_source_heat_pump": {
        "label": "Air source heat pump",
        "charge_kg": 2.00, "leak_rate": 0.035, "install_loss": 0.020,
        "lifetime_years": 18.0, "annual_kwh": 3000.0, "default_gas": "R-410A",
    },
    "ground_source_heat_pump": {
        "label": "Ground source heat pump",
        "charge_kg": 3.50, "leak_rate": 0.030, "install_loss": 0.020,
        "lifetime_years": 20.0, "annual_kwh": 2400.0, "default_gas": "R-410A",
    },
    "heat_pump_dryer": {
        "label": "Heat pump tumble dryer",
        "charge_kg": 0.35, "leak_rate": 0.010, "install_loss": 0.010,
        "lifetime_years": 12.0, "annual_kwh": 180.0, "default_gas": "R-134a",
    },
    "dehumidifier": {
        "label": "Dehumidifier",
        "charge_kg": 0.20, "leak_rate": 0.020, "install_loss": 0.010,
        "lifetime_years": 10.0, "annual_kwh": 200.0, "default_gas": "R-134a",
    },
    "car_ac": {
        "label": "Car air conditioning",
        "charge_kg": 0.55, "leak_rate": 0.120, "install_loss": 0.020,
        "lifetime_years": 14.0, "annual_kwh": 120.0, "default_gas": "R-134a",
    },
    "commercial_cabinet": {
        "label": "Commercial display cabinet",
        "charge_kg": 3.50, "leak_rate": 0.150, "install_loss": 0.030,
        "lifetime_years": 10.0, "annual_kwh": 4000.0, "default_gas": "R-404A",
    },
}


# ---------------------------------------------------------------------------
# Table access
# ---------------------------------------------------------------------------

def list_refrigerants() -> list[str]:
    """Refrigerant keys in table order."""
    return list(REFRIGERANTS)


def list_equipment_classes() -> list[str]:
    """Equipment class keys in table order."""
    return list(EQUIPMENT_CLASSES)


def get_refrigerant(gas: str) -> dict[str, Any]:
    """One gas's properties."""
    if gas not in REFRIGERANTS:
        raise RefrigerantError(f"Unknown refrigerant: {gas}")
    entry = dict(REFRIGERANTS[gas])
    entry["key"] = gas
    entry["phase_down_label"] = PHASE_DOWN_LABELS[entry["phase_down"]]
    return entry


def get_equipment_class(key: str) -> dict[str, Any]:
    """One equipment class's defaults."""
    if key not in EQUIPMENT_CLASSES:
        raise RefrigerantError(f"Unknown equipment class: {key}")
    entry = dict(EQUIPMENT_CLASSES[key])
    entry["key"] = key
    return entry


def gwp(gas: str, vintage: str = DEFAULT_VINTAGE, horizon: int = DEFAULT_HORIZON) -> float:
    """Global warming potential, at a stated vintage and horizon.

    Both are arguments rather than constants because both reorder the table. The
    100-year AR4 and AR6 values for R-410A differ by 21%; the 20- and 100-year
    values differ by more than a factor of two.
    """
    entry = get_refrigerant(gas)
    if vintage not in VINTAGES:
        raise RefrigerantError(
            f"Unknown assessment report: {vintage}; expected one of {VINTAGES}"
        )
    if horizon not in HORIZONS:
        raise RefrigerantError(
            f"Unsupported horizon: {horizon}; expected one of {HORIZONS}"
        )
    return float(entry["gwp"][vintage][horizon])


def gwp_spread(gas: str, horizon: int = DEFAULT_HORIZON) -> dict[str, Any]:
    """How much the vintage alone changes a gas's GWP."""
    values = {vintage: gwp(gas, vintage, horizon) for vintage in VINTAGES}
    low, high = min(values.values()), max(values.values())
    return {
        "gas": gas,
        "horizon": horizon,
        "values": values,
        "low": low,
        "high": high,
        "spread": round(high - low, 4),
        "ratio": round(high / low, 3) if low > 0 else None,
    }


# ---------------------------------------------------------------------------
# Building an equipment record
# ---------------------------------------------------------------------------

def build_equipment(
    equipment_class: str,
    gas: str | None = None,
    charge_kg: float | None = None,
    leak_rate: float | None = None,
    lifetime_years: float | None = None,
    annual_kwh: float | None = None,
    age_years: float = 0.0,
    label: str | None = None,
) -> dict[str, Any]:
    """One piece of equipment, class defaults filled in where not overridden."""
    defaults = get_equipment_class(equipment_class)
    gas = gas or defaults["default_gas"]
    if gas not in REFRIGERANTS:
        raise RefrigerantError(f"Unknown refrigerant: {gas}")

    record = {
        "equipment_class": equipment_class,
        "label": label or defaults["label"],
        "gas": gas,
        "charge_kg": float(defaults["charge_kg"] if charge_kg is None else charge_kg),
        "leak_rate": float(defaults["leak_rate"] if leak_rate is None else leak_rate),
        "install_loss": float(defaults["install_loss"]),
        "lifetime_years": float(
            defaults["lifetime_years"] if lifetime_years is None else lifetime_years
        ),
        "annual_kwh": float(
            defaults["annual_kwh"] if annual_kwh is None else annual_kwh
        ),
        "age_years": float(age_years),
    }

    if record["charge_kg"] <= 0:
        raise RefrigerantError("Charge must be positive")
    if not 0.0 <= record["leak_rate"] <= 1.0:
        raise RefrigerantError("Leak rate must be a fraction between 0 and 1")
    if record["lifetime_years"] <= 0:
        raise RefrigerantError("Lifetime must be positive")
    if record["annual_kwh"] < 0:
        raise RefrigerantError("Energy use cannot be negative")
    if record["age_years"] < 0:
        raise RefrigerantError("Age cannot be negative")
    if record["age_years"] > record["lifetime_years"]:
        raise RefrigerantError("Equipment cannot be older than its own lifetime")
    return record


def annual_leakage_kg(equipment: dict[str, Any], topped_up: bool = True) -> float:
    """Refrigerant lost in one year, in kg of gas.

    With top-ups the machine holds its full charge, so the loss is the same
    every year. Without them the charge declines and each year's loss is smaller
    than the last - which is not a benefit, because the machine is also getting
    less efficient as it empties.
    """
    if topped_up:
        return equipment["charge_kg"] * equipment["leak_rate"]
    remaining = remaining_charge_kg(equipment, equipment["age_years"], topped_up=False)
    return remaining * equipment["leak_rate"]


def remaining_charge_kg(
    equipment: dict[str, Any],
    at_year: float | None = None,
    topped_up: bool = True,
) -> float:
    """How much gas is still in the machine after a given number of years."""
    at_year = equipment["lifetime_years"] if at_year is None else float(at_year)
    if at_year < 0:
        raise RefrigerantError("Cannot look backwards past installation")
    if topped_up:
        return equipment["charge_kg"]
    remaining = equipment["charge_kg"] * (1.0 - equipment["install_loss"])
    return max(0.0, remaining * ((1.0 - equipment["leak_rate"]) ** at_year))


def lifecycle_emissions(
    equipment: dict[str, Any],
    recovery: float = DEFAULT_RECOVERY,
    vintage: str = DEFAULT_VINTAGE,
    horizon: int = DEFAULT_HORIZON,
    topped_up: bool = True,
) -> dict[str, Any]:
    """Direct emissions over the machine's life, split into its three parts.

    The split is the point. An annual rate hides that the disposal event can
    exceed the whole operating life's leakage, and disposal is the only part the
    owner still controls at the moment it happens.
    """
    if not 0.0 <= recovery <= 1.0:
        raise RefrigerantError("Recovery efficiency must be a fraction between 0 and 1")

    factor = gwp(equipment["gas"], vintage, horizon)
    charge = equipment["charge_kg"]
    life = equipment["lifetime_years"]

    install_kg = charge * equipment["install_loss"]

    if topped_up:
        operating_kg = charge * equipment["leak_rate"] * life
        at_disposal_kg = charge
    else:
        at_disposal_kg = remaining_charge_kg(equipment, life, topped_up=False)
        operating_kg = max(0.0, charge - install_kg - at_disposal_kg)

    disposal_kg = at_disposal_kg * (1.0 - recovery)
    total_kg_gas = install_kg + operating_kg + disposal_kg

    return {
        "gas": equipment["gas"],
        "vintage": vintage,
        "horizon": horizon,
        "gwp": factor,
        "topped_up": topped_up,
        "recovery": recovery,
        "install_kg_gas": round(install_kg, 5),
        "operating_kg_gas": round(operating_kg, 5),
        "disposal_kg_gas": round(disposal_kg, 5),
        "charge_at_disposal_kg": round(at_disposal_kg, 5),
        "total_kg_gas": round(total_kg_gas, 5),
        "install_co2e": round(install_kg * factor, 3),
        "operating_co2e": round(operating_kg * factor, 3),
        "disposal_co2e": round(disposal_kg * factor, 3),
        "total_co2e": round(total_kg_gas * factor, 3),
        "annual_operating_co2e": round(operating_kg * factor / life, 3),
        "disposal_share": (
            round(disposal_kg / total_kg_gas, 4) if total_kg_gas > 0 else 0.0
        ),
    }


def tewi(
    equipment: dict[str, Any],
    grid_intensity: float = DEFAULT_GRID_INTENSITY,
    recovery: float = DEFAULT_RECOVERY,
    vintage: str = DEFAULT_VINTAGE,
    horizon: int = DEFAULT_HORIZON,
    topped_up: bool = True,
    efficiency_penalty: float = 0.0,
) -> dict[str, Any]:
    """Total Equivalent Warming Impact - the leak and the electricity together.

    A refrigerant choice cannot honestly be compared on direct emissions alone,
    because the gas that leaks least is not always the gas the machine runs best
    on. ``efficiency_penalty`` is the fractional change in energy use: 0.05 is a
    machine drawing 5% more.
    """
    if grid_intensity < 0:
        raise RefrigerantError("Grid intensity cannot be negative")
    if efficiency_penalty <= -1.0:
        raise RefrigerantError("An efficiency change of -100% or better is not physical")

    direct = lifecycle_emissions(
        equipment, recovery=recovery, vintage=vintage, horizon=horizon,
        topped_up=topped_up,
    )
    lifetime_kwh = (
        equipment["annual_kwh"] * equipment["lifetime_years"] * (1.0 + efficiency_penalty)
    )
    indirect_co2e = lifetime_kwh * grid_intensity
    total = direct["total_co2e"] + indirect_co2e

    return {
        "direct_co2e": direct["total_co2e"],
        "indirect_co2e": round(indirect_co2e, 3),
        "total_co2e": round(total, 3),
        "lifetime_kwh": round(lifetime_kwh, 1),
        "grid_intensity": grid_intensity,
        "efficiency_penalty": efficiency_penalty,
        "direct_share": round(direct["total_co2e"] / total, 4) if total > 0 else 0.0,
        "annual_co2e": round(total / equipment["lifetime_years"], 3),
        "detail": direct,
    }


# ---------------------------------------------------------------------------
# Retrofit
# ---------------------------------------------------------------------------

def retrofit_comparison(
    equipment: dict[str, Any],
    alternative_gas: str,
    efficiency_penalty: float = 0.0,
    grid_intensity: float = DEFAULT_GRID_INTENSITY,
    recovery: float = DEFAULT_RECOVERY,
    vintage: str = DEFAULT_VINTAGE,
    horizon: int = DEFAULT_HORIZON,
    topped_up: bool = True,
) -> dict[str, Any]:
    """Compare a gas swap on TEWI, and find where the answer changes.

    The useful output is not yes or no. It is the grid intensity at which the
    direct saving stops covering the extra electricity - above it the swap makes
    things worse, below it the swap wins, and where that threshold sits relative
    to the actual grid is the whole decision.

    If the alternative is both cleaner and no less efficient there is no
    threshold: it wins everywhere, and saying so is more useful than returning a
    meaningless number.
    """
    if alternative_gas not in REFRIGERANTS:
        raise RefrigerantError(f"Unknown refrigerant: {alternative_gas}")

    current = tewi(
        equipment, grid_intensity=grid_intensity, recovery=recovery,
        vintage=vintage, horizon=horizon, topped_up=topped_up,
    )
    swapped_equipment = dict(equipment)
    swapped_equipment["gas"] = alternative_gas
    swapped = tewi(
        swapped_equipment, grid_intensity=grid_intensity, recovery=recovery,
        vintage=vintage, horizon=horizon, topped_up=topped_up,
        efficiency_penalty=efficiency_penalty,
    )

    direct_change = swapped["direct_co2e"] - current["direct_co2e"]
    indirect_change = swapped["indirect_co2e"] - current["indirect_co2e"]
    base_lifetime_kwh = equipment["annual_kwh"] * equipment["lifetime_years"]
    extra_kwh = base_lifetime_kwh * efficiency_penalty

    breakeven = None
    verdict = ""
    if abs(extra_kwh) < 1e-9:
        # No energy change: the direct comparison decides, at any grid.
        verdict = (
            "wins at every grid intensity" if direct_change < 0
            else "never wins - it is dirtier and no more efficient"
        )
    else:
        breakeven = -direct_change / extra_kwh
        if breakeven < 0:
            verdict = (
                "wins at every grid intensity" if direct_change < 0 and extra_kwh < 0
                else "never wins - it is worse on both counts"
            )
            breakeven = None
        elif extra_kwh > 0:
            verdict = (
                f"wins below a grid intensity of {breakeven:.3f} kg/kWh and "
                "loses above it"
            )
        else:
            verdict = (
                f"wins above a grid intensity of {breakeven:.3f} kg/kWh and "
                "loses below it"
            )

    return {
        "from_gas": equipment["gas"],
        "to_gas": alternative_gas,
        "from_gwp": gwp(equipment["gas"], vintage, horizon),
        "to_gwp": gwp(alternative_gas, vintage, horizon),
        "efficiency_penalty": efficiency_penalty,
        "grid_intensity": grid_intensity,
        "current_tewi": current["total_co2e"],
        "swapped_tewi": swapped["total_co2e"],
        "net_change": round(swapped["total_co2e"] - current["total_co2e"], 3),
        "direct_change": round(direct_change, 3),
        "indirect_change": round(indirect_change, 3),
        "extra_lifetime_kwh": round(extra_kwh, 1),
        # Six places, not four: this is multiplied by a lifetime kWh figure in
        # the thousands, so a coarser threshold does not actually break even.
        "breakeven_grid_intensity": (
            round(breakeven, 6) if breakeven is not None else None
        ),
        "worthwhile_here": swapped["total_co2e"] < current["total_co2e"],
        "verdict": verdict,
        "safety_note": _safety_note(equipment["gas"], alternative_gas),
    }


def _safety_note(from_gas: str, to_gas: str) -> str | None:
    """Whether a swap changes the safety class, which limits where it can go."""
    before = get_refrigerant(from_gas)
    after = get_refrigerant(to_gas)
    # Toxicity is checked first. Ammonia is both toxic and flammable, and
    # reporting only the flammability of a gas that is also toxic would bury
    # the stronger objection under the weaker one.
    if after["safety_class"].startswith("B"):
        return f"{after['label']} is toxic and not suitable for domestic use."
    if after["flammable"] and not before["flammable"]:
        return (
            f"{after['label']} is flammable ({after['safety_class']}) where "
            f"{before['label']} is not. Charge size and siting are regulated, so "
            "this is not a swap that can be made in every installation."
        )
    return None


def retrofit_options(
    equipment: dict[str, Any],
    efficiency_penalty: float = 0.0,
    grid_intensity: float = DEFAULT_GRID_INTENSITY,
    recovery: float = DEFAULT_RECOVERY,
    vintage: str = DEFAULT_VINTAGE,
    horizon: int = DEFAULT_HORIZON,
) -> list[dict[str, Any]]:
    """Every alternative gas compared against the current one, best first."""
    rows = []
    for gas in list_refrigerants():
        if gas == equipment["gas"]:
            continue
        rows.append(
            retrofit_comparison(
                equipment, gas, efficiency_penalty=efficiency_penalty,
                grid_intensity=grid_intensity, recovery=recovery,
                vintage=vintage, horizon=horizon,
            )
        )
    rows.sort(key=lambda row: row["swapped_tewi"])
    return rows


# ---------------------------------------------------------------------------
# Registers
# ---------------------------------------------------------------------------

def register_summary(
    equipment_list: list[dict[str, Any]],
    grid_intensity: float = DEFAULT_GRID_INTENSITY,
    recovery: float = DEFAULT_RECOVERY,
    vintage: str = DEFAULT_VINTAGE,
    horizon: int = DEFAULT_HORIZON,
    topped_up: bool = True,
) -> dict[str, Any]:
    """Everything in the house, added up."""
    if not equipment_list:
        raise RefrigerantError("No equipment to summarise")

    rows = []
    for item in equipment_list:
        result = tewi(
            item, grid_intensity=grid_intensity, recovery=recovery,
            vintage=vintage, horizon=horizon, topped_up=topped_up,
        )
        detail = result["detail"]
        rows.append({
            "label": item["label"],
            "equipment_class": item["equipment_class"],
            "gas": item["gas"],
            "charge_kg": item["charge_kg"],
            "annual_leak_co2e": round(
                item["charge_kg"] * item["leak_rate"] * detail["gwp"], 3
            ),
            "lifetime_direct_co2e": detail["total_co2e"],
            "disposal_co2e": detail["disposal_co2e"],
            "lifetime_indirect_co2e": result["indirect_co2e"],
            "lifetime_tewi": result["total_co2e"],
            "phase_down": get_refrigerant(item["gas"])["phase_down"],
            "years_left": round(
                max(0.0, item["lifetime_years"] - item["age_years"]), 1
            ),
        })
    rows.sort(key=lambda row: row["lifetime_tewi"], reverse=True)

    annual_leak = sum(row["annual_leak_co2e"] for row in rows)
    lifetime_direct = sum(row["lifetime_direct_co2e"] for row in rows)
    lifetime_indirect = sum(row["lifetime_indirect_co2e"] for row in rows)
    return {
        "count": len(rows),
        "total_charge_kg": round(sum(row["charge_kg"] for row in rows), 4),
        "annual_leak_co2e": round(annual_leak, 3),
        "lifetime_direct_co2e": round(lifetime_direct, 3),
        "lifetime_indirect_co2e": round(lifetime_indirect, 3),
        "lifetime_tewi": round(lifetime_direct + lifetime_indirect, 3),
        "disposal_co2e": round(sum(row["disposal_co2e"] for row in rows), 3),
        "direct_share": (
            round(lifetime_direct / (lifetime_direct + lifetime_indirect), 4)
            if (lifetime_direct + lifetime_indirect) > 0 else 0.0
        ),
        "items": rows,
    }


def phase_down_exposure(equipment_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Equipment on gases that are being restricted.

    Servicing cost and gas availability are part of a replacement decision, and
    they arrive before the machine wears out.
    """
    rows = []
    for item in equipment_list:
        entry = get_refrigerant(item["gas"])
        if entry["phase_down"] in ("banned_new", "restricted"):
            rows.append({
                "label": item["label"],
                "gas": item["gas"],
                "status": entry["phase_down"],
                "status_label": entry["phase_down_label"],
                "years_left": round(
                    max(0.0, item["lifetime_years"] - item["age_years"]), 1
                ),
                "charge_kg": item["charge_kg"],
            })
    rows.sort(key=lambda row: row["years_left"], reverse=True)
    return rows


def sensitivity(
    equipment: dict[str, Any],
    grid_intensity: float = DEFAULT_GRID_INTENSITY,
) -> list[dict[str, Any]]:
    """The four inputs that are uncertain enough to change the ordering."""
    rows: list[dict[str, Any]] = []

    for rate in (0.5, 1.0, 1.5, 2.0):
        varied = dict(equipment)
        varied["leak_rate"] = min(1.0, equipment["leak_rate"] * rate)
        result = tewi(varied, grid_intensity=grid_intensity)
        rows.append({
            "parameter": "Leak rate",
            "setting": f"{varied['leak_rate']:.1%} a year",
            "total_co2e": result["total_co2e"],
            "direct_co2e": result["direct_co2e"],
        })

    for recovery in (0.0, 0.5, 0.7, 0.95):
        result = tewi(equipment, grid_intensity=grid_intensity, recovery=recovery)
        rows.append({
            "parameter": "End-of-life recovery",
            "setting": (
                "scrapped with the charge in it" if recovery == 0.0
                else f"{recovery:.0%} recovered"
            ),
            "total_co2e": result["total_co2e"],
            "direct_co2e": result["direct_co2e"],
        })

    for name, intensity in GRID_INTENSITIES.items():
        result = tewi(equipment, grid_intensity=intensity)
        rows.append({
            "parameter": "Grid intensity",
            "setting": f"{name.replace('_', ' ')} ({intensity:.3f} kg/kWh)",
            "total_co2e": result["total_co2e"],
            "direct_co2e": result["direct_co2e"],
        })

    for vintage in VINTAGES:
        for horizon in HORIZONS:
            result = tewi(
                equipment, grid_intensity=grid_intensity,
                vintage=vintage, horizon=horizon,
            )
            rows.append({
                "parameter": "GWP basis",
                "setting": f"{vintage.upper()} over {horizon} years",
                "total_co2e": result["total_co2e"],
                "direct_co2e": result["direct_co2e"],
            })

    return rows


def get_refrigerant_insights(summary: dict[str, Any]) -> list[str]:
    """Plain-language readings of a register summary."""
    if not summary.get("items"):
        return ["No equipment registered."]

    insights: list[str] = []
    top = summary["items"][0]
    insights.append(
        f"{top['label']} leaks about {top['annual_leak_co2e']:.0f} kg CO2e a "
        f"year - {top['charge_kg']:.2f} kg of {top['gas']} at its class's "
        "typical leak rate."
    )

    if summary["disposal_co2e"] > 0:
        insights.append(
            f"{summary['disposal_co2e']:.0f} kg of the lifetime total is the "
            "disposal event. It is the only part still under your control at "
            "the moment it happens, and it happens once."
        )

    share = summary["direct_share"]
    if share >= 0.5:
        insights.append(
            f"Refrigerant leakage is {share:.0%} of the total warming impact of "
            "this equipment - more than the electricity it uses."
        )
    else:
        insights.append(
            f"Electricity is {1 - share:.0%} of the total warming impact here, "
            "so a lower-GWP gas that ran less efficiently could easily be a "
            "step backwards."
        )

    exposed = [row for row in summary["items"] if row["phase_down"] in
               ("banned_new", "restricted")]
    if exposed:
        names = ", ".join(sorted({row["gas"] for row in exposed}))
        insights.append(
            f"{len(exposed)} item(s) run on gases being phased down ({names}). "
            "Servicing gets more expensive before the equipment wears out."
        )

    return insights


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def init_refrigerant_db() -> bool:
    """Create the table if it does not exist yet."""
    conn = None
    try:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS refrigerant_registers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                item_count INTEGER NOT NULL DEFAULT 0,
                total_charge_kg REAL NOT NULL,
                annual_leak_co2e REAL NOT NULL,
                lifetime_tewi REAL NOT NULL,
                detail_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Unable to initialise refrigerant table: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_register(
    user_id: int,
    name: str,
    equipment_list: list[dict[str, Any]],
    summary: dict[str, Any],
) -> int | None:
    """Persist a register. Returns the row id or None."""
    init_refrigerant_db()
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            """
            INSERT INTO refrigerant_registers (
                user_id, name, item_count, total_charge_kg,
                annual_leak_co2e, lifetime_tewi, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(name),
                int(summary.get("count", 0)),
                float(summary.get("total_charge_kg", 0.0)),
                float(summary.get("annual_leak_co2e", 0.0)),
                float(summary.get("lifetime_tewi", 0.0)),
                json.dumps({"equipment": equipment_list, "summary": summary}),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save refrigerant register: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_registers(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Saved registers, newest first."""
    init_refrigerant_db()
    conn = None
    try:
        conn = _connect()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM refrigerant_registers
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        registers = []
        for row in rows:
            record = dict(row)
            if record.get("detail_json"):
                try:
                    record["detail"] = json.loads(record["detail_json"])
                except (TypeError, ValueError):
                    record["detail"] = None
            registers.append(record)
        return registers
    except sqlite3.Error as exc:
        logger.error("Unable to read refrigerant registers: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def delete_register(register_id: int, user_id: int) -> bool:
    """Delete a register the user owns."""
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            "DELETE FROM refrigerant_registers WHERE id = ? AND user_id = ?",
            (int(register_id), int(user_id)),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Unable to delete refrigerant register: %s", exc)
        return False
    finally:
        if conn:
            conn.close()
