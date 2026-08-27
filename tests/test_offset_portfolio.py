"""
Unit tests for Offset Portfolio Manager and Carbon Risk Analyzer.
"""

import pytest
from offset_portfolio_manager import OffsetPortfolioManager
from carbon_risk_analyzer import CarbonRiskAnalyzer


def test_portfolio_manager_add_and_summary():
    manager = OffsetPortfolioManager(user_id="user1")
    manager.add_holding("p1", "reforestation", "SA", "GS", 100.0, 15.0)
    manager.add_holding("p2", "renewable_energy", "IN", "Verra", 50.0, 10.0)

    summary = manager.get_portfolio_summary()
    assert summary["total_tonnes"] == 150.0
    assert summary["total_cost"] == 2000.0
    assert summary["type_breakdown"]["reforestation"] == 100.0
    assert summary["holding_count"] == 2


def test_rebalancing_trades():
    manager = OffsetPortfolioManager(user_id="user1")
    # 100% in reforestation, target is 40%
    manager.add_holding("p1", "reforestation", "SA", "GS", 100.0, 15.0)

    trades = manager.calculate_rebalancing_trades()
    # Should recommend selling 60 tonnes of reforestation
    sell_trade = next(
        (
            t
            for t in trades
            if t["project_type"] == "reforestation" and t["action"] == "sell"
        ),
        None,
    )
    assert sell_trade is not None
    assert sell_trade["tonnes"] == 60.0


def test_hhi_calculation():
    manager = OffsetPortfolioManager(user_id="user1")
    manager.add_holding("p1", "reforestation", "SA", "GS", 100.0, 15.0)

    analyzer = CarbonRiskAnalyzer(manager.get_portfolio_summary())
    hhi = analyzer.calculate_herfindahl_hirschman_index()
    assert hhi == 10000.0  # Monopoly


def test_risk_evaluation():
    manager = OffsetPortfolioManager(user_id="user1")
    manager.add_holding("p1", "direct_air_capture", "IS", "Puro", 100.0, 350.0)

    analyzer = CarbonRiskAnalyzer(manager.get_portfolio_summary())
    risk = analyzer.evaluate_portfolio_risk()

    assert risk["weighted_permanence_risk"] == 5.0
    assert risk["overall_risk_rating"] == "Low Risk"
    assert risk["diversification_score"] == 0.0  # Not diversified, but low risk


def test_risk_recommendations():
    manager = OffsetPortfolioManager(user_id="user1")
    manager.add_holding("p1", "reforestation", "SA", "GS", 100.0, 15.0)

    analyzer = CarbonRiskAnalyzer(manager.get_portfolio_summary())
    recs = analyzer.generate_risk_recommendations()

    assert any("Concentration" in r for r in recs)
    assert any("Permanence Risk" in r for r in recs)
