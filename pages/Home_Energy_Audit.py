"""
pages/Home_Energy_Audit.py
--------------------------
Streamlit page: Home Energy Audit Simulator.

Analyze home energy consumption, get insulation recommendations, size
solar panel systems, calculate ROI, and visualize energy savings over time.
"""

import math
from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Home Energy Audit Simulator",
    page_icon="🏠",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Energy constants & defaults
# ---------------------------------------------------------------------------

APPLIANCE_DATA = {
    "HVAC (Heating/Cooling)": {"watts": 3500, "hours_day": 8, "icon": "🌡️", "category": "HVAC"},
    "Water Heater": {"watts": 4500, "hours_day": 3, "icon": "🚿", "category": "Water"},
    "Refrigerator": {"watts": 150, "hours_day": 24, "icon": "🧊", "category": "Appliance"},
    "Washing Machine": {"watts": 500, "hours_day": 1, "icon": "👕", "category": "Appliance"},
    "Dryer": {"watts": 3000, "hours_day": 1, "icon": "👔", "category": "Appliance"},
    "Dishwasher": {"watts": 1800, "hours_day": 1, "icon": "🍽️", "category": "Appliance"},
    "Oven/Stove": {"watts": 2500, "hours_day": 1.5, "icon": "🍳", "category": "Appliance"},
    "Lighting (LED)": {"watts": 60, "hours_day": 6, "icon": "💡", "category": "Lighting"},
    "Lighting (Incandescent)": {"watts": 100, "hours_day": 6, "icon": "💡", "category": "Lighting"},
    "Television": {"watts": 120, "hours_day": 5, "icon": "📺", "category": "Electronics"},
    "Computer/Laptop": {"watts": 200, "hours_day": 8, "icon": "💻", "category": "Electronics"},
    " Gaming Console": {"watts": 150, "hours_day": 3, "icon": "🎮", "category": "Electronics"},
    "Ceiling Fan": {"watts": 75, "hours_day": 10, "icon": "🌀", "category": "HVAC"},
    "Microwave": {"watts": 1100, "hours_day": 0.3, "icon": "📦", "category": "Appliance"},
    "Vacuum Cleaner": {"watts": 1400, "hours_day": 0.5, "icon": "🧹", "category": "Appliance"},
}

INSULATION_TYPES = {
    "None": {"r_value": 0, "cost_per_sqft": 0, "savings_pct": 0},
    "Fiberglass Batts": {"r_value": 3.2, "cost_per_sqft": 0.50, "savings_pct": 15},
    "Blown-in Cellulose": {"r_value": 3.7, "cost_per_sqft": 0.80, "savings_pct": 20},
    "Spray Foam (Open Cell)": {"r_value": 3.6, "cost_per_sqft": 1.25, "savings_pct": 22},
    "Spray Foam (Closed Cell)": {"r_value": 6.5, "cost_per_sqft": 1.75, "savings_pct": 28},
    "Mineral Wool": {"r_value": 3.3, "cost_per_sqft": 0.90, "savings_pct": 18},
    "Rigid Foam Board": {"r_value": 5.0, "cost_per_sqft": 1.10, "savings_pct": 24},
}

SOLAR_PANEL_DATA = {
    "panel_wattage": 400,
    "panel_area_sqft": 20,
    "efficiency": 0.20,
    "degradation_rate": 0.005,
    "cost_per_watt": 2.80,
    "federal_tax_credit": 0.30,
    "avg_sun_hours": 5.0,
    "panel_life_years": 25,
}

ELECTRICITY_RATE = 0.14  # $/kWh average US

# ---------------------------------------------------------------------------
# Calculation functions
# ---------------------------------------------------------------------------

def _calc_appliance_energy(name: str, custom_hours: float | None = None) -> dict:
    """Calculate energy for an appliance."""
    info = APPLIANCE_DATA.get(name, {"watts": 100, "hours_day": 1, "icon": "⚡", "category": "Other"})
    hours = custom_hours if custom_hours is not None else info["hours_day"]
    kwh_day = (info["watts"] * hours) / 1000
    kwh_month = kwh_day * 30
    kwh_year = kwh_day * 365
    cost_day = kwh_day * ELECTRICITY_RATE
    cost_month = kwh_day * 30 * ELECTRICITY_RATE
    cost_year = kwh_day * 365 * ELECTRICITY_RATE
    return {
        "name": name,
        "watts": info["watts"],
        "hours_day": hours,
        "icon": info["icon"],
        "category": info["category"],
        "kwh_day": round(kwh_day, 2),
        "kwh_month": round(kwh_month, 1),
        "kwh_year": round(kwh_year, 0),
        "cost_day": round(cost_day, 2),
        "cost_month": round(cost_month, 1),
        "cost_year": round(cost_year, 0),
    }


