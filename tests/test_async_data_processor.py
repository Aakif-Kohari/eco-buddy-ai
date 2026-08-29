"""
Comprehensive Unit Tests for Async Data Processor
"""

import time
import pytest
from async_data_processor import process_dataset_async, process_dataset_sync, run_async_processor


def sample_processor(row):
    return {"id": row["id"], "value": row["value"] * 2}


class TestBasicAsync:
    def test_async_processes_all_rows(self):
        """Should process all rows."""
        data = [{"id": 1, "value": 2}, {"id": 2, "value": 3}]
        result = run_async_processor(data, sample_processor)
        assert len(result) == 2

    def test_async_correct_values(self):
        """Should return correct processed values."""
        data = [{"id": 1, "value": 2}]
        result = run_async_processor(data, sample_processor)
        assert result[0]["value"] == 4

    def test_async_empty_list(self):
        """Should handle an empty list."""
        result = run_async_processor([], sample_processor)
        assert result == []

    def test_async_handles_errors(self):
        """Should handle errors without crashing."""
        data = [{"id": 1, "value": "invalid"}]
        result = run_async_processor(data, lambda x: 1 / 0)  # Causes ZeroDivisionError
        assert "error" in result[0]


class TestPerformance:
    def test_async_is_faster_than_sync(self):
        """Async should be faster than sync for large datasets."""
        data = [{"id": i, "value": i} for i in range(100)]
        
        start = time.time()
        process_dataset_sync(data, sample_processor)
        sync_time = time.time() - start

        start = time.time()
        run_async_processor(data, sample_processor)
        async_time = time.time() - start

        assert async_time < sync_time

    def test_async_handles_large_batch(self):
        """Should handle a batch of 1000 rows."""
        data = [{"id": i, "value": i} for i in range(1000)]
        result = run_async_processor(data, sample_processor)
        assert len(result) == 1000


class TestEdgeCases:
    def test_none_input(self):
        """Should handle None input."""
        with pytest.raises(TypeError):
            run_async_processor(None, sample_processor)

    def test_string_input(self):
        """Should handle string input."""
        with pytest.raises(TypeError):
            run_async_processor("string", sample_processor)

    def test_processor_returns_none(self):
        """Should handle a processor that returns None."""
        result = run_async_processor([{"id": 1}], lambda x: None)
        assert result[0] is None

    def test_processor_mutates_data(self):
        """Should not mutate original data."""
        data = [{"id": 1, "value": 2}]
        original = data.copy()
        run_async_processor(data, sample_processor)
        assert data == original