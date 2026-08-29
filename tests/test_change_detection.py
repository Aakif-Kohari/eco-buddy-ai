"""Tests for the change detection engine.

The app could always report that a number moved. This says whether the move was
real, and the tests guard the properties that make that claim worth trusting:

*   the distribution functions agree with published t tables, because every
    verdict downstream is only as good as they are;
*   there are three verdicts and the third one fires - "your data could not
    have found an effect this size" is a different statement from "it did not
    work", and collapsing them is the failure mode the module exists to catch;
*   autocorrelation reduces the effective sample size, so a correlated series
    is treated as the fewer independent observations it actually contains;
*   emission factor uncertainty shared between two periods cancels in the
    difference rather than being counted twice;
*   repeated looks and multiple categories are corrected, because a dashboard
    that is checked monthly across eight categories will otherwise manufacture
    a significant result on its own.

The underpowered verdict is the load-bearing one. A user who abandons a working
intervention because the app said "no change" has been actively misled, and a
version of this module that only returned detected-or-not would be worse than
no module at all.
"""

import math
import os
import tempfile
import unittest

import src.utils.change_detection as cd


NOISY = [420, 455, 398, 510, 530, 470, 405, 388,
         412, 449, 505, 540, 430, 462, 401, 515]

QUIET = [500, 502, 499, 501, 498, 503, 500, 501,
         499, 502, 500, 498, 501, 499, 502, 500]


class TestDistributions(unittest.TestCase):
    """Everything downstream is only as good as these."""

    def test_incomplete_beta_endpoints(self):
        self.assertEqual(cd.regularised_incomplete_beta(2.0, 3.0, 0.0), 0.0)
        self.assertEqual(cd.regularised_incomplete_beta(2.0, 3.0, 1.0), 1.0)

    def test_incomplete_beta_is_symmetric_in_the_expected_way(self):
        """I_x(a, b) = 1 - I_{1-x}(b, a)."""
        self.assertAlmostEqual(
            cd.regularised_incomplete_beta(2.5, 4.5, 0.3),
            1.0 - cd.regularised_incomplete_beta(4.5, 2.5, 0.7),
            places=10,
        )

    def test_t_cdf_matches_published_tables(self):
        self.assertAlmostEqual(cd.student_t_cdf(2.0, 10), 0.96331, places=5)
        self.assertAlmostEqual(cd.student_t_cdf(0.0, 7), 0.5, places=10)
        self.assertAlmostEqual(cd.student_t_cdf(-2.0, 10), 0.03669, places=5)

    def test_t_cdf_approaches_the_normal_at_high_df(self):
        self.assertAlmostEqual(
            cd.student_t_cdf(1.959964, 5_000_000), 0.975, places=5
        )

    def test_two_sided_p_matches_the_five_percent_critical_value(self):
        self.assertAlmostEqual(
            cd.student_t_sf_two_sided(2.228, 10), 0.05, places=4
        )

    def test_t_quantiles_match_published_tables(self):
        self.assertAlmostEqual(cd.student_t_quantile(0.975, 10), 2.2281, places=3)
        self.assertAlmostEqual(cd.student_t_quantile(0.975, 30), 2.0423, places=3)
        self.assertAlmostEqual(cd.student_t_quantile(0.80, 20), 0.8600, places=3)

    def test_the_quantile_inverts_the_cdf(self):
        for probability in (0.05, 0.25, 0.5, 0.9, 0.99):
            value = cd.student_t_quantile(probability, 12)
            self.assertAlmostEqual(
                cd.student_t_cdf(value, 12), probability, places=8
            )

    def test_normal_quantile_matches_the_standard_value(self):
        self.assertAlmostEqual(cd.normal_quantile(0.975), 1.959964, places=5)

    def test_impossible_probabilities_are_refused(self):
        for bad in (0.0, 1.0, -0.5, 2.0):
            with self.assertRaises(cd.ChangeDetectionError):
                cd.normal_quantile(bad)
            with self.assertRaises(cd.ChangeDetectionError):
                cd.student_t_quantile(bad, 10)

    def test_non_positive_degrees_of_freedom_are_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.student_t_cdf(1.0, 0)


