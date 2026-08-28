"""Tests for the Carbon Footprint Comparison & Peer Benchmarking engine.

Comprehensive test suite covering percentile ranking, archetype matching,
category comparisons, reduction targets, readiness scoring, projection
timelines, equivalence calculations, and the full report builder.
"""

from __future__ import annotations

import math
import pytest

from footprint_comparison import (
    COUNTRY_AVERAGES,
    IPCC_TARGETS,
    LIFESTYLE_ARCHETYPES,
    CATEGORY_META,
    READINESS_TIERS,
    compare_categories,
    compute_percentile,
    match_archetypes,
    compute_reduction_targets,
    compute_readiness_score,
    estimate_peer_group_average,
    generate_category_deep_dive,
    compute_projection_timeline,
    compute_equivalents,
    build_full_comparison_report,
    get_country_list,
    get_archetype_list,
    get_ipcc_target_list,
    format_kg_to_tonnes,
    rating_color,
    get_benchmark_country,
    _normal_cdf,
    CategoryComparison,
    PercentileResult,
    ArchetypeMatch,
    ReductionTarget,
    ReadinessScore,
    ComparisonReport,
)


# ── Fixture data ─────────────────────────────────────────────────────────────

TYPICAL_USER_CONTRIBUTORS = {
    "transport": 1500.0,
    "electricity": 1000.0,
    "diet": 800.0,
    "flights": 600.0,
}

TYPICAL_USER_TOTAL = sum(TYPICAL_USER_CONTRIBUTORS.values())  # 3900.0

LOW_EMISSION_USER = {
    "transport": 200.0,
    "electricity": 300.0,
    "diet": 200.0,
    "flights": 0.0,
}

HIGH_EMISSION_USER = {
    "transport": 4000.0,
    "electricity": 3500.0,
    "diet": 2000.0,
    "flights": 3000.0,
}


# ── compare_categories ───────────────────────────────────────────────────────

class TestCompareCategories:
    def test_returns_comparison_for_all_categories(self):
        result = compare_categories(TYPICAL_USER_CONTRIBUTORS, TYPICAL_USER_CONTRIBUTORS)
        assert len(result) == 4

    def test_equal_values_gives_average_rating(self):
        result = compare_categories(TYPICAL_USER_CONTRIBUTORS, TYPICAL_USER_CONTRIBUTORS)
        for comp in result:
            assert comp.rating == "average"
            assert comp.difference_kg == 0.0
            assert comp.percent_of_benchmark == 100.0

    def test_low_user_gives_excellent_rating(self):
        low_bench = {"transport": 5000.0, "electricity": 5000.0, "diet": 5000.0, "flights": 5000.0}
        result = compare_categories(LOW_EMISSION_USER, low_bench)
        for comp in result:
            assert comp.rating == "excellent"

    def test_high_user_gives_critical_rating(self):
        low_bench = {"transport": 100.0, "electricity": 100.0, "diet": 100.0, "flights": 100.0}
        result = compare_categories(HIGH_EMISSION_USER, low_bench)
        for comp in result:
            assert comp.rating == "critical"

    def test_difference_calculation(self):
        user = {"transport": 1000.0, "electricity": 500.0, "diet": 300.0, "flights": 200.0}
        bench = {"transport": 800.0, "electricity": 600.0, "diet": 300.0, "flights": 100.0}
        result = compare_categories(user, bench)

        transport_comp = next(c for c in result if "Transport" in c.name)
        assert transport_comp.difference_kg == pytest.approx(200.0, abs=0.1)
        assert transport_comp.percent_of_benchmark == pytest.approx(125.0, abs=0.1)

        elec_comp = next(c for c in result if "Electricity" in c.name)
        assert elec_comp.difference_kg == pytest.approx(-100.0, abs=0.1)

    def test_empty_user_contributors(self):
        empty_user = {"transport": 0, "electricity": 0, "diet": 0, "flights": 0}
        result = compare_categories(empty_user, TYPICAL_USER_CONTRIBUTORS)
        for comp in result:
            assert comp.rating == "excellent"
            assert comp.percent_of_benchmark == 0.0

    def test_zero_benchmark_handles_gracefully(self):
        zero_bench = {"transport": 0, "electricity": 0, "diet": 0, "flights": 0}
        result = compare_categories(TYPICAL_USER_CONTRIBUTORS, zero_bench)
        for comp in result:
            assert comp.percent_of_benchmark == 0.0


