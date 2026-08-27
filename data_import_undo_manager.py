"""Database Rollback and Undo Manager for Imported Data.

Allows users to safely revert an entire import batch from the core database
if they realize the mapping or data was incorrect after committing.
"""

import sqlite3
import logging
from typing import Dict, Any, List, Optional
from data_import_history import get_import_history, _get_conn

logger = logging.getLogger(__name__)

def get_import_job_details(import_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve details of a specific import job."""
    try:
        conn = _get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM data_imports WHERE import_id = ?", (import_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except sqlite3.Error as e:
        logger.error(f"Error fetching import details: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def rollback_import_job(import_id: int, household_id: int) -> bool:
    """Revert an entire import job.
    
    This deletes the imported_eco_records and attempts to remove
    synced records from the core household_activities table using the
    description tag convention.
    """
    job = get_import_job_details(import_id)
    if not job or job.get("household_id") != household_id:
        logger.warning("Import job not found or does not belong to household.")
        return False
        
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        # 1. Start a transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # 2. Identify imported eco records
        cursor.execute("SELECT activity, category FROM imported_eco_records WHERE import_id = ?", (import_id,))
        eco_records = cursor.fetchall()
        
        # 3. Try to delete synced core activities
        # We rely on the "[Imported]" tag we append in data_import_analytics.py
        for r in eco_records:
            act_desc = f"[Imported] {r[0] or 'Data'}"
            cat = r[1]
            
            cursor.execute('''
                DELETE FROM household_activities 
                WHERE household_id = ? 
                AND category = ? 
                AND description = ?
            ''', (household_id, cat, act_desc))
            
        # 4. Delete the imported records
        cursor.execute("DELETE FROM imported_eco_records WHERE import_id = ?", (import_id,))
        
        # 5. Mark the job as rolled_back
        cursor.execute('''
            UPDATE data_imports 
            SET status = 'rolled_back', valid_records = 0, invalid_records = 0 
            WHERE import_id = ?
        ''', (import_id,))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error during rollback: {e}")
        if 'conn' in locals() and conn:
            conn.rollback()
        return False
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_rollback_eligibility(import_id: int) -> Dict[str, Any]:
    """Determine if a job can be cleanly rolled back."""
    job = get_import_job_details(import_id)
    if not job:
        return {"eligible": False, "reason": "Job not found."}
        
    if job["status"] == "rolled_back":
        return {"eligible": False, "reason": "Job is already rolled back."}
        
    if job["status"] == "failed":
        return {"eligible": False, "reason": "Job failed initially, nothing to rollback."}
        
    # Check if records still exist
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM imported_eco_records WHERE import_id = ?", (import_id,))
        count = cursor.fetchone()[0]
        
        if count == 0:
            return {"eligible": False, "reason": "No stored records found for this import."}
            
        return {"eligible": True, "reason": f"Ready to rollback {count} records."}
    except sqlite3.Error as e:
        return {"eligible": False, "reason": f"DB Error: {e}"}
    finally:
        if 'conn' in locals() and conn:
            conn.close()
