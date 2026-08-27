import sqlite3

def migrate(conn: sqlite3.Connection) -> None:
    """Add eco tables and virtual_city_state table."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eco_ledger_accounts (
            user_id TEXT PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eco_ledger_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id TEXT,
            receiver_id TEXT,
            amount REAL,
            timestamp REAL,
            previous_hash TEXT,
            hash TEXT,
            proof_data TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eco_order_book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            order_type TEXT,
            amount REAL,
            price REAL,
            status TEXT DEFAULT 'OPEN',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eco_community_funds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT,
            target_amount REAL,
            current_amount REAL DEFAULT 0.0,
            description TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
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
