"""
Unit tests for Household Carbon Budget Planner.
"""

import pytest
from household_carbon_budget import (
    HouseholdCarbonBudgetPlanner,
    BudgetPeriod,
    Category,
    AlertLevel,
)


@pytest.fixture
def planner():
    return HouseholdCarbonBudgetPlanner()


@pytest.fixture
def active_plan(planner):
    plan = planner.create_budget_plan(
        household_id="hh1",
        period=BudgetPeriod.MONTHLY,
        start_date="2026-08-01",
        end_date="2026-08-31",
        total_limit_kg=500.0,
        allocations={
            "transport": 100.0,
            "energy": 150.0,
            "food": 120.0,
            "waste": 50.0,
            "water": 30.0,
            "shopping": 30.0,
            "travel": 10.0,
        },
    )
    return plan


# ── Plan Tests ───────────────────────────────────────────────────────────


def test_create_plan(planner):
    plan = planner.create_budget_plan(
        household_id="hh1",
        period=BudgetPeriod.MONTHLY,
        start_date="2026-08-01",
        end_date="2026-08-31",
        total_limit_kg=400.0,
    )
    assert plan.plan_id.startswith("bp_")
    assert plan.total_limit_kg == 400.0
    assert plan.is_active is True
    assert len(plan.allocations) == len(Category)


def test_create_plan_with_allocations(planner, active_plan):
    assert "transport" in active_plan.allocations
    assert active_plan.allocations["transport"].limit_kg == 100.0
    assert "other" in active_plan.allocations


def test_get_plan(planner, active_plan):
    found = planner.get_plan(active_plan.plan_id)
    assert found is not None
    assert found.plan_id == active_plan.plan_id


def test_get_active_plan(planner, active_plan):
    found = planner.get_active_plan("hh1")
    assert found is not None
    assert found.plan_id == active_plan.plan_id


def test_get_active_plan_none(planner):
    assert planner.get_active_plan("nonexistent") is None


def test_deactivate_plan(planner, active_plan):
    result = planner.deactivate_plan(active_plan.plan_id)
    assert result is True
    assert active_plan.is_active is False


def test_delete_inactive_plan(planner):
    plan = planner.create_budget_plan(
        household_id="hh2", period=BudgetPeriod.WEEKLY,
        start_date="2026-08-01", end_date="2026-08-07",
        total_limit_kg=100.0,
    )
    planner.deactivate_plan(plan.plan_id)
    assert planner.delete_plan(plan.plan_id) is True
    assert planner.get_plan(plan.plan_id) is None


def test_cannot_delete_active_plan(planner, active_plan):
    assert planner.delete_plan(active_plan.plan_id) is False


# ── Spending Tests ───────────────────────────────────────────────────────


def test_record_spending(planner, active_plan):
    result = planner.record_spending("hh1", "transport", 25.0, "Bus commute")
    assert result["success"] is True
    assert result["entry"].kg_co2 == 25.0


def test_record_negative_spending(planner, active_plan):
    result = planner.record_spending("hh1", "transport", -5.0, "Invalid")
    assert result["success"] is False


def test_record_invalid_category(planner, active_plan):
    result = planner.record_spending("hh1", "invalid", 10.0, "Test")
    assert result["success"] is False


def test_spending_updates_allocation(planner, active_plan):
    planner.record_spending("hh1", "transport", 50.0, "Drive")
    plan = planner.get_active_plan("hh1")
    assert plan.allocations["transport"].spent_kg == 50.0


def test_spending_trigger_warning(planner, active_plan):
    # Transport limit is 100, warning at 60% = 60kg
    planner.record_spending("hh1", "transport", 65.0, "Long drive")
    result = planner.record_spending("hh1", "transport", 5.0, "More driving")
    assert any(a.level == AlertLevel.WARNING for a in result["alerts"])


def test_spending_trigger_critical(planner, active_plan):
    # Transport limit 100, critical at 80% = 80kg
    planner.record_spending("hh1", "transport", 75.0, "Drive")
    result = planner.record_spending("hh1", "transport", 10.0, "More")
    assert any(a.level == AlertLevel.CRITICAL for a in result["alerts"])


def test_spending_trigger_exceeded(planner, active_plan):
    planner.record_spending("hh1", "transport", 95.0, "Drive")
    result = planner.record_spending("hh1", "transport", 10.0, "Over")
    assert any(a.level == AlertLevel.EXCEEDED for a in result["alerts"])


def test_batch_spending(planner, active_plan):
    entries = [
        {"category": "transport", "kg_co2": 10.0, "description": "Bus"},
        {"category": "energy", "kg_co2": 20.0, "description": "Electricity"},
        {"category": "food", "kg_co2": 15.0, "description": "Groceries"},
    ]
    result = planner.record_batch_spending("hh1", entries)
    assert result["recorded"] == 3
    assert len(result["errors"]) == 0


