"""Tests for co-product allocation and system expansion.

Two claims are being tested. The first is conservation: mass, energy and
economic allocation must return exactly the burden they were given, for every
process and every basis, or the module is dividing something other than what it
was handed.

The second is that the choice of basis is not a detail. There are tests pinning
the ratio between bases for the cases where it is large, tests that system
expansion changes the *sign* of a result across the plausible range of a market
assumption, and tests that each recycling method is genuinely indifferent to the
lever it does not reward - which is the difference between the methods stated as
a derivative rather than as prose.
"""

import os
import tempfile
import unittest

import src.utils.lca_allocation as la


class TestProcessTable(unittest.TestCase):
    """The processes, and their outputs."""

    def test_every_process_has_outputs_and_a_burden(self):
        for process in la.list_processes():
            with self.subTest(process=process):
                entry = la.get_process(process)
                self.assertGreater(entry["burden_kg_co2e"], 0.0)
                self.assertGreaterEqual(len(entry["outputs"]), 2)
                self.assertTrue(entry["note"])

    def test_every_output_has_a_mass_and_a_label(self):
        for process in la.list_processes():
            for key in la.list_outputs(process):
                with self.subTest(process=process, output=key):
                    output = la.get_process(process)["outputs"][key]
                    self.assertGreater(output["mass_kg"], 0.0)
                    self.assertTrue(output["label"])

    def test_every_displaced_product_has_an_intensity(self):
        for process in la.list_processes():
            for output in la.get_process(process)["outputs"].values():
                displaced = output.get("displaces")
                if displaced:
                    with self.subTest(displaced=displaced):
                        self.assertIn(displaced, la.DISPLACED_INTENSITIES)

    def test_every_intensity_has_a_range(self):
        for product in la.DISPLACED_INTENSITIES:
            with self.subTest(product=product):
                self.assertIn(product, la.DISPLACED_INTENSITY_RANGES)

    def test_every_range_brackets_its_central_value(self):
        for product, values in la.DISPLACED_INTENSITY_RANGES.items():
            with self.subTest(product=product):
                self.assertLessEqual(values["low"], values["central"])
                self.assertLessEqual(values["central"], values["high"])
                self.assertAlmostEqual(
                    values["central"], la.DISPLACED_INTENSITIES[product]
                )

    def test_unknown_process_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.get_process("alchemy")


class TestPartitioning(unittest.TestCase):
    """Dividing a burden, and doing it without losing any."""

    def test_factors_always_sum_to_one(self):
        for process in la.list_processes():
            for basis in la.PARTITIONING_BASES:
                try:
                    factors = la.allocation_factors(process, basis)
                except la.AllocationError:
                    continue
                with self.subTest(process=process, basis=basis):
                    self.assertAlmostEqual(sum(factors.values()), 1.0, places=12)

    def test_allocation_conserves_the_burden(self):
        # The central check. If this fails the module is not partitioning.
        for process in la.list_processes():
            for basis in la.PARTITIONING_BASES:
                try:
                    result = la.allocate(process, basis)
                except la.AllocationError:
                    continue
                with self.subTest(process=process, basis=basis):
                    self.assertAlmostEqual(
                        result["allocated_total"],
                        result["burden_kg_co2e"],
                        places=6,
                    )
                    self.assertTrue(result["conserved"])

    def test_every_output_gets_a_line(self):
        for process in la.list_processes():
            result = la.allocate(process, la.MASS)
            with self.subTest(process=process):
                self.assertEqual(
                    {row["output"] for row in result["lines"]},
                    set(la.list_outputs(process)),
                )

    def test_lines_are_ordered_by_size(self):
        result = la.allocate("oil_refinery", la.MASS)
        for earlier, later in zip(result["lines"], result["lines"][1:]):
            self.assertGreaterEqual(
                earlier["allocated_kg_co2e"], later["allocated_kg_co2e"]
            )

    def test_mass_allocation_gives_every_output_the_same_per_kg(self):
        # By definition. It is worth pinning because it is the reason mass
        # allocation is wrong for a refinery: it says a kilogram of bitumen and
        # a kilogram of petrol cost the same to make.
        result = la.allocate("oil_refinery", la.MASS)
        values = {row["per_kg"] for row in result["lines"]}
        self.assertAlmostEqual(max(values), min(values), places=6)

    def test_system_expansion_is_not_a_partitioning_basis(self):
        with self.assertRaises(la.AllocationError):
            la.allocate("dairy_herd", la.SYSTEM_EXPANSION)

    def test_an_unknown_basis_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.allocate("dairy_herd", "vibes")


