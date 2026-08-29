"""Tests for the action persistence engine.

The app annualises a first-week saving and calls it a year. This models the
lapse that annualisation assumes away, and the tests guard the properties that
make the correction worth having:

*   the shape parameter carries the substance - a decreasing hazard is what
    makes "the first month is the hard part" expressible, and an exponential
    model cannot represent it at all;
*   expected savings sit below the naive annualisation for every class that
    needs maintenance, and barely below it for the class that does not;
*   the abatement ranking actually reorders, because a ranking that never
    changed would mean the correction was cosmetic;
*   right-censoring is handled - an action still running at the end of the
    window is not a lapse, and a fully-censored history gives a survival of one
    rather than zero;
*   a seasonal lapse pattern is distinguished from abandonment, on the circle
    rather than the line, because December and January are adjacent.

The re-ranking test is the load-bearing one. Ranking on undiscounted annual
savings systematically favours whichever option is most fragile, and a version
of this module that left the order alone would have added arithmetic without
changing a single decision.
"""

import math
import os
import tempfile
import unittest

import src.lifestyle.action_persistence as ap


OPTIONS = [
    {"name": "Shorter showers", "weekly_saving": 2.4,
     "action_class": "daily_effort", "cost": 0.0},
    {"name": "Loft insulation", "weekly_saving": 1.9,
     "action_class": "structural_one_off", "cost": 600.0},
    {"name": "Car share", "weekly_saving": 3.1,
     "action_class": "social_dependent", "cost": 0.0},
    {"name": "Drying rack", "weekly_saving": 1.2,
     "action_class": "equipment_mediated", "cost": 25.0},
    {"name": "Meal plan", "weekly_saving": 1.6,
     "action_class": "periodic_effort", "cost": 0.0},
]


class TestClassTable(unittest.TestCase):

    def test_every_class_explains_itself(self):
        for key in ap.list_action_classes():
            meta = ap.get_action_class(key)
            self.assertGreater(len(meta["note"]), 80)
            self.assertGreater(len(meta["evidence"]), 40)

    def test_every_class_has_positive_parameters(self):
        for key in ap.list_action_classes():
            summary = ap.class_summary(key)
            self.assertGreater(summary["shape"], 0)
            self.assertGreater(summary["scale_weeks"], 0)

    def test_effortful_classes_have_a_falling_hazard(self):
        """The whole reason for Weibull rather than a decay constant."""
        for key in ("daily_effort", "periodic_effort", "social_dependent",
                    "equipment_mediated"):
            self.assertLess(ap.class_summary(key)["shape"], 1.0)
            self.assertEqual(
                ap.class_summary(key)["hazard_direction"], "falling"
            )

    def test_the_structural_class_does_not_need_maintenance(self):
        summary = ap.class_summary("structural_one_off")
        self.assertFalse(summary["requires_effort"])
        self.assertGreater(summary["survival_at_52_weeks"], 0.99)

    def test_the_classes_are_ordered_by_durability_as_described(self):
        durability = [
            ap.class_summary(key)["median_weeks"]
            for key in ("social_dependent", "daily_effort", "periodic_effort",
                        "equipment_mediated", "structural_one_off")
        ]
        self.assertEqual(durability, sorted(durability))

    def test_an_unknown_class_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.get_action_class("wishful_thinking")
        with self.assertRaises(ap.PersistenceError):
            ap.class_summary("wishful_thinking")


