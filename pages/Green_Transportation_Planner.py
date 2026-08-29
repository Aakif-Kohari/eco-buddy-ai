"""
pages/Green_Transportation_Planner.py
--------------------------------------
Streamlit page: Green Transportation Planner.

Track commute carbon emissions, compare transportation modes, optimize
routes for minimal environmental impact, and visualize emission savings
over time.
"""

import math
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Green Transportation Planner",
    page_icon="🚲",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Emission factors (kg CO2 per km)
# ---------------------------------------------------------------------------

EMISSION_FACTORS = {
    "Car (Gasoline)": 0.21,
    "Car (Diesel)": 0.17,
    "Car (Hybrid)": 0.12,
    "Car (Electric)": 0.05,
    "Motorcycle": 0.10,
    "Bus": 0.089,
    "Metro/Subway": 0.041,
    "Train": 0.035,
    "Tram": 0.030,
    "Bicycle": 0.0,
    "E-Bike": 0.005,
    "Walking": 0.0,
    "Scooter (Electric)": 0.015,
    "Carpool (2 people)": 0.105,
    "Carpool (3+ people)": 0.07,
}

MODE_ICONS = {
    "Car (Gasoline)": "🚗", "Car (Diesel)": "🚗", "Car (Hybrid)": "🚗",
    "Car (Electric)": "⚡", "Motorcycle": "🏍️", "Bus": "🚌",
    "Metro/Subway": "🚇", "Train": "🚆", "Tram": "🚊",
    "Bicycle": "🚲", "E-Bike": "🔋", "Walking": "🚶",
    "Scooter (Electric)": "🛴", "Carpool (2 people)": "👥", "Carpool (3+ people)": "👥",
}

# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _generate_mock_commutes() -> list[dict[str, Any]]:
    """Generate mock commute history data."""
    import random
    random.seed(33)

    routes = [
        {"name": "Home → Office", "distance_km": 12.5, "from": "Residential Area", "to": "Tech Park"},
        {"name": "Home → University", "distance_km": 8.3, "from": "Residential Area", "to": "University Campus"},
        {"name": "Office → Client Site", "distance_km": 15.2, "from": "Tech Park", "to": "Business District"},
        {"name": "Home → Gym", "distance_km": 3.1, "from": "Residential Area", "to": "Fitness Center"},
        {"name": "Home → Market", "distance_km": 2.8, "from": "Residential Area", "to": "Shopping Mall"},
    ]
    modes = list(EMISSION_FACTORS.keys())
    mode_weights = [15, 5, 3, 2, 8, 10, 12, 5, 3, 4, 3, 2, 1, 8, 3]

    commutes = []
    for i in range(60):
        route = random.choice(routes)
        mode = random.choices(modes, weights=mode_weights, k=1)[0]
        day = datetime.now() - timedelta(days=random.randint(0, 90))
        distance = route["distance_km"] * random.uniform(0.85, 1.15)
        emissions = distance * EMISSION_FACTORS[mode]
        time_min = distance / random.uniform(15, 60) * 60
        cost = distance * random.uniform(0.1, 0.8) if mode not in ("Walking", "Bicycle") else 0

        commutes.append({
            "id": f"C-{1000 + i}",
            "date": day.strftime("%Y-%m-%d"),
            "route": route["name"],
            "from": route["from"],
            "to": route["to"],
            "mode": mode,
            "distance_km": round(distance, 1),
            "emissions_kg": round(emissions, 3),
            "time_minutes": round(time_min, 0),
            "cost_usd": round(cost, 2),
            "day_of_week": day.strftime("%A"),
        })
    return commutes


