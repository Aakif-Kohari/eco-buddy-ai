"""
Unit tests for Eco Reward Missions Engine.
"""

import pytest
from eco_reward_missions import (
    EcoRewardMissionsEngine,
    MissionType,
    MissionDifficulty,
    MissionStatus,
    RewardType,
    SeasonTier,
)


@pytest.fixture
def engine():
    return EcoRewardMissionsEngine()


@pytest.fixture
def mission(engine):
    return engine.create_mission(
        title="Test Mission",
        description="A test mission",
        mission_type=MissionType.DAILY,
        difficulty=MissionDifficulty.EASY,
        eco_coin_reward=20,
        xp_reward=10,
        objectives=[
            {"description": "Do thing", "target": 3.0, "unit": "times"},
        ],
        category="test",
    )


@pytest.fixture
def chain(engine):
    return engine.create_chain(
        name="Green Week",
        description="7-day eco chain",
        mission_configs=[
            {"title": "Day 1", "description": "Start", "eco_coin_reward": 10, "xp_reward": 5, "objectives": [{"description": "Do it", "target": 1.0, "unit": "action"}]},
            {"title": "Day 2", "description": "Continue", "eco_coin_reward": 15, "xp_reward": 8, "objectives": [{"description": "Do it", "target": 1.0, "unit": "action"}]},
            {"title": "Day 3", "description": "Finish", "eco_coin_reward": 25, "xp_reward": 12, "objectives": [{"description": "Do it", "target": 1.0, "unit": "action"}]},
        ],
    )


# ── Mission CRUD ─────────────────────────────────────────────────────────


def test_create_mission(engine, mission):
    assert mission.mission_id.startswith("m_")
    assert mission.title == "Test Mission"
    assert len(mission.objectives) == 1


def test_get_mission(engine, mission):
    assert engine.get_mission(mission.mission_id) is not None


def test_list_missions(engine, mission):
    results = engine.list_missions(mission_type=MissionType.DAILY)
    assert len(results) >= 1


def test_delete_mission(engine, mission):
    assert engine.delete_mission(mission.mission_id) is True
    assert engine.get_mission(mission.mission_id) is None


def test_delete_nonexistent(engine):
    assert engine.delete_mission("nope") is False


# ── Accept & Progress ────────────────────────────────────────────────────


def test_accept_mission(engine, mission):
    result = engine.accept_mission("user1", mission.mission_id)
    assert result["success"] is True
    assert mission.status == MissionStatus.ACTIVE


def test_accept_already_active(engine, mission):
    engine.accept_mission("user1", mission.mission_id)
    result = engine.accept_mission("user1", mission.mission_id)
    assert result["success"] is False


def test_accept_nonexistent(engine):
    result = engine.accept_mission("user1", "nope")
    assert result["success"] is False


def test_progress_objective(engine, mission):
    engine.accept_mission("user1", mission.mission_id)
    obj = mission.objectives[0]
    result = engine.update_objective_progress("user1", mission.mission_id, obj.objective_id, 2.0)
    assert result["success"] is True
    assert result["objective_progress"] == pytest.approx(66.7, abs=0.1)
    assert result["mission_completed"] is False


def test_complete_mission(engine, mission):
    engine.accept_mission("user1", mission.mission_id)
    obj = mission.objectives[0]
    engine.update_objective_progress("user1", mission.mission_id, obj.objective_id, 3.0)

    result = engine.update_objective_progress("user1", mission.mission_id, obj.objective_id, 1.0)
    assert result["mission_completed"] is True
    assert result["coins_earned"] > 0
    assert engine.user_coins["user1"] > 0


def test_progress_not_active(engine, mission):
    result = engine.update_objective_progress("user1", mission.mission_id, "fake", 1.0)
    assert result["success"] is False


def test_get_active_missions(engine, mission):
    engine.accept_mission("user1", mission.mission_id)
    active = engine.get_user_active_missions("user1")
    assert len(active) == 1


def test_get_completed_missions(engine, mission):
    engine.accept_mission("user1", mission.mission_id)
    obj = mission.objectives[0]
    engine.update_objective_progress("user1", mission.mission_id, obj.objective_id, 5.0)
    completed = engine.get_user_completed_missions("user1")
    assert len(completed) == 1


# ── Chains ───────────────────────────────────────────────────────────────


def test_chain_creation(chain):
    assert chain.chain_id.startswith("chain_")
    assert len(chain.mission_ids) == 3
    assert chain.total_reward == 50


def test_chain_progress(engine, chain):
    uid = "user1"
    for mid in chain.mission_ids:
        engine.accept_mission(uid, mid)
        mission = engine.get_mission(mid)
        obj = mission.objectives[0]
        engine.update_objective_progress(uid, mid, obj.objective_id, 1.0)

    progress = engine.get_user_chain_progress(uid, chain.chain_id)
    assert progress["completed_steps"] == 3
    assert progress["progress_pct"] == 100.0


def test_chain_partial(engine, chain):
    engine.accept_mission("user1", chain.mission_ids[0])
    mission = engine.get_mission(chain.mission_ids[0])
    obj = mission.objectives[0]
    engine.update_objective_progress("user1", chain.mission_ids[0], obj.objective_id, 1.0)

    progress = engine.get_user_chain_progress("user1", chain.chain_id)
    assert progress["completed_steps"] == 1
    assert progress["progress_pct"] == pytest.approx(33.3, abs=0.1)


# ── Streaks ──────────────────────────────────────────────────────────────


