import pytest
from unittest.mock import MagicMock
from datetime import datetime
from typing import Dict, Any, Optional

# --- Custom Service Domain Exceptions ---
class BusinessRuleViolation(Exception): pass
class DependencyUnavailable(Exception): pass

# --- Simulated Service Layer Component Under Test ---
class CarbonTrackingService:
    """Core domain logic orchestrating calculations independent of HTTP routers or DB clients."""
    def __init__(self, db_repository: Any, notification_client: Optional[Any] = None):
        self.repo = db_repository
        self.notifier = notification_client

    def process_daily_footprint_summary(self, user_id: str, activity_logs: list) -> Dict[str, Any]:
        if not user_id:
            raise ValueError("Invalid identification profile parameter.")
        if not self.repo:
            raise DependencyUnavailable("Critical database repository connection is missing.")
            
        # Business Rule Validation & Boundary Condition Evaluation
        total_co2 = 0.0
        for log in activity_logs:
            emissions = log.get("co2_emissions_kg", 0.0)
            if emissions < 0:
                raise BusinessRuleViolation("Carbon metrics cannot be negative values.")
            total_co2 += emissions

        # Conditional Logic: Trigger warning threshold alerts if limits break 50kg
        status_flag = "NORMAL"
        if total_co2 > 50.0:
            status_flag = "EXCEEDED_BUDGET"
            if self.notifier:
                try:
                    self.notifier.send_alert(user_id, f"Daily limit exceeded by {total_co2 - 50.0}kg")
                except Exception as e:
                    # Error Propagation / Exception Recovery check
                    raise RuntimeError(f"Alert dispatch failed: {str(e)}")

        # Data Transformation Mapping
        transformed_payload = {
            "user_id": user_id,
            "calculated_at": datetime(2026, 8, 23, 12, 0, 0).isoformat(),
            "total_co2_kg": round(total_co2, 2),
            "status": status_flag
        }

        # Dependency Interaction: Save state
        self.repo.save_summary(transformed_payload)
        return transformed_payload

# --- Service Unit Testing Suite ---

def test_valid_service_invocation_and_data_transformation():
    """Scenario 1 & 6: Validate successful orchestration loop and output structural transformations."""
    mock_repo = MagicMock()
    service = CarbonTrackingService(db_repository=mock_repo)
    
    valid_logs = [{"activity": "driving", "co2_emissions_kg": 14.25}, {"activity": "cooking", "co2_emissions_kg": 2.5}]
    
    result = service.process_daily_footprint_summary(user_id="user-7721", activity_logs=valid_logs)
    
    # Assert structural schema results
    assert result["total_co2_kg"] == 16.75
    assert result["status"] == "NORMAL"
    assert result["calculated_at"] == "2026-08-23T12:00:00"
    
    # Verify exact interaction with repository layer
    mock_repo.save_summary.assert_called_once_with(result)


def test_invalid_business_conditions_boundary_rejection():
    """Scenario 2 & 5: Force business rule violations at negative structural boundaries."""
    service = CarbonTrackingService(db_repository=MagicMock())
    invalid_logs = [{"activity": "flights", "co2_emissions_kg": -150.0}]  # Negative limit anomaly
    
    with pytest.raises(BusinessRuleViolation, match="Carbon metrics cannot be negative values"):
        service.process_daily_footprint_summary(user_id="user-12", activity_logs=invalid_logs)


def test_missing_required_dependencies():
    """Scenario 3: Verify execution safety guards when critical dependency injects are missing."""
    service = CarbonTrackingService(db_repository=None) # Explicitly dropped repository link
    
    with pytest.raises(DependencyUnavailable, match="Critical database repository connection is missing"):
        service.process_daily_footprint_summary(user_id="user-12", activity_logs=[])


def test_dependency_exceptions_and_error_propagation():
    """Scenario 4 & 7: Verify cascading errors from mock sub-clients propagate predictably."""
    mock_repo = MagicMock()
    mock_notifier = MagicMock()
    # Force alert interface to throw an unhandled internal exception
    mock_notifier.send_alert.side_effect = ConnectionRefusedError("Mail gateway down.")
    
    service = CarbonTrackingService(db_repository=mock_repo, notification_client=mock_notifier)
    high_impact_logs = [{"activity": "commute", "co2_emissions_kg": 65.0}]  # Triggers the notification pipeline
    
    with pytest.raises(RuntimeError, match="Alert dispatch failed: Mail gateway down"):
        service.process_daily_footprint_summary(user_id="user-99", activity_logs=high_impact_logs)
        
    # Assert state persistence was halted completely due to the execution crash
    mock_repo.save_summary.assert_not_called()


@pytest.mark.parametrize("logs, expected_status", [
    ([{"co2_emissions_kg": 49.9}], "NORMAL"),
    ([{"co2_emissions_kg": 50.0}], "NORMAL"),   # Budget upper boundary limit
    ([{"co2_emissions_kg": 50.01}], "EXCEEDED_BUDGET") # Structural boundary overflow pivot
])
def test_multiple_execution_conditional_paths(logs, expected_status):
    """Scenario 7: Evaluate business routing rule coverage variants across branching limits."""
    service = CarbonTrackingService(db_repository=MagicMock(), notification_client=MagicMock())
    result = service.process_daily_footprint_summary(user_id="user-abc", activity_logs=logs)
    assert result["status"] == expected_status
