"""Tests for the optimal replacement timing engine.

The load-bearing tests are the sign-flip ones. The claim the module makes is
that a decarbonising grid pushes electrification and efficiency in opposite
directions, and that a payback ratio cannot represent either. If those two
regimes ever collapse into the same recommendation, the module is not doing
anything a simpler calculation could not.
"""

import math

import pytest

from src.carbon.replacement_timing import (
    FUELS,
    GRID_FLOOR,
    MAX_HORIZON,
    ReplacementTimingError,
    break_even_grid_intensity,
    build_grid,
    build_unit,
    compare_objectives,
    delete_plan,
    evaluate,
    evaluate_year,
    expected_failure_year,
    failure_distribution,
    fuel_intensity,
    get_fuel,
    get_plans,
    get_timing_insights,
    grid_intensity,
    grid_sensitivity,
    horizon_sensitivity,
    list_fuels,
    regret,
    save_plan,
    scrappage_charge,
    survival_probability,
    weibull_scale,
)


def _boiler(age=8.0):
    return build_unit(
        "Gas boiler", "natural_gas", 18_000, 20, 900, age_years=age
    )


def _heat_pump():
    return build_unit(
        "Heat pump", "electricity", 6_000, 20, 2_400, capital_cost=9_000
    )


def _old_fridge():
    return build_unit(
        "Old fridge", "electricity", 300, 15, 320, age_years=3
    )


def _new_fridge():
    return build_unit(
        "New fridge", "electricity", 200, 15, 420, capital_cost=750
    )


# ---------------------------------------------------------------------------
# The sign flip
# ---------------------------------------------------------------------------

class TestSignFlip:

    def test_a_static_grid_says_never_electrify_on_a_dirty_one(self):
        # At 0.71 kg/kWh a heat pump is dirtier than the boiler it replaces.
        # With no decarbonisation there is no year at which that changes.
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.71, 0.0), 25)
        assert result["optimal_carbon_year"] == 25

    def test_a_decarbonising_grid_turns_never_into_a_date(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.71, 0.06), 25)
        assert 0 < result["optimal_carbon_year"] < 25

    def test_faster_decarbonisation_brings_the_date_forward(self):
        years = [
            evaluate(
                _boiler(), _heat_pump(), build_grid(0.71, decline), 25
            )["optimal_carbon_year"]
            for decline in (0.02, 0.04, 0.06)
        ]
        assert years == sorted(years, reverse=True)

    def test_the_recommendation_moves_by_decades_across_plausible_declines(self):
        sensitivity = grid_sensitivity(
            _boiler(), _heat_pump(), 25, initial_intensity=0.71
        )
        assert sensitivity["recommendation_moves"] is True
        assert sensitivity["span"] > 10

    def test_efficiency_runs_the_other_way(self):
        # Replacing an electric appliance with a more efficient electric one
        # saves emissions that are themselves shrinking. A decarbonising grid
        # makes waiting worse for electrification and better here.
        static = evaluate(
            _old_fridge(), _new_fridge(), build_grid(0.30, 0.0), 20
        )
        declining = evaluate(
            _old_fridge(), _new_fridge(), build_grid(0.30, 0.05), 20
        )
        assert declining["optimal_carbon_year"] > static["optimal_carbon_year"]

    def test_a_clean_grid_can_make_an_efficiency_upgrade_not_worth_doing(self):
        result = evaluate(
            _old_fridge(), _new_fridge(), build_grid(0.30, 0.05), 20
        )
        assert result["optimal_carbon_year"] == 20
        assert result["acting_now_costs"] > 0


# ---------------------------------------------------------------------------
# Grid and fuels
# ---------------------------------------------------------------------------

