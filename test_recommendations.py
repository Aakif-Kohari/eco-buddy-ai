import pytest
from recommendations import generate_recommendations

CONTRIBUTORS = {
    "Transport": 1533,
    "Electricity": 2460,
    "Diet": 1800,
    "Flights": 500
}


def test_returns_insight_and_recommendations():
    insight, recommendations = generate_recommendations(
        transport="Car", electricity=300, diet="Non-Vegetarian",
        flights=4, contributors=CONTRIBUTORS
    )
    assert isinstance(insight, str)
    assert len(insight) > 0
    assert isinstance(recommendations, list)
    assert len(recommendations) > 0


def test_insight_mentions_biggest_contributor():
    insight, _ = generate_recommendations(
        transport="Car", electricity=300, diet="Non-Vegetarian",
        flights=4, contributors=CONTRIBUTORS
    )
    assert "Electricity" in insight


def test_car_transport_gives_priority_recommendation():
    _, recommendations = generate_recommendations(
        transport="Car", electricity=100, diet="Vegetarian",
        flights=0, contributors=CONTRIBUTORS
    )
    combined = " ".join(recommendations)
    assert "Priority" in combined


def test_walking_transport_no_priority():
    _, recommendations = generate_recommendations(
        transport="Walking", electricity=100, diet="Vegetarian",
        flights=0, contributors={"Transport": 0, "Electricity": 984, "Diet": 1000, "Flights": 0}
    )
    combined = " ".join(recommendations)
    assert "Excellent" in combined or "walking" in combined.lower()


def test_high_electricity_recommends_led():
    _, recommendations = generate_recommendations(
        transport="Car", electricity=500, diet="Vegetarian",
        flights=0, contributors=CONTRIBUTORS
    )
    combined = " ".join(recommendations)
    assert "LED" in combined or "energy" in combined.lower()


def test_high_flights_recommends_offsets():
    _, recommendations = generate_recommendations(
        transport="Car", electricity=200, diet="Vegetarian",
        flights=10, contributors=CONTRIBUTORS
    )
    combined = " ".join(recommendations)
    assert "offset" in combined.lower()


def test_non_vegetarian_diet_recommends_plant_swaps():
    _, recommendations = generate_recommendations(
        transport="Bike", electricity=100, diet="Non-Vegetarian",
        flights=0, contributors={"Transport": 0, "Electricity": 984, "Diet": 1800, "Flights": 0}
    )
    combined = " ".join(recommendations)
    assert "plant" in combined.lower() or "meat" in combined.lower()


def test_recommendations_not_empty_for_all_green_profile():
    _, recommendations = generate_recommendations(
        transport="Walking", electricity=50, diet="Vegetarian",
        flights=0, contributors={"Transport": 0, "Electricity": 492, "Diet": 1000, "Flights": 0}
    )
    assert len(recommendations) > 0
