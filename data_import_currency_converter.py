"""Currency normalizer for imported sustainability costs.

Normalizes cost inputs across multiple global currencies to a standard
base (USD) for unified financial tracking of eco activities.
"""

from typing import Dict, List, Any

# Static exchange rates for demonstration (In production, use an API)
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 1.10,
    "GBP": 1.25,
    "JPY": 0.0065,
    "AUD": 0.65,
    "CAD": 0.73,
    "INR": 0.012
}

def normalize_costs(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Scan records for 'cost' and 'currency' fields and normalize to USD."""
    for r in records:
        cost = r.get("cost")
        currency = r.get("currency", "USD").upper()
        
        if cost is not None:
            try:
                f_cost = float(str(cost).replace(",", ""))
                
                if currency != "USD":
                    rate = EXCHANGE_RATES.get(currency, 1.0)
                    r["cost_usd"] = f_cost * rate
                    if "_warnings" not in r:
                        r["_warnings"] = []
                    r["_warnings"].append(f"Normalized cost from {currency} to USD.")
                else:
                    r["cost_usd"] = f_cost
                    
            except ValueError:
                r["cost_usd"] = None
                
    return records
