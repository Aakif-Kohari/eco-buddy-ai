"""Streamlit UI for personalized sustainability action plans."""
from __future__ import annotations

import streamlit as st

from src.utils.action_plan import (
    Action, build_action_plan, calculate_plan_cost, calculate_plan_impact,
    estimate_time_to_complete, load_plan_progress, mark_action_complete,
    save_action_plan,
)
from src.ai.recommendations import generate_recommendations
from src.core.database import get_assessments
from src.carbon.emissions import calculate_footprint


def _assessment(row):
    if isinstance(row, dict):
        return row
    keys = ["id", "date", "transport", "distance", "electricity", "diet", "flights", "footprint", "eco_score", "trip_id", "factor_version"]
    return dict(zip(keys, row))


def _recommendation_actions(texts, contributors):
    actions = []
    category_by_name = {
        "transport": "Transportation", "electric": "Energy", "diet": "Food", "flight": "Transportation",
        "water": "Water", "waste": "Waste", "shopping": "Shopping",
    }
    for text in texts:
        lower = text.lower()
        category = next((v for k, v in category_by_name.items() if k in lower), "General lifestyle")
        if "electricity" in lower or "electronics" in lower or "led" in lower:
            category = "Energy"
        elif "meat" in lower or "plant" in lower or "meal" in lower:
            category = "Food"
        elif "flight" in lower or "air travel" in lower:
            category = "Transportation"
        elif "transport" in lower or "walk" in lower or "cycle" in lower or "public" in lower:
            category = "Transportation"
        digest = __import__("hashlib").sha256(text.strip().encode()).hexdigest()[:16]
        # The recommendation engine does not provide quantified savings, so leave impact unavailable.
        actions.append(Action.from_mapping({
            "id": f"rec-{digest}", "name": text, "category": category,
            "difficulty": "easy" if any(x in lower for x in ("turn off", "walk", "continue", "combine")) else "moderate",
            "time_to_complete": 1 if "turn off" in lower else 7,
            "description": "Existing EcoBuddy recommendation prioritized by your current assessment.",
        }))
    return actions


def main():
    st.set_page_config(page_title="Action Plan", page_icon="🌱", layout="wide")
    st.title("🌱 Personalized Sustainability Action Plan")
    user_id = st.session_state.get("user_id", 1)
    rows = get_assessments(user_id)
    if not rows:
        st.info("Complete a sustainability assessment first to generate a personalized action plan.")
        return
    latest = _assessment(rows[-1])
    total, contributors = calculate_footprint(latest.get("transport"), latest.get("distance", 0), latest.get("electricity", 0), latest.get("diet"), latest.get("flights", 0), latest.get("region", "Global"))
    st.metric("Current annual footprint", f"{total:,.0f} kg CO₂e")
    st.caption("Actions are prioritized from your existing EcoBuddy src.ai.recommendations. Savings are never invented when supporting data is unavailable.")

    _, recommendations = generate_recommendations(latest.get("transport"), latest.get("electricity", 0), latest.get("diet"), latest.get("flights", 0), contributors)
    actions = _recommendation_actions(recommendations, contributors)
    preferences = {"preferred_categories": st.multiselect("Preferred categories", sorted({a.category for a in actions}))}
    horizon = st.selectbox("Plan", ["top5", "top10", "30d", "90d"], format_func=lambda x: {"top5":"Top 5 actions", "top10":"Top 10 actions", "30d":"30-day plan", "90d":"90-day plan"}[x])
    if st.button("Regenerate plan", type="primary") or "action_plan" not in st.session_state:
        plan = build_action_plan(actions, contributors, preferences, horizon, user_id=user_id)
        st.session_state.action_plan = plan.to_dict()
        save_action_plan(plan)
    plan_data = st.session_state.action_plan
    impact = calculate_plan_impact(plan_data)
    cost = calculate_plan_cost(plan_data)
    time = estimate_time_to_complete(plan_data)
    c1, c2, c3 = st.columns(3)
    c1.metric("Estimated potential impact", impact["label"] if impact["available"] else "Unavailable")
    c2.metric("Estimated total cost", "Unavailable" if cost is None else f"{cost:,.0f}")
    c3.metric("Estimated time", "Unavailable" if time is None else f"{time:g} days")
    items = plan_data.get("items", [])
    progress = load_plan_progress(user_id, plan_data["id"])
    completed = sum(1 for i in items if progress.get(i["action_id"], i.get("status")) == "completed")
    st.progress(completed / len(items) if items else 0)
    st.caption(f"Progress: {completed}/{len(items)} completed")
    for item in items:
        status = progress.get(item["action_id"], item.get("status", "planned"))
        with st.container(border=True):
            st.subheader(f"#{item['position']} — {item['name']}")
            st.write(item.get("description", ""))
            a, b, c, d = st.columns(4)
            a.write(f"**Category:** {item['category']}")
            b.write(f"**Difficulty:** {item['difficulty'].title()}")
            c.write(f"**Impact:** {item['impact_label']}")
            d.write(f"**Priority:** {item['priority']:.3f}")
            st.caption(f"Why selected: {item['priority_reason']}")
            if item.get("dependencies"):
                st.caption("Dependencies: " + ", ".join(item["dependencies"]))
            if status != "completed":
                if st.button("Mark complete", key=f"complete-{plan_data['id']}-{item['action_id']}"):
                    mark_action_complete(user_id, plan_data["id"], item["action_id"], "completed")
                    st.rerun()
            else:
                st.success("Completed")

if __name__ == "__main__":
    main()
