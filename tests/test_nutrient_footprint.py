"""Tests for the reactive nitrogen and phosphorus engine.

The claims under test are the ones the module exists to make, and they are the
ones most likely to be quietly broken by a later edit to the factor tables:

*   a nitrogen partition closes, so no pathway is silently lost or invented;
*   denitrified nitrogen is excluded from the reactive total, because it is
    genuinely harmless and including it would overstate the damage by a third;
*   the protein-normalised ranking disagrees with the carbon ranking;
*   the two eutrophication indicators are never combined into one score;
*   the nitrous oxide figure is always flagged as overlapping the app's carbon
    total rather than adding to it.

The last of those is the one worth guarding hardest. A future contributor
summing this module's CO2e onto the app's footprint would double-count, and the
only thing standing between them and that mistake is the flag being present.
"""

import os
import tempfile
import unittest

import src.environment.nutrient_footprint as nf


class TestFoodFactorTable(unittest.TestCase):
    """The table everything downstream depends on."""

    def test_every_food_carries_a_category_a_protein_and_an_explanation(self):
        for key in nf.list_foods():
            with self.subTest(food=key):
                food = nf.get_food(key)
                self.assertIn("category", food)
                self.assertGreaterEqual(food["protein_g"], 0.0)
                self.assertGreater(len(food["note"]), 40)

    def test_no_food_applies_negative_nutrient(self):
        for key in nf.list_foods():
            with self.subTest(food=key):
                self.assertGreaterEqual(nf.get_food(key)["n_applied"], 0.0)
                self.assertGreaterEqual(nf.get_food(key)["p_applied"], 0.0)

    def test_categories_are_all_represented_by_at_least_one_food(self):
        for category in nf.list_categories():
            self.assertTrue(nf.list_foods(category))

    def test_unknown_food_refuses_to_average(self):
        with self.assertRaises(nf.NutrientError) as context:
            nf.get_food("unobtainium_steak")
        self.assertIn("order of magnitude", str(context.exception))

    def test_legumes_apply_far_less_nitrogen_than_any_meat(self):
        """Nitrogen fixation is the whole point and should be unmissable."""
        lentils = nf.get_food("lentils")["n_applied"]
        for meat in nf.list_foods("meat"):
            with self.subTest(meat=meat):
                self.assertGreater(nf.get_food(meat)["n_applied"], lentils * 5)

    def test_feedlot_beef_applies_more_nitrogen_than_pasture_beef(self):
        """Grain finishing moves the burden onto fertilised cereal."""
        self.assertGreater(
            nf.get_food("beef_feedlot")["n_applied"],
            nf.get_food("beef_pasture")["n_applied"],
        )

    def test_cheese_costs_roughly_ten_times_its_milk(self):
        ratio = (
            nf.get_food("cheese")["n_applied"]
            / nf.get_food("milk")["n_applied"]
        )
        self.assertGreater(ratio, 6.0)
        self.assertLess(ratio, 12.0)

    def test_wild_fish_applies_no_nutrient_at_all(self):
        self.assertEqual(nf.get_food("wild_fish")["n_applied"], 0.0)


