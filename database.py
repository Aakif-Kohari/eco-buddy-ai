import os
import sqlite3
from challenge_generator import generate_weekly_challenges
from database import (
    save_weekly_challenge,
    get_weekly_challenges,
    complete_weekly_challenge
)
from database_connection import database_connection, execute_with_retry
from cache import cached
from cache_config import TTL_DB_READ, CACHE_CATEGORY_DB_READS
from invalidation import (
    invalidate_on_assessment_save,
    invalidate_on_assessment_undo,
    invalidate_on_appliance_change,
    invalidate_on_solar_config_save,
    invalidate_on_challenge_enroll,
    invalidate_on_challenge_progress,
    invalidate_on_challenge_complete,
    invalidate_on_xp_award,
    invalidate_on_badge_unlock,
    invalidate_on_skill_tree_update,
    invalidate_on_journey_save,
    invalidate_on_journey_delete,
    invalidate_on_offset_save,
    invalidate_on_offset_delete,
    invalidate_on_offset_clear,
    invalidate_on_water_assessment_save,
    invalidate_on_reduction_goal_change,
    invalidate_on_freeze_token_change,
    invalidate_on_time_capsule_change,
)
import streamlit as st
import bcrypt
import logging

logger = logging.getLogger(__name__)
DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")


def get_db_version(conn):
    """Get the current database schema version using PRAGMA user_version."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA user_version")
    return cursor.fetchone()[0]


def set_db_version(conn, version):
    """Set the database schema version using PRAGMA user_version."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA user_version = {version}")
    conn.commit()


def migrate():
    """
    Apply pending database migrations.

    Returns:
        tuple: (success: bool, message: str)
    """
    import migrations

    try:
        with database_connection(DB_NAME) as conn:
            current_version = get_db_version(conn)

            if current_version >= migrations.CURRENT_VERSION:
                return True, (
                    f"Database is already at version {current_version}"
                )

            migrations_to_apply = range(
                current_version + 1,
                migrations.CURRENT_VERSION + 1,
            )
            for version in migrations_to_apply:
                migration_file = f"migrations/migrate_v{version}.py"
                if os.path.exists(migration_file):
                    module = __import__(
                        f"migrations.migrate_v{version}",
                        fromlist=["migrate"],
                    )
                    if hasattr(module, "migrate"):
                        module.migrate(conn)
                        set_db_version(conn, version)
                        print(f"Applied migration v{version}")

        return True, (
            f"Database migrated to version {migrations.CURRENT_VERSION}"
        )
    except Exception as exc:
        return False, f"Migration failed: {exc}"


def init_db():
    """
    Initialize the database with core tables and run pending migrations.

    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    try:
        def initialize_schema():
            with database_connection(DB_NAME) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        anonymous_leaderboard INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                cursor.execute("""
CREATE TABLE IF NOT EXISTS weekly_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    xp INTEGER NOT NULL,
    category TEXT,
    status TEXT DEFAULT 'Pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

                try:
                    cursor.execute(
                        """
                        ALTER TABLE users
                        ADD COLUMN anonymous_leaderboard INTEGER DEFAULT 0
                        """
                    )
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER DEFAULT 1,
                        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        transport TEXT,
                        distance REAL,
                        electricity REAL,
                        diet TEXT,
                        flights INTEGER,
                        footprint REAL,
                        eco_score INTEGER,
                        trip_id TEXT
                    )
                    """
                )
cursor.execute("""
CREATE TABLE IF NOT EXISTS carbon_budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    budget_type TEXT NOT NULL,
    budget_limit REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
                try:
                    cursor.execute(
                        """
                        ALTER TABLE assessments
                        ADD COLUMN created_at
                        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        """
                    )
                except sqlite3.OperationalError as exc:
                    if "duplicate column name" not in str(exc).lower():
                        raise

                cursor.execute(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_assessments_trip_id
                    ON assessments(trip_id)
                    WHERE trip_id IS NOT NULL
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assessment_drafts (
                        user_id INTEGER PRIMARY KEY,
                        transport TEXT,
                        distance REAL,
                        electricity REAL,
                        diet TEXT,
                        flights INTEGER,
                        region TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS deleted_assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        original_id INTEGER,
                        user_id INTEGER DEFAULT 1,
                        date TIMESTAMP,
                        transport TEXT,
                        distance REAL,
                        electricity REAL,
                        diet TEXT,
                        flights INTEGER,
                        footprint REAL,
                        eco_score INTEGER,
                        deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assessment_activity_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER DEFAULT 1,
                        assessment_id INTEGER,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

        execute_with_retry(initialize_schema)
        migrate()
        return True
    except sqlite3.Error as exc:
        logger.error("Database init error: %s", exc)
        return False


def create_user(
    username,
    email,
    password,
    anonymous_leaderboard=False,
):
    def insert_user():
        with database_connection(DB_NAME) as conn:
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"),
                bcrypt.gensalt(),
            ).decode("utf-8")
            conn.execute(
                """
                INSERT INTO users (
                    username,
                    email,
                    password_hash,
                    anonymous_leaderboard
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    username,
                    email,
                    password_hash,
                    int(bool(anonymous_leaderboard)),
                ),
            )

    try:
        execute_with_retry(insert_user)
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as exc:
        logger.error("Database user creation error: %s", exc)
        return False


def verify_user(username, password):
    def fetch_user():
        with database_connection(DB_NAME) as conn:
            return conn.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    anonymous_leaderboard
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

    try:
        user = execute_with_retry(fetch_user)

        if user and bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8"),
        ):
            return {
                "id": user["id"],
                "username": user["username"],
                "anonymous_leaderboard": bool(
                    user["anonymous_leaderboard"]
                ),
            }
        return None
    except sqlite3.Error as exc:
        logger.error("Database user verification error: %s", exc)
        return None


def get_user_by_username(username):
    def fetch_user():
        with database_connection(DB_NAME) as conn:
            return conn.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    anonymous_leaderboard
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

    try:
        user = execute_with_retry(fetch_user)
        if not user:
            return None

        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "anonymous_leaderboard": bool(
                user["anonymous_leaderboard"]
            ),
        }
    except sqlite3.Error as exc:
        logger.error("Database user lookup error: %s", exc)
        return None


def update_user_leaderboard_preference(user_id, anonymous_leaderboard):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET anonymous_leaderboard = ? WHERE id = ?",
            (int(bool(anonymous_leaderboard)), user_id)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Database update user preference error: {e}")
        return False


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_leaderboard(period="all"):
    """
    Retrieves community leaderboard rankings.
    Returns list of tuples: (display_name, max_eco_score, total_xp, completed_challenges)
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT 
                u.id,
                u.username,
                u.anonymous_leaderboard,
                COALESCE(MAX(a.eco_score), 0) AS max_eco_score,
                COALESCE(SUM(x.amount), 0) AS total_xp,
                COUNT(DISTINCT c.challenge_id) AS completed_challenges
            FROM users u
            LEFT JOIN assessments a ON u.id = a.user_id
            LEFT JOIN xp_transactions x ON u.id = x.user_id
            LEFT JOIN user_challenges c ON u.id = c.user_id AND c.status = 'completed'
            GROUP BY u.id
            ORDER BY max_eco_score DESC, total_xp DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        leaderboard = []
        for row in rows:
            u_id, username, is_anon, eco_score, xp, challenges = row
            display_name = f"User #{u_id}" if is_anon else username
            leaderboard.append((display_name, eco_score, xp, challenges))

        return leaderboard
    except sqlite3.Error as e:
        print(f"Database get_leaderboard error: {e}")
        return []


def save_assessment(
    user_id,
    transport,
    distance,
    electricity,
    diet,
    flights,
    footprint,
    eco_score=0,
    trip_id=None,
    date=None,
    factor_version=None
):
    """
    Persist an assessment.

    `factor_version` records which emission factor set produced the footprint
    (see emission_factors.py). It is optional: rows written without it are read
    back as 'static-v1', which is exactly the factor set the app used before
    versioning existed.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Build the column list from whatever the caller actually supplied,
        # so the optional date / trip_id / factor_version columns keep their
        # database defaults when they are omitted.
        columns = [
            "user_id",
            "transport",
            "distance",
            "electricity",
            "diet",
            "flights",
            "footprint",
            "eco_score",
        ]
        values = [
            user_id,
            transport,
            distance,
            electricity,
            diet,
            flights,
            footprint,
            eco_score,
        ]

        if date is not None:
            columns.append("date")
            values.append(date)
        if trip_id is not None:
            columns.append("trip_id")
            values.append(trip_id)
        if factor_version is not None:
            columns.append("factor_version")
            values.append(factor_version)

        placeholders = ", ".join("?" for _ in columns)
        cursor.execute(
            f"INSERT INTO assessments ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(values),
        )

        conn.commit()
        conn.close()
        invalidate_on_assessment_save()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"Database save error: {e}")
        return False

# -------------------------------------------------------------------------
# Assessment Timestamp Migration
#
# This migration introduces the `created_at` column to the assessments
# table to automatically record when each assessment is created.
#
# The column uses SQLite's `CURRENT_TIMESTAMP` as its default value,
# allowing every newly inserted record to receive an accurate creation
# timestamp without requiring manual handling in application code.
#
# The migration is wrapped in a try/except block to ensure backward
# compatibility with existing databases. If the column already exists,
# SQLite raises an OperationalError, which is safely ignored so the
# application can continue initializing without interruption.
#
# Storing creation timestamps enables future enhancements such as:
#   • Chronological sorting of assessments
#   • Activity history and audit trails
#   • Time-based analytics and reporting
#   • Date range filtering
#   • Exporting records with creation metadata
#
# Existing assessment functionality remains unchanged because SQLite
# automatically populates the timestamp whenever a new record is created.
# -------------------------------------------------------------------------
@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_assessments(user_id=1):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, date,created_at, transport, distance, electricity, diet, flights, footprint, eco_score
            FROM assessments
            WHERE user_id = ?
            ORDER BY created_at  DESC, id DESC
        """, (user_id,))

        data = cursor.fetchall()

        conn.close()
        return data
    except sqlite3.Error as e:
        print(f"Database read error: {e}")
        return []

def save_carbon_budget(user_id, budget_type, budget_limit):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM carbon_budgets WHERE user_id=?",
            (user_id,)
        )

        cursor.execute("""
            INSERT INTO carbon_budgets(user_id,budget_type,budget_limit)
            VALUES(?,?,?)
        """,(user_id,budget_type,budget_limit))

        conn.commit()
        conn.close()

        return True

    except sqlite3.Error as e:
        print(e)
        return False
