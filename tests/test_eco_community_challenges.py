"""
Unit and Integration Tests for Eco-Community Challenges Engine
"""

import unittest
import os
import sqlite3
from src.community.eco_community_challenges_types import (
    ChallengeCategory,
    ChallengeDifficulty,
    VerificationType,
    ChallengeCriteria,
    CommunityChallenge,
    UserChallengeEnrollment,
)
from src.community.eco_community_challenges_db import (
    init_community_challenges_db,
    get_all_active_challenges,
    enroll_user_in_challenge,
    get_user_enrollments,
    record_challenge_progress,
    get_community_analytics_summary,
)
from src.community.eco_community_challenges_service import EcoCommunityChallengesService

TEST_DB = "test_eco_community_challenges.db"


class TestCommunityChallengesEngine(unittest.TestCase):
    def setUp(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_community_challenges_db(TEST_DB)
        self.service = EcoCommunityChallengesService(db_name=TEST_DB)

    def tearDown(self):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_database_initialization_and_seeding(self):
        challenges = get_all_active_challenges(TEST_DB)
        self.assertGreaterEqual(len(challenges), 5)
        self.assertEqual(challenges[0].category, ChallengeCategory.ZERO_WASTE)

    def test_user_enrollment(self):
        enrollment = self.service.enroll_user(user_id=101, challenge_id=1)
        self.assertIsNotNone(enrollment)
        self.assertEqual(enrollment.user_id, 101)
        self.assertEqual(enrollment.challenge_id, 1)
        self.assertEqual(enrollment.status, "ACTIVE")

        # Duplicate enrollment should return None
        duplicate = self.service.enroll_user(user_id=101, challenge_id=1)
        self.assertIsNone(duplicate)

    def test_progress_logging_and_completion(self):
        enrollment = self.service.enroll_user(user_id=102, challenge_id=1)
        self.assertIsNotNone(enrollment)

        # Log partial progress
        res1 = self.service.log_progress(enrollment.id, increment_value=5.0)
        self.assertTrue(res1["success"])
        self.assertFalse(res1["completed"])

        # Log remaining progress to complete
        res2 = self.service.log_progress(enrollment.id, increment_value=10.0)
        self.assertTrue(res2["success"])
        self.assertTrue(res2["completed"])
        self.assertGreater(res2["xp_earned"], 0)

    def test_catalog_filtering(self):
        zero_waste_challenges = self.service.get_catalog(category_filter="Zero Waste")
        self.assertTrue(all(c.category == ChallengeCategory.ZERO_WASTE for c in zero_waste_challenges))

        beginner_challenges = self.service.get_catalog(difficulty_filter="Beginner")
        self.assertTrue(all(c.difficulty == ChallengeDifficulty.BEGINNER for c in beginner_challenges))

    def test_analytics_summary(self):
        self.service.enroll_user(user_id=201, challenge_id=1)
        summary = self.service.get_impact_analytics()
        self.assertGreater(summary.total_challenges, 0)
        self.assertGreaterEqual(summary.active_participants, 1)


if __name__ == "__main__":
    unittest.main()
