"""Tests for offset_portfolio module."""

from __future__ import annotations

import math
import pytest

from offset_portfolio import (
    OFFSET_PROJECTS,
    OffsetTransaction,
    PortfolioSummary,
    NetZeroProjection,
    OffsetCertificate,
    calculate_offset_cost,
    calculate_portfolio_summary,
    project_net_zero_timeline,
    generate_certificate,
    format_certificate_text,
    list_offset_projects,
    list_regions,
    list_project_types,
)


# ── Offset Projects Catalogue ───────────────────────────────────────────────


class TestOffsetProjectsCatalogue:
    def test_all_projects_have_required_keys(self):
        for key, info in OFFSET_PROJECTS.items():
            assert "name" in info, f"{key} missing 'name'"
            assert "region" in info, f"{key} missing 'region'"
            assert "type" in info, f"{key} missing 'type'"
            assert "registry" in info, f"{key} missing 'registry'"
            assert "price_per_tonne" in info, f"{key} missing 'price_per_tonne'"
            assert "co2_per_tonne_removed" in info, f"{key} missing 'co2_per_tonne_removed'"
            assert "rating" in info, f"{key} missing 'rating'"
            assert "description" in info, f"{key} missing 'description'"

    def test_prices_positive(self):
        for key, info in OFFSET_PROJECTS.items():
            assert info["price_per_tonne"] > 0, f"{key} has non-positive price"

    def test_ratings_in_range(self):
        for key, info in OFFSET_PROJECTS.items():
            assert 1.0 <= info["rating"] <= 5.0, f"{key} rating out of range"

    def test_capacity_positive(self):
        for key, info in OFFSET_PROJECTS.items():
            assert info["annual_capacity_tonnes"] > 0, f"{key} has zero capacity"
            assert info["remaining_capacity_tonnes"] >= 0, f"{key} has negative remaining"

    def test_remaining_leq_annual(self):
        for key, info in OFFSET_PROJECTS.items():
            assert info["remaining_capacity_tonnes"] <= info["annual_capacity_tonnes"]


# ── Offset Cost Calculation ─────────────────────────────────────────────────


class TestCalculateOffsetCost:
    def test_returns_dict_with_required_keys(self):
        result = calculate_offset_cost("reforestation_amazon", 1.0)
        assert "project_key" in result
        assert "project_name" in result
        assert "total_cost_usd" in result
        assert "equivalents" in result

    def test_cost_calculation(self):
        result = calculate_offset_cost("reforestation_amazon", 2.0)
        expected = 2.0 * 18.50
        assert abs(result["total_cost_usd"] - expected) < 0.01

    def test_different_projects_different_prices(self):
        r1 = calculate_offset_cost("clean_cookstoves_india", 1.0)
        r2 = calculate_offset_cost("ocean_kelp_uk", 1.0)
        assert r1["total_cost_usd"] != r2["total_cost_usd"]

    def test_exceeding_capacity_raises(self):
        with pytest.raises(ValueError, match="exceeds remaining capacity"):
            calculate_offset_cost("ocean_kelp_uk", 100000)

    def test_unknown_project_raises(self):
        with pytest.raises(ValueError, match="Unknown project"):
            calculate_offset_cost("fake_project", 1.0)

    def test_zero_tonnes(self):
        result = calculate_offset_cost("reforestation_amazon", 0.0)
        assert result["total_cost_usd"] == 0.0

    def test_equivalents_populated(self):
        result = calculate_offset_cost("wind_energy_brazil", 5.0)
        assert result["equivalents"]["trees_needed_per_year"] > 0
        assert result["equivalents"]["km_not_driven"] > 0

    def test_co_benefits_populated(self):
        result = calculate_offset_cost("mangrove_restoration", 1.0)
        assert len(result["co_benefits"]) > 0

    def test_remaining_capacity_shows_correctly(self):
        result = calculate_offset_cost("reforestation_amazon", 1.0)
        assert result["remaining_capacity"] == OFFSET_PROJECTS["reforestation_amazon"]["remaining_capacity_tonnes"]


# ── Portfolio Summary ───────────────────────────────────────────────────────


