"""Tests for green_energy_advisor module."""

from __future__ import annotations

import math
import pytest

from green_energy_advisor import (
    GRID_INTENSITY,
    SOLAR_SYSTEMS,
    BATTERY_OPTIONS,
    GREEN_PROVIDERS,
    ANALYSIS_YEARS,
    SOLAR_TAX_CREDIT_PCT,
    SolarROIResult,
    BatteryResult,
    GreenProviderMatch,
    EnergyAdvisorReport,
    calculate_solar_roi,
    calculate_battery_value,
    find_green_providers,
    build_energy_advisor_report,
    list_solar_systems,
    list_battery_options,
    list_green_providers,
    list_regions,
)


# ── Data Catalogue Tests ─────────────────────────────────────────────────────


class TestCatalogues:
    def test_grid_intensity_all_positive(self):
        for region, info in GRID_INTENSITY.items():
            assert info["intensity"] > 0, f"{region} has non-positive intensity"
            assert info["avg_electricity_cost_kwh"] > 0, f"{region} has non-positive price"

    def test_solar_systems_all_required_keys(self):
        for key, info in SOLAR_SYSTEMS.items():
            assert "capacity_kwp" in info
            assert "upfront_cost" in info
            assert "expected_annual_kwh" in info
            assert "annual_maintenance_cost" in info
            assert "degradation_pct_per_year" in info

    def test_solar_capacity_positive(self):
        for key, info in SOLAR_SYSTEMS.items():
            assert info["capacity_kwp"] > 0
            assert info["expected_annual_kwh"] > 0
            assert info["upfront_cost"] > 0

    def test_battery_options_all_required_keys(self):
        for key, info in BATTERY_OPTIONS.items():
            assert "capacity_kwh" in info
            assert "upfront_cost" in info
            assert "round_trip_efficiency" in info
            assert 0 < info["round_trip_efficiency"] <= 1

    def test_green_providers_all_required_keys(self):
        for key, info in GREEN_PROVIDERS.items():
            assert "name" in info
            assert "regions" in info
            assert "price_kwh" in info
            assert "rating" in info
            assert 1.0 <= info["rating"] <= 5.0


# ── Solar ROI Calculator ────────────────────────────────────────────────────


class TestSolarROI:
    def test_returns_solar_roi_result(self):
        result = calculate_solar_roi("medium", 400, "US")
        assert isinstance(result, SolarROIResult)

    def test_upfront_cost_matches_system(self):
        result = calculate_solar_roi("small", 300, "US")
        assert result.upfront_cost == SOLAR_SYSTEMS["small"]["upfront_cost"]

    def test_tax_credit_applied(self):
        result = calculate_solar_roi("medium", 400, "US")
        expected_credit = SOLAR_SYSTEMS["medium"]["upfront_cost"] * SOLAR_TAX_CREDIT_PCT
        assert abs(result.tax_credit_usd - expected_credit) < 0.01

    def test_net_upfront_minus_tax_credit(self):
        result = calculate_solar_roi("large", 600, "US")
        assert abs(result.net_upfront_cost - (result.upfront_cost - result.tax_credit_usd)) < 0.01

    def test_annual_kwh_matches_system(self):
        result = calculate_solar_roi("small", 300, "US")
        assert result.annual_kwh == SOLAR_SYSTEMS["small"]["expected_annual_kwh"]

    def test_yearly_projection_length(self):
        result = calculate_solar_roi("medium", 400, "US")
        assert len(result.yearly_projection) == ANALYSIS_YEARS

    def test_yearly_projection_has_required_keys(self):
        result = calculate_solar_roi("medium", 400, "US")
        for entry in result.yearly_projection:
            assert "year" in entry
            assert "kwh_generated" in entry
            assert "savings_usd" in entry
            assert "co2_avoided_kg" in entry
            assert "cumulative_savings_usd" in entry

    def test_kwh_decreases_over_time(self):
        result = calculate_solar_roi("medium", 400, "US")
        kwh_values = [p["kwh_generated"] for p in result.yearly_projection]
        # Should decrease each year due to degradation
        for i in range(1, len(kwh_values)):
            assert kwh_values[i] <= kwh_values[i - 1]

    def test_cumulative_savings_increases(self):
        result = calculate_solar_roi("medium", 400, "US")
        cum = [p["cumulative_savings_usd"] for p in result.yearly_projection]
        for i in range(1, len(cum)):
            assert cum[i] >= cum[i - 1]

    def test_payback_exists_for_good_system(self):
        result = calculate_solar_roi("medium", 400, "US")
        # Medium system should pay back within 15 years in US
        assert result.payback_years is not None
        assert result.payback_years <= 15

    def test_roi_positive(self):
        result = calculate_solar_roi("medium", 400, "US")
        assert result.roi_pct > 0

    def test_npv_positive_for_good_system(self):
        result = calculate_solar_roi("medium", 400, "US")
        assert result.npv_usd > 0

    def test_lcoe_positive(self):
        result = calculate_solar_roi("medium", 400, "US")
        assert result.lcoe_kwh > 0
        assert result.lcoe_kwh < 0.50  # Should be cheaper than grid

    def test_different_regions_different_results(self):
        us = calculate_solar_roi("medium", 400, "US")
        de = calculate_solar_roi("medium", 400, "Germany")
        # Different electricity prices → different savings
        assert us.annual_savings_usd != de.annual_savings_usd

    def test_unknown_system_raises(self):
        with pytest.raises(ValueError, match="Unknown system"):
            calculate_solar_roi("mega", 400, "US")

    def test_large_system_higher_output(self):
        small = calculate_solar_roi("small", 400, "US")
        large = calculate_solar_roi("large", 400, "US")
        assert large.annual_kwh > small.annual_kwh

    def test_co2_avoided_positive(self):
        result = calculate_solar_roi("medium", 400, "US")
        assert result.annual_co2_avoided_kg > 0

    def test_self_consumption_affects_savings(self):
        high_sc = calculate_solar_roi("medium", 400, "US", self_consumption_pct=0.9)
        low_sc = calculate_solar_roi("medium", 400, "US", self_consumption_pct=0.3)
        # Higher self-consumption → more savings at retail rate
        assert high_sc.annual_savings_usd >= low_sc.annual_savings_usd


