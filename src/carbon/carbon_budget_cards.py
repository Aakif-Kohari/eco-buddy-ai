"""
Carbon Budget Planner — Card Components
=========================================
Reusable Streamlit UI cards for budget display, spending entry, alerts, and suggestions.
"""

import streamlit as st
from typing import Dict, Any, List, Optional

CARBON_CSS = """
<style>
    .budget-card{background:linear-gradient(145deg,rgba(255,255,255,0.95),rgba(240,255,240,0.8));border:1px solid rgba(34,197,94,0.18);border-radius:16px;padding:24px;margin-bottom:14px;box-shadow:0 8px 28px rgba(0,0,0,0.05);position:relative;overflow:hidden;transition:transform 0.2s ease;}
    .budget-card:hover{transform:translateY(-3px);box-shadow:0 14px 40px rgba(34,197,94,0.12);}
    .budget-card::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#22c55e,#86efac,#16a34a);}
    .budget-big-num{font-size:42px;font-weight:900;color:#111827;line-height:1;}
    .budget-label{font-size:13px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;}
    .category-bar{margin:8px 0;border-radius:12px;overflow:hidden;background:rgba(0,0,0,0.04);height:10px;}
    .category-fill{height:100%;border-radius:inherit;transition:width 0.5s ease;}
    .alert-banner{padding:14px 18px;border-radius:12px;margin-bottom:10px;display:flex;align-items:center;gap:10px;font-weight:600;font-size:14px;}
    .alert-danger{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.25);color:#dc2626;}
    .alert-warning{background:rgba(234,179,8,0.1);border:1px solid rgba(234,179,8,0.25);color:#ca8a04;}
    .alert-success{background:rgba(34,197,94,0.1);border:1px solid rgba(34,197,94,0.25);color:#16a34a;}
    .tip-card{padding:16px;border-radius:12px;background:linear-gradient(135deg,rgba(59,130,246,0.06),rgba(139,92,246,0.04));border:1px solid rgba(59,130,246,0.15);margin-bottom:10px;}
    .tip-card .tip-cat{font-weight:700;color:#3b82f6;font-size:13px;text-transform:uppercase;}
    .tip-card .tip-text{color:#374151;font-size:14px;margin-top:4px;}
    .stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:12px 0;}
    .stat-box{padding:16px;border-radius:12px;background:rgba(255,255,255,0.7);border:1px solid rgba(0,0,0,0.06);text-align:center;}
    .stat-box .stat-val{font-size:24px;font-weight:800;}
    .stat-box .stat-lbl{font-size:11px;color:#6b7280;font-weight:600;text-transform:uppercase;margin-top:4px;}
    @media(prefers-color-scheme:dark){
        .budget-card{background:linear-gradient(145deg,rgba(15,23,42,0.92),rgba(10,30,15,0.75));border-color:rgba(74,222,128,0.18);}
        .budget-big-num,.stat-box .stat-val{color:#f1f5f9;}
        .category-bar{background:rgba(148,163,184,0.12);}
        .stat-box{background:rgba(30,41,59,0.7);border-color:rgba(148,163,184,0.12);}
        .tip-card{background:linear-gradient(135deg,rgba(30,41,59,0.8),rgba(20,28,50,0.6));border-color:rgba(96,165,250,0.2);}
        .tip-card .tip-text{color:#e2e8f0;}
        .alert-danger{background:rgba(239,68,68,0.15);color:#fca5a5;}
        .alert-warning{background:rgba(234,179,8,0.15);color:#fde047;}
        .alert-success{background:rgba(34,197,94,0.15);color:#86efac;}
    }
</style>
"""

def inject_css():
    st.markdown(CARBON_CSS, unsafe_allow_html=True)

def render_budget_overview_card(summary: Dict[str, Any]):
    pct = summary.get("pct_used", 0)
    spent = summary.get("monthly_spent", 0)
    limit = summary.get("monthly_limit", 500)
    remaining = summary.get("remaining", 0)
    bar_color = "#ef4444" if pct >= 100 else "#f59e0b" if pct >= 80 else "#22c55e"
    st.markdown(f"""
    <div class="budget-card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">
            <div>
                <span class="budget-label">This Month's Carbon Budget</span>
                <div class="budget-big-num" style="color:{bar_color};">{spent:.1f} <span style="font-size:18px;color:#6b7280;">/ {limit:.0f} kg</span></div>
            </div>
            <div style="text-align:right;">
                <span class="budget-label">Remaining</span>
                <div class="budget-big-num">{remaining:.1f} <span style="font-size:16px;color:#6b7280;">kg</span></div>
            </div>
        </div>
        <div class="category-bar" style="margin-top:16px;">
            <div class="category-fill" style="width:{min(100,pct):.1f}%;background:{bar_color};"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:6px;">
            <span style="font-size:12px;color:#6b7280;">{pct:.0f}% used</span>
            <span style="font-size:12px;color:#6b7280;">{100-pct:.0f}% left</span>
        </div>
    </div>""", unsafe_allow_html=True)