def _calc_insulation_savings(wall_area_sqft: float, current_r: float, new_type: str) -> dict:
    """Calculate insulation upgrade savings."""
    ins = INSULATION_TYPES.get(new_type, {"r_value": 3, "cost_per_sqft": 0.70, "savings_pct": 15})
    improvement = ins["r_value"] - current_r
    cost = wall_area_sqft * ins["cost_per_sqft"]
    return {
        "type": new_type,
        "r_value": ins["r_value"],
        "improvement": round(max(improvement, 0), 1),
        "cost": round(cost, 0),
        "annual_savings": round(cost * 0.08, 0),
        "payback_years": round(cost / max(cost * 0.08, 1), 1),
        "savings_pct": ins["savings_pct"],
    }


def _calc_solar_sizing(annual_kwh: float, roof_sqft: float) -> dict:
    """Calculate solar panel system sizing and ROI."""
    d = SOLAR_PANEL_DATA
    panels_needed = math.ceil(annual_kwh / (d["panel_wattage"] / 1000 * d["avg_sun_hours"] * 365))
    max_panels = math.floor(roof_sqft / d["panel_area_sqft"])
    actual_panels = min(panels_needed, max_panels)
    system_size_kw = actual_panels * d["panel_wattage"] / 1000
    annual_production = system_size_kw * d["avg_sun_hours"] * 365 * 0.80
    annual_savings = annual_production * ELECTRICITY_RATE
    total_cost = system_size_kw * 1000 * d["cost_per_watt"]
    tax_credit = total_cost * d["federal_tax_credit"]
    net_cost = total_cost - tax_credit
    payback_years = net_cost / max(annual_savings, 1)
    lifetime_savings = annual_savings * d["panel_life_years"] - net_cost

    yearly = []
    production = annual_production
    cumulative_savings = -net_cost
    for yr in range(1, d["panel_life_years"] + 1):
        savings = production * ELECTRICITY_RATE
        cumulative_savings += savings
        yearly.append({
            "year": yr,
            "production_kwh": round(production, 0),
            "savings": round(savings, 0),
            "cumulative": round(cumulative_savings, 0),
        })
        production *= (1 - d["degradation_rate"])

    return {
        "panels_needed": panels_needed,
        "max_panels": max_panels,
        "actual_panels": actual_panels,
        "system_size_kw": round(system_size_kw, 2),
        "annual_production": round(annual_production, 0),
        "annual_savings": round(annual_savings, 0),
        "total_cost": round(total_cost, 0),
        "tax_credit": round(tax_credit, 0),
        "net_cost": round(net_cost, 0),
        "payback_years": round(payback_years, 1),
        "lifetime_savings": round(lifetime_savings, 0),
        "co2_offset_annual": round(annual_production * 0.42, 0),
        "yearly": yearly,
    }