class TestWeibull(unittest.TestCase):

    def test_survival_starts_at_one(self):
        self.assertEqual(ap.survival(0, 0.7, 30.0), 1.0)

    def test_survival_is_monotonically_decreasing(self):
        previous = 1.0
        for week in range(1, 200):
            value = ap.survival(week, 0.7, 30.0)
            self.assertLessEqual(value, previous)
            previous = value

    def test_survival_at_the_scale_is_the_reciprocal_of_e(self):
        """A property of the distribution, not of these parameters."""
        for shape in (0.5, 1.0, 2.0, 6.0):
            self.assertAlmostEqual(
                ap.survival(40.0, shape, 40.0), math.exp(-1.0), places=10
            )

    def test_the_median_halves_the_survival(self):
        for key in ap.list_action_classes():
            shape, scale = ap.ACTION_CLASSES[key]["shape"], ap.ACTION_CLASSES[key]["scale"]
            median = ap.median_lifetime(shape, scale)
            self.assertAlmostEqual(
                ap.survival(median, shape, scale), 0.5, places=8
            )

    def test_a_falling_hazard_actually_falls(self):
        early = ap.hazard(2.0, 0.7, 30.0)
        late = ap.hazard(60.0, 0.7, 30.0)
        self.assertGreater(early, late)

    def test_a_rising_hazard_actually_rises(self):
        early = ap.hazard(10.0, 6.0, 1560.0)
        late = ap.hazard(1000.0, 6.0, 1560.0)
        self.assertLess(early, late)

    def test_a_shape_of_one_gives_a_constant_hazard(self):
        """The exponential special case, which is what this module rejects."""
        self.assertAlmostEqual(
            ap.hazard(5.0, 1.0, 40.0), ap.hazard(500.0, 1.0, 40.0), places=12
        )

    def test_negative_time_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.survival(-1.0, 0.7, 30.0)
        with self.assertRaises(ap.PersistenceError):
            ap.hazard(-1.0, 0.7, 30.0)

    def test_non_positive_parameters_are_refused(self):
        for shape, scale in ((0.0, 30.0), (0.7, 0.0), (-1.0, 30.0)):
            with self.assertRaises(ap.PersistenceError):
                ap.survival(5.0, shape, scale)
            with self.assertRaises(ap.PersistenceError):
                ap.median_lifetime(shape, scale)

    def test_the_curve_starts_at_one_and_never_rises(self):
        points = ap.survival_curve("daily_effort")
        self.assertEqual(points[0]["survival"], 1.0)
        values = [point["survival"] for point in points]
        self.assertEqual(values, sorted(values, reverse=True))


class TestExpectedSavings(unittest.TestCase):

    def test_a_habit_saves_less_than_the_naive_annualisation(self):
        result = ap.expected_savings(1.0, "daily_effort")
        self.assertLess(result["expected_first_year"],
                        result["naive_first_year"])
        self.assertGreater(result["first_year_overstatement_share"], 0.3)

    def test_a_structural_action_is_barely_overstated(self):
        result = ap.expected_savings(1.0, "structural_one_off")
        self.assertLess(result["first_year_overstatement_share"], 0.05)

    def test_the_overstatement_orders_the_classes_as_the_notes_claim(self):
        overstatement = {
            key: ap.expected_savings(1.0, key)["first_year_overstatement_share"]
            for key in ap.list_action_classes()
        }
        self.assertGreater(overstatement["social_dependent"],
                           overstatement["daily_effort"])
        self.assertGreater(overstatement["daily_effort"],
                           overstatement["periodic_effort"])
        self.assertGreater(overstatement["periodic_effort"],
                           overstatement["equipment_mediated"])
        self.assertGreater(overstatement["equipment_mediated"],
                           overstatement["structural_one_off"])

    def test_it_scales_linearly_with_the_weekly_saving(self):
        single = ap.expected_savings(1.0, "daily_effort")
        triple = ap.expected_savings(3.0, "daily_effort")
        self.assertAlmostEqual(
            triple["expected_lifetime_saving"],
            single["expected_lifetime_saving"] * 3.0,
            places=2,
        )

    def test_discounting_reduces_the_total(self):
        undiscounted = ap.expected_savings(
            1.0, "structural_one_off", discount_rate=0.0
        )["expected_lifetime_saving"]
        discounted = ap.expected_savings(
            1.0, "structural_one_off", discount_rate=0.08
        )["expected_lifetime_saving"]
        self.assertLess(discounted, undiscounted)

    def test_a_longer_horizon_never_reduces_the_total(self):
        short = ap.expected_savings(
            1.0, "equipment_mediated", horizon_weeks=52
        )["expected_lifetime_saving"]
        long = ap.expected_savings(
            1.0, "equipment_mediated", horizon_weeks=260
        )["expected_lifetime_saving"]
        self.assertGreaterEqual(long, short)

    def test_effective_weeks_is_below_the_horizon_for_a_fragile_action(self):
        result = ap.expected_savings(2.0, "social_dependent",
                                     horizon_weeks=260)
        self.assertLess(result["effective_weeks"], 100)

    def test_a_negative_saving_is_refused_with_a_reason(self):
        with self.assertRaises(ap.PersistenceError) as caught:
            ap.expected_savings(-1.0, "daily_effort")
        self.assertIn("different calculation", str(caught.exception))

    def test_a_zero_horizon_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.expected_savings(1.0, "daily_effort", horizon_weeks=0)