class TestUndefinedBases(unittest.TestCase):
    """Refusing to compute a basis that has no meaning here."""

    def test_energy_allocation_is_refused_where_an_output_has_no_energy(self):
        # Hides. The ISO point: physical allocation is undefined when the
        # outputs share no physical property that means anything.
        with self.assertRaises(la.AllocationError) as caught:
            la.allocate("dairy_herd", la.ENERGY)
        self.assertIn("hides", str(caught.exception))

    def test_the_refusal_names_the_offending_output(self):
        with self.assertRaises(la.AllocationError) as caught:
            la.allocate("dairy_herd", la.ENERGY)
        self.assertIn("energy", str(caught.exception).lower())

    def test_a_negative_price_is_refused_as_a_disposal_cost(self):
        original = la.PROCESSES["wheat_crop"]["outputs"]["straw"]["price"]
        la.PROCESSES["wheat_crop"]["outputs"]["straw"]["price"] = -0.02
        try:
            with self.assertRaises(la.AllocationError) as caught:
                la.allocate("wheat_crop", la.ECONOMIC)
            self.assertIn("disposal cost", str(caught.exception))
        finally:
            la.PROCESSES["wheat_crop"]["outputs"]["straw"]["price"] = original

    def test_a_missing_price_is_refused(self):
        original = la.PROCESSES["wheat_crop"]["outputs"]["straw"]["price"]
        la.PROCESSES["wheat_crop"]["outputs"]["straw"]["price"] = None
        try:
            with self.assertRaises(la.AllocationError):
                la.allocate("wheat_crop", la.ECONOMIC)
        finally:
            la.PROCESSES["wheat_crop"]["outputs"]["straw"]["price"] = original

    def test_worthless_outputs_are_refused(self):
        originals = {
            key: output["price"]
            for key, output in la.PROCESSES["wheat_crop"]["outputs"].items()
        }
        for output in la.PROCESSES["wheat_crop"]["outputs"].values():
            output["price"] = 0.0
        try:
            with self.assertRaises(la.AllocationError):
                la.allocate("wheat_crop", la.ECONOMIC)
        finally:
            for key, price in originals.items():
                la.PROCESSES["wheat_crop"]["outputs"][key]["price"] = price

    def test_an_undefined_basis_is_reported_rather_than_dropped(self):
        comparison = la.compare_bases("dairy_herd")
        self.assertIn(la.ENERGY, comparison["unavailable_bases"])
        self.assertNotIn(la.ENERGY, comparison["available_bases"])


