"""Physics and thermal comfort simulation engine for Passive Bioclimatic Architecture.
"""

import math
from src.energy.passive_comfort_types import (
    BuildingBioclimaticInputs,
    BioclimaticCoolingResult,
    ThermalMassType,
    GlazingOrientation,
)


class PassiveComfortEngine:
    """Calculates diurnal phase shift damping, stack effect airflow, and Fanger PMV/PPD metrics."""

    MASS_DAMPING_FACTORS = {
        ThermalMassType.RAMMED_EARTH_ADOBE: {"decrement_factor": 0.30, "phase_lag_hours": 9.0},
        ThermalMassType.STONE_MASONRY: {"decrement_factor": 0.45, "phase_lag_hours": 6.5},
        ThermalMassType.LIGHTWEIGHT_TIMBER: {"decrement_factor": 0.85, "phase_lag_hours": 2.0},
        ThermalMassType.PHASE_CHANGE_DRYWALL: {"decrement_factor": 0.22, "phase_lag_hours": 10.5},
    }

    ORIENTATION_SOLAR_GAINS = {
        GlazingOrientation.NORTH_OPTIMIZED: 0.15,
        GlazingOrientation.SOUTH_SOLAR_CONTROL: 0.35,
        GlazingOrientation.EAST_WEST_EXPOSED: 0.80,
    }

    @classmethod
    def calculate_thermal_performance(cls, inputs: BuildingBioclimaticInputs) -> BioclimaticCoolingResult:
        mass = cls.MASS_DAMPING_FACTORS.get(inputs.thermal_mass, cls.MASS_DAMPING_FACTORS[ThermalMassType.STONE_MASONRY])
        solar_gain = cls.ORIENTATION_SOLAR_GAINS.get(inputs.glazing_orientation, 0.40)

        # Diurnal temperature swing
        diurnal_swing = max(2.0, inputs.outdoor_day_peak_temp_c - inputs.outdoor_night_min_temp_c)
        outdoor_mean_temp = (inputs.outdoor_day_peak_temp_c + inputs.outdoor_night_min_temp_c) / 2.0

        # Building volume
        volume_m3 = inputs.floor_area_sq_meters * inputs.ceiling_height_meters

        # Indoor peak temperature = Outdoor Mean + (Diurnal Swing / 2) * Decrement Factor + Solar Gain Penalty
        indoor_peak_temp = outdoor_mean_temp + (diurnal_swing / 2.0) * mass["decrement_factor"] + (solar_gain * inputs.window_to_wall_ratio * 6.0)
        temp_drop = max(0.0, inputs.outdoor_day_peak_temp_c - indoor_peak_temp)

        # Natural ventilation stack effect air changes per hour (ACH)
        # Q = C_d * A * sqrt(2 * g * h * (T_in - T_out) / T_avg)
        temp_delta_stack = max(1.0, abs(indoor_peak_temp - inputs.outdoor_night_min_temp_c))
        effective_opening_area = inputs.floor_area_sq_meters * inputs.window_to_wall_ratio * 0.10
        g = 9.81
        h = inputs.ceiling_height_meters * 0.7
        t_avg_k = 273.15 + outdoor_mean_temp
        airflow_m3_s = 0.65 * effective_opening_area * math.sqrt((2 * g * h * temp_delta_stack) / t_avg_k)
        airflow_rate_m3_hr = airflow_m3_s * 3600.0

        # Simplified Fanger PMV calculation for 23-26°C comfort band
        # Neutral comfort baseline = 24.0°C
        pmv = 0.35 * (indoor_peak_temp - 24.0) - (0.20 * (inputs.air_speed_m_s - 0.1))
        pmv = max(-3.0, min(3.0, pmv))

        # PPD = 100 - 95 * exp(- (0.03353 * PMV^4 + 0.2179 * PMV^2))
        ppd = 100.0 - 95.0 * math.exp(-(0.03353 * (pmv ** 4) + 0.2179 * (pmv ** 2)))

        # Cooling energy savings (Sensible load avoided across 120 summer days)
        # Q = Volume * rho * cp * Delta_T * Hours
        # Density of air = 1.2 kg/m3, cp = 1.005 kJ/kg-K
        summer_hours = 120.0 * 8.0  # 8 hours/day peak cooling
        avoided_thermal_kwh = (volume_m3 * 1.2 * 1.005 * temp_drop * summer_hours) / 3600.0
        avoided_electric_kwh = avoided_thermal_kwh / 3.5  # Seasonal COP 3.5 AC

        cost_savings = avoided_electric_kwh * 0.14
        avoided_co2 = avoided_electric_kwh * 0.45  # 0.45 kg CO2/kWh grid baseline

        if ppd <= 10.0:
            rating = "Class A (Exceptional ASHRAE 55 Comfort: PPD ≤ 10%)"
        elif ppd <= 20.0:
            rating = "Class B (Acceptable Living Environment: PPD ≤ 20%)"
        else:
            rating = "Class C (Marginal: Supplemental Night Purge Ventilation Advised)"

        return BioclimaticCoolingResult(
            building_name=inputs.building_name,
            indoor_peak_temperature_c=round(indoor_peak_temp, 2),
            passive_cooling_temperature_drop_c=round(temp_drop, 2),
            fanger_pmv_index=round(pmv, 2),
            predicted_percentage_dissatisfied_ppd=round(ppd, 1),
            natural_ventilation_airflow_rate_m3_hr=round(airflow_rate_m3_hr, 1),
            avoided_cooling_energy_kwh_per_season=round(avoided_electric_kwh, 1),
            annual_cost_savings_usd=round(cost_savings, 2),
            avoided_co2_kg_per_season=round(avoided_co2, 1),
            comfort_category_rating=rating,
        )