class TestAutocorrelation(unittest.TestCase):

    def test_variance_inflation_is_one_when_independent(self):
        self.assertAlmostEqual(cd.variance_inflation(0.0), 1.0)

    def test_variance_inflation_grows_with_correlation(self):
        self.assertGreater(cd.variance_inflation(0.5), cd.variance_inflation(0.2))
        self.assertAlmostEqual(cd.variance_inflation(0.5), 3.0)

    def test_effective_sample_size_falls_as_correlation_rises(self):
        independent = cd.effective_sample_size(24, 0.0)
        correlated = cd.effective_sample_size(24, 0.6)
        self.assertAlmostEqual(independent, 24.0)
        self.assertLess(correlated, independent)

    def test_effective_sample_size_never_drops_below_two(self):
        self.assertGreaterEqual(cd.effective_sample_size(4, 0.99), 2.0)

    def test_a_strongly_trending_series_is_detected_as_correlated(self):
        rising = [100 + 5 * index for index in range(20)]
        self.assertGreater(cd.lag1_autocorrelation(rising), 0.7)

    def test_an_alternating_series_is_negatively_correlated(self):
        alternating = [100, 200] * 10
        self.assertLess(cd.lag1_autocorrelation(alternating), -0.7)

    def test_a_constant_series_has_no_correlation_rather_than_dividing_by_zero(self):
        self.assertEqual(cd.lag1_autocorrelation([5.0] * 10), 0.0)


class TestBaseline(unittest.TestCase):

    def test_a_short_series_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.characterise_baseline([1.0, 2.0])

    def test_non_numeric_input_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.characterise_baseline([1.0, "two", 3.0])

    def test_non_finite_input_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.characterise_baseline([1.0, float("nan"), 3.0])

    def test_a_noisy_series_reports_more_variation_than_a_quiet_one(self):
        noisy = cd.characterise_baseline(NOISY)
        quiet = cd.characterise_baseline(QUIET)
        self.assertGreater(noisy["residual_sd"], quiet["residual_sd"] * 10)

    def test_the_trend_is_removed_before_the_noise_is_measured(self):
        """A steadily rising series is not noisy; it is trending."""
        rising = [100 + 10 * index for index in range(20)]
        baseline = cd.characterise_baseline(rising)
        self.assertAlmostEqual(baseline["trend_per_period"], 10.0, places=6)
        self.assertLess(baseline["residual_sd"], 1e-6)

    def test_seasonality_is_removed_before_the_noise_is_measured(self):
        """A winter peak is not error, and charging it to error hides effects."""
        seasonal = [100, 140, 180, 140] * 5
        without = cd.characterise_baseline(seasonal)
        with_season = cd.characterise_baseline(seasonal, season_length=4)
        self.assertGreater(without["residual_sd"], 20.0)
        self.assertLess(with_season["residual_sd"], 1e-6)

    def test_a_seasonal_cycle_needs_two_full_periods(self):
        with self.assertRaises(cd.ChangeDetectionError) as caught:
            cd.characterise_baseline([1, 2, 3, 4, 5, 6, 7], season_length=6)
        self.assertIn("two full cycles", str(caught.exception))

    def test_a_short_baseline_is_warned_about(self):
        baseline = cd.characterise_baseline([10, 12, 9, 11])
        self.assertTrue(
            any("indicative" in warning for warning in baseline["warnings"])
        )

    def test_severe_autocorrelation_is_warned_about(self):
        """A slow wave leaves residuals that carry over between periods."""
        wave = [100 + 20 * math.sin(index / 6.0) for index in range(30)]
        baseline = cd.characterise_baseline(wave)
        self.assertGreater(baseline["lag1_autocorrelation"],
                           cd.SEVERE_AUTOCORRELATION)
        self.assertLess(baseline["effective_n"], baseline["n"])
        self.assertTrue(
            any("overconfident" in warning for warning in baseline["warnings"])
        )

    def test_trend_and_seasonality_are_separated_from_each_other(self):
        """Removing either one first biases the other, so they are back-fitted.

        A seasonal pattern whose phases are not symmetric about the midpoint
        induces a spurious trend, and a trend removed first distorts the
        seasonal profile. A single pass in either order leaves residual that is
        neither noise nor signal.
        """
        mixed = [
            100 + 2 * index + 30 * math.sin(2 * math.pi * (index % 12) / 12)
            for index in range(36)
        ]
        baseline = cd.characterise_baseline(mixed, season_length=12)
        self.assertAlmostEqual(baseline["trend_per_period"], 2.0, places=6)
        self.assertLess(baseline["residual_sd"], 1e-6)

    def test_a_single_pass_would_not_have_reached_that_answer(self):
        """Guards the back-fitting rather than the outcome it happens to give."""
        seasonal = [100, 140, 180, 140] * 5
        slope, intercept = cd.linear_trend(seasonal)
        self.assertNotAlmostEqual(slope, 0.0, places=3)
        baseline = cd.characterise_baseline(seasonal, season_length=4)
        self.assertAlmostEqual(baseline["trend_per_period"], 0.0, places=6)

    def test_a_constant_series_is_called_out_rather_than_scored(self):
        baseline = cd.characterise_baseline([7.0] * 12)
        self.assertTrue(
            any("synthetic" in warning for warning in baseline["warnings"])
        )


