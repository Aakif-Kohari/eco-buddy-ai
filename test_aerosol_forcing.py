"""Tests for the co-emitted aerosol and short-lived climate forcer engine.

The gas-only view of these activities is not merely incomplete. For several of
them it points the wrong way, and the tests here are built around the cases
where it does:

*   the table contains species of both signs, and a module that lost the
    cooling half would be an argument for dirty air rather than an inventory;
*   the twenty-year and hundred-year rankings of wood against LPG reverse, so
    reporting one horizon silently takes a side in a policy argument;
*   a diesel with a filter and one without have identical CO2 and differ by
    more than an order of magnitude in black carbon;
*   removing sulphur from marine fuel produces near-term warming, and the
    avoided mortality is reported in the same object so the result cannot be
    quoted as an argument for keeping the sulphur;
*   nothing is reported without its uncertainty bounds, because black carbon's
    published range spans a factor of seventeen.

The horizon-reversal test is the load-bearing one. If the ranking of two
options never changed between horizons there would be no reason to report both,
and reporting both is most of what this module is for.
"""

import os
import tempfile
import unittest

import aerosol_forcing as ar


class TestSpeciesTable(unittest.TestCase):

    def test_the_table_contains_species_of_both_signs(self):
        """Without this the module is propaganda rather than an inventory."""
        centrals = [
            ar.get_species(s)["gwp"][100]["central"] for s in ar.list_species()
        ]
        self.assertTrue(any(v > 0 for v in centrals))
        self.assertTrue(any(v < 0 for v in centrals))

    def test_black_carbon_is_the_largest_warming_agent_here(self):
        warming = [
            s for s in ar.list_species()
            if ar.get_species(s)["gwp"][100]["central"] > 0
        ]
        largest = max(
            warming, key=lambda s: ar.get_species(s)["gwp"][100]["central"]
        )
        self.assertEqual(largest, "bc")

    def test_sulphur_dioxide_cools(self):
        self.assertLess(ar.get_species("so2")["gwp"][100]["central"], 0)

    def test_every_species_is_short_lived(self):
        """Days to weeks. Anything longer belongs in climate_metrics.py."""
        for key in ar.list_species():
            self.assertLess(ar.get_species(key)["lifetime_days"], 120)

    def test_every_species_explains_itself(self):
        for key in ar.list_species():
            self.assertGreater(len(ar.get_species(key)["note"]), 40)

    def test_bounds_bracket_the_central_estimate(self):
        for key in ar.list_species():
            for horizon in ar.HORIZONS:
                with self.subTest(species=key, horizon=horizon):
                    gwp = ar.get_species(key)["gwp"][horizon]
                    self.assertLessEqual(gwp["low"], gwp["central"])
                    self.assertLessEqual(gwp["central"], gwp["high"])

    def test_black_carbons_range_spans_more_than_an_order_of_magnitude(self):
        """The reason no figure in this module is offered without bounds."""
        gwp = ar.get_species("bc")["gwp"][100]
        self.assertGreater(gwp["high"] / gwp["low"], 10)

    def test_nitrogen_oxides_are_the_species_whose_range_crosses_zero(self):
        gwp = ar.get_species("nox")["gwp"][100]
        self.assertLess(gwp["low"], 0)
        self.assertGreater(gwp["high"], 0)

    def test_every_species_is_stronger_over_twenty_years_than_a_hundred(self):
        """They are gone within weeks; only the CO2 comparison changes."""
        for key in ar.list_species():
            with self.subTest(species=key):
                self.assertGreater(
                    abs(ar.get_species(key)["gwp"][20]["central"]),
                    abs(ar.get_species(key)["gwp"][100]["central"]),
                )

    def test_unknown_species_is_rejected_with_a_useful_message(self):
        with self.assertRaises(ar.AerosolError) as caught:
            ar.get_species("methane")
        self.assertIn("bc", str(caught.exception))


