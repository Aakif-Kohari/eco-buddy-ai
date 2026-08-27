"""Tests for the household allocation engine.

The app divides a household total by headcount and calls the result a person's
footprint. These tests guard the properties that make the replacement worth
having:

*   equal division misattributes economies of scale as behaviour, and the size
    of that misattribution is pinned;
*   sharing is not uniform across categories - heating divides across barely
    more than one unit however many people are present, and food across nearly
    all of them;
*   consumption, benefit and control genuinely disagree, and a child is the
    case that proves it: full benefit, partial consumption, no control;
*   an activity logged by two members is counted once, which nothing else in
    this repository catches;
*   a fair-share reallocation redistributes without changing the aggregate,
    which is a much smaller claim than changing it and is the only one this
    module is entitled to make.

The benchmark test is the load-bearing one. Comparing a single-occupancy
household against a national per-capita average and reporting the result as a
finding is the specific harm this exists to prevent, and it is the comparison
every benchmarking surface in this app currently makes.
"""

import math
import os
import tempfile
import unittest

import src.lifestyle.household_allocation as ha


FOOTPRINT = {
    "space_heating": 3200.0,
    "lighting_and_standby": 450.0,
    "appliances": 600.0,
    "water": 300.0,
    "food": 2400.0,
    "personal_transport": 2800.0,
    "goods_and_clothing": 1400.0,
    "waste": 320.0,
    "digital": 260.0,
}


def solo():
    return [ha.build_member("Alex", 42, agency={"space_heating": 1.0})]


def family():
    return [
        ha.build_member("Sam", 41, agency={"space_heating": 0.8,
                                           "personal_transport": 0.7}),
        ha.build_member("Rowan", 39, agency={"space_heating": 0.2,
                                             "personal_transport": 0.3}),
        ha.build_member("Kit", 11),
        ha.build_member("Wren", 7),
    ]


class TestMembers(unittest.TestCase):

    def test_a_member_needs_a_name(self):
        with self.assertRaises(ha.AllocationError):
            ha.build_member("  ", 30)

    def test_an_implausible_age_is_refused(self):
        for age in (-1, 200, "middle-aged"):
            with self.assertRaises(ha.AllocationError):
                ha.build_member("Someone", age)

    def test_the_child_threshold_is_applied(self):
        self.assertTrue(ha.build_member("Kit", 13)["is_child"])
        self.assertFalse(ha.build_member("Kit", 14)["is_child"])

    def test_occupancy_is_a_share_of_the_year(self):
        member = ha.build_member("Visitor", 30, person_days=182.5)
        self.assertAlmostEqual(member["occupancy"], 0.5, places=4)

    def test_zero_occupancy_is_refused_with_a_reason(self):
        with self.assertRaises(ha.AllocationError) as caught:
            ha.build_member("Ghost", 30, person_days=0)
        self.assertIn("Remove them", str(caught.exception))

    def test_more_than_a_year_of_occupancy_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.build_member("Someone", 30, person_days=400)

    def test_agency_must_be_a_share(self):
        with self.assertRaises(ha.AllocationError):
            ha.build_member("Sam", 40, agency={"space_heating": 1.4})

    def test_agency_over_an_unknown_category_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.build_member("Sam", 40, agency={"vibes": 0.5})

    def test_raw_dictionaries_are_refused(self):
        """Members must go through build_member so occupancy is consistent."""
        with self.assertRaises(ha.AllocationError):
            ha.equivalent_adults([{"name": "Sam", "age": 40}])


