"""Spend-based consumption footprint by environmentally-extended input-output.

Everything in this repository that turns money into carbon does it with a
per-category factor. ``receipt_categorization.py`` sorts a receipt into a
category and a kg-per-currency-unit number is applied. That number is a
*direct* intensity: it accounts for what the seller emitted and nothing for what
the seller bought in order to sell it.

Why a direct factor is not a footprint
--------------------------------------
A restaurant meal's direct intensity covers the restaurant's gas and
electricity. It does not cover the farm, the abattoir, the cold chain, the road
freight or the packaging - and for hospitality that upstream is most of the
total. The correction is not a per-sector fudge, because the upstream of a
sector is the upstream of *its* suppliers, recursively, and that recursion does
not terminate: steel needs coke, coke needs mining, mining needs steel. Summing
tiers by hand truncates arbitrarily. The point of input-output analysis is that
the infinite series has a closed form::

    (I - A)^-1 = I + A + A^2 + A^3 + ...

so ``e (I - A)^-1`` is a total intensity with every tier in it. Both routes are
implemented here: the closed form is what runs, and the power series is kept so
the tier-by-tier contribution can be shown and the closed form checked against
something independent.

Three things that are usually got wrong
---------------------------------------
**Purchaser prices are not producer prices.** What a household pays includes
retail and transport margins, and those belong to the retail and transport
sectors. Feeding a supermarket line straight into a food-manufacturing intensity
gives the supermarket's footprint to the farm and then applies the farm's
upstream multiplier to it.

**Spend is nominal.** A 2020 intensity table applied to 2026 money without
deflating reports inflation as emissions growth.

**Spend double counts against physical data.** If electricity is already counted
in kWh by ``emissions.py`` and the electricity *spend* also goes through this
model, it is in the inventory twice. Every sector here declares what it overlaps
with, so ``boundary_reconciliation.py`` has something to work from and a hybrid
inventory can subtract cleanly rather than hope.

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

# The price year the table is denominated in. Nominal spend from any other year
# is deflated to this before intensities touch it.
BASE_PRICE_YEAR = 2020

# Paths shorter than this share of the sector total are not worth listing; the
# residual is reported as a single "beyond depth" line rather than dropped.
DEFAULT_PATH_THRESHOLD = 0.01
DEFAULT_PATH_DEPTH = 4

# A column of A summing to at least this is a sector consuming its own output to
# produce it. The inverse is then meaningless, so it is a hard error.
PRODUCTIVITY_LIMIT = 1.0


class EEIOError(ValueError):
    """Raised when a table or a spend profile cannot be used as given."""


# ---------------------------------------------------------------------------
# Sectors
#
# Chosen to be the things a household actually spends money on, which is not the
# same list a national accountant would use. ``label`` is what a person would
# call it; ``examples`` exists so a receipt line can be placed without guessing.
# ---------------------------------------------------------------------------

SECTORS: dict[str, dict[str, Any]] = {
    "agriculture": {
        "label": "Agriculture and fishing",
        "examples": "farm produce, unprocessed meat, fish",
    },
    "food_manufacturing": {
        "label": "Food manufacturing",
        "examples": "packaged food, bread, dairy products",
    },
    "beverages": {
        "label": "Beverages and tobacco",
        "examples": "soft drinks, alcohol, coffee",
    },
    "textiles": {
        "label": "Textiles and apparel",
        "examples": "clothing, shoes, bedding",
    },
    "chemicals": {
        "label": "Chemicals and pharmaceuticals",
        "examples": "cleaning products, medicines, cosmetics",
    },
    "metals_minerals": {
        "label": "Metals and non-metallic minerals",
        "examples": "cement, steel, glass, tools",
    },
    "electronics": {
        "label": "Electronics and appliances",
        "examples": "phones, laptops, white goods",
    },
    "vehicles": {
        "label": "Vehicle manufacture",
        "examples": "cars, bicycles, vehicle parts",
    },
    "electricity": {
        "label": "Electricity supply",
        "examples": "the electricity bill",
    },
    "gas_supply": {
        "label": "Gas and other fuel supply",
        "examples": "the gas bill, heating oil, petrol",
    },
    "water_waste": {
        "label": "Water and waste services",
        "examples": "water bill, refuse collection",
    },
    "construction": {
        "label": "Construction and repair",
        "examples": "building work, plumbing, decorating",
    },
    "retail": {
        "label": "Wholesale and retail",
        "examples": "the shop's own margin on anything bought",
    },
    "freight": {
        "label": "Freight transport and storage",
        "examples": "delivery, postage, removals",
    },
    "passenger_transport": {
        "label": "Passenger transport",
        "examples": "rail, bus, taxi, flights",
    },
    "hospitality": {
        "label": "Hotels and restaurants",
        "examples": "eating out, takeaways, hotels",
    },
    "finance": {
        "label": "Financial and insurance services",
        "examples": "banking fees, insurance premiums",
    },
    "health_education": {
        "label": "Health and education",
        "examples": "dentist, tuition, childcare",
    },
    "recreation": {
        "label": "Recreation and culture",
        "examples": "cinema, gym, sports clubs",
    },
    "communication": {
        "label": "Communication and IT services",
        "examples": "broadband, mobile, subscriptions",
    },
}

SECTOR_ORDER: tuple[str, ...] = tuple(SECTORS)


# ---------------------------------------------------------------------------
# Direct emission intensities
#
# kg CO2e per unit of output at producer prices, in the base price year. These
# are the *seller's own* emissions only - the entire purpose of the rest of this
# module is that these numbers are not footprints.
#
# Electricity and gas supply are high because they are almost all direct: the
# multiplier on them will come out near 1, which is the sanity check that the
# rest of the table is behaving.
# ---------------------------------------------------------------------------

DIRECT_INTENSITY: dict[str, float] = {
    "agriculture": 0.550,
    "food_manufacturing": 0.120,
    "beverages": 0.090,
    "textiles": 0.100,
    "chemicals": 0.250,
    "metals_minerals": 0.450,
    "electronics": 0.060,
    "vehicles": 0.070,
    "electricity": 1.800,
    "gas_supply": 1.400,
    "water_waste": 0.350,
    "construction": 0.050,
    "retail": 0.040,
    "freight": 0.550,
    "passenger_transport": 0.600,
    "hospitality": 0.080,
    "finance": 0.015,
    "health_education": 0.030,
    "recreation": 0.030,
    "communication": 0.020,
}


# ---------------------------------------------------------------------------
# Technical coefficients
#
# ``TECHNICAL_COEFFICIENTS[j][i]`` is the input from sector *i* needed per unit
# of output from sector *j*. Written column-wise - by the consuming sector -
# because that is how a supply chain is actually described: "to run a restaurant
# you buy food, energy, freight and services".
#
# Every column must sum to less than 1. A column summing to 1 or more is a
# sector that cannot produce anything net, and ``check_productive`` refuses it
# rather than letting the inverse come back negative.
# ---------------------------------------------------------------------------

TECHNICAL_COEFFICIENTS: dict[str, dict[str, float]] = {
    "agriculture": {
        "agriculture": 0.120, "chemicals": 0.075, "electricity": 0.035,
        "gas_supply": 0.055, "freight": 0.040, "retail": 0.020,
        "finance": 0.020, "construction": 0.015,
    },
    "food_manufacturing": {
        "agriculture": 0.300, "food_manufacturing": 0.060, "chemicals": 0.025,
        "metals_minerals": 0.030, "electricity": 0.030, "gas_supply": 0.030,
        "freight": 0.050, "retail": 0.030, "finance": 0.015, "water_waste": 0.010,
    },
    "beverages": {
        "agriculture": 0.150, "food_manufacturing": 0.050, "chemicals": 0.020,
        "metals_minerals": 0.055, "electricity": 0.030, "gas_supply": 0.025,
        "freight": 0.045, "retail": 0.035, "finance": 0.015, "water_waste": 0.015,
    },
    "textiles": {
        "agriculture": 0.090, "chemicals": 0.090, "textiles": 0.080,
        "electricity": 0.030, "gas_supply": 0.020, "freight": 0.045,
        "retail": 0.040, "finance": 0.015, "communication": 0.010,
    },
    "chemicals": {
        "chemicals": 0.130, "gas_supply": 0.080, "metals_minerals": 0.035,
        "electricity": 0.045, "freight": 0.035, "retail": 0.020,
        "finance": 0.020, "water_waste": 0.015, "agriculture": 0.020,
    },
    "metals_minerals": {
        "metals_minerals": 0.150, "chemicals": 0.040, "electricity": 0.070,
        "gas_supply": 0.070, "freight": 0.055, "retail": 0.015,
        "finance": 0.015, "construction": 0.020,
    },
    "electronics": {
        "electronics": 0.140, "metals_minerals": 0.075, "chemicals": 0.045,
        "electricity": 0.025, "freight": 0.035, "retail": 0.035,
        "finance": 0.020, "communication": 0.025, "textiles": 0.010,
    },
    "vehicles": {
        "metals_minerals": 0.120, "electronics": 0.070, "chemicals": 0.045,
        "textiles": 0.020, "vehicles": 0.090, "electricity": 0.020,
        "freight": 0.040, "retail": 0.025, "finance": 0.020,
    },
    "electricity": {
        "gas_supply": 0.180, "metals_minerals": 0.020, "construction": 0.030,
        "electricity": 0.045, "freight": 0.020, "finance": 0.025,
        "communication": 0.010,
    },
    "gas_supply": {
        "gas_supply": 0.150, "chemicals": 0.020, "electricity": 0.030,
        "freight": 0.035, "construction": 0.025, "finance": 0.025,
        "metals_minerals": 0.015,
    },
    "water_waste": {
        "electricity": 0.090, "chemicals": 0.040, "construction": 0.050,
        "freight": 0.030, "water_waste": 0.030, "finance": 0.020,
        "metals_minerals": 0.015,
    },
    "construction": {
        "metals_minerals": 0.180, "construction": 0.090, "chemicals": 0.030,
        "electronics": 0.020, "freight": 0.050, "electricity": 0.015,
        "gas_supply": 0.015, "retail": 0.035, "finance": 0.025,
    },
    "retail": {
        "freight": 0.060, "electricity": 0.030, "construction": 0.025,
        "communication": 0.030, "finance": 0.035, "retail": 0.040,
        "recreation": 0.010,
    },
    "freight": {
        "gas_supply": 0.170, "vehicles": 0.045, "freight": 0.060,
        "construction": 0.020, "finance": 0.030, "communication": 0.015,
        "electricity": 0.010,
    },
    "passenger_transport": {
        "gas_supply": 0.155, "vehicles": 0.050, "construction": 0.025,
        "electricity": 0.025, "finance": 0.030, "communication": 0.015,
        "passenger_transport": 0.040, "hospitality": 0.010,
    },
    "hospitality": {
        "food_manufacturing": 0.130, "agriculture": 0.055, "beverages": 0.070,
        "electricity": 0.030, "gas_supply": 0.025, "water_waste": 0.010,
        "freight": 0.020, "retail": 0.035, "finance": 0.020,
        "construction": 0.020, "communication": 0.010,
    },
    "finance": {
        "finance": 0.100, "communication": 0.045, "construction": 0.020,
        "electricity": 0.010, "recreation": 0.010, "retail": 0.010,
        "electronics": 0.015,
    },
    "health_education": {
        "chemicals": 0.060, "finance": 0.025, "construction": 0.030,
        "electricity": 0.020, "gas_supply": 0.015, "communication": 0.020,
        "food_manufacturing": 0.020, "electronics": 0.020, "retail": 0.020,
    },
    "recreation": {
        "recreation": 0.070, "communication": 0.040, "construction": 0.025,
        "electricity": 0.020, "finance": 0.020, "retail": 0.025,
        "hospitality": 0.030, "electronics": 0.015,
    },
    "communication": {
        "communication": 0.110, "electronics": 0.055, "electricity": 0.035,
        "construction": 0.020, "finance": 0.030, "retail": 0.015,
    },
}


# ---------------------------------------------------------------------------
# Purchaser-to-producer price conversion
#
# What a household pays is a producer price plus a retail margin plus a
# transport margin. Those margins are the *retail* and *freight* sectors'
# output, not the producing sector's, and they carry those sectors' footprints.
#
# Utilities and services are near-zero because they are sold direct - there is
# no shop between the household and the water company.
# ---------------------------------------------------------------------------

MARGIN_RATES: dict[str, dict[str, float]] = {
    "agriculture": {"retail": 0.28, "freight": 0.07},
    "food_manufacturing": {"retail": 0.26, "freight": 0.06},
    "beverages": {"retail": 0.30, "freight": 0.05},
    "textiles": {"retail": 0.40, "freight": 0.05},
    "chemicals": {"retail": 0.32, "freight": 0.04},
    "metals_minerals": {"retail": 0.22, "freight": 0.08},
    "electronics": {"retail": 0.25, "freight": 0.04},
    "vehicles": {"retail": 0.18, "freight": 0.04},
    "electricity": {"retail": 0.00, "freight": 0.00},
    "gas_supply": {"retail": 0.02, "freight": 0.01},
    "water_waste": {"retail": 0.00, "freight": 0.00},
    "construction": {"retail": 0.03, "freight": 0.02},
    "retail": {"retail": 0.00, "freight": 0.00},
    "freight": {"retail": 0.00, "freight": 0.00},
    "passenger_transport": {"retail": 0.02, "freight": 0.00},
    "hospitality": {"retail": 0.00, "freight": 0.00},
    "finance": {"retail": 0.00, "freight": 0.00},
    "health_education": {"retail": 0.00, "freight": 0.00},
    "recreation": {"retail": 0.02, "freight": 0.00},
    "communication": {"retail": 0.03, "freight": 0.00},
}


# Consumer price index, base year = 100. Nominal spend is deflated with this
# before intensities are applied, so a run of inflation is not reported as a
# run of emissions growth.
DEFLATORS: dict[int, float] = {
    2015: 91.2, 2016: 92.4, 2017: 94.9, 2018: 97.1, 2019: 98.8,
    2020: 100.0, 2021: 102.6, 2022: 111.9, 2023: 119.5, 2024: 122.6,
    2025: 125.9, 2026: 129.0,
}


# ---------------------------------------------------------------------------
# Overlap with physical data
#
# A spend-based total is only safe to add to a physical one after the overlap
# has been taken out. Each sector declares which physical activity it covers, so
# ``boundary_reconciliation.py`` has something to reconcile against instead of
# having to infer it.
# ---------------------------------------------------------------------------

PHYSICAL_OVERLAP: dict[str, str] = {
    "electricity": "home.electricity",
    "gas_supply": "home.gas",
    "passenger_transport": "travel.public",
    "water_waste": "home.water",
    "food_manufacturing": "food.groceries",
    "agriculture": "food.groceries",
}


# ---------------------------------------------------------------------------
# Table access
# ---------------------------------------------------------------------------

def list_sectors() -> list[str]:
    """Sector keys in table order."""
    return list(SECTOR_ORDER)


def get_sector(key: str) -> dict[str, Any]:
    """One sector's metadata, with its direct intensity attached."""
    if key not in SECTORS:
        raise EEIOError(f"Unknown sector: {key}")
    entry = dict(SECTORS[key])
    entry["key"] = key
    entry["direct_intensity"] = DIRECT_INTENSITY[key]
    entry["overlaps"] = PHYSICAL_OVERLAP.get(key)
    return entry