class TestMinimumDetectableEffect(unittest.TestCase):

    def test_more_data_detects_smaller_effects(self):
        small = cd.minimum_detectable_effect(50.0, 6, 6)["mde"]
        large = cd.minimum_detectable_effect(50.0, 60, 60)["mde"]
        self.assertLess(large, small)

    def test_noisier_data_detects_only_larger_effects(self):
        quiet = cd.minimum_detectable_effect(10.0, 12, 12)["mde"]
        noisy = cd.minimum_detectable_effect(80.0, 12, 12)["mde"]
        self.assertGreater(noisy, quiet)

    def test_autocorrelation_raises_the_detectable_effect(self):
        independent = cd.minimum_detectable_effect(50.0, 24, 24, 0.0)["mde"]
        correlated = cd.minimum_detectable_effect(50.0, 24, 24, 0.7)["mde"]
        self.assertGreater(correlated, independent)

    def test_it_scales_linearly_with_the_standard_deviation(self):
        single = cd.minimum_detectable_effect(10.0, 20, 20)["mde"]
        double = cd.minimum_detectable_effect(20.0, 20, 20)["mde"]
        self.assertAlmostEqual(double, single * 2.0, places=4)

    def test_impossible_alpha_and_power_are_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.minimum_detectable_effect(10.0, 10, 10, alpha=0.0)
        with self.assertRaises(cd.ChangeDetectionError):
            cd.minimum_detectable_effect(10.0, 10, 10, power=1.0)

    def test_a_negative_standard_deviation_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.minimum_detectable_effect(-1.0, 10, 10)


