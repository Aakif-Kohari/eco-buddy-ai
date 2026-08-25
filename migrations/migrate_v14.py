import sqlite3
import logging

logger = logging.getLogger(__name__)

def migrate(conn: sqlite3.Connection):
    """Create the civic_actions table for tracking user advocacy."""
    logger.info("Applying migration v14: Creating civic_actions table")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS civic_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bill_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT '2023-01-01 00:00:00',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
