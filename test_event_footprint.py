"""
Unit tests for Event Footprint Calculator and Green Vendor Matcher.
"""

import pytest
from event_footprint_calculator import EventFootprintCalculator
from green_vendor_matcher import GreenVendorMatcher


def test_calculator_zero_guests():
    calc = EventFootprintCalculator(
        guest_count=0,
        catering_type="vegan",
        avg_travel_distance_km=10.0,
        travel_mode="carpool",
        venue_type="standard_grid",
        waste_management="standard_recycling",
        duration_hours=4.0,
    )
    result = calc.calculate_footprint()
    assert result["total_emissions_kg"] == 0.0
    assert result["guest_count"] == 0
    assert "virtual event" in result["green_swaps"][0].lower()


def test_calculator_standard_event():
    calc = EventFootprintCalculator(
        guest_count=100,
        catering_type="beef_heavy",
        avg_travel_distance_km=20.0,
        travel_mode="single_occupancy_vehicle",
        venue_type="standard_grid",
        waste_management="landfill_heavy",
        duration_hours=5.0,
    )
    result = calc.calculate_footprint()

    # Catering: 100 * 5.0 = 500
    # Travel: 100 * 40 * 0.25 = 1000
    # Venue: 100 * 5 * 0.2 = 100
    # Waste: 100 * 0.8 = 80
    # Total: 1680
    assert result["total_emissions_kg"] == 1680.0
    assert len(result["green_swaps"]) == 4  # All 4 swaps should trigger


def test_calculator_green_event():
    calc = EventFootprintCalculator(
        guest_count=50,
        catering_type="vegan",
        avg_travel_distance_km=5.0,
        travel_mode="public_transit",
        venue_type="renewable_energy",
        waste_management="zero_waste_compost",
        duration_hours=3.0,
    )
    result = calc.calculate_footprint()

    # Should trigger the "Excellent" swap
    assert "excellent" in result["green_swaps"][0].lower()
    assert result["total_emissions_kg"] < 200.0


def test_vendor_matcher_category_filter():
    matcher = GreenVendorMatcher()
    vendors = matcher.get_vendors_by_category("catering")
    assert len(vendors) == 2
    assert all(v["category"] == "catering" for v in vendors)


def test_vendor_matcher_certification_filter():
    matcher = GreenVendorMatcher()
    # Only EcoBites has both zero_waste and organic
    matched = matcher.match_vendors(
        required_certifications=["zero_waste", "organic"], category="catering"
    )
    assert len(matched) == 1
    assert matched[0]["name"] == "EcoBites Catering"


def test_vendor_matcher_sorting():
    matcher = GreenVendorMatcher()
    matched = matcher.match_vendors(required_certifications=["local_sourced"])
    # Should be sorted by rating descending
    assert matched[0]["rating"] >= matched[1]["rating"]
