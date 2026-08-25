"""
Eco-Community Challenges Core Service Layer
Encapsulates business logic, recommendations, challenge filtering, progress calculation, and leaderboard scoring.
"""

from typing import List, Dict, Any, Optional
import logging

from eco_community_challenges_types import (
    CommunityChallenge,
    ChallengeCategory,
    ChallengeDifficulty,
    UserChallengeEnrollment,
    ChallengeAnalyticsSummary,
)
from eco_community_challenges_db import (
    init_community_challenges_db,
    get_all_active_challenges,
    enroll_user_in_challenge,
    get_user_enrollments,
    record_challenge_progress,
    get_community_analytics_summary,
)

logger = logging.getLogger(__name__)


class EcoCommunityChallengesService:
    def __init__(self, db_name: str = "eco_buddy.db"):
        self.db_name = db_name
        init_community_challenges_db(self.db_name)

    def get_catalog(
        self,
        category_filter: Optional[str] = None,
        difficulty_filter: Optional[str] = None
    ) -> List[CommunityChallenge]:
        """Retrieves and filters active challenges by category and difficulty."""
        challenges = get_all_active_challenges(self.db_name)
        if category_filter and category_filter != "All":
            challenges = [c for c in challenges if c.category.value == category_filter]
        if difficulty_filter and difficulty_filter != "All":
            challenges = [c for c in challenges if c.difficulty.value == difficulty_filter]
        return challenges

    def enroll_user(self, user_id: int, challenge_id: int) -> Optional[UserChallengeEnrollment]:
        """Enrolls a user in a challenge with validation."""
        return enroll_user_in_challenge(user_id, challenge_id, self.db_name)

    def get_active_user_enrollments(self, user_id: int) -> List[Dict[str, Any]]:
        """Gets currently active challenge enrollments for a user."""
        return get_user_enrollments(user_id, status_filter="ACTIVE", db_name=self.db_name)

    def get_user_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Gets all challenge enrollments for a user (Active, Completed, Failed)."""
        return get_user_enrollments(user_id, status_filter=None, db_name=self.db_name)

    def log_progress(self, enrollment_id: int, increment_value: float, notes: str = "") -> Dict[str, Any]:
        """Logs user progress toward an enrolled challenge."""
        if increment_value <= 0:
            return {"success": False, "message": "Increment value must be positive."}
        return record_challenge_progress(enrollment_id, increment_value, notes, self.db_name)

    def get_impact_analytics(self) -> ChallengeAnalyticsSummary:
        """Calculates global community metrics and CO2 impact."""
        return get_community_analytics_summary(self.db_name)

    def recommend_challenges_for_user(self, user_id: int, preferred_categories: Optional[List[str]] = None) -> List[CommunityChallenge]:
        """Recommends relevant eco challenges based on past performance and user preferences."""
        catalog = self.get_catalog()
        user_enrollments = self.get_user_history(user_id)
        enrolled_ids = {e["challenge_id"] for e in user_enrollments if e["status"] == "ACTIVE"}

        # Filter out already active challenges
        available = [c for c in catalog if c.id not in enrolled_ids]

        if preferred_categories:
            recommended = [c for c in available if c.category.value in preferred_categories]
            if recommended:
                return recommended[:3]

        return available[:3]
