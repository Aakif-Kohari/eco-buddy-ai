"""
pages/Eco_Fashion_Impact.py
---------------------------
Streamlit page: Eco Fashion Impact Tracker.

Track the environmental impact of your wardrobe, compare fabric
sustainability, explore supply chain transparency, and get recommendations
for eco-friendly fashion choices.
"""

import math
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Eco Fashion Impact Tracker",
    page_icon="👗",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Fabric database
# ---------------------------------------------------------------------------

FABRIC_DATA = {
    "Organic Cotton": {
        "icon": "🌿", "category": "Natural",
        "co2_per_kg": 5.5, "water_per_kg": 7000, "energy_per_kg": 60,
        "biodegradable": True, "recyclable": True,
        "score": 72, "color": "#28a745",
        "pros": ["Biodegradable", "Low chemical use", "Soft and breathable"],
        "cons": ["High water usage", "Lower yield than conventional"],
        "decomposition": "1-5 months",
    },
    "Conventional Cotton": {
        "icon": "🧵", "category": "Natural",
        "co2_per_kg": 8.0, "water_per_kg": 10000, "energy_per_kg": 65,
        "biodegradable": True, "recyclable": True,
        "score": 45, "color": "#fd7e14",
        "pros": ["Widely available", "Biodegradable"],
        "cons": ["Heavy pesticide use", "Extremely water-intensive"],
        "decomposition": "1-5 months",
    },
    "Hemp": {
        "icon": "🌱", "category": "Natural",
        "co2_per_kg": 3.5, "water_per_kg": 2700, "energy_per_kg": 40,
        "biodegradable": True, "recyclable": True,
        "score": 85, "color": "#20c997",
        "pros": ["Very low water", "Natural pest resistance", "Strengthens with wash"],
        "cons": ["Rough texture", "Limited color options"],
        "decomposition": "2-4 months",
    },
    "Linen (Flax)": {
        "icon": "🌾", "category": "Natural",
        "co2_per_kg": 4.0, "water_per_kg": 3500, "energy_per_kg": 45,
        "biodegradable": True, "recyclable": True,
        "score": 82, "color": "#20c997",
        "pros": ["Low water and pesticide", "Very durable", "Naturally antibacterial"],
        "cons": ["Wrinkles easily", "Higher cost"],
        "decomposition": "2-4 months",
    },
    "Recycled Polyester": {
        "icon": "♻️", "category": "Recycled",
        "co2_per_kg": 3.0, "water_per_kg": 20, "energy_per_kg": 35,
        "biodegradable": False, "recyclable": True,
        "score": 68, "color": "#4a90d9",
        "pros": ["Diverts plastic from landfill", "Low water", "Durable"],
        "cons": ["Sheds microplastics", "Not biodegradable"],
        "decomposition": "200+ years",
    },
    "Conventional Polyester": {
        "icon": "🛢️", "category": "Synthetic",
        "co2_per_kg": 9.5, "water_per_kg": 60, "energy_per_kg": 125,
        "biodegradable": False, "recyclable": True,
        "score": 25, "color": "#dc3545",
        "pros": ["Cheap", "Durable", "Quick-dry"],
        "cons": ["Petroleum-based", "Microplastics", "Not breathable"],
        "decomposition": "200+ years",
    },
    "Tencel (Lyocell)": {
        "icon": "🌳", "category": "Semi-Synthetic",
        "co2_per_kg": 2.5, "water_per_kg": 500, "energy_per_kg": 25,
        "biodegradable": True, "recyclable": True,
        "score": 90, "color": "#20c997",
        "pros": ["Closed-loop process", "Biodegradable", "Silky feel"],
        "cons": ["Higher cost", "Limited availability"],
        "decomposition": "1-2 months",
    },
    "Nylon (Polyamide)": {
        "icon": "⛽", "category": "Synthetic",
        "co2_per_kg": 12.0, "water_per_kg": 80, "energy_per_kg": 150,
        "biodegradable": False, "recyclable": True,
        "score": 18, "color": "#dc3545",
        "pros": ["Very strong", "Elastic", "Abrasion resistant"],
        "cons": ["Petroleum-based", "High energy to produce", "Microplastics"],
        "decomposition": "30-40 years",
    },
    "Wool": {
        "icon": "🐑", "category": "Natural",
        "co2_per_kg": 17.0, "water_per_kg": 15000, "energy_per_kg": 100,
        "biodegradable": True, "recyclable": True,
        "score": 35, "color": "#fd7e14",
        "pros": ["Biodegradable", "Naturally flame-resistant", "Warm"],
        "cons": ["High methane from sheep", "Very water-intensive", "Ethical concerns"],
        "decomposition": "1-5 years",
    },
    "Bamboo Viscose": {
        "icon": "🎋", "category": "Semi-Synthetic",
        "co2_per_kg": 4.5, "water_per_kg": 3000, "energy_per_kg": 50,
        "biodegradable": True, "recyclable": False,
        "score": 58, "color": "#ffc107",
        "pros": ["Fast-growing plant", "Soft", "Antibacterial"],
        "cons": ["Chemical-intensive process", "Greenwashing concerns"],
        "decomposition": "3-6 months",
    },
    "Recycled Nylon": {
        "icon": "🔄", "category": "Recycled",
        "co2_per_kg": 5.0, "water_per_kg": 30, "energy_per_kg": 55,
        "biodegradable": False, "recyclable": True,
        "score": 65, "color": "#4a90d9",
        "pros": ["Diverts ocean waste", "Lower virgin production impact"],
        "cons": ["Still sheds microplastics", "Energy-intensive recycling"],
        "decomposition": "30-40 years",
    },
    "Econyl (Recycled Nylon)": {
        "icon": "🌊", "category": "Recycled",
        "co2_per_kg": 4.2, "water_per_kg": 25, "energy_per_kg": 48,
        "biodegradable": False, "recyclable": True,
        "score": 70, "color": "#4a90d9",
        "pros": ["Ocean waste cleanup", "Infinite recyclability", "High quality"],
        "cons": ["Still synthetic", "Microplastic shedding"],
        "decomposition": "30-40 years",
    },
}

