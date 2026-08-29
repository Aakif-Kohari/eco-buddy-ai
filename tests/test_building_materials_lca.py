"""Tests for whole-life carbon in renovation.

The module exists to stop payback being computed against zero, so the tests are
built around the places where that correction actually changes an answer:

*   a like-for-like comparison happens at a U-value, never per kilogram;
*   replacement inside the assessment period is counted, so a short-lived
    material cannot look cheap by having its second manufacture omitted;
*   module D is never inside a total, however convenient that would be;
*   a measure whose payback exceeds its service life is reported as not paying
    back rather than as a large number;
*   both biogenic conventions are available and they disagree for timber.

The module D test is the one worth guarding hardest. Netting a recycling credit
into a total is the standard way a whole-life figure gets quietly improved, and
the only defence is an assertion that no total contains it.
"""

import os
import tempfile
import unittest

import src.environment.building_materials_lca as lca


class TestMaterialTable(unittest.TestCase):

    def test_every_material_has_a_service_life_and_an_explanation(self):
        for key in lca.list_materials():
            with self.subTest(material=key):
                spec = lca.get_material(key)
                self.assertGreater(spec["service_life"], 0)
                self.assertGreater(len(spec["note"]), 40)

    def test_every_end_of_life_split_sums_to_one(self):
        for key in lca.list_materials():
            with self.subTest(material=key):
                shares = lca.get_material(key)["eol"].values()
                self.assertAlmostEqual(sum(shares), 1.0, places=6)

    def test_every_end_of_life_route_has_a_factor(self):
        for key in lca.list_materials():
            for route in lca.get_material(key)["eol"]:
                with self.subTest(material=key, route=route):
                    self.assertIn(route, lca.EOL_FACTORS)

    def test_installation_waste_is_never_negative_or_absurd(self):
        for key in lca.list_materials():
            with self.subTest(material=key):
                waste = lca.get_material(key)["install_waste"]
                self.assertGreaterEqual(waste, 0.0)
                self.assertLess(waste, 0.5)

    def test_unknown_material_refuses_to_average(self):
        with self.assertRaises(lca.BuildingLCAError) as context:
            lca.get_material("unobtainium_batt")
        self.assertIn("factor of sixty", str(context.exception))

    def test_every_category_has_at_least_one_material(self):
        for category in lca.list_categories():
            self.assertTrue(lca.list_materials(category))

    def test_rigid_boards_waste_more_than_blown_products(self):
        """Cut-and-fit waste is a property of the installation, not the bag."""
        self.assertGreater(
            lca.get_material("pir_board")["install_waste"],
            lca.get_material("cellulose")["install_waste"],
        )


class TestThermalSizing(unittest.TestCase):
    """The functional unit that makes the comparison possible."""

    def test_thickness_follows_from_conductivity(self):
        """Twice the conductivity needs twice the thickness for the same job."""
        wool = lca.thickness_for_u_value("mineral_wool", 0.16, 2.3)
        pir = lca.thickness_for_u_value("pir_board", 0.16, 2.3)
        ratio_thickness = wool / pir
        ratio_conductivity = (
            lca.get_material("mineral_wool")["conductivity"]
            / lca.get_material("pir_board")["conductivity"]
        )
        self.assertAlmostEqual(ratio_thickness, ratio_conductivity, places=6)

    def test_aerogel_is_the_thinnest_option(self):
        thicknesses = {
            key: lca.thickness_for_u_value(key, 0.16, 2.3)
            for key in lca.list_materials("insulation")
        }
        self.assertEqual(min(thicknesses, key=thicknesses.get), "aerogel")

    def test_sizing_round_trips_through_the_u_value(self):
        thickness = lca.thickness_for_u_value("mineral_wool", 0.18, 2.3)
        self.assertAlmostEqual(
            lca.u_value_after("mineral_wool", thickness, 2.3), 0.18, places=9
        )

    def test_a_target_no_better_than_the_existing_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError) as context:
            lca.thickness_for_u_value("mineral_wool", 2.3, 2.3)
        self.assertIn("nothing to insulate for", str(context.exception))

    def test_glazing_cannot_be_sized_to_a_u_value(self):
        """A window is bought as a unit, not as a thickness."""
        with self.assertRaises(lca.BuildingLCAError):
            lca.thickness_for_u_value("triple_glazing", 0.8, 1.4)

    def test_negative_u_values_are_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.thickness_for_u_value("mineral_wool", -0.1, 2.3)


