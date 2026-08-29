"""
Unit tests for Community Eco Challenges Engine.
"""

import pytest
from community_challenges_engine import (
    CommunityChallengesEngine,
    ChallengeCategory,
    ChallengeStatus,
    LeaderboardSort,
    MilestoneStatus,
)


@pytest.fixture
def engine():
    """Returns a fresh CommunityChallengesEngine."""
    return CommunityChallengesEngine()


@pytest.fixture
def sample_milestones():
    """Returns a list of sample milestone dicts."""
    return [
        {"name": "First Step", "description": "Complete first step", "target_value": 1.0, "unit": "action", "points_reward": 10},
        {"name": "Halfway", "description": "Reach 50%", "target_value": 5.0, "unit": "actions", "points_reward": 25},
        {"name": "Finish", "description": "Complete all", "target_value": 10.0, "unit": "actions", "points_reward": 50},
    ]


@pytest.fixture
def active_challenge(engine, sample_milestones):
    """Returns a created and activated challenge."""
    challenge = engine.create_challenge(
        title="Test Challenge",
        description="A test challenge for unit tests",
        category=ChallengeCategory.ENERGY,
        created_by="admin",
        start_date="2026-01-01",
        end_date="2026-01-31",
        difficulty="medium",
        base_points=100,
        tags=["test", "energy"],
        milestones=sample_milestones,
    )
    engine.update_challenge_status(challenge.challenge_id, ChallengeStatus.ACTIVE)
    return challenge


# ── Challenge CRUD Tests ─────────────────────────────────────────────────


def test_create_challenge(engine, sample_milestones):
    challenge = engine.create_challenge(
        title="Reduce Energy",
        description="Cut energy use by 20%",
        category=ChallengeCategory.ENERGY,
        created_by="user1",
        start_date="2026-01-01",
        end_date="2026-01-31",
        milestones=sample_milestones,
    )
    assert challenge.challenge_id.startswith("ch_")
    assert challenge.title == "Reduce Energy"
    assert challenge.category == ChallengeCategory.ENERGY
    assert len(challenge.milestones) == 3
    assert challenge.status == ChallengeStatus.DRAFT


def test_get_challenge(engine, active_challenge):
    found = engine.get_challenge(active_challenge.challenge_id)
    assert found is not None
    assert found.title == active_challenge.title


def test_get_challenge_not_found(engine):
    assert engine.get_challenge("nonexistent") is None


def test_update_challenge_status(engine, active_challenge):
    result = engine.update_challenge_status(
        active_challenge.challenge_id, ChallengeStatus.COMPLETED
    )
    assert result is True
    assert active_challenge.status == ChallengeStatus.COMPLETED


def test_invalid_status_transition(engine, active_challenge):
    result = engine.update_challenge_status(
        active_challenge.challenge_id, ChallengeStatus.DRAFT
    )
    assert result is False


def test_list_challenges_filtering(engine):
    engine.create_challenge(
        title="Energy Challenge",
        description="Test",
        category=ChallengeCategory.ENERGY,
        created_by="u1",
        start_date="2026-01-01",
        end_date="2026-01-31",
    )
    engine.create_challenge(
        title="Transport Challenge",
        description="Test",
        category=ChallengeCategory.TRANSPORT,
        created_by="u1",
        start_date="2026-01-01",
        end_date="2026-01-31",
    )
    energy = engine.list_challenges(category=ChallengeCategory.ENERGY)
    assert len(energy) == 1
    assert energy[0].category == ChallengeCategory.ENERGY


def test_delete_challenge(engine):
    challenge = engine.create_challenge(
        title="Delete Me",
        description="Test",
        category=ChallengeCategory.WASTE,
        created_by="u1",
        start_date="2026-01-01",
        end_date="2026-01-31",
    )
    result = engine.delete_challenge(challenge.challenge_id)
    assert result is True
    assert engine.get_challenge(challenge.challenge_id) is None


def test_cannot_delete_active_challenge(engine, active_challenge):
    result = engine.delete_challenge(active_challenge.challenge_id)
    assert result is False


# ── Participation Tests ──────────────────────────────────────────────────


def test_join_challenge(engine, active_challenge):
    result = engine.join_challenge("user1", active_challenge.challenge_id)
    assert result["success"] is True
    participant = engine.get_participant("user1", active_challenge.challenge_id)
    assert participant is not None
    assert participant.user_id == "user1"