class TestRanking(unittest.TestCase):
    """The load-bearing behaviour: the order actually changes."""

    def test_the_ranking_changes(self):
        result = ap.persistence_adjusted_ranking(OPTIONS)
        self.assertTrue(result["ranking_changed"])
        self.assertTrue(result["moved"])

    def test_the_most_fragile_option_loses_its_top_spot(self):
        result = ap.persistence_adjusted_ranking(OPTIONS)
        car_share = next(
            row for row in result["options"] if row["name"] == "Car share"
        )
        self.assertEqual(car_share["naive_rank"], 1)
        self.assertGreater(car_share["adjusted_rank"], 1)

    def test_the_structural_option_is_promoted(self):
        result = ap.persistence_adjusted_ranking(OPTIONS)
        loft = next(
            row for row in result["options"] if row["name"] == "Loft insulation"
        )
        self.assertLess(loft["adjusted_rank"], loft["naive_rank"])

    def test_the_adjusted_order_is_actually_sorted_by_expected_saving(self):
        result = ap.persistence_adjusted_ranking(OPTIONS)
        values = [row["expected_lifetime_saving"] for row in result["options"]]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_cost_per_unit_uses_the_expected_saving(self):
        result = ap.persistence_adjusted_ranking(OPTIONS)
        loft = next(
            row for row in result["options"] if row["name"] == "Loft insulation"
        )
        self.assertLess(loft["adjusted_cost_per_unit"],
                        loft["naive_cost_per_unit"])

    def test_a_free_option_has_no_cost_per_unit_rather_than_a_zero(self):
        result = ap.persistence_adjusted_ranking(OPTIONS)
        showers = next(
            row for row in result["options"] if row["name"] == "Shorter showers"
        )
        self.assertEqual(showers["adjusted_cost_per_unit"], 0.0)

    def test_an_empty_set_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.persistence_adjusted_ranking([])

    def test_a_non_mapping_option_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.persistence_adjusted_ranking(["shorter showers"])

    def test_an_unknown_class_in_an_option_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.persistence_adjusted_ranking(
                [{"name": "x", "weekly_saving": 1.0, "action_class": "nope"}]
            )


class TestReengagementWindow(unittest.TestCase):

    def test_the_window_holds_the_middle_half_of_lapses(self):
        window = ap.reengagement_window("daily_effort")
        self.assertGreater(window["share_in_window"], 0.4)
        self.assertLess(window["share_in_window"], 0.65)

    def test_the_window_is_not_week_one_despite_the_hazard_peaking_there(self):
        """A prompt at the hazard peak reaches people who have not started."""
        window = ap.reengagement_window("daily_effort")
        self.assertEqual(window["peak_week"], 1)
        self.assertGreater(window["window"][0], 1)

    def test_a_fragile_class_has_an_earlier_window_than_a_durable_one(self):
        fragile = ap.reengagement_window("social_dependent")["window"]
        durable = ap.reengagement_window("equipment_mediated")["window"]
        self.assertLess(fragile[1], durable[1])

    def test_a_class_that_barely_lapses_has_no_window_rather_than_a_spurious_one(self):
        window = ap.reengagement_window("structural_one_off")
        self.assertIsNone(window["window"])
        self.assertIn("never going to stop", window["note"])

    def test_the_window_lies_inside_the_horizon(self):
        window = ap.reengagement_window("daily_effort", horizon_weeks=52)
        self.assertLessEqual(window["window"][1], 52)


