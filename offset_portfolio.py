"""Carbon Offset Portfolio & Net-Zero Roadmap for EcoBuddy AI.

Lets users build a portfolio of verified carbon offset projects, track
offset purchases, project their net-zero timeline with milestone markers,
and generate offset certificates for individual transactions or the full
portfolio.

Offset data is based on published project registries (Gold Standard, VCS)
and intentionally simplified so the module can be extended without
changing the calculation core.
"""

from __future__ import annotations

import os
import json
import sqlite3
import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

# ── Offset Projects Catalogue ────────────────────────────────────────────────

OFFSET_PROJECTS: dict[str, dict[str, Any]] = {
    "reforestation_amazon": {
        "name": "Amazon Reforestation Initiative",
        "region": "South America",
        "type": "Reforestation",
        "registry": "Gold Standard",
        "price_per_tonne": 18.50,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Biodiversity", "Community Livelihoods", "Water Cycles"],
        "rating": 4.8,
        "description": (
            "Planting native tree species in degraded areas of the Amazon "
            "rainforest, restoring habitat and sequestering carbon while "
            "supporting indigenous communities."
        ),
        "verification_url": "https://goldstandard.org/project/amazon-reforestation",
        "annual_capacity_tonnes": 50000,
        "remaining_capacity_tonnes": 32000,
    },
    "clean_cookstoves_india": {
        "name": "Clean Cookstoves — Rural India",
        "region": "South Asia",
        "type": "Energy Access",
        "registry": "Gold Standard",
        "price_per_tonne": 12.00,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Health", "Gender Equality", "Indoor Air Quality"],
        "rating": 4.7,
        "description": (
            "Distributing fuel-efficient cookstoves to rural households, "
            "reducing indoor air pollution and deforestation pressure."
        ),
        "verification_url": "https://goldstandard.org/project/clean-cookstoves-india",
        "annual_capacity_tonnes": 80000,
        "remaining_capacity_tonnes": 45000,
    },
    "wind_energy_brazil": {
        "name": "Wind Farm Expansion — Northeast Brazil",
        "region": "South America",
        "type": "Renewable Energy",
        "registry": "VCS (Verra)",
        "price_per_tonne": 9.50,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Clean Energy", "Job Creation", "Grid Stability"],
        "rating": 4.5,
        "description": (
            "Expanding onshore wind capacity in Brazil's northeast, "
            "displacing fossil-fuel electricity generation."
        ),
        "verification_url": "https://verra.org/project/wind-brazil",
        "annual_capacity_tonnes": 120000,
        "remaining_capacity_tonnes": 78000,
    },
    "methane_capture_landfill": {
        "name": "Landfill Methane Capture — Southeast Asia",
        "region": "Southeast Asia",
        "type": "Methane Avoidance",
        "registry": "VCS (Verra)",
        "price_per_tonne": 14.00,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Air Quality", "Community Health", "Waste Management"],
        "rating": 4.3,
        "description": (
            "Capturing and flaring methane emissions from landfills in "
            "Southeast Asia, preventing potent greenhouse gas release."
        ),
        "verification_url": "https://verra.org/project/methane-sea",
        "annual_capacity_tonnes": 65000,
        "remaining_capacity_tonnes": 40000,
    },
    "ocean_kelp_uk": {
        "name": "Kelp Forest Restoration — UK Coast",
        "region": "Europe",
        "type": "Blue Carbon",
        "registry": "Gold Standard",
        "price_per_tonne": 22.00,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Marine Biodiversity", "Coastal Protection", "Fisheries"],
        "rating": 4.9,
        "description": (
            "Restoring kelp forests along the UK coastline to sequester "
            "carbon and rebuild marine ecosystems."
        ),
        "verification_url": "https://goldstandard.org/project/kelp-uk",
        "annual_capacity_tonnes": 15000,
        "remaining_capacity_tonnes": 9500,
    },
    "solar_rural_africa": {
        "name": "Solar Microgrids — Rural East Africa",
        "region": "Africa",
        "type": "Renewable Energy",
        "registry": "Gold Standard",
        "price_per_tonne": 11.00,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Energy Access", "Education", "Economic Development"],
        "rating": 4.6,
        "description": (
            "Deploying solar microgrids to off-grid villages in East Africa, "
            "replacing diesel generators."
        ),
        "verification_url": "https://goldstandard.org/project/solar-africa",
        "annual_capacity_tonnes": 40000,
        "remaining_capacity_tonnes": 28000,
    },
    "mangrove_restoration": {
        "name": "Mangrove Restoration — Philippines",
        "region": "Southeast Asia",
        "type": "Blue Carbon",
        "registry": "Gold Standard",
        "price_per_tonne": 16.00,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Storm Protection", "Fisheries", "Biodiversity"],
        "rating": 4.7,
        "description": (
            "Replanting mangrove forests in coastal Philippines, protecting "
            "communities from storms while sequestering carbon."
        ),
        "verification_url": "https://goldstandard.org/project/mangrove-ph",
        "annual_capacity_tonnes": 25000,
        "remaining_capacity_tonnes": 16000,
    },
    "soil_carbon_regen": {
        "name": "Regenerative Agriculture — Midwest USA",
        "region": "North America",
        "type": "Soil Carbon",
        "registry": "VCS (Verra)",
        "price_per_tonne": 20.00,
        "co2_per_tonne_removed": 1.0,
        "co_benefits": ["Soil Health", "Water Retention", "Farm Resilience"],
        "rating": 4.4,
        "description": (
            "Supporting farmers in transitioning to regenerative practices "
            "that build soil organic carbon."
        ),
        "verification_url": "https://verra.org/project/soil-carbon-us",
        "annual_capacity_tonnes": 35000,
        "remaining_capacity_tonnes": 22000,
    },
}


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class OffsetTransaction:
    """A single offset purchase record."""
    id: str
    user_id: int
    project_key: str
    tonnes_co2: float
    cost_usd: float
    certificate_id: str
    timestamp: str
    status: str = "active"  # active, retired, cancelled


