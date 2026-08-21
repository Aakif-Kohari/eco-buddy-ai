"""Recommendation feedback and personalization page.

This page is deliberately an adapter around the existing recommendation
engine. The ranking/persistence layer lives in recommendation_feedback.py so
it can be tested without Streamlit and reused elsewhere.
"""
from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from database import get_assessments
from emissions import calculate_footprint
from recommendations import generate_recommendations
from recommendation_feedback import (
    FEEDBACK_TYPES,
    DIFFICULTIES,
    RecommendationFeedbackStore,
    calculate_effectiveness,
    get_feedback_history,
    generate_personalized_order,
    normalize_recommendations,
    record_feedback,
    recommendation_analytics,
    reset_preferences,
)
from styles.theme import apply_theme


st.set_page_config(page_title="Recommendation Feedback", page_icon="🎯", layout="wide")
apply_theme()

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

st.title("🎯 Recommendation Feedback & Personalization")
st.caption("Tell EcoBuddy what works for you. Your feedback changes recommendation ordering without machine learning.")

store = RecommendationFeedbackStore()


def _latest_assessment(user: int):
    rows = get_assessments(user)
    if not rows:
        return None
    columns = [
        "id", "user_id", "date", "created_at", "transport", "distance",
        "electricity", "diet", "flights", "footprint", "eco_score",
        "trip_id", "factor_version",
    ]
    frame = pd.DataFrame(rows, columns=columns[: len(rows[0])])
    frame["created_at_sort"] = pd.to_datetime(frame["created_at"], errors="coerce")
    frame = frame.sort_values("created_at_sort", ascending=False, na_position="last")
    return frame.iloc[0].to_dict()


assessment = _latest_assessment(user_id)
if not assessment:
    st.info("Complete a carbon-footprint assessment before personalizing recommendations.")
    st.stop()

transport = assessment.get("transport") or "Walking"
distance = float(assessment.get("distance") or 0)
electricity = float(assessment.get("electricity") or 0)
diet = assessment.get("diet") or "Vegetarian"
flights = int(assessment.get("flights") or 0)

try:
    footprint, contributors = calculate_footprint(
        transport, distance, electricity, diet, flights, "Global"
    )
    _, generated = generate_recommendations(
        transport, electricity, diet, flights, contributors
    )
except Exception as exc:
    st.error(f"Could not generate recommendations from the latest assessment: {exc}")
    st.stop()

base_recommendations = normalize_recommendations(generated)
# Stable IDs allow feedback to survive reruns and recommendation list growth.
for item in base_recommendations:
    text = str(item.get("text", item.get("title", item.get("id", ""))))
    item["id"] = "recommendation-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

feedback = get_feedback_history(user_id, store=store)

# Record one impression per recommendation per browser session. This keeps
# repeated-display analytics meaningful without counting every Streamlit rerun.
seen_key = "recommendation_impressions_recorded"
recorded = st.session_state.setdefault(seen_key, set())
for item in base_recommendations:
    rid = str(item["id"])
    if rid not in recorded:
        store.record_impression(
            user_id, rid, str(item.get("category", "General")),
            str(item.get("difficulty", "moderate")),
        )
        recorded.add(rid)

impression_counts = store.get_impression_counts(user_id)
last_impressions = {
    str(item["id"]): store.get_last_impression(user_id, str(item["id"]))
    for item in base_recommendations
}
ranked_items = generate_personalized_order(
    base_recommendations, feedback,
    impression_counts=impression_counts,
    last_impressions=last_impressions,
)

with st.container(border=True):
    st.subheader("Your current baseline")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Annual footprint", f"{footprint:,.0f} kg CO₂")
    c2.metric("Transport", str(transport))
    c3.metric("Diet", str(diet))
    c4.metric("Flights", str(flights))

st.divider()

analytics = recommendation_analytics(feedback, impression_counts=impression_counts)
ac1, ac2, ac3, ac4 = st.columns(4)
ac1.metric("Feedback events", analytics["total_events"])
ac2.metric("Helpful rate", f"{analytics['helpfulness_rate'] * 100:.0f}%")
ac3.metric("Completion rate", f"{analytics['completion_rate'] * 100:.0f}%")
ac4.metric("Rejection rate", f"{analytics['rejection_rate'] * 100:.0f}%")

