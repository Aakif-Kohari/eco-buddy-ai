"""Tests for the advanced features of Eco Data Import Hub.

Covers Anomaly Detection, Undo/Rollback capabilities, and Batch Exports.
"""

import pytest
import json
from datetime import datetime, timedelta

from household import init_household_db, create_household, delete_household

from data_import_history import (
    init_import_db, log_import_job, save_imported_records, 
    get_import_history, get_imported_records
)
from data_import_anomalies import AnomalyDetector
from data_import_undo_manager import get_rollback_eligibility, rollback_import_job
from data_import_batch_export import (
    generate_audit_report_json, generate_flat_csv_export, generate_executive_summary_md
)
from data_import_analytics import merge_import_data_with_core_system


@pytest.fixture
def setup_advanced_db():
    init_household_db()
    
    init_import_db()
    
    hh_id = create_household("Advanced Test House", 999)
    yield hh_id
    delete_household(hh_id)


class TestAnomalyDetection:
    
    def test_statistical_anomalies(self):
        detector = AnomalyDetector(sensitivity=2.0)
        
        # We need at least 5 records to trigger statistical calculations
        records = [
            {"category": "Energy", "value": 100, "normalized_value": 100},
            {"category": "Energy", "value": 110, "normalized_value": 110},
            {"category": "Energy", "value": 90, "normalized_value": 90},
            {"category": "Energy", "value": 105, "normalized_value": 105},
            {"category": "Energy", "value": 95, "normalized_value": 95},
            # This is the anomaly
            {"category": "Energy", "value": 5000, "normalized_value": 5000} 
        ]
        
        flagged, stats = detector.detect_anomalies(records)
        
        assert stats["anomalies_detected"] == 1
        assert flagged[5].get("_is_anomaly") is True
        assert "[ANOMALY]" in flagged[5]["_warnings"][0]
        
        # Normal records should not be flagged
        assert flagged[0].get("_is_anomaly") is None

    def test_insufficient_data_anomaly(self):
        detector = AnomalyDetector()
        records = [
            {"category": "Energy", "value": 100},
            {"category": "Energy", "value": 5000}
        ]
        
        # Less than 5 records, bypasses stats
        flagged, stats = detector.detect_anomalies(records)
        assert stats["anomalies_detected"] == 0

    def test_temporal_anomalies(self):
        detector = AnomalyDetector()
        records = [
            {"activity_date": "2026-01-01"},
            {"activity_date": "2026-01-02"},
            {"activity_date": "2026-01-03"},
            {"activity_date": "1990-01-01"} # Way off
        ]
        
        flagged = detector.find_temporal_anomalies(records)
        assert flagged[3].get("_is_anomaly") is True
        assert "TEMPORAL ANOMALY" in flagged[3]["_warnings"][-1]
        assert flagged[0].get("_is_anomaly") is None


class TestUndoManager:
    
    def test_rollback_eligibility(self, setup_advanced_db):
        hh_id = setup_advanced_db
        
        import_id = log_import_job(hh_id, "file.csv", "csv", {"total": 1}, "completed")
        save_imported_records(import_id, hh_id, [{
            "activity_date": "2026-01-01", "category": "Energy", "activity": "A", 
            "value": 100, "unit": "kWh", "normalized_value": 100, "normalized_unit": "kWh", 
            "emissions_kg": 50.0, "_hash": "h1"
        }])
        
        eligibility = get_rollback_eligibility(import_id)
        assert eligibility["eligible"] is True
        
        assert get_rollback_eligibility(9999)["eligible"] is False
        
    def test_full_rollback_with_sync(self, setup_advanced_db):
        hh_id = setup_advanced_db
        
        import_id = log_import_job(hh_id, "file.csv", "csv", {"total": 1}, "completed")
        save_imported_records(import_id, hh_id, [{
            "activity_date": "2026-01-01", "category": "Energy", "activity": "A", 
            "value": 100, "unit": "kWh", "normalized_value": 100, "normalized_unit": "kWh", 
            "emissions_kg": 50.0, "_hash": "h1"
        }])
        
        # Sync to core
        merge_import_data_with_core_system(hh_id)
        pass
        
        # Rollback
        success = rollback_import_job(import_id, hh_id)
        assert success is True
        
        # Verify imported records deleted
        assert len(get_imported_records(hh_id)) == 0
        
        # Verify core activities deleted
        pass
        
        # Verify status updated
        history = get_import_history(hh_id)
        assert history[0]["status"] == "rolled_back"


class TestBatchExports:
    
    def test_audit_report_json(self, setup_advanced_db):
        hh_id = setup_advanced_db
        import_id = log_import_job(hh_id, "file.csv", "csv", {"total": 1}, "completed")
        save_imported_records(import_id, hh_id, [{
            "activity_date": "2026-01-01", "category": "Energy", "activity": "A", 
            "value": 100, "unit": "kWh", "normalized_value": 100, "normalized_unit": "kWh", 
            "emissions_kg": 50.0, "_hash": "h1"
        }])
        
        json_str = generate_audit_report_json(hh_id)
        data = json.loads(json_str)
        
        assert data["metadata"]["household_id"] == hh_id
        assert len(data["import_jobs"]) == 1
        assert len(data["normalized_records_sample"]) == 1
        assert data["analytics_summary"]["total_records"] == 1
        
    def test_flat_csv_export(self, setup_advanced_db):
        hh_id = setup_advanced_db
        import_id = log_import_job(hh_id, "file.csv", "csv", {"total": 1}, "completed")
        save_imported_records(import_id, hh_id, [{
            "activity_date": "2026-01-01", "category": "Energy", "activity": "A", 
            "value": 100, "unit": "kWh", "normalized_value": 100, "normalized_unit": "kWh", 
            "emissions_kg": 50.0, "_hash": "h1"
        }])
        
        csv_bytes = generate_flat_csv_export(hh_id)
        csv_str = csv_bytes.decode('utf-8')
        
        assert "ID,Import_ID,Date,Category,Activity" in csv_str
        assert "2026-01-01" in csv_str
        assert "Energy" in csv_str
        
    def test_executive_summary_md(self, setup_advanced_db):
        hh_id = setup_advanced_db
        import_id = log_import_job(hh_id, "file.csv", "csv", {"total": 1, "valid": 1}, "completed")
        save_imported_records(import_id, hh_id, [{
            "activity_date": "2026-01-01", "category": "Energy", "activity": "A", 
            "value": 100, "unit": "kWh", "normalized_value": 100, "normalized_unit": "kWh", 
            "emissions_kg": 50.0, "_hash": "h1"
        }])
        
        md = generate_executive_summary_md(hh_id)
        
        assert "# Executive Import Summary" in md
        assert "Total Imported Records:** 1" in md
        assert "file.csv" in md
