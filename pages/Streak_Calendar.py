import streamlit as st
import plotly.graph_objects as go
from datetime import date, timedelta
import calendar
from src.community import streak_calendar

st.set_page_config(page_title="Streak Calendar", layout="wide")

st.title("🌱 Your Activity Streak Calendar")
st.markdown("Track your daily eco-activities and watch your impact grow!")

# For now, use user_id = 1 as default (this usually depends on session state)
user_id = st.session_state.get("user_id", 1)
current_year = date.today().year

# Fetch data
activity_data = streak_calendar.get_daily_activity_counts(user_id, current_year)

# Compute stats
current_streak, longest_streak, active_days = streak_calendar.compute_streak_stats(activity_data)

# Layout Stats
st.subheader("Your Consistency")
col1, col2, col3 = st.columns(3)
col1.metric("Current Streak", f"{current_streak} days", delta="🔥" if current_streak > 0 else None)
col2.metric("Longest Streak", f"{longest_streak} days", delta="🏆" if longest_streak > 0 else None)
col3.metric("Total Active Days", f"{active_days} days")

st.markdown("---")

# Heatmap Data Preparation
# We need a 7 x 53 grid (Days of week x Weeks in year)
z_data = [[0 for _ in range(53)] for _ in range(7)]
hover_data = [["" for _ in range(53)] for _ in range(7)]

start_date = date(current_year, 1, 1)
end_date = date(current_year, 12, 31)
curr = start_date

# Plotly expects y to go from bottom to top, so index 0 = Sunday or Monday? 
# Usually, calendar puts Monday as 0 or Sunday as 0. We'll use Monday=0, Sunday=6
day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

while curr <= end_date:
    # ISO calendar returns (year, week_number, weekday)
    # week_number is 1-53, weekday is 1-7
    # For a simple grid, we can just calculate offset from start_date
    delta_days = (curr - start_date).days
    
    # We want week 0 to start on the week containing Jan 1st
    # But Jan 1st could be any day.
    # Let's align column 0 to the week of Jan 1st.
    col_idx = (delta_days + start_date.weekday()) // 7
    row_idx = curr.weekday() # 0-6
    
    intensity = 0
    total_actions = 0
    if curr in activity_data:
        intensity = activity_data[curr]["intensity_level"]
        total_actions = activity_data[curr]["total_actions"]
        
    # To match GitHub style, we often plot [0-6] where 0 is top. Plotly's default is 0 is bottom.
    # We will reverse the y-axis later.
    
    z_data[row_idx][col_idx] = intensity
    hover_data[row_idx][col_idx] = f"{curr}: {total_actions} actions (Level {intensity})"
    
    curr += timedelta(days=1)

# Heatmap Color Scale (GitHub-style greens)
colorscale = [
    [0.0, "#ebedf0"], # Level 0
    [0.25, "#9be9a8"], # Level 1
    [0.5, "#40c463"], # Level 2
    [0.75, "#30a14e"], # Level 3
    [1.0, "#216e39"]  # Level 4
]

fig = go.Figure(data=go.Heatmap(
    z=z_data,
    text=hover_data,
    hoverinfo="text",
    colorscale=colorscale,
    showscale=False,
    xgap=3,
    ygap=3,
    zmin=0,
    zmax=4
))

# Configure axes
fig.update_layout(
    title=f"Activity Map ({current_year})",
    xaxis=dict(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
    ),
    yaxis=dict(
        showgrid=False,
        zeroline=False,
        tickmode='array',
        tickvals=[0, 1, 2, 3, 4, 5, 6],
        ticktext=day_names,
        autorange='reversed' # Monday at top
    ),
    plot_bgcolor="white",
    height=250,
    margin=dict(t=40, l=40, r=40, b=40)
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.subheader("Freeze Token Milestones")
st.info("❄️ You earn Freeze Tokens for maintaining long streaks! These can save your streak on a missed day.")
st.markdown("""
- **14 Days**: 1 Freeze Token
- **30 Days**: 2 Freeze Tokens
- **100 Days**: Special Profile Badge + 5 Freeze Tokens
""")
