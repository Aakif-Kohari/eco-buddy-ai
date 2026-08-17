"""
Microgrid & Residential BESS (Battery Energy Storage System) Simulator for EcoBuddy AI
Optimizes rooftop solar self-consumption, calculates peak-shaving cost/carbon savings,
and simulates battery degradation lifecycle.
"""

from typing import Dict, List, Any, Optional

BATTERY_CHEMISTRIES = {
    "lfp": {"name": "Lithium Iron Phosphate (LFP)", "round_trip_efficiency": 0.92, "cycle_life": 6000, "depth_of_discharge": 0.90},
    "nmc": {"name": "Nickel Manganese Cobalt (NMC)", "round_trip_efficiency": 0.90, "cycle_life": 3500, "depth_of_discharge": 0.85},
    "sodium_ion": {"name": "Sodium-Ion (Na-Ion)", "round_trip_efficiency": 0.86, "cycle_life": 4500, "depth_of_discharge": 0.95}
}


class MicrogridStorageSimulator:
    """Simulates 24-hour solar + storage dispatch, grid arbitrage, and carbon abatement."""

    def __init__(self, chemistries: Optional[Dict[str, Dict[str, Any]]] = None):
        self.chemistries = chemistries or BATTERY_CHEMISTRIES

    def simulate_daily_dispatch(
        self,
        solar_capacity_kw: float,
        battery_capacity_kwh: float,
        daily_consumption_kwh: float,
        battery_chemistry: str = "lfp",
        grid_peak_rate_usd: float = 0.35,
        grid_offpeak_rate_usd: float = 0.12,
        grid_carbon_intensity_gco2: float = 450.0
    ) -> Dict[str, Any]:
        """
        Simulates 24-hour generation, storage dispatch, and cost/carbon savings.
        """
        chem = self.chemistries.get(battery_chemistry.lower(), self.chemistries["lfp"])

        # Estimated daily solar generation (~4.2 peak sun hours average)
        daily_solar_generation_kwh = round(solar_capacity_kw * 4.2, 2)
        
        # Self-consumption without battery: ~30%
        direct_solar_consumed_kwh = round(min(daily_consumption_kwh * 0.35, daily_solar_generation_kwh), 2)
        surplus_solar_kwh = max(daily_solar_generation_kwh - direct_solar_consumed_kwh, 0.0)

        # Usable battery capacity
        usable_battery_kwh = battery_capacity_kwh * chem["depth_of_discharge"]
        battery_stored_kwh = min(surplus_solar_kwh, usable_battery_kwh)
        battery_discharged_kwh = round(battery_stored_kwh * chem["round_trip_efficiency"], 2)

        total_clean_energy_used_kwh = round(direct_solar_consumed_kwh + battery_discharged_kwh, 2)
        remaining_grid_demand_kwh = max(round(daily_consumption_kwh - total_clean_energy_used_kwh, 2), 0.0)

        # Solar self-sufficiency percentage
        self_sufficiency_pct = round((total_clean_energy_used_kwh / daily_consumption_kwh * 100) if daily_consumption_kwh > 0 else 0, 1)

        # Financial savings (avoiding peak electricity tariffs)
        daily_peak_avoided_cost = round(battery_discharged_kwh * grid_peak_rate_usd, 2)
        daily_direct_avoided_cost = round(direct_solar_consumed_kwh * ((grid_peak_rate_usd + grid_offpeak_rate_usd) / 2.0), 2)
        annual_financial_savings_usd = round((daily_peak_avoided_cost + daily_direct_avoided_cost) * 365, 2)

        # Carbon abatement
        annual_carbon_abatement_kg = round((total_clean_energy_used_kwh * 365 * grid_carbon_intensity_gco2) / 1000.0, 2)

        return {
            "battery_chemistry": chem["name"],
            "daily_solar_gen_kwh": daily_solar_generation_kwh,
            "direct_solar_consumed_kwh": direct_solar_consumed_kwh,
            "battery_charged_kwh": round(battery_stored_kwh, 2),
            "battery_discharged_kwh": battery_discharged_kwh,
            "remaining_grid_demand_kwh": remaining_grid_demand_kwh,
            "self_sufficiency_pct": self_sufficiency_pct,
            "annual_financial_savings_usd": annual_financial_savings_usd,
            "annual_carbon_abatement_kg": annual_carbon_abatement_kg,
            "expected_battery_lifespan_years": round(chem["cycle_life"] / 365.0, 1)
        }
