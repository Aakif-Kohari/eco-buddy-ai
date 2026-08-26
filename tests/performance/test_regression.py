import time
import pytest
from typing import Callable, List, Dict, Any

# --- Performance Budgets (Defined in Milliseconds) ---
PERFORMANCE_BUDGETS = {
    "api_response_latency": 150.0,    # Target: under 150ms for live endpoints
    "db_query_execution": 50.0,       # Target: under 50ms for query extraction
    "high_volume_retrieval": 400.0,   # Target: under 400ms for large dataset loads
}

class EcoBuddyAnalyticsEngine:
    """Simulated production core engine executing calculation loops and database lookups."""
    
    @staticmethod
    def query_documents(records_count: int) -> List[Dict[str, Any]]:
        # Simulate baseline indexed query processing overhead (e.g., 2ms per 10 records)
        time.sleep(0.002 * (records_count // 10))
        return [{"id": i, "carbon_footprint": 12.4} for i in range(records_count)]

    @staticmethod
    def process_large_payload(records: List[Dict[str, Any]]) -> float:
        # Simulate processing matrix data scaling recalculations
        total_emissions = 0.0
        for item in records:
            total_emissions += item["carbon_footprint"] * 1.05
        return total_emissions

# --- High-Precision Performance Timer Hook ---
def measure_execution_ms(func: Callable, *args, **kwargs) -> tuple[Any, float]:
    """Measures execution duration using high-precision fractional system clock ticks."""
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000.0
    return result, duration_ms

# --- Performance Testing Suite ---

def test_api_response_latency_budget():
    """Scenario 1: Verify single transactional workflows remain within the 150ms latency budget."""
    def mock_endpoint_routing_lifecycle():
        time.sleep(0.06)  # Simulate network middleware, routing layers, and serialize operations (60ms)
        return "200_OK"
        
    _, latency = measure_execution_ms(mock_endpoint_routing_lifecycle)
    
    assert latency < PERFORMANCE_BUDGETS["api_response_latency"], (
        f"Performance Regression Detected! Endpoint latency hit {latency:.2f}ms. "
        f"Budget is {PERFORMANCE_BUDGETS['api_response_latency']}ms."
    )


def test_database_query_performance():
    """Scenario 2: Assess query index traversal lookups remain within the 50ms budget."""
    _, duration = measure_execution_ms(EcoBuddyAnalyticsEngine.query_documents, records_count=150)
    
    assert duration < PERFORMANCE_BUDGETS["db_query_execution"], (
        f"Database Query Degradation! Query processing execution took {duration:.2f}ms. "
        f"Budget is {PERFORMANCE_BUDGETS['db_query_execution']}ms."
    )


def test_large_input_processing_and_repeated_operations():
    """Scenario 3 & 4: Stress-test payload computation loops with scaled datasets."""
    # Scale up arrays to stress test calculation iteration logic
    large_dataset = [{"id": i, "carbon_footprint": 5.5} for i in range(10000)]
    
    # Run operations repeatedly to ensure algorithmic complexity doesn't degrade linearly
    for _ in range(5):
        _, duration = measure_execution_ms(EcoBuddyAnalyticsEngine.process_large_payload, large_dataset)
        
        # In-memory array loops should complete comfortably within 50ms on standard runtime hardware
        assert duration < 50.0, f"Array iteration computing loops slowed down: took {duration:.2f}ms."


def test_high_volume_data_retrieval_pipeline():
    """Scenario 5: Validate complex multi-layer aggregation processing on heavy historical data."""
    def end_to_end_data_pipeline():
        # Step 1: Heavy database simulation extraction
        records = EcoBuddyAnalyticsEngine.query_documents(records_count=1000)
        # Step 2: Immediate pipeline ingestion and metrics recalculation
        return EcoBuddyAnalyticsEngine.process_large_payload(records)

    _, total_duration = measure_execution_ms(end_to_end_data_pipeline)
    
    assert total_duration < PERFORMANCE_BUDGETS["high_volume_retrieval"], (
        f"Pipeline Aggregation Missed Performance Budget! Execution took {total_duration:.2f}ms. "
        f"Budget limit is {PERFORMANCE_BUDGETS['high_volume_retrieval']}ms."
    )
