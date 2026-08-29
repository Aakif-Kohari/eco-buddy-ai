"""
Tests for the Carbon Budget Planner Engine
"""

import pytest

from src.utils.carbon_budget_planner import (
    get_budget_template, calculate_category_budgets, evaluate_budget_usage,
    project_month_end_usage, generate_budget_alerts, calculate_budget_score,
    generate_budget_recommendations, generate_budget_report,
    DEFAULT_BUDGET_TEMPLATES, ALERT_THRESHOLDS,
)

SAMPLE_BUDGETS = {"Transport": 180.0, "Electricity": 150.0, "Diet": 100.0, "Flights": 40.0}
SAMPLE_ACTUALS = {"Transport": 140.0, "Electricity": 110.0, "Diet": 65.0, "Flights": 0.0}


# ── get_budget_template Tests ────────────────────────────────────────────────

class TestGetBudgetTemplate:
    def test_known_template(self):
        t = get_budget_template("conservative")
        assert t["label"].startswith("🌿")

    def test_unknown_falls_back_to_moderate(self):
        t = get_budget_template("nonexistent")
        assert t["label"].startswith("🌍")

    def test_all_templates_have_required_keys(self):
        required = {"label", "Transport", "Electricity", "Diet", "Flights",
                    "total_monthly_kg", "description"}
        for name, t in DEFAULT_BUDGET_TEMPLATES.items():
            assert required.issubset(t.keys()), f"Template {name} missing keys"


# ── calculate_category_budgets Tests ─────────────────────────────────────────

class TestCalculateCategoryBudgets:
    def test_total_matches(self):
        budgets = calculate_category_budgets(1000.0)
        assert abs(sum(budgets.values()) - 1000.0) < 1.0

    def test_default_categories(self):
        budgets = calculate_category_budgets(500.0)
        assert {"Transport", "Electricity", "Diet", "Flights"}.issubset(budgets.keys())

    def test_custom_weights(self):
        weights = {"Transport": 1.0, "Electricity": 1.0, "Diet": 0.0, "Flights": 0.0}
        budgets = calculate_category_budgets(200.0, weights)
        assert budgets["Diet"] == 0.0
        assert budgets["Flights"] == 0.0

    def test_proportional(self):
        budgets = calculate_category_budgets(1000.0)
        assert budgets["Transport"] > budgets["Flights"]  # Default: Transport has highest weight


# ── evaluate_budget_usage Tests ──────────────────────────────────────────────

class TestEvaluateBudgetUsage:
    def test_returns_all_categories(self):
        evals = evaluate_budget_usage(SAMPLE_BUDGETS, SAMPLE_ACTUALS)
        assert len(evals) == len(SAMPLE_BUDGETS)

    def test_safe_when_under_budget(self):
        evals = evaluate_budget_usage(SAMPLE_BUDGETS, SAMPLE_ACTUALS)
        flights_eval = next(e for e in evals if e["category"] == "Flights")
        assert flights_eval["alert_level"] == "safe"

    def test_exceeded_when_over_budget(self):
        over = {"Transport": 250.0, "Electricity": 100.0, "Diet": 50.0, "Flights": 0.0}
        evals = evaluate_budget_usage(SAMPLE_BUDGETS, over)
        transport_eval = next(e for e in evals if e["category"] == "Transport")
        assert transport_eval["alert_level"] == "exceeded"

    def test_sorted_by_usage_ratio(self):
        evals = evaluate_budget_usage(SAMPLE_BUDGETS, SAMPLE_ACTUALS)
        ratios = [e["usage_ratio"] for e in evals]
        assert ratios == sorted(ratios, reverse=True)

    def test_remaining_calculation(self):
        evals = evaluate_budget_usage(SAMPLE_BUDGETS, SAMPLE_ACTUALS)
        for ev in evals:
            expected = ev["budget_kg"] - ev["actual_kg"]
            assert abs(ev["remaining_kg"] - expected) < 0.1

    def test_zero_budget(self):
        budgets = {"Transport": 0.0, "Electricity": 100.0, "Diet": 50.0, "Flights": 0.0}
        actuals = {"Transport": 10.0, "Electricity": 50.0, "Diet": 25.0, "Flights": 0.0}
        evals = evaluate_budget_usage(budgets, actuals)
        transport_eval = next(e for e in evals if e["category"] == "Transport")
        assert transport_eval["usage_ratio"] == float("inf")


