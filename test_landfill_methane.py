"""Tests for the landfill first order decay model.

The claim being tested is about timing. A flat factor books the whole emission
in the year the bin went out, and the model exists to say that most of it
arrives over the following decades. So the central tests are the ones that pin
the shape of the curve: that generation falls monotonically from a single
disposal, that the cumulative total approaches the methane potential and never
passes it, and that a diversion in year five does not deliver its benefit in
year five.

Conservation is the other half. Methane generated has to equal captured plus
oxidised plus emitted, exactly, or the site controls are doing something other
than what they say.
"""

import math
import os
import tempfile
import unittest

import landfill_methane as lm


HOUSEHOLD_MIX = {"food": 0.15, "garden": 0.10, "paper": 0.08, "cardboard": 0.05}


class TestStreamTable(unittest.TestCase):
    """The composition parameters."""

    def test_every_stream_is_usable(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                entry = lm.get_stream(stream)
                self.assertGreater(entry["doc"], 0.0)
                self.assertGreater(entry["docf"], 0.0)
                self.assertLessEqual(entry["docf"], 1.0)
                self.assertTrue(entry["note"])

    def test_degradable_carbon_spans_a_wide_range(self):
        # The reason one coefficient cannot work: before anything else is
        # considered, the streams differ by more than a factor of two in
        # carbon alone.
        values = [lm.get_stream(s)["doc"] for s in lm.list_streams()]
        self.assertGreater(max(values) / min(values), 2.0)

    def test_timber_carbon_is_mostly_unavailable(self):
        # Lignin-bound. This is the case a flat factor cannot express at all.
        self.assertLess(lm.get_stream("timber")["docf"], 0.25)

    def test_food_carbon_is_mostly_available(self):
        self.assertGreater(lm.get_stream("food")["docf"], 0.6)

    def test_unknown_stream_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.get_stream("moon rock")

    def test_every_climate_zone_covers_every_stream(self):
        for climate in lm.list_climate_zones():
            for stream in lm.list_streams():
                with self.subTest(climate=climate, stream=stream):
                    self.assertGreater(lm.decay_constant(stream, climate), 0.0)

    def test_unknown_climate_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.decay_constant("food", "mars")

    def test_wet_climates_decay_faster_than_dry_ones(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                self.assertGreater(
                    lm.decay_constant(stream, "wet_temperate"),
                    lm.decay_constant(stream, "dry_temperate"),
                )

    def test_food_decays_faster_than_timber_everywhere(self):
        for climate in lm.list_climate_zones():
            with self.subTest(climate=climate):
                self.assertGreater(
                    lm.decay_constant("food", climate),
                    lm.decay_constant("timber", climate),
                )


class TestPotential(unittest.TestCase):
    """How much methane a tonne could ever produce."""

    def test_every_stream_has_a_positive_potential(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                self.assertGreater(lm.methane_potential(stream), 0.0)

    def test_a_less_anaerobic_site_generates_less(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                self.assertLess(
                    lm.methane_potential(stream, "unmanaged_shallow"),
                    lm.methane_potential(stream, "managed_capture"),
                )

    def test_potential_follows_the_formula(self):
        entry = lm.get_stream("food")
        expected = (
            1000.0 * entry["doc"] * entry["docf"] * 1.0
            * lm.METHANE_FRACTION * lm.CH4_C_RATIO
        )
        self.assertAlmostEqual(lm.methane_potential("food"), expected, places=6)

    def test_half_lives_are_ordered_by_decay_rate(self):
        self.assertLess(
            lm.half_life_years("food"), lm.half_life_years("paper")
        )
        self.assertLess(
            lm.half_life_years("paper"), lm.half_life_years("timber")
        )

    def test_half_life_matches_the_decay_constant(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                k = lm.decay_constant(stream)
                self.assertAlmostEqual(
                    lm.half_life_years(stream), math.log(2.0) / k, places=9
                )

    def test_sequestered_carbon_is_what_never_dissimilates(self):
        entry = lm.get_stream("timber")
        self.assertAlmostEqual(
            lm.sequestered_carbon("timber"),
            1000.0 * entry["doc"] * (1.0 - entry["docf"]),
            places=6,
        )

    def test_timber_stores_more_carbon_than_food(self):
        self.assertGreater(
            lm.sequestered_carbon("timber"), lm.sequestered_carbon("food")
        )


class TestDecayProfile(unittest.TestCase):
    """The shape of a single year's disposal."""

    def test_generation_falls_every_year(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                rows = lm.decay_profile(stream, 1.0, years=40)
                # Year one is a part year because of the delay, so the
                # comparison starts at year two.
                for earlier, later in zip(rows[1:], rows[2:]):
                    self.assertLessEqual(
                        later["generated_kg"], earlier["generated_kg"] + 1e-9
                    )

    def test_the_delay_makes_year_one_a_part_year(self):
        rows = lm.decay_profile("food", 1.0, years=5, delay_months=6.0)
        immediate = lm.decay_profile("food", 1.0, years=5, delay_months=0.0)
        self.assertLess(rows[0]["generated_kg"], immediate[0]["generated_kg"])

    def test_cumulative_never_exceeds_the_potential(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                rows = lm.decay_profile(stream, 2.0, years=200)
                self.assertLessEqual(
                    rows[-1]["cumulative_kg"],
                    lm.methane_potential(stream) * 2.0 + 1e-6,
                )

    def test_cumulative_approaches_the_potential(self):
        # Given long enough, essentially all the available carbon goes.
        rows = lm.decay_profile("food", 1.0, years=200)
        self.assertGreater(
            rows[-1]["cumulative_kg"], lm.methane_potential("food") * 0.99
        )

    def test_remaining_plus_cumulative_is_the_potential(self):
        rows = lm.decay_profile("paper", 3.0, years=50)
        potential = lm.methane_potential("paper") * 3.0
        for row in rows:
            with self.subTest(year=row["year"]):
                self.assertAlmostEqual(
                    row["remaining_kg"] + row["cumulative_kg"], potential, places=3
                )

    def test_generation_scales_with_tonnage(self):
        one = lm.decay_profile("food", 1.0, years=30)[-1]["cumulative_kg"]
        three = lm.decay_profile("food", 3.0, years=30)[-1]["cumulative_kg"]
        self.assertAlmostEqual(three, one * 3.0, places=4)

    def test_zero_tonnage_generates_nothing(self):
        rows = lm.decay_profile("food", 0.0, years=10)
        self.assertEqual(sum(row["generated_kg"] for row in rows), 0.0)

    def test_negative_tonnage_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.decay_profile("food", -1.0)

    def test_a_zero_year_horizon_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.decay_profile("food", 1.0, years=0)

    def test_an_impossible_delay_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.decay_profile("food", 1.0, delay_months=18.0)


class TestSiteControls(unittest.TestCase):
    """Capture and oxidation, and that they conserve mass."""

    def test_the_parts_sum_to_what_was_generated(self):
        for site in lm.list_sites():
            with self.subTest(site=site):
                split = lm.site_emissions(1000.0, site=site)
                self.assertAlmostEqual(
                    split["captured_kg"] + split["oxidised_kg"]
                    + split["emitted_kg"],
                    split["generated_kg"],
                    places=6,
                )

    def test_oxidation_applies_only_to_what_escapes(self):
        # Applying it to the gross would count the captured gas twice.
        split = lm.site_emissions(1000.0, capture=0.5, oxidation=0.1)
        self.assertAlmostEqual(split["oxidised_kg"], 50.0, places=6)
        self.assertAlmostEqual(split["emitted_kg"], 450.0, places=6)

    def test_full_capture_emits_nothing(self):
        split = lm.site_emissions(1000.0, capture=1.0)
        self.assertAlmostEqual(split["emitted_kg"], 0.0, places=9)

    def test_no_capture_and_no_oxidation_emits_everything(self):
        split = lm.site_emissions(1000.0, capture=0.0, oxidation=0.0)
        self.assertAlmostEqual(split["emitted_kg"], 1000.0, places=9)

    def test_more_capture_emits_less(self):
        values = [
            lm.site_emissions(1000.0, capture=capture)["emitted_kg"]
            for capture in (0.0, 0.3, 0.6, 0.9)
        ]
        for earlier, later in zip(values, values[1:]):
            self.assertLess(later, earlier)

    def test_an_impossible_capture_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.site_emissions(100.0, capture=1.4)

    def test_an_impossible_oxidation_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.site_emissions(100.0, oxidation=-0.2)

    def test_site_choice_spans_a_large_range(self):
        # The factor the current model cannot express at all: a factor of three
        # across the shipped archetypes, on waste that is identical.
        totals = {
            site: lm.landfill_series(
                {1: {"food": 1.0}}, site=site, years=100
            )[-1]["cumulative_emitted_kg"]
            for site in lm.list_sites()
        }
        self.assertGreater(max(totals.values()) / min(totals.values()), 3.0)


class TestSeries(unittest.TestCase):
    """Many years of disposal superposed."""

    def test_a_single_disposal_matches_its_own_profile(self):
        series = lm.landfill_series({1: {"food": 1.0}}, years=30)
        profile = lm.decay_profile("food", 1.0, years=30)
        for row, expected in zip(series, profile):
            with self.subTest(year=row["year"]):
                self.assertAlmostEqual(
                    row["generated_kg"], expected["generated_kg"], places=4
                )

    def test_a_steady_stream_builds_to_a_plateau(self):
        # Each year's waste starts its own curve, so the total climbs and then
        # levels off as old waste finishes decaying.
        series = lm.landfill_series(
            {year: dict(HOUSEHOLD_MIX) for year in range(1, 81)}, years=80
        )
        early = series[4]["emitted_kg"]
        middle = series[39]["emitted_kg"]
        late = series[79]["emitted_kg"]
        self.assertGreater(middle, early)
        self.assertLess(abs(late - middle) / middle, 0.25)

    def test_two_disposals_superpose(self):
        one = lm.landfill_series({1: {"food": 1.0}}, years=40)
        two = lm.landfill_series({1: {"food": 1.0}, 5: {"food": 1.0}}, years=40)
        self.assertGreater(
            two[-1]["cumulative_emitted_kg"], one[-1]["cumulative_emitted_kg"]
        )

    def test_cumulative_emissions_never_fall(self):
        series = lm.landfill_series({1: {"food": 1.0}}, years=50)
        for earlier, later in zip(series, series[1:]):
            self.assertGreaterEqual(
                later["cumulative_emitted_kg"], earlier["cumulative_emitted_kg"]
            )

    def test_co2e_uses_the_biogenic_methane_gwp(self):
        row = lm.landfill_series({1: {"food": 1.0}}, years=10)[3]
        self.assertAlmostEqual(
            row["emitted_co2e"], row["emitted_kg"] * lm.METHANE_GWP_100, places=2
        )

    def test_an_empty_schedule_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.landfill_series({})

    def test_a_zero_disposal_year_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.landfill_series({0: {"food": 1.0}})

    def test_the_bare_methane_series_matches_the_full_one(self):
        full = lm.landfill_series({1: {"food": 1.0}}, years=25)
        bare = lm.methane_series({1: {"food": 1.0}}, years=25)
        self.assertEqual(len(bare), len(full))
        for row, value in zip(full, bare):
            self.assertAlmostEqual(row["emitted_kg"], value, places=6)

    def test_the_methane_series_is_not_constant(self):
        # The point of exposing it: GWP* has nothing to say about a flat rate,
        # and a flat factor produces exactly that.
        series = lm.methane_series({1: {"food": 1.0}}, years=25)
        self.assertGreater(max(series) / max(min(series), 1e-9), 2.0)


class TestFlatFactorComparison(unittest.TestCase):
    """What the current constant gets wrong."""

    def test_the_constant_exceeds_the_physical_ceiling(self):
        # 0.5 kg of methane per kg of waste is more methane than the carbon in
        # the waste could produce even with nothing captured.
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                result = lm.compare_to_flat_factor(stream, 1.0)
                self.assertTrue(result["exceeds_physical_ceiling"])

    def test_a_plausible_factor_is_not_flagged(self):
        result = lm.compare_to_flat_factor("food", 1.0, flat_factor=0.01)
        self.assertFalse(result["exceeds_physical_ceiling"])

    def test_the_first_year_is_wildly_overstated(self):
        result = lm.compare_to_flat_factor("food", 1.0)
        self.assertGreater(result["first_year_ratio"], 50.0)

    def test_most_of_the_emission_is_not_in_the_first_year(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                result = lm.compare_to_flat_factor(stream, 1.0)
                self.assertLess(
                    result["first_year_kg"], result["modelled_total_kg"] * 0.3
                )

    def test_slow_streams_take_longer_to_reach_half(self):
        food = lm.compare_to_flat_factor("food", 1.0)
        timber = lm.compare_to_flat_factor("timber", 1.0)
        self.assertLess(food["years_to_half"], timber["years_to_half"])

    def test_ninety_percent_comes_after_half(self):
        for stream in lm.list_streams():
            with self.subTest(stream=stream):
                result = lm.compare_to_flat_factor(stream, 1.0)
                self.assertGreaterEqual(
                    result["years_to_ninety"], result["years_to_half"]
                )

    def test_insights_are_produced(self):
        insights = lm.get_landfill_insights(lm.compare_to_flat_factor("food", 1.0))
        self.assertTrue(insights)
        for line in insights:
            self.assertIsInstance(line, str)

    def test_an_empty_comparison_says_so(self):
        self.assertEqual(lm.get_landfill_insights({}), ["Nothing to analyse."])


class TestRoutes(unittest.TestCase):
    """Comparing treatments with the credit kept visible."""

    def test_gross_and_avoided_are_never_merged(self):
        for route in lm.list_routes():
            with self.subTest(route=route):
                result = lm.route_emissions(route, "food", 1.0)
                self.assertAlmostEqual(
                    result["net_co2e"],
                    result["gross_co2e"] - result["avoided_co2e"],
                    places=2,
                )
                self.assertGreaterEqual(result["gross_co2e"], 0.0)

    def test_only_landfill_produces_methane(self):
        for route in lm.list_routes():
            with self.subTest(route=route):
                result = lm.route_emissions(route, "food", 1.0)
                if route == "landfill":
                    self.assertGreater(result["methane_kg"], 0.0)
                else:
                    self.assertEqual(result["methane_kg"], 0.0)

    def test_only_landfill_stores_carbon(self):
        self.assertGreater(
            lm.route_emissions("landfill", "timber", 1.0)["sequestered_carbon_kg"],
            0.0,
        )
        self.assertEqual(
            lm.route_emissions("compost", "timber", 1.0)["sequestered_carbon_kg"],
            0.0,
        )

    def test_landfill_is_the_worst_route_for_food(self):
        rows = lm.compare_routes("food", 1.0)
        self.assertEqual(rows[-1]["route"], "landfill")

    def test_routes_are_ordered_by_net(self):
        rows = lm.compare_routes("food", 1.0)
        for earlier, later in zip(rows, rows[1:]):
            self.assertLessEqual(earlier["net_co2e"], later["net_co2e"])

    def test_a_dirtier_grid_makes_the_energy_credit_bigger(self):
        clean = lm.route_emissions(
            "incineration", "food", 1.0, grid_intensity=0.05
        )["avoided_co2e"]
        dirty = lm.route_emissions(
            "incineration", "food", 1.0, grid_intensity=0.8
        )["avoided_co2e"]
        self.assertGreater(dirty, clean)

    def test_the_credit_is_where_the_grid_assumption_lives(self):
        # Gross is untouched by the grid; only the credit moves. That is the
        # separation the netting would destroy.
        clean = lm.route_emissions("incineration", "food", 1.0, grid_intensity=0.05)
        dirty = lm.route_emissions("incineration", "food", 1.0, grid_intensity=0.8)
        self.assertAlmostEqual(clean["gross_co2e"], dirty["gross_co2e"], places=6)

    def test_landfill_has_no_energy_credit(self):
        self.assertEqual(
            lm.route_emissions("landfill", "food", 1.0)["avoided_power_co2e"], 0.0
        )

    def test_an_unknown_route_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.route_emissions("catapult", "food", 1.0)

    def test_negative_tonnage_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.route_emissions("compost", "food", -1.0)


class TestDiversion(unittest.TestCase):
    """The output the flat factor gets wrong, in the flattering direction."""

    def setUp(self):
        self.result = lm.diversion_scenario(
            HOUSEHOLD_MIX, change_year=5, diverted_share=1.0, years=80
        )

    def test_nothing_is_saved_before_the_change(self):
        for row in self.result["rows"][:4]:
            with self.subTest(year=row["year"]):
                self.assertAlmostEqual(row["saved_kg"], 0.0, places=6)

    def test_the_first_year_saving_is_far_below_the_eventual_one(self):
        # The whole point. Stopping today does not stop the emissions today,
        # because the site is still working through what is already buried.
        self.assertLess(
            self.result["first_year_saving_kg"],
            self.result["steady_saving_kg"] * 0.2,
        )

    def test_the_instant_model_overstates_the_first_year(self):
        self.assertGreater(
            self.result["instant_model_claim_kg"],
            self.result["first_year_saving_kg"],
        )

    def test_the_benefit_takes_years_to_arrive(self):
        self.assertIsNotNone(self.result["years_to_ninety_percent_effect"])
        self.assertGreater(self.result["years_to_ninety_percent_effect"], 5)

    def test_savings_never_go_backwards_after_the_change(self):
        rows = self.result["rows"][4:]
        for earlier, later in zip(rows, rows[1:]):
            self.assertGreaterEqual(later["saved_kg"], earlier["saved_kg"] - 1e-6)

    def test_diverting_nothing_saves_nothing(self):
        result = lm.diversion_scenario(HOUSEHOLD_MIX, 5, 0.0, years=40)
        self.assertAlmostEqual(result["total_saved_kg"], 0.0, places=4)

    def test_diverting_more_saves_more(self):
        totals = [
            lm.diversion_scenario(HOUSEHOLD_MIX, 5, share, years=60)["total_saved_kg"]
            for share in (0.25, 0.5, 0.75, 1.0)
        ]
        for earlier, later in zip(totals, totals[1:]):
            self.assertGreater(later, earlier)

    def test_acting_sooner_saves_more(self):
        early = lm.diversion_scenario(HOUSEHOLD_MIX, 2, 1.0, years=60)
        late = lm.diversion_scenario(HOUSEHOLD_MIX, 20, 1.0, years=60)
        self.assertGreater(early["total_saved_kg"], late["total_saved_kg"])

    def test_an_empty_mix_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.diversion_scenario({}, 5, 1.0)

    def test_a_change_after_the_horizon_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.diversion_scenario(HOUSEHOLD_MIX, 200, 1.0, years=50)

    def test_an_impossible_share_is_refused(self):
        with self.assertRaises(lm.LandfillError):
            lm.diversion_scenario(HOUSEHOLD_MIX, 5, 1.5)


class TestSensitivity(unittest.TestCase):
    """The parameters that move the answer."""

    def test_all_four_parameters_appear(self):
        parameters = {row["parameter"] for row in lm.sensitivity("food", 1.0)}
        self.assertEqual(
            parameters,
            {"Climate", "Site", "Gas capture", "Accounting horizon"},
        )

    def test_every_row_is_reported(self):
        for row in lm.sensitivity("food", 1.0):
            with self.subTest(setting=row["setting"]):
                self.assertGreaterEqual(row["total_kg"], 0.0)
                self.assertTrue(row["setting"])

    def test_capture_dominates_the_spread(self):
        rows = [
            row for row in lm.sensitivity("food", 1.0)
            if row["parameter"] == "Gas capture"
        ]
        values = [row["total_kg"] for row in rows]
        self.assertGreater(max(values) / max(min(values), 1e-9), 5.0)

    def test_a_shorter_horizon_reports_less(self):
        rows = {
            row["setting"]: row["total_kg"]
            for row in lm.sensitivity("food", 1.0)
            if row["parameter"] == "Accounting horizon"
        }
        self.assertLess(rows["20 years"], rows["100 years"])


class TestStorage(unittest.TestCase):
    """Persistence, against a throwaway database."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = lm.DB_NAME
        lm.DB_NAME = self.path
        lm.init_landfill_db()
        series = lm.landfill_series({1: dict(HOUSEHOLD_MIX)}, years=60)
        self.result = {
            "total_emitted_kg": series[-1]["cumulative_emitted_kg"],
            "rows": series,
        }

    def tearDown(self):
        lm.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_init_is_idempotent(self):
        self.assertTrue(lm.init_landfill_db())
        self.assertTrue(lm.init_landfill_db())

    def test_a_saved_profile_comes_back(self):
        profile_id = lm.save_profile(1, "Our bin", HOUSEHOLD_MIX, self.result)
        self.assertIsNotNone(profile_id)
        profiles = lm.get_profiles(1)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["name"], "Our bin")

    def test_co2e_is_stored_alongside_the_methane(self):
        lm.save_profile(1, "Our bin", HOUSEHOLD_MIX, self.result)
        stored = lm.get_profiles(1)[0]
        self.assertAlmostEqual(
            stored["methane_co2e"],
            stored["methane_kg"] * lm.METHANE_GWP_100,
            places=3,
        )

    def test_the_mix_survives_the_round_trip(self):
        lm.save_profile(1, "Our bin", HOUSEHOLD_MIX, self.result)
        stored = lm.get_profiles(1)[0]["detail"]
        self.assertEqual(stored["mix"], HOUSEHOLD_MIX)

    def test_profiles_are_newest_first(self):
        for name in ("first", "second", "third"):
            lm.save_profile(1, name, HOUSEHOLD_MIX, self.result)
        self.assertEqual(lm.get_profiles(1)[0]["name"], "third")

    def test_users_do_not_see_each_other(self):
        lm.save_profile(1, "mine", HOUSEHOLD_MIX, self.result)
        lm.save_profile(2, "theirs", HOUSEHOLD_MIX, self.result)
        self.assertEqual(len(lm.get_profiles(1)), 1)

    def test_delete_removes_it(self):
        profile_id = lm.save_profile(1, "gone", HOUSEHOLD_MIX, self.result)
        self.assertTrue(lm.delete_profile(profile_id, 1))
        self.assertEqual(lm.get_profiles(1), [])

    def test_you_cannot_delete_someone_elses(self):
        profile_id = lm.save_profile(1, "mine", HOUSEHOLD_MIX, self.result)
        self.assertFalse(lm.delete_profile(profile_id, 2))

    def test_the_limit_is_respected(self):
        for n in range(5):
            lm.save_profile(1, f"p{n}", HOUSEHOLD_MIX, self.result)
        self.assertEqual(len(lm.get_profiles(1, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()