# ── compute_percentile ───────────────────────────────────────────────────────

class TestComputePercentile:
    def test_very_low_footprint_ranks_high(self):
        result = compute_percentile(500.0)
        assert result.percentile >= 90
        assert "Top" in result.rank_label

    def test_very_high_footprint_ranks_low(self):
        result = compute_percentile(15000.0)
        assert result.percentile <= 20

    def test_average_footprint_near_50th(self):
        result = compute_percentile(4700.0)
        assert 40 <= result.percentile <= 60

    def test_zero_footprint_handled(self):
        result = compute_percentile(0.0)
        assert result.percentile >= 90

    def test_negative_footprint_handled(self):
        result = compute_percentile(-100.0)
        assert result.percentile >= 90

    def test_result_has_required_fields(self):
        result = compute_percentile(3000.0)
        assert hasattr(result, "percentile")
        assert hasattr(result, "rank_label")
        assert hasattr(result, "better_than_pct")
        assert hasattr(result, "worse_than_pct")
        assert hasattr(result, "context")
        assert result.better_than_pct + result.worse_than_pct == pytest.approx(100.0, abs=0.1)

    def test_percentile_monotonically_decreasing(self):
        """Higher footprint should give lower (worse) percentile."""
        values = [500, 1000, 2000, 4000, 8000, 15000]
        percentiles = [compute_percentile(v).percentile for v in values]
        for i in range(len(percentiles) - 1):
            assert percentiles[i] >= percentiles[i + 1]


class TestNormalCdf:
    def test_cdf_at_zero(self):
        assert _normal_cdf(0.0) == pytest.approx(0.5, abs=0.01)

    def test_cdf_large_positive(self):
        assert _normal_cdf(3.0) > 0.99

    def test_cdf_large_negative(self):
        assert _normal_cdf(-3.0) < 0.01


# ── match_archetypes ─────────────────────────────────────────────────────────

class TestMatchArchetypes:
    def test_returns_all_archetypes(self):
        matches = match_archetypes(TYPICAL_USER_CONTRIBUTORS, TYPICAL_USER_TOTAL)
        assert len(matches) == len(LIFESTYLE_ARCHETYPES)

    def test_results_sorted_by_similarity(self):
        matches = match_archetypes(TYPICAL_USER_CONTRIBUTORS, TYPICAL_USER_TOTAL)
        for i in range(len(matches) - 1):
            assert matches[i].similarity_score >= matches[i + 1].similarity_score

    def test_low_emission_matches_minimalist(self):
        low_total = sum(LOW_EMISSION_USER.values())
        matches = match_archetypes(LOW_EMISSION_USER, low_total)
        assert matches[0].archetype_name == "Minimalist Vegan"

    def test_high_emission_matches_heavy_consumer(self):
        high_total = sum(HIGH_EMISSION_USER.values())
        matches = match_archetypes(HIGH_EMISSION_USER, high_total)
        assert matches[0].archetype_name == "Heavy Consumer"

    def test_similarity_scores_between_0_and_1(self):
        matches = match_archetypes(TYPICAL_USER_CONTRIBUTORS, TYPICAL_USER_TOTAL)
        for match in matches:
            assert 0.0 <= match.similarity_score <= 1.0

    def test_top_match_has_highest_similarity(self):
        matches = match_archetypes(TYPICAL_USER_CONTRIBUTORS, TYPICAL_USER_TOTAL)
        top_score = matches[0].similarity_score
        assert all(m.similarity_score <= top_score for m in matches)

    def test_zero_emissions_handled(self):
        zero_user = {"transport": 0, "electricity": 0, "diet": 0, "flights": 0}
        matches = match_archetypes(zero_user, 0.0)
        assert len(matches) == len(LIFESTYLE_ARCHETYPES)


# ── compute_reduction_targets ────────────────────────────────────────────────

