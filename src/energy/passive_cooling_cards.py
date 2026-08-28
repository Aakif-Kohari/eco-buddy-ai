"""UI Scorecard and KPI presentation components for Passive Cooling Simulator.
"""

from typing import Any
from src.energy.passive_cooling_types import PassiveCoolingSimulationResult


def render_passive_cooling_kpis(st: Any, result: PassiveCoolingSimulationResult) -> None:
    """Renders high-impact summary metric cards."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Annual Energy Saved",
            value=f"{result.annual_energy_saved_kwh:,.0f} kWh",
            delta=f"{result.energy_savings_percentage:.1f}% reduction",
            delta_color="normal",
        )

    with col2:
        st.metric(
            label="Annual Bill Savings",
            value=f"${result.annual_cost_savings_usd:,.2f}",
            delta=f"ROI Payback: {result.simple_payback_years:.1f} yrs",
            delta_color="inverse" if result.simple_payback_years > 10 else "normal",
        )

    with col3:
        st.metric(
            label="CO₂ Emissions Abated",
            value=f"{result.annual_co2_abatement_kg:,.0f} kg",
            delta=f"Peak Temp Cut: -{result.peak_indoor_temp_reduction_c:.1f} °C",
            delta_color="normal",
        )

    with col4:
        st.metric(
            label="Heatwave Resilience",
            value=f"{result.thermal_resilience_hours_during_heatwave} hrs",
            delta=f"+{result.hours_in_comfort_zone_passive - result.hours_in_comfort_zone_unconditioned} Comfort Hrs",
            delta_color="normal",
        )


def render_envelope_efficiency_badge(st: Any, result: PassiveCoolingSimulationResult) -> None:
    """Renders dynamic bioclimatic architectural rating."""
    if result.energy_savings_percentage >= 50.0:
        badge_color = "#10b981"
        tier = "🌿 Platinum Passivhaus Standard"
        desc = "Exceptional passive thermal equilibrium with minimal active HVAC dependency."
    elif result.energy_savings_percentage >= 30.0:
        badge_color = "#3b82f6"
        tier = "⚡ Gold Bioclimatic Standard"
        desc = "Substantial cooling load offset through balanced shading and natural ventilation."
    else:
        badge_color = "#f59e0b"
        tier = "🥉 Silver Basic Retrofit"
        desc = "Moderate thermal buffer. Consider upgrading window shading and nocturnal purge."

    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(59, 130, 246, 0.08) 100%);
                    border-left: 5px solid {badge_color}; padding: 16px; border-radius: 8px; margin: 15px 0;">
            <h4 style="margin: 0 0 6px 0; color: {badge_color};">{tier}</h4>
            <p style="margin: 0; font-size: 0.95rem; color: #4b5563;">{desc}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
