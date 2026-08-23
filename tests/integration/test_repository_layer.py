import sqlite3
import pytest
from typing import List, Dict, Any, Tuple, Optional

# --- Simulated Database Repository Layer Under Test ---
class CarbonLogRepository:
    """Data-access engine encapsulating raw SQL execution patterns and filters."""
    def __init__(self, db_conn: sqlite3.Connection):
        self.conn = db_conn

    def create_log(self, user_id: str, category: str, co2_emissions_kg: float) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO carbon_logs (user_id, category, co2_emissions_kg) 
               VALUES (?, ?, ?);""",
            (user_id, category, co2_emissions_kg)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_logs_paginated(
        self, 
        user_id: str, 
        category: Optional[str] = None, 
        limit: int = 10, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        cursor = self.conn.cursor()
        query = "SELECT id, user_id, category, co2_emissions_kg FROM carbon_logs WHERE user_id = ?"
        params = [user_id]

        # Multi-filter condition handling
        if category:
            query += " AND category = ?"
            params.append(category)

        # Sorting and pagination boundaries parameters
        query += " ORDER BY co2_emissions_kg DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [
            {"id": r[0], "user_id": r[1], "category": r[2], "co2_emissions_kg": r[3]} 
            for r in cursor.fetchall()
        ]

    def update_category_emissions(self, log_id: int, new_emissions: float) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE carbon_logs SET co2_emissions_kg = ? WHERE id = ?;",
            (new_emissions, log_id)
        )
        self.conn.commit()
        return cursor.rowcount

    def delete_log(self, log_id: int) -> int:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM carbon_logs WHERE id = ?;", (log_id,))
        self.conn.commit()
        return cursor.rowcount

# --- Pytest In-Memory Database Architecture Setup ---

@pytest.fixture(scope="function")
def test_db_conn():
    """Provides a fresh, isolated in-memory SQLite database instance per test case."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE carbon_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            category TEXT NOT NULL,
            co2_emissions_kg REAL NOT NULL
        );
    """)
    conn.commit()
    yield conn
    conn.close()

# --- Repository Integration Tests Suite ---

def test_record_creation_and_retrieval(test_db_conn):
    """Scenario 1: Verify smooth record insertion and targeted primary index lookup data mapping."""
    repo = CarbonLogRepository(test_db_conn)
    log_id = repo.create_log("user_101", "transportation", 24.5)
    
    logs = repo.get_logs_paginated("user_101")
    assert len(logs) == 1
    assert logs[0]["id"] == log_id
    assert logs[0]["category"] == "transportation"
    assert logs[0]["co2_emissions_kg"] == 24.5


def test_query_with_multiple_filters_and_sorting(test_db_conn):
    """Scenario 2: Query database with multi-field filters while checking sorted orders."""
    repo = CarbonLogRepository(test_db_conn)
    repo.create_log("user_abc", "diet", 4.2)
    repo.create_log("user_abc", "transportation", 15.0)
    repo.create_log("user_abc", "transportation", 85.5)  # Highest value, should sort to index 0

    # Extract logs matching user AND category filters
    results = repo.get_logs_paginated("user_abc", category="transportation")
    
    assert len(results) == 2
    # Verify sorting constraint: DESC order by co2_emissions_kg
    assert results[0]["co2_emissions_kg"] == 85.5
    assert results[1]["co2_emissions_kg"] == 15.0


def test_handle_empty_query_result_sets(test_db_conn):
    """Scenario 3: Verify database queries handle non-existent user criteria gracefully."""
    repo = CarbonLogRepository(test_db_conn)
    results = repo.get_logs_paginated("non_existent_user_id")
    assert results == []  # Should return a clean empty list profile structure


def test_pagination_boundaries_and_offsets(test_db_conn):
    """Scenario 4: Verify offset sliding steps window calculations."""
    repo = CarbonLogRepository(test_db_conn)
    for i in range(5):
        repo.create_log("user_paginated", "energy", float(10 * i))

    # Page 1: Limit 2 records
    page_1 = repo.get_logs_paginated("user_paginated", limit=2, offset=0)
    assert len(page_1) == 2

    # Page 2: Offset past the first two records to extract downstream content items
    page_2 = repo.get_logs_paginated("user_paginated", limit=2, offset=2)
    assert len(page_2) == 2
    assert page_2[0] != page_1[0]  # Verify pagination boundaries split values perfectly


def test_updates_affect_only_matching_records(test_db_conn):
    """Scenario 5: Confirm column updates stay tightly isolated to targeted row indexes."""
    repo = CarbonLogRepository(test_db_conn)
    log_id_target = repo.create_log("user_x", "energy", 12.0)
    log_id_control = repo.create_log("user_x", "energy", 40.0)

    rows_updated = repo.update_category_emissions(log_id_target, new_emissions=99.9)
    
    assert rows_updated == 1
    
    # Assert data changed on the targeted record row item
    cursor = test_db_conn.cursor()
    cursor.execute("SELECT co2_emissions_kg FROM carbon_logs WHERE id = ?;", (log_id_target,))
    assert cursor.fetchone()[0] == 99.9

    # Assert control target row parameter was preserved completely unchanged
    cursor.execute("SELECT co2_emissions_kg FROM carbon_logs WHERE id = ?;", (log_id_control,))
    assert cursor.fetchone()[0] == 40.0


def test_deletion_behavior_and_isolation(test_db_conn):
    """Scenario 6: Confirm complete row drop-outs on targeted entity deletion."""
    repo = CarbonLogRepository(test_db_conn)
    log_id = repo.create_log("user_y", "diet", 5.0)

    deleted_count = repo.delete_log(log_id)
    assert deleted_count == 1
    assert repo.get_logs_paginated("user_y") == []


def test_simulate_database_level_failures(test_db_conn):
    """Scenario 7: Force database catalog locking exceptions to audit system failure handling."""
    repo = CarbonLogRepository(test_db_conn)
    
    # Intentionally drop the table context to force an extraction crash
    cursor = test_db_conn.cursor()
    cursor.execute("DROP TABLE carbon_logs;")
    test_db_conn.commit()

    with pytest.raises(sqlite3.OperationalError):
        repo.get_logs_paginated("user_any")