class TestNitrogenPartition(unittest.TestCase):
    """A partition that does not close has lost track of something."""

    def test_pathways_and_uptake_sum_to_the_applied_mass(self):
        for method in nf.list_methods():
            with self.subTest(method=method):
                split = nf.partition_nitrogen(100.0, method)
                total = (
                    split["volatilisation"] + split["leaching"] + split["n2o"]
                    + split["denitrification"] + split["uptake"]
                )
                self.assertAlmostEqual(total, 100.0, places=6)

    def test_reactive_loss_excludes_denitrification(self):
        split = nf.partition_nitrogen(100.0, "broadcast_surface")
        self.assertAlmostEqual(
            split["reactive_lost"],
            split["lost_total"] - split["denitrification"],
            places=9,
        )
        self.assertGreater(split["denitrification"], 0.0)

    def test_surface_broadcast_volatilises_far_more_than_incorporation(self):
        """The finding the table exists to make visible: method beats product."""
        surface = nf.partition_nitrogen(100.0, "broadcast_surface")
        incorporated = nf.partition_nitrogen(100.0, "broadcast_incorporated")
        self.assertGreater(
            surface["volatilisation"], incorporated["volatilisation"] * 3
        )

    def test_surface_slurry_is_the_worst_volatiliser(self):
        losses = {
            method: nf.partition_nitrogen(100.0, method)["volatilisation"]
            for method in nf.list_methods()
        }
        self.assertEqual(max(losses, key=losses.get), "surface_slurry")

    def test_slow_release_compost_retains_more_than_any_soluble_product(self):
        """Nitrogen bound in organic matter is never all available at once, so
        there is never much of it sitting in solution waiting to leach."""
        uptakes = {
            method: nf.partition_nitrogen(100.0, method)["uptake"]
            for method in nf.list_methods()
        }
        self.assertEqual(max(uptakes, key=uptakes.get), "compost_topdress")

    def test_fertigation_retains_the_most_of_the_soluble_methods(self):
        soluble = {
            method: nf.partition_nitrogen(100.0, method)["uptake"]
            for method in nf.list_methods()
            if method != "compost_topdress"
        }
        self.assertEqual(max(soluble, key=soluble.get), "fertigation")

    def test_zero_applied_gives_zero_everywhere(self):
        split = nf.partition_nitrogen(0.0, "split_dose")
        self.assertEqual(split["reactive_lost"], 0.0)
        self.assertEqual(split["uptake"], 0.0)

    def test_negative_application_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.partition_nitrogen(-1.0, "split_dose")

    def test_unknown_method_is_refused_rather_than_defaulted(self):
        with self.assertRaises(nf.NutrientError) as context:
            nf.partition_nitrogen(10.0, "sprinkle_hopefully")
        self.assertIn("more than product choice", str(context.exception))

    def test_partition_scales_linearly(self):
        one = nf.partition_nitrogen(1.0, "split_dose")["reactive_lost"]
        ten = nf.partition_nitrogen(10.0, "split_dose")["reactive_lost"]
        self.assertAlmostEqual(ten, one * 10.0, places=9)


class TestPhosphorusPartition(unittest.TestCase):
    """Phosphorus moves when soil moves, so slope is the parameter."""

    def test_runoff_and_retention_sum_to_the_applied_mass(self):
        for slope in nf.P_LOSS_BY_SLOPE:
            with self.subTest(slope=slope):
                split = nf.partition_phosphorus(50.0, slope)
                self.assertAlmostEqual(
                    split["runoff"] + split["retained"], 50.0, places=9
                )

    def test_steep_bare_ground_loses_more_than_flat_stable_ground(self):
        steep = nf.partition_phosphorus(10.0, "steep_bare")["runoff"]
        flat = nf.partition_phosphorus(10.0, "flat_stable")["runoff"]
        self.assertGreater(steep, flat * 3)

    def test_contained_systems_lose_least(self):
        losses = {
            slope: nf.partition_phosphorus(10.0, slope)["runoff"]
            for slope in nf.P_LOSS_BY_SLOPE
        }
        self.assertEqual(min(losses, key=losses.get), "hydroponic")

    def test_unknown_slope_class_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.partition_phosphorus(1.0, "vertical")

    def test_negative_phosphorus_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.partition_phosphorus(-0.5, "gentle")


class TestClimateOverlap(unittest.TestCase):
    """The double-counting guard."""

    def test_the_overlap_flag_is_always_present(self):
        overlap = nf.n2o_climate_overlap(1.0)
        self.assertTrue(overlap["overlaps_carbon_total"])

    def test_the_warning_says_not_to_add_it_on(self):
        self.assertIn("not so it can be added", nf.n2o_climate_overlap(1.0)["warning"])

    def test_mass_conversion_uses_the_molecular_ratio(self):
        """One kg of N as N2O is 44/28 kg of N2O, not one kg."""
        overlap = nf.n2o_climate_overlap(1.0)
        self.assertAlmostEqual(overlap["kg_n2o"], 44.0 / 28.0, places=9)

    def test_co2e_uses_the_ar6_gwp(self):
        overlap = nf.n2o_climate_overlap(1.0)
        self.assertAlmostEqual(
            overlap["kg_co2e"], 44.0 / 28.0 * 273.0, places=6
        )

    def test_a_kilogram_of_nitrogen_as_n2o_is_worth_hundreds_of_kg_co2e(self):
        """If this ever drops to single digits, a GWP has gone missing."""
        self.assertGreater(nf.n2o_climate_overlap(1.0)["kg_co2e"], 400.0)

    def test_negative_input_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.n2o_climate_overlap(-0.1)


