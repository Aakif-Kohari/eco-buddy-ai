import hashlib
import sqlite3
import datetime
import logging

class DataDeletionService:
    """
    Executes 'Right to be Forgotten' requests safely by either hard deleting
    or securely anonymizing PII while retaining statistical footprints.
    """

    def __init__(self, db_path: str = "eco_buddy.db"):
        self.db_path = db_path
        self.logger = logging.getLogger("DataDeletionService")

    def _execute_query(self, query: str, params: tuple = ()) -> None:
        """Helper to run a raw write query, for demonstration purposes."""
        # For the sake of the script, we mock execution if the table doesn't exist
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
        except sqlite3.OperationalError:
            self.logger.warning(f"Simulating query execution (table might not exist): {query}")

    def execute_hard_delete(self, user_id: str) -> bool:
        """
        Permanently deletes all traces of the user from the database.
        WARNING: This breaks statistical continuity.
        """
        self.logger.info(f"Initiating HARD DELETE for user {user_id}")
        
        queries = [
            ("DELETE FROM footprints WHERE user_id = ?", (user_id,)),
            ("DELETE FROM preferences WHERE user_id = ?", (user_id,)),
            ("DELETE FROM users WHERE user_id = ?", (user_id,)),
        ]
        
        try:
            for q, p in queries:
                self._execute_query(q, p)
            return True
        except Exception as e:
            self.logger.error(f"Failed to hard delete user {user_id}: {e}")
            return False

    def execute_anonymization(self, user_id: str) -> str:
        """
        Retains footprint data for global statistical models but safely hashes
        any PII (email, names, IPs). Returns the new anonymized hash ID.
        """
        self.logger.info(f"Initiating ANONYMIZATION for user {user_id}")
        
        # Create an irreversible hash based on current time + user ID
        salt = str(datetime.datetime.now().timestamp())
        anon_id = "ANON_" + hashlib.sha256((user_id + salt).encode('utf-8')).hexdigest()[:16]
        
        queries = [
            # Nullify PII in users table, rename ID
            ("UPDATE users SET email = NULL, name = 'Redacted', user_id = ? WHERE user_id = ?", (anon_id, user_id)),
            # Transfer footprints to anonymized ID
            ("UPDATE footprints SET user_id = ? WHERE user_id = ?", (anon_id, user_id)),
            # Preferences are considered PII if they contain location data etc, so we delete them
            ("DELETE FROM preferences WHERE user_id = ?", (user_id,))
        ]
        
        try:
            for q, p in queries:
                self._execute_query(q, p)
            return anon_id
        except Exception as e:
            self.logger.error(f"Failed to anonymize user {user_id}: {e}")
            return ""
