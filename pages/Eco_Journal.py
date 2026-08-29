"""Page: Eco Journal — Daily eco reflections, mood tracking, and gratitude"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

st.set_page_config(page_title="Eco Journal", page_icon="📔", layout="wide")

from src.utils.eco_journal_service import (
    write_entry, get_calendar_data, get_mood_trend, get_tag_cloud,
    get_streak, ECO_ACTION_PRESETS,
)
from src.utils.eco_journal_db import get_entries, get_entry_by_date, get_journal_stats, get_random_prompt, MOOD_LABELS, ENERGY_LABELS

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("🔐 Please log in to use Eco Journal."); st.stop()

st.markdown("""
<div style="text-align:center;padding:20px 0 12px;background:linear-gradient(135deg,rgba(251,191,36,0.08),rgba(34,197,94,0.04));border-radius:16px;margin-bottom:20px;">
    <span style="font-size:36px;">📔</span>
    <h1 style="margin:6px 0 2px;font-size:28px;font-weight:900;">Eco Journal</h1>
    <p style="color:#6b7280;font-size:14px;">Reflect on your eco journey, track your mood, and build gratitude.</p>
</div>""", unsafe_allow_html=True)

stats = get_journal_stats(user_id)
streak = get_streak(user_id)
c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric("📝 Entries", stats["total_entries"])
with c2: st.metric("🔥 Streak", f"{streak} days")
with c3: st.metric("😊 Avg Mood", stats["avg_mood"])
with c4: st.metric("⚡ Avg Energy", stats["avg_energy"])
with c5: st.metric("🌱 Total Actions", stats["total_actions"])

st.markdown("---")
tab_write, tab_past, tab_calendar, tab_insights = st.tabs(["✍️ Write", "📖 Past Entries", "📅 Calendar", "📊 Insights"])

with tab_write:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    existing = get_entry_by_date(user_id, today)

    # Prompt of the day
    prompt = get_random_prompt()
    if prompt:
        st.info(f"💡 **Prompt:** {prompt['prompt_text']}")

    with st.form("journal_entry", clear_on_submit=True):
        title = st.text_input("Title", value=existing["title"] if existing else "", placeholder="e.g., A Green Monday")
        c1, c2 = st.columns(2)
        with c1:
            mood = st.slider("Mood", 1, 10, existing["mood"] if existing else 5)
            st.caption(MOOD_LABELS.get(mood, ""))
        with c2:
            energy = st.slider("Energy Level", 1, 10, existing["energy_level"] if existing else 5)
            st.caption(ENERGY_LABELS.get(energy, ""))
        content = st.text_area("Journal Entry", value=existing["content"] if existing else "",
                                height=180, placeholder="How was your eco day?")
        c3, c4 = st.columns(2)
        with c3:
            weather = st.text_input("Weather", value=existing["weather"] if existing else "", placeholder="☀️ Sunny")
            gratitude = st.text_input("Gratitude", value=existing["gratitude"] if existing else "",
                                       placeholder="What are you grateful for?")
        with c4:
            tags = st.text_input("Tags", value=", ".join(existing["tags"]) if existing else "",
                                  placeholder="nature, walking, vegan")
        # Eco actions
        st.markdown("**🌱 Eco Actions Done Today**")
        selected_actions = st.multiselect("Select actions", ECO_ACTION_PRESETS,
                                           default=existing["eco_actions_done"] if existing else [])
        entry_date = st.date_input("Date", value=datetime.strptime(today, "%Y-%m-%d"))
        submitted = st.form_submit_button("💾 Save Entry", use_container_width=True)

    if submitted:
        tags_list = [t.strip() for t in tags.split(",") if t.strip()]
        result = write_entry(user_id, title, content, mood, energy, selected_actions,
                              tags_list, weather, gratitude, entry_date.strftime("%Y-%m-%d"))
        if result["success"]:
            action = "Updated" if result.get("updated") else "Created"
            st.success(f"📔 {action}! {len(selected_actions)} eco actions logged.")
            st.rerun()

with tab_past:
    entries = get_entries(user_id, limit=20)
    if not entries:
        st.info("No entries yet. Start writing! ✍️")
    for e in entries:
        mood_emoji = MOOD_LABELS.get(e["mood"], "😐").split(" ")[0]
        with st.expander(f"{mood_emoji} {e['entry_date']} — {e.get('title', 'Untitled')}"):
            st.markdown(f"**Mood:** {MOOD_LABELS.get(e['mood'], '—')} | **Energy:** {ENERGY_LABELS.get(e['energy_level'], '—')}")
            if e.get("weather"): st.markdown(f"**Weather:** {e['weather']}")
            st.markdown(e["content"] if e["content"] else "*No content*")
            if e["eco_actions_done"]:
                st.markdown("**🌱 Eco Actions:**")
                for a in e["eco_actions_done"]:
                    st.markdown(f"- ✅ {a}")
            if e.get("gratitude"):
                st.markdown(f"**🙏 Gratitude:** {e['gratitude']}")
            if e["tags"]:
                st.markdown(f"**🏷️ Tags:** {', '.join(e['tags'])}")

with tab_calendar:
    now = datetime.utcnow()
    col_m, col_y = st.columns([2, 1])
    with col_y:
        year = st.number_input("Year", value=now.year, min_value=2024, max_value=2030)
        month = st.number_input("Month", value=now.month, min_value=1, max_value=12)
    with col_m:
        cal_data = get_calendar_data(user_id, year, month)
        mood_map = {d["entry_date"][-2:]: d["mood"] for d in cal_data}
        days_in_month = 31 if month in (1,3,5,7,8,10,12) else 30 if month != 2 else 28
        import calendar as cal
        cal_text = f"### 📅 {cal.month_name[month]} {year}\n\n"
        cal_text += "| Mon | Tue | Wed | Thu | Fri | Sat | Sun |\n|---|---|---|---|---|---|---|\n"
        first_day = datetime(year, month, 1).weekday()
        week = [""] * first_day
        for d in range(1, days_in_month + 1):
            dd = f"{d:02d}"
            mood = mood_map.get(dd)
            if mood:
                emoji = {1:"😢",2:"😔",3:"😐",4:"🙂",5:"😊",6:"😃",7:"😄",8:"🤩",9:"🥳",10:"🌟"}.get(mood, "📝")
                week.append(f"**{d}** {emoji}")
            else:
                week.append(str(d))
            if len(week) == 7:
                cal_text += "| " + " | ".join(week) + " |\n"
                week = []
        if week:
            while len(week) < 7: week.append("")
            cal_text += "| " + " | ".join(week) + " |\n"
        st.markdown(cal_text)

with tab_insights:
    trend = get_mood_trend(user_id)
    if trend:
        dates = [t["entry_date"] for t in trend]
        moods = [t["mood"] for t in trend]
        energies = [t["energy_level"] for t in trend]
        actions = [t["eco_actions_count"] for t in trend]
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=dates, y=moods, name="Mood", mode="lines+markers",
                                  line=dict(color="#f59e0b", width=3), marker=dict(size=6)), secondary_y=False)
        fig.add_trace(go.Scatter(x=dates, y=energies, name="Energy", mode="lines+markers",
                                  line=dict(color="#3b82f6", width=2), marker=dict(size=5)), secondary_y=False)
        fig.add_trace(go.Bar(x=dates, y=actions, name="Eco Actions",
                              marker_color="rgba(34,197,94,0.3)"), secondary_y=True)
        fig.update_layout(title="📈 Mood & Energy Trend", height=350,
                          font=dict(family="Inter"), paper_bgcolor="rgba(0,0,0,0)",
                          xaxis=dict(gridcolor="rgba(0,0,0,0.06)"), yaxis=dict(gridcolor="rgba(0,0,0,0.06)"),
                          legend=dict(orientation="h", y=-0.15, x=0.5, xanchor="center"))
        fig.update_yaxes(title_text="Score (1-10)", secondary_y=False)
        fig.update_yaxes(title_text="Actions", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Write some entries to see insights!")

    tags = get_tag_cloud(user_id)
    if tags:
        st.subheader("🏷️ Tag Cloud")
        fig_tag = go.Figure(go.Bar(
            y=list(tags.keys())[:15], x=list(tags.values())[:15], orientation="h",
            marker_color="rgba(34,197,94,0.6)", text=list(tags.values())[:15], textposition="auto"))
        fig_tag.update_layout(height=300, yaxis=dict(autorange="reversed"),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               font=dict(family="Inter"))
        st.plotly_chart(fig_tag, use_container_width=True)

st.markdown("---")
st.markdown('<div style="text-align:center;padding:14px;color:#9ca3af;font-size:13px;">📔 Eco Journal — Reflect, grow, and track your eco journey · Powered by EcoBuddy AI</div>', unsafe_allow_html=True)