class TestEquivalenceScales(unittest.TestCase):

    def test_every_scale_explains_itself(self):
        for key in ha.list_scales():
            self.assertGreater(len(ha.get_scale(key)["note"]), 60)

    def test_a_single_person_is_one_equivalent_adult_under_every_scale(self):
        for key in ha.list_scales():
            self.assertAlmostEqual(
                ha.equivalent_adults(solo(), key)["equivalent_adults"],
                1.0, places=6,
            )

    def test_the_oecd_modified_scale_gives_the_published_figure(self):
        """Two adults and two children: 1 + 0.5 + 0.3 + 0.3."""
        result = ha.equivalent_adults(family(), "oecd_modified")
        self.assertAlmostEqual(result["equivalent_adults"], 2.1, places=6)

    def test_the_oecd_original_scale_gives_the_published_figure(self):
        result = ha.equivalent_adults(family(), "oecd_original")
        self.assertAlmostEqual(result["equivalent_adults"], 2.7, places=6)

    def test_the_square_root_scale_is_the_square_root(self):
        result = ha.equivalent_adults(family(), "square_root")
        self.assertAlmostEqual(result["equivalent_adults"], 2.0, places=6)

    def test_per_capita_is_the_degenerate_case(self):
        result = ha.equivalent_adults(family(), "per_capita")
        self.assertAlmostEqual(
            result["equivalent_adults"], result["headcount"], places=6
        )
        self.assertAlmostEqual(result["economies_of_scale"], 0.0, places=6)

    def test_the_scales_order_as_their_notes_claim(self):
        sizes = {
            key: ha.equivalent_adults(family(), key)["equivalent_adults"]
            for key in ha.list_scales()
        }
        self.assertLess(sizes["square_root"], sizes["oecd_modified"])
        self.assertLess(sizes["oecd_modified"], sizes["oecd_original"])
        self.assertLess(sizes["oecd_original"], sizes["per_capita"])

    def test_a_part_time_member_counts_partially(self):
        shared_custody = [
            ha.build_member("Sam", 41),
            ha.build_member("Kit", 11, person_days=182.5),
        ]
        result = ha.equivalent_adults(shared_custody, "oecd_modified")
        self.assertAlmostEqual(result["equivalent_adults"], 1.15, places=4)
        self.assertAlmostEqual(result["headcount"], 1.5, places=4)

    def test_a_household_of_children_still_has_a_first_adult(self):
        """The scales were built for income statistics and are silent here."""
        children = [ha.build_member("Kit", 12), ha.build_member("Wren", 8)]
        result = ha.equivalent_adults(children, "oecd_modified")
        self.assertAlmostEqual(result["equivalent_adults"], 1.3, places=6)

    def test_an_unknown_scale_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.equivalent_adults(solo(), "vibes")

    def test_an_empty_household_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.equivalent_adults([])


class TestSharingElasticity(unittest.TestCase):

    def test_every_category_explains_its_elasticity(self):
        for key in ha.list_categories():
            self.assertGreater(len(ha.get_category(key)["note"]), 60)

    def test_every_elasticity_lies_between_zero_and_one(self):
        for key in ha.list_categories():
            value = ha.get_category(key)["sharing_elasticity"]
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)

    def test_heating_is_shared_far_more_than_food(self):
        self.assertLess(
            ha.get_category("space_heating")["sharing_elasticity"],
            ha.get_category("food")["sharing_elasticity"] / 2,
        )

    def test_heating_divides_across_barely_more_than_one_unit(self):
        """Four people, and the dwelling is still one dwelling."""
        units = ha.category_units(family(), "space_heating")
        self.assertLess(units, 1.15)

    def test_food_divides_across_nearly_the_full_equivalised_size(self):
        equivalised = ha.equivalent_adults(family())["equivalent_adults"]
        units = ha.category_units(family(), "food")
        self.assertGreater(units, equivalised * 0.9)

    def test_a_single_occupant_has_one_unit_in_every_category(self):
        for key in ha.list_categories():
            self.assertAlmostEqual(
                ha.category_units(solo(), key), 1.0, places=6
            )

    def test_an_unknown_category_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.category_units(family(), "vibes")


class TestDivision(unittest.TestCase):

    def test_per_capita_and_per_equivalent_adult_differ_for_a_family(self):
        division = ha.per_person_footprint(FOOTPRINT, family())
        self.assertGreater(division["per_equivalent_adult"],
                           division["per_capita"])
        self.assertGreater(division["difference_share"], 0.5)

    def test_they_are_identical_for_a_single_occupant(self):
        division = ha.per_person_footprint(FOOTPRINT, solo())
        self.assertAlmostEqual(division["per_capita"],
                               division["per_equivalent_adult"], places=3)
        self.assertAlmostEqual(division["difference_share"], 0.0, places=6)

    def test_the_per_capita_figure_is_the_total_over_headcount(self):
        division = ha.per_person_footprint(FOOTPRINT, family())
        self.assertAlmostEqual(
            division["per_capita"],
            division["household_total"] / division["headcount"],
            places=3,
        )

    def test_the_comparable_figure_resolves_each_category_separately(self):
        division = ha.per_person_footprint(FOOTPRINT, family())
        rebuilt = sum(
            row["per_equivalent_adult"] for row in division["categories"]
        )
        self.assertAlmostEqual(
            division["comparable_footprint"], rebuilt, places=2
        )

    def test_the_comparable_figure_exceeds_the_single_scale_one(self):
        """One scale applies heating's sharing to food, and food is private."""
        division = ha.per_person_footprint(FOOTPRINT, family())
        self.assertGreater(division["comparable_footprint"],
                           division["per_equivalent_adult"])

    def test_per_capita_scale_reproduces_the_apps_current_behaviour(self):
        division = ha.per_person_footprint(
            FOOTPRINT, family(), scale="per_capita"
        )
        self.assertAlmostEqual(division["per_capita"],
                               division["per_equivalent_adult"], places=3)

    def test_a_negative_footprint_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.per_person_footprint({"food": -10.0}, solo())

    def test_an_unknown_category_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.per_person_footprint({"vibes": 10.0}, solo())

    def test_an_empty_footprint_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.per_person_footprint({}, solo())


