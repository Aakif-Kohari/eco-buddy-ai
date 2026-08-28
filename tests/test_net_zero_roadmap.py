"""
Unit tests for Emissions Gap Analyzer and Net-Zero Roadmap Generator.
"""

import pytest
from src.carbon.emissions_gap_analyzer import EmissionsGapAnalyzer
from src.utils.net_zero_roadmap_generator import NetZeroRoadmapGenerator


def test_gap_analyzer_calculation():
    analyzer = EmissionsGapAnalyzer(
        current_scope1=100, current_scope2=100, current_scope3=800, target_year=2034
    )
    # Total = 1000. Target year = 2034 (10 years from 2024)
    # Target = 10 (1% of 1000)
    # 10 = 1000 * (1 - r)^10 => (1-r)^10 = 0.01 => 1-r = 0.01^(0.1) ≈ 0.63 => r ≈ 37%

    result = analyzer.calculate_required_reduction_rate()
    assert result["status"] == "valid"
    assert result["total_current_emissions"] == 1000.0
    assert result["years_remaining"] == 10
    assert result["required_annual_reduction_pct"] > 30.0  # Should be around 37%
    assert "Ambitious" in result["feasibility"]


def test_gap_analyzer_invalid_year():
    analyzer = EmissionsGapAnalyzer(100, 100, 800, target_year=2020)
    result = analyzer.calculate_required_reduction_rate()
    assert result["status"] == "invalid"


def test_scope_breakdown():
    analyzer = EmissionsGapAnalyzer(200, 300, 500, target_year=2030)
    breakdown = analyzer.get_scope_breakdown()

    assert breakdown["scope1_pct"] == 20.0
    assert breakdown["scope2_pct"] == 30.0
    assert breakdown["scope3_pct"] == 50.0


def test_roadmap_generation():
    analyzer = EmissionsGapAnalyzer(100, 100, 800, target_year=2034)
    generator = NetZeroRoadmapGenerator(analyzer)
    roadmap = generator.generate_roadmap()

    assert "error" not in roadmap
    assert len(roadmap["roadmap"]) == 10  # 10 years
    assert roadmap["roadmap"][0]["year"] == 2025

    # Check that interventions are assigned
    assert len(roadmap["roadmap"][-1]["interventions"]) > 0

    # Final emissions should be close to or at the 1% floor
    assert (
        roadmap["final_projected_emissions"] <= analyzer.total_current * 0.015
    )  # Allow small margin


def test_roadmap_intervention_sequencing():
    analyzer = EmissionsGapAnalyzer(500, 500, 0, target_year=2030)  # High scope 1 & 2
    generator = NetZeroRoadmapGenerator(analyzer)
    roadmap = generator.generate_roadmap()

    # Check that scope 1 and 2 interventions are prioritized
    all_interventions = []
    for step in roadmap["roadmap"]:
        all_interventions.extend([i["key"] for i in step["interventions"]])

    assert (
        "fleet_electrification_25" in all_interventions
        or "renewable_energy_50" in all_interventions
    )
