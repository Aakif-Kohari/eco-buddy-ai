"""
Carbon Offset Marketplace
Browse, purchase, and track verified carbon offset projects.
Monitor portfolio performance, retirement certificates, and impact verification.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import random

# ─── MOCK DATA ───────────────────────────────────────────────────────────────

OFFSET_PROJECTS = [
    {
        "id": "PROJ-001", "name": "Amazon Rainforest Conservation", "type": "Avoidance",
        "location": "Brazil", "standard": "Verra VCS", "price_per_ton": 18.50,
        "total_credits": 500000, "available": 342000, "vintage": 2026,
        "co_benefits": ["Biodiversity", "Indigenous Communities", "Water Protection"],
        "rating": 4.8, "reviews": 342, "verified": True, "featured": True,
        "description": "Protecting 120,000 hectares of primary Amazon rainforest from deforestation.",
        "annual_offset": 250000, "methodology": "REDD+", "registry": "Verra Registry",
        "image_url": "🌳"
    },
    {
        "id": "PROJ-002", "name": "Kenya Wind Energy Farm", "type": "Renewable Energy",
        "location": "Kenya", "standard": "Gold Standard", "price_per_ton": 22.00,
        "total_credits": 200000, "available": 156000, "vintage": 2026,
        "co_benefits": ["Rural Electrification", "Job Creation", "Healthcare Access"],
        "rating": 4.9, "reviews": 218, "verified": True, "featured": True,
        "description": "100MW wind farm powering 200,000 homes and replacing diesel generators.",
        "annual_offset": 180000, "methodology": "CDM", "registry": "Gold Standard Registry",
        "image_url": "💨"
    },
    {
        "id": "PROJ-003", "name": "Indian Solar Microgrids", "type": "Renewable Energy",
        "location": "India", "standard": "Verra VCS", "price_per_ton": 15.75,
        "total_credits": 150000, "available": 98000, "vintage": 2025,
        "co_benefits": ["Energy Access", "Women Empowerment", "Education"],
        "rating": 4.7, "reviews": 189, "verified": True, "featured": False,
        "description": "Solar microgrids serving 500+ rural villages across Rajasthan and Gujarat.",
        "annual_offset": 120000, "methodology": "ACM0002", "registry": "Verra Registry",
        "image_url": "☀️"
    },
    {
        "id": "PROJ-004", "name": "Colombia Mangrove Restoration", "type": "Blue Carbon",
        "location": "Colombia", "standard": "Plan Vivo", "price_per_ton": 28.00,
        "total_credits": 80000, "available": 45000, "vintage": 2026,
        "co_benefits": ["Coastal Protection", "Fisheries", "Carbon Sequestration"],
        "rating": 4.6, "reviews": 127, "verified": True, "featured": True,
        "description": "Restoring 2,000 hectares of degraded mangrove coastline.",
        "annual_offset": 65000, "methodology": "VM0033", "registry": "Plan Vivo Registry",
        "image_url": "🌊"
    },
    {
        "id": "PROJ-005", "name": "Ethiopian Cookstove Distribution", "type": "Community",
        "location": "Ethiopia", "standard": "Gold Standard", "price_per_ton": 12.50,
        "total_credits": 300000, "available": 210000, "vintage": 2026,
        "co_benefits": ["Health", "Gender Equity", "Indoor Air Quality"],
        "rating": 4.5, "reviews": 256, "verified": True, "featured": False,
        "description": "Distributing 100,000 clean cookstoves to reduce indoor air pollution.",
        "annual_offset": 200000, "methodology": "AMS-II.G", "registry": "Gold Standard Registry",
        "image_url": "🫕"
    },
    {
        "id": "PROJ-006", "name": "Indonesian Peatland Protection", "type": "Avoidance",
        "location": "Indonesia", "standard": "Verra VCS", "price_per_ton": 16.25,
        "total_credits": 400000, "available": 280000, "vintage": 2025,
        "co_benefits": ["Peatland Ecosystem", "Biodiversity", "Fire Prevention"],
        "rating": 4.4, "reviews": 165, "verified": True, "featured": False,
        "description": "Protecting 80,000 hectares of carbon-rich peatland from drainage.",
        "annual_offset": 350000, "methodology": "VM005", "registry": "Verra Registry",
        "image_url": "🌿"
    },
    {
        "id": "PROJ-007", "name": "Canadian Reforestation", "type": "Removal",
        "location": "Canada", "standard": "Plan Vivo", "price_per_ton": 24.00,
        "total_credits": 120000, "available": 78000, "vintage": 2026,
        "co_benefits": ["Forest Restoration", "Wildlife Habitat", "Water Quality"],
        "rating": 4.7, "reviews": 198, "verified": True, "featured": True,
        "description": "Replanting 5 million trees across degraded boreal forest lands.",
        "annual_offset": 95000, "methodology": "ARR 2019", "registry": "Plan Vivo Registry",
        "image_url": "🌲"
    },
    {
        "id": "PROJ-008", "name": "Nepal Biogas Program", "type": "Community",
        "location": "Nepal", "standard": "Gold Standard", "price_per_ton": 14.00,
        "total_credits": 100000, "available": 72000, "vintage": 2026,
        "co_benefits": ["Clean Energy", "Waste Management", "Rural Livelihoods"],
        "rating": 4.3, "reviews": 142, "verified": True, "featured": False,
        "description": "Installing 15,000 household biogas plants from agricultural waste.",
        "annual_offset": 85000, "methodology": "AMS-I.G", "registry": "Gold Standard Registry",
        "image_url": "♻️"
    }
]

MARKET_STATS = {
    "total_market_value": 2840000000,
    "avg_price_per_ton": 19.40,
    "price_change_30d": 8.2,
    "volume_30d": 4200000,
    "volume_change_30d": 12.5,
    "active_projects": 4280,
    "total_retired": 89200000,
    "retired_this_month": 3200000
}

PORTFOLIO = [
    {"project": "Amazon Rainforest Conservation", "credits_held": 50, "purchase_price": 17.25, "current_price": 18.50, "purchase_date": "2026-07-15"},
    {"project": "Kenya Wind Energy Farm", "credits_held": 35, "purchase_price": 20.00, "current_price": 22.00, "purchase_date": "2026-08-01"},
    {"project": "Colombia Mangrove Restoration", "credits_held": 20, "purchase_price": 26.50, "current_price": 28.00, "purchase_date": "2026-08-10"},
    {"project": "Canadian Reforestation", "credits_held": 40, "purchase_price": 22.00, "current_price": 24.00, "purchase_date": "2026-07-20"}
]

RETIREMENTS = [
    {"id": "RET-001", "project": "Amazon Rainforest Conservation", "credits": 25, "date": "2026-08-15", "beneficiary": "Anubhuti Corp", "certificate": "CERT-2026-0815-001"},
    {"id": "RET-002", "project": "Kenya Wind Energy Farm", "credits": 10, "date": "2026-08-20", "beneficiary": "Anubhuti Corp", "certificate": "CERT-2026-0820-002"},
    {"id": "RET-003", "project": "Canadian Reforestation", "credits": 15, "date": "2026-08-25", "beneficiary": "Personal Offset", "certificate": "CERT-2026-0825-003"}
]

PRICE_HISTORY = [
    {"month": "Mar", "avg_price": 15.20, "volume": 3800000},
    {"month": "Apr", "avg_price": 16.10, "volume": 3950000},
    {"month": "May", "avg_price": 17.30, "volume": 4100000},
    {"month": "Jun", "avg_price": 18.50, "volume": 4050000},
    {"month": "Jul", "avg_price": 19.00, "volume": 4180000},
    {"month": "Aug", "avg_price": 19.40, "volume": 4200000}
]

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────

def apply_theme():
    """Apply custom theme styling."""
    st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, rgba(16,185,129,0.08), rgba(99,102,241,0.08));
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #10b981, #6366f1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .project-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .verified-badge {
        background: rgba(16,185,129,0.15);
        color: #10b981;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .price-tag {
        font-size: 1.5rem;
        font-weight: 800;
        color: #10b981;
    }
    .streak-badge {
        background: linear-gradient(135deg, #f59e0b, #ef4444);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)


def render_project_card(project):
    """Render an individual project card."""
    available_pct = (project["available"] / project["total_credits"]) * 100
    stars = "⭐" * int(project["rating"])

    with st.container():
        cols = st.columns([1, 3, 1])
        with cols[0]:
            st.markdown(f"### {project['image_url']}")
            st.markdown(f"**{stars}** {project['rating']}")
        with cols[1]:
            st.markdown(f"#### {project['name']}")
            st.caption(f"📍 {project['location']} • {project['standard']} • {project['type']}")
            st.write(project['description'])
            tags = " ".join([f"`{b}`" for b in project["co_benefits"]])
            st.markdown(tags)
        with cols[2]:
            st.markdown(f"### ${project['price_per_ton']:.2f}")
            st.caption("per ton CO₂")
            st.progress(available_pct / 100)
            st.caption(f"{project['available']:,} / {project['total_credits']:,} available")
            st.caption(f"Vintage: {project['vintage']}")
            if project["verified"]:
                st.success("✅ Verified")
            if st.button(f"🛒 Purchase", key=f"buy_{project['id']}"):
                st.session_state.selected_project = project
                st.rerun()


def render_portfolio_chart():
    """Render portfolio allocation pie chart."""
    portfolio_data = pd.DataFrame([
        {"Project": p["project"], "Credits": p["credits_held"],
         "Value": p["credits_held"] * p["current_price"]}
        for p in PORTFOLIO
    ])

    fig = go.Figure(data=[go.Pie(
        labels=portfolio_data["Project"],
        values=portfolio_data["Credits"],
        hole=0.6,
        marker=dict(colors=["#10b981", "#6366f1", "#f59e0b", "#8b5cf6"]),
        textinfo="label+percent",
        textfont=dict(size=11)
    )])
    fig.update_layout(
        title="Portfolio Allocation",
        height=350,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8"),
        showlegend=True
    )
    return fig


def render_price_chart():
    """Render market price trend chart."""
    df = pd.DataFrame(PRICE_HISTORY)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Scatter(x=df["month"], y=df["avg_price"], name="Avg Price ($/ton)",
                   line=dict(color="#10b981", width=3), fill="tozeroy",
                   fillcolor="rgba(16,185,129,0.1)"),
        secondary_y=False
    )
    fig.add_trace(
        go.Bar(x=df["month"], y=df["volume"], name="Volume (tons)",
               marker_color="rgba(99,102,241,0.4)", yaxis="y2"),
        secondary_y=True
    )
    fig.update_layout(
        title="Market Price Trend (6 Months)",
        height=350,
        margin=dict(t=40, b=20, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8"),
        legend=dict(orientation="h", y=1.12)
    )
    fig.update_yaxes(title_text="Price ($/ton)", secondary_y=False, gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(title_text="Volume", secondary_y=True, showgrid=False)
    return fig


# ─── MAIN RENDER FUNCTION ────────────────────────────────────────────────────

def render_carbon_offset_marketplace():
    """Main render function for the Carbon Offset Marketplace."""
    apply_theme()

    # ─── HEADER ───────────────────────────────────────────────────────────
    st.markdown("# 🌍 Carbon Offset Marketplace")
    st.markdown("Browse, purchase, and track verified carbon offset projects from around the world.")

    # ─── TABS ─────────────────────────────────────────────────────────────
    tabs = st.tabs(["🏪 Browse Projects", "💼 My Portfolio", "📜 Retirement Certificates", "📊 Market Analytics", "🔍 Impact Verification"])

    # ─── TAB: BROWSE PROJECTS ─────────────────────────────────────────────
    with tabs[0]:
        # Market Overview
        cols = st.columns(4)
        with cols[0]:
            st.markdown('<div class="metric-card"><div class="metric-value">$19.40</div><small>Avg Price/ton</small></div>', unsafe_allow_html=True)
        with cols[1]:
            st.markdown('<div class="metric-card"><div class="metric-value">+8.2%</div><small>30d Price Change</small></div>', unsafe_allow_html=True)
        with cols[2]:
            st.markdown('<div class="metric-card"><div class="metric-value">4.2M</div><small>30d Volume</small></div>', unsafe_allow_html=True)
        with cols[3]:
            st.markdown('<div class="metric-card"><div class="metric-value">4,280</div><small>Active Projects</small></div>', unsafe_allow_html=True)

        st.markdown("---")

        # Filters
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            project_type = st.selectbox("Project Type", ["All", "Avoidance", "Renewable Energy", "Blue Carbon", "Community", "Removal"])
        with col2:
            standard = st.selectbox("Standard", ["All", "Verra VCS", "Gold Standard", "Plan Vivo"])
        with col3:
            location = st.selectbox("Region", ["All", "Americas", "Africa", "Asia", "Oceania"])
        with col4:
            sort_by = st.selectbox("Sort By", ["Featured", "Price: Low→High", "Price: High→Low", "Rating", "Availability"])

        st.markdown("---")

        # Filter projects
        filtered = OFFSET_PROJECTS
        if project_type != "All":
            filtered = [p for p in filtered if p["type"] == project_type]
        if standard != "All":
            filtered = [p for p in filtered if p["standard"] == standard]

        # Sort
        if sort_by == "Price: Low→High":
            filtered = sorted(filtered, key=lambda x: x["price_per_ton"])
        elif sort_by == "Price: High→Low":
            filtered = sorted(filtered, key=lambda x: x["price_per_ton"], reverse=True)
        elif sort_by == "Rating":
            filtered = sorted(filtered, key=lambda x: x["rating"], reverse=True)
        elif sort_by == "Featured":
            filtered = sorted(filtered, key=lambda x: x["featured"], reverse=True)

        # Render projects
        for project in filtered:
            render_project_card(project)
            st.markdown("---")

    # ─── TAB: MY PORTFOLIO ────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 💼 My Offset Portfolio")

        # Portfolio Summary
        total_credits = sum(p["credits_held"] for p in PORTFOLIO)
        total_value = sum(p["credits_held"] * p["current_price"] for p in PORTFOLIO)
        total_cost = sum(p["credits_held"] * p["purchase_price"] for p in PORTFOLIO)
        total_gain = total_value - total_cost
        gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0

        cols = st.columns(5)
        with cols[0]:
            st.metric("Total Credits", f"{total_credits}")
        with cols[1]:
            st.metric("Portfolio Value", f"${total_value:,.2f}")
        with cols[2]:
            st.metric("Total Cost", f"${total_cost:,.2f}")
        with cols[3]:
            st.metric("Total Gain", f"${total_gain:,.2f}", f"{gain_pct:+.1f}%")
        with cols[4]:
            st.metric("Avg Cost/Ton", f"${total_cost/total_credits:.2f}")

        st.markdown("---")

        col1, col2 = st.columns([2, 1])
        with col1:
            # Portfolio value over time (simulated)
            dates = pd.date_range("2026-07-01", periods=58)
            values = [total_cost]
            for i in range(1, 58):
                values.append(values[-1] * (1 + random.uniform(-0.01, 0.015)))
            values = [v * (total_value / values[-1]) for v in values]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates, y=values, mode="lines",
                line=dict(color="#10b981", width=2.5),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
                name="Portfolio Value"
            ))
            fig.update_layout(
                title="Portfolio Value Trend",
                height=300,
                margin=dict(t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.plotly_chart(render_portfolio_chart(), use_container_width=True)

        # Holdings Table
        st.markdown("#### 📊 Holdings")
        holdings_df = pd.DataFrame([{
            "Project": p["project"],
            "Credits": p["credits_held"],
            "Purchase Price": f"${p['purchase_price']:.2f}",
            "Current Price": f"${p['current_price']:.2f}",
            "Value": f"${p['credits_held'] * p['current_price']:,.2f}",
            "Gain/Loss": f"${p['credits_held'] * (p['current_price'] - p['purchase_price']):+,.2f}",
            "Purchase Date": p["purchase_date"]
        } for p in PORTFOLIO])
        st.dataframe(holdings_df, use_container_width=True, hide_index=True)

    # ─── TAB: RETIREMENT CERTIFICATES ─────────────────────────────────────
    with tabs[2]:
        st.markdown("### 📜 Retirement Certificates")
        st.markdown("Your retired carbon credits with official certificates of offset.")

        for ret in RETIREMENTS:
            with st.container():
                cols = st.columns([1, 3, 1])
                with cols[0]:
                    st.markdown("### 🏆")
                with cols[1]:
                    st.markdown(f"**{ret['project']}**")
                    st.caption(f"Retired: {ret['date']} • Beneficiary: {ret['beneficiary']}")
                    st.caption(f"Certificate: `{ret['certificate']}`")
                with cols[2]:
                    st.markdown(f"### {ret['credits']} tons")
                    st.caption("CO₂ offset")
                st.markdown("---")

        # Summary
        total_retired = sum(r["credits"] for r in RETIREMENTS)
        st.info(f"🎉 You've retired **{total_retired} tons of CO₂** — equivalent to taking **{total_retired * 2.3:.0f} cars off the road for a year**!")

    # ─── TAB: MARKET ANALYTICS ────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📊 Market Analytics")

        col1, col2 = st.columns([2, 1])
        with col1:
            st.plotly_chart(render_price_chart(), use_container_width=True)
        with col2:
            st.markdown("#### Market Statistics")
            stats = [
                ("Total Market Value", f"${MARKET_STATS['total_market_value']/1e9:.2f}B"),
                ("Avg Price/Ton", f"${MARKET_STATS['avg_price_per_ton']:.2f}"),
                ("30d Price Change", f"+{MARKET_STATS['price_change_30d']}%"),
                ("30d Volume", f"{MARKET_STATS['volume_30d']/1e6:.1f}M tons"),
                ("Volume Change", f"+{MARKET_STATS['volume_change_30d']}%"),
                ("Active Projects", f"{MARKET_STATS['active_projects']:,}"),
                ("Total Retired", f"{MARKET_STATS['total_retired']/1e6:.1f}M tons"),
                ("Retired This Month", f"{MARKET_STATS['retired_this_month']/1e6:.1f}M tons")
            ]
            for label, value in stats:
                st.markdown(f"**{label}:** {value}")

        st.markdown("---")

        # Price by type
        type_prices = pd.DataFrame([{"Type": p["type"], "Price": p["price_per_ton"]} for p in OFFSET_PROJECTS])
        fig = px.bar(type_prices, x="Type", y="Price", color="Type",
                     color_discrete_map={"Avoidance": "#10b981", "Renewable Energy": "#6366f1", "Blue Carbon": "#3b82f6", "Community": "#f59e0b", "Removal": "#8b5cf6"},
                     title="Average Price by Project Type")
        fig.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"), showlegend=False)
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")
        st.plotly_chart(fig, use_container_width=True)

    # ─── TAB: IMPACT VERIFICATION ─────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🔍 Impact Verification")
        st.markdown("Verify the authenticity and impact of offset projects.")

        selected = st.selectbox("Select Project to Verify", [p["name"] for p in OFFSET_PROJECTS])
        project = next((p for p in OFFSET_PROJECTS if p["name"] == selected), None)

        if project:
            cols = st.columns(2)
            with cols[0]:
                st.markdown("#### 📋 Verification Details")
                st.markdown(f"- **Project ID:** `{project['id']}`")
                st.markdown(f"- **Standard:** {project['standard']}")
                st.markdown(f"- **Registry:** {project['registry']}")
                st.markdown(f"- **Methodology:** {project['methodology']}")
                st.markdown(f"- **Vintage:** {project['vintage']}")
                st.markdown(f"- **Annual Offset:** {project['annual_offset']:,} tons CO₂")

            with cols[1]:
                st.markdown("#### ✅ Verification Checks")
                checks = [
                    ("Registry Status", "✅ Active & Verified"),
                    ("Methodology Approval", "✅ Approved by {0}".format(project["standard"])),
                    ("Third-Party Audit", "✅ Completed Q2 2026"),
                    ("Permanence Guarantee", "✅ 25-year monitoring"),
                    ("Leakage Assessment", "✅ No significant leakage"),
                    ("Co-Benefit Validation", "✅ Verified by {0}".format(project["standard"]))
                ]
                for label, status in checks:
                    st.markdown(f"- **{label}:** {status}")

            st.markdown("---")
            st.markdown(f"#### 📊 Impact Summary")
            cols = st.columns(4)
            with cols[0]:
                st.metric("Total Offset", f"{project['total_credits']:,} tons")
            with cols[1]:
                st.metric("Annual Offset", f"{project['annual_offset']:,} tons")
            with cols[2]:
                st.metric("Co-Benefits", f"{len(project['co_benefits'])}")
            with cols[3]:
                st.metric("Rating", f"{'⭐' * int(project['rating'])} {project['rating']}")


# ─── STREAMLIT PAGE ENTRY POINT ──────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(page_title="Carbon Offset Marketplace", page_icon="🌍", layout="wide")
    from styles.theme import apply_theme as apply_app_theme
    apply_app_theme()
    render_carbon_offset_marketplace()

