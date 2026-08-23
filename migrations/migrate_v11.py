import sqlite3

def migrate(conn: sqlite3.Connection) -> None:
    """Apply schema changes for Eco Buddies feature (v11)."""
    cursor = conn.cursor()
    
    # Buddy Requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buddy_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)
    
    # Buddy Pairs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buddy_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            synergy_score REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1_id) REFERENCES users(id),
            FOREIGN KEY (user2_id) REFERENCES users(id)
        )
    """)
    
    # Buddy Nudges table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buddy_nudges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    """)
    
    conn.commit()
