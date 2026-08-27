"""
Pledge Leaderboard & Accountability Groups
==========================================
Community accountability groups for green pledges: users form groups,
track collective pledge completions, earn group XP, and compete on
a weekly leaderboard.

Dependencies: green_pledge_tracker (for pledge templates / stats),
              database_connection (for SQLite context manager).
"""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from database_connection import database_connection
from green_pledge_tracker import (
    DB_NAME,
    PLEDGE_CATALOG,
    PLEDGE_CATEGORIES,
    PledgeTemplate,
    current_week_start,
    current_week_end,
    get_template_by_id,
    get_user_all_pledges,
    get_user_pledge_stats,
    weeks_between,
)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

MAX_GROUP_MEMBERS = 50
MIN_GROUP_MEMBERS = 2
INVITE_CODE_LENGTH = 8
GROUP_NAME_MAX_LENGTH = 60
GROUP_DESC_MAX_LENGTH = 500

GROUP_PRIVACY_PUBLIC = "public"
GROUP_PRIVACY_PRIVATE = "private"


class GroupRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class ChallengeStatus(str, Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


# XP bonus multipliers for group activities
GROUP_COMPLETION_BONUS = 1.25  # 25% XP bonus when completing a pledge inside a group
GROUP_STREAK_BONUS_PER_WEEK = 5  # extra XP per consecutive group streak week
GROUP_CHALLENGE_XP_BASE = 150  # base XP for completing a group challenge


# ──────────────────────────────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────────────────────────────

@dataclass
class AccountabilityGroup:
    group_id: str
    name: str
    description: str
    owner_id: int
    privacy: str  # public | private
    invite_code: str
    max_members: int
    member_count: int = 0
    total_xp: int = 0
    total_co2_saved_kg: float = 0.0
    total_pledges_completed: int = 0
    current_streak_weeks: int = 0
    best_streak_weeks: int = 0
    created_at: str = ""
    tags: list[str] = field(default_factory=list)
    level: str = "Seedling"
    badges: list[str] = field(default_factory=list)


@dataclass
class GroupMember:
    user_id: int
    group_id: str
    role: str  # owner | admin | member
    joined_at: str = ""
    personal_xp_in_group: int = 0
    personal_co2_in_group: float = 0.0
    personal_pledges_completed: int = 0
    display_name: str = ""


@dataclass
class GroupChallenge:
    challenge_id: str
    group_id: str
    title: str
    description: str
    target_type: str  # pledges_completed | co2_saved | streak_weeks | checkins
    target_value: float
    current_value: float
    status: str  # upcoming | active | completed | failed
    xp_reward: int
    eco_points_reward: int
    start_week: str
    end_week: str
    created_at: str = ""
    completed_at: str = ""


@dataclass
class LeaderboardEntry:
    rank: int
    group_id: str
    group_name: str
    score: float  # composite score
    total_xp: int
    total_co2_saved_kg: float
    pledges_completed: int
    member_count: int
    streak_weeks: int
    level: str
    badges: list[str] = field(default_factory=list)
    weekly_delta: float = 0.0  # change from previous week


@dataclass
class WeeklySnapshot:
    snapshot_id: str
    group_id: str
    week_start: str
    xp_earned: int
    co2_saved_kg: float
    pledges_completed: int
    checkins: int
    rank: int = 0
    snapshot_at: str = ""


@dataclass
class GroupAnnouncement:
    announcement_id: str
    group_id: str
    author_id: int
    title: str
    body: str
    priority: str  # normal | important | urgent
    created_at: str = ""
    author_name: str = ""


# ──────────────────────────────────────────────────────────────────────
# Database helpers
# ──────────────────────────────────────────────────────────────────────

def init_leaderboard_tables() -> None:
    """Create all leaderboard / group tables if they don't exist."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pledge_groups (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                description     TEXT DEFAULT '',
                owner_id        INTEGER NOT NULL,
                privacy         TEXT DEFAULT 'public',
                invite_code     TEXT UNIQUE NOT NULL,
                max_members     INTEGER DEFAULT 50,
                total_xp        INTEGER DEFAULT 0,
                total_co2_kg    REAL DEFAULT 0.0,
                total_completed INTEGER DEFAULT 0,
                streak_weeks    INTEGER DEFAULT 0,
                best_streak     INTEGER DEFAULT 0,
                tags            TEXT DEFAULT '[]',
                created_at      TEXT DEFAULT ''
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                user_id             INTEGER NOT NULL,
                group_id            TEXT NOT NULL,
                role                TEXT DEFAULT 'member',
                joined_at           TEXT DEFAULT '',
                personal_xp         INTEGER DEFAULT 0,
                personal_co2_kg     REAL DEFAULT 0.0,
                personal_completed  INTEGER DEFAULT 0,
                display_name        TEXT DEFAULT '',
                PRIMARY KEY (user_id, group_id),
                FOREIGN KEY (group_id) REFERENCES pledge_groups(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_challenges (
                id              TEXT PRIMARY KEY,
                group_id        TEXT NOT NULL,
                title           TEXT NOT NULL,
                description     TEXT DEFAULT '',
                target_type     TEXT NOT NULL,
                target_value    REAL NOT NULL,
                current_value   REAL DEFAULT 0.0,
                status          TEXT DEFAULT 'upcoming',
                xp_reward       INTEGER DEFAULT 100,
                eco_pts_reward  INTEGER DEFAULT 20,
                start_week      TEXT NOT NULL,
                end_week        TEXT NOT NULL,
                created_at      TEXT DEFAULT '',
                completed_at    TEXT DEFAULT '',
                FOREIGN KEY (group_id) REFERENCES pledge_groups(id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_snapshots (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id            TEXT NOT NULL,
                week_start          TEXT NOT NULL,
                xp_earned           INTEGER DEFAULT 0,
                co2_saved_kg        REAL DEFAULT 0.0,
                pledges_completed   INTEGER DEFAULT 0,
                checkins            INTEGER DEFAULT 0,
                rank                INTEGER DEFAULT 0,
                snapshot_at         TEXT DEFAULT '',
                FOREIGN KEY (group_id) REFERENCES pledge_groups(id),
                UNIQUE(group_id, week_start)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_announcements (
                id          TEXT PRIMARY KEY,
                group_id    TEXT NOT NULL,
                author_id   INTEGER NOT NULL,
                title       TEXT NOT NULL,
                body        TEXT DEFAULT '',
                priority    TEXT DEFAULT 'normal',
                created_at  TEXT DEFAULT '',
                FOREIGN KEY (group_id) REFERENCES pledge_groups(id)
            )
        """)
        conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Invite code generation