# ── project_month_end_usage Tests ────────────────────────────────────────────

class TestProjectMonthEndUsage:
    def test_basic_projection(self):
        proj = project_month_end_usage({"Transport": 100.0}, day_of_month=10)
        assert proj["Transport"]["projected_month_end_kg"] == 300.0  # 100/10 * 30

    def test_daily_rate(self):
        proj = project_month_end_usage({"Transport": 150.0}, day_of_month=15)
        assert proj["Transport"]["daily_rate_kg"] == 10.0

    def test_remaining_days(self):
        proj = project_month_end_usage({"Transport": 100.0}, day_of_month=20, days_in_month=30)
        assert proj["Transport"]["remaining_days"] == 10

    def test_day_zero_uses_one(self):
        proj = project_month_end_usage({"Transport": 50.0}, day_of_month=0)
        # day_of_month=0 → max(day,1)=1, so projected = 50/1 * 30 = 1500
        assert proj["Transport"]["projected_month_end_kg"] == 1500.0

    def test_multiple_categories(self):
        proj = project_month_end_usage({"A": 60.0, "B": 30.0}, day_of_month=10)
        assert len(proj) == 2


# ── generate_budget_alerts Tests ─────────────────────────────────────────────

class TestGenerateBudgetAlerts:
    def test_exceeded_generates_critical_alert(self):
        evals = [{"category": "Transport", "alert_level": "exceeded", "usage_percent": 120,
                  "remaining_kg": -36.0, "budget_kg": 180.0, "actual_kg": 216.0}]
        proj = {"Transport": {"remaining_days": 10, "daily_rate_kg": 21.6,
                              "current_kg": 216.0, "projected_month_end_kg": 648.0}}
        alerts = generate_budget_alerts(evals, proj, SAMPLE_BUDGETS)
        assert len(alerts) > 0
        assert alerts[0]["severity"] == "critical"

    def test_no_alerts_when_safe(self):
        evals = [{"category": "Flights", "alert_level": "safe", "usage_percent": 25,
                  "remaining_kg": 30.0, "budget_kg": 40.0, "actual_kg": 10.0}]
        proj = {"Flights": {"remaining_days": 15, "daily_rate_kg": 0.67,
                            "current_kg": 10.0, "projected_month_end_kg": 20.0}}
        alerts = generate_budget_alerts(evals, proj, SAMPLE_BUDGETS)
        assert alerts == []

    def test_alerts_sorted_by_severity(self):
        evals = [
            {"category": "A", "alert_level": "warning", "usage_percent": 85,
             "remaining_kg": 15.0, "budget_kg": 100.0, "actual_kg": 85.0},
            {"category": "B", "alert_level": "exceeded", "usage_percent": 110,
             "remaining_kg": -10.0, "budget_kg": 100.0, "actual_kg": 110.0},
        ]
        proj = {
            "A": {"remaining_days": 10, "daily_rate_kg": 8.5, "current_kg": 85.0,
                  "projected_month_end_kg": 255.0},
            "B": {"remaining_days": 10, "daily_rate_kg": 11.0, "current_kg": 110.0,
                  "projected_month_end_kg": 330.0},
        }
        alerts = generate_budget_alerts(evals, proj, SAMPLE_BUDGETS)
        assert alerts[0]["severity"] == "critical"


# ── calculate_budget_score Tests ─────────────────────────────────────────────

class TestCalculateBudgetScore:
    def test_perfect_score(self):
        evals = [{"usage_ratio": 0.5}] * 4
        assert calculate_budget_score(evals)["score"] == 100

    def test_over_budget_reduces_score(self):
        evals = [{"usage_ratio": 1.5}]
        result = calculate_budget_score(evals)
        assert result["score"] < 60

    def test_empty_returns_perfect(self):
        result = calculate_budget_score([])
        assert result["score"] == 100

    def test_grade_structure(self):
        result = calculate_budget_score([{"usage_ratio": 0.3}])
        assert "grade" in result and "description" in result

    def test_score_bounded(self):
        for ratio in [0.1, 0.5, 1.0, 1.5, 3.0, 5.0]:
            result = calculate_budget_score([{"usage_ratio": ratio}])
            assert 0 <= result["score"] <= 100


