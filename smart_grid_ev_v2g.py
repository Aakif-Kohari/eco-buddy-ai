import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class EVChargerNode:
    charger_id: str
    station_name: str
    charger_type: str  # 'Level 2 AC 22kW', 'DC Fast Charger 150kW', 'V2G Bi-Directional Hub 50kW'
    connected_vehicle_model: str
    battery_capacity_kwh= float
    current_soc_pct= float
    target_soc_pct= float
    v2g_enabled: bool
    current_power_kw: float  # + for charging, - for V2G grid discharge
    battery_health_soh_pct: float

@dataclass
class V2GDispatchRecord:
    record_id: str
    charger_id: str
    station_name: str
    discharged_energy_kwh: float
    grid_tariff_earned_usd: float
    grid_frequency_hz: float
    dispatch_timestamp: str

class SmartEVV2GEngine:
    """
    Smart Grid EV Charging & V2G Vehicle-to-Grid Optimization Engine.
    Manages bi-directional EV charging, grid peak shaving, battery SOH tracking,
    and frequency response revenue generation.
    """
    def __init__(self):
        self.chargers: List[EVChargerNode] = [
            EVChargerNode(
                charger_id="ch-101",
                station_name="Municipal Logistics Depot - Hub A",
                charger_type="V2G Bi-Directional Hub 50kW",
                connected_vehicle_model="Volvo Electric Truck FL",
                battery_capacity_kwh= 200.0,
                current_soc_pct= 82.0,
                target_soc_pct= 90.0,
                v2g_enabled=True,
                current_power_kw=-45.0,  # Supplying grid during peak
                battery_health_soh_pct=96.5
            ),
            EVChargerNode(
                charger_id="ch-102",
                station_name="Tech Park West Charging Bay #4",
                charger_type="DC Fast Charger 150kW",
                connected_vehicle_model="Tesla Model Y Long Range",
                battery_capacity_kwh=78.0,
                current_soc_pct= 45.0,
                target_soc_pct= 80.0,
                v2g_enabled=False,
                current_power_kw=120.0,  # Fast charging
                battery_health_soh_pct=98.0
            ),
            EVChargerNode(
                charger_id="ch-103",
                station_name="Downtown Transit Bus Depot",
                charger_type="V2G Bi-Directional Hub 50kW",
                connected_vehicle_model="BYD K9 Electric Bus",
                battery_capacity_kwh=320.0,
                current_soc_pct= 75.0,
                target_soc_pct= 85.0,
                v2g_enabled=True,
                current_power_kw=-50.0,  # V2G discharge
                battery_health_soh_pct=94.0
            )
        ]

        self.dispatches: List[V2GDispatchRecord] = [
            V2GDispatchRecord(
                record_id="v2g-801",
                charger_id="ch-101",
                station_name="Municipal Logistics Depot - Hub A",
                discharged_energy_kwh=65.0,
                grid_tariff_earned_usd=19.50,
                grid_frequency_hz=49.82,
                dispatch_timestamp="15 minutes ago"
            )
        ]

    def get_chargers(self, type_filter: str = "All") -> List[EVChargerNode]:
        if type_filter == "All":
            return self.chargers
        return [c for c in self.chargers if c.charger_type == type_filter]

    def calculate_fleet_metrics(self) -> Dict[str, float]:
        total_charging = sum(c.current_power_kw for c in self.chargers if c.current_power_kw > 0)
        total_v2g_discharge = sum(abs(c.current_power_kw) for c in self.chargers if c.current_power_kw < 0)
        net_fleet_impact = total_charging - total_v2g_discharge
        avg_soh = np.mean([c.battery_health_soh_pct for c in self.chargers]) if self.chargers else 0.0

        return {
            "total_charging_power_kw": round(total_charging, 2),
            "total_v2g_discharge_power_kw": round(total_v2g_discharge, 2),
            "net_fleet_grid_impact_kw": round(net_fleet_impact, 2),
            "average_battery_soh_pct": round(avg_soh, 1)
        }

    def register_charger(
        self,
        station_name: str,
        charger_type: str,
        connected_vehicle_model: str,
        battery_capacity_kwh: float,
        current_soc_pct: float,
        v2g_enabled: bool
    ) -> EVChargerNode:
        power = -35.0 if v2g_enabled and current_soc_pct > 70.0 else 45.0
        new_node = EVChargerNode(
            charger_id=f"ch-{len(self.chargers) + 101}",
            station_name=station_name,
            charger_type=charger_type,
            connected_vehicle_model=connected_vehicle_model,
            battery_capacity_kwh=battery_capacity_kwh,
            current_soc_pct=current_soc_pct,
            target_soc_pct=90.0,
            v2g_enabled=v2g_enabled,
            current_power_kw=power,
            battery_health_soh_pct=97.0
        )
        self.chargers.append(new_node)
        return new_node

    def trigger_v2g_peak_shaving(self, charger_id: str, energy_kwh: float) -> V2GDispatchRecord:
        charger = next((c for c in self.chargers if c.charger_id == charger_id), None)
        station_name = charger.station_name if charger else "Unknown Charging Hub"

        record = V2GDispatchRecord(
            record_id=f"v2g-{len(self.dispatches) + 801}",
            charger_id=charger_id,
            station_name=station_name,
            discharged_energy_kwh=energy_kwh,
            grid_tariff_earned_usd=round(energy_kwh * 0.32, 2),
            grid_frequency_hz=49.85,
            dispatch_timestamp="Just now"
        )
        self.dispatches.append(record)
        return record