class TestBasisDisagreement(unittest.TestCase):
    """That the choice reverses conclusions rather than nudging them."""

    def test_beef_is_far_dearer_on_value_than_on_mass(self):
        # The single most consequential allocation choice in food footprinting.
        comparison = la.compare_bases("dairy_herd")
        beef = next(row for row in comparison["rows"] if row["output"] == "cull_beef")
        self.assertGreater(beef["ratio"], 4.0)
        self.assertEqual(beef["high_basis"], la.ECONOMIC)
        self.assertEqual(beef["low_basis"], la.MASS)

    def test_milk_moves_the_other_way(self):
        # Because the shares are a zero-sum division: what beef gains, milk
        # gives up. A basis cannot make everything cheaper.
        comparison = la.compare_bases("dairy_herd")
        milk = next(row for row in comparison["rows"] if row["output"] == "milk")
        self.assertEqual(milk["high_basis"], la.MASS)

    def test_bitumen_disagrees_by_more_than_a_factor_of_two(self):
        # Dense, cheap and barely refined: mass loads it, value clears it.
        report = la.spread_report("oil_refinery")
        bitumen = next(row for row in report["rows"] if row["output"] == "bitumen")
        self.assertGreater(bitumen["ratio"], 2.0)

    def test_straw_disagrees_by_more_than_a_factor_of_two(self):
        report = la.spread_report("wheat_crop")
        straw = next(row for row in report["rows"] if row["output"] == "straw")
        self.assertGreater(straw["ratio"], 2.0)

    def test_the_widest_output_is_reported(self):
        report = la.spread_report("dairy_herd")
        self.assertEqual(report["widest"], "Cull beef")
        self.assertGreater(report["widest_ratio"], 4.0)

    def test_a_ratio_is_produced_for_every_process_with_two_bases(self):
        for process in la.list_processes():
            comparison = la.compare_bases(process)
            if len(comparison["available_bases"]) < 2:
                continue
            with self.subTest(process=process):
                for row in comparison["rows"]:
                    self.assertIsNotNone(row.get("ratio"))
                    self.assertGreaterEqual(row["ratio"], 1.0)

    def test_insights_are_produced(self):
        insights = la.get_allocation_insights(la.compare_bases("dairy_herd"))
        self.assertTrue(insights)
        for line in insights:
            self.assertIsInstance(line, str)

    def test_an_empty_comparison_says_so(self):
        self.assertEqual(la.get_allocation_insights({}), ["Nothing to analyse."])


class TestSystemExpansion(unittest.TestCase):
    """Crediting instead of dividing, and what that makes the answer depend on."""

    def test_the_credit_reduces_the_primary_burden(self):
        result = la.system_expansion("dairy_herd", "milk")
        self.assertLess(result["net_kg_co2e"], result["burden_kg_co2e"])

    def test_credits_are_itemised_with_their_assumptions(self):
        result = la.system_expansion("dairy_herd", "milk")
        for credit in result["credits"]:
            with self.subTest(credit=credit["output"]):
                self.assertTrue(credit["displaces"])
                self.assertGreater(credit["displaced_intensity"], 0.0)
                self.assertGreaterEqual(credit["displacement_ratio"], 0.0)

    def test_outputs_that_displace_nothing_are_reported(self):
        result = la.system_expansion("dairy_herd", "milk")
        self.assertIn("Hides", result["uncredited_outputs"])

    def test_a_higher_displaced_intensity_gives_a_bigger_credit(self):
        low = la.system_expansion("dairy_herd", "milk", {"suckler_beef": 10.0})
        high = la.system_expansion("dairy_herd", "milk", {"suckler_beef": 30.0})
        self.assertGreater(high["total_credit_kg_co2e"], low["total_credit_kg_co2e"])
        self.assertLess(high["net_kg_co2e"], low["net_kg_co2e"])

    def test_a_negative_result_is_reported_not_clipped(self):
        result = la.system_expansion("dairy_herd", "milk", {"suckler_beef": 60.0})
        self.assertTrue(result["is_negative"])
        self.assertLess(result["net_kg_co2e"], 0.0)

    def test_a_market_assumption_can_change_the_sign(self):
        # Same process, same physics, same method: soy meal from established
        # cropland gives a positive rapeseed oil footprint, soy meal from
        # cleared land gives a negative one.
        sensitivity = la.displacement_sensitivity("rapeseed_crush", "rape_oil")
        self.assertTrue(sensitivity["changes_sign"])
        self.assertGreater(sensitivity["high"], 0.0)
        self.assertLess(sensitivity["low"], 0.0)

    def test_the_sensitivity_covers_all_three_levels(self):
        sensitivity = la.displacement_sensitivity("dairy_herd", "milk")
        self.assertEqual(
            [row["level"] for row in sensitivity["rows"]],
            ["low", "central", "high"],
        )

    def test_a_higher_intensity_always_gives_a_lower_net(self):
        rows = la.displacement_sensitivity("rapeseed_crush", "rape_oil")["rows"]
        for earlier, later in zip(rows, rows[1:]):
            self.assertLess(later["net_kg_co2e"], earlier["net_kg_co2e"])

    def test_an_output_that_is_not_in_the_process_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.system_expansion("dairy_herd", "unicorn")

    def test_an_unpriced_displaced_product_is_refused(self):
        original = la.PROCESSES["dairy_herd"]["outputs"]["cull_beef"]["displaces"]
        la.PROCESSES["dairy_herd"]["outputs"]["cull_beef"]["displaces"] = "moondust"
        try:
            with self.assertRaises(la.AllocationError):
                la.system_expansion("dairy_herd", "milk")
        finally:
            la.PROCESSES["dairy_herd"]["outputs"]["cull_beef"]["displaces"] = original

    def test_expansion_is_kept_out_of_the_allocated_results(self):
        comparison = la.compare_bases("dairy_herd")
        self.assertNotIn(la.SYSTEM_EXPANSION, comparison["results"])
        self.assertIn("milk", comparison["expansions"])


