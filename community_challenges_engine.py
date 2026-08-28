"""
Community Eco Challenges Engine.

Manages community-wide sustainability challenges: creation, participation,
progress tracking, scoring, leaderboards, and challenge lifecycle management.
Users earn Eco-Points for completing challenge milestones and can compete
on community leaderboards.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class ChallengeStatus(str, Enum):
    """Lifecycle states of a challenge."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ChallengeCategory(str, Enum):
    """Categories of eco challenges."""
    ENERGY = "energy"
    TRANSPORT = "transport"
    FOOD = "food"
    WASTE = "waste"
    WATER = "water"
    BIODIVERSITY = "biodiversity"
    COMMUNITY = "community"
    LIFESTYLE = "lifestyle"


class MilestoneStatus(str, Enum):
    """Status of a participant milestone."""
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class LeaderboardSort(str, Enum):
    """How to sort a leaderboard."""
    POINTS = "points"
    COMPLETIONS = "completions"
    STREAK = "streak"
    EFFICIENCY = "efficiency"


# ──────────────────────────────────────────────────────────────────────────────
# Data Classes
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Milestone:
    """A single milestone within a challenge."""
    milestone_id: str
    name: str
    description: str
    target_value: float
    unit: str
    points_reward: int
    status: MilestoneStatus = MilestoneStatus.LOCKED
    progress: float = 0.0


@dataclass
class Challenge:
    """Represents a community sustainability challenge."""
    challenge_id: str
    title: str
    description: str
    category: ChallengeCategory
    created_by: str
    start_date: str
    end_date: str
    status: ChallengeStatus = ChallengeStatus.DRAFT
    max_participants: int = 0  # 0 means unlimited
    milestones: List[Milestone] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    difficulty: str = "medium"  # easy, medium, hard
    base_points: int = 100
    total_participants: int = 0
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class Participant:
    """Tracks a user's participation in a challenge."""
    user_id: str
    challenge_id: str
    joined_at: str = ""
    completed_at: Optional[str] = None
    total_points_earned: int = 0
    milestones_completed: int = 0
    total_milestones: int = 0
    is_completed: bool = False
    streak_days: int = 0
    last_active_date: Optional[str] = None

    def __post_init__(self):
        if not self.joined_at:
            self.joined_at = datetime.now().isoformat()


@dataclass
class LeaderboardEntry:
    """A single entry on a leaderboard."""
    rank: int
    user_id: str
    display_name: str
    points: int
    challenges_completed: int
    streak_days: int
    efficiency_score: float
    badges: List[str] = field(default_factory=list)


@dataclass
class ChallengeStats:
    """Aggregated statistics for a challenge."""
    total_participants: int
    active_participants: int
    completed_participants: int
    average_progress: float
    completion_rate: float
    total_points_awarded: int
    most_active_day: str
    average_days_to_complete: float


# ──────────────────────────────────────────────────────────────────────────────
# Core Engine
# ──────────────────────────────────────────────────────────────────────────────

