"""Tests for the remaining personal carbon budget.

Two claims. The first is that contraction and convergence is a genuine blend of
the two principles it sits between - so the tests pin it at both limits:
converging today must reproduce equal per capita exactly, converging far enough
out must approach grandfathering, and it must sit between them at every date in
between. For a low emitter that ordering reverses, and it is tested that it does.

The second is that a budget is cumulative. The pathway rates here have closed
forms, so each is checked by integrating the pathway it describes and asserting
the area comes back to the budget - if the rate is right, the curve spends
exactly what it was given.
"""

import math
import os
import tempfile
import unittest

import src.carbon.carbon_budget_equity as cb


HIGH_EMITTER = 12.0
LOW_EMITTER = 2.0


class TestGlobalBudget(unittest.TestCase):
    """The budget, aged forward from its base year."""

    def test_every_target_has_every_likelihood(self):
        for target in cb.list_targets():
            for likelihood in cb.list_likelihoods(target):
                with self.subTest(target=target, likelihood=likelihood):
                    result = cb.remaining_global_budget(target, likelihood)
                    self.assertGreater(result["at_base_year_gt"], 0.0)

    def test_a_higher_likelihood_means_a_smaller_budget(self):
        # Insisting on 83% rather than 50% removes a large share of it. A bare
        # figure without its likelihood is not a figure.
        for target in cb.list_targets():
            budgets = [
                cb.remaining_global_budget(target, likelihood)["remaining_gt"]
                for likelihood in cb.list_likelihoods(target)
            ]
            with self.subTest(target=target):
                for earlier, later in zip(budgets, budgets[1:]):
                    self.assertLess(later, earlier)

    def test_a_warmer_target_means_a_bigger_budget(self):
        targets = cb.list_targets()
        budgets = [
            cb.remaining_global_budget(target, 67)["remaining_gt"]
            for target in targets
        ]
        for earlier, later in zip(budgets, budgets[1:]):
            self.assertGreater(later, earlier)

    def test_the_budget_shrinks_as_the_years_pass(self):
        # The reason it is not stored as a constant.
        values = [
            cb.remaining_global_budget(as_of=year)["remaining_gt"]
            for year in range(2021, cb.latest_data_year() + 1)
        ]
        for earlier, later in zip(values, values[1:]):
            self.assertLess(later, earlier)

    def test_at_the_base_year_nothing_has_elapsed(self):
        result = cb.remaining_global_budget(as_of=cb.BUDGET_BASE_YEAR)
        self.assertAlmostEqual(result["elapsed_gt"], 0.0)
        self.assertAlmostEqual(
            result["remaining_gt"], result["at_base_year_gt"], places=6
        )

    def test_elapsed_is_the_sum_of_the_years_in_between(self):
        result = cb.remaining_global_budget(as_of=2024)
        expected = sum(cb.GLOBAL_EMISSIONS[year] for year in (2020, 2021, 2022, 2023))
        self.assertAlmostEqual(result["elapsed_gt"], expected, places=6)

    def test_an_unknown_target_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.remaining_global_budget(target=3.5)

    def test_an_unknown_likelihood_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.remaining_global_budget(likelihood=95)

    def test_looking_before_the_base_year_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.remaining_global_budget(as_of=2015)

    def test_looking_past_the_data_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.remaining_global_budget(as_of=cb.latest_data_year() + 5)

    def test_every_emissions_year_has_a_population(self):
        for year in cb.GLOBAL_EMISSIONS:
            with self.subTest(year=year):
                self.assertIn(year, cb.WORLD_POPULATION)

    def test_every_target_carries_a_note(self):
        for target in cb.list_targets():
            with self.subTest(target=target):
                self.assertTrue(cb.TARGET_NOTES[target])