class TestGrid:

    def test_a_declining_grid_declines(self):
        grid = build_grid(0.40, 0.05)
        assert grid_intensity(grid, 10) < grid_intensity(grid, 0)

    def test_a_static_grid_does_not(self):
        grid = build_grid(0.40, 0.0)
        assert grid_intensity(grid, 30) == pytest.approx(0.40)

    def test_the_floor_stops_the_grid_reaching_zero(self):
        # Extrapolating an exponential to zero produces a free grid within a
        # lifetime, which is not a forecast to buy a boiler against.
        grid = build_grid(0.40, 0.20)
        assert grid_intensity(grid, 100) == pytest.approx(GRID_FLOOR)

    def test_gas_does_not_improve_with_time(self):
        grid = build_grid(0.40, 0.10)
        assert fuel_intensity("natural_gas", grid, 0) == fuel_intensity(
            "natural_gas", grid, 30
        )

    def test_electricity_does(self):
        grid = build_grid(0.40, 0.10)
        assert fuel_intensity("electricity", grid, 30) < fuel_intensity(
            "electricity", grid, 0
        )

    def test_a_decline_of_one_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="below 1"):
            build_grid(0.40, 1.0)

    def test_a_non_positive_intensity_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="must be positive"):
            build_grid(0.0, 0.05)

    def test_a_floor_above_the_start_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="gets dirtier"):
            build_grid(0.10, 0.05, floor=0.20)

    def test_negative_years_are_refused(self):
        with pytest.raises(ReplacementTimingError, match="start at zero"):
            grid_intensity(build_grid(), -1)

    def test_an_unknown_fuel_is_refused_with_the_list(self):
        with pytest.raises(ReplacementTimingError, match="Known:"):
            fuel_intensity("firewood", build_grid(), 0)

    def test_only_electricity_is_grid_linked(self):
        linked = {entry["key"] for entry in list_fuels() if entry["grid_linked"]}
        assert linked == {"electricity"}

    def test_every_fuel_carries_a_note(self):
        for entry in list_fuels():
            assert len(entry["note"]) > 40

    def test_get_fuel_returns_none_for_an_unknown_key(self):
        assert get_fuel("unobtanium") is None


# ---------------------------------------------------------------------------
# Units and failure
# ---------------------------------------------------------------------------

class TestUnits:

    def test_remaining_life_accounts_for_age(self):
        assert _boiler(age=8)["remaining_life_years"] == pytest.approx(12.0)

    def test_an_over_age_unit_has_no_remaining_life_rather_than_negative(self):
        assert build_unit(
            "Ancient", "natural_gas", 100, 10, 100, age_years=15
        )["remaining_life_years"] == 0.0

    def test_the_weibull_scale_reproduces_the_rated_life_as_a_mean(self):
        unit = _boiler(age=0)
        scale = weibull_scale(unit)
        mean = scale * math.gamma(1.0 + 1.0 / unit["weibull_shape"])
        assert mean == pytest.approx(unit["expected_life_years"], rel=1e-9)

    def test_survival_falls_with_time(self):
        unit = _boiler()
        probabilities = [survival_probability(unit, year) for year in range(0, 20, 2)]
        assert probabilities == sorted(probabilities, reverse=True)

    def test_survival_starts_at_certainty(self):
        assert survival_probability(_boiler(), 0) == pytest.approx(1.0)

    def test_survival_is_conditioned_on_current_age(self):
        # An appliance that has already survived twelve years is not the same
        # risk as a new one with the same rated life.
        young = survival_probability(_boiler(age=0), 10)
        old = survival_probability(_boiler(age=12), 10)
        assert old < young

    def test_a_higher_shape_concentrates_failure_near_the_rated_life(self):
        gentle = build_unit("a", "electricity", 100, 15, 100, weibull_shape=1.2)
        sharp = build_unit("b", "electricity", 100, 15, 100, weibull_shape=6.0)
        assert survival_probability(sharp, 5) > survival_probability(gentle, 5)

    def test_the_failure_distribution_never_exceeds_certainty(self):
        distribution = failure_distribution(_boiler(), 40)
        assert sum(row["fails_this_year"] for row in distribution) <= 1.0

    def test_failure_probabilities_and_survival_reconcile(self):
        unit = _boiler()
        distribution = failure_distribution(unit, 25)
        total = sum(row["fails_this_year"] for row in distribution)
        assert total + survival_probability(unit, 25) == pytest.approx(1.0, rel=1e-9)

    def test_the_expected_failure_year_sits_inside_the_horizon(self):
        failure = expected_failure_year(_boiler(), 25)
        assert 0 < failure["expected_year"] < 25

    def test_a_negative_age_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="cannot be negative"):
            build_unit("x", "electricity", 100, 10, 50, age_years=-1)

    def test_a_zero_life_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="must be positive"):
            build_unit("x", "electricity", 100, 0, 50)

    def test_a_zero_weibull_shape_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="shape must be positive"):
            build_unit("x", "electricity", 100, 10, 50, weibull_shape=0)


