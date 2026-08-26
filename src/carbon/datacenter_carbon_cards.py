"""UI KPI scorecards and badge renderers for Green Data Center and AI Carbon Profiler.
"""

from typing import Any
from src.carbon.datacenter_carbon_types import AIWorkloadCarbonResult


def render_datacenter_carbon_kpis(st: Any, result: AIWorkloadCarbonResult) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Carbon Footprint",
            value=f"{result.total_footprint_kg_co2:,.1f} kg CO₂e",
            delta=f"Scope 3: {result.embodied_hardware_emissions_kg_co2:.1f} kg",
            delta_color="inverse",
        )

    with col2:
        st.metric(
            label="Facility Energy (PUE Adjusted)",
            value=f"{result.total_facility_energy_kwh:,.0f} kWh",
            delta=f"Effective PUE: {result.effective_pue:.3f}",
            delta_color="normal" if result.effective_pue <= 1.15 else "inverse",
        )

    with col3:
        st.metric(
            label="Water Consumption",
            value=f"{result.water_consumption_liters:,.0f} L",
            delta=f"{result.emissions_per_million_tokens_g:.2f} g CO₂/M Tokens",
            delta_color="normal",
        )

    with col4:
        best_save = result.green_region_alternatives[0].carbon_reduction_pct if result.green_region_alternatives else 0.0
        st.metric(
            label="Optimal Migration Gain",
            value=f"-{best_save:.1f}% CO₂e",
            delta=f"Offset Cost: ${result.carbon_offset_cost_usd:.2f}",
            delta_color="normal",
        )


def render_pue_efficiency_badge(st: Any, pue: float) -> None:
    if pue <= 1.10:
        color = "#10b981"
        title = "🌱 Ultra-Green Data Center Class (PUE ≤ 1.10)"
        desc = "Leveraging advanced liquid/immersion cooling and optimized thermal loops."
    elif pue <= 1.25:
        color = "#3b82f6"
        title = "⚡ Standard Modern Hyper-scale Class (PUE 1.11 - 1.25)"
        desc = "Solid energy performance with contained hot/cold aisle architecture."
    else:
        color = "#ef4444"
        title = "⚠️ Legacy High Overhead Infrastructure (PUE > 1.25)"
        desc = "Significant parasitic cooling overhead. Migration or cooling retrofit recommended."

    st.markdown(
        f"""
        <div style="background-color: rgba(0,0,0,0.03); border-left: 5px solid {color};
                    padding: 14px; border-radius: 6px; margin: 10px 0;">
            <strong style="color: {color}; font-size: 1.05rem;">{title}</strong>
            <p style="margin: 4px 0 0 0; color: #4b5563; font-size: 0.9rem;">{desc}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
