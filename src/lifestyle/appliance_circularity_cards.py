"""UI Scorecards and visual indicators for Appliance Circularity.
"""

from typing import Any
from src.lifestyle.appliance_circularity_types import CircularityEvaluationResult


def render_appliance_circularity_kpis(st: Any, result: CircularityEvaluationResult) -> None:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Recommended Strategy",
            value=result.recommended_decision,
            delta=f"Circularity Score: {result.lifecycle_circularity_score:.1f}/100",
            delta_color="normal" if "Repair" in result.recommended_decision else "off",
        )

    with col2:
        st.metric(
            label="Embodied Carbon Saved",
            value=f"{result.embodied_carbon_saved_by_repair_kg:,.0f} kg CO₂e",
            delta="Avoided New Manufacturing",
            delta_color="normal",
        )

    with col3:
        st.metric(
            label="2-Year Failure Hazard",
            value=f"{result.failure_probability_next_2yrs_pct:.1f}%",
            delta="Weibull Conditional Risk",
            delta_color="inverse" if result.failure_probability_next_2yrs_pct > 30.0 else "normal",
        )

    with col4:
        st.metric(
            label="Residual Economic Value",
            value=f"${result.residual_economic_value_usd:.2f}",
            delta=f"Payback: {result.repair_economic_payback_years:.1f} yrs",
            delta_color="normal",
        )
