"""
Green Rewards Marketplace — Database Layer
=============================================
SQLite schema and CRUD for eco rewards, user points, redemptions, and daily challenges.
"""

import sqlite3, os, json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "eco_buddy.db")

def _conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA foreign_keys=ON"); return c

def init_rewards_db():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS green_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            points_cost INTEGER NOT NULL DEFAULT 100,
            reward_type TEXT NOT NULL DEFAULT 'coupon',
            icon TEXT NOT NULL DEFAULT '🎁',
            partner_name TEXT DEFAULT '',
            discount_pct REAL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 100,
            is_active INTEGER NOT NULL DEFAULT 1,
            featured INTEGER NOT NULL DEFAULT 0,
            min_level INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS user_green_points (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            total_points INTEGER NOT NULL DEFAULT 0,
            spent_points INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            title TEXT NOT NULL DEFAULT 'Eco Beginner',
            streak_days INTEGER DEFAULT 0,
            last_activity TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS point_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            points INTEGER NOT NULL,
            tx_type TEXT NOT NULL,
            description TEXT NOT NULL,
            reference_id INTEGER DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS reward_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reward_id INTEGER NOT NULL,
            points_spent INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            coupon_code TEXT DEFAULT NULL,
            redeemed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (reward_id) REFERENCES green_rewards(id)
        );
        CREATE TABLE IF NOT EXISTS daily_eco_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action_name TEXT NOT NULL,
            action_category TEXT NOT NULL,
            points_earned INTEGER NOT NULL DEFAULT 0,
            log_date TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, action_name, log_date)
        );
        CREATE INDEX IF NOT EXISTS idx_pts_user ON point_transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_rr_user ON reward_redemptions(user_id);
        CREATE INDEX IF NOT EXISTS idx_dea_user_date ON daily_eco_actions(user_id, log_date);
    """)
    c.commit(); c.close()

def create_reward(title: str, description: str, category: str = "general",
                   points_cost: int = 100, reward_type: str = "coupon",
                   icon: str = "🎁", partner_name: str = "", discount_pct: float = 0,
                   stock: int = 100, featured: int = 0, min_level: int = 1) -> int:
    c = _conn()
    cur = c.execute(
        """INSERT INTO green_rewards (title,description,category,points_cost,reward_type,
           icon,partner_name,discount_pct,stock,featured,min_level) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (title, description, category, points_cost, reward_type, icon, partner_name,
         discount_pct, stock, featured, min_level))
    c.commit(); rid = cur.lastrowid; c.close(); return rid

def get_all_rewards(category: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
    c = _conn()
    q = "SELECT * FROM green_rewards WHERE 1=1"
    if active_only: q += " AND is_active=1 AND stock>0"
    if category: q += f" AND category='{category}'"
    q += " ORDER BY featured DESC, points_cost ASC"
    rows = [dict(r) for r in c.execute(q).fetchall()]; c.close(); return rows

def get_reward_by_id(reward_id: int) -> Optional[Dict[str, Any]]:
    c = _conn(); row = c.execute("SELECT * FROM green_rewards WHERE id=?", (reward_id,)).fetchone()
    c.close(); return dict(row) if row else None

def get_or_create_user_points(user_id: int) -> Dict[str, Any]:
    c = _conn()
    row = c.execute("SELECT * FROM user_green_points WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        c.execute("INSERT INTO user_green_points (user_id) VALUES (?)", (user_id,))
        c.commit()
        row = c.execute("SELECT * FROM user_green_points WHERE user_id=?", (user_id,)).fetchone()
    d = dict(row); c.close(); return d

def add_points(user_id: int, points: int, tx_type: str = "earn", description: str = "", reference_id: int = None) -> Dict[str, Any]:
    c = _conn()
    c.execute("UPDATE user_green_points SET total_points=total_points+?, updated_at=datetime('now') WHERE user_id=?",
              (points, user_id))
    c.execute("INSERT INTO point_transactions (user_id,points,tx_type,description,reference_id) VALUES (?,?,?,?,?)",
              (user_id, points, tx_type, description, reference_id))
    # Check level up
    up = c.execute("SELECT * FROM user_green_points WHERE user_id=?", (user_id,)).fetchone()
    new_level = _calc_level(up["total_points"])
    titles = {1: "Eco Beginner", 2: "Green Explorer", 3: "Sustainability Advocate",
              4: "Carbon Slayer", 5: "Earth Guardian", 6: "Planet Champion", 7: "Eco Legend"}
    if new_level > up["level"]:
        c.execute("UPDATE user_green_points SET level=?, title=? WHERE user_id=?",
                  (new_level, titles.get(new_level, "Eco Legend"), user_id))
    c.commit(); d = dict(c.execute("SELECT * FROM user_green_points WHERE user_id=?", (user_id,)).fetchone())
    c.close(); return d

def spend_points(user_id: int, points: int, reward_id: int) -> Dict[str, Any]:
    c = _conn()
    up = c.execute("SELECT * FROM user_green_points WHERE user_id=?", (user_id,)).fetchone()
    available = up["total_points"] - up["spent_points"]
    if available < points:
        c.close(); return {"success": False, "error": f"Need {points} pts, have {available}"}
    c.execute("UPDATE user_green_points SET spent_points=spent_points+?, updated_at=datetime('now') WHERE user_id=?",
              (points, user_id))
    c.execute("INSERT INTO point_transactions (user_id,points,tx_type,description,reference_id) VALUES (?,?,?,?,?)",
              (user_id, -points, "redeem", f"Redeemed reward #{reward_id}", reward_id))
    c.execute("UPDATE green_rewards SET stock=stock-1 WHERE id=?", (reward_id,))
    code = f"ECO-{user_id}-{reward_id}-{datetime.utcnow().strftime('%m%d%H%M')}"
    c.execute("INSERT INTO reward_redemptions (user_id,reward_id,points_spent,coupon_code) VALUES (?,?,?,?)",
              (user_id, reward_id, points, code))
    c.commit(); c.close()
    return {"success": True, "coupon_code": code, "remaining": available - points}

def get_user_transactions(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM point_transactions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)).fetchall()]
    c.close(); return rows