def _calc_energy_score(total_kwh_year: float, sqft: float) -> dict:
    """Calculate home energy score (1-100)."""
    intensity = total_kwh_year / max(sqft, 1)
    if intensity <= 10:
        score, grade, label = 95, "A+", "Excellent"
    elif intensity <= 15:
        score, grade, label = 80, "A", "Very Good"
    elif intensity <= 20:
        score, grade, label = 65, "B", "Good"
    elif intensity <= 25:
        score, grade, label = 50, "C", "Average"
    elif intensity <= 35:
        score, grade, label = 35, "D", "Below Average"
    else:
        score, grade, label = 20, "F", "Poor"
    return {"score": score, "grade": grade, "label": label, "intensity": round(intensity, 1)}


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _generate_mock_audit() -> dict:
    """Generate a mock home energy audit."""
    return {
        "home_sqft": 1800, "stories": 2, "year_built": 2005,
        "insulation": "Fiberglass Batts", "current_r_value": 13,
        "climate_zone": "4A (Mixed-Humid)",
        "appliances": {
            "HVAC (Heating/Cooling)": 8, "Water Heater": 3, "Refrigerator": 24,
            "Washing Machine": 1, "Dryer": 1, "Dishwasher": 1, "Oven/Stove": 1.5,
            "Lighting (LED)": 6, "Television": 5, "Computer/Laptop": 8, "Ceiling Fan": 10,
        },
        "monthly_bill": 185, "roof_sqft": 900,
    }


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _render_energy_ring(score: int, grade: str, label: str, size: int = 140):
    """Render energy score ring."""
    color = "#28a745" if score >= 80 else "#ffc107" if score >= 50 else "#dc3545"
    angle = (score / 100) * 360
    rad = math.pi * angle / 180
    r = size * 0.38
    cx, cy = size / 2, size / 2
    x_end = cx + r * math.sin(rad)
    y_end = cy - r * math.cos(rad)
    large_arc = 1 if angle > 180 else 0
    return f'''<svg width="{size}" height="{size + 25}" viewBox="0 0 {size} {size + 25}" xmlns="http://www.w3.org/2000/svg">
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#2a2a3e" stroke-width="10"/>
  <path d="M {cx} {cy - r} A {r} {r} 0 {large_arc} 1 {x_end:.1f} {y_end:.1f}"
        fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round"/>
  <text x="{cx}" y="{cy + 3}" text-anchor="middle" font-size="24" font-weight="bold" fill="{color}">{grade}</text>
  <text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="11" fill="#aaa">{score}/100</text>
  <text x="{cx}" y="{size + 18}" text-anchor="middle" font-size="10" fill="#888">{label}</text>
</svg>'''


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_overview(audit: dict):
    """Render audit overview with energy score."""
    st.subheader("📊 Energy Audit Overview")
    total_kwh_day = sum(_calc_appliance_energy(n, h)["kwh_day"] for n, h in audit["appliances"].items())
    total_kwh_year = total_kwh_day * 365
    total_cost_year = total_kwh_year * ELECTRICITY_RATE
    score = _calc_energy_score(total_kwh_year, audit["home_sqft"])

    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        st.markdown(_render_energy_ring(score["score"], score["grade"], score["label"]), unsafe_allow_html=True)
    with c2:
        st.metric("Daily Usage", f"{total_kwh_day:.1f} kWh")
        st.metric("Annual Usage", f"{total_kwh_year:,.0f} kWh")
    with c3:
        st.metric("Monthly Cost", f"${total_cost_year / 12:,.0f}")
        st.metric("Annual Cost", f"${total_cost_year:,.0f}")
    with c4:
        st.metric("Energy Intensity", f"{score['intensity']} kWh/sqft/yr")
        st.metric("Home Size", f"{audit['home_sqft']:,} sqft")

    st.markdown(
        f"Your home scores **{score['grade']} ({score['score']}/100)** with an energy intensity "
        f"of **{score['intensity']} kWh/sqft/year**. Annual consumption is **{total_kwh_year:,.0f} kWh** "
        f"costing approximately **${total_cost_year:,.0f}** per year."
    )


def _render_appliance_breakdown(audit: dict):
    """Render appliance-by-appliance energy breakdown."""
    st.subheader("⚡ Appliance Breakdown")
    calculations = sorted([_calc_appliance_energy(n, h) for n, h in audit["appliances"].items()],
                          key=lambda x: x["kwh_year"], reverse=True)
    max_kwh = calculations[0]["kwh_year"] if calculations else 1

    for calc in calculations:
        pct = (calc["kwh_year"] / max_kwh * 100) if max_kwh else 0
        color = "#dc3545" if pct > 70 else "#fd7e14" if pct > 40 else "#ffc107" if pct > 20 else "#28a745"
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:5px 0">'
            f'<span style="width:200px;font-size:0.88em">{calc["icon"]} {calc["name"]}</span>'
            f'<div style="width:45%;background:#1e1e2e;border-radius:4px;height:18px">'
            f'<div style="width:{pct:.0f}%;background:{color};border-radius:4px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{calc["kwh_year"]:,.0f} kWh/yr | ${calc["cost_year"]:,.0f}/yr</span></div>',
            unsafe_allow_html=True,
        )

    rows = [{"Appliance": f"{c['icon']} {c['name']}", "Watts": c["watts"], "Hours/Day": c["hours_day"],
             "kWh/Day": c["kwh_day"], "kWh/Year": f"{c['kwh_year']:,.0f}", "Cost/Year": f"${c['cost_year']:,.0f}"} for c in calculations]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    cat_totals = {}
    for calc in calculations:
        cat_totals[calc["category"]] = cat_totals.get(calc["category"], 0) + calc["kwh_year"]
    total = sum(cat_totals.values()) or 1
    cat_colors = {"HVAC": "#dc3545", "Water": "#4a90d9", "Appliance": "#fd7e14", "Lighting": "#ffc107", "Electronics": "#6f42c1"}
    st.markdown("**By Category:**")
    for cat, kwh in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
        pct = kwh / total * 100
        color = cat_colors.get(cat, "#666")
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:3px 0">'
            f'<span style="width:100px;font-size:0.85em;color:{color}">{cat}</span>'
            f'<div style="width:40%;background:#1e1e2e;border-radius:3px;height:14px">'
            f'<div style="width:{pct:.0f}%;background:{color};border-radius:3px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{kwh:,.0f} kWh ({pct:.0f}%)</span></div>',
            unsafe_allow_html=True,
        )


