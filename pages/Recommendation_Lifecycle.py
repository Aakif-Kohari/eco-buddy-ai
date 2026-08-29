"""Streamlit dashboard for recommendation lifecycle and feedback learning."""
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from recommendation_lifecycle import (
    FeedbackReason,
    RecommendationFeedback,
    RecommendationLifecycleStore,
    RecommendationStatus,
    analyze_portfolio,
    build_profile,
    build_user_summary,
    create_event,
    export_lifecycle_json,
    export_signals_csv,
    recommendation_learning_disclaimer,
    utc_now,
)

st.set_page_config(page_title="Recommendation Lifecycle", page_icon="💬", layout="wide")

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

store = RecommendationLifecycleStore()
store.initialize()

st.title("💬 Recommendation Lifecycle & Feedback Learning")
st.caption(
    "Understand which recommendations are being seen, acted on, completed, "
    "and rated—without silently changing the recommendation engine."
)
st.info(recommendation_learning_disclaimer())

events = [dict(row) for row in store.fetch_events(int(user_id), limit=10_000)]
feedback = [dict(row) for row in store.fetch_feedback(int(user_id), limit=10_000)]
outcome_rows = [dict(row) for row in store.fetch_outcomes(int(user_id), limit=10_000)]
summary = build_user_summary(int(user_id), events, feedback)

metrics = st.columns(6)
metrics[0].metric("Recommendations", summary.recommendation_count)
metrics[1].metric("Shown", summary.shown_count)
metrics[2].metric("Started", summary.started_count)
metrics[3].metric("Completed", summary.completed_count)
metrics[4].metric("Dismissed", summary.dismissed_count)
metrics[5].metric("Avg. rating", "—" if summary.average_rating is None else f"{summary.average_rating:.1f}/5")

st.divider()

tab_overview, tab_feedback, tab_events, tab_export = st.tabs(
    ["Overview", "Give Feedback", "Lifecycle Events", "Export"]
)

with tab_overview:
    st.subheader("Learning signals")
    signals = analyze_portfolio(events, feedback)
    if signals:
        frame = pd.DataFrame([
            {
                "Recommendation": s.recommendation_id,
                "Learning score": s.learning_score,
                "Engagement": s.engagement_score,
                "Satisfaction": s.satisfaction_score,
                "Completion": s.completion_score,
                "Confidence": s.confidence_label,
                "Samples": s.sample_size,
            }
            for s in signals
        ])
        st.dataframe(frame, use_container_width=True, hide_index=True)
        st.caption("Scores are descriptive learning signals, not causal effectiveness claims.")
        if summary.improvement_areas:
            st.subheader("Areas to review")
            for item in summary.improvement_areas:
                st.warning(item)
    else:
        st.info("No recommendation lifecycle data has been recorded yet.")

    st.subheader("Record an interaction")
    with st.form("record_event"):
        rec_id = st.text_input("Recommendation ID", placeholder="rec_001")
        status = st.selectbox("Lifecycle status", [x.value for x in RecommendationStatus])
        category = st.text_input("Category (optional)")
        source = st.text_input("Source", value="recommendation_engine")
        submitted = st.form_submit_button("Record event")
        if submitted:
            try:
                if not rec_id.strip():
                    raise ValueError("Recommendation ID is required.")
                event = create_event(rec_id.strip(), int(user_id), status, category=category or None, source=source)
                if store.record_event(event):
                    st.success("Lifecycle event recorded.")
                    st.rerun()
                st.error("That event ID already exists.")
            except Exception as exc:
                st.error(str(exc))

with tab_feedback:
    st.subheader("Tell us whether a recommendation helped")
    rec_ids = store.recommendation_ids(int(user_id))
    with st.form("feedback_form"):
        selected = st.selectbox("Recommendation", rec_ids or ["rec_001"])
        rating = st.slider("Rating", 1, 5, 4)
        useful = st.radio("Was it useful?", [True, False], format_func=lambda x: "Yes" if x else "No", horizontal=True)
        reason = st.selectbox("Reason (optional)", ["None"] + [x.value for x in FeedbackReason])
        comment = st.text_area("Comment (optional)", max_chars=1000)
        submit = st.form_submit_button("Save feedback")
        if submit:
            try:
                store.record_feedback_form(
                    recommendation_id=selected,
                    user_id=int(user_id),
                    rating=float(rating),
                    useful=bool(useful),
                    reason=None if reason == "None" else reason,
                    comment=comment.strip() or None,
                )
                st.success("Thanks—your feedback is now included in the lifecycle analysis.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    if feedback:
        rows = []
        for row in feedback:
            rows.append({
                "Recommendation": row["recommendation_id"],
                "Rating": row["rating"],
                "Useful": "Yes" if row["useful"] else "No",
                "Reason": row["reason"] or "—",
                "Submitted": row["submitted_at"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab_events:
    if events:
        rows = []
        for row in events:
            rows.append({
                "Recommendation": row["recommendation_id"],
                "Status": row["status"].replace("_", " ").title(),
                "Category": row["category"] or "—",
                "Source": row["source"],
                "Occurred": row["occurred_at"],
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No lifecycle events recorded yet.")

    if outcome_rows:
        st.subheader("Observed outcomes")
        st.dataframe(pd.DataFrame(outcome_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No measured outcomes have been attached to recommendations yet.")

with tab_export:
    st.subheader("Local exports")
    st.caption("Exports contain only this user's recommendation lifecycle data and stay local to the browser session.")
    signals = analyze_portfolio(events, feedback)
    st.download_button(
        "Download lifecycle JSON",
        data=export_lifecycle_json(int(user_id), store),
        file_name="recommendation_lifecycle.json",
        mime="application/json",
    )
    st.download_button(
        "Download learning signals CSV",
        data=export_signals_csv(signals),
        file_name="recommendation_learning_signals.csv",
        mime="text/csv",
    )

    st.subheader("Latest learning snapshots")
    snapshots = store.latest_snapshots(int(user_id), limit=20)
    if snapshots:
        st.json(snapshots)
    else:
        st.caption("No snapshots saved yet.")

    if signals:
        if st.button("Save current learning snapshots"):
            for signal in signals:
                store.save_snapshot(int(user_id), signal)
            st.success(f"Saved {len(signals)} immutable snapshot(s).")
            st.rerun()

st.caption(f"Engine {__import__('recommendation_lifecycle').ENGINE_VERSION} · Schema {__import__('recommendation_lifecycle').SCHEMA_VERSION}")
