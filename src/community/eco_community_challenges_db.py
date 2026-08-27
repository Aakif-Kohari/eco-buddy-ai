"""
Eco-Community Challenges Database Engine
Handles database initialization, schema migration, CRUD operations, and progress logging for challenges.
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import date, timedelta, datetime

from src.core.database_connection import database_connection, execute_with_retry
from src.community.eco_community_challenges_types import (
    CommunityChallenge,
    ChallengeCategory,
    ChallengeDifficulty,
    VerificationType,
    ChallengeCriteria,
    UserChallengeEnrollment,
    ChallengeAnalyticsSummary,
)

logger = logging.getLogger(__name__)
DB_NAME = "eco_buddy.db"


def init_community_challenges_db(db_name: str = DB_NAME) -> bool:
    """Initializes database tables for community eco challenges."""
    def _create_tables():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Community Challenges Master Catalog
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS community_challenge_catalog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    duration_days INTEGER NOT NULL,
                    co2_impact_kg REAL NOT NULL,
                    xp_reward INTEGER NOT NULL,
                    criteria_json TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # User Challenge Enrollments
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_challenge_enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    challenge_id INTEGER NOT NULL,
                    joined_date TEXT NOT NULL,
                    target_completion_date TEXT NOT NULL,
                    current_progress REAL DEFAULT 0.0,
                    target_goal REAL NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    proof_submitted TEXT,
                    completed_at TIMESTAMP,
                    FOREIGN KEY(challenge_id) REFERENCES community_challenge_catalog(id)
                )
            """)

            # Progress Activity Log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS challenge_progress_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    enrollment_id INTEGER NOT NULL,
                    increment_value REAL NOT NULL,
                    log_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY(enrollment_id) REFERENCES user_challenge_enrollments(id)
                )
            """)

            conn.commit()

    try:
        execute_with_retry(_create_tables)
        _seed_default_challenges(db_name)
        return True
    except sqlite3.Error as e:
        logger.error("Failed to initialize community challenges DB: %s", e)
        return False


def _seed_default_challenges(db_name: str = DB_NAME) -> None:
    """Seeds default curated eco-challenges into catalog if table is empty."""
    def _seed():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM community_challenge_catalog")
            count = cursor.fetchone()[0]

            if count == 0:
                defaults = [
                    (
                        "Zero-Waste Plastic-Free Week",
                        "Avoid single-use plastics completely for 7 days. Track avoided plastic items.",
                        ChallengeCategory.ZERO_WASTE.value,
                        ChallengeDifficulty.BEGINNER.value,
                        7,
                        5.5,
                        150,
                        json.dumps(ChallengeCriteria("avoided_plastic_items", 14, "items", VerificationType.SELF_REPORT).to_dict()),
                    ),
                    (
                        "100km Clean Commute Sprint",
                        "Log 100km of commuting via walking, cycling, or public transit instead of personal gas car.",
                        ChallengeCategory.SUSTAINABLE_MOBILITY.value,
                        ChallengeDifficulty.INTERMEDIATE.value,
                        14,
                        19.0,
                        350,
                        json.dumps(ChallengeCriteria("clean_commute_km", 100, "km", VerificationType.SELF_REPORT).to_dict()),
                    ),
                    (
                        "14-Day Plant-Power Transformation",
                        "Eat exclusively plant-based meals for 14 consecutive days to reduce dietary emissions.",
                        ChallengeCategory.PLANT_BASED_DIET.value,
                        ChallengeDifficulty.ADVANCED.value,
                        14,
                        32.0,
                        500,
                        json.dumps(ChallengeCriteria("plant_based_meals", 42, "meals", VerificationType.SELF_REPORT).to_dict()),
                    ),
                    (
                        "Home Energy Efficiency Master",
                        "Reduce home electricity consumption by 20 kWh over 10 days by eliminating phantom loads.",
                        ChallengeCategory.ENERGY_SAVER.value,
                        ChallengeDifficulty.INTERMEDIATE.value,
                        10,
                        14.0,
                        300,
                        json.dumps(ChallengeCriteria("kwh_saved", 20, "kWh", VerificationType.METER_READING).to_dict()),
                    ),
                    (
                        "Water-Saver Shower Challenge",
                        "Keep all showers under 5 minutes for 10 days to conserve thousands of liters of clean water.",
                        ChallengeCategory.WATER_CONSERVATION.value,
                        ChallengeDifficulty.BEGINNER.value,
                        10,
                        8.5,
                        200,
                        json.dumps(ChallengeCriteria("short_showers", 10, "showers", VerificationType.SELF_REPORT).to_dict()),
                    ),
                ]

                cursor.executemany("""
                    INSERT INTO community_challenge_catalog
                    (title, description, category, difficulty, duration_days, co2_impact_kg, xp_reward, criteria_json, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                """, defaults)
                conn.commit()

    try:
        execute_with_retry(_seed)
    except Exception as e:
        logger.error("Error seeding default challenges: %s", e)


def get_all_active_challenges(db_name: str = DB_NAME) -> List[CommunityChallenge]:
    """Retrieves all active challenges from the catalog."""
    def _fetch():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, description, category, difficulty, duration_days, co2_impact_kg, xp_reward, criteria_json, created_at, is_active
                FROM community_challenge_catalog
                WHERE is_active = 1
                ORDER BY difficulty ASC, xp_reward ASC
            """)
            rows = cursor.fetchall()
            result = []
            for r in rows:
                crit_dict = json.loads(r[8]) if r[8] else {}
                result.append(CommunityChallenge(
                    id=r[0],
                    title=r[1],
                    description=r[2],
                    category=ChallengeCategory(r[3]),
                    difficulty=ChallengeDifficulty(r[4]),
                    duration_days=r[5],
                    co2_impact_kg=r[6],
                    xp_reward=r[7],
                    criteria=ChallengeCriteria.from_dict(crit_dict),
                    created_at=str(r[9]),
                    is_active=bool(r[10])
                ))
            return result

    try:
        return execute_with_retry(_fetch)
    except Exception as e:
        logger.error("Error getting active challenges: %s", e)
        return []


