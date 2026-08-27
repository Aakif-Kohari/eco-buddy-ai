"""
Community Eco Challenge Hub — Service Layer
=============================================
Business logic for challenge creation, participation, progress tracking,
team management, streak computation, and analytics.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from src.community.community_challenge_db import (
    init_challenge_db, create_challenge, get_all_challenges,
    get_challenge_by_id, deactivate_challenge, join_challenge,
    get_participants, is_participant, log_progress, get_user_progress,
    get_progress_logs, get_team_leaderboard, get_user_leaderboard,
    get_activity_feed, get_challenge_stats,
)

# ── Challenge Lifecycle ────────────────────────────────────────────────────

def list_active_challenges(category: Optional[str] = None, difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return active challenges with optional filters."""
    challenges = get_all_challenges(active_only=True)
    if category:
        challenges = [c for c in challenges if c["category"] == category]
    if difficulty:
        challenges = [c for c in challenges if c["difficulty"] == difficulty]
    return challenges


def get_challenge_overview(challenge_id: int) -> Optional[Dict[str, Any]]:
    """Get a challenge with computed stats and participant count."""
    challenge = get_challenge_by_id(challenge_id)
    if not challenge:
        return None
    stats = get_challenge_stats(challenge_id)
    challenge["stats"] = stats
    challenge["days_remaining"] = _days_remaining(challenge["end_date"])
    challenge["is_expired"] = challenge["days_remaining"] <= 0
    return challenge


def create_new_challenge(
    title: str, description: str, category: str = "general",
    challenge_type: str = "daily", target_value: float = 1.0,
    target_unit: str = "actions", xp_reward: int = 50,
    badge_icon: str = "🏆", difficulty: str = "medium",
    duration_days: int = 30, created_by: Optional[int] = None,
) -> Dict[str, Any]:
    """Validate inputs, create a challenge, and return the result."""
    if not title or len(title.strip()) < 3:
        return {"success": False, "error": "Title must be at least 3 characters"}
    if target_value <= 0:
        return {"success": False, "error": "Target value must be positive"}
    if difficulty not in ("easy", "medium", "hard"):
        return {"success": False, "error": "Difficulty must be easy, medium, or hard"}

    now = datetime.utcnow()
    cid = create_challenge(
        title=title.strip(), description=description.strip(), category=category,
        challenge_type=challenge_type, target_value=target_value,
        target_unit=target_unit, xp_reward=xp_reward, badge_icon=badge_icon,
        difficulty=difficulty,
        start_date=now.strftime("%Y-%m-%d"),
        end_date=(now + timedelta(days=duration_days)).strftime("%Y-%m-%d"),
        created_by=created_by,
    )
    return {"success": True, "challenge_id": cid}


# ── Participation ──────────────────────────────────────────────────────────

def participate_in_challenge(challenge_id: int, user_id: int, team_name: Optional[str] = None) -> Dict[str, Any]:
    """Join a challenge, optionally creating/joining a team."""
    challenge = get_challenge_by_id(challenge_id)
    if not challenge:
        return {"success": False, "error": "Challenge not found"}
    if not challenge["is_active"]:
        return {"success": False, "error": "Challenge is no longer active"}
    if _days_remaining(challenge["end_date"]) <= 0:
        return {"success": False, "error": "Challenge has expired"}
    if is_participant(challenge_id, user_id):
        return {"success": False, "error": "Already participating"}

    ok = join_challenge(challenge_id, user_id, team_name)
    if ok:
        return {"success": True, "message": f"Joined '{challenge['title']}' successfully!"}
    return {"success": False, "error": "Failed to join (maybe the challenge is full)"}


def submit_progress(challenge_id: int, user_id: int, value: float = 1.0,
                     note: str = "") -> Dict[str, Any]:
    """Log progress toward a challenge."""
    if not is_participant(challenge_id, user_id):
        return {"success": False, "error": "You must join the challenge first"}
    challenge = get_challenge_by_id(challenge_id)
    if not challenge:
        return {"success": False, "error": "Challenge not found"}
    if _days_remaining(challenge["end_date"]) <= 0:
        return {"success": False, "error": "Challenge has ended"}

    log_progress(challenge_id, user_id, value, challenge["target_unit"], note)
    progress = get_user_progress(challenge_id, user_id)
    return {
        "success": True,
        "message": f"Logged {value} {challenge['target_unit']}!",
        "progress": progress,
    }


# ── User Dashboard ────────────────────────────────────────────────────────