class TestPrinciples(unittest.TestCase):
    """The four allocations, and how they order against each other."""

    def test_every_principle_produces_a_budget(self):
        for principle in cb.PRINCIPLES:
            with self.subTest(principle=principle):
                result = cb.personal_budget(HIGH_EMITTER, principle)
                self.assertGreater(result["budget_tonnes"], 0.0)
                self.assertTrue(result["principle_note"])

    def test_grandfathering_favours_a_high_emitter(self):
        # The whole objection to it: emit more, get more.
        equal = cb.personal_budget(HIGH_EMITTER, cb.EQUAL_PER_CAPITA)
        grandfathered = cb.personal_budget(HIGH_EMITTER, cb.GRANDFATHERING)
        self.assertGreater(
            grandfathered["budget_tonnes"], equal["budget_tonnes"]
        )

    def test_grandfathering_penalises_a_low_emitter(self):
        # And the ordering reverses, which is what makes it a distributional
        # choice rather than a scaling.
        equal = cb.personal_budget(LOW_EMITTER, cb.EQUAL_PER_CAPITA)
        grandfathered = cb.personal_budget(LOW_EMITTER, cb.GRANDFATHERING)
        self.assertLess(grandfathered["budget_tonnes"], equal["budget_tonnes"])

    def test_the_equal_share_is_the_same_for_everyone(self):
        high = cb.personal_budget(HIGH_EMITTER, cb.EQUAL_PER_CAPITA)
        low = cb.personal_budget(LOW_EMITTER, cb.EQUAL_PER_CAPITA)
        self.assertAlmostEqual(
            high["budget_tonnes"], low["budget_tonnes"], places=6
        )

    def test_converging_today_is_exactly_equal_per_capita(self):
        equal = cb.personal_budget(HIGH_EMITTER, cb.EQUAL_PER_CAPITA)
        converged = cb.personal_budget(
            HIGH_EMITTER, cb.CONTRACTION_CONVERGENCE,
            convergence_year=cb.current_year(),
        )
        self.assertAlmostEqual(
            converged["budget_tonnes"], equal["budget_tonnes"], places=3
        )

    def test_converging_far_enough_out_approaches_grandfathering(self):
        grandfathered = cb.personal_budget(HIGH_EMITTER, cb.GRANDFATHERING)
        distant = cb.personal_budget(
            HIGH_EMITTER, cb.CONTRACTION_CONVERGENCE, convergence_year=2400
        )
        self.assertLess(
            abs(distant["budget_tonnes"] - grandfathered["budget_tonnes"]),
            grandfathered["budget_tonnes"] * 0.05,
        )

    def test_convergence_always_sits_between_the_two(self):
        for emitter in (LOW_EMITTER, 5.0, HIGH_EMITTER, 25.0):
            equal = cb.personal_budget(emitter, cb.EQUAL_PER_CAPITA)["budget_tonnes"]
            grandfathered = cb.personal_budget(
                emitter, cb.GRANDFATHERING
            )["budget_tonnes"]
            low, high = min(equal, grandfathered), max(equal, grandfathered)
            for year in (2030, 2040, 2050, 2070, 2100):
                with self.subTest(emitter=emitter, year=year):
                    value = cb.personal_budget(
                        emitter, cb.CONTRACTION_CONVERGENCE, convergence_year=year
                    )["budget_tonnes"]
                    self.assertGreaterEqual(value, low - 1e-3)
                    self.assertLessEqual(value, high + 1e-3)

    def test_a_later_convergence_favours_a_high_emitter(self):
        # Which is exactly why the convergence date is the negotiation.
        values = [
            cb.personal_budget(
                HIGH_EMITTER, cb.CONTRACTION_CONVERGENCE, convergence_year=year
            )["budget_tonnes"]
            for year in (2030, 2040, 2050, 2070, 2100)
        ]
        for earlier, later in zip(values, values[1:]):
            self.assertGreater(later, earlier)

    def test_ability_to_pay_gives_a_high_earner_less(self):
        rich = cb.personal_budget(
            HIGH_EMITTER, cb.ABILITY_TO_PAY, income=90000.0
        )
        poor = cb.personal_budget(
            HIGH_EMITTER, cb.ABILITY_TO_PAY, income=3000.0
        )
        self.assertLess(rich["budget_tonnes"], poor["budget_tonnes"])

    def test_ability_to_pay_at_the_average_income_is_the_equal_share(self):
        equal = cb.personal_budget(HIGH_EMITTER, cb.EQUAL_PER_CAPITA)
        average = cb.personal_budget(
            HIGH_EMITTER, cb.ABILITY_TO_PAY, income=cb.WORLD_AVERAGE_INCOME
        )
        self.assertAlmostEqual(
            average["budget_tonnes"], equal["budget_tonnes"], places=6
        )

    def test_a_zero_elasticity_removes_the_income_effect(self):
        flat = cb.personal_budget(
            HIGH_EMITTER, cb.ABILITY_TO_PAY, income=90000.0, elasticity=0.0
        )
        equal = cb.personal_budget(HIGH_EMITTER, cb.EQUAL_PER_CAPITA)
        self.assertAlmostEqual(
            flat["budget_tonnes"], equal["budget_tonnes"], places=6
        )

    def test_a_negative_income_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.personal_budget(HIGH_EMITTER, cb.ABILITY_TO_PAY, income=-100.0)

    def test_a_negative_elasticity_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.personal_budget(
                HIGH_EMITTER, cb.ABILITY_TO_PAY, income=50000.0, elasticity=-1.0
            )

    def test_zero_emissions_are_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.personal_budget(0.0)

    def test_an_unknown_principle_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.personal_budget(HIGH_EMITTER, "first_come_first_served")

    def test_the_principles_disagree_by_a_large_factor(self):
        comparison = cb.compare_principles(HIGH_EMITTER, income=45000.0)
        self.assertGreater(comparison["ratio"], 3.0)

    def test_the_comparison_is_ordered(self):
        rows = cb.compare_principles(HIGH_EMITTER)["rows"]
        for earlier, later in zip(rows, rows[1:]):
            self.assertLessEqual(earlier["budget_tonnes"], later["budget_tonnes"])

    def test_all_four_principles_appear(self):
        rows = cb.compare_principles(HIGH_EMITTER)["rows"]
        self.assertEqual({row["principle"] for row in rows}, set(cb.PRINCIPLES))


