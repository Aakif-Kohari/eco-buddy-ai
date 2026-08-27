"""Strict Schema Enforcement Engine for Eco Imports.

Provides deep validation of fields before they are cleaned, checking for 
bounds, regex format constraints, and domain-specific rules.
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    pass

class SchemaEnforcer:
    
    def __init__(self):
        self.rules = {
            "value": {
                "type": "numeric",
                "min": 0.0,
                "max": 1000000.0, # Sanity upper bound
            },
            "activity_date": {
                "type": "date",
                "future_allowed": False,
                "min_year": 1970
            },
            "unit": {
                "type": "string",
                "max_length": 20,
                "regex": r"^[a-zA-Z0-9_/\s-]+$"
            },
            "emissions_kg": {
                "type": "numeric",
                "min": -10000.0, # Negative allowed for offsets
                "max": 10000000.0
            }
        }
        
    def validate_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a single record against strict schema rules."""
        errors = []
        
        for field, rule in self.rules.items():
            if field not in record or record[field] is None:
                continue
                
            val = record[field]
            
            # Numeric checks
            if rule["type"] == "numeric":
                try:
                    f_val = float(str(val).replace(",", "").replace("$", ""))
                    if "min" in rule and f_val < rule["min"]:
                        errors.append(f"Field '{field}' ({f_val}) is below minimum allowed ({rule['min']}).")
                    if "max" in rule and f_val > rule["max"]:
                        errors.append(f"Field '{field}' ({f_val}) exceeds maximum allowed ({rule['max']}).")
                except ValueError:
                    errors.append(f"Field '{field}' must be numeric, got '{val}'.")
                    
            # Date checks
            elif rule["type"] == "date":
                # Assuming cleaner already attempted to parse it into YYYY-MM-DD
                if isinstance(val, str) and len(val) == 10 and "-" in val:
                    try:
                        dt = datetime.strptime(val, "%Y-%m-%d")
                        if not rule.get("future_allowed") and dt > datetime.now():
                            errors.append(f"Field '{field}' ({val}) is in the future.")
                        if "min_year" in rule and dt.year < rule["min_year"]:
                            errors.append(f"Field '{field}' ({val}) is impossibly old (before {rule['min_year']}).")
                    except ValueError:
                        errors.append(f"Field '{field}' must be a valid date.")
                        
            # String checks
            elif rule["type"] == "string":
                s_val = str(val).strip()
                if "max_length" in rule and len(s_val) > rule["max_length"]:
                    errors.append(f"Field '{field}' exceeds max length of {rule['max_length']}.")
                if "regex" in rule and not re.match(rule["regex"], s_val):
                    errors.append(f"Field '{field}' contains invalid characters.")
                    
        return len(errors) == 0, errors
        
    def enforce_batch(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        """Run strict enforcement on an entire batch before deeper cleaning."""
        valid = []
        invalid = []
        stats = {"enforcement_passed": 0, "enforcement_failed": 0}
        
        for idx, r in enumerate(records):
            passed, errs = self.validate_record(r)
            if passed:
                valid.append(r)
                stats["enforcement_passed"] += 1
            else:
                r["_errors"] = r.get("_errors", []) + errs
                r["_row_index"] = idx + 1
                invalid.append(r)
                stats["enforcement_failed"] += 1
                
        return valid, invalid, stats
