"""Tests for the material footprint engine.

Every other module in this app measures an output. This one measures an input,
and the claims worth guarding are the ones that make an input-side metric usable
rather than merely large:

*   the flow categories are never summed, because adding moved topsoil to
    extracted ore produces a number nobody can act on;
*   the rucksack of a metal scales inversely with ore grade, so the model
    separates geology from process;
*   depletion and criticality stay apart, since a material can be abundant and
    critical at once;
*   secondary supply is capped at what recycling input rates can actually
    deliver, so the module cannot be read as saying recycling solves it;
*   the direct-to-hidden ratio, not the tonnage, is the headline.

The category test is the load-bearing one. A "total material requirement" that
adds soil to ore is the standard way this metric gets published and the standard
reason it gets ignored.
"""

import os
import tempfile
import unittest

import material_footprint as mf


class TestMaterialTable(unittest.TestCase):

    def test_every_material_covers_every_flow_category(self):
        for key in mf.list_materials():
            with self.subTest(material=key):
                spec = mf.get_material(key)
                for category in mf.CATEGORIES:
                    self.assertIn(category, spec)
                    self.assertGreaterEqual(spec[category], 0.0)

    def test_every_material_explains_itself(self):
        for key in mf.list_materials():
            self.assertGreater(len(mf.get_material(key)["note"]), 40)

    def test_criticality_fields_are_in_range(self):
        for key in mf.list_materials():
            with self.subTest(material=key):
                spec = mf.get_material(key)
                self.assertGreaterEqual(spec["hhi"], 0)
                self.assertLessEqual(spec["hhi"], 10000)
                self.assertGreaterEqual(spec["substitutability"], 0.0)
                self.assertLessEqual(spec["substitutability"], 1.0)
                self.assertGreaterEqual(spec["recycling_input_rate"], 0.0)
                self.assertLessEqual(spec["recycling_input_rate"], 1.0)

    def test_the_table_spans_orders_of_magnitude(self):
        """Which is why no average is offered."""
        ratios = [mf.get_material(k)["abiotic"] for k in mf.list_materials()]
        self.assertGreater(max(ratios) / min(r for r in ratios if r > 0), 1e5)

    def test_precious_metals_dwarf_base_metals(self):
        self.assertGreater(
            mf.get_material("gold")["abiotic"],
            mf.get_material("steel")["abiotic"] * 10000,
        )

    def test_biotic_materials_carry_their_weight_outside_the_abiotic_column(self):
        """Reading cotton's abiotic column alone says almost nothing about it."""
        cotton = mf.get_material("cotton")
        self.assertGreater(cotton["soil"], cotton["abiotic"] * 5)
        self.assertGreater(cotton["water"], cotton["abiotic"] * 1000)

    def test_an_unknown_material_is_refused_rather_than_averaged(self):
        with self.assertRaises(mf.MaterialError) as context:
            mf.get_material("adamantium")
        self.assertIn("six orders of magnitude", str(context.exception))

    def test_every_family_has_at_least_one_material(self):
        for family in mf.list_families():
            self.assertTrue(mf.list_materials(family))