# ── generate_budget_recommendations Tests ────────────────────────────────────

class TestGenerateBudgetRecommendations:
    def test_over_budget_recommendation(self):
        evals = [{"category": "Transport", "usage_ratio": 1.2, "actual_kg": 216, "budget_kg": 180}]
        recs = generate_budget_recommendations(evals, SAMPLE_BUDGETS)
        assert any("Transport" in r for r in recs)

    def test_all_under_budget(self):
        evals = [{"category": c, "usage_ratio": 0.4, "actual_kg": a, "budget_kg": b}
                 for c, a, b in zip(SAMPLE_ACTUALS.keys(), SAMPLE_ACTUALS.values(), SAMPLE_BUDGETS.values())]
        recs = generate_budget_recommendations(evals, SAMPLE_BUDGETS)
        assert len(recs) > 0

    def test_returns_list_of_strings(self):
        evals = [{"category": "Diet", "usage_ratio": 0.8, "actual_kg": 80, "budget_kg": 100}]
        recs = generate_budget_recommendations(evals, SAMPLE_BUDGETS)
        assert all(isinstance(r, str) for r in recs)


# ── generate_budget_report Tests ─────────────────────────────────────────────

class TestGenerateBudgetReport:
    def test_all_keys_present(self):
        report = generate_budget_report(SAMPLE_BUDGETS, SAMPLE_ACTUALS, day_of_month=15)
        expected = {"template_name", "budgets", "actuals", "evaluations", "projections",
                    "alerts", "score", "recommendations", "totals", "day_of_month", "generated_at"}
        assert expected.issubset(report.keys())

    def test_totals_correct(self):
        report = generate_budget_report(SAMPLE_BUDGETS, SAMPLE_ACTUALS, day_of_month=15)
        assert report["totals"]["budget_kg"] == sum(SAMPLE_BUDGETS.values())
        assert report["totals"]["actual_kg"] == sum(SAMPLE_ACTUALS.values())

    def test_evaluations_match_budgets(self):
        report = generate_budget_report(SAMPLE_BUDGETS, SAMPLE_ACTUALS, day_of_month=10)
        assert len(report["evaluations"]) == len(SAMPLE_BUDGETS)

    def test_with_custom_template(self):
        report = generate_budget_report(SAMPLE_BUDGETS, SAMPLE_ACTUALS, 10,
                                        template_name="conservative")
        assert report["template_name"] == "conservative"

    def test_score_is_dict(self):
        report = generate_budget_report(SAMPLE_BUDGETS, SAMPLE_ACTUALS, 15)
        assert isinstance(report["score"], dict)
        assert "score" in report["score"]


# ── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_all_zero_actuals(self):
        zero = {k: 0.0 for k in SAMPLE_BUDGETS}
        report = generate_budget_report(SAMPLE_BUDGETS, zero, 15)
        assert report["score"]["score"] == 100

    def test_all_zero_budgets(self):
        zero_b = {k: 0.0 for k in SAMPLE_BUDGETS}
        evals = evaluate_budget_usage(zero_b, SAMPLE_ACTUALS)
        # Inf ratios for non-zero actuals
        for ev in evals:
            if SAMPLE_ACTUALS[ev["category"]] > 0:
                assert ev["usage_ratio"] == float("inf")

    def test_day_31_projection(self):
        proj = project_month_end_usage({"Transport": 100.0}, day_of_month=31, days_in_month=31)
        assert proj["Transport"]["projected_month_end_kg"] == 100.0  # Exactly at current

    def test_conservative_budget_total(self):
        t = get_budget_template("conservative")
        cats_total = t["Transport"] + t["Electricity"] + t["Diet"] + t["Flights"]
        assert abs(cats_total - t["total_monthly_kg"]) < 1.0

    def test_moderate_budget_total(self):
        t = get_budget_template("moderate")
        cats_total = t["Transport"] + t["Electricity"] + t["Diet"] + t["Flights"]
        assert abs(cats_total - t["total_monthly_kg"]) < 1.0
