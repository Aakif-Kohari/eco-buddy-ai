"""Tests for the surface albedo radiative forcing engine.

This module converts a reflectivity change into tonnes of CO2, and the headline
figure - roughly six tonnes for a hundred square metres of white roof - is large
enough that the derivation has to be checkable rather than merely plausible. So
the tests guard the steps, not just the answer:

*   surface forcing, top-of-atmosphere forcing, globalisation by area and CO2
    equivalence are each verified on their own before any composite result is;
*   the CO2 equivalence rises with the time horizon, because a sustained forcing
    integrates linearly while a CO2 pulse decays - that asymmetry is the whole
    reason the horizon is a required argument;
*   the same intervention returns two to three times as much in the subtropics
    as at sixty degrees north, which is why no single coefficient is published;
*   soiling pulls a cool roof's effective albedo well below its datasheet value;
*   high-latitude conifer planting comes out net warming, and the module says so.

The canopy test is the load-bearing one. A module that could only ever recommend
tree planting would not be measuring anything, and the boreal crossover is the
result most likely to be silently lost to an over-generous growth assumption.
"""

import math
import os
import tempfile
import unittest

import albedo_forcing as af


class TestSurfaceTable(unittest.TestCase):

    def test_every_albedo_is_physical(self):
        for key in af.list_surfaces():
            with self.subTest(surface=key):
                spec = af.get_surface(key)
                self.assertGreater(spec["albedo"], 0.0)
                self.assertLess(spec["albedo"], 1.0)
                self.assertGreater(spec["aged_albedo"], 0.0)
                self.assertLess(spec["aged_albedo"], 1.0)

    def test_every_surface_explains_itself(self):
        for key in af.list_surfaces():
            self.assertGreater(len(af.get_surface(key)["note"]), 40)

    def test_snow_is_the_brightest_surface_in_the_table(self):
        brightest = max(af.list_surfaces(), key=lambda k: af.SURFACES[k]["albedo"])
        self.assertEqual(brightest, "fresh_snow")

    def test_solar_panels_are_among_the_darkest(self):
        """A panel that reflected light would not work, and that has a cost."""
        self.assertLess(af.get_surface("solar_pv")["albedo"], 0.10)

    def test_unknown_surface_is_rejected_with_a_useful_message(self):
        with self.assertRaises(af.AlbedoError) as caught:
            af.get_surface("mirror")
        self.assertIn("cool_white_roof", str(caught.exception))

    def test_families_partition_the_table(self):
        covered = []
        for family in af.list_surface_families():
            covered.extend(af.list_surfaces(family))
        self.assertCountEqual(covered, af.list_surfaces())


class TestLatitudeBands(unittest.TestCase):

    def test_insolation_falls_towards_the_poles(self):
        """Not monotonic at the equator: the subtropical dry belt gets more sun."""
        bands = af.list_latitude_bands()
        polar_half = bands[3:]
        values = [af.get_latitude_band(b)["insolation_w_m2"] for b in polar_half]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_the_brightest_band_is_the_dry_subtropics_not_the_equator(self):
        """High sun and thin cloud together, which the equator does not have."""
        brightest = max(
            af.list_latitude_bands(),
            key=lambda b: af.get_latitude_band(b)["insolation_w_m2"],
        )
        self.assertEqual(brightest, "tropical")

    def test_snow_fraction_rises_towards_the_poles(self):
        values = [
            af.get_latitude_band(b)["snow_fraction"]
            for b in af.list_latitude_bands()
        ]
        self.assertEqual(values, sorted(values))

    def test_every_band_has_a_forest_carbon_stock(self):
        for band in af.list_latitude_bands():
            self.assertIn(band, af.FOREST_CARBON_STOCK)

    def test_forest_stock_falls_towards_the_poles(self):
        values = [
            af.FOREST_CARBON_STOCK[b]["asymptote_t_co2_ha"]
            for b in af.list_latitude_bands()
        ]
        self.assertEqual(values, sorted(values, reverse=True))


