"""Tests for the hybrid LCA truncation correction engine.

Two properties are load-bearing. The geometric tail must close - the modelled
series has to sum to the corrected total, or the remainder is not the tail it
claims to be. And a chain with a pass-through at or above one has to be
refused, because that series does not converge and reporting a finite number
for it would be the most confident possible way to be wrong.
"""

import math

import pytest

from src.carbon.truncation_correction import (
    BASES,
    MAX_TIER_COUNT,
    SECTORS,
    TruncationError,
    build_process_estimate,
    build_tier,
    compare_options,
    convergence_profile,
    correct,
    coverage_grade,
    delete_correction,
    fitted_ratio,
    get_corrections,
    get_sector,
    get_truncation_insights,
    io_upper_bound,
    list_bases,
    list_sectors,
    modelled_tiers,
    observed_ratios,
    portfolio_coverage,
    ratio_dispersion,
    save_correction,
    screening_loss,
    tiers_to_coverage,
    truncated_share,
)


def _manufacturing(name="Heat pump", scale=1.0):
    return build_process_estimate(name, "manufacturing", [
        {"tier": 0, "co2e_kg": 400 * scale, "label": "Assembly"},
        {"tier": 1, "co2e_kg": 180 * scale, "label": "Components"},
        {"tier": 2, "co2e_kg": 70 * scale, "label": "Raw materials"},
    ])


def _service(name="Consultancy", direct=600.0):
    return build_process_estimate(name, "services", [
        {"tier": 0, "co2e_kg": direct, "label": "Reported operations"},
    ])


# ---------------------------------------------------------------------------
# The convergence arithmetic
# ---------------------------------------------------------------------------

class TestConvergence:

    def test_a_ratio_of_one_is_refused(self):
        with pytest.raises(TruncationError, match="does not converge"):
            truncated_share(1.0, 3)

    def test_a_ratio_above_one_is_refused(self):
        with pytest.raises(TruncationError, match="does not converge"):
            convergence_profile(1.4)

    def test_a_zero_ratio_is_refused_as_a_claim_not_a_boundary(self):
        with pytest.raises(TruncationError, match="must be positive"):
            truncated_share(0.0, 3)

    def test_a_negative_ratio_is_refused(self):
        with pytest.raises(TruncationError, match="must be positive"):
            convergence_profile(-0.3)

    def test_truncated_share_is_the_ratio_raised_to_the_tier_count(self):
        assert truncated_share(0.5, 3) == pytest.approx(0.125)

    def test_counting_more_tiers_leaves_less_out(self):
        shares = [truncated_share(0.45, count) for count in range(1, 8)]
        assert shares == sorted(shares, reverse=True)

    def test_counting_zero_tiers_is_refused(self):
        with pytest.raises(TruncationError, match="direct tier"):
            truncated_share(0.4, 0)

    def test_a_slow_chain_needs_more_tiers_than_a_fast_one(self):
        assert tiers_to_coverage(0.62, 0.95) > tiers_to_coverage(0.30, 0.95)

    def test_tiers_to_coverage_actually_reaches_the_coverage(self):
        for ratio in (0.2, 0.4, 0.62, 0.8):
            needed = tiers_to_coverage(ratio, 0.95)
            assert 1.0 - truncated_share(ratio, needed) >= 0.95

    def test_tiers_to_coverage_is_tight_rather_than_generous(self):
        # One tier fewer must not already be enough, or the answer is padded.
        for ratio in (0.2, 0.4, 0.62, 0.8):
            needed = tiers_to_coverage(ratio, 0.95)
            if needed > 1:
                assert 1.0 - truncated_share(ratio, needed - 1) < 0.95

    def test_impossible_coverage_is_refused(self):
        with pytest.raises(TruncationError, match="strictly between"):
            tiers_to_coverage(0.4, 1.0)

    def test_the_series_multiplier_is_the_geometric_sum(self):
        profile = convergence_profile(0.5)
        assert profile["series_multiplier"] == pytest.approx(2.0)

    def test_services_are_flagged_as_slow_and_energy_is_not(self):
        assert convergence_profile(SECTORS["services"]["tier_ratio"])["slow"]
        assert not convergence_profile(SECTORS["energy"]["tier_ratio"])["slow"]


