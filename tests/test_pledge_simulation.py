"""
Tests for pledge_simulation
==============================
Covers what-if scenarios, carbon budget simulation, strategy comparison,
portfolio optimisation, seasonal projections, long-term projections,
simulation history, and JSON export.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import datetime, timedelta

import pytest


# ── Test database setup ──────────────────────────────────────────────

TEST_DB = "test_simulation.db"


@pytest.fixture(autouse=True)
def _setup_test_db(tmp_path, monkeypatch):
    """Use a temp SQLite DB for every test."""
    db_path = str(tmp_path / TEST_DB)
    monkeypatch.setattr("src.utils.green_pledge_tracker.DB_NAME", db_path)
    monkeypatch.setattr("src.community.pledge_leaderboard.DB_NAME", db_path)
    monkeypatch.setattr("src.community.pledge_impact_engine.DB_NAME", db_path)
    monkeypatch.setattr("src.community.pledge_simulation.DB_NAME", db_path)
    monkeypatch.setattr("src.core.database_connection.database_connection", lambda name: _ctx(name))
    yield db_path


class _ctx:
    def __init__(self, name):
        self._conn = sqlite3.connect(name)
        self._conn.row_factory = sqlite3.Row
    def __enter__(self):
        return self._conn
    def __exit__(self, *a):
        self._conn.close()


@pytest.fixture
def _init_tables(_setup_test_db):
    """Create all required tables."""
    from green_pledge_tracker import init_pledge_tables
    from pledge_leaderboard import init_leaderboard_tables
    from pledge_impact_engine import init_impact_tables
    from pledge_simulation import init_simulation_tables
    init_pledge_tables()
    init_leaderboard_tables()
    init_impact_tables()
    init_simulation_tables()


def _seed_pledges(user_id: int, count: int, weeks_back: int = 4):
    """Seed completed pledges for testing."""
    from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
    templates = [
        "energy_no_standby", "energy_cold_wash", "transport_bike_week",
        "diet_meatless_week", "waste_no_plastic", "water_5min_shower",
    ]
    for i in range(count):
        offset = i % weeks_back
        ws = (datetime.now() - timedelta(weeks=offset)).strftime("%Y-%m-%d")
        monday = datetime.strptime(ws, "%Y-%m-%d") - timedelta(days=datetime.strptime(ws, "%Y-%m-%d").weekday())
        ws = monday.strftime("%Y-%m-%d")
        tpl_id = templates[i % len(templates)]
        pledge = create_pledge(user_id=user_id, template_id=tpl_id, week=ws)
        if pledge:
            for d in range(min(7, 3 + i % 5)):
                day = (monday + timedelta(days=d)).strftime("%Y-%m-%d")
                checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)


# ── What-If tests ────────────────────────────────────────────────────

class TestWhatIf:
    """Tests for what-if scenario engine."""

    def test_whatif_empty_user(self, _init_tables):
        from pledge_simulation import run_what_if
        scenario = run_what_if(user_id=999)
        assert scenario is not None
        assert scenario.scenario_id
        assert scenario.current_weekly_co2_kg >= 0
        assert scenario.simulated_weekly_co2_kg >= 0

    def test_whatif_add_pledges(self, _init_tables):
        from pledge_simulation import run_what_if
        scenario = run_what_if(user_id=999, add_pledges=["energy_no_standby", "transport_bike_week"])
        assert scenario.weekly_delta_kg > 0
        assert len(scenario.pledges_added) == 2
        assert scenario.xp_change > 0

    def test_whatif_remove_pledges(self, _init_tables):
        from pledge_simulation import run_what_if
        _seed_pledges(user_id=1, count=2)
        scenario = run_what_if(user_id=1, remove_pledges=["energy_no_standby"])
        assert scenario.weekly_delta_kg <= 0
        assert len(scenario.pledges_removed) == 1

    def test_whatif_completion_change(self, _init_tables):
        from pledge_simulation import run_what_if
        scenario = run_what_if(user_id=999, completion_rate_change=0.5)
        assert scenario.completion_rate_change == 0.5

    def test_whatif_annual_delta(self, _init_tables):
        from pledge_simulation import run_what_if
        scenario = run_what_if(user_id=999, add_pledges=["energy_no_standby"])
        assert scenario.annual_delta_kg == scenario.weekly_delta_kg * 52

    def test_whatif_equivalent_change(self, _init_tables):
        from pledge_simulation import run_what_if
        scenario = run_what_if(user_id=999, add_pledges=["energy_no_standby"])
        assert scenario.equivalent_change  # non-empty string


# ── Carbon Budget tests ──────────────────────────────────────────────

class TestCarbonBudget:
    """Tests for carbon budget simulation."""

    def test_budget_empty_user(self, _init_tables):
        from pledge_simulation import simulate_carbon_budget
        budget = simulate_carbon_budget(user_id=999)
        assert budget.annual_target_kg == 2000.0
        assert budget.current_annual_usage_kg == 0.0
        assert budget.remaining_budget_kg == 2000.0
        assert budget.on_track is True
        assert len(budget.recommendations) > 0

    def test_budget_with_data(self, _init_tables):
        from pledge_simulation import simulate_carbon_budget
        _seed_pledges(user_id=2, count=4)
        budget = simulate_carbon_budget(user_id=2, annual_target_kg=1000.0)
        assert budget.current_annual_usage_kg > 0
        assert budget.weeks_left > 0
        assert budget.weekly_allowance_kg >= 0

    def test_budget_custom_target(self, _init_tables):
        from pledge_simulation import simulate_carbon_budget
        budget = simulate_carbon_budget(user_id=999, annual_target_kg=500.0)
        assert budget.annual_target_kg == 500.0
        assert budget.remaining_budget_kg == 500.0

    def test_budget_fields(self, _init_tables):
        from pledge_simulation import simulate_carbon_budget
        budget = simulate_carbon_budget(user_id=999)
        assert hasattr(budget, "budget_id")
        assert hasattr(budget, "on_track")
        assert hasattr(budget, "projected_annual_kg")
        assert hasattr(budget, "surplus_deficit_kg")
        assert hasattr(budget, "burn_rate_per_week")


# ── Strategy Comparison tests ────────────────────────────────────────

class TestStrategyComparison:
    """Tests for strategy comparison engine."""

    def test_compare_strategies(self, _init_tables):
        from pledge_simulation import compare_strategies
        comparison = compare_strategies(user_id=999)
        assert comparison.comparison_id
        assert len(comparison.strategies) > 0
        assert comparison.best_for_co2
        assert comparison.best_for_xp
        assert comparison.best_for_ease
        assert comparison.recommendation

    def test_strategies_have_required_fields(self, _init_tables):
        from pledge_simulation import compare_strategies
        comparison = compare_strategies(user_id=999)
        for strat in comparison.strategies:
            assert "strategy" in strat
            assert "title" in strat
            assert "annual_co2_kg" in strat
            assert "annual_xp" in strat
            assert "efficiency" in strat
            assert "completion_rate" in strat

    def test_best_co2_is_not_none(self, _init_tables):
        from pledge_simulation import compare_strategies
        comparison = compare_strategies(user_id=999)
        assert comparison.best_for_co2 in [s["strategy"] for s in comparison.strategies]


# ── Portfolio Optimiser tests ────────────────────────────────────────

class TestPortfolioOptimiser:
    """Tests for portfolio optimisation."""

    def test_optimise_portfolio_default(self, _init_tables):
        from pledge_simulation import optimise_portfolio
        portfolio = optimise_portfolio(user_id=999)
        assert portfolio.portfolio_id
        assert len(portfolio.selected_pledges) > 0
        assert portfolio.total_weekly_co2_kg > 0
        assert portfolio.total_effort > 0
        assert portfolio.efficiency_score > 0

    def test_optimise_portfolio_effort_constraint(self, _init_tables):
        from pledge_simulation import optimise_portfolio
        portfolio = optimise_portfolio(user_id=999, effort_budget=1)
        assert portfolio.total_effort <= 1.0

    def test_optimise_portfolio_difficulty_constraint(self, _init_tables):
        from pledge_simulation import optimise_portfolio
        portfolio = optimise_portfolio(user_id=999, difficulty_budget="easy")
        for p in portfolio.selected_pledges:
            assert p["difficulty"] == "easy"

    def test_portfolio_coverage(self, _init_tables):
        from pledge_simulation import optimise_portfolio
        portfolio = optimise_portfolio(user_id=999, effort_budget=5)
        assert len(portfolio.coverage_categories) > 0

    def test_portfolio_efficiency(self, _init_tables):
        from pledge_simulation import optimise_portfolio
        portfolio = optimise_portfolio(user_id=999)
        assert portfolio.efficiency_score == portfolio.total_weekly_co2_kg / max(portfolio.total_effort, 0.1)


# ── Seasonal Projection tests ───────────────────────────────────────

class TestSeasonalProjection:
    """Tests for seasonal impact projections."""

    def test_seasonal_empty(self, _init_tables):
        from pledge_simulation import project_seasonal_impact
        projections = project_seasonal_impact(user_id=999)
        assert len(projections) == 4  # spring, summer, autumn, winter
        for p in projections:
            assert p.season in ("spring", "summer", "autumn", "winter")
            assert p.total_projected_co2_kg >= 0

    def test_seasonal_with_data(self, _init_tables):
        from pledge_simulation import project_seasonal_impact
        _seed_pledges(user_id=3, count=4)
        projections = project_seasonal_impact(user_id=3)
        assert len(projections) == 4
        # Summer should have higher water factor
        summer = next(p for p in projections if p.season == "summer")
        winter = next(p for p in projections if p.season == "winter")
        assert summer.seasonal_factor > 0
        assert winter.seasonal_factor > 0

    def test_seasonal_category_projections(self, _init_tables):
        from pledge_simulation import project_seasonal_impact
        projections = project_seasonal_impact(user_id=999)
        for p in projections:
            assert len(p.category_projections) > 0
            for cat in p.category_projections:
                assert "category" in cat
                assert "seasonal_factor" in cat
                assert "seasonal_co2_kg" in cat

    def test_seasonal_notes(self, _init_tables):
        from pledge_simulation import project_seasonal_impact
        projections = project_seasonal_impact(user_id=999)
        winter = next(p for p in projections if p.season == "winter")
        assert len(winter.notes) > 0  # should have energy hint


# ── Long-Term Projection tests ──────────────────────────────────────

class TestLongTermProjection:
    """Tests for long-term impact projections."""

    def test_long_term_empty(self, _init_tables):
        from pledge_simulation import project_long_term
        lt = project_long_term(user_id=999, years=3)
        assert lt.years == 3
        assert len(lt.annual_projections) == 3
        assert lt.cumulative_co2_kg >= 0
        assert lt.cumulative_xp >= 0

    def test_long_term_with_data(self, _init_tables):
        from pledge_simulation import project_long_term
        _seed_pledges(user_id=4, count=4)
        lt = project_long_term(user_id=4, years=5, strategy="aggressive")
        assert lt.years == 5
        assert len(lt.annual_projections) == 5
        assert lt.cumulative_co2_kg > 0

    def test_long_term_equivalents(self, _init_tables):
        from pledge_simulation import project_long_term
        lt = project_long_term(user_id=999, years=3)
        assert lt.equivalent_trees >= 0
        assert lt.equivalent_car_km >= 0

    def test_long_term_milestone_projection(self, _init_tables):
        from pledge_simulation import project_long_term
        lt = project_long_term(user_id=999, years=3)
        assert len(lt.milestone_projection) > 0
        for m in lt.milestone_projection:
            assert "milestone" in m
            assert "threshold_kg" in m
            assert "weeks_to_reach" in m

    def test_long_term_annual_growth(self, _init_tables):
        from pledge_simulation import project_long_term
        lt = project_long_term(user_id=999, years=3, strategy="balanced")
        # Each year should have higher CO₂ due to growth factor
        for i in range(1, len(lt.annual_projections)):
            assert lt.annual_projections[i]["annual_co2_kg"] >= lt.annual_projections[i-1]["annual_co2_kg"]


# ── Simulation Runner tests ──────────────────────────────────────────

class TestSimulationRunner:
    """Tests for the unified simulation runner."""

    def test_run_what_if(self, _init_tables):
        from pledge_simulation import run_simulation, SimulationType
        result = run_simulation(999, SimulationType.WHAT_IF)
        assert result.simulation_id
        assert result.simulation_type == "what_if"
        assert result.title
        assert result.created_at

    def test_run_strategy_compare(self, _init_tables):
        from pledge_simulation import run_simulation, SimulationType
        result = run_simulation(999, SimulationType.STRATEGY_COMPARE)
        assert result.simulation_type == "strategy_compare"
        assert len(result.projections) > 0

    def test_run_carbon_budget(self, _init_tables):
        from pledge_simulation import run_simulation, SimulationType
        result = run_simulation(999, SimulationType.CARBON_BUDGET, {"annual_target_kg": 1500.0})
        assert result.simulation_type == "carbon_budget"
        assert "on_track" in result.summary

    def test_run_portfolio_optimise(self, _init_tables):
        from pledge_simulation import run_simulation, SimulationType
        result = run_simulation(999, SimulationType.PORTFOLIO_OPTIMISE, {"effort_budget": 2})
        assert result.simulation_type == "portfolio_optimise"
        assert len(result.projections) > 0

    def test_run_seasonal(self, _init_tables):
        from pledge_simulation import run_simulation, SimulationType
        result = run_simulation(999, SimulationType.SEASONAL)
        assert result.simulation_type == "seasonal"
        assert len(result.projections) == 4

    def test_run_long_term(self, _init_tables):
        from pledge_simulation import run_simulation, SimulationType
        result = run_simulation(999, SimulationType.LONG_TERM, {"years": 2, "strategy": "aggressive"})
        assert result.simulation_type == "long_term"
        assert len(result.projections) == 2


# ── History and Export tests ─────────────────────────────────────────

class TestHistoryAndExport:
    """Tests for simulation history and JSON export."""

    def test_empty_history(self, _init_tables):
        from pledge_simulation import get_simulation_history
        history = get_simulation_history(user_id=999)
        assert history == []

    def test_history_after_simulation(self, _init_tables):
        from pledge_simulation import run_simulation, SimulationType, get_simulation_history
        run_simulation(999, SimulationType.WHAT_IF)
        run_simulation(999, SimulationType.CARBON_BUDGET)
        history = get_simulation_history(user_id=999)
        assert len(history) == 2

    def test_export_json(self, _init_tables):
        from pledge_simulation import run_simulation, export_simulations_json, SimulationType
        run_simulation(999, SimulationType.WHAT_IF)
        json_str = export_simulations_json(user_id=999)
        data = json.loads(json_str)
        assert len(data) >= 1
        assert "simulation_id" in data[0]
        assert "title" in data[0]


# ── Constants tests ──────────────────────────────────────────────────

class TestConstants:
    """Tests for simulation constants and presets."""

    def test_scenario_presets_complete(self, _init_tables):
        from pledge_simulation import SCENARIO_PRESETS
        for key, preset in SCENARIO_PRESETS.items():
            assert "title" in preset
            assert "description" in preset
            assert "pledges_per_week" in preset
            assert "difficulty_mix" in preset
            assert "completion_rate" in preset
            assert sum(preset["difficulty_mix"].values()) == pytest.approx(1.0)

    def test_seasonal_factors_complete(self, _init_tables):
        from pledge_simulation import SEASONAL_FACTORS
        assert len(SEASONAL_FACTORS) == 4
        for season, factors in SEASONAL_FACTORS.items():
            assert len(factors) == 6  # 6 categories
            for cat, factor in factors.items():
                assert factor > 0


# ── Serialisation tests ──────────────────────────────────────────────

class TestSerialisation:
    """Tests for simulation data serialisation."""

    def test_simulation_to_dict(self, _init_tables):
        from pledge_simulation import run_simulation, simulation_to_dict, SimulationType
        result = run_simulation(999, SimulationType.WHAT_IF)
        d = simulation_to_dict(result)
        assert isinstance(d, dict)
        assert "simulation_id" in d
        assert "projections" in d
        assert "summary" in d


# ── Integration test ─────────────────────────────────────────────────

class TestIntegration:
    """Integration test for the full simulation workflow."""

    def test_full_workflow(self, _init_tables):
        from green_pledge_tracker import create_pledge, checkin_pledge, current_week_start
        from pledge_simulation import (
            run_what_if,
            simulate_carbon_budget,
            compare_strategies,
            optimise_portfolio,
            project_seasonal_impact,
            project_long_term,
            run_simulation,
            get_simulation_history,
            SimulationType,
        )

        user_id = 42

        # Seed pledges
        for tpl_id in ["energy_no_standby", "transport_bike_week"]:
            pledge = create_pledge(user_id=user_id, template_id=tpl_id)
            if pledge:
                ws = current_week_start()
                monday = datetime.strptime(ws, "%Y-%m-%d")
                for d in range(7):
                    day = (monday + timedelta(days=d)).strftime("%Y-%m-%d")
                    checkin_pledge(user_id=user_id, pledge_id=pledge.pledge_id, day_date=day)

        # What-if
        whatif = run_what_if(user_id, add_pledges=["diet_meatless_week"])
        assert whatif.weekly_delta_kg > 0

        # Carbon budget
        budget = simulate_carbon_budget(user_id, annual_target_kg=1500.0)
        assert budget.annual_target_kg == 1500.0

        # Strategy comparison
        comparison = compare_strategies(user_id)
        assert len(comparison.strategies) > 0

        # Portfolio optimise
        portfolio = optimise_portfolio(user_id, effort_budget=3)
        assert len(portfolio.selected_pledges) > 0

        # Seasonal
        seasonal = project_seasonal_impact(user_id)
        assert len(seasonal) == 4

        # Long-term
        lt = project_long_term(user_id, years=2)
        assert lt.cumulative_co2_kg >= 0

        # Full simulation run
        result = run_simulation(user_id, SimulationType.LONG_TERM, {"years": 2})
        assert result.simulation_id

        # History
        history = get_simulation_history(user_id)
        assert len(history) >= 1
