import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass
class MicrogridAsset:
    asset_id: str
    asset_name: str
    asset_type: str  # 'Solar PV', 'Wind Turbine', 'BESS Battery Storage', 'Commercial HVAC Load'
    capacity_kw: float
    current_power_kw: float
    state_of_charge_pct: Optional[float] = None  # For BESS
    efficiency_pct: float = 95.0

@dataclass
class VPPDispatchSchedule:
    hour: int
    solar_gen_kw: float
    load_demand_kw: float
    bess_action_kw: float  # + for charge, - for discharge
    grid_export_import_kw: float  # + for export, - for import
    carbon_intensity_g_kwh: float
    tariff_cost_usd_kwh: float
    revenue_usd: float

class MicrogridVPPEngine:
    """
    Microgrid Virtual Power Plant (VPP) Optimization Engine.
    Simulates asset generation, BESS state-of-charge (SoC) management,
    grid arbitrage, and carbon-aware demand response dispatching.
    """
    def __init__(self):
        self.assets: List[MicrogridAsset] = [
            MicrogridAsset("pv-1", "Rooftop Solar PV Array A", "Solar PV", 500.0, 320.0),
            MicrogridAsset("wind-1", "Community Wind Turbine", "Wind Turbine", 250.0, 140.0),
            MicrogridAsset("bess-1", "Containerized Battery BESS", "BESS Battery Storage", 1000.0, 0.0, state_of_charge_pct=65.0, efficiency_pct=92.0),
            MicrogridAsset("load-1", "Commercial HVAC & Lighting", "Commercial HVAC Load", 600.0, 410.0),
        ]

    def add_asset(self, asset: MicrogridAsset):
        self.assets.append(asset)

    def calculate_current_balance(self) -> Dict[str, float]:
        total_gen = sum(a.current_power_kw for a in self.assets if a.asset_type in ['Solar PV', 'Wind Turbine'])
        total_load = sum(a.current_power_kw for a in self.assets if a.asset_type == 'Commercial HVAC Load')
        net_power = total_gen - total_load

        return {
            "total_generation_kw": round(total_gen, 2),
            "total_load_kw": round(total_load, 2),
            "net_power_kw": round(net_power, 2)
        }

    def simulate_24h_vpp_schedule(
        self,
        bess_capacity_kwh: float = 1000.0,
        initial_soc_pct: float = 50.0,
        enable_carbon_arbitrage: bool = True
    ) -> List[VPPDispatchSchedule]:
        """
        Simulates 24-hour VPP microgrid dispatch schedule with dynamic carbon intensity and pricing.
        """
        schedule: List[VPPDispatchSchedule] = []
        current_soc = (initial_soc_pct / 100.0) * bess_capacity_kwh

        # Synthetic 24-hour solar generation profile (bell curve around noon)
        hours = np.arange(24)
        solar_profile = np.maximum(0, np.sin((hours - 6) * np.pi / 12)) * 450.0

        # Synthetic 24-hour load profile (twin peaks: morning & evening)
        load_profile = 250.0 + 150.0 * np.sin((hours - 8) * np.pi / 12)**2 + 180.0 * np.sin((hours - 18) * np.pi / 12)**2

        # Synthetic dynamic carbon intensity (gCO2/kWh) and tariff ($/kWh)
        carbon_intensity = 350.0 + 200.0 * np.cos((hours - 19) * np.pi / 12)
        tariff_pricing = 0.12 + 0.18 * (carbon_intensity > 450).astype(float) + 0.08 * (solar_profile == 0).astype(float)

        for h in range(24):
            gen = float(solar_profile[h])
            load = float(load_profile[h])
            c_int = float(carbon_intensity[h])
            tariff = float(tariff_pricing[h])

            net_surplus = gen - load
            bess_action = 0.0

            if net_surplus > 0:
                # Excess solar generation: charge BESS up to max capacity
                charge_space = bess_capacity_kwh - current_soc
                charge_kw = min(net_surplus, charge_space, 250.0)  # Max 250 kW C-rate
                current_soc += charge_kw * 0.92
                bess_action = charge_kw
                grid_flow = net_surplus - charge_kw  # Export remaining surplus
            else:
                # Deficit: discharge BESS during high carbon intensity or peak tariff
                deficit = abs(net_surplus)
                if enable_carbon_arbitrage and (c_int > 400 or tariff > 0.20) and current_soc > 100.0:
                    discharge_kw = min(deficit, current_soc - 100.0, 250.0)
                    current_soc -= discharge_kw
                    bess_action = -discharge_kw
                    grid_flow = -(deficit - discharge_kw)  # Import remaining deficit
                else:
                    grid_flow = -deficit  # Full grid import

            revenue = grid_flow * tariff if grid_flow > 0 else grid_flow * tariff * 1.1

            schedule.append(
                VPPDispatchSchedule(
                    hour=h,
                    solar_gen_kw=round(gen, 2),
                    load_demand_kw=round(load, 2),
                    bess_action_kw=round(bess_action, 2),
                    grid_export_import_kw=round(grid_flow, 2),
                    carbon_intensity_g_kwh=round(c_int, 1),
                    tariff_cost_usd_kwh=round(tariff, 3),
                    revenue_usd=round(revenue, 2)
                )
            )

        return schedule