def render_smart_grid_ev_v2g_dashboard():
    """
    Streamlit interactive dashboard for Smart Grid EV Charging & V2G Optimization.
    """
    st.title("🔌 Smart Grid EV Charging & V2G Vehicle-to-Grid Suite")
    st.markdown(
        "Optimize bi-directional EV fleet charging, grid peak shaving, battery SOH longevity, and frequency response arbitrage."
    )

    engine = SmartEVV2GEngine()
    metrics = engine.calculate_fleet_metrics()

    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total EV Charging Power", f"{metrics['total_charging_power_kw']} kW")
    with col2:
        st.metric("V2G Bi-Directional Discharge", f"{metrics['total_v2g_discharge_power_kw']} kW", delta="Peak Shaving")
    with col3:
        st.metric("Net Fleet Grid Impact", f"{metrics['net_fleet_grid_impact_kw']} kW")
    with col4:
        st.metric("Avg Fleet Battery Health (SOH)", f"{metrics['average_battery_soh_pct']}%")

    st.markdown("---")

    # Charger Type Filter
    charger_filter = st.selectbox("Filter Chargers by Technology", ["All", "V2G Bi-Directional Hub 50kW", "DC Fast Charger 150kW", "Level 2 AC 22kW"])
    chargers = engine.get_chargers(charger_filter)

    # Plotly Visual
    df_ch = pd.DataFrame([c.__dict__ for c in chargers])
    if not df_ch.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_ch['station_name'],
            y=df_ch['current_power_kw'],
            name='Current Power (kW: +Charging / -V2G Discharge)',
            marker_color=np.where(df_ch['current_power_kw'] < 0, '#10b981', '#ef4444')
        ))
        fig.update_layout(
            title="EV Charging Hub Power Flows (Bi-Directional V2G Discharge vs Charging)",
            xaxis_title="Charging Hub Station",
            yaxis_title="Power Flow (kW)",
            template="plotly_white"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Table
    st.subheader("⚡ Connected EV Fleet Chargers")
    st.dataframe(df_ch, use_container_width=True)

    # V2G Dispatch History
    with st.expander("📜 View V2G Peak-Shaving Frequency Response Dispatch History"):
        df_disp = pd.DataFrame([d.__dict__ for d in engine.dispatches])
        st.dataframe(df_disp, use_container_width=True)

if __name__ == "__main__":
    render_smart_grid_ev_v2g_dashboard()