# ── Battery Value Calculator ────────────────────────────────────────────────


class TestBatteryValue:
    def test_returns_battery_result(self):
        result = calculate_battery_value("medium", 300, "US")
        assert isinstance(result, BatteryResult)

    def test_upfront_cost_matches(self):
        result = calculate_battery_value("small", 300, "US")
        assert result.upfront_cost == BATTERY_OPTIONS["small"]["upfront_cost"]

    def test_annual_value_positive(self):
        result = calculate_battery_value("medium", 300, "US")
        assert result.annual_value_usd > 0

    def test_payback_exists(self):
        result = calculate_battery_value("medium", 300, "US")
        assert result.payback_years is not None
        assert result.payback_years > 0

    def test_lifetime_value_positive(self):
        result = calculate_battery_value("large", 300, "US")
        assert result.lifetime_value_usd > 0

    def test_effective_capacity_less_than_nominal(self):
        result = calculate_battery_value("medium", 300, "US")
        assert result.effective_capacity_kwh < result.capacity_kwh

    def test_different_regions_different_value(self):
        us = calculate_battery_value("medium", 300, "US")
        de = calculate_battery_value("medium", 300, "Germany")
        assert us.annual_value_usd != de.annual_value_usd

    def test_unknown_battery_raises(self):
        with pytest.raises(ValueError, match="Unknown battery"):
            calculate_battery_value("mega", 300, "US")

    def test_high_surplus_more_value(self):
        low = calculate_battery_value("medium", 300, "US", solar_surplus_kwh_day=2)
        high = calculate_battery_value("medium", 300, "US", solar_surplus_kwh_day=15)
        assert high.annual_value_usd > low.annual_value_usd


# ── Green Provider Matching ─────────────────────────────────────────────────


