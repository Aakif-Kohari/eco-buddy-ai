import streamlit as st
import plotly.graph_objects as go
import json
from styles.theme import apply_theme
from lifestyle_optimizer import generate_optimized_lifestyle_plan, LIFESTYLE_ACTIONS_CATALOG
from database import get_assessments

apply_theme()

st.title("🎯 Lifestyle Optimization Engine")
st.subheader("Personalized Action Plan for Target Carbon Reduction")

st.markdown("""
Rather than giving generic sustainability tips, the **Lifestyle Optimization Engine** calculates the **minimum set of high-impact lifestyle changes** required to reach your exact carbon reduction goal.
""")

# Fetch user's assessments if available
all_assessments = get_assessments()
latest_assessment = all_assessments[0] if all_assessments else None
previous_assessment = all_assessments[1] if len(all_assessments) > 1 else None

default_footprint = 3500.0
user_context = {"transport": "Car", "electricity": 250.0, "diet": "Non-Vegetarian", "flights": 2}

if not latest_assessment:
    st.warning("No assessment data found. Using default profile values. Please complete an assessment for truly personalized recommendations.")
else:
    if isinstance(latest_assessment, (list, tuple)) and len(latest_assessment) >= 9:
        user_context["transport"] = str(latest_assessment[3])
        user_context["electricity"] = float(latest_assessment[5])
        user_context["diet"] = str(latest_assessment[6])
        user_context["flights"] = int(latest_assessment[7])
        default_footprint = float(latest_assessment[8])

if latest_assessment and previous_assessment:
    prev_footprint = float(previous_assessment[8])
    diff = default_footprint - prev_footprint
    pct_change = (diff / prev_footprint) * 100 if prev_footprint > 0 else 0
    
    st.subheader("📈 Progress from Previous Assessment")
    if diff < 0:
        st.success(f"Great job! You've reduced your footprint by {abs(diff):,.0f} kg CO₂/yr ({abs(pct_change):.1f}%) compared to your previous assessment ({prev_footprint:,.0f} kg CO₂/yr).")
    elif diff > 0:
        st.warning(f"Your footprint increased by {diff:,.0f} kg CO₂/yr ({pct_change:.1f}%) compared to your previous assessment ({prev_footprint:,.0f} kg CO₂/yr). Let's work on getting it back down!")
    else:
        st.info("Your footprint is unchanged from your previous assessment.")
    st.markdown("---")

col1, col2 = st.columns([1, 1])

with col1:
    baseline_input = st.number_input(
        "Current Baseline Footprint (kg CO₂/year)",
        min_value=100.0,
        max_value=25000.0,
        value=float(default_footprint),
        step=100.0
    )

with col2:
    target_pct = st.slider(
        "Select Reduction Goal Target (%)",
        min_value=5,
        max_value=60,
        value=20,
        step=5,
        format="%d%%"
    )

plan = generate_optimized_lifestyle_plan(
    current_footprint_kg=baseline_input,
    target_reduction_pct=target_pct,
    context=user_context
)

st.markdown("---")

# Summary Metrics Banner
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("Baseline Footprint", f"{plan['baseline_footprint_kg']:,.0f} kg CO₂/yr")

with m2:
    st.metric("Target Reduction Goal", f"{plan['target_reduction_pct']}%", f"-{plan['required_reduction_kg']:,.0f} kg CO₂/yr")

with m3:
    st.metric("Estimated Savings", f"{plan['total_estimated_savings_kg']:,.0f} kg CO₂/yr", f"{plan['projected_reduction_pct']:.1f}% cut")

with m4:
    status_color = "green" if plan['is_target_achieved'] else "orange"
    status_label = "✅ Target Reached" if plan['is_target_achieved'] else "⚠️ Partial Plan"
    st.metric("Projected Footprint", f"{plan['projected_footprint_kg']:,.0f} kg CO₂/yr", status_label)

st.markdown("---")

# Goal Progress Indicator
st.subheader("🎯 Goal Progress")
progress_val = min(1.0, plan['projected_reduction_pct'] / plan['target_reduction_pct']) if plan['target_reduction_pct'] > 0 else 0.0
st.progress(progress_val)
if plan['is_target_achieved']:
    st.success(f"You've reached your {plan['target_reduction_pct']}% target with a projected reduction of {plan['projected_reduction_pct']:.1f}%!")
else:
    st.info(f"Projected reduction: {plan['projected_reduction_pct']:.1f}% / Target: {plan['target_reduction_pct']}%")

# Quick Wins
low_effort_actions = [a for a in plan['recommended_actions'] if a.get('effort') == 'Low']
if low_effort_actions:
    st.subheader("⚡ Quick Wins (Low Effort)")
    for act in low_effort_actions:
        st.write(f"✅ **{act['title']}** — Saves ~{act['annual_savings_kg']:,.0f} kg CO₂/yr")

# Lifestyle Impact Breakdown
st.subheader("🧩 Lifestyle Impact Breakdown")
categories = {}
for act in plan['recommended_actions']:
    cat = act['category']
    categories[cat] = categories.get(cat, 0) + act['annual_savings_kg']

if categories:
    num_cols = min(len(categories), 4)
    cat_cols = st.columns(num_cols)
    for i, (cat, saving) in enumerate(categories.items()):
        with cat_cols[i % num_cols]:
            st.metric(cat, f"-{saving:,.0f} kg")
else:
    st.info("No recommendations generated for breakdown.")

st.markdown("---")

# Visual Chart: Before vs After
st.subheader("📊 Projected Carbon Footprint Impact")

fig = go.Figure()
fig.add_trace(go.Bar(
    x=["Current Baseline", "Projected Footprint"],
    y=[plan['baseline_footprint_kg'], plan['projected_footprint_kg']],
    text=[f"{plan['baseline_footprint_kg']:,.0f} kg", f"{plan['projected_footprint_kg']:,.0f} kg"],
    textposition="auto",
    marker_color=["#e5484d", "#2e9e5b"]
))

fig.update_layout(
    title=f"Carbon Footprint Reduction ({plan['target_reduction_pct']}% Goal)",
    yaxis_title="Annual Emissions (kg CO₂/year)",
    template="plotly_white",
    height=400
)

st.plotly_chart(fig, use_container_width=True)

# Recommended Action Plan Cards
st.subheader(f"💡 Prioritized Action Plan ({plan['actions_count']} Steps)")

if not plan["recommended_actions"]:
    st.info("Your baseline is already extremely low or your target is 0%. No extra actions required!")
else:
    for impact_level in ["High", "Medium", "Low"]:
        impact_actions = [a for a in plan["recommended_actions"] if a.get("impact") == impact_level]
        if impact_actions:
            st.markdown(f"#### {impact_level} Impact")
            for act in impact_actions:
                with st.expander(f"{act['title']} — Saves ~{act['annual_savings_kg']:,.0f} kg CO₂/yr ({act['category']})", expanded=True):
                    c_a, c_b, c_c = st.columns([3, 1, 1])
                    with c_a:
                        st.write(f"**Description:** {act['description']}")
                    with c_b:
                        st.markdown(f"**Impact Level:** `{act['impact']}`")
                    with c_c:
                        st.markdown(f"**Effort Level:** `{act['effort']}`")

st.markdown("---")

# Export Action Plan
st.subheader("📄 Export Your Action Plan")
json_str = json.dumps(plan, indent=2)
st.download_button(
    label="Download Action Plan (JSON)",
    data=json_str,
    file_name="lifestyle_action_plan.json",
    mime="application/json",
    use_container_width=True
)
