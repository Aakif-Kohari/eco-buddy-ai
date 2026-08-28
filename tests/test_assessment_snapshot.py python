import json
import os
import sqlite3
import sys

import pytest

# `migrations/__init__.py` uses bare imports (`database_connection`,
# `database`) that assume `src/core` is directly on sys.path — the same
# assumption the running Streamlit app relies on elsewhere. Add it for the
# duration of the test session so `db.init_db()` can run its migrations.
_SRC_CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "core")
if _SRC_CORE not in sys.path:
    sys.path.insert(0, _SRC_CORE)

from src.core import database as db
from src.core import assessment_snapshot as snap_module
from src.core.assessment_snapshot import (
    build_assessment_snapshot,
    deserialize_snapshot,
    serialize_snapshot,
)


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    """Point the database module at a throwaway SQLite file for each test."""
    test_db = tmp_path / "test_eco_buddy.db"
    monkeypatch.setattr(db, "DB_NAME", str(test_db))
    db.init_db()
    yield str(test_db)


def _sample_footprint_audit(factor_version="static-v1"):
    return {
        "factor_version": factor_version,
        "provenance": {"factor_version": factor_version, "citation": "EcoBuddy built-in offline factors"},
        "inputs": {
            "transport": "Car",
            "daily_distance_km": 20,
            "monthly_electricity_kwh": 250,
            "diet": "Non-Vegetarian",
            "annual_flights": 2,
        },
    }


def _sample_contributors():
    return {"Transport": 1387.0, "Electricity": 2460.0, "Diet": 1750, "Flights": 500}


class TestSnapshotBuildAndSerialize:
    def test_build_snapshot_captures_full_context(self):
        audit = _sample_footprint_audit()
        contributors = _sample_contributors()

        snapshot = build_assessment_snapshot(
            inputs=audit["inputs"], footprint_audit=audit,
            contributors=contributors, total=6097.0, eco_score=42,
        )

        assert snapshot["inputs"] == audit["inputs"]
        assert snapshot["factor_version"] == "static-v1"
        assert snapshot["category_emissions_kg"] == contributors
        assert snapshot["total_kg"] == 6097.0
        assert snapshot["eco_score"] == 42
        assert "engine_version" in snapshot
        assert "calculated_at" in snapshot
        assert "eco_score_config" in snapshot
        assert "category_weights" in snapshot["eco_score_config"]

    def test_serialize_deserialize_round_trip(self):
        snapshot = build_assessment_snapshot(
            inputs=_sample_footprint_audit()["inputs"],
            footprint_audit=_sample_footprint_audit(),
            contributors=_sample_contributors(),
            total=6097.0, eco_score=42,
        )
        round_tripped = deserialize_snapshot(serialize_snapshot(snapshot))
        assert round_tripped == snapshot


class TestSnapshotPersistence:
    def test_save_assessment_stores_and_returns_snapshot(self):
        audit = _sample_footprint_audit()
        contributors = _sample_contributors()
        snapshot = build_assessment_snapshot(
            inputs=audit["inputs"], footprint_audit=audit,
            contributors=contributors, total=6097.0, eco_score=42,
        )

        ok = db.save_assessment(
            1, "Car", 20, 250, "Non-Vegetarian", 2, 6097.0, 42,
            factor_version="static-v1",
            snapshot_json=serialize_snapshot(snapshot),
        )
        assert ok is True

        rows = db.get_assessments(1)
        assessment_id = rows[0][0]

        stored_snapshot = db.get_assessment_snapshot(assessment_id)
        assert stored_snapshot is not None
        assert stored_snapshot["total_kg"] == 6097.0
        assert stored_snapshot["category_emissions_kg"] == contributors

    def test_assessment_without_snapshot_returns_none(self):
        db.save_assessment(1, "Bike", 5, 100, "Vegetarian", 0, 500.0, 80)
        rows = db.get_assessments(1)
        assessment_id = rows[0][0]

        assert db.get_assessment_snapshot(assessment_id) is None

    def test_snapshot_cannot_be_duplicated_for_same_assessment(self):
        """
        The snapshot table has a UNIQUE(assessment_id) constraint and no
        update function exists for it, so a second write for the same
        assessment id is rejected rather than silently overwriting history.
        """
        db.save_assessment(
            1, "Car", 20, 250, "Non-Vegetarian", 2, 6097.0, 42,
            factor_version="static-v1", snapshot_json='{"total_kg": 6097.0}',
        )
        rows = db.get_assessments(1)
        assessment_id = rows[0][0]

        with sqlite3.connect(db.DB_NAME) as conn:
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO assessment_snapshots (assessment_id, snapshot_json) VALUES (?, ?)",
                    (assessment_id, '{"total_kg": 9999.0}'),
                )


class TestHistoricalStabilityAfterConfigChange:
    """
    Comparison test (acceptance criterion): a stored snapshot's numbers must
    not change when emission-factor / eco-score configuration changes later.
    """

    def test_snapshot_is_stable_after_category_weights_change(self, monkeypatch):
        audit = _sample_footprint_audit()
        contributors = _sample_contributors()

        # Snapshot taken under "original" configuration.
        original_weights = dict(snap_module.CATEGORY_WEIGHTS)
        snapshot = build_assessment_snapshot(
            inputs=audit["inputs"], footprint_audit=audit,
            contributors=contributors, total=6097.0, eco_score=42,
        )
        db.save_assessment(
            1, "Car", 20, 250, "Non-Vegetarian", 2, 6097.0, 42,
            factor_version="static-v1", snapshot_json=serialize_snapshot(snapshot),
        )
        rows = db.get_assessments(1)
        assessment_id = rows[0][0]

        # Simulate a later configuration change (category weights retuned).
        changed_weights = {**original_weights, "Transport": 0.9}
        monkeypatch.setattr(snap_module, "CATEGORY_WEIGHTS", changed_weights)

        # A *new* snapshot built after the change reflects the new config...
        new_snapshot = build_assessment_snapshot(
            inputs=audit["inputs"], footprint_audit=audit,
            contributors=contributors, total=6097.0, eco_score=42,
        )
        assert new_snapshot["eco_score_config"]["category_weights"] != original_weights

        # ...but the historical, already-stored snapshot is untouched.
        stored_snapshot = db.get_assessment_snapshot(assessment_id)
        assert stored_snapshot["eco_score_config"]["category_weights"] == original_weights
        assert stored_snapshot["total_kg"] == 6097.0
        assert stored_snapshot["eco_score"] == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])