@dataclass
class PortfolioSummary:
    """Aggregated portfolio statistics."""
    user_id: int
    total_tonnes_offset: float
    total_cost_usd: float
    total_projects: int
    project_breakdown: dict[str, float]
    portfolio_rating: float
    offset_vs_footprint_pct: float
    net_remaining_tonnes: float
    is_net_zero: bool
    certificates: list[dict[str, Any]]


@dataclass
class NetZeroProjection:
    """Timeline projection for reaching net-zero."""
    current_footprint_tonnes: float
    current_offset_tonnes: float
    annual_reduction_rate_pct: float
    annual_new_offsets_tonnes: float
    years_to_net_zero: float | None
    target_year: int | None
    milestones: list[dict[str, Any]]
    monthly_projection: list[dict[str, Any]]


@dataclass
class OffsetCertificate:
    """A generated offset certificate."""
    certificate_id: str
    user_id: int
    project_name: str
    project_type: str
    tonnes_co2: float
    cost_usd: float
    issued_date: str
    registry: str
    verification_url: str


# ── Portfolio Calculator ─────────────────────────────────────────────────────


def calculate_offset_cost(
    project_key: str,
    tonnes: float,
) -> dict[str, Any]:
    """Calculate the cost and details of an offset purchase."""
    if project_key not in OFFSET_PROJECTS:
        raise ValueError(
            f"Unknown project '{project_key}'. "
            f"Available: {sorted(OFFSET_PROJECTS)}"
        )

    project = OFFSET_PROJECTS[project_key]
    price_per_tonne = project["price_per_tonne"]
    total_cost = round(tonnes * price_per_tonne, 2)
    remaining = project["remaining_capacity_tonnes"]

    if tonnes > remaining:
        raise ValueError(
            f"Requested {tonnes} tonnes exceeds remaining capacity "
            f"of {remaining} tonnes for {project['name']}."
        )

    # Impact equivalents
    trees_needed = round(tonnes * 21, 0)  # ~21 kg CO2 per tree per year
    km_not_driven = round(tonnes * 1000 / 0.21, 0)  # ~0.21 kg/km

    return {
        "project_key": project_key,
        "project_name": project["name"],
        "project_type": project["type"],
        "registry": project["registry"],
        "price_per_tonne": price_per_tonne,
        "tonnes": tonnes,
        "total_cost_usd": total_cost,
        "remaining_capacity": remaining,
        "co_benefits": project["co_benefits"],
        "rating": project["rating"],
        "equivalents": {
            "trees_needed_per_year": trees_needed,
            "km_not_driven": km_not_driven,
        },
    }


