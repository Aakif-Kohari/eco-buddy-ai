"""
Eco-Footprint Scenario Simulator Database Layer
Handles SQLite table creation, scenario saving, loading, projection history, and defaults.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from database_connection import database_connection, execute_with_retry
from eco_scenario_simulator_types import (
    FootprintScenario,
    ScenarioLever,
    ScenarioLeverCategory,
)

logger = logging.getLogger(__name__)
DB_NAME = "eco_buddy.db"


def init_scenario_simulator_db(db_name: str = DB_NAME) -> bool:
    """Initializes SQLite tables for footprint scenario simulation."""
    def _create():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Saved Scenarios Master Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS eco_footprint_scenarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    scenario_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    target_year INTEGER NOT NULL,
                    baseline_co2_kg REAL NOT NULL,
                    simulated_co2_kg REAL NOT NULL,
                    reduction_pct REAL NOT NULL,
                    levers_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    try:
        execute_with_retry(_create)
        return True
    except sqlite3.Error as e:
        logger.error("Failed to initialize scenario simulator DB: %s", e)
        return False


def save_footprint_scenario(scenario: FootprintScenario, db_name: str = DB_NAME) -> Optional[FootprintScenario]:
    """Saves a user scenario configuration to database."""
    def _insert():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            levers_dict_list = [
                {
                    "name": l.name,
                    "category": l.category.value,
                    "baseline_value": l.baseline_value,
                    "simulated_value": l.simulated_value,
                    "unit": l.unit,
                    "emission_factor_kg": l.emission_factor_kg,
                    "description": l.description,
                }
                for l in scenario.levers
            ]
            levers_json = json.dumps(levers_dict_list)

            base_co2 = scenario.calculate_total_baseline_co2_kg()
            sim_co2 = scenario.calculate_total_simulated_co2_kg()
            red_pct = scenario.calculate_annual_reduction_pct()

            cursor.execute("""
                INSERT INTO eco_footprint_scenarios (user_id, scenario_name, description, target_year, baseline_co2_kg, simulated_co2_kg, reduction_pct, levers_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scenario.user_id, scenario.scenario_name, scenario.description,
                scenario.target_year, base_co2, sim_co2, red_pct, levers_json
            ))

            scenario.id = cursor.lastrowid
            conn.commit()
            return scenario

    try:
        return execute_with_retry(_insert)
    except Exception as e:
        logger.error("Error saving scenario: %s", e)
        return None


def get_user_scenarios(user_id: int, db_name: str = DB_NAME) -> List[FootprintScenario]:
    """Fetches saved scenarios for a specific user."""
    def _fetch():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, scenario_name, description, target_year, levers_json, created_at
                FROM eco_footprint_scenarios
                WHERE user_id = ?
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                levers_raw = json.loads(r[5]) if r[5] else []
                levers = [
                    ScenarioLever(
                        name=l["name"],
                        category=ScenarioLeverCategory(l["category"]),
                        baseline_value=float(l["baseline_value"]),
                        simulated_value=float(l["simulated_value"]),
                        unit=l["unit"],
                        emission_factor_kg=float(l["emission_factor_kg"]),
                        description=l["description"],
                    )
                    for l in levers_raw
                ]
                results.append(FootprintScenario(
                    id=r[0],
                    user_id=r[1],
                    scenario_name=r[2],
                    description=r[3],
                    target_year=r[4],
                    levers=levers,
                    created_at=str(r[6]),
                ))
            return results

    try:
        return execute_with_retry(_fetch)
    except Exception as e:
        logger.error("Error fetching user scenarios: %s", e)
        return []