class TestRequiredPeriods(unittest.TestCase):
    """The most actionable output in the module."""

    def test_a_larger_target_needs_fewer_periods(self):
        small = cd.required_periods(50.0, 10.0)["periods_per_arm"]
        large = cd.required_periods(50.0, 100.0)["periods_per_arm"]
        self.assertGreater(small, large)

    def test_the_answer_actually_detects_the_target(self):
        target = 30.0
        answer = cd.required_periods(50.0, target)
        achieved = cd.minimum_detectable_effect(
            50.0, answer["periods_per_arm"], answer["periods_per_arm"]
        )["mde"]
        self.assertLessEqual(achieved, target + 1e-6)

    def test_one_fewer_period_would_not_have_been_enough(self):
        target = 30.0
        answer = cd.required_periods(50.0, target)
        n = answer["periods_per_arm"]
        if n > 2:
            self.assertGreater(
                cd.minimum_detectable_effect(50.0, n - 1, n - 1)["mde"], target
            )

    def test_a_target_of_zero_is_refused_rather_than_looped_over(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.required_periods(50.0, 0.0)

    def test_an_unreachable_target_says_so_instead_of_returning_a_number(self):
        answer = cd.required_periods(500.0, 0.01, max_periods=50)
        self.assertFalse(answer["achievable"])
        self.assertIsNone(answer["periods_per_arm"])
        self.assertIn("less noisy measurement", answer["note"])

    def test_autocorrelation_lengthens_the_wait(self):
        independent = cd.required_periods(50.0, 20.0, 0.0)["periods_per_arm"]
        correlated = cd.required_periods(50.0, 20.0, 0.7)["periods_per_arm"]
        self.assertGreater(correlated, independent)


class TestSharedFactorError(unittest.TestCase):
    """Uncertainty on a level is not uncertainty on a difference."""

    def test_shared_uncertainty_scales_the_difference_not_the_levels(self):
        correct = cd.combined_standard_error(10.0, 50.0, 0.15)
        naive = cd.naive_standard_error(10.0, 5000.0, 4950.0, 0.15)
        self.assertLess(correct, naive)

    def test_the_gap_is_large_for_a_small_change_on_a_large_footprint(self):
        """The case where treating them as independent buries a real effect."""
        correct = cd.combined_standard_error(20.0, 100.0, 0.2)
        naive = cd.naive_standard_error(20.0, 8000.0, 7900.0, 0.2)
        self.assertGreater(naive / correct, 20.0)

    def test_zero_shared_uncertainty_leaves_the_sampling_error_alone(self):
        self.assertAlmostEqual(
            cd.combined_standard_error(12.0, 300.0, 0.0), 12.0
        )

    def test_an_absurd_coefficient_of_variation_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.combined_standard_error(10.0, 50.0, 1.5)


class TestComparison(unittest.TestCase):

    def test_a_single_reading_per_side_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError) as caught:
            cd.compare_periods([100.0], [80.0])
        self.assertIn("no error bar", str(caught.exception))

    def test_a_large_change_against_quiet_data_is_detected(self):
        result = cd.compare_periods(QUIET[:8], [400.0] * 8,
                                    meaningful_effect=20.0)
        self.assertEqual(result["verdict"], "detected")
        self.assertLess(result["p_value"], 0.001)

    def test_a_small_change_against_noisy_data_is_underpowered(self):
        """Not 'it did not work'. 'You could not have found out'."""
        result = cd.compare_periods(NOISY[:8], NOISY[8:],
                                    meaningful_effect=20.0)
        self.assertEqual(result["verdict"], "underpowered")
        self.assertGreater(result["minimum_detectable_effect"],
                           abs(result["difference"]))

    def test_a_genuine_null_is_reported_as_not_detected(self):
        """Enough power to have found what mattered, and it was not there."""
        result = cd.compare_periods(QUIET[:8], QUIET[8:],
                                    meaningful_effect=20.0)
        self.assertEqual(result["verdict"], "not_detected")

    def test_all_three_verdicts_are_reachable(self):
        verdicts = {
            cd.compare_periods(QUIET[:8], [400.0] * 8,
                               meaningful_effect=20.0)["verdict"],
            cd.compare_periods(QUIET[:8], QUIET[8:],
                               meaningful_effect=20.0)["verdict"],
            cd.compare_periods(NOISY[:8], NOISY[8:],
                               meaningful_effect=20.0)["verdict"],
        }
        self.assertEqual(verdicts, {"detected", "not_detected", "underpowered"})

    def test_the_confidence_interval_brackets_the_difference(self):
        result = cd.compare_periods(NOISY[:8], NOISY[8:])
        low, high = result["confidence_interval"]
        self.assertLessEqual(low, result["difference"])
        self.assertLessEqual(result["difference"], high)

    def test_a_detected_change_has_an_interval_excluding_zero(self):
        result = cd.compare_periods(QUIET[:8], [400.0] * 8,
                                    meaningful_effect=20.0)
        low, high = result["confidence_interval"]
        self.assertFalse(low <= 0 <= high)

    def test_the_direction_of_the_difference_is_preserved(self):
        result = cd.compare_periods([100.0] * 6, [80.0] * 6)
        self.assertLess(result["difference"], 0)

    def test_autocorrelation_reduces_the_effective_sample_size(self):
        rising = [100 + 3 * index for index in range(20)]
        result = cd.compare_periods(rising[:10], rising[10:])
        self.assertLess(result["effective_n_before"], result["n_before"])

    def test_shared_factor_uncertainty_is_reported_as_a_saving(self):
        result = cd.compare_periods(
            [5000, 5100, 4900, 5050, 4950, 5020],
            [4700, 4750, 4650, 4720, 4680, 4710],
            shared_factor_cv=0.2,
        )
        self.assertGreater(result["shared_factor_saving"], 0.0)

    def test_achieved_power_is_a_probability(self):
        result = cd.compare_periods(NOISY[:8], NOISY[8:])
        self.assertGreaterEqual(result["achieved_power"], 0.0)
        self.assertLessEqual(result["achieved_power"], 1.0)


