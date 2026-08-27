"""Tests for the sufficiency floor engine.

`carbon_budget_equity.py` gives a user their ceiling. This gives them their
floor, and the tests guard the properties that make a floor useful rather than
merely present:

*   the floor is context-dependent, and by a factor of several - a single
    global minimum would make a cold-climate renter's unavoidable heating look
    like overconsumption;
*   agency has three states, not two, because "movable if the landlord agrees"
    collapses badly into either of the other two;
*   where a fair-share ceiling falls below the floor the module names the
    dimensions responsible and refuses to issue a target;
*   reduction advice is drawn only from the discretionary and conditionally-
    movable portions, and where that is not enough the module says so rather
    than distributing the remainder across needs;
*   a footprint below the floor is reported as a welfare problem and is never
    treated as an achievement.

The infeasible-corridor test is the load-bearing one. Presenting an impossible
target as a personal shortfall is the specific harm this module exists to
prevent, and a version that always returned a target would be worse than no
module at all.
"""

import os
import tempfile
import unittest

import sufficiency_floor as sf


class TestDimensionTable(unittest.TestCase):

    def test_every_dimension_explains_itself(self):
        for key in sf.list_dimensions():
            self.assertGreater(len(sf.get_dimension(key)["note"]), 40)

    def test_every_dimension_has_a_positive_reference_value(self):
        for key in sf.list_dimensions():
            self.assertGreater(
                sf.get_dimension(key)["reference_kg_co2e"], 0.0
            )

    def test_the_reference_floor_matches_the_published_range(self):
        """Decent living standards estimates sit around 1.5-2.5 tCO2e."""
        total = sf.sufficiency_floor()["floor_kg_co2e"]
        self.assertGreater(total, 1500)
        self.assertLess(total, 2500)

    def test_every_driver_named_is_one_the_module_understands(self):
        known = {
            "degree_days", "building_efficiency", "density",
            "grid_intensity", "household_size",
        }
        for key in sf.list_dimensions():
            for driver in sf.get_dimension(key)["drivers"]:
                self.assertIn(driver, known)

    def test_every_barrier_sensitivity_names_a_real_barrier(self):
        for key in sf.list_dimensions():
            for barrier in sf.get_dimension(key)["barrier_sensitive"]:
                self.assertIn(barrier, sf.list_barriers())

    def test_collective_provision_is_included(self):
        """Healthcare and education are needs, not consumption choices."""
        for key in ("healthcare", "education"):
            self.assertIn(key, sf.list_dimensions())

    def test_unknown_dimension_is_rejected_with_a_useful_message(self):
        with self.assertRaises(sf.SufficiencyError) as caught:
            sf.get_dimension("holidays")
        self.assertIn("nutrition", str(caught.exception))


class TestBarriers(unittest.TestCase):

    def test_every_barrier_names_who_could_remove_it(self):
        """The field that turns a target into an address."""
        for key in sf.list_barriers():
            self.assertGreater(len(sf.get_barrier(key)["removed_by"]), 10)

    def test_every_barrier_affects_at_least_one_dimension(self):
        for key in sf.list_barriers():
            barrier = sf.get_barrier(key)
            self.assertTrue(barrier["dimensions"])
            for dimension in barrier["dimensions"]:
                self.assertIn(dimension, sf.list_dimensions())

    def test_a_medical_need_is_explicitly_not_movable(self):
        """Included so the module can recognise it and stop."""
        self.assertIn("not", sf.get_barrier("medical_need")["removed_by"])

    def test_an_unknown_barrier_is_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.get_barrier("laziness")


