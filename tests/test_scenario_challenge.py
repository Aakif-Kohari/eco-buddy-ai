"""
Unit tests for Branching Decision Tree and Scenario Challenge Engine.
"""

import pytest
from src.utils.branching_decision_tree import BranchingDecisionTree
from src.community.scenario_challenge_engine import ScenarioChallengeEngine


def test_decision_tree_retrieval():
    tree = BranchingDecisionTree()
    scenario = tree.get_scenario("day_in_life")

    assert scenario is not None
    assert scenario["title"] == "A Day in the Life: Carbon Edition"
    assert "morning_commute" in scenario["nodes"]

    node = tree.get_node("day_in_life", "morning_commute")
    assert len(node["choices"]) == 3


def test_engine_initialization():
    engine = ScenarioChallengeEngine(
        "day_in_life", carbon_budget=15.0, monetary_budget=50.0
    )
    state = engine.get_current_state()

    assert state["current_node_id"] == "morning_commute"
    assert state["total_carbon"] == 0.0
    assert state["total_cost"] == 0.0
    assert state["is_complete"] is False


def test_engine_make_choice():
    engine = ScenarioChallengeEngine(
        "day_in_life", carbon_budget=15.0, monetary_budget=50.0
    )

    # Choose index 2: "Take the electric bus" (1.5 carbon, 2.0 cost)
    state = engine.make_choice(2)

    assert state["total_carbon"] == 1.5
    assert state["total_cost"] == 2.0
    assert state["current_node_id"] == "lunch_decision"
    assert state["is_complete"] is False


def test_engine_full_run_and_evaluation():
    engine = ScenarioChallengeEngine(
        "day_in_life", carbon_budget=10.0, monetary_budget=40.0
    )

    # Path: Bus (1.5, 2.0) -> Plant-based (0.8, 11.0) -> Digital (0.2, 0.0) -> Cook at home (1.0, 5.0)
    engine.make_choice(2)  # Bus
    engine.make_choice(2)  # Plant-based
    engine.make_choice(2)  # Digital
    engine.make_choice(1)  # Cook at home

    assert engine.is_complete is True

    evaluation = engine.evaluate_outcome()
    assert evaluation["status"] == "complete"
    assert evaluation["outcome"] == "perfect"
    assert evaluation["final_carbon"] == 3.5  # 1.5 + 0.8 + 0.2 + 1.0
    assert evaluation["final_cost"] == 18.0  # 2.0 + 11.0 + 0.0 + 5.0


def test_engine_budget_failure():
    engine = ScenarioChallengeEngine(
        "day_in_life", carbon_budget=5.0, monetary_budget=10.0
    )

    # Path: Gas car (6.0, 5.0) -> Beef burger (4.5, 12.0) -> Print single (2.5, 3.0) -> Takeout (3.5, 25.0)
    engine.make_choice(0)
    engine.make_choice(0)
    engine.make_choice(0)
    engine.make_choice(0)

    evaluation = engine.evaluate_outcome()
    assert evaluation["outcome"] == "loss"
    assert evaluation["final_carbon"] == 16.5
    assert evaluation["final_cost"] == 45.0