def get_user_redemptions(user_id: int) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        """SELECT rr.*, gr.title as reward_title, gr.icon as reward_icon
           FROM reward_redemptions rr JOIN green_rewards gr ON rr.reward_id=gr.id
           WHERE rr.user_id=? ORDER BY rr.redeemed_at DESC""", (user_id,)).fetchall()]
    c.close(); return rows

def log_daily_action(user_id: int, action_name: str, action_category: str, points: int,
                      log_date: Optional[str] = None) -> bool:
    if log_date is None: log_date = datetime.utcnow().strftime("%Y-%m-%d")
    c = _conn()
    try:
        c.execute("INSERT INTO daily_eco_actions (user_id,action_name,action_category,points_earned,log_date) VALUES (?,?,?,?,?)",
                  (user_id, action_name, action_category, points, log_date))
        c.commit(); c.close(); return True
    except sqlite3.IntegrityError:
        c.close(); return False

def get_daily_actions(user_id: int, log_date: Optional[str] = None) -> List[Dict[str, Any]]:
    if log_date is None: log_date = datetime.utcnow().strftime("%Y-%m-%d")
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM daily_eco_actions WHERE user_id=? AND log_date=? ORDER BY created_at",
        (user_id, log_date)).fetchall()]
    c.close(); return rows

def get_leaderboard(limit: int = 25) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        """SELECT up.*, COALESCE(u.username, 'User-' || up.user_id) as username
           FROM user_green_points up LEFT JOIN users u ON up.user_id=u.id
           ORDER BY up.total_points DESC LIMIT ?""", (limit,)).fetchall()]
    c.close(); return rows

def get_rewards_stats(user_id: int) -> Dict[str, Any]:
    c = _conn()
    up = c.execute("SELECT * FROM user_green_points WHERE user_id=?", (user_id,)).fetchone()
    redemptions = c.execute("SELECT COUNT(*) as cnt FROM reward_redemptions WHERE user_id=?", (user_id,)).fetchone()["cnt"]
    today = datetime.utcnow().strftime("%Y-%m-%d")
    today_actions = c.execute("SELECT COUNT(*) as cnt FROM daily_eco_actions WHERE user_id=? AND log_date=?",
                               (user_id, today)).fetchone()["cnt"]
    c.close()
    if not up: return {"points": 0, "level": 1, "title": "Eco Beginner", "redemptions": 0, "today_actions": 0}
    return {"points": up["total_points"] - up["spent_points"], "total_earned": up["total_points"],
            "level": up["level"], "title": up["title"], "redemptions": redemptions,
            "today_actions": today_actions}

def _calc_level(points: int) -> int:
    thresholds = [0, 200, 600, 1200, 2500, 5000, 10000]
    level = 1
    for i, t in enumerate(thresholds):
        if points >= t: level = i + 1
    return level

DAILY_ACTIONS = [
    ("Walk or cycle to work", "transport", 15),
    ("Use public transit", "transport", 10),
    ("Skip driving today", "transport", 20),
    ("Eat a vegetarian meal", "diet", 8),
    ("Eat a fully vegan meal", "diet", 12),
    ("Avoid food waste today", "diet", 10),
    ("Recycle all waste today", "waste", 10),
    ("Compost food scraps", "waste", 8),
    ("Use reusable bags", "waste", 5),
    ("Take a short shower (<5min)", "water", 8),
    ("Fix a leaky faucet", "water", 10),
    ("Switch off unused lights", "energy", 5),
    ("Unplug idle electronics", "energy", 8),
    ("Use natural light today", "energy", 6),
    ("Plant a seed or water plants", "nature", 12),
    ("Pick up litter outdoors", "community", 15),
    ("Share eco tip with someone", "community", 8),
    ("Read an eco article", "learning", 5),
    ("Meditate 10 minutes", "wellness", 5),
    ("Use a reusable water bottle", "waste", 5),
]

init_rewards_db()