# ---------------------------------------------------------------------------
# Item lifecycle stages
# ---------------------------------------------------------------------------

LIFECYCLE_STAGES = [
    {"stage": "Raw Material", "icon": "🌱", "impact_pct": 15, "description": "Growing/harvesting raw materials"},
    {"stage": "Processing", "icon": "🏭", "impact_pct": 25, "description": "Spinning, dyeing, weaving"},
    {"stage": "Manufacturing", "icon": "✂️", "impact_pct": 20, "description": "Cutting, sewing, finishing"},
    {"stage": "Transportation", "icon": "🚢", "impact_pct": 10, "description": "Shipping from factory to store"},
    {"stage": "Retail", "icon": "🏪", "impact_pct": 5, "description": "Store operations, hangers, tags"},
    {"stage": "Use Phase", "icon": "👕", "impact_pct": 15, "description": "Washing, drying, ironing"},
    {"stage": "End of Life", "icon": "🗑️", "impact_pct": 10, "description": "Disposal, landfill, recycling"},
]


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _generate_mock_wardrobe() -> list[dict[str, Any]]:
    """Generate mock wardrobe items."""
    import random
    random.seed(42)

    items = [
        {"name": "White T-Shirt", "fabric": "Organic Cotton", "brand": "Patagonia", "price": 45, "age_months": 18, "wears": 85, "category": "Top"},
        {"name": "Denim Jeans", "fabric": "Conventional Cotton", "brand": "Levi's", "price": 80, "age_months": 24, "wears": 150, "category": "Bottom"},
        {"name": "Running Shoes", "fabric": "Recycled Polyester", "brand": "Adidas", "price": 120, "age_months": 12, "wears": 200, "category": "Footwear"},
        {"name": "Wool Sweater", "fabric": "Wool", "brand": "Uniqlo", "price": 60, "age_months": 36, "wears": 60, "category": "Top"},
        {"name": "Summer Dress", "fabric": "Tencel (Lyocell)", "brand": "Eileen Fisher", "price": 150, "age_months": 8, "wears": 30, "category": "Dress"},
        {"name": "Leggings", "fabric": "Conventional Polyester", "brand": "Nike", "price": 70, "age_months": 10, "wears": 120, "category": "Bottom"},
        {"name": "Hemp Pants", "fabric": "Hemp", "brand": "Prana", "price": 85, "age_months": 14, "wears": 45, "category": "Bottom"},
        {"name": "Linen Shirt", "fabric": "Linen (Flax)", "brand": "Everlane", "price": 68, "age_months": 20, "wears": 55, "category": "Top"},
        {"name": "Rain Jacket", "fabric": "Recycled Nylon", "brand": "Patagonia", "price": 200, "age_months": 30, "wears": 90, "category": "Outerwear"},
        {"name": "Bamboo Underwear", "fabric": "Bamboo Viscose", "brand": "Boody", "price": 25, "age_months": 6, "wears": 50, "category": "Underwear"},
        {"name": "Sports Bra", "fabric": "Nylon (Polyamide)", "brand": "Lululemon", "price": 65, "age_months": 14, "wears": 100, "category": "Underwear"},
        {"name": "Cotton Hoodie", "fabric": "Conventional Cotton", "brand": "H&M", "price": 35, "age_months": 16, "wears": 70, "category": "Top"},
        {"name": "Econyl Swimsuit", "fabric": "Econyl (Recycled Nylon)", "brand": "Girlfriend Collective", "price": 78, "age_months": 10, "wears": 25, "category": "Swimwear"},
        {"name": "Flannel Shirt", "fabric": "Organic Cotton", "brand": "Pact", "price": 55, "age_months": 22, "wears": 95, "category": "Top"},
        {"name": "Bamboo Socks (5-pack)", "fabric": "Bamboo Viscose", "brand": "Boody", "price": 20, "age_months": 8, "wears": 60, "category": "Accessories"},
    ]

    # Add computed fields
    for item in items:
        fabric = FABRIC_DATA.get(item["fabric"], FABRIC_DATA["Conventional Cotton"])
        # Rough weight estimate by category
        weight_map = {"Top": 0.3, "Bottom": 0.6, "Dress": 0.5, "Footwear": 0.8, "Outerwear": 0.9, "Underwear": 0.1, "Swimwear": 0.15, "Accessories": 0.1}
        weight = weight_map.get(item["category"], 0.3)
        item["weight_kg"] = weight
        item["co2_kg"] = round(weight * fabric["co2_per_kg"], 2)
        item["water_liters"] = round(weight * fabric["water_per_kg"], 0)
        item["sustainability_score"] = fabric["score"]
        item["cost_per_wear"] = round(item["price"] / max(item["wears"], 1), 2)
        item["carbon_per_wear"] = round(item["co2_kg"] / max(item["wears"], 1), 4)

    return items


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_overview(wardrobe: list[dict]):
    """Render wardrobe overview KPIs."""
    st.subheader("📊 Wardrobe Impact Overview")

    total_items = len(wardrobe)
    total_co2 = sum(i["co2_kg"] for i in wardrobe)
    total_water = sum(i["water_liters"] for i in wardrobe)
    total_cost = sum(i["price"] for i in wardrobe)
    total_wears = sum(i["wears"] for i in wardrobe)
    avg_score = sum(i["sustainability_score"] for i in wardrobe) / total_items if total_items else 0
    avg_cost_per_wear = sum(i["cost_per_wear"] for i in wardrobe) / total_items if total_items else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Items", total_items)
    c2.metric("CO₂", f"{total_co2:.1f} kg")
    c3.metric("Water", f"{total_water:,.0f} L")
    c4.metric("💰 Total Cost", f"${total_cost:,.0f}")
    c5.metric("Avg Score", f"{avg_score:.0f}/100")
    c6.metric("Cost/Wear", f"${avg_cost_per_wear:.2f}")

    # Equivalent impact
    driving_km = total_co2 / 0.21
    showers = total_water / 65
    st.markdown(
        f"Your **{total_items}** wardrobe items have a combined footprint of **{total_co2:.1f} kg CO₂** "
        f"and **{total_water:,.0f} liters of water**. That's equivalent to driving **{driving_km:,.0f} km** "
        f"or **{showers:,.0f} showers**. Average sustainability score: **{avg_score:.0f}/100**."
    )


