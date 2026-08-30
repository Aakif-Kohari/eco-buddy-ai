"""UI Scorecards and visual indicator renderers for Urban Canopy Planner.
"""

from typing import Any
from src.environment.urban_canopy_types import CanopyCoolingResult


def render_canopy_impact_cards(st: Any, result: CanopyCoolingResult) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Ambient Air Cooling",
            value=f"-{result.ambient_air_temperature_reduction_c:.2f} °C",
            delta=f"Surface: -{result.surface_temperature_reduction_c:.2f} °C",
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="Trees Required",
            value=f"{result.species_tree_count_recommended:,} Trees",
            delta=result.thermal_comfort_improvement_index.split(":")[0],
            delta_color="normal",
        )

    with col3:
        st.metric(
            label="Carbon Sequestration",
            value=f"{result.annual_carbon_sequestration_kg_co2:,.1f} kg/yr",
            delta=f"Cooling: {result.evapotranspiration_cooling_kwh_per_year:,.0f} kWh/yr",
            delta_color="normal",
        )

    with col4:
        st.metric(
            label="Stormwater Captured",
            value=f"{result.stormwater_runoff_absorbed_cubic_meters:,.1f} m³",
            delta=f"${result.cooling_energy_savings_usd:,.2f} AC Saved",
            delta_color="normal",
        )