def calculate_portfolio_summary(
    transactions: list[dict[str, Any]],
    annual_footprint_tonnes: float = 0.0,
) -> PortfolioSummary:
    """Build an aggregated summary of the user's offset portfolio."""
    total_tonnes = 0.0
    total_cost = 0.0
    project_breakdown: dict[str, float] = {}
    certificates: list[dict[str, Any]] = []
    user_id = 0

    for tx in transactions:
        user_id = tx.get("user_id", user_id)
        tonnes = float(tx.get("tonnes_co2", 0))
        cost = float(tx.get("cost_usd", 0))
        project_key = tx.get("project_key", "unknown")

        total_tonnes += tonnes
        total_cost += cost
        project_breakdown[project_key] = project_breakdown.get(project_key, 0) + tonnes

        if tx.get("certificate_id"):
            certificates.append({
                "certificate_id": tx["certificate_id"],
                "project_key": project_key,
                "tonnes_co2": tonnes,
                "issued_date": tx.get("timestamp", ""),
            })

    # Portfolio rating = weighted average of project ratings
    portfolio_rating = 0.0
    if total_tonnes > 0:
        weighted_sum = 0.0
        for proj_key, proj_tonnes in project_breakdown.items():
            if proj_key in OFFSET_PROJECTS:
                weighted_sum += OFFSET_PROJECTS[proj_key]["rating"] * proj_tonnes
        portfolio_rating = round(weighted_sum / total_tonnes, 1)

    offset_pct = (
        round((total_tonnes / annual_footprint_tonnes) * 100, 1)
        if annual_footprint_tonnes > 0
        else 0.0
    )
    net_remaining = round(annual_footprint_tonnes - total_tonnes, 2)

    return PortfolioSummary(
        user_id=user_id,
        total_tonnes_offset=round(total_tonnes, 2),
        total_cost_usd=round(total_cost, 2),
        total_projects=len(project_breakdown),
        project_breakdown=project_breakdown,
        portfolio_rating=portfolio_rating,
        offset_vs_footprint_pct=offset_pct,
        net_remaining_tonnes=net_remaining,
        is_net_zero=net_remaining <= 0,
        certificates=certificates,
    )


# ── Net-Zero Projection ─────────────────────────────────────────────────────


def project_net_zero_timeline(
    current_footprint_tonnes: float,
    current_offset_tonnes: float,
    annual_reduction_rate_pct: float = 5.0,
    annual_new_offsets_tonnes: float = 2.0,
    years_ahead: int = 20,
) -> NetZeroProjection:
    """Project when the user will reach net-zero based on current trajectory.

    Parameters
    ----------
    current_footprint_tonnes : float
        User's current annual carbon footprint in tonnes.
    current_offset_tonnes : float
        Total tonnes already offset.
    annual_reduction_rate_pct : float
        Expected annual percentage reduction in footprint.
    annual_new_offsets_tonnes : float
        Additional tonnes expected to be offset each year.
    years_ahead : int
        How many years to project forward.
    """
    months = years_ahead * 12
    monthly_reduction = annual_reduction_rate_pct / 100 / 12
    monthly_new_offsets = annual_new_offsets_tonnes / 12

    monthly_projection: list[dict[str, Any]] = []
    current_fp = current_footprint_tonnes
    current_off = current_offset_tonnes
    year_to_net_zero = None

    for month in range(months + 1):
        net = round(current_fp - current_off, 3)
        monthly_projection.append({
            "month": month,
            "year_offset": round(month / 12, 1),
            "footprint_tonnes": round(current_fp, 3),
            "offset_tonnes": round(current_off, 3),
            "net_emissions": round(net, 3),
        })

        if net <= 0 and year_to_net_zero is None and month > 0:
            year_to_net_zero = round(month / 12, 1)

        # Apply monthly changes
        current_fp *= (1 - monthly_reduction)
        current_off += monthly_new_offsets

    target_year = None
    if year_to_net_zero is not None:
        target_year = datetime.now().year + int(math.ceil(year_to_net_zero))

    # Build milestones
    milestones = _build_milestones(
        current_footprint_tonnes,
        current_offset_tonnes,
        annual_reduction_rate_pct,
        annual_new_offsets_tonnes,
        year_to_net_zero,
    )

    return NetZeroProjection(
        current_footprint_tonnes=current_footprint_tonnes,
        current_offset_tonnes=current_offset_tonnes,
        annual_reduction_rate_pct=annual_reduction_rate_pct,
        annual_new_offsets_tonnes=annual_new_offsets_tonnes,
        years_to_net_zero=year_to_net_zero,
        target_year=target_year,
        milestones=milestones,
        monthly_projection=monthly_projection,
    )


