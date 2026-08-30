"""Incremental Calculation Engine

Intelligently recalculates only affected calculations when inputs change,
reusing cached results for unaffected parts.
"""

from typing import Any, Dict, Set, Callable, Optional
from src.core.dependency_graph import DependencyGraph, NodeType
from src.core.cache_invalidation import CacheInvalidationManager


class IncrementalCalculator:
    """Manages incremental recalculation of assessment results."""

    def __init__(self, dependency_graph: DependencyGraph):
        self.graph = dependency_graph
        self.cache_manager = CacheInvalidationManager(dependency_graph)
        self.calculators: Dict[str, Callable] = {}

    def register_calculator(self, node_id: str, func: Callable):
        """Register a calculation function for a node."""
        self.calculators[node_id] = func

    def on_input_changed(self, input_node_id: str, new_value: Any) -> Set[str]:
        """
        Handle input change and return nodes that need recalculation.

        Returns:
            Set of node IDs that were invalidated
        """
        self.cache_manager.on_input_changed(input_node_id)
        return self.cache_manager.get_invalid_nodes()

    def recalculate_affected(self, changed_input_id: str) -> Dict[str, Any]:
        """
        Recalculate all nodes affected by a changed input.

        Returns:
            Dictionary of node_id -> new_value for recalculated nodes
        """
        affected_nodes = self.graph.get_affected_nodes(changed_input_id)
        results = {}

        # Process nodes in dependency order (topological sort)
        for node_id in self._topological_sort(affected_nodes):
            if node_id not in self.calculators:
                continue

            # Get cached value if available
            cached = self.cache_manager.get(node_id)
            if cached is not None:
                results[node_id] = cached
                continue

            # Recalculate
            try:
                new_value = self.calculators[node_id]()
                self.cache_manager.put(
                    node_id,
                    new_value,
                    self.graph.nodes[node_id].depends_on
                )
                results[node_id] = new_value
            except Exception:
                # Calculation failed, mark as invalid
                pass

        return results

    def get_calculation_stats(self) -> Dict[str, Any]:
        """Get statistics about cache hits/misses."""
        valid = self.cache_manager.get_valid_nodes()
        invalid = self.cache_manager.get_invalid_nodes()

        return {
            "total_cached": len(self.cache_manager.cache),
            "valid_entries": len(valid),
            "invalid_entries": len(invalid),
            "cache_hit_rate": len(valid) / max(1, len(self.cache_manager.cache))
        }

    def _topological_sort(self, node_ids: Set[str]) -> list:
        """Sort nodes in dependency order."""
        sorted_nodes = []
        visited = set()

        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)

            node = self.graph.get_node(node_id)
            if node:
                for dep in node.depends_on:
                    if dep in node_ids:
                        visit(dep)

            if node_id in node_ids:
                sorted_nodes.append(node_id)

        for node_id in node_ids:
            visit(node_id)

        return sorted_nodes

    def clear_cache(self):
        """Clear all cached results."""
        self.cache_manager.clear_cache()