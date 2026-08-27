"""Tests for carbon_benchmarking module."""

from __future__ import annotations

import math
import pytest

from carbon_benchmarking import (
    COUNTRY_BENCHMARKS,
    LIFESTYLE_ARCHETYPES,
    GLOBAL_PERCENTILE_DISTRIBUTION,
    BenchmarkResult,
    PeerGroupMatch,
    TrendEntry,
    TrendAnalysis,
    LeaderboardEntry,
    FullBenchmarkReport,
    compare_against_country,
    compare_against_all_countries,
    compute_global_percentile,
    find_closest_lifestyle,
    analyse_trend,
    generate_benchmark_insights,
    generate_improvement_actions,
    build_full_benchmark_report,
    list_available_countries,
    list_lifestyle_archetypes,
)


# ── Sample Data ──────────────────────────────────────────────────────────────

SAMPLE_CONTRIBUTORS: dict[str, float] = {
    "Transport": 2000,
    "Electricity": 1500,
    "Diet": 1000,
    "Flights": 500,
}
SAMPLE_FOOTPRINT = sum(SAMPLE_CONTRIBUTORS.values())  # 5000


# ── BenchmarkResult ──────────────────────────────────────────────────────────


class TestBenchmarkResult:
    def test_computes_delta_kg(self):
        r = BenchmarkResult(
            reference_name="Test",
            reference_kg=4000,
            user_kg=5000,
            delta_kg=0,
            delta_pct=0,
        )
        assert r.delta_kg == 1000.0

    def test_computes_delta_pct(self):
        r = BenchmarkResult(
            reference_name="Test",
            reference_kg=4000,
            user_kg=5000,
            delta_kg=0,
            delta_pct=0,
        )
        assert r.delta_pct == 25.0

    def test_is_below_true(self):
        r = BenchmarkResult(
            reference_name="Test",
            reference_kg=6000,
            user_kg=5000,
            delta_kg=0,
            delta_pct=0,
        )
        assert r.is_below is True

    def test_is_below_false(self):
        r = BenchmarkResult(
            reference_name="Test",
            reference_kg=4000,
            user_kg=5000,
            delta_kg=0,
            delta_pct=0,
        )
        assert r.is_below is False

    def test_zero_reference_no_division_error(self):
        r = BenchmarkResult(
            reference_name="Test",
            reference_kg=0,
            user_kg=500,
            delta_kg=0,
            delta_pct=0,
        )
        assert r.delta_pct == 0.0


# ── Country Comparisons ─────────────────────────────────────────────────────


class TestCountryComparison:
    def test_all_countries_covered(self):
        for code in COUNTRY_BENCHMARKS:
            result = compare_against_country(
                SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS, code,
            )
            assert isinstance(result, BenchmarkResult)
            assert result.reference_kg > 0

    def test_vs_global_average(self):
        result = compare_against_country(
            SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS, "Global",
        )
        assert result.reference_kg == 4700
        assert result.delta_kg == 300.0

    def test_vs_nigeria_low_benchmark(self):
        result = compare_against_country(
            SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS, "Nigeria",
        )
        assert result.is_below is False  # 5000 > 550
        assert result.delta_kg > 0

    def test_vs_australia_high_benchmark(self):
        result = compare_against_country(
            SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS, "Australia",
        )
        assert result.is_below is True  # 5000 < 15400

    def test_category_deltas_populated(self):
        result = compare_against_country(
            SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS, "US",
        )
        assert len(result.category_deltas) == 4
        assert "Transport" in result.category_deltas

    def test_unknown_country_raises(self):
        with pytest.raises(ValueError, match="Unknown country"):
            compare_against_country(5000, SAMPLE_CONTRIBUTORS, "Atlantis")

    def test_all_countries_comparison(self):
        results = compare_against_all_countries(
            SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS,
        )
        assert len(results) == len(COUNTRY_BENCHMARKS)
        # Sorted by delta ascending
        for i in range(len(results) - 1):
            assert results[i].delta_kg <= results[i + 1].delta_kg


