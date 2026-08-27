"""Unit Normalization and Analytics Conversions.

Provides safe normalization of various sustainability metrics (distance,
energy, volume, weight) into a consistent internal format to enable
accurate analytics and aggregations.
"""

import logging
from typing import Dict, Any, Tuple, List

logger = logging.getLogger(__name__)

# Standard units we want to convert to
STANDARD_UNITS = {
    "Energy": "kWh",
    "Transport": "km",
    "Water": "L",
    "Waste": "kg",
    "Food": "meals"
}

# Conversion factors to standard unit
CONVERSIONS = {
    # Energy to kWh
    "wh": 0.001,
    "mwh": 1000.0,
    "joules": 2.77778e-7,
    "mj": 0.277778,
    "btu": 0.000293071,
    "therms": 29.3001,
    "kwh": 1.0,
    
    # Transport to km
    "mi": 1.60934,
    "miles": 1.60934,
    "meters": 0.001,
    "m": 0.001,
    "km": 1.0,
    "kilometers": 1.0,
    
    # Water/Volume to Liters (L)
    "gal": 3.78541,
    "gallons": 3.78541,
    "oz": 0.0295735,
    "fl oz": 0.0295735,
    "ml": 0.001,
    "m3": 1000.0,
    "cubic meters": 1000.0,
    "l": 1.0,
    "liters": 1.0,
    "litres": 1.0,
    
    # Waste/Weight to kg
    "lbs": 0.453592,
    "pounds": 0.453592,
    "oz_weight": 0.0283495,
    "tons": 907.185,
    "metric tons": 1000.0,
    "tonnes": 1000.0,
    "g": 0.001,
    "grams": 0.001,
    "kg": 1.0,
    "kilograms": 1.0
}

def normalize_units(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Normalize values in the records based on their category and unit.
    
    Args:
        records: List of cleaned, validated records.
        
    Returns:
        (normalized_records, stats_dict)
    """
    normalized_records = []
    stats = {
        "converted": 0,
        "unsupported_unit": 0,
        "unchanged": 0
    }
    
    for record in records:
        cat = record["category"]
        val = record["value"]
        orig_unit = str(record["unit"]).strip().lower()
        
        target_unit = STANDARD_UNITS.get(cat)
        
        # If we don't have a standard target for this category (e.g. Shopping), leave it alone.
        if not target_unit:
            stats["unchanged"] += 1
            normalized_records.append(record)
            continue
            
        if orig_unit == target_unit.lower():
            record["normalized_value"] = val
            record["normalized_unit"] = target_unit
            stats["unchanged"] += 1
            normalized_records.append(record)
            continue
            
        # Attempt conversion
        # Some units overlap in name but context differs (e.g., oz). Context is derived by target unit.
        conversion_factor = CONVERSIONS.get(orig_unit)
        
        # Special handling for ambiguous units like 'oz' based on category
        if orig_unit == "oz":
            if cat == "Water":
                conversion_factor = CONVERSIONS["oz"] # fluid oz
            elif cat == "Waste":
                conversion_factor = CONVERSIONS["oz_weight"]
        
        if conversion_factor is not None:
            record["normalized_value"] = val * conversion_factor
            record["normalized_unit"] = target_unit
            
            if "_warnings" not in record:
                record["_warnings"] = []
            record["_warnings"].append(f"Normalized unit from '{orig_unit}' to '{target_unit}'.")
            
            stats["converted"] += 1
        else:
            # Cannot convert securely. Leave original, but add warning.
            record["normalized_value"] = val
            record["normalized_unit"] = record["unit"]
            if "_warnings" not in record:
                record["_warnings"] = []
            record["_warnings"].append(f"Unsupported unit '{orig_unit}' for category '{cat}'. Could not normalize.")
            stats["unsupported_unit"] += 1
            
        normalized_records.append(record)
        
    return normalized_records, stats

def estimate_missing_emissions(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Estimate emissions for records where emissions_kg is 0 or missing,
    using basic fallback emission factors per normalized unit.
    """
    # Simple fallback emission factors (kg CO2e per standard unit)
    FALLBACK_EF = {
        "Energy": 0.4,       # kg/kWh (average grid)
        "Transport": 0.2,    # kg/km (average car)
        "Water": 0.001,      # kg/L (treatment + pumping)
        "Waste": 0.5,        # kg/kg (average landfill)
        "Food": 2.0,         # kg/meal (average mixed diet)
        "Shopping": 5.0      # kg/item (rough proxy)
    }
    
    for record in records:
        emissions = record.get("emissions_kg", 0.0)
        if emissions == 0.0:
            cat = record["category"]
            # Use normalized value if available, else fallback to raw value
            val = record.get("normalized_value", record["value"])
            
            factor = FALLBACK_EF.get(cat, 0.0)
            record["emissions_kg"] = val * factor
            
            if factor > 0:
                if "_warnings" not in record:
                    record["_warnings"] = []
                record["_warnings"].append(f"Estimated missing emissions using fallback factor for {cat}.")
                
    return records
