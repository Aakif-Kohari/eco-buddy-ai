"""Tests for the land-use change carbon engine.

The load-bearing tests are the amortisation ones. Every scheme's weights must
sum to one, or the four are not four views of the same stock and comparing
them is meaningless. And a conversion older than its window must discharge to
zero rather than going negative, because a negative would credit a user for
the passage of time.
"""

import math

import pytest

from src.environment.luc_amortisation import (
    AMORTISATION_SCHEMES,
    ATTRIBUTIONS,
    CO2_PER_C,
    DEFAULT_SOIL_DECAY,
    ILUC_SCENARIOS,
    LAND_COVERS,
    LUCError,
    amortisation_weights,
    amortise,
    assess,
    compare_schemes,
    country_average_intensity,
    delete_assessment,
    direct_intensity,
    foregone_sequestration,
    get_assessments,
    get_land_cover,
    get_luc_insights,
    iluc_component,
    list_iluc_scenarios,
    list_land_covers,
    list_schemes,
    save_assessment,
    scheme_sensitivity,
    soil_decay_profile,
    soil_released_by,
    sourcing_comparison,
    stock_change,
)


def _beef(**overrides):
    kwargs = dict(
        commodity="beef",
        prior_cover="tropical_moist_forest",
        subsequent_cover="pasture",
        area_ha=1.0,
        annual_yield_t_per_ha=0.05,
        conversion_year=2016,
        assessment_year=2026,
        annual_consumption_kg=25.0,
        national_conversion_ha=1_200_000.0,
        national_output_t=10_500_000.0,
    )
    kwargs.update(overrides)
    return assess(**kwargs)


# ---------------------------------------------------------------------------
# Stock change
# ---------------------------------------------------------------------------

class TestStockChange:

    def test_clearing_forest_for_pasture_releases_carbon(self):
        change = stock_change("tropical_moist_forest", "pasture", 1.0)
        assert change["total_co2"] > 0
        assert change["sequestering"] is False

    def test_the_carbon_to_carbon_dioxide_ratio_is_applied(self):
        change = stock_change("tropical_moist_forest", "pasture", 1.0)
        assert change["total_co2"] == pytest.approx(
            change["total_loss_c"] * CO2_PER_C, rel=1e-12
        )
        assert CO2_PER_C == pytest.approx(44.0 / 12.0)

    def test_biomass_and_soil_are_kept_apart(self):
        change = stock_change("tropical_moist_forest", "pasture", 1.0)
        assert change["biomass_co2"] + change["soil_co2"] == pytest.approx(
            change["total_co2"], rel=1e-12
        )
        assert change["biomass_co2"] > 0
        assert change["soil_co2"] > 0

    def test_boreal_conversion_loses_more_from_soil_than_biomass(self):
        # Breaks the usual assumption that clearing is a biomass event.
        change = stock_change("boreal_forest", "cropland_annual", 1.0)
        assert change["soil_co2"] > change["biomass_co2"]
        assert change["soil_share"] > 0.5

    def test_holding_more_soil_carbon_does_not_mean_losing_more_of_it(self):
        # Temperate forest holds 80 tC/ha in soil against 60 in biomass, and
        # still loses more biomass than soil when cleared, because cropland
        # keeps half the soil stock and almost none of the trees. Worth
        # pinning: the stock table and the change are not the same ordering.
        entry = get_land_cover("temperate_forest")
        assert entry["soil_c"] > entry["biomass_c"]
        change = stock_change("temperate_forest", "cropland_annual", 1.0)
        assert change["biomass_co2"] > change["soil_co2"]

    def test_peatland_dominates_everything_else(self):
        peat = stock_change("peatland", "oil_palm", 1.0)
        forest = stock_change("tropical_moist_forest", "oil_palm", 1.0)
        assert peat["total_co2"] > 3 * forest["total_co2"]

    def test_restoring_degraded_land_sequesters(self):
        change = stock_change("degraded_land", "cropland_perennial", 1.0)
        assert change["total_co2"] < 0
        assert change["sequestering"] is True

    def test_area_scales_the_release_linearly(self):
        one = stock_change("tropical_moist_forest", "pasture", 1.0)
        ten = stock_change("tropical_moist_forest", "pasture", 10.0)
        assert ten["total_co2"] == pytest.approx(10 * one["total_co2"], rel=1e-12)

    def test_a_zero_area_is_refused(self):
        with pytest.raises(LUCError, match="must be positive"):
            stock_change("tropical_moist_forest", "pasture", 0)

    def test_an_unknown_cover_is_refused_with_the_list(self):
        with pytest.raises(LUCError, match="Known:"):
            stock_change("moon", "pasture", 1.0)

    def test_a_missing_cover_is_refused(self):
        with pytest.raises(LUCError, match="land cover is required"):
            stock_change(None, "pasture", 1.0)

    def test_converting_a_cover_to_itself_releases_nothing(self):
        change = stock_change("pasture", "pasture", 1.0)
        assert change["total_co2"] == 0.0


