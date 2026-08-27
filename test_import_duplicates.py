"""Tests for duplication resolution and simulated data generation."""

import pytest
import json
from data_import_duplicate_resolver import DuplicateResolver
from data_import_simulator import EcoDataSimulator

class TestDuplicateResolver:
    def test_drop_strategy(self):
        records = [
            {"value": 10, "_hash": "h1"},
            {"value": 20, "_hash": "h1"},
            {"value": 30, "_hash": "h2"}
        ]
        resolver = DuplicateResolver("drop")
        resolved, stats = resolver.resolve(records)
        
        assert len(resolved) == 2
        assert resolved[0]["value"] == 10
        assert resolved[1]["value"] == 30
        assert stats["duplicates_processed"] == 1

    def test_keep_latest_strategy(self):
        records = [
            {"value": 10, "_hash": "h1"},
            {"value": 20, "_hash": "h1"},
            {"value": 30, "_hash": "h2"}
        ]
        resolver = DuplicateResolver("keep_latest")
        resolved, stats = resolver.resolve(records)
        
        assert len(resolved) == 2
        # 'keep_latest' uses list order, so it keeps the second occurrence
        assert resolved[0]["value"] == 20
        assert resolved[1]["value"] == 30

    def test_sum_strategy(self):
        records = [
            {"value": 10.0, "normalized_value": 15.0, "_hash": "h1"},
            {"value": 20.0, "normalized_value": 25.0, "_hash": "h1"},
            {"value": 30.0, "normalized_value": 30.0, "_hash": "h2"}
        ]
        resolver = DuplicateResolver("sum")
        resolved, stats = resolver.resolve(records)
        
        assert len(resolved) == 2
        assert resolved[0]["value"] == 30.0
        assert resolved[0]["normalized_value"] == 40.0
        assert "[SUMMED]" in resolved[0]["_warnings"][0]

    def test_flag_only_strategy(self):
        records = [
            {"value": 10, "_hash": "h1"},
            {"value": 20, "_hash": "h1"}
        ]
        resolver = DuplicateResolver("flag_only")
        resolved, stats = resolver.resolve(records)
        
        assert len(resolved) == 2
        assert "_warnings" not in resolved[0]
        assert "[DUPLICATE]" in resolved[1]["_warnings"][0]

class TestEcoDataSimulator:
    def test_simulator_generation(self):
        sim = EcoDataSimulator(seed=123)
        records = sim.generate_records(50, malformation_rate=0.1)
        
        # May be more than 50 due to duplicates
        assert len(records) >= 50
        
        csv_bytes = sim.generate_csv_bytes(records)
        assert len(csv_bytes) > 100
        
        json_bytes = sim.generate_json_bytes(records)
        data = json.loads(json_bytes.decode('utf-8'))
        assert len(data) == len(records)