def build_matrix() -> list[list[float]]:
    """The technical coefficient matrix as ``A[i][j]`` - input i per unit of j.

    The declaration is column-wise for readability, so this transposes it. An
    unknown sector key anywhere in the declaration is an error, not a zero.
    """
    index = {key: n for n, key in enumerate(SECTOR_ORDER)}
    size = len(SECTOR_ORDER)
    matrix = [[0.0] * size for _ in range(size)]
    for consumer, inputs in TECHNICAL_COEFFICIENTS.items():
        if consumer not in index:
            raise EEIOError(f"Coefficients declared for unknown sector: {consumer}")
        col = index[consumer]
        for supplier, value in inputs.items():
            if supplier not in index:
                raise EEIOError(
                    f"Sector {consumer} declares an input from unknown sector {supplier}"
                )
            if value < 0.0:
                raise EEIOError(f"Negative coefficient {supplier}->{consumer}")
            matrix[index[supplier]][col] = float(value)
    return matrix


def column_sums(matrix: list[list[float]] | None = None) -> dict[str, float]:
    """Intermediate input share per sector - each column's total."""
    matrix = build_matrix() if matrix is None else matrix
    return {
        key: sum(matrix[i][j] for i in range(len(SECTOR_ORDER)))
        for j, key in enumerate(SECTOR_ORDER)
    }


