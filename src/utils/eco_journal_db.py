"""Eco Journal — Database Layer"""
import sqlite3, os, json
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "eco_buddy.db")
def _conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); return c

def init_journal_db():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS eco_journal_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            mood INTEGER DEFAULT 5,
            energy_level INTEGER DEFAULT 5,
            eco_actions_done TEXT DEFAULT '[]',
            eco_actions_count INTEGER DEFAULT 0,
            tags TEXT DEFAULT '[]',
            weather TEXT DEFAULT '',
            gratitude TEXT DEFAULT '',
            is_private INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS journal_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_text TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            is_active INTEGER DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_je_user_date ON eco_journal_entries(user_id, entry_date);
    """); c.commit(); c.close()

def create_entry(user_id: int, entry_date: str, title: str, content: str,
                  mood: int = 5, energy_level: int = 5, eco_actions: list = None,
                  tags: list = None, weather: str = "", gratitude: str = "") -> int:
    c = _conn()
    cur = c.execute(
        """INSERT INTO eco_journal_entries (user_id,entry_date,title,content,mood,energy_level,
           eco_actions_done,eco_actions_count,tags,weather,gratitude) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, entry_date, title, content, mood, energy_level,
         json.dumps(eco_actions or []), len(eco_actions or []),
         json.dumps(tags or []), weather, gratitude))
    c.commit(); eid = cur.lastrowid; c.close(); return eid

def get_entries(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM eco_journal_entries WHERE user_id=? ORDER BY entry_date DESC LIMIT ?",
        (user_id, limit)).fetchall()]
    for r in rows:
        r["eco_actions_done"] = json.loads(r["eco_actions_done"])
        r["tags"] = json.loads(r["tags"])
    c.close(); return rows

def get_entry_by_date(user_id: int, entry_date: str) -> Optional[Dict[str, Any]]:
    c = _conn()
    row = c.execute("SELECT * FROM eco_journal_entries WHERE user_id=? AND entry_date=?",
                     (user_id, entry_date)).fetchone()
    c.close()
    if row:
        d = dict(row); d["eco_actions_done"] = json.loads(d["eco_actions_done"]); d["tags"] = json.loads(d["tags"]); return d
    return None

def get_entry_by_id(entry_id: int) -> Optional[Dict[str, Any]]:
    c = _conn(); row = c.execute("SELECT * FROM eco_journal_entries WHERE id=?", (entry_id,)).fetchone(); c.close()
    if row:
        d = dict(row); d["eco_actions_done"] = json.loads(d["eco_actions_done"]); d["tags"] = json.loads(d["tags"]); return d
    return None

def update_entry(entry_id: int, **kwargs):
    c = _conn(); sets, vals = [], []
    for k, v in kwargs.items():
        if k in ("title","content","mood","energy_level","eco_actions_done","eco_actions_count","tags","weather","gratitude"):
            if k in ("eco_actions_done","tags") and isinstance(v, list): v = json.dumps(v)
            sets.append(f"{k}=?"); vals.append(v)
    if sets:
        sets.append("updated_at=datetime('now')"); vals.append(entry_id)
        c.execute(f"UPDATE eco_journal_entries SET {','.join(sets)} WHERE id=?", vals); c.commit()
    c.close()

def delete_entry(entry_id: int):
    c = _conn(); c.execute("DELETE FROM eco_journal_entries WHERE id=?", (entry_id,)); c.commit(); c.close()

def get_journal_stats(user_id: int) -> Dict[str, Any]:
    c = _conn()
    total = c.execute("SELECT COUNT(*) as cnt FROM eco_journal_entries WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    avg_mood = c.execute("SELECT COALESCE(AVG(mood),5) as avg FROM eco_journal_entries WHERE user_id=?", (user_id,)).fetchone()["avg"]
    avg_energy = c.execute("SELECT COALESCE(AVG(energy_level),5) as avg FROM eco_journal_entries WHERE user_id=?", (user_id,)).fetchone()["avg"]
    avg_actions = c.execute("SELECT COALESCE(AVG(eco_actions_count),0) as avg FROM eco_journal_entries WHERE user_id=?", (user_id,)).fetchone()["avg"]
    total_actions = c.execute("SELECT COALESCE(SUM(eco_actions_count),0) as total FROM eco_journal_entries WHERE user_id=?", (user_id,)).fetchone()["total"]
    c.close()
    return {"total_entries": total, "avg_mood": round(avg_mood, 1), "avg_energy": round(avg_energy, 1),
            "avg_actions": round(avg_actions, 1), "total_actions": total_actions}

def seed_prompts():
    c = _conn()
    existing = c.execute("SELECT COUNT(*) as cnt FROM journal_prompts").fetchone()["cnt"]
    if existing > 0: c.close(); return
    prompts = [
        ("What eco-friendly choice are you most proud of today?", "reflection"),
        ("How did your daily routine impact the environment today?", "reflection"),
        ("What's one thing you could do differently tomorrow?", "planning"),
        ("Describe a moment today when you felt connected to nature.", "gratitude"),
        ("What challenge did you face in living sustainably today?", "challenge"),
        ("How did you feel about your carbon footprint today?", "mood"),
        ("What eco-action had the biggest impact today?", "impact"),
        ("Write about a sustainable habit you're building.", "habits"),
        ("What made you smile about the environment today?", "gratitude"),
        ("If you could change one thing about your day eco-wise, what would it be?", "planning"),
        ("How did your food choices affect the planet today?", "diet"),
        ("What inspired you to be more eco-friendly today?", "inspiration"),
        ("Describe your ideal zero-waste day.", "vision"),
        ("What did you learn about sustainability today?", "learning"),
        ("How did you reduce, reuse, or recycle today?", "actions"),
    ]
    for text, cat in prompts:
        c.execute("INSERT INTO journal_prompts (prompt_text,category) VALUES (?,?)", (text, cat))
    c.commit(); c.close()

def get_random_prompt() -> Optional[Dict[str, Any]]:
    c = _conn(); row = c.execute("SELECT * FROM journal_prompts WHERE is_active=1 ORDER BY RANDOM() LIMIT 1").fetchone()
    c.close(); return dict(row) if row else None

MOOD_LABELS = {1: "😢 Terrible", 2: "😔 Bad", 3: "😐 Okay", 4: "🙂 Good", 5: "😊 Fine",
               6: "😃 Great", 7: "😄 Happy", 8: "🤩 Amazing", 9: "🥳 Excellent", 10: "🌟 Perfect"}
ENERGY_LABELS = {1: "💤 Exhausted", 3: "😴 Tired", 5: "😐 Normal", 7: "⚡ Energized", 10: "🔥 Fired Up"}

init_journal_db()
seed_prompts()
