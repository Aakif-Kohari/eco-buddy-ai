"""Tests for calculators."""
from src.decision_engine.calculator import ImpactCalculator, FinancialCalculator
from src.decision_engine.models import ScenarioInputs, TransportMode, EnergySource, DietType

def test_impact_calculator_baseline():
    inputs = ScenarioInputs()
    impact = ImpactCalculator.calculate(inputs)
    assert impact.carbon_emissions_kg_co2e_per_year > 0
    assert impact.energy_consumption_kwh_per_year == 3600 # 300 * 12
    assert impact.sustainability_score > 0

def test_impact_calculator_ev_upgrade():
    base = ScenarioInputs()
    alt = ScenarioInputs()
    alt.transport.primary_mode = TransportMode.EV_CAR
    
    base_imp = ImpactCalculator.calculate(base)
    alt_imp = ImpactCalculator.calculate(alt)
    
    # EV should have lower CO2 than ICE car for default distances
    assert alt_imp.transport_co2e < base_imp.transport_co2e

def test_financial_calculator_solar():
    base = ScenarioInputs()
    alt = ScenarioInputs()
    alt.energy.primary_source = EnergySource.SOLAR_ROOF
    
    base_fin = FinancialCalculator.calculate(base)
    alt_fin = FinancialCalculator.calculate(alt)
    
    assert alt_fin.implementation_cost_upfront > base_fin.implementation_cost_upfront
    assert alt_fin.yearly_recurring_cost < base_fin.yearly_recurring_cost