# ---------------------------------------------------------------------------
# Sector reference data
# ---------------------------------------------------------------------------

class TestSectors:

    def test_every_sector_has_a_bracketed_range(self):
        for entry in list_sectors():
            assert entry["ratio_low"] < entry["tier_ratio"] < entry["ratio_high"]

    def test_every_range_stays_inside_the_convergent_region(self):
        for entry in list_sectors():
            assert 0 < entry["ratio_low"] < 1
            assert 0 < entry["ratio_high"] < 1

    def test_every_sector_explains_its_own_convergence(self):
        for entry in list_sectors():
            assert len(entry["note"]) > 60

    def test_services_truncate_worse_than_construction(self):
        services = get_sector("services")
        construction = get_sector("construction")
        assert (
            services["truncation_at_three_tiers"]
            > construction["truncation_at_three_tiers"]
        )

    def test_get_sector_returns_none_for_an_unknown_key(self):
        assert get_sector("astrology") is None

    def test_an_unknown_sector_is_refused_with_the_list(self):
        with pytest.raises(TruncationError, match="Known sectors"):
            build_process_estimate("x", "astrology", [{"tier": 0, "co2e_kg": 1}])

    def test_a_missing_sector_is_refused_with_a_reason(self):
        with pytest.raises(TruncationError, match="how fast the chain converges"):
            build_process_estimate("x", None, [{"tier": 0, "co2e_kg": 1}])

    def test_the_input_output_bound_scales_with_spend(self):
        assert io_upper_bound(1000, "manufacturing") == pytest.approx(
            2 * io_upper_bound(500, "manufacturing")
        )

    def test_negative_spend_is_refused(self):
        with pytest.raises(TruncationError, match="cannot be negative"):
            io_upper_bound(-5, "manufacturing")


# ---------------------------------------------------------------------------
# Building estimates
# ---------------------------------------------------------------------------

class TestBuilding:

    def test_tiers_are_sorted_and_totalled(self):
        estimate = build_process_estimate("x", "manufacturing", [
            {"tier": 1, "co2e_kg": 50},
            {"tier": 0, "co2e_kg": 100},
        ])
        assert [item["tier"] for item in estimate["tiers"]] == [0, 1]
        assert estimate["process_total"] == 150

    def test_a_gap_in_the_tiers_is_refused(self):
        # A missing tier would make one tier's decay look like two, and the
        # fitted ratio would come out as its square root.
        with pytest.raises(TruncationError, match="contiguously from zero"):
            build_process_estimate("x", "manufacturing", [
                {"tier": 0, "co2e_kg": 100},
                {"tier": 2, "co2e_kg": 25},
            ])

    def test_a_duplicate_tier_is_refused(self):
        with pytest.raises(TruncationError, match="only once"):
            build_process_estimate("x", "manufacturing", [
                {"tier": 0, "co2e_kg": 100},
                {"tier": 0, "co2e_kg": 20},
            ])

    def test_a_series_not_starting_at_zero_is_refused(self):
        with pytest.raises(TruncationError, match="contiguously from zero"):
            build_process_estimate("x", "manufacturing", [
                {"tier": 1, "co2e_kg": 100},
            ])

    def test_a_negative_tier_is_refused(self):
        with pytest.raises(TruncationError, match="negative amount"):
            build_tier(0, -5)

    def test_a_negative_tier_index_is_refused(self):
        with pytest.raises(TruncationError, match="start at zero"):
            build_tier(-1, 5)

    def test_an_empty_estimate_is_refused(self):
        with pytest.raises(TruncationError, match="at least the direct tier"):
            build_process_estimate("x", "manufacturing", [])

    def test_an_all_zero_estimate_is_refused(self):
        with pytest.raises(TruncationError, match="some emissions"):
            build_process_estimate("x", "manufacturing", [
                {"tier": 0, "co2e_kg": 0},
            ])

    def test_too_many_tiers_is_not_a_truncation_problem(self):
        tiers = [{"tier": index, "co2e_kg": 10} for index in range(MAX_TIER_COUNT + 1)]
        with pytest.raises(TruncationError, match="not a truncation problem"):
            build_process_estimate("x", "manufacturing", tiers)

    def test_an_unknown_basis_is_refused(self):
        with pytest.raises(TruncationError, match="Unknown basis"):
            build_process_estimate(
                "x", "manufacturing", [{"tier": 0, "co2e_kg": 1}], basis="vibes"
            )

    def test_every_basis_is_described(self):
        assert {item["key"] for item in list_bases()} == set(BASES)


