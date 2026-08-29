"""Tests for the footprint decomposition engine.

The app could always report that a footprint moved. This module reports why,
and the tests guard the properties that make an attribution worth reading
rather than merely present:

*   the decomposition closes exactly - effects sum to the observed change with
    no residual, which is the property LMDI was chosen for and the one that
    distinguishes it from the naive alternative;
*   a category that appears or disappears is handled by the analytical limit
    rather than crashing, and its emissions land in the structure effect;
*   what the user did and what happened to the user are reported apart, and a
    reduction delivered entirely by a decarbonising grid is described as such;
*   the multiplicative form's indices multiply back to the total ratio;
*   the logarithmic mean is accurate where the closed form is not.

The closure test is the load-bearing one. An additive decomposition that leaves
a residual invites the reader to assume the residual was theirs, which is the
specific error this module exists to prevent, and a version that quietly
absorbed the remainder into one of the named effects would be worse than no
module at all.
"""

import math
import os
import tempfile
import unittest

import src.utils.footprint_decomposition as fd


def transport_before(unit="km"):
    return fd.build_period("2024", {
        "car": {"activity": 9000, "energy": 5400, "emissions": 1350},
        "rail": {"activity": 1000, "energy": 300, "emissions": 60},
        "air": {"activity": 4000, "energy": 1200, "emissions": 900},
    }, activity_unit=unit)


def transport_after(unit="km"):
    return fd.build_period("2025", {
        "car": {"activity": 6000, "energy": 3300, "emissions": 700},
        "rail": {"activity": 4000, "energy": 1100, "emissions": 180},
        "air": {"activity": 0, "energy": 0, "emissions": 0},
        "ebike": {"activity": 1500, "energy": 25, "emissions": 4},
    }, activity_unit=unit)


class TestLogarithmicMean(unittest.TestCase):

    def test_equal_arguments_return_the_argument(self):
        self.assertAlmostEqual(fd.logarithmic_mean(7.0, 7.0), 7.0)

    def test_it_sits_between_the_geometric_and_arithmetic_means(self):
        a, b = 3.0, 11.0
        self.assertLess(math.sqrt(a * b), fd.logarithmic_mean(a, b))
        self.assertLess(fd.logarithmic_mean(a, b), (a + b) / 2.0)

    def test_it_is_symmetric(self):
        self.assertAlmostEqual(
            fd.logarithmic_mean(4.0, 19.0), fd.logarithmic_mean(19.0, 4.0)
        )

    def test_the_series_branch_agrees_with_high_precision_arithmetic(self):
        """Where the closed form loses digits to cancellation, this must not."""
        from decimal import Decimal, getcontext
        getcontext().prec = 50
        a, b = 1000.0, 1000.00001
        exact = float(
            (Decimal(b) - Decimal(a))
            / (Decimal(b).ln() - Decimal(a).ln())
        )
        self.assertAlmostEqual(fd.logarithmic_mean(a, b), exact, places=6)

    def test_the_series_branch_is_actually_taken(self):
        a = 500.0
        b = a * (1 + 1e-8)
        self.assertLess(abs((b - a) / (a + b)), fd.SERIES_THRESHOLD)
        self.assertAlmostEqual(fd.logarithmic_mean(a, b), a, places=4)

    def test_non_positive_arguments_are_refused(self):
        with self.assertRaises(fd.DecompositionError):
            fd.logarithmic_mean(0.0, 5.0)
        with self.assertRaises(fd.DecompositionError):
            fd.logarithmic_mean(-1.0, 5.0)


class TestPeriodConstruction(unittest.TestCase):

    def test_a_period_needs_a_label(self):
        with self.assertRaises(fd.DecompositionError):
            fd.build_period("  ", {"a": {"activity": 1, "emissions": 1}})

    def test_a_period_needs_categories(self):
        with self.assertRaises(fd.DecompositionError):
            fd.build_period("2024", {})

    def test_a_category_needs_activity_and_emissions(self):
        with self.assertRaises(fd.DecompositionError):
            fd.build_period("2024", {"a": {"activity": 5}})

    def test_negative_quantities_are_refused(self):
        with self.assertRaises(fd.DecompositionError):
            fd.build_period("2024", {"a": {"activity": -1, "emissions": 1}})

    def test_mixing_categories_with_and_without_energy_is_refused(self):
        """The two halves would not mean the same thing and must not be summed."""
        with self.assertRaises(fd.DecompositionError) as caught:
            fd.build_period("2024", {
                "a": {"activity": 10, "energy": 5, "emissions": 2},
                "b": {"activity": 10, "emissions": 2},
            })
        self.assertIn("every category or for none", str(caught.exception))

    def test_totals_are_computed(self):
        period = transport_before()
        self.assertAlmostEqual(period["total_emissions"], 2310.0)
        self.assertAlmostEqual(period["total_activity"], 14000.0)
        self.assertTrue(period["has_energy"])

    def test_a_period_without_energy_reports_so(self):
        period = fd.build_period("2024", {
            "a": {"activity": 10, "emissions": 2},
        })
        self.assertFalse(period["has_energy"])


