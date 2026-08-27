"""Core calculation engine for Building Passive Cooling and Thermal Comfort Simulation.

Implements heat transfer calculations:
- Conduction through building envelope (Q = U * A * deltaT)
- Solar heat gain coefficients (SHGC) & shading attenuation
- Thermal mass dampening and diurnal phase lag
- Natural ventilation convective cooling rate
- Fanger PMV/PPD thermal comfort index approximations
"""

import math
from typing import List, Tuple
from src.energy.passive_cooling_types import (
    BuildingParameters,
    ClimateZone,
    InsulationLevel,
    ShadingStrategy,
    VentilationMode,
    HourlyComfortPoint,
    PassiveCoolingSimulationResult,
)


class PassiveCoolingEngine:
    U_VALUES = {
        InsulationLevel.UNINSULATED: 4.8,
        InsulationLevel.STANDARD: 2.2,
        InsulationLevel.HIGH_PERFORMANCE: 1.2,
        InsulationLevel.PASSIVE_HOUSE: 0.65,
    }

    SHADING_COEFFICIENTS = {
        ShadingStrategy.NONE: 0.85,
        ShadingStrategy.OVERHANG: 0.45,
        ShadingStrategy.LOUVERS: 0.20,
        ShadingStrategy.EXTERIOR_VEGETATION: 0.32,
        ShadingStrategy.LOW_E_SOLAR_FILM: 0.38,
    }

    VENTILATION_HEAT_REMOVAL_COEFF = {
        VentilationMode.SEALED_AC: 1.0,
        VentilationMode.NIGHT_PURGE: 3.8,
        VentilationMode.CROSS_VENTILATION: 3.2,
        VentilationMode.THERMAL_CHIMNEY: 4.5,
    }

    RETROFIT_COSTS_PER_M2 = {
        ShadingStrategy.NONE: 0.0,
        ShadingStrategy.OVERHANG: 35.0,
        ShadingStrategy.LOUVERS: 85.0,
        ShadingStrategy.EXTERIOR_VEGETATION: 25.0,
        ShadingStrategy.LOW_E_SOLAR_FILM: 18.0,
    }

    @classmethod
    def generate_diurnal_weather_profile(cls, climate: ClimateZone) -> List[Tuple[float, float, float]]:
        """Returns 24-hr list of (outdoor_temp_c, humidity_pct, solar_radiation_w_m2)."""
        profiles = {
            ClimateZone.HOT_ARID: {"base": 32.0, "swing": 14.0, "peak_h": 15, "hum": 22.0, "max_sol": 950.0},
            ClimateZone.HOT_HUMID: {"base": 29.0, "swing": 7.0, "peak_h": 14, "hum": 78.0, "max_sol": 820.0},
            ClimateZone.TEMPERATE: {"base": 23.0, "swing": 9.0, "peak_h": 14, "hum": 55.0, "max_sol": 750.0},
            ClimateZone.CONTINENTAL: {"base": 26.0, "swing": 12.0, "peak_h": 15, "hum": 45.0, "max_sol": 850.0},
            ClimateZone.MEDITERRANEAN: {"base": 28.0, "swing": 11.0, "peak_h": 15, "hum": 40.0, "max_sol": 900.0},
        }
        cfg = profiles.get(climate, profiles[ClimateZone.TEMPERATE])
        points = []
        for h in range(24):
            # Diurnal sinusoidal temperature cycle
            rad = (h - 9) * math.pi / 12.0
            temp = cfg["base"] + (cfg["swing"] / 2.0) * math.sin(rad)
            # Solar radiation curve between 6am and 18pm
            if 6 <= h <= 18:
                sol_rad = math.sin((h - 6) * math.pi / 12.0)
                sol = cfg["max_sol"] * max(0.0, sol_rad)
            else:
                sol = 0.0
            # Inverse humidity swing
            hum = max(15.0, min(95.0, cfg["hum"] - 0.4 * (temp - cfg["base"])))
            points.append((round(temp, 2), round(hum, 1), round(sol, 1)))
        return points

    @classmethod
    def calculate_pmv_ppd(cls, indoor_temp: float, humidity_pct: float, air_vel: float = 0.2) -> Tuple[float, float]:
        """Calculates approximate ISO 7730 PMV (Predicted Mean Vote) & PPD."""
        # Simplified Fanger model for sedentary office/domestic conditions (1.1 met, 0.6 clo)
        optimal_temp = 24.5 - (0.015 * (humidity_pct - 50.0)) + (1.2 * math.sqrt(air_vel))
        pmv = (indoor_temp - optimal_temp) * 0.38
        pmv = max(-3.0, min(3.0, pmv))
        # PPD formula
        ppd = 100.0 - 95.0 * math.exp(-0.03353 * (pmv**4) - 0.2179 * (pmv**2))
        return round(pmv, 2), round(ppd, 1)

    @classmethod
    def simulate(cls, params: BuildingParameters) -> PassiveCoolingSimulationResult:
        """Runs building heat transfer balance and passive cooling performance simulation."""
        u_val = cls.U_VALUES.get(params.insulation_level, 2.2)
        shgc = cls.SHADING_COEFFICIENTS.get(params.shading_strategy, 0.85)
        vent_mult = cls.VENTILATION_HEAT_REMOVAL_COEFF.get(params.ventilation_mode, 1.0)

        envelope_area = params.floor_area_m2 * 2.2  # Approximate exterior envelope ratio
        window_area = envelope_area * params.window_to_wall_ratio

        weather_24 = cls.generate_diurnal_weather_profile(params.climate_zone)
        hourly_records: List[HourlyComfortPoint] = []

        total_saved_kwh_day = 0.0
        baseline_cooling_kwh_day = 0.0
        passive_cooling_kwh_day = 0.0
        peak_temp_baseline = -100.0
        peak_temp_passive = -100.0
        comfort_hours_base = 0
        comfort_hours_passive = 0

        # Thermal mass time lag constant (hours)
        mass_damping = min(0.75, params.thermal_mass_capacity_kj_m2_k / 350.0)

        for h, (t_out, hum, sol) in enumerate(weather_24):
            # Baseline (Unconditioned envelope without passive strategy)
            internal_heat_kw = (params.internal_heat_gain_w_per_m2 * params.floor_area_m2 + params.occupant_count * 100.0) / 1000.0
            solar_heat_base_kw = (sol * window_area * 0.85) / 1000.0
            conduction_base_kw = (4.8 * envelope_area * (t_out - 22.0)) / 1000.0

            # Passive Envelope Strategy
            solar_heat_passive_kw = (sol * window_area * shgc) / 1000.0
            conduction_passive_kw = (u_val * envelope_area * (t_out - 22.0)) / 1000.0

            # Ventilation heat flush during night (20h to 7h) or cross-vent
            is_night = (h >= 20 or h <= 7)
            if is_night and params.ventilation_mode in [VentilationMode.NIGHT_PURGE, VentilationMode.THERMAL_CHIMNEY]:
                vent_flush_kw = (1.2 * params.air_changes_per_hour * params.floor_area_m2 * params.ceiling_height_m * vent_mult * max(0.0, 24.0 - t_out)) / 3600.0
            elif params.ventilation_mode == VentilationMode.CROSS_VENTILATION:
                vent_flush_kw = (1.0 * params.air_changes_per_hour * params.floor_area_m2 * params.ceiling_height_m * 2.5 * max(0.0, 25.0 - t_out)) / 3600.0
            else:
                vent_flush_kw = 0.0

            # Thermal indoor temperatures
            t_in_base = t_out + (solar_heat_base_kw + internal_heat_kw) * 0.45
            # Passive temperature damped by thermal mass and shading
            t_in_passive = (t_out * (1 - mass_damping) + 22.5 * mass_damping) + (solar_heat_passive_kw + internal_heat_kw - vent_flush_kw) * 0.28
            t_in_passive = max(18.0, min(t_in_passive, t_in_base))

            peak_temp_baseline = max(peak_temp_baseline, t_in_base)
            peak_temp_passive = max(peak_temp_passive, t_in_passive)

            # HVAC COP assumed 3.2
            cop = 3.2
            cooling_need_base = max(0.0, (t_in_base - 24.0) * params.floor_area_m2 * 0.08) / cop
            cooling_need_passive = max(0.0, (t_in_passive - 24.0) * params.floor_area_m2 * 0.08) / cop
            kwh_saved_h = max(0.0, cooling_need_base - cooling_need_passive)

            baseline_cooling_kwh_day += cooling_need_base
            passive_cooling_kwh_day += cooling_need_passive
            total_saved_kwh_day += kwh_saved_h

            pmv, ppd = cls.calculate_pmv_ppd(t_in_passive, hum, air_vel=0.4 if params.ventilation_mode != VentilationMode.SEALED_AC else 0.15)
            if 20.0 <= t_in_base <= 26.0:
                comfort_hours_base += 1
            if 20.0 <= t_in_passive <= 26.0:
                comfort_hours_passive += 1

            hourly_records.append(
                HourlyComfortPoint(
                    hour=h,
                    outdoor_temp_c=t_out,
                    outdoor_humidity_pct=hum,
                    solar_radiation_w_m2=sol,
                    indoor_temp_unconditioned_c=round(t_in_base, 2),
                    indoor_temp_passive_c=round(t_in_passive, 2),
                    predicted_mean_vote_pmv=pmv,
                    predicted_percentage_dissatisfied_ppd=ppd,
                    cooling_load_saved_kwh=round(kwh_saved_h, 3),
                )
            )

        # Extrapolate to 365 days (hot/cooling season scaling factor ~ 180 days)
        cooling_season_days = 200.0
        annual_baseline_kwh = baseline_cooling_kwh_day * cooling_season_days
        annual_passive_kwh = passive_cooling_kwh_day * cooling_season_days
        annual_saved_kwh = annual_baseline_kwh - annual_passive_kwh
        savings_pct = (annual_saved_kwh / max(1.0, annual_baseline_kwh)) * 100.0

        cost_saved_usd = annual_saved_kwh * params.electricity_cost_kwh
        co2_abated_kg = annual_saved_kwh * params.grid_emission_factor_kg_kwh

        # Capex calculation
        capex_shading = cls.RETROFIT_COSTS_PER_M2.get(params.shading_strategy, 0.0) * window_area
        capex_insulation = (50.0 if params.insulation_level == InsulationLevel.HIGH_PERFORMANCE else (90.0 if params.insulation_level == InsulationLevel.PASSIVE_HOUSE else 0.0)) * envelope_area
        total_capex = max(250.0, capex_shading + capex_insulation)
        payback = total_capex / max(1.0, cost_saved_usd)

        # Strategy breakdown
        shading_saving_share = 45.0 if params.shading_strategy != ShadingStrategy.NONE else 5.0
        vent_saving_share = 35.0 if params.ventilation_mode != VentilationMode.SEALED_AC else 5.0
        mass_saving_share = 100.0 - shading_saving_share - vent_saving_share

        return PassiveCoolingSimulationResult(
            building_name=params.building_name,
            annual_cooling_energy_baseline_kwh=round(annual_baseline_kwh, 1),
            annual_cooling_energy_passive_kwh=round(annual_passive_kwh, 1),
            annual_energy_saved_kwh=round(annual_saved_kwh, 1),
            energy_savings_percentage=round(savings_pct, 1),
            annual_cost_savings_usd=round(cost_saved_usd, 2),
            annual_co2_abatement_kg=round(co2_abated_kg, 1),
            peak_indoor_temp_reduction_c=round(peak_temp_baseline - peak_temp_passive, 2),
            hours_in_comfort_zone_unconditioned=int(comfort_hours_base * (cooling_season_days / 24.0 * 24.0)),
            hours_in_comfort_zone_passive=int(comfort_hours_passive * (cooling_season_days / 24.0 * 24.0)),
            thermal_resilience_hours_during_heatwave=int(18 + (params.thermal_mass_capacity_kj_m2_k / 20.0)),
            estimated_retrofit_capex_usd=round(total_capex, 2),
            simple_payback_years=round(payback, 2),
            hourly_profiles=hourly_records,
            strategy_breakdown_pct={
                "Solar Shading & Glazing": shading_saving_share,
                "Natural & Night Ventilation": vent_saving_share,
                "Thermal Mass & Insulation": mass_saving_share,
            },
        )