# ---------------------------------------------------------------------------
# Fitting the ratio from the data
# ---------------------------------------------------------------------------

class TestFitting:

    def test_a_single_tier_yields_no_observed_ratios(self):
        assert observed_ratios(_service()) == []
        assert fitted_ratio(_service()) is None

    def test_a_clean_geometric_chain_recovers_its_own_ratio(self):
        estimate = build_process_estimate("x", "manufacturing", [
            {"tier": 0, "co2e_kg": 1000},
            {"tier": 1, "co2e_kg": 400},
            {"tier": 2, "co2e_kg": 160},
            {"tier": 3, "co2e_kg": 64},
        ])
        assert fitted_ratio(estimate) == pytest.approx(0.4, rel=1e-9)

    def test_the_fit_is_geometric_not_arithmetic(self):
        # Ratios of 0.2 and 0.8. The arithmetic mean is 0.5; the geometric
        # mean is 0.4, and only the second reproduces the two-step decay.
        estimate = build_process_estimate("x", "manufacturing", [
            {"tier": 0, "co2e_kg": 1000},
            {"tier": 1, "co2e_kg": 200},
            {"tier": 2, "co2e_kg": 160},
        ])
        assert fitted_ratio(estimate) == pytest.approx(math.sqrt(0.2 * 0.8))

    def test_dispersion_needs_two_ratios(self):
        estimate = build_process_estimate("x", "manufacturing", [
            {"tier": 0, "co2e_kg": 100},
            {"tier": 1, "co2e_kg": 40},
        ])
        assert ratio_dispersion(estimate) is None

    def test_dispersion_reports_the_max_over_min(self):
        estimate = build_process_estimate("x", "manufacturing", [
            {"tier": 0, "co2e_kg": 1000},
            {"tier": 1, "co2e_kg": 200},
            {"tier": 2, "co2e_kg": 160},
        ])
        assert ratio_dispersion(estimate) == pytest.approx(4.0)

    def test_a_fitted_ratio_is_preferred_over_the_sector_default(self):
        result = correct(_manufacturing())
        assert result["ratio_source"] == "fitted from the tier data"

    def test_a_single_tier_falls_back_to_the_sector_default(self):
        result = correct(_service())
        assert result["ratio_source"] == "sector default"
        assert result["ratio"] == SECTORS["services"]["tier_ratio"]

    def test_a_supplied_ratio_overrides_everything(self):
        result = correct(_manufacturing(), ratio=0.25)
        assert result["ratio_source"] == "supplied"
        assert result["ratio"] == 0.25

    def test_a_supplied_divergent_ratio_is_refused(self):
        with pytest.raises(TruncationError, match="does not converge"):
            correct(_manufacturing(), ratio=1.1)


# ---------------------------------------------------------------------------
# The correction itself
# ---------------------------------------------------------------------------

