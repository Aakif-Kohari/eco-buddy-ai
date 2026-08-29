import pytest
import json
import datetime
from src.data.data_portability_engine import DataPortabilityEngine
from src.utils.gdpr_compliance_checker import GDPRComplianceChecker
from src.data.data_deletion_service import DataDeletionService

class TestGDPRSystems:

    def test_data_portability_json(self):
        engine = DataPortabilityEngine("TEST_USER_01")
        json_output = engine.export_as_json()
        assert len(json_output) > 0
        
        parsed = json.loads(json_output)
        assert "metadata" in parsed
        assert "data" in parsed
        assert parsed["data"]["account"]["user_id"] == "TEST_USER_01"

    def test_data_portability_csv(self):
        engine = DataPortabilityEngine("TEST_USER_01")
        csv_output = engine.export_as_csv()
        assert "date,type,co2_kg" in csv_output
        assert len(csv_output.split("\n")) > 2

    def test_gdpr_compliance_scoring(self):
        # 1 user compliant, 1 user uncompliant (inactive too long)
        now = datetime.datetime.now()
        old_date = (now - datetime.timedelta(days=800)).isoformat()
        recent_date = (now - datetime.timedelta(days=10)).isoformat()
        
        mock_db = [
            {"user_id": "U1", "last_active": recent_date, "consent_logs": {"terms_accepted": True}},
            {"user_id": "U2", "last_active": old_date, "consent_logs": {"terms_accepted": True}}
        ]
        
        checker = GDPRComplianceChecker(mock_db)
        violations = checker.check_retention_violations()
        
        assert len(violations) == 1
        assert violations[0]["user_id"] == "U2"
        
        score = checker.get_compliance_score()
        assert score == 95.0 # penalty of 5 for one retention violation

    def test_gdpr_audit_log(self):
        mock_db = [{"user_id": "U1", "last_active": datetime.datetime.now().isoformat(), "consent_logs": {"terms_accepted": True}}]
        checker = GDPRComplianceChecker(mock_db)
        logs = checker.generate_audit_log()
        assert len(logs) > 0
        assert "GDPR Audit Generated:" in logs[0]

    def test_data_deletion_service(self):
        service = DataDeletionService(":memory:") 
        # Using in-memory sqlite won't actually affect our test logic since we handle operational errors
        
        # Test Anonymization
        anon_id = service.execute_anonymization("TEST_USER")
        assert "ANON_" in anon_id
        
        # Test Hard Delete
        success = service.execute_hard_delete("TEST_USER")
        assert success == True
