import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class CCUSFacilityNode:
    node_id: str
    facility_name: str
    industry_sector: str  # 'Cement Plant', 'Steel Mill', 'Natural Gas Power Plant', 'Chemical Refinery'
    capture_technology: str  # 'Amine Absorption', 'Direct Air Capture (DAC)', 'Calcium Looping', 'Membrane Separation'
    flue_gas_flow_m3h: float
    co2_concentration_pct: float
    capture_efficiency_pct: float
    daily_co2_captured_tons: float
    sequestration_destination: str  # 'Deep Saline Aquifer', 'Basalt Mineralization', 'EOR Enhanced Recovery', 'Synthetic Fuel Synthesis'
    operational_status: str  # 'Optimal Capture', 'Solvent Regeneration Required', 'Maintenance Overhaul'

@dataclass
class CarbonOffsetRecord:
    record_id: str
    facility_id: str
    facility_name: str
    verified_co2_tons: float
    carbon_credit_serial: str
    issuance_date: str
    monetary_value_usd: float

class CCUSEngine:
    """
    Industrial Carbon Capture, Utilization & Storage (CCUS) Telemetry Engine.
    Tracks flue gas volume, amine absorption efficiency, energy duty (GJ/ton CO2),
    and carbon offset credit issuance for heavy industrial emitters.
    """
    def __init__(self):
        self.facilities: List[CCUSFacilityNode] = [
            CCUSFacilityNode(
                node_id="ccus-101",
                facility_name="Rhenish Steel Mill Capture Plant #3",
                industry_sector="Steel Mill",
                capture_technology="Amine Absorption",
                flue_gas_flow_m3h=120000.0,
                co2_concentration_pct=22.5,
                capture_efficiency_pct=91.4,
                daily_co2_captured_tons=1450.0,
                sequestration_destination="Deep Saline Aquifer",
                operational_status="Optimal Capture"
            ),
            CCUSFacilityNode(
                node_id="ccus-102",
                facility_name="Nordic Cement Works CCUS Hub",
                industry_sector="Cement Plant",
                capture_technology="Calcium Looping",
                flue_gas_flow_m3h=85000.0,
                co2_concentration_pct=18.0,
                capture_efficiency_pct=88.2,
                daily_co2_captured_tons=820.0,
                sequestration_destination="Basalt Mineralization",
                operational_status="Optimal Capture"
            ),
            CCUSFacilityNode(
                node_id="ccus-103",
                facility_name="Rotterdam Petrochemical DAC Terminal",
                industry_sector="Chemical Refinery",
                capture_technology="Direct Air Capture (DAC)",
                flue_gas_flow_m3h=250000.0,
                co2_concentration_pct=0.04,
                capture_efficiency_pct=76.0,
                daily_co2_captured_tons=350.0,
                sequestration_destination="Synthetic Fuel Synthesis",
                operational_status="Solvent Regeneration Required"
            )
        ]

        self.records: List[CarbonOffsetRecord] = [
            CarbonOffsetRecord(
                record_id="cred-901",
                facility_id="ccus-101",
                facility_name="Rhenish Steel Mill Capture Plant #3",
                verified_co2_tons=1450.0,
                carbon_credit_serial="VCS-2026-EU-94812",
                issuance_date="2026-08-19",
                monetary_value_usd=123250.0
            )
        ]

    def get_facilities(self, sector_filter: str = "All") -> List[CCUSFacilityNode]:
        if sector_filter == "All":
            return self.facilities
        return [f for f in self.facilities if f.industry_sector == sector_filter]

    def calculate_total_telemetry(self) -> Dict[str, float]:
        total_captured = sum(f.daily_co2_captured_tons for f in self.facilities)
        avg_efficiency = np.mean([f.capture_efficiency_pct for f in self.facilities]) if self.facilities else 0.0
        est_credits_usd = sum(r.monetary_value_usd for r in self.records)

        return {
            "total_daily_co2_captured_tons": round(total_captured, 2),
            "average_capture_efficiency_pct": round(avg_efficiency, 1),
            "total_offset_credits_usd": round(est_credits_usd, 2)
        }

    def register_facility(
        self,
        facility_name: str,
        industry_sector: str,
        capture_technology: str,
        flue_gas_flow_m3h: float,
        co2_concentration_pct: float,
        sequestration_destination: str
    ) -> CCUSFacilityNode:
        efficiency = 92.5 if capture_technology == "Amine Absorption" else 85.0
        captured_tons = round((flue_gas_flow_m3h * (co2_concentration_pct / 100.0) * (efficiency / 100.0) * 0.048), 1)

        new_node = CCUSFacilityNode(
            node_id=f"ccus-{len(self.facilities) + 101}",
            facility_name=facility_name,
            industry_sector=industry_sector,
            capture_technology=capture_technology,
            flue_gas_flow_m3h=flue_gas_flow_m3h,
            co2_concentration_pct=co2_concentration_pct,
            capture_efficiency_pct=efficiency,
            daily_co2_captured_tons=captured_tons,
            sequestration_destination=sequestration_destination,
            operational_status="Optimal Capture"
        )
        self.facilities.append(new_node)
        return new_node

    def issue_carbon_offset_credit(self, facility_id: str, verified_tons: float) -> CarbonOffsetRecord:
        facility = next((f for f in self.facilities if f.node_id == facility_id), None)
        fac_name = facility.facility_name if facility else "Unknown Emitter Facility"

        new_record = CarbonOffsetRecord(
            record_id=f"cred-{len(self.records) + 901}",
            facility_id=facility_id,
            facility_name=fac_name,
            verified_co2_tons=verified_tons,
            carbon_credit_serial=f"VCS-2026-GLOBAL-{np.random.randint(10000, 99999)}",
            issuance_date="2026-08-20",
            monetary_value_usd=round(verified_tons * 85.0, 2)
        )
        self.records.append(new_record)
        return new_record