st.subheader("Personalized recommendations")
st.caption("Recommendations are ordered using environmental impact plus your feedback history. Numerical ranking weights are intentionally hidden.")

for position, item in enumerate(ranked_items, start=1):
    rid = str(item["id"])
    text = str(item.get("text", item.get("title", rid)))
    category = str(item.get("category", "General"))
    difficulty = str(item.get("difficulty", "moderate"))
    history = [event for event in feedback if event.recommendation_id == rid]
    last = history[-1].feedback_type if history else None
    completed = sum(event.feedback_type == "completed" for event in history)
    rejected = sum(event.feedback_type in {"not_helpful", "not_relevant", "already_doing", "too_difficult"} for event in history)

    with st.container(border=True):
        left, right = st.columns([4, 1])
        with left:
            st.markdown(f"### {position}. {text}")
            st.caption(f"Category: {category} · Difficulty: {difficulty}")
            if last == "completed":
                st.success("You completed this recommendation before.")
            elif rejected >= 2:
                st.warning("This recommendation has been rejected repeatedly and may be temporarily suppressed.")
            elif completed:
                st.info("Prioritized because you completed similar actions.")
        with right:
            st.metric("Past completions", completed)

        st.write("How useful is this recommendation?")
        cols = st.columns(7)
        actions = [
            ("👍", "helpful", "Helpful"),
            ("👎", "not_helpful", "Not helpful"),
            ("✅", "already_doing", "Already doing"),
            ("⚠️", "too_difficult", "Too difficult"),
            ("🚫", "not_relevant", "Not relevant"),
            ("🎉", "completed", "Completed"),
            ("×", "dismissed", "Dismiss"),
        ]
        for col, (icon, feedback_type, label) in zip(cols, actions):
            with col:
                if st.button(f"{icon} {label}", key=f"feedback-{rid}-{feedback_type}", use_container_width=True):
                    ok, message = record_feedback(
                        user_id, rid, category, feedback_type, difficulty, store=store
                    )
                    if ok:
                        st.success(message)
                        st.rerun()
                    st.warning(message)

        with st.expander("Set difficulty preference for this recommendation"):
            selected = st.selectbox(
                "Difficulty",
                DIFFICULTIES,
                index=DIFFICULTIES.index(difficulty) if difficulty in DIFFICULTIES else 1,
                key=f"difficulty-{rid}",
            )
            if selected != difficulty:
                st.caption("The selected difficulty is recorded with your next feedback event.")
                if st.button("Mark as helpful at this difficulty", key=f"difficulty-save-{rid}"):
                    ok, message = record_feedback(
                        user_id, rid, category, "helpful", selected, store=store
                    )
                    if ok:
                        st.success(message)
                        st.rerun()
                    st.warning(message)

st.divider()
st.subheader("📊 Personalization analytics")

history_df = pd.DataFrame([
    {
        "Recommendation": event.recommendation_id,
        "Category": event.category,
        "Feedback": event.feedback_type,
        "Difficulty": event.difficulty,
        "Timestamp": event.timestamp,
    }
    for event in feedback
])
if history_df.empty:
    st.info("No feedback yet. Rate a recommendation above to start personalization.")
else:
    tab1, tab2 = st.tabs(["History", "Category performance"])
    with tab1:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    with tab2:
        category_rows = []
        for category, stats in analytics["by_category"].items():
            category_rows.append({
                "Category": category,
                "Events": stats["events"],
                "Helpful": stats["helpful"],
                "Completed": stats["completed"],
                "Rejected": stats["rejected"],
                "Completion rate": stats["completion_rate"],
            })
        category_df = pd.DataFrame(category_rows)
        st.dataframe(category_df, use_container_width=True, hide_index=True)
        if not category_df.empty:
            chart_df = category_df.set_index("Category")[["Completed", "Rejected"]]
            st.bar_chart(chart_df)

st.divider()
with st.expander("Reset personalization"):
    st.warning("This permanently deletes your recommendation feedback history. Assessment data is not changed.")
    if st.checkbox("I understand that feedback history will be deleted", key="confirm-feedback-reset"):
        if st.button("Reset all recommendation preferences", type="secondary"):
            deleted = reset_preferences(user_id, store=store)
            st.success(f"Reset complete. Deleted {deleted} feedback event(s).")
            st.rerun()

st.caption("Personalization is deterministic and explainable. Completion is tracked as user feedback and is not treated as proof of a measured carbon reduction.")