# ── Global Percentile ───────────────────────────────────────────────────────


class TestGlobalPercentile:
    def test_very_low_footprint(self):
        assert compute_global_percentile(100) == 1

    def test_below_50th(self):
        assert compute_global_percentile(2000) <= 30

    def test_average(self):
        assert compute_global_percentile(4700) <= 60
        assert compute_global_percentile(4700) >= 40

    def test_high_footprint(self):
        assert compute_global_percentile(15000) >= 90

    def test_very_high(self):
        assert compute_global_percentile(25000) == 99

    def test_exact_match(self):
        pct = compute_global_percentile(4700)
        assert 40 <= pct <= 60


# ── Lifestyle Matching ──────────────────────────────────────────────────────


class TestLifestyleMatching:
    def test_all_archetypes_accessible(self):
        for key in LIFESTYLE_ARCHETYPES:
            arch = LIFESTYLE_ARCHETYPES[key]
            assert "name" in arch
            assert "footprint_kg" in arch
            assert "category_breakdown" in arch

    def test_low_footprint_matches_eco_warrior(self):
        low_users = {
            "Transport": 200,
            "Electricity": 900,
            "Diet": 500,
            "Flights": 100,
        }
        match = find_closest_lifestyle(1700, low_users)
        assert match.similarity_score > 50
        # Should be close to urban_eco_warrior (2200 kg)
        assert match.archetype_key in ("urban_eco_warrior", "minimalist_rural", "student")

    def test_high_footprint_matches_high_emitter(self):
        high_users = {
            "Transport": 5000,
            "Electricity": 4500,
            "Diet": 3000,
            "Flights": 3500,
        }
        match = find_closest_lifestyle(16000, high_users)
        assert match.archetype_key == "luxury_high_emitter"
        assert match.similarity_score > 90

    def test_similarity_score_range(self):
        match = find_closest_lifestyle(SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS)
        assert 0 <= match.similarity_score <= 100

    def test_category_distances_populated(self):
        match = find_closest_lifestyle(SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS)
        assert len(match.category_distances) > 0

    def test_result_has_required_fields(self):
        match = find_closest_lifestyle(SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS)
        assert match.archetype_key
        assert match.archetype_name
        assert match.description
        assert match.archetype_kg > 0
        assert match.user_kg == SAMPLE_FOOTPRINT


# ── Trend Analysis ───────────────────────────────────────────────────────────


