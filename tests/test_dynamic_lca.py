"""Tests for the time-explicit LCA engine.

The load-bearing tests are the calibration ones. The whole argument of the
module is that any gap between its answer and the conventional answer is a
timing effect, and that claim is only true if the physics is anchored to the
same published values the conventional answer uses. If the anchor drifts,
every result becomes an unattributable mixture of timing and parameterisation
and the module is worse than useless.
"""

import math

import pytest

from src.carbon.dynamic_lca import (
    CO2_IRF_A0,
    CO2_IRF_TERMS,
    GASES,
    METRICS,
    REFERENCE_HORIZON,
    DynamicLCAError,
    absolute_gwp,
    build_emission,
    build_inventory,
    category_table,
    characterisation_factor,
    compare_inventories,
    cumulative_forcing,
    delayed_emission_credit,
    delete_inventory,
    describe_metric,
    dominant_divergence,
    dynamic_payback_year,
    dynamic_score,
    emission_table,
    expand_annual,
    expand_first_order_decay,
    forcing_series,
    get_dynamic_insights,
    get_gas,
    get_inventories,
    gwp,
    impulse_response,
    instantaneous_forcing,
    list_gases,
    list_metrics,
    merge_inventories,
    metric_comparison,
    model_fidelity,
    peak_forcing,
    radiative_efficiency,
    save_inventory,
    static_score,
    temporary_storage_credit,
    ton_year_equivalence,
)


# ---------------------------------------------------------------------------
# Calibration: the anchor the whole module rests on
# ---------------------------------------------------------------------------

class TestCalibration:

    def test_co2_gwp100_is_exactly_one(self):
        assert gwp("co2", 100) == pytest.approx(1.0, abs=1e-12)

    @pytest.mark.parametrize("key", sorted(GASES))
    def test_every_gas_reproduces_its_published_gwp100(self, key):
        assert gwp(key, REFERENCE_HORIZON) == pytest.approx(
            GASES[key]["gwp100"], rel=1e-9
        )

    def test_co2_absolute_gwp_matches_the_published_value(self):
        # 9.17e-14 W m-2 yr kg-1 is the figure quoted in AR5 and AR6 and is
        # the denominator of every GWP in circulation.
        assert absolute_gwp("co2", 100) == pytest.approx(9.17e-14, rel=0.01)

    def test_impulse_response_weights_sum_to_one_at_time_zero(self):
        assert impulse_response("co2", 0) == pytest.approx(1.0, abs=1e-12)

    def test_co2_irf_coefficients_sum_to_one(self):
        total = CO2_IRF_A0 + sum(weight for weight, _ in CO2_IRF_TERMS)
        assert total == pytest.approx(1.0, abs=1e-9)

    def test_co2_retains_a_permanent_fraction(self):
        # The property a single-exponential model cannot represent, and the
        # reason CO2 is handled separately throughout.
        assert impulse_response("co2", 10_000) == pytest.approx(
            CO2_IRF_A0, abs=1e-6
        )

    def test_methane_is_effectively_gone_after_a_century(self):
        assert impulse_response("ch4_fossil", 100) < 0.001

    def test_model_fidelity_reports_methane_as_the_outlier(self):
        rows = model_fidelity()
        assert rows[0]["key"] == "ch4_fossil"
        assert rows[0]["deviation"] > 0.05
        assert rows[0]["within_tolerance"] is False

    def test_every_other_gas_is_within_tolerance_at_twenty_years(self):
        for row in model_fidelity():
            if row["key"] == "ch4_fossil":
                continue
            assert row["within_tolerance"], row

    def test_radiative_efficiency_ordering_follows_potency(self):
        assert radiative_efficiency("sf6") > radiative_efficiency("hfc134a")
        assert radiative_efficiency("hfc134a") > radiative_efficiency("n2o")
        assert radiative_efficiency("n2o") > radiative_efficiency("co2")


# ---------------------------------------------------------------------------
# The characterisation factor identity
# ---------------------------------------------------------------------------