# ──────────────────────────────────────────────────────────────────────

def _generate_invite_code(group_name: str, owner_id: int) -> str:
    """Generate a short, URL-friendly invite code."""
    raw = f"{group_name}:{owner_id}:{uuid.uuid4().hex}"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return digest[:INVITE_CODE_LENGTH].upper()


# ──────────────────────────────────────────────────────────────────────
# Group CRUD
# ──────────────────────────────────────────────────────────────────────

def create_group(
    name: str,
    owner_id: int,
    description: str = "",
    privacy: str = GROUP_PRIVACY_PUBLIC,
    max_members: int = MAX_GROUP_MEMBERS,
    tags: list[str] | None = None,
) -> AccountabilityGroup | None:
    """Create a new accountability group. Returns None if name is taken."""
    if len(name) > GROUP_NAME_MAX_LENGTH:
        name = name[:GROUP_NAME_MAX_LENGTH]
    if len(description) > GROUP_DESC_MAX_LENGTH:
        description = description[:GROUP_DESC_MAX_LENGTH]

    max_members = max(MIN_GROUP_MEMBERS, min(max_members, MAX_GROUP_MEMBERS))
    tags = tags or []
    invite_code = _generate_invite_code(name, owner_id)
    group_id = str(uuid.uuid4())[:12]
    now = datetime.now().isoformat(timespec="seconds")

    try:
        with database_connection(DB_NAME) as conn:
            cur = conn.cursor()
            # Check duplicate name
            cur.execute("SELECT id FROM pledge_groups WHERE name = ?", (name,))
            if cur.fetchone():
                return None

            cur.execute("""
                INSERT INTO pledge_groups
                    (id, name, description, owner_id, privacy, invite_code,
                     max_members, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                group_id, name, description, owner_id, privacy,
                invite_code, max_members, json.dumps(tags), now,
            ))

            # Owner joins automatically
            cur.execute("""
                INSERT INTO group_members
                    (user_id, group_id, role, joined_at, display_name)
                VALUES (?, ?, 'owner', ?, ?)
            """, (owner_id, group_id, now, f"User#{owner_id}"))

            conn.commit()
    except sqlite3.IntegrityError:
        return None

    return _fetch_group(group_id)


def join_group(user_id: int, invite_code: str) -> AccountabilityGroup | None:
    """Join a group by invite code. Returns updated group or None."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, max_members FROM pledge_groups WHERE invite_code = ?", (invite_code,))
        row = cur.fetchone()
        if not row:
            return None
        group_id, max_members = row

        # Check membership count
        cur.execute("SELECT COUNT(*) FROM group_members WHERE group_id = ?", (group_id,))
        count = cur.fetchone()[0]
        if count >= max_members:
            return None

        # Check already member
        cur.execute(
            "SELECT role FROM group_members WHERE user_id = ? AND group_id = ?",
            (user_id, group_id),
        )
        if cur.fetchone():
            return None  # already a member

        now = datetime.now().isoformat(timespec="seconds")
        cur.execute("""
            INSERT INTO group_members (user_id, group_id, role, joined_at, display_name)
            VALUES (?, ?, 'member', ?, ?)
        """, (user_id, group_id, now, f"User#{user_id}"))
        conn.commit()

    return _fetch_group(group_id)