class TestTrendAnalysis:
    def test_empty_history(self):
        result = analyse_trend([])
        assert result.direction == "no_data"
        assert result.entries == []

    def test_single_entry(self):
        history = [{"total_emission": 5000, "eco_score": 50, "created_at": "2024-01-01"}]
        result = analyse_trend(history)
        assert result.months_of_data == 1
        assert result.direction == "stable"

    def test_improving_trend(self):
        history = [
            {"total_emission": 6000, "eco_score": 40, "created_at": "2024-01-01"},
            {"total_emission": 5000, "eco_score": 50, "created_at": "2024-02-01"},
            {"total_emission": 4000, "eco_score": 60, "created_at": "2024-03-01"},
        ]
        result = analyse_trend(history)
        assert result.direction == "improving"
        assert result.total_change_kg < 0
        assert result.total_change_pct < 0

    def test_worsening_trend(self):
        history = [
            {"total_emission": 3000, "eco_score": 70, "created_at": "2024-01-01"},
            {"total_emission": 4000, "eco_score": 60, "created_at": "2024-02-01"},
            {"total_emission": 5500, "eco_score": 45, "created_at": "2024-03-01"},
        ]
        result = analyse_trend(history)
        assert result.direction == "worsening"
        assert result.total_change_kg > 0

    def test_entries_chronological(self):
        history = [
            {"total_emission": 5000, "eco_score": 50, "created_at": "2024-03-01"},
            {"total_emission": 4500, "eco_score": 55, "created_at": "2024-01-01"},
            {"total_emission": 4800, "eco_score": 52, "created_at": "2024-02-01"},
        ]
        result = analyse_trend(history)
        assert result.entries[0].footprint_kg == 4500  # Jan first
        assert result.entries[2].footprint_kg == 5000  # Mar last

    def test_avg_best_worst(self):
        history = [
            {"total_emission": 5000, "eco_score": 50, "created_at": "2024-01-01"},
            {"total_emission": 3000, "eco_score": 70, "created_at": "2024-02-01"},
            {"total_emission": 6000, "eco_score": 40, "created_at": "2024-03-01"},
        ]
        result = analyse_trend(history)
        assert result.best_kg == 3000
        assert result.worst_kg == 6000
        assert result.avg_footprint_kg == 4666.67

    def test_streak_improving(self):
        history = [
            {"total_emission": 5000, "eco_score": 50, "created_at": "2024-01-01"},
            {"total_emission": 4500, "eco_score": 55, "created_at": "2024-02-01"},
            {"total_emission": 4000, "eco_score": 60, "created_at": "2024-03-01"},
        ]
        result = analyse_trend(history)
        assert result.streak_improving >= 1

    def test_streak_worsening(self):
        history = [
            {"total_emission": 3000, "eco_score": 70, "created_at": "2024-01-01"},
            {"total_emission": 4000, "eco_score": 60, "created_at": "2024-02-01"},
            {"total_emission": 5000, "eco_score": 50, "created_at": "2024-03-01"},
        ]
        result = analyse_trend(history)
        assert result.streak_worsening >= 1

    def test_trend_entry_fields(self):
        history = [
            {"total_emission": 5000, "eco_score": 50, "created_at": "2024-01-01"},
        ]
        result = analyse_trend(history)
        entry = result.entries[0]
        assert isinstance(entry, TrendEntry)
        assert entry.footprint_kg == 5000
        assert entry.eco_score == 50


# ── Insights ─────────────────────────────────────────────────────────────────


class TestInsights:
    def test_returns_list_of_strings(self):
        insights = generate_benchmark_insights(
            SAMPLE_FOOTPRINT, 50, SAMPLE_CONTRIBUTORS, "Global",
        )
        assert isinstance(insights, list)
        assert len(insights) >= 3
        for insight in insights:
            assert isinstance(insight, str)
            assert len(insight) > 10

    def test_below_average_insight(self):
        """User at 2000 kg should be below global avg (4700)."""
        insights = generate_benchmark_insights(
            2000, 80, {"Transport": 500, "Electricity": 700, "Diet": 500, "Flights": 100},
            "Global",
        )
        below_insight = [i for i in insights if "LESS" in i]
        assert len(below_insight) == 1

    def test_above_average_insight(self):
        """User at 8000 kg should be above global avg."""
        insights = generate_benchmark_insights(
            8000, 30, {"Transport": 3000, "Electricity": 2500, "Diet": 1500, "Flights": 700},
            "Global",
        )
        above_insight = [i for i in insights if "MORE" in i]
        assert len(above_insight) == 1

    def test_paris_target_met(self):
        insights = generate_benchmark_insights(
            1500, 90, {"Transport": 300, "Electricity": 500, "Diet": 400, "Flights": 100},
            "Global",
        )
        paris_insight = [i for i in insights if "Paris" in i]
        assert len(paris_insight) == 1
        assert "within" in paris_insight[0] or "Excellent" in paris_insight[0]

    def test_paris_target_near(self):
        insights = generate_benchmark_insights(
            2200, 70, {"Transport": 600, "Electricity": 700, "Diet": 500, "Flights": 100},
            "Global",
        )
        paris_insight = [i for i in insights if "Paris" in i]
        assert len(paris_insight) == 1

    def test_lifestyle_insight_present(self):
        insights = generate_benchmark_insights(
            SAMPLE_FOOTPRINT, 50, SAMPLE_CONTRIBUTORS, "Global",
        )
        lifestyle = [i for i in insights if "lifestyle" in i.lower()]
        assert len(lifestyle) >= 1

    def test_top_contributor_insight(self):
        contributors = {
            "Transport": 5000,
            "Electricity": 1000,
            "Diet": 500,
            "Flights": 300,
        }
        insights = generate_benchmark_insights(6800, 35, contributors, "Global")
        top_cat = [i for i in insights if "Transport" in i]
        assert len(top_cat) == 1