def _build_milestones(
    footprint: float,
    offset: float,
    reduction_rate: float,
    new_offsets: float,
    net_zero_year: float | None,
) -> list[dict[str, Any]]:
    """Create milestone markers for the roadmap."""
    milestones: list[dict[str, Any]] = []

    # Start milestone
    offset_pct = (offset / footprint * 100) if footprint > 0 else 0
    milestones.append({
        "label": "Today",
        "year_offset": 0,
        "description": f"Footprint: {footprint:.1f}t | Offset: {offset:.1f}t ({offset_pct:.0f}%)",
        "type": "start",
        "met": True,
    })

    # 25% offset milestone
    if footprint > 0:
        target_25 = footprint * 0.25
        if offset < target_25:
            years_to_25 = max(0, (target_25 - offset) / new_offsets) if new_offsets > 0 else float("inf")
        else:
            years_to_25 = 0
        milestones.append({
            "label": "25% Offset",
            "year_offset": round(years_to_25, 1),
            "description": f"Offset 25% of footprint ({target_25:.1f}t)",
            "type": "milestone",
            "met": offset_pct >= 25,
        })

    # 50% offset milestone
    if footprint > 0:
        target_50 = footprint * 0.50
        if offset < target_50:
            years_to_50 = max(0, (target_50 - offset) / new_offsets) if new_offsets > 0 else float("inf")
        else:
            years_to_50 = 0
        milestones.append({
            "label": "50% Offset",
            "year_offset": round(years_to_50, 1),
            "description": f"Offset 50% of footprint ({target_50:.1f}t)",
            "type": "milestone",
            "met": offset_pct >= 50,
        })

    # 75% offset milestone
    if footprint > 0:
        target_75 = footprint * 0.75
        if offset < target_75:
            years_to_75 = max(0, (target_75 - offset) / new_offsets) if new_offsets > 0 else float("inf")
        else:
            years_to_75 = 0
        milestones.append({
            "label": "75% Offset",
            "year_offset": round(years_to_75, 1),
            "description": f"Offset 75% of footprint ({target_75:.1f}t)",
            "type": "milestone",
            "met": offset_pct >= 75,
        })

    # Carbon Neutral (100% offset)
    if net_zero_year is not None:
        milestones.append({
            "label": "🌿 Carbon Neutral",
            "year_offset": net_zero_year,
            "description": f"Fully offset all emissions",
            "type": "goal",
            "met": False,
        })

    # 50% reduction milestone
    reduction_50_year = None
    if reduction_rate > 0:
        reduction_50_year = round(math.log(0.5) / math.log(1 - reduction_rate / 100), 1)
        milestones.append({
            "label": "50% Footprint Reduction",
            "year_offset": reduction_50_year,
            "description": f"Reduce footprint to {footprint * 0.5:.1f}t through behaviour changes",
            "type": "milestone",
            "met": False,
        })

    milestones.sort(key=lambda m: m["year_offset"])
    return milestones


# ── Certificate Generator ───────────────────────────────────────────────────


def generate_certificate(
    user_id: int,
    project_key: str,
    tonnes_co2: float,
    cost_usd: float,
) -> OffsetCertificate:
    """Generate an offset certificate for a purchase."""
    if project_key not in OFFSET_PROJECTS:
        raise ValueError(f"Unknown project '{project_key}'")

    project = OFFSET_PROJECTS[project_key]
    cert_id = f"ECO-{uuid.uuid4().hex[:8].upper()}"

    return OffsetCertificate(
        certificate_id=cert_id,
        user_id=user_id,
        project_name=project["name"],
        project_type=project["type"],
        tonnes_co2=tonnes_co2,
        cost_usd=cost_usd,
        issued_date=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        registry=project["registry"],
        verification_url=project["verification_url"],
    )


