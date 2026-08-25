"""
Eco Impact Time Capsule — Card Components
============================================
Reusable Streamlit cards for capsule display, comparison, and timeline.
"""

import streamlit as st
from typing import Dict, Any, List, Optional

CAPSULE_CSS = """
<style>
    .capsule-card{background:linear-gradient(145deg,rgba(255,255,255,0.95),rgba(240,250,255,0.85));border:1px solid rgba(99,102,241,0.18);border-radius:18px;padding:24px;margin-bottom:14px;box-shadow:0 8px 30px rgba(99,102,241,0.08);position:relative;overflow:hidden;transition:transform 0.2s ease;}
    .capsule-card:hover{transform:translateY(-3px);box-shadow:0 14px 40px rgba(99,102,241,0.12);}
    .capsule-card.sealed{border-left:5px solid #f59e0b;}
    .capsule-card.opened{border-left:5px solid #22c55e;opacity:0.85;}
    .capsule-card.ready{border-left:5px solid #ef4444;animation:pulse-border 2s infinite;}
    @keyframes pulse-border{0%,100%{border-left-color:#ef4444;}50%{border-left-color:#f97316;}}
    .capsule-title{font-size:18px;font-weight:800;margin:0 0 4px;}
    .capsule-meta{font-size:12px;color:#6b7280;font-weight:500;}
    .capsule-mood{font-size:28px;}
    .compare-card{background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(168,85,247,0.04));border:1px solid rgba(99,102,241,0.15);border-radius:14px;padding:18px;margin-bottom:10px;}
    .compare-metric{display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(0,0,0,0.05);}
    .compare-metric:last-child{border-bottom:none;}
    .delta-up{color:#16a34a;font-weight:700;}
    .delta-down{color:#ef4444;font-weight:700;}
    .delta-same{color:#6b7280;font-weight:600;}
    .milestone-badge{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:20px;background:linear-gradient(135deg,rgba(245,158,11,0.1),rgba(245,158,11,0.05));border:1px solid rgba(245,158,11,0.2);font-size:13px;font-weight:700;margin:4px;}
    .timeline-dot{width:14px;height:14px;border-radius:50%;display:inline-block;margin-right:8px;}
    .timeline-line{border-left:3px solid rgba(99,102,241,0.2);margin-left:6px;padding-left:20px;margin-top:-4px;padding-top:4px;padding-bottom:12px;}
    .growth-bar{height:8px;border-radius:999px;background:rgba(0,0,0,0.05);overflow:hidden;margin:4px 0;}
    .growth-fill{height:100%;border-radius:inherit;background:linear-gradient(90deg,#6366f1,#a855f7);}
    @media(prefers-color-scheme:dark){
        .capsule-card{background:linear-gradient(145deg,rgba(15,23,42,0.92),rgba(20,18,42,0.75));border-color:rgba(129,140,248,0.18);color:#f1f5f9;}
        .capsule-meta{color:#9ca3af;}
        .compare-card{background:linear-gradient(135deg,rgba(30,27,75,0.6),rgba(40,20,70,0.4));}
        .compare-metric{border-bottom-color:rgba(148,163,184,0.12);}
        .milestone-badge{background:linear-gradient(135deg,rgba(245,158,11,0.15),rgba(245,158,11,0.05));}
    }
</style>
"""

def inject_css():
    st.markdown(CAPSULE_CSS, unsafe_allow_html=True)

def render_capsule_card(capsule: Dict[str, Any], show_actions: bool = True):
    opened = capsule.get("opened", False)
    status_cls = "opened" if opened else "sealed"
    mood_emoji = {"amazing":"🤩","great":"😊","good":"🙂","neutral":"😐","struggling":"😔","terrible":"😢"}.get(capsule.get("mood","neutral"),"😐")
    open_date = capsule.get("open_date", "")
    st.markdown(f"""
    <div class="capsule-card {status_cls}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <div class="capsule-title">{'📂' if opened else '🔒'} {capsule.get('title','Time Capsule')}</div>
                <div class="capsule-meta">Created {capsule.get('created_at','')[:10]} · {capsule.get('capsule_type','snapshot').replace('_',' ').title()}</div>
                {f'<div class="capsule-meta">📅 Opens: {open_date}</div>' if open_date and not opened else ''}
            </div>
            <div class="capsule-mood">{mood_emoji}</div>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:12px;">
            <div style="text-align:center;"><div style="font-size:20px;font-weight:800;color:#6366f1;">{capsule.get('eco_score',0)}</div><div style="font-size:11px;color:#6b7280;">Eco Score</div></div>
            <div style="text-align:center;"><div style="font-size:20px;font-weight:800;color:#22c55e;">{capsule.get('carbon_kg',0):.0f}</div><div style="font-size:11px;color:#6b7280;">kg CO₂</div></div>
            <div style="text-align:center;"><div style="font-size:20px;font-weight:800;color:#f59e0b;">{capsule.get('streak_days',0)}</div><div style="font-size:11px;color:#6b7280;">Streak</div></div>
            <div style="text-align:center;"><div style="font-size:20px;font-weight:800;color:#ec4899;">{capsule.get('badges_earned',0)}</div><div style="font-size:11px;color:#6b7280;">Badges</div></div>
            <div style="text-align:center;"><div style="font-size:20px;font-weight:800;color:#8b5cf6;">{capsule.get('challenges_done',0)}</div><div style="font-size:11px;color:#6b7280;">Challenges</div></div>
        </div>
        {f'<div style="margin-top:10px;font-size:13px;color:#6b7280;font-style:italic;">"{capsule.get("notes","")}"</div>' if capsule.get('notes') else ''}
    </div>""", unsafe_allow_html=True)

