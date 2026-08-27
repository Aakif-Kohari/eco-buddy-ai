import hashlib
import json
import os
import sqlite3
import time
from typing import Optional, Dict, Any, List
from src.core.database_connection import database_connection

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")
SECRET_SALT = os.getenv("ECO_CREDITS_SALT", "default-insecure-salt")

def generate_hash(sender_id: str, receiver_id: str, amount: float, timestamp: float, previous_hash: str) -> str:
    """Generate a cryptographic hash for a transaction."""
    payload = f"{sender_id}:{receiver_id}:{amount}:{timestamp}:{previous_hash}:{SECRET_SALT}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def mint_credits(user_id: str, amount: float, proof_data: Dict[str, Any]) -> bool:
    """
    Mint new credits based on verifiable proof data (e.g. OCR results).
    In a real system, the proof data would be validated against OCR history.
    """
    if amount <= 0:
        return False
        
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # Get the previous hash for the system
        cursor.execute("SELECT hash FROM eco_ledger_transactions ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        previous_hash = row[0] if row else "0"
        
        timestamp = time.time()
        # Sender is 'SYSTEM' for minting
        tx_hash = generate_hash("SYSTEM", user_id, amount, timestamp, previous_hash)
        
        cursor.execute("BEGIN TRANSACTION")
        try:
            # Insert transaction
            cursor.execute('''
                INSERT INTO eco_ledger_transactions (sender_id, receiver_id, amount, timestamp, previous_hash, hash, proof_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', ("SYSTEM", user_id, amount, timestamp, previous_hash, tx_hash, json.dumps(proof_data)))
            
            # Update receiver balance
            cursor.execute('''
                INSERT INTO eco_ledger_accounts (user_id, balance)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET balance = balance + excluded.balance
            ''', (user_id, amount))
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            print(f"Error minting credits: {e}")
            return False

from src.core.database_connection import execute_with_retry

def transfer_credits(sender_id: str, receiver_id: str, amount: float) -> bool:
    """Transfer credits between users."""
    if amount <= 0 or sender_id == receiver_id:
        return False
        
    def _transfer():
        with database_connection(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            try:
                # Check sender balance
                cursor.execute("SELECT balance FROM eco_ledger_accounts WHERE user_id = ?", (sender_id,))
                row = cursor.fetchone()
                if not row or row[0] < amount:
                    conn.rollback()
                    return False
                    
                # Get previous hash
                cursor.execute("SELECT hash FROM eco_ledger_transactions ORDER BY id DESC LIMIT 1")
                row = cursor.fetchone()
                previous_hash = row[0] if row else "0"
                
                timestamp = time.time()
                tx_hash = generate_hash(sender_id, receiver_id, amount, timestamp, previous_hash)
                
                # Insert transaction
                cursor.execute('''
                    INSERT INTO eco_ledger_transactions (sender_id, receiver_id, amount, timestamp, previous_hash, hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (sender_id, receiver_id, amount, timestamp, previous_hash, tx_hash))
                
                # Update sender balance
                cursor.execute('''
                    UPDATE eco_ledger_accounts SET balance = balance - ? WHERE user_id = ?
                ''', (amount, sender_id))
                
                # Update receiver balance
                cursor.execute('''
                    INSERT INTO eco_ledger_accounts (user_id, balance)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET balance = balance + excluded.balance
                ''', (receiver_id, amount))
                
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                print(f"Error transferring credits: {e}")
                raise  # Re-raise so execute_with_retry can handle it

    try:
        return execute_with_retry(_transfer, max_attempts=10, base_delay=0.1)
    except Exception as e:
        print(f"Transfer failed after retries: {e}")
        return False

def get_balance(user_id: str) -> float:
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM eco_ledger_accounts WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0.0

def verify_ledger_integrity() -> bool:
    """Verify that no transactions have been tampered with."""
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sender_id, receiver_id, amount, timestamp, previous_hash, hash FROM eco_ledger_transactions ORDER BY id ASC")
        rows = cursor.fetchall()
        
        expected_previous_hash = "0"
        for row in rows:
            sender, receiver, amount, ts, prev_hash, stored_hash = row
            if prev_hash != expected_previous_hash:
                return False
            
            calculated_hash = generate_hash(sender, receiver, amount, ts, prev_hash)
            if calculated_hash != stored_hash:
                return False
                
            expected_previous_hash = stored_hash
            
    return True