class TestEutrophication(unittest.TestCase):
    """Two receiving systems, two limiting nutrients, no combined score."""

    def test_freshwater_responds_to_phosphorus_only(self):
        with_n = nf.eutrophication_potential(100.0, 0.0)
        self.assertEqual(with_n["freshwater_po4_eq"], 0.0)
        self.assertGreater(with_n["marine_n_eq"], 0.0)

    def test_marine_responds_to_nitrogen_only(self):
        with_p = nf.eutrophication_potential(0.0, 100.0)
        self.assertEqual(with_p["marine_n_eq"], 0.0)
        self.assertGreater(with_p["freshwater_po4_eq"], 0.0)

    def test_there_is_no_combined_eutrophication_score(self):
        """A single score would hide which system is being loaded."""
        result = nf.eutrophication_potential(5.0, 5.0)
        for key in result:
            self.assertNotIn("total", key)
            self.assertNotIn("combined", key)

    def test_phosphate_conversion_uses_the_molecular_ratio(self):
        result = nf.eutrophication_potential(0.0, 1.0, delivery_p=1.0)
        self.assertAlmostEqual(
            result["freshwater_po4_eq"], 95.0 / 31.0, places=9
        )

    def test_delivery_ratios_reduce_the_load_reaching_water(self):
        full = nf.eutrophication_potential(10.0, 10.0, 1.0, 1.0)
        partial = nf.eutrophication_potential(10.0, 10.0, 0.5, 0.5)
        self.assertAlmostEqual(
            partial["marine_n_eq"], full["marine_n_eq"] / 2, places=9
        )

    def test_a_delivery_ratio_outside_zero_to_one_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.eutrophication_potential(1.0, 1.0, delivery_n=1.4)

    def test_the_limiting_nutrients_are_stated_in_the_result(self):
        result = nf.eutrophication_potential(1.0, 1.0)
        self.assertEqual(result["limiting_nutrients"]["freshwater"], "phosphorus")
        self.assertEqual(result["limiting_nutrients"]["marine"], "nitrogen")


class TestProteinNormalisedRanking(unittest.TestCase):
    """The ranking that disagrees with the carbon ranking."""

    def test_soy_beats_every_animal_protein(self):
        ranking = nf.compare_by_protein()
        keys = [row["key"] for row in ranking]
        animal = [
            k for k in keys
            if nf.get_food(k)["category"] in ("meat", "animal_product")
        ]
        self.assertLess(keys.index("soy"), min(keys.index(k) for k in animal))

    def test_pork_loses_to_pasture_beef_on_protein_normalised_nitrogen(self):
        """The specific inversion the module was written to expose."""
        by_key = {row["key"]: row for row in nf.compare_by_protein()}
        self.assertGreater(
            by_key["pork"]["n_per_100g_protein"],
            by_key["beef_pasture"]["n_per_100g_protein"],
        )

    def test_feedlot_beef_is_the_worst_protein_source_in_the_table(self):
        ranking = nf.compare_by_protein()
        self.assertEqual(ranking[-1]["key"], "beef_feedlot")

    def test_low_protein_produce_is_excluded_rather_than_ranked_badly(self):
        """A lettuce is not a failed protein source."""
        keys = [row["key"] for row in nf.compare_by_protein()]
        self.assertNotIn("vegetables_field", keys)
        self.assertNotIn("fruit", keys)

    def test_the_ranking_is_sorted_ascending(self):
        values = [row["n_per_100g_protein"] for row in nf.compare_by_protein()]
        self.assertEqual(values, sorted(values))


class TestFoodFootprint(unittest.TestCase):
    """The basket calculation."""

    BASKET = {"beef_feedlot": 5.0, "chicken": 8.0, "lentils": 4.0, "milk": 30.0}

    def test_totals_match_the_sum_of_the_items(self):
        result = nf.food_footprint(self.BASKET)
        summed = sum(
            nf.get_food(k)["n_applied"] * v for k, v in self.BASKET.items()
        )
        self.assertAlmostEqual(result["n_applied_kg"], summed, places=9)

    def test_items_are_returned_worst_first(self):
        rows = nf.food_footprint(self.BASKET)["items"]
        values = [row["n_applied"] for row in rows]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_an_empty_basket_is_refused_rather_than_scored_zero(self):
        with self.assertRaises(nf.NutrientError):
            nf.food_footprint({})

    def test_a_negative_quantity_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.food_footprint({"chicken": -2.0})

    def test_the_climate_overlap_is_carried_through_to_the_result(self):
        result = nf.food_footprint(self.BASKET)
        self.assertTrue(result["climate_overlap"]["overlaps_carbon_total"])

    def test_changing_method_changes_the_loss_but_not_the_application(self):
        surface = nf.food_footprint(self.BASKET, method="broadcast_surface")
        drip = nf.food_footprint(self.BASKET, method="fertigation")
        self.assertAlmostEqual(
            surface["n_applied_kg"], drip["n_applied_kg"], places=9
        )
        self.assertGreater(
            surface["reactive_n_lost_kg"], drip["reactive_n_lost_kg"]
        )


