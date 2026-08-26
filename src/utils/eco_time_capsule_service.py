"""
Eco Impact Time Capsule — Service Layer
=========================================
Logic for creating, comparing, and reflecting on eco time capsules.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from src.utils.eco_time_capsule_db import (
    init_capsule_db, create_capsule, get_user_capsules, get_capsule_by_id,
    mark_capsule_opened, add_milestone, get_milestones, add_reflection,
    get_reflections, delete_capsule, get_capsule_stats, MOOD_EMOJI, CAPSULE_TYPES,
)

def create_snapshot_capsule(user_id: int, title: str, eco_score: float = 0,
                             carbon_kg: float = 0, streak_days: int = 0,
                             badges_earned: int = 0, challenges_done: int = 0,
                             mood: str = "neutral", notes: str = "",
                             open_date: Optional[str] = None) -> Dict[str, Any]:
    snapshot = {
        "eco_score": eco_score, "carbon_kg": carbon_kg, "streak_days": streak_days,
        "badges_earned": badges_earned, "challenges_done": challenges_done,
        "mood": mood, "timestamp": datetime.utcnow().isoformat(),
    }
    cid = create_capsule(user_id, title, "snapshot", snapshot, eco_score,
                          carbon_kg, streak_days, badges_earned, challenges_done,
                          mood, notes, open_date)
    return {"success": True, "capsule_id": cid}

def get_user_dashboard(user_id: int) -> Dict[str, Any]:
    capsules = get_user_capsules(user_id)
    stats = get_capsule_stats(user_id)
    sealed = [c for c in capsules if not c["opened"]]
    opened = [c for c in capsules if c["opened"]]
    now = datetime.utcnow()
    ready_to_open = []
    for c in sealed:
        if c.get("open_date"):
            try:
                od = datetime.strptime(c["open_date"], "%Y-%m-%d")
                if od <= now:
                    ready_to_open.append(c)
            except (ValueError, TypeError):
                pass
    return {"capsules": capsules, "stats": stats, "sealed": sealed,
            "opened": opened, "ready_to_open": ready_to_open}

def open_capsule(capsule_id: int, user_id: int) -> Dict[str, Any]:
    capsule = get_capsule_by_id(capsule_id)
    if not capsule:
        return {"success": False, "error": "Capsule not found"}
    if capsule["user_id"] != user_id:
        return {"success": False, "error": "Not your capsule"}
    if capsule["opened"]:
        return {"success": False, "error": "Already opened"}
    mark_capsule_opened(capsule_id)
    milestones = get_milestones(capsule_id)
    reflections = get_reflections(capsule_id)
    return {"success": True, "capsule": capsule, "milestones": milestones, "reflections": reflections}

def compare_capsules(capsule_a_id: int, capsule_b_id: int) -> Dict[str, Any]:
    a = get_capsule_by_id(capsule_a_id)
    b = get_capsule_by_id(capsule_b_id)
    if not a or not b:
        return {"error": "Capsule not found"}
    comparison = {
        "eco_score": {"a": a["eco_score"], "b": b["eco_score"],
                       "delta": round(b["eco_score"] - a["eco_score"], 1),
                       "direction": "up" if b["eco_score"] > a["eco_score"] else "down"},
        "carbon_kg": {"a": a["carbon_kg"], "b": b["carbon_kg"],
                       "delta": round(b["carbon_kg"] - a["carbon_kg"], 1),
                       "direction": "down" if b["carbon_kg"] < a["carbon_kg"] else "up"},
        "streak_days": {"a": a["streak_days"], "b": b["streak_days"],
                         "delta": b["streak_days"] - a["streak_days"],
                         "direction": "up" if b["streak_days"] > a["streak_days"] else "down"},
        "badges_earned": {"a": a["badges_earned"], "b": b["badges_earned"],
                           "delta": b["badges_earned"] - a["badges_earned"],
                           "direction": "up" if b["badges_earned"] > a["badges_earned"] else "same"},
        "challenges_done": {"a": a["challenges_done"], "b": b["challenges_done"],
                             "delta": b["challenges_done"] - a["challenges_done"],
                             "direction": "up" if b["challenges_done"] > a["challenges_done"] else "same"},
    }
    a_date = a.get("created_at", "")[:10]
    b_date = b.get("created_at", "")[:10]
    try:
        d1 = datetime.strptime(a_date, "%Y-%m-%d")
        d2 = datetime.strptime(b_date, "%Y-%m-%d")
        comparison["days_between"] = (d2 - d1).days
    except (ValueError, TypeError):
        comparison["days_between"] = 0
    return {"capsule_a": a, "capsule_b": b, "comparison": comparison}

def auto_detect_milestones(capsule_id: int) -> List[str]:
    capsule = get_capsule_by_id(capsule_id)
    if not capsule:
        return []
    detected = []
    if capsule["eco_score"] >= 90:
        add_milestone(capsule_id, "achievement", "🌟 Eco Score 90+ Club")
        detected.append("🌟 Eco Score 90+ Club")
    if capsule["eco_score"] >= 75:
        add_milestone(capsule_id, "achievement", "🌿 Sustainability Champion")
        detected.append("🌿 Sustainability Champion")
    if capsule["streak_days"] >= 30:
        add_milestone(capsule_id, "streak", "🔥 30-Day Streak Master")
        detected.append("🔥 30-Day Streak Master")
    if capsule["streak_days"] >= 7:
        add_milestone(capsule_id, "streak", "⚡ Week-Long Warrior")
        detected.append("⚡ Week-Long Warrior")
    if capsule["challenges_done"] >= 5:
        add_milestone(capsule_id, "challenge", "🏆 Challenge Veteran (5+)")
        detected.append("🏆 Challenge Veteran (5+)")
    if capsule["badges_earned"] >= 10:
        add_milestone(capsule_id, "collection", "🏅 Badge Collector (10+)")
        detected.append("🏅 Badge Collector (10+)")
    if capsule["carbon_kg"] < 200:
        add_milestone(capsule_id, "low_carbon", "🌱 Low-Carbon Lifestyle (<200 kg)")
        detected.append("🌱 Low-Carbon Lifestyle (<200 kg)")
    if capsule["mood"] == "amazing":
        add_milestone(capsule_id, "mood", "🤩 Peak Eco Enthusiasm")
        detected.append("🤩 Peak Eco Enthusiasm")
    return detected

def get_timeline_data(user_id: int) -> List[Dict[str, Any]]:
    capsules = get_user_capsules(user_id)
    timeline = []
    for c in capsules:
        timeline.append({
            "id": c["id"], "title": c["title"], "date": c["created_at"][:10],
            "eco_score": c["eco_score"], "carbon_kg": c["carbon_kg"],
            "mood": MOOD_EMOJI.get(c.get("mood", "neutral"), "😐"),
            "opened": c["opened"], "type": c.get("capsule_type", "snapshot"),
        })
    return timeline

def get_growth_summary(user_id: int) -> Dict[str, Any]:
    capsules = get_user_capsules(user_id)
    if len(capsules) < 2:
        return {"has_growth": False}
    oldest = capsules[-1]
    newest = capsules[0]
    return {
        "has_growth": True,
        "first_score": oldest["eco_score"],
        "latest_score": newest["eco_score"],
        "score_change": round(newest["eco_score"] - oldest["eco_score"], 1),
        "first_carbon": oldest["carbon_kg"],
        "latest_carbon": newest["carbon_kg"],
        "carbon_change": round(newest["carbon_kg"] - oldest["carbon_kg"], 1),
        "total_capsules": len(capsules),
        "first_date": oldest["created_at"][:10],
        "latest_date": newest["created_at"][:10],
    }