class TestCorrection:

    def test_the_correction_is_always_upward(self):
        for estimate in (_manufacturing(), _service()):
            result = correct(estimate)
            assert result["remainder"] > 0
            assert result["corrected_total"] > result["process_total"]

    def test_the_modelled_series_sums_to_the_corrected_total(self):
        # The property that makes the remainder a tail rather than a guess.
        result = correct(_manufacturing())
        assert sum(
            row["co2e_kg"] for row in modelled_tiers(result, 200)
        ) == pytest.approx(result["corrected_total"], rel=1e-9)

    def test_counted_tiers_carry_their_measured_values(self):
        result = correct(_manufacturing())
        rows = modelled_tiers(result, 6)
        assert [row["co2e_kg"] for row in rows[:3]] == [400.0, 180.0, 70.0]
        assert [row["modelled"] for row in rows[:3]] == [False, False, False]
        assert all(row["modelled"] for row in rows[3:])

    def test_the_modelled_tail_decays(self):
        result = correct(_manufacturing())
        tail = [row["co2e_kg"] for row in modelled_tiers(result, 10)[3:]]
        assert tail == sorted(tail, reverse=True)

    def test_a_zero_length_series_is_refused(self):
        with pytest.raises(TruncationError, match="at least one tier"):
            modelled_tiers(correct(_manufacturing()), 0)

    def test_services_lose_far_more_than_manufacturing(self):
        # The asymmetry that makes a flat uplift the wrong answer.
        manufacturing = correct(_manufacturing())
        services = correct(_service())
        assert services["coverage_ratio"] < manufacturing["coverage_ratio"]
        assert services["uplift_percent"] > 100
        assert manufacturing["uplift_percent"] < 20

    def test_coverage_is_the_process_share_of_the_corrected_total(self):
        result = correct(_manufacturing())
        assert result["coverage_ratio"] == pytest.approx(
            result["process_total"] / result["corrected_total"], rel=1e-12
        )

    def test_the_band_brackets_the_central_estimate(self):
        result = correct(_service())
        assert result["corrected_low"] <= result["corrected_total"]
        assert result["corrected_total"] <= result["corrected_high"]

    def test_the_coverage_band_runs_the_other_way(self):
        result = correct(_service())
        assert result["coverage_low"] <= result["coverage_ratio"]
        assert result["coverage_ratio"] <= result["coverage_high"]

    def test_deeper_data_needs_less_correction(self):
        shallow = build_process_estimate("x", "manufacturing", [
            {"tier": 0, "co2e_kg": 1000},
            {"tier": 1, "co2e_kg": 400},
        ])
        deep = build_process_estimate("x", "manufacturing", [
            {"tier": 0, "co2e_kg": 1000},
            {"tier": 1, "co2e_kg": 400},
            {"tier": 2, "co2e_kg": 160},
            {"tier": 3, "co2e_kg": 64},
        ])
        assert correct(deep)["coverage_ratio"] > correct(shallow)["coverage_ratio"]

    def test_correcting_a_hybrid_figure_is_refused(self):
        estimate = build_process_estimate(
            "x", "manufacturing", [{"tier": 0, "co2e_kg": 100}], basis="hybrid"
        )
        with pytest.raises(TruncationError, match="count the tail twice"):
            correct(estimate)

    def test_correcting_an_input_output_figure_is_refused(self):
        estimate = build_process_estimate(
            "x", "manufacturing", [{"tier": 0, "co2e_kg": 100}], basis="io"
        )
        with pytest.raises(TruncationError, match="complete by construction"):
            correct(estimate)

    def test_a_single_tier_estimate_says_so(self):
        result = correct(_service())
        assert any("least informative" in item for item in result["warnings"])

    def test_wildly_varying_tiers_produce_a_fit_warning(self):
        estimate = build_process_estimate("x", "manufacturing", [
            {"tier": 0, "co2e_kg": 1000},
            {"tier": 1, "co2e_kg": 200},
            {"tier": 2, "co2e_kg": 160},
        ])
        result = correct(estimate)
        assert any("constant-ratio" in item for item in result["warnings"])

    def test_a_slow_chain_produces_a_convergence_warning(self):
        result = correct(_service())
        assert any("95% coverage" in item for item in result["warnings"])