def get_carbon_budget(user_id):

    try:
        conn=sqlite3.connect(DB_NAME)
        cursor=conn.cursor()

        cursor.execute("""
        SELECT budget_type,budget_limit
        FROM carbon_budgets
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 1
        """,(user_id,))

        row=cursor.fetchone()

        conn.close()

        return row

    except sqlite3.Error:
        return None
def update_carbon_budget(user_id,budget_type,budget_limit):

    try:

        conn=sqlite3.connect(DB_NAME)
        cursor=conn.cursor()

        cursor.execute("""
        UPDATE carbon_budgets
        SET budget_type=?,
            budget_limit=?
        WHERE user_id=?
        """,(budget_type,budget_limit,user_id))

        conn.commit()

        conn.close()

        return True

    except sqlite3.Error:

        return False
@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_assessments_with_factors(user_id=1):
    """
    Assessments including the factor version each was computed under.

    Kept separate from get_assessments() so the existing nine-column tuple
    shape that every caller already unpacks stays untouched.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, date, transport,created_at, distance, electricity, diet, flights,
                   footprint, eco_score, factor_version
            FROM assessments
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
        """, (user_id,))
        return cursor.fetchall()
    except sqlite3.Error as exc:
        logger.error("Unable to read assessments with factor versions: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_all_assessments():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, date, created_at,transport, distance, electricity, diet, flights, footprint, eco_score
            FROM assessments
            ORDER BY date DESC, id DESC
        """)

        data = cursor.fetchall()

        conn.close()
        return data
    except sqlite3.Error as e:
        print(f"Database read error: {e}")
        return []


def undo_last_assessment(user_id=1):
    """
    Undo the user's most recent assessment record.
    Moves record to deleted_assessments table, logs action in activity log,
    and invalidates dependent caches.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Find latest assessment
        cursor.execute(
            """
            SELECT id, date, transport, distance, electricity, diet, flights, footprint, eco_score
            FROM assessments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "No assessment found to undo.", None

        rec_id, date, transport, distance, electricity, diet, flights, footprint, eco_score = row

        # Backup into deleted_assessments
        cursor.execute(
            """
            INSERT INTO deleted_assessments (original_id, user_id, date, transport, distance, electricity, diet, flights, footprint, eco_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rec_id, user_id, date, transport, distance, electricity, diet, flights, footprint, eco_score)
        )

        # Delete from assessments table
        cursor.execute("DELETE FROM assessments WHERE id = ?", (rec_id,))

        # Log activity
        details = f"Undone assessment #{rec_id} ({footprint:.1f} kg CO2, score {eco_score})"
        cursor.execute(
            """
            INSERT INTO assessment_activity_log (user_id, assessment_id, action, details)
            VALUES (?, ?, 'UNDO', ?)
            """,
            (user_id, rec_id, details)
        )

        conn.commit()
        conn.close()

        invalidate_on_assessment_undo()
        record_dict = {
            "id": rec_id,
            "date": date,
            "transport": transport,
            "distance": distance,
            "electricity": electricity,
            "diet": diet,
            "flights": flights,
            "footprint": footprint,
            "eco_score": eco_score,
        }
        return True, f"Successfully undone assessment #{rec_id}.", record_dict
    except sqlite3.Error as e:
        logger.error("Undo assessment error: %s", e)
        return False, f"Database error during undo: {e}", None


def restore_last_deleted_assessment(user_id=1):
    """
    Restore the user's most recently undone assessment.
    Re-inserts record into assessments table and logs action.
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Find latest deleted assessment
        cursor.execute(
            """
            SELECT id, original_id, date, transport, distance, electricity, diet, flights, footprint, eco_score
            FROM deleted_assessments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False, "No deleted assessment available to restore.", None

        del_id, orig_id, date, transport, distance, electricity, diet, flights, footprint, eco_score = row

        # Re-insert into assessments
        cursor.execute(
            """
            INSERT INTO assessments (user_id, date, transport, distance, electricity, diet, flights, footprint, eco_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, date, transport, distance, electricity, diet, flights, footprint, eco_score)
        )
        new_id = cursor.lastrowid

        # Delete from deleted_assessments
        cursor.execute("DELETE FROM deleted_assessments WHERE id = ?", (del_id,))

        # Log activity
        details = f"Restored assessment (formerly #{orig_id}, now #{new_id})"
        cursor.execute(
            """
            INSERT INTO assessment_activity_log (user_id, assessment_id, action, details)
            VALUES (?, ?, 'RESTORE', ?)
            """,
            (user_id, new_id, details)
        )

        conn.commit()
        conn.close()

        invalidate_on_assessment_save()
        return True, f"Successfully restored assessment #{new_id}.", {"id": new_id, "footprint": footprint}
    except sqlite3.Error as e:
        logger.error("Restore assessment error: %s", e)
        return False, f"Database error during restore: {e}", None


def get_last_undone_assessment(user_id=1):
    """Fetch the latest undone assessment for restore preview."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT original_id, date, transport, distance, electricity, diet, flights, footprint, eco_score, deleted_at
            FROM deleted_assessments
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "original_id": row[0],
                "date": row[1],
                "transport": row[2],
                "distance": row[3],
                "electricity": row[4],
                "diet": row[5],
                "flights": row[6],
                "footprint": row[7],
                "eco_score": row[8],
                "deleted_at": row[9],
            }
        return None
    except sqlite3.Error:
        return None


def get_assessment_activity_history(user_id=1):
    """Retrieve chronological activity log for assessment creations, undos, and restores."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, assessment_id, action, details, timestamp
            FROM assessment_activity_log
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "assessment_id": r[1],
                "action": r[2],
                "details": r[3],
                "timestamp": r[4],
            }
            for r in rows
        ]
    except sqlite3.Error:
        return []


def save_assessment_draft(
    user_id,
    transport,
    distance,
    electricity,
    diet,
    flights,
    region,
):
    """Insert or update one unfinished assessment per user."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO assessment_drafts (
                user_id,
                transport,
                distance,
                electricity,
                diet,
                flights,
                region,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                transport = excluded.transport,
                distance = excluded.distance,
                electricity = excluded.electricity,
                diet = excluded.diet,
                flights = excluded.flights,
                region = excluded.region,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                user_id,
                transport,
                distance,
                electricity,
                diet,
                flights,
                region,
            ),
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Database draft save error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def get_diet_history(user_id, limit=7):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date, diet FROM assessments
            WHERE user_id = ?
            ORDER BY date DESC LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except sqlite3.Error as e:
        print(f"get_diet_history error: {e}")
        return []