class TestTransmittance(unittest.TestCase):

    def test_cloud_swallows_most_of_a_reflection(self):
        clear = af.upward_transmittance(0.0)
        overcast = af.upward_transmittance(1.0)
        self.assertGreater(clear, 0.7)
        self.assertLess(overcast, 0.2)

    def test_transmittance_is_monotonic_in_cloud(self):
        values = [af.upward_transmittance(c / 10) for c in range(11)]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_a_reflection_never_more_than_fully_escapes(self):
        for cloud in (0.0, 0.3, 0.6, 1.0):
            self.assertLessEqual(af.upward_transmittance(cloud), 1.0)

    def test_impossible_cloud_fraction_is_rejected(self):
        with self.assertRaises(af.AlbedoError):
            af.upward_transmittance(1.4)


class TestForcingSteps(unittest.TestCase):
    """Each step of the derivation checked on its own."""

    def test_brightening_gives_a_negative_forcing(self):
        forcing = af.local_radiative_forcing(0.5, "temperate")
        self.assertLess(forcing, 0.0)

    def test_darkening_gives_a_positive_forcing(self):
        forcing = af.local_radiative_forcing(-0.5, "temperate")
        self.assertGreater(forcing, 0.0)

    def test_forcing_is_linear_in_the_albedo_change(self):
        one = af.local_radiative_forcing(0.1, "temperate")
        two = af.local_radiative_forcing(0.2, "temperate")
        self.assertAlmostEqual(two, one * 2, places=9)

    def test_forcing_matches_the_stated_formula(self):
        band = af.get_latitude_band("temperate")
        expected = -(
            band["insolation_w_m2"] * 0.4
            * af.upward_transmittance(band["cloud_fraction"])
        )
        self.assertAlmostEqual(
            af.local_radiative_forcing(0.4, "temperate"), expected, places=9
        )

    def test_globalising_divides_by_the_area_of_the_earth(self):
        self.assertAlmostEqual(
            af.globalise(10.0, af.EARTH_SURFACE_AREA_M2), 10.0, places=9
        )

    def test_globalising_is_linear_in_area(self):
        self.assertAlmostEqual(
            af.globalise(5.0, 200.0), af.globalise(5.0, 100.0) * 2, places=15
        )

    def test_zero_area_is_rejected(self):
        with self.assertRaises(af.AlbedoError):
            af.globalise(5.0, 0.0)

    def test_absurd_albedo_change_is_rejected(self):
        with self.assertRaises(af.AlbedoError):
            af.local_radiative_forcing(1.5, "temperate")


class TestCo2Equivalence(unittest.TestCase):

    def test_a_cooling_forcing_converts_to_an_offset(self):
        self.assertLess(af.co2_equivalent(-1e-11, 100), 0.0)

    def test_the_equivalent_mass_grows_with_the_horizon(self):
        """A sustained forcing integrates linearly; a CO2 pulse decays.

        This asymmetry is the reason the horizon cannot be hidden inside a
        coefficient, and it is the single most misused property of the metric.
        """
        masses = [
            abs(af.co2_equivalent(-1e-11, horizon))
            for horizon in (20, 50, 100, 500)
        ]
        self.assertEqual(masses, sorted(masses))

    def test_agwp_is_interpolated_between_tabulated_horizons(self):
        value = af.agwp_co2(75)
        self.assertGreater(value, af.AGWP_CO2_W_M2_YR_PER_KG[50])
        self.assertLess(value, af.AGWP_CO2_W_M2_YR_PER_KG[100])

    def test_agwp_is_exact_at_tabulated_horizons(self):
        for horizon, expected in af.AGWP_CO2_W_M2_YR_PER_KG.items():
            self.assertEqual(af.agwp_co2(horizon), expected)

    def test_the_carbon_cycle_response_is_sublinear(self):
        """Which is exactly why the horizon changes the answer."""
        per_year_20 = af.AGWP_CO2_W_M2_YR_PER_KG[20] / 20
        per_year_100 = af.AGWP_CO2_W_M2_YR_PER_KG[100] / 100
        self.assertLess(per_year_100, per_year_20)

    def test_an_untabulated_horizon_is_refused_rather_than_extrapolated(self):
        with self.assertRaises(af.AlbedoError):
            af.agwp_co2(2000)

    def test_a_negative_horizon_is_rejected(self):
        with self.assertRaises(af.AlbedoError):
            af.co2_equivalent(-1e-11, -10)