def render_stat_grid(stats: Dict[str, Any]):
    icons = {"daily_avg": "📅", "projected_month": "📈", "daily_budget": "🎯", "on_track": "✅"}
    colors = {"daily_avg": "#3b82f6", "projected_month": "#f59e0b", "daily_budget": "#22c55e", "on_track": "#16a34a"}
    html = '<div class="stat-grid">'
    for key, val in stats.items():
        icon = icons.get(key, "📊")
        color = colors.get(key, "#111827")
        label = key.replace("_", " ").title()
        display_val = "On Track ✅" if key == "on_track" else (val if not isinstance(val, bool) else "Yes" if val else "No")
        html += f'<div class="stat-box"><div class="stat-val" style="color:{color};">{display_val}</div><div class="stat-lbl">{icon} {label}</div></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

def render_category_card(cat: str, label: str, spent: float, limit: float, color: str = "#22c55e"):
    pct = (spent / limit * 100) if limit > 0 else 0
    status_color = "#ef4444" if pct >= 100 else "#f59e0b" if pct >= 80 else color
    st.markdown(f"""
    <div style="padding:14px;border-radius:12px;border:1px solid rgba(0,0,0,0.06);background:rgba(255,255,255,0.6);margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <span style="font-weight:700;font-size:14px;">{label}</span>
            <span style="font-weight:800;color:{status_color};">{spent:.1f} / {limit:.0f} kg</span>
        </div>
        <div class="category-bar" style="margin-top:6px;">
            <div class="category-fill" style="width:{min(100,pct):.1f}%;background:{status_color};"></div>
        </div>
        <div style="font-size:11px;color:#6b7280;margin-top:2px;">{pct:.0f}% used — {max(0,limit-spent):.1f} kg remaining</div>
    </div>""", unsafe_allow_html=True)

def render_alert(alert: Dict[str, Any]):
    atype = alert.get("alert_type", "info")
    cls = "alert-danger" if atype == "hard_cap" else "alert-warning" if atype == "threshold" else "alert-success"
    icon = "⛔" if atype == "hard_cap" else "⚠️" if atype == "threshold" else "ℹ️"
    st.markdown(f'<div class="alert-banner {cls}">{icon} {alert.get("message","")}</div>', unsafe_allow_html=True)

def render_suggestion_card(suggestion: Dict[str, Any]):
    severity_color = "#ef4444" if suggestion["severity"] == "high" else "#f59e0b"
    st.markdown(f"""
    <div class="tip-card">
        <div class="tip-cat" style="color:{severity_color};">{suggestion['category'].upper()} — {suggestion['pct']:.0f}% used</div>
        <div class="tip-text">{suggestion['tip']}</div>
    </div>""", unsafe_allow_html=True)

def render_spending_log_form(categories: Dict[str, Dict], activity_db: Dict[str, Dict[str, float]]):
    with st.form("spend_log", clear_on_submit=True):
        st.subheader("📝 Log Carbon Spending")
        c1, c2, c3 = st.columns(3)
        with c1:
            cat = st.selectbox("Category", list(categories.keys()),
                               format_func=lambda x: categories[x]["label"])
        with c2:
            activities = list(activity_db.get(cat, {}).keys())
            activity = st.selectbox("Activity", activities if activities else ["No activities"])
        with c3:
            default_co2 = activity_db.get(cat, {}).get(activity, 0) if activity in activity_db.get(cat, {}) else 1.0
            co2 = st.number_input("CO₂ (kg)", min_value=0.0, value=float(default_co2), step=0.1)
        log_date = st.date_input("Date")
        note = st.text_input("Note (optional)", placeholder="e.g., commute to office")
        submitted = st.form_submit_button("✅ Log Spending", use_container_width=True)
    return {"submitted": submitted, "category": cat, "activity": activity, "co2_kg": co2,
            "log_date": log_date.strftime("%Y-%m-%d"), "note": note}

def render_budget_setup_form(default_limit: float = 500.0):
    with st.form("budget_setup"):
        st.subheader("🎯 Set Your Monthly Carbon Budget")
        limit = st.slider("Monthly limit (kg CO₂)", min_value=100.0, max_value=5000.0, value=default_limit, step=50.0)
        threshold = st.slider("Alert threshold (%)", min_value=50, max_value=95, value=80, step=5)
        st.caption("You'll receive alerts when your spending reaches this percentage of your budget.")
        submitted = st.form_submit_button("🚀 Create Budget", use_container_width=True)
    return {"submitted": submitted, "monthly_limit_kg": limit, "alert_threshold_pct": threshold}
