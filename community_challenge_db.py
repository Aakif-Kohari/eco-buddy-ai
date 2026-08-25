"""
Community Eco Challenge Hub — Database Layer
=============================================
Provides SQLite schema and CRUD operations for eco challenges, team
leaderboards, participant progress, and activity logging.
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "eco_buddy.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_challenge_db():
    """Create community challenge tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS eco_challenges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            description     TEXT NOT NULL,
            category        TEXT NOT NULL DEFAULT 'general',
            challenge_type  TEXT NOT NULL DEFAULT 'daily',
            target_value    REAL NOT NULL DEFAULT 1.0,
            target_unit     TEXT NOT NULL DEFAULT 'actions',
            xp_reward       INTEGER NOT NULL DEFAULT 50,
            badge_icon      TEXT NOT NULL DEFAULT '🏆',
            difficulty      TEXT NOT NULL DEFAULT 'medium',
            start_date      TEXT NOT NULL,
            end_date        TEXT NOT NULL,
            created_by      INTEGER,
            is_active       INTEGER NOT NULL DEFAULT 1,
            max_participants INTEGER DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS challenge_participants (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id    INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            team_name       TEXT DEFAULT NULL,
            joined_at       TEXT NOT NULL DEFAULT (datetime('now')),
            current_progress REAL NOT NULL DEFAULT 0.0,
            is_completed    INTEGER NOT NULL DEFAULT 0,
            completed_at    TEXT DEFAULT NULL,
            FOREIGN KEY (challenge_id) REFERENCES eco_challenges(id),
            UNIQUE(challenge_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS challenge_progress_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id    INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            log_date        TEXT NOT NULL,
            value_logged    REAL NOT NULL DEFAULT 1.0,
            unit            TEXT DEFAULT 'actions',
            note            TEXT DEFAULT '',
            verified        INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (challenge_id) REFERENCES eco_challenges(id)
        );

        CREATE TABLE IF NOT EXISTS challenge_teams (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id    INTEGER NOT NULL,
            team_name       TEXT NOT NULL,
            team_icon       TEXT NOT NULL DEFAULT '🌿',
            total_score     REAL NOT NULL DEFAULT 0.0,
            member_count    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (challenge_id) REFERENCES eco_challenges(id),
            UNIQUE(challenge_id, team_name)
        );

        CREATE TABLE IF NOT EXISTS challenge_activity_feed (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id    INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            activity_type   TEXT NOT NULL,
            payload         TEXT DEFAULT '{}',
            created_at      TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (challenge_id) REFERENCES eco_challenges(id)
        );

        CREATE INDEX IF NOT EXISTS idx_cp_challenge ON challenge_participants(challenge_id);
        CREATE INDEX IF NOT EXISTS idx_cp_user ON challenge_participants(user_id);
        CREATE INDEX IF NOT EXISTS idx_cpl_challenge ON challenge_progress_log(challenge_id);
        CREATE INDEX IF NOT EXISTS idx_cpl_date ON challenge_progress_log(log_date);
    """)
    conn.commit()
    conn.close()


# ── Challenge CRUD ──────────────────────────────────────────────────────────

def create_challenge(
    title: str, description: str, category: str = "general",
    challenge_type: str = "daily", target_value: float = 1.0,
    target_unit: str = "actions", xp_reward: int = 50,
    badge_icon: str = "🏆", difficulty: str = "medium",
    start_date: Optional[str] = None, end_date: Optional[str] = None,
    created_by: Optional[int] = None, max_participants: int = 0,
) -> int:
    now = datetime.utcnow()
    if start_date is None:
        start_date = now.strftime("%Y-%m-%d")
    if end_date is None:
        end_date = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    conn = _get_conn()
    cur = conn.execute(
        """INSERT INTO eco_challenges
           (title, description, category, challenge_type, target_value,
            target_unit, xp_reward, badge_icon, difficulty, start_date,
            end_date, created_by, max_participants)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (title, description, category, challenge_type, target_value,
         target_unit, xp_reward, badge_icon, difficulty, start_date,
         end_date, created_by, max_participants),
    )
    conn.commit()
    cid = cur.lastrowid
    conn.close()
    return cid


def get_all_challenges(active_only: bool = True) -> List[Dict[str, Any]]:
    conn = _get_conn()
    q = "SELECT * FROM eco_challenges"
    if active_only:
        q += " WHERE is_active = 1"
    q += " ORDER BY start_date DESC"
    rows = [dict(r) for r in conn.execute(q).fetchall()]
    conn.close()
    return rows