class TestSoiling(unittest.TestCase):

    def test_a_cool_roof_loses_a_meaningful_share_of_its_datasheet_value(self):
        result = af.effective_albedo("cool_white_roof", 100)
        self.assertLess(result["effective_albedo"], result["initial_albedo"])
        self.assertLess(result["fraction_of_nameplate"], 0.85)

    def test_the_effective_value_stays_above_the_fully_aged_one(self):
        result = af.effective_albedo("cool_white_roof", 100)
        self.assertGreater(result["effective_albedo"], result["aged_albedo"])

    def test_recoating_recovers_part_of_the_loss(self):
        never = af.effective_albedo("cool_white_roof", 100)
        recoated = af.effective_albedo("cool_white_roof", 100, 5)
        self.assertGreater(
            recoated["effective_albedo"], never["effective_albedo"]
        )

    def test_more_frequent_recoating_recovers_more(self):
        rare = af.effective_albedo("cool_white_roof", 100, 20)
        often = af.effective_albedo("cool_white_roof", 100, 3)
        self.assertGreater(often["effective_albedo"], rare["effective_albedo"])

    def test_a_surface_that_does_not_soil_keeps_its_value(self):
        result = af.effective_albedo("solar_pv", 100)
        self.assertFalse(result["soils"])
        self.assertEqual(
            result["effective_albedo"], af.get_surface("solar_pv")["albedo"]
        )

    def test_asphalt_gets_lighter_with_age_rather_than_darker(self):
        """Unusual, and the model has to allow the decay to run either way."""
        spec = af.get_surface("asphalt_new")
        self.assertGreater(spec["aged_albedo"], spec["albedo"])
        result = af.effective_albedo("asphalt_new", 30)
        self.assertGreater(result["effective_albedo"], spec["albedo"])


class TestSurfaceChange(unittest.TestCase):

    def test_a_white_roof_is_an_offset_of_a_credible_size(self):
        """Order of magnitude, not a fitted value.

        A hundred square metres taken from a dark membrane to cool white at
        mid-latitude should land in single-figure tonnes over a century. Much
        less and the module is not worth having; much more and it is wrong.
        """
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        self.assertTrue(result["is_offset"])
        tonnes = abs(result["co2_equivalent_kg"]) / 1000
        self.assertGreater(tonnes, 2.0)
        self.assertLess(tonnes, 20.0)

    def test_the_same_roof_is_worth_far_more_in_the_subtropics(self):
        warm = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "tropical"
        )
        cold = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "boreal"
        )
        self.assertGreater(
            abs(warm["co2_equivalent_kg"]), abs(cold["co2_equivalent_kg"]) * 2
        )

    def test_darkening_a_surface_reports_an_emission(self):
        result = af.surface_change(
            "cool_white_roof", "solar_pv", 100, "temperate"
        )
        self.assertFalse(result["is_offset"])
        self.assertGreater(result["co2_equivalent_kg"], 0.0)

    def test_the_result_scales_with_area(self):
        small = af.surface_change("dark_roof", "cool_white_roof", 50, "temperate")
        large = af.surface_change("dark_roof", "cool_white_roof", 200, "temperate")
        self.assertAlmostEqual(
            large["co2_equivalent_kg"], small["co2_equivalent_kg"] * 4, places=6
        )

    def test_per_square_metre_is_independent_of_area(self):
        small = af.surface_change("dark_roof", "cool_white_roof", 50, "temperate")
        large = af.surface_change("dark_roof", "cool_white_roof", 500, "temperate")
        self.assertAlmostEqual(
            small["co2_equivalent_kg_per_m2"],
            large["co2_equivalent_kg_per_m2"],
            places=9,
        )

    def test_soiling_reduces_the_claim(self):
        with_soiling = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate", apply_soiling=True
        )
        nameplate = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate", apply_soiling=False
        )
        self.assertLess(
            abs(with_soiling["co2_equivalent_kg"]),
            abs(nameplate["co2_equivalent_kg"]),
        )

    def test_clear_skies_make_the_intervention_worth_more(self):
        clear = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate", cloud_fraction=0.0
        )
        cloudy = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate", cloud_fraction=1.0
        )
        self.assertGreater(
            abs(clear["co2_equivalent_kg"]), abs(cloudy["co2_equivalent_kg"]) * 3
        )

    def test_the_derivation_is_reproducible_from_the_reported_steps(self):
        """The intermediate values must actually compose into the headline."""
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        rebuilt_local = -(
            result["insolation_w_m2"]
            * result["delta_albedo"]
            * result["upward_transmittance"]
        )
        self.assertAlmostEqual(rebuilt_local, result["local_forcing_w_m2"], places=9)
        rebuilt_global = (
            rebuilt_local * result["area_m2"] / af.EARTH_SURFACE_AREA_M2
        )
        self.assertAlmostEqual(
            rebuilt_global, result["global_forcing_w_m2"], places=18
        )
        rebuilt_co2 = (
            rebuilt_global * result["horizon_years"]
            / af.agwp_co2(result["horizon_years"])
        )
        self.assertAlmostEqual(rebuilt_co2, result["co2_equivalent_kg"], places=6)

    def test_zero_area_is_rejected(self):
        with self.assertRaises(af.AlbedoError):
            af.surface_change("dark_roof", "cool_white_roof", 0, "temperate")

    def test_unknown_latitude_band_is_rejected(self):
        with self.assertRaises(af.AlbedoError):
            af.surface_change("dark_roof", "cool_white_roof", 10, "antarctic")


