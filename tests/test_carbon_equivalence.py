import pytest
import json
import sqlite3
from unittest.mock import patch

from src.carbon.carbon_equivalence import (
    translate_footprint,
    get_category_equivalences,
    EQUIVALENCE_FACTORS
)
from src.core.database import save_equivalence_preferences, get_equivalence_preferences

def test_translate_footprint_positive():
    # 10 kg CO2
    results = translate_footprint(10.0, top_n=5)
    assert len(results) > 0
    assert len(results) <= 5
    
    # Check math for trees_planted: 10 / 6 = 1.67
    trees = next((r for r in translate_footprint(10.0, top_n=15) if r["key"] == "trees_planted"), None)
    if trees:
        assert trees["units"] == 1.67

def test_translate_footprint_negative():
    results = translate_footprint(-5.0)
    assert results == []

def test_translate_footprint_zero():
    results = translate_footprint(0.0)
    assert len(results) > 0
    assert all(r["units"] == 0.0 for r in results)

def test_translate_footprint_large():
    results = translate_footprint(1000000.0)
    assert len(results) > 0
    assert results[0]["units"] > 1000

def test_get_category_equivalences():
    # Transport category
    results = get_category_equivalences("transport", 50.0)
    assert any(r["key"] == "miles_driven" for r in results)
    
    # Unknown category falls back to first 3
    results = get_category_equivalences("unknown_cat", 50.0)
    assert len(results) == 3

def test_get_category_equivalences_negative():
    results = get_category_equivalences("transport", -10.0)
    assert results == []

@pytest.fixture
def temp_db():
    from src.core import database
    import os
    import sqlite3
    import uuid
    test_db_path = f"test_carbon_eq_{uuid.uuid4().hex}.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    original_db = database.DB_NAME
    database.DB_NAME = test_db_path
    
    database.init_db()
    
    # Force table creation just to be absolutely sure
    with sqlite3.connect(test_db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equivalence_preferences (
                user_id INTEGER PRIMARY KEY,
                top_metrics TEXT,
                region TEXT DEFAULT 'Global',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    
    yield
    database.DB_NAME = original_db
    
    import gc
    gc.collect()
    
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass

def test_save_and_get_equivalence_preferences(temp_db):
    user_id = 9999
    metrics = json.dumps(["trees_planted", "miles_driven"])
    region = "US"
    
    assert save_equivalence_preferences(user_id, metrics, region) is True
    
    prefs = get_equivalence_preferences(user_id)
    assert prefs is not None
    assert prefs["top_metrics"] == metrics
    assert prefs["region"] == region
    
    # Test update
    metrics2 = json.dumps(["smartphones_charged"])
    region2 = "EU"
    assert save_equivalence_preferences(user_id, metrics2, region2) is True
    
    prefs2 = get_equivalence_preferences(user_id)
    assert prefs2["top_metrics"] == metrics2
    assert prefs2["region"] == region2

def test_get_equivalence_preferences_not_found(temp_db):
    assert get_equivalence_preferences(8888) is None