def get_user_challenge_dashboard(user_id: int) -> Dict[str, Any]:
    """Build a summary dashboard for a user's challenge activity."""
    challenges = get_all_challenges(active_only=True)
    joined = []
    available = []
    completed = []

    for ch in challenges:
        progress = get_user_progress(ch["id"], user_id)
        if progress:
            entry = {**ch, "my_progress": progress}
            if progress.get("is_completed"):
                completed.append(entry)
            else:
                joined.append(entry)
        else:
            available.append(ch)

    total_xp = sum(c.get("xp_reward", 0) for c in completed)
    total_actions = sum(c.get("my_progress", {}).get("current_progress", 0) for c in joined + completed)

    return {
        "active_challenges": joined,
        "completed_challenges": completed,
        "available_challenges": available,
        "total_xp_earned": total_xp,
        "total_actions_logged": total_actions,
        "challenges_completed": len(completed),
        "challenges_active": len(joined),
    }


def get_user_streak(user_id: int) -> Dict[str, Any]:
    """Compute the user's current and longest streak across all challenges."""
    from src.community.community_challenge_db import _get_conn
    conn = _get_conn()
    rows = conn.execute(
        """SELECT DISTINCT log_date FROM challenge_progress_log
           WHERE user_id=? ORDER BY log_date DESC""",
        (user_id,),
    ).fetchall()
    conn.close()

    if not rows:
        return {"current_streak": 0, "longest_streak": 0, "total_days_active": 0}

    dates = [datetime.strptime(r["log_date"], "%Y-%m-%d").date() for r in rows]
    total_days = len(dates)
    unique_dates = sorted(set(dates), reverse=True)

    # Current streak
    current = 0
    today = datetime.utcnow().date()
    check = today
    for d in unique_dates:
        if d == check:
            current += 1
            check -= timedelta(days=1)
        elif d == check - timedelta(days=1):
            # Allow gap from today
            check = d
            current += 1
            check -= timedelta(days=1)
        else:
            break

    # Longest streak
    longest = 0
    streak = 1
    sorted_dates = sorted(set(dates))
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            streak += 1
        else:
            longest = max(longest, streak)
            streak = 1
    longest = max(longest, streak)

    return {
        "current_streak": current,
        "longest_streak": longest,
        "total_days_active": total_days,
    }


# ── Analytics ─────────────────────────────────────────────────────────────

def get_category_distribution(user_id: int) -> Dict[str, int]:
    """Get breakdown of challenge categories a user has participated in."""
    from src.community.community_challenge_db import _get_conn
    conn = _get_conn()
    rows = conn.execute(
        """SELECT ec.category, COUNT(DISTINCT cp.challenge_id) as cnt
           FROM challenge_participants cp
           JOIN eco_challenges ec ON cp.challenge_id = ec.id
           WHERE cp.user_id=?
           GROUP BY ec.category""",
        (user_id,),
    ).fetchall()
    conn.close()
    return {r["category"]: r["cnt"] for r in rows}


def get_difficulty_distribution(user_id: int) -> Dict[str, int]:
    """Get breakdown of challenge difficulties a user has participated in."""
    from src.community.community_challenge_db import _get_conn
    conn = _get_conn()
    rows = conn.execute(
        """SELECT ec.difficulty, COUNT(DISTINCT cp.challenge_id) as cnt
           FROM challenge_participants cp
           JOIN eco_challenges ec ON cp.challenge_id = ec.id
           WHERE cp.user_id=?
           GROUP BY ec.difficulty""",
        (user_id,),
    ).fetchall()
    conn.close()
    return {r["difficulty"]: r["cnt"] for r in rows}


def get_weekly_progress_data(challenge_id: int, days: int = 14) -> List[Dict[str, Any]]:
    """Get daily aggregated progress for a challenge over the last N days."""
    from src.community.community_challenge_db import _get_conn
    conn = _get_conn()
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT log_date, SUM(value_logged) as total_value, COUNT(DISTINCT user_id) as active_users
           FROM challenge_progress_log
           WHERE challenge_id=? AND log_date >= ?
           GROUP BY log_date ORDER BY log_date""",
        (challenge_id, start),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Helpers ───────────────────────────────────────────────────────────────

def _days_remaining(end_date: str) -> int:
    try:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        return max(0, (end - datetime.utcnow().date()).days)
    except (ValueError, TypeError):
        return 0


def get_available_categories() -> List[str]:
    """Return all valid challenge categories."""
    return ["transport", "energy", "diet", "waste", "water", "nature",
            "health", "community", "general"]


def get_difficulty_meta() -> Dict[str, Dict[str, Any]]:
    """Return metadata for difficulty levels."""
    return {
        "easy": {"label": "Easy", "color": "#22c55e", "icon": "🟢", "multiplier": 1.0},
        "medium": {"label": "Medium", "color": "#eab308", "icon": "🟡", "multiplier": 1.5},
        "hard": {"label": "Hard", "color": "#ef4444", "icon": "🔴", "multiplier": 2.0},
    }