class TestAttribution(unittest.TestCase):

    def test_every_basis_explains_itself(self):
        for key in ha.list_bases():
            self.assertGreater(len(ha.get_basis(key)["note"]), 60)

    def test_attribution_conserves_the_household_total(self):
        for basis in ("consumption", "benefit"):
            result = ha.attribute(FOOTPRINT, family(), basis)
            self.assertAlmostEqual(
                result["attributed_total"], result["household_total"], places=2
            )

    def test_benefit_is_shared_equally_between_full_time_members(self):
        result = ha.attribute(FOOTPRINT, family(), "benefit")
        values = [row["attributed"] for row in result["members"]]
        self.assertAlmostEqual(max(values), min(values), places=3)

    def test_a_child_benefits_fully_consumes_less_and_controls_nothing(self):
        """The case that proves the three bases are different questions."""
        comparison = ha.compare_bases(FOOTPRINT, family())
        kit = next(row for row in comparison["members"] if row["name"] == "Kit")
        self.assertGreater(kit["benefit"], kit["consumption"])
        self.assertAlmostEqual(kit["control"], 0.0, places=3)

    def test_the_bases_disagree_for_a_household_with_dependants(self):
        comparison = ha.compare_bases(FOOTPRINT, family())
        self.assertTrue(comparison["bases_disagree"])
        self.assertGreater(comparison["largest_spread_share"], 0.1)

    def test_the_bases_agree_for_a_single_adult(self):
        comparison = ha.compare_bases(FOOTPRINT, solo())
        self.assertFalse(comparison["bases_disagree"])

    def test_declared_agency_drives_the_control_basis(self):
        result = ha.attribute(FOOTPRINT, family(), "control")
        sam = next(row for row in result["members"] if row["name"] == "Sam")
        rowan = next(row for row in result["members"] if row["name"] == "Rowan")
        self.assertGreater(sam["attributed"], rowan["attributed"])

    def test_a_category_nobody_controls_is_reported_rather_than_spread(self):
        """Advice about it belongs with a landlord, not with the household."""
        children_only = [ha.build_member("Kit", 11), ha.build_member("Wren", 7)]
        result = ha.attribute(
            {"space_heating": 1000.0}, children_only, "control"
        )
        self.assertIn("space_heating", result["unattributed_categories"])
        self.assertAlmostEqual(result["unattributed_total"], 1000.0, places=2)

    def test_an_unknown_basis_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.attribute(FOOTPRINT, family(), "vibes")