def enroll_user_in_challenge(user_id: int, challenge_id: int, db_name: str = DB_NAME) -> Optional[UserChallengeEnrollment]:
    """Enrolls a user in a specified challenge."""
    def _enroll():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()

            # Check if active enrollment already exists
            cursor.execute("""
                SELECT id FROM user_challenge_enrollments
                WHERE user_id = ? AND challenge_id = ? AND status = 'ACTIVE'
            """, (user_id, challenge_id))
            existing = cursor.fetchone()
            if existing:
                return None

            # Get challenge criteria & duration
            cursor.execute("""
                SELECT duration_days, criteria_json FROM community_challenge_catalog WHERE id = ?
            """, (challenge_id,))
            ch_data = cursor.fetchone()
            if not ch_data:
                return None

            duration_days = ch_data[0]
            crit_dict = json.loads(ch_data[1]) if ch_data[1] else {}
            target_goal = crit_dict.get("target_value", 10.0)

            joined_date = date.today().isoformat()
            target_completion_date = (date.today() + timedelta(days=duration_days)).isoformat()

            cursor.execute("""
                INSERT INTO user_challenge_enrollments
                (user_id, challenge_id, joined_date, target_completion_date, current_progress, target_goal, status)
                VALUES (?, ?, ?, ?, 0.0, ?, 'ACTIVE')
            """, (user_id, challenge_id, joined_date, target_completion_date, target_goal))
            conn.commit()
            enrollment_id = cursor.lastrowid

            return UserChallengeEnrollment(
                id=enrollment_id,
                user_id=user_id,
                challenge_id=challenge_id,
                joined_date=joined_date,
                target_completion_date=target_completion_date,
                current_progress=0.0,
                target_goal=target_goal,
                status="ACTIVE",
            )

    try:
        return execute_with_retry(_enroll)
    except Exception as e:
        logger.error("Error enrolling user in challenge: %s", e)
        return None


def get_user_enrollments(user_id: int, status_filter: Optional[str] = None, db_name: str = DB_NAME) -> List[Dict[str, Any]]:
    """Fetches user enrollments joined with challenge catalog information."""
    def _fetch():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            query = """
                SELECT 
                    e.id as enrollment_id, e.user_id, e.challenge_id, e.joined_date, e.target_completion_date,
                    e.current_progress, e.target_goal, e.status, e.proof_submitted, e.completed_at,
                    c.title, c.description, c.category, c.difficulty, c.co2_impact_kg, c.xp_reward, c.criteria_json
                FROM user_challenge_enrollments e
                JOIN community_challenge_catalog c ON e.challenge_id = c.id
                WHERE e.user_id = ?
            """
            params = [user_id]
            if status_filter:
                query += " AND e.status = ?"
                params.append(status_filter)
            query += " ORDER BY e.joined_date DESC"

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                crit_dict = json.loads(r[16]) if r[16] else {}
                pct = min(100.0, round((r[5] / r[6]) * 100.0, 1)) if r[6] > 0 else 100.0
                results.append({
                    "enrollment_id": r[0],
                    "user_id": r[1],
                    "challenge_id": r[2],
                    "joined_date": r[3],
                    "target_completion_date": r[4],
                    "current_progress": r[5],
                    "target_goal": r[6],
                    "status": r[7],
                    "proof_submitted": r[8],
                    "completed_at": r[9],
                    "title": r[10],
                    "description": r[11],
                    "category": r[12],
                    "difficulty": r[13],
                    "co2_impact_kg": r[14],
                    "xp_reward": r[15],
                    "unit": crit_dict.get("unit", "units"),
                    "percentage": pct,
                })
            return results

    try:
        return execute_with_retry(_fetch)
    except Exception as e:
        logger.error("Error getting user enrollments: %s", e)
        return []