class TestSourceTable(unittest.TestCase):

    def test_every_source_covers_every_species(self):
        for key in ar.list_sources():
            with self.subTest(source=key):
                emissions = ar.get_source(key)["emissions_g_per_unit"]
                for species in ar.list_species():
                    self.assertIn(species, emissions)
                    self.assertGreaterEqual(emissions[species], 0.0)

    def test_every_source_explains_itself(self):
        for key in ar.list_sources():
            self.assertGreater(len(ar.get_source(key)["note"]), 40)

    def test_sectors_partition_the_table(self):
        covered = []
        for sector in ar.list_sectors():
            covered.extend(ar.list_sources(sector))
        self.assertCountEqual(covered, ar.list_sources())

    def test_the_two_diesels_have_identical_co2(self):
        """The pair exists to show that the fuel label is not the factor."""
        self.assertEqual(
            ar.get_source("diesel_no_dpf")["co2_kg_per_unit"],
            ar.get_source("diesel_dpf")["co2_kg_per_unit"],
        )

    def test_a_filter_removes_most_of_the_black_carbon(self):
        unfiltered = ar.get_source("diesel_no_dpf")["emissions_g_per_unit"]["bc"]
        filtered = ar.get_source("diesel_dpf")["emissions_g_per_unit"]["bc"]
        self.assertGreater(unfiltered / filtered, 10)

    def test_the_two_shipping_fuels_have_identical_co2(self):
        self.assertEqual(
            ar.get_source("shipping_hfo_high_sulphur")["co2_kg_per_unit"],
            ar.get_source("shipping_low_sulphur")["co2_kg_per_unit"],
        )

    def test_the_sulphur_cap_removed_most_of_the_sulphur(self):
        before = ar.get_source("shipping_hfo_high_sulphur")
        after = ar.get_source("shipping_low_sulphur")
        self.assertGreater(
            before["emissions_g_per_unit"]["so2"]
            / after["emissions_g_per_unit"]["so2"],
            10,
        )

    def test_certified_and_traditional_stoves_burn_the_same_wood(self):
        self.assertEqual(
            ar.get_source("wood_stove_traditional")["co2_kg_per_unit"],
            ar.get_source("wood_stove_certified")["co2_kg_per_unit"],
        )

    def test_a_kerosene_lamp_is_the_most_black_carbon_intensive_source(self):
        worst = max(
            ar.list_sources(),
            key=lambda k: ar.get_source(k)["emissions_g_per_unit"]["bc"],
        )
        self.assertEqual(worst, "kerosene_lamp")


class TestDeposition(unittest.TestCase):

    def test_the_arctic_multiplier_is_the_largest(self):
        self.assertEqual(ar.list_regions()[0], "arctic")

    def test_temperate_is_the_unweighted_reference_case(self):
        self.assertEqual(ar.get_region("temperate")["bc_efficacy"], 1.0)

    def test_deposition_only_touches_the_depositing_species(self):
        for species in ar.list_species():
            with self.subTest(species=species):
                temperate = ar.species_gwp(species, 100, region="temperate")
                arctic = ar.species_gwp(species, 100, region="arctic")
                if ar.get_species(species)["deposition_sensitive"]:
                    self.assertGreater(abs(arctic), abs(temperate))
                else:
                    self.assertEqual(arctic, temperate)

    def test_arctic_black_carbon_is_worth_several_times_temperate(self):
        self.assertGreater(
            ar.species_gwp("bc", 20, region="arctic")
            / ar.species_gwp("bc", 20, region="temperate"),
            2.0,
        )

    def test_unknown_region_is_rejected(self):
        with self.assertRaises(ar.AerosolError):
            ar.species_gwp("bc", 100, region="antarctic")


class TestCharacterisation(unittest.TestCase):

    def test_warming_and_cooling_are_accumulated_separately(self):
        result = ar.characterise({"bc": 1.0, "so2": 10.0}, 20)
        self.assertGreater(result["warming_co2e"], 0)
        self.assertLess(result["cooling_co2e"], 0)

    def test_the_net_is_the_sum_of_the_two_halves(self):
        result = ar.characterise({"bc": 1.0, "so2": 10.0}, 20)
        self.assertAlmostEqual(
            result["net_co2e"],
            result["warming_co2e"] + result["cooling_co2e"],
            places=6,
        )

    def test_bounds_bracket_the_net(self):
        result = ar.characterise({"bc": 1.0, "so2": 10.0, "nox": 5.0}, 20)
        self.assertLessEqual(result["net_co2e_low"], result["net_co2e"])
        self.assertLessEqual(result["net_co2e"], result["net_co2e_high"])

    def test_a_cooling_species_bound_is_ordered_not_trusted_to_its_label(self):
        """Low and high swap over for a negative GWP, so they get sorted."""
        result = ar.characterise({"so2": 10.0}, 20)
        row = result["species"][0]
        self.assertLessEqual(row["co2e_low"], row["co2e_high"])

    def test_characterisation_is_linear_in_mass(self):
        one = ar.characterise({"bc": 1.0}, 20)
        two = ar.characterise({"bc": 2.0}, 20)
        self.assertAlmostEqual(
            two["net_co2e"], one["net_co2e"] * 2, places=6
        )

    def test_an_untabulated_horizon_is_refused(self):
        with self.assertRaises(ar.AerosolError):
            ar.characterise({"bc": 1.0}, 50)

    def test_negative_mass_is_rejected(self):
        with self.assertRaises(ar.AerosolError):
            ar.characterise({"bc": -1.0}, 20)

    def test_an_empty_inventory_characterises_to_nothing(self):
        result = ar.characterise({}, 20)
        self.assertEqual(result["species"], [])
        self.assertEqual(result["net_co2e"], 0.0)