class TestFertiliserApplication(unittest.TestCase):
    """The garden bed, where a household has direct control."""

    def test_bag_labels_are_read_as_oxide_and_stored_as_element(self):
        """A 7-7-7 bag is 3.1% phosphorus, not 7%."""
        npk = nf.get_fertiliser("npk_growmore")
        self.assertAlmostEqual(npk["p_fraction"], 0.070 * 0.4364, places=6)
        self.assertLess(npk["p_fraction"], 0.070)

    def test_application_rate_is_reported_per_hectare(self):
        result = nf.fertiliser_application("urea", 1.0, 10.0)
        self.assertAlmostEqual(result["n_rate_kg_per_ha"], 0.46 * 1000.0, places=6)

    def test_over_application_is_only_reported_when_a_requirement_is_given(self):
        without = nf.fertiliser_application("urea", 1.0, 20.0)
        self.assertNotIn("over_application_ratio", without)
        with_req = nf.fertiliser_application(
            "urea", 1.0, 20.0, crop_requirement_kg_n=0.1
        )
        self.assertIn("over_application_ratio", with_req)

    def test_heavy_over_application_gets_the_blunt_verdict(self):
        result = nf.fertiliser_application(
            "urea", 1.0, 20.0, crop_requirement_kg_n=0.1
        )
        self.assertGreater(result["over_application_ratio"], 3.0)
        self.assertIn("Halving the dose", result["over_application_verdict"])

    def test_a_matched_dose_is_not_scolded(self):
        result = nf.fertiliser_application(
            "urea", 1.0, 20.0, crop_requirement_kg_n=0.46
        )
        self.assertIn("Matched", result["over_application_verdict"])

    def test_compost_defaults_to_its_own_slow_release_method(self):
        result = nf.fertiliser_application("garden_compost", 20.0, 10.0)
        self.assertEqual(result["method"], "compost_topdress")

    def test_zero_area_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.fertiliser_application("urea", 1.0, 0.0)

    def test_zero_quantity_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.fertiliser_application("urea", 0.0, 10.0)

    def test_unknown_product_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.fertiliser_application("magic_dust", 1.0, 10.0)

    def test_organic_slurry_spread_on_the_surface_beats_urea_for_ammonia(self):
        """Organic does not mean well retained."""
        slurry = nf.partition_nitrogen(1.0, "surface_slurry")["volatilisation"]
        urea = nf.partition_nitrogen(1.0, "broadcast_surface")["volatilisation"]
        self.assertGreater(slurry, urea)


class TestMethodComparison(unittest.TestCase):

    def test_comparison_covers_every_known_method(self):
        rows = nf.compare_methods(10.0)
        self.assertEqual(len(rows), len(nf.APPLICATION_METHODS))

    def test_comparison_is_ranked_best_first(self):
        values = [row["reactive_lost"] for row in nf.compare_methods(10.0)]
        self.assertEqual(values, sorted(values))

    def test_the_spread_between_best_and_worst_method_is_large(self):
        """If method did not matter, the module would have little to say."""
        rows = nf.compare_methods(100.0)
        self.assertGreater(rows[-1]["reactive_lost"] / rows[0]["reactive_lost"], 2.0)


class TestPlanetaryBoundary(unittest.TestCase):

    def test_the_world_is_already_over_both_boundaries(self):
        share = nf.planetary_boundary_share(0.0, 0.0)
        self.assertGreater(share["world_n_share"], 1.0)
        self.assertGreater(share["world_p_share"], 1.0)

    def test_the_transgression_is_stated_in_words_not_only_in_a_ratio(self):
        share = nf.planetary_boundary_share(1.0, 1.0)
        self.assertIn("nowhere near", share["context"])

    def test_share_scales_with_the_load(self):
        one = nf.planetary_boundary_share(5.0, 0.5)
        two = nf.planetary_boundary_share(10.0, 1.0)
        self.assertAlmostEqual(
            two["n_share_of_boundary"], one["n_share_of_boundary"] * 2, places=9
        )

    def test_negative_totals_are_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.planetary_boundary_share(-1.0, 0.0)


