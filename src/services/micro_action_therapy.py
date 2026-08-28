"""
Micro-Action Therapy.
Generates personalized, low-barrier daily action plans based on the user's current efficacy score.
"""

from typing import Dict, Any, List
import random


class MicroActionTherapy:
    """Curates and assigns manageable daily actions to build climate agency."""

    # Database of micro-actions categorized by effort level and domain
    MICRO_ACTIONS = {
        "low_effort": [
            "Unplug one electronic device that is not in use.",
            "Turn off the tap while brushing your teeth today.",
            "Research one local composting drop-off location.",
            "Set your thermostat 1 degree more efficient (lower in winter, higher in summer).",
            "Send a quick message to a friend about a sustainable swap you made.",
        ],
        "medium_effort": [
            "Plan one plant-based meal for this week.",
            "Audit your fridge for food that needs to be eaten first.",
            "Wash your clothes in cold water for the next load.",
            "Cancel one unused subscription or reduce digital clutter.",
            "Take a 15-minute walk instead of driving for a short errand.",
        ],
        "high_effort": [
            "Draft an email to a local representative about a climate issue you care about.",
            "Research and switch to a green energy provider or community solar.",
            "Organize a small clothing swap with friends or neighbors.",
            "Conduct a full home energy audit using a smart plug or meter.",
            "Volunteer for 2 hours with a local environmental cleanup group.",
        ],
    }

    def __init__(self):
        self.completed_actions: List[str] = []

    def generate_daily_action(self, current_efficacy_score: float) -> Dict[str, Any]:
        """
        Generates a tailored micro-action based on the user's current efficacy score.
        Lower scores get low-effort actions to prevent overwhelm.
        """
        if current_efficacy_score < 50:
            pool = self.MICRO_ACTIONS["low_effort"]
            category = "low_effort"
            encouragement = (
                "Start small. This tiny action is a valid and important contribution."
            )
        elif current_efficacy_score < 80:
            pool = self.MICRO_ACTIONS["medium_effort"]
            category = "medium_effort"
            encouragement = (
                "You're building great momentum. This step will deepen your impact."
            )
        else:
            pool = self.MICRO_ACTIONS["high_effort"]
            category = "high_effort"
            encouragement = "You have strong agency! This action will create meaningful ripple effects."

        # Filter out recently completed actions to avoid repetition
        available_actions = [
            action for action in pool if action not in self.completed_actions
        ]

        # Fallback if all actions in pool have been completed
        if not available_actions:
            available_actions = pool

        selected_action = random.choice(available_actions)
        self.completed_actions.append(selected_action)

        # Keep history manageable
        if len(self.completed_actions) > 20:
            self.completed_actions.pop(0)

        return {
            "action_text": selected_action,
            "effort_level": category.replace("_", " ").title(),
            "encouragement": encouragement,
            "action_id": hash(selected_action) % 10000,  # Simple ID for tracking
        }

    def log_completion(self, action_text: str) -> None:
        """Logs the completion of an action (already handled by appending in generate, but explicit is good)."""
        if action_text not in self.completed_actions:
            self.completed_actions.append(action_text)