def get_challenge_by_id(challenge_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM eco_challenges WHERE id=?", (challenge_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def deactivate_challenge(challenge_id: int):
    conn = _get_conn()
    conn.execute("UPDATE eco_challenges SET is_active=0 WHERE id=?", (challenge_id,))
    conn.commit()
    conn.close()


# ── Participant Management ──────────────────────────────────────────────────

def join_challenge(challenge_id: int, user_id: int, team_name: Optional[str] = None) -> bool:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT INTO challenge_participants (challenge_id, user_id, team_name) VALUES (?,?,?)",
            (challenge_id, user_id, team_name),
        )
        # Update team member count
        if team_name:
            conn.execute(
                """INSERT OR IGNORE INTO challenge_teams (challenge_id, team_name, member_count)
                   VALUES (?, ?, 1)""",
                (challenge_id, team_name),
            )
            conn.execute(
                """UPDATE challenge_teams SET member_count = member_count + 1
                   WHERE challenge_id=? AND team_name=?""",
                (challenge_id, team_name),
            )
        # Log activity
        _log_activity(conn, challenge_id, user_id, "joined", json.dumps({"team": team_name}))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False
    except Exception:
        conn.close()
        return False


def get_participants(challenge_id: int) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT cp.*, COALESCE(u.username, 'User-' || cp.user_id) as username
           FROM challenge_participants cp
           LEFT JOIN users u ON cp.user_id = u.id
           WHERE cp.challenge_id=?
           ORDER BY cp.current_progress DESC""",
        (challenge_id,),
    ).fetchall()]
    conn.close()
    return rows


def is_participant(challenge_id: int, user_id: int) -> bool:
    conn = _get_conn()
    row = conn.execute(
        "SELECT 1 FROM challenge_participants WHERE challenge_id=? AND user_id=?",
        (challenge_id, user_id),
    ).fetchone()
    conn.close()
    return row is not None


# ── Progress Tracking ──────────────────────────────────────────────────────

def log_progress(
    challenge_id: int, user_id: int, value: float = 1.0,
    unit: str = "actions", note: str = "", log_date: Optional[str] = None,
) -> bool:
    if log_date is None:
        log_date = datetime.utcnow().strftime("%Y-%m-%d")
    conn = _get_conn()
    conn.execute(
        """INSERT INTO challenge_progress_log
           (challenge_id, user_id, log_date, value_logged, unit, note)
           VALUES (?,?,?,?,?,?)""",
        (challenge_id, user_id, log_date, value, unit, note),
    )
    # Update participant progress
    conn.execute(
        """UPDATE challenge_participants
           SET current_progress = current_progress + ?
           WHERE challenge_id=? AND user_id=?""",
        (value, challenge_id, user_id),
    )
    # Check completion
    challenge = dict(conn.execute(
        "SELECT target_value FROM eco_challenges WHERE id=?", (challenge_id,)
    ).fetchone() or {})
    participant = dict(conn.execute(
        "SELECT current_progress FROM challenge_participants WHERE challenge_id=? AND user_id=?",
        (challenge_id, user_id),
    ).fetchone() or {})

    if challenge and participant:
        if participant.get("current_progress", 0) >= challenge.get("target_value", float("inf")):
            conn.execute(
                """UPDATE challenge_participants
                   SET is_completed=1, completed_at=datetime('now')
                   WHERE challenge_id=? AND user_id=?""",
                (challenge_id, user_id),
            )
            _log_activity(conn, challenge_id, user_id, "completed", json.dumps({"value": value}))

    # Update team score
    participant_full = conn.execute(
        "SELECT team_name FROM challenge_participants WHERE challenge_id=? AND user_id=?",
        (challenge_id, user_id),
    ).fetchone()
    if participant_full and participant_full["team_name"]:
        conn.execute(
            """UPDATE challenge_teams SET total_score = total_score + ?
               WHERE challenge_id=? AND team_name=?""",
            (value, challenge_id, participant_full["team_name"]),
        )

    _log_activity(conn, challenge_id, user_id, "progress", json.dumps({"value": value, "note": note}))
    conn.commit()
    conn.close()
    return True


def get_user_progress(challenge_id: int, user_id: int) -> Optional[Dict[str, Any]]:
    conn = _get_conn()
    row = conn.execute(
        """SELECT cp.*, ec.target_value, ec.target_unit, ec.xp_reward
           FROM challenge_participants cp
           JOIN eco_challenges ec ON cp.challenge_id = ec.id
           WHERE cp.challenge_id=? AND cp.user_id=?""",
        (challenge_id, user_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_progress_logs(challenge_id: int, user_id: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
    conn = _get_conn()
    q = "SELECT * FROM challenge_progress_log WHERE challenge_id=?"
    params: list = [challenge_id]
    if user_id is not None:
        q += " AND user_id=?"
        params.append(user_id)
    q += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return rows


# ── Team Leaderboard ───────────────────────────────────────────────────────

def get_team_leaderboard(challenge_id: int) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT * FROM challenge_teams
           WHERE challenge_id=?
           ORDER BY total_score DESC""",
        (challenge_id,),
    ).fetchall()]
    conn.close()
    return rows