def check_productive(matrix: list[list[float]] | None = None) -> bool:
    """Refuse a table that cannot produce anything net.

    A column summing to 1 or more means the sector consumes at least its own
    output to make it. The Leontief inverse is then meaningless - it comes back
    with negative entries rather than failing - so this is checked up front and
    the offending sector is named.
    """
    for key, total in column_sums(matrix).items():
        if total >= PRODUCTIVITY_LIMIT:
            raise EEIOError(
                f"Sector {key} consumes {total:.3f} per unit of its own output; "
                "a column summing to 1 or more makes the table non-productive"
            )
    return True


# ---------------------------------------------------------------------------
# The Leontief inverse
# ---------------------------------------------------------------------------

def leontief_inverse(matrix: list[list[float]] | None = None) -> list[list[float]]:
    """``(I - A)^-1`` by Gauss-Jordan elimination with partial pivoting.

    Partial pivoting is not decoration. Several sectors here have a zero own-use
    coefficient, and without pivoting the elimination hits a zero pivot on a
    matrix that is perfectly well conditioned.
    """
    matrix = build_matrix() if matrix is None else matrix
    check_productive(matrix)
    size = len(matrix)

    # Augment (I - A) with the identity; Gauss-Jordan leaves the inverse there.
    work = [
        [(1.0 if i == j else 0.0) - matrix[i][j] for j in range(size)]
        + [1.0 if i == j else 0.0 for j in range(size)]
        for i in range(size)
    ]

    for col in range(size):
        pivot_row = max(range(col, size), key=lambda r: abs(work[r][col]))
        if abs(work[pivot_row][col]) < 1e-12:
            raise EEIOError(
                f"(I - A) is singular at sector {SECTOR_ORDER[col]}; "
                "the table cannot be inverted"
            )
        work[col], work[pivot_row] = work[pivot_row], work[col]

        pivot = work[col][col]
        work[col] = [value / pivot for value in work[col]]

        for row in range(size):
            if row == col:
                continue
            factor = work[row][col]
            if factor == 0.0:
                continue
            work[row] = [
                value - factor * pivot_value
                for value, pivot_value in zip(work[row], work[col])
            ]

    return [row[size:] for row in work]