def record_challenge_progress(enrollment_id: int, increment_value: float, notes: str = "", db_name: str = DB_NAME) -> Dict[str, Any]:
    """Records progress toward an active challenge and marks completion if target met."""
    def _record():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT e.id, e.current_progress, e.target_goal, e.status, c.co2_impact_kg, c.xp_reward, e.user_id
                FROM user_challenge_enrollments e
                JOIN community_challenge_catalog c ON e.challenge_id = c.id
                WHERE e.id = ?
            """, (enrollment_id,))
            row = cursor.fetchone()
            if not row or row[3] != "ACTIVE":
                return {"success": False, "message": "Enrollment not found or not active."}

            current_prog, target_goal, status, co2_impact, xp_reward, user_id = row[1], row[2], row[3], row[4], row[5], row[6]
            new_prog = current_prog + increment_value
            is_completed = new_prog >= target_goal

            new_status = "COMPLETED" if is_completed else "ACTIVE"
            completed_at = datetime.now().isoformat() if is_completed else None

            cursor.execute("""
                UPDATE user_challenge_enrollments
                SET current_progress = ?, status = ?, completed_at = ?
                WHERE id = ?
            """, (new_prog, new_status, completed_at, enrollment_id))

            cursor.execute("""
                INSERT INTO challenge_progress_logs (enrollment_id, increment_value, notes)
                VALUES (?, ?, ?)
            """, (enrollment_id, increment_value, notes))

            conn.commit()

            pct = min(100.0, round((new_prog / target_goal) * 100.0, 1))
            return {
                "success": True,
                "new_progress": new_prog,
                "target_goal": target_goal,
                "percentage": pct,
                "completed": is_completed,
                "xp_earned": xp_reward if is_completed else 0,
                "co2_avoided_kg": co2_impact if is_completed else round(co2_impact * (increment_value / target_goal), 2),
            }

    try:
        return execute_with_retry(_record)
    except Exception as e:
        logger.error("Error recording challenge progress: %s", e)
        return {"success": False, "message": str(e)}


def get_community_analytics_summary(db_name: str = DB_NAME) -> ChallengeAnalyticsSummary:
    """Calculates high-level impact and engagement metrics for community challenges."""
    def _analytics():
        with database_connection(db_name) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM community_challenge_catalog WHERE is_active = 1")
            total_challenges = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT user_id) FROM user_challenge_enrollments WHERE status = 'ACTIVE'")
            active_participants = cursor.fetchone()[0]

            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN e.status = 'COMPLETED' THEN c.co2_impact_kg ELSE c.co2_impact_kg * (e.current_progress / e.target_goal) END),
                    SUM(CASE WHEN e.status = 'COMPLETED' THEN c.xp_reward ELSE 0 END),
                    COUNT(*),
                    SUM(CASE WHEN e.status = 'COMPLETED' THEN 1 ELSE 0 END)
                FROM user_challenge_enrollments e
                JOIN community_challenge_catalog c ON e.challenge_id = c.id
            """)
            row = cursor.fetchone()
            total_co2 = round(row[0] or 0.0, 2)
            total_xp = int(row[1] or 0)
            total_enrollments = row[2] or 0
            completed_enrollments = row[3] or 0

            completion_rate = round((completed_enrollments / total_enrollments) * 100.0, 1) if total_enrollments > 0 else 0.0

            return ChallengeAnalyticsSummary(
                total_challenges=total_challenges,
                active_participants=active_participants,
                total_co2_avoided_kg=total_co2,
                total_xp_awarded=total_xp,
                completion_rate_pct=completion_rate,
            )

    try:
        return execute_with_retry(_analytics)
    except Exception as e:
        logger.error("Error calculating challenge analytics: %s", e)
        return ChallengeAnalyticsSummary(0, 0, 0.0, 0, 0.0)
