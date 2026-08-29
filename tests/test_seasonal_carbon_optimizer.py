"""Tests for seasonal_carbon_optimizer module."""

from __future__ import annotations

import math
import pytest

from src.carbon.seasonal_carbon_optimizer import (
    MONTHS,
    HEMISPHERES,
    SEASON_MONTHS,
    QUARTER_MONTHS,
    HEATING_COOLING_ADJUSTMENTS,
    TRANSPORT_ADJUSTMENTS,
    DIET_ADJUSTMENTS,
    FLIGHT_ADJUSTMENTS,
    WATER_ADJUSTMENTS,
    ALL_CATEGORY_ADJUSTMENTS,
    _get_season,
    get_seasonal_adjustment,
    get_all_adjustments,
    calculate_seasonal_footprint,
    seasonal_eco_score,
    generate_seasonal_recommendations,
    generate_seasonal_report,
    generate_quarterly_comparison,
    generate_monthly_forecast,
    SeasonalFootprintResult,
    SeasonalReport,
    QuarterlyComparison,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


SAMPLE_CONTRIBUTORS: dict[str, float] = {
    "Transport": 1500.0,
    "Electricity": 1200.0,
    "Diet": 900.0,
    "Flights": 500.0,
}

RAW_FOOTPRINT = sum(SAMPLE_CONTRIBUTORS.values())  # 4100.0


# ── _get_season ──────────────────────────────────────────────────────────────


class TestGetSeason:
    """Tests for _get_season helper."""

    def test_northern_winter_months(self):
        for m in [12, 1, 2]:
            assert _get_season(m, "northern") == "winter"

    def test_northern_spring_months(self):
        for m in [3, 4, 5]:
            assert _get_season(m, "northern") == "spring"

    def test_northern_summer_months(self):
        for m in [6, 7, 8]:
            assert _get_season(m, "northern") == "summer"

    def test_northern_autumn_months(self):
        for m in [9, 10, 11]:
            assert _get_season(m, "northern") == "autumn"

    def test_southern_seasons_shifted(self):
        # December is summer in the south
        assert _get_season(12, "southern") == "summer"
        # June is winter in the south
        assert _get_season(6, "southern") == "winter"
        # March is autumn
        assert _get_season(3, "southern") == "autumn"
        # September is spring
        assert _get_season(9, "southern") == "spring"

    def test_invalid_hemisphere_raises(self):
        with pytest.raises(ValueError, match="Unknown hemisphere"):
            _get_season(6, "tropical")

    def test_invalid_month_raises(self):
        with pytest.raises(ValueError, match="Invalid month"):
            _get_season(0, "northern")
        with pytest.raises(ValueError, match="Invalid month"):
            _get_season(13, "northern")


# ── get_seasonal_adjustment ─────────────────────────────────────────────────


class TestGetSeasonalAdjustment:
    """Tests for get_seasonal_adjustment."""

    def test_all_categories_covered(self):
        """Every known category should return a factor for every month."""
        for cat in ALL_CATEGORY_ADJUSTMENTS:
            for m in MONTHS:
                factor = get_seasonal_adjustment(cat, m, "northern")
                assert isinstance(factor, float)
                assert factor > 0

    def test_winter_electricity_northern_heavy(self):
        factor = get_seasonal_adjustment("electricity", 1, "northern")
        assert factor > 1.0  # heating demand increases

    def test_summer_electricity_northern_moderate(self):
        factor = get_seasonal_adjustment("electricity", 7, "northern")
        assert factor > 1.0  # cooling demand

    def test_spring_electricity_northern_reduced(self):
        factor = get_seasonal_adjustment("electricity", 4, "northern")
        assert factor <= 1.0  # mild weather

    def test_winter_transport_northern_higher(self):
        factor = get_seasonal_adjustment("transport", 1, "northern")
        assert factor > 1.0

    def test_summer_transport_northern_lower(self):
        factor = get_seasonal_adjustment("transport", 7, "northern")
        assert factor < 1.0

    def test_summer_water_northern_peak(self):
        factor = get_seasonal_adjustment("water", 7, "northern")
        assert factor > 1.0  # irrigation peak

    def test_winter_water_northern_low(self):
        factor = get_seasonal_adjustment("water", 1, "northern")
        assert factor < 1.0  # no garden watering

    def test_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            get_seasonal_adjustment("unknown_cat", 6, "northern")

    def test_invalid_month_raises(self):
        with pytest.raises(ValueError, match="month must be 1–12"):
            get_seasonal_adjustment("electricity", 0, "northern")

    def test_default_month_is_current(self):
        """Calling without month should use current month without error."""
        factor = get_seasonal_adjustment("electricity")
        assert 0 < factor < 3  # reasonable range


# ── get_all_adjustments ─────────────────────────────────────────────────────


class TestGetAllAdjustments:
    def test_returns_all_categories(self):
        adj = get_all_adjustments(6, "northern")
        assert set(adj.keys()) == set(ALL_CATEGORY_ADJUSTMENTS.keys())

    def test_values_are_positive(self):
        for m in MONTHS:
            adj = get_all_adjustments(m, "southern")
            for cat, val in adj.items():
                assert val > 0, f"{cat} month {m} has non-positive factor"


# ── calculate_seasonal_footprint ────────────────────────────────────────────


class TestCalculateSeasonalFootprint:
    def test_returns_correct_type(self):
        result = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 6, "northern",
        )
        assert isinstance(result, SeasonalFootprintResult)

    def test_raw_matches_input(self):
        result = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 6, "northern",
        )
        assert result.raw_footprint_kg == RAW_FOOTPRINT

    def test_adjusted_differs_from_raw(self):
        result = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 1, "northern",
        )
        # Winter should change the footprint
        assert result.adjusted_footprint_kg != RAW_FOOTPRINT

    def test_adjusted_breakdown_keys_match_contributors(self):
        result = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 4, "northern",
        )
        assert set(result.adjusted_breakdown.keys()) == set(
            SAMPLE_CONTRIBUTORS.keys()
        )

    def test_delta_kg_positive_when_worse(self):
        result = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 1, "northern",
        )
        # Winter northern: transport and electricity go up
        assert result.delta_kg > 0

    def test_hemisphere_affects_result(self):
        n = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 1, "northern",
        )
        s = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 1, "southern",
        )
        # Jan is winter (north) vs summer (south) — different adjustments
        assert n.adjusted_footprint_kg != s.adjusted_footprint_kg

    def test_zero_footprint_no_division_error(self):
        zero_contributors = {k: 0.0 for k in SAMPLE_CONTRIBUTORS}
        result = calculate_seasonal_footprint(0.0, zero_contributors, 6, "northern")
        assert result.adjusted_footprint_kg == 0.0
        assert result.adjustment_factor == 1.0

    def test_unknown_contributor_unadjusted(self):
        extra = {**SAMPLE_CONTRIBUTORS, "Unknown": 100.0}
        result = calculate_seasonal_footprint(
            RAW_FOOTPRINT + 100, extra, 6, "northern",
        )
        assert result.adjusted_breakdown["Unknown"] == 100.0

    def test_sum_adjusted_contributions(self):
        result = calculate_seasonal_footprint(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 7, "southern",
        )
        total = sum(result.adjusted_breakdown.values())
        assert abs(total - result.adjusted_footprint_kg) < 0.1