class CommunityChallengesEngine:
    """
    Manages community eco challenges: creation, participation, milestone
    tracking, scoring, leaderboards, and statistics.
    """

    def __init__(self) -> None:
        self.challenges: Dict[str, Challenge] = {}
        self.participants: Dict[str, Dict[str, Participant]] = {}  # challenge_id -> {user_id: Participant}
        self.user_points: Dict[str, int] = {}  # user_id -> total lifetime points
        self.user_completions: Dict[str, int] = {}  # user_id -> number of challenges completed
        self.user_badges: Dict[str, List[str]] = {}  # user_id -> list of badge names
        self.activity_log: List[Dict[str, Any]] = []  # chronological activity feed

    # ── Challenge CRUD ────────────────────────────────────────────────────

    def create_challenge(
        self,
        title: str,
        description: str,
        category: ChallengeCategory,
        created_by: str,
        start_date: str,
        end_date: str,
        max_participants: int = 0,
        difficulty: str = "medium",
        base_points: int = 100,
        tags: Optional[List[str]] = None,
        milestones: Optional[List[Dict[str, Any]]] = None,
    ) -> Challenge:
        """
        Creates a new community challenge.

        Args:
            title: Short title for the challenge.
            description: Detailed description of goals and rules.
            category: Challenge category (energy, transport, food, etc.).
            created_by: User ID of the creator.
            start_date: ISO date string for when the challenge begins.
            end_date: ISO date string for when the challenge ends.
            max_participants: Maximum allowed participants (0 = unlimited).
            difficulty: Difficulty level (easy, medium, hard).
            base_points: Base points awarded for completion.
            tags: Optional list of searchable tags.
            milestones: Optional list of milestone dicts.

        Returns:
            The newly created Challenge object.
        """
        challenge_id = f"ch_{uuid.uuid4().hex[:12]}"
        challenge = Challenge(
            challenge_id=challenge_id,
            title=title,
            description=description,
            category=category,
            created_by=created_by,
            start_date=start_date,
            end_date=end_date,
            max_participants=max_participants,
            difficulty=difficulty,
            base_points=base_points,
            tags=tags or [],
        )

        if milestones:
            for ms in milestones:
                milestone = Milestone(
                    milestone_id=f"ms_{uuid.uuid4().hex[:8]}",
                    name=ms.get("name", ""),
                    description=ms.get("description", ""),
                    target_value=ms.get("target_value", 1.0),
                    unit=ms.get("unit", "units"),
                    points_reward=ms.get("points_reward", 10),
                )
                challenge.milestones.append(milestone)

        self.challenges[challenge_id] = challenge
        self._log_activity(created_by, "challenge_created", {
            "challenge_id": challenge_id,
            "title": title,
            "category": category.value,
        })
        return challenge

    def get_challenge(self, challenge_id: str) -> Optional[Challenge]:
        """Retrieves a challenge by ID."""
        return self.challenges.get(challenge_id)

    def update_challenge_status(
        self, challenge_id: str, new_status: ChallengeStatus
    ) -> bool:
        """
        Updates a challenge's lifecycle status.

        Returns:
            True if the status was updated, False if challenge not found.
        """
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return False

        valid_transitions = {
            ChallengeStatus.DRAFT: [ChallengeStatus.ACTIVE, ChallengeStatus.ARCHIVED],
            ChallengeStatus.ACTIVE: [ChallengeStatus.PAUSED, ChallengeStatus.COMPLETED, ChallengeStatus.ARCHIVED],
            ChallengeStatus.PAUSED: [ChallengeStatus.ACTIVE, ChallengeStatus.ARCHIVED],
            ChallengeStatus.COMPLETED: [ChallengeStatus.ARCHIVED],
            ChallengeStatus.ARCHIVED: [],
        }

        allowed = valid_transitions.get(challenge.status, [])
        if new_status not in allowed:
            return False

        challenge.status = new_status
        challenge.updated_at = datetime.now().isoformat()

        self._log_activity(challenge.created_by, "status_changed", {
            "challenge_id": challenge_id,
            "old_status": challenge.status.value,
            "new_status": new_status.value,
        })
        return True

    def list_challenges(
        self,
        category: Optional[ChallengeCategory] = None,
        status: Optional[ChallengeStatus] = None,
        difficulty: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> List[Challenge]:
        """
        Lists challenges with optional filtering.

        Args:
            category: Filter by category.
            status: Filter by status.
            difficulty: Filter by difficulty level.
            tag: Filter by a specific tag.

        Returns:
            List of matching challenges.
        """
        results = list(self.challenges.values())

        if category:
            results = [c for c in results if c.category == category]
        if status:
            results = [c for c in results if c.status == status]
        if difficulty:
            results = [c for c in results if c.difficulty == difficulty]
        if tag:
            results = [c for c in results if tag in c.tags]

        return results

    def delete_challenge(self, challenge_id: str) -> bool:
        """
        Deletes a challenge and all associated participant data.

        Returns:
            True if deleted, False if not found.
        """
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return False

        if challenge.status == ChallengeStatus.ACTIVE:
            return False  # Cannot delete an active challenge

        del self.challenges[challenge_id]
        self.participants.pop(challenge_id, None)
        return True

    # ── Participation ─────────────────────────────────────────────────────

    def join_challenge(self, user_id: str, challenge_id: str) -> Dict[str, Any]:
        """
        Registers a user as a participant in a challenge.

        Returns:
            Dict with 'success' key and optional 'error' or 'participant'.
        """
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return {"success": False, "error": "Challenge not found."}

        if challenge.status not in (ChallengeStatus.ACTIVE, ChallengeStatus.DRAFT):
            return {"success": False, "error": "Challenge is not accepting participants."}

        if challenge_id not in self.participants:
            self.participants[challenge_id] = {}

        if user_id in self.participants[challenge_id]:
            return {"success": False, "error": "Already participating."}

        if (
            challenge.max_participants > 0
            and challenge.total_participants >= challenge.max_participants
        ):
            return {"success": False, "error": "Challenge is full."}

        total_milestones = len(challenge.milestones)
        participant = Participant(
            user_id=user_id,
            challenge_id=challenge_id,
            total_milestones=total_milestones,
        )

        self.participants[challenge_id][user_id] = participant
        challenge.total_participants += 1
        challenge.updated_at = datetime.now().isoformat()

        self._log_activity(user_id, "challenge_joined", {
            "challenge_id": challenge_id,
            "title": challenge.title,
        })

        return {"success": True, "participant": participant}

    def leave_challenge(self, user_id: str, challenge_id: str) -> Dict[str, Any]:
        """
        Removes a user from a challenge.

        Returns:
            Dict with 'success' key and optional 'error'.
        """
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return {"success": False, "error": "Challenge not found."}

        participants = self.participants.get(challenge_id, {})
        if user_id not in participants:
            return {"success": False, "error": "Not participating."}

        del participants[user_id]
        challenge.total_participants = max(0, challenge.total_participants - 1)
        challenge.updated_at = datetime.now().isoformat()

        self._log_activity(user_id, "challenge_left", {
            "challenge_id": challenge_id,
        })
        return {"success": True}

    def get_participant(
        self, user_id: str, challenge_id: str
    ) -> Optional[Participant]:
        """Retrieves a participant record for a specific challenge."""
        return self.participants.get(challenge_id, {}).get(user_id)

    def get_user_challenges(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Returns all challenges a user is participating in, with their progress.

        Returns:
            List of dicts containing challenge and participant info.
        """
        results = []
        for challenge_id, user_map in self.participants.items():
            if user_id in user_map:
                challenge = self.get_challenge(challenge_id)
                if challenge:
                    results.append({
                        "challenge": challenge,
                        "participant": user_map[user_id],
                        "progress_pct": self._calculate_progress_pct(
                            user_map[user_id], challenge
                        ),
                    })
        return results

    # ── Milestone & Progress Tracking ─────────────────────────────────────

    def update_milestone_progress(
        self,
        user_id: str,
        challenge_id: str,
        milestone_id: str,
        progress_value: float,
    ) -> Dict[str, Any]:
        """
        Updates a user's progress on a specific milestone.

        Args:
            user_id: The participant's user ID.
            challenge_id: The challenge ID.
            milestone_id: The milestone ID to update.
            progress_value: New progress value (added to current).

        Returns:
            Dict with success status, points earned, and milestone info.
        """
        participant = self.get_participant(user_id, challenge_id)
        if not participant:
            return {"success": False, "error": "Not participating."}

        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return {"success": False, "error": "Challenge not found."}

        if participant.is_completed:
            return {"success": False, "error": "Challenge already completed."}

        milestone = None
        for ms in challenge.milestones:
            if ms.milestone_id == milestone_id:
                milestone = ms
                break

        if not milestone:
            return {"success": False, "error": "Milestone not found."}

        # Update progress
        milestone.status = MilestoneStatus.IN_PROGRESS
        milestone.progress = min(
            milestone.progress + progress_value, milestone.target_value
        )

        points_earned = 0
        if milestone.progress >= milestone.target_value:
            milestone.status = MilestoneStatus.COMPLETED
            participant.milestones_completed += 1
            points_earned = milestone.points_reward
            participant.total_points_earned += points_earned

            # Award points globally
            self.user_points[user_id] = self.user_points.get(user_id, 0) + points_earned

        # Update streak
        today = datetime.now().strftime("%Y-%m-%d")
        if participant.last_active_date != today:
            last = participant.last_active_date
            if last:
                last_dt = datetime.strptime(last, "%Y-%m-%d")
                today_dt = datetime.strptime(today, "%Y-%m-%d")
                diff = (today_dt - last_dt).days
                if diff == 1:
                    participant.streak_days += 1
                elif diff > 1:
                    participant.streak_days = 1
            else:
                participant.streak_days = 1
            participant.last_active_date = today

        # Check if all milestones are done -> challenge complete
        if participant.milestones_completed >= participant.total_milestones:
            participant.is_completed = True
            participant.completed_at = datetime.now().isoformat()
            bonus = self._calculate_completion_bonus(challenge)
            participant.total_points_earned += bonus
            self.user_points[user_id] = self.user_points.get(user_id, 0) + bonus
            self.user_completions[user_id] = self.user_completions.get(user_id, 0) + 1

            # Award badges
            badges = self._evaluate_badges(user_id, challenge)
            for badge in badges:
                if badge not in self.user_badges.get(user_id, []):
                    self.user_badges.setdefault(user_id, []).append(badge)

            self._log_activity(user_id, "challenge_completed", {
                "challenge_id": challenge_id,
                "points_earned": participant.total_points_earned,
            })

        self._log_activity(user_id, "milestone_progress", {
            "challenge_id": challenge_id,
            "milestone_id": milestone_id,
            "progress": milestone.progress,
            "points_earned": points_earned,
        })

        return {
            "success": True,
            "milestone": milestone,
            "points_earned": points_earned,
            "challenge_completed": participant.is_completed,
            "total_points": participant.total_points_earned,
        }

    def get_milestone_progress(
        self, user_id: str, challenge_id: str
    ) -> List[Dict[str, Any]]:
        """
        Returns all milestone progress for a user in a challenge.

        Returns:
            List of milestone progress dicts.
        """
        participant = self.get_participant(user_id, challenge_id)
        challenge = self.get_challenge(challenge_id)
        if not participant or not challenge:
            return []

        results = []
        for i, ms in enumerate(challenge.milestones):
            pct = (ms.progress / ms.target_value * 100) if ms.target_value > 0 else 0
            results.append({
                "milestone_id": ms.milestone_id,
                "name": ms.name,
                "description": ms.description,
                "target_value": ms.target_value,
                "current_value": ms.progress,
                "unit": ms.unit,
                "percentage": round(min(pct, 100), 1),
                "status": ms.status.value,
                "points_reward": ms.points_reward,
                "order": i + 1,
            })
        return results

    # ── Leaderboard ───────────────────────────────────────────────────────

    def get_leaderboard(
        self,
        challenge_id: Optional[str] = None,
        sort_by: LeaderboardSort = LeaderboardSort.POINTS,
        limit: int = 50,
    ) -> List[LeaderboardEntry]:
        """
        Generates a leaderboard, either for a specific challenge or global.

        Args:
            challenge_id: If provided, leaderboard for this challenge only.
            sort_by: How to sort entries.
            limit: Max entries to return.

        Returns:
            Sorted list of LeaderboardEntry objects.
        """
        user_stats: Dict[str, Dict[str, Any]] = {}

        if challenge_id:
            participants = self.participants.get(challenge_id, {})
            for uid, part in participants.items():
                if uid not in user_stats:
                    user_stats[uid] = {
                        "points": 0,
                        "completions": 0,
                        "streak": 0,
                    }
                user_stats[uid]["points"] = part.total_points_earned
                user_stats[uid]["completions"] = 1 if part.is_completed else 0
                user_stats[uid]["streak"] = part.streak_days
        else:
            for uid in self.user_points:
                user_stats[uid] = {
                    "points": self.user_points.get(uid, 0),
                    "completions": self.user_completions.get(uid, 0),
                    "streak": self._get_max_streak(uid),
                }

        # Calculate efficiency score
        for uid, stats in user_stats.items():
            completions = stats["completions"]
            points = stats["points"]
            streak = stats["streak"]
            # Efficiency = points per completion weighted by streak
            if completions > 0:
                stats["efficiency"] = round(
                    (points / completions) * (1 + streak * 0.05), 2
                )
            else:
                stats["efficiency"] = 0.0

        # Sort
        sort_key_map = {
            LeaderboardSort.POINTS: lambda s: s["points"],
            LeaderboardSort.COMPLETIONS: lambda s: s["completions"],
            LeaderboardSort.STREAK: lambda s: s["streak"],
            LeaderboardSort.EFFICIENCY: lambda s: s["efficiency"],
        }
        key_fn = sort_key_map.get(sort_by, sort_key_map[LeaderboardSort.POINTS])
        sorted_users = sorted(user_stats.items(), key=lambda x: key_fn(x[1]), reverse=True)

        entries = []
        for rank, (uid, stats) in enumerate(sorted_users[:limit], start=1):
            entries.append(LeaderboardEntry(
                rank=rank,
                user_id=uid,
                display_name=uid,  # In production, resolve display name
                points=stats["points"],
                challenges_completed=stats["completions"],
                streak_days=stats["streak"],
                efficiency_score=stats["efficiency"],
                badges=self.user_badges.get(uid, []),
            ))

        return entries

    def get_user_rank(self, user_id: str, challenge_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns a user's rank and surrounding context.

        Returns:
            Dict with rank, total users, and nearby entries.
        """
        leaderboard = self.get_leaderboard(challenge_id=challenge_id, limit=1000)

        user_rank = None
        for entry in leaderboard:
            if entry.user_id == user_id:
                user_rank = entry.rank
                break

        if user_rank is None:
            return {
                "rank": None,
                "total_users": len(leaderboard),
                "message": "User not found on leaderboard.",
            }

        # Get surrounding context (3 above and 3 below)
        start = max(0, user_rank - 4)
        end = min(len(leaderboard), user_rank + 3)
        context = leaderboard[start:end]

        return {
            "rank": user_rank,
            "total_users": len(leaderboard),
            "surrounding": context,
        }

    # ── Statistics & Analytics ────────────────────────────────────────────

    def get_challenge_stats(self, challenge_id: str) -> Optional[ChallengeStats]:
        """
        Computes aggregated statistics for a challenge.

        Returns:
            ChallengeStats object or None if challenge not found.
        """
        challenge = self.get_challenge(challenge_id)
        if not challenge:
            return None

        participants = self.participants.get(challenge_id, {})
        if not participants:
            return ChallengeStats(
                total_participants=0,
                active_participants=0,
                completed_participants=0,
                average_progress=0.0,
                completion_rate=0.0,
                total_points_awarded=0,
                most_active_day="N/A",
                average_days_to_complete=0.0,
            )

        total = len(participants)
        completed = sum(1 for p in participants.values() if p.is_completed)
        active = total - completed

        # Average progress
        progress_values = []
        for part in participants.values():
            if part.total_milestones > 0:
                progress_values.append(
                    part.milestones_completed / part.total_milestones
                )
        avg_progress = (
            sum(progress_values) / len(progress_values) if progress_values else 0.0
        )

        total_points = sum(p.total_points_earned for p in participants.values())

        # Find most active day from activity log
        day_counts: Dict[str, int] = {}
        for entry in self.activity_log:
            if entry.get("data", {}).get("challenge_id") == challenge_id:
                day = entry.get("timestamp", "")[:10]
                day_counts[day] = day_counts.get(day, 0) + 1
        most_active_day = max(day_counts, key=day_counts.get) if day_counts else "N/A"

        # Average days to complete
        completion_days = []
        for part in participants.values():
            if part.completed_at and part.joined_at:
                try:
                    start = datetime.fromisoformat(part.joined_at)
                    end = datetime.fromisoformat(part.completed_at)
                    completion_days.append((end - start).days)
                except (ValueError, TypeError):
                    pass
        avg_days = (
            sum(completion_days) / len(completion_days) if completion_days else 0.0
        )

        return ChallengeStats(
            total_participants=total,
            active_participants=active,
            completed_participants=completed,
            average_progress=round(avg_progress * 100, 1),
            completion_rate=round((completed / total) * 100, 1) if total > 0 else 0.0,
            total_points_awarded=total_points,
            most_active_day=most_active_day,
            average_days_to_complete=round(avg_days, 1),
        )

    def get_category_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a breakdown of challenges by category.

        Returns:
            Dict mapping category name to counts and participant info.
        """
        breakdown: Dict[str, Dict[str, Any]] = {}
        for category in ChallengeCategory:
            challenges = self.list_challenges(category=category)
            total_participants = sum(c.total_participants for c in challenges)
            total_completed = sum(
                sum(
                    1
                    for p in self.participants.get(c.challenge_id, {}).values()
                    if p.is_completed
                )
                for c in challenges
            )
            breakdown[category.value] = {
                "challenge_count": len(challenges),
                "total_participants": total_participants,
                "completed_participants": total_completed,
            }
        return breakdown

    def get_user_achievements(self, user_id: str) -> Dict[str, Any]:
        """
        Returns a comprehensive view of a user's achievements.

        Returns:
            Dict with points, completions, badges, streaks, and rank.
        """
        total_points = self.user_points.get(user_id, 0)
        completions = self.user_completions.get(user_id, 0)
        badges = self.user_badges.get(user_id, [])
        max_streak = self._get_max_streak(user_id)
        rank_info = self.get_user_rank(user_id)

        # Challenges in progress
        in_progress = 0
        for challenge_id, user_map in self.participants.items():
            if user_id in user_map and not user_map[user_id].is_completed:
                in_progress += 1

        return {
            "user_id": user_id,
            "total_points": total_points,
            "challenges_completed": completions,
            "challenges_in_progress": in_progress,
            "badges": badges,
            "max_streak_days": max_streak,
            "global_rank": rank_info.get("rank"),
            "total_users": rank_info.get("total_users", 0),
            "level": self._calculate_level(total_points),
            "xp_to_next_level": self._xp_to_next_level(total_points),
        }

    def get_activity_feed(
        self, challenge_id: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Returns recent activity entries.

        Args:
            challenge_id: Filter by challenge.
            limit: Max entries to return.

        Returns:
            List of activity dicts.
        """
        feed = self.activity_log
        if challenge_id:
            feed = [
                e for e in feed
                if e.get("data", {}).get("challenge_id") == challenge_id
            ]
        return feed[-limit:]

    # ── Challenge Templates ───────────────────────────────────────────────

    def create_from_template(
        self, template_name: str, created_by: str
    ) -> Optional[Challenge]:
        """
        Creates a challenge from a predefined template.

        Args:
            template_name: Name of the template.
            created_by: User ID of the creator.

        Returns:
            The new Challenge, or None if template not found.
        """
        templates = self._get_templates()
        template = templates.get(template_name)
        if not template:
            return None

        return self.create_challenge(**template, created_by=created_by)

    def get_available_templates(self) -> List[str]:
        """Returns list of available template names."""
        return list(self._get_templates().keys())

    # ── Private Helpers ───────────────────────────────────────────────────

    def _calculate_progress_pct(
        self, participant: Participant, challenge: Challenge
    ) -> float:
        """Calculate overall progress percentage for a participant."""
        if not challenge.milestones or participant.total_milestones == 0:
            return 0.0
        return round(
            (participant.milestones_completed / participant.total_milestones) * 100, 1
        )

    def _calculate_completion_bonus(self, challenge: Challenge) -> int:
        """Calculate bonus points for completing all milestones."""
        difficulty_multiplier = {"easy": 1.0, "medium": 1.5, "hard": 2.0}
        mult = difficulty_multiplier.get(challenge.difficulty, 1.0)
        return int(challenge.base_points * mult)

    def _evaluate_badges(
        self, user_id: str, challenge: Challenge
    ) -> List[str]:
        """Evaluate and return new badges earned."""
        badges = []

        completions = self.user_completions.get(user_id, 0)
        if completions == 1:
            badges.append("🌱 First Challenge")
        elif completions == 5:
            badges.append("🌿 Eco Warrior")
        elif completions == 10:
            badges.append("🌳 Sustainability Champion")

        if challenge.difficulty == "hard":
            badges.append("💪 Hard Challenge Master")

        streak = self._get_max_streak(user_id)
        if streak >= 7:
            badges.append("🔥 Week Streak")
        if streak >= 30:
            badges.append("⚡ Monthly Streak")

        total_points = self.user_points.get(user_id, 0)
        if total_points >= 1000:
            badges.append("🏆 Point Collector")

        # Category mastery
        category_count = self._count_category_completions(user_id, challenge.category)
        if category_count >= 3:
            badges.append(
                f"🎓 {challenge.category.value.title()} Expert"
            )

        return badges

    def _count_category_completions(
        self, user_id: str, category: ChallengeCategory
    ) -> int:
        """Count how many challenges of a category a user completed."""
        count = 0
        for challenge_id, user_map in self.participants.items():
            if user_id in user_map and user_map[user_id].is_completed:
                challenge = self.get_challenge(challenge_id)
                if challenge and challenge.category == category:
                    count += 1
        return count

    def _get_max_streak(self, user_id: str) -> int:
        """Get the maximum streak across all challenges for a user."""
        max_streak = 0
        for user_map in self.participants.values():
            if user_id in user_map:
                max_streak = max(max_streak, user_map[user_id].streak_days)
        return max_streak

    def _calculate_level(self, total_points: int) -> int:
        """Calculate user level based on total points (logarithmic scale)."""
        if total_points <= 0:
            return 1
        return int(math.log2(total_points // 50 + 1)) + 1

    def _xp_to_next_level(self, total_points: int) -> int:
        """Calculate XP needed to reach the next level."""
        current_level = self._calculate_level(total_points)
        next_level_threshold = (2 ** (current_level - 1) - 1) * 50
        return max(0, next_level_threshold - total_points)

    def _log_activity(
        self, user_id: str, action: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Logs an activity entry."""
        self.activity_log.append({
            "user_id": user_id,
            "action": action,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        })

    @staticmethod
    def _get_templates() -> Dict[str, Dict[str, Any]]:
        """Returns predefined challenge templates."""
        return {
            "zero_waste_week": {
                "title": "Zero Waste Week",
                "description": (
                    "Reduce your household waste to zero for an entire week. "
                    "Track your daily waste output and aim for landfill-free days."
                ),
                "category": ChallengeCategory.WASTE,
                "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d"),
                "difficulty": "medium",
                "base_points": 150,
                "tags": ["waste", "zero-waste", "weekly"],
                "milestones": [
                    {"name": "Audit Your Waste", "description": "Document your current daily waste", "target_value": 1.0, "unit": "audit", "points_reward": 10},
                    {"name": "Reduce by 50%", "description": "Cut waste output in half", "target_value": 50.0, "unit": "percent", "points_reward": 30},
                    {"name": "Zero Waste Day", "description": "Achieve a zero-waste day", "target_value": 1.0, "unit": "day", "points_reward": 40},
                    {"name": "Full Week Complete", "description": "Complete all 7 days", "target_value": 7.0, "unit": "days", "points_reward": 50},
                ],
            },
            "bike_to_work": {
                "title": "Bike to Work Challenge",
                "description": (
                    "Cycle to work every day for two weeks. "
                    "Track your distance and calculate carbon savings."
                ),
                "category": ChallengeCategory.TRANSPORT,
                "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
                "difficulty": "easy",
                "base_points": 100,
                "tags": ["transport", "cycling", "commute"],
                "milestones": [
                    {"name": "First Ride", "description": "Complete your first bike commute", "target_value": 1.0, "unit": "ride", "points_reward": 10},
                    {"name": "5 Rides", "description": "Bike to work 5 times", "target_value": 5.0, "unit": "rides", "points_reward": 25},
                    {"name": "10 Rides", "description": "Bike to work 10 times", "target_value": 10.0, "unit": "rides", "points_reward": 40},
                    {"name": "Full Fortnight", "description": "Complete all 10 business days", "target_value": 10.0, "unit": "days", "points_reward": 50},
                ],
            },
            "plant_based_month": {
                "title": "Plant-Based Month",
                "description": (
                    "Eat entirely plant-based for 30 days. "
                    "Log your meals and track CO2 savings from avoided animal products."
                ),
                "category": ChallengeCategory.FOOD,
                "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d"),
                "difficulty": "hard",
                "base_points": 200,
                "tags": ["food", "vegan", "monthly"],
                "milestones": [
                    {"name": "First Week", "description": "Complete 7 plant-based days", "target_value": 7.0, "unit": "days", "points_reward": 20},
                    {"name": "Halfway", "description": "15 plant-based days", "target_value": 15.0, "unit": "days", "points_reward": 40},
                    {"name": "30 Days", "description": "Complete the full month", "target_value": 30.0, "unit": "days", "points_reward": 80},
                ],
            },
            "energy_saver": {
                "title": "Home Energy Saver",
                "description": (
                    "Reduce your household electricity consumption by 20% "
                    "over three weeks. Monitor daily usage and adopt energy-saving habits."
                ),
                "category": ChallengeCategory.ENERGY,
                "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=22)).strftime("%Y-%m-%d"),
                "difficulty": "medium",
                "base_points": 120,
                "tags": ["energy", "electricity", "savings"],
                "milestones": [
                    {"name": "Baseline Set", "description": "Record your current usage", "target_value": 1.0, "unit": "baseline", "points_reward": 10},
                    {"name": "10% Reduction", "description": "Cut usage by 10%", "target_value": 10.0, "unit": "percent", "points_reward": 30},
                    {"name": "20% Reduction", "description": "Hit the 20% target", "target_value": 20.0, "unit": "percent", "points_reward": 50},
                ],
            },
            "water_guardian": {
                "title": "Water Guardian",
                "description": (
                    "Reduce your household water consumption by 15% in two weeks. "
                    "Implement water-saving techniques and track daily usage."
                ),
                "category": ChallengeCategory.WATER,
                "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
                "difficulty": "easy",
                "base_points": 80,
                "tags": ["water", "conservation", "household"],
                "milestones": [
                    {"name": "Water Audit", "description": "Complete a water usage audit", "target_value": 1.0, "unit": "audit", "points_reward": 10},
                    {"name": "10% Saved", "description": "Reduce usage by 10%", "target_value": 10.0, "unit": "percent", "points_reward": 25},
                    {"name": "15% Saved", "description": "Hit the 15% target", "target_value": 15.0, "unit": "percent", "points_reward": 40},
                ],
            },
        }