def test_streak_increments(engine, mission):
    engine.accept_mission("user1", mission.mission_id)
    obj = mission.objectives[0]
    engine.update_objective_progress("user1", mission.mission_id, obj.objective_id, 5.0)

    streak = engine.get_streak("user1")
    assert streak.current_streak >= 1
    assert streak.streak_multiplier >= 1.0


def test_streak_multiplier(engine, mission):
    engine.user_streaks["user1"] = __import__("eco_reward_missions", fromlist=["StreakInfo"]).StreakInfo(
        current_streak=10, longest_streak=10, streak_multiplier=1.5
    )
    engine.accept_mission("user1", mission.mission_id)
    obj = mission.objectives[0]
    engine.update_objective_progress("user1", mission.mission_id, obj.objective_id, 5.0)

    assert engine.user_coins["user1"] >= mission.eco_coin_reward


# ── Shop ─────────────────────────────────────────────────────────────────


def test_add_shop_item(engine):
    item = engine.add_shop_item(
        name="Eco Badge",
        description="A special badge",
        reward_type=RewardType.BADGE,
        cost_coins=50,
    )
    assert item.item_id.startswith("shop_")


def test_purchase_item(engine, mission):
    engine.user_coins["user1"] = 100
    item = engine.add_shop_item(
        name="Badge", description="Test", reward_type=RewardType.BADGE, cost_coins=30
    )
    result = engine.purchase_item("user1", item.item_id)
    assert result["success"] is True
    assert result["remaining_coins"] == 70
    assert "Badge" in engine.badge_collection["user1"]


def test_purchase_insufficient_coins(engine):
    engine.user_coins["user1"] = 5
    item = engine.add_shop_item(
        name="Badge", description="Test", reward_type=RewardType.BADGE, cost_coins=30
    )
    result = engine.purchase_item("user1", item.item_id)
    assert result["success"] is False


def test_purchase_out_of_stock(engine):
    engine.user_coins["user1"] = 100
    item = engine.add_shop_item(
        name="Badge", description="Test", reward_type=RewardType.BADGE, cost_coins=10, stock=0
    )
    result = engine.purchase_item("user1", item.item_id)
    assert result["success"] is False


def test_shop_stock_decrements(engine):
    engine.user_coins["user1"] = 100
    item = engine.add_shop_item(
        name="Badge", description="Test", reward_type=RewardType.BADGE, cost_coins=10, stock=2
    )
    engine.purchase_item("user1", item.item_id)
    assert engine.shop_items[item.item_id].stock == 1


def test_get_shop_items(engine):
    engine.add_shop_item(name="A", description="", reward_type=RewardType.BADGE, cost_coins=10, category="badges")
    engine.add_shop_item(name="B", description="", reward_type=RewardType.TITLE, cost_coins=20, category="titles")
    badges = engine.get_shop_items(category="badges")
    assert len(badges) == 1


# ── Season Pass ──────────────────────────────────────────────────────────


def test_create_season_pass(engine):
    sp = engine.create_season_pass("Summer 2026", "2026-06-01", "2026-08-31")
    assert sp.season_id.startswith("sp_")
    assert len(sp.tiers) == 4


def test_add_season_xp(engine):
    sp = engine.create_season_pass("Summer 2026", "2026-06-01", "2026-08-31")
    result = engine.add_season_xp("user1", sp.season_id, 150)
    assert result["success"] is True
    assert result["current_tier"] == 1  # bronze at 100


def test_season_progress(engine):
    sp = engine.create_season_pass("Summer 2026", "2026-06-01", "2026-08-31")
    engine.add_season_xp("user1", sp.season_id, 350)
    progress = engine.get_season_progress("user1", sp.season_id)
    assert progress["user_xp"] == 350
    assert progress["current_tier"] == 2  # silver at 300


# ── Profile & Leaderboard ────────────────────────────────────────────────


def test_user_profile(engine, mission):
    engine.user_coins["user1"] = 200
    engine.user_xp["user1"] = 100
    engine.badge_collection["user1"] = ["badge1"]
    profile = engine.get_user_profile("user1")
    assert profile["eco_coins"] == 200
    assert profile["total_xp"] == 100
    assert "badge1" in profile["badges"]


def test_leaderboard(engine):
    engine.user_coins["u1"] = 500
    engine.user_coins["u2"] = 300
    engine.user_xp["u1"] = 100
    engine.user_xp["u2"] = 200
    lb = engine.get_leaderboard(sort_by="coins")
    assert lb[0]["user_id"] == "u1"
    assert lb[0]["eco_coins"] == 500


def test_leaderboard_by_xp(engine):
    engine.user_xp["u1"] = 100
    engine.user_xp["u2"] = 300
    lb = engine.get_leaderboard(sort_by="xp")
    assert lb[0]["user_id"] == "u2"


# ── Daily Generation ─────────────────────────────────────────────────────


def test_generate_daily_missions(engine):
    missions = engine.generate_daily_missions("user1")
    assert len(missions) == 5
    assert all(m.mission_type == MissionType.DAILY for m in missions)


# ── Difficulty Rewards ───────────────────────────────────────────────────


def test_difficulty_rewards():
    easy = EcoRewardMissionsEngine.get_difficulty_rewards(MissionDifficulty.EASY)
    epic = EcoRewardMissionsEngine.get_difficulty_rewards(MissionDifficulty.EPIC)
    assert epic["coins"] > easy["coins"]
    assert epic["xp"] > easy["xp"]