class TestGreenProviders:
    def test_us_providers(self):
        matches = find_green_providers("US", 400)
        assert len(matches) > 0
        for m in matches:
            assert "US" in GREEN_PROVIDERS[m.provider_key]["regions"]

    def test_uk_providers(self):
        matches = find_green_providers("UK", 400)
        assert len(matches) > 0

    def test_unknown_region_no_providers(self):
        matches = find_green_providers("Antarctica", 400)
        assert len(matches) == 0

    def test_match_score_range(self):
        matches = find_green_providers("US", 400)
        for m in matches:
            assert 0 <= m.match_score <= 100

    def test_sorted_by_match_score(self):
        matches = find_green_providers("US", 400)
        scores = [m.match_score for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_max_price_filter(self):
        matches = find_green_providers("US", 400, max_price_kwh=0.15)
        for m in matches:
            provider = GREEN_PROVIDERS[m.provider_key]
            assert provider["price_kwh"] <= 0.15

    def test_annual_cost_calculation(self):
        matches = find_green_providers("US", 300)
        for m in matches:
            expected = m.monthly_cost_usd * 12
            assert abs(m.annual_cost_usd - expected) < 0.1

    def test_co2_savings_positive(self):
        matches = find_green_providers("US", 400)
        for m in matches:
            assert m.annual_co2_savings_kg > 0

    def test_provider_has_features(self):
        matches = find_green_providers("US", 400)
        for m in matches:
            assert len(m.features) > 0

    def test_returns_provider_match_type(self):
        matches = find_green_providers("US", 400)
        for m in matches:
            assert isinstance(m, GreenProviderMatch)


# ── Full Advisor Report ─────────────────────────────────────────────────────


class TestAdvisorReport:
    def test_returns_report(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert isinstance(report, EnergyAdvisorReport)

    def test_solar_options_populated(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert len(report.solar_options) == len(SOLAR_SYSTEMS)

    def test_battery_options_populated(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert len(report.battery_options) == len(BATTERY_OPTIONS)

    def test_provider_matches_populated(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert len(report.provider_matches) > 0

    def test_best_solar_selected(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert report.best_solar is not None

    def test_best_provider_selected(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert report.best_provider is not None

    def test_recommendations_populated(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert len(report.recommendations) > 0

    def test_current_annual_cost(self):
        report = build_energy_advisor_report(1, 400, "US")
        grid = GRID_INTENSITY["US"]
        expected = 400 * 12 * grid["avg_electricity_cost_kwh"]
        assert abs(report.current_annual_cost - expected) < 0.1

    def test_current_annual_co2(self):
        report = build_energy_advisor_report(1, 400, "US")
        grid = GRID_INTENSITY["US"]
        expected = 400 * 12 * grid["intensity"]
        assert abs(report.current_annual_co2_kg - expected) < 0.1

    def test_total_savings_potential(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert report.total_annual_savings_potential >= 0

    def test_total_co2_reduction(self):
        report = build_energy_advisor_report(1, 400, "US")
        assert report.total_annual_co2_reduction_kg >= 0

    def test_different_monthly_kwh_different_results(self):
        r1 = build_energy_advisor_report(1, 200, "US")
        r2 = build_energy_advisor_report(1, 800, "US")
        assert r1.total_annual_savings_potential != r2.total_annual_savings_potential


# ── List Helpers ─────────────────────────────────────────────────────────────


class TestListHelpers:
    def test_list_solar_systems(self):
        systems = list_solar_systems()
        assert len(systems) == len(SOLAR_SYSTEMS)
        for s in systems:
            assert "key" in s and "name" in s

    def test_list_battery_options(self):
        options = list_battery_options()
        assert len(options) == len(BATTERY_OPTIONS)

    def test_list_green_providers_all(self):
        providers = list_green_providers()
        assert len(providers) == len(GREEN_PROVIDERS)

    def test_list_green_providers_by_region(self):
        providers = list_green_providers(region="US")
        for p in providers:
            assert "US" in GREEN_PROVIDERS[p["key"]]["regions"]

    def test_list_regions(self):
        regions = list_regions()
        assert "US" in regions
        assert "UK" in regions
        assert "Global" in regions
        assert regions == sorted(regions)


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_zero_monthly_kwh(self):
        result = calculate_solar_roi("medium", 0, "US")
        assert result.yearly_projection[0]["savings_usd"] == 0

    def test_very_high_monthly_kwh(self):
        result = calculate_solar_roi("premium", 2000, "US")
        assert result.annual_kwh > 0

    def test_all_solar_systems_calculable(self):
        for key in SOLAR_SYSTEMS:
            result = calculate_solar_roi(key, 400, "US")
            assert result.capacity_kwp > 0

    def test_all_batteries_calculable(self):
        for key in BATTERY_OPTIONS:
            result = calculate_battery_value(key, 300, "US")
            assert result.capacity_kwh > 0

    def test_high_self_consumption_better_savings(self):
        r90 = calculate_solar_roi("medium", 400, "US", self_consumption_pct=0.90)
        r30 = calculate_solar_roi("medium", 400, "US", self_consumption_pct=0.30)
        assert r90.lifetime_savings_usd >= r30.lifetime_savings_usd