class TestPathways(unittest.TestCase):
    """The rate that spends exactly the budget, checked by integration."""

    def setUp(self):
        self.budget = cb.personal_budget(
            LOW_EMITTER, cb.EQUAL_PER_CAPITA, target=2.0, likelihood=50
        )["budget_tonnes"]

    def test_constant_percentage_spends_exactly_the_budget(self):
        # Sum e0(1-r)^t over all t must equal the budget if r = e0/budget.
        result = cb.required_rate(LOW_EMITTER, self.budget, cb.CONSTANT_PERCENTAGE)
        rate = result["annual_reduction"]
        total = sum(LOW_EMITTER * ((1.0 - rate) ** t) for t in range(4000))
        self.assertAlmostEqual(total, self.budget, places=3)

    def test_linear_spends_exactly_the_budget(self):
        # The triangle under a straight line to zero.
        result = cb.required_rate(LOW_EMITTER, self.budget, cb.LINEAR)
        years = result["years_to_zero"]
        self.assertAlmostEqual(LOW_EMITTER * years / 2.0, self.budget, places=6)

    def test_exponential_spends_exactly_the_budget(self):
        # Integral of e0 e^-kt is e0/k.
        result = cb.required_rate(LOW_EMITTER, self.budget, cb.EXPONENTIAL)
        continuous = -math.log(1.0 - result["annual_reduction"])
        self.assertAlmostEqual(LOW_EMITTER / continuous, self.budget, places=5)

    def test_a_bigger_budget_needs_a_gentler_rate(self):
        rates = [
            cb.required_rate(LOW_EMITTER, budget)["annual_reduction"]
            for budget in (20.0, 40.0, 80.0, 160.0)
        ]
        for earlier, later in zip(rates, rates[1:]):
            self.assertLess(later, earlier)

    def test_a_spent_budget_has_no_solution(self):
        result = cb.required_rate(LOW_EMITTER, 0.0)
        self.assertFalse(result["achievable"])
        self.assertIsNone(result["annual_reduction"])
        self.assertTrue(result["reason"])

    def test_a_budget_under_one_year_is_unachievable(self):
        result = cb.required_rate(10.0, 5.0, cb.CONSTANT_PERCENTAGE)
        self.assertFalse(result["achievable"])

    def test_a_rate_above_the_ceiling_is_flagged_as_not_a_plan(self):
        result = cb.required_rate(12.0, 25.0, cb.CONSTANT_PERCENTAGE)
        self.assertTrue(result["achievable"])
        self.assertFalse(result["feasible"])
        self.assertIn("collapse", result["reason"])

    def test_a_comfortable_budget_is_feasible(self):
        result = cb.required_rate(2.0, 200.0, cb.CONSTANT_PERCENTAGE)
        self.assertTrue(result["feasible"])
        self.assertEqual(result["reason"], "")

    def test_an_unknown_pathway_is_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.required_rate(LOW_EMITTER, self.budget, "hope")

    def test_zero_emissions_are_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.required_rate(0.0, self.budget)

    def test_every_pathway_declines(self):
        for pathway in cb.PATHWAYS:
            rows = cb.pathway_series(LOW_EMITTER, self.budget, pathway, years=30)
            with self.subTest(pathway=pathway):
                for earlier, later in zip(rows, rows[1:]):
                    self.assertLessEqual(
                        later["emissions_tonnes"],
                        earlier["emissions_tonnes"] + 1e-9,
                    )

    def test_every_pathway_starts_at_current_emissions(self):
        for pathway in cb.PATHWAYS:
            rows = cb.pathway_series(LOW_EMITTER, self.budget, pathway, years=5)
            with self.subTest(pathway=pathway):
                self.assertAlmostEqual(
                    rows[0]["emissions_tonnes"], LOW_EMITTER, places=4
                )

    def test_the_budget_drains_and_lands_near_zero(self):
        rows = cb.pathway_series(
            LOW_EMITTER, self.budget, cb.CONSTANT_PERCENTAGE, years=400
        )
        self.assertLess(abs(rows[-1]["remaining_budget"]), self.budget * 0.02)