def leave_group(user_id: int, group_id: str) -> bool:
    """Remove a member from a group. Owners cannot leave — must transfer first."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT role FROM group_members WHERE user_id = ? AND group_id = ?",
            (user_id, group_id),
        )
        row = cur.fetchone()
        if not row:
            return False
        if row[0] == GroupRole.OWNER:
            return False  # owner must transfer ownership first

        cur.execute(
            "DELETE FROM group_members WHERE user_id = ? AND group_id = ?",
            (user_id, group_id),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_group(user_id: int, group_id: str) -> bool:
    """Delete a group. Only the owner can do this."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT owner_id FROM pledge_groups WHERE id = ?", (group_id,)
        )
        row = cur.fetchone()
        if not row or row[0] != user_id:
            return False

        cur.execute("DELETE FROM group_announcements WHERE group_id = ?", (group_id,))
        cur.execute("DELETE FROM group_challenges WHERE group_id = ?", (group_id,))
        cur.execute("DELETE FROM weekly_snapshots WHERE group_id = ?", (group_id,))
        cur.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))
        cur.execute("DELETE FROM pledge_groups WHERE id = ?", (group_id,))
        conn.commit()
        return True


def transfer_ownership(owner_id: int, group_id: str, new_owner_id: int) -> bool:
    """Transfer group ownership to another member."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT owner_id FROM pledge_groups WHERE id = ?", (group_id,)
        )
        row = cur.fetchone()
        if not row or row[0] != owner_id:
            return False

        # Verify new owner is a member
        cur.execute(
            "SELECT role FROM group_members WHERE user_id = ? AND group_id = ?",
            (new_owner_id, group_id),
        )
        if not cur.fetchone():
            return False

        cur.execute("UPDATE pledge_groups SET owner_id = ? WHERE id = ?", (new_owner_id, group_id))
        cur.execute(
            "UPDATE group_members SET role = 'owner' WHERE user_id = ? AND group_id = ?",
            (new_owner_id, group_id),
        )
        cur.execute(
            "UPDATE group_members SET role = 'admin' WHERE user_id = ? AND group_id = ?",
            (owner_id, group_id),
        )
        conn.commit()
        return True


def promote_member(admin_id: int, group_id: str, target_user_id: int) -> bool:
    """Promote a member to admin. Requires owner or admin privileges."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT role FROM group_members WHERE user_id = ? AND group_id = ?",
            (admin_id, group_id),
        )
        row = cur.fetchone()
        if not row or row[0] not in (GroupRole.OWNER, GroupRole.ADMIN):
            return False

        cur.execute(
            "UPDATE group_members SET role = 'admin' WHERE user_id = ? AND group_id = ? AND role = 'member'",
            (target_user_id, group_id),
        )
        conn.commit()
        return cur.rowcount > 0


