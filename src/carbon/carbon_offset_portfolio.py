"""Carbon Offset Portfolio Tracker – Track carbon credits, offset projects, portfolio performance, and environmental impact."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import math

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Carbon Offset Portfolio", page_icon="🌍", layout="wide")

# ─── Theme ──────────────────────────────────────────────────────────────────
try:
    from styles.theme import apply_theme
    apply_theme()
except Exception:
    pass

# ─── Constants ──────────────────────────────────────────────────────────────
OFFSET_PROJECT_TYPES = {
    "reforestation": {"label": "🌳 Reforestation", "color": "#22c55e", "avgPrice": 15, "avgCO2": 50},
    "renewable_energy": {"label": "⚡ Renewable Energy", "color": "#3b82f6", "avgPrice": 20, "avgCO2": 100},
    "methane_capture": {"label": "🏭 Methane Capture", "color": "#f59e0b", "avgPrice": 25, "avgCO2": 200},
    "cookstoves": {"label": "🍳 Clean Cookstoves", "color": "#ef4444", "avgPrice": 10, "avgCO2": 30},
    "ocean_restoration": {"label": "🌊 Ocean Restoration", "color": "#06b6d4", "avgPrice": 35, "avgCO2": 75},
    "soil_carbon": {"label": "🌱 Soil Carbon", "color": "#8b5cf6", "avgPrice": 18, "avgCO2": 40},
    "mangrove": {"label": "🌴 Mangrove Restoration", "color": "#14b8a6", "avgPrice": 22, "avgCO2": 60},
    "direct_air_capture": {"label": "💨 Direct Air Capture", "color": "#6366f1", "avgPrice": 60, "avgCO2": 500},
}

VERIFICATION_STANDARDS = ["Gold Standard", "Verra VCS", "American Carbon Registry", "Climate Action Reserve", "Plan Vivo", "CDM"]

COUNTRIES = ["Brazil", "India", "Kenya", "Indonesia", "Peru", "Colombia", "Costa Rica", "Madagascar", "Mexico", "Tanzania"]

# ─── Session State ──────────────────────────────────────────────────────────
if "offset_credits" not in st.session_state:
    st.session_state.offset_credits = []
if "offset_projects" not in st.session_state:
    st.session_state.offset_projects = _generate_sample_projects()
if "retired_credits" not in st.session_state:
    st.session_state.retired_credits = []


def _generate_sample_projects():
    """Generate sample offset projects for demo."""
    projects = []
    types = list(OFFSET_PROJECT_TYPES.keys())
    for i in range(8):
        ptype = types[i % len(types)]
        meta = OFFSET_PROJECT_TYPES[ptype]
        total_credits = random.randint(500, 5000)
        sold = random.randint(100, total_credits)
        projects.append({
            "id": f"PROJ-{1000 + i}",
            "name": f"{meta['label'].split(' ')[1]} Project {i + 1}",
            "type": ptype,
            "country": random.choice(COUNTRIES),
            "total_credits": total_credits,
            "credits_sold": sold,
            "credits_available": total_credits - sold,
            "price_per_credit": meta["avgPrice"] + random.randint(-5, 10),
            "co2_per_credit": meta["avgCO2"] + random.randint(-10, 20),
            "verification": random.choice(VERIFICATION_STANDARDS),
            "start_date": (datetime.now() - timedelta(days=random.randint(30, 365))).strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=random.randint(180, 1825))).strftime("%Y-%m-%d"),
            "sdg_goals": random.sample([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], k=random.randint(2, 5)),
            "rating": round(random.uniform(3.5, 5.0), 1),
            "photos": random.randint(5, 30),
            "community_benefit": random.choice([
                "Provides jobs to 200+ local community members",
                "Funds local school construction",
                "Supports women-led cooperatives",
                "Protects endangered wildlife habitat",
                "Improves water access for 500 families",
            ]),
        })
    return projects


# ─── Helper Functions ───────────────────────────────────────────────────────

def get_portfolio_stats():
    """Calculate portfolio statistics."""
    credits = st.session_state.offset_credits
    retired = st.session_state.retired_credits
    
    total_purchased = sum(c["quantity"] for c in credits)
    total_retired = sum(c["quantity"] for c in retired)
    total_spent = sum(c["quantity"] * c["price_per_credit"] for c in credits)
    total_co2_offset = sum(c["quantity"] * c["co2_per_credit"] for c in credits)
    total_co2_retired = sum(c["quantity"] * c["co2_per_credit"] for c in retired)
    avg_price = total_spent / total_purchased if total_purchased > 0 else 0
    
    return {
        "total_purchased": total_purchased,
        "total_retired": total_retired,
        "active_credits": total_purchased - total_retired,
        "total_spent": total_spent,
        "total_co2_offset": total_co2_offset,
        "total_co2_retired": total_co2_retired,
        "avg_price": round(avg_price, 2),
        "portfolio_value": total_spent,
        "cost_per_ton": round(total_spent / (total_co2_offset / 1000), 2) if total_co2_offset > 0 else 0,
    }


def get_type_breakdown():
    """Get breakdown by project type."""
    credits = st.session_state.offset_credits
    breakdown = {}
    for c in credits:
        ptype = c.get("type", "unknown")
        if ptype not in breakdown:
            breakdown[ptype] = {"quantity": 0, "value": 0, "co2": 0}
        breakdown[ptype]["quantity"] += c["quantity"]
        breakdown[ptype]["value"] += c["quantity"] * c["price_per_credit"]
        breakdown[ptype]["co2"] += c["quantity"] * c["co2_per_credit"]
    return breakdown


def get_monthly_trend():
    """Generate monthly purchase trend."""
    credits = st.session_state.offset_credits
    monthly = {}
    for c in credits:
        month = c.get("purchase_date", datetime.now().strftime("%Y-%m"))[:7]
        if month not in monthly:
            monthly[month] = {"quantity": 0, "value": 0, "co2": 0}
        monthly[month]["quantity"] += c["quantity"]
        monthly[month]["value"] += c["quantity"] * c["price_per_credit"]
        monthly[month]["co2"] += c["quantity"] * c["co2_per_credit"]
    return dict(sorted(monthly.items()))


def render_stat_card(label, value, icon="", delta=None, color="blue"):
    """Render a stat metric card."""
    st.metric(label=f"{icon} {label}" if icon else label, value=value, delta=delta)


# ─── Main Rendering ─────────────────────────────────────────────────────────

def render_offset_portfolio_hub():
    """Main hub rendering."""
    st.title("🌍 Carbon Offset Portfolio")
    st.markdown("Track your carbon credit purchases, manage offset projects, and visualize your environmental impact.")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Portfolio Overview",
        "🛒 Buy Credits",
        "📁 My Credits",
        "🏗️ Offset Projects",
        "🔥 Retire Credits",
        "📈 Analytics",
    ])
    
    # ═══════════════════════════════════════════
    # TAB 1: Portfolio Overview
    # ═══════════════════════════════════════════
    with tab1:
        stats = get_portfolio_stats()
        
        # KPI Row
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("🏷️ Total Credits", f"{stats['total_purchased']:,}")
        with col2:
            st.metric("🔥 Retired", f"{stats['total_retired']:,}")
        with col3:
            st.metric("💎 Active", f"{stats['active_credits']:,}")
        with col4:
            st.metric("💰 Total Spent", f"${stats['total_spent']:,.0f}")
        with col5:
            st.metric("🌍 CO₂ Offset", f"{stats['total_co2_offset'] / 1000:,.1f}t")
        
        st.divider()
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Portfolio Value Trend
            st.subheader("📈 Portfolio Growth")
            monthly = get_monthly_trend()
            if monthly:
                df = pd.DataFrame([
                    {"Month": k, "Value": v["value"], "Credits": v["quantity"], "CO2 (kg)": v["co2"]}
                    for k, v in monthly.items()
                ])
                fig = px.area(df, x="Month", y="Value", title="Cumulative Investment",
                              color_discrete_sequence=["#22c55e"])
                fig.update_layout(height=300, margin=dict(t=40, b=20, l=40, r=20))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No credits purchased yet. Start building your portfolio!")
        
        with col_right:
            # Type Breakdown
            st.subheader("🎯 Offset by Type")
            breakdown = get_type_breakdown()
            if breakdown:
                labels = [OFFSET_PROJECT_TYPES.get(k, {"label": k})["label"] for k in breakdown.keys()]
                values = [v["co2"] for v in breakdown.values()]
                colors = [OFFSET_PROJECT_TYPES.get(k, {"color": "#999"})["color"] for k in breakdown.keys()]
                
                fig = go.Figure(data=[go.Pie(
                    labels=labels, values=values,
                    hole=0.4, marker=dict(colors=colors),
                    textinfo="label+percent", textposition="outside",
                )])
                fig.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No credits to display.")
        
        # CO2 Impact Visualization
        st.subheader("🌍 Your Carbon Impact")
        if stats["total_co2_offset"] > 0:
            co2_tons = stats["total_co2_offset"] / 1000
            trees_equivalent = int(co2_tons * 45)
            cars_removed = round(co2_tons / 4.6, 1)
            flights_offset = round(co2_tons / 0.255, 1)
            homes_powered = round(co2_tons / 7.5, 1)
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🌳 Trees Equivalent", f"{trees_equivalent:,}")
            with c2:
                st.metric("🚗 Cars Removed", f"{cars_removed}")
            with c3:
                st.metric("✈️ Flights Offset", f"{flights_offset}")
            with c4:
                st.metric("🏠 Homes Powered", f"{homes_powered} yr")
            
            # Impact gauge
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=stats["total_co2_offset"] / 1000,
                title={"text": "Total CO₂ Offset (tonnes)"},
                delta={"reference": 10, "increasing": {"color": "#22c55e"}},
                gauge={
                    "axis": {"range": [0, 50]},
                    "bar": {"color": "#22c55e"},
                    "steps": [
                        {"range": [0, 10], "color": "#fef2f2"},
                        {"range": [10, 25], "color": "#fefce8"},
                        {"range": [25, 50], "color": "#f0fdf4"},
                    ],
                    "threshold": {
                        "line": {"color": "#16a34a", "width": 4},
                        "thickness": 0.75,
                        "value": 25,
                    },
                },
            ))
            fig.update_layout(height=250, margin=dict(t=60, b=20))
            st.plotly_chart(fig, use_container_width=True)
    
    # ═══════════════════════════════════════════
    # TAB 2: Buy Credits
    # ═══════════════════════════════════════════
    with tab2:
        st.subheader("🛒 Carbon Credit Marketplace")
        st.markdown("Browse verified offset projects and purchase carbon credits.")
        
        # Filters
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            filter_type = st.selectbox("Project Type", ["All"] + [v["label"] for v in OFFSET_PROJECT_TYPES.values()])
        with fcol2:
            filter_country = st.selectbox("Country", ["All"] + COUNTRIES)
        with fcol3:
            filter_standard = st.selectbox("Verification", ["All"] + VERIFICATION_STANDARDS)
        with fcol4:
            sort_by = st.selectbox("Sort by", ["Price (Low)", "Price (High)", "Rating", "Available"])
        
        # Filter projects
        projects = st.session_state.offset_projects
        filtered = projects
        
        if filter_type != "All":
            ptype = [k for k, v in OFFSET_PROJECT_TYPES.items() if v["label"] == filter_type][0]
            filtered = [p for p in filtered if p["type"] == ptype]
        if filter_country != "All":
            filtered = [p for p in filtered if p["country"] == filter_country]
        if filter_standard != "All":
            filtered = [p for p in filtered if p["verification"] == filter_standard]
        
        # Sort
        if sort_by == "Price (Low)":
            filtered.sort(key=lambda x: x["price_per_credit"])
        elif sort_by == "Price (High)":
            filtered.sort(key=lambda x: x["price_per_credit"], reverse=True)
        elif sort_by == "Rating":
            filtered.sort(key=lambda x: x["rating"], reverse=True)
        elif sort_by == "Available":
            filtered.sort(key=lambda x: x["credits_available"], reverse=True)
        
        st.caption(f"Showing {len(filtered)} projects")
        
        # Project Cards
        for project in filtered:
            meta = OFFSET_PROJECT_TYPES.get(project["type"], {"label": "Unknown", "color": "#999"})
            
            with st.container():
                cols = st.columns([3, 2, 2, 2])
                
                with cols[0]:
                    st.markdown(f"**{project['name']}**")
                    st.caption(f"{meta['label']} • {project['country']}")
                    st.caption(f"⭐ {project['rating']}/5.0 • {project['verification']}")
                    st.caption(f"📅 {project['start_date']} → {project['end_date']}")
                
                with cols[1]:
                    st.metric("Available", f"{project['credits_available']:,}")
                    st.metric("Price/Credit", f"${project['price_per_credit']}")
                
                with cols[2]:
                    st.metric("CO₂/Credit", f"{project['co2_per_credit']}kg")
                    st.metric("Total Credits", f"{project['total_credits']:,}")
                
                with cols[3]:
                    qty = st.number_input(
                        "Qty",
                        min_value=1,
                        max_value=project["credits_available"],
                        value=10,
                        key=f"buy_{project['id']}",
                    )
                    total = qty * project["price_per_credit"]
                    st.caption(f"Total: **${total:,.0f**}")
                    
                    if st.button("🛒 Buy", key=f"purchase_{project['id']}", type="primary"):
                        credit = {
                            "id": f"CRED-{random.randint(10000, 99999)}",
                            "project_id": project["id"],
                            "project_name": project["name"],
                            "type": project["type"],
                            "country": project["country"],
                            "quantity": qty,
                            "price_per_credit": project["price_per_credit"],
                            "co2_per_credit": project["co2_per_credit"],
                            "verification": project["verification"],
                            "purchase_date": datetime.now().strftime("%Y-%m-%d"),
                            "status": "active",
                        }
                        st.session_state.offset_credits.append(credit)
                        st.success(f"✅ Purchased {qty} credits from {project['name']}!")
                        st.rerun()
                
                st.divider()
    
    # ═══════════════════════════════════════════
    # TAB 3: My Credits
    # ═══════════════════════════════════════════
    with tab3:
        st.subheader("📁 My Carbon Credits")
        
        credits = st.session_state.offset_credits
        if credits:
            df = pd.DataFrame(credits)
            df["total_value"] = df["quantity"] * df["price_per_credit"]
            df["total_co2"] = df["quantity"] * df["co2_per_credit"]
            
            # Summary
            st.metric("Active Credits", f"{len(credits)} lots • {df['quantity'].sum():,} total")
            
            # Table
            display_df = df[["id", "project_name", "type", "country", "quantity", "price_per_credit", "total_value", "total_co2", "purchase_date", "verification"]].copy()
            display_df.columns = ["ID", "Project", "Type", "Country", "Qty", "Price", "Value", "CO₂ (kg)", "Purchased", "Standard"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Charts
            c1, c2 = st.columns(2)
            with c1:
                type_sums = df.groupby("type")["quantity"].sum().reset_index()
                type_sums["label"] = type_sums["type"].map(lambda x: OFFSET_PROJECT_TYPES.get(x, {"label": x})["label"])
                fig = px.bar(type_sums, x="label", y="quantity", title="Credits by Project Type",
                             color="label", color_discrete_map={r: OFFSET_PROJECT_TYPES.get(k, {"color": "#999"})["color"] for k, r in zip(OFFSET_PROJECT_TYPES.keys(), [v["label"] for v in OFFSET_PROJECT_TYPES.values()])})
                fig.update_layout(height=300, showlegend=False, xaxis_title="", yaxis_title="Credits")
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                country_sums = df.groupby("country")["total_co2"].sum().reset_index()
                fig = px.bar(country_sums, x="country", y="total_co2", title="CO₂ Offset by Country",
                             color="country")
                fig.update_layout(height=300, showlegend=False, xaxis_title="", yaxis_title="CO₂ (kg)")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No credits purchased yet. Visit the Buy Credits tab to get started!")
    
    # ═══════════════════════════════════════════
    # TAB 4: Offset Projects
    # ═══════════════════════════════════════════
    with tab4:
        st.subheader("🏗️ Available Offset Projects")
        st.markdown("Explore verified carbon offset projects around the world.")
        
        projects = st.session_state.offset_projects
        
        # Project type overview
        type_counts = {}
        for p in projects:
            t = p["type"]
            if t not in type_counts:
                type_counts[t] = {"count": 0, "total_credits": 0, "avg_rating": []}
            type_counts[t]["count"] += 1
            type_counts[t]["total_credits"] += p["total_credits"]
            type_counts[t]["avg_rating"].append(p["rating"])
        
        st.subheader("Project Types Overview")
        cols = st.columns(4)
        for i, (ptype, data) in enumerate(sorted(type_counts.items(), key=lambda x: x[1]["total_credits"], reverse=True)):
            meta = OFFSET_PROJECT_TYPES.get(ptype, {"label": "Unknown", "color": "#999"})
            avg_rating = sum(data["avg_rating"]) / len(data["avg_rating"])
            with cols[i % 4]:
                st.metric(
                    label=meta["label"],
                    value=f"{data['total_credits']:,} credits",
                    delta=f"{data['count']} projects • ⭐{avg_rating:.1f}",
                )
        
        st.divider()
        
        # Detailed project view
        for project in projects:
            meta = OFFSET_PROJECT_TYPES.get(project["type"], {"label": "Unknown", "color": "#999"})
            
            with st.expander(f"{meta['label']} — {project['name']} ({project['country']})", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**Location:** {project['country']}")
                    st.write(f"**Verification:** {project['verification']}")
                    st.write(f"**Rating:** {'⭐' * int(project['rating'])} {project['rating']}/5.0")
                    st.write(f"**Duration:** {project['start_date']} → {project['end_date']}")
                with c2:
                    st.write(f"**Total Credits:** {project['total_credits']:,}")
                    st.write(f"**Credits Sold:** {project['credits_sold']:,}")
                    st.write(f"**Available:** {project['credits_available']:,}")
                    st.write(f"**Price/Credit:** ${project['price_per_credit']}")
                with c3:
                    st.write(f"**CO₂ per Credit:** {project['co2_per_credit']}kg")
                    st.write(f"**Total CO₂ Capacity:** {project['total_credits'] * project['co2_per_credit'] / 1000:.1f}t")
                    st.write(f"**Photos:** {project['photos']}")
                    st.write(f"**Community:** {project['community_benefit']}")
                
                # SDG Goals
                st.write(f"**SDG Goals:** {', '.join([f'Goal {g}' for g in project['sdg_goals']])}")
                
                # Progress bar
                progress = project["credits_sold"] / project["total_credits"] if project["total_credits"] > 0 else 0
                st.progress(progress)
                st.caption(f"{progress * 100:.0f}% of credits sold")
    
    # ═══════════════════════════════════════════
    # TAB 5: Retire Credits
    # ═══════════════════════════════════════════
    with tab5:
        st.subheader("🔥 Retire Carbon Credits")
        st.markdown("Permanently retire your credits to claim the carbon offset. Retired credits cannot be resold.")
        
        active = [c for c in st.session_state.offset_credits if c["status"] == "active"]
        
        if active:
            for credit in active:
                meta = OFFSET_PROJECT_TYPES.get(credit["type"], {"label": "Unknown"})
                with st.container():
                    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                    with c1:
                        st.write(f"**{credit['project_name']}**")
                        st.caption(f"{meta['label']} • {credit['country']} • {credit['verification']}")
                    with c2:
                        st.write(f"Qty: {credit['quantity']:,}")
                        st.write(f"CO₂: {credit['quantity'] * credit['co2_per_credit'] / 1000:.1f}t")
                    with c3:
                        st.write(f"Value: ${credit['quantity'] * credit['price_per_credit']:,.0f}")
                        st.write(f"Purchased: {credit['purchase_date']}")
                    with c4:
                        retire_qty = st.number_input(
                            "Retire", min_value=1, max_value=credit["quantity"],
                            value=credit["quantity"], key=f"retire_{credit['id']}",
                        )
                        if st.button("🔥 Retire", key=f"dorefire_{credit['id']}", type="primary"):
                            retired = {**credit, "quantity": retire_qty, "retired_date": datetime.now().strftime("%Y-%m-%d")}
                            st.session_state.retired_credits.append(retired)
                            
                            remaining = credit["quantity"] - retire_qty
                            if remaining > 0:
                                credit["quantity"] = remaining
                            else:
                                st.session_state.offset_credits.remove(credit)
                            
                            st.success(f"🔥 Retired {retire_qty} credits! Thank you for offsetting {retire_qty * credit['co2_per_credit'] / 1000:.1f}t CO₂.")
                            st.rerun()
                    st.divider()
            
            # Retired credits history
            if st.session_state.retired_credits:
                st.subheader("📜 Retirement History")
                retired_df = pd.DataFrame(st.session_state.retired_credits)
                retired_df["total_co2"] = retired_df["quantity"] * retired_df["co2_per_credit"]
                display = retired_df[["id", "project_name", "quantity", "total_co2", "retired_date"]].copy()
                display.columns = ["ID", "Project", "Qty Retired", "CO₂ Offset (kg)", "Retired On"]
                st.dataframe(display, use_container_width=True, hide_index=True)
        else:
            st.info("No active credits to retire. Purchase credits first!")
    
    # ═══════════════════════════════════════════
    # TAB 6: Analytics
    # ═══════════════════════════════════════════
    with tab6:
        st.subheader("📈 Portfolio Analytics")
        
        stats = get_portfolio_stats()
        credits = st.session_state.offset_credits
        retired = st.session_state.retired_credits
        
        if credits or retired:
            # Cost Efficiency
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("💰 Avg Price/Credit", f"${stats['avg_price']}")
            with c2:
                st.metric("📊 Cost per Tonne", f"${stats['cost_per_ton']}" if stats['cost_per_ton'] > 0 else "N/A")
            with c3:
                st.metric("🌍 CO₂ Offset", f"{stats['total_co2_offset'] / 1000:,.1f}t")
            with c4:
                st.metric("🔥 CO₂ Retired", f"{stats['total_co2_retired'] / 1000:,.1f}t")
            
            st.divider()
            
            if credits:
                df = pd.DataFrame(credits)
                df["value"] = df["quantity"] * df["price_per_credit"]
                df["co2"] = df["quantity"] * df["co2_per_credit"]
                
                c1, c2 = st.columns(2)
                
                with c1:
                    # Price distribution
                    fig = px.histogram(df, x="price_per_credit", nbins=10, title="Price Distribution ($/credit)",
                                       color_discrete_sequence=["#3b82f6"])
                    fig.update_layout(height=300, xaxis_title="Price ($)", yaxis_title="Count")
                    st.plotly_chart(fig, use_container_width=True)
                
                with c2:
                    # Verification standards
                    std_counts = df["verification"].value_counts().reset_index()
                    std_counts.columns = ["Standard", "Count"]
                    fig = px.pie(std_counts, values="Count", names="Standard", title="Verification Standards",
                                 hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
                    fig.update_layout(height=300, showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Country analysis
                country_data = df.groupby("country").agg({
                    "quantity": "sum",
                    "value": "sum",
                    "co2": "sum",
                }).reset_index()
                
                fig = px.bar(country_data, x="country", y=["quantity", "co2"],
                             title="Credits & CO₂ by Country", barmode="group",
                             labels={"value": "Credits", "co2": "CO₂ (kg)"})
                fig.update_layout(height=350, legend_title="Metric")
                st.plotly_chart(fig, use_container_width=True)
                
                # Price vs CO2 scatter
                fig = px.scatter(df, x="price_per_credit", y="co2_per_credit", size="quantity",
                                 color="type", title="Price vs CO₂ Efficiency",
                                 color_discrete_map={k: v["color"] for k, v in OFFSET_PROJECT_TYPES.items()})
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            # Recommendations
            st.subheader("💡 Recommendations")
            recommendations = []
            
            if stats["avg_price"] > 25:
                recommendations.append("💡 Your average credit price is above $25. Consider Cookstove or Reforestation projects for better value.")
            if stats["active_credits"] == 0 and stats["total_purchased"] > 0:
                recommendations.append("🔥 All your credits are retired! Time to purchase more to maintain your offset.")
            if len(credits) > 0:
                types = set(c["type"] for c in credits)
                if len(types) < 3:
                    recommendations.append("🎯 Diversify your portfolio across more project types for broader impact.")
            
            total_co2 = stats["total_co2_offset"] / 1000
            if total_co2 < 1:
                recommendations.append("🌍 You've offset less than 1 tonne of CO₂. Consider increasing your purchases.")
            elif total_co2 > 10:
                recommendations.append("🌟 Amazing! You've offset over 10 tonnes of CO₂. You're making a real difference!")
            
            if not recommendations:
                recommendations.append("✅ Your portfolio looks well-balanced! Keep up the great work.")
            
            for rec in recommendations:
                st.info(rec)
        else:
            st.info("No data yet. Purchase and retire credits to see analytics!")


# ─── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    render_offset_portfolio_hub()