class TestCharacterisationFactor:

    def test_co2_now_scored_a_century_out_is_exactly_one(self):
        # The anchor. Everything else on the page is read as a departure
        # from this, so it has to be exact rather than close.
        assert characterisation_factor("co2", 0, 100) == pytest.approx(
            1.0, abs=1e-12
        )

    def test_absolute_years_give_the_same_answer_as_relative_ones(self):
        assert characterisation_factor("co2", 2026, 2126) == pytest.approx(
            characterisation_factor("co2", 0, 100), rel=1e-12
        )

    def test_a_later_emission_scores_lower_against_a_fixed_target(self):
        early = characterisation_factor("co2", 2026, 2100)
        late = characterisation_factor("co2", 2070, 2100)
        assert late < early

    def test_the_factor_falls_monotonically_with_emission_year(self):
        factors = [
            characterisation_factor("co2", year, 2100)
            for year in range(2026, 2100, 5)
        ]
        assert factors == sorted(factors, reverse=True)

    def test_an_emission_in_the_target_year_scores_zero(self):
        assert characterisation_factor("co2", 2100, 2100) == 0.0

    def test_methane_decays_out_faster_than_carbon_dioxide(self):
        # Both lose value as the window shortens; methane keeps more of its
        # own value for longer because it delivers its effect early.
        co2_share = (
            characterisation_factor("co2", 2070, 2100)
            / characterisation_factor("co2", 2026, 2100)
        )
        ch4_share = (
            characterisation_factor("ch4_fossil", 2070, 2100)
            / characterisation_factor("ch4_fossil", 2026, 2100)
        )
        assert ch4_share > co2_share

    def test_a_target_before_the_emission_is_refused(self):
        with pytest.raises(DynamicLCAError, match="before the emission"):
            characterisation_factor("co2", 2100, 2050)

    def test_sulphur_hexafluoride_barely_notices_the_window(self):
        # A three-thousand-year lifetime against a seventy-four-year window.
        ratio = (
            characterisation_factor("sf6", 2026, 2100)
            / gwp("sf6", REFERENCE_HORIZON)
        )
        assert 0.6 < ratio < 0.85


# ---------------------------------------------------------------------------
# Building inventories
# ---------------------------------------------------------------------------

class TestBuilding:

    def test_an_emission_carries_its_year(self):
        emission = build_emission(2030, "co2", 1000, "boiler", "heating")
        assert emission["year"] == 2030
        assert emission["gas"] == "co2"
        assert emission["amount_kg"] == 1000.0
        assert emission["category"] == "heating"

    def test_gas_keys_are_case_insensitive(self):
        assert build_emission(2030, "CO2", 1)["gas"] == "co2"

    def test_an_unknown_gas_is_refused_with_the_list(self):
        with pytest.raises(DynamicLCAError, match="Known gases"):
            build_emission(2030, "argon", 1)

    def test_negative_amounts_are_allowed_because_removals_exist(self):
        assert build_emission(2030, "co2", -500)["amount_kg"] == -500.0

    def test_a_non_finite_amount_is_refused(self):
        with pytest.raises(DynamicLCAError, match="finite"):
            build_emission(2030, "co2", float("inf"))

    def test_an_empty_inventory_is_refused(self):
        with pytest.raises(DynamicLCAError, match="at least one emission"):
            build_inventory("nothing", [])

    def test_emissions_are_sorted_by_year(self):
        inventory = build_inventory("mixed", [
            build_emission(2040, "co2", 1),
            build_emission(2026, "co2", 1),
            build_emission(2033, "co2", 1),
        ])
        assert [item["year"] for item in inventory["emissions"]] == [
            2026, 2033, 2040
        ]

    def test_base_year_defaults_to_the_first_emission(self):
        inventory = build_inventory("a", [build_emission(2031, "co2", 1)])
        assert inventory["base_year"] == 2031

    def test_a_base_year_after_the_first_emission_is_refused(self):
        with pytest.raises(DynamicLCAError, match="after the first emission"):
            build_inventory(
                "a", [build_emission(2026, "co2", 1)], base_year=2030
            )

    def test_annual_expansion_produces_one_entry_per_year(self):
        series = expand_annual("co2", 100, 2026, 5)
        assert len(series) == 5
        assert [item["year"] for item in series] == [2026, 2027, 2028, 2029, 2030]
        assert sum(item["amount_kg"] for item in series) == 500

    def test_a_zero_length_annual_series_is_refused(self):
        with pytest.raises(DynamicLCAError, match="at least one year"):
            expand_annual("co2", 100, 2026, 0)

    def test_first_order_decay_never_releases_more_than_the_stock(self):
        series = expand_first_order_decay("ch4_biogenic", 1000, 0.05, 2026, 200)
        assert sum(item["amount_kg"] for item in series) <= 1000.0

    def test_first_order_decay_converges_to_the_analytical_total(self):
        stock, rate, years = 1000.0, 0.06, 80
        series = expand_first_order_decay(
            "ch4_biogenic", stock, rate, 2026, years
        )
        expected = stock * (1.0 - math.exp(-rate * years))
        assert sum(item["amount_kg"] for item in series) == pytest.approx(
            expected, rel=1e-12
        )

    def test_first_order_decay_is_front_loaded(self):
        series = expand_first_order_decay("ch4_biogenic", 1000, 0.06, 2026, 40)
        amounts = [item["amount_kg"] for item in series]
        assert amounts == sorted(amounts, reverse=True)

    def test_a_zero_decay_rate_is_refused_rather_than_silently_flat(self):
        with pytest.raises(DynamicLCAError, match="never released"):
            expand_first_order_decay("ch4_biogenic", 1000, 0, 2026, 40)

    def test_merging_preserves_every_emission(self):
        first = build_inventory("a", expand_annual("co2", 10, 2026, 3))
        second = build_inventory("b", expand_annual("ch4_fossil", 1, 2030, 2))
        merged = merge_inventories("both", [first, second])
        assert len(merged["emissions"]) == 5
        assert merged["gases"] == ["ch4_fossil", "co2"]