def get_group_by_invite(invite_code: str) -> AccountabilityGroup | None:
    """Look up a group by invite code."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM pledge_groups WHERE invite_code = ?", (invite_code,))
        row = cur.fetchone()
        if row:
            return _fetch_group(row[0])
    return None


def get_user_groups(user_id: int) -> list[AccountabilityGroup]:
    """Return all groups a user belongs to."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT g.id FROM pledge_groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
            ORDER BY gm.joined_at DESC
        """, (user_id,))
        group_ids = [r[0] for r in cur.fetchall()]

    groups = []
    for gid in group_ids:
        g = _fetch_group(gid)
        if g:
            groups.append(g)
    return groups


def get_public_groups(
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "members",
) -> list[AccountabilityGroup]:
    """Return paginated public groups."""
    order_map = {
        "members": "g.total_completed DESC",
        "xp": "g.total_xp DESC",
        "co2": "g.total_co2_kg DESC",
        "newest": "g.created_at DESC",
    }
    order = order_map.get(sort_by, "g.total_completed DESC")

    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(f"""
            SELECT g.id FROM pledge_groups g
            WHERE g.privacy = 'public'
            ORDER BY {order}
            LIMIT ? OFFSET ?
        """, (limit, offset))
        group_ids = [r[0] for r in cur.fetchall()]

    groups = []
    for gid in group_ids:
        g = _fetch_group(gid)
        if g:
            groups.append(g)
    return groups


def get_group_members(group_id: str) -> list[GroupMember]:
    """Return all members of a group."""
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT gm.*, u.username AS display_name
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = ?
            ORDER BY
                CASE gm.role
                    WHEN 'owner' THEN 0
                    WHEN 'admin' THEN 1
                    ELSE 2
                END,
                gm.personal_xp DESC
        """, (group_id,))
        return [dict(r) for r in cur.fetchall()]


# ──────────────────────────────────────────────────────────────────────
# Leaderboard
# ──────────────────────────────────────────────────────────────────────

def _compute_group_score(group: AccountabilityGroup) -> float:
    """Composite score: weighted blend of XP, CO2, completions, streak, size."""
    xp_component = group.total_xp * 1.0
    co2_component = group.total_co2_saved_kg * 2.0
    completion_component = group.total_pledges_completed * 15.0
    streak_component = group.current_streak_weeks * 50.0
    size_factor = math.log2(max(group.member_count, 1)) * 20.0

    return round(
        xp_component + co2_component + completion_component
        + streak_component + size_factor,
        2,
    )


def get_leaderboard(limit: int = 50) -> list[LeaderboardEntry]:
    """Compute the current community-wide group leaderboard."""
    groups = _all_groups()

    scored: list[tuple[float, AccountabilityGroup]] = []
    for g in groups:
        score = _compute_group_score(g)
        scored.append((score, g))

    scored.sort(key=lambda x: x[0], reverse=True)

    entries: list[LeaderboardEntry] = []
    for rank, (score, g) in enumerate(scored[:limit], 1):
        entries.append(LeaderboardEntry(
            rank=rank,
            group_id=g.group_id,
            group_name=g.name,
            score=score,
            total_xp=g.total_xp,
            total_co2_saved_kg=g.total_co2_saved_kg,
            pledges_completed=g.total_pledges_completed,
            member_count=g.member_count,
            streak_weeks=g.current_streak_weeks,
            level=g.level,
            badges=g.badges,
        ))

    return entries


def get_group_leaderboard_position(group_id: str) -> LeaderboardEntry | None:
    """Find a specific group's position on the leaderboard."""
    entries = get_leaderboard(limit=500)
    for e in entries:
        if e.group_id == group_id:
            return e
    return None


# ──────────────────────────────────────────────────────────────────────
# Group challenges
# ──────────────────────────────────────────────────────────────────────