class TestContext(unittest.TestCase):

    def test_the_reference_context_is_the_default(self):
        self.assertEqual(sf.build_context(), sf.REFERENCE_CONTEXT)

    def test_fields_default_individually(self):
        context = sf.build_context(household_size=1)
        self.assertEqual(context["household_size"], 1.0)
        self.assertEqual(
            context["density"], sf.REFERENCE_CONTEXT["density"]
        )

    def test_a_household_has_at_least_one_person(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.build_context(household_size=0)

    def test_negative_degree_days_are_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.build_context(heating_degree_days=-100)

    def test_an_unknown_building_band_is_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.build_context(building_efficiency="perfect")

    def test_an_unknown_density_is_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.build_context(density="offworld")


class TestFloorIsContextDependent(unittest.TestCase):
    """Why a global minimum would be worse than none."""

    def _hard(self):
        return sf.build_context(
            heating_degree_days=4200, building_efficiency="poor",
            density="rural", grid_intensity_kg_per_kwh=0.45,
            household_size=1,
        )

    def _easy(self):
        return sf.build_context(
            heating_degree_days=1200, building_efficiency="excellent",
            density="dense_urban", grid_intensity_kg_per_kwh=0.05,
            household_size=4,
        )

    def test_the_floor_spans_several_times_between_contexts(self):
        hard = sf.sufficiency_floor(self._hard())["floor_kg_co2e"]
        easy = sf.sufficiency_floor(self._easy())["floor_kg_co2e"]
        self.assertGreater(hard / easy, 3.0)

    def test_a_colder_climate_raises_the_thermal_floor(self):
        warm = sf.dimension_floor(
            "shelter_thermal", sf.build_context(heating_degree_days=1000)
        )
        cold = sf.dimension_floor(
            "shelter_thermal", sf.build_context(heating_degree_days=5000)
        )
        self.assertGreater(cold["floor_kg_co2e"], warm["floor_kg_co2e"] * 2)

    def test_a_worse_building_raises_the_thermal_floor(self):
        good = sf.dimension_floor(
            "shelter_thermal", sf.build_context(building_efficiency="good")
        )
        poor = sf.dimension_floor(
            "shelter_thermal", sf.build_context(building_efficiency="poor")
        )
        self.assertGreater(poor["floor_kg_co2e"], good["floor_kg_co2e"] * 2)

    def test_rural_living_raises_the_mobility_floor(self):
        urban = sf.dimension_floor(
            "mobility_access", sf.build_context(density="dense_urban")
        )
        rural = sf.dimension_floor(
            "mobility_access", sf.build_context(density="rural")
        )
        self.assertGreater(rural["floor_kg_co2e"], urban["floor_kg_co2e"] * 3)

    def test_a_larger_household_lowers_the_per_person_shelter_floor(self):
        alone = sf.dimension_floor(
            "shelter_construction", sf.build_context(household_size=1)
        )
        family = sf.dimension_floor(
            "shelter_construction", sf.build_context(household_size=4)
        )
        self.assertGreater(
            alone["floor_kg_co2e"], family["floor_kg_co2e"]
        )

    def test_economies_of_scale_are_less_than_proportional(self):
        """A larger home is still a larger home."""
        alone = sf.dimension_floor(
            "shelter_construction", sf.build_context(household_size=1)
        )["floor_kg_co2e"]
        family = sf.dimension_floor(
            "shelter_construction", sf.build_context(household_size=4)
        )["floor_kg_co2e"]
        self.assertGreater(family, alone / 4)

    def test_nutrition_barely_moves_with_context(self):
        """The cleanest part of the floor, and deliberately so."""
        hard = sf.dimension_floor("nutrition", self._hard())
        easy = sf.dimension_floor("nutrition", self._easy())
        self.assertAlmostEqual(
            hard["floor_kg_co2e"], easy["floor_kg_co2e"], places=6
        )

    def test_a_cleaner_grid_lowers_the_floor(self):
        dirty = sf.sufficiency_floor(
            sf.build_context(grid_intensity_kg_per_kwh=0.6)
        )["floor_kg_co2e"]
        clean = sf.sufficiency_floor(
            sf.build_context(grid_intensity_kg_per_kwh=0.05)
        )["floor_kg_co2e"]
        self.assertGreater(dirty, clean)

    def test_the_floor_states_its_basis_and_its_limits(self):
        floor = sf.sufficiency_floor()
        self.assertIn("third significant figure", floor["basis_note"])
        self.assertIn("not a budget", floor["rights_note"])


class TestThreeAgencyStates(unittest.TestCase):

    def _actual(self):
        return {
            "nutrition": 900.0,
            "shelter_thermal": 1800.0,
            "shelter_construction": 200.0,
            "water_sanitation": 60.0,
            "clothing": 200.0,
            "healthcare": 180.0,
            "education": 90.0,
            "communication": 120.0,
            "mobility_access": 1400.0,
        }

    def test_there_are_exactly_three_states(self):
        self.assertEqual(len(sf.list_agency_states()), 3)

    def test_everything_up_to_the_floor_is_structurally_fixed(self):
        result = sf.classify_agency(self._actual())
        for row in result["dimensions"]:
            self.assertLessEqual(
                row["structurally_fixed"], row["floor_kg_co2e"] + 1e-9
            )

    def test_the_three_states_sum_to_the_actual_footprint(self):
        result = sf.classify_agency(self._actual())
        self.assertAlmostEqual(
            sum(result["totals"].values()),
            result["actual_kg_co2e"],
            places=6,
        )

    def test_without_barriers_nothing_is_conditionally_movable(self):
        result = sf.classify_agency(self._actual())
        self.assertEqual(result["totals"]["conditionally_movable"], 0.0)

    def test_a_barrier_moves_excess_out_of_discretionary(self):
        free = sf.classify_agency(self._actual())
        renting = sf.classify_agency(self._actual(), barriers=["tenure_rented"])
        self.assertGreater(renting["totals"]["conditionally_movable"], 0.0)
        self.assertLess(
            renting["totals"]["discretionary"],
            free["totals"]["discretionary"],
        )

    def test_a_barrier_does_not_lock_everything(self):
        """Even a renter can change some heating behaviour."""
        renting = sf.classify_agency(self._actual(), barriers=["tenure_rented"])
        thermal = next(
            row for row in renting["dimensions"]
            if row["dimension"] == "shelter_thermal"
        )
        self.assertGreater(thermal["discretionary"], 0.0)
        self.assertGreater(thermal["conditionally_movable"], 0.0)

    def test_a_barrier_only_touches_its_own_dimensions(self):
        result = sf.classify_agency(self._actual(), barriers=["no_transit"])
        for row in result["dimensions"]:
            if row["dimension"] != "mobility_access":
                self.assertEqual(row["conditionally_movable"], 0.0)

    def test_each_locked_portion_carries_who_can_release_it(self):
        result = sf.classify_agency(self._actual(), barriers=["tenure_rented"])
        thermal = next(
            row for row in result["dimensions"]
            if row["dimension"] == "shelter_thermal"
        )
        self.assertTrue(thermal["active_barriers"])
        self.assertIn("landlord", thermal["active_barriers"][0]["removed_by"])

    def test_constraint_and_circumstance_dominate_the_discretionary_share(self):
        """The distinction the app currently cannot draw.

        The same footprint, in a cold rural rented flat and in a warm dense
        urban home, differs by several times in how much of it the household
        can actually move. Not to zero - even a heavily constrained household
        has some latitude, and claiming otherwise would be as wrong as the
        flat percentage target this replaces.
        """
        constrained = sf.classify_agency(
            self._actual(),
            sf.build_context(
                heating_degree_days=4200, building_efficiency="poor",
                density="rural", household_size=1,
            ),
            barriers=["tenure_rented", "no_transit", "no_capital"],
        )
        unconstrained = sf.classify_agency(
            self._actual(),
            sf.build_context(
                heating_degree_days=1200, building_efficiency="good",
                density="dense_urban", household_size=4,
            ),
        )
        self.assertGreater(unconstrained["discretionary_share"], 0.40)
        self.assertLess(constrained["discretionary_share"], 0.20)
        self.assertGreater(
            unconstrained["discretionary_share"],
            constrained["discretionary_share"] * 2.5,
        )

    def test_even_a_constrained_household_retains_some_latitude(self):
        constrained = sf.classify_agency(
            self._actual(),
            sf.build_context(
                heating_degree_days=4200, building_efficiency="poor",
                density="rural", household_size=1,
            ),
            barriers=["tenure_rented", "no_transit", "no_capital"],
        )
        self.assertGreater(constrained["totals"]["discretionary"], 0.0)

    def test_an_unknown_barrier_is_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.classify_agency(self._actual(), barriers=["bad_attitude"])

    def test_negative_actual_footprint_is_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.classify_agency({"nutrition": -50.0})


class TestFeasibleCorridor(unittest.TestCase):
    """The load-bearing behaviour."""

    def _hard(self):
        return sf.build_context(
            heating_degree_days=4200, building_efficiency="poor",
            density="rural", grid_intensity_kg_per_kwh=0.45,
            household_size=1,
        )

    def test_a_comfortable_ceiling_leaves_a_corridor(self):
        corridor = sf.feasible_corridor(3000)
        self.assertTrue(corridor["is_feasible"])
        self.assertGreater(corridor["corridor_width_kg_co2e"], 0)

    def test_a_ceiling_below_the_floor_is_reported_as_infeasible(self):
        corridor = sf.feasible_corridor(2500, self._hard())
        self.assertFalse(corridor["is_feasible"])
        self.assertLess(corridor["corridor_width_kg_co2e"], 0)

    def test_an_infeasible_corridor_refuses_to_issue_a_target(self):
        corridor = sf.feasible_corridor(2500, self._hard())
        self.assertIn("No personal target", corridor["verdict"])

    def test_an_infeasible_corridor_names_the_structural_cause(self):
        corridor = sf.feasible_corridor(2500, self._hard())
        self.assertIsNotNone(corridor["structural_note"])
        self.assertIn("housing stock", corridor["structural_note"])

    def test_the_responsible_dimensions_are_listed_largest_first(self):
        corridor = sf.feasible_corridor(2500, self._hard())
        responsible = corridor["responsible_dimensions"]
        self.assertTrue(responsible)
        self.assertEqual(responsible[0]["dimension"], "shelter_thermal")
        excesses = [r["context_excess_kg_co2e"] for r in responsible]
        self.assertEqual(excesses, sorted(excesses, reverse=True))

    def test_a_feasible_corridor_names_nobody(self):
        corridor = sf.feasible_corridor(3000)
        self.assertEqual(corridor["responsible_dimensions"], [])
        self.assertIsNone(corridor["structural_note"])

    def test_a_non_positive_ceiling_is_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.feasible_corridor(0)


class TestConsumptionPosition(unittest.TestCase):

    def test_a_large_footprint_is_above_the_ceiling(self):
        position = sf.consumption_position(9000, 3000)
        self.assertEqual(position["position"], "above_ceiling")
        self.assertGreater(position["overshoot_kg_co2e"], 0)

    def test_a_footprint_inside_the_corridor_carries_no_obligation(self):
        position = sf.consumption_position(2200, 3000)
        self.assertEqual(position["position"], "within_corridor")
        self.assertIn("no reduction obligation", position["verdict"].lower())

    def test_a_footprint_below_the_floor_is_a_welfare_concern(self):
        """Not a success, and the module says so explicitly."""
        position = sf.consumption_position(900, 3000)
        self.assertEqual(position["position"], "below_floor")
        self.assertTrue(position["is_welfare_concern"])
        self.assertIn("energy poverty", position["verdict"])

    def test_the_module_refuses_to_congratulate_under_provision(self):
        position = sf.consumption_position(900, 3000)
        self.assertIsNotNone(position["no_congratulation_note"])
        self.assertIn("not a success", position["no_congratulation_note"])

    def test_no_such_note_appears_when_it_would_be_wrong(self):
        position = sf.consumption_position(9000, 3000)
        self.assertIsNone(position["no_congratulation_note"])

    def test_a_negative_footprint_is_rejected(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.consumption_position(-100, 3000)


class TestReductionTargets(unittest.TestCase):

    def _actual(self):
        return {
            "nutrition": 900.0,
            "shelter_thermal": 1800.0,
            "shelter_construction": 200.0,
            "water_sanitation": 60.0,
            "clothing": 200.0,
            "healthcare": 180.0,
            "education": 90.0,
            "communication": 120.0,
            "mobility_access": 1400.0,
        }

    def test_a_modest_reduction_comes_from_discretionary_alone(self):
        classification = sf.classify_agency(self._actual())
        targets = sf.reduction_targets(
            classification, classification["actual_kg_co2e"] - 200
        )
        self.assertTrue(targets["achievable_by_household_alone"])

    def test_targets_never_draw_on_the_structurally_fixed_portion(self):
        classification = sf.classify_agency(self._actual())
        targets = sf.reduction_targets(classification, 1000)
        drawn = sum(t["available_kg_co2e"] for t in targets["targets"])
        self.assertLessEqual(
            drawn,
            classification["totals"]["discretionary"]
            + classification["totals"]["conditionally_movable"]
            + 1e-6,
        )

    def test_an_impossible_reduction_is_reported_rather_than_distributed(self):
        """The residual sits inside the floor and is not a legitimate target."""
        classification = sf.classify_agency(self._actual())
        targets = sf.reduction_targets(classification, 500)
        self.assertFalse(targets["achievable_at_all"])
        self.assertGreater(targets["unmet_kg_co2e"], 0)
        self.assertIn("not a legitimate target", targets["verdict"])

    def test_conditional_targets_are_addressed_to_whoever_can_act(self):
        classification = sf.classify_agency(
            self._actual(), barriers=["tenure_rented"]
        )
        targets = sf.reduction_targets(classification, 2000)
        conditional = [
            t for t in targets["targets"]
            if t["agency"] == "conditionally_movable"
        ]
        self.assertTrue(conditional)
        self.assertIn("landlord", conditional[0]["who_acts"])

    def test_discretionary_targets_are_addressed_to_the_household(self):
        classification = sf.classify_agency(self._actual())
        targets = sf.reduction_targets(classification, 2000)
        discretionary = [
            t for t in targets["targets"] if t["agency"] == "discretionary"
        ]
        self.assertTrue(discretionary)
        self.assertEqual(discretionary[0]["who_acts"], "the household")

    def test_no_reduction_is_required_below_the_ceiling(self):
        classification = sf.classify_agency(self._actual())
        targets = sf.reduction_targets(
            classification, classification["actual_kg_co2e"] + 500
        )
        self.assertEqual(targets["required_reduction_kg_co2e"], 0.0)
        self.assertIn("No reduction is required", targets["verdict"])

    def test_the_restriction_is_stated_rather_than_implied(self):
        classification = sf.classify_agency(self._actual())
        targets = sf.reduction_targets(classification, 2000)
        self.assertIn("will not generate it", targets["restriction_note"])


class TestInsights(unittest.TestCase):

    def _classification(self, **kwargs):
        actual = {
            "nutrition": 900.0,
            "shelter_thermal": 2600.0,
            "shelter_construction": 200.0,
            "water_sanitation": 60.0,
            "clothing": 200.0,
            "healthcare": 180.0,
            "education": 90.0,
            "communication": 120.0,
            "mobility_access": 1400.0,
        }
        return sf.classify_agency(actual, **kwargs)

    def test_insights_are_produced_and_are_sentences(self):
        classification = self._classification()
        corridor = sf.feasible_corridor(3000)
        insights = sf.get_sufficiency_insights(classification, corridor)
        self.assertGreaterEqual(len(insights), 2)
        for line in insights:
            self.assertGreater(len(line), 40)

    def test_the_three_way_split_is_always_stated(self):
        classification = self._classification()
        corridor = sf.feasible_corridor(3000)
        text = " ".join(
            sf.get_sufficiency_insights(classification, corridor)
        ).lower()
        self.assertIn("decent life requires", text)
        self.assertIn("leverage", text)

    def test_a_barrier_is_named_with_who_can_remove_it(self):
        classification = self._classification(barriers=["tenure_rented"])
        corridor = sf.feasible_corridor(3000)
        text = " ".join(
            sf.get_sufficiency_insights(classification, corridor)
        ).lower()
        self.assertIn("landlord", text)

    def test_an_infeasible_corridor_is_always_surfaced(self):
        hard = sf.build_context(
            heating_degree_days=4200, building_efficiency="poor",
            density="rural", household_size=1,
        )
        classification = self._classification(context=hard)
        corridor = sf.feasible_corridor(2000, hard)
        text = " ".join(sf.get_sufficiency_insights(classification, corridor))
        self.assertIn("No personal target", text)

    def test_under_provision_is_flagged_as_a_welfare_signal(self):
        classification = sf.classify_agency({"nutrition": 100.0})
        corridor = sf.feasible_corridor(3000)
        text = " ".join(
            sf.get_sufficiency_insights(classification, corridor)
        ).lower()
        self.assertIn("welfare signal", text)
        self.assertIn("not a saving", text)


class TestPersistence(unittest.TestCase):

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.previous = sf.DB_NAME
        sf.DB_NAME = self.path

    def tearDown(self):
        sf.DB_NAME = self.previous
        os.unlink(self.path)

    def _classification(self):
        return sf.classify_agency(
            {
                "nutrition": 900.0,
                "shelter_thermal": 1800.0,
                "mobility_access": 1400.0,
            },
            barriers=["tenure_rented"],
        )

    def test_save_and_read_back(self):
        row_id = sf.save_assessment("u1", "Our flat", self._classification())
        self.assertGreater(row_id, 0)
        saved = sf.get_assessments("u1")
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["name"], "Our flat")
        self.assertGreater(saved[0]["floor_kg_co2e"], 0)

    def test_assessments_are_scoped_to_their_user(self):
        sf.save_assessment("u1", "Mine", self._classification())
        self.assertEqual(sf.get_assessments("u2"), [])

    def test_a_nameless_assessment_is_refused(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.save_assessment("u1", "  ", self._classification())

    def test_an_ownerless_assessment_is_refused(self):
        with self.assertRaises(sf.SufficiencyError):
            sf.save_assessment("", "Flat", self._classification())

    def test_delete_removes_only_the_owner_s_row(self):
        row_id = sf.save_assessment("u1", "Flat", self._classification())
        self.assertFalse(sf.delete_assessment("u2", row_id))
        self.assertTrue(sf.delete_assessment("u1", row_id))
        self.assertEqual(sf.get_assessments("u1"), [])

    def test_the_barriers_survive_the_round_trip(self):
        """A stored classification without its barriers would be unreadable."""
        sf.save_assessment("u1", "Flat", self._classification())
        payload = sf.get_assessments("u1")[0]["payload"]
        self.assertIn("tenure_rented", payload["barriers"])
        self.assertIn("context", payload)


if __name__ == "__main__":
    unittest.main()