class TestComputeReductionTargets:
    def test_returns_all_ipcc_targets(self):
        targets = compute_reduction_targets(TYPICAL_USER_TOTAL, TYPICAL_USER_CONTRIBUTORS)
        assert len(targets) == len(IPCC_TARGETS)

    def test_high_footprint_has_large_gap(self):
        targets = compute_reduction_targets(10000.0, HIGH_EMISSION_USER)
        assert any(t.gap_kg > 5000 for t in targets)

    def test_low_footprint_has_small_gap(self):
        targets = compute_reduction_targets(1000.0, LOW_EMISSION_USER)
        assert any(t.gap_kg == 0.0 for t in targets)

    def test_targets_sorted_by_gap(self):
        targets = compute_reduction_targets(TYPICAL_USER_TOTAL, TYPICAL_USER_CONTRIBUTORS)
        gaps = [t.gap_kg for t in targets]
        assert gaps == sorted(gaps)

    def test_feasibility_calculation(self):
        targets = compute_reduction_targets(10000.0, HIGH_EMISSION_USER)
        for t in targets:
            if t.target_kg * 1.1 < 10000.0:
                assert t.feasible is True
            else:
                assert t.feasible is False

    def test_reduction_pct_calculation(self):
        targets = compute_reduction_targets(5000.0, TYPICAL_USER_CONTRIBUTORS)
        for t in targets:
            expected_pct = (t.gap_kg / 5000.0 * 100) if 5000.0 > 0 else 0.0
            assert t.reduction_needed_pct == pytest.approx(expected_pct, abs=0.1)

    def test_all_targets_have_source(self):
        targets = compute_reduction_targets(TYPICAL_USER_TOTAL, TYPICAL_USER_CONTRIBUTORS)
        for t in targets:
            assert t.source  # Non-empty string


# ── compute_readiness_score ─────────────────────────────────────────────────

class TestComputeReadinessScore:
    def test_score_between_0_and_100(self):
        result = compute_readiness_score(TYPICAL_USER_TOTAL, TYPICAL_USER_CONTRIBUTORS)
        assert 0 <= result.score <= 100

    def test_low_emission_gets_high_score(self):
        low_total = sum(LOW_EMISSION_USER.values())
        result = compute_readiness_score(low_total, LOW_EMISSION_USER)
        assert result.score >= 70

    def test_high_emission_gets_low_score(self):
        high_total = sum(HIGH_EMISSION_USER.values())
        result = compute_readiness_score(high_total, HIGH_EMISSION_USER)
        assert result.score <= 40

    def test_tier_name_matches_score(self):
        result = compute_readiness_score(TYPICAL_USER_TOTAL, TYPICAL_USER_CONTRIBUTORS)
        assert result.tier_name  # Non-empty

    def test_breakdown_includes_all_components(self):
        result = compute_readiness_score(TYPICAL_USER_TOTAL, TYPICAL_USER_CONTRIBUTORS)
        assert "overall" in result.breakdown
        assert "transport" in result.breakdown
        assert "electricity" in result.breakdown
        assert "diet" in result.breakdown
        assert "flights" in result.breakdown

    def test_breakdown_total_matches_score(self):
        result = compute_readiness_score(TYPICAL_USER_TOTAL, TYPICAL_USER_CONTRIBUTORS)
        total = sum(result.breakdown.values())
        assert round(total) == result.score

    def test_recommendations_provided_for_high_emitters(self):
        high_total = sum(HIGH_EMISSION_USER.values())
        result = compute_readiness_score(high_total, HIGH_EMISSION_USER)
        assert len(result.recommendations) > 0

    def test_zero_footprint_handled(self):
        zero_user = {"transport": 0, "electricity": 0, "diet": 0, "flights": 0}
        result = compute_readiness_score(0.0, zero_user)
        assert result.score >= 0


# ── compute_projection_timeline ──────────────────────────────────────────────