def _render_fabric_comparison():
    """Render fabric sustainability comparison."""
    st.subheader("🧵 Fabric Sustainability")

    # Score bars
    st.markdown("**Sustainability Scores:**")
    sorted_fabrics = sorted(FABRIC_DATA.items(), key=lambda x: x[1]["score"], reverse=True)
    for name, data in sorted_fabrics:
        score = data["score"]
        color = data["color"]
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:4px 0">'
            f'<span style="width:170px;font-size:0.85em">{data["icon"]} {name}</span>'
            f'<div style="width:40%;background:#1e1e2e;border-radius:4px;height:16px">'
            f'<div style="width:{score}%;background:{color};border-radius:4px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em;font-weight:600;color:{color}">{score}/100</span></div>',
            unsafe_allow_html=True,
        )

    # Detailed comparison table
    st.markdown("**Detailed Comparison:**")
    rows = []
    for name, data in sorted_fabrics:
        rows.append({
            "Fabric": f"{data['icon']} {name}",
            "Score": data["score"],
            "CO₂/kg": f"{data['co2_per_kg']} kg",
            "Water/kg": f"{data['water_per_kg']:,} L",
            "Energy/kg": f"{data['energy_per_kg']} MJ",
            "Biodegradable": "✅" if data["biodegradable"] else "❌",
            "Recyclable": "✅" if data["recyclable"] else "❌",
            "Decomposition": data["decomposition"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Detail cards
    with st.expander("🔍 View Fabric Details", expanded=False):
        for name, data in sorted_fabrics:
            st.markdown(
                f'<div style="border-left:4px solid {data["color"]};padding:8px 12px;margin:6px 0;background:#f8f9fa;border-radius:4px">'
                f'<strong>{data["icon"]} {name}</strong> ({data["category"]}) — Score: {data["score"]}/100<br/>'
                f'<span style="color:#28a745">✅ {", ".join(data["pros"])}</span><br/>'
                f'<span style="color:#dc3545">❌ {", ".join(data["cons"])}</span></div>',
                unsafe_allow_html=True,
            )


def _render_lifecycle_analysis():
    """Render fashion item lifecycle impact breakdown."""
    st.subheader("🔄 Lifecycle Impact")
    st.markdown("Environmental impact at each stage of a garment's life:")

    max_impact = max(s["impact_pct"] for s in LIFECYCLE_STAGES)
    for stage in LIFECYCLE_STAGES:
        pct = stage["impact_pct"]
        color = "#dc3545" if pct >= 20 else "#fd7e14" if pct >= 15 else "#ffc107" if pct >= 10 else "#28a745"
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:5px 0">'
            f'<span style="width:160px;font-size:0.88em">{stage["icon"]} {stage["stage"]}</span>'
            f'<div style="width:50%;background:#1e1e2e;border-radius:4px;height:18px">'
            f'<div style="width:{pct / max_impact * 100:.0f}%;background:{color};border-radius:4px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{pct}% — {stage["description"]}</span></div>',
            unsafe_allow_html=True,
        )

    st.info(
        "💡 **Tip:** The Use Phase (washing/drying) contributes 15% of a garment's lifetime impact. "
        "Wash in cold water, air dry, and wear items more times to reduce this significantly."
    )


def _render_wardrobe_analysis(wardrobe: list[dict]):
    """Render per-item wardrobe impact analysis."""
    st.subheader("👗 Wardrobe Items")

    # Category filter
    categories = list(set(i["category"] for i in wardrobe))
    cat_filter = st.multiselect("Filter by Category", categories, default=categories, key="wardrobe_cat")

    filtered = [i for i in wardrobe if i["category"] in cat_filter]
    filtered.sort(key=lambda x: x["co2_kg"], reverse=True)

    for item in filtered:
        fabric = FABRIC_DATA.get(item["fabric"], {})
        score = item["sustainability_score"]
        color = fabric.get("color", "#666")

        with st.expander(
            f"{fabric.get('icon', '👕')} **{item['name']}** — {item['fabric']} | "
            f"Score: {score}/100 | CO₂: {item['co2_kg']} kg",
            expanded=False,
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Brand", item["brand"])
            c2.metric("Price", f"${item['price']}")
            c3.metric("Cost/Wear", f"${item['cost_per_wear']:.2f}")
            c4.metric("Wears", item["wears"])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("CO₂", f"{item['co2_kg']} kg")
            c2.metric("Water", f"{item['water_liters']:,.0f} L")
            c3.metric("Carbon/Wear", f"{item['carbon_per_wear']:.4f} kg")
            c4.metric("Age", f"{item['age_months']} months")

            # Sustainability score bar
            st.markdown(
                f'<div style="background:#1e1e2e;border-radius:4px;height:12px;margin:8px 0">'
                f'<div style="width:{score}%;background:{color};border-radius:4px;height:100%"></div></div>'
                f'<span style="font-size:0.82em;color:{color}">{score}/100 sustainability</span>',
                unsafe_allow_html=True,
            )

            # Wear recommendation
            if item["cost_per_wear"] < 1:
                st.success(f"✅ Great value at ${item['cost_per_wear']:.2f} per wear! Keep wearing it.")
            elif item["cost_per_wear"] > 5:
                st.warning(f"⚠️ High cost per wear (${item['cost_per_wear']:.2f}). Consider wearing more or donating.")


def _render_brand_ranking(wardrobe: list[dict]):
    """Render brand sustainability ranking."""
    st.subheader("🏷️ Brand Ranking")

    brand_stats: dict[str, dict] = {}
    for item in wardrobe:
        brand = item["brand"]
        if brand not in brand_stats:
            brand_stats[brand] = {"items": 0, "total_co2": 0, "total_water": 0, "total_cost": 0, "scores": []}
        brand_stats[brand]["items"] += 1
        brand_stats[brand]["total_co2"] += item["co2_kg"]
        brand_stats[brand]["total_water"] += item["water_liters"]
        brand_stats[brand]["total_cost"] += item["price"]
        brand_stats[brand]["scores"].append(item["sustainability_score"])

    rows = []
    for brand, stats in sorted(brand_stats.items(), key=lambda x: sum(x[1]["scores"]) / len(x[1]["scores"]), reverse=True):
        avg_score = sum(stats["scores"]) / len(stats["scores"])
        rows.append({
            "Brand": brand,
            "Items": stats["items"],
            "Total CO₂": f"{stats['total_co2']:.1f} kg",
            "Total Water": f"{stats['total_water']:,.0f} L",
            "Total Cost": f"${stats['total_cost']}",
            "Avg Score": f"{avg_score:.0f}/100",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Score bars
    st.markdown("**Brand Sustainability Scores:**")
    for brand, stats in sorted(brand_stats.items(), key=lambda x: sum(x[1]["scores"]) / len(x[1]["scores"]), reverse=True):
        avg_score = sum(stats["scores"]) / len(stats["scores"])
        color = "#28a745" if avg_score >= 70 else "#ffc107" if avg_score >= 50 else "#dc3545"
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:3px 0">'
            f'<span style="width:150px;font-size:0.85em;font-weight:600">{brand}</span>'
            f'<div style="width:35%;background:#1e1e2e;border-radius:3px;height:14px">'
            f'<div style="width:{avg_score}%;background:{color};border-radius:3px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{avg_score:.0f}/100 ({stats["items"]} items)</span></div>',
            unsafe_allow_html=True,
        )


def _render_sustainability_tips():
    """Render eco-fashion tips and recommendations."""
    st.subheader("💡 Sustainable Fashion Tips")

    tips = [
        {"title": "🛒 Buy Less, Choose Well", "text": "Invest in quality pieces that last. One well-made item beats five cheap ones.", "impact": "Reduces consumption by 50%"},
        {"title": "♻️ Choose Recycled Fabrics", "text": "Recycled polyester and nylon use 50-80% less energy than virgin production.", "impact": "Saves 3-7 kg CO₂ per garment"},
        {"title": "🌿 Opt for Natural Fibers", "text": "Hemp, linen, and organic cotton are biodegradable and require fewer chemicals.", "impact": "60% less water than conventional cotton"},
        {"title": "🧺 Wash Cold, Air Dry", "text": "80% of a garment's lifetime energy goes to washing. Cold water and air drying save massively.", "impact": "Reduces use-phase emissions by 70%"},
        {"title": "🔄 Extend Garment Life", "text": "Wear each item 30+ times before considering replacement. Repair rather than discard.", "impact": "Each extra 9 months reduces footprint by 20-30%"},
        {"title": "🏪 Buy Secondhand", "text": "Thrift stores, consignment, and online resale reduce demand for new production.", "impact": "Zero new manufacturing impact"},
        {"title": "🏷️ Check Certifications", "text": "Look for GOTS, OEKO-TEX, B Corp, Fair Trade, and Bluesign labels.", "impact": "Ensures verified sustainability standards"},
        {"title": "🗑️ Recycle When Done", "text": "Donate wearable items. Use textile recycling for worn-out garments.", "impact": "Diverts from landfill"},
    ]

    for tip in tips:
        st.markdown(
            f'<div style="border:1px solid #333;border-radius:8px;padding:12px;margin:8px 0;background:#f8f9fa">'
            f'<strong style="color:#28a745">{tip["title"]}</strong><br/>'
            f'{tip["text"]}<br/>'
            f'<span style="color:#4a90d9;font-size:0.85em">📈 Impact: {tip["impact"]}</span></div>',
            unsafe_allow_html=True,
        )

    # Certifications guide
    st.markdown("---")
    st.subheader("🏷️ Certification Guide")
    certs = [
        {"name": "GOTS", "desc": "Global Organic Textile Standard — organic fibers, fair labor", "icon": "🌿"},
        {"name": "OEKO-TEX", "desc": "Tested for harmful substances", "icon": "🔬"},
        {"name": "Fair Trade", "desc": "Fair wages and safe working conditions", "icon": "🤝"},
        {"name": "B Corp", "desc": "Meets high standards of social and environmental performance", "icon": "🅱️"},
        {"name": "Bluesign", "desc": "Sustainable textile production", "icon": "🔵"},
        {"name": "Cradle to Cradle", "desc": "Designed for circular economy", "icon": "♻️"},
    ]
    for cert in certs:
        st.markdown(f"- {cert['icon']} **{cert['name']}**: {cert['desc']}")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def render_eco_fashion_impact():
    """Render the Eco Fashion Impact Tracker page."""
    st.title("👗 Eco Fashion Impact Tracker")
    st.markdown(
        "Track your wardrobe's environmental impact, compare fabrics, and discover sustainable fashion choices."
    )

    wardrobe = _generate_mock_wardrobe()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        show_overview = st.checkbox("Overview", True)
        show_fabrics = st.checkbox("Fabric Comparison", True)
        show_lifecycle = st.checkbox("Lifecycle Impact", True)
        show_wardrobe = st.checkbox("Wardrobe Analysis", True)
        show_brands = st.checkbox("Brand Ranking", True)
        show_tips = st.checkbox("Sustainable Tips", True)

    if show_overview:
        _render_overview(wardrobe)

    if show_fabrics:
        st.markdown("---")
        _render_fabric_comparison()

    if show_lifecycle:
        st.markdown("---")
        _render_lifecycle_analysis()

    if show_wardrobe:
        st.markdown("---")
        _render_wardrobe_analysis(wardrobe)

    if show_brands:
        st.markdown("---")
        _render_brand_ranking(wardrobe)

    if show_tips:
        st.markdown("---")
        _render_sustainability_tips()

    st.markdown("---")
    st.caption(
        f"Eco Fashion Impact Tracker | {len(wardrobe)} wardrobe items | {len(FABRIC_DATA)} fabrics | "
        f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )


# Entry point
if __name__ == "__main__" or True:
    render_eco_fashion_impact()