class TestKaplanMeier(unittest.TestCase):
    """Right-censoring is where an empirical persistence estimate goes wrong."""

    def test_a_fully_censored_history_gives_a_survival_of_one(self):
        """Nobody has lapsed. Reporting zero would be the classic mistake."""
        result = ap.kaplan_meier(
            [{"duration_weeks": 10, "censored": True}] * 5
        )
        self.assertEqual(result["final_survival"], 1.0)
        self.assertTrue(result["fully_censored"])

    def test_censored_observations_are_counted_separately(self):
        result = ap.kaplan_meier([
            {"duration_weeks": 4},
            {"duration_weeks": 12, "censored": True},
            {"duration_weeks": 20},
        ])
        self.assertEqual(result["observed_lapses"], 2)
        self.assertEqual(result["censored"], 1)

    def test_the_curve_starts_at_one_and_never_rises(self):
        result = ap.kaplan_meier([
            {"duration_weeks": week} for week in (3, 8, 15, 26, 40)
        ])
        values = [point["survival"] for point in result["curve"]]
        self.assertEqual(values[0], 1.0)
        self.assertEqual(values, sorted(values, reverse=True))

    def test_all_lapsed_gives_a_survival_of_zero(self):
        result = ap.kaplan_meier([
            {"duration_weeks": week} for week in (3, 8, 15)
        ])
        self.assertAlmostEqual(result["final_survival"], 0.0)

    def test_censoring_raises_the_estimated_survival(self):
        """The point of handling it: treating censored as lapsed biases down."""
        as_lapses = ap.kaplan_meier([
            {"duration_weeks": 4},
            {"duration_weeks": 10},
            {"duration_weeks": 10},
        ])["final_survival"]
        as_censored = ap.kaplan_meier([
            {"duration_weeks": 4},
            {"duration_weeks": 10, "censored": True},
            {"duration_weeks": 10, "censored": True},
        ])["final_survival"]
        self.assertGreater(as_censored, as_lapses)

    def test_the_median_is_the_first_week_at_or_below_half(self):
        result = ap.kaplan_meier([
            {"duration_weeks": week} for week in (4, 8, 12, 16)
        ])
        self.assertEqual(result["median_weeks"], 8.0)

    def test_a_median_beyond_the_data_is_reported_as_unknown(self):
        result = ap.kaplan_meier([
            {"duration_weeks": 4},
            {"duration_weeks": 10, "censored": True},
            {"duration_weeks": 20, "censored": True},
            {"duration_weeks": 30, "censored": True},
        ])
        self.assertIsNone(result["median_weeks"])

    def test_an_empty_history_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.kaplan_meier([])

    def test_a_negative_duration_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.kaplan_meier([{"duration_weeks": -3}])

    def test_a_missing_duration_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.kaplan_meier([{"censored": True}])