# ---------------------------------------------------------------------------
# Scrappage
# ---------------------------------------------------------------------------

class TestScrappage:

    def test_scrapping_early_costs_the_unused_share(self):
        # Twelve of twenty years left, so sixty percent of the embodied
        # carbon is being thrown away.
        assert scrappage_charge(_boiler(age=8), 0) == pytest.approx(900 * 0.6)

    def test_waiting_reduces_the_charge(self):
        boiler = _boiler()
        assert scrappage_charge(boiler, 5) < scrappage_charge(boiler, 0)

    def test_it_reaches_zero_at_the_end_of_the_rated_life(self):
        assert scrappage_charge(_boiler(age=8), 12) == 0.0

    def test_it_never_goes_negative(self):
        assert scrappage_charge(_boiler(age=8), 30) == 0.0

    def test_it_appears_in_the_act_now_path(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.30, 0.03), 25)
        assert result["act_now"]["scrappage_carbon"] > 0

    def test_the_do_nothing_path_carries_none_of_it(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.30, 0.03), 25)
        assert result["do_nothing"]["scrappage_carbon"] == 0.0
        assert result["do_nothing"]["embodied_carbon"] == 0.0


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class TestEvaluation:

    def test_a_path_is_produced_for_every_year_including_never(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.40, 0.03), 25)
        assert len(result["paths"]) == 26
        assert result["paths"][-1]["do_nothing"] is True

    def test_the_do_nothing_path_is_pure_operation(self):
        path = evaluate_year(
            _boiler(), _heat_pump(), build_grid(0.40, 0.03), 25, 25
        )
        assert path["total_carbon"] == pytest.approx(path["operating_carbon"])
        assert path["capital_cost"] == 0.0

    def test_acting_now_carries_the_full_capital_cost_undiscounted(self):
        path = evaluate_year(
            _boiler(), _heat_pump(), build_grid(0.40, 0.03), 25, 0
        )
        assert path["capital_cost"] == pytest.approx(9_000)

    def test_waiting_discounts_the_capital_cost(self):
        later = evaluate_year(
            _boiler(), _heat_pump(), build_grid(0.40, 0.03), 25, 10
        )
        assert later["capital_cost"] < 9_000

    def test_a_falling_capital_cost_rewards_waiting_further(self):
        flat = evaluate_year(
            _boiler(), _heat_pump(), build_grid(0.40, 0.03), 25, 10,
            capital_decline=0.0,
        )
        falling = evaluate_year(
            _boiler(), _heat_pump(), build_grid(0.40, 0.03), 25, 10,
            capital_decline=0.05,
        )
        assert falling["capital_cost"] < flat["capital_cost"]

    def test_the_survival_probability_travels_with_every_path(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.40, 0.03), 25)
        probabilities = [row["survival_probability"] for row in result["paths"]]
        assert probabilities == sorted(probabilities, reverse=True)

    def test_a_replacement_year_outside_the_horizon_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="outside the horizon"):
            evaluate_year(_boiler(), _heat_pump(), build_grid(), 25, 30)

    def test_a_missing_incumbent_points_at_the_payback_module(self):
        with pytest.raises(ReplacementTimingError, match="carbon_payback"):
            evaluate(None, _heat_pump(), build_grid(), 25)

    def test_a_horizon_shorter_than_the_new_unit_is_refused(self):
        # It would cut off part of the new unit's operating burden and
        # flatter it, which is the direction this whole module argues against.
        with pytest.raises(ReplacementTimingError, match="flatter it"):
            evaluate(_boiler(), _heat_pump(), build_grid(), 15)

    def test_an_absurd_horizon_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="longer than the"):
            evaluate(_boiler(), _heat_pump(), build_grid(), MAX_HORIZON + 1)

    def test_a_negative_discount_rate_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="Discount rate"):
            evaluate_year(
                _boiler(), _heat_pump(), build_grid(), 25, 0, discount_rate=-0.1
            )


# ---------------------------------------------------------------------------
# Objectives
# ---------------------------------------------------------------------------

