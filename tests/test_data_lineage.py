"""Tests for Data Lineage Tracking"""

import pytest
from src.carbon.data_lineage import (
    LineageNode, CategoryLineage, LineageGraph,
    LineageBuilder
)
from src.carbon.lineage_inspector import LineageInspector


class TestLineageNode:
    """Test LineageNode creation and serialization."""

    def test_create_input_node(self):
        node = LineageNode(
            node_id="node_1",
            node_type="input",
            category="transport",
            input_value=10.0,
            input_unit="km/day",
            output_value=10.0,
            output_unit="km/day",
            description="Daily distance"
        )
        assert node.node_id == "node_1"
        assert node.node_type == "input"
        assert node.input_value == 10.0

    def test_node_serialization(self):
        node = LineageNode(
            node_id="test",
            node_type="calculation",
            category="transport",
            input_value=100.0,
            output_value=3650.0
        )
        d = node.to_dict()
        assert d["node_id"] == "test"
        assert d["output_value"] == 3650.0


class TestCategoryLineage:
    """Test CategoryLineage construction."""

    def test_category_lineage_creation(self):
        lineage = CategoryLineage(
            category="transport",
            source_input_value=10.0,
            source_input_unit="km/day",
            final_emission_kg_co2=3650.0,
            emission_factor_value=1.0,
            emission_factor_unit="kg CO2/km",
            emission_factor_version="static-v1",
            emission_factor_source="EcoBuddy"
        )
        assert lineage.category == "transport"
        assert lineage.final_emission_kg_co2 == 3650.0

    def test_get_calculation_path(self):
        lineage = CategoryLineage(
            category="electricity",
            source_input_value=50.0,
            source_input_unit="kWh/month",
            final_emission_kg_co2=600.0
        )
        node1 = LineageNode(
            node_id="n1", node_type="input", category="electricity",
            input_value=50.0, input_unit="kWh/month",
            output_value=50.0, output_unit="kWh/month"
        )
        node2 = LineageNode(
            node_id="n2", node_type="calculation", category="electricity",
            input_value=50.0, output_value=600.0,
            depends_on=["n1"]
        )
        lineage.add_node(node1)
        lineage.add_node(node2)
        
        path = lineage.get_calculation_path()
        assert len(path) == 2
        assert "input" in path[0]


class TestLineageGraph:
    """Test LineageGraph structure."""

    def test_graph_creation(self):
        graph = LineageGraph("calc_123")
        assert graph.calculation_id == "calc_123"
        assert len(graph.category_lineages) == 0

    def test_add_and_retrieve_lineage(self):
        graph = LineageGraph("test")
        lineage = CategoryLineage(
            category="diet",
            source_input_value=1.0,
            source_input_unit="year",
            final_emission_kg_co2=2500.0
        )
        graph.add_category_lineage(lineage)
        
        retrieved = graph.get_category_lineage("diet")
        assert retrieved is not None
        assert retrieved.category == "diet"

    def test_graph_serialization(self):
        graph = LineageGraph("test_id")
        graph.total_emissions = 5000.0
        d = graph.to_dict()
        
        assert d["calculation_id"] == "test_id"
        assert d["total_emissions_kg_co2"] == 5000.0


class TestLineageBuilder:
    """Test LineageBuilder for constructing lineages."""

    def test_builder_creation(self):
        builder = LineageBuilder("test_calc")
        assert builder.lineage_graph.calculation_id == "test_calc"

    def test_create_input_node(self):
        builder = LineageBuilder("test")
        node = builder.create_input_node(
            "transport", 15.0, "km/day", "Daily commute"
        )
        assert node.node_type == "input"
        assert node.input_value == 15.0

    def test_create_conversion_node(self):
        builder = LineageBuilder("test")
        input_node = builder.create_input_node("energy", 100.0, "kWh", "Energy")
        conv_node = builder.create_conversion_node(
            "energy", 100.0, "kWh", 360000.0, "kJ",
            3600.0, input_node, "kWh to kJ"
        )
        assert conv_node.node_type == "conversion"
        assert conv_node.depends_on == [input_node.node_id]

    def test_create_factor_lookup_node(self):
        builder = LineageBuilder("test")
        factor_node = builder.create_factor_lookup_node(
            "electricity", 0.82, "kg CO2/kWh", "static-v1", "EcoBuddy",
            "Grid emissions factor"
        )
        assert factor_node.node_type == "factor_lookup"
        assert factor_node.metadata["factor_version"] == "static-v1"

    def test_create_calculation_node(self):
        builder = LineageBuilder("test")
        input_node = builder.create_input_node("test", 100.0, "unit", "")
        factor_node = builder.create_factor_lookup_node(
            "test", 5.0, "unit", "v1", "source"
        )
        calc_node = builder.create_calculation_node(
            "test", 500.0, "input * factor",
            [input_node, factor_node],
            "100 * 5"
        )
        assert calc_node.output_value == 500.0
        assert len(calc_node.depends_on) == 2

    def test_build_category_lineage(self):
        builder = LineageBuilder("test")
        nodes = [
            builder.create_input_node("transport", 10.0, "km/day", ""),
            builder.create_factor_lookup_node("transport", 1.0, "kg/km", "v1", "src", ""),
        ]
        lineage = builder.build_category_lineage(
            "transport", 10.0, "km/day", 3650.0,
            1.0, "kg/km", "v1", "source",
            nodes
        )
        assert lineage.category == "transport"
        assert lineage.final_emission_kg_co2 == 3650.0


class TestLineageInspector:
    """Test LineageInspector for querying lineage."""

    def test_trace_to_input(self):
        builder = LineageBuilder("test")
        input_node = builder.create_input_node("diet", 1.0, "year", "")
        factor_node = builder.create_factor_lookup_node(
            "diet", 2500.0, "kg CO2/year", "v1", "src"
        )
        factor_node.depends_on = [input_node.node_id]
        
        graph = builder.lineage_graph
        graph.global_nodes[input_node.node_id] = input_node
        graph.global_nodes[factor_node.node_id] = factor_node
        
        inspector = LineageInspector(graph)
        path = inspector.trace_to_input(factor_node.node_id)
        
        assert len(path) >= 1
        assert any(n.node_type == "input" for n in path)

    def test_find_nodes_by_type(self):
        builder = LineageBuilder("test")
        inp = builder.create_input_node("test", 1.0, "u", "")
        fac = builder.create_factor_lookup_node("test", 2.0, "u", "v", "s")
        
        graph = builder.lineage_graph
        graph.global_nodes[inp.node_id] = inp
        graph.global_nodes[fac.node_id] = fac
        
        inspector = LineageInspector(graph)
        inputs = inspector.find_nodes_by_type("input")
        assert len(inputs) == 1
        
        factors = inspector.find_nodes_by_type("factor_lookup")
        assert len(factors) == 1

    def test_get_emission_factors_used(self):
        builder = LineageBuilder("test")
        factor = builder.create_factor_lookup_node(
            "electricity", 0.82, "kg CO2/kWh", "static-v1", "Grid"
        )
        graph = builder.lineage_graph
        graph.global_nodes[factor.node_id] = factor
        
        inspector = LineageInspector(graph)
        factors = inspector.get_emission_factors_used()
        assert len(factors) > 0

    def test_generate_lineage_report(self):
        builder = LineageBuilder("test")
        graph = builder.lineage_graph
        graph.total_emissions = 5000.0
        
        inspector = LineageInspector(graph)
        report = inspector.generate_lineage_report()
        
        assert "Lineage Report" in report
        assert "5000" in report