class TestSequentialMonitoring(unittest.TestCase):

    def test_an_early_look_is_much_stricter_than_the_last(self):
        first = cd.sequential_boundary(1, 12)["critical_z"]
        last = cd.sequential_boundary(12, 12)["critical_z"]
        self.assertGreater(first, last)

    def test_the_final_look_returns_to_the_nominal_level(self):
        last = cd.sequential_boundary(12, 12)
        self.assertAlmostEqual(last["critical_z"], 1.959964, places=4)

    def test_the_uncorrected_family_error_is_reported(self):
        boundary = cd.sequential_boundary(4, 12)
        self.assertGreater(boundary["naive_family_error"], 0.4)

    def test_an_out_of_range_look_is_refused(self):
        for look, total in ((0, 5), (6, 5), (-1, 5)):
            with self.assertRaises(cd.ChangeDetectionError):
                cd.sequential_boundary(look, total)

    def test_a_result_significant_at_the_nominal_level_can_still_fail_early(self):
        """Which is the whole reason for the boundary."""
        verdict = cd.sequential_verdict(2.1, look=2, total_looks=12)
        self.assertFalse(verdict["crossed"])
        self.assertIn("not the same as being real", verdict["note"])

    def test_a_strong_early_result_does_cross(self):
        verdict = cd.sequential_verdict(9.0, look=1, total_looks=12)
        self.assertTrue(verdict["crossed"])