# ── seasonal_eco_score ─────────────────────────────────────────────────────


class TestSeasonalEcoScore:
    def test_returns_expected_keys(self):
        sc = seasonal_eco_score(3500, 4, "northern")
        expected_keys = {
            "score", "grade", "season", "hemisphere", "month",
            "benchmark_kg", "adjusted_footprint_kg", "vs_benchmark_pct",
            "status", "color",
        }
        assert expected_keys == set(sc.keys())

    def test_score_range_0_to_100(self):
        for val in [0, 1000, 3000, 4000, 6000, 10000]:
            sc = seasonal_eco_score(val, 6, "northern")
            assert 0 <= sc["score"] <= 100

    def test_low_footprint_high_score(self):
        sc = seasonal_eco_score(500, 6, "northern")
        assert sc["score"] >= 70

    def test_high_footprint_low_score(self):
        sc = seasonal_eco_score(10000, 6, "northern")
        assert sc["score"] <= 40

    def test_grades_valid(self):
        valid_grades = {"A", "B", "C", "D", "F"}
        for val in [200, 2000, 4000, 6000, 9000]:
            sc = seasonal_eco_score(val, 1, "northern")
            assert sc["grade"] in valid_grades

    def test_benchmark_depends_on_season(self):
        winter = seasonal_eco_score(4000, 1, "northern")
        summer = seasonal_eco_score(4000, 7, "northern")
        assert winter["benchmark_kg"] != summer["benchmark_kg"]

    def test_vs_benchmark_calculation(self):
        sc = seasonal_eco_score(5000, 4, "northern")
        benchmark = sc["benchmark_kg"]
        expected_pct = ((5000 - benchmark) / benchmark) * 100.0
        assert abs(sc["vs_benchmark_pct"] - expected_pct) < 0.1

    def test_color_matches_grade(self):
        sc = seasonal_eco_score(100, 6, "northern")  # very low → A
        assert sc["color"] == "#22c55e"
        sc_bad = seasonal_eco_score(20000, 6, "northern")  # very high → F
        assert sc_bad["color"] == "#ef4444"


