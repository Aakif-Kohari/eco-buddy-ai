"""Query and Display Data Lineage Information

Provides utilities for inspecting, debugging, and reporting on calculation lineage.
"""

from typing import List, Dict, Any, Optional
from src.carbon.data_lineage import LineageGraph, CategoryLineage, LineageNode


class LineageInspector:
    """Inspect and query lineage graphs."""

    def __init__(self, lineage_graph: LineageGraph):
        self.graph = lineage_graph

    def trace_to_input(self, node_id: str) -> List[LineageNode]:
        """Get complete path from specified node back to input."""
        path = []
        current_node = self.graph.get_node(node_id)

        while current_node:
            path.insert(0, current_node)
            if current_node.node_type == "input":
                break
            if current_node.depends_on:
                current_node = self.graph.get_node(current_node.depends_on[0])
            else:
                break

        return path

    def get_input_to_output_path(self, category: str) -> List[LineageNode]:
        """Get complete calculation path for a category."""
        lineage = self.graph.get_category_lineage(category)
        if not lineage:
            return []
        return lineage.nodes

    def find_nodes_by_type(self, node_type: str) -> List[LineageNode]:
        """Find all nodes of a specific type."""
        return [
            n for n in self.graph.global_nodes.values()
            if n.node_type == node_type
        ]

    def find_nodes_by_category(self, category: str) -> List[LineageNode]:
        """Find all nodes for a category."""
        return [
            n for n in self.graph.global_nodes.values()
            if n.category == category
        ]

    def get_conversion_chain(self, category: str) -> List[str]:
        """Get all unit conversions for a category."""
        conversions = []
        nodes = self.find_nodes_by_category(category)
        for node in nodes:
            if node.node_type == "conversion":
                conversions.append(
                    f"{node.input_unit} → {node.output_unit} (factor: {node.metadata.get('conversion_factor', '?')})"
                )
        return conversions

    def get_emission_factors_used(self) -> Dict[str, Dict[str, Any]]:
        """List all emission factors used in calculation."""
        factors = {}
        for node in self.find_nodes_by_type("factor_lookup"):
            key = f"{node.category}_{node.metadata.get('factor_version', 'unknown')}"
            factors[key] = {
                "category": node.category,
                "value": node.input_value,
                "unit": node.input_unit,
                "version": node.metadata.get("factor_version", "unknown"),
                "source": node.metadata.get("factor_source", "unknown"),
            }
        return factors

    def generate_lineage_report(self) -> str:
        """Generate human-readable lineage report."""
        lines = [
            f"Lineage Report: {self.graph.calculation_id}",
            f"Generated: {self.graph.created_at}",
            f"Total Emissions: {self.graph.total_emissions:.2f} kg CO2",
            "",
            "CATEGORY BREAKDOWNS:",
            "=" * 60,
        ]

        for cat, lineage in self.graph.category_lineages.items():
            lines.append("")
            lines.append(f"Category: {cat.upper()}")
            lines.append(f"  Source Input: {lineage.source_input_value} {lineage.source_input_unit}")
            lines.append(f"  Final Result: {lineage.final_emission_kg_co2} kg CO2")
            lines.append(f"  Calculation Path:")

            for i, node in enumerate(lineage.nodes, 1):
                indent = "    " if i == 1 else "    → "
                if node.node_type == "factor_lookup":
                    lines.append(
                        f"{indent}[{node.node_type}] {node.description} "
                        f"(v{node.metadata.get('factor_version', '?')})"
                    )
                elif node.node_type == "conversion":
                    lines.append(
                        f"{indent}[{node.node_type}] {node.input_value} {node.input_unit} "
                        f"→ {node.output_value} {node.output_unit}"
                    )
                else:
                    lines.append(f"{indent}[{node.node_type}] {node.description}")

        return "\n".join(lines)

    def validate_lineage(self) -> List[str]:
        """Check for lineage inconsistencies."""
        issues = []

        # Check for orphaned nodes
        for cat_lineage in self.graph.category_lineages.values():
            for node in cat_lineage.nodes:
                for dep_id in node.depends_on:
                    if dep_id not in self.graph.global_nodes:
                        issues.append(
                            f"Node {node.node_id} depends on missing node {dep_id}"
                        )

        # Check for cycles
        for node_id in self.graph.global_nodes:
            path = self.trace_to_input(node_id)
            if not any(n.node_type == "input" for n in path):
                issues.append(f"Node {node_id} has no upstream input")

        return issues