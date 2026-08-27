"""Multi-pool Soil Organic Carbon (SOC) and Agroecological Kinetics Engine.

Based on RothC/DayCent simplified humification dynamics:
- SOC Stock = Area * Depth * BulkDensity * %SOC
- Biomass C inputs from cover crops and compost humification (humus pool formation)
- Tillage oxidation decomposition rate multipliers
- IPCC Tier 1 Nitrogen Fertilizer Direct N2O Emissions (1% emission factor, GWP 273)
"""

from typing import List
from soil_carbon_types import (
    FarmFieldParameters,
    SoilTextureType,
    TillagePractice,
    CoverCropStrategy,
    AnnualSoilCarbonPoint,
    AgroecologySimulationResult,
)


class SoilCarbonEngine:
    TILLAGE_DECOMPOSITION_RATE = {
        TillagePractice.CONVENTIONAL_INTENSIVE: 1.45,
        TillagePractice.REDUCED_MINIMUM_TILL: 1.15,
        TillagePractice.NO_TILL: 0.85,
    }

    COVER_CROP_INPUTS_TONS_C_HA = {
        CoverCropStrategy.NONE_FALLOW: 0.0,
        CoverCropStrategy.LEGUME_CRIMSON_CLOVER: 1.8,
        CoverCropStrategy.GRASS_RYE: 2.6,
        CoverCropStrategy.MULTI_SPECIES_POLY: 3.4,
    }

    LEGUME_N_FIXATION_KG_HA = {
        CoverCropStrategy.NONE_FALLOW: 0.0,
        CoverCropStrategy.LEGUME_CRIMSON_CLOVER: 65.0,
        CoverCropStrategy.GRASS_RYE: 15.0,
        CoverCropStrategy.MULTI_SPECIES_POLY: 55.0,
    }

    TEXTURE_PROTECTION_FACTOR = {
        SoilTextureType.CLAY_LOAM: 0.70,
        SoilTextureType.SILT_LOAM: 0.85,
        SoilTextureType.SANDY_LOAM: 1.10,
        SoilTextureType.PEAT_ORGANIC: 0.60,
    }

    @classmethod
    def calculate_initial_soc_stock(cls, params: FarmFieldParameters) -> float:
        # SOC Stock (Tons C / ha) = SOC_pct * BulkDensity (g/cm3) * Depth (cm) * 100
        # 1.8% * 1.35 * 30 * 100 = 72.9 tons C / ha
        return params.baseline_soc_pct * params.bulk_density_g_cm3 * params.sampling_depth_cm * 1.0

    @classmethod
    def simulate(cls, params: FarmFieldParameters) -> AgroecologySimulationResult:
        initial_stock = cls.calculate_initial_soc_stock(params)
        current_stock = initial_stock

        decomp_mult = cls.TILLAGE_DECOMPOSITION_RATE.get(params.tillage_practice, 1.0)
        texture_prot = cls.TEXTURE_PROTECTION_FACTOR.get(params.soil_texture, 0.85)
        cover_c_input = cls.COVER_CROP_INPUTS_TONS_C_HA.get(params.cover_crop_strategy, 0.0)
        compost_c_input = params.compost_addition_dry_tons_per_ha_yr * 0.42  # ~42% Carbon content

        n_fixed_kg_yr = cls.LEGUME_N_FIXATION_KG_HA.get(params.cover_crop_strategy, 0.0) * params.area_hectares
        reduced_synthetic_n = min(params.synthetic_nitrogen_kg_per_ha_yr, n_fixed_kg_yr / params.area_hectares)

        trajectory: List[AnnualSoilCarbonPoint] = []
        cumulative_credits_usd = 0.0

        for yr in range(1, 11):
            # Base native decomposition of labile & humic organic matter (~1.5% base loss)
            annual_loss = current_stock * 0.018 * decomp_mult * texture_prot

            # Annual humified addition (~25% humification efficiency of fresh plant & compost residue)
            annual_gain = (cover_c_input + compost_c_input) * 0.28

            net_delta_c_ha = annual_gain - annual_loss
            current_stock = max(10.0, current_stock + net_delta_c_ha)

            # C to CO2 conversion factor = 44/12 = 3.667
            net_co2e_seq_ha = net_delta_c_ha * 3.667

            # N2O from remaining synthetic fertilizer: 1% emission factor, N2O to CO2e = 273
            active_fert_n = max(0.0, params.synthetic_nitrogen_kg_per_ha_yr - reduced_synthetic_n)
            n2o_kg_ha = active_fert_n * 0.01 * (44.0 / 28.0)
            n2o_co2e_tons_ha = (n2o_kg_ha * 273.0) / 1000.0

            net_ghg_balance_ha = net_co2e_seq_ha - n2o_co2e_tons_ha

            if net_ghg_balance_ha > 0:
                credit_earn_yr = net_ghg_balance_ha * params.area_hectares * params.carbon_credit_price_usd_ton
                cumulative_credits_usd += credit_earn_yr

            trajectory.append(
                AnnualSoilCarbonPoint(
                    year=yr,
                    soc_stock_tons_c_ha=round(current_stock, 2),
                    net_annual_sequestration_tons_co2e_ha=round(net_co2e_seq_ha, 2),
                    n2o_fertilizer_emissions_tons_co2e_ha=round(n2o_co2e_tons_ha, 3),
                    net_ghg_balance_tons_co2e_ha=round(net_ghg_balance_ha, 2),
                    cumulative_carbon_credits_usd=round(cumulative_credits_usd, 2),
                )
            )

        total_seq_tons = (current_stock - initial_stock) * 3.667 * params.area_hectares
        avg_rate_ha = (current_stock - initial_stock) * 3.667 / 10.0

        # Each 1% increase in SOC increases available water capacity by ~3.5%
        soc_pct_gain = ((current_stock - initial_stock) / (params.bulk_density_g_cm3 * params.sampling_depth_cm * 1.0))
        water_capacity_uplift = max(0.0, soc_pct_gain * 3.7)

        return AgroecologySimulationResult(
            field_name=params.field_name,
            area_hectares=params.area_hectares,
            initial_soc_stock_tons_c_ha=round(initial_stock, 2),
            final_soc_stock_tons_c_ha_yr10=round(current_stock, 2),
            net_10yr_carbon_sequestered_tons_co2e=round(total_seq_tons, 2),
            annual_sequestration_rate_tons_co2e_per_ha=round(avg_rate_ha, 2),
            synthetic_n_fertilizer_offset_kg_yr=round(reduced_synthetic_n * params.area_hectares, 1),
            total_carbon_credit_revenue_10yr_usd=round(cumulative_credits_usd, 2),
            soil_water_holding_capacity_uplift_pct=round(water_capacity_uplift, 1),
            trajectory=trajectory,
        )
