import pytest
import sqlite3
from typing import List, Dict, Any, Optional

# --- Simulated Production Query Dispatcher Engine ---
class QueryEngine:
    @staticmethod
    def search_records(
        db_conn: sqlite3.Connection,
        page: int = 1,
        page_size: int = 10,
        categories: Optional[List[str]] = None,
        min_impact: Optional[float] = None,
        sort_by: str = "id",  # Allowed: 'id', 'impact'
        sort_dir: str = "asc" # Allowed: 'asc', 'desc'
    ) -> Dict[str, Any]:
        """Processes advanced pagination matrix offsets and multi-filter criteria."""
        # 1. Enforce strict configuration constraints and values safety guards
        if page < 1 or page_size < 1:
            raise ValueError("Page index parameters must be positive integers.")
        
        # Enforce maximum page size limit budget
        MAX_PAGE_SIZE = 100
        effective_size = min(page_size, MAX_PAGE_SIZE)
        
        cursor = db_conn.cursor()
        base_query = "SELECT id, category, impact FROM logs WHERE 1=1"
        params = []

        # 2. Ingest Multiple Simultaneous Filters
        if categories:
            placeholders = ",".join(["?"] * len(categories))
            base_query += f" AND category IN ({placeholders})"
            params.extend(categories)
            
        if min_impact is not None:
            base_query += " AND impact >= ?"
            params.append(min_impact)

        # 3. Calculate Global Row Scale for Metadata Checkpoints
        count_query = f"SELECT COUNT(*) FROM ({base_query})"
        cursor.execute(count_query, params)
        total_records = cursor.fetchone()[0]

        # 4. Inject Dynamic Sorting Columns and Directives
        allowed_sort_columns = {"id": "id", "impact": "impact"}
        sort_col = allowed_sort_columns.get(sort_by, "id")
        direction = "DESC" if sort_dir.lower() == "desc" else "ASC"
        base_query += f" ORDER BY {sort_col} {direction}"

        # 5. Calculate Window Offsets Boundaries
        offset = (page - 1) * effective_size
        base_query += " LIMIT ? OFFSET ?"
        params.extend([effective_size, offset])

        # 6. Execute Matrix Extraction
        cursor.execute(base_query, params)
        records = [
            {"id": row[0], "category": row[1], "impact": row[2]} 
            for row in cursor.fetchall()
        ]

        return {
            "data": records,
            "meta": {
                "page": page,
                "page_size": effective_size,
                "total_records": total_records,
                "total_pages": (total_records + effective_size - 1) // effective_size
            }
        }

# --- Pytest In-Memory Seeding Fixture ---

@pytest.fixture(scope="function")
def populated_db():
    """Provides an isolated database pre-populated with deterministic entries."""
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE logs (id INTEGER PRIMARY KEY, category TEXT, impact REAL);
    """)
    # Seed 25 records across distinct operational profiles
    for i in range(1, 26):
        category = "transport" if i % 2 == 0 else "diet"
        impact = float(10 * i) # Deterministic scaling impact metrics (10.0 to 250.0)
        cursor.execute("INSERT INTO logs VALUES (?, ?, ?);", (i, category, impact))
    conn.commit()
    yield conn
    conn.close()

# --- Advanced Query Tests Suite ---

def test_first_and_last_page_retrieval(populated_db):
    """Scenarios: Verify accurate first and last page extraction metrics boundaries."""
    # First Page Selection: 10 items per window scale
    res_first = QueryEngine.search_records(populated_db, page=1, page_size=10)
    assert len(res_first["data"]) == 10
    assert res_first["meta"]["total_pages"] == 3
    assert res_first["data"][0]["id"] == 1

    # Last Page Selection (Page 3 containing trailing remainder array offsets)
    res_last = QueryEngine.search_records(populated_db, page=3, page_size=10)
    assert len(res_last["data"]) == 5  # 25 total records - 20 historical offset = 5 left
    assert res_last["data"][-1]["id"] == 25


def test_empty_page_and_page_beyond_available_results(populated_db):
    """Scenarios: Gracefully return empty records arrays when page parameters exceed total data limits."""
    res_beyond = QueryEngine.search_records(populated_db, page=10, page_size=10)
    assert res_beyond["data"] == []
    assert res_beyond["meta"]["total_records"] == 25  # Global visibility remain accurate


def test_minimum_and_maximum_page_size_budgets(populated_db):
    """Scenarios: Verify bounds enforcement when processing standard sizing limits."""
    # Minimum Valid Limit
    res_min = QueryEngine.search_records(populated_db, page=1, page_size=1)
    assert len(res_min["data"]) == 1

    # Maximum Cap Budget Enforcement (Clamps an input of 500 down to the safety envelope ceiling of 100)
    res_max = QueryEngine.search_records(populated_db, page=1, page_size=500)
    assert res_max["meta"]["page_size"] == 100


def test_invalid_page_values_rejection(populated_db):
    """Scenario: Block zero index limits or negative parameter values predictably."""
    with pytest.raises(ValueError, match="Page index parameters must be positive integers"):
        QueryEngine.search_records(populated_db, page=0, page_size=10)


def test_multiple_simultaneous_and_conflicting_filters(populated_db):
    """Scenarios: Compound matching queries and evaluating empty intersections under conflicting fields."""
    # Simultaneous: Ingesting explicit list array categories along with lower limits values
    res_filtered = QueryEngine.search_records(
        populated_db, categories=["transport"], min_impact=150.0
    )
    # Checks matching data items without leakage paths
    for log in res_filtered["data"]:
        assert log["category"] == "transport"
        assert log["impact"] >= 150.0

    # Conflicting: Impossible threshold boundary criteria matching no valid data index rows
    res_conflicting = QueryEngine.search_records(
        populated_db, categories=["diet"], min_impact=9000.0
    )
    assert res_conflicting["data"] == []
    assert res_conflicting["meta"]["total_records"] == 0


@pytest.mark.parametrize("direction, expected_first_id, expected_last_id", [
    ("asc", 1, 10),
    ("desc", 25, 16)
])
def test_sorting_continuity_and_directions(populated_db, direction, expected_first_id, expected_last_id):
    """Scenario: Assert sorting transformations order rows predictably across both directions."""
    result = QueryEngine.search_records(
        populated_db, page=1, page_size=10, sort_by="impact", sort_dir=direction
    )
    assert result["data"][0]["id"] == expected_first_id
    assert result["data"][-1]["id"] == expected_last_id