class TestMultipleComparisons(unittest.TestCase):

    def test_the_correction_is_never_more_lenient_than_the_raw_value(self):
        result = cd.benjamini_hochberg([0.001, 0.02, 0.04, 0.3, 0.5])
        for index, raw in enumerate([0.001, 0.02, 0.04, 0.3, 0.5]):
            self.assertGreaterEqual(result["adjusted"][index], raw - 1e-12)

    def test_adjusted_values_are_monotone_in_the_raw_values(self):
        raw = [0.001, 0.01, 0.02, 0.04, 0.2, 0.6]
        adjusted = cd.benjamini_hochberg(raw)["adjusted"]
        ordered = [adjusted[index] for index in range(len(raw))]
        self.assertEqual(ordered, sorted(ordered))

    def test_it_rejects_fewer_than_the_uncorrected_test(self):
        result = cd.benjamini_hochberg(
            {"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.3, "e": 0.5}
        )
        self.assertLess(len(result["survivors"]),
                        len(result["naive_significant"]))
        self.assertIn("c", result["naive_significant"])
        self.assertNotIn("c", result["survivors"])

    def test_the_uncorrected_family_error_is_reported(self):
        result = cd.benjamini_hochberg([0.5] * 8)
        self.assertGreater(result["family_error_if_uncorrected"], 0.3)

    def test_labels_are_preserved_when_a_mapping_is_given(self):
        result = cd.benjamini_hochberg({"food": 0.001, "travel": 0.6})
        self.assertEqual(set(result["adjusted"]), {"food", "travel"})

    def test_an_empty_set_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.benjamini_hochberg([])

    def test_a_value_outside_zero_to_one_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.benjamini_hochberg([0.1, 1.4])


class TestInsights(unittest.TestCase):

    def test_an_underpowered_result_is_not_described_as_no_change(self):
        result = cd.compare_periods(NOISY[:8], NOISY[8:],
                                    meaningful_effect=20.0)
        text = " ".join(cd.get_detection_insights(result))
        self.assertIn("never capable of answering", text)
        self.assertNotIn("No change detected", text)

    def test_a_genuine_null_says_the_test_had_the_power(self):
        result = cd.compare_periods(QUIET[:8], QUIET[8:],
                                    meaningful_effect=20.0)
        text = " ".join(cd.get_detection_insights(result))
        self.assertIn("No change detected", text)

    def test_a_detected_change_reports_its_p_value(self):
        result = cd.compare_periods(QUIET[:8], [400.0] * 8,
                                    meaningful_effect=20.0)
        text = " ".join(cd.get_detection_insights(result))
        self.assertIn("p =", text)

    def test_an_interval_spanning_zero_is_called_out(self):
        result = cd.compare_periods(NOISY[:8], NOISY[8:])
        text = " ".join(cd.get_detection_insights(result))
        self.assertIn("direction itself is not established", text)

    def test_baseline_warnings_are_carried_through(self):
        baseline = cd.characterise_baseline([10, 12, 9, 11])
        result = cd.compare_periods([10, 12], [9, 11])
        text = " ".join(cd.get_detection_insights(result, baseline))
        self.assertIn("indicative", text)


class TestReferenceTables(unittest.TestCase):

    def test_there_are_exactly_three_verdicts(self):
        self.assertEqual(len(cd.list_verdicts()), 3)

    def test_every_verdict_explains_itself(self):
        for key in cd.list_verdicts():
            self.assertGreater(len(cd.get_verdict(key)["note"]), 60)

    def test_an_unknown_verdict_is_refused(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.get_verdict("maybe")


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = cd.DB_NAME
        cd.DB_NAME = self.path
        self.result = cd.compare_periods(NOISY[:8], NOISY[8:],
                                         meaningful_effect=20.0)

    def tearDown(self):
        cd.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_test_comes_back(self):
        saved_id = cd.save_test("user-1", "Detergent switch", self.result)
        self.assertIsInstance(saved_id, int)
        rows = cd.get_tests("user-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Detergent switch")

    def test_the_verdict_survives_a_round_trip(self):
        cd.save_test("user-1", "Round trip", self.result)
        row = cd.get_tests("user-1")[0]
        self.assertEqual(row["verdict"], self.result["verdict"])
        self.assertAlmostEqual(row["p_value"], self.result["p_value"], 6)

    def test_users_do_not_see_each_others_tests(self):
        cd.save_test("user-1", "Mine", self.result)
        self.assertEqual(cd.get_tests("user-2"), [])

    def test_a_test_needs_a_user_and_a_name(self):
        with self.assertRaises(cd.ChangeDetectionError):
            cd.save_test("", "Named", self.result)
        with self.assertRaises(cd.ChangeDetectionError):
            cd.save_test("user-1", "  ", self.result)

    def test_deletion_is_scoped_to_the_owner(self):
        saved_id = cd.save_test("user-1", "Mine", self.result)
        self.assertFalse(cd.delete_test("user-2", saved_id))
        self.assertTrue(cd.delete_test("user-1", saved_id))
        self.assertEqual(cd.get_tests("user-1"), [])

    def test_reading_without_a_user_returns_nothing_rather_than_raising(self):
        self.assertEqual(cd.get_tests(None), [])
        self.assertFalse(cd.delete_test(None, 1))


if __name__ == "__main__":
    unittest.main()
