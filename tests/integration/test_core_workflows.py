import pytest
from unittest.mock import MagicMock

# --- Simulated App Layers ---
class ResourceNotFoundError(Exception): pass
class DatabaseConnectionError(Exception): pass
class BusinessValidationError(Exception): pass

class EcoBuddyService:
    """Core Service managing business logic validations."""
    def process_carbon_log(self, data: dict, repository) -> dict:
        if not data.get("category") or data.get("co2_emissions_kg", 0) < 0:
            raise BusinessValidationError("Invalid carbon metrics payload.")
        if data.get("user_id") == "0000-missing":
            raise ResourceNotFoundError("Target EcoBuddy profile missing.")
        
        return repository.save(data)

# --- Integration Tests Suite ---

def test_complete_successful_workflow(user_factory, log_factory):
    """Scenario 1: Complete successful end-to-end integration workflow."""
    mock_user = user_factory.build()
    valid_payload = log_factory.build(user_id=mock_user["id"], category="transportation", co2_emissions_kg=12.5)
    
    # Mock Repository Success
    mock_repo = MagicMock()
    mock_repo.save.return_value = {**valid_payload, "id": "generated-log-uuid", "status": "persisted"}
    
    service = EcoBuddyService()
    response = service.process_carbon_log(valid_payload, mock_repo)
    
    assert response["status"] == "persisted"
    assert response["co2_emissions_kg"] == 12.5
    mock_repo.save.assert_called_once_with(valid_payload)


def test_invalid_input_workflow(log_factory):
    """Scenario 2 & 4: Business-logic validation failure due to invalid/negative inputs."""
    invalid_payload = log_factory.build(co2_emissions_kg=-5.0)  # Impossible boundary metric
    mock_repo = MagicMock()
    service = EcoBuddyService()
    
    with pytest.raises(BusinessValidationError, match="Invalid carbon metrics payload"):
        service.process_carbon_log(invalid_payload, mock_repo)
        
    mock_repo.save.assert_not_called()


def test_database_failure_during_workflow(log_factory):
    """Scenario 3: Database failure/Connection dropout during active state commitment."""
    valid_payload = log_factory.build()
    mock_repo = MagicMock()
    mock_repo.save.side_effect = DatabaseConnectionError("Database connection lost.")
    
    service = EcoBuddyService()
    
    with pytest.raises(DatabaseConnectionError, match="Database connection lost"):
        service.process_carbon_log(valid_payload, mock_repo)


def test_missing_resource_workflow(log_factory):
    """Scenario 5: Request processed correctly but references a missing parent resource."""
    missing_user_payload = log_factory.build(user_id="0000-missing")
    mock_repo = MagicMock()
    service = EcoBuddyService()
    
    with pytest.raises(ResourceNotFoundError, match="Target EcoBuddy profile missing"):
        service.process_carbon_log(missing_user_payload, mock_repo)
        
    mock_repo.save.assert_not_called()


def test_dependency_failure_during_processing(log_factory):
    """Scenario 6: External microservice or framework dependency crashing during operations."""
    valid_payload = log_factory.build()
    mock_repo = MagicMock()
    
    # Simulating a core system dependency failure (e.g., third-party emission-factor API crash)
    mock_repo.save.side_effect = RuntimeError("External Emission API Unavailable")
    service = EcoBuddyService()
    
    with pytest.raises(RuntimeError, match="External Emission API Unavailable"):
        service.process_carbon_log(valid_payload, mock_repo)