# ── Improvement Actions ─────────────────────────────────────────────────────


class TestImprovementActions:
    def test_returns_list(self):
        actions = generate_improvement_actions(
            SAMPLE_FOOTPRINT, SAMPLE_CONTRIBUTORS, "Global",
        )
        assert isinstance(actions, list)

    def test_actions_sorted_by_savings(self):
        actions = generate_improvement_actions(
            12000, {"Transport": 5000, "Electricity": 3500, "Diet": 2000, "Flights": 1500},
            "Global",
        )
        if len(actions) >= 2:
            for i in range(len(actions) - 1):
                assert actions[i]["potential_savings_kg"] >= actions[i + 1]["potential_savings_kg"]

    def test_action_has_required_keys(self):
        actions = generate_improvement_actions(
            10000, {"Transport": 4000, "Electricity": 3000, "Diet": 1500, "Flights": 1000},
            "Global",
        )
        for action in actions:
            assert "category" in action
            assert "action" in action
            assert "potential_savings_kg" in action
            assert "difficulty" in action
            assert "impact" in action

    def test_no_actions_for_perfect_user(self):
        """User below all benchmarks should get no actions."""
        low = {
            "Transport": 100,
            "Electricity": 200,
            "Diet": 150,
            "Flights": 50,
        }
        actions = generate_improvement_actions(500, low, "Global")
        assert len(actions) == 0

    def test_transport_actions_for_high_transport(self):
        contributors = {
            "Transport": 5000,
            "Electricity": 1000,
            "Diet": 500,
            "Flights": 200,
        }
        actions = generate_improvement_actions(6700, contributors, "Global")
        transport_actions = [a for a in actions if a["category"] == "Transport"]
        assert len(transport_actions) > 0

    def test_actions_all_positive_savings(self):
        actions = generate_improvement_actions(
            10000, {"Transport": 4000, "Electricity": 3000, "Diet": 1500, "Flights": 1000},
            "Global",
        )
        for action in actions:
            assert action["potential_savings_kg"] > 0


# ── Full Report Builder ─────────────────────────────────────────────────────


