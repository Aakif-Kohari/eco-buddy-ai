import pytest
from unittest.mock import MagicMock, patch

# --- Simulated System Components ---
class DatabaseSession:
    def __init__(self):
        self.is_rolled_back = False
        self.is_committed = False
        self.dirty_state = []

    def add(self, item):
        self.dirty_state.append(item)

    def commit(self):
        self.is_committed = True

    def rollback(self):
        self.is_rolled_back = True
        self.dirty_state.clear()

class CentralizedErrorHandler:
    @staticmethod
    def handle(exception: Exception) -> dict:
        if isinstance(exception, ValueError):
            return {"error": "ValidationError", "status_code": 400}
        if isinstance(exception, TimeoutError):
            return {"error": "DependencyTimeout", "status_code": 504}
        # Centralized catch-all fallback for unexpected crash states
        return {"error": "InternalServerError", "status_code": 500}

class TransactionManager:
    def execute_workflow(self, payload: dict, session: DatabaseSession, remote_client) -> dict:
        session.add(payload)
        try:
            if not payload.get("title"):
                raise ValueError("Validation missing required field.")
            
            # Contact external microservice dependency
            remote_client.fetch_external_rates()
            
            session.commit()
            return {"status": "success"}
        except Exception as e:
            session.rollback()  # Secure zero partial state maintenance
            return CentralizedErrorHandler.handle(e)

# --- Failure & Recovery Tests Suite ---

def test_database_rollback_and_zero_partial_state():
    """Scenarios: Simulate failure and verify transactions are rolled back with no partial state."""
    session = DatabaseSession()
    mock_client = MagicMock()
    # Force an unexpected runtime exception during processing
    mock_client.fetch_external_rates.side_effect = RuntimeError("Database write disk full.")
    
    manager = TransactionManager()
    payload = {"title": "Valid Log", "metric": 42}
    
    response = manager.execute_workflow(payload, session, mock_client)
    
    assert response["error"] == "InternalServerError"
    assert response["status_code"] == 500
    assert session.is_rolled_back is True
    assert session.is_committed is False
    assert len(session.dirty_state) == 0  # No partial corrupted data leaks out


def test_external_service_timeout_handling():
    """Scenario: Simulate external service timeout and check application error mapping."""
    session = DatabaseSession()
    mock_client = MagicMock()
    mock_client.fetch_external_rates.side_effect = TimeoutError("Remote API took too long to respond.")
    
    manager = TransactionManager()
    payload = {"title": "Eco Transport Log"}
    
    response = manager.execute_workflow(payload, session, mock_client)
    
    assert response["error"] == "DependencyTimeout"
    assert response["status_code"] == 504
    assert session.is_rolled_back is True


def test_validation_exception_graceful_rejection():
    """Scenario: Force expected application payload logic failures."""
    session = DatabaseSession()
    mock_client = MagicMock()
    
    manager = TransactionManager()
    invalid_payload = {"metric": 100}  # Missing required 'title' field
    
    response = manager.execute_workflow(invalid_payload, session, mock_client)
    
    assert response["error"] == "ValidationError"
    assert response["status_code"] == 400
    assert session.is_rolled_back is True
    mock_client.fetch_external_rates.assert_not_called()


@patch.object(CentralizedErrorHandler, 'handle')
def test_centralized_error_handler_fallback(mock_handler):
    """Scenario: Verify unexpected exceptions are handled cleanly by centralized middleware."""
    session = DatabaseSession()
    mock_client = MagicMock()
    mock_client.fetch_external_rates.side_effect = SystemError("Fatal unexpected kernel interrupt.")
    
    manager = TransactionManager()
    payload = {"title": "Solar Tracker Deployment"}
    
    manager.execute_workflow(payload, session, mock_client)
    
    # Assert standard system architecture successfully catches the underlying runtime crash
    mock_handler.assert_called_once()
    assert isinstance(mock_handler.call_args[0][0], SystemError)
