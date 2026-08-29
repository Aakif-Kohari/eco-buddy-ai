"""
Unit tests for P2P Energy Trading and Microgrid Simulator.
"""

import pytest
from p2p_energy_trading import P2PEnergyTrading
from microgrid_simulator import MicrogridSimulator


def test_microgrid_hourly_profile():
    sim = MicrogridSimulator(num_households=2)
    # Noon should have high generation
    profile_noon = sim.generate_hourly_profile(12)
    assert profile_noon["hour"] == 12
    assert profile_noon["total_generation_kw"] > 0.0

    # Midnight should have zero solar generation
    profile_midnight = sim.generate_hourly_profile(0)
    assert profile_midnight["total_generation_kw"] == 0.0
    assert profile_midnight["total_demand_kw"] > 0.0


def test_microgrid_grid_independence():
    sim = MicrogridSimulator(num_households=2)
    daily_profile = sim.simulate_full_day()
    independence = sim.calculate_grid_independence(daily_profile)

    # Should be between 0 and 100
    assert 0.0 <= independence <= 100.0


def test_p2p_trading_execution():
    trader = P2PEnergyTrading(grid_import_price=0.30, p2p_price=0.15)

    # Mock a specific hour profile manually to guarantee a trade
    mock_hour_profile = {
        "hour": 12,
        "total_generation_kw": 5.0,
        "total_demand_kw": 3.0,
        "net_grid_import_kw": 0.0,
        "net_grid_export_kw": 2.0,
        "household_details": {
            "house_1": {
                "generation_kw": 5.0,
                "demand_kw": 1.0,
                "net_kw": 4.0,
            },  # Supplier
            "house_2": {
                "generation_kw": 0.0,
                "demand_kw": 2.0,
                "net_kw": -2.0,
            },  # Consumer
        },
    }

    result = trader.execute_hourly_trades(mock_hour_profile)

    assert result["hour"] == 12
    assert result["total_p2p_volume_kwh"] == 2.0  # Matches consumer deficit
    assert result["money_saved_usd"] == 2.0 * (0.30 - 0.15)  # 0.30
    assert result["carbon_avoided_kg"] == 2.0 * 0.4  # 0.8
    assert len(result["transactions"]) == 1
    assert result["transactions"][0]["supplier_id"] == "house_1"
    assert result["transactions"][0]["consumer_id"] == "house_2"


def test_p2p_full_day_simulation():
    trader = P2PEnergyTrading(grid_import_price=0.25, p2p_price=0.15)
    result = trader.simulate_and_trade_full_day()

    assert "daily_profile" in result
    assert "hourly_trades" in result
    assert "summary" in result
    assert result["summary"]["total_p2p_volume_kwh"] >= 0.0
    assert result["summary"]["grid_independence_pct"] >= 0.0
