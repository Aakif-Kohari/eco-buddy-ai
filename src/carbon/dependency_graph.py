"""
Carbon Calculation Dependency Graph & Impact Attribution (#1259).

Represents how a single footprint calculation flows:

    User Input -> Activity -> Emission Factor -> Category Emission -> Total Footprint

The graph is built entirely from the audit log that
``src.carbon.emissions.generate_full_audit_log`` already produces. Nothing in
this module re-implements or approximates emission math, so contribution
attribution can never drift from what the calculation engine actually did.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.carbon.emissions import calculate_footprint, generate_full_audit_log

# Which raw input(s) each category's "Activity" node consumes. This only
# describes which node feeds which - it carries no factors or thresholds -
# so it does not duplicate any calculation logic from emissions.py.
CATEGORY_INPUTS: dict[str, tuple[str, ...]] = {
    "Transport": ("transport", "daily_distance_km"),
    "Electricity": ("monthly_electricity_kwh",),
    "Diet": ("diet",),
    "Flights": ("annual_flights",),
}

# Maps a category to the emission-factor key emissions.py stores it under.
CATEGORY_FACTOR_KEYS: dict[str, str] = {
    "Transport": "transport_kg_co2_per_km",
    "Electricity": "electricity_kg_co2_per_kwh",
    "Diet": "diet_kg_co2_per_year",
    "Flights": "flight_kg_co2_per_flight",
}

# Maps an audit-log input key back to the calculate_footprint() keyword
# argument it came from, so a hypothetical value can be re-run through the
# real engine instead of being estimated separately.
INPUT_TO_KWARG: dict[str, str] = {
    "transport": "transport",
    "daily_distance_km": "distance",
    "monthly_electricity_kwh": "electricity",
    "diet": "diet",
    "annual_flights": "flights",
}


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str  # "input" | "activity" | "emission_factor" | "category_emission" | "total_footprint"
    label: str
    value: Any = None


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str


@dataclass(frozen=True)
class DependencyGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    inputs: dict[str, Any]
    total_kg_co2: float
    calc_kwargs: dict[str, Any]

    def node(self, node_id: str) -> GraphNode | None:
        return next((n for n in self.nodes if n.id == node_id), None)

    def outgoing(self, node_id: str) -> tuple[str, ...]:
        return tuple(edge.target for edge in self.edges if edge.source == node_id)


def build_dependency_graph(transport: str, distance: float, electricity: float, diet: str,
                          flights: int, region: str = "Global") -> DependencyGraph:
    """
    Build the User Input -> Activity -> Emission Factor -> Category Emission ->
    Total Footprint graph for one calculation, from the engine's own audit log.
    """
    audit = generate_full_audit_log(transport, distance, electricity, diet, flights, region)
    footprint_audit = audit["footprint_audit"]
    inputs = footprint_audit["inputs"]
    factors = footprint_audit["emission_factors"]
    steps = footprint_audit["intermediate_calculations"]
    total = footprint_audit["total_emissions_kg_co2"]

    nodes: list[GraphNode] = [GraphNode("total_footprint", "total_footprint", "Total Footprint", total)]
    edges: list[GraphEdge] = []
    seen_inputs: set[str] = set()

    for category, step in steps.items():
        cat_id = f"category:{category}"
        factor_id = f"factor:{category}"
        activity_id = f"activity:{category}"

        nodes.append(GraphNode(cat_id, "category_emission", category, step["rounded_result_kg"]))
        edges.append(GraphEdge(cat_id, "total_footprint"))

        nodes.append(GraphNode(factor_id, "emission_factor", f"{category} emission factor",
                                factors[CATEGORY_FACTOR_KEYS[category]]))
        edges.append(GraphEdge(factor_id, cat_id))

        nodes.append(GraphNode(activity_id, "activity", step["formula"], step["expression"]))
        edges.append(GraphEdge(activity_id, factor_id))

        for input_key in CATEGORY_INPUTS[category]:
            input_id = f"input:{input_key}"
            if input_key not in seen_inputs:
                nodes.append(GraphNode(input_id, "input", input_key, inputs[input_key]))
                seen_inputs.add(input_key)
            edges.append(GraphEdge(input_id, activity_id))

    return DependencyGraph(
        nodes=tuple(nodes),
        edges=tuple(edges),
        inputs=inputs,
        total_kg_co2=total,
        calc_kwargs={
            "transport": transport, "distance": distance, "electricity": electricity,
            "diet": diet, "flights": flights, "region": region,
        },
    )


def contribution_breakdown(graph: DependencyGraph) -> dict[str, dict[str, float]]:
    """Contribution percentage of each category, reconciled against the graph's total."""
    breakdown: dict[str, dict[str, float]] = {}
    for node in graph.nodes:
        if node.kind == "category_emission":
            percentage = (node.value / graph.total_kg_co2 * 100.0) if graph.total_kg_co2 else 0.0
            breakdown[node.label] = {"emissions_kg_co2": node.value, "percentage": round(percentage, 2)}
    return breakdown


