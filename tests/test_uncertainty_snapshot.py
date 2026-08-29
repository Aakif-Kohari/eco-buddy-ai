"""
Tests for uncertainty data persistence through assessment snapshots (#1308).
"""

import json
import os
import sqlite3
import sys
import pytest

_SRC_CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "core")
if _SRC_CORE not in sys.path:
    sys.path.insert(0, _SRC_CORE)

from src.core import database as db
from src.core.assessment_snapshot import (
    build_assessment_snapshot,
    serialize_snapshot,
    deserialize_snapshot,
)


@pytest.fixture(autouse=True)
def temp_db(monkeypatch, tmp_path):
    """Point the database module at a throwaway SQLite file for each test."""
    test_db = tmp_path / "test_eco_buddy.db"
    monkeypatch.setattr(db, "DB_NAME", str(test_db))
    db.init_db()
    yield str(test_db)


def _sample_footprint_audit():
    return {
        "factor_version": "static-v1",
        "provenance": {
            "factor_version": "static-v1",
            "citation": "EcoBuddy built-in offline factors",
        },
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


def _sample_uncertainty_range():
    return {
        "low_kg": 5772.75,
        "central_kg": 6097.0,
        "high_kg": 6421.25,
        "uncertainty_percent": 25.0,
        "factor_version": "static-v1",
        "provenance": {"factor_version": "static-v1", "citation": "..."},
        "category_bounds": {
            "transport": {
                "low_kg": 1040.25,
                "central_kg": 1387.0,
                "high_kg": 1733.75,
                "range_kg": 693.5,
            },
            "electricity": {
                "low_kg": 1845.0,
                "central_kg": 2460.0,
                "high_kg": 3075.0,
                "range_kg": 1230.0,
            },
            "diet": {
                "low_kg": 1312.5,
                "central_kg": 1750.0,
                "high_kg": 2187.5,
                "range_kg": 875.0,
            },
            "flights": {
                "low_kg": 375.0,
                "central_kg": 500.0,
                "high_kg": 625.0,
                "range_kg": 250.0,
            },
        },
        "top_uncertainty_contributors": [
            {"category": "electricity", "range_kg": 1230.0, "share_percent": 34.77},
            {"category": "diet", "range_kg": 875.0, "share_percent": 24.83},
            {"category": "transport", "range_kg": 693.5, "share_percent": 19.65},
            {"category": "flights", "range_kg": 250.0, "share_percent": 7.07},
        ],
    }


class TestUncertaintyInSnapshot:
    """Verify uncertainty bounds are captured and preserved in snapshots."""

    def test_snapshot_includes_uncertainty_when_provided(self):
        audit = _sample_footprint_audit()
        contributors = _sample_contributors()
        uncertainty_range = _sample_uncertainty_range()

        snapshot = build_assessment_snapshot(
            inputs=audit["inputs"],
            footprint_audit=audit,
            contributors=contributors,
            total=6097.0,
            eco_score=42,
            uncertainty_range=uncertainty_range,
        )

        assert "uncertainty_percent" in snapshot
        assert snapshot["uncertainty_percent"] == 25.0
        assert "category_bounds" in snapshot
        assert "transport" in snapshot["category_bounds"]
        assert snapshot["category_bounds"]["transport"]["central_kg"] == 1387.0
        assert snapshot["category_bounds"]["transport"]["range_kg"] == 693.5
        assert "uncertainty_range" in snapshot
        assert snapshot["uncertainty_range"]["low_kg"] == 5772.75
        assert snapshot["uncertainty_range"]["central_kg"] == 6097.0
        assert snapshot["uncertainty_range"]["high_kg"] == 6421.25

    def test_snapshot_uncertainty_survives_serialization(self):
        audit = _sample_footprint_audit()
        contributors = _sample_contributors()
        uncertainty_range = _sample_uncertainty_range()

        snapshot = build_assessment_snapshot(
            inputs=audit["inputs"],
            footprint_audit=audit,
            contributors=contributors,
            total=6097.0,
            eco_score=42,
            uncertainty_range=uncertainty_range,
        )

        serialized = serialize_snapshot(snapshot)
        deserialized = deserialize_snapshot(serialized)

        assert deserialized["uncertainty_percent"] == 25.0
        assert deserialized["category_bounds"]["electricity"]["range_kg"] == 1230.0
        assert deserialized["uncertainty_range"]["high_kg"] == 6421.25

    def test_snapshot_without_uncertainty_remains_backward_compatible(self):
        """Snapshots without uncertainty_range should still work."""
        audit = _sample_footprint_audit()
        contributors = _sample_contributors()

        snapshot = build_assessment_snapshot(
            inputs=audit["inputs"],
            footprint_audit=audit,
            contributors=contributors,
            total=6097.0,
            eco_score=42,
        )

        # Should not crash; optional fields should be missing
        assert "uncertainty_percent" not in snapshot
        assert "category_bounds" not in snapshot
        assert "uncertainty_range" not in snapshot
        assert snapshot["total_kg"] == 6097.0

    def test_uncertainty_persists_through_database_round_trip(self):
        audit = _sample_footprint_audit()
        contributors = _sample_contributors()
        uncertainty_range = _sample_uncertainty_range()

        snapshot = build_assessment_snapshot(
            inputs=audit["inputs"],
            footprint_audit=audit,
            contributors=contributors,
            total=6097.0,
            eco_score=42,
            uncertainty_range=uncertainty_range,
        )

        db.save_assessment(
            1, "Car", 20, 250, "Non-Vegetarian", 2, 6097.0, 42,
            factor_version="static-v1",
            snapshot_json=serialize_snapshot(snapshot),
        )

        rows = db.get_assessments(1)
        assessment_id = rows[0][0]

        stored_snapshot = db.get_assessment_snapshot(assessment_id)
        assert stored_snapshot is not None
        assert stored_snapshot["uncertainty_percent"] == 25.0
        assert stored_snapshot["uncertainty_range"]["low_kg"] == 5772.75
        # Verify all category bounds are preserved
        for category in ["transport", "electricity", "diet", "flights"]:
            assert category in stored_snapshot["category_bounds"]
            assert "central_kg" in stored_snapshot["category_bounds"][category]
            assert "range_kg" in stored_snapshot["category_bounds"][category]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])