def total_intensities() -> dict[str, float]:
    """kg CO2e per unit of final demand, upstream included, at producer prices.

    This is ``e (I - A)^-1``: the direct intensity of every sector, weighted by
    how much of that sector every unit of final demand ultimately pulls in.
    """
    inverse = leontief_inverse()
    direct = [DIRECT_INTENSITY[key] for key in SECTOR_ORDER]
    return {
        key: sum(direct[i] * inverse[i][j] for i in range(len(SECTOR_ORDER)))
        for j, key in enumerate(SECTOR_ORDER)
    }


def series_intensities(terms: int = 8) -> dict[str, float]:
    """The same thing by power series, truncated at ``terms`` tiers.

    Not the production path - the closed form is exact and this is not. It is
    here because it is independently derived, so it can be checked against the
    inverse, and because the tier-by-tier convergence is the clearest available
    demonstration of why truncating the supply chain understates.
    """
    if terms < 1:
        raise EEIOError("A power series needs at least one term")
    matrix = build_matrix()
    check_productive(matrix)
    size = len(SECTOR_ORDER)
    direct = [DIRECT_INTENSITY[key] for key in SECTOR_ORDER]

    # Row vector accumulation: e, then eA, then eA^2 ... each term is the
    # emissions from one tier further upstream.
    totals = list(direct)
    term = list(direct)
    for _ in range(terms - 1):
        term = [
            sum(term[i] * matrix[i][j] for i in range(size))
            for j in range(size)
        ]
        totals = [total + value for total, value in zip(totals, term)]
    return {key: totals[j] for j, key in enumerate(SECTOR_ORDER)}