class TestReplacementCount(unittest.TestCase):
    """B4, and the reason a cheap material is not always a low-carbon one."""

    def test_a_component_lasting_the_whole_period_is_never_replaced(self):
        self.assertEqual(lca.replacement_count(60, 60), 0)

    def test_a_component_lasting_half_the_period_is_replaced_once(self):
        self.assertEqual(lca.replacement_count(30, 60), 1)

    def test_a_component_lasting_a_third_of_the_period_is_replaced_twice(self):
        self.assertEqual(lca.replacement_count(20, 60), 2)

    def test_a_component_outlasting_the_period_is_never_replaced(self):
        self.assertEqual(lca.replacement_count(100, 60), 0)

    def test_a_shorter_study_hides_replacements(self):
        """The reason the assessment period is a parameter and not a constant."""
        self.assertEqual(lca.replacement_count(40, 30), 0)
        self.assertEqual(lca.replacement_count(40, 60), 1)

    def test_a_zero_service_life_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.replacement_count(0, 60)

    def test_a_zero_assessment_period_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.replacement_count(30, 0)


class TestWholeLifeCarbon(unittest.TestCase):

    def setUp(self):
        self.thickness = lca.thickness_for_u_value("mineral_wool", 0.16, 2.3)

    def test_every_en15978_stage_is_reported(self):
        result = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=self.thickness
        )
        for stage in ("A1-A3", "A4", "A5", "B4", "C3-C4"):
            self.assertIn(stage, result["stages"])

    def test_module_d_is_never_inside_a_total(self):
        """The guard against a recycling credit quietly improving a number."""
        result = lca.whole_life_carbon("structural_steel", 10.0, thickness_m=0.02)
        self.assertLess(result["module_d_kg_co2e"], 0.0)
        self.assertTrue(result["module_d_excluded_from_total"])
        stage_sum = sum(result["stages"].values())
        self.assertAlmostEqual(
            result["total_kg_co2e"], stage_sum, places=6
        )

    def test_upfront_is_a1_to_a5_and_nothing_later(self):
        result = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=self.thickness
        )
        stages = result["stages"]
        self.assertAlmostEqual(
            result["upfront_kg_co2e"],
            stages["A1-A3"] + stages["A4"] + stages["A5"],
            places=6,
        )

    def test_installation_waste_is_charged_in_a5_not_hidden_in_a1_a3(self):
        result = lca.whole_life_carbon("pir_board", 30.0, thickness_m=0.1)
        spec = lca.get_material("pir_board")
        self.assertAlmostEqual(
            result["stages"]["A1-A3"], result["mass_kg"] * spec["a1_a3"], places=6
        )
        self.assertGreater(result["stages"]["A5"], 0.0)

    def test_a_longer_study_period_adds_replacements_and_carbon(self):
        short = lca.whole_life_carbon(
            "pir_board", 30.0, thickness_m=0.1, assessment_period=30
        )
        long = lca.whole_life_carbon(
            "pir_board", 30.0, thickness_m=0.1, assessment_period=60
        )
        self.assertEqual(short["replacements"], 0)
        self.assertEqual(long["replacements"], 1)
        self.assertGreater(long["total_kg_co2e"], short["total_kg_co2e"])

    def test_air_freight_dominates_a4_where_road_does_not(self):
        by_road = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=self.thickness,
            transport_km=1000.0, transport_mode="hgv_articulated",
        )
        by_air = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=self.thickness,
            transport_km=1000.0, transport_mode="air_freight",
        )
        self.assertGreater(by_air["stages"]["A4"], by_road["stages"]["A4"] * 5)

    def test_glazing_is_sized_per_square_metre_without_a_thickness(self):
        result = lca.whole_life_carbon("triple_glazing", 12.0)
        self.assertAlmostEqual(result["mass_kg"], 39.0 * 12.0, places=6)

    def test_a_thickness_sized_material_refuses_to_run_without_one(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.whole_life_carbon("mineral_wool", 50.0)

    def test_zero_area_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.whole_life_carbon("mineral_wool", 0.0, thickness_m=0.2)

    def test_an_unknown_biogenic_convention_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError) as context:
            lca.whole_life_carbon(
                "structural_timber", 10.0, thickness_m=0.05,
                biogenic_convention="whatever_looks_best",
            )
        self.assertIn("Both are defensible", str(context.exception))

    def test_an_unknown_transport_mode_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.whole_life_carbon(
                "mineral_wool", 50.0, thickness_m=0.2, transport_mode="teleport"
            )


