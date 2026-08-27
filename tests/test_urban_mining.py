"""
Unit tests for Urban Mining Calculator and Critical Mineral DB.
"""

import pytest
from urban_mining_calculator import UrbanMiningCalculator
from critical_mineral_db import CriticalMineralDB


def test_db_retrieval():
    db = CriticalMineralDB()
    profile = db.get_device_profile("smartphone")
    assert profile is not None
    assert profile["name"] == "Smartphone"
    assert "lithium" in profile["minerals"]

    assert db.get_device_display_name("smartwatch") == "Smartwatch"


def test_calculator_add_device():
    calc = UrbanMiningCalculator()
    success = calc.add_device("laptop", 2)
    assert success is True
    assert len(calc.logged_devices) == 1
    assert calc.logged_devices[0]["quantity"] == 2

    fail = calc.add_device("nonexistent_device", 1)
    assert fail is False


def test_calculator_recovery_value():
    calc = UrbanMiningCalculator()
    # 1 smartphone
    calc.add_device("smartphone", 1)
    result = calc.calculate_recovery_value()

    assert result["total_devices"] == 1
    assert "gold" in result["recovered_minerals_g"]
    # Smartphone gold: 0.030g * 95% recovery = 0.0285g
    assert abs(result["recovered_minerals_g"]["gold"] - 0.0285) < 0.001
    assert result["total_carbon_avoided_kg"] > 0.0


def test_calculator_multiple_devices():
    calc = UrbanMiningCalculator()
    calc.add_device("smartphone", 1)
    calc.add_device("laptop", 1)

    result = calc.calculate_recovery_value()
    assert result["total_devices"] == 2
    # Should have combined minerals
    assert (
        result["recovered_minerals_g"]["copper"] > 15.0
    )  # 15 from phone + 25 from laptop (adjusted for recovery)


def test_urban_mining_score():
    calc = UrbanMiningCalculator()
    calc.add_device("laptop", 10)  # High quantity for higher score

    result = calc.calculate_recovery_value()
    assert 0 <= result["urban_mining_score"] <= 100


def test_recycling_recommendations():
    calc = UrbanMiningCalculator()
    recs_empty = calc.get_recycling_recommendations()
    assert "Log some devices" in recs_empty[0]

    calc.add_device("smartphone", 1)
    recs_full = calc.get_recycling_recommendations()
    assert any("Certified Recyclers" in r for r in recs_full)
    assert any("Battery Safety" in r for r in recs_full)
