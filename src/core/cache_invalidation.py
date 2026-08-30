"""Cache Invalidation Strategy for Incremental Calculations

When an input changes, intelligently invalidates dependent cached results
while preserving unaffected calculations.
"""

from typing import Dict, Set, Any
from src.core.dependency_graph import DependencyGraph


class CacheEntry:
    """Represents a cached calculation result."""

    def __init__(self, node_id: str, value: Any, dependencies: Set[str]):
        self.node_id = node_id
        self.value = value
        self.dependencies = dependencies  # Input node IDs this depends on
        self.is_valid = True

    def invalidate(self):
        """Mark this cache entry as invalid."""
        self.is_valid = False


class CacheInvalidationManager:
    """Manages cache invalidation based on dependency changes."""

    def __init__(self, dependency_graph: DependencyGraph):
        self.graph = dependency_graph
        self.cache: Dict[str, CacheEntry] = {}

    def put(self, node_id: str, value: Any, dependencies: Set[str]):
        """Store a calculation result in cache."""
        self.cache[node_id] = CacheEntry(node_id, value, dependencies)

    def get(self, node_id: str) -> Any | None:
        """Retrieve a cached result if valid."""
        entry = self.cache.get(node_id)
        if entry and entry.is_valid:
            return entry.value
        return None

    def is_valid(self, node_id: str) -> bool:
        """Check if a cached result is valid."""
        entry = self.cache.get(node_id)
        return entry is not None and entry.is_valid

    def on_input_changed(self, changed_input_id: str):
        """Handle input change by invalidating dependent results."""
        # Get all nodes affected by this input change
        affected_nodes = self.graph.get_affected_nodes(changed_input_id)

        # Invalidate cache for all affected nodes
        for node_id in affected_nodes:
            if node_id in self.cache:
                self.cache[node_id].invalidate()

    def on_nodes_changed(self, changed_node_ids: Set[str]):
        """Handle multiple node changes by invalidating dependents."""
        all_affected = set()
        for node_id in changed_node_ids:
            all_affected.update(self.graph.get_affected_nodes(node_id))

        for node_id in all_affected:
            if node_id in self.cache:
                self.cache[node_id].invalidate()

    def clear_cache(self):
        """Clear all cached results."""
        self.cache.clear()

    def get_invalid_nodes(self) -> Set[str]:
        """Get all node IDs with invalid cache entries."""
        return {
            node_id for node_id, entry in self.cache.items()
            if not entry.is_valid
        }

    def get_valid_nodes(self) -> Set[str]:
        """Get all node IDs with valid cache entries."""
        return {
            node_id for node_id, entry in self.cache.items()
            if entry.is_valid
        }