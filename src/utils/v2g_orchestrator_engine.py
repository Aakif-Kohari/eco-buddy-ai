"""Optimization and Simulation Engine for Vehicle-to-Grid (V2G) Bi-Directional Charging.

Implements:
- Linear dispatch rule optimization for dynamic TOU pricing
- Battery calendar and cycling degradation (Rainflow/Ah throughput heuristic)
- Renewable solar generation tracking & self-consumption matching
- Avoided fossil peaker plant Scope 2 carbon calculus
"""

import math
from typing import List, Tuple
from src.utils.v2g_orchestrator_types import (
    FleetVehicleConfig,
    BatteryChemistry,
    ChargingTariffScheme,
    GridServiceMode,
    V2GHourlyDispatch,
    V2GOrchestrationResult,
)


class V2GOrchestratorEngine:
    CHEMISTRY_CYCLE_LIFE = {
        BatteryChemistry.LFP: 4500,
        BatteryChemistry.NMC_811: 2000,
        BatteryChemistry.NCA: 1800,
        BatteryChemistry.SOLID_STATE: 6500,
    }

    TARIFF_HOURLY_PRICES = {
        ChargingTariffScheme.TIME_OF_USE_AGGRESSIVE: [
            0.08, 0.08, 0.08, 0.08, 0.08, 0.12,  # 00-05: Off peak
            0.18, 0.25, 0.22, 0.20, 0.18, 0.18,  # 06-11: Mid peak
            0.16, 0.16, 0.22, 0.28, 0.42, 0.48,  # 12-17: On peak afternoon
            0.45, 0.38, 0.28, 0.20, 0.12, 0.08   # 18-23: Evening peak & wind down
        ],
        ChargingTariffScheme.TIME_OF_USE_MODERATE: [
            0.12, 0.12, 0.12, 0.12, 0.12, 0.14,
            0.18, 0.24, 0.24, 0.22, 0.20, 0.20,
            0.20, 0.20, 0.22, 0.28, 0.32, 0.34,
            0.32, 0.28, 0.22, 0.18, 0.14, 0.12
        ],
        ChargingTariffScheme.FIXED_FLAT: [0.18] * 24,
    }

    @classmethod
    def simulate_fleet(
        cls,
        fleet_size: int,
        vehicle_cfg: FleetVehicleConfig,
        tariff_scheme: ChargingTariffScheme,
        service_mode: GridServiceMode,
        rooftop_solar_peak_kw: float,
    ) -> V2GOrchestrationResult:
        prices = cls.TARIFF_HOURLY_PRICES.get(tariff_scheme, cls.TARIFF_HOURLY_PRICES[ChargingTariffScheme.TIME_OF_USE_AGGRESSIVE])
        total_fleet_capacity_kwh = fleet_size * vehicle_cfg.battery_capacity_kwh

        # Initial conditions (fleet arrives in evening with 50% SoC)
        current_soc_kwh = total_fleet_capacity_kwh * 0.50
        min_kwh = total_fleet_capacity_kwh * (vehicle_cfg.min_allowable_soc_pct / 100.0)
        max_kwh = total_fleet_capacity_kwh * 0.95
        target_departure_kwh = total_fleet_capacity_kwh * (vehicle_cfg.target_departure_soc_pct / 100.0)

        max_fleet_charge_kw = fleet_size * vehicle_cfg.max_charge_power_kw
        max_fleet_discharge_kw = fleet_size * vehicle_cfg.max_discharge_power_kw
        eta = vehicle_cfg.round_trip_efficiency_pct / 100.0

        hourly_records: List[V2GHourlyDispatch] = []
        daily_charging_cost = 0.0
        daily_discharging_rev = 0.0
        daily_throughput_kwh = 0.0
        daily_avoided_co2_kg = 0.0
        total_solar_used_kwh = 0.0
        total_solar_gen_kwh = 0.0

        for h in range(24):
            price = prices[h]
            # Grid emission factor: higher during peaker hours
            grid_g_kwh = 350.0 + 300.0 * (price / max(prices))

            # Solar curve peak at noon
            if 6 <= h <= 18:
                solar_kw = rooftop_solar_peak_kw * math.sin((h - 6) * math.pi / 12.0)
            else:
                solar_kw = 0.0
            total_solar_gen_kwh += solar_kw

            # Decision Logic: Charge vs Discharge
            charge_kw = 0.0
            discharge_kw = 0.0

            # Off-peak hours (midnight to 5am): aggressive charging
            if 0 <= h <= 5 or (solar_kw > 20.0 and service_mode == GridServiceMode.SOLAR_SELF_CONSUMPTION):
                needed_kwh = max(0.0, target_departure_kwh - current_soc_kwh)
                possible_kw = min(max_fleet_charge_kw, needed_kwh / math.sqrt(eta))
                charge_kw = possible_kw
                current_soc_kwh = min(max_kwh, current_soc_kwh + charge_kw * math.sqrt(eta))
                daily_charging_cost += charge_kw * price
                daily_throughput_kwh += charge_kw
                total_solar_used_kwh += min(solar_kw, charge_kw)

            # Peak afternoon/evening hours (16:00 to 20:00): Discharge to grid
            elif 16 <= h <= 20 and service_mode in [GridServiceMode.ARBITRAGE_ONLY, GridServiceMode.PEAK_DEMAND_SHAVING, GridServiceMode.FREQUENCY_REGULATION]:
                avail_discharge_kwh = max(0.0, current_soc_kwh - min_kwh)
                discharge_kw = min(max_fleet_discharge_kw, avail_discharge_kwh * math.sqrt(eta))
                current_soc_kwh = max(min_kwh, current_soc_kwh - discharge_kw / math.sqrt(eta))
                daily_discharging_rev += discharge_kw * price
                daily_throughput_kwh += discharge_kw
                # Avoided peaker plant emissions (600g/kWh displaced)
                daily_avoided_co2_kg += (discharge_kw * 0.60)

            # Day commute usage deduction (7:00 to 9:00)
            if h == 8:
                current_soc_kwh = max(min_kwh, current_soc_kwh - (fleet_size * vehicle_cfg.daily_commute_kwh))

            net_grid_kw = charge_kw - discharge_kw - solar_kw
            soc_pct = (current_soc_kwh / max(1.0, total_fleet_capacity_kwh)) * 100.0

            hourly_records.append(
                V2GHourlyDispatch(
                    hour=h,
                    tariff_price_usd_kwh=price,
                    grid_carbon_intensity_g_kwh=round(grid_g_kwh, 1),
                    solar_generation_kw=round(solar_kw, 1),
                    fleet_charging_kw=round(charge_kw, 1),
                    fleet_discharging_kw=round(discharge_kw, 1),
                    net_grid_exchange_kw=round(net_grid_kw, 1),
                    average_fleet_soc_pct=round(soc_pct, 1),
                    cumulative_cashflow_usd=round(daily_discharging_rev - daily_charging_cost, 2),
                )
            )

        annual_days = 365.0
        annual_rev = daily_discharging_rev * annual_days
        annual_cost = daily_charging_cost * annual_days
        net_profit = annual_rev - annual_cost
        annual_co2_tons = (daily_avoided_co2_kg * annual_days) / 1000.0

        # Degradation heuristic: Equivalent full cycles per year
        eff_cycles_per_year = (daily_throughput_kwh * annual_days) / max(1.0, 2.0 * total_fleet_capacity_kwh)
        max_cycles = cls.CHEMISTRY_CYCLE_LIFE.get(vehicle_cfg.chemistry, 3000)
        annual_degradation_pct = (eff_cycles_per_year / max_cycles) * 20.0  # to 80% EOL
        cycle_life_years = max_cycles / max(1.0, eff_cycles_per_year)

        solar_self_consump = (total_solar_used_kwh / max(1.0, total_solar_gen_kwh)) * 100.0

        return V2GOrchestrationResult(
            fleet_size=fleet_size,
            total_fleet_capacity_kwh=round(total_fleet_capacity_kwh, 1),
            annual_grid_revenue_usd=round(annual_rev, 2),
            annual_charging_cost_usd=round(annual_cost, 2),
            net_annual_arbitrage_profit_usd=round(net_profit, 2),
            annual_co2_avoided_tons=round(annual_co2_tons, 2),
            annual_battery_degradation_pct=round(annual_degradation_pct, 2),
            estimated_battery_cycle_life_years=round(cycle_life_years, 1),
            solar_self_consumption_pct=round(min(100.0, solar_self_consump), 1),
            hourly_schedule=hourly_records,
        )
