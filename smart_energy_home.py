"""Smart Energy Home Dashboard – Track solar production, energy consumption, battery storage, grid usage, and optimize your home energy footprint."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import math

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Smart Energy Home", page_icon="⚡", layout="wide")

# ─── Theme ──────────────────────────────────────────────────────────────────
try:
    from styles.theme import apply_theme
    apply_theme()
except Exception:
    pass

# ─── Constants ──────────────────────────────────────────────────────────────
APPLIANCE_CATEGORIES = {
    "hvac": {"label": "🌡️ HVAC (Heating/Cooling)", "color": "#ef4444", "avg_kwh": 350, "avg_cost": 0.12},
    "lighting": {"label": "💡 Lighting", "color": "#f59e0b", "avg_kwh": 80, "avg_cost": 0.10},
    "kitchen": {"label": "🍳 Kitchen (Fridge, Oven, Dishwasher)", "color": "#3b82f6", "avg_kwh": 150, "avg_cost": 0.11},
    "laundry": {"label": "👕 Laundry (Washer, Dryer)", "color": "#8b5cf6", "avg_kwh": 100, "avg_cost": 0.10},
    "entertainment": {"label": "📺 Entertainment (TV, Gaming, Speakers)", "color": "#06b6d4", "avg_kwh": 60, "avg_cost": 0.12},
    "computing": {"label": "💻 Computing (PC, Router, NAS)", "color": "#10b981", "avg_kwh": 45, "avg_cost": 0.12},
    "ev_charging": {"label": "🚗 EV Charging", "color": "#6366f1", "avg_kwh": 300, "avg_cost": 0.08},
    "water_heating": {"label": "🚿 Water Heating", "color": "#f97316", "avg_kwh": 200, "avg_cost": 0.11},
    "other": {"label": "📦 Other (Standby, Small Appliances)", "color": "#6b7280", "avg_kwh": 40, "avg_cost": 0.12},
}

SOLAR_PANEL_TYPES = [
    {"name": "Monocrystalline", "efficiency": 0.22, "cost_per_watt": 2.80, "lifespan": 25, "icon": "⬛"},
    {"name": "Polycrystalline", "efficiency": 0.18, "cost_per_watt": 2.20, "lifespan": 25, "icon": "🔵"},
    {"name": "Thin-Film", "efficiency": 0.13, "cost_per_watt": 1.80, "lifespan": 20, "icon": "🟩"},
    {"name": "PERC", "efficiency": 0.23, "cost_per_watt": 3.00, "lifespan": 30, "icon": "🟪"},
]

WEATHER_CONDITIONS = ["sunny", "partly_cloudy", "cloudy", "rainy", "snowy"]
WEATHER_MULTIPLIER = {"sunny": 1.0, "partly_cloudy": 0.75, "cloudy": 0.45, "rainy": 0.30, "snowy": 0.25}

TARIFF_RATES = {
    "off_peak": {"label": "Off-Peak (10PM-7AM)", "rate": 0.06, "hours": list(range(22, 24)) + list(range(0, 7))},
    "mid_peak": {"label": "Mid-Peak (7AM-11AM, 5PM-10PM)", "rate": 0.10, "hours": list(range(7, 11)) + list(range(17, 22))},
    "on_peak": {"label": "On-Peak (11AM-5PM)", "rate": 0.15, "hours": list(range(11, 17))},
}

# ─── Session State ──────────────────────────────────────────────────────────
if "energy_config" not in st.session_state:
    st.session_state.energy_config = {
        "solar_panels": 12,
        "panel_type": "Monocrystalline",
        "system_size_kw": 5.0,
        "battery_capacity_kwh": 13.5,
        "battery_level": 0.75,
        "home_sqft": 2000,
        "occupants": 4,
        "ev_owned": True,
        "location": "California, US",
        "grid_provider": "Pacific Gas & Electric",
        "monthly_bill_target": 50,
    }

if "energy_history" not in st.session_state:
    st.session_state.energy_history = _generate_30day_history() if '_generate_30day_history' in dir() else []


def _generate_sample_history():
    """Generate 30 days of sample energy data."""
    history = []
    now = datetime.now()
    for day_offset in range(30):
        day = now - timedelta(days=29 - day_offset)
        weather = random.choice(WEATHER_CONDITIONS)
        multiplier = WEATHER_MULTIPLIER[weather]

        solar_base = st.session_state.energy_config["system_size_kw"] * 5.5 * multiplier
        solar_kwh = round(solar_base + random.uniform(-2, 2), 2)
        solar_kwh = max(0, solar_kwh)

        consumption = {}
        total_consumption = 0
        for cat, meta in APPLIANCE_CATEGORIES.items():
            daily = meta["avg_kwh"] / 30 + random.uniform(-3, 3)
            daily = max(0.5, daily)
            if cat == "ev_charging" and not st.session_state.energy_config["ev_owned"]:
                daily = 0
            consumption[cat] = round(daily, 2)
            total_consumption += daily

        grid_import = max(0, total_consumption - solar_kwh)
        grid_export = max(0, solar_kwh - total_consumption)
        battery_charge = min(
            st.session_state.energy_config["battery_capacity_kwh"],
            st.session_state.energy_config["battery_level"] * st.session_state.energy_config["battery_capacity_kwh"] + solar_kwh * 0.3,
        )

        grid_cost = 0
        for period, info in TARIFF_RATES.items():
            hours = len(info["hours"])
            share = hours / 24
            grid_cost += grid_import * share * info["rate"]

        history.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "weather": weather,
            "solar_kwh": solar_kwh,
            "consumption_kwh": round(total_consumption, 2),
            "consumption_by_type": consumption,
            "grid_import_kwh": round(grid_import, 2),
            "grid_export_kwh": round(grid_export, 2),
            "grid_cost": round(grid_cost, 2),
            "grid_export_income": round(grid_export * 0.05, 2),
            "net_cost": round(grid_cost - grid_export * 0.05, 2),
            "battery_level": round(min(1.0, st.session_state.energy_config["battery_level"] + (solar_kwh - total_consumption) / st.session_state.energy_config["battery_capacity_kwh"] * 0.3), 2),
            "self_sufficiency": round(min(100, (solar_kwh / total_consumption * 100) if total_consumption > 0 else 0), 1),
            "co2_saved_kg": round(solar_kwh * 0.42, 2),
        })
    return history


# ─── Helpers ────────────────────────────────────────────────────────────────

def render_stat(label, value, icon="", delta=None, color="blue"):
    st.metric(label=f"{icon} {label}" if icon else label, value=value, delta=delta)


def get_solar_output(panel_type, num_panels, weather, hours_sun=6):
    """Calculate solar output for given conditions."""
    panel = next((p for p in SOLAR_PANEL_TYPES if p["name"] == panel_type), SOLAR_PANEL_TYPES[0])
    panel_wattage = panel["efficiency"] * 1.7 * 1000  # 1.7m² per panel, 1000 W/m² STC
    multiplier = WEATHER_MULTIPLIER.get(weather, 0.5)
    daily_kwh = (panel_wattage * num_panels * hours_sun * multiplier) / 1000
    return round(daily_kwh, 2)


# ─── Main Rendering ─────────────────────────────────────────────────────────

def render_smart_energy_hub():
    st.title("⚡ Smart Energy Home Dashboard")
    st.markdown("Monitor your solar production, track energy consumption, optimize battery storage, and minimize your grid dependency.")

    # Generate history if empty
    if not st.session_state.energy_history:
        st.session_state.energy_history = _generate_sample_history()

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Overview",
        "☀️ Solar Production",
        "🏠 Energy Consumption",
        "🔋 Battery & Grid",
        "💰 Cost Analysis",
        "🌍 Carbon Impact",
        "⚙️ Settings",
    ])

    config = st.session_state.energy_config
    history = st.session_state.energy_history
    today = history[-1] if history else {}

    # ═══════════════════════════════════════════
    # TAB 1: Overview
    # ═══════════════════════════════════════════
    with tab1:
        # Today's KPIs
        st.subheader("📊 Today's Energy Snapshot")
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("☀️ Solar", f"{today.get('solar_kwh', 0)} kWh")
        with c2:
            st.metric("🏠 Usage", f"{today.get('consumption_kwh', 0)} kWh")
        with c3:
            st.metric("⬇️ Grid Import", f"{today.get('grid_import_kwh', 0)} kWh")
        with c4:
            st.metric("⬆️ Grid Export", f"{today.get('grid_export_kwh', 0)} kWh")
        with c5:
            st.metric("🔋 Battery", f"{int(today.get('battery_level', 0.75) * 100)}%")
        with c6:
            st.metric("💰 Net Cost", f"${today.get('net_cost', 0):.2f}")

        st.divider()

        # 30-day Overview
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("📈 30-Day Production vs Consumption")
            df = pd.DataFrame(history)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["date"], y=df["solar_kwh"], name="Solar Production",
                                     line=dict(color="#f59e0b", width=2), fill="tozeroy", fillcolor="rgba(245,158,11,0.1)"))
            fig.add_trace(go.Scatter(x=df["date"], y=df["consumption_kwh"], name="Consumption",
                                     line=dict(color="#ef4444", width=2), fill="tozeroy", fillcolor="rgba(239,68,68,0.1)"))
            fig.add_trace(go.Scatter(x=df["date"], y=df["grid_import_kwh"], name="Grid Import",
                                     line=dict(color="#6b7280", width=1, dash="dot")))
            fig.update_layout(height=350, margin=dict(t=30, b=30), legend=dict(orientation="h", y=-0.15))
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.subheader("🌤️ Weather Impact")
            weather_data = df.groupby("weather").agg({
                "solar_kwh": "mean",
                "self_sufficiency": "mean",
            }).reset_index()
            weather_data["weather_label"] = weather_data["weather"].map({
                "sunny": "☀️ Sunny", "partly_cloudy": "⛅ Partly Cloudy",
                "cloudy": "☁️ Cloudy", "rainy": "🌧️ Rainy", "snowy": "❄️ Snowy",
            })
            fig = px.bar(weather_data, x="weather_label", y="solar_kwh",
                         title="Avg Solar Output by Weather",
                         color="weather_label",
                         color_discrete_map={"☀️ Sunny": "#f59e0b", "⛅ Partly Cloudy": "#94a3b8",
                                             "☁️ Cloudy": "#6b7280", "🌧️ Rainy": "#3b82f6", "❄️ Snowy": "#e2e8f0"})
            fig.update_layout(height=350, showlegend=False, xaxis_title="", yaxis_title="kWh")
            st.plotly_chart(fig, use_container_width=True)

        # Self-Sufficiency Gauge
        st.subheader("🔋 Self-Sufficiency Score")
        avg_self_suff = df["self_sufficiency"].mean()
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=avg_self_suff,
            title={"text": "30-Day Avg Self-Sufficiency (%)"},
            delta={"reference": config["monthly_bill_target"] / 10},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#22c55e" if avg_self_suff >= 70 else "#f59e0b" if avg_self_suff >= 40 else "#ef4444"},
                "steps": [
                    {"range": [0, 30], "color": "#fef2f2"},
                    {"range": [30, 60], "color": "#fefce8"},
                    {"range": [60, 80], "color": "#f0fdf4"},
                    {"range": [80, 100], "color": "#dcfce7"},
                ],
                "threshold": {"line": {"color": "#16a34a", "width": 4}, "thickness": 0.75, "value": 70},
            },
        ))
        fig.update_layout(height=280, margin=dict(t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 2: Solar Production
    # ═══════════════════════════════════════════
    with tab2:
        st.subheader("☀️ Solar Panel System")
        panel_info = next((p for p in SOLAR_PANEL_TYPES if p["name"] == config["panel_type"]), SOLAR_PANEL_TYPES[0])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("System Size", f"{config['system_size_kw']} kW")
        with c2:
            st.metric("Panels", f"{config['solar_panels']} × {panel_info['icon']}")
        with c3:
            st.metric("Panel Type", config["panel_type"])
        with c4:
            st.metric("Efficiency", f"{panel_info['efficiency'] * 100:.0f}%")

        st.divider()

        # Hourly Production Profile
        st.subheader("🕐 Hourly Production Profile (Typical Day)")
        hours = list(range(6, 21))
        hourly_solar = []
        for h in hours:
            if 6 <= h <= 20:
                sun_angle = math.sin(math.pi * (h - 6) / 14)
                output = config["system_size_kw"] * sun_angle * panel_info["efficiency"] / 0.22
                hourly_solar.append(max(0, output + random.uniform(-0.3, 0.3)))
            else:
                hourly_solar.append(0)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=[f"{h}:00" for h in hours], y=hourly_solar, name="Solar Output",
                             marker_color="#f59e0b"))
        fig.add_trace(go.Scatter(x=[f"{h}:00" for h in hours], y=[config["system_size_kw"]] * len(hours),
                                 name="Max Capacity", line=dict(color="#ef4444", dash="dash", width=1)))
        fig.update_layout(height=350, title="Hourly Solar Production", xaxis_title="Hour", yaxis_title="kW",
                          margin=dict(t=40, b=30))
        st.plotly_chart(fig, use_container_width=True)

        # 30-day production trend
        df = pd.DataFrame(history)
        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(df, x="date", y="solar_kwh", title="Daily Solar Production (30 Days)",
                          color_discrete_sequence=["#f59e0b"])
            fig.update_layout(height=300, xaxis_title="", yaxis_title="kWh")
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            # Cumulative
            df["cumulative_solar"] = df["solar_kwh"].cumsum()
            fig = px.area(df, x="date", y="cumulative_solar", title="Cumulative Solar Production",
                          color_discrete_sequence=["#22c55e"])
            fig.update_layout(height=300, xaxis_title="", yaxis_title="kWh")
            st.plotly_chart(fig, use_container_width=True)

        # Panel simulator
        st.subheader("🔧 Panel Calculator")
        with st.form("panel_calc"):
            pc1, pc2, pc3, pc3 = st.columns(4)
            with pc1:
                calc_panels = st.number_input("Number of Panels", 1, 50, config["solar_panels"])
            with pc2:
                calc_type = st.selectbox("Panel Type", [p["name"] for p in SOLAR_PANEL_TYPES],
                                          index=[p["name"] for p in SOLAR_PANEL_TYPES].index(config["panel_type"]))
            with pc3:
                calc_weather = st.selectbox("Weather", list(WEATHER_CONDITIONS), index=0)
            with pc3:
                calc_hours = st.slider("Sun Hours", 2, 12, 6)

            if st.form_submit_button("Calculate"):
                output = get_solar_output(calc_type, calc_panels, calc_weather, calc_hours)
                p = next(x for x in SOLAR_PANEL_TYPES if x["name"] == calc_type)
                system_kw = calc_panels * p["efficiency"] * 1.7
                cost = system_kw * 1000 * p["cost_per_watt"]
                annual_output = output * 365
                payback = cost / (annual_output * 0.12) if annual_output > 0 else 999

                st.success(f"📊 **Daily Output:** {output} kWh | **System Size:** {system_kw:.1f} kW | **Install Cost:** ${cost:,.0f} | **Payback:** {payback:.1f} years")

    # ═══════════════════════════════════════════
    # TAB 3: Energy Consumption
    # ═══════════════════════════════════════════
    with tab3:
        st.subheader("🏠 Energy Consumption Breakdown")
        df = pd.DataFrame(history)
        today_data = history[-1]
        consumption = today_data.get("consumption_by_type", {})

        # Appliance breakdown
        if consumption:
            labels = [APPLIANCE_CATEGORIES.get(k, {"label": k})["label"] for k in consumption.keys()]
            values = list(consumption.values())
            colors = [APPLIANCE_CATEGORIES.get(k, {"color": "#999"})["color"] for k in consumption.keys()]

            c1, c2 = st.columns(2)
            with c1:
                fig = go.Figure(data=[go.Pie(
                    labels=labels, values=values, hole=0.4,
                    marker=dict(colors=colors), textinfo="label+percent", textposition="outside",
                )])
                fig.update_layout(height=400, title="Today's Consumption by Appliance",
                                  margin=dict(t=40, b=20, l=20, r=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                st.subheader("📊 Appliance Details")
                for cat, kwh in sorted(consumption.items(), key=lambda x: x[1], reverse=True):
                    meta = APPLIANCE_CATEGORIES.get(cat, {"label": cat, "color": "#999", "avg_cost": 0.12})
                    daily_cost = kwh * meta["avg_cost"]
                    pct = (kwh / today_data["consumption_kwh"] * 100) if today_data["consumption_kwh"] > 0 else 0
                    st.markdown(f"""
                    <div style="padding:8px;margin:4px 0;border-radius:8px;border-left:4px solid {meta['color']};background:rgba(0,0,0,0.03)">
                        <b>{meta['label']}</b><br/>
                        <span style="font-size:14px">{kwh:.1f} kWh ({pct:.0f}%) • ${daily_cost:.2f}/day</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.divider()

        # 30-day consumption trend by category
        st.subheader("📈 30-Day Consumption by Category")
        category_totals = {}
        for day in history:
            for cat, kwh in day.get("consumption_by_type", {}).items():
                if cat not in category_totals:
                    category_totals[cat] = []
                category_totals[cat].append(kwh)

        if category_totals:
            cat_df = pd.DataFrame(category_totals)
            cat_df["date"] = [d["date"] for d in history]
            fig = px.area(cat_df, x="date", y=list(category_totals.keys()),
                          title="Consumption by Category Over Time")
            fig.update_layout(height=400, xaxis_title="", yaxis_title="kWh",
                              color_discrete_map={k: APPLIANCE_CATEGORIES.get(k, {"color": "#999"})["color"] for k in category_totals.keys()})
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 4: Battery & Grid
    # ═══════════════════════════════════════════
    with tab4:
        st.subheader("🔋 Battery Storage & Grid Interaction")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Battery Capacity", f"{config['battery_capacity_kwh']} kWh")
        with c2:
            st.metric("Current Level", f"{int(today.get('battery_level', 0.75) * 100)}%")
        with c3:
            st.metric("Grid Import", f"{today.get('grid_import_kwh', 0)} kWh")
        with c4:
            st.metric("Grid Export", f"{today.get('grid_export_kwh', 0)} kWh")

        # Battery visualization
        battery_pct = today.get("battery_level", 0.75) * 100
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=battery_pct,
            title={"text": "Battery Level (%)"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#22c55e" if battery_pct > 50 else "#f59e0b" if battery_pct > 20 else "#ef4444"},
                "steps": [
                    {"range": [0, 20], "color": "#fef2f2"},
                    {"range": [20, 50], "color": "#fefce8"},
                    {"range": [50, 100], "color": "#f0fdf4"},
                ],
            },
        ))
        fig.update_layout(height=250, margin=dict(t=60, b=20))
        st.plotly_chart(fig, use_container_width=True)

        # Grid flow over time
        df = pd.DataFrame(history)
        st.subheader("⚡ Grid Import vs Export (30 Days)")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df["date"], y=df["grid_import_kwh"], name="Grid Import",
                             marker_color="#ef4444"))
        fig.add_trace(go.Bar(x=df["date"], y=-df["grid_export_kwh"], name="Grid Export",
                             marker_color="#22c55e"))
        fig.update_layout(barmode="relative", height=350, yaxis_title="kWh",
                          margin=dict(t=30, b=30), legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig, use_container_width=True)

        # Tariff analysis
        st.subheader("💡 Time-of-Use Tariff Analysis")
        st.caption("Understanding when you use grid power helps optimize costs.")
        tariff_data = []
        for period, info in TARIFF_RATES.items():
            tariff_data.append({"Period": info["label"], "Rate ($/kWh)": info["rate"], "Hours": len(info["hours"])})
        tariff_df = pd.DataFrame(tariff_data)
        fig = px.bar(tariff_df, x="Period", y="Rate ($/kWh)", color="Period",
                     color_discrete_map={"Off-Peak (10PM-7AM)": "#22c55e", "Mid-Peak (7AM-11AM, 5PM-10PM)": "#f59e0b", "On-Peak (11AM-5PM)": "#ef4444"})
        fig.update_layout(height=250, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 5: Cost Analysis
    # ═══════════════════════════════════════════
    with tab5:
        st.subheader("💰 Cost Analysis & Savings")
        df = pd.DataFrame(history)

        total_grid_cost = df["grid_cost"].sum()
        total_export_income = df["grid_export_income"].sum()
        total_net_cost = df["net_cost"].sum()
        avg_daily_cost = df["net_cost"].mean()
        monthly_projected = avg_daily_cost * 30

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("💰 Total Grid Cost", f"${total_grid_cost:.2f}")
        with c2:
            st.metric("📈 Export Income", f"${total_export_income:.2f}")
        with c3:
            st.metric("💵 Net Cost (30 Days)", f"${total_net_cost:.2f}")
        with c4:
            st.metric("📊 Projected Monthly", f"${monthly_projected:.2f}")

        st.divider()

        # Without solar comparison
        no_solar_cost = df["consumption_kwh"].sum() * 0.12
        savings = no_solar_cost - total_net_cost

        st.subheader("📊 Solar Savings Comparison")
        c1, c2 = st.columns(2)
        with c1:
            comparison_data = pd.DataFrame({
                "Scenario": ["With Solar", "Without Solar"],
                "30-Day Cost": [total_net_cost, no_solar_cost],
            })
            fig = px.bar(comparison_data, x="Scenario", y="30-Day Cost", color="Scenario",
                         color_discrete_map={"With Solar": "#22c55e", "Without Solar": "#ef4444"})
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.metric("🌟 30-Day Savings", f"${savings:.2f}", delta=f"{savings / no_solar_cost * 100:.0f}% reduction" if no_solar_cost > 0 else None)
            annual_savings = savings * 12
            st.metric("📅 Projected Annual Savings", f"${annual_savings:.2f}")
            roi_years = (config["system_size_kw"] * 1000 * 2.80) / annual_savings if annual_savings > 0 else 999
            st.metric("⏱️ System Payback", f"{roi_years:.1f} years")

        # Daily cost trend
        fig = px.bar(df, x="date", y=["grid_cost", "grid_export_income"],
                     title="Daily Grid Cost vs Export Income",
                     barmode="group", color_discrete_map={"grid_cost": "#ef4444", "grid_export_income": "#22c55e"})
        fig.update_layout(height=350, xaxis_title="", yaxis_title="USD",
                          margin=dict(t=40, b=30))
        st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 6: Carbon Impact
    # ═══════════════════════════════════════════
    with tab6:
        st.subheader("🌍 Carbon Impact")
        df = pd.DataFrame(history)

        total_co2_saved = df["co2_saved_kg"].sum()
        total_solar = df["solar_kwh"].sum()
        trees_equivalent = int(total_co2_saved / 21)  # ~21kg CO2 per tree per year
        cars_removed = round(total_co2_saved / 4600, 2)  # ~4.6 tonnes per car per year
        flights_offset = round(total_co2_saved / 255, 2)  # ~255kg per short-haul flight

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🌍 CO₂ Saved", f"{total_co2_saved:.1f} kg")
        with c2:
            st.metric("🌳 Trees Equivalent", f"{trees_equivalent:,}")
        with c3:
            st.metric("🚗 Cars Removed", f"{cars_removed}")
        with c4:
            st.metric("✈️ Flights Offset", f"{flights_offset}")

        # CO2 savings trend
        fig = px.area(df, x="date", y="co2_saved_kg", title="Daily CO₂ Savings (kg)",
                      color_discrete_sequence=["#22c55e"])
        fig.update_layout(height=300, xaxis_title="", yaxis_title="kg CO₂")
        st.plotly_chart(fig, use_container_width=True)

        # Annual projection
        st.subheader("📅 Annual Impact Projection")
        annual_solar = total_solar * 12
        annual_co2 = total_co2_saved * 12
        annual_trees = int(annual_co2 / 21)
        annual_cars = round(annual_co2 / 4600, 1)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("⚡ Annual Solar", f"{annual_solar:,.0f} kWh")
        with c2:
            st.metric("🌍 Annual CO₂", f"{annual_co2:,.0f} kg")
        with c3:
            st.metric("🌳 Trees/Year", f"{annual_trees:,}")
        with c4:
            st.metric("🚗 Cars/Year", f"{annual_cars}")

    # ═══════════════════════════════════════════
    # TAB 7: Settings
    # ═══════════════════════════════════════════
    with tab7:
        st.subheader("⚙️ Energy System Settings")

        with st.form("energy_settings"):
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("Solar Panels", 1, 50, config["solar_panels"], key="set_panels")
                st.selectbox("Panel Type", [p["name"] for p in SOLAR_PANEL_TYPES],
                             index=[p["name"] for p in SOLAR_PANEL_TYPES].index(config["panel_type"]), key="set_panel_type")
                st.number_input("System Size (kW)", 0.5, 20.0, config["system_size_kw"], step=0.5, key="set_size")
                st.number_input("Battery Capacity (kWh)", 1.0, 50.0, config["battery_capacity_kwh"], step=0.5, key="set_battery")
            with c2:
                st.number_input("Home Size (sqft)", 500, 10000, config["home_sqft"], key="set_sqft")
                st.number_input("Occupants", 1, 10, config["occupants"], key="set_occupants")
                st.checkbox("Electric Vehicle", config["ev_owned"], key="set_ev")
                st.text_input("Location", config["location"], key="set_location")
                st.number_input("Monthly Bill Target ($)", 0, 500, config["monthly_bill_target"], key="set_target")

            if st.form_submit_button("💾 Save Settings"):
                st.session_state.energy_config.update({
                    "solar_panels": st.session_state.set_panels,
                    "panel_type": st.session_state.set_panel_type,
                    "system_size_kw": st.session_state.set_size,
                    "battery_capacity_kwh": st.session_state.set_battery,
                    "home_sqft": st.session_state.set_sqft,
                    "occupants": st.session_state.set_occupants,
                    "ev_owned": st.session_state.set_ev,
                    "location": st.session_state.set_location,
                    "monthly_bill_target": st.session_state.set_target,
                })
                st.session_state.energy_history = []
                st.success("✅ Settings saved! Dashboard will regenerate data.")
                st.rerun()


# ─── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    render_smart_energy_hub()