def _render_insulation_analysis(audit: dict):
    """Render insulation upgrade recommendations."""
    st.subheader("🧱 Insulation Analysis")
    c1, c2 = st.columns(2)
    with c1:
        current_r = st.number_input("Current R-Value", 0, 60, audit["current_r_value"])
    with c2:
        wall_area = st.number_input("Total Wall Area (sqft)", 100, 10000, int(audit["home_sqft"] * 2.5))

    st.markdown(f"**Current Insulation:** {audit['insulation']} (R-{current_r})")
    results = sorted(
        [_calc_insulation_savings(wall_area, current_r, t) for t, d in INSULATION_TYPES.items() if d["r_value"] > current_r],
        key=lambda x: x["savings_pct"], reverse=True,
    )

    for r in results:
        color = "#28a745" if r["savings_pct"] >= 20 else "#ffc107" if r["savings_pct"] >= 15 else "#6c757d"
        with st.expander(f"**{r['type']}** — R-{r['r_value']} | Save {r['savings_pct']}% | Cost: ${r['cost']:,.0f}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("R-Value", f"{r['r_value']}")
            c2.metric("Improvement", f"+{r['improvement']}")
            c3.metric("Installation Cost", f"${r['cost']:,.0f}")
            c4.metric("Annual Savings", f"${r['annual_savings']:,.0f}")
            st.markdown(f"**Payback Period:** {r['payback_years']:.1f} years")


def _render_solar_analysis(audit: dict):
    """Render solar panel system analysis."""
    st.subheader("☀️ Solar Panel Analysis")
    total_kwh_day = sum(_calc_appliance_energy(n, h)["kwh_day"] for n, h in audit["appliances"].items())
    annual_kwh = total_kwh_day * 365
    result = _calc_solar_sizing(annual_kwh, audit["roof_sqft"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("System Size", f"{result['system_size_kw']} kW")
    c2.metric("Panels", f"{result['actual_panels']}")
    c3.metric("Annual Production", f"{result['annual_production']:,.0f} kWh")
    c4.metric("Annual Savings", f"${result['annual_savings']:,.0f}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Cost", f"${result['total_cost']:,.0f}")
    c2.metric("Tax Credit (30%)", f"-${result['tax_credit']:,.0f}")
    c3.metric("Net Cost", f"${result['net_cost']:,.0f}")
    c4.metric("Payback", f"{result['payback_years']} years")

    if result["actual_panels"] < result["panels_needed"]:
        st.warning(f"⚠️ Roof fits **{result['max_panels']} panels** — need {result['panels_needed']} for full offset.")

    st.markdown(
        f"**{result['system_size_kw']} kW** system with **{result['actual_panels']} panels** produces "
        f"**{result['annual_production']:,.0f} kWh/yr**. Net cost **${result['net_cost']:,.0f}**, payback "
        f"**{result['payback_years']} years**, lifetime savings **${result['lifetime_savings']:,.0f}**. "
        f"Offsets **{result['co2_offset_annual']:,.0f} kg CO₂/yr**."
    )

    yearly = result["yearly"]
    max_cum = max(y["cumulative"] for y in yearly) if yearly else 1
    min_cum = min(y["cumulative"] for y in yearly) if yearly else -1
    rng = max_cum - min_cum if max_cum != min_cum else 1
    chart_html = '<div style="display:flex;align-items:flex-end;gap:2px;height:200px;padding:10px 0">'
    for y in yearly:
        h = ((y["cumulative"] - min_cum) / rng * 180) if rng else 90
        color = "#28a745" if y["cumulative"] > 0 else "#dc3545"
        chart_html += (
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center">'
            f'<div style="width:100%;height:{h:.0f}px;background:{color};border-radius:2px 2px 0 0;min-height:1px"></div>'
            f'{"<span style=font-size:0.55em;color:#666>" + str(y["year"]) + "</span>" if y["year"] % 5 == 0 else ""}'
            f'</div>'
        )
    chart_html += '</div>'
    st.markdown(chart_html, unsafe_allow_html=True)


def _render_savings_calculator(audit: dict):
    """Render energy savings tips calculator."""
    st.subheader("💰 Savings Calculator")
    tips = [
        {"name": "Switch to LED lighting", "saving_pct": 75, "description": "LED bulbs use 75% less energy than incandescent"},
        {"name": "Install smart thermostat", "saving_pct": 15, "description": "Smart thermostats reduce heating/cooling by 15%"},
        {"name": "Seal air leaks", "saving_pct": 10, "description": "Weatherstripping and caulking reduce drafts"},
        {"name": "Add attic insulation", "saving_pct": 20, "description": "Proper attic insulation reduces heat loss by 20%"},
        {"name": "Upgrade to ENERGY STAR appliances", "saving_pct": 25, "description": "ENERGY STAR certified appliances use 25% less energy"},
        {"name": "Install low-flow showerheads", "saving_pct": 30, "description": "Reduces hot water usage by 30%"},
        {"name": "Use cold water for laundry", "saving_pct": 5, "description": "90% of washing machine energy goes to heating water"},
        {"name": "Install window film", "saving_pct": 8, "description": "Reduces heat gain in summer and heat loss in winter"},
    ]
    total_kwh_year = sum(_calc_appliance_energy(n, h)["kwh_year"] for n, h in audit["appliances"].items())
    for tip in tips:
        saved_kwh = total_kwh_year * (tip["saving_pct"] / 100) * 0.1
        saved_cost = saved_kwh * ELECTRICITY_RATE
        with st.expander(f"💡 **{tip['name']}** — Save ~${saved_cost:,.0f}/yr", expanded=False):
            st.markdown(tip["description"])
            st.markdown(f"**Potential Annual Savings:** {saved_kwh:,.0f} kWh = ${saved_cost:,.0f}")


def _render_energy_tips():
    """Render general energy saving tips."""
    st.subheader("🔋 Quick Energy Tips")
    for tip in [
        "🌡️ Set thermostat to 68°F in winter, 78°F in summer — saves 3% per degree",
        "🔌 Unplug 'vampire' electronics — standby power costs $100+/year",
        "💡 Replace all bulbs with LED — saves $225/year on average",
        "🧊 Keep fridge at 37°F and freezer at 0°F for optimal efficiency",
        "🍳 Use microwave or toaster oven for small meals — 75% less energy than oven",
        "👕 Wash clothes in cold water — saves $60/year",
        "🌬️ Clean HVAC filters monthly — improves efficiency by 15%",
        "📐 Use ceiling fans before AC — uses 1% of the energy",
    ]:
        st.markdown(f"- {tip}")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def render_home_energy_audit():
    """Render the Home Energy Audit Simulator page."""
    st.title("🏠 Home Energy Audit Simulator")
    st.markdown("Analyze your home's energy consumption, explore insulation and solar options, and calculate potential savings.")

    audit = _generate_mock_audit()

    with st.sidebar:
        st.header("⚙️ Home Settings")
        audit["home_sqft"] = st.number_input("Home Size (sqft)", 500, 5000, audit["home_sqft"])
        audit["current_r_value"] = st.slider("Current Insulation R-Value", 0, 60, audit["current_r_value"])
        audit["roof_sqft"] = st.number_input("Roof Area (sqft)", 200, 5000, audit["roof_sqft"])
        st.markdown("---")
        show_overview = st.checkbox("Energy Score & Overview", True)
        show_appliances = st.checkbox("Appliance Breakdown", True)
        show_insulation = st.checkbox("Insulation Analysis", True)
        show_solar = st.checkbox("Solar Panel Analysis", True)
        show_savings = st.checkbox("Savings Calculator", True)
        show_tips = st.checkbox("Quick Tips", True)

    if show_overview:
        _render_overview(audit)
    if show_appliances:
        st.markdown("---")
        _render_appliance_breakdown(audit)
    if show_insulation:
        st.markdown("---")
        _render_insulation_analysis(audit)
    if show_solar:
        st.markdown("---")
        _render_solar_analysis(audit)
    if show_savings:
        st.markdown("---")
        _render_savings_calculator(audit)
    if show_tips:
        st.markdown("---")
        _render_energy_tips()

    st.markdown("---")
    st.caption(f"Home Energy Audit Simulator | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")


if __name__ == "__main__" or True:
    render_home_energy_audit()
