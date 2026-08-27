import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SupplierNode:
    supplier_id: str
    vendor_name: str
    tier_level: str  # 'Tier-1 Direct Supplier', 'Tier-2 Raw Sub-supplier'
    procurement_category: str  # 'Semiconductor Foundry', 'Logistics Freight', 'Metal Fabrication', 'Chemical Synthesis'
    annual_spend_usd: float
    carbon_intensity_kg_co2_per_usd: float
    total_allocated_scope3_tons: float
    sbti_netzero_committed: bool
    decarbonization_score: float  # 0 - 100
    decarbonization_status: str  # 'On Track NetZero 2030', 'Moderate Action Required', 'High Carbon Penalty Risk'

@dataclass
class SupplierEngagementRecord:
    record_id: str
    supplier_id: str
    vendor_name: str
    target_reduction_pct: float
    agreed_audit_year: int
    allocated_grant_usd: float
    engagement_status: str

class Scope3SupplyChainEngine:
    """
    Scope 3 Supply Chain Upstream Decarbonization & Supplier Allocation Engine.
    Allocates GHG Protocol Scope 3 Category 1 spend-based and hybrid emissions,
    evaluates vendor carbon intensities, and tracks SBTi NetZero supplier engagements.
    """
    def __init__(self):
        self.suppliers: List[SupplierNode] = [
            SupplierNode(
                supplier_id="sup-101",
                vendor_name="TSMC Taiwan Silicon Foundry Corp",
                tier_level="Tier-1 Direct Supplier",
                procurement_category="Semiconductor Foundry",
                annual_spend_usd=15000000.0,
                carbon_intensity_kg_co2_per_usd=0.28,
                total_allocated_scope3_tons=4200.0,
                sbti_netzero_committed=True,
                decarbonization_score=88.5,
                decarbonization_status="On Track NetZero 2030"
            ),
            SupplierNode(
                supplier_id="sup-102",
                vendor_name="Maersk Global Maritime Freight",
                tier_level="Tier-1 Direct Supplier",
                procurement_category="Logistics Freight",
                annual_spend_usd=6200000.0,
                carbon_intensity_kg_co2_per_usd=0.65,
                total_allocated_scope3_tons=4030.0,
                sbti_netzero_committed=True,
                decarbonization_score=72.0,
                decarbonization_status="Moderate Action Required"
            ),
            SupplierNode(
                supplier_id="sup-103",
                vendor_name="Guangdong Steel Stamping Ltd",
                tier_level="Tier-2 Raw Sub-supplier",
                procurement_category="Metal Fabrication",
                annual_spend_usd=3400000.0,
                carbon_intensity_kg_co2_per_usd=1.45,
                total_allocated_scope3_tons=4930.0,
                sbti_netzero_committed=False,
                decarbonization_score=41.0,
                decarbonization_status="High Carbon Penalty Risk"
            )
        ]

        self.engagements: List[SupplierEngagementRecord] = [
            SupplierEngagementRecord(
                record_id="eng-601",
                supplier_id="sup-103",
                vendor_name="Guangdong Steel Stamping Ltd",
                target_reduction_pct=30.0,
                agreed_audit_year=2027,
                allocated_grant_usd=150000.0,
                engagement_status="Active Audit Agreement"
            )
        ]

    def get_suppliers(self, tier_filter: str = "All") -> List[SupplierNode]:
        if tier_filter == "All":
            return self.suppliers
        return [s for s in self.suppliers if s.tier_level == tier_filter]

    def calculate_scope3_summary(self) -> Dict[str, float]:
        total_spend = sum(s.annual_spend_usd for s in self.suppliers)
        total_scope3_tons = sum(s.total_allocated_scope3_tons for s in self.suppliers)
        avg_score = np.mean([s.decarbonization_score for s in self.suppliers]) if self.suppliers else 0.0
        sbti_pct = (sum(1 for s in self.suppliers if s.sbti_netzero_committed) / len(self.suppliers)) * 100.0 if self.suppliers else 0.0

        return {
            "total_procurement_spend_usd": round(total_spend, 2),
            "total_allocated_scope3_emissions_tons": round(total_scope3_tons, 2),
            "average_decarbonization_score": round(avg_score, 1),
            "sbti_committed_suppliers_pct": round(sbti_pct, 1)
        }

    def register_supplier(
        self,
        vendor_name: str,
        tier_level: str,
        procurement_category: str,
        annual_spend_usd: float,
        carbon_intensity_kg_co2_per_usd: float,
        sbti_netzero_committed: bool
    ) -> SupplierNode:
        allocated_tons = (annual_spend_usd * carbon_intensity_kg_co2_per_usd) / 1000.0
        score = 85.0 if sbti_netzero_committed else 50.0
        status = "On Track NetZero 2030" if sbti_netzero_committed else "Moderate Action Required"

        new_node = SupplierNode(
            supplier_id=f"sup-{len(self.suppliers) + 101}",
            vendor_name=vendor_name,
            tier_level=tier_level,
            procurement_category=procurement_category,
            annual_spend_usd=annual_spend_usd,
            carbon_intensity_kg_co2_per_usd=carbon_intensity_kg_co2_per_usd,
            total_allocated_scope3_tons=round(allocated_tons, 2),
            sbti_netzero_committed=sbti_netzero_committed,
            decarbonization_score=score,
            decarbonization_status=status
        )
        self.suppliers.append(new_node)
        return new_node

    def initiate_decarbonization_engagement(
        self,
        supplier_id: str,
        target_reduction_pct: float,
        grant_usd: float
    ) -> SupplierEngagementRecord:
        supplier = next((s for s in self.suppliers if s.supplier_id == supplier_id), None)
        v_name = supplier.vendor_name if supplier else "Unknown Supplier"

        record = SupplierEngagementRecord(
            record_id=f"eng-{len(self.engagements) + 601}",
            supplier_id=supplier_id,
            vendor_name=v_name,
            target_reduction_pct=target_reduction_pct,
            agreed_audit_year=2028,
            allocated_grant_usd=grant_usd,
            engagement_status="Grant Dispatched"
        )
        self.engagements.append(record)
        return record