def get_assessment_draft(user_id):
    """Return the active user's unfinished assessment, if one exists."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                transport,
                distance,
                created_at,
                electricity,
                diet,
                flights,
                region,
                updated_at
            FROM assessment_drafts
            WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "transport": row[0],
            "distance": row[1],
            "electricity": row[2],
            "diet": row[3],
            "flights": row[4],
            "region": row[5],
            "updated_at": row[6],
        }
    except sqlite3.Error as exc:
        logger.error("Database draft read error: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


def delete_assessment_draft(user_id):
    """Delete the active user's unfinished assessment."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM assessment_drafts WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Database draft delete error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def init_energy_db():
    """
    Initialize energy-related tables (appliances, solar_configs).
    
    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        
        # Run migrations to ensure schema is up to date
        migrate()
        
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                name TEXT,
                category TEXT,
                quantity INTEGER,
                power_rating_watts REAL,
                hours_used_per_day REAL,
                standby_draw_watts REAL,
                usage_schedule TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solar_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER DEFAULT 1,
                roof_space_m2 REAL,
                peak_sun_hours REAL,
                utility_rate_per_kwh REAL,
                panel_efficiency REAL,
                installation_cost_per_kw REAL,
                maintenance_cost_per_year REAL,
                annual_rate_increase REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        print(f"Database energy init error: {e}")
        return False


def add_appliance(user_id, name, category, quantity, power_rating, hours_used, standby_draw):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appliances (user_id, name, category, quantity, power_rating_watts, hours_used_per_day, standby_draw_watts)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, category, quantity, power_rating, hours_used, standby_draw))
        conn.commit()
        conn.close()
        invalidate_on_appliance_change()
        return True
    except sqlite3.Error as e:
        print(f"Appliance save error: {e}")
        return False


def delete_appliance(app_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM appliances WHERE id = ?", (app_id,))
        conn.commit()
        conn.close()
        invalidate_on_appliance_change()
        return True
    except sqlite3.Error as e:
        return False


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_appliances(user_id=1):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appliances WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error as e:
        return []


def save_solar_config(user_id, roof_space, peak_sun_hours, utility_rate, panel_efficiency, install_cost, maint_cost, rate_inc):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM solar_configs WHERE user_id = ?", (user_id,))
        
        cursor.execute("""
            INSERT INTO solar_configs (
                user_id, roof_space_m2, peak_sun_hours, utility_rate_per_kwh, panel_efficiency, 
                installation_cost_per_kw, maintenance_cost_per_year, annual_rate_increase
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, roof_space, peak_sun_hours, utility_rate, panel_efficiency, install_cost, maint_cost, rate_inc))
        conn.commit()
        conn.close()
        invalidate_on_solar_config_save()
        return True
    except sqlite3.Error as e:
        return False


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_solar_config(user_id=1):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM solar_configs WHERE user_id = ? LIMIT 1", (user_id,))
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        conn.close()
        if row:
            return dict(zip(columns, row))
        return None
    except sqlite3.Error as e:
        return None