class TestModeSelection(unittest.TestCase):

    def test_energy_on_both_sides_gives_four_factors(self):
        result = fd.decompose(transport_before(), transport_after())
        self.assertEqual(result["mode"], "four_factor")
        self.assertEqual(len(result["effect_keys"]), 4)

    def test_no_energy_gives_three_factors(self):
        before = fd.build_period("a", {"x": {"activity": 10, "emissions": 5}})
        after = fd.build_period("b", {"x": {"activity": 8, "emissions": 3}})
        result = fd.decompose(before, after)
        self.assertEqual(result["mode"], "three_factor")
        self.assertNotIn("factor", result["effects"])

    def test_mismatched_activity_units_are_refused(self):
        with self.assertRaises(fd.DecompositionError) as caught:
            fd.decompose(transport_before("km"), transport_after("miles"))
        self.assertIn("activity unit", str(caught.exception))

    def test_one_period_with_energy_and_one_without_is_refused(self):
        before = transport_before()
        after = fd.build_period("2025", {
            "car": {"activity": 6000, "emissions": 700},
        }, activity_unit="km")
        with self.assertRaises(fd.DecompositionError):
            fd.decompose(before, after)


class TestPerfectDecomposition(unittest.TestCase):
    """The property the whole module rests on."""

    def test_the_effects_sum_to_the_observed_change(self):
        result = fd.decompose(transport_before(), transport_after())
        self.assertTrue(result["perfectly_decomposed"])
        self.assertAlmostEqual(
            sum(result["effects"].values()),
            result["observed_change"],
            places=2,
        )

    def test_the_residual_is_zero_to_floating_point(self):
        result = fd.decompose(transport_before(), transport_after())
        self.assertLess(abs(result["residual"]), 1e-6)

    def test_it_closes_for_an_increase_as_well_as_a_decrease(self):
        result = fd.decompose(transport_after(), transport_before())
        self.assertTrue(result["perfectly_decomposed"])
        self.assertGreater(result["observed_change"], 0)

    def test_it_closes_when_nothing_changed(self):
        period = transport_before()
        result = fd.decompose(period, period)
        self.assertAlmostEqual(result["observed_change"], 0.0)
        for value in result["effects"].values():
            self.assertAlmostEqual(value, 0.0, places=6)

    def test_it_closes_in_three_factor_mode(self):
        before = fd.build_period("a", {
            "food": {"activity": 800, "emissions": 1600},
            "goods": {"activity": 300, "emissions": 900},
        }, activity_unit="kg")
        after = fd.build_period("b", {
            "food": {"activity": 750, "emissions": 1200},
            "goods": {"activity": 420, "emissions": 1000},
        }, activity_unit="kg")
        result = fd.decompose(before, after)
        self.assertTrue(result["perfectly_decomposed"])

    def test_it_closes_across_a_wide_range_of_magnitudes(self):
        before = fd.build_period("a", {
            "tiny": {"activity": 0.004, "energy": 0.002, "emissions": 0.0005},
            "huge": {"activity": 90000, "energy": 41000, "emissions": 15000},
        }, activity_unit="units")
        after = fd.build_period("b", {
            "tiny": {"activity": 0.02, "energy": 0.01, "emissions": 0.003},
            "huge": {"activity": 61000, "energy": 25000, "emissions": 7000},
        }, activity_unit="units")
        result = fd.decompose(before, after)
        self.assertLess(abs(result["residual"]), 1e-5)

    def test_it_closes_when_a_category_is_unchanged_alongside_a_changed_one(self):
        """The near-equal branch of the logarithmic mean, in context."""
        before = fd.build_period("a", {
            "flat": {"activity": 500, "energy": 250, "emissions": 120},
            "moving": {"activity": 500, "energy": 250, "emissions": 120},
        }, activity_unit="units")
        after = fd.build_period("b", {
            "flat": {"activity": 500, "energy": 250, "emissions": 120},
            "moving": {"activity": 900, "energy": 500, "emissions": 300},
        }, activity_unit="units")
        result = fd.decompose(before, after)
        self.assertTrue(result["perfectly_decomposed"])