# ---------------------------------------------------------------------------
# Soil decay
# ---------------------------------------------------------------------------

class TestSoilDecay:

    def _change(self):
        return stock_change("temperate_forest", "cropland_annual", 1.0)

    def test_the_profile_converges_to_the_whole_soil_pool(self):
        profile = soil_decay_profile(self._change(), years=400)
        assert sum(row["co2"] for row in profile) == pytest.approx(
            self._change()["soil_co2"], rel=1e-6
        )

    def test_the_profile_is_front_loaded(self):
        profile = soil_decay_profile(self._change(), years=40)
        amounts = [row["co2"] for row in profile]
        assert amounts == sorted(amounts, reverse=True)

    def test_soil_is_still_emitting_a_decade_later(self):
        # A conversion twelve years ago is not finished, and every constant
        # emission factor in this app implicitly says it is.
        change = self._change()
        at_ten = soil_released_by(change, 10)
        assert 0.2 < at_ten / change["soil_co2"] < 0.6

    def test_released_soil_carbon_rises_with_time(self):
        change = self._change()
        released = [soil_released_by(change, year) for year in range(0, 60, 5)]
        assert released == sorted(released)

    def test_nothing_has_been_released_at_the_moment_of_conversion(self):
        assert soil_released_by(self._change(), 0) == pytest.approx(0.0)

    def test_the_analytical_form_matches_the_profile(self):
        change = self._change()
        profile = soil_decay_profile(change, years=25)
        assert sum(row["co2"] for row in profile) == pytest.approx(
            soil_released_by(change, 25), rel=1e-9
        )

    def test_the_default_decay_rate_is_a_twenty_year_time_constant(self):
        assert 1.0 / DEFAULT_SOIL_DECAY == pytest.approx(20.0)

    def test_a_zero_decay_rate_is_refused(self):
        with pytest.raises(LUCError, match="never reaches its new equilibrium"):
            soil_decay_profile(self._change(), decay_rate=0)

    def test_a_negative_elapsed_time_is_refused(self):
        with pytest.raises(LUCError, match="cannot be negative"):
            soil_released_by(self._change(), -1)

    def test_a_zero_length_profile_is_refused(self):
        with pytest.raises(LUCError, match="at least one year"):
            soil_decay_profile(self._change(), years=0)


# ---------------------------------------------------------------------------
# Amortisation
# ---------------------------------------------------------------------------