class TestBlending(unittest.TestCase):

    def test_a_thin_history_leaves_the_prior_dominant(self):
        thin = ap.kaplan_meier([{"duration_weeks": 6}, {"duration_weeks": 9}])
        blend = ap.blend_with_prior(thin, "daily_effort")
        self.assertLess(blend["weight_on_own_history"], 0.2)

    def test_a_thick_history_takes_over(self):
        thick = ap.kaplan_meier([
            {"duration_weeks": 5 + index} for index in range(30)
        ])
        blend = ap.blend_with_prior(thick, "daily_effort")
        self.assertEqual(blend["weight_on_own_history"], 1.0)

    def test_the_blend_lies_between_the_two_inputs(self):
        history = ap.kaplan_meier([
            {"duration_weeks": 5 + index} for index in range(10)
        ])
        blend = ap.blend_with_prior(history, "daily_effort")
        low = min(blend["prior_survival"], blend["empirical_survival"])
        high = max(blend["prior_survival"], blend["empirical_survival"])
        self.assertGreaterEqual(blend["blended_survival"], low - 1e-9)
        self.assertLessEqual(blend["blended_survival"], high + 1e-9)

    def test_the_note_names_the_weighting_rather_than_asserting_it(self):
        history = ap.kaplan_meier([{"duration_weeks": 6}])
        blend = ap.blend_with_prior(history, "daily_effort")
        self.assertIn("class prior still dominates", blend["note"])


class TestSeasonality(unittest.TestCase):

    def test_a_winter_cluster_is_recognised_as_seasonal(self):
        """December and January are adjacent, which a linear spread misses."""
        result = ap.seasonal_reactivation([11, 12, 1, 12, 11])
        self.assertTrue(result["seasonal"])
        self.assertIn(result["typical_month"], (11, 12, 1))

    def test_a_spread_pattern_is_not_called_seasonal(self):
        result = ap.seasonal_reactivation([1, 4, 7, 10, 2, 8])
        self.assertFalse(result["seasonal"])
        self.assertIn("survival model stands", result["note"])

    def test_two_events_are_not_enough_to_call_it_a_pattern(self):
        result = ap.seasonal_reactivation([12, 1])
        self.assertFalse(result["seasonal"])

    def test_concentration_is_between_zero_and_one(self):
        for months in ([1, 1, 1], [1, 4, 7, 10], [3, 3, 4, 4, 5]):
            value = ap.seasonal_reactivation(months)["concentration"]
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_perfectly_opposed_months_have_no_concentration(self):
        result = ap.seasonal_reactivation([1, 7, 1, 7])
        self.assertLess(result["concentration"], 1e-9)

    def test_an_impossible_month_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.seasonal_reactivation([0, 5, 9])
        with self.assertRaises(ap.PersistenceError):
            ap.seasonal_reactivation([13])

    def test_an_empty_history_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.seasonal_reactivation([])


class TestPortfolio(unittest.TestCase):

    def test_retention_falls_with_the_horizon(self):
        portfolio = ap.portfolio_persistence(OPTIONS)
        shares = [point["retained_share"]
                  for point in portfolio["horizon_points"]]
        self.assertEqual(shares, sorted(shares, reverse=True))

    def test_a_plan_of_habits_retains_less_than_a_plan_of_retrofits(self):
        habits = ap.portfolio_persistence([
            {"name": "a", "weekly_saving": 2.0,
             "action_class": "daily_effort"},
        ])
        retrofits = ap.portfolio_persistence([
            {"name": "b", "weekly_saving": 2.0,
             "action_class": "structural_one_off"},
        ])
        self.assertLess(
            habits["horizon_points"][-1]["retained_share"],
            retrofits["horizon_points"][-1]["retained_share"],
        )

    def test_two_plans_with_identical_headlines_diverge(self):
        """The finding the module exists to surface."""
        fragile = ap.portfolio_persistence([
            {"name": f"habit {index}", "weekly_saving": 1.0,
             "action_class": "social_dependent"}
            for index in range(4)
        ])
        durable = ap.portfolio_persistence([
            {"name": f"retrofit {index}", "weekly_saving": 1.0,
             "action_class": "structural_one_off"}
            for index in range(4)
        ])
        self.assertAlmostEqual(
            fragile["assumed_weekly_saving"],
            durable["assumed_weekly_saving"],
        )
        self.assertLess(
            fragile["horizon_points"][-1]["surviving_weekly_saving"],
            durable["horizon_points"][-1]["surviving_weekly_saving"] / 2,
        )

    def test_fragile_actions_are_identified(self):
        portfolio = ap.portfolio_persistence(OPTIONS)
        names = {row["name"] for row in portfolio["fragile_actions"]}
        self.assertIn("Car share", names)
        self.assertNotIn("Loft insulation", names)

    def test_the_fragile_share_is_a_proportion(self):
        portfolio = ap.portfolio_persistence(OPTIONS)
        self.assertGreater(portfolio["fragile_share_of_plan"], 0.0)
        self.assertLessEqual(portfolio["fragile_share_of_plan"], 1.0)

    def test_an_empty_portfolio_is_refused(self):
        with self.assertRaises(ap.PersistenceError):
            ap.portfolio_persistence([])