class TestZeroHandling(unittest.TestCase):
    """Appearing and disappearing categories are most of the data."""

    def test_a_new_category_does_not_crash(self):
        before = fd.build_period("a", {
            "car": {"activity": 100, "energy": 60, "emissions": 20},
        }, activity_unit="km")
        after = fd.build_period("b", {
            "car": {"activity": 100, "energy": 60, "emissions": 20},
            "ev": {"activity": 50, "energy": 10, "emissions": 2},
        }, activity_unit="km")
        result = fd.decompose(before, after)
        self.assertTrue(result["perfectly_decomposed"])

    def test_a_new_categorys_emissions_land_in_the_structure_effect(self):
        """The analytical limit, and also the intuitively right answer.

        Convergence towards the limit is logarithmic in the substituted value,
        so the structure effect approaches but does not reach the category's
        emissions. What must hold exactly is that the category's four effects
        sum to its change; the rest is a bound.
        """
        before = fd.build_period("a", {
            "car": {"activity": 100, "energy": 60, "emissions": 20},
        }, activity_unit="km")
        after = fd.build_period("b", {
            "car": {"activity": 100, "energy": 60, "emissions": 20},
            "ev": {"activity": 50, "energy": 10, "emissions": 2},
        }, activity_unit="km")
        result = fd.decompose(before, after)
        row = next(r for r in result["categories"] if r["category"] == "ev")

        self.assertAlmostEqual(sum(row["effects"].values()), 2.0, places=5)
        structure = row["effects"]["structure"]
        self.assertGreater(structure, 1.8)
        self.assertLess(structure, 2.2)
        for effect in ("activity", "intensity", "factor"):
            self.assertLess(abs(row["effects"][effect]), 0.25)

    def test_a_removed_category_is_flagged_and_closes(self):
        result = fd.decompose(transport_before(), transport_after())
        row = next(r for r in result["categories"] if r["category"] == "air")
        self.assertTrue(row["disappeared"])
        self.assertAlmostEqual(row["change"], -900.0)
        self.assertTrue(result["perfectly_decomposed"])

    def test_appearance_and_disappearance_are_both_flagged(self):
        result = fd.decompose(transport_before(), transport_after())
        appeared = [r["category"] for r in result["categories"] if r["appeared"]]
        gone = [r["category"] for r in result["categories"] if r["disappeared"]]
        self.assertIn("ebike", appeared)
        self.assertIn("air", gone)

    def test_a_period_of_entirely_zero_emissions_does_not_divide_by_zero(self):
        before = fd.build_period("a", {
            "x": {"activity": 0, "energy": 0, "emissions": 0},
        }, activity_unit="units")
        after = fd.build_period("b", {
            "x": {"activity": 10, "energy": 4, "emissions": 3},
        }, activity_unit="units")
        result = fd.decompose(before, after)
        self.assertTrue(result["perfectly_decomposed"])


