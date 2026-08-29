"""Tests for the savings verification engine.

The claim under test is that a before-and-after difference on a seasonal series
attributes the season to the intervention, and that a comparison group takes it
back out. So the load-bearing test recovers a *known* effect from data where the
seasonal swing is four times larger than the effect, and asserts both halves:
DiD lands near the truth, and before-and-after does not.

The second claim is about standard errors. An unclustered error on a serially
correlated panel understates, and the understatement must grow with the serial
correlation. Testing the ratio at one value of rho would prove nothing; testing
that it increases with rho tests the mechanism.

The refusals are tested as hard as the arithmetic, because a design that cannot
support a causal estimate and returns one anyway is the failure mode.
"""

import math

import pytest

from src.utils.savings_verification import (
    DEFAULT_ALPHA,
    MIN_PRE_PERIODS,
    MIN_UNITS_PER_ARM,
    PARALLEL_TRENDS_ALPHA,
    VerificationError,
    betai,
    build_observation,
    build_panel,
    delete_verification,
    durbin_watson,
    estimate_did,
    event_study,
    get_verifications,
    get_verification_notes,
    minimum_detectable_effect,
    naive_standard_error,
    newey_west_variance,
    option_c_regression,
    parallel_trends,
    placebo_test,
    save_verification,
    seasonal_panel,
    single_unit_series,
    summarise,
    t_cdf,
    t_ppf,
    two_sided_p,
    unclustered_standard_error,
    verify,
)


def _flat_panel(effect=0.0, treated=4, control=4, periods=10, start=6, noise=0.0):
    """A panel with no season and no noise, so every number is checkable by hand."""
    observations = []
    for index in range(treated + control):
        is_treated = index < treated
        for period in range(periods):
            value = 100.0 + index * 0.0
            if is_treated and period >= start:
                value += effect
            observations.append(
                build_observation(
                    "%s%d" % ("T" if is_treated else "C", index),
                    period,
                    value + (noise if period % 2 else -noise),
                    is_treated,
                    degree_days=50.0,
                )
            )
    return observations


# ---------------------------------------------------------------------------
# Distribution functions
# ---------------------------------------------------------------------------


class TestDistributionFunctions:
    @pytest.mark.parametrize(
        "degrees,expected",
        [(1, 12.7062), (2, 4.3027), (5, 2.5706), (10, 2.2281), (30, 2.0423)],
    )
    def test_t_quantiles_match_published_tables(self, degrees, expected):
        assert t_ppf(0.975, degrees) == pytest.approx(expected, abs=1e-3)

    def test_t_cdf_is_symmetric(self):
        assert t_cdf(1.4, 9) == pytest.approx(1.0 - t_cdf(-1.4, 9), abs=1e-10)

    def test_two_sided_p_at_zero_is_one(self):
        assert two_sided_p(0.0, 10) == pytest.approx(1.0, abs=1e-9)

    def test_betai_endpoints(self):
        assert betai(1.5, 2.5, 0.0) == 0.0
        assert betai(1.5, 2.5, 1.0) == 1.0

    def test_t_ppf_rejects_bad_input(self):
        with pytest.raises(VerificationError):
            t_ppf(1.0, 5)
        with pytest.raises(VerificationError):
            t_ppf(0.5, 0)


# ---------------------------------------------------------------------------
# Panel construction
# ---------------------------------------------------------------------------


