import sqlite3

def migrate(conn: sqlite3.Connection) -> None:
    """Add virtual_city_state table."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS virtual_city_state (
            user_id INTEGER PRIMARY KEY,
            carbon_saved_kg REAL DEFAULT 0,
            unlocked_assets TEXT DEFAULT '[]',
            layout_state TEXT DEFAULT '{}',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