class TestPortfolioSummary:
    def test_empty_portfolio(self):
        result = calculate_portfolio_summary([], 5.0)
        assert isinstance(result, PortfolioSummary)
        assert result.total_tonnes_offset == 0
        assert result.total_cost_usd == 0
        assert result.total_projects == 0
        assert result.offset_vs_footprint_pct == 0
        assert result.is_net_zero is False

    def test_single_transaction(self):
        txs = [{"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 5.0, "cost_usd": 92.50, "certificate_id": "ECO-ABC123"}]
        result = calculate_portfolio_summary(txs, 10.0)
        assert result.total_tonnes_offset == 5.0
        assert result.total_cost_usd == 92.50
        assert result.total_projects == 1
        assert result.offset_vs_footprint_pct == 50.0

    def test_multiple_transactions(self):
        txs = [
            {"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 3.0, "cost_usd": 55.50},
            {"user_id": 1, "project_key": "wind_energy_brazil", "tonnes_co2": 2.0, "cost_usd": 19.00},
            {"user_id": 1, "project_key": "clean_cookstoves_india", "tonnes_co2": 1.0, "cost_usd": 12.00},
        ]
        result = calculate_portfolio_summary(txs, 10.0)
        assert result.total_tonnes_offset == 6.0
        assert result.total_cost_usd == 86.50
        assert result.total_projects == 3

    def test_net_zero_detected(self):
        txs = [{"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 10.0, "cost_usd": 185.0}]
        result = calculate_portfolio_summary(txs, 8.0)
        assert result.is_net_zero is True
        assert result.net_remaining_tonnes <= 0

    def test_project_breakdown(self):
        txs = [
            {"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 3.0, "cost_usd": 55.50},
            {"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 2.0, "cost_usd": 37.00},
        ]
        result = calculate_portfolio_summary(txs, 10.0)
        assert result.project_breakdown["reforestation_amazon"] == 5.0

    def test_portfolio_rating(self):
        txs = [
            {"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 5.0, "cost_usd": 92.50},
        ]
        result = calculate_portfolio_summary(txs, 10.0)
        assert result.portfolio_rating == 4.8

    def test_certificates_collected(self):
        txs = [
            {"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 1.0, "cost_usd": 18.50, "certificate_id": "ECO-AAA"},
            {"user_id": 1, "project_key": "wind_energy_brazil", "tonnes_co2": 2.0, "cost_usd": 19.00, "certificate_id": "ECO-BBB"},
        ]
        result = calculate_portfolio_summary(txs, 10.0)
        assert len(result.certificates) == 2

    def test_offset_percentage_zero_footprint(self):
        txs = [{"user_id": 1, "project_key": "reforestation_amazon", "tonnes_co2": 5.0, "cost_usd": 92.50}]
        result = calculate_portfolio_summary(txs, 0.0)
        assert result.offset_vs_footprint_pct == 0


# ── Net-Zero Projection ─────────────────────────────────────────────────────


class TestNetZeroProjection:
    def test_returns_projection(self):
        result = project_net_zero_timeline(10.0, 2.0, 5.0, 3.0, 10)
        assert isinstance(result, NetZeroProjection)
        assert result.current_footprint_tonnes == 10.0
        assert result.current_offset_tonnes == 2.0

    def test_net_zero_reached_with_high_offsets(self):
        result = project_net_zero_timeline(5.0, 4.0, 10.0, 10.0, 10)
        assert result.years_to_net_zero is not None
        assert result.years_to_net_zero < 1

    def test_net_zero_not_reached_with_low_offsets(self):
        result = project_net_zero_timeline(20.0, 0.0, 2.0, 0.5, 10)
        assert result.years_to_net_zero is None

    def test_target_year_populated(self):
        result = project_net_zero_timeline(5.0, 0.0, 20.0, 5.0, 10)
        assert result.target_year is not None
        assert result.target_year > 2024

    def test_monthly_projection_length(self):
        result = project_net_zero_timeline(10.0, 2.0, 5.0, 3.0, 5)
        # 5 years * 12 months + 1 starting point
        assert len(result.monthly_projection) == 61

    def test_footprint_decreasing(self):
        result = project_net_zero_timeline(10.0, 0.0, 10.0, 0.0, 5)
        fps = [m["footprint_tonnes"] for m in result.monthly_projection]
        for i in range(1, len(fps)):
            assert fps[i] <= fps[i - 1]

    def test_offsets_increasing(self):
        result = project_net_zero_timeline(10.0, 0.0, 0.0, 5.0, 5)
        offs = [m["offset_tonnes"] for m in result.monthly_projection]
        for i in range(1, len(offs)):
            assert offs[i] >= offs[i - 1]

    def test_milestones_populated(self):
        result = project_net_zero_timeline(10.0, 2.0, 5.0, 3.0, 10)
        assert len(result.milestones) >= 4  # start, 25%, 50%, 75%, net-zero, reduction

    def test_milestones_sorted_by_year(self):
        result = project_net_zero_timeline(10.0, 2.0, 5.0, 3.0, 10)
        years = [m["year_offset"] for m in result.milestones]
        assert years == sorted(years)

    def test_start_milestone_always_met(self):
        result = project_net_zero_timeline(10.0, 2.0, 5.0, 3.0, 10)
        start = result.milestones[0]
        assert start["type"] == "start"
        assert start["met"] is True

    def test_zero_footprint_no_division_error(self):
        result = project_net_zero_timeline(0.0, 0.0, 5.0, 2.0, 10)
        assert len(result.monthly_projection) > 0

    def test_net_emissions_in_projection(self):
        result = project_net_zero_timeline(10.0, 5.0, 5.0, 3.0, 10)
        for m in result.monthly_projection:
            assert "net_emissions" in m


# ── Certificate ──────────────────────────────────────────────────────────────


class TestCertificate:
    def test_generates_unique_id(self):
        c1 = generate_certificate(1, "reforestation_amazon", 1.0, 18.50)
        c2 = generate_certificate(1, "reforestation_amazon", 1.0, 18.50)
        assert c1.certificate_id != c2.certificate_id

    def test_certificate_id_format(self):
        cert = generate_certificate(1, "reforestation_amazon", 1.0, 18.50)
        assert cert.certificate_id.startswith("ECO-")

    def test_certificate_has_all_fields(self):
        cert = generate_certificate(1, "wind_energy_brazil", 2.0, 19.00)
        assert cert.user_id == 1
        assert cert.project_name == "Wind Farm Expansion — Northeast Brazil"
        assert cert.project_type == "Renewable Energy"
        assert cert.tonnes_co2 == 2.0
        assert cert.cost_usd == 19.00
        assert cert.registry == "VCS (Verra)"
        assert len(cert.verification_url) > 0

    def test_unknown_project_raises(self):
        with pytest.raises(ValueError, match="Unknown project"):
            generate_certificate(1, "fake_project", 1.0, 10.0)

    def test_format_certificate_text(self):
        cert = generate_certificate(1, "reforestation_amazon", 1.0, 18.50)
        text = format_certificate_text(cert)
        assert "CARBON OFFSET CERTIFICATE" in text
        assert cert.certificate_id in text
        assert "1.00 tonnes" in text
        assert "$18.50" in text

    def test_issued_date_populated(self):
        cert = generate_certificate(1, "reforestation_amazon", 1.0, 18.50)
        assert len(cert.issued_date) > 0
        assert "UTC" in cert.issued_date


# ── List Helpers ─────────────────────────────────────────────────────────────


class TestListHelpers:
    def test_list_projects_all(self):
        projects = list_offset_projects()
        assert len(projects) == len(OFFSET_PROJECTS)

    def test_list_projects_by_region(self):
        sa = list_offset_projects(region="South America")
        for p in sa:
            assert p["region"] == "South America"
        assert len(sa) > 0

    def test_list_projects_empty_region(self):
        projects = list_offset_projects(region="Antarctica")
        assert len(projects) == 0

    def test_project_dict_has_required_keys(self):
        projects = list_offset_projects()
        for p in projects:
            assert "key" in p
            assert "name" in p
            assert "price_per_tonne" in p
            assert "rating" in p

    def test_list_regions(self):
        regions = list_regions()
        assert len(regions) > 0
        assert "South America" in regions

    def test_list_project_types(self):
        types = list_project_types()
        assert len(types) > 0
        assert "Reforestation" in types
        assert "Renewable Energy" in types

    def test_regions_sorted(self):
        regions = list_regions()
        assert regions == sorted(regions)


# ── Edge Cases ───────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_very_small_offset(self):
        result = calculate_offset_cost("reforestation_amazon", 0.001)
        assert result["total_cost_usd"] == round(0.001 * 18.50, 2)

    def test_very_large_offset_within_capacity(self):
        result = calculate_offset_cost("wind_energy_brazil", 70000)
        assert result["total_cost_usd"] == round(70000 * 9.50, 2)

    def test_portfolio_with_unknown_project_key(self):
        txs = [{"user_id": 1, "project_key": "unknown_project", "tonnes_co2": 1.0, "cost_usd": 10.0}]
        result = calculate_portfolio_summary(txs, 5.0)
        # Should still work, unknown project just won't have a rating
        assert result.total_tonnes_offset == 1.0

    def test_projection_negative_reduction_rate(self):
        """Negative reduction means footprint grows."""
        result = project_net_zero_timeline(10.0, 0.0, -5.0, 1.0, 10)
        fps = [m["footprint_tonnes"] for m in result.monthly_projection]
        # Footprint should increase
        assert fps[-1] > fps[0]

    def test_all_projects_projectable(self):
        for key in OFFSET_PROJECTS:
            cost = calculate_offset_cost(key, 1.0)
            assert cost["total_cost_usd"] > 0