def create_group_challenge(
    creator_id: int,
    group_id: str,
    title: str,
    description: str,
    target_type: str,
    target_value: float,
    duration_weeks: int = 1,
    xp_reward: int = GROUP_CHALLENGE_XP_BASE,
    eco_points_reward: int = 30,
) -> GroupChallenge | None:
    """Create a new group challenge. Creator must be owner or admin."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT role FROM group_members WHERE user_id = ? AND group_id = ?",
            (creator_id, group_id),
        )
        row = cur.fetchone()
        if not row or row[0] not in (GroupRole.OWNER, GroupRole.ADMIN):
            return None

        challenge_id = str(uuid.uuid4())[:12]
        now = datetime.now().isoformat(timespec="seconds")
        ws = current_week_start()
        end = (datetime.strptime(ws, "%Y-%m-%d") + timedelta(weeks=duration_weeks)).strftime("%Y-%m-%d")

        cur.execute("""
            INSERT INTO group_challenges
                (id, group_id, title, description, target_type, target_value,
                 status, xp_reward, eco_pts_reward, start_week, end_week, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?, ?)
        """, (
            challenge_id, group_id, title, description, target_type, target_value,
            xp_reward, eco_points_reward, ws, end, now,
        ))
        conn.commit()

    return _fetch_challenge(challenge_id)


def get_group_challenges(
    group_id: str,
    status: str | None = None,
) -> list[GroupChallenge]:
    """Return challenges for a group, optionally filtered by status."""
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if status:
            cur.execute(
                "SELECT * FROM group_challenges WHERE group_id = ? AND status = ? ORDER BY created_at DESC",
                (group_id, status),
            )
        else:
            cur.execute(
                "SELECT * FROM group_challenges WHERE group_id = ? ORDER BY created_at DESC",
                (group_id,),
            )
        return [_dict_to_challenge(dict(r)) for r in cur.fetchall()]


def update_challenge_progress(challenge_id: str, increment: float) -> GroupChallenge | None:
    """Increment a challenge's current value and check for completion."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM group_challenges WHERE id = ?", (challenge_id,))
        row = cur.fetchone()
        if not row:
            return None

        columns = [d[0] for d in cur.description]
        data = dict(zip(columns, row))
        if data["status"] != "active":
            return _fetch_challenge(challenge_id)

        new_value = data["current_value"] + increment
        if new_value >= data["target_value"]:
            now = datetime.now().isoformat(timespec="seconds")
            cur.execute("""
                UPDATE group_challenges
                SET current_value = ?, status = 'completed', completed_at = ?
                WHERE id = ?
            """, (data["target_value"], now, challenge_id))

            # Award XP and eco points to group
            cur.execute("""
                UPDATE pledge_groups
                SET total_xp = total_xp + ?, total_completed = total_completed + 1
                WHERE id = ?
            """, (data["xp_reward"], data["group_id"]))
        else:
            cur.execute(
                "UPDATE group_challenges SET current_value = ? WHERE id = ?",
                (new_value, challenge_id),
            )

        conn.commit()
    return _fetch_challenge(challenge_id)


# ──────────────────────────────────────────────────────────────────────
# Announcements
# ──────────────────────────────────────────────────────────────────────

def post_announcement(
    author_id: int,
    group_id: str,
    title: str,
    body: str,
    priority: str = "normal",
) -> GroupAnnouncement | None:
    """Post an announcement to a group. Must be owner or admin."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT role FROM group_members WHERE user_id = ? AND group_id = ?",
            (author_id, group_id),
        )
        row = cur.fetchone()
        if not row or row[0] not in (GroupRole.OWNER, GroupRole.ADMIN):
            return None

        announcement_id = str(uuid.uuid4())[:12]
        now = datetime.now().isoformat(timespec="seconds")

        cur.execute("""
            INSERT INTO group_announcements (id, group_id, author_id, title, body, priority, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (announcement_id, group_id, author_id, title, body, priority, now))
        conn.commit()

    return GroupAnnouncement(
        announcement_id=announcement_id,
        group_id=group_id,
        author_id=author_id,
        title=title,
        body=body,
        priority=priority,
        created_at=now,
    )


