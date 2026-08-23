import pandas as pd
from typing import Dict, Tuple

class SmartBuildingLogic:
    """
    Core analytics logic for processing IoT telemetry into sustainability metrics.
    Computes emissions based on real-time grid carbon intensity.
    """

    # Average emissions factor for the grid (kg CO2e per kWh)
    GRID_CARBON_INTENSITY = 0.38 
    
    # Cost per kWh in USD
    ENERGY_COST_PER_KWH = 0.12

    def __init__(self, current_telemetry: pd.DataFrame):
        self.telemetry = current_telemetry

    def calculate_energy_metrics(self) -> pd.DataFrame:
        """
        Converts raw watt observations into hourly kWh aggregates.
        """
        if self.telemetry.empty:
            return pd.DataFrame()

        df = self.telemetry.copy()
        
        # Power is in watts for that hour instance. Treat as Watt-hours to KWh.
        df["energy_kwh"] = df["power_usage_watts"] / 1000.0
        df["carbon_emissions_kg"] = df["energy_kwh"] * self.GRID_CARBON_INTENSITY
        df["cost_usd"] = df["energy_kwh"] * self.ENERGY_COST_PER_KWH

        return df

    def get_floor_aggregates(self) -> pd.DataFrame:
        """Aggregates metrics by floor."""
        metrics = self.calculate_energy_metrics()
        if metrics.empty: return pd.DataFrame()
        
        agg = metrics.groupby("floor").agg({
            "energy_kwh": "sum",
            "carbon_emissions_kg": "sum",
            "cost_usd": "sum"
        }).reset_index()
        return agg

    def get_device_type_aggregates(self) -> pd.DataFrame:
        """Aggregates metrics by device type."""
        metrics = self.calculate_energy_metrics()
        if metrics.empty: return pd.DataFrame()
        
        agg = metrics.groupby("type").agg({
            "energy_kwh": "sum",
            "carbon_emissions_kg": "sum",
            "cost_usd": "sum"
        }).reset_index()
        return agg

    def calculate_building_score(self) -> Dict[str, float]:
        """
        Computes an efficiency score out of 100 based on usage intensity.
        (Mocked algorithm).
        """
        metrics = self.calculate_energy_metrics()
        if metrics.empty:
            return {"score": 0, "total_kwh": 0, "total_co2": 0}

        total_kwh = metrics["energy_kwh"].sum()
        total_co2 = metrics["carbon_emissions_kg"].sum()
        total_cost = metrics["cost_usd"].sum()

        # Simple heuristic for score calculation
        # Lower density of energy per device = higher score
        avg_kwh_per_device_per_hr = total_kwh / len(metrics)
        score = max(0, min(100, 100 - (avg_kwh_per_device_per_hr * 100)))

        return {
            "score": round(score, 1),
            "total_kwh": round(total_kwh, 2),
            "total_co2_kg": round(total_co2, 2),
            "total_cost_usd": round(total_cost, 2),
            "avg_kwh_per_reading": round(avg_kwh_per_device_per_hr, 3)
        }

    def get_time_series_data(self) -> pd.DataFrame:
        """Returns time series of total building energy consumption."""
        metrics = self.calculate_energy_metrics()
        if metrics.empty: return pd.DataFrame()
        
        # Group by timestamp (hour)
        ts_agg = metrics.groupby("timestamp").agg({
            "energy_kwh": "sum",
            "carbon_emissions_kg": "sum"
        }).reset_index()
        return ts_agg