class TestAttributionSplit(unittest.TestCase):
    """Separating what the user did from what happened to the user."""

    def test_the_two_subtotals_reconstruct_the_change(self):
        result = fd.decompose(transport_before(), transport_after())
        self.assertAlmostEqual(
            result["attributable_change"] + result["exogenous_change"],
            result["observed_change"],
            places=3,
        )

    def test_a_pure_grid_improvement_is_entirely_exogenous(self):
        """Same behaviour, cleaner electricity. The user did nothing."""
        before = fd.build_period("2024", {
            "power": {"activity": 3000, "energy": 3000, "emissions": 750},
        }, activity_unit="kWh")
        after = fd.build_period("2025", {
            "power": {"activity": 3000, "energy": 3000, "emissions": 500},
        }, activity_unit="kWh")
        result = fd.decompose(before, after)
        self.assertAlmostEqual(result["attributable_change"], 0.0, places=3)
        self.assertAlmostEqual(result["exogenous_change"], -250.0, places=3)

    def test_a_pure_behaviour_change_is_entirely_attributable(self):
        """Less electricity, same grid."""
        before = fd.build_period("2024", {
            "power": {"activity": 3000, "energy": 3000, "emissions": 750},
        }, activity_unit="kWh")
        after = fd.build_period("2025", {
            "power": {"activity": 2000, "energy": 2000, "emissions": 500},
        }, activity_unit="kWh")
        result = fd.decompose(before, after)
        self.assertAlmostEqual(result["exogenous_change"], 0.0, places=3)
        self.assertAlmostEqual(result["attributable_change"], -250.0, places=3)

    def test_three_factor_mode_reports_no_exogenous_component(self):
        before = fd.build_period("a", {"x": {"activity": 10, "emissions": 5}})
        after = fd.build_period("b", {"x": {"activity": 10, "emissions": 3}})
        result = fd.decompose(before, after)
        self.assertAlmostEqual(result["exogenous_change"], 0.0)


class TestCounterfactual(unittest.TestCase):

    def test_it_removes_the_supply_side_credit(self):
        before = fd.build_period("2024", {
            "power": {"activity": 3000, "energy": 3000, "emissions": 750},
        }, activity_unit="kWh")
        after = fd.build_period("2025", {
            "power": {"activity": 3000, "energy": 3000, "emissions": 500},
        }, activity_unit="kWh")
        counter = fd.counterfactual_footprint(fd.decompose(before, after))
        self.assertAlmostEqual(counter["without_supply_change"], 750.0, places=2)
        self.assertAlmostEqual(counter["supply_credit"], 250.0, places=2)
        self.assertAlmostEqual(counter["own_change"], 0.0, places=3)

    def test_it_refuses_in_three_factor_mode(self):
        """Nothing to remove: the two effects are merged and cannot be split."""
        before = fd.build_period("a", {"x": {"activity": 10, "emissions": 5}})
        after = fd.build_period("b", {"x": {"activity": 10, "emissions": 3}})
        result = fd.decompose(before, after)
        with self.assertRaises(fd.DecompositionError) as caught:
            fd.counterfactual_footprint(result)
        self.assertIn("four-factor", str(caught.exception))


class TestMultiplicativeForm(unittest.TestCase):

    def test_the_indices_multiply_back_to_the_total_ratio(self):
        result = fd.decompose_multiplicative(transport_before(), transport_after())
        self.assertTrue(result["closes"])
        self.assertAlmostEqual(
            result["product"], result["total_ratio"], places=6
        )

    def test_no_change_gives_unit_indices(self):
        period = transport_before()
        result = fd.decompose_multiplicative(period, period)
        for value in result["indices"].values():
            self.assertAlmostEqual(value, 1.0, places=6)

    def test_percent_change_is_reported_per_effect(self):
        result = fd.decompose_multiplicative(transport_before(), transport_after())
        self.assertEqual(
            set(result["percent_change"]), set(result["indices"])
        )


