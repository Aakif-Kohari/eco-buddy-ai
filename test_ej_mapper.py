"""
Unit tests for Environmental Justice Mapper and Local Air Quality Tracker.
"""

import pytest
from environmental_justice_mapper import EnvironmentalJusticeMapper
from local_air_quality_tracker import LocalAirQualityTracker


def test_mapper_retrieval():
    mapper = EnvironmentalJusticeMapper()
    profile = mapper.get_region_profile("77001")

    assert profile is not None
    assert profile["region_name"] == "Downtown Houston, TX"
    assert profile["ej_index"] == 75
    assert (
        mapper.assess_vulnerability_level(75)
        == "High Vulnerability (Priority for Mitigation)"
    )
    assert mapper.assess_vulnerability_level(20) == "Low Vulnerability"


def test_tracker_activity_impact():
    mapper = EnvironmentalJusticeMapper()
    tracker = LocalAirQualityTracker(mapper)

    # 100 miles of ICE car
    impact = tracker.calculate_activity_impact("10001", "ice_car_mile", 100.0)

    assert impact["region_name"] == "Manhattan, NY"
    assert impact["activity"] == "Ice Car Mile"
    assert impact["added_pm25_g"] == 5.0  # 0.05 * 100
    assert impact["added_nox_g"] == 30.0  # 0.30 * 100
    assert impact["baseline_ej_index"] == 45


def test_tracker_unknown_region():
    mapper = EnvironmentalJusticeMapper()
    tracker = LocalAirQualityTracker(mapper)

    with pytest.raises(ValueError, match="Unknown zip code"):
        tracker.calculate_activity_impact("00000", "ice_car_mile", 10.0)


def test_tracker_unknown_activity():
    mapper = EnvironmentalJusticeMapper()
    tracker = LocalAirQualityTracker(mapper)

    with pytest.raises(ValueError, match="Unknown activity type"):
        tracker.calculate_activity_impact("90210", "magic_carpet_ride", 10.0)


def test_mitigation_tips_generation():
    mapper = EnvironmentalJusticeMapper()
    tracker = LocalAirQualityTracker(mapper)

    # High EJ index + car activity
    impact = tracker.calculate_activity_impact("77001", "ice_car_mile", 50.0)
    tips = tracker.generate_mitigation_tips(impact)

    assert any("Advocacy" in tip for tip in tips)
    assert any("Mobility" in tip for tip in tips)
    assert any("Greening" in tip for tip in tips)
