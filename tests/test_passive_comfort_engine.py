"""Unit tests for Bioclimatic Passive Cooling & Thermal Comfort Engine.
"""

import pytest
from src.energy.passive_comfort_types import (
    BuildingBioclimaticInputs,
    ThermalMassType,
    GlazingOrientation,
)
from src.energy.passive_comfort_engine import PassiveComfortEngine
from src.energy.passive_comfort_db import (
    init_passive_comfort_db,
    save_comfort_audit,
    get_user_comfort_audits,
)


@pytest.fixture
def sample_rammed_earth_home():
    return BuildingBioclimaticInputs(
        building_name="Eco Adobe Residence",
        floor_area_sq_meters=140.0,
        ceiling_height_meters=3.2,
        window_to_wall_ratio=0.20,
        thermal_mass=ThermalMassType.RAMMED_EARTH_ADOBE,
        glazing_orientation=GlazingOrientation.SOUTH_SOLAR_CONTROL,
        outdoor_day_peak_temp_c=38.0,
        outdoor_night_min_temp_c=18.0,
        air_speed_m_s=0.3,
    )


def test_passive_comfort_calculations(sample_rammed_earth_home):
    result = PassiveComfortEngine.calculate_thermal_performance(sample_rammed_earth_home)

    assert result.indoor_peak_temperature_c < sample_rammed_earth_home.outdoor_day_peak_temp_c
    assert result.passive_cooling_temperature_drop_c > 0.0
    assert -3.0 <= result.fanger_pmv_index <= 3.0
    assert 5.0 <= result.predicted_percentage_dissatisfied_ppd <= 100.0
    assert result.natural_ventilation_airflow_rate_m3_hr > 0.0
    assert result.avoided_cooling_energy_kwh_per_season > 0.0
    assert result.annual_cost_savings_usd > 0.0


def test_thermal_mass_damping_comparison():
    timber_home = BuildingBioclimaticInputs(
        building_name="Timber Frame",
        floor_area_sq_meters=100.0,
        ceiling_height_meters=2.8,
        window_to_wall_ratio=0.25,
        thermal_mass=ThermalMassType.LIGHTWEIGHT_TIMBER,
        glazing_orientation=GlazingOrientation.EAST_WEST_EXPOSED,
        outdoor_day_peak_temp_c=36.0,
        outdoor_night_min_temp_c=20.0,
    )
    pcm_home = BuildingBioclimaticInputs(
        building_name="PCM Bio-Mass",
        floor_area_sq_meters=100.0,
        ceiling_height_meters=2.8,
        window_to_wall_ratio=0.25,
        thermal_mass=ThermalMassType.PHASE_CHANGE_DRYWALL,
        glazing_orientation=GlazingOrientation.EAST_WEST_EXPOSED,
        outdoor_day_peak_temp_c=36.0,
        outdoor_night_min_temp_c=20.0,
    )

    res_timber = PassiveComfortEngine.calculate_thermal_performance(timber_home)
    res_pcm = PassiveComfortEngine.calculate_thermal_performance(pcm_home)

    # PCM mass keeps the indoor peak lower
    assert res_pcm.indoor_peak_temperature_c < res_timber.indoor_peak_temperature_c
    assert res_pcm.avoided_cooling_energy_kwh_per_season > res_timber.avoided_cooling_energy_kwh_per_season


def test_passive_comfort_db_persistence(tmp_path):
    db_file = str(tmp_path / "test_comfort.db")
    init_passive_comfort_db(db_file)

    audit_id = save_comfort_audit(
        user_id=77,
        building_name="Solar Villa",
        indoor_temp=24.8,
        temp_drop=8.2,
        pmv=0.28,
        ppd=6.5,
        avoided_kwh=1420.0,
        savings_usd=198.80,
        comfort_rating="Class A",
        db_path=db_file,
    )

    assert audit_id > 0
    audits = get_user_comfort_audits(77, db_path=db_file)
    assert len(audits) == 1
    assert audits[0]["building_name"] == "Solar Villa"
    assert audits[0]["comfort_rating"] == "Class A"
