"""Tests for the toxicity characterisation engine.

Toxicity is the impact category where mass tells you nothing, and every other
module in this app is mass-weighted. The tests here guard the properties that
make an impact-based toxicity indicator usable rather than merely present:

*   the emission compartment is required and has no default, because the same
    kilogram differs by thousands of times depending on where it went;
*   fate, exposure and effect stay separable and their product reproduces the
    characterisation factor, so a result can be argued with;
*   cancer and non-cancer are never added, and neither is added to carbon;
*   human toxicity and freshwater ecotoxicity do not stand in for one another -
    copper carries the lowest human hazard in the table and one of the highest
    aquatic ones, and benzene is the reverse;
*   interim factors keep their flag all the way into the comparison output, and
    a winning margin inside their uncertainty is reported as no result at all.

The compartment test is the load-bearing one. A flat toxicity score per
kilogram is not a simplification of this model; it is a different quantity, and
it is the standard way the indicator gets published and then misused.
"""

import os
import tempfile
import unittest

import src.carbon.toxicity_characterisation as tc


class TestSubstanceTable(unittest.TestCase):

    def test_every_substance_covers_every_compartment(self):
        for key in tc.list_substances():
            with self.subTest(substance=key):
                half_lives = tc.get_substance(key)["half_life_days"]
                for compartment in tc.list_compartments():
                    self.assertIn(compartment, half_lives)
                    self.assertGreater(half_lives[compartment], 0)

    def test_every_substance_explains_itself(self):
        for key in tc.list_substances():
            self.assertGreater(len(tc.get_substance(key)["note"]), 40)

    def test_families_partition_the_table(self):
        covered = []
        for family in tc.list_families():
            covered.extend(tc.list_substances(family))
        self.assertCountEqual(covered, tc.list_substances())

    def test_bioavailability_is_a_fraction(self):
        for key in tc.list_substances():
            with self.subTest(substance=key):
                value = tc.get_substance(key)["bioavailability"]
                self.assertGreater(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_effect_factors_are_never_negative(self):
        for key in tc.list_substances():
            effects = tc.effect_factors(key)
            self.assertGreaterEqual(effects["cancer"], 0.0)
            self.assertGreaterEqual(effects["noncancer"], 0.0)

    def test_every_metal_is_flagged_interim(self):
        """Not a defect in the table - metal factors are not settled."""
        for key in tc.list_substances("heavy_metal"):
            self.assertTrue(tc.get_substance(key)["interim"], key)

    def test_some_substances_are_not_interim(self):
        """Otherwise the flag carries no information."""
        self.assertTrue(
            set(tc.list_substances()) - set(tc.list_interim_substances())
        )

    def test_persistent_substances_are_present(self):
        """The mass-invisible case the module exists for."""
        persistent = [
            k for k in tc.list_substances()
            if tc.get_substance(k)["half_life_days"]["agricultural_soil"] > 1000
        ]
        self.assertGreaterEqual(len(persistent), 5)

    def test_unknown_substance_is_rejected_with_a_useful_message(self):
        with self.assertRaises(tc.ToxicityError) as caught:
            tc.get_substance("water")
        self.assertIn("lead", str(caught.exception))


class TestCompartmentIsRequired(unittest.TestCase):
    """The load-bearing rule."""

    def test_a_missing_compartment_is_refused_with_an_explanation(self):
        with self.assertRaises(tc.ToxicityError) as caught:
            tc.get_compartment(None)
        self.assertIn("no defensible default", str(caught.exception))

    def test_an_unknown_compartment_is_rejected(self):
        with self.assertRaises(tc.ToxicityError):
            tc.characterisation_factor("lead", "stratosphere")

    def test_the_same_mass_differs_by_orders_of_magnitude_by_compartment(self):
        sensitivity = tc.compartment_sensitivity("cadmium")
        self.assertGreater(sensitivity["human_spread_ratio"], 100)

    def test_urban_air_exposes_far_more_than_rural_air(self):
        urban = tc.assess_emission("benzene", 1.0, "urban_air")
        rural = tc.assess_emission("benzene", 1.0, "rural_air")
        self.assertGreater(
            urban["cancer_ctuh"], rural["cancer_ctuh"] * 5
        )

    def test_natural_soil_has_almost_no_human_intake_pathway(self):
        comp = tc.get_compartment("natural_soil")
        urban = tc.get_compartment("urban_air")
        self.assertLess(
            comp["intake_rate_per_day"], urban["intake_rate_per_day"] / 100
        )

    def test_agricultural_soil_matters_most_for_a_crop_uptake_metal(self):
        agricultural = tc.assess_emission("cadmium", 1.0, "agricultural_soil")
        urban = tc.assess_emission("cadmium", 1.0, "urban_air")
        self.assertGreater(
            agricultural["noncancer_ctuh"], urban["noncancer_ctuh"]
        )


class TestThreeSteps(unittest.TestCase):

    def test_fate_is_derived_from_the_half_life(self):
        import math
        spec = tc.get_substance("lead")
        expected = spec["half_life_days"]["freshwater"] / math.log(2)
        self.assertAlmostEqual(
            tc.fate_factor("lead", "freshwater"), expected, places=6
        )

    def test_exposure_combines_compartment_and_bioavailability(self):
        expected = (
            tc.get_compartment("urban_air")["intake_rate_per_day"]
            * tc.get_substance("benzene")["bioavailability"]
        )
        self.assertAlmostEqual(
            tc.exposure_factor("benzene", "urban_air"), expected, places=15
        )

    def test_intake_fraction_is_fate_times_exposure(self):
        self.assertAlmostEqual(
            tc.intake_fraction("lead", "urban_air"),
            tc.fate_factor("lead", "urban_air")
            * tc.exposure_factor("lead", "urban_air"),
            places=15,
        )

    def test_the_characterisation_factor_is_the_product_of_the_three(self):
        """The decomposition has to actually compose, or it is decoration."""
        cf = tc.characterisation_factor("cadmium", "agricultural_soil")
        rebuilt = (
            cf["fate_factor_days"]
            * cf["exposure_factor_per_day"]
            * cf["effect_noncancer"]
        )
        self.assertAlmostEqual(
            rebuilt, cf["cf_noncancer_ctuh_per_kg"], places=15
        )

    def test_the_three_steps_are_all_reported(self):
        cf = tc.characterisation_factor("lead", "urban_air")
        for field in (
            "fate_factor_days", "exposure_factor_per_day",
            "effect_cancer", "effect_noncancer",
        ):
            self.assertIn(field, cf)

    def test_a_persistent_substance_has_a_large_fate_factor(self):
        self.assertGreater(tc.fate_factor("tfa", "freshwater"), 100000)

    def test_a_short_lived_substance_has_a_small_one(self):
        self.assertLess(tc.fate_factor("formaldehyde", "urban_air"), 5)


class TestCharacterisationFactors(unittest.TestCase):

    def test_human_factors_land_in_a_credible_range(self):
        """Order of magnitude against published values, not a fitted match."""
        for substance in tc.list_substances():
            with self.subTest(substance=substance):
                cf = tc.characterisation_factor(substance, "urban_air")
                total = (
                    cf["cf_cancer_ctuh_per_kg"] + cf["cf_noncancer_ctuh_per_kg"]
                )
                self.assertGreater(total, 1e-10)
                self.assertLess(total, 1e-1)

    def test_ecotoxicity_factors_land_in_a_credible_range(self):
        for substance in tc.list_substances():
            with self.subTest(substance=substance):
                eco = tc.ecotoxicity_factor(substance, "freshwater")
                self.assertGreater(eco["cf_ctue_per_kg"], 1e-2)
                self.assertLess(eco["cf_ctue_per_kg"], 1e8)

    def test_the_table_spans_many_orders_of_magnitude(self):
        """Which is exactly why it is not folded into a composite score."""
        values = [
            tc.characterisation_factor(s, "urban_air")["cf_noncancer_ctuh_per_kg"]
            for s in tc.list_substances()
        ]
        positive = [v for v in values if v > 0]
        self.assertGreater(max(positive) / min(positive), 1e4)

    def test_a_marine_emission_has_no_freshwater_ecotoxicity(self):
        eco = tc.ecotoxicity_factor("copper_ion", "seawater")
        self.assertEqual(eco["cf_ctue_per_kg"], 0.0)

    def test_that_zero_is_labelled_a_boundary_not_an_absence_of_harm(self):
        eco = tc.ecotoxicity_factor("copper_ion", "seawater")
        self.assertIn("rather than an absence of harm", eco["boundary_note"])


class TestIndicatorsAreNotInterchangeable(unittest.TestCase):

    def test_copper_is_the_lowest_human_hazard_and_the_highest_aquatic_one(self):
        """The effect factors, where the divergence actually lives.

        Copper's characterisation factor for humans is not small, because
        metals never degrade and the fate step carries them. Its *hazard* is,
        and that is what a substitution decision turns on.
        """
        copper = tc.effect_factors("copper_ion")
        self.assertEqual(copper["cancer"], 0.0)
        non_zero = [
            tc.effect_factors(k)["noncancer"] for k in tc.list_substances()
            if tc.effect_factors(k)["noncancer"] > 0
        ]
        self.assertLess(copper["noncancer"], sorted(non_zero)[len(non_zero) // 2])
        eco = [
            tc.get_substance(k)["eco_effect_paf_m3_per_kg"]
            for k in tc.list_substances()
        ]
        self.assertGreater(
            tc.get_substance("copper_ion")["eco_effect_paf_m3_per_kg"],
            sorted(eco)[int(len(eco) * 0.8)],
        )

    def test_benzene_is_the_reverse_of_copper(self):
        benzene = tc.effect_factors("benzene")
        copper = tc.effect_factors("copper_ion")
        self.assertGreater(benzene["cancer"], copper["cancer"])
        self.assertGreater(
            tc.get_substance("copper_ion")["eco_effect_paf_m3_per_kg"],
            tc.get_substance("benzene")["eco_effect_paf_m3_per_kg"] * 100,
        )

    def test_arsenic_is_more_carcinogenic_than_it_is_otherwise_toxic(self):
        effects = tc.effect_factors("arsenic")
        self.assertGreater(effects["cancer"], effects["noncancer"])

    def test_lead_is_the_reverse_of_arsenic(self):
        effects = tc.effect_factors("lead")
        self.assertGreater(effects["noncancer"], effects["cancer"])

    def test_the_result_states_that_the_indicators_are_not_summed(self):
        result = tc.assess_emission("lead", 1.0, "urban_air")
        self.assertIn("not summed with carbon", result["aggregation_note"])


class TestInventory(unittest.TestCase):

    def _inventory(self):
        return tc.assess_inventory(
            {"mercury": 0.05, "zinc_ion": 5.0, "glyphosate": 20.0},
            "agricultural_soil",
        )

    def test_totals_are_per_indicator_only(self):
        inventory = self._inventory()
        self.assertIn("cancer_ctuh", inventory["totals"])
        self.assertIn("ecotoxicity_ctue", inventory["totals"])
        self.assertNotIn("total", inventory["totals"])

    def test_there_is_no_grand_total_and_the_module_says_why(self):
        inventory = self._inventory()
        self.assertIn("not commensurable", inventory["no_grand_total_note"])

    def test_the_interim_share_is_tracked_per_indicator(self):
        inventory = self._inventory()
        for indicator in ("cancer_ctuh", "noncancer_ctuh", "ecotoxicity_ctue"):
            share = inventory["interim_share"][indicator]
            self.assertGreaterEqual(share, 0.0)
            self.assertLessEqual(share, 1.0)

    def test_a_metal_heavy_inventory_is_mostly_interim(self):
        inventory = self._inventory()
        self.assertGreater(inventory["interim_share"]["noncancer_ctuh"], 0.5)

    def test_impact_concentrates_in_a_tiny_share_of_the_mass(self):
        """The whole argument for an impact indicator over a mass one."""
        inventory = self._inventory()
        focus = tc.dominant_contributors(inventory, "noncancer_ctuh", top_n=1)
        self.assertGreater(focus["top_share_of_impact"], 0.5)
        self.assertLess(focus["top_share_of_mass"], 0.05)

    def test_the_dominant_contributor_differs_between_indicators(self):
        inventory = self._inventory()
        human = tc.dominant_contributors(inventory, "noncancer_ctuh", 1)
        eco = tc.dominant_contributors(inventory, "ecotoxicity_ctue", 1)
        self.assertNotEqual(
            human["top"][0]["substance"], eco["top"][0]["substance"]
        )

    def test_an_unknown_indicator_is_rejected(self):
        with self.assertRaises(tc.ToxicityError):
            tc.dominant_contributors(self._inventory(), "carbon")

    def test_an_empty_inventory_is_refused(self):
        with self.assertRaises(tc.ToxicityError):
            tc.assess_inventory({}, "urban_air")

    def test_negative_mass_is_rejected(self):
        with self.assertRaises(tc.ToxicityError):
            tc.assess_emission("lead", -1.0, "urban_air")

    def test_results_scale_with_mass(self):
        one = tc.assess_emission("lead", 1.0, "urban_air")
        ten = tc.assess_emission("lead", 10.0, "urban_air")
        self.assertAlmostEqual(
            ten["noncancer_ctuh"], one["noncancer_ctuh"] * 10, places=12
        )


class TestSubstitutionComparison(unittest.TestCase):

    def test_a_substitution_that_helps_on_both_is_reported_as_such(self):
        comparison = tc.compare_options([
            {
                "name": "Benzene-based",
                "emissions": {"benzene": 1.0},
                "compartment": "urban_air",
                "carbon_kg": 3.0,
            },
            {
                "name": "Toluene-based",
                "emissions": {"toluene": 1.0},
                "compartment": "urban_air",
                "carbon_kg": 3.0,
            },
        ])
        self.assertEqual(comparison["best_human_toxicity"], "Toluene-based")

    def test_disagreement_between_carbon_and_toxicity_is_stated(self):
        comparison = tc.compare_options([
            {
                "name": "Low carbon, toxic",
                "emissions": {"chromium_vi": 0.5},
                "compartment": "urban_air",
                "carbon_kg": 1.0,
            },
            {
                "name": "High carbon, clean",
                "emissions": {"glyphosate": 0.01},
                "compartment": "urban_air",
                "carbon_kg": 40.0,
            },
        ])
        self.assertTrue(comparison["indicators_disagree"])
        self.assertIn("better on carbon", comparison["disagreement"])

    def test_no_composite_score_is_ever_produced(self):
        comparison = tc.compare_options([
            {
                "name": "A", "emissions": {"benzene": 1.0},
                "compartment": "urban_air", "carbon_kg": 1.0,
            },
            {
                "name": "B", "emissions": {"toluene": 1.0},
                "compartment": "urban_air", "carbon_kg": 2.0,
            },
        ])
        for option in comparison["options"]:
            self.assertNotIn("score", option)
        self.assertIn("No composite score", comparison["no_composite_note"])

    def test_human_and_ecosystem_winners_can_differ(self):
        comparison = tc.compare_options([
            {
                "name": "Neonicotinoid seed treatment",
                "emissions": {"imidacloprid": 1.0},
                "compartment": "freshwater",
            },
            {
                "name": "Solvent-based alternative",
                "emissions": {"benzene": 1.0},
                "compartment": "freshwater",
            },
        ])
        self.assertNotEqual(
            comparison["best_human_toxicity"], comparison["best_ecotoxicity"]
        )

    def test_a_margin_inside_interim_uncertainty_is_reported_as_no_result(self):
        """The most important refusal in the module."""
        comparison = tc.compare_options([
            {
                "name": "Lead alloy",
                "emissions": {"lead": 1.0},
                "compartment": "urban_air",
            },
            {
                "name": "Lead alloy, reduced",
                "emissions": {"lead": 0.75},
                "compartment": "urban_air",
            },
        ])
        self.assertTrue(comparison["too_close_to_call"])
        self.assertIn("does not distinguish them", comparison["verdict"])

    def test_a_wide_margin_is_not_dismissed_as_too_close(self):
        comparison = tc.compare_options([
            {
                "name": "Mercury switch",
                "emissions": {"mercury": 1.0},
                "compartment": "urban_air",
            },
            {
                "name": "Solid state",
                "emissions": {"zinc_ion": 0.01},
                "compartment": "urban_air",
            },
        ])
        self.assertFalse(comparison["too_close_to_call"])

    def test_carbon_is_optional_and_its_absence_is_recorded(self):
        comparison = tc.compare_options([
            {"name": "A", "emissions": {"benzene": 1.0},
             "compartment": "urban_air"},
            {"name": "B", "emissions": {"toluene": 1.0},
             "compartment": "urban_air"},
        ])
        self.assertFalse(comparison["carbon_compared"])
        self.assertIsNone(comparison["best_carbon"])

    def test_a_single_option_is_refused(self):
        with self.assertRaises(tc.ToxicityError):
            tc.compare_options([
                {"name": "A", "emissions": {"benzene": 1.0},
                 "compartment": "urban_air"}
            ])

    def test_a_malformed_option_is_refused(self):
        with self.assertRaises(tc.ToxicityError):
            tc.compare_options([
                {"name": "A", "emissions": {"benzene": 1.0}},
                {"name": "B", "emissions": {"toluene": 1.0},
                 "compartment": "urban_air"},
            ])


class TestInsights(unittest.TestCase):

    def test_insights_are_produced_and_are_sentences(self):
        result = tc.assess_emission("lead", 0.5, "agricultural_soil")
        insights = tc.get_toxicity_insights(result)
        self.assertGreaterEqual(len(insights), 4)
        for line in insights:
            self.assertGreater(len(line), 40)

    def test_the_three_steps_are_always_explained(self):
        result = tc.assess_emission("lead", 0.5, "urban_air")
        text = " ".join(tc.get_toxicity_insights(result)).lower()
        self.assertIn("fate", text)
        self.assertIn("intake fraction", text)

    def test_an_interim_factor_is_always_flagged_in_the_insights(self):
        result = tc.assess_emission("cadmium", 0.5, "urban_air")
        text = " ".join(tc.get_toxicity_insights(result)).lower()
        self.assertIn("interim", text)

    def test_persistence_is_called_out_where_it_dominates(self):
        result = tc.assess_emission("tfa", 0.5, "freshwater")
        text = " ".join(tc.get_toxicity_insights(result)).lower()
        self.assertIn("does not go away", text)

    def test_the_non_aggregation_rule_is_always_stated(self):
        result = tc.assess_emission("lead", 0.5, "urban_air")
        text = " ".join(tc.get_toxicity_insights(result))
        self.assertIn("not summed with carbon", text)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.previous = tc.DB_NAME
        tc.DB_NAME = self.path

    def tearDown(self):
        tc.DB_NAME = self.previous
        os.unlink(self.path)

    def _inventory(self):
        return tc.assess_inventory(
            {"lead": 0.002, "glyphosate": 5.0}, "agricultural_soil"
        )

    def test_save_and_read_back(self):
        row_id = tc.save_assessment("u1", "Allotment", self._inventory())
        self.assertGreater(row_id, 0)
        saved = tc.get_assessments("u1")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["name"], "Allotment")
        self.assertGreater(saved[0]["noncancer_ctuh"], 0)

    def test_assessments_are_scoped_to_their_user(self):
        tc.save_assessment("u1", "Mine", self._inventory())
        self.assertEqual(tc.get_assessments("u2"), [])

    def test_a_nameless_assessment_is_refused(self):
        with self.assertRaises(tc.ToxicityError):
            tc.save_assessment("u1", "  ", self._inventory())

    def test_an_ownerless_assessment_is_refused(self):
        with self.assertRaises(tc.ToxicityError):
            tc.save_assessment("", "Allotment", self._inventory())

    def test_delete_removes_only_the_owner_s_row(self):
        row_id = tc.save_assessment("u1", "Allotment", self._inventory())
        self.assertFalse(tc.delete_assessment("u2", row_id))
        self.assertTrue(tc.delete_assessment("u1", row_id))
        self.assertEqual(tc.get_assessments("u1"), [])

    def test_the_interim_flag_survives_the_round_trip(self):
        tc.save_assessment("u1", "Allotment", self._inventory())
        payload = tc.get_assessments("u1")[0]["payload"]
        flags = {row["substance"]: row["interim"] for row in payload["substances"]}
        self.assertTrue(flags["lead"])
        self.assertFalse(flags["glyphosate"])


if __name__ == "__main__":
    unittest.main()