class TestInsights(unittest.TestCase):

    def test_the_reordering_is_described(self):
        ranking = ap.persistence_adjusted_ranking(OPTIONS)
        text = " ".join(ap.get_persistence_insights(ranking))
        self.assertIn("equally permanent", text)

    def test_the_worst_overstatement_is_named(self):
        ranking = ap.persistence_adjusted_ranking(OPTIONS)
        text = " ".join(ap.get_persistence_insights(ranking))
        self.assertIn("most overstated option", text)

    def test_the_portfolio_year_two_figure_is_reported(self):
        ranking = ap.persistence_adjusted_ranking(OPTIONS)
        portfolio = ap.portfolio_persistence(OPTIONS)
        text = " ".join(ap.get_persistence_insights(ranking, portfolio))
        self.assertIn("Two years out", text)

    def test_fragility_is_flagged_without_being_moralised_about(self):
        ranking = ap.persistence_adjusted_ranking(OPTIONS)
        portfolio = ap.portfolio_persistence(OPTIONS)
        text = " ".join(ap.get_persistence_insights(ranking, portfolio))
        self.assertIn("not an argument against them", text)

    def test_an_unchanged_ranking_is_reported_as_such(self):
        same = [
            {"name": "a", "weekly_saving": 10.0,
             "action_class": "daily_effort"},
            {"name": "b", "weekly_saving": 1.0,
             "action_class": "daily_effort"},
        ]
        ranking = ap.persistence_adjusted_ranking(same)
        text = " ".join(ap.get_persistence_insights(ranking))
        self.assertIn("ranking is unchanged", text)


class TestPersistenceStorage(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = ap.DB_NAME
        ap.DB_NAME = self.path
        self.portfolio = ap.portfolio_persistence(OPTIONS)

    def tearDown(self):
        ap.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_plan_comes_back(self):
        plan_id = ap.save_plan("user-1", "Autumn plan", self.portfolio)
        self.assertIsInstance(plan_id, int)
        rows = ap.get_plans("user-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Autumn plan")

    def test_the_year_two_figure_survives_a_round_trip(self):
        ap.save_plan("user-1", "Round trip", self.portfolio)
        row = ap.get_plans("user-1")[0]
        self.assertLess(row["expected_year_two_saving"],
                        row["assumed_weekly_saving"])

    def test_users_do_not_see_each_others_plans(self):
        ap.save_plan("user-1", "Mine", self.portfolio)
        self.assertEqual(ap.get_plans("user-2"), [])

    def test_a_plan_needs_a_user_and_a_name(self):
        with self.assertRaises(ap.PersistenceError):
            ap.save_plan("", "Named", self.portfolio)
        with self.assertRaises(ap.PersistenceError):
            ap.save_plan("user-1", "   ", self.portfolio)

    def test_deletion_is_scoped_to_the_owner(self):
        plan_id = ap.save_plan("user-1", "Mine", self.portfolio)
        self.assertFalse(ap.delete_plan("user-2", plan_id))
        self.assertTrue(ap.delete_plan("user-1", plan_id))
        self.assertEqual(ap.get_plans("user-1"), [])

    def test_reading_without_a_user_returns_nothing_rather_than_raising(self):
        self.assertEqual(ap.get_plans(None), [])
        self.assertFalse(ap.delete_plan(None, 1))


if __name__ == "__main__":
    unittest.main()
