import sqlite3
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
        logger.error(f"Migration v11 failed: {exc}")
        raise
