"""Migration v8: add time capsule feature."""

def migrate(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS time_capsules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            promise_text TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            unlock_date TEXT NOT NULL,
            is_unlocked INTEGER DEFAULT 0,
            unlocked_at TIMESTAMP,
            progress_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_time_capsules_user
        ON time_capsules(user_id, unlock_date DESC)
    """)
    conn.commit()
