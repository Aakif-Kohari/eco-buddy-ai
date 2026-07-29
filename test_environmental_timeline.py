import sqlite3

import database
from environmental_timeline import (
    MilestoneDefinition,
    evaluate_milestones,
    sync_environmental_milestones,
)


def assessment(footprint=10.0, eco_score=50):
    return (1, "2026-07-29", "Car", 10, 100, "Veg", 0, footprint, eco_score)


def test_evaluate_milestones_supports_current_rules():
    rows = [assessment(4.5, 88) for _ in range(5)]
    types = {item["milestone_type"] for item in evaluate_milestones(rows)}
    assert types == {
        "first_assessment",
        "five_assessments",
        "eco_score_70",
        "eco_score_85",
        "footprint_under_5",
    }


def test_future_milestone_type_can_be_added_without_engine_changes():
    custom = MilestoneDefinition(
        "future_type",
        "Future",
        "Extensible",
        "🔮",
        lambda rows: bool(rows),
        lambda rows: {"count": len(rows)},
    )
    assert evaluate_milestones([assessment()], [custom]) == [
        {
            "milestone_type": "future_type",
            "title": "Future",
            "description": "Extensible",
            "icon": "🔮",
            "metadata": {"count": 1},
        }
    ]


def test_record_and_get_milestones_are_user_scoped(tmp_path, monkeypatch):
    db_path = tmp_path / "timeline.db"
    monkeypatch.setattr(database, "DB_NAME", str(db_path))
    conn = sqlite3.connect(db_path)
    from migrations.migrate_v5 import migrate
    migrate(conn)
    conn.close()

    assert database.record_environmental_milestone(
        1, "first_assessment", "Journey Started", "Done"
    )
    assert not database.record_environmental_milestone(
        1, "first_assessment", "Journey Started", "Done"
    )
    assert database.record_environmental_milestone(
        2, "first_assessment", "Journey Started", "Done"
    )

    assert len(database.get_environmental_milestones(1)) == 1
    assert len(database.get_environmental_milestones(2)) == 1


def test_sync_only_reports_new_milestones(monkeypatch):
    monkeypatch.setattr(
        "environmental_timeline.get_assessments",
        lambda user_id: [assessment(4.0, 90)],
    )
    inserted = []

    def fake_record(**kwargs):
        inserted.append(kwargs["milestone_type"])
        return True

    monkeypatch.setattr(
        "environmental_timeline.record_environmental_milestone",
        fake_record,
    )
    count = sync_environmental_milestones(7)
    assert count == 4
    assert set(inserted) == {
        "first_assessment",
        "eco_score_70",
        "eco_score_85",
        "footprint_under_5",
    }