def test_get_spending(planner, active_plan):
    planner.record_spending("hh1", "transport", 10.0, "Bus")
    planner.record_spending("hh1", "energy", 20.0, "Power")
    entries = planner.get_spending("hh1", category="transport")
    assert len(entries) == 1
    assert entries[0].category == Category.TRANSPORT


def test_get_spending_summary(planner, active_plan):
    planner.record_spending("hh1", "transport", 10.0, "Bus")
    planner.record_spending("hh1", "transport", 5.0, "Metro")
    summary = planner.get_spending_summary("hh1")
    assert summary["total_spent_kg"] == 15.0
    assert summary["by_category"]["transport"] == 15.0
    assert summary["entry_count"] == 2


# ── Budget Analysis Tests ────────────────────────────────────────────────


def test_budget_status(planner, active_plan):
    planner.record_spending("hh1", "transport", 30.0, "Drive")
    status = planner.get_budget_status("hh1")
    assert status["has_plan"] is True
    assert status["total_spent_kg"] == 30.0
    assert len(status["categories"]) > 0


def test_budget_status_no_plan(planner):
    status = planner.get_budget_status("nobody")
    assert status["has_plan"] is False


def test_savings_rate(planner, active_plan):
    planner.record_spending("hh1", "transport", 20.0, "Bus")
    savings = planner.calculate_savings_rate("hh1")
    assert savings["savings_kg"] > 0
    assert savings["savings_pct"] > 0


def test_suggest_reallocation(planner, active_plan):
    # Overspend transport
    for _ in range(12):
        planner.record_spending("hh1", "transport", 10.0, "Drive")

    suggestions = planner.suggest_reallocation("hh1")
    increase_sugs = [s for s in suggestions if s["action"] == "increase"]
    assert len(increase_sugs) > 0
    assert increase_sugs[0]["category"] == "transport"


def test_compare_periods(planner, active_plan):
    planner.record_spending("hh1", "transport", 50.0, "Drive")
    comparison = planner.compare_periods("hh1", months_back=3)
    assert len(comparison) == 3


# ── Alert Tests ──────────────────────────────────────────────────────────


def test_alerts_generated(planner, active_plan):
    planner.record_spending("hh1", "transport", 85.0, "Drive")
    alerts = planner.get_alerts("hh1")
    assert len(alerts) > 0


def test_acknowledge_alert(planner, active_plan):
    planner.record_spending("hh1", "transport", 85.0, "Drive")
    alerts = planner.get_alerts("hh1")
    alert_id = alerts[0].alert_id
    assert planner.acknowledge_alert("hh1", alert_id) is True
    refreshed = planner.get_alerts("hh1", unacknowledged_only=True)
    assert all(a.alert_id != alert_id for a in refreshed)


def test_alert_summary(planner, active_plan):
    planner.record_spending("hh1", "transport", 85.0, "Drive")
    summary = planner.get_alert_summary("hh1")
    assert isinstance(summary, dict)


# ── Snapshot & Trend Tests ───────────────────────────────────────────────


def test_take_snapshot(planner, active_plan):
    planner.record_spending("hh1", "transport", 30.0, "Bus")
    snapshot = planner.take_snapshot("hh1")
    assert snapshot.total_spent_kg == 30.0
    assert snapshot.month


def test_get_snapshot_history(planner, active_plan):
    planner.take_snapshot("hh1")
    history = planner.get_snapshot_history("hh1")
    assert len(history) == 1


def test_get_trend_insufficient_data(planner, active_plan):
    trend = planner.get_trend("hh1")
    assert trend["trend"] == "insufficient_data"


# ── Preset Tests ─────────────────────────────────────────────────────────


def test_get_presets():
    presets = HouseholdCarbonBudgetPlanner.get_budget_presets()
    assert "solo_eco_warrior" in presets
    assert "family_balanced" in presets
    assert len(presets) == 5


def test_create_from_preset(planner):
    plan = planner.create_from_preset(
        household_id="hh2",
        preset_name="couple_green",
        start_date="2026-08-01",
        end_date="2026-08-31",
    )
    assert plan is not None
    assert plan.total_limit_kg == 350.0
    assert plan.allocations["transport"].limit_kg == 60.0


def test_create_from_preset_scaled(planner):
    plan = planner.create_from_preset(
        household_id="hh3",
        preset_name="family_balanced",
        start_date="2026-08-01",
        end_date="2026-08-31",
        scale_factor=1.5,
    )
    assert plan.total_limit_kg == 900.0


def test_preset_not_found(planner):
    result = planner.create_from_preset(
        "hh1", "nonexistent", "2026-08-01", "2026-08-31"
    )
    assert result is None


# ── Equivalents Tests ────────────────────────────────────────────────────


def test_kg_to_equivalents():
    eq = HouseholdCarbonBudgetPlanner.kg_to_equivalents(100.0)
    assert eq["kg_co2"] == 100.0
    assert eq["tree_days"] > 0
    assert eq["car_km"] > 0


def test_kg_to_equivalents_zero():
    eq = HouseholdCarbonBudgetPlanner.kg_to_equivalents(0.0)
    assert eq["kg_co2"] == 0.0
