"""Eco Journal — Service Layer"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from eco_journal_db import (
    create_entry, get_entries, get_entry_by_date, get_entry_by_id,
    update_entry, delete_entry, get_journal_stats, get_random_prompt,
    MOOD_LABELS, ENERGY_LABELS,
)

def write_entry(user_id: int, title: str, content: str, mood: int = 5, energy: int = 5,
                 eco_actions: list = None, tags: list = None, weather: str = "",
                 gratitude: str = "", entry_date: Optional[str] = None) -> Dict[str, Any]:
    if entry_date is None: entry_date = datetime.utcnow().strftime("%Y-%m-%d")
    existing = get_entry_by_date(user_id, entry_date)
    if existing:
        update_entry(existing["id"], title=title, content=content, mood=mood,
                     energy_level=energy, eco_actions_done=eco_actions or [],
                     eco_actions_count=len(eco_actions or []), tags=tags or [],
                     weather=weather, gratitude=gratitude)
        return {"success": True, "entry_id": existing["id"], "updated": True}
    eid = create_entry(user_id, entry_date, title, content, mood, energy,
                        eco_actions or [], tags or [], weather, gratitude)
    return {"success": True, "entry_id": eid, "updated": False}

def get_calendar_data(user_id: int, year: int, month: int) -> List[Dict[str, Any]]:
    from eco_journal_db import _conn
    c = _conn()
    prefix = f"{year}-{month:02d}"
    rows = [dict(r) for r in c.execute(
        "SELECT entry_date, mood, energy_level, eco_actions_count FROM eco_journal_entries WHERE user_id=? AND entry_date LIKE ?",
        (user_id, f"{prefix}%")).fetchall()]
    c.close(); return rows

def get_mood_trend(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
    from eco_journal_db import _conn
    c = _conn()
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = [dict(r) for r in c.execute(
        "SELECT entry_date, mood, energy_level, eco_actions_count FROM eco_journal_entries WHERE user_id=? AND entry_date>=? ORDER BY entry_date",
        (user_id, start)).fetchall()]
    c.close(); return rows

def get_tag_cloud(user_id: int) -> Dict[str, int]:
    entries = get_entries(user_id, limit=100)
    tags = {}
    for e in entries:
        for t in e.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
    return dict(sorted(tags.items(), key=lambda x: x[1], reverse=True))

def get_streak(user_id: int) -> int:
    from eco_journal_db import _conn
    c = _conn()
    rows = c.execute("SELECT DISTINCT entry_date FROM eco_journal_entries WHERE user_id=? ORDER BY entry_date DESC",
                      (user_id,)).fetchall()
    c.close()
    if not rows: return 0
    dates = [datetime.strptime(r["entry_date"], "%Y-%m-%d").date() for r in rows]
    streak = 1
    for i in range(1, len(dates)):
        if (dates[i-1] - dates[i]).days == 1: streak += 1
        else: break
    return streak

ECO_ACTION_PRESETS = [
    "Walked/cycled instead of driving", "Took public transit", "Ate vegetarian meal",
    "Ate vegan meal", "Composted food waste", "Recycled all waste", "Used reusable bags",
    "Took short shower", "Switched off unused lights", "Used natural light",
    "Planted/watered plants", "Picked up litter", "Shared eco tip", "Biked to work",
    "Avoided single-use plastic", "Used public water fountain", "Ate local produce",
    "Repaired instead of replaced", "Borrowed instead of bought", "Donated old clothes",
]