class TestActivityAssessment(unittest.TestCase):

    def test_both_horizons_are_always_present(self):
        """There is no argument to request only one, deliberately."""
        result = ar.assess_activity("wood_stove_traditional", 1.0)
        self.assertEqual(set(result["horizons"]), set(ar.HORIZONS))

    def test_a_traditional_stove_more_than_doubles_its_near_term_effect(self):
        result = ar.assess_activity("wood_stove_traditional", 1.0)
        self.assertGreater(result["near_term_multiple"], 2.0)

    def test_the_same_stove_is_close_to_its_co2_over_a_century(self):
        result = ar.assess_activity("wood_stove_traditional", 1.0)
        self.assertLess(result["long_term_multiple"], 1.6)

    def test_a_certified_stove_is_far_better_with_identical_co2(self):
        traditional = ar.assess_activity("wood_stove_traditional", 1.0)
        certified = ar.assess_activity("wood_stove_certified", 1.0)
        self.assertEqual(traditional["co2_kg"], certified["co2_kg"])
        self.assertLess(
            certified["horizons"][20]["net_co2e"],
            traditional["horizons"][20]["net_co2e"] / 3,
        )

    def test_a_kerosene_lamp_is_dominated_by_its_particulate(self):
        result = ar.assess_activity("kerosene_lamp", 1.0)
        self.assertTrue(result["slcf_dominates_near_term"])
        self.assertGreater(result["near_term_multiple"], 10)

    def test_a_filter_closes_almost_the_whole_gap_between_two_diesels(self):
        unfiltered = ar.assess_activity("diesel_no_dpf", 1.0)
        filtered = ar.assess_activity("diesel_dpf", 1.0)
        self.assertEqual(unfiltered["co2_kg"], filtered["co2_kg"])
        self.assertGreater(
            unfiltered["horizons"][20]["total_co2e"],
            filtered["horizons"][20]["total_co2e"] * 1.5,
        )

    def test_high_sulphur_marine_fuel_is_net_cooling_in_the_near_term(self):
        """Uncomfortable, well established, and the module reports it."""
        result = ar.assess_activity("shipping_hfo_high_sulphur", 1.0)
        self.assertLess(result["horizons"][20]["net_co2e"], 0)
        self.assertLess(result["horizons"][20]["total_co2e"], 0)

    def test_lpg_beats_wood_in_the_near_term_despite_more_co2(self):
        wood = ar.assess_activity("wood_stove_traditional", 1.0)
        lpg = ar.assess_activity("lpg_cooking", 1.0)
        self.assertGreater(lpg["co2_kg"], wood["co2_kg"])
        self.assertLess(
            lpg["horizons"][20]["total_co2e"],
            wood["horizons"][20]["total_co2e"],
        )

    def test_the_result_scales_with_activity(self):
        one = ar.assess_activity("wood_stove_traditional", 1.0)
        ten = ar.assess_activity("wood_stove_traditional", 10.0)
        self.assertAlmostEqual(
            ten["horizons"][20]["net_co2e"],
            one["horizons"][20]["net_co2e"] * 10,
            places=6,
        )

    def test_arctic_deposition_raises_a_sooty_source(self):
        temperate = ar.assess_activity("kerosene_lamp", 1.0, "temperate")
        arctic = ar.assess_activity("kerosene_lamp", 1.0, "arctic")
        self.assertGreater(
            arctic["horizons"][20]["net_co2e"],
            temperate["horizons"][20]["net_co2e"] * 2,
        )

    def test_the_result_says_it_is_an_overlay_not_a_replacement(self):
        result = ar.assess_activity("wood_stove_traditional", 1.0)
        self.assertIn("climate_metrics", result["overlay_note"])

    def test_negative_activity_is_rejected(self):
        with self.assertRaises(ar.AerosolError):
            ar.assess_activity("wood_stove_traditional", -1.0)

    def test_unknown_source_is_rejected(self):
        with self.assertRaises(ar.AerosolError):
            ar.assess_activity("nuclear", 1.0)


