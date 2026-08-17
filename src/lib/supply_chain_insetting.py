"""
Scope 3 Supply Chain Carbon Insetting & Decarbonization Planner for EcoBuddy AI
Enables upstream/downstream Scope 3 category footprint calculations,
direct supplier intervention ROI modeling, and verified insetting tracking.
"""

from typing import Dict, List, Any, Optional

SCOPE3_CATEGORIES = {
    "cat1_purchased_goods": {"name": "Cat 1: Purchased Goods & Services", "default_factor_kg_per_dollar": 0.42},
    "cat2_capital_goods": {"name": "Cat 2: Capital Goods", "default_factor_kg_per_dollar": 0.35},
    "cat4_upstream_transport": {"name": "Cat 4: Upstream Transportation & Distribution", "default_factor_kg_per_tkm": 0.12},
    "cat6_business_travel": {"name": "Cat 6: Business Travel", "default_factor_kg_per_dollar": 0.28},
    "cat9_downstream_transport": {"name": "Cat 9: Downstream Transportation & Distribution", "default_factor_kg_per_tkm": 0.14}
}

INSETTING_INTERVENTIONS = {
    "regenerative_agriculture": {
        "title": "Regenerative Agriculture & Soil Carbon Insetting",
        "cost_per_ton_co2": 25.0,
        "co_benefits": ["Biodiversity restoration", "Water retention", "Farmer livelihood improvement"]
    },
    "supplier_renewable_ppa": {
        "title": "Direct Supplier Clean Power PPA Co-Investment",
        "cost_per_ton_co2": 18.0,
        "co_benefits": ["Grid decarbonization", "Long-term fixed energy costs"]
    },
    "route_intermodal_shift": {
        "title": "Freight Modal Shift (Road to Rail/Electrified Fleet)",
        "cost_per_ton_co2": 32.0,
        "co_benefits": ["Particulate pollution reduction", "Congestion relief"]
    },
    "bio_based_packaging_feedstock": {
        "title": "Sustainable Bio-Feedstock Packaging Transition",
        "cost_per_ton_co2": 40.0,
        "co_benefits": ["Microplastic elimination", "Circular economy compliance"]
    }
}


class SupplyChainInsettingPlanner:
    """Calculates Scope 3 footprint across supply chain tiers and models insetting project returns."""

    def __init__(self, categories: Optional[Dict[str, Dict[str, Any]]] = None):
        self.categories = categories or SCOPE3_CATEGORIES

    def calculate_category_emissions(
        self,
        category_key: str,
        activity_amount: float,
        supplier_primary_data_discount_pct: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates Scope 3 emissions for an activity or spend amount.
        """
        cat_info = self.categories.get(category_key, {"name": category_key, "default_factor_kg_per_dollar": 0.35})
        
        factor = cat_info.get("default_factor_kg_per_dollar") or cat_info.get("default_factor_kg_per_tkm", 0.35)
        raw_emissions_kg = activity_amount * factor
        
        discount = min(max(supplier_primary_data_discount_pct / 100.0, 0.0), 0.70)
        adjusted_emissions_kg = raw_emissions_kg * (1.0 - discount)
        adjusted_tonnes_co2 = round(adjusted_emissions_kg / 1000.0, 3)

        return {
            "category": cat_info["name"],
            "activity_amount": activity_amount,
            "emission_factor": factor,
            "raw_emissions_tco2e": round(raw_emissions_kg / 1000.0, 3),
            "adjusted_emissions_tco2e": adjusted_tonnes_co2,
            "primary_data_confidence": "High (Direct Supplier Audited)" if discount > 0 else "Screening (Spend-based Average)"
        }

    def evaluate_insetting_intervention(
        self,
        intervention_type: str,
        target_abatement_tonnes: float,
        co_investment_budget: float
    ) -> Dict[str, Any]:
        """
        Models carbon insetting feasibility, abatement potential, and investment efficiency.
        """
        project = INSETTING_INTERVENTIONS.get(intervention_type, {
            "title": intervention_type.replace("_", " ").title(),
            "cost_per_ton_co2": 30.0,
            "co_benefits": ["Ecosystem protection"]
        })

        total_project_cost = round(target_abatement_tonnes * project["cost_per_ton_co2"], 2)
        achievable_tonnes = round(co_investment_budget / project["cost_per_ton_co2"], 2) if co_investment_budget > 0 else 0.0
        
        funding_gap = max(round(total_project_cost - co_investment_budget, 2), 0.0)

        return {
            "intervention_name": project["title"],
            "cost_per_ton_co2": project["cost_per_ton_co2"],
            "target_abatement_tonnes": target_abatement_tonnes,
            "total_estimated_project_cost_usd": total_project_cost,
            "achievable_abatement_with_budget_tco2e": achievable_tonnes,
            "funding_gap_usd": funding_gap,
            "co_benefits": project["co_benefits"],
            "is_fully_funded": co_investment_budget >= total_project_cost
        }