class TestBiogenicConventions(unittest.TestCase):
    """Both are defensible and they disagree, so both are shown."""

    def test_the_conventions_disagree_upfront_for_timber(self):
        zero = lca.whole_life_carbon(
            "structural_timber", 20.0, thickness_m=0.05,
            biogenic_convention="0/0",
        )
        credited = lca.whole_life_carbon(
            "structural_timber", 20.0, thickness_m=0.05,
            biogenic_convention="-1/+1",
        )
        self.assertGreater(zero["upfront_kg_co2e"], credited["upfront_kg_co2e"])
        self.assertLess(credited["upfront_kg_co2e"], 0.0)

    def test_the_conventions_agree_on_the_whole_life_total(self):
        """Crediting sequestration and charging the release moves timing, not
        the total. If these ever diverge, one half of the convention is
        missing."""
        zero = lca.whole_life_carbon(
            "structural_timber", 20.0, thickness_m=0.05,
            biogenic_convention="0/0",
        )
        credited = lca.whole_life_carbon(
            "structural_timber", 20.0, thickness_m=0.05,
            biogenic_convention="-1/+1",
        )
        self.assertAlmostEqual(
            zero["total_kg_co2e"], credited["total_kg_co2e"], places=6
        )

    def test_the_conventions_agree_entirely_for_a_mineral_material(self):
        zero = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=0.2, biogenic_convention="0/0"
        )
        credited = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=0.2, biogenic_convention="-1/+1"
        )
        self.assertAlmostEqual(
            zero["upfront_kg_co2e"], credited["upfront_kg_co2e"], places=6
        )

    def test_biogenic_storage_is_zero_for_a_mineral_material(self):
        self.assertEqual(lca.biogenic_storage("mineral_wool", 100.0), 0.0)

    def test_biogenic_storage_uses_the_molecular_ratio(self):
        stored = lca.biogenic_storage("structural_timber", 100.0)
        self.assertAlmostEqual(stored, 100.0 * 0.90 * 0.50 * 44.0 / 12.0, places=6)

    def test_negative_mass_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.biogenic_storage("structural_timber", -1.0)


class TestOperationalSaving(unittest.TestCase):

    def test_a_bigger_u_value_improvement_saves_more(self):
        small = lca.operational_saving(50.0, 2.3, 1.0)
        large = lca.operational_saving(50.0, 2.3, 0.16)
        self.assertGreater(large["annual_kg_co2e"], small["annual_kg_co2e"])

    def test_a_heat_pump_saves_less_carbon_for_the_same_fabric_measure(self):
        """Counterintuitive and true: a more efficient system means the heat
        being saved was cheaper, so the fabric measure repays more slowly."""
        gas = lca.operational_saving(50.0, 2.3, 0.16, "gas_boiler")
        pump = lca.operational_saving(50.0, 2.3, 0.16, "heat_pump")
        self.assertAlmostEqual(
            gas["heat_saved_kwh"], pump["heat_saved_kwh"], places=6
        )
        self.assertGreater(gas["annual_kg_co2e"], pump["annual_kg_co2e"] * 2)

    def test_saving_scales_with_area(self):
        one = lca.operational_saving(10.0, 2.3, 0.16)
        ten = lca.operational_saving(100.0, 2.3, 0.16)
        self.assertAlmostEqual(
            ten["annual_kg_co2e"], one["annual_kg_co2e"] * 10.0, places=6
        )

    def test_an_improvement_that_is_not_an_improvement_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.operational_saving(50.0, 0.16, 2.3)

    def test_an_unknown_heat_source_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.operational_saving(50.0, 2.3, 0.16, "wishful_thinking")

    def test_zero_degree_days_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.operational_saving(50.0, 2.3, 0.16, degree_days=0.0)