def get_group_announcements(group_id: str, limit: int = 20) -> list[GroupAnnouncement]:
    """Return recent announcements for a group."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ga.*, COALESCE(u.username, 'Unknown') AS author_name
            FROM group_announcements ga
            LEFT JOIN users u ON ga.author_id = u.id
            WHERE ga.group_id = ?
            ORDER BY ga.created_at DESC
            LIMIT ?
        """, (group_id, limit))
        columns = [d[0] for d in cur.description]
        return [
            GroupAnnouncement(**dict(zip(columns, r)))
            for r in cur.fetchall()
        ]


# ──────────────────────────────────────────────────────────────────────
# Weekly snapshots & analytics
# ──────────────────────────────────────────────────────────────────────

def take_weekly_snapshot(group_id: str) -> WeeklySnapshot | None:
    """Capture a weekly snapshot of a group's activity for trend tracking."""
    ws = current_week_start()
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        # Get this week's aggregate from group members
        cur.execute("""
            SELECT
                COALESCE(SUM(personal_xp), 0) AS xp,
                COALESCE(SUM(personal_co2_kg), 0) AS co2,
                COALESCE(SUM(personal_completed), 0) AS completed
            FROM group_members
            WHERE group_id = ?
        """, (group_id,))
        row = cur.fetchone()
        xp_earned = row[0] if row else 0
        co2 = row[1] if row else 0
        completed = row[2] if row else 0

        now = datetime.now().isoformat(timespec="seconds")
        cur.execute("""
            INSERT INTO weekly_snapshots (group_id, week_start, xp_earned, co2_saved_kg, pledges_completed, snapshot_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(group_id, week_start) DO UPDATE SET
                xp_earned = excluded.xp_earned,
                co2_saved_kg = excluded.co2_saved_kg,
                pledges_completed = excluded.pledges_completed,
                snapshot_at = excluded.snapshot_at
        """, (group_id, ws, xp_earned, co2, completed, now))
        conn.commit()

    return WeeklySnapshot(
        snapshot_id="",
        group_id=group_id,
        week_start=ws,
        xp_earned=xp_earned,
        co2_saved_kg=co2,
        pledges_completed=completed,
        checkins=0,
        snapshot_at=now,
    )


def get_group_weekly_trend(group_id: str, weeks: int = 12) -> list[dict[str, Any]]:
    """Return weekly trend data for a group over the last N weeks."""
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM weekly_snapshots
            WHERE group_id = ?
            ORDER BY week_start DESC
            LIMIT ?
        """, (group_id, weeks))
        rows = [dict(r) for r in cur.fetchall()]

    return list(reversed(rows))


def get_group_members_leaderboard(group_id: str) -> list[dict[str, Any]]:
    """Rank individual members within a group by their contributions."""
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT gm.user_id, gm.personal_xp, gm.personal_co2_kg,
                   gm.personal_completed, gm.role, gm.joined_at,
                   COALESCE(u.username, 'User#' || gm.user_id) AS display_name
            FROM group_members gm
            LEFT JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = ?
            ORDER BY gm.personal_xp DESC, gm.personal_co2_kg DESC
        """, (group_id,))

        results = []
        for rank, row in enumerate(cur.fetchall(), 1):
            results.append({
                "rank": rank,
                "user_id": row[0],
                "display_name": row[6],
                "role": row[4],
                "personal_xp": row[1],
                "personal_co2_kg": row[2],
                "personal_completed": row[3],
                "joined_at": row[5],
            })
    return results


# ──────────────────────────────────────────────────────────────────────
# Group level & badges
# ──────────────────────────────────────────────────────────────────────

GROUP_LEVEL_THRESHOLDS: list[tuple[str, int]] = [
    ("Seedling", 0),
    ("Sprout", 100),
    ("Sapling", 500),
    ("Tree", 1500),
    ("Forest", 4000),
    ("Biome", 10000),
]


def _compute_group_level(group: AccountabilityGroup) -> str:
    level_name = "Seedling"
    for name, threshold in GROUP_LEVEL_THRESHOLDS:
        if group.total_xp >= threshold:
            level_name = name
        else:
            break
    return level_name


