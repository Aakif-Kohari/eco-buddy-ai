import pytest
from marketplace import (
    calculate_trip_emissions, calculate_recurring_trip_emissions, compare_transit_modes,
    calculate_offset_cost, validate_offset_transaction, calculate_net_emissions, calculate_net_zero_progress
)

def test_calculate_trip_emissions():
    assert calculate_trip_emissions(10, "Single-occupancy car") == 1.92
    assert calculate_trip_emissions(10, "Bus") == 1.05
    assert calculate_trip_emissions(10, "Cycling") == 0.0
    
    # Test carpool scaling
    assert calculate_trip_emissions(10, "Single-occupancy car", 2) == 0.96
    
    with pytest.raises(ValueError):
        calculate_trip_emissions(-10, "Bus")
    with pytest.raises(ValueError):
        calculate_trip_emissions(10, "Teleporter")

def test_calculate_recurring_trip_emissions():
    res = calculate_recurring_trip_emissions(10.0, 5)
    assert res["weekly"] == 50.0
    assert res["annual"] == 2600.0

def test_compare_transit_modes():
    comps = compare_transit_modes(10)
    assert len(comps) == 9 # All modes
    assert comps[0]["mode"] in ["Walking", "Cycling"] # Should be zero
    assert comps[-1]["mode"] == "Flight" # Highest

def test_calculate_offset_cost():
    assert calculate_offset_cost(2.0, 15.0) == 30.0
    with pytest.raises(ValueError):
        calculate_offset_cost(-1.0, 15.0)

def test_validate_offset_transaction():
    valid, msg = validate_offset_transaction(5.0, 10.0)
    assert valid is True
    
    valid, msg = validate_offset_transaction(15.0, 10.0)
    assert valid is False
    
    valid, msg = validate_offset_transaction(-1.0, 10.0)
    assert valid is False

def test_calculate_net_emissions():
    assert calculate_net_emissions(100.0, 20.0) == 80.0
    assert calculate_net_emissions(100.0, 150.0) == 0.0

def test_calculate_net_zero_progress():
    assert calculate_net_zero_progress(100.0, 20.0) == 20.0
    assert calculate_net_zero_progress(100.0, 150.0) == 100.0
    assert calculate_net_zero_progress(0.0, 10.0) == 100.0
