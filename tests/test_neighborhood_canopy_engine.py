import pytest
from src.environment.neighborhood_canopy_engine import NeighborhoodCanopyEngine

@pytest.fixture
def engine():
    return NeighborhoodCanopyEngine()

def test_geocode_address_mock(engine):
    lat, lng = engine.geocode_address("1600 Amphitheatre Pkwy, Mountain View, CA")
    assert 37.0 <= lat <= 42.0
    assert -122.0 <= lng <= -112.0

def test_calculate_green_canopy_ratio(engine):
    ratio = engine.calculate_green_canopy_ratio("mock_image.jpg")
    assert 15.0 <= ratio <= 35.0

def test_project_carbon_sequestration(engine):
    projection = engine.project_carbon_sequestration(current_canopy_pct=20.0, added_trees=10)
    assert projection.added_trees == 10
    assert projection.drawdown_10y_kg == 500.0  # 10 * 50
    assert projection.drawdown_20y_kg == 1500.0 # 10 * 150
    assert projection.drawdown_50y_kg == 4000.0 # 10 * 400
    
    # 10 trees * 30 sq meters = 300 sq meters
    # 300 / 10000 = 0.03 (3% added canopy)
    # 3 * 0.1 = 0.3
    assert projection.temperature_reduction_c == 0.3

def test_get_baseline_for_address(engine):
    baseline = engine.get_baseline_for_address("Test Address")
    assert baseline.address == "Test Address"
    assert hasattr(baseline, 'green_canopy_percentage')
    assert hasattr(baseline, 'latitude')
    assert hasattr(baseline, 'longitude')