class TestCarbonPayback(unittest.TestCase):

    def test_loft_insulation_repays_almost_immediately(self):
        thickness = lca.thickness_for_u_value("mineral_wool", 0.16, 2.3)
        result = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=thickness
        )
        saving = lca.operational_saving(50.0, 2.3, 0.16, "gas_boiler")
        payback = lca.carbon_payback(
            result["upfront_kg_co2e"], saving["annual_kg_co2e"], 60
        )
        self.assertLess(payback["years"], 3.0)
        self.assertTrue(payback["pays_back"])

    def test_triple_glazing_on_a_heat_pump_never_repays(self):
        """The specific case the module was written to catch."""
        result = lca.whole_life_carbon("triple_glazing", 12.0)
        saving = lca.operational_saving(12.0, 1.40, 0.80, "heat_pump")
        payback = lca.carbon_payback(
            result["upfront_kg_co2e"], saving["annual_kg_co2e"], 30
        )
        self.assertFalse(payback["pays_back"])
        self.assertIn("does not pay back", payback["verdict"])

    def test_a_failure_to_repay_is_stated_in_words_not_just_a_number(self):
        payback = lca.carbon_payback(10000.0, 100.0, 30)
        self.assertIn("brings emissions forward", payback["verdict"])

    def test_no_saving_means_no_payback_rather_than_a_division_error(self):
        payback = lca.carbon_payback(500.0, 0.0, 60)
        self.assertIsNone(payback["years"])
        self.assertFalse(payback["pays_back"])

    def test_negative_upfront_is_not_treated_as_a_payback_question(self):
        payback = lca.carbon_payback(-500.0, 100.0, 60)
        self.assertTrue(payback["pays_back"])
        self.assertIn("property of the convention", payback["verdict"])


class TestTimeWeighting(unittest.TestCase):

    def test_discounting_reduces_the_value_of_future_savings(self):
        weighted = lca.time_weighted_payback(1000.0, 100.0, 60, 0.03)
        self.assertLess(weighted["discounted_saving"], weighted["undiscounted_saving"])

    def test_a_zero_discount_rate_reproduces_the_flat_arithmetic(self):
        weighted = lca.time_weighted_payback(1000.0, 100.0, 60, 0.0)
        self.assertAlmostEqual(
            weighted["discounted_saving"], weighted["undiscounted_saving"], places=6
        )

    def test_a_measure_can_be_net_positive_flat_and_net_negative_discounted(self):
        """The disagreement the module exists to surface."""
        weighted = lca.time_weighted_payback(2400.0, 60.0, 60, 0.05)
        self.assertGreater(weighted["undiscounted_net"], 0.0)
        self.assertLess(weighted["discounted_net"], 0.0)

    def test_a_discount_rate_of_one_or_more_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.time_weighted_payback(1000.0, 100.0, 60, 1.0)

    def test_the_contested_nature_of_discounting_carbon_is_stated(self):
        weighted = lca.time_weighted_payback(1000.0, 100.0, 60)
        self.assertIn("contested", weighted["note"])


class TestLikeForLikeComparison(unittest.TestCase):

    def test_comparison_is_at_a_u_value_not_a_thickness(self):
        rows = lca.compare_at_u_value(
            lca.list_materials("insulation"), 50.0, 0.16, 2.3
        )
        thicknesses = {row["thickness_mm"] for row in rows}
        self.assertGreater(len(thicknesses), 1)

    def test_glazing_is_excluded_from_a_thermal_comparison(self):
        rows = lca.compare_at_u_value(lca.list_materials(), 50.0, 0.16, 2.3)
        self.assertNotIn("triple_glazing", {row["material"] for row in rows})

    def test_results_are_ranked_best_first(self):
        rows = lca.compare_at_u_value(
            lca.list_materials("insulation"), 50.0, 0.16, 2.3
        )
        values = [row["total_kg_co2e"] for row in rows]
        self.assertEqual(values, sorted(values))

    def test_cellulose_beats_aerogel_by_orders_of_magnitude(self):
        rows = {
            row["material"]: row
            for row in lca.compare_at_u_value(
                lca.list_materials("insulation"), 50.0, 0.16, 2.3
            )
        }
        self.assertGreater(
            rows["aerogel"]["total_kg_co2e"] / rows["cellulose"]["total_kg_co2e"],
            20.0,
        )

    def test_per_kilogram_ranking_differs_from_the_functional_unit_ranking(self):
        """If these agreed, the functional unit would not be earning its keep."""
        by_mass = sorted(
            lca.list_materials("insulation"),
            key=lambda k: lca.get_material(k)["a1_a3"],
        )
        by_function = [
            row["material"] for row in lca.compare_at_u_value(
                lca.list_materials("insulation"), 50.0, 0.16, 2.3
            )
        ]
        self.assertNotEqual(by_mass, by_function)


