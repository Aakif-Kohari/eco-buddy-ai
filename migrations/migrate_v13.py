import logging
import sqlite3

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection) -> None:
    """
    Migration v13: Green Canopy & UHI Simulator
    Creates tables for neighborhood_canopy_baselines and neighborhood_canopy_targets.
    """
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS neighborhood_canopy_baselines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT UNIQUE NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                green_canopy_percentage REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS neighborhood_canopy_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                baseline_id INTEGER NOT NULL,
                added_trees INTEGER NOT NULL,
                carbon_drawdown_10y REAL,
                carbon_drawdown_20y REAL,
                carbon_drawdown_50y REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (baseline_id) REFERENCES neighborhood_canopy_baselines (id)
            )
        ''')

        conn.commit()
    except sqlite3.Error as exc:
        logger.error(f"Migration v13 failed: {exc}")
        raise
