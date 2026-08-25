"""
Eco Impact Time Capsule — Database Layer
==========================================
Snapshots of a user's eco state at a point in time, compared later to track growth.
"""

import sqlite3, os, json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "eco_buddy.db")

def _conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA foreign_keys=ON"); return c

def init_capsule_db():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS eco_time_capsules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            title           TEXT NOT NULL,
            capsule_type    TEXT NOT NULL DEFAULT 'snapshot',
            snapshot_data   TEXT NOT NULL DEFAULT '{}',
            eco_score       REAL DEFAULT 0,
            carbon_kg       REAL DEFAULT 0,
            streak_days     INTEGER DEFAULT 0,
            badges_earned   INTEGER DEFAULT 0,
            challenges_done INTEGER DEFAULT 0,
            mood            TEXT DEFAULT 'neutral',
            notes           TEXT DEFAULT '',
            is_sealed       INTEGER NOT NULL DEFAULT 1,
            seal_date       TEXT DEFAULT (datetime('now')),
            open_date       TEXT DEFAULT NULL,
            opened          INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS capsule_milestones (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            capsule_id      INTEGER NOT NULL,
            milestone_type  TEXT NOT NULL,
            title           TEXT NOT NULL,
            achieved_at     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (capsule_id) REFERENCES eco_time_capsules(id)
        );
        CREATE TABLE IF NOT EXISTS capsule_reflections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            capsule_id      INTEGER NOT NULL,
            reflection_text TEXT NOT NULL,
            rating          INTEGER DEFAULT 5,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (capsule_id) REFERENCES eco_time_capsules(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cps_user ON eco_time_capsules(user_id);
        CREATE INDEX IF NOT EXISTS idx_cps_capsule ON capsule_milestones(capsule_id);
    """)
    c.commit(); c.close()

def create_capsule(user_id: int, title: str, capsule_type: str = "snapshot",
                    snapshot_data: Dict = None, eco_score: float = 0,
                    carbon_kg: float = 0, streak_days: int = 0,
                    badges_earned: int = 0, challenges_done: int = 0,
                    mood: str = "neutral", notes: str = "",
                    open_date: Optional[str] = None) -> int:
    c = _conn()
    cur = c.execute(
        """INSERT INTO eco_time_capsules
           (user_id,title,capsule_type,snapshot_data,eco_score,carbon_kg,
            streak_days,badges_earned,challenges_done,mood,notes,open_date)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, title, capsule_type, json.dumps(snapshot_data or {}),
         eco_score, carbon_kg, streak_days, badges_earned, challenges_done,
         mood, notes, open_date))
    c.commit(); cid = cur.lastrowid; c.close(); return cid

def get_user_capsules(user_id: int) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM eco_time_capsules WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)).fetchall()]
    for r in rows:
        r["snapshot_data"] = json.loads(r["snapshot_data"])
    c.close(); return rows

def get_capsule_by_id(capsule_id: int) -> Optional[Dict[str, Any]]:
    c = _conn(); row = c.execute("SELECT * FROM eco_time_capsules WHERE id=?", (capsule_id,)).fetchone()
    c.close()
    if row:
        d = dict(row); d["snapshot_data"] = json.loads(d["snapshot_data"]); return d
    return None

def mark_capsule_opened(capsule_id: int):
    c = _conn(); c.execute("UPDATE eco_time_capsules SET opened=1 WHERE id=?", (capsule_id,))
    c.commit(); c.close()

def add_milestone(capsule_id: int, milestone_type: str, title: str) -> int:
    c = _conn()
    cur = c.execute("INSERT INTO capsule_milestones (capsule_id,milestone_type,title) VALUES (?,?,?)",
                     (capsule_id, milestone_type, title))
    c.commit(); mid = cur.lastrowid; c.close(); return mid

def get_milestones(capsule_id: int) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM capsule_milestones WHERE capsule_id=? ORDER BY achieved_at",
        (capsule_id,)).fetchall()]
    c.close(); return rows

def add_reflection(capsule_id: int, text: str, rating: int = 5) -> int:
    c = _conn()
    cur = c.execute("INSERT INTO capsule_reflections (capsule_id,reflection_text,rating) VALUES (?,?,?)",
                     (capsule_id, text, rating))
    c.commit(); rid = cur.lastrowid; c.close(); return rid

def get_reflections(capsule_id: int) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM capsule_reflections WHERE capsule_id=? ORDER BY created_at DESC",
        (capsule_id,)).fetchall()]
    c.close(); return rows

def delete_capsule(capsule_id: int):
    c = _conn()
    c.execute("DELETE FROM capsule_reflections WHERE capsule_id=?", (capsule_id,))
    c.execute("DELETE FROM capsule_milestones WHERE capsule_id=?", (capsule_id,))
    c.execute("DELETE FROM eco_time_capsules WHERE id=?", (capsule_id,))
    c.commit(); c.close()

def get_capsule_stats(user_id: int) -> Dict[str, Any]:
    c = _conn()
    total = c.execute("SELECT COUNT(*) as cnt FROM eco_time_capsules WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    opened = c.execute("SELECT COUNT(*) as cnt FROM eco_time_capsules WHERE user_id=? AND opened=1", (user_id,)).fetchone()["cnt"]
    pending = total - opened
    avg_score = c.execute("SELECT COALESCE(AVG(eco_score),0) as avg FROM eco_time_capsules WHERE user_id=?", (user_id,)).fetchone()["avg"]
    c.close()
    return {"total_capsules": total, "opened": opened, "pending": pending, "avg_eco_score": round(avg_score, 1)}

MOOD_EMOJI = {"amazing": "🤩", "great": "😊", "good": "🙂", "neutral": "😐", "struggling": "😔", "terrible": "😢"}
CAPSULE_TYPES = {"snapshot": ("📸 Snapshot", "Capture your eco state right now"),
                 "monthly": ("🗓️ Monthly Review", "End-of-month reflection"),
                 "goal": ("🎯 Goal Capsule", "Seal a goal to open when achieved"),
                 "challenge": ("🏆 Challenge Memory", "Remember a completed challenge"),
                 "newyear": ("🎆 New Year", "Open next New Year's Day")}

init_capsule_db()