def init_gamification_db():
    """
    Initialize gamification-related tables.
    
    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        
        # Run migrations to ensure schema is up to date
        migrate()
        
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                challenge_id TEXT NOT NULL,
                progress_value REAL DEFAULT 0.0,
                status TEXT DEFAULT 'enrolled',
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                xp_awarded BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS unlocked_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                badge_id TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                xp_awarded BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, badge_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS xp_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                xp_amount INTEGER NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, source_type, source_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_xp_user ON xp_transactions(user_id)")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                card_id TEXT NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, card_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_tree_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                node_id TEXT NOT NULL,
                status TEXT DEFAULT 'Locked',
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, node_id)
            )
        """)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database gamification init error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def enroll_challenge(user_id, challenge_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM user_challenges WHERE user_id=? AND challenge_id=? AND status != 'expired'", (user_id, challenge_id))
        if cursor.fetchone():
            return False
            
        cursor.execute("""
            INSERT INTO user_challenges (user_id, challenge_id, status)
            VALUES (?, ?, 'enrolled')
        """, (user_id, challenge_id))
        conn.commit()
        invalidate_on_challenge_enroll()
        return True
    except sqlite3.Error as e:
        print(f"enroll_challenge error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def update_challenge_progress(user_id, challenge_id, progress_increment=None, set_progress=None):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if progress_increment is not None:
            cursor.execute("""
                UPDATE user_challenges 
                SET progress_value = progress_value + ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND challenge_id = ? AND status = 'enrolled'
            """, (progress_increment, user_id, challenge_id))
        elif set_progress is not None:
             cursor.execute("""
                UPDATE user_challenges 
                SET progress_value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND challenge_id = ? AND status = 'enrolled'
            """, (set_progress, user_id, challenge_id))
            
        conn.commit()
        invalidate_on_challenge_enroll()
        return True
    except sqlite3.Error as e:
        print(f"update_challenge_progress error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def complete_challenge(user_id, challenge_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE user_challenges 
            SET status = 'completed', completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND challenge_id = ? AND status = 'enrolled'
        """, (user_id, challenge_id))
        
        conn.commit()
        invalidate_on_challenge_enroll()
        return True
    except sqlite3.Error as e:
        print(f"complete_challenge error: {e}")
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_user_challenges(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_challenges WHERE user_id = ?", (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error as e:
        return []
    finally:
        if conn:
            conn.close()


def award_xp(user_id, source_type, source_id, xp_amount, description):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO xp_transactions (user_id, source_type, source_id, xp_amount, description)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, source_type, source_id, xp_amount, description))
        
        if source_type == 'challenge':
            cursor.execute("UPDATE user_challenges SET xp_awarded = 1 WHERE user_id = ? AND challenge_id = ?", (user_id, source_id))
            invalidate_on_challenge_enroll()
        elif source_type == 'badge':
            cursor.execute("UPDATE unlocked_badges SET xp_awarded = 1 WHERE user_id = ? AND badge_id = ?", (user_id, source_id))
            invalidate_on_badge_unlock()
            
        conn.commit()
        invalidate_on_xp_award()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"award_xp error: {e}")
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_total_xp(user_id):
    
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(xp_amount) FROM xp_transactions WHERE user_id = ?", (user_id,))
        total = cursor.fetchone()[0]
        return total if total else 0
    except sqlite3.Error:
        return 0
    finally:
        if conn:
            conn.close()


def unlock_badge_in_db(user_id, badge_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO unlocked_badges (user_id, badge_id)
            VALUES (?, ?)
        """, (user_id, badge_id))
        
        conn.commit()
        invalidate_on_badge_unlock()
        invalidate_on_xp_award()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"unlock_badge_in_db error: {e}")
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_unlocked_badges(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM unlocked_badges WHERE user_id = ?", (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error as e:
        return []
    finally:
        if conn:
            conn.close()


def unlock_card_in_db(user_id, card_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO user_cards (user_id, card_id)
            VALUES (?, ?)
        """, (user_id, card_id))

        conn.commit()
        get_unlocked_cards.clear()
        return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.Error as e:
        print(f"unlock_card_in_db error: {e}")
        return False
    finally:
        if conn:
            conn.close()


@st.cache_data
def get_unlocked_cards(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_cards WHERE user_id = ?", (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error as e:
        return []
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_skill_tree_progress(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skill_tree_progress WHERE user_id = ?", (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error as e:
        return []
    finally:
        if conn:
            conn.close()


def update_skill_node_status(user_id, node_id, status):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM skill_tree_progress WHERE user_id=? AND node_id=?", (user_id, node_id))
        if cursor.fetchone():
            if status == 'Completed':
                cursor.execute("""
                    UPDATE skill_tree_progress 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND node_id = ?
                """, (status, user_id, node_id))
            else:
                cursor.execute("""
                    UPDATE skill_tree_progress 
                    SET status = ?
                    WHERE user_id = ? AND node_id = ?
                """, (status, user_id, node_id))
        else:
            if status == 'Completed':
                cursor.execute("""
                    INSERT INTO skill_tree_progress (user_id, node_id, status, completed_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, node_id, status))
            else:
                cursor.execute("""
                    INSERT INTO skill_tree_progress (user_id, node_id, status)
                    VALUES (?, ?, ?)
                """, (user_id, node_id, status))
                
        conn.commit()
        invalidate_on_skill_tree_update()
        return True
    except sqlite3.Error as e:
        print(f"update_skill_node_status error: {e}")
        return False
    finally:
        if conn:
            conn.close()


def init_marketplace_db():
    """
    Initialize marketplace-related tables (journey_profiles, offset_transactions).
    
    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        
        # Run migrations to ensure schema is up to date
        migrate()
        
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journey_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                name TEXT NOT NULL,
                distance_km REAL NOT NULL,
                transport_mode TEXT NOT NULL,
                passenger_count INTEGER DEFAULT 1,
                trips_per_week INTEGER DEFAULT 1,
                is_commute BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS offset_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                project_id TEXT NOT NULL,
                project_name TEXT NOT NULL,
                offset_tonnes REAL NOT NULL,
                cost_per_tonne REAL NOT NULL,
                total_cost REAL NOT NULL,
                transaction_status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        return True
    except Exception as e:
        print(f'Database marketplace init error: {e}')
        return False
    finally:
        if conn:
            conn.close()


def save_journey_profile(user_id, name, distance_km, transport_mode, passenger_count, trips_per_week, is_commute):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO journey_profiles (user_id, name, distance_km, transport_mode, passenger_count, trips_per_week, is_commute)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, distance_km, transport_mode, passenger_count, trips_per_week, is_commute))
        
        conn.commit()
        invalidate_on_journey_save()
        return True
    except Exception as e:
        print(f'save_journey_profile error: {e}')
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_journey_profiles(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM journey_profiles WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def delete_journey_profile(profile_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM journey_profiles WHERE id = ?', (profile_id,))
        conn.commit()
        invalidate_on_journey_save()
        return True
    except Exception:
        return False
    finally:
        if conn:
            conn.close()


def save_offset_transaction(user_id, project_id, project_name, offset_tonnes, cost_per_tonne, total_cost, transaction_status='completed'):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO offset_transactions (user_id, project_id, project_name, offset_tonnes, cost_per_tonne, total_cost, transaction_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, project_id, project_name, offset_tonnes, cost_per_tonne, total_cost, transaction_status))
        
        conn.commit()
        invalidate_on_offset_save()
        return True
    except Exception as e:
        print(f'save_offset_transaction error: {e}')
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_offset_transactions(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM offset_transactions WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()


def delete_offset_transaction(transaction_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM offset_transactions WHERE id = ?', (transaction_id,))
        conn.commit()
        invalidate_on_offset_save()
        return True
    except Exception:
        return False
    finally:
        if conn:
            conn.close()


def clear_offset_transactions(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM offset_transactions WHERE user_id = ?', (user_id,))
        conn.commit()
        invalidate_on_offset_save()
        return True
    except Exception:
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_total_offsets(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(offset_tonnes) FROM offset_transactions WHERE user_id = ? AND transaction_status != "reversed"', (user_id,))
        total = cursor.fetchone()[0]
        return total if total else 0.0
    except Exception:
        return 0.0
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_total_spend(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT SUM(total_cost) FROM offset_transactions WHERE user_id = ? AND transaction_status != "reversed"', (user_id,))
        total = cursor.fetchone()[0]
        return total if total else 0.0
    except Exception:
        return 0.0
    finally:
        if conn:
            conn.close()


def init_water_db():
    """
    Initialize water consumption table.
    
    Returns:
        bool: True if initialization succeeded, False otherwise
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        
        # Run migrations to ensure schema is up to date
        migrate()
        
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS water_consumption (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                shower_mins_per_day REAL,
                laundry_loads_per_week REAL,
                dishwasher_runs_per_week REAL,
                garden_mins_per_week REAL,
                diet TEXT,
                total_liters REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        return True
    except Exception as e:
        print(f'Database water init error: {e}')
        return False
    finally:
        if conn:
            conn.close()


def save_water_assessment(user_id, shower, laundry, dishwasher, garden, diet, total_liters):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO water_consumption (user_id, shower_mins_per_day, laundry_loads_per_week, dishwasher_runs_per_week, garden_mins_per_week, diet, total_liters)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, shower, laundry, dishwasher, garden, diet, total_liters))
        
        conn.commit()
        invalidate_on_water_assessment_save()
        return True
    except Exception as e:
        print(f'save_water_assessment error: {e}')
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_water_assessments(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM water_consumption WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except Exception:
        return []
    finally:
        if conn:
            conn.close()
            conn.close()


def save_dashboard_widget_preferences(user_id, widget_ids):
    """Persist the ordered dashboard widget IDs selected by a user."""
    import json

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboard_widget_preferences (
                user_id INTEGER PRIMARY KEY,
                widgets_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO dashboard_widget_preferences (user_id, widgets_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                widgets_json = excluded.widgets_json,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, json.dumps(list(widget_ids))),
        )
        conn.commit()
        return True
    except (sqlite3.Error, TypeError, ValueError) as exc:
        logger.error("Dashboard preference save error: %s", exc)
        return False
    finally:
        if 'conn' in locals():
            conn.close()


def get_dashboard_widget_preferences(user_id):
    """Return the saved widget IDs, or None when the user has no preference."""
    import json

    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS dashboard_widget_preferences (
                user_id INTEGER PRIMARY KEY,
                widgets_json TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            "SELECT widgets_json FROM dashboard_widget_preferences WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        value = json.loads(row[0])
        return value if isinstance(value, list) else None
    except (sqlite3.Error, json.JSONDecodeError, TypeError) as exc:
        logger.error("Dashboard preference read error: %s", exc)
        return None
    finally:
        if 'conn' in locals():
            conn.close()


def record_environmental_milestone(
    user_id,
    milestone_type,
    title,
    description,
    icon="🌱",
    achieved_at=None,
    metadata=None,
):
    """Persist a milestone once per user and milestone type.

    Returns True only when a new milestone is inserted.
    """
    import json

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO environmental_milestones (
                user_id,
                milestone_type,
                title,
                description,
                icon,
                achieved_at,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?)
            """,
            (
                user_id,
                milestone_type,
                title,
                description,
                icon,
                achieved_at,
                json.dumps(metadata or {}, sort_keys=True),
            ),
        )
        conn.commit()
        return cursor.rowcount == 1
    except sqlite3.Error as exc:
        logger.error("Unable to record environmental milestone: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def get_environmental_milestones(user_id):
    """Return a user's milestones from newest to oldest."""
    import json

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                milestone_type,
                title,
                description,
                icon,
                achieved_at,
                metadata_json
            FROM environmental_milestones
            WHERE user_id = ?
            ORDER BY datetime(achieved_at) DESC, id DESC
            """,
            (user_id,),
        )
        milestones = []
        for row in cursor.fetchall():
            try:
                metadata = json.loads(row[6] or "{}")
            except (TypeError, json.JSONDecodeError):
                metadata = {}
            milestones.append(
                {
                    "id": row[0],
                    "milestone_type": row[1],
                    "title": row[2],
                    "description": row[3],
                    "icon": row[4],
                    "achieved_at": row[5],
                    "metadata": metadata,
                }
            )
        return milestones
    except sqlite3.Error as exc:
        logger.error("Unable to load environmental milestones: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def init_freeze_tokens_db():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        migrate()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS freeze_token_balances (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                total_earned INTEGER NOT NULL DEFAULT 0,
                total_used INTEGER NOT NULL DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS freeze_token_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS streak_freezes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                frozen_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, frozen_date)
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_streak_freezes_user_date
            ON streak_freezes(user_id, frozen_date DESC)
        """)
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error("Freeze tokens DB init error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_freeze_token_balance(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM freeze_token_balances WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error:
        return 0
    finally:
        if conn:
            conn.close()


def ensure_freeze_token_row(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO freeze_token_balances (user_id, balance, total_earned, total_used)
            VALUES (?, 0, 0, 0)
        """, (user_id,))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        if conn:
            conn.close()


def award_freeze_tokens(user_id, amount, reason):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        ensure_freeze_token_row(user_id)
        cursor.execute("""
            UPDATE freeze_token_balances
            SET balance = balance + ?, total_earned = total_earned + ?
            WHERE user_id = ?
        """, (amount, amount, user_id))
        cursor.execute("""
            INSERT INTO freeze_token_transactions (user_id, amount, reason)
            VALUES (?, ?, ?)
        """, (user_id, amount, reason))
        conn.commit()
        invalidate_on_freeze_token_change()
        return True
    except sqlite3.Error as e:
        logger.error("award_freeze_tokens error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def redeem_freeze_token(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM freeze_token_balances WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row or row[0] < 1:
            return False
        cursor.execute("""
            UPDATE freeze_token_balances
            SET balance = balance - 1, total_used = total_used + 1
            WHERE user_id = ? AND balance >= 1
        """, (user_id,))
        cursor.execute("""
            INSERT INTO freeze_token_transactions (user_id, amount, reason)
            VALUES (?, ?, ?)
        """, (user_id, -1, 'redeem'))
        conn.commit()
        invalidate_on_freeze_token_change()
        return True
    except sqlite3.Error as e:
        logger.error("redeem_freeze_token error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def use_streak_freeze(user_id, frozen_date):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO streak_freezes (user_id, frozen_date)
            VALUES (?, ?)
        """, (user_id, frozen_date))
        conn.commit()
        invalidate_on_freeze_token_change()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error("use_streak_freeze error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_streak_freeze_dates(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT frozen_date FROM streak_freezes
            WHERE user_id = ?
            ORDER BY frozen_date DESC
        """, (user_id,))
        return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error:
        return []
    finally:
        if conn:
            conn.close()


def get_freeze_token_transactions(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, amount, reason, created_at
            FROM freeze_token_transactions
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
        """, (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error:
        return []
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_total_freeze_tokens_earned(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT total_earned FROM freeze_token_balances WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    except sqlite3.Error:
        return 0
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Reduction goals
# ---------------------------------------------------------------------------

def init_goals_db():
    """
    Create the reduction_goals table.

    Kept as its own initializer to match the existing per-feature pattern
    (init_energy_db, init_gamification_db, init_marketplace_db, init_water_db).
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reduction_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                baseline_kg REAL NOT NULL,
                target_kg REAL NOT NULL,
                start_date TEXT NOT NULL,
                target_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # A user may only have one active goal at a time; history rows are
        # archived or completed and are excluded from the index.
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_reduction_goals_active
            ON reduction_goals(user_id)
            WHERE status = 'active'
        """)
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Reduction goals init error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def _goal_row_to_dict(row):
    """Map a reduction_goals row onto the dict shape goals.py expects."""
    if not row:
        return None
    return {
        "id": row[0],
        "user_id": row[1],
        "baseline_kg": row[2],
        "target_kg": row[3],
        "start_date": row[4],
        "target_date": row[5],
        "status": row[6],
        "created_at": row[7],
    }


def save_reduction_goal(user_id, baseline_kg, target_kg, start_date, target_date):
    """
    Persist a new goal, archiving any goal the user already had active.

    Returns the new goal id, or None if the write failed.
    """
    init_goals_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Only one active goal per user, so retire the previous one first.
        cursor.execute(
            "UPDATE reduction_goals SET status = 'archived' "
            "WHERE user_id = ? AND status = 'active'",
            (user_id,),
        )
        cursor.execute("""
            INSERT INTO reduction_goals (
                user_id, baseline_kg, target_kg, start_date, target_date, status
            )
            VALUES (?, ?, ?, ?, ?, 'active')
        """, (
            user_id,
            float(baseline_kg),
            float(target_kg),
            str(start_date),
            str(target_date),
        ))
        goal_id = cursor.lastrowid
        conn.commit()
        invalidate_on_reduction_goal_change()
        return goal_id
    except sqlite3.Error as exc:
        logger.error("Unable to save reduction goal: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_active_goal(user_id):
    """Return the user's current active goal, or None."""
    init_goals_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, baseline_kg, target_kg, start_date,
                   target_date, status, created_at
            FROM reduction_goals
            WHERE user_id = ? AND status = 'active'
            ORDER BY id DESC
            LIMIT 1
        """, (user_id,))
        return _goal_row_to_dict(cursor.fetchone())
    except sqlite3.Error as exc:
        logger.error("Unable to load active goal: %s", exc)
        return None
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_goal_history(user_id):
    """Return every goal the user has ever set, newest first."""
    init_goals_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, baseline_kg, target_kg, start_date,
                   target_date, status, created_at
            FROM reduction_goals
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,))
        return [_goal_row_to_dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as exc:
        logger.error("Unable to load goal history: %s", exc)
        return []
    finally:
        if conn:
            conn.close()


def update_goal_status(goal_id, status):
    """Move a goal to a new lifecycle state (archived / completed / active)."""
    if status not in ("active", "archived", "completed"):
        logger.error("Refusing to set unknown goal status: %s", status)
        return False

    init_goals_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE reduction_goals SET status = ? WHERE id = ?",
            (status, goal_id),
        )
        changed = cursor.rowcount > 0
        conn.commit()
        invalidate_on_reduction_goal_change()
        return changed
    except sqlite3.Error as exc:
        logger.error("Unable to update goal status: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def archive_goal(goal_id):
    """Retire a goal without marking it as met."""
    return update_goal_status(goal_id, "archived")


def complete_goal(goal_id):
    """Mark a goal as successfully achieved."""
    return update_goal_status(goal_id, "completed")


def delete_reduction_goal(goal_id):
    """Permanently remove a goal row."""
    init_goals_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reduction_goals WHERE id = ?", (goal_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        invalidate_on_reduction_goal_change()
        return deleted
    except sqlite3.Error as exc:
        logger.error("Unable to delete reduction goal: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def init_waste_db():
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waste_assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                food_scraps REAL DEFAULT 0,
                plastic_packaging REAL DEFAULT 0,
                paper_cardboard REAL DEFAULT 0,
                glass REAL DEFAULT 0,
                metal_cans REAL DEFAULT 0,
                e_waste REAL DEFAULT 0,
                textiles REAL DEFAULT 0,
                mixed_waste REAL DEFAULT 0,
                total_weekly_kg REAL DEFAULT 0,
                annual_co2 REAL DEFAULT 0,
                recyclable_pct REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error("Waste DB init error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def save_waste_assessment(user_id, waste_data, total_weekly_kg, annual_co2, recyclable_pct):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO waste_assessments (
                user_id, food_scraps, plastic_packaging, paper_cardboard,
                glass, metal_cans, e_waste, textiles, mixed_waste,
                total_weekly_kg, annual_co2, recyclable_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            waste_data.get("Food Scraps", 0),
            waste_data.get("Plastic Packaging", 0),
            waste_data.get("Paper & Cardboard", 0),
            waste_data.get("Glass", 0),
            waste_data.get("Metal (Cans)", 0),
            waste_data.get("Electronics (E-Waste)", 0),
            waste_data.get("Textiles", 0),
            waste_data.get("Other (Mixed Waste)", 0),
            total_weekly_kg, annual_co2, recyclable_pct,
        ))
        conn.commit()
        get_waste_assessments.clear()
        return True
    except sqlite3.Error as e:
        logger.error("Waste assessment save error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_waste_assessments(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM waste_assessments WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error as e:
        logger.error("Waste assessment read error: %s", e)
        return []
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Unit and currency preferences
# ---------------------------------------------------------------------------

def init_unit_preferences():
    """
    Add the unit_system and currency columns to the users table.

    Uses the same defensive ALTER-and-swallow pattern already used for
    anonymous_leaderboard in init_db(), so it is safe to call repeatedly and on
    a database that already has the columns.
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        for statement in (
            "ALTER TABLE users ADD COLUMN unit_system TEXT DEFAULT 'metric'",
            "ALTER TABLE users ADD COLUMN currency TEXT DEFAULT 'USD'",
        ):
            try:
                cursor.execute(statement)
            except sqlite3.OperationalError:
                pass
        conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.error("Unit preference init error: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def save_unit_preference(user_id, unit_system, currency):
    """
    Persist a user's display preference.

    The value is normalised through units.make_preference() first, so an
    unknown system or currency is stored as the default rather than as
    something no page can render.
    """
    from units import make_preference

    preference = make_preference(unit_system, currency)
    init_unit_preferences()

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET unit_system = ?, currency = ? WHERE id = ?",
            (preference["system"], preference["currency"], user_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    except sqlite3.Error as exc:
        logger.error("Unable to save unit preference: %s", exc)
        return False
    finally:
        if conn:
            conn.close()


def get_unit_preference(user_id):
    """
    Return a user's display preference, defaulting to metric + USD.

    Never raises and never returns None: every page reads this on load, so a
    missing user, a missing column or a corrupted value must all degrade to the
    default rather than break the page.
    """
    from units import make_preference

    init_unit_preferences()

    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT unit_system, currency FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return make_preference()
        return make_preference(row[0], row[1])
    except sqlite3.Error as exc:
        logger.error("Unable to read unit preference: %s", exc)
        return make_preference()
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Community Polls
# ---------------------------------------------------------------------------

def init_community_polls_db():
    """Initialize database tables for community polls."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_polls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                category TEXT DEFAULT 'General',
                status TEXT DEFAULT 'active',
                created_by TEXT DEFAULT 'Community',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_options (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                option_text TEXT NOT NULL,
                vote_count INTEGER DEFAULT 0,
                FOREIGN KEY (poll_id) REFERENCES community_polls (id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS poll_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id INTEGER NOT NULL,
                user_identifier TEXT NOT NULL,
                option_id INTEGER NOT NULL,
                voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(poll_id, user_identifier),
                FOREIGN KEY (poll_id) REFERENCES community_polls (id) ON DELETE CASCADE,
                FOREIGN KEY (option_id) REFERENCES poll_options (id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error("Community polls DB init error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def seed_community_polls():
    """Seed sample sustainability community polls if table is empty."""
    init_community_polls_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM community_polls")
        if cursor.fetchone()[0] > 0:
            return

        sample_polls = [
            (
                "What is your primary action for reducing personal carbon footprint in 2026?",
                "Lifestyle",
                "active",
                "EcoBuddy Team",
                [
                    ("Switching to plant-based diet", 45),
                    ("Using public transport & biking", 38),
                    ("Installing solar panels / renewable energy", 29),
                    ("Reducing single-use plastic & waste", 52),
                ],
            ),
            (
                "Which sector needs the most aggressive climate policy enforcement?",
                "Policy",
                "active",
                "EcoBuddy Team",
                [
                    ("Energy & Electricity Generation", 60),
                    ("Industrial Manufacturing & Heavy Industry", 42),
                    ("Transportation & Logistics", 31),
                    ("Agriculture & Deforestation", 25),
                ],
            ),
            (
                "What was the most impactful eco-habit you adopted last year?",
                "Community",
                "archived",
                "Community",
                [
                    ("Composting organic waste", 85),
                    ("Eliminating fast fashion purchases", 64),
                    ("Switching to EV / E-bike", 40),
                    ("Smart home energy management", 53),
                ],
            ),
        ]

        for question, category, status, created_by, options in sample_polls:
            cursor.execute("""
                INSERT INTO community_polls (question, category, status, created_by)
                VALUES (?, ?, ?, ?)
            """, (question, category, status, created_by))
            poll_id = cursor.lastrowid
            for opt_text, count in options:
                cursor.execute("""
                    INSERT INTO poll_options (poll_id, option_text, vote_count)
                    VALUES (?, ?, ?)
                """, (poll_id, opt_text, count))

        conn.commit()
    except sqlite3.Error as e:
        logger.error("Failed to seed community polls: %s", e)
    finally:
        if conn:
            conn.close()


def create_poll(question: str, options: list[str], category: str = "General", created_by: str = "Community") -> int | None:
    """Create a new poll with given options."""
    if not question.strip() or len(options) < 2:
        return None
    init_community_polls_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO community_polls (question, category, status, created_by)
            VALUES (?, ?, 'active', ?)
        """, (question.strip(), category, created_by))
        poll_id = cursor.lastrowid
        for opt in options:
            if opt.strip():
                cursor.execute("""
                    INSERT INTO poll_options (poll_id, option_text, vote_count)
                    VALUES (?, ?, 0)
                """, (poll_id, opt.strip()))
        conn.commit()
        get_active_polls.clear()
        get_archived_polls.clear()
        return poll_id
    except sqlite3.Error as e:
        logger.error("Failed to create poll: %s", e)
        return None
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_active_polls() -> list[dict]:
    """Retrieve all active community polls with their options and vote counts."""
    seed_community_polls()
    return _fetch_polls_by_status("active")


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_archived_polls() -> list[dict]:
    """Retrieve all archived community polls with final results."""
    seed_community_polls()
    return _fetch_polls_by_status("archived")


def _fetch_polls_by_status(status: str) -> list[dict]:
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, question, category, status, created_by, created_at
            FROM community_polls
            WHERE status = ?
            ORDER BY created_at DESC
        """, (status,))
        poll_rows = cursor.fetchall()
        polls = []
        for p in poll_rows:
            poll_id = p[0]
            cursor.execute("""
                SELECT id, option_text, vote_count
                FROM poll_options
                WHERE poll_id = ?
                ORDER BY id ASC
            """, (poll_id,))
            option_rows = cursor.fetchall()
            options = [
                {"id": opt[0], "option_text": opt[1], "vote_count": opt[2]}
                for opt in option_rows
            ]
            total_votes = sum(opt["vote_count"] for opt in options)
            polls.append({
                "id": poll_id,
                "question": p[1],
                "category": p[2],
                "status": p[3],
                "created_by": p[4],
                "created_at": p[5],
                "options": options,
                "total_votes": total_votes,
            })
        return polls
    except sqlite3.Error as e:
        logger.error("Failed to fetch polls: %s", e)
        return []
    finally:
        if conn:
            conn.close()


def has_user_voted(poll_id: int, user_identifier: str) -> bool:
    """Check if a specific user/identifier has already voted on a poll."""
    init_community_polls_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM poll_votes WHERE poll_id = ? AND user_identifier = ?
        """, (poll_id, str(user_identifier)))
        return cursor.fetchone() is not None
    except sqlite3.Error as e:
        logger.error("Error checking poll vote: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def vote_poll(poll_id: int, option_id: int, user_identifier: str) -> bool:
    """Record an anonymous vote for an option in a poll."""
    init_community_polls_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        # Check if already voted
        cursor.execute("""
            SELECT 1 FROM poll_votes WHERE poll_id = ? AND user_identifier = ?
        """, (poll_id, str(user_identifier)))
        if cursor.fetchone():
            return False

        cursor.execute("""
            INSERT INTO poll_votes (poll_id, user_identifier, option_id)
            VALUES (?, ?, ?)
        """, (poll_id, str(user_identifier), option_id))

        cursor.execute("""
            UPDATE poll_options SET vote_count = vote_count + 1 WHERE id = ? AND poll_id = ?
        """, (option_id, poll_id))

        conn.commit()
        get_active_polls.clear()
        get_archived_polls.clear()
        return True
    except sqlite3.Error as e:
        logger.error("Failed to record vote: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def archive_poll(poll_id: int) -> bool:
    """Archive a poll by ID."""
    init_community_polls_db()
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE community_polls SET status = 'archived' WHERE id = ?", (poll_id,))
        changed = cursor.rowcount > 0
        conn.commit()
        get_active_polls.clear()
        get_archived_polls.clear()
        return changed
    except sqlite3.Error as e:
        logger.error("Failed to archive poll: %s", e)
        return False
    finally:
        if conn:
            conn.close()

def create_time_capsule(user_id, title, promise_text, category, unlock_date):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO time_capsules (user_id, title, promise_text, category, unlock_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, promise_text, category, unlock_date))
        conn.commit()
        invalidate_on_time_capsule_change()
        return True
    except sqlite3.Error as e:
        logger.error("create_time_capsule error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


@cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
def get_time_capsules(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, title, promise_text, category,
                   unlock_date, is_unlocked, unlocked_at, progress_notes,
                   created_at, updated_at
            FROM time_capsules
            WHERE user_id = ?
            ORDER BY unlock_date ASC, created_at DESC
        """, (user_id,))
        columns = [column[0] for column in cursor.description]
        data = cursor.fetchall()
        return [dict(zip(columns, row)) for row in data]
    except sqlite3.Error:
        return []
    finally:
        if conn:
            conn.close()


def update_time_capsule_unlock(capsule_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE time_capsules
            SET is_unlocked = 1, unlocked_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND is_unlocked = 0
        """, (capsule_id,))
        conn.commit()
        invalidate_on_time_capsule_change()
        return cursor.rowcount > 0
    except sqlite3.Error as e:
        logger.error("update_time_capsule_unlock error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def update_time_capsule_progress(capsule_id, progress_notes):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE time_capsules
            SET progress_notes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (progress_notes, capsule_id))
        conn.commit()
        invalidate_on_time_capsule_change()
        return True
    except sqlite3.Error as e:
        logger.error("update_time_capsule_progress error: %s", e)
        return False
    finally:
        if conn:
            conn.close()


def delete_time_capsule(capsule_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM time_capsules WHERE id = ?", (capsule_id,))
        conn.commit()
        invalidate_on_time_capsule_change()
        return True
    except sqlite3.Error as e:
        logger.error("delete_time_capsule error: %s", e)
        return False
    finally:
        if conn:
            conn.close()
def save_weekly_challenge(user_id, title, difficulty, xp, category):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO weekly_challenges
        (user_id,title,difficulty,xp,category)
        VALUES(?,?,?,?,?)
    """,(user_id,title,difficulty,xp,category))

    conn.commit()
    conn.close()

    return True
def get_weekly_challenges(user_id):

    conn=sqlite3.connect(DB_NAME)
    cursor=conn.cursor()

    cursor.execute("""
    SELECT *
    FROM weekly_challenges
    WHERE user_id=?
    ORDER BY created_at DESC
    """,(user_id,))

    data=cursor.fetchall()

    conn.close()

    return data
def complete_weekly_challenge(challenge_id):

    conn=sqlite3.connect(DB_NAME)
    cursor=conn.cursor()

    cursor.execute("""
    UPDATE weekly_challenges
    SET status='Completed'
    WHERE id=?
    """,(challenge_id,))

    conn.commit()

    conn.close()

    return True
if st.button("Generate Weekly Challenges"):

    challenges = generate_weekly_challenges(
        footprint,
        transport,
        electricity,
        diet,
        flights
    )

    for challenge in challenges:

        save_weekly_challenge(
            user_id,
            challenge["title"],
            challenge["difficulty"],
            challenge["xp"],
            challenge["category"]
        )

    st.success("Weekly challenges generated!")
challenges = get_weekly_challenges(user_id)

for challenge in challenges:

    st.subheader(challenge[2])

    st.write(f"Difficulty : {challenge[3]}")

    st.write(f"XP : {challenge[4]}")

    st.write(f"Category : {challenge[5]}")

    st.write(f"Status : {challenge[6]}")
if st.button(
    f"Complete {challenge[0]}"
):

    complete_weekly_challenge(
        challenge[0]
    )

    award_xp(
        user_id,
        "challenge",
        challenge[0],
        challenge[4],
        challenge[2]
    )

    st.success("Challenge Completed!")
from datetime import datetime, timedelta

def weekly_challenges_exist(user_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    last_week = datetime.now() - timedelta(days=7)

    cursor.execute("""
        SELECT COUNT(*)
        FROM weekly_challenges
        WHERE user_id = ?
        AND created_at >= ?
    """, (user_id, last_week))

    count = cursor.fetchone()[0]

    conn.close()

    return count > 0
if not weekly_challenges_exist(user_id):

    challenges = generate_weekly_challenges(
        footprint,
        transport,
        electricity,
        diet,
        flights
    )

    for challenge in challenges:

        save_weekly_challenge(
            user_id,
            challenge["title"],
            challenge["difficulty"],
            challenge["xp"],
            challenge["category"]
        )

else:

    st.info("Weekly challenges already generated.")
completed = sum(
    1 for c in challenges
    if c[6] == "Completed"
)

total = len(challenges)

st.metric(
    "Weekly Progress",
    f"{completed}/{total}"
)

if total > 0:
    st.progress(completed / total)

xp = sum(
    c[4]
    for c in challenges
    if c[6] == "Completed"
)

st.metric(
    "XP Earned",
    xp
)
def get_completed_challenges(user_id):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT title,difficulty,created_at
        FROM weekly_challenges
        WHERE user_id=?
        AND status='Completed'
        ORDER BY created_at DESC
    """,(user_id,))

    data = cursor.fetchall()

    conn.close()

    return data
history = get_completed_challenges(user_id)

st.subheader("Challenge History")

for row in history:

    st.write(
        f"✅ {row[0]} ({row[1]}) - {row[2]}"
    )
completed = len(history)

if completed == 5:

    unlock_badge_in_db(
        user_id,
        "eco_beginner"
    )

elif completed == 15:

    unlock_badge_in_db(
        user_id,
        "eco_master"
    )
st.subheader("Recommended Next Step")

highest = max(
    challenges,
    key=lambda x: x["xp"]
)

st.success(
    f"Focus on: {highest['title']}"
)