# ---------------------------------------------------------------------------
# Forcing
# ---------------------------------------------------------------------------

class TestForcing:

    def test_forcing_before_the_emission_is_zero(self):
        inventory = build_inventory("later", [build_emission(2050, "co2", 1000)])
        assert instantaneous_forcing(inventory, 2040) == 0.0

    def test_forcing_decays_after_the_emission(self):
        inventory = build_inventory("pulse", [build_emission(2026, "ch4_fossil", 100)])
        assert (
            instantaneous_forcing(inventory, 2026)
            > instantaneous_forcing(inventory, 2046)
            > instantaneous_forcing(inventory, 2076)
        )

    def test_carbon_dioxide_forcing_never_reaches_zero(self):
        inventory = build_inventory("pulse", [build_emission(2026, "co2", 1000)])
        assert instantaneous_forcing(inventory, 5000) > 0

    def test_cumulative_forcing_is_the_dynamic_total_times_the_reference(self):
        inventory = build_inventory("a", expand_annual("co2", 500, 2026, 10))
        result = dynamic_score(inventory, 2100)
        assert cumulative_forcing(inventory, 2100) == pytest.approx(
            result["dynamic_total_co2e"] * absolute_gwp("co2", 100), rel=1e-12
        )

    def test_a_target_before_the_last_emission_is_refused(self):
        inventory = build_inventory("a", expand_annual("co2", 100, 2026, 30))
        with pytest.raises(DynamicLCAError, match="before the last emission"):
            cumulative_forcing(inventory, 2040)

    def test_the_series_ends_on_the_target_year(self):
        inventory = build_inventory("a", expand_annual("co2", 100, 2026, 5))
        rows = forcing_series(inventory, 2100, step=7)
        assert rows[-1]["year"] == 2100

    def test_the_series_cumulative_column_matches_the_closed_form(self):
        inventory = build_inventory("a", expand_annual("co2", 100, 2026, 5))
        rows = forcing_series(inventory, 2100)
        assert rows[-1]["cumulative_forcing"] == pytest.approx(
            cumulative_forcing(inventory, 2100), rel=1e-12
        )

    def test_a_non_positive_step_is_refused(self):
        inventory = build_inventory("a", expand_annual("co2", 100, 2026, 5))
        with pytest.raises(DynamicLCAError, match="step must be positive"):
            forcing_series(inventory, 2100, step=0)

    def test_a_methane_pulse_peaks_in_the_year_it_is_emitted(self):
        inventory = build_inventory("pulse", [build_emission(2026, "ch4_fossil", 1000)])
        peak = peak_forcing(inventory, 2100)
        assert peak["year"] == 2026
        assert peak["declining_at_target"] is True

    def test_a_sustained_burden_peaks_when_it_stops(self):
        inventory = build_inventory("run", expand_annual("ch4_fossil", 10, 2026, 20))
        peak = peak_forcing(inventory, 2100)
        assert peak["year"] == 2045


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestScoring:

    def test_a_single_co2_pulse_a_century_before_target_matches_static(self):
        inventory = build_inventory("pulse", [build_emission(2026, "co2", 1000)])
        result = dynamic_score(inventory, 2126)
        assert result["dynamic_total_co2e"] == pytest.approx(
            result["static_total_co2e"], rel=1e-9
        )
        assert result["ratio"] == pytest.approx(1.0, rel=1e-9)

    def test_a_shorter_window_scores_below_the_static_figure(self):
        inventory = build_inventory("pulse", [build_emission(2026, "co2", 1000)])
        result = dynamic_score(inventory, 2076)
        assert result["dynamic_total_co2e"] < result["static_total_co2e"]
        assert result["ratio"] < 1.0

    def test_a_longer_window_scores_above_the_static_figure(self):
        inventory = build_inventory("pulse", [build_emission(2026, "co2", 1000)])
        result = dynamic_score(inventory, 2226)
        assert result["ratio"] > 1.0

    def test_the_boiler_case_the_module_exists_for(self):
        # Twenty years of a running boiler, scored to 2100. Static GWP100
        # gives every one of those years a full century; most of them do not
        # have one. The overstatement is large and it is not a rounding error.
        inventory = build_inventory(
            "gas boiler",
            expand_annual("co2", 2000, 2026, 20, "boiler", "heating"),
        )
        result = dynamic_score(inventory, 2100)
        assert result["static_total_co2e"] == pytest.approx(40_000, rel=1e-9)
        assert result["ratio"] < 0.75
        assert result["difference_co2e"] < -10_000

    def test_static_score_is_horizon_dependent_for_short_lived_gases(self):
        inventory = build_inventory("pulse", [build_emission(2026, "ch4_fossil", 100)])
        assert static_score(inventory, 20) > static_score(inventory, 100)

    def test_static_score_is_horizon_independent_for_carbon_dioxide(self):
        inventory = build_inventory("pulse", [build_emission(2026, "co2", 100)])
        assert static_score(inventory, 20) == pytest.approx(
            static_score(inventory, 100), rel=1e-12
        )

    def test_category_totals_sum_to_the_inventory_total(self):
        emissions = (
            expand_annual("co2", 1000, 2026, 10, "car", "transport")
            + expand_annual("co2", 500, 2026, 10, "boiler", "heating")
        )
        result = dynamic_score(build_inventory("home", emissions), 2100)
        assert sum(
            bucket["dynamic"] for bucket in result["by_category"].values()
        ) == pytest.approx(result["dynamic_total_co2e"], rel=1e-12)

    def test_gas_totals_sum_to_the_inventory_total(self):
        emissions = (
            expand_annual("co2", 1000, 2026, 10)
            + expand_annual("ch4_fossil", 20, 2026, 10)
        )
        result = dynamic_score(build_inventory("mixed", emissions), 2100)
        assert sum(
            bucket["static"] for bucket in result["by_gas"].values()
        ) == pytest.approx(result["static_total_co2e"], rel=1e-12)

    def test_removals_reduce_the_total(self):
        with_removal = build_inventory("net", [
            build_emission(2026, "co2", 1000),
            build_emission(2026, "co2", -400),
        ])
        without = build_inventory("gross", [build_emission(2026, "co2", 1000)])
        assert (
            dynamic_score(with_removal, 2100)["dynamic_total_co2e"]
            < dynamic_score(without, 2100)["dynamic_total_co2e"]
        )

    def test_the_emission_table_is_ordered_by_year(self):
        inventory = build_inventory("a", expand_annual("co2", 10, 2026, 5))
        rows = emission_table(dynamic_score(inventory, 2100))
        assert [row["year"] for row in rows] == sorted(row["year"] for row in rows)

    def test_the_category_table_leads_with_the_largest(self):
        emissions = (
            expand_annual("co2", 100, 2026, 5, "small", "small")
            + expand_annual("co2", 5000, 2026, 5, "big", "big")
        )
        rows = category_table(dynamic_score(build_inventory("a", emissions), 2100))
        assert rows[0]["category"] == "big"