class TestPanel:
    def test_splits_pre_and_post(self):
        panel = build_panel(_flat_panel(), 6)
        entry = panel["units"][0]
        assert len(entry["pre"]) == 6
        assert len(entry["post"]) == 4

    def test_arms_are_separated(self):
        panel = build_panel(_flat_panel(treated=3, control=5), 6)
        assert len(panel["treated"]) == 3
        assert len(panel["control"]) == 5

    def test_treatment_is_a_property_of_the_unit(self):
        """A unit marked treated in one reading and control in another is a data
        error, not something to average over."""
        observations = _flat_panel()
        observations[0]["treated"] = not observations[0]["treated"]
        with pytest.raises(VerificationError) as error:
            build_panel(observations, 6)
        assert "both treated and control" in str(error.value)

    def test_duplicate_period_is_refused(self):
        observations = _flat_panel()
        observations.append(dict(observations[0]))
        with pytest.raises(VerificationError):
            build_panel(observations, 6)

    def test_no_control_group_is_refused(self):
        """Without a comparison group this is a before-and-after study, which
        is the thing the module exists to replace."""
        observations = [
            observation for observation in _flat_panel() if observation["treated"]
        ]
        with pytest.raises(VerificationError) as error:
            build_panel(observations, 6)
        assert "comparison group" in str(error.value)

    def test_too_few_treated_units_is_refused(self):
        observations = _flat_panel(treated=1, control=4)
        with pytest.raises(VerificationError) as error:
            build_panel(observations, 6)
        assert "treated units" in str(error.value)

    def test_short_pre_period_is_refused(self):
        """An untested parallel-trends assumption is not an assumption."""
        with pytest.raises(VerificationError) as error:
            build_panel(_flat_panel(periods=8, start=2), 2)
        assert "parallel trends" in str(error.value)

    def test_short_post_period_is_refused(self):
        with pytest.raises(VerificationError):
            build_panel(_flat_panel(periods=8, start=7), 7)

    def test_empty_observations_are_refused(self):
        with pytest.raises(VerificationError):
            build_panel([], 6)

    def test_non_numeric_value_is_refused(self):
        with pytest.raises(VerificationError):
            build_observation("a", 1, "lots", True)

    def test_non_numeric_driver_is_refused(self):
        with pytest.raises(VerificationError):
            build_observation("a", 1, 100.0, True, degree_days="warm")


# ---------------------------------------------------------------------------
# Parallel trends
# ---------------------------------------------------------------------------


class TestParallelTrends:
    def test_identical_arms_pass(self):
        panel = build_panel(_flat_panel(), 6)
        trends = parallel_trends(panel)
        assert trends["passes"] is True

    def test_diverging_pre_trends_fail(self):
        """The two arms were already on different paths, so DiD would credit
        that divergence to the intervention."""
        observations = []
        for index in range(4):
            for period in range(10):
                observations.append(
                    build_observation(
                        "T%d" % index, period, 100.0 + 5.0 * period + index, True
                    )
                )
        for index in range(4):
            for period in range(10):
                observations.append(
                    build_observation(
                        "C%d" % index, period, 100.0 - 5.0 * period + index, False
                    )
                )
        panel = build_panel(observations, 6)
        trends = parallel_trends(panel)
        assert trends["passes"] is False
        assert "diverge" in trends["headline"]

    def test_failed_trends_block_the_estimate(self):
        observations = []
        for index in range(4):
            for period in range(10):
                observations.append(
                    build_observation("T%d" % index, period, 100.0 + 6.0 * period + index * 0.3, True)
                )
                observations.append(
                    build_observation("C%d" % index, period, 100.0 - 6.0 * period + index * 0.3, False)
                )
        panel = build_panel(observations, 6)
        result = estimate_did(panel)
        assert result["usable"] is False
        assert result["effect"] is None

    def test_can_be_overridden_for_the_placebo_path(self):
        observations = []
        for index in range(4):
            for period in range(10):
                observations.append(
                    build_observation("T%d" % index, period, 100.0 + 6.0 * period + index * 0.3, True)
                )
                observations.append(
                    build_observation("C%d" % index, period, 100.0 - 6.0 * period + index * 0.3, False)
                )
        panel = build_panel(observations, 6)
        result = estimate_did(panel, require_parallel_trends=False)
        assert result["usable"] is True

    def test_alpha_is_lenient_on_purpose(self):
        """A validity check the analysis wants to pass needs the threshold set
        the other way round from a hypothesis test."""
        assert PARALLEL_TRENDS_ALPHA > DEFAULT_ALPHA

    def test_worked_example_passes(self):
        panel = build_panel(seasonal_panel(), 14)
        assert parallel_trends(panel)["passes"] is True


# ---------------------------------------------------------------------------
# The estimate
# ---------------------------------------------------------------------------


