"""Tests for external data connectors, PDF parser, and geospatial modules."""

import pytest
from data_import_api_connectors import (
    TeslaAPIConnector, OpowerConnector, FlightAwareConnector, ConnectorManager
)
from data_import_pdf_parser import PDFUtilityBillParser
from data_import_geospatial import extract_region_from_text, apply_geospatial_emission_factors, calculate_commute_geospatial

class TestConnectors:
    def test_tesla_connector(self):
        conn = TeslaAPIConnector("dummy_key")
        raw = conn.fetch_data("2026-01-01", "2026-01-05")
        
        # It's random, so it might be empty or full, but mapping should not crash
        mapped = conn.map_to_standard_schema(raw)
        
        for r in mapped:
            assert r["category"] in ["Transport", "Energy"]
            
    def test_opower_connector(self):
        conn = OpowerConnector("dummy")
        raw = conn.fetch_data("2026-01-01", "2026-01-05")
        mapped = conn.map_to_standard_schema(raw)
        
        assert len(mapped) == 5
        assert mapped[0]["unit"] == "kWh"
        assert mapped[0]["category"] == "Energy"
        
    def test_flightaware_connector(self):
        conn = FlightAwareConnector("dummy")
        raw = conn.fetch_data("2026-01-01", "2026-12-31")
        mapped = conn.map_to_standard_schema(raw)
        
        # Might have flights, just ensure the format is right
        for r in mapped:
            assert r["category"] == "Transport"
            assert "Flight" in r["activity"]


class TestGeospatial:
    def test_extract_region(self):
        assert extract_region_from_text("My home in California") == "US-CA"
        assert extract_region_from_text("Trip to Paris, France") == "EU-FR"
        assert extract_region_from_text("Somewhere in united states") == "US-AVG"
        assert extract_region_from_text("Unknown place") == "GLOBAL-AVG"
        
    def test_apply_geospatial_factors(self):
        records = [
            {
                "category": "Energy", 
                "activity": "House in California", 
                "value": 100, 
                "normalized_value": 100
            },
            {
                "category": "Energy", 
                "location": "Wyoming", 
                "value": 100, 
                "normalized_value": 100
            }
        ]
        
        adjusted, stats = apply_geospatial_emission_factors(records)
        assert stats["regions_detected"] == 2
        
        # CA factor is 0.22, WY is 0.85
        assert adjusted[0]["emissions_kg"] == 22.0
        assert adjusted[1]["emissions_kg"] == 85.0
        
    def test_calculate_commute(self):
        dist = calculate_commute_geospatial("JFK", "LAX")
        assert dist == 3983.0
        dist_rev = calculate_commute_geospatial("LAX", "JFK")
        assert dist_rev == 3983.0


class TestPDFParser:
    def test_pge_parsing(self):
        text = '''
        Statement Date: 08/15/2026
        Total Electric Charges $105.20
        Electricity Usage 450.5 kWh
        Total Gas Charges $45.10
        Gas Usage 25.4 Therms
        '''
        parser = PDFUtilityBillParser()
        records = parser.parse_text(text)
        
        assert len(records) == 2
        assert records[0]["category"] == "Energy"
        assert records[0]["value"] == 450.5
        assert records[0]["unit"] == "kWh"
        
        assert records[1]["value"] == 25.4
        assert records[1]["unit"] == "therms"
        
    def test_coned_parsing(self):
        text = '''
        Billing Period: August 12, 2026
        Your Electricity Use 300 kWh
        '''
        parser = PDFUtilityBillParser()
        records = parser.parse_text(text)
        
        assert len(records) == 1
        assert records[0]["value"] == 300.0