# ---------------------------------------------------------------------------
# Metric disagreement
# ---------------------------------------------------------------------------

class TestMetrics:

    def test_all_four_metrics_are_reported(self):
        inventory = build_inventory("a", expand_annual("co2", 100, 2026, 5))
        values = metric_comparison(inventory, 2100)["values"]
        assert set(values) == set(METRICS)

    def test_methane_and_carbon_dioxide_swap_places_between_metrics(self):
        # The disagreement the module exists to surface. Equal static GWP100
        # weight, and the two metrics rank them in opposite orders.
        methane = build_inventory(
            "methane", [build_emission(2026, "ch4_fossil", 1000)]
        )
        carbon = build_inventory(
            "carbon dioxide",
            [build_emission(2026, "co2", 1000 * GASES["ch4_fossil"]["gwp100"])],
        )
        comparison = compare_inventories([methane, carbon], 2100)
        assert comparison["robust"] is False
        assert comparison["disagreements"]

    def test_a_comparison_of_identical_inventories_is_robust(self):
        first = build_inventory("a", expand_annual("co2", 100, 2026, 5))
        second = build_inventory("b", expand_annual("co2", 200, 2026, 5))
        comparison = compare_inventories([first, second], 2100)
        assert comparison["robust"] is True
        assert comparison["rankings"]["cumulative_dynamic"] == ["a", "b"]

    def test_comparing_one_inventory_is_refused(self):
        inventory = build_inventory("a", expand_annual("co2", 100, 2026, 5))
        with pytest.raises(DynamicLCAError, match="at least two"):
            compare_inventories([inventory], 2100)

    def test_metric_descriptions_state_the_question_they_answer(self):
        for metric in list_metrics():
            assert metric["question"].endswith("?")
            assert metric["unit"]

    def test_describe_metric_returns_none_for_an_unknown_key(self):
        assert describe_metric("vibes") is None


