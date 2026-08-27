import pytest
import sqlite3
import os
import tempfile
import pandas as pd
from datetime import date, timedelta
import pages.Smart_Pantry
from pages.Smart_Pantry import calculate_risk

def test_calculate_risk():
    # Expired: expiry date is in the past
    row_expired = pd.Series({'status': 'Active', 'expiry_date': date.today() - timedelta(days=1)})
    assert calculate_risk(row_expired) == 'Expired'
    
    # High Risk: 0-2 days remaining
    row_high_0 = pd.Series({'status': 'Active', 'expiry_date': date.today()})
    assert calculate_risk(row_high_0) == 'High Risk'
    row_high_1 = pd.Series({'status': 'Active', 'expiry_date': date.today() + timedelta(days=2)})
    assert calculate_risk(row_high_1) == 'High Risk'
    
    # Moderate Risk: 3-5 days remaining
    row_mod_3 = pd.Series({'status': 'Active', 'expiry_date': date.today() + timedelta(days=3)})
    assert calculate_risk(row_mod_3) == 'Moderate Risk'
    row_mod_5 = pd.Series({'status': 'Active', 'expiry_date': date.today() + timedelta(days=5)})
    assert calculate_risk(row_mod_5) == 'Moderate Risk'
    
    # Low Risk: >5 days remaining
    row_low = pd.Series({'status': 'Active', 'expiry_date': date.today() + timedelta(days=6)})
    assert calculate_risk(row_low) == 'Low Risk'
    
    # Logged: status is not Active
    row_logged = pd.Series({'status': 'Consumed', 'expiry_date': date.today() + timedelta(days=10)})
    assert calculate_risk(row_logged) == 'Logged'

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    original_db = pages.Smart_Pantry.DB_FILE
    pages.Smart_Pantry.DB_FILE = path
    pages.Smart_Pantry.init_db()
    
    yield path
    
    pages.Smart_Pantry.DB_FILE = original_db
    if os.path.exists(path):
        import gc
        gc.collect()
        try:
            os.remove(path)
        except Exception:
            pass

def test_database_operations(temp_db):
    df = pages.Smart_Pantry.get_all_items()
    assert df.empty
    
    today = date.today()
    expiry = today + timedelta(days=7)
    pages.Smart_Pantry.add_pantry_item("Banana", "Fruits & Vegetables", today, expiry, 2.5, True)
    
    df = pages.Smart_Pantry.get_all_items()
    assert len(df) == 1
    assert df.iloc[0]['item_name'] == "Banana"
    assert df.iloc[0]['category'] == "Fruits & Vegetables"
    assert df.iloc[0]['cost'] == 2.5
    assert df.iloc[0]['is_perishable'] == 1
    assert df.iloc[0]['status'] == "Active"
    
    item_id = df.iloc[0]['id']
    pages.Smart_Pantry.update_item_status(item_id, "Consumed")
    
    df = pages.Smart_Pantry.get_all_items()
    assert df.iloc[0]['status'] == "Consumed"