def render_microgrid_vpp_dashboard():
    """
    Streamlit interactive dashboard for Microgrid Virtual Power Plant (VPP) Optimization.
    """
    st.title("⚡ Renewable Energy Microgrid & Virtual Power Plant (VPP) Suite")
    st.markdown(
        "Optimize distributed solar PV, battery BESS energy storage, dynamic grid arbitrage, and carbon-aware demand response dispatching."
    )

    engine = MicrogridVPPEngine()
    balance = engine.calculate_current_balance()

    # Metrics Summary Row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Generation", f"{balance['total_generation_kw']} kW", delta="Solar + Wind")
    with col2:
        st.metric("Facility Load Demand", f"{balance['total_load_kw']} kW")
    with col3:
        st.metric("Net Microgrid Power", f"{balance['net_power_kw']} kW", delta="Surplus Export" if balance['net_power_kw'] >= 0 else "-Grid Deficit")
    with col4:
        st.metric("BESS State of Charge", "65.0%", delta="Normal Operating Range")

    st.markdown("---")

    # Simulation Controls Sidebar / Expander
    st.subheader("🎛️ 24-Hour VPP Dispatch Simulation Controls")
    c1, c2, c3 = st.columns(3)
    with c1:
        bess_cap = st.number_input("BESS Battery Capacity (kWh)", min_value=100.0, max_value=5000.0, value=1000.0, step=100.0)
    with c2:
        init_soc = st.slider("Initial State of Charge (%)", min_value=10.0, max_value=100.0, value=50.0)
    with c3:
        carbon_arb = st.checkbox("Enable Carbon-Aware Grid Arbitrage", value=True)

    schedules = engine.simulate_24h_vpp_schedule(bess_cap, init_soc, carbon_arb)
    df_sched = pd.DataFrame([s.__dict__ for s in schedules])

    # Plotly Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_sched['hour'], y=df_sched['solar_gen_kw'], mode='lines+markers', name='Solar PV Generation (kW)', line=dict(color='#eab308', width=3)))
    fig.add_trace(go.Scatter(x=df_sched['hour'], y=df_sched['load_demand_kw'], mode='lines', name='Load Demand (kW)', line=dict(color='#ef4444', width=2, dash='dash')))
    fig.add_trace(go.Bar(x=df_sched['hour'], y=df_sched['grid_export_import_kw'], name='Grid Export (+)/Import (-)', marker_color='#3b82f6', opacity=0.6))
    fig.add_trace(go.Scatter(x=df_sched['hour'], y=df_sched['bess_action_kw'], mode='lines+markers', name='BESS Action (kW)', line=dict(color='#10b981', width=2)))

    fig.update_layout(
        title="24-Hour Microgrid Power Flow & BESS Arbitrage Profile",
        xaxis_title="Hour of Day",
        yaxis_title="Power (kW)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detailed Schedule Data Table
    with st.expander("📋 View Detailed 24-Hour VPP Dispatch Schedule Data"):
        st.dataframe(df_sched, use_container_width=True)

if __name__ == "__main__":
    render_microgrid_vpp_dashboard()
