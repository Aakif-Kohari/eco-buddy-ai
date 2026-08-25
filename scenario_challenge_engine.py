"""
Scenario Challenge Engine.
Tracks the user's running footprint, time, and budget during the simulation, determining win/loss states.
"""

from typing import Dict, Any, List
from branching_decision_tree import BranchingDecisionTree


class ScenarioChallengeEngine:
    """Manages the state and rules of an interactive carbon challenge."""

    def __init__(self, scenario_id: str, carbon_budget: float, monetary_budget: float):
        self.tree = BranchingDecisionTree()
        self.scenario_id = scenario_id
        self.carbon_budget = carbon_budget
        self.monetary_budget = monetary_budget

        self.reset_state()

    def reset_state(self) -> None:
        """Resets the challenge to its initial state."""
        scenario = self.tree.get_scenario(self.scenario_id)
        if not scenario:
            raise ValueError("Invalid scenario ID")

        self.current_node_id = scenario["starting_node"]
        self.total_carbon = 0.0
        self.total_cost = 0.0
        self.history: List[Dict[str, Any]] = []
        self.is_complete = False

    def get_current_state(self) -> Dict[str, Any]:
        """Returns the current state of the challenge."""
        scenario = self.tree.get_scenario(self.scenario_id)
        node = self.tree.get_node(self.scenario_id, self.current_node_id)

        return {
            "scenario_title": scenario["title"],
            "current_node_id": self.current_node_id,
            "text": node["text"],
            "choices": node["choices"],
            "total_carbon": round(self.total_carbon, 2),
            "total_cost": round(self.total_cost, 2),
            "carbon_budget": self.carbon_budget,
            "monetary_budget": self.monetary_budget,
            "carbon_remaining": round(self.carbon_budget - self.total_carbon, 2),
            "money_remaining": round(self.monetary_budget - self.total_cost, 2),
            "is_complete": self.is_complete,
        }

    def make_choice(self, choice_index: int) -> Dict[str, Any]:
        """Processes a user's choice and advances the state."""
        if self.is_complete:
            raise ValueError("Challenge is already complete. Reset to play again.")

        node = self.tree.get_node(self.scenario_id, self.current_node_id)
        if choice_index < 0 or choice_index >= len(node["choices"]):
            raise ValueError("Invalid choice index")

        choice = node["choices"][choice_index]

        # Update state
        self.total_carbon += choice["carbon_impact"]
        self.total_cost += choice["cost_impact"]
        self.history.append(
            {
                "node": self.current_node_id,
                "choice": choice["text"],
                "carbon_added": choice["carbon_impact"],
                "cost_added": choice["cost_impact"],
            }
        )

        # Advance to next node
        self.current_node_id = choice["next_node"]

        # Check for terminal node
        next_node = self.tree.get_node(self.scenario_id, self.current_node_id)
        if not next_node["choices"]:
            self.is_complete = True

        return self.get_current_state()

    def evaluate_outcome(self) -> Dict[str, Any]:
        """Evaluates the final outcome based on budgets."""
        if not self.is_complete:
            return {"status": "incomplete", "message": "Challenge not finished."}

        carbon_success = self.total_carbon <= self.carbon_budget
        money_success = self.total_cost <= self.monetary_budget

        if carbon_success and money_success:
            outcome = "perfect"
            message = "🏆 Perfect! You stayed under both carbon and monetary budgets."
        elif carbon_success:
            outcome = "carbon_win"
            message = (
                "🌱 Carbon Victory! You saved the planet, but overspent your budget."
            )
        elif money_success:
            outcome = "money_win"
            message = (
                "💰 Budget Victory! You saved money, but exceeded your carbon limit."
            )
        else:
            outcome = "loss"
            message = (
                "⚠️ Challenge Failed. You exceeded both carbon and monetary budgets."
            )

        return {
            "status": "complete",
            "outcome": outcome,
            "message": message,
            "final_carbon": round(self.total_carbon, 2),
            "final_cost": round(self.total_cost, 2),
            "history": self.history,
        }