class TestChaining(unittest.TestCase):

    def test_chaining_needs_two_periods(self):
        with self.assertRaises(fd.DecompositionError):
            fd.decompose_chain([transport_before()])

    def test_each_step_closes(self):
        middle = fd.build_period("mid", {
            "car": {"activity": 7500, "energy": 4300, "emissions": 1000},
            "rail": {"activity": 2500, "energy": 700, "emissions": 120},
            "air": {"activity": 2000, "energy": 600, "emissions": 450},
        }, activity_unit="km")
        chain = fd.decompose_chain(
            [transport_before(), middle, transport_after()]
        )
        for step in chain["steps"]:
            self.assertTrue(step["perfectly_decomposed"])

    def test_the_chained_total_matches_the_observed_change(self):
        middle = fd.build_period("mid", {
            "car": {"activity": 7500, "energy": 4300, "emissions": 1000},
            "rail": {"activity": 2500, "energy": 700, "emissions": 120},
            "air": {"activity": 2000, "energy": 600, "emissions": 450},
        }, activity_unit="km")
        chain = fd.decompose_chain(
            [transport_before(), middle, transport_after()]
        )
        self.assertAlmostEqual(
            sum(chain["chained_effects"].values()),
            chain["observed_change"],
            places=2,
        )

    def test_path_dependence_is_reported_rather_than_hidden(self):
        """Three distinct points: the route taken changes the attribution."""
        first = fd.build_period("first", {
            "a": {"activity": 100, "energy": 50, "emissions": 25},
            "b": {"activity": 100, "energy": 50, "emissions": 25},
        }, activity_unit="units")
        second = fd.build_period("second", {
            "a": {"activity": 900, "energy": 450, "emissions": 220},
            "b": {"activity": 20, "energy": 10, "emissions": 5},
        }, activity_unit="units")
        third = fd.build_period("third", {
            "a": {"activity": 300, "energy": 150, "emissions": 60},
            "b": {"activity": 600, "energy": 300, "emissions": 180},
        }, activity_unit="units")
        chain = fd.decompose_chain([first, second, third])
        self.assertTrue(chain["path_dependent"])
        self.assertGreater(chain["path_dependence_share"], 0.05)

    def test_a_closed_loop_cancels_exactly(self):
        """LMDI-I is time-reversal invariant, so there and back is nothing."""
        start = fd.build_period("start", {
            "a": {"activity": 100, "energy": 50, "emissions": 25},
            "b": {"activity": 100, "energy": 50, "emissions": 25},
        }, activity_unit="units")
        away = fd.build_period("away", {
            "a": {"activity": 900, "energy": 450, "emissions": 220},
            "b": {"activity": 20, "energy": 10, "emissions": 5},
        }, activity_unit="units")
        chain = fd.decompose_chain([start, away, start])
        for value in chain["chained_effects"].values():
            self.assertAlmostEqual(value, 0.0, places=6)
        self.assertFalse(chain["path_dependent"])

    def test_a_monotone_history_is_not_flagged_as_path_dependent(self):
        periods = []
        for index, scale in enumerate((1.0, 0.9, 0.8)):
            periods.append(fd.build_period(f"p{index}", {
                "a": {
                    "activity": 100 * scale,
                    "energy": 50 * scale,
                    "emissions": 25 * scale,
                },
            }, activity_unit="units"))
        chain = fd.decompose_chain(periods)
        self.assertFalse(chain["path_dependent"])


class TestDerivedViews(unittest.TestCase):

    def test_the_waterfall_opens_and_closes_on_the_totals(self):
        result = fd.decompose(transport_before(), transport_after())
        rows = fd.waterfall(result)
        self.assertAlmostEqual(rows[0]["running"], result["before_total"])
        self.assertAlmostEqual(rows[-1]["running"], result["after_total"])

    def test_the_waterfall_running_total_reaches_the_end_total(self):
        result = fd.decompose(transport_before(), transport_after())
        rows = fd.waterfall(result)
        last_effect = [r for r in rows if r["kind"] == "effect"][-1]
        self.assertAlmostEqual(
            last_effect["running"], result["after_total"], places=2
        )

    def test_category_contributions_sum_to_the_effect_total(self):
        result = fd.decompose(transport_before(), transport_after())
        for effect in result["effect_keys"]:
            rows = fd.category_effect_table(result, effect)
            self.assertAlmostEqual(
                sum(r["value"] for r in rows),
                result["effects"][effect],
                places=3,
            )

    def test_an_unknown_effect_is_refused(self):
        result = fd.decompose(transport_before(), transport_after())
        with self.assertRaises(fd.DecompositionError):
            fd.category_effect_table(result, "vibes")

    def test_the_dominant_effect_is_the_largest_by_magnitude(self):
        result = fd.decompose(transport_before(), transport_after())
        top = fd.dominant_effect(result)
        for value in result["effects"].values():
            self.assertLessEqual(abs(value), abs(top["value"]) + 1e-9)

    def test_the_dominant_effect_reports_whether_it_was_the_users_doing(self):
        result = fd.decompose(transport_before(), transport_after())
        self.assertIn("attributable", fd.dominant_effect(result))