class TestAmortisation:

    @pytest.mark.parametrize("scheme", sorted(AMORTISATION_SCHEMES))
    def test_every_scheme_distributes_the_whole_stock_and_no_more(self, scheme):
        # Without this the four schemes are not four views of one stock and
        # comparing them says nothing.
        assert sum(amortisation_weights(scheme)) == pytest.approx(1.0, rel=1e-12)

    @pytest.mark.parametrize("scheme", sorted(AMORTISATION_SCHEMES))
    def test_no_scheme_has_a_negative_weight(self, scheme):
        assert all(weight >= 0 for weight in amortisation_weights(scheme))

    def test_the_linear_schemes_are_flat(self):
        weights = amortisation_weights("pas2050_20")
        assert len(weights) == 20
        assert len(set(round(value, 12) for value in weights)) == 1

    def test_the_discounted_scheme_front_loads(self):
        weights = amortisation_weights("discounted_20")
        assert weights == sorted(weights, reverse=True)
        assert weights[0] > weights[-1]

    def test_the_pulse_scheme_charges_everything_at_once(self):
        assert amortisation_weights("pulse") == [1.0]

    def test_thirty_years_charges_two_thirds_of_what_twenty_does(self):
        twenty = amortise(1000, 2020, 2026, "pas2050_20")["annual_co2"]
        thirty = amortise(1000, 2020, 2026, "linear_30")["annual_co2"]
        assert thirty / twenty == pytest.approx(20.0 / 30.0, rel=1e-9)

    def test_a_closed_window_discharges_to_zero_not_to_a_negative(self):
        # A negative here would credit the user for the passage of time.
        schedule = amortise(1000, 1990, 2026, "pas2050_20")
        assert schedule["annual_co2"] == 0.0
        assert schedule["obligation_complete"] is True

    def test_a_closed_window_still_reports_the_whole_cumulative_stock(self):
        schedule = amortise(1000, 1990, 2026, "pas2050_20")
        assert schedule["cumulative_co2"] == pytest.approx(1000)
        assert "not the same as the carbon having come back" in schedule["note"]

    def test_the_boundary_year_is_the_last_one_charged(self):
        assert amortise(1000, 2006, 2025, "pas2050_20")["annual_co2"] > 0
        assert amortise(1000, 2006, 2026, "pas2050_20")["annual_co2"] == 0.0

    def test_assessing_before_the_conversion_is_refused(self):
        with pytest.raises(LUCError, match="nothing to amortise yet"):
            amortise(1000, 2030, 2026)

    def test_an_unknown_scheme_is_refused_with_the_list(self):
        with pytest.raises(LUCError, match="Known:"):
            amortise(1000, 2016, 2026, "vibes")

    def test_the_cumulative_charge_reaches_the_whole_stock(self):
        final = amortise(1000, 2006, 2025, "pas2050_20")
        assert final["cumulative_co2"] == pytest.approx(1000, rel=1e-9)

    def test_comparing_schemes_reports_the_spread(self):
        comparison = compare_schemes(1000, 2024, 2026)
        assert comparison["spread"] > 1.0
        assert len(comparison["rows"]) == len(AMORTISATION_SCHEMES)

    def test_a_long_closed_conversion_reports_every_scheme_complete(self):
        comparison = compare_schemes(1000, 1950, 2026)
        assert comparison["all_complete"] is True

    def test_every_scheme_explains_the_choice_it_embodies(self):
        for scheme in list_schemes():
            assert len(scheme["note"]) > 60
            assert scheme["period"] >= 1


# ---------------------------------------------------------------------------
# Attribution
# ---------------------------------------------------------------------------

