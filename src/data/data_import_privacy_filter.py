"""PII Privacy Filter for Eco Data Exports.

Ensures that exported datasets and analytics do not leak personally 
identifiable information (PII) such as exact names, account numbers, 
or precise geolocation coordinates, which might have been accidentally 
ingested via PDF OCR or external APIs.
"""

import re
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class PrivacyFilter:
    
    def __init__(self):
        # Regex patterns to detect PII
        self.pii_patterns = {
            "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            "phone": r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            "ssn": r"\d{3}-\d{2}-\d{4}",
            "credit_card": r"\b(?:\d{4}[ -]?){3}\d{4}\b",
            "account_number": r"\b(?:Acct|Account)[:\s]*\d{6,12}\b",
            "meter_number": r"\b(?:Meter|MTR)[:\s]*[A-Z0-9]{6,12}\b"
        }
        
    def _redact_text(self, text: str) -> str:
        """Apply all PII redaction patterns to a string."""
        if not text or not isinstance(text, str):
            return text
            
        redacted = text
        for pii_type, pattern in self.pii_patterns.items():
            redacted = re.sub(pattern, f"[REDACTED {pii_type.upper()}]", redacted, flags=re.IGNORECASE)
            
        return redacted

    def sanitize_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deep copy and sanitize a list of records for safe export."""
        sanitized = []
        for r in records:
            clean_r = {}
            for k, v in r.items():
                # We specifically scrub string fields like activity, description, warnings
                if isinstance(v, str) and k in ["activity", "description", "warnings", "location", "notes"]:
                    clean_r[k] = self._redact_text(v)
                elif isinstance(v, list) and k == "_warnings":
                    clean_r[k] = [self._redact_text(w) for w in v]
                else:
                    clean_r[k] = v
            sanitized.append(clean_r)
        return sanitized