class TestChains(unittest.TestCase):
    """Carrying a basis through more than one step."""

    def setUp(self):
        self.steps = [
            {"process": "dairy_herd", "output": "milk", "quantity": 10.0},
            {"process": "cheese_making", "output": "cheese", "quantity": 1.0},
        ]

    def test_a_chain_accumulates(self):
        result = la.chain(self.steps)
        self.assertGreater(result["total_kg_co2e"], 0.0)
        self.assertEqual(len(result["steps"]), 2)

    def test_the_running_total_never_falls(self):
        result = la.chain(self.steps)
        for earlier, later in zip(result["steps"], result["steps"][1:]):
            self.assertGreaterEqual(
                later["running_kg_co2e"], earlier["running_kg_co2e"]
            )

    def test_the_second_step_inherits_the_first(self):
        result = la.chain(self.steps)
        self.assertAlmostEqual(
            result["steps"][1]["inherited_kg_co2e"],
            result["steps"][0]["running_kg_co2e"],
            places=6,
        )

    def test_a_consistent_chain_is_not_flagged_as_mixed(self):
        self.assertFalse(la.chain(self.steps)["mixed_bases"])

    def test_a_mixed_chain_is_flagged(self):
        mixed = [
            dict(self.steps[0], basis=la.MASS),
            dict(self.steps[1], basis=la.ECONOMIC),
        ]
        self.assertTrue(la.chain(mixed)["mixed_bases"])

    def test_the_basis_carries_through_to_a_different_answer(self):
        rows = {
            row["basis"]: row["total_kg_co2e"]
            for row in la.chain_across_bases(self.steps)
        }
        self.assertIsNotNone(rows[la.MASS])
        self.assertIsNotNone(rows[la.ECONOMIC])
        self.assertNotAlmostEqual(rows[la.MASS], rows[la.ECONOMIC], places=3)

    def test_a_basis_undefined_upstream_fails_the_whole_chain(self):
        rows = {row["basis"]: row for row in la.chain_across_bases(self.steps)}
        self.assertIsNone(rows[la.ENERGY]["total_kg_co2e"])
        self.assertIn("undefined", rows[la.ENERGY]["error"])

    def test_more_input_means_more_burden(self):
        small = la.chain(self.steps)
        larger = la.chain([
            dict(self.steps[0], quantity=20.0), self.steps[1]
        ])
        self.assertGreater(larger["total_kg_co2e"], small["total_kg_co2e"])

    def test_an_empty_chain_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.chain([])

    def test_a_non_positive_quantity_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.chain([dict(self.steps[0], quantity=0.0)])

    def test_an_output_not_in_the_process_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.chain([{"process": "dairy_herd", "output": "petrol"}])


