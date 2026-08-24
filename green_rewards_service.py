"""
Green Rewards Marketplace — Service Layer
============================================
Business logic for earning points, redeeming rewards, streaks, and level progression.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from green_rewards_db import (
    init_rewards_db, create_reward, get_all_rewards, get_reward_by_id,
    get_or_create_user_points, add_points, spend_points, get_user_transactions,
    get_user_redemptions, log_daily_action, get_daily_actions, get_leaderboard,
    get_rewards_stats, DAILY_ACTIONS,
)

LEVEL_CONFIG = {
    1: {"title": "Eco Beginner", "icon": "🌱", "color": "#22c55e", "next": 200},
    2: {"title": "Green Explorer", "icon": "🌿", "color": "#16a34a", "next": 600},
    3: {"title": "Sustainability Advocate", "icon": "🌍", "color": "#3b82f6", "next": 1200},
    4: {"title": "Carbon Slayer", "icon": "⚔️", "color": "#8b5cf6", "next": 2500},
    5: {"title": "Earth Guardian", "icon": "🛡️", "color": "#f59e0b", "next": 5000},
    6: {"title": "Planet Champion", "icon": "🏆", "color": "#ef4444", "next": 10000},
    7: {"title": "Eco Legend", "icon": "👑", "color": "#ec4899", "next": None},
}

def earn_points(user_id: int, action_name: str, action_category: str, points: int) -> Dict[str, Any]:
    ok = log_daily_action(user_id, action_name, action_category, points)
    if not ok:
        return {"success": False, "error": "Already logged this action today!"}
    up = add_points(user_id, points, "daily_action", action_name)
    level_info = LEVEL_CONFIG.get(up["level"], LEVEL_CONFIG[1])
    return {"success": True, "points_earned": points, "total_points": up["total_points"] - up["spent_points"],
            "level": up["level"], "level_title": up["title"], "level_icon": level_info["icon"]}

def redeem_reward(user_id: int, reward_id: int) -> Dict[str, Any]:
    reward = get_reward_by_id(reward_id)
    if not reward:
        return {"success": False, "error": "Reward not found"}
    if not reward["is_active"] or reward["stock"] <= 0:
        return {"success": False, "error": "Reward unavailable"}
    up = get_or_create_user_points(user_id)
    if up["level"] < reward.get("min_level", 1):
        return {"success": False, "error": f"Requires level {reward['min_level']} ({LEVEL_CONFIG.get(reward['min_level'],{}).get('title','')})"}
    result = spend_points(user_id, reward["points_cost"], reward_id)
    if result["success"]:
        add_points(user_id, 0, "redeem_bonus", f"Redeemed: {reward['title']}")
    return result

def get_user_dashboard(user_id: int) -> Dict[str, Any]:
    stats = get_rewards_stats(user_id)
    level_info = LEVEL_CONFIG.get(stats.get("level", 1), LEVEL_CONFIG[1])
    next_level_pts = level_info.get("next")
    progress = 0
    if next_level_pts:
        progress = min(100, ((stats.get("total_earned", 0)) / next_level_pts) * 100)
    daily_actions = get_daily_actions(user_id)
    today_done = [a["action_name"] for a in daily_actions]
    transactions = get_user_transactions(user_id, limit=10)
    redemptions = get_user_redemptions(user_id)
    available_rewards = get_all_rewards()
    # Filter by level
    available_rewards = [r for r in available_rewards if r.get("min_level", 1) <= stats.get("level", 1)]
    return {**stats, "level_info": level_info, "next_level_pts": next_level_pts,
            "progress": round(progress, 1), "today_actions": today_done,
            "available_rewards": available_rewards, "transactions": transactions,
            "redemptions": redemptions, "all_daily_actions": DAILY_ACTIONS}

def get_category_rewards(category: str) -> List[Dict[str, Any]]:
    return get_all_rewards(category=category)

def seed_sample_rewards():
    from green_rewards_db import _conn
    c = _conn()
    existing = c.execute("SELECT COUNT(*) as cnt FROM green_rewards").fetchone()["cnt"]
    c.close()
    if existing > 0:
        return
    samples = [
        ("🌱 10% Off Eco Store", "Save 10% on sustainable products", "shopping", 150, "coupon", "🌱", "EcoStore", 10, 50, 1, 1),
        ("☕ Free Organic Coffee", "Free coffee at partner cafés", "food", 200, "coupon", "☕", "GreenBean Café", 100, 30, 1, 2),
        ("🌳 Plant a Tree", "We'll plant a tree in your name", "nature", 300, "donation", "🌳", "TreeFoundation", 0, 100, 1, 1),
        ("🚲 Free Bike Rental Day", "1-day bike rental at partner shops", "transport", 250, "voucher", "🚲", "CityBikes", 100, 20, 1, 2),
        ("📱 Plant 5 Trees Bundle", "Fund 5 trees through verified project", "nature", 500, "donation", "🌳", "OneTreePlanted", 0, 100, 1, 3),
        ("♻️ Free Reusable Kit", "Starter kit: bottle, bag, straw, container", "waste", 400, "physical", "♻️", "ZeroWaste Co", 0, 25, 0, 2),
        ("🧘 Eco Wellness Workshop", "Free online sustainability workshop", "education", 350, "digital", "🧘", "EcoLearn", 100, 40, 1, 3),
        ("🎫 Carbon Offset Voucher", "Offset 100kg CO₂ through verified credits", "offsets", 600, "voucher", "🎫", "CarbonTrust", 0, 30, 1, 4),
        ("🌍 Premium Eco Membership", "3-month premium access to EcoBuddy AI", "digital", 1000, "subscription", "🌍", "EcoBuddy", 0, 10, 1, 5),
        ("🏔️ Eco Adventure Trip", "Discounted eco-tourism trip package", "travel", 2000, "voucher", "🏔️", "GreenTrails", 30, 5, 1, 6),
    ]
    for title, desc, cat, pts, rtype, icon, partner, disc, stock, feat, lvl in samples:
        create_reward(title, desc, cat, pts, rtype, icon, partner, disc, stock, feat, lvl)

seed_sample_rewards()
