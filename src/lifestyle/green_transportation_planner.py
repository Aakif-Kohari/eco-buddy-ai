"""Green Transportation Planner – Compare transport modes, optimize routes for carbon savings, track your commute impact, and discover eco-friendly出行 alternatives."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import math

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Green Transportation", page_icon="🚲", layout="wide")

# ─── Theme ──────────────────────────────────────────────────────────────────
try:
    from styles.theme import apply_theme
    apply_theme()
except Exception:
    pass

# ─── Transport Mode Data ───────────────────────────────────────────────────
TRANSPORT_MODES = {
    "walk": {"label": "🚶 Walking", "color": "#22c55e", "co2_per_km": 0.0, "speed_kmh": 5, "cost_per_km": 0.0, "calories_per_km": 60, "icon": "🚶"},
    "bicycle": {"label": "🚲 Bicycle", "color": "#10b981", "co2_per_km": 0.0, "speed_kmh": 15, "cost_per_km": 0.0, "calories_per_km": 30, "icon": "🚲"},
    "ebike": {"label": "⚡ E-Bike", "color": "#06b6d4", "co2_per_km": 0.02, "speed_kmh": 25, "cost_per_km": 0.01, "calories_per_km": 15, "icon": "⚡"},
    "scooter": {"label": "🛴 E-Scooter", "color": "#8b5cf6", "co2_per_km": 0.03, "speed_kmh": 20, "cost_per_km": 0.02, "calories_per_km": 5, "icon": "🛴"},
    "bus": {"label": "🚌 Bus", "color": "#f59e0b", "co2_per_km": 0.089, "speed_kmh": 20, "cost_per_km": 0.12, "calories_per_km": 0, "icon": "🚌"},
    "tram": {"label": "🚋 Tram/Light Rail", "color": "#3b82f6", "co2_per_km": 0.041, "speed_kmh": 25, "cost_per_km": 0.10, "calories_per_km": 0, "icon": "🚋"},
    "metro": {"label": "🚇 Metro/Subway", "color": "#6366f1", "co2_per_km": 0.035, "speed_kmh": 35, "cost_per_km": 0.08, "calories_per_km": 0, "icon": "🚇"},
    "train": {"label": "🚆 Train", "color": "#ec4899", "co2_per_km": 0.041, "speed_kmh": 80, "cost_per_km": 0.06, "calories_per_km": 0, "icon": "🚆"},
    "car_solo": {"label": "🚗 Car (Solo)", "color": "#ef4444", "co2_per_km": 0.171, "speed_kmh": 40, "cost_per_km": 0.25, "calories_per_km": 0, "icon": "🚗"},
    "carpool": {"label": "🚗 Carpool (2)", "color": "#f97316", "co2_per_km": 0.086, "speed_kmh": 40, "cost_per_km": 0.13, "calories_per_km": 0, "icon": "🚗"},
    "carpool4": {"label": "🚗 Carpool (4)", "color": "#eab308", "co2_per_km": 0.043, "speed_kmh": 40, "cost_per_km": 0.07, "calories_per_km": 0, "icon": "🚗"},
    "ev_solo": {"label": "🔋 EV (Solo)", "color": "#14b8a6", "co2_per_km": 0.053, "speed_kmh": 40, "cost_per_km": 0.08, "calories_per_km": 0, "icon": "🔋"},
    "ev_carpool": {"label": "🔋 EV Carpool", "color": "#0d9488", "co2_per_km": 0.027, "speed_kmh": 40, "cost_per_km": 0.04, "calories_per_km": 0, "icon": "🔋"},
    "motorcycle": {"label": "🏍️ Motorcycle", "color": "#a855f7", "co2_per_km": 0.103, "speed_kmh": 50, "cost_per_km": 0.15, "calories_per_km": 0, "icon": "🏍️"},
}

POPULAR_ROUTES = [
    {"name": "Home → Office", "distance_km": 12, "elevation_m": 50, "city": "Local"},
    {"name": "Home → Gym", "distance_km": 3.5, "elevation_m": 20, "city": "Local"},
    {"name": "Home → Grocery Store", "distance_km": 2.0, "elevation_m": 10, "city": "Local"},
    {"name": "Home → University", "distance_km": 8.0, "elevation_m": 30, "city": "Local"},
    {"name": "City Center → Airport", "distance_km": 25.0, "elevation_m": 100, "city": "Metro"},
    {"name": "Home → Train Station", "distance_km": 4.5, "elevation_m": 15, "city": "Local"},
    {"name": "Office → Lunch Spot", "distance_km": 1.5, "elevation_m": 5, "city": "Local"},
    {"name": "Weekend Trail Ride", "distance_km": 20.0, "elevation_m": 200, "city": "Recreation"},
]

WEATHER_CONDITIONS = {
    "sunny": {"label": "☀️ Sunny", "walk_mult": 1.0, "bike_mult": 1.0, "bus_mult": 1.0},
    "rainy": {"label": "🌧️ Rainy", "walk_mult": 0.7, "bike_mult": 0.6, "bus_mult": 0.95},
    "snowy": {"label": "❄️ Snowy", "walk_mult": 0.5, "bike_mult": 0.3, "bus_mult": 0.9},
    "hot": {"label": "🔥 Hot (>35°C)", "walk_mult": 0.6, "bike_mult": 0.7, "bus_mult": 1.0},
}

# ─── Session State ──────────────────────────────────────────────────────────
if "commute_log" not in st.session_state:
    st.session_state.commute_log = _generate_sample_commute_log() if False else []
if "favorite_routes" not in st.session_state:
    st.session_state.favorite_routes = POPULAR_ROUTES[:4]


def _generate_sample_commute_log():
    """Generate 30 days of sample commute data."""
    log = []
    modes = list(TRANSPORT_MODES.keys())
    weights = [0.05, 0.1, 0.05, 0.05, 0.15, 0.05, 0.1, 0.05, 0.25, 0.05, 0.02, 0.03, 0.01, 0.03]
    for i in range(60):
        day = datetime.now() - timedelta(days=59 - i)
        if day.weekday() >= 5:
            continue  # skip weekends for commute
        mode = random.choices(modes, weights=weights, k=1)[0]
        distance = random.uniform(2, 20)
        meta = TRANSPORT_MODES[mode]
        co2 = distance * meta["co2_per_km"]
        time_min = (distance / meta["speed_kmh"]) * 60
        cost = distance * meta["cost_per_km"]
        calories = distance * meta["calories_per_km"]

        log.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "mode": mode,
            "mode_label": meta["label"],
            "distance_km": round(distance, 1),
            "co2_kg": round(co2, 3),
            "time_min": round(time_min, 1),
            "cost_usd": round(cost, 2),
            "calories": round(calories),
            "route": random.choice(["Home → Office", "Office → Home", "Home → Gym", "Errands"]),
        })
    return log


# ─── Helpers ────────────────────────────────────────────────────────────────

def calculate_route(mode_key, distance_km, weather="sunny"):
    """Calculate route metrics for a transport mode."""
    mode = TRANSPORT_MODES[mode_key]
    weather_info = WEATHER_CONDITIONS.get(weather, WEATHER_CONDITIONS["sunny"])

    speed_mult = 1.0
    if mode_key in ["walk", "bicycle"]:
        lookup_key = "bike" if mode_key == "bicycle" else mode_key
        speed_mult = weather_info.get(f"{lookup_key}_mult", 1.0)
    elif mode_key in ["bus", "tram", "metro"]:
        speed_mult = weather_info.get("bus_mult", 1.0)

    effective_speed = mode["speed_kmh"] * speed_mult
    time_min = (distance_km / effective_speed) * 60 if effective_speed > 0 else 999
    co2 = distance_km * mode["co2_per_km"]
    cost = distance_km * mode["cost_per_km"]
    calories = distance_km * mode["calories_per_km"]

    return {
        "mode": mode_key,
        "label": mode["label"],
        "color": mode["color"],
        "distance_km": distance_km,
        "time_min": round(time_min, 1),
        "co2_kg": round(co2, 3),
        "cost_usd": round(cost, 2),
        "calories": round(calories),
        "speed_kmh": round(effective_speed, 1),
    }


def get_carbon_rating(co2_kg, distance_km):
    """Get carbon rating for a trip."""
    if distance_km == 0:
        return "🌟", "No Trip", "#22c55e"
    intensity = co2_kg / distance_km
    if intensity < 0.01:
        return "🌟", "Zero Carbon", "#22c55e"
    elif intensity < 0.05:
        return "✅", "Very Low", "#10b981"
    elif intensity < 0.10:
        return "🟢", "Low", "#3b82f6"
    elif intensity < 0.15:
        return "⚠️", "Moderate", "#f59e0b"
    else:
        return "🔴", "High", "#ef4444"


# ─── Main Rendering ─────────────────────────────────────────────────────────

def render_green_transport_hub():
    st.title("🚲 Green Transportation Planner")
    st.markdown("Compare transport modes, optimize routes for carbon savings, track your commute impact, and discover eco-friendly出行 alternatives.")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🗺️ Route Optimizer",
        "📊 Mode Comparison",
        "📅 Commute Tracker",
        "🌍 Carbon Savings",
        "🏙️ City Planner",
        "💡 Recommendations",
    ])

    # ═══════════════════════════════════════════
    # TAB 1: Route Optimizer
    # ═══════════════════════════════════════════
    with tab1:
        st.subheader("🗺️ Smart Route Optimizer")
        st.markdown("Find the greenest way to get from A to B.")

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            origin = st.text_input("📍 From", "Home")
        with rc2:
            destination = st.text_input("📍 To", "Office")
        with rc3:
            distance = st.number_input("Distance (km)", 0.5, 100.0, 10.0, step=0.5)

        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            weather = st.selectbox("🌤️ Weather", list(WEATHER_CONDITIONS.keys()),
                                   format_func=lambda x: WEATHER_CONDITIONS[x]["label"])
        with oc2:
            priority = st.selectbox("🎯 Priority", ["Lowest Carbon", "Fastest", "Cheapest", "Best Exercise"])
        with oc3:
            avoid_modes = st.multiselect("🚫 Avoid", list(TRANSPORT_MODES.keys()),
                                          format_func=lambda x: TRANSPORT_MODES[x]["label"])

        if st.button("🔍 Find Best Routes", type="primary"):
            results = []
            for mode_key in TRANSPORT_MODES:
                if mode_key not in avoid_modes:
                    result = calculate_route(mode_key, distance, weather)
                    results.append(result)

            # Sort by priority
            if priority == "Lowest Carbon":
                results.sort(key=lambda x: x["co2_kg"])
            elif priority == "Fastest":
                results.sort(key=lambda x: x["time_min"])
            elif priority == "Cheapest":
                results.sort(key=lambda x: x["cost_usd"])
            elif priority == "Best Exercise":
                results.sort(key=lambda x: x["calories"], reverse=True)

            st.divider()
            st.subheader(f"🏁 Results: {origin} → {destination} ({distance} km, {WEATHER_CONDITIONS[weather]['label']})")

            # Best option highlight
            best = results[0]
            rating_icon, rating_label, rating_color = get_carbon_rating(best["co2_kg"], distance)

            st.markdown(f"""
            <div style="padding:20px;background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:2px solid #22c55e;border-radius:16px;margin:16px 0">
                <div style="font-size:14px;color:#6b7280;margin-bottom:8px">🏆 Best Option ({priority})</div>
                <div style="font-size:24px;font-weight:bold">{best['label']}</div>
                <div style="display:flex;gap:24px;margin-top:12px">
                    <div><span style="font-size:12px;color:#6b7280">Time</span><br/><b>{best['time_min']} min</b></div>
                    <div><span style="font-size:12px;color:#6b7280">Carbon</span><br/><b>{best['co2_kg']} kg CO₂</b> {rating_icon}</div>
                    <div><span style="font-size:12px;color:#6b7280">Cost</span><br/><b>${best['cost_usd']}</b></div>
                    <div><span style="font-size:12px;color:#6b7280">Calories</span><br/><b>{best['calories']} kcal</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # All options comparison
            comp_df = pd.DataFrame(results)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=comp_df["label"], y=comp_df["co2_kg"],
                name="CO₂ (kg)", marker_color=comp_df["color"],
                text=comp_df["co2_kg"].apply(lambda x: f"{x:.3f}"), textposition="outside",
            ))
            fig.update_layout(height=350, title="Carbon Emissions by Mode", yaxis_title="kg CO₂",
                              xaxis_title="", margin=dict(t=40, b=100))
            st.plotly_chart(fig, use_container_width=True)

            # Detailed table
            display_df = comp_df[["label", "time_min", "co2_kg", "cost_usd", "calories", "speed_kmh"]].copy()
            display_df.columns = ["Mode", "Time (min)", "CO₂ (kg)", "Cost ($)", "Calories", "Speed (km/h)"]
            display_df["Rating"] = comp_df.apply(lambda r: f"{get_carbon_rating(r['co2_kg'], distance)[0]} {get_carbon_rating(r['co2_kg'], distance)[1]}", axis=1)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            # Multi-axis comparison
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=comp_df["time_min"], y=comp_df["co2_kg"],
                                     mode="markers+text", text=comp_df["label"].str.split(" ").str[-1],
                                     textposition="top center", marker=dict(size=comp_df["cost_usd"] * 30 + 10,
                                                                             color=comp_df["co2_kg"],
                                                                             colorscale="RdYlGn_r", showscale=True),
                                     name="Modes"))
            fig.update_layout(height=400, title="Time vs Carbon (bubble size = cost)",
                              xaxis_title="Time (min)", yaxis_title="CO₂ (kg)")
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 2: Mode Comparison
    # ═══════════════════════════════════════════
    with tab2:
        st.subheader("📊 Transport Mode Deep Dive")

        selected_modes = st.multiselect(
            "Select modes to compare",
            list(TRANSPORT_MODES.keys()),
            default=["walk", "bicycle", "bus", "car_solo", "ev_solo"],
            format_func=lambda x: TRANSPORT_MODES[x]["label"],
        )

        if selected_modes:
            mode_data = []
            for key in selected_modes:
                m = TRANSPORT_MODES[key]
                mode_data.append({
                    "Mode": m["label"],
                    "CO₂ (g/km)": m["co2_per_km"] * 1000,
                    "Speed (km/h)": m["speed_kmh"],
                    "Cost ($/km)": m["cost_per_km"],
                    "Calories/km": m["calories_per_km"],
                    "Color": m["color"],
                })

            mode_df = pd.DataFrame(mode_data)

            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(mode_df, x="Mode", y="CO₂ (g/km)", color="Mode",
                             color_discrete_map={r["Mode"]: r["Color"] for _, r in mode_df.iterrows()},
                             title="Carbon Emissions (g CO₂/km)")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fig = px.bar(mode_df, x="Mode", y="Speed (km/h)", color="Mode",
                             color_discrete_map={r["Mode"]: r["Color"] for _, r in mode_df.iterrows()},
                             title="Average Speed (km/h)")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(mode_df, x="Mode", y="Cost ($/km)", color="Mode",
                             color_discrete_map={r["Mode"]: r["Color"] for _, r in mode_df.iterrows()},
                             title="Cost ($/km)")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                if mode_df["Calories/km"].sum() > 0:
                    fig = px.bar(mode_df, x="Mode", y="Calories/km", color="Mode",
                                 color_discrete_map={r["Mode"]: r["Color"] for _, r in mode_df.iterrows()},
                                 title="Calories Burned (kcal/km)")
                    fig.update_layout(height=350, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No active transport modes selected for calorie comparison.")

            # Radar chart
            st.subheader("🎯 Multi-Criteria Comparison")
            if len(selected_modes) >= 2:
                categories = ["Low Carbon", "Speed", "Low Cost", "Exercise", "Convenience"]
                fig = go.Figure()
                for key in selected_modes[:5]:
                    m = TRANSPORT_MODES[key]
                    # Normalize scores 0-10
                    co2_score = max(0, 10 - m["co2_per_km"] * 100)
                    speed_score = min(10, m["speed_kmh"] / 10)
                    cost_score = max(0, 10 - m["cost_per_km"] * 50)
                    cal_score = min(10, m["calories_per_km"] / 10)
                    conv_score = 5 if m["speed_kmh"] >= 20 else 3

                    fig.add_trace(go.Scatterpolar(
                        r=[co2_score, speed_score, cost_score, cal_score, conv_score, co2_score],
                        theta=categories + [categories[0]],
                        name=m["label"].split(" ")[-1],
                        fill="toself",
                        opacity=0.6,
                    ))
                fig.update_layout(height=450, polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                                  title="Multi-Criteria Radar")
                st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 3: Commute Tracker
    # ═══════════════════════════════════════════
    with tab3:
        st.subheader("📅 Commute Tracker")

        # Log a trip
        with st.expander("➕ Log a Trip", expanded=False):
            with st.form("log_trip"):
                lc1, lc2, lc3 = st.columns(3)
                with lc1:
                    trip_mode = st.selectbox("Mode", list(TRANSPORT_MODES.keys()),
                                              format_func=lambda x: TRANSPORT_MODES[x]["label"])
                with lc2:
                    trip_dist = st.number_input("Distance (km)", 0.1, 200.0, 10.0, step=0.5)
                with lc3:
                    trip_date = st.date_input("Date", datetime.now())
                    trip_route = st.selectbox("Route", ["Home → Office", "Office → Home", "Gym", "Errands", "Other"])

                if st.form_submit_button("📝 Log Trip"):
                    meta = TRANSPORT_MODES[trip_mode]
                    st.session_state.commute_log.append({
                        "date": trip_date.strftime("%Y-%m-%d"),
                        "day_name": trip_date.strftime("%A"),
                        "mode": trip_mode,
                        "mode_label": meta["label"],
                        "distance_km": trip_dist,
                        "co2_kg": round(trip_dist * meta["co2_per_km"], 3),
                        "time_min": round((trip_dist / meta["speed_kmh"]) * 60, 1),
                        "cost_usd": round(trip_dist * meta["cost_per_km"], 2),
                        "calories": round(trip_dist * meta["calories_per_km"]),
                        "route": trip_route,
                    })
                    st.success("✅ Trip logged!")
                    st.rerun()

        log = st.session_state.commute_log

        if log:
            log_df = pd.DataFrame(log)
            log_df["date"] = pd.to_datetime(log_df["date"])

            total_dist = log_df["distance_km"].sum()
            total_co2 = log_df["co2_kg"].sum()
            total_cost = log_df["cost_usd"].sum()
            total_cal = log_df["calories"].sum()
            total_time = log_df["time_min"].sum()

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("🛣️ Total Distance", f"{total_dist:.0f} km")
            with c2:
                st.metric("🌍 Total CO₂", f"{total_co2:.1f} kg")
            with c3:
                st.metric("💰 Total Cost", f"${total_cost:.2f}")
            with c4:
                st.metric("🔥 Calories", f"{total_cal:,}")
            with c5:
                st.metric("⏱️ Total Time", f"{total_time:.0f} min")

            st.divider()

            # Mode distribution
            c1, c2 = st.columns(2)
            with c1:
                mode_dist = log_df.groupby("mode")["distance_km"].sum().reset_index()
                mode_dist["label"] = mode_dist["mode"].map(lambda x: TRANSPORT_MODES.get(x, {}).get("label", x))
                fig = px.pie(mode_dist, values="distance_km", names="label", title="Distance by Mode",
                             hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                daily_co2 = log_df.groupby("date")["co2_kg"].sum().reset_index()
                fig = px.bar(daily_co2, x="date", y="co2_kg", title="Daily CO₂ Emissions",
                             color_discrete_sequence=["#22c55e"])
                fig.update_layout(height=350, xaxis_title="", yaxis_title="kg CO₂")
                st.plotly_chart(fig, use_container_width=True)

            # Full log
            st.subheader("📋 Trip History")
            display_log = log_df[["date", "mode_label", "distance_km", "co2_kg", "time_min", "cost_usd", "calories", "route"]].copy()
            display_log.columns = ["Date", "Mode", "Distance", "CO₂ (kg)", "Time (min)", "Cost ($)", "Calories", "Route"]
            st.dataframe(display_log.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("No trips logged yet. Start tracking your commutes!")

    # ═══════════════════════════════════════════
    # TAB 4: Carbon Savings
    # ═══════════════════════════════════════════
    with tab4:
        st.subheader("🌍 Carbon Savings Calculator")

        st.markdown("See how much CO₂ you save by choosing greener transport options.")

        calc_dist = st.slider("Monthly commute distance (km)", 50, 2000, 400, step=50)
        calc_mode = st.selectbox("Your primary mode", list(TRANSPORT_MODES.keys()),
                                  format_func=lambda x: TRANSPORT_MODES[x]["label"],
                                  key="savings_mode")

        meta = TRANSPORT_MODES[calc_mode]
        monthly_co2 = calc_dist * meta["co2_per_km"]
        annual_co2 = monthly_co2 * 12

        # Compare with car solo
        car_co2_monthly = calc_dist * TRANSPORT_MODES["car_solo"]["co2_per_km"]
        savings_monthly = car_co2_monthly - monthly_co2
        savings_annual = savings_monthly * 12

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("🚗 If Drove (Monthly)", f"{car_co2_monthly:.1f} kg")
        with c2:
            st.metric(f"{meta['icon']} Your Mode (Monthly)", f"{monthly_co2:.1f} kg")
        with c3:
            st.metric("💰 Monthly Savings", f"{savings_monthly:.1f} kg", delta=f"{savings_monthly/car_co2_monthly*100:.0f}% less")
        with c4:
            st.metric("📅 Annual Savings", f"{savings_annual:.0f} kg")

        if savings_annual > 0:
            trees = int(savings_annual / 21)
            cars = round(savings_annual / 4600, 2)

            st.divider()
            st.subheader("🌳 Your Annual Impact")
            ic1, ic2, ic3, ic4 = st.columns(4)
            with ic1:
                st.metric("🌳 Trees Equivalent", f"{trees}")
            with ic2:
                st.metric("🚗 Cars Removed", f"{cars}")
            with ic3:
                cost_savings = savings_annual * 0.05  # social cost of carbon
                st.metric("💵 Social Cost Savings", f"${cost_savings:.0f}")
            with ic4:
                flights = round(savings_annual / 255, 1)
                st.metric("✈️ Flights Offset", f"{flights}")

        # Mode comparison chart
        st.divider()
        st.subheader("📊 All Modes Comparison (Monthly)")
        all_modes_data = []
        for key, m in TRANSPORT_MODES.items():
            all_modes_data.append({
                "Mode": m["label"],
                "Monthly CO₂ (kg)": calc_dist * m["co2_per_km"],
                "Monthly Cost ($)": calc_dist * m["cost_per_km"],
                "Monthly Calories": calc_dist * m["calories_per_km"],
                "Color": m["color"],
            })

        modes_df = pd.DataFrame(all_modes_data).sort_values("Monthly CO₂ (kg)")

        fig = px.bar(modes_df, x="Mode", y="Monthly CO₂ (kg)", color="Mode",
                     color_discrete_map={r["Mode"]: r["Color"] for _, r in modes_df.iterrows()},
                     title=f"Monthly CO₂ for {calc_dist} km Commute")
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 5: City Planner
    # ═══════════════════════════════════════════
    with tab5:
        st.subheader("🏙️ City Transport Planner")

        st.markdown("Plan your weekly transport schedule to minimize carbon footprint while meeting your needs.")

        # Weekly planner
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        weekly_plan = {}

        for day in days:
            with st.expander(f"📅 {day}", expanded=(day == "Monday")):
                wc1, wc2, wc3 = st.columns(3)
                with wc1:
                    morning_mode = st.selectbox("Morning Commute", list(TRANSPORT_MODES.keys()),
                                                 format_func=lambda x: TRANSPORT_MODES[x]["label"],
                                                 key=f"morning_{day}")
                with wc2:
                    morning_dist = st.number_input("Distance (km)", 1.0, 50.0, 10.0, key=f"mdist_{day}")
                with wc3:
                    morning_route = st.selectbox("Route", ["Home → Office", "Home → University", "Home → Client"],
                                                  key=f"mroute_{day}")

                # Evening return
                evening_mode = st.selectbox("Evening Return", list(TRANSPORT_MODES.keys()),
                                             format_func=lambda x: TRANSPORT_MODES[x]["label"],
                                             key=f"evening_{day}")

                morning = calculate_route(morning_mode, morning_dist)
                evening = calculate_route(evening_mode, morning_dist)
                total_day_co2 = morning["co2_kg"] + evening["co2_kg"]
                total_day_cost = morning["cost_usd"] + evening["cost_usd"]

                weekly_plan[day] = {
                    "morning": morning, "evening": evening,
                    "total_co2": total_day_co2, "total_cost": total_day_cost,
                }

                rating_icon, rating_label, _ = get_carbon_rating(total_day_co2, morning_dist * 2)
                st.caption(f"📊 Day Total: {total_day_co2:.3f} kg CO₂ • ${total_day_cost:.2f} • {rating_icon} {rating_label}")

        # Weekly summary
        if weekly_plan:
            st.divider()
            st.subheader("📊 Weekly Summary")
            total_week_co2 = sum(d["total_co2"] for d in weekly_plan.values())
            total_week_cost = sum(d["total_cost"] for d in weekly_plan.values())

            wc1, wc2, wc3, wc4 = st.columns(4)
            with wc1:
                st.metric("🌍 Weekly CO₂", f"{total_week_co2:.2f} kg")
            with wc2:
                st.metric("💰 Weekly Cost", f"${total_week_cost:.2f}")
            with wc3:
                monthly_co2 = total_week_co2 * 4
                st.metric("📅 Monthly Est.", f"{monthly_co2:.1f} kg")
            with wc4:
                car_monthly = sum((TRANSPORT_MODES["car_solo"]["co2_per_km"] * weekly_plan[d]["morning"]["distance_km"] * 2) for d in weekly_plan) * 4
                saved = car_monthly - monthly_co2
                st.metric("💡 vs Driving", f"{saved:.1f} kg saved", delta=f"{saved/car_monthly*100:.0f}% less")

            # Daily breakdown chart
            days_list = list(weekly_plan.keys())
            co2_values = [weekly_plan[d]["total_co2"] for d in days_list]
            cost_values = [weekly_plan[d]["total_cost"] for d in days_list]

            fig = go.Figure()
            fig.add_trace(go.Bar(x=days_list, y=co2_values, name="CO₂ (kg)", marker_color="#22c55e"))
            fig.add_trace(go.Bar(x=days_list, y=cost_values, name="Cost ($)", marker_color="#3b82f6"))
            fig.update_layout(barmode="group", height=350, title="Daily Breakdown", yaxis_title="Value")
            st.plotly_chart(fig, use_container_width=True)

    # ═══════════════════════════════════════════
    # TAB 6: Recommendations
    # ═══════════════════════════════════════════
    with tab6:
        st.subheader("💡 Green Transport Recommendations")

        log = st.session_state.commute_log
        if log:
            log_df = pd.DataFrame(log)
            car_trips = log_df[log_df["mode"].isin(["car_solo", "carpool", "motorcycle"])]
            active_trips = log_df[log_df["mode"].isin(["walk", "bicycle", "ebike"])]
            transit_trips = log_df[log_df["mode"].isin(["bus", "tram", "metro", "train"])]

            recommendations = []

            if len(car_trips) > len(log_df) * 0.3:
                src.ai.recommendations.append({
                    "icon": "🚗→🚲",
                    "title": "Try Active Transport",
                    "description": f"You drive {len(car_trips)} times. Switch short trips (<5km) to cycling or walking to save CO₂ and get exercise.",
                    "impact": f"Could save {len(car_trips) * 2:.0f} kg CO₂/year",
                    "priority": "high",
                })

            if len(active_trips) == 0:
                src.ai.recommendations.append({
                    "icon": "🚲",
                    "title": "Start Cycling",
                    "description": "No active transport logged. Try cycling for trips under 10km — it's free, healthy, and zero-emission.",
                    "impact": "Could save 50+ kg CO₂/year",
                    "priority": "medium",
                })

            if len(transit_trips) > 0:
                src.ai.recommendations.append({
                    "icon": "🚇",
                    "title": "Great Transit Use!",
                    "description": f"You use public transit {len(transit_trips)} times. Keep it up!",
                    "impact": f"Already saving {len(transit_trips) * 3:.0f} kg CO₂ vs driving",
                    "priority": "info",
                })

            # General recommendations
            src.ai.recommendations.extend([
                {
                    "icon": "🚗",
                    "title": "Carpool When Possible",
                    "description": "Sharing rides halves per-person emissions and costs.",
                    "impact": "50% CO₂ reduction per trip",
                    "priority": "medium",
                },
                {
                    "icon": "🔋",
                    "title": "Consider an EV",
                    "description": "Electric vehicles produce 70% less CO₂ than petrol cars over their lifetime.",
                    "impact": "70% lifetime CO₂ reduction",
                    "priority": "medium",
                },
                {
                    "icon": "📅",
                    "title": "Bundle Errands",
                    "description": "Combine multiple errands into one trip to reduce total distance.",
                    "impact": "10-20% fewer km traveled",
                    "priority": "low",
                },
                {
                    "icon": "🌧️",
                    "title": "Plan for Weather",
                    "description": "Keep rain gear ready so weather doesn't derail your green commute.",
                    "impact": "Maintains consistent green habits",
                    "priority": "low",
                },
            ])

            for rec in recommendations:
                priority_colors = {"high": "#ef4444", "medium": "#f59e0b", "low": "#3b82f6", "info": "#22c55e"}
                color = priority_colors.get(rec["priority"], "#6b7280")

                st.markdown(f"""
                <div style="padding:16px;margin:8px 0;border-left:4px solid {color};background:#f8fafc;border-radius:0 12px 12px 0">
                    <div style="display:flex;align-items:center;gap:12px">
                        <span style="font-size:28px">{rec['icon']}</span>
                        <div>
                            <div style="font-weight:bold;font-size:15px">{rec['title']}</div>
                            <div style="color:#6b7280;font-size:13px;margin-top:4px">{rec['description']}</div>
                            <div style="color:{color};font-size:12px;font-weight:600;margin-top:4px">Impact: {rec['impact']}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Log some trips first to get personalized recommendations!")
            st.markdown("""
            ### 🌟 General Green Transport Tips
            1. **Walk or cycle** for trips under 3 km
            2. **Use public transit** for medium distances
            3. **Carpool** when driving is necessary
            4. **Work from home** when possible
            5. **Bundle errands** to reduce total trips
            6. **Maintain your vehicle** for better fuel efficiency
            7. **Choose EV or hybrid** for your next car
            8. **Use micro-mobility** (e-scooters, e-bikes) for last-mile
            """)


# ─── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    render_green_transport_hub()