class TestComputeProjectionTimeline:
    def test_length_includes_year_zero(self):
        timeline = compute_projection_timeline(5000.0, 5.0, 10)
        assert len(timeline) == 11  # years 0..10

    def test_year_zero_equals_initial(self):
        timeline = compute_projection_timeline(5000.0, 5.0, 10)
        assert timeline[0]["projected_kg"] == 5000.0
        assert timeline[0]["cumulative_saved_kg"] == 0.0

    def test_footprint_decreases_over_time(self):
        timeline = compute_projection_timeline(5000.0, 10.0, 20)
        for i in range(1, len(timeline)):
            assert timeline[i]["projected_kg"] <= timeline[i - 1]["projected_kg"]

    def test_cumulative_saved_increases(self):
        timeline = compute_projection_timeline(5000.0, 5.0, 10)
        for i in range(1, len(timeline)):
            assert timeline[i]["cumulative_saved_kg"] >= timeline[i - 1]["cumulative_saved_kg"]

    def test_zero_reduction_rate(self):
        timeline = compute_projection_timeline(5000.0, 0.0, 10)
        for entry in timeline:
            assert entry["projected_kg"] == 5000.0

    def test_footprint_never_goes_negative(self):
        timeline = compute_projection_timeline(5000.0, 20.0, 50)
        for entry in timeline:
            assert entry["projected_kg"] >= 0.0

    def test_50_percent_reduction_halves_in_some_years(self):
        timeline = compute_projection_timeline(10000.0, 10.0, 10)
        # After 10 years at 10% reduction, should be ~35% of original
        final = timeline[-1]["projected_kg"]
        assert final < 10000.0 * 0.5


# ── compute_equivalents ──────────────────────────────────────────────────────

class TestComputeEquivalents:
    def test_zero_co2(self):
        equivs = compute_equivalents(0.0)
        for val in equivs.values():
            assert val == 0

    def test_negative_co2(self):
        equivs = compute_equivalents(-100.0)
        for val in equivs.values():
            assert val == 0

    def test_positive_co2(self):
        equivs = compute_equivalents(1000.0)
        assert equivs["trees_needed"] > 0
        assert equivs["driving_km"] > 0
        assert equivs["smartphone_charges"] > 0
        assert equivs["meals_equivalent"] > 0
        assert equivs["liters_water"] > 0

    def test_proportional_values(self):
        equivs_1k = compute_equivalents(1000.0)
        equivs_2k = compute_equivalents(2000.0)
        for key in equivs_1k:
            assert equivs_2k[key] == pytest.approx(equivs_1k[key] * 2, abs=0.1)


# ── build_full_comparison_report ─────────────────────────────────────────────

class TestBuildFullComparisonReport:
    def test_returns_comparison_report(self):
        report = build_full_comparison_report(
            TYPICAL_USER_TOTAL, 65, TYPICAL_USER_CONTRIBUTORS
        )
        assert isinstance(report, ComparisonReport)

    def test_report_has_all_components(self):
        report = build_full_comparison_report(
            TYPICAL_USER_TOTAL, 65, TYPICAL_USER_CONTRIBUTORS
        )
        assert report.user_footprint_kg == TYPICAL_USER_TOTAL
        assert report.user_eco_score == 65
        assert len(report.category_comparisons) == 4
        assert report.country_percentile is not None
        assert len(report.archetype_matches) == len(LIFESTYLE_ARCHETYPES)
        assert len(report.reduction_targets) == len(IPCC_TARGETS)
        assert report.readiness is not None
        assert report.peer_group_avg_kg > 0
        assert report.generated_at  # Non-empty string

    def test_low_emission_report(self):
        low_total = sum(LOW_EMISSION_USER.values())
        report = build_full_comparison_report(low_total, 95, LOW_EMISSION_USER)
        assert report.readiness.score >= 70
        assert report.country_percentile.percentile >= 80

    def test_high_emission_report(self):
        high_total = sum(HIGH_EMISSION_USER.values())
        report = build_full_comparison_report(high_total, 15, HIGH_EMISSION_USER)
        assert report.readiness.score <= 40
        assert report.potential_savings_kg > 0


# ── get_country_list / get_archetype_list / get_ipcc_target_list ─────────────