class TestHouseholdBalance(unittest.TestCase):

    ITEMS = {"chicken": 20.0, "wheat": 60.0, "vegetables_field": 100.0}

    def test_compost_returned_to_soil_reduces_the_net_import(self):
        without = nf.household_nutrient_balance(self.ITEMS, compost_kg=0.0)
        with_compost = nf.household_nutrient_balance(self.ITEMS, compost_kg=200.0)
        self.assertLess(with_compost["net_n_kg"], without["net_n_kg"])

    def test_compost_sent_away_is_not_counted_as_recovery(self):
        away = nf.household_nutrient_balance(
            self.ITEMS, compost_kg=200.0, compost_returned_to_soil=False
        )
        self.assertEqual(away["recovered_n_kg"], 0.0)

    def test_recovery_is_small_against_the_upstream_virtual_nutrient(self):
        """The lever is the diet, and the module says so rather than implying
        that a compost bin closes the loop."""
        balance = nf.household_nutrient_balance(self.ITEMS, compost_kg=200.0)
        self.assertLess(balance["recovery_fraction_n"], 0.5)
        self.assertIn("lever is the diet", balance["note"])

    def test_negative_compost_is_refused(self):
        with self.assertRaises(nf.NutrientError):
            nf.household_nutrient_balance(self.ITEMS, compost_kg=-1.0)


class TestInsights(unittest.TestCase):

    def test_insights_name_the_dominant_pathway(self):
        result = nf.food_footprint(
            {"beef_feedlot": 10.0}, method="surface_slurry"
        )
        insights = nf.get_nutrient_insights(result)
        self.assertTrue(any("ammonia to air" in line for line in insights))

    def test_insights_always_repeat_the_double_counting_warning(self):
        result = nf.food_footprint({"pork": 10.0})
        insights = nf.get_nutrient_insights(result)
        self.assertTrue(any("do not add it on" in line for line in insights))

    def test_a_single_item_basket_produces_no_concentration_insight(self):
        result = nf.food_footprint({"pork": 10.0})
        insights = nf.get_nutrient_insights(result)
        self.assertFalse(any("accounts for" in line for line in insights))

    def test_a_meat_heavy_basket_is_compared_against_soy(self):
        result = nf.food_footprint({"beef_feedlot": 20.0, "cheese": 5.0})
        insights = nf.get_nutrient_insights(result)
        self.assertTrue(any("soybeans do" in line for line in insights))

    def test_a_legume_basket_is_not_lectured_about_protein_source(self):
        result = nf.food_footprint({"lentils": 20.0, "soy": 10.0})
        insights = nf.get_nutrient_insights(result)
        self.assertFalse(any("soybeans do" in line for line in insights))


class TestPersistence(unittest.TestCase):
    """Scenario storage, against a throwaway src.core.database."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self._original = nf.DB_NAME
        nf.DB_NAME = self.path

    def tearDown(self):
        nf.DB_NAME = self._original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_scenario_comes_back(self):
        result = nf.food_footprint({"chicken": 10.0, "lentils": 5.0})
        scenario_id = nf.save_scenario("user-1", "Weekly shop", result)
        self.assertGreater(scenario_id, 0)

        scenarios = nf.get_scenarios("user-1")
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0]["name"], "Weekly shop")
        self.assertAlmostEqual(
            scenarios[0]["n_applied_kg"], result["n_applied_kg"], places=6
        )

    def test_scenarios_are_scoped_to_their_user(self):
        result = nf.food_footprint({"chicken": 1.0})
        nf.save_scenario("user-1", "Mine", result)
        self.assertEqual(nf.get_scenarios("user-2"), [])

    def test_newest_scenario_comes_back_first(self):
        result = nf.food_footprint({"chicken": 1.0})
        nf.save_scenario("user-1", "First", result)
        nf.save_scenario("user-1", "Second", result)
        self.assertEqual(nf.get_scenarios("user-1")[0]["name"], "Second")

    def test_deleting_someone_elses_scenario_does_nothing(self):
        result = nf.food_footprint({"chicken": 1.0})
        scenario_id = nf.save_scenario("user-1", "Mine", result)
        self.assertFalse(nf.delete_scenario("user-2", scenario_id))
        self.assertEqual(len(nf.get_scenarios("user-1")), 1)

    def test_deleting_your_own_scenario_removes_it(self):
        result = nf.food_footprint({"chicken": 1.0})
        scenario_id = nf.save_scenario("user-1", "Mine", result)
        self.assertTrue(nf.delete_scenario("user-1", scenario_id))
        self.assertEqual(nf.get_scenarios("user-1"), [])

    def test_an_unnamed_scenario_is_refused(self):
        result = nf.food_footprint({"chicken": 1.0})
        with self.assertRaises(nf.NutrientError):
            nf.save_scenario("user-1", "   ", result)

    def test_an_anonymous_scenario_is_refused(self):
        result = nf.food_footprint({"chicken": 1.0})
        with self.assertRaises(nf.NutrientError):
            nf.save_scenario("", "Anonymous", result)

    def test_reading_scenarios_without_a_user_returns_empty(self):
        self.assertEqual(nf.get_scenarios(""), [])


if __name__ == "__main__":
    unittest.main()
