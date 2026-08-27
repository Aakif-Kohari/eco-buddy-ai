"""Geospatial Processing and Region-Based Emission Factors.

When users import data with location tags, this module normalizes the location
and applies localized emission factors. For example, 100 kWh of electricity 
in California has a wildly different carbon footprint than 100 kWh in Wyoming
due to the makeup of their respective electrical grids.
"""

import logging
import re
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Simplified grid emission factors (kg CO2e per kWh)
# In a real app, this would be an expansive EPA eGRID or IEA database.
REGIONAL_GRID_FACTORS = {
    # US Regions
    "US-CA": 0.22, # California (high renewables)
    "US-NY": 0.23, # New York
    "US-TX": 0.42, # Texas (mixed)
    "US-WY": 0.85, # Wyoming (coal heavy)
    "US-WA": 0.11, # Washington (hydro heavy)
    "US-FL": 0.40,
    "US-AVG": 0.38,
    
    # Global Regions
    "EU-FR": 0.05, # France (nuclear heavy)
    "EU-DE": 0.35, # Germany
    "EU-UK": 0.23, # UK
    "AU-NSW": 0.70, # Australia NSW (coal heavy)
    "AU-TAS": 0.15, # Tasmania (hydro)
    "CA-ON": 0.04, # Ontario (nuclear/hydro)
    "CA-AB": 0.55, # Alberta
    "IN-MH": 0.75, # India Maharashtra
    "BR-SP": 0.10, # Brazil (hydro heavy)
    
    "GLOBAL-AVG": 0.45
}

# Simple text-to-region mapping heuristics
REGION_MAPPING = {
    r"\bcalifornia\b|\bca\b|\bsan francisco\b|\blos angeles\b": "US-CA",
    r"\bnew york\b|\bny\b|\bnyc\b": "US-NY",
    r"\btexas\b|\btx\b|\bhouston\b|\baustin\b": "US-TX",
    r"\bwyoming\b|\bwy\b": "US-WY",
    r"\bwashington\b|\bwa\b|\bseattle\b": "US-WA",
    r"\bfrance\b|\bparis\b": "EU-FR",
    r"\bgermany\b|\bberlin\b": "EU-DE",
    r"\buk\b|\bunited kingdom\b|\blondon\b": "EU-UK",
    r"\bontario\b|\btoronto\b": "CA-ON",
    r"\bsydney\b|\bnsw\b": "AU-NSW"
}

def extract_region_from_text(text: str) -> str:
    """Attempt to extract a known region code from arbitrary text."""
    if not text:
        return "GLOBAL-AVG"
        
    text = text.lower()
    
    for pattern, region_code in REGION_MAPPING.items():
        if re.search(pattern, text):
            return region_code
            
    # Fallback checks
    if re.search(r"\b(us|usa|united states)\b", text):
        return "US-AVG"
        
    return "GLOBAL-AVG"

def apply_geospatial_emission_factors(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Scan imported records for location metadata and adjust energy emission calculations."""
    stats = {"regions_detected": 0, "emissions_adjusted": 0}
    
    for r in records:
        # Only adjust if it's Energy (grid) and emissions haven't been explicitly provided
        if r.get("category") == "Energy" and (not r.get("emissions_kg") or r.get("_is_estimated")):
            
            # Check if there is a location column
            location_text = str(r.get("location", "")) + " " + str(r.get("activity", ""))
            
            region_code = extract_region_from_text(location_text)
            
            if region_code != "GLOBAL-AVG":
                stats["regions_detected"] += 1
                
            factor = REGIONAL_GRID_FACTORS.get(region_code, REGIONAL_GRID_FACTORS["GLOBAL-AVG"])
            
            val = r.get("normalized_value") or r.get("value", 0.0)
            
            try:
                val = float(val)
            except (ValueError, TypeError):
                val = 0.0
            
            # Calculate new localized emissions
            old_emissions = r.get("emissions_kg")
            if old_emissions is None:
                old_emissions = 0.0
                
            new_emissions = val * factor
            
            if abs(old_emissions - new_emissions) > 0.1:
                r["emissions_kg"] = new_emissions
                if "_warnings" not in r:
                    r["_warnings"] = []
                r["_warnings"].append(f"[Geospatial] Applied localized grid factor for region {region_code} ({factor} kg/kWh).")
                r["_is_estimated"] = True
                stats["emissions_adjusted"] += 1
                
    return records, stats

def calculate_commute_geospatial(origin: str, destination: str) -> Optional[float]:
    """Calculate the distance in km between two text locations.
    
    This is a mock implementation of a geospatial bounding box / distance API.
    Returns simulated distances for testing.
    """
    if not origin or not destination:
        return None
        
    # Mock some known routes
    route = f"{origin.lower()}-{destination.lower()}"
    routes = {
        "jfk-lax": 3983.0,
        "london-paris": 344.0,
        "sydney-melbourne": 713.0,
        "tokyo-osaka": 400.0,
        "ny-dc": 362.0
    }
    
    if route in routes:
        return routes[route]
        
    # Reverse lookup
    rev_route = f"{destination.lower()}-{origin.lower()}"
    if rev_route in routes:
        return routes[rev_route]
        
    # Fallback hash-based deterministic distance for unknown pairs
    import hashlib
    hash_val = int(hashlib.md5(route.encode()).hexdigest()[:8], 16)
    return float((hash_val % 1000) + 10)
