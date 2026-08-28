"""
Home Energy Audit Simulator
===========================
Analyze home energy usage, identify inefficiencies, recommend upgrades
with ROI calculations, insulation scoring, and energy savings projections.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import random

# ─── Appliance Database ───────────────────────────────────────────────────
APPLIANCES = [
    {"name": "Central AC", "category": "HVAC", "wattage": 3500, "hours_per_day": 8,
     "efficiency_rating": "SEER 14", "age_years": 7, "monthly_kwh": 840, "monthly_cost": 113.40,
     "carbon_kg": 504, "status": "Moderate", "replacement_cost": 4500,
     "energy_star_alternative": {"name": "SEER 20 Heat Pump", "monthly_kwh": 588, "monthly_cost": 79.38,
                                 "carbon_kg": 352.8, "cost": 6500},
     "tips": ["Clean filter monthly", "Set thermostat to 78°F summer", "Use programmable thermostat"]},
    {"name": "Water Heater", "category": "Plumbing", "wattage": 4500, "hours_per_day": 3,
     "efficiency_rating": "EF 0.62", "age_years": 12, "monthly_kwh": 405, "monthly_cost": 54.68,
     "carbon_kg": 243, "status": "Poor", "replacement_cost": 1200,
     "energy_star_alternative": {"name": "Heat Pump Water Heater", "monthly_kwh": 135, "monthly_cost": 18.23,
                                 "carbon_kg": 81, "cost": 2200},
     "tips": ["Insulate tank", "Lower to 120°F", "Install low-flow showerheads"]},
    {"name": "Refrigerator", "category": "Kitchen", "wattage": 150, "hours_per_day": 24,
     "efficiency_rating": "Energy Star", "age_years": 5, "monthly_kwh": 108, "monthly_cost": 14.58,
     "carbon_kg": 64.8, "status": "Good", "replacement_cost": 1200,
     "energy_star_alternative": {"name": "Smart Inverter Fridge", "monthly_kwh": 72, "monthly_cost": 9.72,
                                 "carbon_kg": 43.2, "cost": 1500},
     "tips": ["Keep at 37°F / 0°F freezer", "Clean coils annually", "Check door seals"]},
    {"name": "Dryer", "category": "Laundry", "wattage": 5000, "hours_per_day": 1,
     "efficiency_rating": "Standard", "age_years": 8, "monthly_kwh": 150, "monthly_cost": 20.25,
     "carbon_kg": 90, "status": "Moderate", "replacement_cost": 800,
     "energy_star_alternative": {"name": "Heat Pump Dryer", "monthly_kwh": 60, "monthly_cost": 8.10,
                                 "carbon_kg": 36, "cost": 1200},
     "tips": ["Clean lint trap every load", "Use moisture sensor setting", "Air dry when possible"]},
    {"name": "Lighting (all bulbs)", "category": "Lighting", "wattage": 800, "hours_per_day": 6,
     "efficiency_rating": "60% LED / 40% Incandescent", "age_years": 3, "monthly_kwh": 144,
     "monthly_cost": 19.44, "carbon_kg": 86.4, "status": "Mixed", "replacement_cost": 0,
     "energy_star_alternative": {"name": "100% LED Smart Bulbs", "monthly_kwh": 36, "monthly_cost": 4.86,
                                 "carbon_kg": 21.6, "cost": 200},
     "tips": ["Replace remaining incandescent with LED", "Use dimmer switches", "Install motion sensors"]},
    {"name": "Oven & Stove", "category": "Kitchen", "wattage": 3000, "hours_per_day": 1.5,
     "efficiency_rating": "Electric Coil", "age_years": 10, "monthly_kwh": 135, "monthly_cost": 18.23,
     "carbon_kg": 81, "status": "Poor", "replacement_cost": 2000,
     "energy_star_alternative": {"name": "Induction Cooktop", "monthly_kwh": 90, "monthly_cost": 12.15,
                                 "carbon_kg": 54, "cost": 2500},
     "tips": ["Use lids on pots", "Match pan size to burner", "Use microwave for reheating"]},
    {"name": "Washing Machine", "category": "Laundry", "wattage": 500, "hours_per_day": 1,
     "efficiency_rating": "Top Load Standard", "age_years": 9, "monthly_kwh": 30, "monthly_cost": 4.05,
     "carbon_kg": 18, "status": "Moderate", "replacement_cost": 900,
     "energy_star_alternative": {"name": "Front Load HE Washer", "monthly_kwh": 12, "monthly_cost": 1.62,
                                 "carbon_kg": 7.2, "cost": 1100},
     "tips": ["Wash in cold water", "Run full loads only", "Use high-spin cycle"]},
    {"name": "Entertainment System", "category": "Electronics", "wattage": 400, "hours_per_day": 5,
     "efficiency_rating": "Standard", "age_years": 4, "monthly_kwh": 60, "monthly_cost": 8.10,
     "carbon_kg": 36, "status": "Good", "replacement_cost": 0,
     "energy_star_alternative": {"name": "Energy Star Smart TV", "monthly_kwh": 20, "monthly_cost": 2.70,
                                 "carbon_kg": 12, "cost": 600},
     "tips": ["Use power strip (kill phantom load)", "Lower brightness", "Set auto-off timer"]},
    {"name": "Desktop Computer", "category": "Electronics", "wattage": 300, "hours_per_day": 8,
     "efficiency_rating": "Standard", "age_years": 5, "monthly_kwh": 72, "monthly_cost": 9.72,
     "carbon_kg": 43.2, "status": "Good", "replacement_cost": 0,
     "energy_star_alternative": {"name": "Laptop (replaces desktop)", "monthly_kwh": 14.4, "monthly_cost": 1.94,
                                 "carbon_kg": 8.64, "cost": 1000},
     "tips": ["Enable sleep mode", "Use laptop instead if possible", "Turn off when not in use"]},
    {"name": "Pool Pump", "category": "Outdoor", "wattage": 2000, "hours_per_day": 6,
     "efficiency_rating": "Single Speed", "age_years": 6, "monthly_kwh": 360, "monthly_cost": 48.60,
     "carbon_kg": 216, "status": "Poor", "replacement_cost": 800,
     "energy_star_alternative": {"name": "Variable Speed Pump", "monthly_kwh": 108, "monthly_cost": 14.58,
                                 "carbon_kg": 64.8, "cost": 1500},
     "tips": ["Run 6-8 hrs max", "Use timer for off-peak hours", "Clean skimmer basket weekly"]},
]

# ─── Insulation Data ──────────────────────────────────────────────────────
INSULATION_AREAS = [
    {"area": "Attic", "current_r_value": 19, "recommended_r_value": 49, "condition": "Fair",
     "heat_loss_pct": 25, "upgrade_cost": 2500, "annual_savings": 600, "material": "Fiberglass Batt",
     "sealing_needed": True, "air_leak_pct": 8},
    {"area": "Walls (Exterior)", "current_r_value": 13, "recommended_r_value": 21, "condition": "Good",
     "heat_loss_pct": 15, "upgrade_cost": 4000, "annual_savings": 350, "material": "Blown-in Cellulose",
     "sealing_needed": False, "air_leak_pct": 5},
    {"area": "Floor/Crawlspace", "current_r_value": 10, "recommended_r_value": 25, "condition": "Poor",
     "heat_loss_pct": 12, "upgrade_cost": 1800, "annual_savings": 280, "material": "Spray Foam",
     "sealing_needed": True, "air_leak_pct": 12},
    {"area": "Windows", "current_r_value": 3, "recommended_r_value": 5, "condition": "Fair",
     "heat_loss_pct": 20, "upgrade_cost": 8000, "annual_savings": 450, "material": "Double-Pane Low-E",
     "sealing_needed": True, "air_leak_pct": 10},
    {"area": "Garage Door", "current_r_value": 6, "recommended_r_value": 12, "condition": "Poor",
     "heat_loss_pct": 8, "upgrade_cost": 2000, "annual_savings": 180, "material": "Insulated Panels",
     "sealing_needed": True, "air_leak_pct": 15},
    {"area": "Basement", "current_r_value": 8, "recommended_r_value": 15, "condition": "Good",
     "heat_loss_pct": 5, "upgrade_cost": 3000, "annual_savings": 150, "material": "Rigid Foam Board",
     "sealing_needed": False, "air_leak_pct": 3},
]

# ─── Solar Panel Data ─────────────────────────────────────────────────────
SOLAR_CONFIGS = [
    {"panels": 10, "capacity_kwh": 4.0, "annual_output": 5600, "cost_before_incentive": 22000,
     "cost_after_incentive": 15400, "payback_years": 8.5, "monthly_bill_reduction": 150,
     "co2_offset_tons": 3.9, "roof_area_sqft": 200, "trees_equivalent": 65},
    {"panels": 15, "capacity_kwh": 6.0, "annual_output": 8400, "cost_before_incentive": 33000,
     "cost_after_incentive": 23100, "payback_years": 7.2, "monthly_bill_reduction": 225,
     "co2_offset_tons": 5.9, "roof_area_sqft": 300, "trees_equivalent": 98},
    {"panels": 20, "capacity_kwh": 8.0, "annual_output": 11200, "cost_before_incentive": 44000,
     "cost_after_incentive": 30800, "payback_years": 6.5, "monthly_bill_reduction": 300,
     "co2_offset_tons": 7.8, "roof_area_sqft": 400, "trees_equivalent": 130},
    {"panels": 25, "capacity_kwh": 10.0, "annual_output": 14000, "cost_before_incentive": 55000,
     "cost_after_incentive": 38500, "payback_years": 5.8, "monthly_bill_reduction": 375,
     "co2_offset_tons": 9.8, "roof_area_sqft": 500, "trees_equivalent": 162},
]

# ─── HVAC Efficiency Data ─────────────────────────────────────────────────
HVAC_SYSTEMS = [
    {"name": "Central AC (Current)", "seer": 14, "annual_kwh": 4800, "annual_cost": 648,
     "carbon_tons": 2.88, "lifespan_years": 15, "monthly_comfort": 7},
    {"name": "Central AC (High-Efficiency)", "seer": 20, "annual_kwh": 3360, "annual_cost": 453.60,
     "carbon_tons": 2.02, "lifespan_years": 20, "monthly_comfort": 8},
    {"name": "Heat Pump (Air-Source)", "seer": 18, "annual_kwh": 2800, "annual_cost": 378,
     "carbon_tons": 1.68, "lifespan_years": 15, "monthly_comfort": 9},
    {"name": "Mini-Split Ductless", "seer": 22, "annual_kwh": 2400, "annual_cost": 324,
     "carbon_tons": 1.44, "lifespan_years": 20, "monthly_comfort": 9},
    {"name": "Geothermal Heat Pump", "seer": 30, "annual_kwh": 1680, "annual_cost": 226.80,
     "carbon_tons": 1.01, "lifespan_years": 25, "monthly_comfort": 10},
]

# ─── Energy Tips ───────────────────────────────────────────────────────────
ENERGY_TIPS = [
    {"tip": "Switch to LED bulbs everywhere", "category": "Lighting", "annual_savings": 225,
     "difficulty": "Easy", "upfront_cost": 50, "payback_months": 3, "co2_saved_kg": 135},
    {"tip": "Install smart thermostat", "category": "HVAC", "annual_savings": 180,
     "difficulty": "Easy", "upfront_cost": 250, "payback_months": 17, "co2_saved_kg": 800},
    {"tip": "Add attic insulation (R-49)", "category": "Insulation", "annual_savings": 600,
     "difficulty": "Medium", "upfront_cost": 2500, "payback_months": 50, "co2_saved_kg": 400},
    {"tip": "Seal air leaks around windows/doors", "category": "Insulation", "annual_savings": 200,
     "difficulty": "Easy", "upfront_cost": 100, "payback_months": 6, "co2_saved_kg": 150},
    {"tip": "Upgrade to Energy Star refrigerator", "category": "Appliance", "annual_savings": 58,
     "difficulty": "Medium", "upfront_cost": 1500, "payback_months": 310, "co2_saved_kg": 260},
    {"tip": "Install low-flow showerheads", "category": "Plumbing", "annual_savings": 70,
     "difficulty": "Easy", "upfront_cost": 40, "payback_months": 7, "co2_saved_kg": 50},
    {"tip": "Use power strips for electronics", "category": "Electronics", "annual_savings": 100,
     "difficulty": "Easy", "upfront_cost": 60, "payback_months": 7, "co2_saved_kg": 200},
    {"tip": "Wash clothes in cold water", "category": "Laundry", "annual_savings": 60,
     "difficulty": "Easy", "upfront_cost": 0, "payback_months": 0, "co2_saved_kg": 120},
    {"tip": "Install variable speed pool pump", "category": "Outdoor", "annual_savings": 418,
     "difficulty": "Medium", "upfront_cost": 1500, "payback_months": 43, "co2_saved_kg": 900},
    {"tip": "Upgrade water heater to heat pump", "category": "Plumbing", "annual_savings": 437,
     "difficulty": "Hard", "upfront_cost": 2200, "payback_months": 60, "co2_saved_kg": 1944},
]


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: ENERGY OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
def render_energy_overview():
    st.markdown("### ⚡ Home Energy Overview")

    total_kwh = sum(a["monthly_kwh"] for a in APPLIANCES)
    total_cost = sum(a["monthly_cost"] for a in APPLIANCES)
    total_carbon = sum(a["carbon_kg"] for a in APPLIANCES)
    total_annual_cost = total_cost * 12
    total_annual_kwh = total_kwh * 12

    # KPIs
    cols = st.columns(5)
    for i, (label, value, color) in enumerate([
        ("Monthly Usage", f"{total_kwh:,.0f} kWh", "#8b5cf6"),
        ("Monthly Cost", f"${total_cost:,.2f}", "#3b82f6"),
        ("Monthly CO₂", f"{total_carbon:,.0f} kg", "#f97316"),
        ("Annual Cost", f"${total_annual_cost:,.0f}", "#22c55e"),
        ("Annual kWh", f"{total_annual_kwh:,.0f}", "#ec4899"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Energy usage by category pie
    cat_kwh = {}
    cat_cost = {}
    for a in APPLIANCES:
        cat = a["category"]
        cat_kwh[cat] = cat_kwh.get(cat, 0) + a["monthly_kwh"]
        cat_cost[cat] = cat_cost.get(cat, 0) + a["monthly_cost"]

    col1, col2 = st.columns(2)
    with col1:
        kwh_df = pd.DataFrame(list(cat_kwh.items()), columns=["Category", "kWh"])
        fig = px.pie(kwh_df, values="kWh", names="Category", title="Energy Usage by Category (kWh)",
                     color_discrete_sequence=px.colors.qualitative.Set2)
        fig.update_layout(template="plotly_dark", height=380, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        cost_df = pd.DataFrame(list(cat_cost.items()), columns=["Category", "Cost"])
        fig = px.pie(cost_df, values="Cost", names="Category", title="Monthly Cost by Category ($)",
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(template="plotly_dark", height=380, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    # Appliance bar chart
    app_df = pd.DataFrame([
        {"Appliance": a["name"], "kWh/month": a["monthly_kwh"], "Cost/month": a["monthly_cost"],
         "CO₂ (kg)": a["carbon_kg"], "Status": a["status"]}
        for a in APPLIANCES
    ])
    fig = px.bar(app_df, x="Appliance", y=["kWh/month", "Cost/month"], barmode="group",
                 title="Appliance Comparison",
                 color_discrete_map={"kWh/month": "#8b5cf6", "Cost/month": "#22c55e"})
    fig.update_layout(template="plotly_dark", height=400, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Appliance cards
    st.markdown("#### 🏠 Appliance Details")
    for a in sorted(APPLIANCES, key=lambda x: x["monthly_kwh"], reverse=True):
        status_color = {"Good": "#22c55e", "Moderate": "#eab308", "Poor": "#ef4444",
                        "Mixed": "#f97316"}.get(a["status"], "#6b7280")
        with st.expander(f"{'🟢' if a['status'] == 'Good' else '🟡' if a['status'] in ['Moderate', 'Mixed'] else '🔴'} {a['name']} — {a['monthly_kwh']} kWh | ${a['monthly_cost']:.2f}/mo", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Category:** {a['category']} | **Wattage:** {a['wattage']}W")
                st.markdown(f"**Hours/day:** {a['hours_per_day']} | **Age:** {a['age_years']} years")
                st.markdown(f"**Efficiency:** {a['efficiency_rating']} | **Status:** :{status_color}[{a['status']}]")
                st.markdown(f"**CO₂:** {a['carbon_kg']} kg/month | **Annual Cost:** ${a['monthly_cost']*12:,.0f}")
            with col2:
                alt = a["energy_star_alternative"]
                savings = a["monthly_kwh"] - alt["monthly_kwh"]
                savings_pct = savings / a["monthly_kwh"] * 100
                st.markdown(f"**🔄 Upgrade: {alt['name']}**")
                st.markdown(f"- New monthly kWh: {alt['monthly_kwh']} ({savings_pct:.0f}% savings)")
                st.markdown(f"- New monthly cost: ${alt['monthly_cost']:.2f}")
                st.markdown(f"- Upgrade cost: ${alt['cost']:,}")
                st.markdown(f"- Monthly savings: ${a['monthly_cost'] - alt['monthly_cost']:.2f}")
                st.progress(1 - savings_pct/100)

            st.markdown("**💡 Tips:**")
            for tip in a["tips"]:
                st.markdown(f"  • {tip}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: INSULATION & AIR SEALING
# ═══════════════════════════════════════════════════════════════════════════
def render_insulation():
    st.markdown("### 🧱 Insulation & Air Sealing Audit")

    total_heat_loss = sum(a["heat_loss_pct"] for a in INSULATION_AREAS)
    total_upgrade_cost = sum(a["upgrade_cost"] for a in INSULATION_AREAS)
    total_annual_savings = sum(a["annual_savings"] for a in INSULATION_AREAS)
    payback = total_upgrade_cost / total_annual_savings if total_annual_savings else 0

    cols = st.columns(5)
    for i, (label, value, color) in enumerate([
        ("Areas Audited", len(INSULATION_AREAS), "#8b5cf6"),
        ("Total Heat Loss", f"{total_heat_loss}%", "#ef4444"),
        ("Upgrade Cost", f"${total_upgrade_cost:,}", "#3b82f6"),
        ("Annual Savings", f"${total_annual_savings:,}", "#22c55e"),
        ("Payback Period", f"{payback:.1f} yrs", "#f97316"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Heat loss chart
    ins_df = pd.DataFrame([{"Area": a["area"], "Heat Loss %": a["heat_loss_pct"],
                            "Current R": a["current_r_value"], "Recommended R": a["recommended_r_value"]}
                           for a in INSULATION_AREAS])
    fig = px.bar(ins_df, x="Area", y="Heat Loss %", title="Heat Loss by Area",
                 color="Heat Loss %", color_continuous_scale="RdYlGn_r")
    fig.update_layout(template="plotly_dark", height=350, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # R-value comparison
    fig = go.Figure()
    fig.add_trace(go.Bar(x=ins_df["Area"], y=ins_df["Current R"], name="Current R-Value", marker_color="#f97316"))
    fig.add_trace(go.Bar(x=ins_df["Area"], y=ins_df["Recommended R"], name="Recommended R-Value", marker_color="#22c55e"))
    fig.update_layout(barmode="group", title="R-Value: Current vs Recommended", template="plotly_dark",
                      height=350, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Area cards
    for area in sorted(INSULATION_AREAS, key=lambda x: x["heat_loss_pct"], reverse=True):
        cond_color = {"Good": "#22c55e", "Fair": "#eab308", "Poor": "#ef4444"}.get(area["condition"], "#6b7280")
        roi = (area["annual_savings"] / area["upgrade_cost"] * 100) if area["upgrade_cost"] > 0 else 100
        with st.expander(f"{'🟢' if area['condition'] == 'Good' else '🟡' if area['condition'] == 'Fair' else '🔴'} {area['area']} — R-{area['current_r_value']} → R-{area['recommended_r_value']} | {area['heat_loss_pct']}% heat loss", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Condition:** :{cond_color}[{area['condition']}]")
                st.markdown(f"**Material:** {area['material']}")
                st.markdown(f"**Air Leak:** {area['air_leak_pct']}%")
                if area["sealing_needed"]:
                    st.warning("⚠️ Air sealing recommended")
            with col2:
                st.markdown(f"**Upgrade Cost:** ${area['upgrade_cost']:,}")
                st.markdown(f"**Annual Savings:** ${area['annual_savings']}")
                st.markdown(f"**ROI:** {roi:.1f}%")
            with col3:
                st.markdown(f"**R-Value Gap:** +{area['recommended_r_value'] - area['current_r_value']}")
                st.progress(area["current_r_value"] / area["recommended_r_value"])


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: HVAC ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def render_hvac():
    st.markdown("### ❄️ HVAC System Analysis")

    current = HVAC_SYSTEMS[0]
    best = HVAC_SYSTEMS[-1]
    annual_savings_best = current["annual_cost"] - best["annual_cost"]
    carbon_reduction = (current["carbon_tons"] - best["carbon_tons"]) * 1000

    cols = st.columns(4)
    for i, (label, value, color) in enumerate([
        ("Current System", current["name"], "#f97316"),
        ("Current SEER", f"{current['seer']}", "#ef4444"),
        ("Best SEER", f"{best['seer']}", "#22c55e"),
        ("Max Annual Savings", f"${annual_savings_best:,.0f}", "#3b82f6"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:18px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # HVAC comparison
    hvac_df = pd.DataFrame([
        {"System": s["name"], "SEER": s["seer"], "Annual kWh": s["annual_kwh"],
         "Annual Cost": s["annual_cost"], "Carbon (tons)": s["carbon_tons"],
         "Comfort (1-10)": s["monthly_comfort"], "Lifespan": s["lifespan_years"]}
        for s in HVAC_SYSTEMS
    ])

    fig = px.bar(hvac_df, x="System", y=["Annual kWh", "Annual Cost", "Carbon (tons)"],
                 barmode="group", title="HVAC System Comparison",
                 color_discrete_map={"Annual kWh": "#8b5cf6", "Annual Cost": "#3b82f6", "Carbon (tons)": "#ef4444"})
    fig.update_layout(template="plotly_dark", height=400, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # SEER efficiency radar
    fig = go.Figure()
    for s in HVAC_SYSTEMS:
        fig.add_trace(go.Scatterpolar(
            r=[s["seer"], s["annual_cost"], s["monthly_comfort"]*10, s["lifespan_years"]],
            theta=["SEER Efficiency", "Annual Cost (÷10)", "Comfort (×10)", "Lifespan"],
            fill="toself", name=s["name"]))
    fig.update_layout(template="plotly_dark", height=400, polar=dict(
        radialaxis=dict(visible=True, range=[0, 100]),
        bgcolor="rgba(0,0,0,0)"), paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # System cards
    for s in HVAC_SYSTEMS:
        is_current = s == current
        with st.expander(f"{'📍 ' if is_current else ''}{s['name']} — SEER {s['seer']} | ${s['annual_cost']}/yr | {s['carbon_tons']}t CO₂", expanded=is_current):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Annual kWh:** {s['annual_kwh']:,}")
                st.markdown(f"**Annual Cost:** ${s['annual_cost']:,.0f}")
            with col2:
                st.markdown(f"**Carbon:** {s['carbon_tons']} tons/yr")
                st.markdown(f"**Comfort:** {s['monthly_comfort']}/10")
            with col3:
                st.markdown(f"**Lifespan:** {s['lifespan_years']} years")
                savings_vs_current = current["annual_cost"] - s["annual_cost"]
                if savings_vs_current > 0:
                    st.success(f"💰 Saves ${savings_vs_current:,.0f}/yr vs current")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: SOLAR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
def render_solar():
    st.markdown("### ☀️ Solar Panel Analysis")

    cols = st.columns(4)
    for i, (label, value, color) in enumerate([
        ("Configurations", len(SOLAR_CONFIGS), "#8b5cf6"),
        ("Best Payback", f"{min(s['payback_years'] for s in SOLAR_CONFIGS)} yrs", "#22c55e"),
        ("Max Output", f"{max(s['annual_output'] for s in SOLAR_CONFIGS):,} kWh", "#3b82f6"),
        ("30% Tax Credit", "Included", "#f97316"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Solar comparison
    solar_df = pd.DataFrame([
        {"Panels": s["panels"], "Capacity (kW)": s["capacity_kwh"],
         "Annual Output (kWh)": s["annual_output"], "Cost (after credit)": s["cost_after_incentive"],
         "Payback (years)": s["payback_years"], "Monthly Savings": s["monthly_bill_reduction"],
         "CO₂ Offset (tons)": s["co2_offset_tons"]}
        for s in SOLAR_CONFIGS
    ])

    fig = px.line(solar_df, x="Panels", y=["Cost (after credit)", "Annual Output (kWh)"],
                  title="Solar Configuration Comparison",
                  color_discrete_map={"Cost (after credit)": "#f97316", "Annual Output (kWh)": "#22c55e"})
    fig.update_layout(template="plotly_dark", height=380, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Payback analysis
    fig = px.bar(solar_df, x="Panels", y="Payback (years)", color="Payback (years)",
                 color_continuous_scale="RdYlGn_r", title="Payback Period by Configuration")
    fig.update_layout(template="plotly_dark", height=300, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Solar config cards
    for s in SOLAR_CONFIGS:
        with st.expander(f"☀️ {s['panels']} Panels — {s['capacity_kwh']}kW | ${s['cost_after_incentive']:,} | {s['payback_years']}yr payback", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Annual Output:** {s['annual_output']:,} kWh")
                st.markdown(f"**Monthly Savings:** ${s['monthly_bill_reduction']}")
                st.markdown(f"**Annual Savings:** ${s['monthly_bill_reduction']*12:,}")
                st.markdown(f"**Roof Area Needed:** {s['roof_area_sqft']} sq ft")
            with col2:
                st.markdown(f"**CO₂ Offset:** {s['co2_offset_tons']} tons/yr")
                st.markdown(f"**Trees Equivalent:** {s['trees_equivalent']}")
                st.markdown(f"**Before Incentive:** ${s['cost_before_incentive']:,}")
                st.markdown(f"**After 30% Credit:** ${s['cost_after_incentive']:,}")

            # 25-year savings projection
            years = list(range(0, 26))
            cumulative = [s["monthly_bill_reduction"] * 12 * y - s["cost_after_incentive"] for y in years]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=cumulative, mode="lines",
                                     fill="tozeroy", line=dict(color="#22c55e" if cumulative[-1] > 0 else "#ef4444")))
            fig.add_hline(y=0, line_dash="dash", line_color="#6b7280")
            fig.update_layout(title="25-Year Savings Projection", template="plotly_dark",
                              height=200, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="#e2e8f0"), xaxis_title="Years", yaxis_title="Cumulative $")
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5: ENERGY SAVINGS PLAN
# ═══════════════════════════════════════════════════════════════════════════
def render_savings_plan():
    st.markdown("### 💰 Energy Savings Action Plan")

    total_savings = sum(t["annual_savings"] for t in ENERGY_TIPS)
    total_co2 = sum(t["co2_saved_kg"] for t in ENERGY_TIPS)
    easy_count = sum(1 for t in ENERGY_TIPS if t["difficulty"] == "Easy")

    cols = st.columns(4)
    for i, (label, value, color) in enumerate([
        ("Total Tips", len(ENERGY_TIPS), "#8b5cf6"),
        ("Potential Savings", f"${total_savings:,}/yr", "#22c55e"),
        ("CO₂ Reduction", f"{total_co2:,} kg", "#3b82f6"),
        ("Easy Actions", f"{easy_count}/{len(ENERGY_TIPS)}", "#f97316"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Savings by category
    cat_savings = {}
    for t in ENERGY_TIPS:
        cat_savings[t["category"]] = cat_savings.get(t["category"], 0) + t["annual_savings"]

    fig = px.bar(x=list(cat_savings.keys()), y=list(cat_savings.values()),
                 title="Savings Potential by Category", color=list(cat_savings.values()),
                 color_continuous_scale="Greens")
    fig.update_layout(template="plotly_dark", height=350, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # Tip cards
    for tip in sorted(ENERGY_TIPS, key=lambda x: x["annual_savings"], reverse=True):
        diff_color = {"Easy": "#22c55e", "Medium": "#eab308", "Hard": "#ef4444"}[tip["difficulty"]]
        payback_display = f"{tip['payback_months']} mo" if tip["payback_months"] > 0 else "Immediate"
        with st.expander(f"{'🟢' if tip['difficulty'] == 'Easy' else '🟡' if tip['difficulty'] == 'Medium' else '🔴'} {tip['tip']} — ${tip['annual_savings']}/yr savings", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Category:** {tip['category']}")
                st.markdown(f"**Difficulty:** :{diff_color}[{tip['difficulty']}]")
                st.markdown(f"**Upfront Cost:** ${tip['upfront_cost']:,}")
            with col2:
                st.markdown(f"**Annual Savings:** ${tip['annual_savings']}")
                st.markdown(f"**Payback:** {payback_display}")
                st.markdown(f"**CO₂ Saved:** {tip['co2_saved_kg']:,} kg/yr")
            with col3:
                roi = (tip["annual_savings"] / tip["upfront_cost"] * 100) if tip["upfront_cost"] > 0 else 999
                st.metric("ROI", f"{roi:.0f}%", delta=f"${tip['annual_savings']*10:,} over 10 yrs")

    # Interactive savings calculator
    st.markdown("---")
    st.markdown("#### 🧮 Custom Savings Calculator")

    selected = []
    for i, tip in enumerate(ENERGY_TIPS):
        if st.checkbox(f"{tip['tip']} (${tip['annual_savings']}/yr)", key=f"save_{i}"):
            selected.append(tip)

    if selected:
        total = sum(t["annual_savings"] for t in selected)
        total_invest = sum(t["upfront_cost"] for t in selected)
        total_co2_sel = sum(t["co2_saved_kg"] for t in selected)
        st.success(f"""
        **📊 Your Savings Summary:**
        - Annual savings: **${total:,}**
        - Total investment: **${total_invest:,}**
        - CO₂ reduction: **{total_co2_sel:,} kg/yr**
        - 10-year net savings: **${total*10 - total_invest:,}**
        - Trees equivalent: **{total_co2_sel // 22} trees**
        """)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="Home Energy Audit Simulator", page_icon="⚡", layout="wide")

    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: rgba(255,255,255,0.03); border-radius: 12px; padding: 6px; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 10px 20px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #f59e0b, #ef4444); color: white; }
    .stExpander { background: rgba(255,255,255,0.02); border: 1px solid rgba(245,158,11,0.2); border-radius: 10px; }
    h1 { background: linear-gradient(135deg, #f59e0b, #ef4444, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    h2 { background: linear-gradient(135deg, #f59e0b, #ef4444); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>""", unsafe_allow_html=True)

    st.markdown("# ⚡ Home Energy Audit Simulator")
    st.markdown("Analyze your home's energy usage, find inefficiencies, and plan upgrades with ROI calculations.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚡ Energy Overview", "🧱 Insulation Audit", "❄️ HVAC Analysis",
        "☀️ Solar Panels", "💰 Savings Plan"
    ])

    with tab1:
        render_energy_overview()
    with tab2:
        render_insulation()
    with tab3:
        render_hvac()
    with tab4:
        render_solar()
    with tab5:
        render_savings_plan()


if __name__ == "__main__":
    main()
