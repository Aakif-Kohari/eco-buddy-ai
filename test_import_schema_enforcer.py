"""Tests for the strict schema enforcer."""

import pytest
from datetime import datetime, timedelta
from data_import_schema_enforcer import SchemaEnforcer

class TestSchemaEnforcer:
    
    def test_valid_record(self):
        enforcer = SchemaEnforcer()
        record = {
            "value": 150.5,
            "activity_date": "2026-05-15",
            "unit": "kWh",
            "emissions_kg": 50.0
        }
        
        passed, errors = enforcer.validate_record(record)
        assert passed is True
        assert len(errors) == 0
        
    def test_numeric_bounds(self):
        enforcer = SchemaEnforcer()
        
        # Below min
        passed, errors = enforcer.validate_record({"value": -10.0})
        assert passed is False
        assert "below minimum" in errors[0]
        
        # Above max
        passed, errors = enforcer.validate_record({"value": 2000000.0})
        assert passed is False
        assert "exceeds maximum" in errors[0]
        
        # Invalid numeric string
        passed, errors = enforcer.validate_record({"value": "abc"})
        assert passed is False
        assert "must be numeric" in errors[0]
        
    def test_date_validation(self):
        enforcer = SchemaEnforcer()
        
        # Future date
        future = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
        passed, errors = enforcer.validate_record({"activity_date": future})
        assert passed is False
        assert "future" in errors[0]
        
        # Too old
        passed, errors = enforcer.validate_record({"activity_date": "1960-01-01"})
        assert passed is False
        assert "impossibly old" in errors[0]
        
    def test_string_validation(self):
        enforcer = SchemaEnforcer()
        
        # Too long
        passed, errors = enforcer.validate_record({"unit": "this_unit_name_is_way_too_long_for_db"})
        assert passed is False
        assert "exceeds max length" in errors[0]
        
        # Invalid characters
        passed, errors = enforcer.validate_record({"unit": "kWh !@#"})
        assert passed is False
        assert "invalid characters" in errors[0]
        
    def test_enforce_batch(self):
        enforcer = SchemaEnforcer()
        records = [
            {"value": 100, "activity_date": "2026-01-01", "unit": "kWh"},
            {"value": -50, "activity_date": "2026-01-01", "unit": "kWh"}, # Invalid value
            {"value": 100, "activity_date": "3000-01-01", "unit": "kWh"}  # Invalid date
        ]
        
        valid, invalid, stats = enforcer.enforce_batch(records)
        
        assert len(valid) == 1
        assert len(invalid) == 2
        assert stats["enforcement_passed"] == 1
        assert stats["enforcement_failed"] == 2
        
        assert "_errors" in invalid[0]
        assert "_row_index" in invalid[0]
