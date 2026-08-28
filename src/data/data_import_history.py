"""Database persistence and Import History tracking.

Maintains tables for tracking import jobs, raw data preservation,
and cleaned, analytics-ready records.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.lifestyle.household import _get_conn

logger = logging.getLogger(__name__)

def init_import_db() -> bool:
    """Initialize the data import tables."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # Track the import jobs themselves
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_imports (
                import_id INTEGER PRIMARY KEY AUTOINCREMENT,
                household_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                source_type TEXT NOT NULL,
                total_records INTEGER DEFAULT 0,
                valid_records INTEGER DEFAULT 0,
                invalid_records INTEGER DEFAULT 0,
                duplicate_records INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
            )
        ''')
        
        # Store the actual cleaned/normalized records
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS imported_eco_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id INTEGER NOT NULL,
                household_id INTEGER NOT NULL,
                activity_date DATE NOT NULL,
                category TEXT NOT NULL,
                activity TEXT,
                original_value REAL NOT NULL,
                original_unit TEXT NOT NULL,
                normalized_value REAL,
                normalized_unit TEXT,
                emissions_kg REAL,
                record_hash TEXT NOT NULL,
                warnings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (import_id) REFERENCES data_imports(import_id) ON DELETE CASCADE,
                FOREIGN KEY (household_id) REFERENCES households(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error initializing import DB: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def log_import_job(
    household_id: int, 
    filename: str, 
    source_type: str, 
    stats: Dict[str, int], 
    status: str
) -> Optional[int]:
    """Create a record of a new data import job."""
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO data_imports 
            (household_id, filename, source_type, total_records, valid_records, invalid_records, duplicate_records, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            household_id, filename, source_type, 
            stats.get("total", 0), stats.get("valid", 0), 
            stats.get("invalid", 0), stats.get("duplicates", 0), status
        ))
        
        import_id = cursor.lastrowid
        conn.commit()
        return import_id
    except sqlite3.Error as e:
        logger.error(f"Error logging import job: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def save_imported_records(import_id: int, household_id: int, valid_records: List[Dict[str, Any]]) -> bool:
    """Save the validated and normalized records to the src.core.database."""
    if not valid_records:
        return True
        
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        insert_data = []
        for r in valid_records:
            warnings_str = json.dumps(r.get("_warnings", []))
            
            insert_data.append((
                import_id,
                household_id,
                r["activity_date"],
                r["category"],
                r.get("activity"),
                r["value"],
                r["unit"],
                r.get("normalized_value"),
                r.get("normalized_unit"),
                r.get("emissions_kg", 0.0),
                r.get("_hash", "no_hash_provided"),
                warnings_str
            ))
            
        cursor.executemany('''
            INSERT INTO imported_eco_records 
            (import_id, household_id, activity_date, category, activity, 
             original_value, original_unit, normalized_value, normalized_unit, 
             emissions_kg, record_hash, warnings)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', insert_data)
        
        conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Error saving imported records: {e}")
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_import_history(household_id: int) -> List[Dict[str, Any]]:
    """Retrieve all import jobs for a src.lifestyle.household."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM data_imports 
            WHERE household_id = ? 
            ORDER BY import_date DESC
        ''', (household_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching import history: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_imported_records(household_id: int, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve all cleaned, normalized records for a household, optionally filtered by category."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category:
            cursor.execute('''
                SELECT * FROM imported_eco_records 
                WHERE household_id = ? AND category = ?
                ORDER BY activity_date DESC
            ''', (household_id, category))
        else:
            cursor.execute('''
                SELECT * FROM imported_eco_records 
                WHERE household_id = ?
                ORDER BY activity_date DESC
            ''', (household_id,))
            
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        logger.error(f"Error fetching imported records: {e}")
        return []
    finally:
        if 'conn' in locals() and conn:
            conn.close()