class TestJointConsumption(unittest.TestCase):

    def test_an_activity_logged_twice_is_counted_once(self):
        logs = [
            {"member": "Sam", "activity": "school run",
             "emissions": 180.0, "shared": True},
            {"member": "Rowan", "activity": "school run",
             "emissions": 180.0, "shared": True},
        ]
        result = ha.reconcile_joint_activities(logs)
        self.assertAlmostEqual(result["raw_sum"], 360.0)
        self.assertAlmostEqual(result["reconciled_total"], 180.0)
        self.assertAlmostEqual(result["double_counted"], 180.0)

    def test_separate_activities_are_left_alone(self):
        logs = [
            {"member": "Sam", "activity": "commute", "emissions": 600.0},
            {"member": "Rowan", "activity": "gym trip", "emissions": 120.0},
        ]
        result = ha.reconcile_joint_activities(logs)
        self.assertAlmostEqual(result["double_counted"], 0.0)
        self.assertEqual(result["duplicate_activities"], [])

    def test_an_unflagged_repeat_is_not_treated_as_a_duplicate(self):
        """Two people can genuinely make the same journey separately."""
        logs = [
            {"member": "Sam", "activity": "commute", "emissions": 600.0},
            {"member": "Rowan", "activity": "commute", "emissions": 600.0},
        ]
        result = ha.reconcile_joint_activities(logs)
        self.assertAlmostEqual(result["double_counted"], 0.0)

    def test_the_duplicates_are_named(self):
        logs = [
            {"member": "Sam", "activity": "holiday flight",
             "emissions": 900.0, "shared": True},
            {"member": "Rowan", "activity": "holiday flight",
             "emissions": 900.0, "shared": True},
            {"member": "Sam", "activity": "commute", "emissions": 600.0},
        ]
        result = ha.reconcile_joint_activities(logs)
        self.assertEqual(result["duplicate_activities"], ["holiday flight"])

    def test_it_reconciles_against_a_stated_household_total(self):
        logs = [
            {"member": "Sam", "activity": "school run",
             "emissions": 180.0, "shared": True},
            {"member": "Rowan", "activity": "school run",
             "emissions": 180.0, "shared": True},
            {"member": "Sam", "activity": "commute", "emissions": 600.0},
        ]
        result = ha.reconcile_joint_activities(logs, household_total=780.0)
        self.assertTrue(result["reconciles"])
        self.assertAlmostEqual(result["discrepancy"], 0.0, places=3)

    def test_a_mismatch_against_the_stated_total_is_reported(self):
        logs = [{"member": "Sam", "activity": "commute", "emissions": 600.0}]
        result = ha.reconcile_joint_activities(logs, household_total=900.0)
        self.assertFalse(result["reconciles"])
        self.assertAlmostEqual(result["discrepancy"], -300.0, places=3)

    def test_an_empty_log_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.reconcile_joint_activities([])

    def test_a_log_missing_a_field_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.reconcile_joint_activities([{"member": "Sam"}])

    def test_a_negative_activity_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.reconcile_joint_activities([
                {"member": "Sam", "activity": "x", "emissions": -5.0}
            ])


class TestBenchmarking(unittest.TestCase):
    """The comparison every benchmarking surface in this app currently makes."""

    def _reference(self):
        return {key: value / 2.1 for key, value in FOOTPRINT.items()}

    def test_the_size_effect_and_the_behaviour_effect_are_separated(self):
        result = ha.composition_adjusted_benchmark(
            FOOTPRINT, solo(), self._reference()
        )
        self.assertAlmostEqual(
            result["composition_effect"] + result["behaviour_effect"],
            result["actual_total"] - result["expected_per_capita_comparison"],
            places=2,
        )

    def test_a_single_occupant_is_penalised_by_the_per_capita_comparison(self):
        modest = {key: value * 0.55 for key, value in FOOTPRINT.items()}
        result = ha.composition_adjusted_benchmark(
            modest, solo(), self._reference()
        )
        self.assertGreater(result["composition_effect"], 0.0)

    def test_the_verdict_can_flip_between_the_two_comparisons(self):
        """Above the national average, below a household of its own shape."""
        frugal = {key: value * 0.35 for key, value in FOOTPRINT.items()}
        result = ha.composition_adjusted_benchmark(
            frugal, solo(), self._reference()
        )
        self.assertTrue(result["verdict_flips"])
        self.assertEqual(result["naive_verdict"], "above average")
        self.assertEqual(result["adjusted_verdict"], "below average")

    def test_the_reference_household_sits_at_its_own_benchmark(self):
        reference_members = [
            ha.build_member(entry["name"], entry["age"])
            for entry in ha.REFERENCE_HOUSEHOLD
        ]
        expected = {
            key: value * ha.category_units(reference_members, key)
            for key, value in self._reference().items()
        }
        result = ha.composition_adjusted_benchmark(
            expected, reference_members, self._reference()
        )
        self.assertAlmostEqual(result["behaviour_effect"], 0.0, places=2)

    def test_a_benchmark_without_reference_values_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.composition_adjusted_benchmark(FOOTPRINT, solo(), {})