class TestDelayAndShortfall(unittest.TestCase):
    """Why starting late cannot be recovered by finishing harder."""

    def setUp(self):
        self.budget = cb.personal_budget(
            LOW_EMITTER, cb.EQUAL_PER_CAPITA, target=2.0, likelihood=50
        )["budget_tonnes"]

    def test_acting_now_is_the_baseline(self):
        rows = cb.cost_of_delay(LOW_EMITTER, self.budget)
        self.assertEqual(rows[0]["delay_years"], 0)
        self.assertAlmostEqual(rows[0]["multiple_of_acting_now"], 1.0, places=6)

    def test_delay_raises_the_required_rate(self):
        rows = [
            row for row in cb.cost_of_delay(LOW_EMITTER, self.budget)
            if row["annual_reduction"] is not None
        ]
        for earlier, later in zip(rows, rows[1:]):
            self.assertGreater(later["annual_reduction"], earlier["annual_reduction"])

    def test_the_cost_of_delay_compounds(self):
        # Not linear: each year removed from the budget raises the rate by more
        # than the last did.
        rows = [
            row for row in cb.cost_of_delay(LOW_EMITTER, self.budget)
            if row["annual_reduction"] is not None
        ]
        steps = [
            later["annual_reduction"] - earlier["annual_reduction"]
            for earlier, later in zip(rows, rows[1:])
        ]
        normalised = [
            step / (later["delay_years"] - earlier["delay_years"])
            for step, earlier, later in zip(steps, rows, rows[1:])
        ]
        for earlier, later in zip(normalised, normalised[1:]):
            self.assertGreater(later, earlier)

    def test_enough_delay_makes_it_unachievable(self):
        rows = cb.cost_of_delay(LOW_EMITTER, self.budget, delays=(0, 5, 50, 500))
        self.assertTrue(rows[0]["achievable"])
        self.assertFalse(rows[-1]["achievable"])

    def test_a_shortfall_is_reported_when_reduction_cannot_close_it(self):
        result = cb.shortfall(12.0, 25.0)
        self.assertFalse(result["closable_by_reduction"])
        self.assertGreater(result["shortfall_tonnes"], 0.0)
        self.assertIn("removed", result["note"])

    def test_no_shortfall_when_reduction_can_close_it(self):
        result = cb.shortfall(2.0, 500.0)
        self.assertTrue(result["closable_by_reduction"])
        self.assertEqual(result["shortfall_tonnes"], 0.0)

    def test_the_best_case_follows_the_ceiling(self):
        result = cb.shortfall(10.0, 1.0)
        self.assertAlmostEqual(
            result["best_case_cumulative_tonnes"],
            10.0 / cb.FEASIBLE_ANNUAL_REDUCTION,
            places=6,
        )

    def test_zero_emissions_are_refused(self):
        with self.assertRaises(cb.BudgetError):
            cb.shortfall(0.0, 100.0)
        with self.assertRaises(cb.BudgetError):
            cb.cost_of_delay(0.0, 100.0)