class TestObjectives:

    def test_carbon_and_cost_are_reported_separately(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.40, 0.04), 25)
        comparison = compare_objectives(result)
        assert "carbon_optimum" in comparison
        assert "cost_optimum" in comparison

    def test_the_disagreement_is_surfaced_rather_than_averaged(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.40, 0.04), 25)
        if not result["objectives_agree"]:
            assert any(
                "disagree about when" in item["title"]
                for item in get_timing_insights(result)
            )

    def test_the_penalty_of_each_choice_is_quantified(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.40, 0.04), 25)
        comparison = compare_objectives(result)
        assert comparison["carbon_penalty_of_cost_choice"] >= 0
        assert comparison["cost_penalty_of_carbon_choice"] >= -1e-9

    def test_a_shadow_price_produces_a_combined_optimum_only_when_asked(self):
        without = evaluate(_boiler(), _heat_pump(), build_grid(0.40, 0.04), 25)
        assert without["optimal_combined_year"] is None
        withprice = evaluate(
            _boiler(), _heat_pump(), build_grid(0.40, 0.04), 25,
            shadow_carbon_price=120.0,
        )
        assert withprice["optimal_combined_year"] is not None
        assert withprice["shadow_carbon_price"] == 120.0

    def test_a_negative_shadow_price_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="cannot be negative"):
            evaluate(
                _boiler(), _heat_pump(), build_grid(), 25,
                shadow_carbon_price=-10,
            )


# ---------------------------------------------------------------------------
# Regret
# ---------------------------------------------------------------------------

class TestRegret:

    def _result(self):
        return evaluate(_boiler(), _heat_pump(), build_grid(0.71, 0.05), 25)

    def test_the_optimum_is_never_worse_than_its_neighbours(self):
        penalties = regret(self._result())
        for side in ("one_year_early", "one_year_late"):
            if penalties[side] is not None:
                assert penalties[side] >= -1e-9

    def test_early_and_late_are_not_symmetric(self):
        penalties = regret(self._result())
        assert penalties["one_year_early"] != penalties["one_year_late"]

    def test_acting_now_and_never_acting_are_both_priced(self):
        penalties = regret(self._result())
        assert penalties["acting_now"] >= 0
        assert penalties["never_acting"] >= 0

    def test_a_flat_optimum_says_the_timing_is_not_the_decision(self):
        penalties = regret(self._result())
        if penalties["flat_optimum"]:
            assert "not the decision" in penalties["note"]
        else:
            assert "sharp" in penalties["note"]

    def test_regret_can_be_asked_about_cost_instead(self):
        penalties = regret(self._result(), objective="cost")
        assert penalties["objective"] == "cost"

    def test_a_blended_objective_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="not blended"):
            regret(self._result(), objective="everything")


# ---------------------------------------------------------------------------
# Break-even and robustness
# ---------------------------------------------------------------------------

class TestBreakEven:

    def test_a_threshold_is_found_where_one_exists(self):
        result = break_even_grid_intensity(_old_fridge(), _new_fridge(), 20)
        assert result["break_even_intensity"] is not None
        assert 0 < result["break_even_intensity"] < 2

    def test_the_threshold_actually_separates_the_two_answers(self):
        threshold = break_even_grid_intensity(
            _old_fridge(), _new_fridge(), 20
        )["break_even_intensity"]
        above = evaluate(
            _old_fridge(), _new_fridge(), build_grid(threshold * 1.5, 0.0), 20
        )
        below = evaluate(
            _old_fridge(), _new_fridge(), build_grid(threshold * 0.5, 0.0), 20
        )
        assert above["optimal_carbon_year"] < below["optimal_carbon_year"]

    def test_no_threshold_is_a_stronger_answer_than_a_number(self):
        result = break_even_grid_intensity(_boiler(), _heat_pump(), 25)
        if result["break_even_intensity"] is None:
            assert "stronger answer" in result["note"]

    def test_horizon_sensitivity_catches_a_boundary_artefact(self):
        # The fridge's "wait twelve years" at a twenty-year horizon becomes
        # "act now" at twenty-five, because the new unit's embodied charge is
        # pro-rated to the life used inside the window.
        sensitivity = horizon_sensitivity(
            _old_fridge(), _new_fridge(), build_grid(0.30, 0.0)
        )
        assert sensitivity["optimum_moves"] is True
        years = [row["optimal_carbon_year"] for row in sensitivity["rows"]]
        assert years[0] > years[-1]

    def test_a_robust_recommendation_says_so(self):
        sensitivity = horizon_sensitivity(
            _boiler(), _heat_pump(), build_grid(0.71, 0.04)
        )
        assert sensitivity["decision_flips"] is False
        assert "about the appliance" in sensitivity["note"]

    def test_a_horizon_set_too_short_for_the_unit_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="long enough"):
            horizon_sensitivity(
                _boiler(), _heat_pump(), build_grid(), horizons=(5, 10)
            )


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