class TestFullReport:
    def test_report_structure(self):
        report = build_full_benchmark_report(
            user_id=1,
            footprint_kg=SAMPLE_FOOTPRINT,
            eco_score=50,
            contributors=SAMPLE_CONTRIBUTORS,
            country_code="Global",
        )
        assert isinstance(report, FullBenchmarkReport)
        assert report.user_id == 1
        assert report.footprint_kg == SAMPLE_FOOTPRINT
        assert report.eco_score == 50

    def test_country_benchmarks_populated(self):
        report = build_full_benchmark_report(
            user_id=1,
            footprint_kg=SAMPLE_FOOTPRINT,
            eco_score=50,
            contributors=SAMPLE_CONTRIBUTORS,
            country_code="US",
        )
        assert len(report.country_benchmarks) == len(COUNTRY_BENCHMARKS)

    def test_lifestyle_match_populated(self):
        report = build_full_benchmark_report(
            user_id=1,
            footprint_kg=SAMPLE_FOOTPRINT,
            eco_score=50,
            contributors=SAMPLE_CONTRIBUTORS,
            country_code="Global",
        )
        assert report.lifestyle_match is not None
        assert report.lifestyle_match.similarity_score > 0

    def test_global_percentile(self):
        report = build_full_benchmark_report(
            user_id=1,
            footprint_kg=SAMPLE_FOOTPRINT,
            eco_score=50,
            contributors=SAMPLE_CONTRIBUTORS,
            country_code="Global",
        )
        assert 1 <= report.global_percentile <= 99

    def test_insights_populated(self):
        report = build_full_benchmark_report(
            user_id=1,
            footprint_kg=SAMPLE_FOOTPRINT,
            eco_score=50,
            contributors=SAMPLE_CONTRIBUTORS,
            country_code="Global",
        )
        assert len(report.insights) >= 3

    def test_improvement_actions_populated(self):
        report = build_full_benchmark_report(
            user_id=1,
            footprint_kg=10000,
            eco_score=30,
            contributors={"Transport": 4000, "Electricity": 3000, "Diet": 1500, "Flights": 1000},
            country_code="Global",
        )
        assert len(report.improvement_actions) > 0

    def test_comparison_date_set(self):
        report = build_full_benchmark_report(
            user_id=1,
            footprint_kg=SAMPLE_FOOTPRINT,
            eco_score=50,
            contributors=SAMPLE_CONTRIBUTORS,
            country_code="Global",
        )
        assert len(report.comparison_date) > 0


# ── Helper Functions ─────────────────────────────────────────────────────────


class TestHelpers:
    def test_list_countries(self):
        countries = list_available_countries()
        assert len(countries) == len(COUNTRY_BENCHMARKS)
        for c in countries:
            assert "code" in c
            assert "name" in c
            assert "per_capita_kg" in c

    def test_list_archetypes(self):
        archetypes = list_lifestyle_archetypes()
        assert len(archetypes) == len(LIFESTYLE_ARCHETYPES)
        for a in archetypes:
            assert "key" in a
            assert "name" in a
            assert "footprint_kg" in a


# ── Data Integrity ──────────────────────────────────────────────────────────


class TestDataIntegrity:
    def test_all_benchmarks_positive(self):
        for code, info in COUNTRY_BENCHMARKS.items():
            assert info["per_capita_kg"] > 0, f"{code} has non-positive benchmark"
            assert "category_breakdown" in info, f"{code} missing category_breakdown"

    def test_benchmark_categories_sum_close(self):
        """Category breakdown should roughly sum to per_capita (within 20%)."""
        for code, info in COUNTRY_BENCHMARKS.items():
            cat_sum = sum(info["category_breakdown"].values())
            ratio = cat_sum / info["per_capita_kg"]
            assert 0.6 < ratio < 1.4, (
                f"{code}: category sum {cat_sum} vs per_capita {info['per_capita_kg']}"
            )

    def test_percentile_distribution_sorted(self):
        sorted_pcts = sorted(GLOBAL_PERCENTILE_DISTRIBUTION.keys())
        assert sorted_pcts == [1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99]

    def test_percentile_distribution_monotonic(self):
        sorted_items = sorted(GLOBAL_PERCENTILE_DISTRIBUTION.items())
        for i in range(len(sorted_items) - 1):
            assert sorted_items[i][1] <= sorted_items[i + 1][1]

    def test_archetypes_have_all_categories(self):
        required_cats = {"Transport", "Electricity", "Diet", "Flights"}
        for key, arch in LIFESTYLE_ARCHETYPES.items():
            assert set(arch["category_breakdown"].keys()) == required_cats, (
                f"{key} missing categories"
            )

    def test_archetype_sum_matches_footprint(self):
        for key, arch in LIFESTYLE_ARCHETYPES.items():
            cat_sum = sum(arch["category_breakdown"].values())
            assert cat_sum == arch["footprint_kg"], (
                f"{key}: category sum {cat_sum} != footprint_kg {arch['footprint_kg']}"
            )
