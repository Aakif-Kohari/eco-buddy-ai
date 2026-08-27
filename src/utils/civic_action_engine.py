import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class CivicActionEngine:
    def __init__(self):
        # Mocked database of active bills for the MVP
        self.active_bills = [
            {
                "bill_id": "hr-4040",
                "title": "Clean Energy Rebate Expansion Act",
                "level": "Federal",
                "summary": "Expands tax rebates for EV purchases and home solar panel installations, increasing the maximum rebate limit.",
                "financial_impact": {
                    "ev_rebate_usd": 7500.0,
                    "solar_rebate_pct": 0.30
                },
                "carbon_impact": {
                    "ev_co2_savings_kg_per_year": 4600.0,
                    "solar_co2_savings_kg_per_year": 3500.0
                }
            },
            {
                "bill_id": "sb-110",
                "title": "Local Carbon Fee and Dividend",
                "level": "State",
                "summary": "Implements a carbon fee on fossil fuels and returns the revenue as a dividend to households.",
                "financial_impact": {
                    "dividend_usd": 400.0,
                    "gas_price_increase_pct": 0.15
                },
                "carbon_impact": {
                    "general_co2_savings_pct": 0.10
                }
            },
            {
                "bill_id": "cb-90",
                "title": "Municipal Composting Mandate",
                "level": "Local",
                "summary": "Requires municipal composting and provides free bins to reduce organic waste in landfills.",
                "financial_impact": {
                    "trash_fee_reduction_usd": 120.0
                },
                "carbon_impact": {
                    "waste_co2_savings_kg_per_year": 300.0
                }
            }
        ]

    def get_active_bills(self) -> List[Dict[str, Any]]:
        """Mock Civic API fetch for active environmental bills."""
        return self.active_bills
        
    def evaluate_user_impact(self, user_id: int, user_footprint: Dict[str, Any], bill: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates financial and carbon diff based on bill metadata and user footprint."""
        financial_diff_usd = 0.0
        carbon_diff_kg = 0.0
        
        # Example naive evaluation logic
        if bill["bill_id"] == "hr-4040":
            if user_footprint.get("owns_ev", False) is False:
                financial_diff_usd += bill["financial_impact"]["ev_rebate_usd"]
                carbon_diff_kg += bill["carbon_impact"]["ev_co2_savings_kg_per_year"]
                
        elif bill["bill_id"] == "sb-110":
            financial_diff_usd += bill["financial_impact"]["dividend_usd"]
            # Estimate extra cost if user drives a gas car
            gas_spend = user_footprint.get("monthly_gas_spend_usd", 100.0) * 12
            financial_diff_usd -= (gas_spend * bill["financial_impact"]["gas_price_increase_pct"])
            
            base_emissions = user_footprint.get("total_emissions_kg", 15000.0)
            carbon_diff_kg += base_emissions * bill["carbon_impact"]["general_co2_savings_pct"]
            
        elif bill["bill_id"] == "cb-90":
            if user_footprint.get("composts", False) is False:
                financial_diff_usd += bill["financial_impact"]["trash_fee_reduction_usd"]
                carbon_diff_kg += bill["carbon_impact"]["waste_co2_savings_kg_per_year"]
                
        return {
            "financial_savings_usd": round(financial_diff_usd, 2),
            "carbon_savings_kg": round(carbon_diff_kg, 2)
        }

    def generate_advocacy_prompt(self, user_name: str, bill_title: str, savings_usd: float, savings_kg: float) -> str:
        """Generates an advocacy email prompt for the user's representative."""
        return f"""Dear Representative,

My name is {user_name} and I am a constituent in your district. I am writing to urge your support for the {bill_title}.

As someone actively trying to reduce my environmental impact, I've calculated that this legislation would directly help me save approximately ${savings_usd:,.2f} while enabling me to reduce my carbon footprint by {savings_kg:,.0f} kg of CO2 annually. 

Supporting this bill is not just an environmental imperative; it makes economic sense for households like mine. I respectfully ask you to co-sponsor and vote in favor of this critical legislation.

Sincerely,
{user_name}
"""
