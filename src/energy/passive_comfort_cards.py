"""UI KPI Cards for Bioclimatic Passive Cooling.
"""

from typing import Any
from src.energy.passive_comfort_types import BioclimaticCoolingResult


def render_passive_comfort_kpis(st: Any, result: BioclimaticCoolingResult) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Peak Indoor Temperature",
            value=f"{result.indoor_peak_temperature_c:.1f} °C",
            delta=f"-{result.passive_cooling_temperature_drop_c:.1f} °C vs Outdoor",
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="Thermal Comfort (Fanger PMV)",
            value=f"{result.fanger_pmv_index:+.2f}",
            delta=f"PPD: {result.predicted_percentage_dissatisfied_ppd:.1f}%",
            delta_color="normal" if result.predicted_percentage_dissatisfied_ppd <= 15.0 else "inverse",
        )

    with col3:
        st.metric(
            label="Natural Airflow (Night Purge)",
            value=f"{result.natural_ventilation_airflow_rate_m3_hr:,.0f} m³/h",
            delta="Stack Effect Driven",
            delta_color="normal",
        )

    with col4:
        st.metric(
            label="Avoided AC Energy",
            value=f"{result.avoided_cooling_energy_kwh_per_season:,.0f} kWh",
            delta=f"${result.annual_cost_savings_usd:.2f} Saved/yr",
            delta_color="normal",
        )