class TestLookupFunctions:
    def test_country_list_sorted(self):
        countries = get_country_list()
        assert countries == sorted(countries)
        assert "USA" in countries
        assert "Global" in countries

    def test_archetype_list_has_all_fields(self):
        archetypes = get_archetype_list()
        assert len(archetypes) == len(LIFESTYLE_ARCHETYPES)
        for a in archetypes:
            assert "name" in a
            assert "avatar" in a
            assert "description" in a
            assert "typical_kg" in a

    def test_ipcc_target_list(self):
        targets = get_ipcc_target_list()
        assert len(targets) == len(IPCC_TARGETS)
        for t in targets:
            assert "name" in t
            assert "description" in t
            assert "target_kg" in t
            assert "source" in t

    def test_get_benchmark_country_known(self):
        data = get_benchmark_country("USA")
        assert data["total_tonnes"] == 14.7

    def test_get_benchmark_country_unknown_returns_global(self):
        data = get_benchmark_country("Atlantis")
        assert data == COUNTRY_AVERAGES["Global"]


# ── format_kg_to_tonnes / rating_color ──────────────────────────────────────

class TestFormattingHelpers:
    def test_format_kg_to_tonnes(self):
        assert format_kg_to_tonnes(1000.0) == "1.00 t"
        assert format_kg_to_tonnes(0.0) == "0.00 t"
        assert format_kg_to_tonnes(500.0) == "0.50 t"

    def test_rating_colors(self):
        assert rating_color("excellent") == "#22c55e"
        assert rating_color("good") == "#84cc16"
        assert rating_color("average") == "#eab308"
        assert rating_color("poor") == "#f97316"
        assert rating_color("critical") == "#ef4444"
        assert rating_color("unknown") == "#6b7280"


# ── estimate_peer_group_average ──────────────────────────────────────────────

class TestEstimatePeerGroupAverage:
    def test_fallback_to_global_average(self):
        # Without a real DB, should return global average
        avg = estimate_peer_group_average(user_id=99999)
        global_avg = COUNTRY_AVERAGES["Global"]["total_tonnes"] * 1000
        assert avg == global_avg


# ── generate_category_deep_dive ──────────────────────────────────────────────

class TestCategoryDeepDive:
    def test_returns_all_categories(self):
        dd = generate_category_deep_dive(TYPICAL_USER_CONTRIBUTORS)
        assert len(dd) == 4

    def test_each_category_has_required_fields(self):
        dd = generate_category_deep_dive(TYPICAL_USER_CONTRIBUTORS)
        for label, data in dd.items():
            assert "user_kg" in data
            assert "eu_average_kg" in data
            assert "global_average_kg" in data
            assert "improvement_potential_kg" in data
            assert "tips" in data
            assert len(data["tips"]) > 0
            assert "color" in data

    def test_improvement_potential_non_negative_for_high_emitter(self):
        dd = generate_category_deep_dive(HIGH_EMISSION_USER)
        for label, data in dd.items():
            assert data["improvement_potential_kg"] >= 0

    def test_zero_emissions_no_improvement_needed(self):
        zero_user = {"transport": 0, "electricity": 0, "diet": 0, "flights": 0}
        dd = generate_category_deep_dive(zero_user)
        for label, data in dd.items():
            assert data["improvement_potential_kg"] == 0.0


# ── Data integrity ──────────────────────────────────────────────────────────

class TestDataIntegrity:
    def test_all_countries_have_required_keys(self):
        required = {"total_tonnes", "transport", "electricity", "diet", "flights"}
        for country, data in COUNTRY_AVERAGES.items():
            for key in required:
                assert key in data, f"{country} missing {key}"

    def test_country_values_positive(self):
        for country, data in COUNTRY_AVERAGES.items():
            assert data["total_tonnes"] > 0, f"{country} has non-positive total"
            for key in ["transport", "electricity", "diet", "flights"]:
                assert data[key] >= 0, f"{country} has negative {key}"

    def test_archetype_categories_match_category_meta(self):
        expected_cats = set(CATEGORY_META.keys())
        for name, data in LIFESTYLE_ARCHETYPES.items():
            assert set(data["categories"].keys()) == expected_cats

    def test_readiness_tiers_sorted_descending(self):
        scores = [t[0] for t in READINESS_TIERS]
        assert scores == sorted(scores, reverse=True)
