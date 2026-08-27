"""Tests for the cross-impact burden shifting engine.

This repository computes climate, water, land, biodiversity, nutrient,
toxicity, resource and plastic impacts, each on its own page in its own unit.
This puts them in one frame, and the tests guard the properties that make that
frame honest rather than merely convenient:

*   burden shifting is detected on the disaggregated movement, so a change that
    improves the weighted total and triples freshwater impact is still flagged;
*   categories with no agreed safe level are reported as un-normalisable rather
    than given an invented boundary;
*   coverage is stated, because a favourable profile across the categories that
    were measured says nothing about the ones that were not;
*   dominated options are separated from the ones that genuinely require a
    value judgement, and only the second set needs a weighting;
*   the carbon-only weighting set reproduces the app's current implicit
    behaviour, and the winner changing when it is switched away from is the
    finding.

The burden-shift detector is the load-bearing one. A detector that looked only
at a weighted total would miss exactly the cases it exists for, and there is a
test constructed so the net movement is an improvement while the shift is real.
"""

import os
import tempfile
import unittest

import src.environment.burden_shifting as bs


DAIRY = {
    "climate_change": 1400.0, "water_scarcity": 900.0, "land_use": 1800.0,
    "biodiversity_loss": 42000.0, "eutrophication_freshwater": 0.09,
    "eutrophication_marine": 3.4, "resource_depletion": 0.002,
    "human_toxicity": 2.1e-5, "ecotoxicity": 2600.0, "plastic_leakage": 0.4,
}

ALMOND = {
    "climate_change": 520.0, "water_scarcity": 4200.0, "land_use": 900.0,
    "biodiversity_loss": 31000.0, "eutrophication_freshwater": 0.05,
    "eutrophication_marine": 1.1, "resource_depletion": 0.003,
    "human_toxicity": 4.4e-5, "ecotoxicity": 9100.0, "plastic_leakage": 0.9,
}

OAT = {
    "climate_change": 600.0, "water_scarcity": 700.0, "land_use": 1100.0,
    "biodiversity_loss": 26000.0, "eutrophication_freshwater": 0.06,
    "eutrophication_marine": 1.6, "resource_depletion": 0.002,
    "human_toxicity": 1.8e-5, "ecotoxicity": 2100.0, "plastic_leakage": 0.5,
}