def render_comparison(comparison: Dict[str, Any]):
    comp = comparison.get("comparison", {})
    a_label = comparison.get("capsule_a", {}).get("title", "A")[:20]
    b_label = comparison.get("capsule_b", {}).get("title", "B")[:20]
    st.markdown(f'<div class="compare-card">', unsafe_allow_html=True)
    st.markdown(f"**{a_label}** → **{b_label}** ({comp.get('days_between',0)} days apart)")
    for key, data in comp.items():
        if key == "days_between":
            continue
        direction = data.get("direction", "same")
        delta = data.get("delta", 0)
        arrow = "↑" if direction == "up" else "↓" if direction == "down" else "→"
        cls = "delta-up" if direction == "up" else "delta-down" if direction == "down" else "delta-same"
        label = key.replace("_", " ").title()
        # For carbon_kg, "down" is good
        if key == "carbon_kg" and direction == "down":
            cls = "delta-up"
        elif key == "carbon_kg" and direction == "up":
            cls = "delta-down"
        st.markdown(f"""<div class="compare-metric">
            <span style="font-weight:600;">{label}</span>
            <span>{data['a']} → {data['b']} <span class="{cls}">{arrow} {abs(delta)}</span></span>
        </div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def render_milestone(milestone: Dict[str, Any]):
    st.markdown(f'<div class="milestone-badge">{milestone.get("title","🏆")}</div>', unsafe_allow_html=True)

def render_timeline_item(item: Dict[str, Any]):
    opened = item.get("opened", False)
    dot_color = "#22c55e" if opened else "#f59e0b"
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
        <div class="timeline-dot" style="background:{dot_color};"></div>
        <div>
            <span style="font-weight:700;font-size:14px;">{item.get('mood','')} {item.get('title','')}</span>
            <span style="font-size:12px;color:#6b7280;margin-left:8px;">{item.get('date','')}</span>
            <span style="font-size:12px;color:#6366f1;font-weight:600;margin-left:8px;">Score: {item.get('eco_score',0)}</span>
        </div>
    </div>""", unsafe_allow_html=True)

def render_growth_card(growth: Dict[str, Any]):
    if not growth.get("has_growth"):
        st.info("Create at least 2 capsules to see your growth!")
        return
    score_delta = growth["score_change"]
    carbon_delta = growth["carbon_change"]
    score_cls = "delta-up" if score_delta >= 0 else "delta-down"
    carbon_cls = "delta-up" if carbon_delta <= 0 else "delta-down"
    st.markdown(f"""
    <div class="capsule-card" style="border-left:5px solid #6366f1;">
        <div class="capsule-title">📈 Your Growth Journey</div>
        <div class="capsule-meta">{growth['first_date']} → {growth['latest_date']} · {growth['total_capsules']} capsules</div>
        <div style="display:flex;gap:24px;margin-top:12px;">
            <div>
                <div style="font-size:11px;color:#6b7280;font-weight:600;">ECO SCORE</div>
                <div style="font-size:16px;font-weight:800;">{growth['first_score']} → {growth['latest_score']}</div>
                <div class="{score_cls}" style="font-size:14px;font-weight:700;">{'+' if score_delta>=0 else ''}{score_delta}</div>
            </div>
            <div>
                <div style="font-size:11px;color:#6b7280;font-weight:600;">CARBON (kg)</div>
                <div style="font-size:16px;font-weight:800;">{growth['first_carbon']:.0f} → {growth['latest_carbon']:.0f}</div>
                <div class="{carbon_cls}" style="font-size:14px;font-weight:700;">{'+' if carbon_delta>=0 else ''}{carbon_delta}</div>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

def render_create_form():
    with st.form("create_capsule", clear_on_submit=True):
        st.subheader("📸 Create New Time Capsule")
        title = st.text_input("Capsule Title", max_chars=60, placeholder="e.g., August 2026 Eco Snapshot")
        c1, c2 = st.columns(2)
        with c1:
            capsule_type = st.selectbox("Type", ["snapshot", "monthly", "goal", "challenge", "newyear"])
            mood = st.selectbox("Current Mood", ["amazing", "great", "good", "neutral", "struggling", "terrible"])
        with c2:
            eco_score = st.slider("Your Eco Score", 0, 100, 50)
            carbon_kg = st.number_input("Monthly Carbon (kg)", min_value=0.0, value=400.0, step=10.0)
        c3, c4 = st.columns(2)
        with c3:
            streak_days = st.number_input("Current Streak (days)", min_value=0, value=0, step=1)
            badges = st.number_input("Badges Earned", min_value=0, value=0, step=1)
        with c4:
            challenges = st.number_input("Challenges Completed", min_value=0, value=0, step=1)
            open_date = st.date_input("Open Date (optional)", value=None)
        notes = st.text_area("Notes", max_chars=300, placeholder="What do you want to remember about this moment?")
        submitted = st.form_submit_button("📸 Seal Capsule", use_container_width=True)
    return {"submitted": submitted, "title": title, "capsule_type": capsule_type, "mood": mood,
            "eco_score": eco_score, "carbon_kg": carbon_kg, "streak_days": streak_days,
            "badges_earned": badges, "challenges_done": challenges, "notes": notes,
            "open_date": open_date.strftime("%Y-%m-%d") if open_date else None}