class TestRucksack(unittest.TestCase):

    def test_flows_scale_linearly_with_mass(self):
        one = mf.rucksack("copper", 1.0)
        ten = mf.rucksack("copper", 10.0)
        for category in mf.CATEGORIES:
            with self.subTest(category=category):
                self.assertAlmostEqual(
                    ten["flows"][category], one["flows"][category] * 10.0,
                    places=6,
                )

    def test_the_categories_are_returned_separately_and_never_totalled(self):
        """The load-bearing property: no combined material requirement figure."""
        result = mf.rucksack("cotton", 1.0)
        for key in result:
            self.assertNotIn("total_material", key)
        self.assertEqual(set(result["flows"]), set(mf.CATEGORIES))

    def test_halving_the_ore_grade_doubles_the_rock_moved(self):
        """Geology, not inefficiency."""
        reference = mf.get_material("copper")["reference_grade"]
        at_grade = mf.rucksack("copper", 1.0, ore_grade=reference)
        at_half = mf.rucksack("copper", 1.0, ore_grade=reference / 2)
        self.assertAlmostEqual(
            at_half["abiotic_kg"], at_grade["abiotic_kg"] * 2, places=6
        )

    def test_grade_only_moves_the_abiotic_column(self):
        reference = mf.get_material("copper")["reference_grade"]
        base = mf.rucksack("copper", 1.0)
        richer = mf.rucksack("copper", 1.0, ore_grade=reference * 2)
        self.assertLess(richer["abiotic_kg"], base["abiotic_kg"])
        self.assertAlmostEqual(
            richer["flows"]["water"], base["flows"]["water"], places=6
        )

    def test_a_material_without_an_ore_refuses_a_grade(self):
        with self.assertRaises(mf.MaterialError) as context:
            mf.rucksack("concrete", 1.0, ore_grade=0.5)
        self.assertIn("no grade to vary", str(context.exception))

    def test_an_impossible_grade_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.rucksack("copper", 1.0, ore_grade=1.5)

    def test_a_negative_mass_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.rucksack("copper", -1.0)

    def test_zero_mass_gives_a_zero_ratio_rather_than_a_division_error(self):
        self.assertEqual(mf.rucksack("copper", 0.0)["ratio"], 0.0)


class TestGradeSensitivity(unittest.TestCase):

    def test_the_curve_runs_from_rich_ore_to_poor_ore(self):
        rows = mf.grade_sensitivity("copper")
        grades = [row["ore_grade"] for row in rows]
        self.assertEqual(grades, sorted(grades, reverse=True))

    def test_poorer_ore_always_moves_more_rock(self):
        values = [row["abiotic_kg_per_kg"] for row in mf.grade_sensitivity("copper")]
        self.assertEqual(values, sorted(values))

    def test_the_reference_grade_is_marked(self):
        rows = mf.grade_sensitivity("copper")
        self.assertEqual(sum(1 for row in rows if row["is_reference"]), 1)

    def test_a_non_mined_material_has_no_grade_sensitivity(self):
        with self.assertRaises(mf.MaterialError):
            mf.grade_sensitivity("glass")


class TestProductFootprint(unittest.TestCase):

    def test_a_smartphone_moves_hundreds_of_times_its_own_mass(self):
        result = mf.product_footprint("smartphone")
        self.assertGreater(result["ratio"], 150.0)
        self.assertLess(result["ratio"], 400.0)

    def test_hidden_flow_is_everything_beyond_the_product_mass(self):
        result = mf.product_footprint("smartphone")
        self.assertAlmostEqual(
            result["hidden_flow_kg"],
            result["abiotic_kg"] - result["direct_mass_kg"],
            places=6,
        )

    def test_the_flows_are_the_sum_of_the_materials(self):
        result = mf.product_footprint("laptop")
        for category in mf.CATEGORIES:
            with self.subTest(category=category):
                self.assertAlmostEqual(
                    result["flows"][category],
                    sum(row["flows"][category] for row in result["materials"]),
                    places=6,
                )

    def test_materials_come_back_worst_first(self):
        rows = mf.product_footprint("smartphone")["materials"]
        values = [row["abiotic_kg"] for row in rows]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_footprint_scales_with_quantity(self):
        one = mf.product_footprint("solar_panel_400w", 1.0)
        ten = mf.product_footprint("solar_panel_400w", 10.0)
        self.assertAlmostEqual(ten["abiotic_kg"], one["abiotic_kg"] * 10, places=6)

    def test_the_result_states_that_categories_are_not_summed(self):
        result = mf.product_footprint("cotton_tshirt")
        self.assertIn("no meaning", result["categories_not_summed"])

    def test_a_grade_override_changes_the_answer(self):
        default = mf.product_footprint("ev_battery_60kwh")
        poorer = mf.product_footprint(
            "ev_battery_60kwh", grades={"copper": 0.003}
        )
        self.assertGreater(poorer["abiotic_kg"], default["abiotic_kg"])

    def test_a_zero_quantity_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.product_footprint("smartphone", 0.0)

    def test_an_unknown_product_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.product_footprint("hoverboard")

    def test_mutating_a_returned_bom_does_not_corrupt_the_table(self):
        copy = mf.get_product("smartphone")
        copy["bom"]["gold"] = 999.0
        self.assertLess(mf.get_product("smartphone")["bom"]["gold"], 0.001)


