from contamination_simulator import check_contamination, get_contamination_penalty
from waste_analytics import process_waste_log


def test_check_contamination_pizza_box():
    is_contaminated, reason = check_contamination("Pizza Box", "recycling")
    assert is_contaminated is True
    assert "Grease" in reason


def test_check_contamination_clean_bottle():
    is_contaminated, reason = check_contamination("Plastic Bottle", "recycling")
    assert is_contaminated is False
    assert reason == ""


def test_get_contamination_penalty():
    assert get_contamination_penalty(0.02) == 0.0
    assert get_contamination_penalty(0.10) == 15.0
    assert get_contamination_penalty(0.25) == 40.0
    assert get_contamination_penalty(0.50) == 80.0


def test_process_waste_log_with_contamination():
    items = [
        {"name": "Plastic Bottle", "weight_kg": 1.0, "stream": "recycling"},
        {"name": "Pizza Box", "weight_kg": 2.0, "stream": "recycling"},
        {"name": "Food Scraps", "weight_kg": 1.0, "stream": "compost"},
    ]
    analytics = process_waste_log(items)

    assert analytics["total_weight_kg"] == 4.0
    assert analytics["contaminated_weight_kg"] == 2.0
    assert analytics["stream_breakdown"]["landfill"] == 2.0  # Pizza box diverted
    assert analytics["stream_breakdown"]["recycling"] == 1.0
    assert len(analytics["contamination_warnings"]) == 1
    assert analytics["recycling_efficiency_score"] < 100.0


def test_process_waste_log_clean():
    items = [
        {"name": "Plastic Bottle", "weight_kg": 1.0, "stream": "recycling"},
        {"name": "Apple Core", "weight_kg": 0.5, "stream": "compost"},
    ]
    analytics = process_waste_log(items)
    assert analytics["contaminated_weight_kg"] == 0.0
    assert analytics["recycling_efficiency_score"] == 100.0
