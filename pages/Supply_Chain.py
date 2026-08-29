import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

# Ensure parent directory is in path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.business.supply_chain_data import SupplyChainDataGenerator
from src.business.supply_chain_logic import SupplyChainLogic
from src.business.supply_chain_report import SupplyChainReportGenerator

st.set_page_config(
    page_title="Supply Chain ESG Tracker",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom highly styled CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        text-align: center;
        border: 1px solid #334155;
        transition: transform 0.3s ease;
    }
    .metric-card:hover {
        transform: translateY(-5px);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        color: #38bdf8;
        font-size: 32px;
        font-weight: 800;
        margin-top: 10px;
    }
    .good-value { color: #4ade80; }
    .bad-value { color: #f87171; }
    .stDataFrame { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_and_process_data(num_suppliers=50, seed=42):
    generator = SupplyChainDataGenerator(num_suppliers=num_suppliers, seed=seed)
    raw_data = generator.get_full_dataset()
    logic = SupplyChainLogic(raw_data)
    scorecard = logic.generate_supplier_scorecard()
    metrics = logic.get_summary_metrics()
    return scorecard, metrics, raw_data

st.title("🌱 Enterprise Supply Chain ESG Tracker")
st.markdown("Monitor, analyze, and optimize Scope 3 emissions across your global supplier network.")

# Sidebar Controls
st.sidebar.header("⚙️ Configuration")
supplier_count = st.sidebar.slider("Number of Suppliers Assessed", 10, 200, 50)
random_seed = st.sidebar.number_input("Randomization Seed", value=42)

# Load data
scorecard, metrics, raw_data = load_and_process_data(supplier_count, random_seed)

# Top Metrics Row
cols = st.columns(4)
with cols[0]:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Total Suppliers</div>
            <div class="metric-value">{metrics['total_suppliers']}</div>
        </div>
    """, unsafe_allow_html=True)
with cols[1]:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Scope 3 Emissions (MT)</div>
            <div class="metric-value bad-value">{metrics['total_scope3_emissions']:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
with cols[2]:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Average ESG Score</div>
            <div class="metric-value good-value">{metrics['avg_esg_score']:.1f}/100</div>
        </div>
    """, unsafe_allow_html=True)
with cols[3]:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">Suppliers At Risk</div>
            <div class="metric-value" style="color: #fbbf24;">{metrics['at_risk_suppliers']}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# Main Dashboard Content
tab1, tab2, tab3 = st.tabs(["📊 Analytics Dashboard", "📋 Supplier Scorecard", "📄 Report Generator"])

with tab1:
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Emissions by Region")
        fig_region = px.box(
            scorecard, x="region", y="total_scope3_emissions_mt", color="region",
            title="Scope 3 Emissions Spread per Region", template="plotly_dark"
        )
        st.plotly_chart(fig_region, use_container_width=True)
        
    with c2:
        st.subheader("ESG Score vs Emissions")
        fig_scatter = px.scatter(
            scorecard, x="esg_score", y="total_scope3_emissions_mt", 
            color="compliance_status", size="renewable_energy_pct", hover_name="name",
            title="Supplier Performance Quadrant", template="plotly_dark",
            color_discrete_map={"Compliant": "#4ade80", "At Risk": "#f87171"}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Supply Chain Composition")
    c3, c4 = st.columns(2)
    with c3:
        tier_counts = scorecard["tier"].value_counts().reset_index()
        tier_counts.columns = ["Tier", "Count"]
        fig_tier = px.pie(tier_counts, names="Tier", values="Count", hole=0.4, title="Suppliers by Tier", template="plotly_dark")
        st.plotly_chart(fig_tier, use_container_width=True)
        
    with c4:
        shipments = raw_data["shipments"]
        transport_mix = shipments["transport_mode"].value_counts().reset_index()
        transport_mix.columns = ["Mode", "Count"]
        fig_mode = px.bar(transport_mix, x="Mode", y="Count", color="Mode", title="Transport Mode Utilization", template="plotly_dark")
        st.plotly_chart(fig_mode, use_container_width=True)


with tab2:
    st.subheader("Supplier Master Scorecard")
    st.info("Interactive table of all evaluated suppliers and their corresponding ESG metrics.")
    
    filter_region = st.selectbox("Filter by Region", ["All"] + list(scorecard["region"].unique()))
    
    display_df = scorecard.copy()
    if filter_region != "All":
        display_df = display_df[display_df["region"] == filter_region]
        
    # Formatting for display
    display_cols = ["supplier_id", "name", "region", "tier", "esg_score", "compliance_status", "renewable_energy_pct", "total_scope3_emissions_mt"]
    st.dataframe(
        display_df[display_cols].style.background_gradient(cmap="RdYlGn_r", subset=["total_scope3_emissions_mt"])
                                       .background_gradient(cmap="RdYlGn", subset=["esg_score"]),
        use_container_width=True,
        height=600
    )


with tab3:
    st.subheader("Export Compliance Report")
    st.write("Generate a comprehensive PDF report containing high-level metrics, insights, and action items for stakeholders.")
    
    report_name = st.text_input("Report Output Filename", value="Q3_Supply_Chain_Report.pdf")
    
    if st.button("Generate PDF Report", type="primary"):
        with st.spinner("Generating document..."):
            generator = SupplyChainReportGenerator(scorecard, metrics, report_name)
            output_path = generator.generate_report()
            
            with open(output_path, "rb") as file:
                btn = st.download_button(
                    label="📥 Download PDF",
                    data=file,
                    file_name=report_name,
                    mime="application/pdf"
                )
            
        st.success(f"Report generated successfully!")
