"""Assessment State Management for Incremental Calculation

Tracks the current state of an assessment and its dependencies.
"""

from typing import Dict, Any, Set
from src.core.dependency_graph import DependencyGraph, DependencyGraphBuilder
from src.core.incremental_calculator import IncrementalCalculator


class AssessmentState:
    """Maintains assessment state and handles incremental updates."""

    def __init__(self):
        self.graph = self._build_default_graph()
        self.calculator = IncrementalCalculator(self.graph)
        self.input_values: Dict[str, Any] = {}
        self.calculation_results: Dict[str, Any] = {}

    def _build_default_graph(self) -> DependencyGraph:
        """Build standard dependency graph for assessments."""
        builder = DependencyGraphBuilder()

        # Input nodes
        builder.add_input_node("input_distance", "Daily distance", "transport")
        builder.add_input_node("input_electricity", "Monthly electricity", "electricity")
        builder.add_input_node("input_diet", "Diet type", "diet")
        builder.add_input_node("input_flights", "Annual flights", "flights")

        # Category calculations (depend on inputs)
        transport_calc = builder.add_category_calculation_node("calc_transport", "transport")
        builder.connect("input_distance", transport_calc.node_id)

        elec_calc = builder.add_category_calculation_node("calc_electricity", "electricity")
        builder.connect("input_electricity", elec_calc.node_id)

        diet_calc = builder.add_category_calculation_node("calc_diet", "diet")
        builder.connect("input_diet", diet_calc.node_id)

        flight_calc = builder.add_category_calculation_node("calc_flights", "flights")
        builder.connect("input_flights", flight_calc.node_id)

        # Eco Score (depends on all categories)
        eco_score = builder.add_eco_score_node()
        builder.connect("calc_transport", "eco_score")
        builder.connect("calc_electricity", "eco_score")
        builder.connect("calc_diet", "eco_score")
        builder.connect("calc_flights", "eco_score")

        # Recommendations (depend on categories)
        builder.add_recommendation_node("rec_transport", "transport")
        builder.connect("calc_transport", "rec_transport")

        builder.add_recommendation_node("rec_electricity", "electricity")
        builder.connect("calc_electricity", "rec_electricity")

        # Report (depends on everything)
        report = builder.add_report_node()
        builder.connect("eco_score", "report")
        builder.connect("rec_transport", "report")
        builder.connect("rec_electricity", "report")

        return builder.build()

    def set_input(self, input_id: str, value: Any) -> Set[str]:
        """
        Update an input value and return affected calculation nodes.

        Returns:
            Set of node IDs that need recalculation
        """
        self.input_values[input_id] = value
        affected = self.calculator.on_input_changed(input_id, value)
        return affected

    def register_calculation(self, node_id: str, func: callable):
        """Register calculation function for a node."""
        self.calculator.register_calculator(node_id, func)

    def get_result(self, node_id: str) -> Any | None:
        """Get cached result for a node."""
        return self.calculator.cache_manager.get(node_id)

    def put_result(self, node_id: str, value: Any):
        """Store calculation result."""
        node = self.graph.get_node(node_id)
        if node:
            self.calculator.cache_manager.put(
                node_id,
                value,
                node.depends_on
            )
            self.calculation_results[node_id] = value

    def get_stats(self) -> Dict[str, Any]:
        """Get calculation statistics."""
        return self.calculator.get_calculation_stats()

    def needs_recalculation(self, node_id: str) -> bool:
        """Check if a node needs recalculation."""
        return not self.calculator.cache_manager.is_valid(node_id)