"""Unit tests for Soil Organic Carbon (SOC) and Agroecology Engine.
"""

import pytest
from soil_carbon_types import (
    FarmFieldParameters,
    SoilTextureType,
    TillagePractice,
    CoverCropStrategy,
)
from soil_carbon_engine import SoilCarbonEngine


@pytest.fixture
def base_field():
    return FarmFieldParameters(
        field_name="Test Farm",
        area_hectares=50.0,
        baseline_soc_pct=1.8,
        bulk_density_g_cm3=1.35,
        sampling_depth_cm=30.0,
        soil_texture=SoilTextureType.CLAY_LOAM,
        tillage_practice=TillagePractice.NO_TILL,
        cover_crop_strategy=CoverCropStrategy.MULTI_SPECIES_POLY,
        compost_addition_dry_tons_per_ha_yr=4.0,
        synthetic_nitrogen_kg_per_ha_yr=100.0,
        carbon_credit_price_usd_ton=30.0,
    )


def test_initial_soc_stock_calculation(base_field):
    stock = SoilCarbonEngine.calculate_initial_soc_stock(base_field)
    assert stock == pytest.approx(1.8 * 1.35 * 30.0, rel=1e-3)
    assert stock > 50.0


def test_agroecology_simulation(base_field):
    result = SoilCarbonEngine.simulate(base_field)

    assert result.initial_soc_stock_tons_c_ha > 0.0
    assert result.final_soc_stock_tons_c_ha_yr10 > result.initial_soc_stock_tons_c_ha
    assert result.net_10yr_carbon_sequestered_tons_co2e > 0.0
    assert result.annual_sequestration_rate_tons_co2e_per_ha > 0.0
    assert result.total_carbon_credit_revenue_10yr_usd > 0.0
    assert result.synthetic_n_fertilizer_offset_kg_yr > 0.0
    assert len(result.trajectory) == 10


def test_no_till_vs_intensive_tillage(base_field):
    field_intensive = FarmFieldParameters(
        field_name="Intensive Farm",
        area_hectares=50.0,
        baseline_soc_pct=1.8,
        bulk_density_g_cm3=1.35,
        sampling_depth_cm=30.0,
        soil_texture=SoilTextureType.CLAY_LOAM,
        tillage_practice=TillagePractice.CONVENTIONAL_INTENSIVE,
        cover_crop_strategy=CoverCropStrategy.NONE_FALLOW,
        compost_addition_dry_tons_per_ha_yr=0.0,
        synthetic_nitrogen_kg_per_ha_yr=100.0,
    )

    res_regen = SoilCarbonEngine.simulate(base_field)
    res_intense = SoilCarbonEngine.simulate(field_intensive)

    assert res_regen.final_soc_stock_tons_c_ha_yr10 > res_intense.final_soc_stock_tons_c_ha_yr10
    assert res_regen.net_10yr_carbon_sequestered_tons_co2e > res_intense.net_10yr_carbon_sequestered_tons_co2e
