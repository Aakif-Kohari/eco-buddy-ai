"""Tests for the net energy and EROI engine.

Every energy module in this app reports gross output. This one reports what is
left after the energy sector has taken its own cut, and the tests guard the
properties that make that distinction usable:

*   the system boundary is required, because the same technology differs by
    more than a factor of two between the wellhead and the extended boundary -
    a boundary-free ratio is a rhetorical device, not a number;
*   the reinvestment curve is non-linear, so a fall from five to three costs
    society far more than a fall from thirty to twenty;
*   storage is an energy cost, and buffering can take a source from above the
    societal minimum to below it;
*   energy payback and lifetime ratio are different questions, and a source can
    be good at one and middling at the other;
*   the three energy quality conventions reorder electric against thermal
    options, so none of them is presented as the answer;
*   energy return and carbon are separate scarcities - coal ranks near the top
    on one and the bottom on the other, and no composite is offered.

The boundary test is the load-bearing one. Selective boundary choice is the
standard way EROI figures are used to mislead, from both directions.
"""

import os
import tempfile
import unittest

import net_energy_eroi as ne


class TestSourceTable(unittest.TestCase):

    def test_every_source_has_all_three_boundaries(self):
        for key in ne.list_sources():
            with self.subTest(source=key):
                ratios = ne.get_source(key)["eroi"]
                for boundary in ne.list_boundaries():
                    self.assertIn(boundary, ratios)
                    self.assertGreater(ratios[boundary], 0)

    def test_every_source_explains_itself(self):
        for key in ne.list_sources():
            self.assertGreater(len(ne.get_source(key)["note"]), 40)

    def test_families_partition_the_table(self):
        covered = []
        for family in ne.list_families():
            covered.extend(ne.list_sources(family))
        self.assertCountEqual(covered, ne.list_sources())

    def test_capacity_factors_are_fractions(self):
        for key in ne.list_sources():
            with self.subTest(source=key):
                factor = ne.get_source(key)["capacity_factor"]
                self.assertGreater(factor, 0.0)
                self.assertLessEqual(factor, 1.0)

    def test_every_carrier_is_known(self):
        for key in ne.list_sources():
            self.assertIn(ne.get_source(key)["carrier"], ne.list_carriers())

    def test_hydro_has_the_best_ratio_and_biofuel_the_worst(self):
        ordered = sorted(
            ne.list_sources(), key=lambda k: ne.eroi(k, "standard")
        )
        self.assertEqual(ordered[-1], "hydro")
        self.assertEqual(ordered[0], "corn_ethanol")

    def test_biofuels_sit_near_the_energetic_floor(self):
        for key in ne.list_sources("biofuel"):
            self.assertLess(ne.eroi(key, "point_of_use"), 4.0)

    def test_efficiency_measures_compete_with_supply(self):
        """A negawatt has a return on investment like anything else."""
        insulation = ne.eroi("efficiency_insulation", "point_of_use")
        self.assertGreater(insulation, ne.eroi("solar_pv_utility", "point_of_use"))

    def test_unknown_source_is_rejected_with_a_useful_message(self):
        with self.assertRaises(ne.NetEnergyError) as caught:
            ne.get_source("fusion")
        self.assertIn("hydro", str(caught.exception))