class TestConcentration(unittest.TestCase):
    """A few hundredths of a gram carrying most of the material moved."""

    def test_three_materials_carry_most_of_a_phone_and_almost_none_of_its_mass(self):
        result = mf.product_footprint("smartphone")
        focus = mf.concentration(result, top_n=3)
        self.assertGreater(focus["top_share_of_abiotic"], 0.6)
        self.assertLess(focus["top_share_of_mass"], 0.10)

    def test_gold_and_palladium_lead_a_phone(self):
        focus = mf.concentration(mf.product_footprint("smartphone"), top_n=2)
        leaders = {row["material"] for row in focus["top"]}
        self.assertEqual(leaders, {"gold", "palladium"})

    def test_a_single_material_product_is_entirely_concentrated(self):
        focus = mf.concentration(mf.product_footprint("cotton_tshirt"))
        self.assertAlmostEqual(focus["top_share_of_abiotic"], 1.0, places=6)


class TestDepletionAndCriticality(unittest.TestCase):
    """Different questions, deliberately different answers."""

    def test_depletion_scales_with_mass(self):
        one = mf.abiotic_depletion("copper", 1.0)["adp_sb_eq"]
        ten = mf.abiotic_depletion("copper", 10.0)["adp_sb_eq"]
        self.assertAlmostEqual(ten, one * 10, places=9)

    def test_the_reserve_basis_is_stated_as_economic_not_geological(self):
        basis = mf.abiotic_depletion("copper", 1.0)["basis"]
        self.assertIn("move with price", basis)
        self.assertIn("rather than a countdown", basis)

    def test_cobalt_is_abundant_and_critical_at_once(self):
        """The clearest case for keeping the two dimensions apart."""
        result = mf.criticality("cobalt")
        self.assertTrue(result["abundant_but_critical"])
        self.assertLess(result["adp_per_kg"], 1e-3)
        self.assertGreaterEqual(result["hhi"], mf.HHI_HIGHLY_CONCENTRATED)

    def test_gold_is_scarce_and_not_supply_concentrated(self):
        result = mf.criticality("gold")
        self.assertFalse(result["abundant_but_critical"])
        self.assertGreater(result["adp_per_kg"], 1.0)

    def test_criticality_returns_three_dimensions_not_one_score(self):
        result = mf.criticality("neodymium")
        for field in ("hhi", "substitutability", "recycling_input_rate"):
            self.assertIn(field, result)
        for key in result:
            self.assertNotIn("score", key)

    def test_rare_earths_have_essentially_no_secondary_supply(self):
        self.assertTrue(
            mf.criticality("neodymium")["secondary_supply_constrained"]
        )

    def test_steel_has_plenty_of_secondary_supply(self):
        self.assertFalse(mf.criticality("steel")["secondary_supply_constrained"])

    def test_the_separation_of_the_two_questions_is_stated(self):
        result = mf.criticality("cobalt")
        self.assertIn("different questions", result["dimensions_kept_separate"])

    def test_concentration_verdicts_follow_the_thresholds(self):
        self.assertIn("Diversified", mf.criticality("glass")["concentration_verdict"])
        self.assertIn(
            "Highly concentrated",
            mf.criticality("neodymium")["concentration_verdict"],
        )


