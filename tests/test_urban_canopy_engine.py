"""Unit tests for Urban Canopy & Agroforestry Microclimate Planner.
"""

import pytest
from src.environment.urban_canopy_types import (
    UrbanZoneParameters,
    TreeSpeciesType,
    SoilPermeabilityType,
)
from src.environment.urban_canopy_engine import UrbanCanopyPlannerEngine
from src.environment.urban_canopy_db import (
    init_urban_canopy_db,
    save_canopy_plan,
    get_user_canopy_plans,
)


@pytest.fixture
def sample_urban_zone():
    return UrbanZoneParameters(
        zone_name="Downtown Corridor",
        baseline_surface_temp_c=36.5,
        impervious_surface_fraction=0.85,
        current_canopy_cover_pct=10.0,
        target_canopy_cover_pct=30.0,
        selected_species=TreeSpeciesType.OAK,
        soil_type=SoilPermeabilityType.BIOSWALE_ENGINEERED,
        district_area_sq_meters=50_000.0,
        annual_rainfall_mm=800.0,
    )


def test_canopy_cooling_calculation(sample_urban_zone):
    result = UrbanCanopyPlannerEngine.calculate_canopy_impact(sample_urban_zone)

    assert result.surface_temperature_reduction_c > 0.0
    assert result.ambient_air_temperature_reduction_c > 0.0
    assert result.species_tree_count_recommended > 0
    assert result.annual_carbon_sequestration_kg_co2 > 0.0
    assert result.stormwater_runoff_absorbed_cubic_meters > 0.0
    assert result.cooling_energy_savings_usd > 0.0


def test_species_properties_variation():
    zone_oak = UrbanZoneParameters(
        zone_name="Zone A",
        baseline_surface_temp_c=35.0,
        impervious_surface_fraction=0.5,
        current_canopy_cover_pct=10.0,
        target_canopy_cover_pct=25.0,
        selected_species=TreeSpeciesType.OAK,
        soil_type=SoilPermeabilityType.LOAMY_HEALTHY,
        district_area_sq_meters=20_000.0,
    )
    zone_birch = UrbanZoneParameters(
        zone_name="Zone B",
        baseline_surface_temp_c=35.0,
        impervious_surface_fraction=0.5,
        current_canopy_cover_pct=10.0,
        target_canopy_cover_pct=25.0,
        selected_species=TreeSpeciesType.BIRCH,
        soil_type=SoilPermeabilityType.LOAMY_HEALTHY,
        district_area_sq_meters=20_000.0,
    )

    res_oak = UrbanCanopyPlannerEngine.calculate_canopy_impact(zone_oak)
    res_birch = UrbanCanopyPlannerEngine.calculate_canopy_impact(zone_birch)

    # Oak has higher LAI and greater sequestration per tree
    assert res_oak.ambient_air_temperature_reduction_c > res_birch.ambient_air_temperature_reduction_c
    assert res_oak.annual_carbon_sequestration_kg_co2 > 0


def test_canopy_plan_db_persistence(tmp_path):
    db_file = str(tmp_path / "test_canopy.db")
    init_urban_canopy_db(db_file)

    plan_id = save_canopy_plan(
        user_id=42,
        zone_name="Green District",
        baseline_temp=34.0,
        target_canopy=30.0,
        species="Oak",
        soil_type="Loam",
        trees=150,
        temp_drop=2.1,
        carbon_kg=3300.0,
        db_path=db_file,
    )

    assert plan_id > 0
    plans = get_user_canopy_plans(42, db_path=db_file)
    assert len(plans) == 1
    assert plans[0]["zone_name"] == "Green District"
    assert plans[0]["trees_recommended"] == 150
