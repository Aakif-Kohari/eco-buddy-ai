"""
Eco-Marketplace & Verified Carbon Offsets Database Layer
Handles SQLite table creation, project seeding, transaction processing, and user portfolio queries.
"""

import sqlite3
import json
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.core.database_connection import database_connection, execute_with_retry
from src.carbon.eco_marketplace_offsets_types import (
    CarbonOffsetProject,
    OffsetProjectType,
    OffsetCertificationStandard,
    OffsetPurchaseTransaction,
    UserOffsetPortfolioSummary,
)

logger = logging.getLogger(__name__)
DB_NAME = "eco_buddy.db"


def init_marketplace_offsets_db(db_name: str = DB_NAME) -> bool:
    """Initializes SQLite tables for the verified carbon offsets src.utils.marketplace."""
    def _create():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Offset Projects Catalog Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offset_projects_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    project_type TEXT NOT NULL,
                    certification_standard TEXT NOT NULL,
                    location TEXT NOT NULL,
                    price_per_tonne_usd REAL NOT NULL,
                    total_available_tonnes REAL NOT NULL,
                    permanence_years INTEGER NOT NULL,
                    sdg_goals_json TEXT NOT NULL,
                    rating_stars REAL DEFAULT 4.8,
                    is_verified INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Offset Purchase Transactions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offset_purchase_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    tonnes_purchased REAL NOT NULL,
                    total_cost_usd REAL NOT NULL,
                    certificate_id TEXT UNIQUE NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES offset_projects_catalog(id)
                )
            """)

            conn.commit()

    try:
        execute_with_retry(_create)
        _seed_default_offset_projects(db_name)
        return True
    except sqlite3.Error as e:
        logger.error("Failed to initialize marketplace offsets DB: %s", e)
        return False


def _seed_default_offset_projects(db_name: str = DB_NAME) -> None:
    """Seeds verified carbon credit projects into the catalog if empty."""
    def _seed():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM offset_projects_catalog")
            count = cursor.fetchone()[0]

            if count == 0:
                projects = [
                    (
                        "Amazon Rainforest Community Protection",
                        "Avoided deforestation project protecting biodiversity and supporting local indigenous communities in Brazil.",
                        OffsetProjectType.REFORESTATION.value,
                        OffsetCertificationStandard.GOLD_STANDARD.value,
                        "Brazil",
                        14.50,
                        5000.0,
                        100,
                        json.dumps([13, 15, 1]),
                        4.9,
                    ),
                    (
                        "Kenya Clean Cookstoves Initiative",
                        "Distributing fuel-efficient clean cookstoves to reduce wood consumption and indoor air pollution.",
                        OffsetProjectType.METHANE_CAPTURE.value,
                        OffsetCertificationStandard.GOLD_STANDARD.value,
                        "Kenya",
                        11.00,
                        3500.0,
                        40,
                        json.dumps([3, 5, 13]),
                        4.8,
                    ),
                    (
                        "Kelp Forest Blue Carbon Restoration",
                        "Restoring coastal giant kelp forests off the coast of Maine for high-permanence marine carbon sequestration.",
                        OffsetProjectType.OCEAN_BLUE_CARBON.value,
                        OffsetCertificationStandard.VERRA_VCS.value,
                        "United States",
                        28.00,
                        1200.0,
                        80,
                        json.dumps([14, 13, 8]),
                        4.95,
                    ),
                    (
                        "Iceland Geothermal Direct Air Capture",
                        "Permanently capturing atmospheric CO2 and mineralization storage in deep basalt rock formations.",
                        OffsetProjectType.DIRECT_AIR_CAPTURE.value,
                        OffsetCertificationStandard.AMERICAN_CARBON_REGISTRY.value,
                        "Iceland",
                        120.00,
                        450.0,
                        1000,
                        json.dumps([9, 13, 11]),
                        5.0,
                    ),
                    (
                        "Rajasthan Solar Energy Park",
                        "Utility-scale grid solar energy deployment displacing coal-fired electricity generation in India.",
                        OffsetProjectType.RENEWABLE_ENERGY.value,
                        OffsetCertificationStandard.VERRA_VCS.value,
                        "India",
                        8.75,
                        10000.0,
                        30,
                        json.dumps([7, 13, 9]),
                        4.75,
                    ),
                ]

                cursor.executemany("""
                    INSERT INTO offset_projects_catalog
                    (title, description, project_type, certification_standard, location, price_per_tonne_usd, total_available_tonnes, permanence_years, sdg_goals_json, rating_stars, is_verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, projects)

                conn.commit()

    try:
        execute_with_retry(_seed)
    except Exception as e:
        logger.error("Error seeding offset projects: %s", e)