class TestCircularity(unittest.TestCase):

    def test_doubling_the_service_life_halves_the_material(self):
        result = mf.circularity_saving("smartphone", 3.0, 6.0, 20.0)
        self.assertAlmostEqual(result["avoided_share"], 0.5, places=6)

    def test_life_extension_is_not_credited_with_the_recycling_saving(self):
        """The secondary share applies to both scenarios, so the avoided share
        reflects life extension alone."""
        without = mf.circularity_saving("smartphone", 3.0, 6.0, 20.0, 0.0)
        with_secondary = mf.circularity_saving("smartphone", 3.0, 6.0, 20.0, 0.3)
        self.assertAlmostEqual(
            without["avoided_share"], with_secondary["avoided_share"], places=6
        )

    def test_the_recycling_contribution_is_reported_separately(self):
        result = mf.circularity_saving("smartphone", 3.0, 6.0, 20.0, 0.3)
        self.assertGreater(result["secondary_avoided_kg"], 0.0)

    def test_secondary_supply_is_capped_at_what_recycling_can_deliver(self):
        """So the module cannot be read as saying recycling solves it."""
        result = mf.circularity_saving("smartphone", 3.0, 6.0, 20.0, 0.95)
        self.assertTrue(result["secondary_capped"])
        self.assertLess(result["secondary_share_applied"], 0.95)

    def test_a_product_full_of_unrecoverable_metals_has_a_low_ceiling(self):
        result = mf.circularity_saving("smartphone", 3.0, 6.0, 20.0, 1.0)
        self.assertLess(result["achievable_secondary_share"], 0.6)

    def test_a_steel_heavy_product_has_a_higher_ceiling_than_a_phone(self):
        washer = mf.circularity_saving("washing_machine", 11.0, 20.0, 40.0, 1.0)
        phone = mf.circularity_saving("smartphone", 3.0, 6.0, 20.0, 1.0)
        self.assertGreater(
            washer["achievable_secondary_share"],
            phone["achievable_secondary_share"],
        )

    def test_shortening_a_life_is_refused_rather_than_reported_as_a_saving(self):
        with self.assertRaises(mf.MaterialError) as context:
            mf.circularity_saving("laptop", 6.0, 3.0, 20.0)
        self.assertIn("not pretend otherwise", str(context.exception))

    def test_a_zero_service_life_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.circularity_saving("laptop", 0.0, 6.0)

    def test_a_secondary_share_outside_zero_to_one_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.circularity_saving("laptop", 3.0, 6.0, 20.0, 1.5)

    def test_the_recycling_caveat_is_always_carried(self):
        result = mf.circularity_saving("smartphone", 3.0, 6.0)
        self.assertIn("using the thing longer", result["recycling_caveat"])


class TestPerCapitaContext(unittest.TestCase):

    def test_the_share_scales_linearly(self):
        one = mf.per_capita_context(1000.0)["share"]
        two = mf.per_capita_context(2000.0)["share"]
        self.assertAlmostEqual(two, one * 2, places=9)

    def test_the_contested_basis_is_stated(self):
        basis = mf.per_capita_context(1000.0)["basis"]
        self.assertIn("contested", basis)
        self.assertIn("rather than as a limit", basis)

    def test_a_negative_footprint_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.per_capita_context(-1.0)


class TestProductComparison(unittest.TestCase):

    def test_products_are_ranked_per_year_of_service(self):
        rows = mf.compare_products()
        values = [row["abiotic_per_year"] for row in rows]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_the_per_year_ranking_differs_from_the_per_unit_ranking(self):
        """A laptop lasting five years and a phone lasting three are not
        comparable per unit, which is the reason for the normalisation."""
        by_year = [row["product"] for row in mf.compare_products()]
        by_unit = [
            row["product"]
            for row in sorted(
                mf.compare_products(), key=lambda r: -r["abiotic_kg"]
            )
        ]
        self.assertNotEqual(by_year, by_unit)

    def test_the_comparison_covers_every_product(self):
        self.assertEqual(len(mf.compare_products()), len(mf.list_products()))

    def test_an_ev_battery_moves_more_than_a_car_body(self):
        """The carbon-versus-materials trade, made explicit."""
        rows = {row["product"]: row for row in mf.compare_products()}
        self.assertGreater(
            rows["ev_battery_60kwh"]["ratio"], rows["car_ice"]["ratio"]
        )


