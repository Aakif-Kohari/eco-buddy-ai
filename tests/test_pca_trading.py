"""
Unit tests for PCA Trading Engine and Local Exchange Market.
"""

import pytest
from src.utils.pca_trading_engine import PCATradingEngine
from src.utils.local_exchange_market import LocalExchangeMarket


def test_pca_engine_initialization():
    engine = PCATradingEngine(user_id="user1")
    balance = engine.initialize_allowance(500.0)
    assert balance == 500.0
    assert engine.get_balance("user1") == 500.0


def test_pca_engine_decrement():
    engine = PCATradingEngine(user_id="user1")
    engine.initialize_allowance(500.0)

    success = engine.decrement_balance("user1", 100.0)
    assert success is True
    assert engine.get_balance("user1") == 400.0

    fail = engine.decrement_balance("user1", 500.0)
    assert fail is False
    assert engine.get_balance("user1") == 400.0


def test_pca_trade_execution():
    engine = PCATradingEngine(user_id="user1")
    engine.initialize_allowance(500.0)
    engine.initialize_allowance(600.0)  # For user2 implicitly via dict

    trade = engine.execute_trade(
        buyer_id="user1", seller_id="user2", amount=100.0, price_per_tonne=50.0
    )

    assert trade["amount_kg"] == 100.0
    assert trade["total_cost_usd"] == 5.0
    assert trade["status"] == "completed"
    assert engine.get_balance("user1") == 600.0
    assert engine.get_balance("user2") == 500.0


def test_pca_trade_insufficient_funds():
    engine = PCATradingEngine(user_id="user1")
    engine.balances["user2"] = 50.0

    with pytest.raises(ValueError, match="Seller has insufficient carbon allowance"):
        engine.execute_trade("user1", "user2", 100.0, 50.0)


def test_market_price_dynamics():
    market = LocalExchangeMarket()
    initial_price = market.current_price

    # Heavy demand should increase price
    market.update_market_conditions(5000.0)
    assert market.current_price > initial_price

    # Heavy supply should decrease price
    market.update_market_conditions(-6000.0)
    assert market.current_price < market.historical_prices[-2]


def test_market_snapshot():
    market = LocalExchangeMarket()
    snapshot = market.get_market_snapshot()

    assert "current_price_per_tonne_usd" in snapshot
    assert "total_supply_kg" in snapshot
    assert "total_demand_kg" in snapshot
    assert snapshot["current_price_per_tonne_usd"] >= 5.0