def test_join_duplicate(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    result = engine.join_challenge("user1", active_challenge.challenge_id)
    assert result["success"] is False
    assert "Already" in result["error"]


def test_join_full_challenge(engine):
    challenge = engine.create_challenge(
        title="Full Challenge",
        description="Test",
        category=ChallengeCategory.ENERGY,
        created_by="admin",
        start_date="2026-01-01",
        end_date="2026-01-31",
        max_participants=2,
    )
    engine.update_challenge_status(challenge.challenge_id, ChallengeStatus.ACTIVE)

    engine.join_challenge("user1", challenge.challenge_id)
    engine.join_challenge("user2", challenge.challenge_id)
    result = engine.join_challenge("user3", challenge.challenge_id)
    assert result["success"] is False
    assert "full" in result["error"].lower()


def test_leave_challenge(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    result = engine.leave_challenge("user1", active_challenge.challenge_id)
    assert result["success"] is True
    assert engine.get_participant("user1", active_challenge.challenge_id) is None


def test_get_user_challenges(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    user_challenges = engine.get_user_challenges("user1")
    assert len(user_challenges) == 1
    assert user_challenges[0]["challenge"].challenge_id == active_challenge.challenge_id


# ── Milestone Progress Tests ─────────────────────────────────────────────


def test_milestone_progress(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    milestone = active_challenge.milestones[0]

    result = engine.update_milestone_progress(
        "user1", active_challenge.challenge_id, milestone.milestone_id, 1.0
    )
    assert result["success"] is True
    assert result["milestone"].status == MilestoneStatus.COMPLETED
    assert result["points_earned"] > 0


def test_milestone_partial_progress(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    milestone = active_challenge.milestones[1]  # target = 5.0

    result = engine.update_milestone_progress(
        "user1", active_challenge.challenge_id, milestone.milestone_id, 2.0
    )
    assert result["success"] is True
    assert result["milestone"].status == MilestoneStatus.IN_PROGRESS
    assert result["milestone"].progress == 2.0
    assert result["points_earned"] == 0


def test_challenge_completion(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)

    for ms in active_challenge.milestones:
        result = engine.update_milestone_progress(
            "user1", active_challenge.challenge_id, ms.milestone_id, ms.target_value
        )

    participant = engine.get_participant("user1", active_challenge.challenge_id)
    assert participant.is_completed is True
    assert participant.completed_at is not None
    assert result["challenge_completed"] is True


def test_milestone_progress_not_participating(engine, active_challenge):
    milestone = active_challenge.milestones[0]
    result = engine.update_milestone_progress(
        "ghost", active_challenge.challenge_id, milestone.milestone_id, 1.0
    )
    assert result["success"] is False


def test_get_milestone_progress(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    progress = engine.get_milestone_progress("user1", active_challenge.challenge_id)
    assert len(progress) == 3
    assert progress[0]["status"] == MilestoneStatus.LOCKED.value


# ── Leaderboard Tests ────────────────────────────────────────────────────


def test_leaderboard_ordering(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    engine.join_challenge("user2", active_challenge.challenge_id)

    # user1 completes one milestone
    engine.update_milestone_progress(
        "user1", active_challenge.challenge_id,
        active_challenge.milestones[0].milestone_id, 1.0
    )

    leaderboard = engine.get_leaderboard()
    assert len(leaderboard) >= 2
    assert leaderboard[0].user_id == "user1"
    assert leaderboard[0].points >= leaderboard[1].points


def test_leaderboard_by_completions(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    engine.join_challenge("user2", active_challenge.challenge_id)

    for ms in active_challenge.milestones:
        engine.update_milestone_progress(
            "user1", active_challenge.challenge_id, ms.milestone_id, ms.target_value
        )

    lb = engine.get_leaderboard(sort_by=LeaderboardSort.COMPLETIONS)
    assert lb[0].user_id == "user1"
    assert lb[0].challenges_completed == 1


def test_user_rank(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    engine.join_challenge("user2", active_challenge.challenge_id)

    engine.update_milestone_progress(
        "user1", active_challenge.challenge_id,
        active_challenge.milestones[0].milestone_id, 1.0
    )

    rank_info = engine.get_user_rank("user1")
    assert rank_info["rank"] == 1
    assert rank_info["total_users"] == 2


# ── Statistics Tests ─────────────────────────────────────────────────────


def test_challenge_stats(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    engine.join_challenge("user2", active_challenge.challenge_id)

    stats = engine.get_challenge_stats(active_challenge.challenge_id)
    assert stats is not None
    assert stats.total_participants == 2
    assert stats.active_participants == 2
    assert stats.completed_participants == 0


def test_category_breakdown(engine):
    engine.create_challenge(
        title="E1", description="Test",
        category=ChallengeCategory.ENERGY,
        created_by="u1", start_date="2026-01-01", end_date="2026-01-31",
    )
    engine.create_challenge(
        title="E2", description="Test",
        category=ChallengeCategory.ENERGY,
        created_by="u1", start_date="2026-01-01", end_date="2026-01-31",
    )
    breakdown = engine.get_category_breakdown()
    assert breakdown["energy"]["challenge_count"] == 2


def test_user_achievements(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    for ms in active_challenge.milestones:
        engine.update_milestone_progress(
            "user1", active_challenge.challenge_id, ms.milestone_id, ms.target_value
        )
    achievements = engine.get_user_achievements("user1")
    assert achievements["challenges_completed"] == 1
    assert achievements["total_points"] > 0
    assert len(achievements["badges"]) > 0


# ── Template Tests ───────────────────────────────────────────────────────


def test_create_from_template(engine):
    templates = engine.get_available_templates()
    assert "zero_waste_week" in templates

    challenge = engine.create_from_template("zero_waste_week", "user1")
    assert challenge is not None
    assert challenge.title == "Zero Waste Week"
    assert len(challenge.milestones) == 4


def test_template_not_found(engine):
    result = engine.create_from_template("nonexistent", "user1")
    assert result is None


# ── Activity Feed Tests ──────────────────────────────────────────────────


def test_activity_feed(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    feed = engine.get_activity_feed(limit=5)
    assert len(feed) >= 1
    assert feed[-1]["action"] == "challenge_joined"


# ── Streak Tests ─────────────────────────────────────────────────────────


def test_streak_tracking(engine, active_challenge):
    engine.join_challenge("user1", active_challenge.challenge_id)
    engine.update_milestone_progress(
        "user1", active_challenge.challenge_id,
        active_challenge.milestones[0].milestone_id, 1.0
    )
    participant = engine.get_participant("user1", active_challenge.challenge_id)
    assert participant.streak_days >= 1