def get_all_offset_projects(db_name: str = DB_NAME) -> List[CarbonOffsetProject]:
    """Retrieves all verified carbon offset projects from catalog."""
    def _fetch():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, description, project_type, certification_standard, location, price_per_tonne_usd, total_available_tonnes, permanence_years, sdg_goals_json, rating_stars, is_verified
                FROM offset_projects_catalog
                WHERE is_verified = 1
                ORDER BY rating_stars DESC
            """)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                sdgs = json.loads(r[9]) if r[9] else []
                results.append(CarbonOffsetProject(
                    id=r[0],
                    title=r[1],
                    description=r[2],
                    project_type=OffsetProjectType(r[3]),
                    certification_standard=OffsetCertificationStandard(r[4]),
                    location=r[5],
                    price_per_tonne_usd=r[6],
                    total_available_tonnes=r[7],
                    permanence_years=r[8],
                    sdg_goals_supported=sdgs,
                    rating_stars=r[10],
                    is_verified=bool(r[11]),
                ))
            return results

    try:
        return execute_with_retry(_fetch)
    except Exception as e:
        logger.error("Error getting offset projects: %s", e)
        return []


def purchase_carbon_offsets(user_id: int, project_id: int, tonnes: float, db_name: str = DB_NAME) -> Optional[OffsetPurchaseTransaction]:
    """Executes carbon offset purchase, deducts available inventory, and issues retirement src.utils.certificate."""
    def _purchase():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Check inventory & price
            cursor.execute("SELECT price_per_tonne_usd, total_available_tonnes FROM offset_projects_catalog WHERE id = ?", (project_id,))
            proj = cursor.fetchone()
            if not proj or proj[1] < tonnes:
                return None

            price_per_tonne, available = proj[0], proj[1]
            total_cost = round(tonnes * price_per_tonne, 2)
            cert_id = f"CERT-ECO-{uuid.uuid4().hex[:8].upper()}"

            # Deduct inventory
            cursor.execute("UPDATE offset_projects_catalog SET total_available_tonnes = total_available_tonnes - ? WHERE id = ?", (tonnes, project_id))

            # Record purchase
            cursor.execute("""
                INSERT INTO offset_purchase_transactions (user_id, project_id, tonnes_purchased, total_cost_usd, certificate_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, project_id, tonnes, total_cost, cert_id))

            tx_id = cursor.lastrowid
            conn.commit()

            return OffsetPurchaseTransaction(
                id=tx_id,
                user_id=user_id,
                project_id=project_id,
                tonnes_purchased=tonnes,
                total_cost_usd=total_cost,
                certificate_id=cert_id,
                purchased_at=datetime.now().isoformat(),
            )

    try:
        return execute_with_retry(_purchase)
    except Exception as e:
        logger.error("Error executing offset purchase: %s", e)
        return None


def get_user_offset_portfolio(user_id: int, db_name: str = DB_NAME) -> Dict[str, Any]:
    """Calculates user's total retired carbon offset portfolio and certificates."""
    def _portfolio():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    t.id, t.tonnes_purchased, t.total_cost_usd, t.certificate_id, t.purchased_at,
                    p.title, p.project_type, p.certification_standard, p.location
                FROM offset_purchase_transactions t
                JOIN offset_projects_catalog p ON t.project_id = p.id
                WHERE t.user_id = ?
                ORDER BY t.purchased_at DESC
            """, (user_id,))
            rows = cursor.fetchall()

            total_tonnes = sum(r[1] for r in rows)
            total_spent = sum(r[2] for r in rows)
            cert_count = len(rows)

            transactions = [
                {
                    "tx_id": r[0],
                    "tonnes": r[1],
                    "cost_usd": r[2],
                    "certificate_id": r[3],
                    "purchased_at": r[4],
                    "project_title": r[5],
                    "project_type": r[6],
                    "certification": r[7],
                    "location": r[8],
                }
                for r in rows
            ]

            return {
                "summary": UserOffsetPortfolioSummary(
                    total_tonnes_retired=round(total_tonnes, 2),
                    total_spent_usd=round(total_spent, 2),
                    total_certificates=cert_count,
                    diversification_score=min(100.0, cert_count * 20.0),
                    top_project_type="Reforestation" if cert_count > 0 else "None",
                ),
                "transactions": transactions,
            }

    try:
        return execute_with_retry(_portfolio)
    except Exception as e:
        logger.error("Error fetching user offset portfolio: %s", e)
        return {
            "summary": UserOffsetPortfolioSummary(0.0, 0.0, 0, 0.0, "None"),
            "transactions": [],
        }
