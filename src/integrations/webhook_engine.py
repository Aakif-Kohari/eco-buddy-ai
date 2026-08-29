import sqlite3
import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

def _get_db_conn() -> sqlite3.Connection:
    from src.core.database import DB_NAME
    return sqlite3.connect(DB_NAME)

def resolve_json_path(payload: Dict[str, Any], path: str) -> Any:
    """Resolve a simple dot-notation JSON path (e.g. 'ride.distance')."""
    keys = path.split('.')
    current = payload
    try:
        for key in keys:
            # Handle array indices like items[0]
            if '[' in key and ']' in key:
                base_key, index_str = key.split('[', 1)
                index = int(index_str.rstrip(']'))
                if base_key:
                    current = current[base_key][index]
                else:
                    current = current[index]
            else:
                current = current[key]
        return current
    except (KeyError, TypeError, IndexError, ValueError):
        return None


def process_webhook_payload(secure_token: str, raw_payload: str) -> Tuple[bool, str]:
    """
    Process an incoming webhook payload.
    Returns (success, message_or_error)
    """
    conn = _get_db_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Validate Token
        cursor.execute(
            "SELECT id, user_id, action_template, mapping_rules FROM inbound_webhooks WHERE secure_token = ? AND is_active = 1",
            (secure_token,)
        )
        webhook = cursor.fetchone()
        
        if not webhook:
            return False, "Invalid or inactive webhook token"

        webhook_id = webhook['id']
        user_id = webhook['user_id']
        action_template = webhook['action_template']
        mapping_rules_str = webhook['mapping_rules']
        
        try:
            payload_data = json.loads(raw_payload)
        except json.JSONDecodeError:
            _log_webhook_event(conn, webhook_id, raw_payload, "FAILED", "Invalid JSON payload")
            return False, "Invalid JSON payload"

        mapping_rules = json.loads(mapping_rules_str) if mapping_rules_str else {}
        
        # Extract mapped data
        extracted_data = {}
        for target_field, json_path in mapping_rules.items():
            val = resolve_json_path(payload_data, json_path)
            if val is not None:
                extracted_data[target_field] = val

        # Example action handling:
        # In a real scenario, this would route to journal logging, footprint update, etc.
        # For now, we simulate success if parsing succeeds.
        if not extracted_data and mapping_rules:
            error_msg = f"Failed to extract any mapped fields using rules: {mapping_rules_str}"
            _log_webhook_event(conn, webhook_id, raw_payload, "FAILED", error_msg)
            return False, error_msg

        _log_webhook_event(conn, webhook_id, raw_payload, "SUCCESS", f"Action: {action_template}, Data: {json.dumps(extracted_data)}")
        return True, "Payload processed successfully"

    except Exception as exc:
        logger.exception("Error processing webhook payload")
        return False, str(exc)
    finally:
        conn.close()


def _log_webhook_event(conn: sqlite3.Connection, webhook_id: str, payload: str, status: str, error_message: str = "") -> None:
    """Log the event in webhook_event_logs"""
    import uuid
    log_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO webhook_event_logs (id, webhook_id, payload, status, error_message) VALUES (?, ?, ?, ?, ?)",
            (log_id, webhook_id, payload, status, error_message)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log webhook event: {e}")