class TestDifferenceInDifferences:
    def test_recovers_an_exact_effect_on_noiseless_data(self):
        panel = build_panel(_flat_panel(effect=-25.0), 6)
        result = estimate_did(panel)
        assert result["effect"] == pytest.approx(-25.0)

    def test_reports_zero_when_nothing_happened(self):
        panel = build_panel(_flat_panel(effect=0.0), 6)
        result = estimate_did(panel)
        assert result["effect"] == pytest.approx(0.0)
        assert result["significant"] is False

    def test_recovers_the_effect_through_a_much_larger_season(self):
        """The whole argument. The seasonal swing is 180 and the effect is 40;
        DiD must find the 40 and before-and-after must not."""
        panel = build_panel(seasonal_panel(true_effect=-40.0), 14)
        result = estimate_did(panel)
        assert result["effect"] == pytest.approx(-40.0, abs=15.0)
        assert abs(result["before_after_estimate"]) > 2.0 * abs(result["effect"])

    def test_the_season_is_attributed_to_the_control_group(self):
        panel = build_panel(seasonal_panel(true_effect=-40.0), 14)
        result = estimate_did(panel)
        assert result["confounded_share"] > 40.0

    def test_scales_with_the_true_effect(self):
        small = estimate_did(build_panel(seasonal_panel(true_effect=-20.0), 14))
        large = estimate_did(build_panel(seasonal_panel(true_effect=-120.0), 14))
        assert large["effect"] < small["effect"]

    def test_interval_is_symmetric(self):
        result = estimate_did(build_panel(seasonal_panel(), 14))
        assert result["effect"] - result["lower"] == pytest.approx(
            result["upper"] - result["effect"], abs=1e-9
        )

    def test_a_real_effect_is_significant(self):
        result = estimate_did(build_panel(seasonal_panel(true_effect=-120.0), 14))
        assert result["significant"] is True

    def test_headline_names_the_before_after_figure(self):
        result = estimate_did(build_panel(seasonal_panel(), 14))
        assert "before-and-after" in result["headline"]


# ---------------------------------------------------------------------------
# Standard errors
# ---------------------------------------------------------------------------


class TestStandardErrors:
    def test_unclustered_understates(self):
        panel = build_panel(seasonal_panel(autocorrelation=0.7), 14)
        result = estimate_did(panel)
        assert result["unclustered_standard_error"] < result["clustered_standard_error"]
        assert result["clustered_over_unclustered"] > 1.0

    def test_understatement_grows_with_serial_correlation(self):
        """Testing the ratio at one value of rho would prove nothing. Testing
        that it rises with rho tests the mechanism."""
        ratios = []
        for rho in (0.0, 0.4, 0.8):
            panel = build_panel(seasonal_panel(autocorrelation=rho), 14)
            ratios.append(estimate_did(panel)["clustered_over_unclustered"])
        assert ratios[0] < ratios[1] < ratios[2]

    def test_raw_naive_error_is_inflated_by_the_season(self):
        """Wrong in the other direction: with no period effects the seasonal
        swing gets counted as noise."""
        panel = build_panel(seasonal_panel(), 14)
        result = estimate_did(panel)
        assert result["naive_standard_error"] > result["clustered_standard_error"]

    def test_all_three_errors_are_positive(self):
        panel = build_panel(seasonal_panel(), 14)
        result = estimate_did(panel)
        for key in (
            "clustered_standard_error",
            "unclustered_standard_error",
            "naive_standard_error",
        ):
            assert result[key] > 0

    def test_errors_are_finite_on_a_minimal_panel(self):
        panel = build_panel(_flat_panel(effect=-10.0, noise=3.0), 6)
        assert math.isfinite(naive_standard_error(panel))
        assert math.isfinite(unclustered_standard_error(panel))


# ---------------------------------------------------------------------------
# Minimum detectable effect
# ---------------------------------------------------------------------------


