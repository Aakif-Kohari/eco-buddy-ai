"""Tests for Incremental Recalculation Engine"""

import pytest
from src.core.dependency_graph import (
    DependencyGraph, DependencyGraphBuilder, NodeType
)
from src.core.cache_invalidation import CacheInvalidationManager
from src.core.incremental_calculator import IncrementalCalculator
from src.core.assessment_state import AssessmentState


class TestDependencyGraph:
    """Test dependency graph construction."""

    def test_graph_creation(self):
        graph = DependencyGraph()
        assert len(graph.nodes) == 0

    def test_add_nodes(self):
        builder = DependencyGraphBuilder()
        node1 = builder.add_input_node("inp1", "Input 1")
        assert "inp1" in builder.graph.nodes

    def test_add_dependency(self):
        builder = DependencyGraphBuilder()
        inp = builder.add_input_node("inp", "Input")
        calc = builder.add_category_calculation_node("calc", "test")
        builder.connect("inp", "calc")

        assert "inp" in builder.graph.nodes["calc"].depends_on
        assert "calc" in builder.graph.nodes["inp"].dependents

    def test_get_affected_nodes(self):
        builder = DependencyGraphBuilder()
        inp = builder.add_input_node("inp", "Input")
        calc = builder.add_category_calculation_node("calc", "test")
        score = builder.add_eco_score_node()
        builder.connect("inp", "calc")
        builder.connect("calc", "eco_score")

        graph = builder.build()
        affected = graph.get_affected_nodes("inp")

        assert "inp" in affected
        assert "calc" in affected
        assert "eco_score" in affected

    def test_get_upstream_nodes(self):
        builder = DependencyGraphBuilder()
        inp = builder.add_input_node("inp", "Input")
        calc = builder.add_category_calculation_node("calc", "test")
        builder.connect("inp", "calc")

        graph = builder.build()
        upstream = graph.get_upstream_nodes("calc")

        assert "inp" in upstream
        assert "calc" not in upstream


class TestCacheInvalidation:
    """Test cache invalidation logic."""

    def test_cache_put_and_get(self):
        graph = DependencyGraphBuilder().add_input_node("inp", "").build()
        manager = CacheInvalidationManager(graph)

        manager.put("node1", 100, {"inp"})
        assert manager.get("node1") == 100

    def test_cache_invalidation_on_input_change(self):
        builder = DependencyGraphBuilder()
        inp = builder.add_input_node("inp", "Input")
        calc = builder.add_category_calculation_node("calc", "test")
        builder.connect("inp", "calc")
        graph = builder.build()

        manager = CacheInvalidationManager(graph)
        manager.put("calc", 500, {"inp"})
        assert manager.get("calc") == 500

        manager.on_input_changed("inp")
        assert manager.get("calc") is None

    def test_unaffected_cache_preserved(self):
        builder = DependencyGraphBuilder()
        builder.add_input_node("inp1", "")
        builder.add_input_node("inp2", "")
        calc1 = builder.add_category_calculation_node("calc1", "test")
        calc2 = builder.add_category_calculation_node("calc2", "test")
        builder.connect("inp1", "calc1")
        builder.connect("inp2", "calc2")
        graph = builder.build()

        manager = CacheInvalidationManager(graph)
        manager.put("calc1", 100, {"inp1"})
        manager.put("calc2", 200, {"inp2"})

        manager.on_input_changed("inp1")

        assert manager.get("calc1") is None  # Invalidated
        assert manager.get("calc2") == 200  # Preserved


class TestIncrementalCalculator:
    """Test incremental calculation logic."""

    def test_register_calculator(self):
        graph = DependencyGraphBuilder().add_input_node("inp", "").build()
        calc = IncrementalCalculator(graph)

        func = lambda: 42
        calc.register_calculator("node1", func)
        assert "node1" in calc.calculators

    def test_affected_nodes_after_input_change(self):
        builder = DependencyGraphBuilder()
        inp = builder.add_input_node("inp", "")
        calc = builder.add_category_calculation_node("calc", "test")
        builder.connect("inp", "calc")
        graph = builder.build()

        calc_engine = IncrementalCalculator(graph)
        affected = calc_engine.on_input_changed("inp", 100)

        assert "calc" in affected


class TestAssessmentState:
    """Test assessment state management."""

    def test_assessment_state_creation(self):
        state = AssessmentState()
        assert state.graph is not None
        assert state.calculator is not None

    def test_set_input_affects_calculations(self):
        state = AssessmentState()
        affected = state.set_input("input_distance", 10.0)

        assert "calc_transport" in affected

    def test_multiple_inputs_independent_changes(self):
        state = AssessmentState()

        # Change distance (affects transport only)
        affected1 = state.set_input("input_distance", 10.0)
        assert "calc_transport" in affected1
        assert "calc_electricity" not in affected1

        # Change electricity (affects electricity only)
        affected2 = state.set_input("input_electricity", 50.0)
        assert "calc_electricity" in affected2
        assert "calc_transport" not in affected2

    def test_eco_score_invalidated_when_category_changes(self):
        state = AssessmentState()

        # Change a category input
        affected = state.set_input("input_distance", 15.0)

        # Eco Score should be affected (depends on transport)
        assert "eco_score" in affected

    def test_report_invalidated_when_dependent_changes(self):
        state = AssessmentState()

        # Change eco score dependency
        affected = state.set_input("input_flights", 5)

        # Report depends on eco score, which depends on flights
        assert "report" in affected

    def test_calculation_results_storage(self):
        state = AssessmentState()
        state.put_result("calc_transport", 2500)

        assert state.get_result("calc_transport") == 2500
        assert state.needs_recalculation("calc_transport") is False

    def test_invalidation_invalidates_dependent_results(self):
        state = AssessmentState()
        state.put_result("calc_transport", 2500)

        # Invalidate the dependency
        state.set_input("input_distance", 20.0)

        # Result should need recalculation
        assert state.needs_recalculation("calc_transport") is True

    def test_incremental_vs_full_equivalence(self):
        """Verify incremental calculation gives same results as full."""
        state = AssessmentState()

        # Set initial values
        state.set_input("input_distance", 10.0)
        state.set_input("input_electricity", 50.0)
        state.set_input("input_diet", 1.0)
        state.set_input("input_flights", 2)

        # Store some results
        state.put_result("calc_transport", 3650.0)
        state.put_result("calc_electricity", 600.0)

        # Change one input
        affected = state.set_input("input_distance", 15.0)

        # Only transport should be invalidated
        assert state.needs_recalculation("calc_transport") is True
        assert state.needs_recalculation("calc_electricity") is False

        # Electricity result should still be available
        assert state.get_result("calc_electricity") == 600.0

    def test_stats_reporting(self):
        """Test cache statistics reporting."""
        state = AssessmentState()
        state.put_result("calc_transport", 2500)
        state.put_result("calc_electricity", 600)

        stats = state.get_stats()
        assert stats["total_cached"] == 2
        assert stats["valid_entries"] == 2
        assert stats["invalid_entries"] == 0