def tier_contributions(sector: str, tiers: int = 6) -> list[dict[str, Any]]:
    """How much of a sector's total intensity each upstream tier adds."""
    if sector not in SECTORS:
        raise EEIOError(f"Unknown sector: {sector}")
    total = total_intensities()[sector]
    rows: list[dict[str, Any]] = []
    previous = 0.0
    for depth in range(1, tiers + 1):
        cumulative = series_intensities(depth)[sector]
        rows.append({
            "tier": depth,
            "added": round(cumulative - previous, 6),
            "cumulative": round(cumulative, 6),
            "share_of_total": round(cumulative / total, 4) if total else 0.0,
        })
        previous = cumulative
    return rows


def multipliers() -> dict[str, float]:
    """Total intensity divided by direct - how much the supply chain adds.

    Electricity should come out near 1 because it is almost all direct;
    hospitality should come out well above 3 because it is almost all bought in.
    A table where those two are not far apart is a table with a mistake in it.
    """
    totals = total_intensities()
    return {
        key: (totals[key] / DIRECT_INTENSITY[key]) if DIRECT_INTENSITY[key] else 0.0
        for key in SECTOR_ORDER
    }


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------

def deflate(amount: float, from_year: int, to_year: int = BASE_PRICE_YEAR) -> float:
    """Convert nominal money in ``from_year`` into ``to_year`` prices."""
    if from_year not in DEFLATORS:
        raise EEIOError(f"No deflator for {from_year}")
    if to_year not in DEFLATORS:
        raise EEIOError(f"No deflator for {to_year}")
    return float(amount) * DEFLATORS[to_year] / DEFLATORS[from_year]


