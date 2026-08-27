import pytest
from pages.Green_Transportation_Planner import calculate_commute_emissions, generate_green_score, get_recommendations

def test_calculate_commute_emissions():
    # Gasoline Car, 10km one-way, 5 days/week, 1 passenger
    # 20km daily * 0.19 = 3.8 kg daily
    impact = calculate_commute_emissions("Gasoline Car", 10.0, 5, 1)
    assert impact["Daily"] == 3.8
    assert impact["Weekly"] == 19.0
    assert impact["Monthly"] == pytest.approx(19.0 * 4.33)
    assert impact["Yearly"] == pytest.approx(19.0 * 52)
    
    # Carpool: 2 passengers -> halved emissions
    impact_carpool = calculate_commute_emissions("Gasoline Car", 10.0, 5, 2)
    assert impact_carpool["Daily"] == 1.9
    
    # Bicycle -> 0 emissions
    impact_bike = calculate_commute_emissions("Bicycle", 10.0, 5, 1)
    assert impact_bike["Daily"] == 0.0

def test_generate_green_score():
    score, label = generate_green_score(0.0)
    assert score == 100
    assert "Perfect" in label
    
    score, label = generate_green_score(400.0)
    assert score == 90
    
    score, label = generate_green_score(5000.0)
    assert score == 10

def test_get_recommendations():
    # Short drive
    recs = get_recommendations("Gasoline Car", 2.0)
    assert any("Walking or cycling" in r for r in recs)
    
    # SUV
    recs = get_recommendations("SUV/Truck", 20.0)
    assert any("Hybrid or EV" in r for r in recs)
    assert any("carpool" in r for r in recs)
    
    # Public transit short
    recs = get_recommendations("Public Transit (Bus/Train)", 3.0)
    assert any("bicycle or e-bike" in r for r in recs)