class TestSensitivity(unittest.TestCase):

    def test_horizon_sensitivity_spans_a_wide_range(self):
        rows = af.horizon_sensitivity(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        masses = [abs(row["co2_equivalent_kg"]) for row in rows]
        self.assertGreater(max(masses) / min(masses), 1.5)

    def test_latitude_sensitivity_covers_every_band(self):
        rows = af.latitude_sensitivity("dark_roof", "cool_white_roof", 100)
        self.assertEqual(len(rows), len(af.list_latitude_bands()))

    def test_latitude_sensitivity_tracks_insolation(self):
        rows = af.latitude_sensitivity("dark_roof", "cool_white_roof", 100)
        best = max(rows, key=lambda r: abs(r["co2_equivalent_kg"]))
        worst = min(rows, key=lambda r: abs(r["co2_equivalent_kg"]))
        self.assertGreater(best["insolation_w_m2"], worst["insolation_w_m2"])


class TestSequestrationStock(unittest.TestCase):

    def test_growth_saturates_rather_than_continuing_forever(self):
        fifty = af.sequestration_stock("temperate", 50, "conifer_forest")
        hundred = af.sequestration_stock("temperate", 100, "conifer_forest")
        self.assertLess(
            hundred["accumulated_t_co2_ha"],
            fifty["accumulated_t_co2_ha"] * 2,
        )

    def test_stock_never_exceeds_its_asymptote(self):
        result = af.sequestration_stock("temperate", 1000, "conifer_forest")
        self.assertLessEqual(
            result["accumulated_t_co2_ha"], result["asymptote_t_co2_ha"]
        )

    def test_mean_rate_falls_as_the_stand_matures(self):
        early = af.sequestration_stock("temperate", 20, "conifer_forest")
        late = af.sequestration_stock("temperate", 120, "conifer_forest")
        self.assertGreater(
            early["mean_rate_t_co2_ha_yr"], late["mean_rate_t_co2_ha_yr"]
        )

    def test_boreal_stands_hold_far_less_than_tropical_ones(self):
        boreal = af.sequestration_stock("boreal", 100, "conifer_forest")
        tropical = af.sequestration_stock("tropical", 100, "conifer_forest")
        self.assertGreater(
            tropical["accumulated_t_co2_ha"],
            boreal["accumulated_t_co2_ha"] * 3,
        )

    def test_nothing_has_grown_at_time_zero(self):
        self.assertAlmostEqual(
            af.sequestration_stock("temperate", 0, "conifer_forest")[
                "accumulated_t_co2_ha"
            ],
            0.0,
            places=9,
        )


class TestCanopy(unittest.TestCase):
    """The result the rest of the app cannot currently produce."""

    def test_planting_pays_in_the_tropics(self):
        result = af.canopy_albedo_penalty("conifer_forest", 10000, "tropical")
        self.assertTrue(result["planting_is_net_beneficial"])

    def test_high_latitude_conifer_planting_comes_out_net_warming(self):
        """The load-bearing test.

        A conifer stand over seasonal snow replaces a surface reflecting about
        0.72 with one reflecting about 0.21 for half the year, and boreal
        forests hold little carbon. Above some latitude the darkening wins, and
        a module that cannot return that answer is not measuring anything.
        """
        result = af.canopy_albedo_penalty("conifer_forest", 10000, "arctic")
        self.assertFalse(result["planting_is_net_beneficial"])
        self.assertGreater(result["net_co2_kg"], 0.0)

    def test_the_albedo_penalty_grows_with_snow_cover(self):
        temperate = af.canopy_albedo_penalty(
            "conifer_forest", 10000, "temperate"
        )
        boreal = af.canopy_albedo_penalty("conifer_forest", 10000, "boreal")
        self.assertGreater(boreal["snow_fraction"], temperate["snow_fraction"])
        self.assertGreater(
            abs(boreal["delta_albedo"]), abs(temperate["delta_albedo"])
        )
        self.assertGreater(
            boreal["albedo_co2_kg"] / abs(boreal["sequestration_co2_kg"]),
            temperate["albedo_co2_kg"] / abs(temperate["sequestration_co2_kg"]),
        )

    def test_deciduous_masks_snow_less_completely_than_conifer(self):
        conifer = af.canopy_albedo_penalty("conifer_forest", 10000, "boreal")
        deciduous = af.canopy_albedo_penalty("deciduous_forest", 10000, "boreal")
        self.assertLess(
            deciduous["albedo_co2_kg"], conifer["albedo_co2_kg"]
        )

    def test_crossover_finds_a_band_for_conifer(self):
        crossover = af.canopy_crossover("conifer_forest")
        self.assertIsNotNone(crossover["crossover_band"])
        self.assertGreaterEqual(crossover["crossover_latitude"], 50)

    def test_deciduous_holds_on_to_a_higher_latitude_than_conifer(self):
        conifer = af.canopy_crossover("conifer_forest")
        deciduous = af.canopy_crossover("deciduous_forest")
        self.assertGreater(
            deciduous["crossover_latitude"], conifer["crossover_latitude"]
        )

    def test_bands_below_the_crossover_are_all_beneficial(self):
        crossover = af.canopy_crossover("conifer_forest")
        cutoff = crossover["crossover_latitude"]
        for row in crossover["bands"]:
            if row["centre_latitude"] < cutoff:
                self.assertTrue(row["beneficial"], row["latitude_band"])

    def test_an_unmodelled_species_is_refused(self):
        with self.assertRaises(af.AlbedoError):
            af.canopy_albedo_penalty("grassland", 10000, "temperate")


class TestSolarPanels(unittest.TestCase):

    def test_generation_dominates_the_albedo_penalty(self):
        result = af.solar_panel_net(30, "temperate", 150, 0.25)
        self.assertLess(result["net_co2_kg"], 0.0)
        self.assertLess(result["albedo_penalty_share"], 0.15)

    def test_the_albedo_penalty_is_present_rather_than_dropped(self):
        """Small is not the same as zero, and it is normally reported as zero."""
        result = af.solar_panel_net(30, "temperate", 150, 0.25)
        self.assertGreater(result["albedo_co2_kg"], 0.0)

    def test_a_clean_grid_leaves_less_to_displace(self):
        dirty = af.solar_panel_net(30, "temperate", 150, 0.45)
        clean = af.solar_panel_net(30, "temperate", 150, 0.05)
        self.assertGreater(
            clean["albedo_penalty_share"], dirty["albedo_penalty_share"]
        )

    def test_covering_a_white_roof_costs_more_than_covering_a_dark_one(self):
        over_white = af.solar_panel_net(
            30, "temperate", 150, 0.25, replaced_surface="cool_white_roof"
        )
        over_dark = af.solar_panel_net(
            30, "temperate", 150, 0.25, replaced_surface="dark_roof"
        )
        self.assertGreater(
            over_white["albedo_co2_kg"], over_dark["albedo_co2_kg"]
        )

    def test_negative_yield_is_rejected(self):
        with self.assertRaises(af.AlbedoError):
            af.solar_panel_net(30, "temperate", -10, 0.25)


class TestLocalVersusGlobal(unittest.TestCase):

    def test_the_two_effects_are_never_declared_comparable(self):
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        split = af.local_versus_global(result)
        self.assertFalse(split["comparable"])

    def test_an_evaporative_surface_is_flagged_as_local_only(self):
        result = af.surface_change("grey_roof", "green_roof", 100, "temperate")
        split = af.local_versus_global(result)
        self.assertEqual(split["local_mechanism"], "evaporative")

    def test_a_green_roof_over_grey_is_a_small_global_penalty(self):
        """Not an argument against green roofs, but it should not be hidden."""
        result = af.surface_change("grey_roof", "green_roof", 100, "temperate")
        self.assertGreater(result["co2_equivalent_kg"], 0.0)


class TestAbatementCost(unittest.TestCase):

    def test_a_cost_per_tonne_is_produced_for_a_real_abatement(self):
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        cost = af.abatement_cost(result, cost_per_m2=12.0)
        self.assertTrue(cost["is_abatement"])
        self.assertGreater(cost["cost_per_tonne"], 0.0)

    def test_no_cost_per_tonne_is_offered_for_a_net_warming_change(self):
        result = af.surface_change(
            "cool_white_roof", "dark_roof", 100, "temperate"
        )
        cost = af.abatement_cost(result, cost_per_m2=12.0)
        self.assertFalse(cost["is_abatement"])
        self.assertIsNone(cost["cost_per_tonne"])

    def test_recoating_adds_capital_over_the_horizon(self):
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        once = af.abatement_cost(result, cost_per_m2=12.0)
        repeated = af.abatement_cost(
            result, cost_per_m2=12.0, recoat_interval_years=20
        )
        self.assertGreater(repeated["capital_cost"], once["capital_cost"])

    def test_cool_roofs_are_cheap_against_typical_abatement_measures(self):
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "subtropical"
        )
        cost = af.abatement_cost(result, cost_per_m2=12.0)
        self.assertLess(cost["cost_per_tonne"], 500.0)


