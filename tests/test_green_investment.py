"""
Unit tests for Green Investment Tracker and Banking Impact Analyzer.
"""

import pytest
from src.utils.green_investment_tracker import GreenInvestmentTracker
from src.utils.banking_impact_analyzer import BankingImpactAnalyzer


def test_investment_tracker_allocation():
    tracker = GreenInvestmentTracker(total_portfolio_value_usd=100000)
    tracker.set_allocation("equities_developed", 60.0)
    tracker.set_allocation("cash", 40.0)

    assert tracker.validate_allocations() is True

    with pytest.raises(ValueError, match="must sum to 100%"):
        tracker.set_allocation("esg_funds", 10.0)  # Makes it 110%
        tracker.calculate_financed_emissions()


def test_investment_tracker_calculation():
    tracker = GreenInvestmentTracker(total_portfolio_value_usd=1_000_000)
    tracker.set_allocation("equities_developed", 100.0)

    results = tracker.calculate_financed_emissions()
    # 1M * 100% = 1M. 1M / 1M = 1. 1 * 150 = 150 tonnes.
    assert results["total_financed_emissions_tonnes"] == 150.0
    assert results["breakdown"]["equities_developed"]["emissions_tonnes"] == 150.0


def test_investment_suggestions():
    tracker = GreenInvestmentTracker(total_portfolio_value_usd=1_000_000)
    tracker.set_allocation("equities_emerging", 100.0)  # High emission (250)

    suggestions = tracker.suggest_greener_alternatives()
    assert len(suggestions) > 0
    assert suggestions[0]["current_asset"] == "Equities Emerging"
    assert suggestions[0]["potential_savings_tonnes"] > 0


def test_banking_impact_calculation():
    analyzer = BankingImpactAnalyzer(deposit_amount_usd=10000)

    traditional = analyzer.calculate_deposit_footprint("traditional_large_bank")
    green = analyzer.calculate_deposit_footprint("certified_green_bank")

    assert traditional["annual_emissions_tonnes"] == 0.85
    assert green["annual_emissions_tonnes"] == 0.10
    assert (
        traditional["equivalent_tree_seedlings"] == 42
    )  # 0.85 * 1000 / 20 = 42.5 -> 42


def test_banking_alternatives_comparison():
    analyzer = BankingImpactAnalyzer(deposit_amount_usd=10000)
    alternatives = analyzer.compare_banking_options("traditional_large_bank")

    # Should suggest green bank as top alternative
    assert alternatives[0]["alternative_bank_type"] == "Certified Green Bank"
    assert alternatives[0]["potential_annual_savings_tonnes"] == 0.75  # 0.85 - 0.10
    assert alternatives[0]["savings_percentage"] == 88.2  # (0.75 / 0.85) * 100