def format_certificate_text(cert: OffsetCertificate) -> str:
    """Format a certificate as readable text."""
    lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║            🌍 CARBON OFFSET CERTIFICATE                  ║",
        "╠══════════════════════════════════════════════════════════╣",
        f"║  Certificate ID:  {cert.certificate_id:<37}║",
        f"║  Issued:          {cert.issued_date:<37}║",
        "║                                                            ║",
        f"║  Project:         {cert.project_name:<37}║",
        f"║  Type:            {cert.project_type:<37}║",
        f"║  Registry:        {cert.registry:<37}║",
        "║                                                            ║",
        f"║  CO₂ Offset:      {cert.tonnes_co2:>8.2f} tonnes                      ║",
        f"║  Cost:            ${cert.cost_usd:>8.2f} USD                        ║",
        "║                                                            ║",
        f"║  Verification:    {cert.verification_url:<37}║",
        "║                                                            ║",
        "║  This certificate confirms that the above quantity of     ║",
        "║  carbon dioxide has been offset through a verified         ║",
        "║  carbon offset project.                                    ║",
        "╚══════════════════════════════════════════════════════════╝",
    ]
    return "\n".join(lines)


# ── Database Persistence ────────────────────────────────────────────────────


def init_offset_db() -> bool:
    """Create the offset portfolio tables if needed."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS offset_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                project_key TEXT NOT NULL,
                project_name TEXT NOT NULL,
                tonnes_co2 REAL NOT NULL,
                cost_usd REAL NOT NULL,
                certificate_id TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS offset_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                annual_footprint_tonnes REAL NOT NULL,
                target_reduction_pct REAL DEFAULT 5.0,
                target_new_offsets_per_year REAL DEFAULT 2.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Offset DB init error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_offset_transaction(
    user_id: int,
    project_key: str,
    tonnes_co2: float,
    cost_usd: float,
    certificate_id: str,
) -> int | None:
    """Persist an offset purchase. Returns the new row id."""
    init_offset_db()
    conn = None
    try:
        project_name = OFFSET_PROJECTS.get(project_key, {}).get("name", project_key)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.execute(
            """
            INSERT INTO offset_transactions
                (user_id, project_key, project_name, tonnes_co2, cost_usd, certificate_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, project_key, project_name, tonnes_co2, cost_usd, certificate_id),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save offset transaction: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_offset_transactions(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    """Return a user's offset transactions, newest first."""
    init_offset_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, user_id, project_key, project_name, tonnes_co2,
                   cost_usd, certificate_id, status, created_at
            FROM offset_transactions
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.error("Unable to load offset transactions: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def save_offset_goal(
    user_id: int,
    annual_footprint_tonnes: float,
    reduction_pct: float = 5.0,
    new_offsets_per_year: float = 2.0,
) -> int | None:
    """Save the user's net-zero goal parameters."""
    init_offset_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.execute(
            """
            INSERT INTO offset_goals
                (user_id, annual_footprint_tonnes, target_reduction_pct, target_new_offsets_per_year)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, annual_footprint_tonnes, reduction_pct, new_offsets_per_year),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as exc:
        logger.error("Unable to save offset goal: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def get_offset_goal(user_id: int) -> dict[str, Any] | None:
    """Retrieve the user's most recent offset goal."""
    init_offset_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT annual_footprint_tonnes, target_reduction_pct,
                   target_new_offsets_per_year, created_at
            FROM offset_goals
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        return dict(row) if row else None
    except sqlite3.Error as exc:
        logger.error("Unable to load offset goal: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


# ── Catalogue Helpers ────────────────────────────────────────────────────────


def list_offset_projects(region: str | None = None) -> list[dict[str, Any]]:
    """List all available offset projects, optionally filtered by region."""
    projects = []
    for key, info in OFFSET_PROJECTS.items():
        if region and info["region"] != region:
            continue
        projects.append({
            "key": key,
            "name": info["name"],
            "region": info["region"],
            "type": info["type"],
            "registry": info["registry"],
            "price_per_tonne": info["price_per_tonne"],
            "rating": info["rating"],
            "remaining_capacity": info["remaining_capacity_tonnes"],
            "co_benefits": info["co_benefits"],
        })
    return projects


def list_regions() -> list[str]:
    """Return all unique project regions."""
    return sorted(set(p["region"] for p in OFFSET_PROJECTS.values()))


def list_project_types() -> list[str]:
    """Return all unique project types."""
    return sorted(set(p["type"] for p in OFFSET_PROJECTS.values()))