# ---------------------------------------------------------------------------
# Delay and storage
# ---------------------------------------------------------------------------

class TestDelayAndStorage:

    def test_no_delay_earns_no_credit(self):
        credit = delayed_emission_credit(1000, "co2", 0, 2100, base_year=2026)
        assert credit["credit_co2e"] == pytest.approx(0.0, abs=1e-9)

    def test_a_longer_delay_earns_more_credit(self):
        short = delayed_emission_credit(1000, "co2", 10, 2100, base_year=2026)
        long = delayed_emission_credit(1000, "co2", 40, 2100, base_year=2026)
        assert long["credit_co2e"] > short["credit_co2e"]

    def test_a_delay_past_the_target_is_flagged_as_an_artefact(self):
        credit = delayed_emission_credit(1000, "co2", 200, 2100, base_year=2026)
        assert credit["beyond_target"] is True
        assert credit["credit_fraction"] == pytest.approx(1.0, rel=1e-9)
        assert "artefact" in credit["note"]

    def test_the_note_refuses_to_call_a_delay_a_removal(self):
        credit = delayed_emission_credit(1000, "co2", 20, 2100, base_year=2026)
        assert "removed from the atmosphere" in credit["note"]

    def test_a_negative_delay_is_refused(self):
        with pytest.raises(DynamicLCAError, match="cannot be negative"):
            delayed_emission_credit(1000, "co2", -5, 2100, base_year=2026)

    def test_mixing_absolute_and_relative_years_is_refused(self):
        # The footgun this guard exists for: a 2100 target with a base year
        # of zero produces a plausible-looking and completely wrong number.
        with pytest.raises(DynamicLCAError, match="same footing"):
            delayed_emission_credit(1000, "co2", 30, 2100)

    def test_thirty_year_storage_is_worth_about_a_quarter_of_permanence(self):
        credit = temporary_storage_credit(1000, 30, 2126, base_year=2026)
        assert 0.2 < credit["credit_fraction"] < 0.3

    def test_lashof_reproduces_the_forcing_calculation_exactly(self):
        # Not a coincidence and worth pinning: Lashof accounting is the
        # delayed-emission integral written a different way.
        credit = temporary_storage_credit(1000, 30, 2126, base_year=2026)
        assert credit["lashof_equivalent"] == pytest.approx(
            credit["credit_fraction"], rel=1e-9
        )

    def test_moura_costa_is_the_more_generous_convention(self):
        credit = temporary_storage_credit(1000, 30, 2126, base_year=2026)
        assert credit["moura_costa_equivalent"] > credit["lashof_equivalent"]

    def test_moura_costa_caps_at_full_permanence(self):
        assert ton_year_equivalence(500) == 1.0

    def test_lashof_caps_at_full_permanence(self):
        assert ton_year_equivalence(150, "lashof", 100) == 1.0

    def test_an_unknown_ton_year_method_is_refused(self):
        with pytest.raises(DynamicLCAError, match="Unknown ton-year method"):
            ton_year_equivalence(30, "handwave")

    def test_zero_length_storage_is_refused(self):
        with pytest.raises(DynamicLCAError, match="at least some time"):
            temporary_storage_credit(1000, 0, 2126, base_year=2026)


