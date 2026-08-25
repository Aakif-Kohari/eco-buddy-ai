"""
Carbon Budget Planner — Database Layer
========================================
SQLite schema and CRUD for personal carbon budgets, monthly allocations,
daily spending logs, alerts, and budget history.
"""

import sqlite3, os, json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "eco_buddy.db")

def _conn():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row; c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA foreign_keys=ON"); return c

def init_budget_db():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS carbon_budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL DEFAULT 'My Carbon Budget',
            monthly_limit_kg REAL NOT NULL DEFAULT 500.0,
            category_limits TEXT NOT NULL DEFAULT '{}',
            alert_threshold_pct REAL NOT NULL DEFAULT 80.0,
            hard_cap_kg REAL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, is_active) WHERE is_active=1
        );
        CREATE TABLE IF NOT EXISTS carbon_spending_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            budget_id INTEGER,
            log_date TEXT NOT NULL,
            category TEXT NOT NULL,
            activity TEXT NOT NULL,
            co2_kg REAL NOT NULL,
            source TEXT DEFAULT 'manual',
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (budget_id) REFERENCES carbon_budgets(id)
        );
        CREATE TABLE IF NOT EXISTS carbon_budget_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            budget_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            threshold_pct REAL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (budget_id) REFERENCES carbon_budgets(id)
        );
        CREATE TABLE IF NOT EXISTS carbon_budget_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            budget_id INTEGER,
            month TEXT NOT NULL,
            total_spent_kg REAL NOT NULL DEFAULT 0,
            monthly_limit_kg REAL NOT NULL,
            savings_kg REAL NOT NULL DEFAULT 0,
            category_breakdown TEXT DEFAULT '{}',
            completed_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_csl_user_date ON carbon_spending_log(user_id, log_date);
        CREATE INDEX IF NOT EXISTS idx_csl_budget ON carbon_spending_log(budget_id);
        CREATE INDEX IF NOT EXISTS idx_cba_user ON carbon_budget_alerts(user_id);
    """)
    c.commit(); c.close()

# ── Budget CRUD ────────────────────────────────────────────────────────

def create_budget(user_id: int, name: str = "My Carbon Budget", monthly_limit_kg: float = 500.0,
                   category_limits: Optional[Dict] = None, alert_threshold_pct: float = 80.0,
                   hard_cap_kg: float = 0) -> int:
    c = _conn()
    c.execute("UPDATE carbon_budgets SET is_active=0 WHERE user_id=? AND is_active=1", (user_id,))
    cur = c.execute(
        "INSERT INTO carbon_budgets (user_id,name,monthly_limit_kg,category_limits,alert_threshold_pct,hard_cap_kg) VALUES (?,?,?,?,?,?)",
        (user_id, name, monthly_limit_kg, json.dumps(category_limits or {}), alert_threshold_pct, hard_cap_kg))
    c.commit(); cid = cur.lastrowid; c.close(); return cid

def get_active_budget(user_id: int) -> Optional[Dict[str, Any]]:
    c = _conn()
    row = c.execute("SELECT * FROM carbon_budgets WHERE user_id=? AND is_active=1", (user_id,)).fetchone()
    c.close()
    if row:
        d = dict(row); d["category_limits"] = json.loads(d["category_limits"]); return d
    return None

def get_budget_by_id(budget_id: int) -> Optional[Dict[str, Any]]:
    c = _conn(); row = c.execute("SELECT * FROM carbon_budgets WHERE id=?", (budget_id,)).fetchone(); c.close()
    if row:
        d = dict(row); d["category_limits"] = json.loads(d["category_limits"]); return d
    return None

def update_budget(budget_id: int, **kwargs):
    c = _conn()
    allowed = {"name", "monthly_limit_kg", "category_limits", "alert_threshold_pct", "hard_cap_kg", "is_active"}
    sets, vals = [], []
    for k, v in kwargs.items():
        if k in allowed:
            if k == "category_limits" and isinstance(v, dict): v = json.dumps(v)
            sets.append(f"{k}=?"); vals.append(v)
    if sets:
        sets.append("updated_at=datetime('now')"); vals.append(budget_id)
        c.execute(f"UPDATE carbon_budgets SET {','.join(sets)} WHERE id=?", vals)
        c.commit()
    c.close()

# ── Spending Log ───────────────────────────────────────────────────────

def log_spending(user_id: int, category: str, activity: str, co2_kg: float,
                  budget_id: Optional[int] = None, source: str = "manual",
                  log_date: Optional[str] = None, metadata: Optional[Dict] = None) -> int:
    if log_date is None: log_date = datetime.utcnow().strftime("%Y-%m-%d")
    c = _conn()
    cur = c.execute(
        "INSERT INTO carbon_spending_log (user_id,budget_id,log_date,category,activity,co2_kg,source,metadata) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, budget_id, log_date, category, activity, co2_kg, source, json.dumps(metadata or {})))
    c.commit(); lid = cur.lastrowid; c.close(); return lid

def get_spending_logs(user_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None,
                       category: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    c = _conn()
    q = "SELECT * FROM carbon_spending_log WHERE user_id=?"; p = [user_id]
    if start_date: q += " AND log_date>=?"; p.append(start_date)
    if end_date: q += " AND log_date<=?"; p.append(end_date)
    if category: q += " AND category=?"; p.append(category)
    q += " ORDER BY log_date DESC, created_at DESC LIMIT ?"; p.append(limit)
    rows = [dict(r) for r in c.execute(q, p).fetchall()]; c.close(); return rows

def get_monthly_spending(user_id: int, year: int, month: int) -> Dict[str, float]:
    c = _conn()
    prefix = f"{year}-{month:02d}"
    rows = c.execute(
        "SELECT category, SUM(co2_kg) as total FROM carbon_spending_log WHERE user_id=? AND log_date LIKE ? GROUP BY category",
        (user_id, f"{prefix}%")).fetchall()
    c.close(); return {r["category"]: round(r["total"], 2) for r in rows}

def get_daily_spending(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
    c = _conn()
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = c.execute(
        "SELECT log_date, SUM(co2_kg) as total_kg, COUNT(*) as entries FROM carbon_spending_log WHERE user_id=? AND log_date>=? GROUP BY log_date ORDER BY log_date",
        (user_id, start)).fetchall()
    c.close(); return [dict(r) for r in rows]

def get_total_monthly_spent(user_id: int, year: Optional[int] = None, month: Optional[int] = None) -> float:
    if year is None or month is None:
        now = datetime.utcnow(); year, month = now.year, now.month
    c = _conn()
    prefix = f"{year}-{month:02d}"
    row = c.execute("SELECT COALESCE(SUM(co2_kg),0) as total FROM carbon_spending_log WHERE user_id=? AND log_date LIKE ?",
                     (user_id, f"{prefix}%")).fetchone()
    c.close(); return round(row["total"], 2)

# ── Alerts ─────────────────────────────────────────────────────────────

def create_alert(user_id: int, budget_id: int, alert_type: str, message: str, threshold_pct: float = 0) -> int:
    c = _conn()
    cur = c.execute(
        "INSERT INTO carbon_budget_alerts (user_id,budget_id,alert_type,message,threshold_pct) VALUES (?,?,?,?,?)",
        (user_id, budget_id, alert_type, message, threshold_pct))
    c.commit(); aid = cur.lastrowid; c.close(); return aid

def get_unread_alerts(user_id: int) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM carbon_budget_alerts WHERE user_id=? AND is_read=0 ORDER BY created_at DESC", (user_id,)).fetchall()]
    c.close(); return rows

def mark_alert_read(alert_id: int):
    c = _conn(); c.execute("UPDATE carbon_budget_alerts SET is_read=1 WHERE id=?", (alert_id,)); c.commit(); c.close()

# ── History ────────────────────────────────────────────────────────────

def save_monthly_history(user_id: int, budget_id: int, month: str, total_spent: float,
                          monthly_limit: float, category_breakdown: Dict):
    savings = max(0, monthly_limit - total_spent)
    c = _conn()
    c.execute(
        "INSERT INTO carbon_budget_history (user_id,budget_id,month,total_spent_kg,monthly_limit_kg,savings_kg,category_breakdown) VALUES (?,?,?,?,?,?,?)",
        (user_id, budget_id, month, total_spent, monthly_limit, savings, json.dumps(category_breakdown)))
    c.commit(); c.close()

def get_budget_history(user_id: int, limit: int = 12) -> List[Dict[str, Any]]:
    c = _conn()
    rows = [dict(r) for r in c.execute(
        "SELECT * FROM carbon_budget_history WHERE user_id=? ORDER BY month DESC LIMIT ?", (user_id, limit)).fetchall()]
    for r in rows: r["category_breakdown"] = json.loads(r["category_breakdown"])
    c.close(); return rows

# ── Seed ───────────────────────────────────────────────────────────────

def seed_default_categories() -> Dict[str, Dict[str, Any]]:
    return {
        "transport": {"label": "🚗 Transport", "default_limit_kg": 150, "color": "#3b82f6"},
        "energy": {"label": "⚡ Home Energy", "default_limit_kg": 120, "color": "#f59e0b"},
        "diet": {"label": "🥗 Diet & Food", "default_limit_kg": 100, "color": "#22c55e"},
        "flights": {"label": "✈️ Flights", "default_limit_kg": 80, "color": "#ef4444"},
        "shopping": {"label": "🛍️ Shopping", "default_limit_kg": 50, "color": "#8b5cf6"},
        "waste": {"label": "♻️ Waste", "default_limit_kg": 30, "color": "#06b6d4"},
        "water": {"label": "💧 Water", "default_limit_kg": 20, "color": "#0ea5e9"},
        "digital": {"label": "💻 Digital", "default_limit_kg": 25, "color": "#ec4899"},
    }

ACTIVITY_CO2_DATABASE = {
    "transport": {
        "Drive car (per km)": 0.21, "Bus ride (per km)": 0.089, "Train (per km)": 0.041,
        "Bike (per km)": 0.0, "Walk (per km)": 0.0, "Motorcycle (per km)": 0.113,
        "EV charge (per km)": 0.053, "Rideshare (per km)": 0.15,
    },
    "energy": {
        "Electricity 1 kWh": 0.42, "Natural gas 1 kWh": 0.18, "Heating oil 1L": 2.52,
        "Solar generation 1 kWh": -0.42, "AC 1 hour": 0.9, "Heater 1 hour": 1.5,
        "LED bulb 1 hour": 0.01, "Laptop 1 hour": 0.05, "Fridge 1 day": 1.2,
    },
    "diet": {
        "Beef meal": 7.2, "Pork meal": 3.8, "Chicken meal": 2.5, "Fish meal": 3.1,
        "Vegetarian meal": 1.7, "Vegan meal": 0.9, "Dairy milk 1L": 1.5,
        "Plant milk 1L": 0.3, "Coffee 1 cup": 0.28, "Local produce 1kg": 0.4,
        "Imported produce 1kg": 2.1,
    },
    "flights": {
        "Short-haul flight (<3h)": 255, "Medium-haul (3-6h)": 550, "Long-haul (>6h)": 1100,
        "Domestic flight": 350, "International economy": 900, "Private jet (per hour)": 2500,
    },
    "shopping": {
        "New clothing item": 8.0, "Electronics device": 50.0, "Furniture piece": 40.0,
        "Second-hand item": 1.5, "Recycled material item": 3.0,
    },
    "waste": {
        "Landfill bag 1kg": 2.5, "Recycled bag 1kg": 0.5, "Composted 1kg": 0.1,
        "E-waste 1kg": 15.0, "Food waste 1kg": 3.5,
    },
    "water": {
        "Shower 10min": 0.8, "Bath": 2.5, "Toilet flush": 0.3,
        "Dish washing 15min": 1.2, "Laundry load": 2.0, "Garden watering 30min": 5.0,
    },
    "digital": {
        "Streaming 1 hour": 0.12, "Video call 1 hour": 0.15, "Gaming 1 hour": 0.1,
        "Cloud storage 1GB/month": 0.02, "AI query": 0.004, "Email sent": 0.004,
    },
}

init_budget_db()