class TestRecyclingAllocation(unittest.TestCase):
    """Which lever each method actually rewards."""

    def test_cut_off_ignores_what_happens_afterwards(self):
        # Stated as a derivative rather than as prose: change the recovery rate
        # from nothing to everything and cut-off does not move at all.
        for material in la.list_materials():
            with self.subTest(material=material):
                none = la.recycling_allocation(
                    material, la.CUT_OFF, recovery_rate=0.0
                )["burden_kg_co2e"]
                full = la.recycling_allocation(
                    material, la.CUT_OFF, recovery_rate=1.0
                )["burden_kg_co2e"]
                self.assertAlmostEqual(none, full, places=9)

    def test_avoided_burden_ignores_what_it_was_made_from(self):
        for material in la.list_materials():
            with self.subTest(material=material):
                none = la.recycling_allocation(
                    material, la.AVOIDED_BURDEN, recycled_content=0.0
                )["burden_kg_co2e"]
                full = la.recycling_allocation(
                    material, la.AVOIDED_BURDEN, recycled_content=1.0
                )["burden_kg_co2e"]
                self.assertAlmostEqual(none, full, places=9)

    def test_fifty_fifty_responds_to_both_and_equally(self):
        for material in la.list_materials():
            with self.subTest(material=material):
                base = la.recycling_allocation(
                    material, la.FIFTY_FIFTY,
                    recycled_content=0.2, recovery_rate=0.2,
                )["burden_kg_co2e"]
                more_content = la.recycling_allocation(
                    material, la.FIFTY_FIFTY,
                    recycled_content=0.6, recovery_rate=0.2,
                )["burden_kg_co2e"]
                more_recovery = la.recycling_allocation(
                    material, la.FIFTY_FIFTY,
                    recycled_content=0.2, recovery_rate=0.6,
                )["burden_kg_co2e"]
                self.assertLess(more_content, base)
                self.assertLess(more_recovery, base)
                self.assertAlmostEqual(more_content, more_recovery, places=9)

    def test_each_method_declares_what_it_rewards(self):
        rewards = {
            method: la.recycling_allocation("aluminium", method)
            for method in la.RECYCLING_METHODS
        }
        self.assertTrue(rewards[la.CUT_OFF]["rewards_recycled_content"])
        self.assertFalse(rewards[la.CUT_OFF]["rewards_recyclability"])
        self.assertFalse(rewards[la.AVOIDED_BURDEN]["rewards_recycled_content"])
        self.assertTrue(rewards[la.AVOIDED_BURDEN]["rewards_recyclability"])
        self.assertTrue(rewards[la.FIFTY_FIFTY]["rewards_recycled_content"])
        self.assertTrue(rewards[la.FIFTY_FIFTY]["rewards_recyclability"])

    def test_no_method_can_beat_fully_recycled(self):
        for material in la.list_materials():
            entry = la.get_material(material)
            for method in la.RECYCLING_METHODS:
                with self.subTest(material=material, method=method):
                    result = la.recycling_allocation(
                        material, method, recycled_content=1.0, recovery_rate=1.0
                    )
                    self.assertGreaterEqual(
                        result["burden_kg_co2e"], entry["recycled_kg_co2e"] - 1e-9
                    )

    def test_nothing_recycled_anywhere_is_the_virgin_burden(self):
        for material in la.list_materials():
            entry = la.get_material(material)
            for method in la.RECYCLING_METHODS:
                with self.subTest(material=material, method=method):
                    result = la.recycling_allocation(
                        material, method, recycled_content=0.0, recovery_rate=0.0
                    )
                    self.assertAlmostEqual(
                        result["burden_kg_co2e"], entry["virgin_kg_co2e"], places=9
                    )

    def test_fifty_fifty_sits_between_the_other_two(self):
        for material in la.list_materials():
            with self.subTest(material=material):
                rows = {
                    row["method"]: row["burden_kg_co2e"]
                    for row in la.compare_recycling_methods(material)["rows"]
                }
                self.assertLessEqual(
                    min(rows[la.CUT_OFF], rows[la.AVOIDED_BURDEN]),
                    rows[la.FIFTY_FIFTY] + 1e-9,
                )
                self.assertGreaterEqual(
                    max(rows[la.CUT_OFF], rows[la.AVOIDED_BURDEN]),
                    rows[la.FIFTY_FIFTY] - 1e-9,
                )

    def test_the_method_matters_most_where_the_gap_is_widest(self):
        # Aluminium: the largest virgin-to-recycled gap of any common material.
        aluminium = la.compare_recycling_methods("aluminium")["ratio"]
        glass = la.compare_recycling_methods("glass")["ratio"]
        self.assertGreater(aluminium, glass)

    def test_an_unknown_method_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.recycling_allocation("steel", "wishful_thinking")

    def test_an_impossible_recycled_content_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.recycling_allocation("steel", la.CUT_OFF, recycled_content=1.5)

    def test_an_impossible_recovery_rate_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.recycling_allocation("steel", la.CUT_OFF, recovery_rate=-0.2)

    def test_an_unknown_material_is_refused(self):
        with self.assertRaises(la.AllocationError):
            la.get_material("unobtainium")