def _generate_mock_routes() -> list[dict[str, Any]]:
    """Generate alternative route comparisons."""
    return [
        {
            "name": "Commute to Work (12.5 km)",
            "alternatives": [
                {"mode": "Car (Gasoline)", "distance": 12.5, "time_min": 25, "cost": 2.50, "emissions": 2.625, "comfort": "High", "reliability": "95%"},
                {"mode": "Bus", "distance": 13.1, "time_min": 40, "cost": 1.50, "emissions": 1.166, "comfort": "Medium", "reliability": "88%"},
                {"mode": "Metro/Subway", "distance": 11.8, "time_min": 22, "cost": 2.00, "emissions": 0.484, "comfort": "Medium", "reliability": "96%"},
                {"mode": "Bicycle", "distance": 10.2, "time_min": 35, "cost": 0.00, "emissions": 0.0, "comfort": "Low", "reliability": "90%"},
                {"mode": "E-Bike", "distance": 10.5, "time_min": 28, "cost": 0.30, "emissions": 0.053, "comfort": "Medium", "reliability": "92%"},
                {"mode": "Carpool (3+ people)", "distance": 12.5, "time_min": 30, "cost": 0.83, "emissions": 0.875, "comfort": "High", "reliability": "85%"},
            ],
        },
        {
            "name": "Commute to University (8.3 km)",
            "alternatives": [
                {"mode": "Car (Gasoline)", "distance": 8.3, "time_min": 18, "cost": 1.66, "emissions": 1.743, "comfort": "High", "reliability": "95%"},
                {"mode": "Bus", "distance": 9.0, "time_min": 30, "cost": 1.20, "emissions": 0.801, "comfort": "Medium", "reliability": "87%"},
                {"mode": "Metro/Subway", "distance": 7.8, "time_min": 15, "cost": 1.50, "emissions": 0.320, "comfort": "Medium", "reliability": "96%"},
                {"mode": "Bicycle", "distance": 7.1, "time_min": 25, "cost": 0.00, "emissions": 0.0, "comfort": "Low", "reliability": "92%"},
                {"mode": "Walking", "distance": 6.5, "time_min": 78, "cost": 0.00, "emissions": 0.0, "comfort": "Low", "reliability": "100%"},
            ],
        },
    ]


def _generate_mock_goals() -> list[dict[str, Any]]:
    """Generate weekly emission reduction goals."""
    return [
        {"week": "Week 1 (Aug 4)", "target": 25.0, "actual": 28.3, "status": "missed"},
        {"week": "Week 2 (Aug 11)", "target": 23.0, "actual": 22.1, "status": "met"},
        {"week": "Week 3 (Aug 18)", "target": 20.0, "actual": 19.8, "status": "met"},
        {"week": "Week 4 (Aug 25)", "target": 18.0, "actual": 17.2, "status": "met"},
        {"week": "Week 5 (Sep 1)", "target": 15.0, "actual": None, "status": "upcoming"},
    ]


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def _render_emission_bar(mode: str, emissions: float, max_emissions: float, savings: float = 0):
    """Render a single transportation mode emission comparison bar."""
    icon = MODE_ICONS.get(mode, "🚗")
    pct = (emissions / max_emissions * 100) if max_emissions else 0
    color = "#dc3545" if emissions > 2 else "#fd7e14" if emissions > 1 else "#ffc107" if emissions > 0.5 else "#28a745"

    savings_html = ""
    if savings > 0:
        savings_html = f' <span style="color:#28a745;font-size:0.82em">(-{savings:.0f}% vs car)</span>'

    return (
        f'<div style="display:flex;align-items:center;margin:6px 0">'
        f'<span style="width:160px;font-size:0.88em">{icon} {mode}</span>'
        f'<div style="width:50%;background:#1e1e2e;border-radius:4px;height:20px">'
        f'<div style="width:{pct:.0f}%;background:{color};border-radius:4px;height:100%"></div></div>'
        f'<span style="margin-left:8px;font-size:0.85em;font-weight:600;color:{color}">{emissions:.3f} kg CO₂</span>'
        f'{savings_html}</div>'
    )


