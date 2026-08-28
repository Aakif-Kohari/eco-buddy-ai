"""
Unit tests for Noise Pollution Tracker and Green Space Health Impact.
"""

import pytest
from src.utils.noise_pollution_tracker import NoisePollutionTracker
from src.utils.green_space_health_impact import GreenSpaceHealthImpact


def test_calculate_daily_exposure():
    tracker = NoisePollutionTracker()
    allocation = {"dense_urban": 4.0, "indoor_home": 8.0, "park_green": 2.0}
    # Total hours = 14. Weighted sum = (75*4) + (40*8) + (45*2) = 300 + 320 + 90 = 710
    # Average = 710 / 14 = 50.7 dB

    result = tracker.calculate_daily_exposure(allocation)
    assert result["total_hours_logged"] == 14.0
    assert result["average_daily_db"] == 50.7
    assert result["risk_level"] == "Moderate"
    assert 0 <= result["health_impact_score"] <= 100


def test_calculate_daily_exposure_empty():
    tracker = NoisePollutionTracker()
    result = tracker.calculate_daily_exposure({})
    assert result["total_hours_logged"] == 24.0


def test_green_space_mitigation():
    analyzer = GreenSpaceHealthImpact()

    # High noise impact, good green space habits
    result = analyzer.calculate_mitigation(
        noise_impact_score=80.0, weekly_park_visits=4, home_tree_canopy_pct=40.0
    )

    assert result["baseline_noise_impact"] == 80.0
    assert result["park_mitigation_points"] == 12.0  # 4 * 3.0
    assert result["canopy_mitigation_points"] == 6.0  # (40/100) * 15.0
    assert result["total_mitigation_points"] == 18.0
    assert result["adjusted_health_impact_score"] == 62.0
    assert result["sleep_quality_improvement"] == "Moderate"


def test_green_space_mitigation_maxed():
    analyzer = GreenSpaceHealthImpact()

    # Low noise impact, excellent green space habits
    result = analyzer.calculate_mitigation(
        noise_impact_score=20.0, weekly_park_visits=7, home_tree_canopy_pct=80.0
    )

    # Mitigation would be 21 + 12 = 33, but capped at baseline 20.0
    assert result["total_mitigation_points"] == 20.0
    assert result["adjusted_health_impact_score"] == 0.0
    assert "excellent" in result["recommendations"][0].lower()


def test_recommendations_generation():
    analyzer = GreenSpaceHealthImpact()
    recs = analyzer._generate_recommendations(
        visits=1, canopy_pct=10, adjusted_score=60
    )

    assert any("2 park visits" in r for r in recs)
    assert any("indoor plants" in r for r in recs)
    assert any("noise-canceling" in r for r in recs)
