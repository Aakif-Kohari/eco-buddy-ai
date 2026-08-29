"""Data Cleaning and Validation Pipeline.

Handles type enforcement, missing value imputation, date normalization,
and detection of invalid or duplicate records.
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Tuple, Set, Optional

logger = logging.getLogger(__name__)

# Valid EcoBuddy Categories
VALID_CATEGORIES = {"Energy", "Transport", "Waste", "Water", "Food", "Shopping", "Other"}

class DataCleaner:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.seen_hashes: Set[str] = set()

    def clean_and_validate(self, standardized_records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        """Process the mapped records.
        
        Returns:
            (valid_records, invalid_records, stats_dict)
        """
        valid = []
        invalid = []
        
        stats = {
            "total": len(standardized_records),
            "valid": 0,
            "invalid": 0,
            "duplicates": 0,
            "missing_values_filled": 0
        }
        
        for idx, record in enumerate(standardized_records):
            row_errors = []
            row_warnings = []
            
            # 1. Clean Whitespace & Nulls
            cleaned_record = self._clean_strings(record)
            
            # 2. Type Conversions & Normalizations
            
            # Date
            date_val, d_err = self._parse_date(cleaned_record.get("activity_date"))
            if d_err:
                row_errors.append(d_err)
            else:
                cleaned_record["activity_date"] = date_val
                
            # Value
            val, v_err = self._parse_numeric(cleaned_record.get("value"))
            if v_err:
                row_errors.append(v_err)
            else:
                cleaned_record["value"] = val
                
            # Emissions (optional)
            em, em_err = self._parse_numeric(cleaned_record.get("emissions_kg"), allow_none=True)
            if em_err:
                row_warnings.append(em_err)
                cleaned_record["emissions_kg"] = 0.0
            else:
                cleaned_record["emissions_kg"] = em or 0.0
                
            # Category
            cat, c_warn = self._normalize_category(cleaned_record.get("category"))
            cleaned_record["category"] = cat
            if c_warn:
                row_warnings.append(c_warn)
                
            # Fallbacks for missing non-criticals
            if not cleaned_record.get("activity"):
                cleaned_record["activity"] = "Imported Activity"
                stats["missing_values_filled"] += 1
                
            if not cleaned_record.get("unit"):
                row_errors.append("Unit is missing.")
                
            # 3. Duplicate Detection
            if not row_errors:
                record_hash = self._generate_record_hash(cleaned_record)
                if record_hash in self.seen_hashes:
                    row_errors.append("Duplicate record detected within import.")
                    stats["duplicates"] += 1
                else:
                    self.seen_hashes.add(record_hash)
                    cleaned_record["_hash"] = record_hash
                    
            # 4. Routing
            if row_errors:
                record["_errors"] = row_errors
                record["_row_index"] = idx + 1
                invalid.append(record)
                stats["invalid"] += 1
            else:
                if row_warnings:
                    cleaned_record["_warnings"] = row_warnings
                valid.append(cleaned_record)
                stats["valid"] += 1
                
        return valid, invalid, stats

    def _clean_strings(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Strip whitespace and convert empty strings to None."""
        cleaned = {}
        for k, v in record.items():
            if isinstance(v, str):
                v = v.strip()
                cleaned[k] = v if v else None
            else:
                cleaned[k] = v
        return cleaned

    def _parse_date(self, val: Any) -> Tuple[Optional[str], Optional[str]]:
        """Attempt to parse various date formats into YYYY-MM-DD."""
        if not val:
            return None, "Date is missing."
            
        if isinstance(val, str):
            # Try common formats
            formats = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]
            
            # Handle ISO with time
            if "T" in val:
                val = val.split("T")[0]
            
            # Handle simple space separation
            if " " in val:
                val = val.split(" ")[0]
                
            for fmt in formats:
                try:
                    parsed = datetime.strptime(val, fmt)
                    return parsed.strftime("%Y-%m-%d"), None
                except ValueError:
                    continue
            return None, f"Could not parse date format: {val}"
            
        elif isinstance(val, datetime):
            return val.strftime("%Y-%m-%d"), None
            
        return None, "Invalid date type."

    def _parse_numeric(self, val: Any, allow_none: bool = False) -> Tuple[Optional[float], Optional[str]]:
        """Parse value to float safely."""
        if val is None or str(val).strip() == "":
            if allow_none:
                return None, None
            return None, "Numeric value is missing."
            
        try:
            # Handle currency or comma thousands
            if isinstance(val, str):
                val = val.replace(",", "").replace("$", "").replace("£", "").replace("€", "")
            
            f_val = float(val)
            if f_val < 0:
                return None, "Value cannot be negative."
            return f_val, None
        except (ValueError, TypeError):
            return None, f"Could not convert '{val}' to number."

    def _normalize_category(self, val: Any) -> Tuple[str, Optional[str]]:
        """Map input category to a valid internal category."""
        if not val:
            return "Other", "Category missing, defaulting to 'Other'."
            
        val_str = str(val).strip().title()
        
        if val_str in VALID_CATEGORIES:
            return val_str, None
            
        # Common fuzzy mappings
        lower_val = val_str.lower()
        if "elec" in lower_val or "power" in lower_val or "gas" in lower_val:
            return "Energy", f"Mapped '{val}' to 'Energy'."
        if "car" in lower_val or "flight" in lower_val or "bus" in lower_val or "train" in lower_val or "drive" in lower_val:
            return "Transport", f"Mapped '{val}' to 'Transport'."
        if "trash" in lower_val or "garbage" in lower_val or "recycle" in lower_val or "compost" in lower_val:
            return "Waste", f"Mapped '{val}' to 'Waste'."
        if "meal" in lower_val or "diet" in lower_val or "meat" in lower_val or "grocery" in lower_val:
            return "Food", f"Mapped '{val}' to 'Food'."
        
        return "Other", f"Unknown category '{val}', mapped to 'Other'."

    def _generate_record_hash(self, record: Dict[str, Any]) -> str:
        """Create a deterministic hash to identify duplicate records."""
        # Using date, category, value, and unit as identity
        identity_string = f"{record.get('activity_date')}_{record.get('category')}_{record.get('value')}_{record.get('unit')}".lower()
        return hashlib.md5(identity_string.encode('utf-8')).hexdigest()
