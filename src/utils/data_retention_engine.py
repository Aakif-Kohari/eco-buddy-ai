"""Data Retention Engine — Lifecycle & Compliance Management"""
import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "eco_buddy.db")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataRetentionEngine:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def _conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        return c

    def init_db(self):
        """Initialize retention tracking tables."""
        c = self._conn()
        try:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS retention_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    retention_days INTEGER NOT NULL,
                    action TEXT CHECK(action IN ('delete', 'anonymize')) NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                
                CREATE TABLE IF NOT EXISTS retention_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action_type TEXT NOT NULL,
                    tables_affected TEXT NOT NULL,
                    rows_affected INTEGER NOT NULL,
                    manifest_json TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                );
            """)
            c.commit()
            
            # Seed default policies if empty
            if c.execute("SELECT COUNT(*) FROM retention_policies").fetchone()[0] == 0:
                self.set_policy('eco_journal_entries', 'Logs', 365, 'delete')
                # We can add more defaults here later
        finally:
            c.close()

    def set_policy(self, table_name: str, category: str, retention_days: int, action: str):
        c = self._conn()
        try:
            # Upsert logic based on table_name
            c.execute("DELETE FROM retention_policies WHERE table_name = ?", (table_name,))
            c.execute("""
                INSERT INTO retention_policies (table_name, category, retention_days, action)
                VALUES (?, ?, ?, ?)
            """, (table_name, category, retention_days, action))
            c.commit()
        finally:
            c.close()

    def get_policies(self) -> List[Dict[str, Any]]:
        c = self._conn()
        try:
            rows = c.execute("SELECT * FROM retention_policies").fetchall()
            return [dict(row) for row in rows]
        finally:
            c.close()

    def compute_stale_rows(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Preview stale records across all tables based on retention policies."""
        policies = self.get_policies()
        c = self._conn()
        stale_data = {}
        total_stale = 0
        try:
            for policy in policies:
                table = policy['table_name']
                days = policy['retention_days']
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                
                # We assume a standard 'created_at' or 'entry_date' column.
                # In sqlite, we can check table pragma for columns
                cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
                date_col = 'entry_date' if 'entry_date' in cols else 'created_at' if 'created_at' in cols else None
                
                if not date_col:
                    continue
                
                query = f"SELECT COUNT(*) as cnt FROM {table} WHERE {date_col} <= ?"
                params = [cutoff_date]
                if user_id is not None:
                    if 'user_id' in cols:
                        query += " AND user_id = ?"
                        params.append(user_id)
                    else:
                        continue
                
                try:
                    cnt = c.execute(query, params).fetchone()['cnt']
                    if cnt > 0:
                        stale_data[table] = {
                            'action': policy['action'],
                            'category': policy['category'],
                            'stale_count': cnt,
                            'cutoff_date': cutoff_date
                        }
                        total_stale += cnt
                except sqlite3.Error as e:
                    logger.error(f"Error querying {table}: {e}")
            
            return {"stale_data": stale_data, "total_stale_rows": total_stale}
        finally:
            c.close()

    def run_cleanup(self):
        """Execute cleanup background task to delete/anonymize stale rows globally."""
        stale_info = self.compute_stale_rows()
        stale_data = stale_info.get("stale_data", {})
        
        c = self._conn()
        try:
            for table, info in stale_data.items():
                cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
                date_col = 'entry_date' if 'entry_date' in cols else 'created_at' if 'created_at' in cols else None
                
                if not date_col:
                    continue
                
                c.execute("BEGIN TRANSACTION")
                try:
                    rows_affected = 0
                    if info['action'] == 'delete':
                        cur = c.execute(f"DELETE FROM {table} WHERE {date_col} <= ?", (info['cutoff_date'],))
                        rows_affected = cur.rowcount
                    elif info['action'] == 'anonymize':
                        # Example generic anonymization. Replace identifiable text cols.
                        # This will need specific column targeting based on requirements.
                        update_cols = []
                        if 'content' in cols: update_cols.append("content = '[ANONYMIZED]'")
                        if 'title' in cols: update_cols.append("title = '[ANONYMIZED]'")
                        if 'user_id' in cols: update_cols.append("user_id = -1")
                        
                        if update_cols:
                            set_clause = ", ".join(update_cols)
                            cur = c.execute(f"UPDATE {table} SET {set_clause} WHERE {date_col} <= ?", (info['cutoff_date'],))
                            rows_affected = cur.rowcount
                    
                    # Log audit
                    c.execute("""
                        INSERT INTO retention_audit_log (action_type, tables_affected, rows_affected, manifest_json)
                        VALUES (?, ?, ?, ?)
                    """, (f"policy_cleanup_{info['action']}", table, rows_affected, json.dumps(info)))
                    
                    c.commit()
                    logger.info(f"Cleaned up {rows_affected} rows from {table}")
                except sqlite3.Error as e:
                    c.rollback()
                    logger.error(f"Transaction failed for {table}: {e}")
        finally:
            c.close()

    def purge_user_data(self, user_id: int) -> Dict[str, Any]:
        """Right to Erasure: fully purge all user records transactionally."""
        c = self._conn()
        manifest = {"user_id": user_id, "deleted_records": {}, "timestamp": datetime.now().isoformat()}
        total_deleted = 0
        
        try:
            tables = [row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            c.execute("BEGIN TRANSACTION")
            
            for table in tables:
                cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
                if 'user_id' in cols:
                    cur = c.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
                    if cur.rowcount > 0:
                        manifest["deleted_records"][table] = cur.rowcount
                        total_deleted += cur.rowcount
            
            if total_deleted > 0:
                c.execute("""
                    INSERT INTO retention_audit_log (user_id, action_type, tables_affected, rows_affected, manifest_json)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, "user_purge", json.dumps(list(manifest["deleted_records"].keys())), total_deleted, json.dumps(manifest)))
                
            c.commit()
            return manifest
        except sqlite3.Error as e:
            c.rollback()
            logger.error(f"Purge failed for user {user_id}: {e}")
            raise e
        finally:
            c.close()

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        c = self._conn()
        try:
            rows = c.execute("SELECT * FROM retention_audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]
        finally:
            c.close()

engine = DataRetentionEngine()