class TestHorizonReversal(unittest.TestCase):
    """The load-bearing case for reporting both horizons."""

    def test_wood_and_lpg_swap_places_between_horizons(self):
        comparison = ar.compare_sources(
            ["wood_stove_traditional", "lpg_cooking"]
        )
        self.assertTrue(comparison["ranking_changes_with_horizon"])
        self.assertEqual(comparison["ranking_20"][0], "lpg_cooking")
        self.assertEqual(comparison["ranking_100"][0], "wood_stove_traditional")

    def test_a_reversal_is_reported_in_words(self):
        comparison = ar.compare_sources(
            ["wood_stove_traditional", "lpg_cooking"]
        )
        self.assertIn("reverses", comparison["note"])

    def test_a_stable_ranking_is_also_reported_in_words(self):
        comparison = ar.compare_sources(["diesel_no_dpf", "diesel_dpf"])
        self.assertFalse(comparison["ranking_changes_with_horizon"])
        self.assertIn("holds at both horizons", comparison["note"])

    def test_comparing_nothing_is_refused(self):
        with self.assertRaises(ar.AerosolError):
            ar.compare_sources([])


class TestCo2OnlyError(unittest.TestCase):

    def test_a_sooty_source_is_understated_by_a_co2_only_inventory(self):
        error = ar.co2_only_error("wood_stove_traditional")
        near = next(r for r in error["rows"] if r["horizon_years"] == 20)
        self.assertTrue(near["understated"])
        self.assertGreater(near["error_fraction"], 1.0)

    def test_a_sulphurous_source_is_overstated_by_a_co2_only_inventory(self):
        error = ar.co2_only_error("shipping_hfo_high_sulphur")
        near = next(r for r in error["rows"] if r["horizon_years"] == 20)
        self.assertFalse(near["understated"])
        self.assertLess(near["error_fraction"], 0.0)

    def test_the_error_shrinks_towards_the_longer_horizon(self):
        error = ar.co2_only_error("wood_stove_traditional")
        near = next(r for r in error["rows"] if r["horizon_years"] == 20)
        far = next(r for r in error["rows"] if r["horizon_years"] == 100)
        self.assertGreater(
            abs(near["error_fraction"]), abs(far["error_fraction"])
        )

    def test_a_clean_source_has_almost_no_error(self):
        error = ar.co2_only_error("lpg_cooking")
        for row in error["rows"]:
            self.assertLess(abs(row["error_fraction"]), 0.05)


class TestUnmasking(unittest.TestCase):

    def test_the_sulphur_cap_warms_in_the_near_term(self):
        result = ar.unmasking(
            "shipping_hfo_high_sulphur", "shipping_low_sulphur", 1000
        )
        self.assertTrue(result["is_unmasking"])
        self.assertGreater(result["horizons"][20]["delta_co2e"], 0)

    def test_the_avoided_exposure_is_reported_in_the_same_object(self):
        """So the result cannot be quoted as an argument for dirty air."""
        result = ar.unmasking(
            "shipping_hfo_high_sulphur", "shipping_low_sulphur", 1000
        )
        self.assertGreater(result["pm_avoided_kg"], 0)
        self.assertGreater(result["indicative_deaths_avoided"], 0)

    def test_the_note_frames_it_as_a_trade_off_rather_than_a_verdict(self):
        result = ar.unmasking(
            "shipping_hfo_high_sulphur", "shipping_low_sulphur", 1000
        )
        self.assertIn("not an argument against", result["note"])

    def test_scrubbing_a_coal_plant_is_also_unmasking(self):
        result = ar.unmasking("coal_power_no_fgd", "coal_power_with_fgd", 1000)
        self.assertTrue(result["is_unmasking"])

    def test_fitting_a_particulate_filter_is_not_unmasking(self):
        """Removing a warming species cools; there is no trade-off to weigh."""
        result = ar.unmasking("diesel_no_dpf", "diesel_dpf", 1000)
        self.assertFalse(result["is_unmasking"])
        self.assertIn("no unmasking trade-off", result["note"])

    def test_the_mortality_figure_is_flagged_as_indicative(self):
        result = ar.unmasking(
            "shipping_hfo_high_sulphur", "shipping_low_sulphur", 1000
        )
        self.assertIn("health_cobenefits", result["mortality_caveat"])


