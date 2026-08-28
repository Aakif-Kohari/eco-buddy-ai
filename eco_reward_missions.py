"""
Eco Reward Missions Engine.

Daily and weekly sustainability missions that users complete for Eco-Coins.
Supports mission chains, streaks, difficulty tiers, a reward shop, and
a seasonal pass with tiered unlocks.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class MissionType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BONUS = "bonus"
    CHAIN = "chain"
    SEASONAL = "seasonal"


class MissionDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EPIC = "epic"


class MissionStatus(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class RewardType(str, Enum):
    ECO_COINS = "eco_coins"
    BADGE = "badge"
    TITLE = "title"
    THEME = "theme"
    AVATAR = "avatar"
    REAL_WORLD = "real_world"


class SeasonTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class MissionObjective:
    objective_id: str
    description: str
    target: float
    unit: str
    current: float = 0.0

    @property
    def progress_pct(self) -> float:
        if self.target <= 0:
            return 0.0
        return round(min((self.current / self.target) * 100, 100), 1)

    @property
    def is_complete(self) -> bool:
        return self.current >= self.target


@dataclass
class Mission:
    mission_id: str
    title: str
    description: str
    mission_type: MissionType
    difficulty: MissionDifficulty
    eco_coin_reward: int
    xp_reward: int
    objectives: List[MissionObjective] = field(default_factory=list)
    status: MissionStatus = MissionStatus.AVAILABLE
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    expires_at: Optional[str] = None
    chain_id: Optional[str] = None
    chain_order: int = 0
    prerequisites: List[str] = field(default_factory=list)
    bonus_multiplier: float = 1.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def all_objectives_met(self) -> bool:
        return all(o.is_complete for o in self.objectives) if self.objectives else False


@dataclass
class UserMission:
    user_id: str
    mission_id: str
    status: MissionStatus = MissionStatus.ACTIVE
    progress: Dict[str, float] = field(default_factory=dict)
    started_at: str = ""
    completed_at: Optional[str] = None
    coins_earned: int = 0
    xp_earned: int = 0

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()


@dataclass
class MissionChain:
    chain_id: str
    name: str
    description: str
    mission_ids: List[str] = field(default_factory=list)
    total_reward: int = 0
    completed: bool = False


@dataclass
class ShopItem:
    item_id: str
    name: str
    description: str
    reward_type: RewardType
    cost_coins: int
    stock: int = -1  # -1 = unlimited
    category: str = "general"
    limited_time: bool = False
    available_until: Optional[str] = None


@dataclass
class UserPurchase:
    purchase_id: str
    user_id: str
    item_id: str
    cost_coins: int
    purchased_at: str = ""

    def __post_init__(self):
        if not self.purchased_at:
            self.purchased_at = datetime.now().isoformat()


@dataclass
class SeasonPassTier:
    tier: SeasonTier
    required_xp: int
    reward_coins: int
    reward_items: List[str] = field(default_factory=list)


@dataclass
class SeasonPass:
    season_id: str
    name: str
    start_date: str
    end_date: str
    tiers: List[SeasonPassTier] = field(default_factory=list)
    user_xp: int = 0
    current_tier: int = 0


@dataclass
class StreakInfo:
    current_streak: int = 0
    longest_streak: int = 0
    last_mission_date: Optional[str] = None
    streak_multiplier: float = 1.0


# ──────────────────────────────────────────────────────────────────────────────
# Core Engine
# ──────────────────────────────────────────────────────────────────────────────

class EcoRewardMissionsEngine:
    """Manages eco missions, rewards, shops, streaks, and season passes."""

    def __init__(self) -> None:
        self.missions: Dict[str, Mission] = {}
        self.user_missions: Dict[str, Dict[str, UserMission]] = {}
        self.user_coins: Dict[str, int] = {}
        self.user_xp: Dict[str, int] = {}
        self.user_streaks: Dict[str, StreakInfo] = {}
        self.chains: Dict[str, MissionChain] = {}
        self.shop_items: Dict[str, ShopItem] = {}
        self.user_purchases: Dict[str, List[UserPurchase]] = {}
        self.season_passes: Dict[str, SeasonPass] = {}
        self.user_season_xp: Dict[str, Dict[str, int]] = {}  # user_id -> {season_id: xp}
        self.badge_collection: Dict[str, List[str]] = {}
        self.title_collection: Dict[str, List[str]] = {}

    # ── Mission Management ────────────────────────────────────────────────

    def create_mission(
        self,
        title: str,
        description: str,
        mission_type: MissionType,
        difficulty: MissionDifficulty,
        eco_coin_reward: int,
        xp_reward: int,
        objectives: Optional[List[Dict[str, Any]]] = None,
        category: str = "general",
        tags: Optional[List[str]] = None,
        expires_hours: Optional[int] = None,
        chain_id: Optional[str] = None,
        chain_order: int = 0,
        prerequisites: Optional[List[str]] = None,
    ) -> Mission:
        """Creates a new mission."""
        mission_id = f"m_{uuid.uuid4().hex[:10]}"
        expires_at = None
        if expires_hours:
            expires_at = (datetime.now() + timedelta(hours=expires_hours)).isoformat()

        mission = Mission(
            mission_id=mission_id,
            title=title,
            description=description,
            mission_type=mission_type,
            difficulty=difficulty,
            eco_coin_reward=eco_coin_reward,
            xp_reward=xp_reward,
            category=category,
            tags=tags or [],
            expires_at=expires_at,
            chain_id=chain_id,
            chain_order=chain_order,
            prerequisites=prerequisites or [],
        )

        if objectives:
            for obj in objectives:
                mission.objectives.append(MissionObjective(
                    objective_id=f"obj_{uuid.uuid4().hex[:8]}",
                    description=obj.get("description", ""),
                    target=obj.get("target", 1.0),
                    unit=obj.get("unit", "units"),
                ))

        self.missions[mission_id] = mission
        return mission

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        return self.missions.get(mission_id)

    def list_missions(
        self,
        mission_type: Optional[MissionType] = None,
        difficulty: Optional[MissionDifficulty] = None,
        category: Optional[str] = None,
        status: Optional[MissionStatus] = None,
    ) -> List[Mission]:
        results = list(self.missions.values())
        if mission_type:
            results = [m for m in results if m.mission_type == mission_type]
        if difficulty:
            results = [m for m in results if m.difficulty == difficulty]
        if category:
            results = [m for m in results if m.category == category]
        if status:
            results = [m for m in results if m.status == status]
        return results

    def delete_mission(self, mission_id: str) -> bool:
        if mission_id not in self.missions:
            return False
        del self.missions[mission_id]
        return True

    # ── Mission Acceptance & Progress ─────────────────────────────────────

    def accept_mission(self, user_id: str, mission_id: str) -> Dict[str, Any]:
        """User accepts/starts a mission."""
        mission = self.get_mission(mission_id)
        if not mission:
            return {"success": False, "error": "Mission not found."}

        if mission.status != MissionStatus.AVAILABLE:
            return {"success": False, "error": "Mission not available."}

        # Check prerequisites
        user_completed = self._get_user_completed_ids(user_id)
        for prereq in mission.prerequisites:
            if prereq not in user_completed:
                return {"success": False, "error": f"Prerequisite not met: {prereq}"}

        user_missions = self.user_missions.setdefault(user_id, {})
        if mission_id in user_missions and user_missions[mission_id].status == MissionStatus.ACTIVE:
            return {"success": False, "error": "Already accepted."}

        user_missions[mission_id] = UserMission(
            user_id=user_id, mission_id=mission_id
        )
        mission.status = MissionStatus.ACTIVE
        return {"success": True, "mission": mission}

    def update_objective_progress(
        self, user_id: str, mission_id: str, objective_id: str, amount: float
    ) -> Dict[str, Any]:
        """Updates progress on a specific objective."""
        user_missions = self.user_missions.get(user_id, {})
        user_mission = user_missions.get(mission_id)
        if not user_mission or user_mission.status != MissionStatus.ACTIVE:
            return {"success": False, "error": "Mission not active."}

        mission = self.get_mission(mission_id)
        if not mission:
            return {"success": False, "error": "Mission not found."}

        objective = None
        for obj in mission.objectives:
            if obj.objective_id == objective_id:
                objective = obj
                break
        if not objective:
            return {"success": False, "error": "Objective not found."}

        objective.current = min(objective.current + amount, objective.target)
        user_mission.progress[objective_id] = objective.current

        coins_earned = 0
        xp_earned = 0
        mission_completed = False

        if mission.all_objectives_met:
            streak = self.user_streaks.get(user_id, StreakInfo())
            multiplier = streak.streak_multiplier
            coins_earned = int(mission.eco_coin_reward * mission.bonus_multiplier * multiplier)
            xp_earned = int(mission.xp_reward * multiplier)

            user_mission.status = MissionStatus.COMPLETED
            user_mission.completed_at = datetime.now().isoformat()
            user_mission.coins_earned = coins_earned
            user_mission.xp_earned = xp_earned
            mission.status = MissionStatus.COMPLETED

            self.user_coins[user_id] = self.user_coins.get(user_id, 0) + coins_earned
            self.user_xp[user_id] = self.user_xp.get(user_id, 0) + xp_earned

            self._update_streak(user_id)
            mission_completed = True

            # Check chain completion
            if mission.chain_id:
                self._check_chain_completion(user_id, mission.chain_id)

        return {
            "success": True,
            "objective_progress": objective.progress_pct,
            "mission_completed": mission_completed,
            "coins_earned": coins_earned,
            "xp_earned": xp_earned,
        }

    def get_user_active_missions(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all active missions for a user with progress info."""
        user_missions = self.user_missions.get(user_id, {})
        results = []
        for mid, um in user_missions.items():
            if um.status == MissionStatus.ACTIVE:
                mission = self.get_mission(mid)
                if mission:
                    obj_progress = []
                    for obj in mission.objectives:
                        obj_progress.append({
                            "objective_id": obj.objective_id,
                            "description": obj.description,
                            "progress": obj.current,
                            "target": obj.target,
                            "unit": obj.unit,
                            "percentage": obj.progress_pct,
                        })
                    results.append({
                        "mission": mission,
                        "user_mission": um,
                        "objectives": obj_progress,
                    })
        return results

    def get_user_completed_missions(self, user_id: str) -> List[Dict[str, Any]]:
        """Returns all completed missions for a user."""
        user_missions = self.user_missions.get(user_id, {})
        results = []
        for mid, um in user_missions.items():
            if um.status == MissionStatus.COMPLETED:
                mission = self.get_mission(mid)
                if mission:
                    results.append({"mission": mission, "user_mission": um})
        return results

    # ── Mission Chains ────────────────────────────────────────────────────

    def create_chain(
        self, name: str, description: str, mission_configs: List[Dict[str, Any]]
    ) -> MissionChain:
        """Creates a chain of sequential missions."""
        chain_id = f"chain_{uuid.uuid4().hex[:8]}"
        chain = MissionChain(chain_id=chain_id, name=name, description=description)

        for i, cfg in enumerate(mission_configs):
            mission = self.create_mission(
                title=cfg.get("title", f"Step {i + 1}"),
                description=cfg.get("description", ""),
                mission_type=MissionType.CHAIN,
                difficulty=MissionDifficulty(cfg.get("difficulty", "medium")),
                eco_coin_reward=cfg.get("eco_coin_reward", 50),
                xp_reward=cfg.get("xp_reward", 25),
                objectives=cfg.get("objectives"),
                chain_id=chain_id,
                chain_order=i,
                prerequisites=[mission_configs[i - 1]["title"]] if i > 0 else [],
            )
            chain.mission_ids.append(mission.mission_id)
            chain.total_reward += cfg.get("eco_coin_reward", 50)

        self.chains[chain_id] = chain
        return chain

    def get_chain(self, chain_id: str) -> Optional[MissionChain]:
        return self.chains.get(chain_id)

    def get_user_chain_progress(
        self, user_id: str, chain_id: str
    ) -> Dict[str, Any]:
        """Returns a user's progress through a mission chain."""
        chain = self.get_chain(chain_id)
        if not chain:
            return {"error": "Chain not found."}

        steps = []
        for mid in chain.mission_ids:
            mission = self.get_mission(mid)
            user_missions = self.user_missions.get(user_id, {})
            um = user_missions.get(mid)
            steps.append({
                "mission_id": mid,
                "title": mission.title if mission else "?",
                "status": um.status.value if um else "not_started",
                "completed": um.status == MissionStatus.COMPLETED if um else False,
            })

        completed_count = sum(1 for s in steps if s["completed"])
        return {
            "chain_id": chain_id,
            "name": chain.name,
            "total_steps": len(steps),
            "completed_steps": completed_count,
            "progress_pct": round((completed_count / len(steps) * 100) if steps else 0, 1),
            "steps": steps,
            "total_reward": chain.total_reward,
        }

    # ── Streaks ───────────────────────────────────────────────────────────

    def _update_streak(self, user_id: str) -> None:
        """Updates a user's daily mission streak."""
        streak = self.user_streaks.get(user_id, StreakInfo())
        today = datetime.now().strftime("%Y-%m-%d")

        if streak.last_mission_date == today:
            return

        if streak.last_mission_date:
            last = datetime.strptime(streak.last_mission_date, "%Y-%m-%d")
            diff = (datetime.now() - last).days
            if diff == 1:
                streak.current_streak += 1
            elif diff > 1:
                streak.current_streak = 1
        else:
            streak.current_streak = 1

        streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        streak.last_mission_date = today

        # Streak multiplier: +5% per day, max 2x
        streak.streak_multiplier = min(1.0 + streak.current_streak * 0.05, 2.0)
        self.user_streaks[user_id] = streak

    def get_streak(self, user_id: str) -> StreakInfo:
        return self.user_streaks.get(user_id, StreakInfo())

    # ── Reward Shop ───────────────────────────────────────────────────────

    def add_shop_item(
        self,
        name: str,
        description: str,
        reward_type: RewardType,
        cost_coins: int,
        stock: int = -1,
        category: str = "general",
        limited_time: bool = False,
        available_until: Optional[str] = None,
    ) -> ShopItem:
        """Adds an item to the reward shop."""
        item_id = f"shop_{uuid.uuid4().hex[:8]}"
        item = ShopItem(
            item_id=item_id,
            name=name,
            description=description,
            reward_type=reward_type,
            cost_coins=cost_coins,
            stock=stock,
            category=category,
            limited_time=limited_time,
            available_until=available_until,
        )
        self.shop_items[item_id] = item
        return item

    def get_shop_items(
        self,
        category: Optional[str] = None,
        reward_type: Optional[RewardType] = None,
    ) -> List[ShopItem]:
        """Returns available shop items."""
        items = [
            i for i in self.shop_items.values()
            if i.stock != 0
            and (not i.limited_time or not i.available_until or i.available_until > datetime.now().isoformat())
        ]
        if category:
            items = [i for i in items if i.category == category]
        if reward_type:
            items = [i for i in items if i.reward_type == reward_type]
        return items

    def purchase_item(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """User purchases a shop item with eco-coins."""
        item = self.shop_items.get(item_id)
        if not item:
            return {"success": False, "error": "Item not found."}
        if item.stock == 0:
            return {"success": False, "error": "Out of stock."}

        user_coins = self.user_coins.get(user_id, 0)
        if user_coins < item.cost_coins:
            return {"success": False, "error": "Insufficient eco-coins.", "balance": user_coins}

        self.user_coins[user_id] = user_coins - item.cost_coins
        if item.stock > 0:
            item.stock -= 1

        purchase = UserPurchase(
            purchase_id=f"pur_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            item_id=item_id,
            cost_coins=item.cost_coins,
        )
        self.user_purchases.setdefault(user_id, []).append(purchase)

        # Apply reward
        if item.reward_type == RewardType.BADGE:
            self.badge_collection.setdefault(user_id, []).append(item.name)
        elif item.reward_type == RewardType.TITLE:
            self.title_collection.setdefault(user_id, []).append(item.name)

        return {
            "success": True,
            "purchase": purchase,
            "remaining_coins": self.user_coins[user_id],
        }

    def get_user_purchases(self, user_id: str) -> List[UserPurchase]:
        return self.user_purchases.get(user_id, [])

    # ── Season Pass ───────────────────────────────────────────────────────

    def create_season_pass(
        self,
        name: str,
        start_date: str,
        end_date: str,
        tier_rewards: Optional[List[Dict[str, Any]]] = None,
    ) -> SeasonPass:
        """Creates a new season pass."""
        season_id = f"sp_{uuid.uuid4().hex[:8]}"
        sp = SeasonPass(
            season_id=season_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
        )

        default_tiers = [
            {"tier": "bronze", "required_xp": 100, "reward_coins": 50},
            {"tier": "silver", "required_xp": 300, "reward_coins": 100},
            {"tier": "gold", "required_xp": 600, "reward_coins": 200},
            {"tier": "platinum", "required_xp": 1000, "reward_coins": 500},
        ]

        tiers_data = tier_rewards or default_tiers
        for td in tiers_data:
            sp.tiers.append(SeasonPassTier(
                tier=SeasonTier(td["tier"]),
                required_xp=td["required_xp"],
                reward_coins=td["reward_coins"],
                reward_items=td.get("reward_items", []),
            ))

        self.season_passes[season_id] = sp
        return sp

    def get_season_pass(self, season_id: str) -> Optional[SeasonPass]:
        return self.season_passes.get(season_id)

    def add_season_xp(self, user_id: str, season_id: str, xp: int) -> Dict[str, Any]:
        """Adds XP to a user's season pass progress."""
        sp = self.get_season_pass(season_id)
        if not sp:
            return {"success": False, "error": "Season pass not found."}

        user_season = self.user_season_xp.setdefault(user_id, {})
        current_xp = user_season.get(season_id, 0)
        user_season[season_id] = current_xp + xp
        sp.user_xp = user_season[season_id]

        # Determine tier
        new_tier = 0
        for i, tier in enumerate(sp.tiers):
            if sp.user_xp >= tier.required_xp:
                new_tier = i + 1

        tier_unlocked = new_tier > sp.current_tier
        sp.current_tier = new_tier

        return {
            "success": True,
            "total_xp": sp.user_xp,
            "current_tier": new_tier,
            "tier_unlocked": tier_unlocked,
        }

    def get_season_progress(self, user_id: str, season_id: str) -> Dict[str, Any]:
        """Returns a user's season pass progress."""
        sp = self.get_season_pass(season_id)
        if not sp:
            return {"error": "Season not found."}

        user_xp = self.user_season_xp.get(user_id, {}).get(season_id, 0)
        tiers = []
        for i, tier in enumerate(sp.tiers):
            reached = user_xp >= tier.required_xp
            tiers.append({
                "tier": tier.tier.value,
                "required_xp": tier.required_xp,
                "reward_coins": tier.reward_coins,
                "reached": reached,
                "reward_items": tier.reward_items,
            })

        next_tier = None
        if sp.current_tier < len(sp.tiers):
            next_tier = {
                "tier": sp.tiers[sp.current_tier].tier.value,
                "required_xp": sp.tiers[sp.current_tier].required_xp,
                "xp_needed": sp.tiers[sp.current_tier].required_xp - user_xp,
            }

        return {
            "user_xp": user_xp,
            "current_tier": sp.current_tier,
            "tiers": tiers,
            "next_tier": next_tier,
        }

    # ── User Profile & Stats ──────────────────────────────────────────────

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Returns a comprehensive user profile."""
        coins = self.user_coins.get(user_id, 0)
        xp = self.user_xp.get(user_id, 0)
        streak = self.get_streak(user_id)
        completed = self.get_user_completed_missions(user_id)
        badges = self.badge_collection.get(user_id, [])
        titles = self.title_collection.get(user_id, [])

        level = int(math.log2(xp // 25 + 1)) + 1 if xp > 0 else 1

        return {
            "user_id": user_id,
            "eco_coins": coins,
            "total_xp": xp,
            "level": level,
            "current_streak": streak.current_streak,
            "longest_streak": streak.longest_streak,
            "streak_multiplier": streak.streak_multiplier,
            "missions_completed": len(completed),
            "badges": badges,
            "titles": titles,
            "total_purchases": len(self.get_user_purchases(user_id)),
        }

    def get_leaderboard(self, sort_by: str = "coins", limit: int = 20) -> List[Dict[str, Any]]:
        """Returns a global leaderboard."""
        sort_keys = {
            "coins": lambda uid: self.user_coins.get(uid, 0),
            "xp": lambda uid: self.user_xp.get(uid, 0),
            "streak": lambda uid: self.user_streaks.get(uid, StreakInfo()).longest_streak,
        }
        key_fn = sort_keys.get(sort_by, sort_keys["coins"])

        all_users = set(self.user_coins.keys()) | set(self.user_xp.keys())
        ranked = sorted(all_users, key=key_fn, reverse=True)[:limit]

        entries = []
        for rank, uid in enumerate(ranked, 1):
            entries.append({
                "rank": rank,
                "user_id": uid,
                "eco_coins": self.user_coins.get(uid, 0),
                "total_xp": self.user_xp.get(uid, 0),
                "streak": self.user_streaks.get(uid, StreakInfo()).longest_streak,
            })
        return entries

    # ── Daily Mission Generation ──────────────────────────────────────────

    def generate_daily_missions(self, user_id: str) -> List[Mission]:
        """Generates a fresh set of daily missions for a user."""
        templates = [
            {"title": "Eco Commute", "desc": "Use green transport today", "cat": "transport", "obj": {"description": "Commute sustainably", "target": 1.0, "unit": "trip"}, "coins": 15, "xp": 10},
            {"title": "Meatless Meal", "desc": "Eat a plant-based meal", "cat": "food", "obj": {"description": "Eat plant-based", "target": 1.0, "unit": "meal"}, "coins": 10, "xp": 8},
            {"title": "Energy Saver", "desc": "Reduce energy usage today", "cat": "energy", "obj": {"description": "Save 2 kWh", "target": 2.0, "unit": "kWh"}, "coins": 20, "xp": 12},
            {"title": "Waste Warrior", "desc": "Sort and recycle all waste", "cat": "waste", "obj": {"description": "Recycle items", "target": 3.0, "unit": "items"}, "coins": 12, "xp": 8},
            {"title": "Water Watcher", "desc": "Keep showers under 5 minutes", "cat": "water", "obj": {"description": "Short showers", "target": 2.0, "unit": "showers"}, "coins": 10, "xp": 8},
            {"title": "Green Shopping", "desc": "Buy a local/organic product", "cat": "shopping", "obj": {"description": "Buy sustainable", "target": 1.0, "unit": "item"}, "coins": 15, "xp": 10},
            {"title": "Nature Break", "desc": "Spend 20 min outdoors", "cat": "lifestyle", "obj": {"description": "Outdoor time", "target": 20.0, "unit": "minutes"}, "coins": 10, "xp": 8},
            {"title": "Zero Waste Lunch", "desc": "Generate zero packaging waste", "cat": "waste", "obj": {"description": "Zero-waste meal", "target": 1.0, "unit": "meal"}, "coins": 18, "xp": 12},
        ]

        selected = random.sample(templates, min(5, len(templates)))
        missions = []
        for t in selected:
            m = self.create_mission(
                title=t["title"],
                description=t["desc"],
                mission_type=MissionType.DAILY,
                difficulty=MissionDifficulty.EASY,
                eco_coin_reward=t["coins"],
                xp_reward=t["xp"],
                objectives=[t["obj"]],
                category=t["cat"],
                tags=["daily"],
                expires_hours=24,
            )
            missions.append(m)
        return missions

    # ── Private Helpers ───────────────────────────────────────────────────

    def _get_user_completed_ids(self, user_id: str) -> List[str]:
        user_missions = self.user_missions.get(user_id, {})
        return [
            mid for mid, um in user_missions.items()
            if um.status == MissionStatus.COMPLETED
        ]

    def _check_chain_completion(self, user_id: str, chain_id: str) -> None:
        chain = self.get_chain(chain_id)
        if not chain:
            return
        user_missions = self.user_missions.get(user_id, {})
        all_done = all(
            user_missions.get(mid, UserMission(user_id="", mission_id="")).status == MissionStatus.COMPLETED
            for mid in chain.mission_ids
        )
        if all_done:
            chain.completed = True
            self.user_coins[user_id] = self.user_coins.get(user_id, 0) + chain.total_reward

    @staticmethod
    def get_difficulty_rewards(difficulty: MissionDifficulty) -> Dict[str, int]:
        """Returns base reward values for a difficulty level."""
        return {
            MissionDifficulty.EASY: {"coins": 10, "xp": 5},
            MissionDifficulty.MEDIUM: {"coins": 25, "xp": 15},
            MissionDifficulty.HARD: {"coins": 50, "xp": 30},
            MissionDifficulty.EPIC: {"coins": 100, "xp": 60},
        }.get(difficulty, {"coins": 10, "xp": 5})