class TestBoundaryIsRequired(unittest.TestCase):
    """The load-bearing rule."""

    def test_a_missing_boundary_is_refused_with_an_explanation(self):
        with self.assertRaises(ne.NetEnergyError) as caught:
            ne.get_boundary(None)
        self.assertIn("not a number", str(caught.exception))

    def test_an_unknown_boundary_is_rejected(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.eroi("hydro", "at_the_socket")

    def test_the_boundary_always_narrows_the_ratio(self):
        for key in ne.list_sources():
            with self.subTest(source=key):
                spec = ne.get_source(key)
                self.assertGreaterEqual(
                    spec["eroi"]["standard"], spec["eroi"]["point_of_use"]
                )
                self.assertGreaterEqual(
                    spec["eroi"]["point_of_use"], spec["eroi"]["extended"]
                )

    def test_the_spread_across_boundaries_is_large(self):
        spread = ne.eroi_across_boundaries("conventional_oil")
        self.assertGreater(spread["spread_ratio"], 2.0)

    def test_refining_takes_most_of_a_liquid_fuels_return(self):
        spec = ne.get_source("conventional_oil")
        self.assertLess(
            spec["eroi"]["point_of_use"], spec["eroi"]["standard"] * 0.6
        )

    def test_the_spread_note_names_both_ends(self):
        spread = ne.eroi_across_boundaries("wind_onshore")
        self.assertIn("where the accounting stops", spread["note"])

    def test_variable_sources_lose_most_at_the_extended_boundary(self):
        """Because grid and storage are a large share of what they need."""
        variable = ne.eroi_across_boundaries("wind_onshore")["spread_ratio"]
        firm = ne.eroi_across_boundaries("geothermal")["spread_ratio"]
        self.assertGreater(variable, firm)


class TestTheCliff(unittest.TestCase):

    def test_reinvestment_is_the_reciprocal_of_the_ratio(self):
        self.assertAlmostEqual(ne.reinvestment_fraction(10.0), 0.1, places=12)

    def test_the_curve_is_non_linear(self):
        """The whole point: the top of the range is flat and the bottom is not."""
        top = (
            ne.reinvestment_fraction(20.0) - ne.reinvestment_fraction(30.0)
        )
        bottom = (
            ne.reinvestment_fraction(3.0) - ne.reinvestment_fraction(5.0)
        )
        self.assertGreater(bottom, top * 5)

    def test_surplus_and_reinvestment_always_sum_to_one(self):
        for row in ne.net_energy_cliff()["rows"]:
            self.assertAlmostEqual(
                row["surplus_fraction"] + row["reinvestment_fraction"],
                1.0,
                places=12,
            )

    def test_the_societal_minimum_is_stated_as_contested(self):
        cliff = ne.net_energy_cliff()
        self.assertIn("contested", cliff["minimum_caveat"])

    def test_low_ratio_sources_are_flagged_against_the_minimum(self):
        position = ne.societal_position("corn_ethanol", "point_of_use")
        self.assertTrue(position["below_societal_minimum"])

    def test_high_ratio_sources_are_not(self):
        position = ne.societal_position("hydro", "point_of_use")
        self.assertFalse(position["below_societal_minimum"])

    def test_a_zero_ratio_is_rejected(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.reinvestment_fraction(0.0)


class TestPayback(unittest.TestCase):

    def test_paybacks_land_in_credible_ranges(self):
        """Order of magnitude against published values."""
        for key in ne.list_sources():
            with self.subTest(source=key):
                payback = ne.energy_payback(key)
                self.assertGreater(payback["payback_years"], 0.05)
                self.assertLess(payback["payback_years"], 10.0)

    def test_rooftop_solar_takes_a_few_years(self):
        payback = ne.energy_payback("solar_pv_rooftop_temperate")
        self.assertGreater(payback["payback_years"], 1.5)
        self.assertLess(payback["payback_years"], 5.0)

    def test_wind_pays_back_within_a_year(self):
        payback = ne.energy_payback("wind_onshore")
        self.assertLess(payback["payback_years"], 1.0)

    def test_payback_is_always_a_small_share_of_life(self):
        for key in ne.list_sources():
            with self.subTest(source=key):
                self.assertLess(
                    ne.energy_payback(key)["payback_share_of_life"], 0.35
                )

    def test_payback_and_lifetime_ratio_are_different_questions(self):
        """Offshore wind pays back faster than rooftop solar and returns more
        per unit invested than its own capacity factor would suggest."""
        offshore = ne.energy_payback("wind_offshore")
        rooftop = ne.energy_payback("solar_pv_rooftop_temperate")
        self.assertLess(offshore["payback_years"], rooftop["payback_years"])
        self.assertGreater(
            offshore["lifetime_ratio"], rooftop["lifetime_ratio"]
        )

    def test_more_sun_means_faster_payback(self):
        poor = ne.energy_payback("solar_pv_utility", 0.12)
        good = ne.energy_payback("solar_pv_utility", 0.30)
        self.assertGreater(poor["payback_years"], good["payback_years"] * 2)

    def test_sensitivity_brackets_the_reference_case(self):
        rows = ne.payback_sensitivity("solar_pv_utility")
        self.assertTrue(any(row["is_reference"] for row in rows))
        self.assertGreater(len(rows), 2)

    def test_the_result_distinguishes_itself_from_carbon_payback(self):
        payback = ne.energy_payback("solar_pv_utility")
        self.assertIn("carbon_payback.py", payback["carbon_payback_note"])

    def test_an_impossible_capacity_factor_is_rejected(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.energy_payback("solar_pv_utility", 1.4)


class TestBuffering(unittest.TestCase):

    def test_storage_always_costs_an_intermittent_source(self):
        result = ne.buffered_eroi("wind_onshore", "point_of_use")
        self.assertLess(result["buffered_eroi"], result["unbuffered_eroi"])
        self.assertGreater(result["penalty_fraction"], 0.0)

    def test_a_dispatchable_source_is_not_penalised(self):
        """It does not incur the cost, so it must not be charged for it."""
        result = ne.buffered_eroi("nuclear_lwr", "point_of_use")
        self.assertEqual(result["buffered_eroi"], result["unbuffered_eroi"])
        self.assertFalse(result["intermittent"])

    def test_the_unbuffered_case_is_labelled_as_not_a_system_figure(self):
        result = ne.buffered_eroi("wind_onshore", "point_of_use", "none")
        self.assertIn("not a system figure", result["note"])

    def test_a_poor_round_trip_destroys_delivered_energy(self):
        """Isolating the efficiency term from the embodied one."""
        battery = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", "lithium_ion"
        )
        hydrogen = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", "hydrogen"
        )
        self.assertLess(
            hydrogen["delivered_kwh_per_kw"], battery["delivered_kwh_per_kw"]
        )

    def test_cheap_storage_can_offset_a_poor_round_trip(self):
        """Which is why the penalty is not simply a function of efficiency.

        Hydrogen loses nearly two thirds of every round trip and costs a
        fraction of lithium-ion's embodied energy per kilowatt-hour of
        capacity. At short durations the second effect wins, and a model that
        ranked storage on efficiency alone would get this backwards.
        """
        battery = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", "lithium_ion"
        )
        hydrogen = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", "hydrogen"
        )
        self.assertLess(
            hydrogen["storage_invested_kwh_per_kw"],
            battery["storage_invested_kwh_per_kw"],
        )
        self.assertLess(
            hydrogen["penalty_fraction"], battery["penalty_fraction"]
        )

    def test_a_poor_round_trip_dominates_at_long_duration(self):
        """The crossover, which is the actual finding about storage choice."""
        battery = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", "lithium_ion",
            storage_hours=4.0, buffered_share=0.9,
        )
        hydrogen = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", "hydrogen",
            storage_hours=4.0, buffered_share=0.9,
        )
        self.assertGreater(
            hydrogen["penalty_fraction"], battery["penalty_fraction"]
        )

    def test_more_storage_costs_more(self):
        light = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", storage_hours=2.0
        )
        heavy = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", storage_hours=12.0
        )
        self.assertLess(heavy["buffered_eroi"], light["buffered_eroi"])

    def test_buffering_can_cross_the_societal_minimum(self):
        """The result the storage modules cannot currently produce."""
        result = ne.buffered_eroi(
            "solar_pv_utility", "point_of_use", "lithium_ion",
            storage_hours=8.0, buffered_share=0.6,
        )
        self.assertTrue(result["crosses_societal_minimum"])
        self.assertLess(result["buffered_eroi"], ne.SOCIETAL_MINIMUM_EROI)
        self.assertGreater(result["unbuffered_eroi"], ne.SOCIETAL_MINIMUM_EROI)

    def test_every_branch_returns_the_same_shape(self):
        """Callers must not have to know which branch they got."""
        keys = {
            "unbuffered_eroi", "buffered_eroi", "penalty_fraction",
            "crosses_societal_minimum", "intermittent",
        }
        for source, storage in (
            ("wind_onshore", "lithium_ion"),
            ("wind_onshore", "none"),
            ("nuclear_lwr", "lithium_ion"),
        ):
            with self.subTest(source=source, storage=storage):
                result = ne.buffered_eroi(source, "point_of_use", storage)
                self.assertTrue(keys.issubset(result))

    def test_curtailment_outside_range_is_rejected(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.buffered_eroi("wind_onshore", "point_of_use", curtailment=1.2)

    def test_buffered_share_outside_range_is_rejected(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.buffered_eroi(
                "wind_onshore", "point_of_use", buffered_share=-0.1
            )


class TestEnergyQuality(unittest.TestCase):

    def test_the_conventions_reorder_electric_against_thermal_options(self):
        """The reason neither is presented as the answer."""
        comparison = ne.quality_comparison(
            ["heat_pump_displacement", "solar_pv_utility",
             "efficiency_insulation"],
            "point_of_use",
        )
        self.assertTrue(comparison["conventions_disagree"])

    def test_a_disagreement_is_reported_in_words(self):
        comparison = ne.quality_comparison(
            ["heat_pump_displacement", "solar_pv_utility"], "point_of_use"
        )
        self.assertIn("different questions", comparison["note"])

    def test_thermal_equivalent_weights_everything_the_same(self):
        for key in ne.list_sources():
            with self.subTest(source=key):
                weighted = ne.quality_weighted(
                    key, "point_of_use", "thermal_equivalent"
                )
                self.assertEqual(weighted["weight"], 1.0)

    def test_exergy_penalises_low_grade_heat(self):
        heat = ne.quality_weighted(
            "efficiency_insulation", "point_of_use", "exergy"
        )
        self.assertLess(heat["weighted_eroi"], heat["unweighted_eroi"])

    def test_primary_equivalent_favours_electricity(self):
        power = ne.quality_weighted(
            "solar_pv_utility", "point_of_use", "primary_equivalent"
        )
        self.assertGreater(power["weighted_eroi"], power["unweighted_eroi"])

    def test_an_unknown_convention_is_rejected(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.quality_weighted("hydro", "point_of_use", "vibes")

    def test_a_single_source_comparison_is_refused(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.quality_comparison(["hydro"], "point_of_use")


class TestHousehold(unittest.TestCase):

    def test_a_household_position_combines_its_measures(self):
        position = ne.household_position(
            {"solar_pv_rooftop_temperate": 4.0, "efficiency_insulation": 2.0},
            "point_of_use",
        )
        self.assertGreater(position["gross_annual_kwh"], 0)
        self.assertGreater(position["net_annual_kwh"], 0)
        self.assertLess(
            position["net_annual_kwh"], position["gross_annual_kwh"]
        )

    def test_the_combined_ratio_lies_between_its_components(self):
        position = ne.household_position(
            {"solar_pv_rooftop_temperate": 4.0, "efficiency_insulation": 2.0},
            "point_of_use",
        )
        ratios = [row["eroi"] for row in position["installations"]]
        self.assertGreaterEqual(position["combined_eroi"], min(ratios))
        self.assertLessEqual(position["combined_eroi"], max(ratios))

    def test_efficiency_lifts_a_solar_only_household(self):
        """Because insulation returns more per unit invested than a panel."""
        solar_only = ne.household_position(
            {"solar_pv_rooftop_temperate": 4.0}, "point_of_use"
        )
        with_insulation = ne.household_position(
            {"solar_pv_rooftop_temperate": 4.0, "efficiency_insulation": 2.0},
            "point_of_use",
        )
        self.assertGreater(
            with_insulation["combined_eroi"], solar_only["combined_eroi"]
        )

    def test_adding_storage_lowers_the_position(self):
        without = ne.household_position(
            {"solar_pv_rooftop_temperate": 4.0}, "point_of_use"
        )
        with_battery = ne.household_position(
            {"solar_pv_rooftop_temperate": 4.0}, "point_of_use",
            storage="lithium_ion", storage_hours=6.0,
        )
        self.assertLess(
            with_battery["combined_eroi"], without["combined_eroi"]
        )

    def test_an_empty_household_is_refused(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.household_position({}, "point_of_use")

    def test_zero_capacity_is_rejected(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.household_position(
                {"solar_pv_rooftop_temperate": 0.0}, "point_of_use"
            )


class TestEnergyVersusCarbon(unittest.TestCase):

    def test_coal_ranks_near_the_top_on_energy_and_the_bottom_on_carbon(self):
        """The flagship divergence, and the reason no composite is offered."""
        result = ne.energy_versus_carbon()
        coal = next(c for c in result["conflicts"] if c["source"] == "coal")
        self.assertLess(coal["energy_rank"], 6)
        self.assertGreater(coal["carbon_rank"], 10)

    def test_conflicts_are_detected_at_all(self):
        result = ne.energy_versus_carbon()
        self.assertGreater(len(result["conflicts"]), 0)

    def test_no_composite_score_is_produced(self):
        result = ne.energy_versus_carbon()
        for row in result["rows"]:
            self.assertNotIn("score", row)
        self.assertIn("political question", result["no_composite_note"])

    def test_both_rankings_cover_every_source_asked_for(self):
        sources = ["coal", "hydro", "solar_pv_utility"]
        result = ne.energy_versus_carbon(sources)
        self.assertCountEqual(result["ranking_by_energy"], sources)
        self.assertCountEqual(result["ranking_by_carbon"], sources)


class TestInsights(unittest.TestCase):

    def test_insights_are_produced_and_are_sentences(self):
        insights = ne.get_net_energy_insights("solar_pv_rooftop_temperate",
                                              "point_of_use")
        self.assertGreaterEqual(len(insights), 4)
        for line in insights:
            self.assertGreater(len(line), 40)

    def test_the_boundary_spread_is_always_mentioned(self):
        text = " ".join(
            ne.get_net_energy_insights("conventional_oil", "point_of_use")
        )
        self.assertIn("where the accounting stops", text)

    def test_carbon_is_always_separated_out(self):
        text = " ".join(ne.get_net_energy_insights("coal", "point_of_use"))
        self.assertIn("separate questions", text)

    def test_buffering_is_mentioned_for_a_variable_source(self):
        text = " ".join(
            ne.get_net_energy_insights("wind_onshore", "point_of_use")
        ).lower()
        self.assertIn("dispatchability", text)

    def test_buffering_is_not_mentioned_for_a_firm_source(self):
        text = " ".join(
            ne.get_net_energy_insights("nuclear_lwr", "point_of_use")
        ).lower()
        self.assertNotIn("dispatchability", text)

    def test_the_societal_minimum_is_flagged_where_it_bites(self):
        text = " ".join(
            ne.get_net_energy_insights("corn_ethanol", "point_of_use")
        ).lower()
        self.assertIn("minimum", text)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.previous = ne.DB_NAME
        ne.DB_NAME = self.path

    def tearDown(self):
        ne.DB_NAME = self.previous
        os.unlink(self.path)

    def _position(self):
        return ne.household_position(
            {"solar_pv_rooftop_temperate": 4.0, "efficiency_insulation": 2.0},
            "point_of_use",
        )

    def test_save_and_read_back(self):
        row_id = ne.save_position("u1", "Our house", self._position())
        self.assertGreater(row_id, 0)
        saved = ne.get_positions("u1")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["name"], "Our house")
        self.assertGreater(saved[0]["combined_eroi"], 0)

    def test_positions_are_scoped_to_their_user(self):
        ne.save_position("u1", "Mine", self._position())
        self.assertEqual(ne.get_positions("u2"), [])

    def test_a_nameless_position_is_refused(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.save_position("u1", "  ", self._position())

    def test_an_ownerless_position_is_refused(self):
        with self.assertRaises(ne.NetEnergyError):
            ne.save_position("", "House", self._position())

    def test_delete_removes_only_the_owner_s_row(self):
        row_id = ne.save_position("u1", "House", self._position())
        self.assertFalse(ne.delete_position("u2", row_id))
        self.assertTrue(ne.delete_position("u1", row_id))
        self.assertEqual(ne.get_positions("u1"), [])

    def test_the_boundary_survives_the_round_trip(self):
        """A saved ratio without its boundary would be meaningless."""
        ne.save_position("u1", "House", self._position())
        saved = ne.get_positions("u1")[0]
        self.assertEqual(saved["boundary"], "point_of_use")
        self.assertEqual(saved["payload"]["boundary"], "point_of_use")


if __name__ == "__main__":
    unittest.main()