class TestAttribution:

    def test_direct_attribution_charges_the_plot(self):
        change = stock_change("tropical_moist_forest", "pasture", 1.0)
        intensity = direct_intensity(change, 0.05, "pas2050_20")
        assert intensity == pytest.approx(change["total_co2"] / (0.05 * 20))

    def test_a_higher_yield_dilutes_the_conversion(self):
        change = stock_change("tropical_moist_forest", "pasture", 1.0)
        assert direct_intensity(change, 0.1) < direct_intensity(change, 0.05)

    def test_a_zero_yield_is_refused(self):
        change = stock_change("tropical_moist_forest", "pasture", 1.0)
        with pytest.raises(LUCError, match="Yield must be positive"):
            direct_intensity(change, 0)

    def test_country_average_is_far_smaller_than_direct(self):
        result = _beef()
        assert result["country_average_intensity_t_co2_per_t"] < (
            result["direct_intensity_t_co2_per_t"]
        )
        assert result["attribution_ratio"] > 10

    def test_zero_national_output_is_refused(self):
        with pytest.raises(LUCError, match="must be positive"):
            country_average_intensity(500, 1000, 0)

    def test_negative_national_conversion_is_refused(self):
        with pytest.raises(LUCError, match="cannot be negative"):
            country_average_intensity(500, -1, 1000)

    def test_country_average_attribution_without_national_data_is_refused(self):
        # Falling back to the direct figure would silently answer a different
        # question, which is the failure this refusal exists for.
        with pytest.raises(LUCError, match="different question"):
            assess(
                commodity="beef",
                prior_cover="tropical_moist_forest",
                subsequent_cover="pasture",
                area_ha=1.0,
                annual_yield_t_per_ha=0.05,
                conversion_year=2016,
                assessment_year=2026,
                attribution="country_average",
            )

    def test_an_unknown_attribution_is_refused(self):
        with pytest.raises(LUCError, match="Unknown attribution"):
            _beef(attribution="guesswork")

    def test_both_attributions_are_described(self):
        assert set(ATTRIBUTIONS) == {"direct", "country_average"}
        for description in ATTRIBUTIONS.values():
            assert len(description) > 40


# ---------------------------------------------------------------------------
# Indirect land-use change
# ---------------------------------------------------------------------------

class TestIndirect:

    def test_excluded_is_the_default_and_contributes_nothing(self):
        result = _beef()
        assert result["iluc"]["scenario"] == "none"
        assert result["iluc_intensity_t_co2_per_t"] == 0.0

    def test_excluding_it_is_labelled_as_a_choice_not_a_neutral(self):
        assert "not the neutral choice" in ILUC_SCENARIOS["none"]["note"].lower()

    def test_the_scenarios_are_ordered(self):
        low = iluc_component("beef", "low")["factor_t_co2_per_t"]
        central = iluc_component("beef", "central")["factor_t_co2_per_t"]
        high = iluc_component("beef", "high")["factor_t_co2_per_t"]
        assert low < central < high

    def test_the_published_range_is_reported_alongside(self):
        component = iluc_component("palm_oil", "central")
        assert component["range"]["low"] < component["range"]["high"]

    def test_the_range_spans_an_order_of_magnitude_for_beef(self):
        component = iluc_component("beef", "central")
        assert component["range"]["high"] / component["range"]["low"] >= 9

    def test_an_unknown_commodity_reports_unavailable_rather_than_zero(self):
        component = iluc_component("saffron", "central")
        assert component["available"] is False
        assert component["factor_t_co2_per_t"] is None

    def test_an_unknown_scenario_is_refused(self):
        with pytest.raises(LUCError, match="Unknown iLUC scenario"):
            iluc_component("beef", "optimistic")

    def test_a_total_including_indirect_is_labelled_with_the_scenario(self):
        result = _beef(iluc_scenario="central")
        assert "iLUC central" in result["label"]
        assert result["total_intensity_t_co2_per_t"] > (
            result["intensity_t_co2_per_t"]
        )

    def test_every_scenario_is_described(self):
        for scenario in list_iluc_scenarios():
            assert len(scenario["note"]) > 40


# ---------------------------------------------------------------------------
# Foregone sequestration
# ---------------------------------------------------------------------------

class TestForegone:

    def test_it_grows_with_time(self):
        ten = foregone_sequestration("tropical_moist_forest", 1.0, 10)
        twenty = foregone_sequestration("tropical_moist_forest", 1.0, 20)
        assert twenty["co2"] == pytest.approx(2 * ten["co2"], rel=1e-12)

    def test_sealed_ground_has_no_regrowth_term(self):
        assert foregone_sequestration("settlement", 1.0, 50)["co2"] == 0.0

    def test_it_is_never_folded_into_a_total(self):
        result = _beef()
        assert "foregone" not in result
        assert "not included in any total" in (
            foregone_sequestration("tropical_moist_forest", 1.0, 10)["note"].lower()
        )

    def test_a_zero_area_is_refused(self):
        with pytest.raises(LUCError, match="must be positive"):
            foregone_sequestration("tropical_moist_forest", 0, 10)

    def test_negative_years_are_refused(self):
        with pytest.raises(LUCError, match="cannot be negative"):
            foregone_sequestration("tropical_moist_forest", 1.0, -1)


