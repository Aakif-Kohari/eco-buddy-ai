"""
Unit tests for the Carbon Calculation Dependency Graph & Impact Attribution (#1259).
"""

import pytest

from src.carbon.emissions import calculate_footprint
from src.carbon.dependency_graph import (
    build_dependency_graph,
    contribution_breakdown,
    largest_category_contributor,
    trace_input,
    estimate_input_change,
    rank_inputs_by_marginal_impact,
)


@pytest.fixture
def graph():
    return build_dependency_graph(
        transport="Car", distance=20, electricity=300, diet="Vegetarian", flights=2, region="Global"
    )


def test_graph_exposes_input_to_output_dependencies(graph):
    assert graph.node("input:daily_distance_km") is not None
    assert graph.node("activity:Transport") is not None
    assert graph.node("factor:Transport") is not None
    assert graph.node("category:Transport") is not None
    assert graph.node("total_footprint") is not None
    assert "total_footprint" in graph.outgoing("category:Transport")


def test_contribution_percentages_reconcile_with_calculated_total(graph):
    total, contributors = calculate_footprint("Car", 20, 300, "Vegetarian", 2, "Global")
    breakdown = contribution_breakdown(graph)

    for category, value in contributors.items():
        assert breakdown[category]["emissions_kg_co2"] == value

    assert sum(item["percentage"] for item in breakdown.values()) == pytest.approx(100.0, abs=0.05)
    assert sum(item["emissions_kg_co2"] for item in breakdown.values()) == pytest.approx(total, abs=0.01)


def test_largest_category_contributor(graph):
    breakdown = contribution_breakdown(graph)
    winner = largest_category_contributor(graph)
    assert breakdown[winner]["emissions_kg_co2"] == max(v["emissions_kg_co2"] for v in breakdown.values())


def test_trace_input_to_resulting_emissions(graph):
    traced = trace_input(graph, "daily_distance_km")
    assert traced["categories"] == {"Transport": contribution_breakdown(graph)["Transport"]}
    assert traced["traced_emissions_kg_co2"] == contribution_breakdown(graph)["Transport"]["emissions_kg_co2"]


def test_trace_input_rejects_unknown_input(graph):
    with pytest.raises(ValueError):
        trace_input(graph, "not_a_real_input")


def test_estimate_hypothetical_input_change_matches_real_recalculation(graph):
    estimate = estimate_input_change(graph, "daily_distance_km", 40)
    expected_total, _ = calculate_footprint("Car", 40, 300, "Vegetarian", 2, "Global")

    assert estimate["estimated_total_kg_co2"] == expected_total
    assert estimate["estimated_change_kg_co2"] == pytest.approx(expected_total - graph.total_kg_co2, abs=0.01)


def test_rank_inputs_by_marginal_impact_orders_by_absolute_change(graph):
    ranked = rank_inputs_by_marginal_impact(graph)
    impacts = [abs(item["marginal_change_kg_co2"]) for item in ranked]
    assert impacts == sorted(impacts, reverse=True)
    assert all(item["input"] not in ("transport", "diet") for item in ranked)


def test_attribution_consistent_across_repeated_builds():
    graph_a = build_dependency_graph("Car", 20, 300, "Vegetarian", 2, "Global")
    graph_b = build_dependency_graph("Car", 20, 300, "Vegetarian", 2, "Global")
    assert contribution_breakdown(graph_a) == contribution_breakdown(graph_b)