# ---------------------------------------------------------------------------
# Dynamic payback
# ---------------------------------------------------------------------------

class TestPayback:

    def _case(self):
        burden = build_inventory(
            "manufacture", [build_emission(2026, "co2", 6000, "heat pump", "capital")]
        )
        savings = build_inventory(
            "avoided", expand_annual("co2", 900, 2027, 40, "gas avoided", "heating")
        )
        return burden, savings

    def test_dating_both_sides_pushes_payback_later(self):
        # The whole argument against the ratio in carbon_payback.py: the
        # upfront burden has been forcing the climate the entire time.
        burden, savings = self._case()
        result = dynamic_payback_year(burden, savings, 2100)
        assert result["breakeven_year"] is not None
        assert result["breakeven_years_from_start"] > result["naive_payback_years"]

    def test_the_naive_figure_is_reported_alongside(self):
        burden, savings = self._case()
        result = dynamic_payback_year(burden, savings, 2100)
        assert result["naive_payback_years"] == pytest.approx(6000 / 900, rel=1e-9)

    def test_an_inadequate_saving_never_repays(self):
        burden = build_inventory(
            "manufacture", [build_emission(2026, "co2", 60_000)]
        )
        savings = build_inventory("avoided", expand_annual("co2", 10, 2027, 20))
        result = dynamic_payback_year(burden, savings, 2100)
        assert result["never_repays"] is True
        assert result["breakeven_year"] is None
        assert result["net_at_target"] > 0

    def test_the_trajectory_starts_at_zero_because_nothing_has_acted_yet(self):
        # Cumulative forcing in the emission year is zero, and reading that
        # as a repaid debt is exactly the bug the deficit flag guards.
        burden, savings = self._case()
        result = dynamic_payback_year(burden, savings, 2100)
        assert result["trajectory"][0]["net_co2e"] == pytest.approx(0.0, abs=1e-9)
        assert result["breakeven_year"] > 2026

    def test_the_trajectory_ends_in_credit(self):
        burden, savings = self._case()
        result = dynamic_payback_year(burden, savings, 2100)
        assert result["trajectory"][-1]["net_co2e"] < 0

    def test_the_deficit_peaks_and_then_falls_away(self):
        burden, savings = self._case()
        result = dynamic_payback_year(burden, savings, 2100)
        after_peak = [
            row["net_co2e"] for row in result["trajectory"]
            if row["year"] > result["peak_deficit_year"]
        ]
        assert after_peak == sorted(after_peak, reverse=True)
        assert result["peak_deficit_year"] > 2026

    def test_a_savings_only_inventory_is_never_in_deficit(self):
        burden = build_inventory("none", [build_emission(2026, "co2", 0.0)])
        savings = build_inventory("avoided", expand_annual("co2", 100, 2027, 10))
        result = dynamic_payback_year(burden, savings, 2100)
        assert result["never_in_deficit"] is True
        assert result["never_repays"] is False


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

class TestInsights:

    def test_a_short_window_produces_an_overstatement_warning(self):
        inventory = build_inventory("a", expand_annual("co2", 2000, 2026, 20))
        insights = get_dynamic_insights(dynamic_score(inventory, 2100))
        assert any("overstates" in item["title"] for item in insights)

    def test_a_long_window_produces_an_understatement_warning(self):
        inventory = build_inventory("a", [build_emission(2026, "co2", 1000)])
        insights = get_dynamic_insights(dynamic_score(inventory, 2226))
        assert any("understates" in item["title"] for item in insights)

    def test_an_exactly_anchored_inventory_says_timing_does_not_matter(self):
        inventory = build_inventory("a", [build_emission(2026, "co2", 1000)])
        insights = get_dynamic_insights(dynamic_score(inventory, 2126))
        assert any("barely matters" in item["title"] for item in insights)

    def test_late_emissions_earn_a_sensitivity_warning(self):
        inventory = build_inventory("a", expand_annual("co2", 1000, 2085, 15))
        insights = get_dynamic_insights(dynamic_score(inventory, 2100))
        assert any("last twenty years" in item["title"] for item in insights)

    def test_a_cancelling_inventory_reports_an_undefined_ratio(self):
        inventory = build_inventory("net zero", [
            build_emission(2026, "co2", 1000),
            build_emission(2026, "co2", -1000),
        ])
        result = dynamic_score(inventory, 2100)
        assert result["ratio"] is None
        insights = get_dynamic_insights(result)
        assert insights[0]["level"] == "warning"

    def test_dominant_divergence_names_the_gas_responsible(self):
        emissions = (
            expand_annual("co2", 10, 2026, 20)
            + expand_annual("ch4_fossil", 100, 2026, 20)
        )
        result = dynamic_score(build_inventory("a", emissions), 2100)
        assert dominant_divergence(result)["gas"] == "ch4_fossil"

    def test_every_insight_has_a_level_and_a_body(self):
        inventory = build_inventory("a", expand_annual("co2", 500, 2026, 30))
        for item in get_dynamic_insights(dynamic_score(inventory, 2100)):
            assert item["level"] in {"info", "warning"}
            assert item["title"] and item["body"]


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