def render_industrial_ccus_dashboard():
    """
    Streamlit interactive dashboard for Industrial Carbon Capture, Utilization & Storage (CCUS).
    """
    st.title("🏭 Industrial Carbon Capture, Utilization & Storage (CCUS) Suite")
    st.markdown(
        "Monitor flue gas CO2 absorption, solvent regeneration heat duty, deep saline aquifer sequestration, and carbon offset issuance."
    )

    engine = CCUSEngine()
    telemetry = engine.calculate_total_telemetry()

    # Metric Row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Daily CO2 Captured", f"{telemetry['total_daily_co2_captured_tons']} Tons/day", delta="+12.4% vs Baseline")
    with col2:
        st.metric("Average Absorption Efficiency", f"{telemetry['average_capture_efficiency_pct']}%", delta="Target >85%")
    with col3:
        st.metric("Verified Offset Credit Ledger", f"${telemetry['total_offset_credits_usd']:,.2f} USD")

    st.markdown("---")

    # Sector Filter
    sector = st.selectbox("Filter Facilities by Industrial Sector", ["All", "Steel Mill", "Cement Plant", "Chemical Refinery"])
    facilities = engine.get_facilities(sector)

    # Plotly Visual
    df_fac = pd.DataFrame([f.__dict__ for f in facilities])
    if not df_fac.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_fac['facility_name'],
            y=df_fac['daily_co2_captured_tons'],
            name='Daily CO2 Captured (Tons)',
            marker_color='#0284c7'
        ))
        fig.update_layout(
            title="Daily Carbon Capture Volume by Emitter Facility",
            xaxis_title="Facility Name",
            yaxis_title="CO2 Captured (Tons/day)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Facilities Table
    st.subheader("🏢 Monitored CCUS Facilities")
    st.dataframe(df_fac, use_container_width=True)

    # Carbon Offset Credit Ledger Table
    with st.expander("📜 View Verified Carbon Offset Credit Ledger"):
        df_cred = pd.DataFrame([r.__dict__ for r in engine.records])
        st.dataframe(df_cred, use_container_width=True)

if __name__ == "__main__":
    render_industrial_ccus_dashboard()