def _compute_group_badges(group: AccountabilityGroup) -> list[str]:
    badges: list[str] = []
    if group.total_pledges_completed >= 1:
        badges.append("🌱 First Group Pledge")
    if group.total_pledges_completed >= 10:
        badges.append("🔥 Pledge Crew")
    if group.total_pledges_completed >= 25:
        badges.append("💪 Green Squad")
    if group.total_pledges_completed >= 50:
        badges.append("🏆 Eco Battalion")
    if group.total_pledges_completed >= 100:
        badges.append("🌍 Climate Force")
    if group.member_count >= 5:
        badges.append("👥 Growing Team")
    if group.member_count >= 10:
        badges.append("🏠 Green Household")
    if group.member_count >= 25:
        badges.append("🏙️ Eco Community")
    if group.current_streak_weeks >= 3:
        badges.append("⚡ 3-Week Streak")
    if group.current_streak_weeks >= 6:
        badges.append("🌟 6-Week Streak")
    if group.current_streak_weeks >= 12:
        badges.append("👑 Year-Round Warriors")
    if group.total_co2_saved_kg >= 50:
        badges.append("🌍 50 kg CO₂ Group Save")
    if group.total_co2_saved_kg >= 200:
        badges.append("🌎 200 kg CO₂ Group Save")
    if group.total_co2_saved_kg >= 500:
        badges.append("🌐 500 kg CO₂ Group Save")
    return badges


# ──────────────────────────────────────────────────────────────────────
# Social share cards
# ──────────────────────────────────────────────────────────────────────

def generate_group_share_card(group: AccountabilityGroup) -> dict[str, Any]:
    """Generate a shareable card with group stats for social media."""
    return {
        "title": group.name,
        "subtitle": "EcoBuddy Accountability Group",
        "stats": {
            "members": group.member_count,
            "pledges_completed": group.total_pledges_completed,
            "co2_saved_kg": round(group.total_co2_saved_kg, 1),
            "total_xp": group.total_xp,
            "streak_weeks": group.current_streak_weeks,
            "level": group.level,
        },
        "badges": group.badges[:5],
        "invite_code": group.invite_code,
        "tagline": _generate_tagline(group),
    }


def generate_member_share_card(
    member: GroupMember,
    group: AccountabilityGroup,
) -> dict[str, Any]:
    """Generate a shareable card for a single member's group contribution."""
    return {
        "title": f"{member.display_name}",
        "subtitle": f"Member of {group.name}",
        "stats": {
            "personal_xp": member.personal_xp_in_group,
            "personal_co2_kg": round(member.personal_co2_in_group, 1),
            "personal_pledges": member.personal_pledges_completed,
            "role": member.role,
        },
        "group_stats": {
            "group_level": group.level,
            "group_co2_saved": round(group.total_co2_saved_kg, 1),
        },
    }


def _generate_tagline(group: AccountabilityGroup) -> str:
    co2 = group.total_co2_saved_kg
    if co2 >= 500:
        return f"🌿 Together we've saved {co2:.0f} kg CO₂ — real impact!"
    elif co2 >= 100:
        return f"🌱 {group.member_count} eco-warriors saving {co2:.0f} kg CO₂ together!"
    elif co2 >= 10:
        return f"🍃 {group.member_count} members making a difference — {co2:.1f} kg CO₂ saved!"
    elif group.member_count >= 5:
        return f"🤝 {group.member_count} strong and growing!"
    else:
        return "🌍 Building a greener future, one pledge at a time."


# ──────────────────────────────────────────────────────────────────────
# Collab challenge presets
# ──────────────────────────────────────────────────────────────────────

COLLAB_CHALLENGE_PRESETS: list[dict[str, Any]] = [
    {
        "title": "🌍 Group Carbon Crunch",
        "description": "Collectively complete 10 pledges as a group this month.",
        "target_type": "pledges_completed",
        "target_value": 10,
        "duration_weeks": 4,
        "xp_reward": 200,
        "eco_points_reward": 40,
    },
    {
        "title": "💪 Streak Squad",
        "description": "Maintain a group check-in streak for 4 consecutive weeks.",
        "target_type": "streak_weeks",
        "target_value": 4,
        "duration_weeks": 4,
        "xp_reward": 250,
        "eco_points_reward": 50,
    },
    {
        "title": "🌱 CO₂ Crusaders",
        "description": "Save a combined 50 kg of CO₂ through pledges.",
        "target_type": "co2_saved",
        "target_value": 50.0,
        "duration_weeks": 6,
        "xp_reward": 300,
        "eco_points_reward": 60,
    },
    {
        "title": "⚡ Daily Check-in Blitz",
        "description": "Record 30 group check-ins across all members this week.",
        "target_type": "checkins",
        "target_value": 30,
        "duration_weeks": 1,
        "xp_reward": 150,
        "eco_points_reward": 30,
    },
    {
        "title": "🏆 Mega Month Challenge",
        "description": "Complete 25 pledges and save 100 kg CO₂ in a month.",
        "target_type": "pledges_completed",
        "target_value": 25,
        "duration_weeks": 4,
        "xp_reward": 500,
        "eco_points_reward": 100,
    },
]


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────