# ---------------------------------------------------------------------------
# The input-output ceiling
# ---------------------------------------------------------------------------

class TestUpperBound:

    def test_a_correction_below_the_ceiling_is_untouched(self):
        result = correct(_manufacturing(), io_bound=5000)
        assert result["capped_at_io"] is False
        assert result["exceeds_io"] is False

    def test_a_correction_above_the_ceiling_is_capped(self):
        result = correct(_service(), io_bound=1000)
        assert result["capped_at_io"] is True
        assert result["corrected_total"] == pytest.approx(1000)
        assert result["remainder"] == pytest.approx(400)

    def test_a_process_figure_above_the_ceiling_is_reported_not_resolved(self):
        # Reported as a finding. Taking the larger of the two would make the
        # question disappear, which is the one thing that must not happen.
        result = correct(_manufacturing(), io_bound=100)
        assert result["exceeds_io"] is True
        assert result["capped_at_io"] is False
        assert result["corrected_total"] > 100

    def test_exceeding_the_ceiling_produces_an_insight(self):
        result = correct(_manufacturing(), io_bound=100)
        titles = [item["title"] for item in get_truncation_insights(result)]
        assert any("above the input-output" in title for title in titles)

    def test_a_non_positive_ceiling_is_refused(self):
        with pytest.raises(TruncationError, match="must be positive"):
            correct(_manufacturing(), io_bound=0)


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

class TestComparison:

    def test_an_asymmetric_boundary_flips_the_ranking(self):
        # The single most useful thing this module does. On process data the
        # consultancy wins by 50 kg; corrected, it loses by nearly a tonne.
        comparison = compare_options([_manufacturing(), _service(direct=600)])
        assert comparison["process_order"] == ["Consultancy", "Heat pump"]
        assert comparison["corrected_order"] == ["Heat pump", "Consultancy"]
        assert comparison["ranking_flipped"] is True
        assert comparison["winner_changed"] is True

    def test_a_robust_ranking_is_labelled_as_one(self):
        comparison = compare_options([
            _manufacturing("Small", scale=1.0),
            _manufacturing("Large", scale=4.0),
        ])
        assert comparison["ranking_flipped"] is False
        assert "survives correction" in comparison["note"]

    def test_a_cross_sector_comparison_is_flagged(self):
        comparison = compare_options([_manufacturing(), _service()])
        assert comparison["cross_sector"] is True

    def test_a_same_sector_comparison_is_not_flagged(self):
        comparison = compare_options([
            _manufacturing("A"), _manufacturing("B", scale=2.0)
        ])
        assert comparison["cross_sector"] is False

    def test_supplied_ratios_are_applied_per_option(self):
        comparison = compare_options(
            [_manufacturing(), _service()], ratios={"Consultancy": 0.2}
        )
        by_name = {row["name"]: row for row in comparison["results"]}
        assert by_name["Consultancy"]["ratio"] == 0.2

    def test_comparing_one_option_is_refused(self):
        with pytest.raises(TruncationError, match="at least two"):
            compare_options([_manufacturing()])


# ---------------------------------------------------------------------------
# Portfolio and screening
# ---------------------------------------------------------------------------

