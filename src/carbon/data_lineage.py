"""Data Lineage Tracking for Carbon Calculations

Captures the complete path from input data through calculations to final results,
enabling full transparency and reproducibility of all carbon estimates.

A LineageNode represents a single calculation step. Multiple nodes form a directed
acyclic graph (DAG) representing the full calculation pipeline.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class LineageNode:
    """Represents a single step in a calculation pipeline."""

    # Identification
    node_id: str
    node_type: str  # 'input', 'conversion', 'factor_lookup', 'calculation', 'aggregation'
    category: str   # 'transport', 'electricity', 'diet', 'flights', etc.

    # Data
    input_value: float
    input_unit: str = ""
    output_value: float = 0.0
    output_unit: str = ""

    # Context
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Upstream references
    depends_on: List[str] = field(default_factory=list)  # node_ids

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "category": self.category,
            "input_value": self.input_value,
            "input_unit": self.input_unit,
            "output_value": self.output_value,
            "output_unit": self.output_unit,
            "description": self.description,
            "timestamp": self.timestamp,
            "depends_on": self.depends_on,
            "metadata": self.metadata,
        }


@dataclass
class CategoryLineage:
    """Complete lineage for a single emission category."""

    category: str  # 'transport', 'electricity', 'diet', 'flights'
    source_input_value: float
    source_input_unit: str
    final_emission_kg_co2: float

    # Full node sequence
    nodes: List[LineageNode] = field(default_factory=list)

    # Emission factor used
    emission_factor_value: float = 0.0
    emission_factor_unit: str = ""
    emission_factor_version: str = ""
    emission_factor_source: str = ""

    def add_node(self, node: LineageNode):
        """Add a calculation node to this lineage."""
        self.nodes.append(node)

    def get_root_node(self) -> Optional[LineageNode]:
        """Get the original input node."""
        if self.nodes:
            return self.nodes[0]
        return None

    def get_calculation_path(self) -> List[str]:
        """Get sequence of operations applied."""
        return [f"{n.node_type}({n.description})" for n in self.nodes]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "category": self.category,
            "source_input_value": self.source_input_value,
            "source_input_unit": self.source_input_unit,
            "final_emission_kg_co2": self.final_emission_kg_co2,
            "calculation_path": self.get_calculation_path(),
            "emission_factor": {
                "value": self.emission_factor_value,
                "unit": self.emission_factor_unit,
                "version": self.emission_factor_version,
                "source": self.emission_factor_source,
            },
            "nodes": [n.to_dict() for n in self.nodes],
        }

    def get_summary(self) -> str:
        """Human-readable summary of the calculation."""
        path = " → ".join(self.get_calculation_path())
        return (
            f"{self.category.upper()}: {self.source_input_value} {self.source_input_unit} "
            f"{path} = {self.final_emission_kg_co2} kg CO2"
        )


class LineageGraph:
    """Tracks complete calculation lineage for a footprint result."""

    def __init__(self, calculation_id: str):
        self.calculation_id = calculation_id
        self.created_at = datetime.utcnow().isoformat()
        self.category_lineages: Dict[str, CategoryLineage] = {}
        self.global_nodes: Dict[str, LineageNode] = {}
        self.total_emissions: float = 0.0

    def add_category_lineage(self, lineage: CategoryLineage):
        """Register lineage for a category."""
        self.category_lineages[lineage.category] = lineage
        for node in lineage.nodes:
            self.global_nodes[node.node_id] = node

    def get_category_lineage(self, category: str) -> Optional[CategoryLineage]:
        """Retrieve lineage for a specific category."""
        return self.category_lineages.get(category)

    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """Retrieve a specific node by ID."""
        return self.global_nodes.get(node_id)

    def get_upstream_nodes(self, node_id: str) -> List[LineageNode]:
        """Get all nodes that feed into this node."""
        node = self.get_node(node_id)
        if not node:
            return []

        upstream = []
        for dep_id in node.depends_on:
            dep_node = self.get_node(dep_id)
            if dep_node:
                upstream.append(dep_node)
                upstream.extend(self.get_upstream_nodes(dep_id))
        return upstream

    def get_downstream_nodes(self, node_id: str) -> List[LineageNode]:
        """Get all nodes that depend on this node."""
        downstream = []
        for node in self.global_nodes.values():
            if node_id in node.depends_on:
                downstream.append(node)
                downstream.extend(self.get_downstream_nodes(node.node_id))
        return downstream

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entire lineage graph."""
        return {
            "calculation_id": self.calculation_id,
            "created_at": self.created_at,
            "total_emissions_kg_co2": self.total_emissions,
            "categories": {
                cat: lineage.to_dict()
                for cat, lineage in self.category_lineages.items()
            },
            "all_nodes": {
                nid: node.to_dict()
                for nid, node in self.global_nodes.items()
            },
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    def get_summary(self) -> str:
        """Human-readable summary of all lineages."""
        summaries = [
            lineage.get_summary()
            for lineage in self.category_lineages.values()
        ]
        return "\n".join(summaries)


class LineageBuilder:
    """Helper for constructing lineage during calculations."""

    def __init__(self, calculation_id: str):
        self.lineage_graph = LineageGraph(calculation_id)
        self.node_counter = 0

    def _gen_node_id(self) -> str:
        """Generate unique node ID."""
        self.node_counter += 1
        return f"node_{self.node_counter}"

    def create_input_node(
        self,
        category: str,
        value: float,
        unit: str,
        description: str = ""
    ) -> LineageNode:
        """Create an input data node."""
        node = LineageNode(
            node_id=self._gen_node_id(),
            node_type="input",
            category=category,
            input_value=value,
            input_unit=unit,
            output_value=value,
            output_unit=unit,
            description=description or f"Raw {category} input",
        )
        return node

    def create_conversion_node(
        self,
        category: str,
        from_value: float,
        from_unit: str,
        to_value: float,
        to_unit: str,
        conversion_factor: float,
        previous_node: LineageNode,
        description: str = ""
    ) -> LineageNode:
        """Create a unit conversion node."""
        node = LineageNode(
            node_id=self._gen_node_id(),
            node_type="conversion",
            category=category,
            input_value=from_value,
            input_unit=from_unit,
            output_value=to_value,
            output_unit=to_unit,
            description=description or f"Convert {from_unit} to {to_unit}",
            depends_on=[previous_node.node_id],
            metadata={"conversion_factor": conversion_factor},
        )
        return node

    def create_factor_lookup_node(
        self,
        category: str,
        factor_value: float,
        factor_unit: str,
        factor_version: str,
        factor_source: str,
        description: str = ""
    ) -> LineageNode:
        """Create an emission factor lookup node."""
        node = LineageNode(
            node_id=self._gen_node_id(),
            node_type="factor_lookup",
            category=category,
            input_value=factor_value,
            input_unit=factor_unit,
            output_value=factor_value,
            output_unit=factor_unit,
            description=description or f"Emission factor: {factor_version}",
            metadata={
                "factor_version": factor_version,
                "factor_source": factor_source,
            },
        )
        return node

    def create_calculation_node(
        self,
        category: str,
        result: float,
        formula: str,
        previous_nodes: List[LineageNode],
        description: str = ""
    ) -> LineageNode:
        """Create a calculation node."""
        node = LineageNode(
            node_id=self._gen_node_id(),
            node_type="calculation",
            category=category,
            input_value=0.0,  # Multiple inputs
            output_value=result,
            output_unit="kg CO2",
            description=description or formula,
            depends_on=[n.node_id for n in previous_nodes],
            metadata={"formula": formula},
        )
        return node

    def build_category_lineage(
        self,
        category: str,
        source_value: float,
        source_unit: str,
        final_emission: float,
        factor_value: float,
        factor_unit: str,
        factor_version: str,
        factor_source: str,
        nodes: List[LineageNode]
    ) -> CategoryLineage:
        """Build complete lineage for a category."""
        lineage = CategoryLineage(
            category=category,
            source_input_value=source_value,
            source_input_unit=source_unit,
            final_emission_kg_co2=final_emission,
            emission_factor_value=factor_value,
            emission_factor_unit=factor_unit,
            emission_factor_version=factor_version,
            emission_factor_source=factor_source,
            nodes=nodes,
        )
        return lineage

    def get_graph(self) -> LineageGraph:
        """Get the constructed lineage graph."""
        return self.lineage_graph