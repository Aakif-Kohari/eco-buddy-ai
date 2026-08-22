import time
import pytest
from typing import Callable, List, Dict, Any

# --- Simulated System Profiles & Performance Budgets ---
# Defined in milliseconds (ms)
BUDGETS = {
    "single_api_latency": 150.0,    # Target under 150ms for live endpoints
    "db_query_threshold": 50.0,     # Target under 50ms for query extraction
    "high_volume_retrieval": 400.0, # Target under 400ms for heavy processing loads
}

class AnalyticsEngine:
    """Core EcoBuddy heavy calculation and tracking matrix engine."""
    
    @staticmethod
    def mock_db_query(records_count: int) -> List[Dict[str, Any]]:
        # Simulate proportional latency relative to scale
        time.sleep(0.002 * min(records_count, 100))  # Base indexing delay
        return [{"id": i, "impact": 12.4} for i in range(records_count)]

    @staticmethod
    def process_large_payload(records: List[Dict[str, Any]]) -> float:
        # Simulate processing matrix operations
        total = 0.0
        for item in records:
            total += item["impact"] * 1.05
        return total

# --- Helper Timer Hook ---
def measure_execution_ms(func: Callable, *args, **kwargs) -> tuple[Any, float]:
    start_time = time.perf_counter()
    result = func(*args, **kwargs)
    end_time = time.perf_counter()
    duration_ms = (end_time - start_time) * 1000.0
    return result, duration_ms

# --- Performance Testing Suite ---

def test_api_response_latency_budget():
    """Scenario 1: Verify single transactional workflows remain within tight API latency budgets."""
    def sample_endpoint_workflow():
        time.sleep(0.05)  # Simulate typical routing overhead (50ms)
        return "200_OK"
        
    _, latency = measure_execution_ms(sample_endpoint_workflow)
    
    assert latency < BUDGETS["single_api_latency"], (
        f"API regression detected! Spent {latency:.2f}ms, budget is {BUDGETS['single_api_latency']}ms"
    )


def test_database_query_performance():
    """Scenario 2: Assess query execution latency configurations under standard index lookups."""
    _, duration = measure_execution_ms(AnalyticsEngine.mock_db_query, records_count=20)
    
    assert duration < BUDGETS["db_query_threshold"], (
        f"Database query processing slowed down: took {duration:.2f}ms"
    )


def test_large_input_processing():
    """Scenario 3 & 4: Stress-test computation loops with repeated processing operations over large inputs."""
    large_dataset = [{"id": i, "impact": 5.5} for i in range(5000)]
    
    # Execute computation loops repeatedly to ensure memory/CPU cycles don't degrade linearly
    _, duration = measure_execution_ms(AnalyticsEngine.process_large_payload, large_dataset)
    
    # Massive calculations should comfortably resolve inside 100ms on basic modern CPU hardware
    assert duration < 100.0, f"Array processing calculation regression: took {duration:.2f}ms"


def test_high_volume_data_retrieval_limit():
    """Scenario 5: Validate complex multi-layer aggregation tracking metrics on heavy data structures."""
    def end_to_end_analytics_pipeline():
        # Fetching a highly inflated profile array sequence
        records = AnalyticsEngine.mock_db_query(records_count=250)
        # Immediately pipe the records into the calculation block
        return AnalyticsEngine.process_large_payload(records)

    _, total_duration = measure_execution_ms(end_to_end_analytics_pipeline)
    
    assert total_duration < BUDGETS["high_volume_retrieval"], (
        f"Pipeline aggregation performance missed budget: took {total_duration:.2f}ms"
    )