class TestSensitivityAndInsights(unittest.TestCase):
    """The parameters, and the plain-language layer."""

    def test_all_three_parameters_appear(self):
        parameters = {row["parameter"] for row in cb.sensitivity(HIGH_EMITTER)}
        self.assertEqual(
            parameters,
            {"Budget definition", "Equity principle", "Convergence date"},
        )

    def test_every_row_is_labelled_and_positive(self):
        for row in cb.sensitivity(HIGH_EMITTER):
            with self.subTest(setting=row["setting"]):
                self.assertTrue(row["setting"])
                self.assertGreaterEqual(row["budget_tonnes"], 0.0)

    def test_the_budget_definition_spans_a_wide_range(self):
        rows = [
            row for row in cb.sensitivity(HIGH_EMITTER)
            if row["parameter"] == "Budget definition"
        ]
        values = [row["budget_tonnes"] for row in rows]
        self.assertGreater(max(values) / min(values), 3.0)

    def test_insights_are_produced(self):
        insights = cb.get_budget_insights(cb.compare_principles(HIGH_EMITTER))
        self.assertTrue(insights)
        for line in insights:
            self.assertIsInstance(line, str)

    def test_the_grandfathering_warning_appears_for_a_high_emitter(self):
        insights = cb.get_budget_insights(cb.compare_principles(HIGH_EMITTER))
        self.assertTrue(any("Grandfathering" in line for line in insights))

    def test_an_empty_comparison_says_so(self):
        self.assertEqual(cb.get_budget_insights({}), ["Nothing to analyse."])


class TestStorage(unittest.TestCase):
    """Persistence, against a throwaway src.core.database."""

    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.original = cb.DB_NAME
        cb.DB_NAME = self.path
        cb.init_budget_db()
        self.result = cb.personal_budget(HIGH_EMITTER)

    def tearDown(self):
        cb.DB_NAME = self.original
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_init_is_idempotent(self):
        self.assertTrue(cb.init_budget_db())
        self.assertTrue(cb.init_budget_db())

    def test_a_saved_scenario_comes_back(self):
        scenario_id = cb.save_scenario(1, "Mine", self.result)
        self.assertIsNotNone(scenario_id)
        scenarios = cb.get_scenarios(1)
        self.assertEqual(len(scenarios), 1)
        self.assertEqual(scenarios[0]["name"], "Mine")

    def test_the_target_and_likelihood_are_stored(self):
        cb.save_scenario(1, "Mine", self.result)
        stored = cb.get_scenarios(1)[0]
        self.assertAlmostEqual(stored["target"], self.result["target"])
        self.assertEqual(stored["likelihood"], self.result["likelihood"])

    def test_detail_survives_the_round_trip(self):
        cb.save_scenario(1, "Mine", self.result)
        stored = cb.get_scenarios(1)[0]["detail"]
        self.assertEqual(stored["principle"], self.result["principle"])

    def test_scenarios_are_newest_first(self):
        for name in ("first", "second", "third"):
            cb.save_scenario(1, name, self.result)
        self.assertEqual(cb.get_scenarios(1)[0]["name"], "third")

    def test_users_do_not_see_each_other(self):
        cb.save_scenario(1, "mine", self.result)
        cb.save_scenario(2, "theirs", self.result)
        self.assertEqual(len(cb.get_scenarios(1)), 1)

    def test_delete_removes_it(self):
        scenario_id = cb.save_scenario(1, "gone", self.result)
        self.assertTrue(cb.delete_scenario(scenario_id, 1))
        self.assertEqual(cb.get_scenarios(1), [])

    def test_you_cannot_delete_someone_elses(self):
        scenario_id = cb.save_scenario(1, "mine", self.result)
        self.assertFalse(cb.delete_scenario(scenario_id, 2))

    def test_the_limit_is_respected(self):
        for n in range(5):
            cb.save_scenario(1, f"s{n}", self.result)
        self.assertEqual(len(cb.get_scenarios(1, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()