class TestInsights(unittest.TestCase):

    def test_the_ratio_is_always_the_first_thing_reported(self):
        insights = mf.get_material_insights(mf.product_footprint("smartphone"))
        self.assertIn("per kilogram you hold", insights[0])

    def test_a_phone_is_told_how_concentrated_its_footprint_is(self):
        insights = mf.get_material_insights(mf.product_footprint("smartphone"))
        self.assertTrue(any("of the product's own mass" in i for i in insights))

    def test_a_cotton_product_is_told_to_read_the_other_columns(self):
        insights = mf.get_material_insights(mf.product_footprint("cotton_tshirt"))
        self.assertTrue(any("More soil is moved" in i for i in insights))
        self.assertTrue(any("water flow" in i for i in insights))

    def test_abundant_but_critical_materials_are_named(self):
        insights = mf.get_material_insights(mf.product_footprint("smartphone"))
        self.assertTrue(
            any("Abundant and critical at once" in i for i in insights)
        )

    def test_materials_with_no_recovery_route_are_named(self):
        insights = mf.get_material_insights(mf.product_footprint("cotton_tshirt"))
        self.assertTrue(
            any("no end-of-life recovery route" in i for i in insights)
        )

    def test_a_single_material_gets_singular_grammar(self):
        insights = mf.get_material_insights(mf.product_footprint("cotton_tshirt"))
        line = next(i for i in insights if "recovery route" in i)
        self.assertIn("has essentially no", line)
        self.assertNotIn("have essentially no", line)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self._original = mf.DB_NAME
        mf.DB_NAME = self.path
        self.result = mf.product_footprint("smartphone")

    def tearDown(self):
        mf.DB_NAME = self._original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_footprint_comes_back(self):
        footprint_id = mf.save_footprint("u1", "My phone", self.result)
        self.assertGreater(footprint_id, 0)
        saved = mf.get_footprints("u1")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["name"], "My phone")

    def test_the_ratio_is_stored_alongside_the_tonnage(self):
        mf.save_footprint("u1", "My phone", self.result)
        self.assertAlmostEqual(
            mf.get_footprints("u1")[0]["ratio"], self.result["ratio"], places=6
        )

    def test_the_ore_grades_used_are_stored_with_the_result(self):
        mf.save_footprint("u1", "My phone", self.result)
        materials = mf.get_footprints("u1")[0]["payload"]["materials"]
        self.assertTrue(all("ore_grade" in row for row in materials))

    def test_footprints_are_scoped_to_their_user(self):
        mf.save_footprint("u1", "Mine", self.result)
        self.assertEqual(mf.get_footprints("u2"), [])

    def test_deleting_someone_elses_footprint_does_nothing(self):
        footprint_id = mf.save_footprint("u1", "Mine", self.result)
        self.assertFalse(mf.delete_footprint("u2", footprint_id))
        self.assertEqual(len(mf.get_footprints("u1")), 1)

    def test_deleting_your_own_footprint_removes_it(self):
        footprint_id = mf.save_footprint("u1", "Mine", self.result)
        self.assertTrue(mf.delete_footprint("u1", footprint_id))
        self.assertEqual(mf.get_footprints("u1"), [])

    def test_an_unnamed_footprint_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.save_footprint("u1", "  ", self.result)

    def test_an_anonymous_footprint_is_refused(self):
        with self.assertRaises(mf.MaterialError):
            mf.save_footprint("", "Mine", self.result)


if __name__ == "__main__":
    unittest.main()
