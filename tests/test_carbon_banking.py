"""
Unit tests for Carbon Banking Engine and Intertemporal Trading.
"""

import pytest
from src.carbon.carbon_banking_engine import CarbonBankingEngine
from src.utils.intertemporal_trading import IntertemporalTrading


def test_rollover_logic():
    engine = CarbonBankingEngine(user_id="user1", base_monthly_allowance=1000.0)
    engine.get_account("2023-10")
    engine.get_account("2023-11")

    # Use 400, leaving 600
    engine.log_usage("2023-10", 400.0)

    # Rollover 50% of 600 = 300
    rolled = engine.rollover_unused_allowance("2023-10", "2023-11", 50.0)

    assert rolled == 300.0
    assert engine.get_account("2023-11")["banked_from_previous"] == 300.0
    assert engine.get_account("2023-11")["total_available"] == 1300.0


def test_borrowing_limits():
    engine = CarbonBankingEngine(user_id="user1", base_monthly_allowance=1000.0)
    engine.get_account("2023-10")
    engine.get_account("2023-11")

    # Try to borrow 600 (max is 50% of 1000 = 500)
    success = engine.borrow_from_future("2023-10", "2023-11", 600.0)
    assert success is False

    # Borrow 400 (valid)
    success = engine.borrow_from_future("2023-10", "2023-11", 400.0)
    assert success is True
    assert engine.get_account("2023-10")["borrowed_from_future"] == 400.0
    assert engine.get_account("2023-11")["base_allowance"] == 600.0


def test_decay_calculation():
    trading = IntertemporalTrading(decay_rate_pct=10.0)

    # 100 kg held for 1 month at 10% decay = 90 kg
    decayed = trading.apply_decay_to_banked(100.0, 1)
    assert decayed == 90.0

    # 100 kg held for 2 months = 81 kg
    decayed_2 = trading.apply_decay_to_banked(100.0, 2)
    assert decayed_2 == 81.0


def test_borrowing_penalty():
    trading = IntertemporalTrading(interest_rate_pct=20.0)

    penalty = trading.calculate_borrowing_penalty(100.0, 1)
    assert penalty["principal"] == 100.0
    assert penalty["interest"] == 20.0
    assert penalty["total_owed"] == 120.0


def test_strategy_evaluation():
    trading = IntertemporalTrading(decay_rate_pct=10.0)

    # Test surplus
    strategy = trading.evaluate_banking_strategy(
        current_surplus=100.0, projected_deficit=0.0
    )
    assert strategy["recommendation"] == "Bank Surplus"
    assert strategy["value_next_month"] == 90.0

    # Test deficit
    strategy_deficit = trading.evaluate_banking_strategy(
        current_surplus=0.0, projected_deficit=100.0
    )
    assert strategy_deficit["recommendation"] == "Borrow with Caution"
    assert strategy_deficit["total_repayment_next_month"] == 110.0  # 10% interest
