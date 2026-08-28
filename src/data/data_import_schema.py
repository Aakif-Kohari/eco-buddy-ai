"""Eco Data Import Schema and Column Mapping.

Provides structures and heuristics to automatically detect and map
arbitrary user CSV/JSON columns into the standardized EcoBuddy data model.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Standard EcoBuddy field definitions
@dataclass
class StandardField:
    name: str
    data_type: str  # 'date', 'string', 'numeric', 'category'
    required: bool
    aliases: List[str]
    description: str

STANDARD_SCHEMA = {
    "activity_date": StandardField(
        name="activity_date",
        data_type="date",
        required=True,
        aliases=["date", "time", "timestamp", "activitydate", "created_at", "day"],
        description="The date of the sustainability activity."
    ),
    "category": StandardField(
        name="category",
        data_type="category",
        required=True,
        aliases=["cat", "type", "activity_type", "domain", "sector"],
        description="The broad category (e.g., Energy, Transport, Waste, Food)."
    ),
    "activity": StandardField(
        name="activity",
        data_type="string",
        required=False,
        aliases=["name", "description", "item", "action", "detail"],
        description="A specific description of the activity."
    ),
    "value": StandardField(
        name="value",
        data_type="numeric",
        required=True,
        aliases=["amount", "quantity", "qty", "consumption", "distance", "cost"],
        description="The numeric amount of the activity."
    ),
    "unit": StandardField(
        name="unit",
        data_type="string",
        required=True,
        aliases=["uom", "measure", "measurement", "units"],
        description="The unit of measurement (e.g., kWh, miles, kg)."
    ),
    "emissions_kg": StandardField(
        name="emissions_kg",
        data_type="numeric",
        required=False,
        aliases=["emissions", "carbon", "co2", "co2e", "carbon_footprint", "impact"],
        description="The calculated carbon impact in kg CO2e."
    )
}

def normalize_column_name(col: str) -> str:
    """Normalize a column name for easier matching."""
    if not isinstance(col, str):
        return ""
    # Lowercase, replace non-alphanumeric with underscores, strip ends
    cleaned = re.sub(r'[^a-z0-9]+', '_', col.lower()).strip('_')
    return cleaned

def detect_schema_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    """Automatically suggest mappings from user columns to standard fields.
    
    Args:
        columns: List of column names from the uploaded dataset.
        
    Returns:
        Dict mapping standard field names to the best-matched uploaded column.
    """
    mapping: Dict[str, Optional[str]] = {field: None for field in STANDARD_SCHEMA.keys()}
    used_columns: Set[str] = set()
    
    # Pre-clean columns
    col_map = {col: normalize_column_name(col) for col in columns}
    
    # 1. Exact match pass
    for std_key, std_field in STANDARD_SCHEMA.items():
        for orig_col, norm_col in col_map.items():
            if orig_col in used_columns:
                continue
            if norm_col == std_key or norm_col == std_field.name:
                mapping[std_key] = orig_col
                used_columns.add(orig_col)
                break
                
    # 2. Alias match pass
    for std_key, std_field in STANDARD_SCHEMA.items():
        if mapping[std_key] is not None:
            continue
            
        best_match = None
        for orig_col, norm_col in col_map.items():
            if orig_col in used_columns:
                continue
                
            # Check if norm_col matches any alias
            if any(alias in norm_col for alias in std_field.aliases):
                best_match = orig_col
                break
                
        if best_match:
            mapping[std_key] = best_match
            used_columns.add(best_match)
            
    # 3. Fallback heuristics for value/unit if not found
    if mapping["value"] is None:
        for orig_col, norm_col in col_map.items():
            if orig_col not in used_columns and any(x in norm_col for x in ["num", "count", "total"]):
                mapping["value"] = orig_col
                used_columns.add(orig_col)
                break
                
    return mapping

def validate_mapping(mapping: Dict[str, Optional[str]]) -> Tuple[bool, List[str]]:
    """Check if the current mapping satisfies required fields.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Check duplicate mappings
    mapped_targets = [v for v in mapping.values() if v is not None]
    if len(mapped_targets) != len(set(mapped_targets)):
        src.core.errors.append("Duplicate mapping: Multiple fields mapped to the same column.")
        
    for std_key, std_field in STANDARD_SCHEMA.items():
        if std_field.required and mapping.get(std_key) is None:
            src.core.errors.append(f"Required field '{std_field.name}' is unmapped.")
            
    return len(errors) == 0, errors

def apply_mapping(records: List[Dict[str, Any]], mapping: Dict[str, Optional[str]]) -> List[Dict[str, Any]]:
    """Transform raw records into standardized records using the mapping.
    
    Unmapped fields are dropped from the standardized output.
    """
    standardized = []
    
    for row in records:
        std_row = {}
        for std_key, orig_col in mapping.items():
            if orig_col is not None and orig_col in row:
                std_row[std_key] = row[orig_col]
            else:
                std_row[std_key] = None
        standardized.append(std_row)
        
    return standardized
