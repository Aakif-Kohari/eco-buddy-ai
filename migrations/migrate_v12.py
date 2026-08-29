import sqlite3

def migrate(conn: sqlite3.Connection) -> None:
    """
    Migration v12: Community Pledge Board
    Creates tables for eco_pledges, pledge_checkins, and pledge_supporters.
    """
    cursor = conn.cursor()

    # Create eco_pledges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eco_pledges (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            template_id TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            target_metric TEXT,
            target_value REAL,
            current_value REAL DEFAULT 0,
            deadline TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Create pledge_checkins table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pledge_checkins (
            id TEXT PRIMARY KEY,
            pledge_id TEXT NOT NULL,
            assessment_id TEXT,
            value_contributed REAL NOT NULL,
            checked_in_at TEXT NOT NULL,
            FOREIGN KEY (pledge_id) REFERENCES eco_pledges (id)
        )
    ''')

    # Create pledge_supporters table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pledge_supporters (
            id TEXT PRIMARY KEY,
            pledge_id TEXT NOT NULL,
            supporter_id TEXT NOT NULL,
            supported_at TEXT NOT NULL,
            FOREIGN KEY (pledge_id) REFERENCES eco_pledges (id),
            FOREIGN KEY (supporter_id) REFERENCES users (id),
            UNIQUE(pledge_id, supporter_id)
        )
    ''')

    conn.commit()
import logging

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection) -> None:
    """
    Migration to add the monthly_reports table for the Monthly Report Engine.
    """
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monthly_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                month_year TEXT,
                report_data TEXT,
                pdf_path TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except sqlite3.Error as exc:
        logger.error(f"Migration v12 failed: {exc}")
        raise