# ---------------------------------------------------------------------------
# The composed assessment
# ---------------------------------------------------------------------------

class TestAssessment:

    def test_every_total_carries_the_choices_that_produced_it(self):
        label = _beef()["label"]
        assert "PAS 2050" in label
        assert "direct attribution" in label
        assert "iLUC excluded" in label

    def test_annual_consumption_scales_the_result(self):
        one = _beef(annual_consumption_kg=25.0)
        two = _beef(annual_consumption_kg=50.0)
        assert two["total_annual_kg_co2"] == pytest.approx(
            2 * one["total_annual_kg_co2"], rel=1e-9
        )

    def test_negative_consumption_is_refused(self):
        with pytest.raises(LUCError, match="cannot be negative"):
            _beef(annual_consumption_kg=-1)

    def test_the_scheme_choice_moves_the_answer_by_more_than_the_biology(self):
        sensitivity = scheme_sensitivity(_beef())
        assert sensitivity["spread"] > 2.0

    def test_scheme_sensitivity_recovers_the_original_intensity(self):
        result = _beef()
        sensitivity = scheme_sensitivity(result)
        matching = [
            row for row in sensitivity["rows"] if row["scheme"] == result["scheme"]
        ]
        assert matching[0]["intensity_t_co2_per_t"] == pytest.approx(
            result["direct_intensity_t_co2_per_t"], rel=1e-9
        )

    def test_sourcing_comparison_quantifies_the_switch(self):
        result = _beef()
        comparison = sourcing_comparison(result, deforestation_free_intensity=25.0)
        assert comparison["saving_per_tonne"] > 0
        assert comparison["annual_saving_kg_co2"] > 0
        assert 0 < comparison["reduction_share"] < 1

    def test_a_free_option_worse_than_the_linked_one_is_refused(self):
        result = _beef()
        with pytest.raises(LUCError, match="not what it claims to be"):
            sourcing_comparison(result, deforestation_free_intensity=10_000)

    def test_a_negative_free_intensity_is_refused(self):
        with pytest.raises(LUCError, match="cannot be negative"):
            sourcing_comparison(_beef(), deforestation_free_intensity=-1)


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------

class TestInsights:

    def test_the_release_per_hectare_leads(self):
        insights = get_luc_insights(_beef())
        assert "tonnes of CO2 released per hectare" in insights[0]["title"]

    def test_the_choices_are_always_restated(self):
        insights = get_luc_insights(_beef())
        assert any("labelled with the choices" in item["title"] for item in insights)

    def test_a_large_attribution_gap_is_flagged(self):
        insights = get_luc_insights(_beef())
        assert any("Sourcing matters" in item["title"] for item in insights)

    def test_excluding_indirect_is_flagged_as_a_choice(self):
        insights = get_luc_insights(_beef())
        assert any(
            "Indirect land-use change is excluded" in item["title"]
            for item in insights
        )

    def test_including_indirect_is_flagged_as_contested(self):
        insights = get_luc_insights(_beef(iluc_scenario="high"))
        assert any("contested indirect term" in item["title"] for item in insights)

    def test_a_sequestering_conversion_says_so(self):
        result = assess(
            commodity="wheat",
            prior_cover="degraded_land",
            subsequent_cover="cropland_perennial",
            area_ha=1.0,
            annual_yield_t_per_ha=3.0,
            conversion_year=2020,
            assessment_year=2026,
        )
        insights = get_luc_insights(result)
        assert any("accumulates carbon" in item["title"] for item in insights)

    def test_a_closed_window_is_reported(self):
        insights = get_luc_insights(_beef(conversion_year=1980))
        assert any("window has closed" in item["title"] for item in insights)

    def test_every_insight_has_a_level_and_a_body(self):
        for item in get_luc_insights(_beef(iluc_scenario="central")):
            assert item["level"] in {"info", "warning"}
            assert item["title"] and item["body"]


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

