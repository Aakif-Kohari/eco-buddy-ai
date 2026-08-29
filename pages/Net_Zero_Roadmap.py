"""
Net-Zero Roadmap Page.
Streamlit page displaying a Gantt-style roadmap chart, gap analysis metrics, and milestone tracking.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from src.carbon.emissions_gap_analyzer import EmissionsGapAnalyzer
from src.utils.net_zero_roadmap_generator import NetZeroRoadmapGenerator
from src.core.database import save_net_zero_roadmap, get_roadmap_history

st.set_page_config(page_title="Net-Zero Roadmap", page_icon="🗺️", layout="wide")

st.title("🗺️ Corporate Net-Zero Gap Analysis & Roadmap Generator")
st.markdown(
    "Bridge the gap between your current GHG inventory and a certified Net-Zero target with a dynamic, year-by-year reduction plan."
)

# --- Input Section ---
st.sidebar.header("🏢 Company Emissions Profile")
scope1 = st.sidebar.number_input(
    "Scope 1 Emissions (tonnes CO₂e)", min_value=0.0, step=10.0, value=500.0
)
scope2 = st.sidebar.number_input(
    "Scope 2 Emissions (tonnes CO₂e)", min_value=0.0, step=10.0, value=300.0
)
scope3 = st.sidebar.number_input(
    "Scope 3 Emissions (tonnes CO₂e)", min_value=0.0, step=50.0, value=2000.0
)
target_year = st.sidebar.number_input(
    "Target Net-Zero Year", min_value=2025, max_value=2060, step=1, value=2040
)

if st.sidebar.button("🚀 Generate Roadmap", type="primary"):
    analyzer = EmissionsGapAnalyzer(scope1, scope2, scope3, target_year)
    generator = NetZeroRoadmapGenerator(analyzer)
    result = generator.generate_roadmap()

    if "error" in result:
        st.error(result["error"])
    else:
        st.session_state.roadmap_result = result
        save_net_zero_roadmap(scope1, scope2, scope3, target_year, result)
        st.success("Roadmap generated and saved successfully!")

# --- Results Display ---
if "roadmap_result" in st.session_state:
    result = st.session_state.roadmap_result
    gap = result["gap_analysis"]

    st.divider()
    st.subheader("📊 Gap Analysis Summary")

    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Total Current Emissions", f"{gap['total_current_emissions']:,.0f} tonnes"
    )
    col2.metric(
        "Required Annual Reduction",
        f"{gap['required_annual_reduction_pct']:.1f}%",
        help="Compound annual reduction needed to reach 1% of current emissions by target year.",
    )
    col3.metric("Feasibility", gap["feasibility"].split("(")[0].strip())

    # Scope Breakdown Pie Chart
    st.markdown("### Current Emissions Breakdown")
    fig_pie = go.Figure(
        data=[
            go.Pie(
                labels=[
                    "Scope 1 (Direct)",
                    "Scope 2 (Electricity)",
                    "Scope 3 (Value Chain)",
                ],
                values=[
                    result["scope_breakdown"]["scope1_pct"],
                    result["scope_breakdown"]["scope2_pct"],
                    result["scope_breakdown"]["scope3_pct"],
                ],
                hole=0.4,
            )
        ]
    )
    fig_pie.update_layout(template="plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()
    st.subheader("🗺️ Year-by-Year Reduction Roadmap")

    # Prepare data for trajectory chart
    years = [2024] + [step["year"] for step in result["roadmap"]]
    emissions = [gap["total_current_emissions"]] + [
        step["projected_emissions"] for step in result["roadmap"]
    ]

    fig_line = go.Figure()
    fig_line.add_trace(
        go.Scatter(
            x=years,
            y=emissions,
            mode="lines+markers",
            name="Projected Emissions",
            line=dict(color="#2ca02c", width=3),
            fill="tozeroy",
        )
    )

    # Target line
    target_val = gap["total_current_emissions"] * 0.01
    fig_line.add_hline(
        y=target_val,
        line_dash="dash",
        line_color="red",
        annotation_text="Net-Zero Target (1%)",
    )

    fig_line.update_layout(
        title="Emissions Reduction Trajectory",
        xaxis_title="Year",
        yaxis_title="Emissions (tonnes CO₂e)",
        template="plotly_white",
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # Detailed Roadmap Table
    st.markdown("### 📅 Actionable Milestones")
    roadmap_data = []
    for step in result["roadmap"]:
        interventions = (
            ", ".join([i["name"] for i in step["interventions"]])
            or "Monitor & Optimize"
        )
        roadmap_data.append(
            {
                "Year": step["year"],
                "Annual Reduction": f"{step['projected_annual_reduction_pct']:.1f}%",
                "Cumulative Reduction": f"{step['cumulative_reduction_pct']:.1f}%",
                "Projected Emissions": f"{step['projected_emissions']:,.0f} tonnes",
                "Key Interventions": interventions,
            }
        )

    df_roadmap = pd.DataFrame(roadmap_data)
    st.dataframe(df_roadmap, use_container_width=True, hide_index=True)
