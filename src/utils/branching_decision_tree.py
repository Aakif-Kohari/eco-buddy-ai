"""
Branching Decision Tree.
Manages complex, multi-node scenario paths where each user choice leads to different subsequent events and carbon consequences.
"""

from typing import Dict, Any, List, Optional


class BranchingDecisionTree:
    """Defines and traverses interactive carbon footprint scenarios."""

    def __init__(self):
        # Define a sample scenario: "A Day in the Life"
        self.scenarios = {
            "day_in_life": {
                "title": "A Day in the Life: Carbon Edition",
                "description": "Navigate a typical day making choices that balance convenience, budget, and carbon footprint.",
                "starting_node": "morning_commute",
                "nodes": {
                    "morning_commute": {
                        "text": "It's 8:00 AM. You need to get to work, which is 15 miles away. How do you travel?",
                        "choices": [
                            {
                                "text": "Drive alone in a gas car",
                                "carbon_impact": 6.0,
                                "cost_impact": 5.0,
                                "next_node": "lunch_decision",
                            },
                            {
                                "text": "Carpool with a coworker",
                                "carbon_impact": 3.0,
                                "cost_impact": 2.5,
                                "next_node": "lunch_decision",
                            },
                            {
                                "text": "Take the electric bus",
                                "carbon_impact": 1.5,
                                "cost_impact": 2.0,
                                "next_node": "lunch_decision",
                            },
                        ],
                    },
                    "lunch_decision": {
                        "text": "It's lunchtime. You're hungry and have $15 to spend. What do you eat?",
                        "choices": [
                            {
                                "text": "Beef burger and fries",
                                "carbon_impact": 4.5,
                                "cost_impact": 12.0,
                                "next_node": "afternoon_work",
                            },
                            {
                                "text": "Chicken salad",
                                "carbon_impact": 2.0,
                                "cost_impact": 10.0,
                                "next_node": "afternoon_work",
                            },
                            {
                                "text": "Plant-based bowl",
                                "carbon_impact": 0.8,
                                "cost_impact": 11.0,
                                "next_node": "afternoon_work",
                            },
                        ],
                    },
                    "afternoon_work": {
                        "text": "3:00 PM. You need to print a 50-page document for a meeting. What do you do?",
                        "choices": [
                            {
                                "text": "Print it single-sided on new paper",
                                "carbon_impact": 2.5,
                                "cost_impact": 3.0,
                                "next_node": "evening_plan",
                            },
                            {
                                "text": "Print it double-sided on recycled paper",
                                "carbon_impact": 1.0,
                                "cost_impact": 1.5,
                                "next_node": "evening_plan",
                            },
                            {
                                "text": "Share it digitally via tablet",
                                "carbon_impact": 0.2,
                                "cost_impact": 0.0,
                                "next_node": "evening_plan",
                            },
                        ],
                    },
                    "evening_plan": {
                        "text": "6:00 PM. Work is done. How do you spend your evening?",
                        "choices": [
                            {
                                "text": "Order takeout (packaging + delivery)",
                                "carbon_impact": 3.5,
                                "cost_impact": 25.0,
                                "next_node": "end",
                            },
                            {
                                "text": "Cook at home using leftovers",
                                "carbon_impact": 1.0,
                                "cost_impact": 5.0,
                                "next_node": "end",
                            },
                            {
                                "text": "Go out to a local restaurant",
                                "carbon_impact": 2.5,
                                "cost_impact": 30.0,
                                "next_node": "end",
                            },
                        ],
                    },
                    "end": {
                        "text": "The day is over! Let's see how your choices added up.",
                        "choices": [],  # Terminal node
                    },
                },
            }
        }

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a scenario definition by ID."""
        return self.scenarios.get(scenario_id)

    def get_node(self, scenario_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific node within a scenario."""
        scenario = self.get_scenario(scenario_id)
        if scenario:
            return scenario["nodes"].get(node_id)
        return None

    def get_available_scenarios(self) -> List[str]:
        """Returns a list of all available scenario IDs."""
        return list(self.scenarios.keys())
