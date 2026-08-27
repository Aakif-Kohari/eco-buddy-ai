"""PDF Utility Bill Extractor.

Provides heuristic text extraction for common utility bill formats
(e.g., PG&E, ConEdison, Thames Water) using regex pattern matching.
This allows the Import Hub to ingest PDF text dumps.
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class PDFUtilityBillParser:
    
    def __init__(self):
        # Common regex patterns to hunt for in raw OCR/PDF text
        self.patterns = {
            "pge": {
                "provider": "PG&E",
                "date": r"(?:Statement Date|Bill Date):\s*(\d{2}/\d{2}/\d{4})",
                "electricity_kwh": r"(?:Total Electric Charges|Electricity Usage)\s*.*?([\d,]+(?:\.\d+)?)\s*kWh",
                "gas_therms": r"(?:Total Gas Charges|Gas Usage)\s*.*?([\d,]+(?:\.\d+)?)\s*Therms"
            },
            "coned": {
                "provider": "ConEdison",
                "date": r"(?:Billing Period|Date):\s*([A-Za-z]+ \d{1,2}, \d{4})",
                "electricity_kwh": r"(?:Electricity Supply|Your Electricity Use)\s*.*?([\d,]+(?:\.\d+)?)\s*kWh"
            },
            "generic_water": {
                "provider": "Generic Water",
                "date": r"(?:Invoice Date|Bill Date):?\s*([\w/.-]+)",
                "water_gal": r"(?:Water Usage|Consumption):?\s*([\d,]+(?:\.\d+)?)\s*(?:Gal|Gallons)"
            }
        }
        
    def _clean_number(self, num_str: str) -> float:
        try:
            return float(num_str.replace(",", ""))
        except ValueError:
            return 0.0
            
    def _standardize_date(self, date_str: str) -> str:
        # A real implementation would use dateutil.parser
        return date_str.strip()

    def parse_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse raw text from a PDF bill and emit structured EcoBuddy records."""
        records = []
        if not text:
            return records
            
        # Try all known formats, use the one that yields the most hits
        best_records = []
        
        for provider_key, rules in self.patterns.items():
            extracted = []
            
            # Find date
            date_match = re.search(rules["date"], text, re.IGNORECASE)
            bill_date = self._standardize_date(date_match.group(1)) if date_match else "Unknown Date"
            
            # Find Electricity
            if "electricity_kwh" in rules:
                e_match = re.search(rules["electricity_kwh"], text, re.IGNORECASE)
                if e_match:
                    extracted.append({
                        "activity_date": bill_date,
                        "category": "Energy",
                        "activity": f"{rules['provider']} Electricity Bill",
                        "value": self._clean_number(e_match.group(1)),
                        "unit": "kWh"
                    })
                    
            # Find Gas
            if "gas_therms" in rules:
                g_match = re.search(rules["gas_therms"], text, re.IGNORECASE)
                if g_match:
                    extracted.append({
                        "activity_date": bill_date,
                        "category": "Energy",
                        "activity": f"{rules['provider']} Gas Bill",
                        "value": self._clean_number(g_match.group(1)),
                        "unit": "therms"
                    })
                    
            # Find Water
            if "water_gal" in rules:
                w_match = re.search(rules["water_gal"], text, re.IGNORECASE)
                if w_match:
                    extracted.append({
                        "activity_date": bill_date,
                        "category": "Water",
                        "activity": f"{rules['provider']} Water Bill",
                        "value": self._clean_number(w_match.group(1)),
                        "unit": "gallons"
                    })
                    
            if len(extracted) > len(best_records):
                best_records = extracted
                
        return best_records