class TestUncertainty(unittest.TestCase):

    def test_bounds_are_produced_at_both_horizons(self):
        result = ar.uncertainty_range("wood_stove_traditional")
        self.assertEqual(len(result["rows"]), len(ar.HORIZONS))

    def test_the_central_estimate_lies_within_its_bounds(self):
        result = ar.uncertainty_range("wood_stove_traditional")
        for row in result["rows"]:
            self.assertLessEqual(row["low"], row["central"])
            self.assertLessEqual(row["central"], row["high"])

    def test_a_sooty_source_carries_a_wide_range(self):
        result = ar.uncertainty_range("kerosene_lamp")
        near = next(r for r in result["rows"] if r["horizon_years"] == 20)
        self.assertGreater(near["high"] - near["low"], near["central"])

    def test_the_sign_can_be_reported_as_undetermined(self):
        """Where the bounds straddle zero, the central sign is not a finding."""
        result = ar.uncertainty_range("coal_residential")
        near = next(r for r in result["rows"] if r["horizon_years"] == 20)
        self.assertFalse(near["sign_determined"])

    def test_the_note_explains_why_the_range_is_this_wide(self):
        result = ar.uncertainty_range("wood_stove_traditional")
        self.assertIn("largest uncertainty", result["note"])


class TestInsights(unittest.TestCase):

    def test_insights_are_produced_and_are_sentences(self):
        result = ar.assess_activity("wood_stove_traditional", 1.0)
        insights = ar.get_aerosol_insights(result)
        self.assertGreaterEqual(len(insights), 4)
        for line in insights:
            self.assertGreater(len(line), 40)

    def test_both_horizons_are_always_mentioned(self):
        result = ar.assess_activity("wood_stove_traditional", 1.0)
        text = " ".join(ar.get_aerosol_insights(result)).lower()
        self.assertIn("twenty-year", text)
        self.assertIn("hundred-year", text)

    def test_the_uncertainty_is_always_mentioned(self):
        result = ar.assess_activity("wood_stove_traditional", 1.0)
        text = " ".join(ar.get_aerosol_insights(result)).lower()
        self.assertIn("range", text)

    def test_cooling_is_described_as_a_by_product_not_a_benefit(self):
        result = ar.assess_activity("shipping_hfo_high_sulphur", 1.0)
        text = " ".join(ar.get_aerosol_insights(result)).lower()
        self.assertIn("not something to preserve", text)

    def test_the_deposition_weighting_is_stated_when_it_applies(self):
        result = ar.assess_activity("kerosene_lamp", 1.0, "arctic")
        text = " ".join(ar.get_aerosol_insights(result)).lower()
        self.assertIn("deposition", text)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.previous = ar.DB_NAME
        ar.DB_NAME = self.path

    def tearDown(self):
        ar.DB_NAME = self.previous
        os.unlink(self.path)

    def _result(self):
        return ar.assess_activity("wood_stove_traditional", 500.0)

    def test_save_and_read_back(self):
        row_id = ar.save_assessment("u1", "Winter wood", self._result())
        self.assertGreater(row_id, 0)
        saved = ar.get_assessments("u1")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["name"], "Winter wood")
        self.assertGreater(saved[0]["net_slcf_20"], saved[0]["net_slcf_100"])

    def test_assessments_are_scoped_to_their_user(self):
        ar.save_assessment("u1", "Mine", self._result())
        self.assertEqual(ar.get_assessments("u2"), [])

    def test_a_nameless_assessment_is_refused(self):
        with self.assertRaises(ar.AerosolError):
            ar.save_assessment("u1", "  ", self._result())

    def test_an_ownerless_assessment_is_refused(self):
        with self.assertRaises(ar.AerosolError):
            ar.save_assessment("", "Wood", self._result())

    def test_delete_removes_only_the_owner_s_row(self):
        row_id = ar.save_assessment("u1", "Wood", self._result())
        self.assertFalse(ar.delete_assessment("u2", row_id))
        self.assertTrue(ar.delete_assessment("u1", row_id))
        self.assertEqual(ar.get_assessments("u1"), [])

    def test_the_payload_survives_the_round_trip(self):
        ar.save_assessment("u1", "Wood", self._result())
        payload = ar.get_assessments("u1")[0]["payload"]
        self.assertEqual(payload["source"], "wood_stove_traditional")
        self.assertIn("bc", payload["emissions_kg"])
        self.assertGreater(payload["near_term_multiple"], 1.0)


if __name__ == "__main__":
    unittest.main()