class TestPortfolio:

    def test_portfolio_totals_are_the_sum_of_the_parts(self):
        portfolio = portfolio_coverage([_manufacturing(), _service()])
        assert portfolio["process_total"] == pytest.approx(650 + 600)
        assert portfolio["missing_kg"] == pytest.approx(
            portfolio["corrected_total"] - portfolio["process_total"]
        )

    def test_the_worst_covered_line_is_named(self):
        portfolio = portfolio_coverage([_manufacturing(), _service()])
        assert portfolio["worst_covered"] == "Consultancy"
        assert portfolio["worst_coverage"] < portfolio["coverage_ratio"]

    def test_an_empty_portfolio_is_refused(self):
        with pytest.raises(TruncationError, match="at least one estimate"):
            portfolio_coverage([])

    def test_screening_reports_the_cutoff_in_both_denominators(self):
        loss = screening_loss(_manufacturing(), 0.05)
        assert loss["apparent_cutoff_kg"] == pytest.approx(650 * 0.05)
        assert loss["effective_share_of_corrected"] < 0.05
        assert loss["share_shift"] > 0

    def test_screening_says_the_threshold_is_not_what_it_reads(self):
        loss = screening_loss(_service(), 0.05)
        assert "not the number written on it" in loss["note"]

    def test_a_threshold_outside_zero_to_one_is_refused(self):
        with pytest.raises(TruncationError, match="between 0 and 1"):
            screening_loss(_manufacturing(), 1.5)


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

class TestInsights:

    def test_poor_coverage_is_raised_as_a_warning(self):
        insights = get_truncation_insights(correct(_service()))
        assert insights[0]["level"] == "warning"

    def test_good_coverage_is_raised_as_information(self):
        insights = get_truncation_insights(correct(_manufacturing()))
        assert insights[0]["level"] == "info"

    def test_the_ratio_source_is_always_stated(self):
        insights = get_truncation_insights(correct(_manufacturing()))
        assert any("ratio came from" in item["title"] for item in insights)

    def test_every_insight_has_a_level_and_a_body(self):
        for estimate in (_manufacturing(), _service()):
            for item in get_truncation_insights(correct(estimate)):
                assert item["level"] in {"info", "warning"}
                assert item["title"] and item["body"]

    def test_grades_run_from_well_characterised_to_dominated(self):
        assert coverage_grade(correct(_manufacturing())) == "well characterised"
        assert coverage_grade(correct(_service())) == (
            "dominated by what was not counted"
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.carbon.truncation_correction.DB_NAME", str(tmp_path / "test.db")
        )

    def test_a_saved_correction_comes_back(self):
        result = correct(_manufacturing())
        row_id = save_correction("user-1", result)
        saved = get_corrections("user-1")
        assert len(saved) == 1
        assert saved[0]["id"] == row_id
        assert saved[0]["sector"] == "manufacturing"

    def test_saved_totals_round_trip(self):
        result = correct(_manufacturing())
        save_correction("user-1", result)
        saved = get_corrections("user-1")[0]
        assert saved["corrected_total"] == pytest.approx(
            result["corrected_total"], rel=1e-9
        )
        assert saved["coverage_ratio"] == pytest.approx(
            result["coverage_ratio"], rel=1e-9
        )

    def test_the_payload_keeps_the_ratio_provenance(self):
        save_correction("user-1", correct(_manufacturing()))
        payload = get_corrections("user-1")[0]["payload"]
        assert payload["ratio_source"] == "fitted from the tier data"

    def test_users_do_not_see_each_others_corrections(self):
        save_correction("user-1", correct(_manufacturing()))
        save_correction("user-2", correct(_service()))
        assert len(get_corrections("user-1")) == 1
        assert get_corrections("user-2")[0]["sector"] == "services"

    def test_saving_without_a_user_is_refused(self):
        with pytest.raises(TruncationError, match="needs a user"):
            save_correction("", correct(_manufacturing()))

    def test_reading_without_a_user_returns_nothing(self):
        assert get_corrections(None) == []

    def test_deleting_removes_the_row(self):
        row_id = save_correction("user-1", correct(_manufacturing()))
        assert delete_correction("user-1", row_id) is True
        assert get_corrections("user-1") == []

    def test_deleting_another_users_row_does_nothing(self):
        row_id = save_correction("user-1", correct(_manufacturing()))
        assert delete_correction("user-2", row_id) is False
        assert len(get_corrections("user-1")) == 1

    def test_deleting_without_a_user_returns_false(self):
        assert delete_correction(None, 1) is False