def split_purchaser_price(sector: str, amount: float) -> dict[str, float]:
    """Split purchaser-price spend into producer-price spend by sector.

    The margins do not vanish - they become spend on retail and freight, which
    have footprints of their own. Splitting and then discarding the margins
    would understate; not splitting at all overstates, because the producing
    sector's multiplier gets applied to the shopkeeper's markup.
    """
    if sector not in SECTORS:
        raise EEIOError(f"Unknown sector: {sector}")
    if amount < 0:
        raise EEIOError("Spend cannot be negative")

    rates = MARGIN_RATES.get(sector, {})
    split: dict[str, float] = {}
    remainder = 1.0
    for margin_sector, rate in rates.items():
        if rate <= 0.0:
            continue
        split[margin_sector] = split.get(margin_sector, 0.0) + amount * rate
        remainder -= rate
    if remainder <= 0.0:
        raise EEIOError(f"Margins on {sector} consume the whole purchaser price")
    split[sector] = split.get(sector, 0.0) + amount * remainder
    return split


# ---------------------------------------------------------------------------
# Footprints
# ---------------------------------------------------------------------------

def spend_footprint(
    spend: dict[str, float],
    year: int = BASE_PRICE_YEAR,
    apply_margins: bool = True,
) -> dict[str, Any]:
    """Footprint of a spend profile, upstream included.

    ``spend`` is purchaser-price money per sector, in ``year`` prices.
    """
    if not spend:
        raise EEIOError("No spend given")
    for key, amount in spend.items():
        if key not in SECTORS:
            raise EEIOError(f"Unknown sector in spend: {key}")
        if amount < 0:
            raise EEIOError(f"Negative spend on {key}")

    totals = total_intensities()
    direct = DIRECT_INTENSITY

    producer: dict[str, float] = {}
    for key, amount in spend.items():
        real = deflate(amount, year)
        parts = split_purchaser_price(key, real) if apply_margins else {key: real}
        for target, value in parts.items():
            producer[target] = producer.get(target, 0.0) + value

    lines: list[dict[str, Any]] = []
    for key in SECTOR_ORDER:
        value = producer.get(key, 0.0)
        if value <= 0.0:
            continue
        lines.append({
            "sector": key,
            "label": SECTORS[key]["label"],
            "producer_spend": round(value, 2),
            "purchaser_spend": round(spend.get(key, 0.0), 2),
            "total_kg": round(value * totals[key], 3),
            "direct_only_kg": round(value * direct[key], 3),
            "overlaps": PHYSICAL_OVERLAP.get(key),
        })
    lines.sort(key=lambda row: row["total_kg"], reverse=True)

    total_kg = sum(row["total_kg"] for row in lines)
    direct_kg = sum(row["direct_only_kg"] for row in lines)
    return {
        "year": year,
        "price_year": BASE_PRICE_YEAR,
        "margins_applied": apply_margins,
        "nominal_spend": round(sum(spend.values()), 2),
        "real_spend": round(sum(producer.values()), 2),
        "total_kg": round(total_kg, 3),
        "direct_only_kg": round(direct_kg, 3),
        "understatement_factor": round(total_kg / direct_kg, 3) if direct_kg else 0.0,
        "lines": lines,
    }