class TestStorage(unittest.TestCase):
    """Persistence, against a throwaway src.core.database."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = la.DB_NAME
        la.DB_NAME = self.path
        la.init_allocation_db()
        self.comparison = la.compare_bases("dairy_herd")

    def tearDown(self):
        la.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_init_is_idempotent(self):
        self.assertTrue(la.init_allocation_db())
        self.assertTrue(la.init_allocation_db())

    def test_a_saved_study_comes_back(self):
        study_id = la.save_study(
            1, "Herd", "dairy_herd", la.ECONOMIC, self.comparison
        )
        self.assertIsNotNone(study_id)
        studies = la.get_studies(1)
        self.assertEqual(len(studies), 1)
        self.assertEqual(studies[0]["process"], "dairy_herd")

    def test_the_widest_ratio_is_stored(self):
        la.save_study(1, "Herd", "dairy_herd", la.ECONOMIC, self.comparison)
        self.assertGreater(la.get_studies(1)[0]["widest_ratio"], 4.0)

    def test_the_comparison_survives_the_round_trip(self):
        la.save_study(1, "Herd", "dairy_herd", la.ECONOMIC, self.comparison)
        stored = la.get_studies(1)[0]["detail"]
        self.assertEqual(len(stored["rows"]), len(self.comparison["rows"]))

    def test_studies_are_newest_first(self):
        for name in ("first", "second", "third"):
            la.save_study(1, name, "dairy_herd", la.MASS, self.comparison)
        self.assertEqual(la.get_studies(1)[0]["name"], "third")

    def test_users_do_not_see_each_other(self):
        la.save_study(1, "mine", "dairy_herd", la.MASS, self.comparison)
        la.save_study(2, "theirs", "dairy_herd", la.MASS, self.comparison)
        self.assertEqual(len(la.get_studies(1)), 1)

    def test_delete_removes_it(self):
        study_id = la.save_study(1, "gone", "dairy_herd", la.MASS, self.comparison)
        self.assertTrue(la.delete_study(study_id, 1))
        self.assertEqual(la.get_studies(1), [])

    def test_you_cannot_delete_someone_elses(self):
        study_id = la.save_study(1, "mine", "dairy_herd", la.MASS, self.comparison)
        self.assertFalse(la.delete_study(study_id, 2))

    def test_the_limit_is_respected(self):
        for n in range(5):
            la.save_study(1, f"s{n}", "dairy_herd", la.MASS, self.comparison)
        self.assertEqual(len(la.get_studies(1, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()
