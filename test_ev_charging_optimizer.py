import pytest

from config import HOURS_PER_DAY
from ev_charging_optimizer import (
    generate_charging_recommendations,
    optimize_charging_schedule,
)
from grid_intensity_simulator import (
    generate_grid_intensity_profile,
    generate_pricing_profile,
)


def test_optimize_charging_schedule_basic():
    grid_profile = generate_grid_intensity_profile("mixed")
    pricing_profile = generate_pricing_profile("time_of_use")

    result = optimize_charging_schedule(
        battery_capacity_kwh=60.0,
        current_soc_pct=20.0,
        target_soc_pct=80.0,
        charging_rate_kw=7.4,
        grid_profile=grid_profile,
        pricing_profile=pricing_profile,
    )

    assert result["energy_needed_kwh"] == 36.0
    assert result["hours_needed"] == 5
    assert len(result["optimal_hours"]) == 5
    assert len(result["schedule"]) == HOURS_PER_DAY
    assert sum(result["schedule"]) == 5 * 7.4
    assert result["carbon_savings_kg"] >= 0
    assert result["cost_savings_usd"] >= 0


def test_optimize_charging_schedule_already_full():
    grid_profile = generate_grid_intensity_profile("mixed")
    pricing_profile = generate_pricing_profile("flat")

    with pytest.raises(ValueError, match="Target SOC must be greater than current SOC"):
        optimize_charging_schedule(60.0, 80.0, 50.0, 7.4, grid_profile, pricing_profile)


def test_optimize_charging_schedule_exceeds_24h():
    grid_profile = generate_grid_intensity_profile("mixed")
    pricing_profile = generate_pricing_profile("flat")

    with pytest.raises(ValueError, match="Charging requirement exceeds 24 hours"):
        optimize_charging_schedule(
            100.0, 10.0, 90.0, 1.0, grid_profile, pricing_profile
        )


def test_generate_charging_recommendations():
    result = {
        "carbon_savings_kg": 5.2,
        "cost_savings_usd": 1.50,
        "optimal_hours": [2, 3, 4],
    }
    recs = generate_charging_recommendations(result)
    assert any("5.2" in r for r in recs)
    assert any("1.5" in r for r in recs)
    assert any("2:00" in r for r in recs)