class TestRenovateVersusRebuild(unittest.TestCase):

    def test_demolition_is_charged_to_the_rebuild(self):
        result = lca.renovate_versus_rebuild(90.0, 3000.0, 900.0)
        self.assertAlmostEqual(result["demolition_carbon"], 60.0 * 90.0, places=6)
        self.assertGreater(
            result["rebuild_upfront"], 550.0 * 90.0
        )

    def test_a_deep_retrofit_beats_a_rebuild(self):
        result = lca.renovate_versus_rebuild(90.0, 12000.0, 3500.0)
        self.assertEqual(result["better"], "retrofit")

    def test_a_shallow_retrofit_of_a_poor_building_can_lose(self):
        """The module says so rather than assuming the answer in advance."""
        result = lca.renovate_versus_rebuild(90.0, 3000.0, 400.0)
        self.assertEqual(result["better"], "rebuild")

    def test_no_operational_gap_means_no_crossover_year(self):
        result = lca.renovate_versus_rebuild(
            90.0, 12000.0, 3500.0, existing_annual_demand_kwh_per_m2=30.0
        )
        self.assertIsNone(result["crossover_years"])

    def test_the_sunk_carbon_of_the_standing_building_is_stated(self):
        result = lca.renovate_versus_rebuild(90.0, 3000.0, 900.0)
        self.assertIn("sunk under", result["note"])

    def test_zero_floor_area_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.renovate_versus_rebuild(0.0, 3000.0, 900.0)


class TestInsights(unittest.TestCase):

    def test_a_replaced_component_gets_a_replacement_insight(self):
        result = lca.whole_life_carbon("pir_board", 30.0, thickness_m=0.1)
        insights = lca.get_lca_insights(result)
        self.assertTrue(any("Replaced" in line for line in insights))

    def test_a_durable_component_gets_a_durability_insight(self):
        result = lca.whole_life_carbon("mineral_wool", 50.0, thickness_m=0.2)
        insights = lca.get_lca_insights(result)
        self.assertTrue(any("Durability" in line for line in insights))

    def test_module_d_is_flagged_as_excluded_when_it_exists(self):
        result = lca.whole_life_carbon("structural_steel", 10.0, thickness_m=0.02)
        insights = lca.get_lca_insights(result)
        self.assertTrue(any("excluded from every total" in line for line in insights))

    def test_a_high_waste_material_is_called_out(self):
        result = lca.whole_life_carbon("plasterboard", 40.0, thickness_m=0.0125)
        insights = lca.get_lca_insights(result)
        self.assertTrue(any("installation waste" in line for line in insights))

    def test_the_biogenic_convention_in_force_is_named(self):
        result = lca.whole_life_carbon(
            "structural_timber", 20.0, thickness_m=0.05,
            biogenic_convention="0/0",
        )
        insights = lca.get_lca_insights(result)
        self.assertTrue(any("0/0 convention" in line for line in insights))


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self._original = lca.DB_NAME
        lca.DB_NAME = self.path
        self.result = lca.whole_life_carbon(
            "mineral_wool", 50.0, thickness_m=0.2
        )

    def tearDown(self):
        lca.DB_NAME = self._original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_project_comes_back(self):
        project_id = lca.save_project(user_id="u1", name="Loft", result=self.result)
        self.assertGreater(project_id, 0)
        projects = lca.get_projects("u1")
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["name"], "Loft")

    def test_payback_is_stored_alongside_the_result_when_given(self):
        payback = lca.carbon_payback(self.result["upfront_kg_co2e"], 500.0, 60)
        lca.save_project("u1", "Loft", self.result, payback)
        self.assertAlmostEqual(
            lca.get_projects("u1")[0]["payback_years"], payback["years"], places=6
        )

    def test_a_project_without_payback_stores_null_rather_than_zero(self):
        lca.save_project("u1", "Loft", self.result)
        self.assertIsNone(lca.get_projects("u1")[0]["payback_years"])

    def test_projects_are_scoped_to_their_user(self):
        lca.save_project("u1", "Mine", self.result)
        self.assertEqual(lca.get_projects("u2"), [])

    def test_deleting_someone_elses_project_does_nothing(self):
        project_id = lca.save_project("u1", "Mine", self.result)
        self.assertFalse(lca.delete_project("u2", project_id))
        self.assertEqual(len(lca.get_projects("u1")), 1)

    def test_deleting_your_own_project_removes_it(self):
        project_id = lca.save_project("u1", "Mine", self.result)
        self.assertTrue(lca.delete_project("u1", project_id))
        self.assertEqual(lca.get_projects("u1"), [])

    def test_an_unnamed_project_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.save_project("u1", "  ", self.result)

    def test_an_anonymous_project_is_refused(self):
        with self.assertRaises(lca.BuildingLCAError):
            lca.save_project("", "Loft", self.result)


if __name__ == "__main__":
    unittest.main()