class TestReference:

    def test_every_cover_carries_a_note(self):
        for entry in list_land_covers():
            assert len(entry["note"]) > 60

    def test_every_stock_is_non_negative(self):
        for entry in list_land_covers():
            assert entry["biomass_c"] >= 0
            assert entry["soil_c"] >= 0
            assert entry["regrowth_c_per_year"] >= 0

    def test_forests_hold_more_than_croplands(self):
        forest = get_land_cover("tropical_moist_forest")
        cropland = get_land_cover("cropland_annual")
        assert forest["total_c"] > cropland["total_c"]

    def test_peat_holds_the_most_soil_carbon(self):
        peat = get_land_cover("peatland")["soil_c"]
        assert peat == max(entry["soil_c"] for entry in list_land_covers())

    def test_stocks_are_reported_in_both_units(self):
        entry = get_land_cover("savanna")
        assert entry["total_co2_per_ha"] == pytest.approx(
            entry["total_c"] * CO2_PER_C, rel=1e-12
        )

    def test_get_land_cover_returns_none_for_an_unknown_key(self):
        assert get_land_cover("tundra_of_the_mind") is None

    def test_the_cover_table_and_the_constant_agree(self):
        assert set(LAND_COVERS) == {
            entry["key"] for entry in list_land_covers()
        }

    def test_regrowth_is_slowest_in_boreal_and_fastest_in_the_tropics(self):
        assert (
            get_land_cover("tropical_moist_forest")["regrowth_c_per_year"]
            > get_land_cover("boreal_forest")["regrowth_c_per_year"]
        )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class TestPersistence:

    @pytest.fixture(autouse=True)
    def _isolated_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "src.environment.luc_amortisation.DB_NAME", str(tmp_path / "test.db")
        )

    def test_a_saved_assessment_comes_back(self):
        row_id = save_assessment("user-1", _beef())
        saved = get_assessments("user-1")
        assert len(saved) == 1
        assert saved[0]["id"] == row_id
        assert saved[0]["commodity"] == "beef"

    def test_the_choices_are_stored_as_columns_not_prose(self):
        save_assessment("user-1", _beef(iluc_scenario="central"))
        saved = get_assessments("user-1")[0]
        assert saved["scheme"] == "pas2050_20"
        assert saved["attribution"] == "direct"
        assert saved["iluc_scenario"] == "central"

    def test_the_payload_keeps_both_attributions(self):
        save_assessment("user-1", _beef())
        payload = get_assessments("user-1")[0]["payload"]
        assert payload["direct_intensity"] > payload["country_average_intensity"]

    def test_users_do_not_see_each_others_assessments(self):
        save_assessment("user-1", _beef())
        save_assessment("user-2", _beef(commodity="soy"))
        assert get_assessments("user-1")[0]["commodity"] == "beef"
        assert get_assessments("user-2")[0]["commodity"] == "soy"

    def test_saving_without_a_user_is_refused(self):
        with pytest.raises(LUCError, match="needs a user"):
            save_assessment("", _beef())

    def test_reading_without_a_user_returns_nothing(self):
        assert get_assessments(None) == []

    def test_deleting_removes_the_row(self):
        row_id = save_assessment("user-1", _beef())
        assert delete_assessment("user-1", row_id) is True
        assert get_assessments("user-1") == []

    def test_deleting_another_users_row_does_nothing(self):
        row_id = save_assessment("user-1", _beef())
        assert delete_assessment("user-2", row_id) is False
        assert len(get_assessments("user-1")) == 1

    def test_deleting_without_a_user_returns_false(self):
        assert delete_assessment(None, 1) is False