class TestInsights:

    def test_an_immediate_optimum_says_act_now(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.30, 0.02), 25)
        if result["optimal_carbon_year"] == 0:
            assert any(
                item["title"] == "Act now" for item in get_timing_insights(result)
            )

    def test_a_terminal_optimum_says_do_not_replace(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.71, 0.0), 25)
        assert any(
            "Do not replace" in item["title"]
            for item in get_timing_insights(result)
        )

    def test_an_interior_optimum_is_named_as_one(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.71, 0.06), 25)
        assert any(
            item["title"].startswith("Wait ")
            for item in get_timing_insights(result)
        )

    def test_scrapped_life_is_always_reported_when_it_exists(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.40, 0.03), 25)
        assert any(
            "paid-for life" in item["title"]
            for item in get_timing_insights(result)
        )

    def test_a_low_survival_probability_earns_a_warning(self):
        # A boiler already 17 years into a 20-year rated life, with the
        # optimum ten years out. The plan assumes it survives; there is a
        # 34% chance it does, and saying so is the point.
        old = build_unit(
            "Very old boiler", "natural_gas", 18_000, 20, 900, age_years=17
        )
        result = evaluate(old, _heat_pump(), build_grid(0.71, 0.02), 25)
        assert result["optimal_carbon_year"] > 0
        assert result["paths"][result["optimal_carbon_year"]][
            "survival_probability"
        ] < 0.7
        assert any(
            "will not last that long" in item["title"]
            for item in get_timing_insights(result)
        )

    def test_a_healthy_incumbent_earns_no_such_warning(self):
        result = evaluate(_boiler(age=2), _heat_pump(), build_grid(0.71, 0.06), 25)
        assert not any(
            "will not last that long" in item["title"]
            for item in get_timing_insights(result)
        )

    def test_every_insight_has_a_level_and_a_body(self):
        result = evaluate(_boiler(), _heat_pump(), build_grid(0.71, 0.06), 25)
        for item in get_timing_insights(result):
            assert item["level"] in {"info", "warning"}
            assert item["title"] and item["body"]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.carbon.replacement_timing.DB_NAME", str(tmp_path / "test.db")
        )

    def _result(self):
        return evaluate(_boiler(), _heat_pump(), build_grid(0.71, 0.05), 25)

    def test_a_saved_plan_comes_back(self):
        row_id = save_plan("user-1", self._result())
        saved = get_plans("user-1")
        assert len(saved) == 1
        assert saved[0]["id"] == row_id
        assert saved[0]["incumbent"] == "Gas boiler"
        assert saved[0]["replacement"] == "Heat pump"

    def test_both_optima_are_stored_as_columns(self):
        result = self._result()
        save_plan("user-1", result)
        saved = get_plans("user-1")[0]
        assert saved["optimal_carbon_year"] == result["optimal_carbon_year"]
        assert saved["optimal_cost_year"] == result["optimal_cost_year"]

    def test_the_payload_keeps_the_grid_assumption(self):
        save_plan("user-1", self._result())
        payload = get_plans("user-1")[0]["payload"]
        assert payload["grid"]["decline"] == pytest.approx(0.05)
        assert payload["incumbent_fuel"] == "natural_gas"

    def test_users_do_not_see_each_others_plans(self):
        save_plan("user-1", self._result())
        save_plan("user-2", self._result())
        assert len(get_plans("user-1")) == 1
        assert len(get_plans("user-2")) == 1

    def test_saving_without_a_user_is_refused(self):
        with pytest.raises(ReplacementTimingError, match="needs a user"):
            save_plan("", self._result())

    def test_reading_without_a_user_returns_nothing(self):
        assert get_plans(None) == []

    def test_deleting_removes_the_row(self):
        row_id = save_plan("user-1", self._result())
        assert delete_plan("user-1", row_id) is True
        assert get_plans("user-1") == []

    def test_deleting_another_users_row_does_nothing(self):
        row_id = save_plan("user-1", self._result())
        assert delete_plan("user-2", row_id) is False
        assert len(get_plans("user-1")) == 1

    def test_deleting_without_a_user_returns_false(self):
        assert delete_plan(None, 1) is False