def largest_category_contributor(graph: DependencyGraph) -> str:
    """Category responsible for the largest share of emissions."""
    breakdown = contribution_breakdown(graph)
    return max(breakdown, key=lambda category: breakdown[category]["emissions_kg_co2"])


def trace_input(graph: DependencyGraph, input_key: str) -> dict[str, Any]:
    """
    Trace one input forward through the graph to the category emission(s) and
    total footprint it feeds, by walking the graph's actual edges.
    """
    input_id = f"input:{input_key}"
    if graph.node(input_id) is None:
        raise ValueError(f"Unknown input '{input_key}'. Known inputs: {sorted(graph.inputs)}")

    frontier = {input_id}
    reached_categories: set[str] = set()
    while frontier:
        next_frontier: set[str] = set()
        for node_id in frontier:
            for target_id in graph.outgoing(node_id):
                next_frontier.add(target_id)
                target = graph.node(target_id)
                if target and target.kind == "category_emission":
                    reached_categories.add(target_id)
        frontier = next_frontier

    breakdown = contribution_breakdown(graph)
    traced = {graph.node(cat_id).label: breakdown[graph.node(cat_id).label] for cat_id in reached_categories}
    traced_total = round(sum(item["emissions_kg_co2"] for item in traced.values()), 2)
    return {
        "input": input_key,
        "value": graph.inputs[input_key],
        "categories": traced,
        "traced_emissions_kg_co2": traced_total,
        "share_of_total_percentage": round((traced_total / graph.total_kg_co2 * 100.0), 2) if graph.total_kg_co2 else 0.0,
    }


def estimate_input_change(graph: DependencyGraph, input_key: str, new_value: Any) -> dict[str, Any]:
    """
    Estimate the effect of changing a single input, by re-running the real
    calculation engine with only that one input changed - never approximated.
    """
    if input_key not in INPUT_TO_KWARG:
        raise ValueError(f"Unknown input '{input_key}'. Known inputs: {sorted(INPUT_TO_KWARG)}")

    kwargs = dict(graph.calc_kwargs)
    kwargs[INPUT_TO_KWARG[input_key]] = new_value
    new_total, _ = calculate_footprint(**kwargs)

    return {
        "input": input_key,
        "previous_value": graph.inputs[input_key],
        "new_value": new_value,
        "baseline_total_kg_co2": graph.total_kg_co2,
        "estimated_total_kg_co2": new_total,
        "estimated_change_kg_co2": round(new_total - graph.total_kg_co2, 2),
    }


def rank_inputs_by_marginal_impact(graph: DependencyGraph, *, percent_step: float = 0.1) -> list[dict[str, Any]]:
    """
    Rank every numeric input by how much a small change to it moves the total
    footprint (its marginal impact), largest absolute impact first. Categorical
    inputs (transport mode, diet) have no "small step" and are skipped.
    """
    results: list[dict[str, Any]] = []
    for input_key, value in graph.inputs.items():
        if isinstance(value, str):
            continue
        step = value * percent_step if value else 1
        estimate = estimate_input_change(graph, input_key, value + step)
        results.append({
            "input": input_key,
            "step_applied": round(step, 4),
            "marginal_change_kg_co2": estimate["estimated_change_kg_co2"],
        })
    results.sort(key=lambda item: abs(item["marginal_change_kg_co2"]), reverse=True)
    return results