class TestMinimumDetectableEffect:
    def test_more_units_detect_smaller_effects(self):
        small = minimum_detectable_effect(
            build_panel(seasonal_panel(treated_units=3, control_units=3), 14)
        )
        large = minimum_detectable_effect(
            build_panel(seasonal_panel(treated_units=30, control_units=30), 14)
        )
        assert large["effect"] < small["effect"]

    def test_noisier_data_detects_less(self):
        quiet = minimum_detectable_effect(build_panel(seasonal_panel(noise=10.0), 14))
        loud = minimum_detectable_effect(build_panel(seasonal_panel(noise=90.0), 14))
        assert loud["effect"] > quiet["effect"]

    def test_higher_power_needs_a_larger_effect(self):
        panel = build_panel(seasonal_panel(), 14)
        assert (
            minimum_detectable_effect(panel, power=0.95)["effect"]
            > minimum_detectable_effect(panel, power=0.80)["effect"]
        )

    def test_only_standard_power_levels(self):
        with pytest.raises(VerificationError):
            minimum_detectable_effect(build_panel(seasonal_panel(), 14), power=0.72)

    def test_null_result_reports_what_could_have_been_found(self):
        """'No significant change' and 'this design could never have found one'
        look identical on a dashboard and mean different things."""
        panel = build_panel(seasonal_panel(true_effect=-1.0, noise=90.0), 14)
        result = estimate_did(panel)
        if not result["significant"]:
            assert "could only have found" in result["headline"]


# ---------------------------------------------------------------------------
# Event study and placebo
# ---------------------------------------------------------------------------


class TestEventStudy:
    def test_pre_period_effects_are_near_zero(self):
        study = event_study(build_panel(seasonal_panel(true_effect=-80.0), 14))
        pre = [point["effect"] for point in study["points"] if not point["post"]]
        post = [point["effect"] for point in study["points"] if point["post"]]
        assert max(abs(value) for value in pre) < abs(sum(post) / len(post))

    def test_post_period_effects_have_the_right_sign(self):
        study = event_study(build_panel(seasonal_panel(true_effect=-80.0), 14))
        assert study["mean_post_effect"] < 0

    def test_reference_period_is_before_treatment(self):
        study = event_study(build_panel(seasonal_panel(), 14))
        assert study["reference_period"] < 14

    def test_relative_periods_are_centred_on_the_intervention(self):
        study = event_study(build_panel(seasonal_panel(), 14))
        first_post = next(point for point in study["points"] if point["post"])
        assert first_post["relative"] == 0


class TestPlacebo:
    def test_placebo_finds_nothing_when_nothing_happened(self):
        observations = seasonal_panel(true_effect=-80.0)
        result = placebo_test(observations, 14)
        assert result["ran"] is True
        assert result["passed"] is True

    def test_placebo_only_uses_pre_period_data(self):
        observations = seasonal_panel(true_effect=-500.0)
        result = placebo_test(observations, 14)
        assert result["placebo_period"] < 14
        assert abs(result["effect"]) < 100.0

    def test_placebo_reports_when_it_cannot_run(self):
        """Being unable to run a placebo is a limitation, not a pass."""
        observations = _flat_panel(periods=10, start=6)
        result = placebo_test(observations, 4)
        assert result["ran"] is False
        assert "not a pass" in result["headline"]

    def test_placebo_needs_a_pre_period(self):
        with pytest.raises(VerificationError):
            placebo_test(_flat_panel(), 0)


# ---------------------------------------------------------------------------
# Option C
# ---------------------------------------------------------------------------


class TestOptionC:
    def test_recovers_a_baseline_relationship(self):
        result = option_c_regression(single_unit_series(), 18, ["degree_days"])
        assert result["r_squared"] > 0.9
        assert result["coefficients"][1] == pytest.approx(1.6, abs=0.3)

    def test_finds_the_avoided_consumption(self):
        result = option_c_regression(single_unit_series(true_effect=-60.0), 18, ["degree_days"])
        assert result["mean_avoided"] > 0
        assert result["lower"] < 60.0 * result["reporting_periods"] < result["upper"]

    def test_never_claims_causality(self):
        """It has no comparison group, so it cannot separate the intervention
        from anything else that changed at the same time."""
        result = option_c_regression(single_unit_series(), 18, ["degree_days"])
        assert result["causal"] is False
        assert "not a causal estimate" in result["headline"]

    def test_reports_autocorrelation(self):
        result = option_c_regression(single_unit_series(), 18, ["degree_days"])
        assert 0.0 <= result["durbin_watson"] <= 4.0

    def test_short_baseline_is_refused(self):
        series = [
            observation
            for observation in single_unit_series()
            if observation["period"] >= 15
        ]
        with pytest.raises(VerificationError) as error:
            option_c_regression(series, 18, ["degree_days"])
        assert "baseline periods" in str(error.value)

    def test_missing_driver_is_refused(self):
        with pytest.raises(VerificationError) as error:
            option_c_regression(single_unit_series(), 18, ["occupancy"])
        assert "no value for driver" in str(error.value)