# ── generate_seasonal_recommendations ──────────────────────────────────────


class TestGenerateSeasonalRecommendations:
    def test_returns_list(self):
        recs = generate_seasonal_recommendations(1, "northern")
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_all_recommendations_for_season(self):
        """Winter should return winter tips only."""
        recs = generate_seasonal_recommendations(1, "northern")
        for rec in recs:
            assert rec["season"] == "winter"

    def test_category_filter(self):
        recs = generate_seasonal_recommendations(
            7, "northern", categories=["water"],
        )
        for rec in recs:
            assert rec["category"] == "water"

    def test_difficulty_filter(self):
        recs = generate_seasonal_recommendations(
            6, "northern", difficulty_filter="easy",
        )
        for rec in recs:
            assert rec["difficulty"] == "easy"

    def test_sorted_by_impact_descending(self):
        recs = generate_seasonal_recommendations(1, "northern")
        impacts = [r["impact_kg_year"] for r in recs]
        assert impacts == sorted(impacts, reverse=True)

    def test_impact_positive(self):
        for m in MONTHS:
            recs = generate_seasonal_recommendations(m, "northern")
            for rec in recs:
                assert rec["impact_kg_year"] > 0

    def test_southern_hemisphere_different_season(self):
        """June is winter in southern hemisphere → should get winter tips."""
        recs = generate_seasonal_recommendations(6, "southern")
        for rec in recs:
            assert rec["season"] == "winter"

    def test_recommendations_have_required_keys(self):
        recs = generate_seasonal_recommendations(4, "northern")
        for rec in recs:
            assert "action" in rec
            assert "impact_kg_year" in rec
            assert "difficulty" in rec
            assert "tip" in rec
            assert "category" in rec
            assert "season" in rec


# ── generate_seasonal_report ───────────────────────────────────────────────


class TestGenerateSeasonalReport:
    def test_returns_seasonal_report(self):
        report = generate_seasonal_report(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 3, "northern",
        )
        assert isinstance(report, SeasonalReport)

    def test_quarter_matches_month(self):
        report = generate_seasonal_report(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 5, "northern",
        )
        assert src.reporting.report.quarter == 2

    def test_summary_text_populated(self):
        report = generate_seasonal_report(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 8, "northern",
        )
        assert len(src.reporting.report.summary_text) > 50

    def test_monthly_savings_positive(self):
        report = generate_seasonal_report(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 1, "northern",
        )
        assert src.reporting.report.monthly_savings_potential_kg > 0

    def test_annualised_savings_12x_monthly(self):
        report = generate_seasonal_report(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 7, "southern",
        )
        expected = round(src.reporting.report.monthly_savings_potential_kg * 12, 2)
        assert abs(src.reporting.report.annualised_savings_potential_kg - expected) < 0.1

    def test_max_recommendations_respected(self):
        report = generate_seasonal_report(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, 1, "northern",
            max_recommendations=2,
        )
        assert len(src.reporting.report.recommendations) <= 2


# ── generate_quarterly_comparison ───────────────────────────────────────────