class TestInsights(unittest.TestCase):

    def test_insights_are_produced_and_are_sentences(self):
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        insights = af.get_albedo_insights(result)
        self.assertGreaterEqual(len(insights), 4)
        for line in insights:
            self.assertGreater(len(line), 40)

    def test_the_horizon_dependence_is_always_stated(self):
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        text = " ".join(af.get_albedo_insights(result)).lower()
        self.assertIn("horizon", text)

    def test_the_local_and_global_split_is_always_stated(self):
        result = af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )
        text = " ".join(af.get_albedo_insights(result)).lower()
        self.assertIn("not added", text)

    def test_a_darkening_is_described_as_an_emission(self):
        result = af.surface_change(
            "cool_white_roof", "dark_roof", 100, "temperate"
        )
        text = " ".join(af.get_albedo_insights(result)).lower()
        self.assertIn("emitting", text)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.previous = af.DB_NAME
        af.DB_NAME = self.path

    def tearDown(self):
        af.DB_NAME = self.previous
        os.unlink(self.path)

    def _result(self):
        return af.surface_change(
            "dark_roof", "cool_white_roof", 100, "temperate"
        )

    def test_save_and_read_back(self):
        row_id = af.save_assessment("u1", "Warehouse roof", self._result())
        self.assertGreater(row_id, 0)
        saved = af.get_assessments("u1")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["name"], "Warehouse roof")
        self.assertLess(saved[0]["co2_equivalent_kg"], 0)

    def test_assessments_are_scoped_to_their_user(self):
        af.save_assessment("u1", "Mine", self._result())
        self.assertEqual(af.get_assessments("u2"), [])

    def test_a_nameless_assessment_is_refused(self):
        with self.assertRaises(af.AlbedoError):
            af.save_assessment("u1", "   ", self._result())

    def test_an_ownerless_assessment_is_refused(self):
        with self.assertRaises(af.AlbedoError):
            af.save_assessment("", "Roof", self._result())

    def test_delete_removes_only_the_owner_s_row(self):
        row_id = af.save_assessment("u1", "Roof", self._result())
        self.assertFalse(af.delete_assessment("u2", row_id))
        self.assertTrue(af.delete_assessment("u1", row_id))
        self.assertEqual(af.get_assessments("u1"), [])

    def test_the_payload_survives_the_round_trip(self):
        af.save_assessment("u1", "Roof", self._result())
        payload = af.get_assessments("u1")[0]["payload"]
        self.assertEqual(payload["from_surface"], "dark_roof")
        self.assertEqual(payload["to_surface"], "cool_white_roof")
        self.assertIn("global_forcing_w_m2", payload)


if __name__ == "__main__":
    unittest.main()