class TestInsights(unittest.TestCase):

    def test_insights_are_produced(self):
        insights = fd.get_decomposition_insights(
            fd.decompose(transport_before(), transport_after())
        )
        self.assertGreater(len(insights), 2)

    def test_a_grid_driven_reduction_is_named_as_such(self):
        before = fd.build_period("2024", {
            "power": {"activity": 3000, "energy": 3000, "emissions": 900},
        }, activity_unit="kWh")
        after = fd.build_period("2025", {
            "power": {"activity": 3000, "energy": 3000, "emissions": 450},
        }, activity_unit="kWh")
        text = " ".join(
            fd.get_decomposition_insights(fd.decompose(before, after))
        )
        self.assertIn("not this user's doing", text)
        self.assertIn("Most of this improvement was the grid", text)

    def test_three_factor_mode_warns_that_the_effects_are_merged(self):
        before = fd.build_period("a", {"x": {"activity": 10, "emissions": 5}})
        after = fd.build_period("b", {"x": {"activity": 10, "emissions": 3}})
        text = " ".join(
            fd.get_decomposition_insights(fd.decompose(before, after))
        )
        self.assertIn("three-factor", text)

    def test_a_compositional_reduction_is_distinguished_from_doing_less(self):
        before = fd.build_period("a", {
            "beef": {"activity": 50, "energy": 50, "emissions": 1500},
            "beans": {"activity": 50, "energy": 50, "emissions": 50},
        }, activity_unit="kg")
        after = fd.build_period("b", {
            "beef": {"activity": 10, "energy": 10, "emissions": 300},
            "beans": {"activity": 90, "energy": 90, "emissions": 90},
        }, activity_unit="kg")
        text = " ".join(
            fd.get_decomposition_insights(fd.decompose(before, after))
        )
        self.assertIn("compositional", text)

    def test_a_disappearing_category_prompts_a_check_on_the_logging(self):
        text = " ".join(
            fd.get_decomposition_insights(
                fd.decompose(transport_before(), transport_after())
            )
        )
        self.assertIn("whether the activity stopped or the logging did", text)


class TestReferenceTables(unittest.TestCase):

    def test_every_effect_explains_itself(self):
        for key in fd.list_effects():
            self.assertGreater(len(fd.get_effect(key)["note"]), 60)

    def test_exactly_one_effect_is_exogenous(self):
        self.assertEqual(len(fd.EXOGENOUS_EFFECTS), 1)
        self.assertEqual(fd.EXOGENOUS_EFFECTS[0], "factor")

    def test_every_mode_explains_itself(self):
        for key in fd.list_modes():
            self.assertGreater(len(fd.get_mode(key)["note"]), 60)

    def test_unknown_lookups_are_refused(self):
        with self.assertRaises(fd.DecompositionError):
            fd.get_effect("nope")
        with self.assertRaises(fd.DecompositionError):
            fd.get_mode("nope")


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = fd.DB_NAME
        fd.DB_NAME = self.path
        self.result = fd.decompose(transport_before(), transport_after())

    def tearDown(self):
        fd.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_decomposition_comes_back(self):
        saved_id = fd.save_decomposition("user-1", "Transport 2024 to 2025",
                                         self.result)
        self.assertIsInstance(saved_id, int)
        rows = fd.get_decompositions("user-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Transport 2024 to 2025")

    def test_the_attribution_split_survives_a_round_trip(self):
        fd.save_decomposition("user-1", "Round trip", self.result)
        row = fd.get_decompositions("user-1")[0]
        self.assertAlmostEqual(
            row["attributable_change"], self.result["attributable_change"], 3
        )
        self.assertAlmostEqual(
            row["exogenous_change"], self.result["exogenous_change"], 3
        )

    def test_users_do_not_see_each_others_decompositions(self):
        fd.save_decomposition("user-1", "Mine", self.result)
        self.assertEqual(fd.get_decompositions("user-2"), [])

    def test_a_decomposition_needs_a_user_and_a_name(self):
        with self.assertRaises(fd.DecompositionError):
            fd.save_decomposition("", "Named", self.result)
        with self.assertRaises(fd.DecompositionError):
            fd.save_decomposition("user-1", "   ", self.result)

    def test_deletion_is_scoped_to_the_owner(self):
        saved_id = fd.save_decomposition("user-1", "Mine", self.result)
        self.assertFalse(fd.delete_decomposition("user-2", saved_id))
        self.assertTrue(fd.delete_decomposition("user-1", saved_id))
        self.assertEqual(fd.get_decompositions("user-1"), [])

    def test_reading_without_a_user_returns_nothing_rather_than_raising(self):
        self.assertEqual(fd.get_decompositions(None), [])
        self.assertFalse(fd.delete_decomposition(None, 1))


if __name__ == "__main__":
    unittest.main()