def _fetch_group(group_id: str) -> AccountabilityGroup | None:
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM pledge_groups WHERE id = ?", (group_id,))
        row = cur.fetchone()
        if not row:
            return None
        data = dict(row)

        # Member count
        cur.execute("SELECT COUNT(*) FROM group_members WHERE group_id = ?", (group_id,))
        member_count = cur.fetchone()[0]

    tags = json.loads(data.get("tags", "[]")) if isinstance(data.get("tags"), str) else data.get("tags", [])

    group = AccountabilityGroup(
        group_id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        owner_id=data["owner_id"],
        privacy=data.get("privacy", "public"),
        invite_code=data.get("invite_code", ""),
        max_members=data.get("max_members", MAX_GROUP_MEMBERS),
        member_count=member_count,
        total_xp=data.get("total_xp", 0),
        total_co2_saved_kg=data.get("total_co2_kg", 0.0),
        total_pledges_completed=data.get("total_completed", 0),
        current_streak_weeks=data.get("streak_weeks", 0),
        best_streak_weeks=data.get("best_streak", 0),
        created_at=data.get("created_at", ""),
        tags=tags,
    )
    group.level = _compute_group_score_label(group)
    group.badges = _compute_group_badges(group)
    return group


def _compute_group_score_label(group: AccountabilityGroup) -> str:
    level_name = "Seedling"
    for name, threshold in GROUP_LEVEL_THRESHOLDS:
        if group.total_xp >= threshold:
            level_name = name
        else:
            break
    return level_name


def _all_groups() -> list[AccountabilityGroup]:
    with database_connection(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM pledge_groups")
        ids = [r[0] for r in cur.fetchall()]
    return [g for gid in ids if (g := _fetch_group(gid))]


def _fetch_challenge(challenge_id: str) -> GroupChallenge | None:
    with database_connection(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM group_challenges WHERE id = ?", (challenge_id,))
        row = cur.fetchone()
        if row:
            return _dict_to_challenge(dict(row))
    return None


def _dict_to_challenge(d: dict[str, Any]) -> GroupChallenge:
    return GroupChallenge(
        challenge_id=d["id"],
        group_id=d["group_id"],
        title=d["title"],
        description=d.get("description", ""),
        target_type=d["target_type"],
        target_value=d["target_value"],
        current_value=d.get("current_value", 0.0),
        status=d.get("status", "active"),
        xp_reward=d.get("xp_reward", 100),
        eco_points_reward=d.get("eco_pts_reward", 20),
        start_week=d["start_week"],
        end_week=d["end_week"],
        created_at=d.get("created_at", ""),
        completed_at=d.get("completed_at", ""),
    )


def group_to_dict(g: AccountabilityGroup) -> dict[str, Any]:
    """Serialise group to a plain dict for JSON export."""
    d = asdict(g)
    d["score"] = _compute_group_score(g)
    return d


def export_group_json(group_id: str) -> str:
    """Export a full group profile as JSON."""
    g = _fetch_group(group_id)
    if not g:
        return "{}"
    members = get_group_members(group_id)
    challenges = get_group_challenges(group_id)
    trend = get_group_weekly_trend(group_id)
    announcements = get_group_announcements(group_id)

    data = {
        "group": group_to_dict(g),
        "members": members,
        "challenges": [asdict(c) for c in challenges],
        "weekly_trend": trend,
        "announcements": [asdict(a) for a in announcements],
    }
    return json.dumps(data, indent=2, default=str)
