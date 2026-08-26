import pytest
from src.lifestyle.green_transportation_planner import calculate_route, get_carbon_rating

def test_calculate_route():
    # Gasoline Car (car_solo), 10km one-way
    # 10km * 0.171 = 1.71 kg CO2
    impact = calculate_route("car_solo", 10.0)
    assert impact["co2_kg"] == 1.71
    assert impact["distance_km"] == 10.0
    
    # Carpool (2) -> halved emissions approx (0.086 * 10 = 0.86)
    impact_carpool = calculate_route("carpool", 10.0)
    assert impact_carpool["co2_kg"] == 0.86
    
    # Bicycle -> 0 emissions
    impact_bike = calculate_route("bicycle", 10.0)
    assert impact_bike["co2_kg"] == 0.0

def test_get_carbon_rating():
    icon, label, color = get_carbon_rating(0.0, 10.0)
    assert label == "Zero Carbon"
    assert color == "#22c55e"
    
    icon, label, color = get_carbon_rating(4.0, 10.0) # 0.4 intensity
    assert label == "High"
    assert color == "#ef4444"
