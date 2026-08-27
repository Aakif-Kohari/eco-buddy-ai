"""Tests for models."""
from src.decision_engine.models import ScenarioInputs, TransportInputs, EnvironmentalImpact, FinancialImpact, TransportMode

def test_environmental_impact_subtraction():
    e1 = EnvironmentalImpact(carbon_emissions_kg_co2e_per_year=1000)
    e2 = EnvironmentalImpact(carbon_emissions_kg_co2e_per_year=200)
    diff = e1 - e2
    assert diff.carbon_emissions_kg_co2e_per_year == 800
    
def test_financial_impact_projections():
    f = FinancialImpact(implementation_cost_upfront=5000, yearly_recurring_cost=1000)
    total_5_years = f.calculate_total_cost_over_years(5.0, inflation_rate=0.0)
    assert total_5_years == 10000.0  # 5000 + (1000 * 5)
    
    total_inflated = f.calculate_total_cost_over_years(2.0, inflation_rate=0.10)
    # y1 = 1000
    # y2 = 1100
    # total = 5000 + 1000 + 1100 = 7100
    assert total_inflated == 7100.0
