"""Dependency Graph for Assessment Calculations

Represents explicit dependencies between inputs, intermediate calculations,
and final results. Enables intelligent cache invalidation and incremental
recalculation.
"""

from typing import Set, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field


class NodeType(str, Enum):
    """Types of nodes in the dependency graph."""
    INPUT = "input"
    CONVERSION = "conversion"
    FACTOR_LOOKUP = "factor_lookup"
    CATEGORY_CALC = "category_calc"
    CONFIDENCE_CALC = "confidence_calc"
    UNCERTAINTY_CALC = "uncertainty_calc"
    ECO_SCORE = "eco_score"
    RECOMMENDATION = "recommendation"
    REPORT = "report"


@dataclass
class DependencyNode:
    """Represents a single node in the dependency graph."""

    node_id: str
    node_type: NodeType
    name: str
    category: str = ""  # For category-specific nodes

    # Dependencies (what this node depends on)
    depends_on: Set[str] = field(default_factory=set)

    # Dependents (what depends on this node)
    dependents: Set[str] = field(default_factory=set)

    def add_dependency(self, node_id: str):
        """Add an incoming dependency."""
        self.depends_on.add(node_id)

    def add_dependent(self, node_id: str):
        """Add an outgoing dependent."""
        self.dependents.add(node_id)

    def remove_dependency(self, node_id: str):
        """Remove an incoming dependency."""
        self.depends_on.discard(node_id)

    def remove_dependent(self, node_id: str):
        """Remove an outgoing dependent."""
        self.dependents.discard(node_id)


class DependencyGraph:
    """Graph of calculation dependencies."""

    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}

    def add_node(self, node: DependencyNode):
        """Add a node to the graph."""
        self.nodes[node.node_id] = node

    def add_dependency(self, from_node_id: str, to_node_id: str):
        """Add dependency: to_node depends on from_node."""
        if from_node_id not in self.nodes:
            raise ValueError(f"Node {from_node_id} not found")
        if to_node_id not in self.nodes:
            raise ValueError(f"Node {to_node_id} not found")

        self.nodes[to_node_id].add_dependency(from_node_id)
        self.nodes[from_node_id].add_dependent(to_node_id)

    def get_affected_nodes(self, changed_node_id: str) -> Set[str]:
        """Get all nodes affected by a change to the specified node."""
        affected = set()
        to_visit = [changed_node_id]

        while to_visit:
            current = to_visit.pop(0)
            if current in affected:
                continue

            affected.add(current)
            current_node = self.nodes.get(current)
            if current_node:
                to_visit.extend(current_node.dependents)

        return affected

    def get_upstream_nodes(self, node_id: str) -> Set[str]:
        """Get all nodes this node depends on (directly or indirectly)."""
        upstream = set()
        to_visit = [node_id]

        while to_visit:
            current = to_visit.pop(0)
            current_node = self.nodes.get(current)
            if current_node:
                for dep in current_node.depends_on:
                    if dep not in upstream:
                        upstream.add(dep)
                        to_visit.append(dep)

        return upstream

    def get_node(self, node_id: str) -> Optional[DependencyNode]:
        """Retrieve a node by ID."""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[DependencyNode]:
        """Get all nodes of a specific type."""
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def get_nodes_by_category(self, category: str) -> List[DependencyNode]:
        """Get all nodes for a specific category."""
        return [n for n in self.nodes.values() if n.category == category]

    def validate(self) -> List[str]:
        """Check for graph issues."""
        issues = []

        # Check for orphaned nodes
        for node_id, node in self.nodes.items():
            for dep in node.depends_on:
                if dep not in self.nodes:
                    issues.append(f"Node {node_id} depends on missing {dep}")

        # Check for cycles (simplified)
        for node_id in self.nodes:
            upstream = self.get_upstream_nodes(node_id)
            if node_id in upstream:
                issues.append(f"Cycle detected involving {node_id}")

        return issues


class DependencyGraphBuilder:
    """Helper for constructing dependency graphs."""

    def __init__(self):
        self.graph = DependencyGraph()

    def add_input_node(self, node_id: str, name: str, category: str = "") -> DependencyNode:
        """Add an input node."""
        node = DependencyNode(
            node_id=node_id,
            node_type=NodeType.INPUT,
            name=name,
            category=category
        )
        self.graph.add_node(node)
        return node

    def add_category_calculation_node(
        self, node_id: str, category: str
    ) -> DependencyNode:
        """Add a category calculation node (e.g., transport_calc)."""
        node = DependencyNode(
            node_id=node_id,
            node_type=NodeType.CATEGORY_CALC,
            name=f"{category} calculation",
            category=category
        )
        self.graph.add_node(node)
        return node

    def add_eco_score_node(self) -> DependencyNode:
        """Add eco score calculation node."""
        node = DependencyNode(
            node_id="eco_score",
            node_type=NodeType.ECO_SCORE,
            name="Eco Score"
        )
        self.graph.add_node(node)
        return node

    def add_recommendation_node(self, node_id: str, category: str) -> DependencyNode:
        """Add a recommendation node."""
        node = DependencyNode(
            node_id=node_id,
            node_type=NodeType.RECOMMENDATION,
            name=f"{category} recommendation",
            category=category
        )
        self.graph.add_node(node)
        return node

    def add_report_node(self) -> DependencyNode:
        """Add report node."""
        node = DependencyNode(
            node_id="report",
            node_type=NodeType.REPORT,
            name="Assessment Report"
        )
        self.graph.add_node(node)
        return node

    def connect(self, from_id: str, to_id: str):
        """Connect two nodes with a dependency."""
        self.graph.add_dependency(from_id, to_id)

    def build(self) -> DependencyGraph:
        """Return the constructed graph."""
        return self.graph