def render_scope3_supply_chain_dashboard():
    """
    Streamlit interactive dashboard for Scope 3 Supply Chain Upstream Decarbonization.
    """
    st.title("🚢 Scope 3 Supply Chain Upstream Decarbonization Suite")
    st.markdown(
        "Allocate GHG Protocol Scope 3 Category 1 supply chain emissions, benchmark vendor carbon intensity, and track SBTi supplier NetZero engagements."
    )

    engine = Scope3SupplyChainEngine()
    summary = engine.calculate_scope3_summary()

    # Metric Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Procurement Spend", f"${summary['total_procurement_spend_usd']:,.2f} USD")
    with col2:
        st.metric("Allocated Scope 3 Emissions", f"{summary['total_allocated_scope3_emissions_tons']:,} Tons CO2e")
    with col3:
        st.metric("Avg Vendor Decarbonization Score", f"{summary['average_decarbonization_score']} / 100")
    with col4:
        st.metric("SBTi NetZero Vendors", f"{summary['sbti_committed_suppliers_pct']}%", delta="Target 100%")

    st.markdown("---")

    # Tier Filter
    tier_filter = st.selectbox("Filter Suppliers by Supply Chain Tier", ["All", "Tier-1 Direct Supplier", "Tier-2 Raw Sub-supplier"])
    suppliers = engine.get_suppliers(tier_filter)

    # Plotly Visual
    df_sup = pd.DataFrame([s.__dict__ for s in suppliers])
    if not df_sup.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_sup['vendor_name'],
            y=df_sup['total_allocated_scope3_tons'],
            name='Allocated Scope 3 Emissions (Tons)',
            marker_color='#ef4444'
        ))
        fig.update_layout(
            title="Allocated Scope 3 Emissions Breakdown by Vendor",
            xaxis_title="Supplier Vendor Name",
            yaxis_title="Allocated Scope 3 (Tons CO2e)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("🏭 Monitored Supply Chain Vendors")
    st.dataframe(df_sup, use_container_width=True)

    # Engagements Table
    with st.expander("📜 View Active Supplier Decarbonization Grant Engagements"):
        df_eng = pd.DataFrame([e.__dict__ for e in engine.engagements])
        st.dataframe(df_eng, use_container_width=True)

if __name__ == "__main__":
    render_scope3_supply_chain_dashboard()