def structural_paths(
    sector: str,
    amount: float = 1.0,
    max_depth: int = DEFAULT_PATH_DEPTH,
    threshold: float = DEFAULT_PATH_THRESHOLD,
) -> dict[str, Any]:
    """Decompose a sector's footprint into the supply chains that carry it.

    A number that is larger than the user expected is not persuasive on its own.
    This says *where* it comes from: "180 kg of your food spend is agriculture,
    reached through food manufacturing".

    Enumeration is depth-limited, so it never accounts for the whole total. The
    unexplained remainder is reported rather than quietly dropped - it is the
    part of the chain that is too diffuse to name, and pretending it is zero
    would be the same truncation error this module exists to fix.
    """
    if sector not in SECTORS:
        raise EEIOError(f"Unknown sector: {sector}")
    if max_depth < 1:
        raise EEIOError("Path depth must be at least 1")

    matrix = build_matrix()
    index = {key: n for n, key in enumerate(SECTOR_ORDER)}
    total = total_intensities()[sector] * amount
    paths: list[dict[str, Any]] = []

    def walk(current: str, coefficient: float, trail: list[str]) -> None:
        emissions = coefficient * DIRECT_INTENSITY[current] * amount
        if total and abs(emissions / total) >= threshold:
            paths.append({
                "path": list(trail),
                "kg": round(emissions, 4),
                "share": round(emissions / total, 4) if total else 0.0,
                "depth": len(trail),
            })
        if len(trail) >= max_depth:
            return
        col = index[current]
        for supplier in SECTOR_ORDER:
            step = matrix[index[supplier]][col]
            if step <= 0.0:
                continue
            next_coefficient = coefficient * step
            # Prune once a path can no longer reach the threshold even if every
            # remaining sector were the dirtiest one in the table.
            ceiling = next_coefficient * max(DIRECT_INTENSITY.values()) * amount
            if total and abs(ceiling / total) < threshold:
                continue
            walk(supplier, next_coefficient, trail + [supplier])

    walk(sector, 1.0, [sector])
    paths.sort(key=lambda row: row["kg"], reverse=True)
    explained = sum(row["kg"] for row in paths)
    return {
        "sector": sector,
        "label": SECTORS[sector]["label"],
        "amount": round(amount, 2),
        "total_kg": round(total, 4),
        "explained_kg": round(explained, 4),
        "unexplained_kg": round(total - explained, 4),
        "explained_share": round(explained / total, 4) if total else 0.0,
        "max_depth": max_depth,
        "paths": paths,
    }


def declare_overlap(spend: dict[str, float]) -> list[dict[str, Any]]:
    """Which of this spend is already likely counted physically elsewhere."""
    rows = []
    for key, amount in spend.items():
        if key not in SECTORS:
            raise EEIOError(f"Unknown sector in spend: {key}")
        category = PHYSICAL_OVERLAP.get(key)
        if category:
            rows.append({
                "sector": key,
                "label": SECTORS[key]["label"],
                "physical_category": category,
                "spend": round(amount, 2),
            })
    return rows


def hybrid_footprint(
    spend: dict[str, float],
    physical_kg: dict[str, float],
    year: int = BASE_PRICE_YEAR,
) -> dict[str, Any]:
    """Physical data where it exists, spend-based for the rest, overlap removed.

    This is the construction that makes a spend-based module safe to use next to
    ``emissions.py``. The removal is the whole point: a hybrid inventory that
    adds a spend total to a physical total without subtracting the intersection
    is not a better inventory, it is a double-counted one.
    """
    covered = {
        key for key, category in PHYSICAL_OVERLAP.items()
        if category in physical_kg
    }
    remaining = {
        key: amount for key, amount in spend.items() if key not in covered
    }

    displaced = {key: spend[key] for key in spend if key in covered}
    spend_side = spend_footprint(remaining, year=year) if remaining else None
    physical_total = sum(physical_kg.values())
    spend_total = spend_side["total_kg"] if spend_side else 0.0

    naive = spend_footprint(spend, year=year)["total_kg"] + physical_total
    return {
        "physical_kg": round(physical_total, 3),
        "spend_kg": round(spend_total, 3),
        "total_kg": round(physical_total + spend_total, 3),
        "naive_total_kg": round(naive, 3),
        "double_count_avoided_kg": round(naive - physical_total - spend_total, 3),
        "displaced_spend": {k: round(v, 2) for k, v in displaced.items()},
        "physical_categories": sorted(physical_kg),
        "spend_detail": spend_side,
    }


def sensitivity(
    spend: dict[str, float],
    year: int = BASE_PRICE_YEAR,
) -> list[dict[str, Any]]:
    """The footprint under the choices that are genuinely arguable.

    Truncating the supply chain and ignoring margins are not exotic errors -
    they are what a per-category factor does. Showing them next to the full
    result is the argument for the full result.
    """
    rows: list[dict[str, Any]] = []
    full = spend_footprint(spend, year=year)
    rows.append({
        "variant": "Full model",
        "note": "closed-form inverse, margins split, deflated",
        "total_kg": full["total_kg"],
    })
    rows.append({
        "variant": "Direct intensities only",
        "note": "what a per-category factor gives",
        "total_kg": full["direct_only_kg"],
    })
    rows.append({
        "variant": "Margins not split",
        "note": "producing sector's multiplier applied to the retail markup",
        "total_kg": spend_footprint(spend, year=year, apply_margins=False)["total_kg"],
    })
    if year != BASE_PRICE_YEAR:
        rows.append({
            "variant": "Not deflated",
            "note": f"{year} money treated as {BASE_PRICE_YEAR} money",
            "total_kg": spend_footprint(spend, year=BASE_PRICE_YEAR)["total_kg"],
        })
    for terms in (1, 2, 3, 5):
        truncated = series_intensities(terms)
        producer: dict[str, float] = {}
        for key, amount in spend.items():
            for target, value in split_purchaser_price(key, deflate(amount, year)).items():
                producer[target] = producer.get(target, 0.0) + value
        rows.append({
            "variant": f"Truncated at {terms} tier{'s' if terms > 1 else ''}",
            "note": "supply chain cut off part way up",
            "total_kg": round(
                sum(value * truncated[key] for key, value in producer.items()), 3
            ),
        })
    return rows