def _render_weekly_chart(goals: list[dict]):
    """Render weekly emission goal tracking chart."""
    valid = [g for g in goals if g["actual"] is not None]
    if not valid:
        st.info("No weekly data yet.")
        return

    max_val = max(max(g["target"], g["actual"]) for g in valid) or 1

    chart_html = '<div style="display:flex;align-items:flex-end;gap:12px;height:200px;padding:10px 0">'
    for g in valid:
        target_h = (g["target"] / max_val * 180)
        actual_h = (g["actual"] / max_val * 180)
        color = "#28a745" if g["actual"] <= g["target"] else "#dc3545"
        chart_html += (
            f'<div style="flex:1;display:flex;flex-direction:column;align-items:center">'
            f'<span style="font-size:0.72em;color:{color};font-weight:600">{g["actual"]:.1f}</span>'
            f'<div style="display:flex;align-items:flex-end;gap:4px;height:180px">'
            f'<div style="width:20px;height:{target_h:.0f}px;background:#4a90d9;border-radius:3px 3px 0 0;opacity:0.5" title="Target: {g["target"]:.1f}"></div>'
            f'<div style="width:20px;height:{actual_h:.0f}px;background:{color};border-radius:3px 3px 0 0" title="Actual: {g["actual"]:.1f}"></div>'
            f'</div>'
            f'<span style="font-size:0.68em;color:#888;margin-top:4px;text-align:center">{g["week"][:12]}</span>'
            f'</div>'
        )
    chart_html += '</div>'
    st.markdown(chart_html, unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.82em;color:#888">'
        '<span style="color:#4a90d9">■</span> Target &nbsp;&nbsp; '
        '<span style="color:#28a745">■</span> Met Goal &nbsp;&nbsp; '
        '<span style="color:#dc3545">■</span> Exceeded'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_overview(commutes: list[dict]):
    """Render commute overview KPIs."""
    st.subheader("📊 Commute Overview")
    total = len(commutes)
    total_distance = sum(c["distance_km"] for c in commutes)
    total_emissions = sum(c["emissions_kg"] for c in commutes)
    total_cost = sum(c["cost_usd"] for c in commutes)
    avg_emissions = total_emissions / total if total else 0

    # Best and worst commutes
    green_comms = sum(1 for c in commutes if c["emissions_kg"] == 0)
    high_comms = sum(1 for c in commutes if c["emissions_kg"] > 2)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Commutes", total)
    c2.metric("Total Distance", f"{total_distance:.0f} km")
    c3.metric("Total CO₂", f"{total_emissions:.1f} kg")
    c4.metric("Avg per Trip", f"{avg_emissions:.2f} kg")
    c5.metric("💰 Total Cost", f"${total_cost:.0f}")
    c6.metric("🌿 Zero-Emission", green_comms)

    st.markdown(
        f"Over **{total} commutes** totaling **{total_distance:.0f} km**, you've produced "
        f"**{total_emissions:.1f} kg CO₂**. **{green_comms}** commutes were zero-emission "
        f"(bicycle/walking), while **{high_comms}** produced over 2 kg CO₂ each."
    )
    if high_comms > 0:
        st.warning(f"⚠️ **{high_comms} high-emission commutes** — consider switching to greener alternatives.")


def _render_mode_comparison(commutes: list[dict]):
    """Render transportation mode comparison."""
    st.subheader("🚗 Mode Comparison")

    mode_stats: dict[str, dict] = {}
    for c in commutes:
        mode = c["mode"]
        if mode not in mode_stats:
            mode_stats[mode] = {"count": 0, "total_distance": 0, "total_emissions": 0, "total_cost": 0, "total_time": 0}
        mode_stats[mode]["count"] += 1
        mode_stats[mode]["total_distance"] += c["distance_km"]
        mode_stats[mode]["total_emissions"] += c["emissions_kg"]
        mode_stats[mode]["total_cost"] += c["cost_usd"]
        mode_stats[mode]["total_time"] += c["time_minutes"]

    # Emission comparison bars
    st.markdown("**Emissions by Mode (total kg CO₂):**")
    car_emissions = mode_stats.get("Car (Gasoline)", {}).get("total_emissions", 1)
    max_emissions = max((s["total_emissions"] for s in mode_stats.values()), default=1) or 1

    for mode, stats in sorted(mode_stats.items(), key=lambda x: x[1]["total_emissions"], reverse=True):
        savings = ((car_emissions - stats["total_emissions"]) / car_emissions * 100) if car_emissions and stats["total_emissions"] < car_emissions else 0
        st.markdown(_render_emission_bar(mode, stats["total_emissions"], max_emissions, savings), unsafe_allow_html=True)

    # Detailed stats table
    st.markdown("**Mode Statistics:**")
    rows = []
    for mode, stats in sorted(mode_stats.items(), key=lambda x: x[1]["total_emissions"], reverse=True):
        avg_dist = stats["total_distance"] / stats["count"]
        avg_em = stats["total_emissions"] / stats["count"]
        avg_time = stats["total_time"] / stats["count"]
        rows.append({
            "Mode": f"{MODE_ICONS.get(mode, '🚗')} {mode}",
            "Trips": stats["count"],
            "Total km": f"{stats['total_distance']:.0f}",
            "Avg Distance": f"{avg_dist:.1f}",
            "Total CO₂": f"{stats['total_emissions']:.2f}",
            "Avg CO₂/Trip": f"{avg_em:.3f}",
            "Avg Time": f"{avg_time:.0f} min",
            "Total Cost": f"${stats['total_cost']:.0f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_route_comparison(routes: list[dict]):
    """Render route-by-route alternative comparison."""
    st.subheader("🗺️ Route Alternatives")

    for route in routes:
        with st.expander(f"📍 **{route['name']}**", expanded=True):
            alts = route["alternatives"]
            max_em = max(a["emissions"] for a in alts) or 1
            car_em = next((a["emissions"] for a in alts if "Gasoline" in a["mode"]), max_em)

            for alt in alts:
                savings = ((car_em - alt["emissions"]) / car_em * 100) if car_em and alt["emissions"] < car_em else 0
                icon = MODE_ICONS.get(alt["mode"], "🚗")
                color = "#28a745" if alt["emissions"] == 0 else "#ffc107" if alt["emissions"] < 0.5 else "#fd7e14" if alt["emissions"] < 1.5 else "#dc3545"
                pct = (alt["emissions"] / max_em * 100) if max_em else 0

                c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                with c1:
                    st.markdown(
                        f'{icon} **{alt["mode"]}<br/>'
                        f'<div style="width:{pct}%;background:{color};height:8px;border-radius:4px;margin-top:4px"></div>'
                        f'<span style="font-size:0.78em;color:{color}">{alt["emissions"]:.3f} kg CO₂</span></div>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(f"⏱️ {alt['time_min']:.0f} min<br/>${alt['cost']:.2f}")
                with c3:
                    st.markdown(f"📏 {alt['distance']:.1f} km")
                with c4:
                    if savings > 0:
                        st.markdown(f"<span style='color:#28a745;font-weight:600'>🌿 -{savings:.0f}%</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("Baseline")


def _render_emission_trend(commutes: list[dict]):
    """Render emission trend over time."""
    st.subheader("📈 Emission Trend")

    # Group by date
    daily = {}
    for c in commutes:
        day = c["date"]
        daily.setdefault(day, {"emissions": 0, "distance": 0, "count": 0})
        daily[day]["emissions"] += c["emissions_kg"]
        daily[day]["distance"] += c["distance_km"]
        daily[day]["count"] += 1

    sorted_days = sorted(daily.keys())
    if not sorted_days:
        st.info("No data available.")
        return

    labels = [d[5:] for d in sorted_days]
    values = [daily[d]["emissions"] for d in sorted_days]
    max_val = max(values) if values else 1

    # SVG sparkline
    width, height = 700, 120
    points = []
    for i, v in enumerate(values):
        x = (i / max(len(values) - 1, 1)) * width
        y = height - (v / max_val * (height - 20)) if max_val else height / 2
        points.append(f"{x:.1f},{y:.1f}")

    svg = f'''<svg width="100%" viewBox="0 0 {width} {height + 30}" xmlns="http://www.w3.org/2000/svg" style="background:#0d1117;border-radius:8px">
  <polyline points="{" ".join(points)}" fill="none" stroke="#4a90d9" stroke-width="2" stroke-linecap="round"/>
  {"".join(f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3" fill="#4a90d9"/>' for p in points[:1])}
  {"".join(f'<text x="{(i / max(len(labels)-1,1)) * width}" y="{height + 18}" fill="#666" font-size="8" text-anchor="middle">{l}</text>' for i, l in enumerate(labels) if i % max(1, len(labels)//8) == 0)}
</svg>'''
    st.markdown(svg, unsafe_allow_html=True)

    # Weekly averages
    st.markdown("**Weekly Emission Averages:**")
    weekly = {}
    for c in commutes:
        day = datetime.strptime(c["date"], "%Y-%m-%d")
        week_key = day.strftime("%Y-W%U")
        weekly.setdefault(week_key, {"emissions": 0, "count": 0})
        weekly[week_key]["emissions"] += c["emissions_kg"]
        weekly[week_key]["count"] += 1

    for wk in sorted(weekly.keys())[-6:]:
        avg = weekly[wk]["emissions"] / weekly[wk]["count"] if weekly[wk]["count"] else 0
        total = weekly[wk]["emissions"]
        color = "#28a745" if avg < 1 else "#ffc107" if avg < 2 else "#dc3545"
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:3px 0">'
            f'<span style="width:100px;font-size:0.85em">{wk}</span>'
            f'<div style="width:40%;background:#1e1e2e;border-radius:3px;height:14px">'
            f'<div style="width:{min(avg / 3 * 100, 100):.0f}%;background:{color};border-radius:3px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{total:.1f} kg total, {avg:.2f} kg/trip</span></div>',
            unsafe_allow_html=True,
        )


def _render_commute_log(commutes: list[dict]):
    """Render detailed commute log."""
    st.subheader("📋 Commute Log")

    df = pd.DataFrame(commutes)
    c1, c2, c3 = st.columns(3)
    with c1:
        mode_filter = st.multiselect("Filter by Mode", list(EMISSION_FACTORS.keys()), key="log_mode")
    with c2:
        route_filter = st.multiselect("Filter by Route", list(set(c["route"] for c in commutes)), key="log_route")
    with c3:
        sort_by = st.selectbox("Sort by", ["date", "emissions_kg", "distance_km", "cost_usd"], key="log_sort")

    filtered = commutes
    if mode_filter:
        filtered = [c for c in filtered if c["mode"] in mode_filter]
    if route_filter:
        filtered = [c for c in filtered if c["route"] in route_filter]
    filtered = sorted(filtered, key=lambda x: x[sort_by], reverse=(sort_by != "date"))

    rows = []
    for c in filtered:
        icon = MODE_ICONS.get(c["mode"], "🚗")
        rows.append({
            "Date": c["date"],
            "Route": c["route"],
            "Mode": f"{icon} {c['mode']}",
            "Distance": f"{c['distance_km']:.1f} km",
            "CO₂": f"{c['emissions_kg']:.3f} kg",
            "Time": f"{c['time_minutes']:.0f} min",
            "Cost": f"${c['cost_usd']:.2f}",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Export
    csv = pd.DataFrame(filtered).to_csv(index=False)
    st.download_button("📥 Export Log (CSV)", csv, file_name="commute_log.csv", mime="text/csv")


def _render_green_savings(commutes: list[dict]):
    """Render green savings and impact analysis."""
    st.subheader("🌿 Green Savings Impact")

    # Calculate savings vs all-car baseline
    total_emissions = sum(c["emissions_kg"] for c in commutes)
    baseline_emissions = sum(c["distance_km"] * EMISSION_FACTORS["Car (Gasoline)"] for c in commutes)
    savings_kg = baseline_emissions - total_emissions
    savings_pct = (savings_kg / baseline_emissions * 100) if baseline_emissions else 0

    # Equivalent visualizations
    trees_equivalent = savings_kg / 21  # ~21 kg CO2 per tree per year
    driving_equivalent = savings_kg / 0.21  # km of driving avoided
    phone_charges = savings_kg / 0.008  # phone charges equivalent

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌿 CO₂ Saved", f"{savings_kg:.1f} kg", delta=f"-{savings_pct:.0f}% vs baseline")
    c2.metric("🌳 Tree Equivalent", f"{trees_equivalent:.1f}", help="Trees needed to absorb this CO₂ in a year")
    c3.metric("🚗 Driving Avoided", f"{driving_equivalent:.0f} km")
    c4.metric("📱 Phone Charges", f"{phone_charges:.0f}")

    st.markdown(
        f"By choosing greener transportation options, you've saved **{savings_kg:.1f} kg CO₂** "
        f"compared to driving a gasoline car for every trip — equivalent to **{trees_equivalent:.1f} trees** "
        f"growing for a full year, or avoiding **{driving_equivalent:.0f} km** of driving."
    )

    # Mode shift recommendations
    st.markdown("---")
    st.markdown("**🎯 Recommended Mode Shifts:**")
    car_commutes = [c for c in commutes if "Car" in c["mode"] and c["emissions_kg"] > 1]
    for c in car_commutes[:8]:
        best_mode = "Metro/Subway"
        best_emissions = c["distance_km"] * EMISSION_FACTORS[best_mode]
        saved = c["emissions_kg"] - best_emissions
        icon = MODE_ICONS.get(best_mode, "🚇")
        st.markdown(
            f'<div style="border-left:3px solid #28a745;padding:6px 10px;margin:4px 0;background:#0d1117;border-radius:3px">'
            f'📅 {c["date"]} | {c["route"]} ({c["distance_km"]:.1f} km)<br/>'
            f'🚗 {c["mode"]} → {icon} {best_mode} '
            f'<span style="color:#28a745;font-weight:600">saves {saved:.2f} kg CO₂</span></div>',
            unsafe_allow_html=True,
        )


def _render_goals_tracking(goals: list[dict]):
    """Render weekly emission reduction goals."""
    st.subheader("🎯 Weekly Goals")

    _render_weekly_chart(goals)

    # Goal details
    met = sum(1 for g in goals if g["status"] == "met")
    missed = sum(1 for g in goals if g["status"] == "missed")
    st.markdown(f"**{met}/{met + missed}** goals achieved. ")

    for g in goals:
        if g["actual"] is not None:
            color = "#28a745" if g["actual"] <= g["target"] else "#dc3545"
            icon = "✅" if g["actual"] <= g["target"] else "❌"
            diff = g["target"] - g["actual"]
            st.markdown(
                f'{icon} **{g["week"]}** — Target: {g["target"]:.1f} kg | Actual: {g["actual"]:.1f} kg | '
                f'<span style="color:{color}">{"+" if diff < 0 else ""}{diff:.1f} kg</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(f'⏳ **{g["week"]}** — Target: {g["target"]:.1f} kg (upcoming)')


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def render_green_transportation_planner():
    """Render the Green Transportation Planner page."""
    st.title("🚲 Green Transportation Planner")
    st.markdown(
        "Track commute emissions, compare transportation modes, and optimize for minimal environmental impact."
    )

    commutes = _generate_mock_commutes()
    routes = _generate_mock_routes()
    goals = _generate_mock_goals()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        show_overview = st.checkbox("Overview", True)
        show_modes = st.checkbox("Mode Comparison", True)
        show_routes = st.checkbox("Route Alternatives", True)
        show_trend = st.checkbox("Emission Trend", True)
        show_log = st.checkbox("Commute Log", True)
        show_savings = st.checkbox("Green Savings", True)
        show_goals = st.checkbox("Weekly Goals", True)

    if show_overview:
        _render_overview(commutes)

    if show_modes:
        st.markdown("---")
        _render_mode_comparison(commutes)

    if show_routes:
        st.markdown("---")
        _render_route_comparison(routes)

    if show_trend:
        st.markdown("---")
        _render_emission_trend(commutes)

    if show_log:
        st.markdown("---")
        _render_commute_log(commutes)

    if show_savings:
        st.markdown("---")
        _render_green_savings(commutes)

    if show_goals:
        st.markdown("---")
        _render_goals_tracking(goals)

    st.markdown("---")
    st.caption(f"Green Transportation Planner | {len(commutes)} commutes tracked | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# Entry point
if __name__ == "__main__" or True:
    render_green_transportation_planner()
