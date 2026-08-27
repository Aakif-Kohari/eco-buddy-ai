import pytest
from green_transportation_planner import calculate_route, get_carbon_rating

def test_calculate_route():
    # Solo car commute, 10km distance, sunny weather
    # 10km * 0.171 = 1.71 kg CO2
    res = calculate_route("car_solo", 10.0)
    assert res["co2_kg"] == 1.71
    assert res["speed_kmh"] == 40.0
    
    # Bicycle, 10km, sunny weather -> 0 emissions
    res_bike = calculate_route("bicycle", 10.0)
    assert res_bike["co2_kg"] == 0.0
    assert res_bike["speed_kmh"] == 15.0

    # Bicycle, 10km, rainy weather -> 15 * 0.6 = 9.0 speed_kmh
    res_rainy_bike = calculate_route("bicycle", 10.0, weather="rainy")
    assert res_rainy_bike["speed_kmh"] == 9.0

def test_get_carbon_rating():
    # Zero Carbon
    emoji, label, color = get_carbon_rating(0.0, 10.0)
    assert emoji == "🌟"
    assert label == "Zero Carbon"
    
    # High Carbon (intensity >= 0.15)
    # co2_kg = 1.71, distance = 10.0 -> intensity = 0.171
    emoji_high, label_high, color_high = get_carbon_rating(1.71, 10.0)
    assert emoji_high == "🔴"
    assert label_high == "High"