def get_eeio_insights(result: dict[str, Any]) -> list[str]:
    """Plain-language readings of a footprint result."""
    insights: list[str] = []
    if not result.get("lines"):
        return ["No spend to analyse."]

    factor = result.get("understatement_factor", 0.0)
    if factor >= 1.5:
        insights.append(
            f"Counting only what sellers emit directly would report "
            f"{result['direct_only_kg']:.0f} kg. Including their supply chains "
            f"gives {result['total_kg']:.0f} kg - {factor:.1f} times as much."
        )

    top = result["lines"][0]
    share = top["total_kg"] / result["total_kg"] if result["total_kg"] else 0.0
    insights.append(
        f"{top['label']} is the largest single sector at {top['total_kg']:.0f} kg, "
        f"{share:.0%} of the total."
    )

    hidden = [
        row for row in result["lines"]
        if row["direct_only_kg"] and row["total_kg"] / row["direct_only_kg"] >= 3.0
    ]
    if hidden:
        names = ", ".join(row["label"] for row in hidden[:3])
        insights.append(
            f"Most of the footprint of {names} is upstream rather than at the "
            "point of sale, so a direct factor would miss nearly all of it."
        )

    overlapping = [row for row in result["lines"] if row.get("overlaps")]
    if overlapping:
        total = sum(row["total_kg"] for row in overlapping)
        insights.append(
            f"{total:.0f} kg of this sits in sectors that are usually also "
            "measured physically. Subtract the overlap before adding this to "
            "another total."
        )

    if result.get("margins_applied"):
        insights.append(
            "Retail and transport margins have been routed to the retail and "
            "freight sectors rather than left with the producer."
        )
    return insights


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_NAME)


def init_eeio_db() -> bool:
    """Create the table if it does not exist yet."""
    conn = None
    try:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS eeio_spend_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                year INTEGER NOT NULL,
                nominal_spend REAL NOT NULL,
                total_kg REAL NOT NULL,
                direct_only_kg REAL NOT NULL,
                detail_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Unable to initialise eeio table: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_profile(user_id: int, name: str, result: dict[str, Any]) -> int | None:
    """Persist a spend profile. Returns the row id or None."""
    init_eeio_db()
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            """
            INSERT INTO eeio_spend_profiles (
                user_id, name, year, nominal_spend, total_kg,
                direct_only_kg, detail_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(user_id),
                str(name),
                int(result.get("year", BASE_PRICE_YEAR)),
                float(result.get("nominal_spend", 0.0)),
                float(result.get("total_kg", 0.0)),
                float(result.get("direct_only_kg", 0.0)),
                json.dumps(result),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save spend profile: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_profiles(user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    """Saved profiles, newest first."""
    init_eeio_db()
    conn = None
    try:
        conn = _connect()
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT * FROM eeio_spend_profiles
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (int(user_id), int(limit)),
        ).fetchall()
        profiles = []
        for row in rows:
            record = dict(row)
            if record.get("detail_json"):
                try:
                    record["detail"] = json.loads(record["detail_json"])
                except (TypeError, ValueError):
                    record["detail"] = None
            profiles.append(record)
        return profiles
    except sqlite3.Error as exc:
        logger.error("Unable to read spend profiles: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def delete_profile(profile_id: int, user_id: int) -> bool:
    """Delete a profile the user owns."""
    conn = None
    try:
        conn = _connect()
        cursor = conn.execute(
            "DELETE FROM eeio_spend_profiles WHERE id = ? AND user_id = ?",
            (int(profile_id), int(user_id)),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Unable to delete spend profile: %s", exc)
        return False
    finally:
        if conn:
            conn.close()
