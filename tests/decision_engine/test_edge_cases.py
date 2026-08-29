"""Tests for edge cases and input validation."""
import pytest
from src.decision_engine.calculator import ImpactCalculator, FinancialCalculator
from src.decision_engine.models import ScenarioInputs, TransportMode, WaterInputs

def test_negative_inputs_clamped():
    inputs = ScenarioInputs()
    inputs.transport.weekly_commute_km = -100  # Invalid
    inputs.transport.car_efficiency_mpg = 0.001 # Extremely low
    inputs.water.shower_duration_minutes = -5 # Invalid
    
    # Python dataclasses don't auto-validate unless we add __post_init__ or property setters.
    # If the calculator clamps them or handles them, we test that.
    
    impact = ImpactCalculator.calculate(inputs)
    
    # We should ensure water footprint isn't negative
    assert impact.water_footprint_liters_per_year >= 0
    
def test_zero_values():
    inputs = ScenarioInputs()
    inputs.transport.weekly_commute_km = 0
    inputs.transport.weekend_travel_km = 0
    inputs.transport.flights_per_year = 0
    
    impact = ImpactCalculator.calculate(inputs)
    # Transport CO2 should just be 0 for ICE if no miles driven, and 0 flights
    assert impact.transport_co2e == 0.0
