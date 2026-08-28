"""
Skill Swap Engine.
Manages user skill listings, matches compatible teaching/learning requests, and handles Eco-Karma transactions.
"""

from typing import Dict, Any, List, Optional


class SkillSwapEngine:
    """Facilitates non-monetary skill exchanges using an Eco-Karma point system."""

    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.listings: List[Dict[str, Any]] = []
        self.swaps: List[Dict[str, Any]] = []

    def register_user(self, user_id: str, initial_karma: int = 50) -> None:
        """Registers a new user with an initial Eco-Karma balance."""
        if user_id not in self.users:
            self.users[user_id] = {
                "user_id": user_id,
                "eco_karma": initial_karma,
                "skills_offered": [],
                "skills_requested": [],
                "completed_swaps": 0,
                "rating": 5.0,
            }

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user profile data."""
        return self.users.get(user_id)

    def add_skill_offering(
        self,
        user_id: str,
        skill_name: str,
        category: str,
        difficulty: str,
        karma_cost: int,
    ) -> bool:
        """Adds a skill that the user is willing to teach."""
        user = self.get_user(user_id)
        if not user:
            return False

        listing = {
            "listing_id": f"{user_id}_{skill_name.replace(' ', '_').lower()}",
            "teacher_id": user_id,
            "skill_name": skill_name,
            "category": category,
            "difficulty": difficulty,
            "karma_cost": karma_cost,
            "status": "active",
        }
        self.listings.append(listing)
        user["skills_offered"].append(skill_name)
        return True

    def find_matches(self, learner_id: str, desired_skill: str) -> List[Dict[str, Any]]:
        """Finds active listings for a desired skill that the learner can afford."""
        learner = self.get_user(learner_id)
        if not learner:
            return []

        matches = []
        for listing in self.listings:
            if (
                listing["skill_name"].lower() == desired_skill.lower()
                and listing["status"] == "active"
            ):
                if listing["teacher_id"] != learner_id:  # Cannot swap with self
                    if learner["eco_karma"] >= listing["karma_cost"]:
                        matches.append(listing)

        return matches

    def execute_swap(self, learner_id: str, listing_id: str) -> Dict[str, Any]:
        """
        Executes a skill swap, transferring Eco-Karma and updating records.
        """
        learner = self.get_user(learner_id)
        listing = next(
            (l for l in self.listings if l["listing_id"] == listing_id), None
        )

        if not learner or not listing:
            return {"success": False, "error": "Invalid user or listing."}

        if learner["eco_karma"] < listing["karma_cost"]:
            return {"success": False, "error": "Insufficient Eco-Karma."}

        teacher_id = listing["teacher_id"]
        teacher = self.get_user(teacher_id)

        # Transfer Karma
        learner["eco_karma"] -= listing["karma_cost"]
        teacher["eco_karma"] += listing["karma_cost"]

        # Update stats
        learner["completed_swaps"] += 1
        teacher["completed_swaps"] += 1

        # Mark listing as fulfilled (or keep active for multiple learners, we'll mark fulfilled for simplicity)
        listing["status"] = "fulfilled"

        swap_record = {
            "swap_id": f"swap_{len(self.swaps) + 1}",
            "learner_id": learner_id,
            "teacher_id": teacher_id,
            "skill_name": listing["skill_name"],
            "karma_transferred": listing["karma_cost"],
            "status": "completed",
        }
        self.swaps.append(swap_record)

        return {"success": True, "swap_record": swap_record}