class TestImpactTable(unittest.TestCase):

    def test_every_category_explains_itself(self):
        for key in bs.list_impacts():
            self.assertGreater(len(bs.get_impact(key)["note"]), 80)

    def test_every_category_names_the_module_that_produces_it(self):
        for key in bs.list_impacts():
            self.assertTrue(bs.get_impact(key)["module"].startswith("src."))

    def test_every_category_has_a_positive_global_average(self):
        for key in bs.list_impacts():
            self.assertGreater(bs.get_impact(key)["global_average"], 0.0)

    def test_every_category_states_its_confidence(self):
        allowed = {"well established", "moderately established",
                   "contested", "no boundary defined"}
        for key in bs.list_impacts():
            self.assertIn(bs.get_impact(key)["confidence"], allowed)

    def test_categories_without_a_boundary_say_so_in_their_confidence(self):
        """The honest pairing: no boundary and no claim that there is one."""
        for key in bs.list_impacts():
            meta = bs.get_impact(key)
            if meta["boundary"] is None:
                self.assertEqual(meta["confidence"], "no boundary defined")

    def test_at_least_one_category_has_no_boundary(self):
        """Otherwise the un-normalisable path would never be exercised."""
        without = [
            key for key in bs.list_impacts()
            if bs.get_impact(key)["boundary"] is None
        ]
        self.assertGreaterEqual(len(without), 1)

    def test_the_global_average_exceeds_the_boundary_where_one_exists(self):
        """Every quantified boundary in this table is already transgressed."""
        for key in bs.list_impacts():
            meta = bs.get_impact(key)
            if meta["boundary"] is not None:
                self.assertGreater(meta["global_average"], meta["boundary"])

    def test_an_unknown_category_is_refused(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.get_impact("vibes")


class TestNormalisation(unittest.TestCase):

    def test_shares_are_the_amount_over_the_reference(self):
        result = bs.normalise({"climate_change": 985.0}, "boundary")
        row = next(
            r for r in result["ranked"] if r["category"] == "climate_change"
        )
        self.assertAlmostEqual(row["share"], 1.0, places=6)

    def test_the_two_references_disagree_sharply(self):
        """They answer different questions and this is the size of the gap."""
        against_boundary = bs.normalise(DAIRY, "boundary")["worst_share"]
        against_average = bs.normalise(DAIRY, "global_average")["worst_share"]
        self.assertGreater(against_boundary, against_average * 2)

    def test_categories_without_a_boundary_are_not_given_one(self):
        result = bs.normalise(DAIRY, "boundary")
        self.assertIn("human_toxicity", result["unnormalisable"])
        row = next(
            r for r in result["categories"]
            if r["category"] == "human_toxicity"
        )
        self.assertIsNone(row["share"])

    def test_the_same_categories_normalise_against_the_average(self):
        result = bs.normalise(DAIRY, "global_average")
        self.assertEqual(result["unnormalisable"], [])
        self.assertAlmostEqual(result["scored_coverage"], 1.0, places=6)

    def test_the_worst_category_is_the_largest_share(self):
        result = bs.normalise(DAIRY, "boundary")
        for row in result["ranked"]:
            self.assertLessEqual(row["share"], result["worst_share"] + 1e-12)

    def test_categories_over_the_reference_are_listed(self):
        result = bs.normalise({"climate_change": 2000.0}, "boundary")
        self.assertEqual(result["over_reference"], ["climate_change"])

    def test_a_partial_profile_reports_what_is_missing(self):
        result = bs.normalise({"climate_change": 500.0}, "boundary")
        self.assertLess(result["coverage"], 1.0)
        self.assertIn("water_scarcity", result["missing"])

    def test_an_unknown_category_is_refused(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.normalise({"vibes": 1.0})

    def test_a_negative_impact_is_refused_with_a_reason(self):
        with self.assertRaises(bs.BurdenShiftError) as caught:
            bs.normalise({"climate_change": -10.0})
        self.assertIn("avoided burden", str(caught.exception))

    def test_an_empty_profile_is_refused(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.normalise({})

    def test_an_unknown_reference_is_refused(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.normalise(DAIRY, "vibes")


class TestCoverage(unittest.TestCase):

    def test_a_partial_profile_is_warned_about(self):
        report = bs.coverage_report(
            bs.normalise({"climate_change": 500.0}, "boundary")
        )
        self.assertFalse(report["complete"])
        self.assertTrue(
            any("says nothing about the ones that were not" in warning
                for warning in report["warnings"])
        )

    def test_missing_boundaries_are_warned_about(self):
        report = bs.coverage_report(bs.normalise(DAIRY, "boundary"))
        self.assertTrue(
            any("resting on nothing" in warning
                for warning in report["warnings"])
        )

    def test_contested_references_are_warned_about(self):
        report = bs.coverage_report(bs.normalise(DAIRY, "boundary"))
        self.assertTrue(
            any("weaker than it looks" in warning
                for warning in report["warnings"])
        )

    def test_a_complete_profile_is_marked_complete(self):
        report = bs.coverage_report(bs.normalise(DAIRY, "boundary"))
        self.assertTrue(report["complete"])
        self.assertEqual(report["measured"], report["total_categories"])


class TestWeighting(unittest.TestCase):

    def test_every_weighting_set_explains_itself(self):
        for key in bs.list_weightings():
            self.assertGreater(len(bs.get_weighting(key)["note"]), 80)

    def test_carbon_only_reproduces_the_apps_current_behaviour(self):
        normalised = bs.normalise(DAIRY, "boundary")
        score = bs.weighted_score(normalised, "carbon_only")
        climate = next(
            row for row in normalised["ranked"]
            if row["category"] == "climate_change"
        )
        self.assertAlmostEqual(score["score"], climate["share"], places=6)

    def test_equal_weighting_sums_the_shares(self):
        normalised = bs.normalise(DAIRY, "boundary")
        score = bs.weighted_score(normalised, "equal")
        self.assertAlmostEqual(
            score["score"],
            sum(row["share"] for row in normalised["ranked"]),
            places=6,
        )

    def test_the_weighting_sets_give_materially_different_scores(self):
        normalised = bs.normalise(DAIRY, "boundary")
        scores = {
            key: bs.weighted_score(normalised, key)["score"]
            for key in bs.list_weightings()
        }
        self.assertGreater(max(scores.values()), min(scores.values()) * 2)

    def test_distance_to_boundary_weights_are_normalised_to_one(self):
        weights = bs.get_weighting("distance_to_boundary")["weights"]
        self.assertAlmostEqual(max(weights.values()), 1.0, places=6)

    def test_categories_without_a_boundary_fall_back_rather_than_to_zero(self):
        weights = bs.get_weighting("distance_to_boundary")["weights"]
        self.assertGreater(weights["human_toxicity"], 0.0)

    def test_the_score_is_always_labelled_with_its_weighting(self):
        score = bs.weighted_score(bs.normalise(DAIRY), "equal")
        self.assertIn("weighting_label", score)
        self.assertIn("weighting_note", score)

    def test_excluded_categories_are_named_on_the_score(self):
        score = bs.weighted_score(bs.normalise(DAIRY, "boundary"), "equal")
        self.assertIn("human_toxicity", score["excluded"])

    def test_there_is_no_unweighted_option(self):
        """Summing normalised impacts is itself equal weighting."""
        with self.assertRaises(bs.BurdenShiftError) as caught:
            bs.weighted_score(bs.normalise(DAIRY), "none")
        self.assertIn("no unweighted option", str(caught.exception))

    def test_normalise_does_not_produce_a_headline_score(self):
        """The disaggregated profile is the primary output, on purpose."""
        result = bs.normalise(DAIRY)
        self.assertNotIn("score", result)
        self.assertNotIn("total", result)


class TestBurdenShift(unittest.TestCase):
    """The load-bearing behaviour."""

    def test_a_carbon_improvement_that_worsens_water_is_flagged(self):
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        self.assertTrue(shift["burden_shifted"])
        self.assertIn("climate_change", shift["improved"])
        self.assertIn("water_scarcity", shift["material_worsening"])

    def test_it_fires_even_when_the_net_movement_is_an_improvement(self):
        """A detector reading only a total would miss exactly this case."""
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        self.assertLess(shift["net_share_change"], 0.0)
        self.assertTrue(shift["burden_shifted"])

    def test_an_improvement_across_the_board_is_not_flagged(self):
        shift = bs.detect_burden_shift(DAIRY, OAT)
        self.assertFalse(shift["burden_shifted"])
        self.assertEqual(shift["material_worsening"], [])

    def test_a_trivial_worsening_stays_below_the_threshold(self):
        nudged = dict(DAIRY)
        nudged["climate_change"] = DAIRY["climate_change"] - 200.0
        nudged["water_scarcity"] = DAIRY["water_scarcity"] + 1.0
        shift = bs.detect_burden_shift(DAIRY, nudged)
        self.assertIn("water_scarcity", shift["worsened"])
        self.assertNotIn("water_scarcity", shift["material_worsening"])
        self.assertFalse(shift["burden_shifted"])

    def test_the_threshold_can_be_tightened(self):
        nudged = dict(DAIRY)
        nudged["climate_change"] = DAIRY["climate_change"] - 200.0
        nudged["water_scarcity"] = DAIRY["water_scarcity"] + 100.0
        loose = bs.detect_burden_shift(DAIRY, nudged, threshold=0.5)
        tight = bs.detect_burden_shift(DAIRY, nudged, threshold=0.001)
        self.assertFalse(loose["burden_shifted"])
        self.assertTrue(tight["burden_shifted"])

    def test_worsening_in_an_unnormalisable_category_is_reported_separately(self):
        """No weighted total will ever reflect it, so it is named on its own."""
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        self.assertIn("ecotoxicity", shift["unnormalisable_worsening"])

    def test_no_change_produces_no_shift(self):
        shift = bs.detect_burden_shift(DAIRY, DAIRY)
        self.assertFalse(shift["burden_shifted"])
        self.assertEqual(shift["improved"], [])
        self.assertEqual(shift["worsened"], [])

    def test_the_direction_of_each_category_is_preserved(self):
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        water = next(
            row for row in shift["categories"]
            if row["category"] == "water_scarcity"
        )
        self.assertGreater(water["amount_change"], 0)
        self.assertGreater(water["relative_change"], 3.0)


class TestTradeOffs(unittest.TestCase):

    def test_ratios_are_expressed_in_boundary_shares(self):
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        ratios = bs.trade_off_ratios(shift)
        self.assertTrue(ratios)
        top = ratios[0]
        self.assertAlmostEqual(
            top["ratio"], top["share_lost"] / top["share_gained"], places=3
        )

    def test_a_uniform_improvement_produces_no_trade_offs(self):
        shift = bs.detect_burden_shift(DAIRY, OAT)
        self.assertEqual(bs.trade_off_ratios(shift), [])

    def test_the_steepest_exchange_comes_first(self):
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        ratios = bs.trade_off_ratios(shift)
        values = [row["ratio"] for row in ratios]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_the_raw_unit_ratio_is_reported_alongside(self):
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        self.assertIsNotNone(bs.trade_off_ratios(shift)[0]["unit_ratio"])


class TestPareto(unittest.TestCase):

    def test_a_dominated_option_is_identified(self):
        result = bs.pareto_front([
            {"name": "Dairy", "profile": DAIRY},
            {"name": "Oat", "profile": OAT},
        ])
        self.assertEqual(result["front"], ["Oat"])
        self.assertEqual(result["dominated"][0]["name"], "Dairy")

    def test_a_dominated_option_needs_no_value_judgement(self):
        result = bs.pareto_front([
            {"name": "Dairy", "profile": DAIRY},
            {"name": "Oat", "profile": OAT},
        ])
        self.assertFalse(result["needs_value_judgement"])
        self.assertIn("No weighting is required", result["note"])

    def test_options_that_trade_off_both_survive(self):
        result = bs.pareto_front([
            {"name": "Dairy", "profile": DAIRY},
            {"name": "Almond", "profile": ALMOND},
            {"name": "Oat", "profile": OAT},
        ])
        self.assertIn("Almond", result["front"])
        self.assertIn("Oat", result["front"])
        self.assertTrue(result["needs_value_judgement"])

    def test_domination_is_not_reflexive(self):
        self.assertFalse(bs.dominates(DAIRY, DAIRY))

    def test_domination_is_antisymmetric(self):
        self.assertTrue(bs.dominates(OAT, DAIRY))
        self.assertFalse(bs.dominates(DAIRY, OAT))

    def test_a_single_option_is_refused(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.pareto_front([{"name": "Only", "profile": DAIRY}])

    def test_an_option_without_a_profile_is_refused(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.pareto_front([{"name": "a"}, {"name": "b", "profile": OAT}])


class TestRobustness(unittest.TestCase):

    def test_the_winner_flipping_is_reported_as_a_value_judgement(self):
        result = bs.weighting_robustness([
            {"name": "Almond", "profile": ALMOND},
            {"name": "Oat", "profile": OAT},
        ])
        self.assertFalse(result["robust"])
        self.assertIn("value judgement wearing a number", result["note"])

    def test_carbon_only_picks_a_different_winner(self):
        """Which is what the rest of the app has been doing without saying so."""
        result = bs.weighting_robustness([
            {"name": "Almond", "profile": ALMOND},
            {"name": "Oat", "profile": OAT},
        ])
        self.assertEqual(result["winners"]["carbon_only"], "Almond")
        self.assertEqual(result["winners"]["equal"], "Oat")

    def test_a_dominant_option_wins_under_every_weighting(self):
        result = bs.weighting_robustness([
            {"name": "Dairy", "profile": DAIRY},
            {"name": "Oat", "profile": OAT},
        ])
        self.assertTrue(result["robust"])
        self.assertEqual(result["distinct_winners"], ["Oat"])

    def test_every_weighting_set_is_evaluated(self):
        result = bs.weighting_robustness([
            {"name": "Almond", "profile": ALMOND},
            {"name": "Oat", "profile": OAT},
        ])
        self.assertEqual(len(result["by_weighting"]), len(bs.list_weightings()))

    def test_a_single_option_is_refused(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.weighting_robustness([{"name": "Only", "profile": DAIRY}])


class TestInsights(unittest.TestCase):

    def test_the_worst_category_is_named(self):
        text = " ".join(bs.get_burden_insights(bs.normalise(DAIRY)))
        self.assertIn("furthest beyond its reference", text)

    def test_burden_shifting_is_described_as_such(self):
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        text = " ".join(
            bs.get_burden_insights(bs.normalise(ALMOND), shift)
        )
        self.assertIn("That is burden shifting", text)
        self.assertIn("whatever the weighted total does", text)

    def test_the_steepest_trade_off_is_quantified(self):
        shift = bs.detect_burden_shift(DAIRY, ALMOND)
        text = " ".join(
            bs.get_burden_insights(bs.normalise(ALMOND), shift)
        )
        self.assertIn("steepest exchange", text)

    def test_a_clean_improvement_is_not_overstated(self):
        shift = bs.detect_burden_shift(DAIRY, OAT)
        text = " ".join(bs.get_burden_insights(bs.normalise(OAT), shift))
        self.assertIn("weaker statement than it sounds", text)

    def test_the_robustness_verdict_is_carried_through(self):
        robustness = bs.weighting_robustness([
            {"name": "Almond", "profile": ALMOND},
            {"name": "Oat", "profile": OAT},
        ])
        text = " ".join(
            bs.get_burden_insights(bs.normalise(OAT), None, robustness)
        )
        self.assertIn("value judgement wearing a number", text)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = bs.DB_NAME
        bs.DB_NAME = self.path
        self.normalised = bs.normalise(ALMOND, "boundary")
        self.shift = bs.detect_burden_shift(DAIRY, ALMOND)

    def tearDown(self):
        bs.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_assessment_comes_back(self):
        saved_id = bs.save_assessment(
            "user-1", "Dairy to almond", self.normalised, self.shift
        )
        self.assertIsInstance(saved_id, int)
        rows = bs.get_assessments("user-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Dairy to almond")

    def test_the_shift_flag_survives_a_round_trip(self):
        bs.save_assessment("user-1", "Round trip", self.normalised, self.shift)
        row = bs.get_assessments("user-1")[0]
        self.assertTrue(row["burden_shifted"])

    def test_an_assessment_without_a_shift_saves_too(self):
        bs.save_assessment("user-1", "Profile only", self.normalised)
        row = bs.get_assessments("user-1")[0]
        self.assertFalse(row["burden_shifted"])

    def test_users_do_not_see_each_others_assessments(self):
        bs.save_assessment("user-1", "Mine", self.normalised)
        self.assertEqual(bs.get_assessments("user-2"), [])

    def test_an_assessment_needs_a_user_and_a_name(self):
        with self.assertRaises(bs.BurdenShiftError):
            bs.save_assessment("", "Named", self.normalised)
        with self.assertRaises(bs.BurdenShiftError):
            bs.save_assessment("user-1", "  ", self.normalised)

    def test_deletion_is_scoped_to_the_owner(self):
        saved_id = bs.save_assessment("user-1", "Mine", self.normalised)
        self.assertFalse(bs.delete_assessment("user-2", saved_id))
        self.assertTrue(bs.delete_assessment("user-1", saved_id))
        self.assertEqual(bs.get_assessments("user-1"), [])

    def test_reading_without_a_user_returns_nothing_rather_than_raising(self):
        self.assertEqual(bs.get_assessments(None), [])
        self.assertFalse(bs.delete_assessment(None, 1))


if __name__ == "__main__":
    unittest.main()