class TestReference:

    def test_every_gas_carries_a_note_explaining_its_behaviour(self):
        for entry in list_gases():
            assert len(entry["note"]) > 40

    def test_get_gas_returns_none_for_an_unknown_key(self):
        assert get_gas("phlogiston") is None

    def test_short_lived_gases_score_higher_at_twenty_years(self):
        for entry in list_gases():
            if entry["kind"] != "short-lived":
                continue
            assert entry["gwp20"] > entry["gwp100"]

    def test_short_lived_gases_score_lower_at_five_hundred_years(self):
        for entry in list_gases():
            if entry["kind"] != "short-lived":
                continue
            assert entry["gwp500"] < entry["gwp100"]

    def test_carbon_dioxide_is_one_at_every_horizon(self):
        entry = get_gas("co2")
        assert entry["gwp20"] == pytest.approx(1.0, rel=1e-12)
        assert entry["gwp500"] == pytest.approx(1.0, rel=1e-12)

    def test_a_zero_horizon_gwp_is_refused(self):
        with pytest.raises(DynamicLCAError, match="must be positive"):
            gwp("co2", 0)

    def test_a_negative_horizon_absolute_gwp_is_refused(self):
        with pytest.raises(DynamicLCAError, match="cannot be negative"):
            absolute_gwp("co2", -1)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.carbon.dynamic_lca.DB_NAME", str(tmp_path / "test.db")
        )

    def _saved(self, user="user-1"):
        inventory = build_inventory("boiler", expand_annual("co2", 500, 2026, 10))
        result = dynamic_score(inventory, 2100)
        return save_inventory(user, inventory, result), inventory, result

    def test_a_saved_inventory_comes_back(self):
        row_id, inventory, result = self._saved()
        saved = get_inventories("user-1")
        assert len(saved) == 1
        assert saved[0]["id"] == row_id
        assert saved[0]["name"] == "boiler"
        assert saved[0]["target_year"] == 2100

    def test_saved_totals_round_trip(self):
        _, _, result = self._saved()
        saved = get_inventories("user-1")[0]
        assert saved["dynamic_total"] == pytest.approx(
            result["dynamic_total_co2e"], rel=1e-9
        )
        assert saved["static_total"] == pytest.approx(
            result["static_total_co2e"], rel=1e-9
        )

    def test_users_do_not_see_each_others_inventories(self):
        self._saved("user-1")
        self._saved("user-2")
        assert len(get_inventories("user-1")) == 1
        assert len(get_inventories("user-2")) == 1

    def test_saving_without_a_user_is_refused(self):
        inventory = build_inventory("a", expand_annual("co2", 1, 2026, 2))
        result = dynamic_score(inventory, 2100)
        with pytest.raises(DynamicLCAError, match="needs a user"):
            save_inventory("", inventory, result)

    def test_reading_without_a_user_returns_nothing(self):
        assert get_inventories(None) == []

    def test_deleting_removes_the_row(self):
        row_id, _, _ = self._saved()
        assert delete_inventory("user-1", row_id) is True
        assert get_inventories("user-1") == []

    def test_deleting_another_users_row_does_nothing(self):
        row_id, _, _ = self._saved("user-1")
        assert delete_inventory("user-2", row_id) is False
        assert len(get_inventories("user-1")) == 1

    def test_deleting_without_a_user_returns_false(self):
        assert delete_inventory(None, 1) is False