class TestFairShare(unittest.TestCase):

    def test_the_reference_household_is_unaffected(self):
        """The calibration point: redistribution, not a change in the total."""
        reference_members = [
            ha.build_member(entry["name"], entry["age"])
            for entry in ha.REFERENCE_HOUSEHOLD
        ]
        result = ha.fair_share_reallocation(2500.0, reference_members)
        self.assertAlmostEqual(
            result["adjusted_budget"], result["naive_budget"], places=2
        )

    def test_a_single_occupant_receives_more(self):
        result = ha.fair_share_reallocation(2500.0, solo())
        self.assertGreater(result["adjusted_budget"], result["naive_budget"])
        self.assertEqual(result["direction"], "more")

    def test_the_per_head_allocation_falls_as_the_household_grows(self):
        """Economies of scale, holding composition type constant."""
        per_head = []
        for size in (1, 2, 4, 6):
            household = [
                ha.build_member(f"Person {index}", 30 + index)
                for index in range(size)
            ]
            result = ha.fair_share_reallocation(2500.0, household)
            per_head.append(result["adjusted_budget"] / result["headcount"])
        self.assertEqual(per_head, sorted(per_head, reverse=True))

    def test_an_adult_is_allocated_more_than_a_child(self):
        """Which is why six adults are not compared against four people."""
        with_adult = ha.fair_share_reallocation(2500.0, [
            ha.build_member("Sam", 41), ha.build_member("Rowan", 39),
        ])
        with_child = ha.fair_share_reallocation(2500.0, [
            ha.build_member("Sam", 41), ha.build_member("Kit", 8),
        ])
        self.assertGreater(with_adult["adjusted_budget"],
                           with_child["adjusted_budget"])

    def test_per_capita_scale_changes_nothing(self):
        result = ha.fair_share_reallocation(
            2500.0, solo(), scale="per_capita"
        )
        self.assertAlmostEqual(
            result["adjusted_budget"], result["naive_budget"], places=2
        )

    def test_a_non_positive_budget_is_refused(self):
        with self.assertRaises(ha.AllocationError):
            ha.fair_share_reallocation(0.0, solo())


class TestInsights(unittest.TestCase):

    def _all(self, members, footprint):
        division = ha.per_person_footprint(footprint, members)
        comparison = ha.compare_bases(footprint, members)
        reference = {key: value / 2.1 for key, value in FOOTPRINT.items()}
        benchmark = ha.composition_adjusted_benchmark(
            footprint, members, reference
        )
        reconciliation = ha.reconcile_joint_activities([
            {"member": "Sam", "activity": "school run",
             "emissions": 180.0, "shared": True},
            {"member": "Rowan", "activity": "school run",
             "emissions": 180.0, "shared": True},
        ])
        fair = ha.fair_share_reallocation(2500.0, members)
        return ha.get_allocation_insights(
            division, comparison, benchmark, reconciliation, fair
        )

    def test_single_occupancy_is_called_out(self):
        text = " ".join(self._all(solo(), FOOTPRINT))
        self.assertIn("single-occupancy household", text)

    def test_the_double_count_is_named(self):
        text = " ".join(self._all(family(), FOOTPRINT))
        self.assertIn("counted twice", text)

    def test_the_heating_case_is_explained_for_a_multi_person_household(self):
        text = " ".join(self._all(family(), FOOTPRINT))
        self.assertIn("whether one person or four are in it", text)

    def test_the_composition_and_behaviour_split_is_reported(self):
        text = " ".join(self._all(family(), FOOTPRINT))
        self.assertIn("Only the second is actionable", text)

    def test_the_fair_share_note_names_who_it_redistributes_from(self):
        text = " ".join(self._all(solo(), FOOTPRINT))
        self.assertIn("age, bereavement and low income", text)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = ha.DB_NAME
        ha.DB_NAME = self.path
        self.division = ha.per_person_footprint(FOOTPRINT, family())

    def tearDown(self):
        ha.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_a_saved_allocation_comes_back(self):
        saved_id = ha.save_allocation("user-1", "Our house", self.division)
        self.assertIsInstance(saved_id, int)
        rows = ha.get_allocations("user-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Our house")

    def test_both_divisions_survive_a_round_trip(self):
        ha.save_allocation("user-1", "Round trip", self.division)
        row = ha.get_allocations("user-1")[0]
        self.assertAlmostEqual(row["per_capita"],
                               self.division["per_capita"], 2)
        self.assertAlmostEqual(row["per_equivalent_adult"],
                               self.division["per_equivalent_adult"], 2)

    def test_users_do_not_see_each_others_allocations(self):
        ha.save_allocation("user-1", "Mine", self.division)
        self.assertEqual(ha.get_allocations("user-2"), [])

    def test_an_allocation_needs_a_user_and_a_name(self):
        with self.assertRaises(ha.AllocationError):
            ha.save_allocation("", "Named", self.division)
        with self.assertRaises(ha.AllocationError):
            ha.save_allocation("user-1", "   ", self.division)

    def test_deletion_is_scoped_to_the_owner(self):
        saved_id = ha.save_allocation("user-1", "Mine", self.division)
        self.assertFalse(ha.delete_allocation("user-2", saved_id))
        self.assertTrue(ha.delete_allocation("user-1", saved_id))
        self.assertEqual(ha.get_allocations("user-1"), [])

    def test_reading_without_a_user_returns_nothing_rather_than_raising(self):
        self.assertEqual(ha.get_allocations(None), [])
        self.assertFalse(ha.delete_allocation(None, 1))


if __name__ == "__main__":
    unittest.main()
