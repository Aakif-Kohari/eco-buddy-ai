"""Environmental impact timeline utilities and Streamlit renderer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Mapping, Sequence

import streamlit as st

from database import (
    get_assessments,
    get_environmental_milestones,
    record_environmental_milestone,
)


@dataclass(frozen=True)
class MilestoneDefinition:
    """An extensible rule used to recognize one sustainability achievement."""

    milestone_type: str
    title: str
    description: str
    icon: str
    predicate: Callable[[Sequence[tuple]], bool]
    metadata_factory: Callable[[Sequence[tuple]], Mapping[str, object]]


def _assessment_count(rows: Sequence[tuple]) -> int:
    return len(rows)


def _best_eco_score(rows: Sequence[tuple]) -> int:
    scores = [int(row[8]) for row in rows if len(row) > 8 and row[8] is not None]
    return max(scores, default=0)


def _lowest_footprint(rows: Sequence[tuple]) -> float | None:
    values = [float(row[7]) for row in rows if len(row) > 7 and row[7] is not None]
    return min(values) if values else None


MILESTONE_DEFINITIONS: tuple[MilestoneDefinition, ...] = (
    MilestoneDefinition(
        "first_assessment",
        "Journey Started",
        "Completed the first environmental footprint assessment.",
        "🌱",
        lambda rows: _assessment_count(rows) >= 1,
        lambda rows: {"assessment_count": _assessment_count(rows)},
    ),
    MilestoneDefinition(
        "five_assessments",
        "Consistency Builder",
        "Completed five environmental footprint assessments.",
        "🗓️",
        lambda rows: _assessment_count(rows) >= 5,
        lambda rows: {"assessment_count": _assessment_count(rows)},
    ),
    MilestoneDefinition(
        "eco_score_70",
        "Eco Score: 70",
        "Reached an eco score of at least 70.",
        "⭐",
        lambda rows: _best_eco_score(rows) >= 70,
        lambda rows: {"best_eco_score": _best_eco_score(rows)},
    ),
    MilestoneDefinition(
        "eco_score_85",
        "Eco Champion",
        "Reached an eco score of at least 85.",
        "🏆",
        lambda rows: _best_eco_score(rows) >= 85,
        lambda rows: {"best_eco_score": _best_eco_score(rows)},
    ),
    MilestoneDefinition(
        "footprint_under_5",
        "Low-Impact Day",
        "Recorded a carbon footprint below 5 kg CO₂e.",
        "🍃",
        lambda rows: (
            _lowest_footprint(rows) is not None
            and _lowest_footprint(rows) < 5
        ),
        lambda rows: {"lowest_footprint": _lowest_footprint(rows)},
    ),
)


def evaluate_milestones(
    assessments: Sequence[tuple],
    definitions: Iterable[MilestoneDefinition] = MILESTONE_DEFINITIONS,
) -> list[dict]:
    """Return milestone payloads whose predicates are satisfied."""
    achieved: list[dict] = []
    for definition in definitions:
        if definition.predicate(assessments):
            achieved.append(
                {
                    "milestone_type": definition.milestone_type,
                    "title": definition.title,
                    "description": definition.description,
                    "icon": definition.icon,
                    "metadata": dict(definition.metadata_factory(assessments)),
                }
            )
    return achieved


def sync_environmental_milestones(user_id: int) -> int:
    """Evaluate assessment history and persist newly reached milestones."""
    assessments = get_assessments(user_id)
    inserted = 0
    for milestone in evaluate_milestones(assessments):
        inserted += int(
            record_environmental_milestone(
                user_id=user_id,
                milestone_type=milestone["milestone_type"],
                title=milestone["title"],
                description=milestone["description"],
                icon=milestone["icon"],
                metadata=milestone["metadata"],
            )
        )
    return inserted


def _format_date(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime(
            "%d %b %Y"
        )
    except ValueError:
        return text[:10]


def render_environmental_timeline(user_id: int) -> None:
    """Render a visual milestone timeline for the active user."""
    sync_environmental_milestones(user_id)
    milestones = get_environmental_milestones(user_id)

    st.markdown("## 🌍 Environmental Impact Timeline")
    st.caption(
        "Your sustainability milestones are recorded automatically as your "
        "assessment history grows."
    )

    if not milestones:
        st.info(
            "Complete your first footprint assessment to unlock the first "
            "timeline milestone."
        )
        return

    for index, milestone in enumerate(milestones):
        date_label = _format_date(milestone.get("achieved_at"))
        highlight = index == 0
        border = "#22c55e" if highlight else "#94a3b8"
        badge = "LATEST ACHIEVEMENT" if highlight else "MILESTONE"

        st.markdown(
            f"""
            <div style="
                position: relative;
                margin: 0 0 14px 18px;
                padding: 16px 18px;
                border-left: 4px solid {border};
                border-radius: 0 14px 14px 0;
                background: rgba(34, 197, 94, 0.08);
            ">
                <div style="
                    position: absolute;
                    left: -15px;
                    top: 17px;
                    width: 26px;
                    height: 26px;
                    border-radius: 50%;
                    display: grid;
                    place-items: center;
                    background: white;
                    border: 3px solid {border};
                ">{milestone.get("icon", "🌱")}</div>
                <div style="
                    font-size: 11px;
                    font-weight: 800;
                    letter-spacing: .08em;
                    color: {border};
                ">{badge}</div>
                <div style="font-size: 18px; font-weight: 800;">
                    {milestone.get("title", "Achievement")}
                </div>
                <div style="opacity: .78; margin-top: 4px;">
                    {milestone.get("description", "")}
                </div>
                <div style="font-size: 12px; opacity: .58; margin-top: 8px;">
                    {date_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