class TestNeweyWest:
    def test_returns_one_variance_per_coefficient(self):
        design = [[1.0, float(index)] for index in range(30)]
        residuals = [math.sin(index) for index in range(30)]
        variance = newey_west_variance(design, residuals)
        assert variance is not None
        assert len(variance) == 2
        assert all(value >= 0 for value in variance)

    def test_returns_none_when_underdetermined(self):
        design = [[1.0, 2.0, 3.0]]
        assert newey_west_variance(design, [1.0]) is None

    def test_positively_autocorrelated_residuals_inflate_the_variance(self):
        design = [[1.0, float(index)] for index in range(60)]
        independent = [(-1.0) ** index for index in range(60)]
        persistent = [1.0 if index < 30 else -1.0 for index in range(60)]
        alternating = newey_west_variance(design, independent)
        blocked = newey_west_variance(design, persistent)
        assert blocked[0] > alternating[0]

    def test_durbin_watson_detects_persistence(self):
        assert durbin_watson([1.0] * 10 + [-1.0] * 10) < 1.0
        assert durbin_watson([(-1.0) ** index for index in range(20)]) > 3.0

    def test_durbin_watson_of_a_short_series(self):
        assert durbin_watson([1.0]) == 2.0


# ---------------------------------------------------------------------------
# The full workflow
# ---------------------------------------------------------------------------


class TestVerify:
    def test_reports_assumption_before_effect(self):
        report = verify(seasonal_panel(), 14)
        assert "parallel_trends" in report
        assert report["causal"] is True

    def test_unusable_design_reports_no_effect_and_says_why(self):
        observations = []
        for index in range(4):
            for period in range(10):
                observations.append(
                    build_observation("T%d" % index, period, 100.0 + 6.0 * period + index * 0.3, True)
                )
                observations.append(
                    build_observation("C%d" % index, period, 100.0 - 6.0 * period + index * 0.3, False)
                )
        report = verify(observations, 6)
        assert report["causal"] is False
        notes = " ".join(get_verification_notes(report))
        assert "not a missing result" in notes

    def test_notes_compare_the_two_designs(self):
        report = verify(seasonal_panel(), 14)
        notes = " ".join(get_verification_notes(report))
        assert "comparison group absorbed" in notes
        assert "Clustered standard error" in notes

    def test_summary_is_one_line(self):
        assert "\n" not in summarise(verify(seasonal_panel(), 14))


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.utils.savings_verification.DB_NAME", str(tmp_path / "test.db")
        )

    def _report(self):
        return verify(seasonal_panel(treated_units=4, control_units=4), 14)

    def test_round_trip(self):
        verification_id = save_verification("user-1", self._report(), "rollout")
        assert verification_id is not None
        saved = get_verifications("user-1")
        assert len(saved) == 1
        assert saved[0]["label"] == "rollout"
        assert saved[0]["payload"]["parallel_trends"]

    def test_scoped_to_the_user(self):
        save_verification("user-1", self._report())
        assert get_verifications("user-2") == []

    def test_delete(self):
        verification_id = save_verification("user-1", self._report())
        assert delete_verification("user-1", verification_id) is True
        assert get_verifications("user-1") == []

    def test_delete_refuses_another_user(self):
        verification_id = save_verification("user-1", self._report())
        assert delete_verification("user-2", verification_id) is False

    def test_missing_user_is_a_no_op(self):
        assert save_verification(None, self._report()) is None
        assert get_verifications(None) == []
        assert delete_verification(None, 1) is False
