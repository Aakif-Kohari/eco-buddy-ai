"""Customizable dashboard widgets for EcoBuddy AI."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Mapping

import streamlit as st

from database import (
    get_assessments,
    get_dashboard_widget_preferences,
    save_dashboard_widget_preferences,
)

WIDGETS = OrderedDict(
    [
        ("summary", "🌍 Latest impact summary"),
        ("eco_score", "🏆 Eco score"),
        ("trend", "📈 Footprint trend"),
        ("activity", "🧭 Latest activity"),
        ("quick_tips", "💡 Quick eco tips"),
    ]
)
DEFAULT_WIDGETS = tuple(WIDGETS.keys())
SESSION_KEY = "dashboard_widget_preferences"


def normalize_widget_preferences(widget_ids: Iterable[str] | None) -> list[str]:
    """Return unique, known widget IDs in the canonical display order."""
    requested = set(widget_ids or [])
    return [widget_id for widget_id in WIDGETS if widget_id in requested]


def load_widget_preferences(user_id: int) -> list[str]:
    """Load a user's saved widgets, falling back to all dashboard widgets."""
    saved = get_dashboard_widget_preferences(user_id)
    if saved is None:
        return list(DEFAULT_WIDGETS)
    return normalize_widget_preferences(saved)


def render_widget_customizer(user_id: int) -> list[str]:
    """Render the sidebar widget picker and persist explicit saves."""
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = load_widget_preferences(user_id)

    with st.sidebar.expander("🧩 Dashboard widgets", expanded=False):
        st.caption("Choose which cards appear on your personal dashboard.")
        with st.form("dashboard_widget_preferences_form"):
            selected_labels = st.multiselect(
                "Visible widgets",
                options=list(WIDGETS.values()),
                default=[
                    WIDGETS[widget_id]
                    for widget_id in st.session_state[SESSION_KEY]
                    if widget_id in WIDGETS
                ],
                help="Your selection is restored the next time you sign in.",
            )
            save_clicked = st.form_submit_button(
                "Save dashboard",
                use_container_width=True,
            )

        if save_clicked:
            label_to_id = {label: widget_id for widget_id, label in WIDGETS.items()}
            selected_ids = normalize_widget_preferences(
                label_to_id[label] for label in selected_labels
            )
            if save_dashboard_widget_preferences(user_id, selected_ids):
                st.session_state[SESSION_KEY] = selected_ids
                st.success("Dashboard preferences saved.")
                st.rerun()
            else:
                st.error("Could not save dashboard preferences. Please try again.")

        if not st.session_state[SESSION_KEY]:
            st.info("No widgets selected. Use the picker above to add dashboard cards.")

    return list(st.session_state[SESSION_KEY])


def _assessment_rows_to_frame(rows: list[tuple]):
    import pandas as pd
    columns = [
        "id",
        "date",
        "transport",
        "distance",
        "electricity",
        "diet",
        "flights",
        "footprint",
        "eco_score",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    if not frame.empty:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["footprint"] = pd.to_numeric(frame["footprint"], errors="coerce")
        frame["eco_score"] = pd.to_numeric(frame["eco_score"], errors="coerce")
    return frame


def render_customizable_dashboard(user_id: int, selected_widgets: Iterable[str]) -> None:
    """Render the saved dashboard layout using the user's assessment history."""
    selected = normalize_widget_preferences(selected_widgets)
    if not selected:
        return

    st.markdown("<div class='section-header'>📊 My Dashboard</div>", unsafe_allow_html=True)
    st.caption("Personalized widgets based on your saved dashboard preferences.")

    frame = _assessment_rows_to_frame(get_assessments(user_id))
    latest: Mapping[str, object] | None = None
    if not frame.empty:
        latest = frame.iloc[0].to_dict()

    if "summary" in selected:
        with st.container(border=True):
            st.subheader("🌍 Latest impact summary")
            if latest:
                col1, col2, col3 = st.columns(3)
                col1.metric("Annual footprint", f"{float(latest['footprint']):,.0f} kg CO₂")
                col2.metric("Eco score", f"{int(latest['eco_score'])}/100")
                col3.metric("Primary transport", str(latest["transport"]))
            else:
                st.info("Complete your first carbon assessment to populate this widget.")

    if "eco_score" in selected:
        with st.container(border=True):
            st.subheader("🏆 Eco score")
            if latest:
                score = max(0, min(100, int(latest["eco_score"])))
                st.progress(score / 100, text=f"Current score: {score}/100")
                if score >= 85:
                    st.success("Eco Champion — excellent sustainable habits.")
                elif score >= 70:
                    st.info("Green Guardian — you are performing well.")
                elif score >= 50:
                    st.warning("Eco Learner — small changes can raise your score.")
                else:
                    st.error("High impact — focus on your largest emission source first.")
            else:
                st.info("Your eco score will appear after an assessment.")

    if "trend" in selected:
        with st.container(border=True):
            st.subheader("📈 Footprint trend")
            trend = frame.dropna(subset=["date", "footprint"]).sort_values("date")
            if len(trend) >= 2:
                import plotly.express as px
                figure = px.line(
                    trend,
                    x="date",
                    y="footprint",
                    markers=True,
                    labels={"date": "Assessment date", "footprint": "kg CO₂/year"},
                )
                figure.update_layout(margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(figure, use_container_width=True)
            elif len(trend) == 1:
                st.info("Complete one more assessment to unlock your trend chart.")
            else:
                st.info("Assessment history is not available yet.")

    if "activity" in selected:
        with st.container(border=True):
            st.subheader("🧭 Latest activity")
            if latest:
                import pandas as pd
                activity = pd.DataFrame(
                    {
                        "Category": ["Transport", "Distance", "Electricity", "Diet", "Flights"],
                        "Value": [
                            str(latest["transport"]),
                            f"{float(latest['distance']):g} km/day",
                            f"{float(latest['electricity']):g} kWh/month",
                            str(latest["diet"]),
                            str(int(latest["flights"])),
                        ],
                    }
                )
                st.dataframe(activity, hide_index=True, use_container_width=True)
            else:
                st.info("Your latest lifestyle inputs will appear here.")

    if "quick_tips" in selected:
        with st.container(border=True):
            st.subheader("💡 Quick eco tips")
            tips = [
                "Walk, cycle, or use public transport for short journeys.",
                "Turn off standby appliances and unnecessary lights.",
                "Plan meals to reduce food waste.",
            ]
            if latest and str(latest.get("transport")) == "Car":
                tips.insert(0, "Combine car trips or car-share to reduce transport emissions.")
            for tip in tips[:3]:
                st.markdown(f"- {tip}")