def get_user_leaderboard(challenge_id: int, limit: int = 25) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT cp.*, COALESCE(u.username, 'User-' || cp.user_id) as username
           FROM challenge_participants cp
           LEFT JOIN users u ON cp.user_id = u.id
           WHERE cp.challenge_id=?
           ORDER BY cp.current_progress DESC
           LIMIT ?""",
        (challenge_id, limit),
    ).fetchall()]
    conn.close()
    return rows


# ── Activity Feed ──────────────────────────────────────────────────────────

def get_activity_feed(challenge_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    conn = _get_conn()
    rows = [dict(r) for r in conn.execute(
        """SELECT caf.*, COALESCE(u.username, 'User-' || caf.user_id) as username
           FROM challenge_activity_feed caf
           LEFT JOIN users u ON caf.user_id = u.id
           WHERE caf.challenge_id=?
           ORDER BY caf.created_at DESC
           LIMIT ?""",
        (challenge_id, limit),
    ).fetchall()]
    conn.close()
    return rows


def _log_activity(conn: sqlite3.Connection, challenge_id: int, user_id: int,
                   activity_type: str, payload: str = "{}"):
    conn.execute(
        """INSERT INTO challenge_activity_feed
           (challenge_id, user_id, activity_type, payload)
           VALUES (?,?,?,?)""",
        (challenge_id, user_id, activity_type, payload),
    )


# ── Aggregate Stats ───────────────────────────────────────────────────────

def get_challenge_stats(challenge_id: int) -> Dict[str, Any]:
    conn = _get_conn()
    participants = conn.execute(
        "SELECT COUNT(*) as cnt FROM challenge_participants WHERE challenge_id=?",
        (challenge_id,),
    ).fetchone()["cnt"]
    completed = conn.execute(
        "SELECT COUNT(*) as cnt FROM challenge_participants WHERE challenge_id=? AND is_completed=1",
        (challenge_id,),
    ).fetchone()["cnt"]
    total_logged = conn.execute(
        "SELECT COALESCE(SUM(value_logged), 0) as total FROM challenge_progress_log WHERE challenge_id=?",
        (challenge_id,),
    ).fetchone()["total"]
    avg_progress = conn.execute(
        "SELECT COALESCE(AVG(current_progress), 0) as avg_p FROM challenge_participants WHERE challenge_id=?",
        (challenge_id,),
    ).fetchone()["avg_p"]
    conn.close()
    return {
        "total_participants": participants,
        "completed": completed,
        "completion_rate": round((completed / participants * 100), 1) if participants else 0,
        "total_value_logged": round(total_logged, 2),
        "average_progress": round(avg_progress, 2),
    }


# ── Seed Data ─────────────────────────────────────────────────────────────

def seed_sample_challenges():
    """Insert sample challenges if none exist."""
    existing = get_all_challenges(active_only=False)
    if existing:
        return
    samples = [
        ("🚲 Bike Commute Week", "Cycle to work or school for 5 consecutive days", "transport",
         "weekly", 5.0, "days", 120, "🚲", "medium"),
        ("🥗 Meatless March", "Go meat-free for the entire month of March", "diet",
         "monthly", 31.0, "days", 300, "🥗", "hard"),
        ("💡 Energy Saver Sprint", "Reduce daily electricity usage by 20% for 2 weeks", "energy",
         "daily", 14.0, "days", 200, "💡", "hard"),
        ("♻️ Zero Waste Week", "Produce zero landfill waste for 7 days", "waste",
         "weekly", 7.0, "days", 150, "♻️", "medium"),
        ("🌳 Plant 10 Trees", "Plant or sponsor planting of 10 trees", "nature",
         "monthly", 10.0, "trees", 250, "🌳", "easy"),
        ("🚶 10K Steps Daily", "Walk 10,000 steps every day for a week", "health",
         "weekly", 7.0, "days", 100, "🚶", "easy"),
        ("🌊 Ocean Cleanup Hour", "Spend 1 hour cleaning a local waterway", "community",
         "one_time", 1.0, "hour", 180, "🌊", "medium"),
        ("♻️ Recycling Streak", "Recycle correctly for 21 consecutive days", "waste",
         "daily", 21.0, "days", 220, "♻️", "medium"),
    ]
    now = datetime.utcnow()
    for title, desc, cat, ctype, target, unit, xp, icon, diff in samples:
        create_challenge(
            title=title, description=desc, category=cat, challenge_type=ctype,
            target_value=target, target_unit=unit, xp_reward=xp,
            badge_icon=icon, difficulty=diff,
            start_date=now.strftime("%Y-%m-%d"),
            end_date=(now + timedelta(days=60)).strftime("%Y-%m-%d"),
        )


# Auto-init on import
init_challenge_db()
seed_sample_challenges()