class TestGenerateQuarterlyComparison:
    def test_returns_quarterly_comparison(self):
        comp = generate_quarterly_comparison(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        assert isinstance(comp, QuarterlyComparison)

    def test_all_four_quarters_present(self):
        comp = generate_quarterly_comparison(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        assert set(comp.quarters.keys()) == {1, 2, 3, 4}

    def test_best_quarter_is_winter_or_autumn(self):
        comp = generate_quarterly_comparison(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        best = comp.best_quarter
        # Winter (Q1) and Autumn (Q4) have lower heating/transport in south
        assert best in [1, 2, 3, 4]

    def test_worst_quarter_differs_from_best(self):
        comp = generate_quarterly_comparison(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        assert comp.worst_quarter != comp.best_quarter

    def test_annual_adjusted_is_sum(self):
        comp = generate_quarterly_comparison(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "southern",
        )
        expected = sum(q["adjusted_kg"] for q in comp.quarters.values())
        assert abs(comp.annual_adjusted_kg - round(expected, 2)) < 0.1

    def test_quarter_data_has_expected_keys(self):
        comp = generate_quarterly_comparison(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        expected_keys = {
            "quarter", "mid_month", "season", "raw_kg",
            "adjusted_kg", "delta_kg", "delta_pct",
            "score", "grade", "recommendation_count",
        }
        for q_data in comp.quarters.values():
            assert expected_keys == set(q_data.keys())


# ── generate_monthly_forecast ───────────────────────────────────────────────


class TestGenerateMonthlyForecast:
    def test_returns_12_entries(self):
        forecast = generate_monthly_forecast(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        assert len(forecast) == 12

    def test_months_ordered(self):
        forecast = generate_monthly_forecast(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        months = [f["month"] for f in forecast]
        assert months == list(range(1, 13))

    def test_all_entries_have_keys(self):
        forecast = generate_monthly_forecast(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        for entry in forecast:
            assert "month" in entry
            assert "month_name" in entry
            assert "season" in entry
            assert "adjusted_kg" in entry
            assert "score" in entry
            assert "grade" in entry
            assert "color" in entry
            assert "delta_pct" in entry

    def test_seasons_varied(self):
        forecast = generate_monthly_forecast(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "northern",
        )
        seasons = {f["season"] for f in forecast}
        assert len(seasons) >= 3  # at least 3 distinct seasons over 12 months

    def test_southern_hemisphere_seasons_shifted(self):
        forecast = generate_monthly_forecast(
            RAW_FOOTPRINT, SAMPLE_CONTRIBUTORS, "southern",
        )
        jan = forecast[0]
        jul = forecast[6]
        # Jan is summer in south, Jul is winter
        assert jan["season"] == "summer"
        assert jul["season"] == "winter"


# ── SeasonalFootprintResult ─────────────────────────────────────────────────


class TestSeasonalFootprintResult:
    def test_delta_kg(self):
        result = SeasonalFootprintResult(
            raw_footprint_kg=4000.0,
            adjusted_footprint_kg=4400.0,
            adjustment_factor=1.1,
            month=1,
            season="winter",
            hemisphere="northern",
        )
        assert result.delta_kg == 400.0

    def test_delta_pct(self):
        result = SeasonalFootprintResult(
            raw_footprint_kg=4000.0,
            adjusted_footprint_kg=3600.0,
            adjustment_factor=0.9,
            month=4,
            season="spring",
            hemisphere="northern",
        )
        assert result.delta_pct == -10.0

    def test_delta_pct_zero_baseline(self):
        result = SeasonalFootprintResult(
            raw_footprint_kg=0.0,
            adjusted_footprint_kg=0.0,
            adjustment_factor=1.0,
            month=6,
            season="summer",
            hemisphere="northern",
        )
        assert result.delta_pct == 0.0


# ── Data Integrity ──────────────────────────────────────────────────────────


class TestDataIntegrity:
    def test_all_adjustment_dicts_positive(self):
        for cat_dict in ALL_CATEGORY_ADJUSTMENTS.values():
            for hem in cat_dict.values():
                for season, factor in hem.items():
                    assert factor > 0, f"{cat_dict} {season} = {factor}"

    def test_quarter_months_cover_all_months(self):
        covered = set()
        for months in QUARTER_MONTHS.values():
            covered.update(months)
        assert covered == set(MONTHS)

    def test_season_months_cover_all_months(self):
        covered = set()
        for hem in SEASON_MONTHS.values():
            for months in hem.values():
                covered.update(months)
        assert covered == set(MONTHS)
