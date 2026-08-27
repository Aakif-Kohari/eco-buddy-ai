"""
Unit tests for Relocation Impact Analyzer and City Environmental DB.
"""

import pytest
from relocation_impact_analyzer import RelocationImpactAnalyzer
from city_environmental_db import CityEnvironmentalDB


def test_city_db_retrieval():
    db = CityEnvironmentalDB()
    profile = db.get_city_profile("new_york")
    assert profile is not None
    assert profile["name"] == "New York, USA"
    assert profile["grid_intensity"] == 0.28

    # Test case insensitivity and spacing
    profile_mixed = db.get_city_profile("San Francisco")
    assert profile_mixed is not None
    assert profile_mixed["name"] == "San Francisco, USA"


def test_city_db_missing():
    db = CityEnvironmentalDB()
    assert db.get_city_profile("unknown_city_xyz") is None


def test_relocation_analyzer_valid_cities():
    analyzer = RelocationImpactAnalyzer()
    result = analyzer.calculate_differential_footprint("new_york", "london")

    assert result is not None
    assert result["current_city"] == "New York, USA"
    assert result["target_city"] == "London, UK"
    assert "annual_delta_kg_co2e" in result
    assert "breakdown" in result
    assert "recommendations" in result


def test_relocation_analyzer_missing_city():
    analyzer = RelocationImpactAnalyzer()
    result = analyzer.calculate_differential_footprint("new_york", "mars_city")
    assert result is None


def test_relocation_analyzer_delta_calculation():
    analyzer = RelocationImpactAnalyzer()
    # Moving from high grid intensity (Sydney) to low (Toronto) should yield negative grid delta
    result = analyzer.calculate_differential_footprint("sydney", "toronto")
    assert result["breakdown"]["grid_intensity_delta_kg"] < 0

    # Moving from high transit (Tokyo) to low transit (Sydney) should yield positive transport delta
    result2 = analyzer.calculate_differential_footprint("tokyo", "sydney")
    assert result2["breakdown"]["transport_delta_kg"] > 0
