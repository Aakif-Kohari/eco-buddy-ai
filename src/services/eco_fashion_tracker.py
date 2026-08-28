"""
Eco Fashion Impact Tracker
==========================
Track fashion sustainability: brand ratings, supply chain transparency,
textile waste, ethical shopping, and sustainable alternatives.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# ─── Brand Database ───────────────────────────────────────────────────────
BRANDS = [
    {"name": "Patagonia", "rating": 92, "category": "Outdoor", "origin": "USA", "founded": 1973,
     "sustainability_score": 95, "ethics_score": 90, "transparency_score": 94, "carbon_score": 88,
     "certifications": ["B Corp", "Fair Trade", "bluesign", "1% for the Planet"],
     "supply_chain": {"raw_materials": "Recycled Polyester, Organic Cotton", "manufacturing": "Fair Trade Certified",
                      "distribution": "Carbon-neutral shipping", "end_of_life": "Worn Wear program"},
     "materials": {"organic_cotton": 35, "recycled_polyester": 40, "hemp": 10, "nylon_recycled": 15},
     "price_range": "$$$", "animal_friendly": True, "vegan_options": True,
     "score_history": [78, 82, 85, 88, 90, 92]},
    {"name": "Everlane", "rating": 78, "category": "Basics", "origin": "USA", "founded": 2010,
     "sustainability_score": 72, "ethics_score": 85, "transparency_score": 90, "carbon_score": 65,
     "certifications": ["Fair Trade", "OEKO-TEX"],
     "supply_chain": {"raw_materials": "Organic Cotton, Recycled Cashmere", "manufacturing": "Factories audited annually",
                      "distribution": "Plastic-free packaging", "end_of_life": "Donation program"},
     "materials": {"organic_cotton": 50, "recycled_cashmere": 15, "tencel": 20, "recycled_nylon": 15},
     "price_range": "$$", "animal_friendly": False, "vegan_options": True,
     "score_history": [60, 65, 70, 72, 75, 78]},
    {"name": "H&M Conscious", "rating": 55, "category": "Fast Fashion", "origin": "Sweden", "founded": 1947,
     "sustainability_score": 50, "ethics_score": 55, "transparency_score": 60, "carbon_score": 45,
     "certifications": ["OEKO-TEX", "Better Cotton Initiative"],
     "supply_chain": {"raw_materials": "Mixed — 35% sustainable materials", "manufacturing": "1,200+ suppliers",
                      "distribution": "Optimizing logistics", "end_of_life": "Garment collecting program"},
     "materials": {"organic_cotton": 15, "recycled_polyester": 12, "conventional_cotton": 38, "polyester": 35},
     "price_range": "$", "animal_friendly": False, "vegan_options": False,
     "score_history": [35, 40, 42, 45, 50, 55]},
    {"name": "Stella McCartney", "rating": 95, "category": "Luxury", "origin": "UK", "founded": 2001,
     "sustainability_score": 96, "ethics_score": 92, "transparency_score": 88, "carbon_score": 94,
     "certifications": ["B Corp", "Cradle to Cradle", "Fur-Free"],
     "supply_chain": {"raw_materials": "Vegetarian leather, Organic cotton", "manufacturing": "European workshops",
                      "distribution": "Carbon offset programs", "end_of_life": "Circular fashion initiative"},
     "materials": {"vegetarian_leather": 30, "organic_cotton": 25, "recycled_cashmere": 20, "eco_silk": 15, "hemp": 10},
     "price_range": "$$$$", "animal_friendly": True, "vegan_options": True,
     "score_history": [85, 88, 90, 92, 94, 95]},
    {"name": "Shein", "rating": 18, "category": "Ultra Fast Fashion", "origin": "China", "founded": 2008,
     "sustainability_score": 12, "ethics_score": 15, "transparency_score": 10, "carbon_score": 20,
     "certifications": [],
     "supply_chain": {"raw_materials": "Conventional materials, unknown origins", "manufacturing": "Opaque supply chain",
                      "distribution": "Air freight dominant", "end_of_life": "No program"},
     "materials": {"polyester": 55, "conventional_cotton": 25, "nylon": 15, "spandex": 5},
     "price_range": "$", "animal_friendly": False, "vegan_options": False,
     "score_history": [10, 12, 14, 15, 16, 18]},
    {"name": "Eileen Fisher", "rating": 88, "category": "Womenswear", "origin": "USA", "founded": 1984,
     "sustainability_score": 85, "ethics_score": 90, "transparency_score": 92, "carbon_score": 82,
     "certifications": ["B Corp", "Fair Trade", "bluesign"],
     "supply_chain": {"raw_materials": "Organic linen, Tencel, Recycled wool", "manufacturing": "SA8000 certified",
                      "distribution": "Green logistics", "end_of_life": "Renew program — take back & remake"},
     "materials": {"organic_linens": 30, "tencel": 25, "recycled_wool": 25, "organic_cotton": 20},
     "price_range": "$$$", "animal_friendly": False, "vegan_options": False,
     "score_history": [70, 75, 78, 82, 85, 88]},
    {"name": "Reformation", "rating": 82, "category": "Trendy", "origin": "USA", "founded": 2009,
     "sustainability_score": 80, "ethics_score": 78, "transparency_score": 85, "carbon_score": 82,
     "certifications": ["Climate Neutral", "OEKO-TEX"],
     "supply_chain": {"raw_materials": "Deadstock fabric, Tencel, Organic cotton", "manufacturing": "LA factories",
                      "distribution": "Carbon-neutral since 2015", "end_of_life": "RefScale lifecycle tracking"},
     "materials": {"deadstock_fabric": 30, "tencel": 25, "organic_cotton": 25, "recycled_polyester": 20},
     "price_range": "$$", "animal_friendly": True, "vegan_options": True,
     "score_history": [60, 65, 72, 76, 80, 82]},
    {"name": "Zara Join Life", "rating": 48, "category": "Fast Fashion", "origin": "Spain", "founded": 1975,
     "sustainability_score": 42, "ethics_score": 50, "transparency_score": 55, "carbon_score": 40,
     "certifications": ["Better Cotton Initiative", "OEKO-TEX"],
     "supply_chain": {"raw_materials": "25% sustainable materials target", "manufacturing": "Vertically integrated",
                      "distribution": "Efficiency-focused logistics", "end_of_life": "In-store garment collection"},
     "materials": {"recycled_polyester": 15, "organic_cotton": 10, "conventional_polyester": 40, "conventional_cotton": 35},
     "price_range": "$", "animal_friendly": False, "vegan_options": False,
     "score_history": [28, 32, 36, 40, 45, 48]},
    {"name": "Veja", "rating": 90, "category": "Footwear", "origin": "France", "founded": 2005,
     "sustainability_score": 92, "ethics_score": 88, "transparency_score": 86, "carbon_score": 90,
     "certifications": ["B Corp", "Fair Trade", "OEKO-TEX", "FSC"],
     "supply_chain": {"raw_materials": "Wild rubber from Amazon, Organic cotton", "manufacturing": "Brazil factories",
                      "distribution": "No advertising budget — invests in materials", "end_of_life": "Designed for durability"},
     "materials": {"wild_rubber": 25, "organic_cotton": 30, "recycled_polyester": 20, "sugar_cane": 15, "rice_waste": 10},
     "price_range": "$$", "animal_friendly": True, "vegan_options": True,
     "score_history": [72, 78, 82, 86, 88, 90]},
    {"name": "Nike Move to Zero", "rating": 62, "category": "Athletic", "origin": "USA", "founded": 1972,
     "sustainability_score": 58, "ethics_score": 60, "transparency_score": 65, "carbon_score": 62,
     "certifications": ["Better Cotton Initiative"],
     "supply_chain": {"raw_materials": "Nike Grind recycled materials", "manufacturing": "Contracted factories",
                      "distribution": "Optimizing air freight", "end_of_life": "Nike Refurbished program"},
     "materials": {"recycled_polyester": 25, "nike_grind": 15, "conventional_polyester": 35, "conventional_cotton": 25},
     "price_range": "$$", "animal_friendly": False, "vegan_options": True,
     "score_history": [40, 45, 48, 52, 58, 62]},
]

# ─── My Closet / Wardrobe Tracker ─────────────────────────────────────────
MY_CLOSET = [
    {"item": "Organic Cotton T-Shirt", "brand": "Patagonia", "category": "Top", "price": 45,
     "materials": {"organic_cotton": 100}, "purchased": "2025-06-15", "worn": 28, "washes": 12,
     "carbon_footprint": 3.2, "water_usage": 715, "ethical_score": 92, "condition": "Good",
     "end_of_life": "Donate", "replaced_would_be": "Fast fashion tee — 7.5kg CO2"},
    {"item": "Recycled Denim Jeans", "brand": "Reformation", "category": "Bottom", "price": 128,
     "materials": {"recycled_denim": 70, "organic_cotton": 30}, "purchased": "2025-03-20", "worn": 45, "washes": 15,
     "carbon_footprint": 8.5, "water_usage": 2100, "ethical_score": 80, "condition": "Good",
     "end_of_life": "Upcycle", "replaced_would_be": "Conventional jeans — 33.4kg CO2"},
    {"item": "Vegan Leather Jacket", "brand": "Stella McCartney", "category": "Outerwear", "price": 895,
     "materials": {"vegetarian_leather": 80, "organic_silk_lining": 20}, "purchased": "2024-11-10", "worn": 52, "washes": 5,
     "carbon_footprint": 12.8, "water_usage": 3500, "ethical_score": 95, "condition": "Excellent",
     "end_of_life": "Resell", "replaced_would_be": "Real leather jacket — 22kg CO2"},
    {"item": "Hemp Canvas Sneakers", "brand": "Veja", "category": "Footwear", "price": 150,
     "materials": {"hemp": 40, "wild_rubber": 35, "organic_cotton": 25}, "purchased": "2025-04-01", "worn": 38, "washes": 8,
     "carbon_footprint": 5.5, "water_usage": 1200, "ethical_score": 90, "condition": "Good",
     "end_of_life": "Recycle via Veja", "replaced_would_be": "Conventional sneakers — 14kg CO2"},
    {"item": "Tencel Midi Dress", "brand": "Eileen Fisher", "category": "Dress", "price": 228,
     "materials": {"tencel": 60, "organic_cotton": 40}, "purchased": "2025-07-05", "worn": 15, "washes": 6,
     "carbon_footprint": 4.1, "water_usage": 900, "ethical_score": 88, "condition": "Excellent",
     "end_of_life": "Renew program", "replaced_would_be": "Polyester dress — 9kg CO2"},
    {"item": "Recycled Cashmere Sweater", "brand": "Everlane", "category": "Knitwear", "price": 168,
     "materials": {"recycled_cashmere": 70, "recycled_nylon": 30}, "purchased": "2025-10-12", "worn": 22, "washes": 8,
     "carbon_footprint": 6.2, "water_usage": 1800, "ethical_score": 85, "condition": "Good",
     "end_of_life": "Donate", "replaced_would_be": "Virgin cashmere — 45kg CO2"},
    {"item": "Deadstock Silk Blouse", "brand": "Reformation", "category": "Top", "price": 148,
     "materials": {"deadstock_silk": 100}, "purchased": "2025-08-22", "worn": 10, "washes": 4,
     "carbon_footprint": 2.8, "water_usage": 650, "ethical_score": 82, "condition": "Excellent",
     "end_of_life": "Consignment", "replaced_would_be": "New silk blouse — 11kg CO2"},
    {"item": "Conventional Polyester Hoodie", "brand": "Unknown Fast Fashion", "category": "Outerwear", "price": 25,
     "materials": {"polyester": 80, "spandex": 20}, "purchased": "2024-12-01", "worn": 60, "washes": 30,
     "carbon_footprint": 7.8, "water_usage": 2500, "ethical_score": 20, "condition": "Fading",
     "end_of_life": "Textile recycling", "replaced_would_be": "N/A — already fast fashion"},
]

# ─── Textile Waste Data ──────────────────────────────────────────────────
TEXTILE_WASTE = {
    "global_annual_tons": "92 million",
    "recycled_percentage": 12,
    "landfill_percentage": 73,
    "incinerated_percentage": 12,
    "downcycled_percentage": 3,
    "water_per_cotton_tshirt_liters": 2700,
    "microplastics_per_wash_grams": 0.5,
    "fashion_share_of_global_emissions": 8,
    "decomposition_polyester_years": 200,
    "decomposition_cotton_years": 5,
    "decomposition_leather_years": 50,
    "decomposition_nylon_years": 40,
}

# ─── Ethical Alternatives ─────────────────────────────────────────────────
ALTERNATIVES = [
    {"fast_fashion_item": "Polyester T-shirt", "fast_brand": "Shein", "fast_price": 8, "fast_co2": 7.5,
     "eco_alternative": "Organic Cotton Tee", "eco_brand": "Patagonia", "eco_price": 45, "eco_co2": 3.2,
     "water_saved_liters": 1800, "chemicals_avoided": True, "microplastic_free": True},
    {"fast_fashion_item": "PU Leather Jacket", "fast_brand": "Zara", "fast_price": 69, "fast_co2": 18.2,
     "eco_alternative": "Vegetarian Leather Jacket", "eco_brand": "Stella McCartney", "eco_price": 895, "eco_co2": 12.8,
     "water_saved_liters": 5200, "chemicals_avoided": True, "microplastic_free": True},
    {"fast_fashion_item": "Acrylic Sweater", "fast_brand": "H&M", "fast_price": 19, "fast_co2": 10.5,
     "eco_alternative": "Recycled Cashmere Sweater", "eco_brand": "Everlane", "eco_price": 168, "eco_co2": 6.2,
     "water_saved_liters": 3400, "chemicals_avoided": True, "microplastic_free": True},
    {"fast_fashion_item": "Synthetic Sneakers", "fast_brand": "Fashion Nova", "fast_price": 35, "fast_co2": 14.0,
     "eco_alternative": "Hemp Canvas Sneakers", "eco_brand": "Veja", "eco_price": 150, "eco_co2": 5.5,
     "water_saved_liters": 2100, "chemicals_avoided": True, "microplastic_free": True},
    {"fast_fashion_item": "Conventional Jeans", "fast_brand": "Zara", "fast_price": 39, "fast_co2": 33.4,
     "eco_alternative": "Recycled Denim Jeans", "eco_brand": "Reformation", "eco_price": 128, "eco_co2": 8.5,
     "water_saved_liters": 5500, "chemicals_avoided": True, "microplastic_free": False},
    {"fast_fashion_item": "Nylon Bag", "fast_brand": "Shein", "fast_price": 12, "fast_co2": 9.2,
     "eco_alternative": "Organic Hemp Tote", "eco_brand": "Patagonia", "eco_price": 55, "eco_co2": 1.8,
     "water_saved_liters": 1200, "chemicals_avoided": True, "microplastic_free": True},
]

# ─── Textile Recycling Methods ────────────────────────────────────────────
RECYCLING_METHODS = [
    {"method": "Mechanical Recycling", "process": "Shredding → Fiber re-spinning", "quality_loss": "20-30%",
     "compatible_materials": ["Cotton", "Wool", "Polyester (blend)"], "energy_usage": "Low",
     "acceptance_rate": 35, "description": "Physical shredding of fabric into fibers that are re-spun. Each cycle shortens fibers reducing quality."},
    {"method": "Chemical Recycling", "process": "Dissolution → Polymer regeneration", "quality_loss": "5-10%",
     "compatible_materials": ["Polyester", "Nylon", "Cellulosic"], "energy_usage": "Medium",
     "acceptance_rate": 20, "description": "Chemical processes dissolve fabric into raw polymers for new fiber production. Near-virgin quality."},
    {"method": "Fiber-to-Fiber (Cellulosic)", "process": "Pulping → Re-forming", "quality_loss": "10-15%",
     "compatible_materials": ["Cotton", "Tencel", "Viscose"], "energy_usage": "High",
     "acceptance_rate": 15, "description": "Converting cotton waste back to pulp and forming new cellulosic fibers like Lyocell."},
    {"method": "Pyrolysis", "process": "Heat decomposition → Fuel / Chemicals", "quality_loss": "100% (material)",
     "compatible_materials": ["Mixed blends", "Contaminated textiles"], "energy_usage": "Very High",
     "acceptance_rate": 10, "description": "Thermal decomposition of textiles into synthetic fuel or chemical feedstock when recycling isn't possible."},
    {"method": "Upcycling / Reuse", "process": "Redesign → New product", "quality_loss": "0%",
     "compatible_materials": ["All"], "energy_usage": "Minimal",
     "acceptance_rate": 20, "description": "Transforming old garments into new higher-value products. Preserves most embodied energy and materials."},
]

# ─── Supply Chain Stage Definitions ───────────────────────────────────────
SUPPLY_CHAIN_STAGES = [
    {"stage": "Raw Materials", "icon": "🌱", "impact_areas": ["Water usage", "Pesticide use", "Land use", "Biodiversity loss"],
     "key_questions": ["Where is the cotton grown?", "Is it organic?", "What chemicals are used?", "Who owns the land?"],
     "eco_solution": "Organic, recycled, or regenerative materials from certified sources"},
    {"stage": "Spinning & Weaving", "icon": "🧵", "impact_areas": ["Energy consumption", "Chemical dyes", "Water pollution", "Worker safety"],
     "key_questions": ["What dyes are used?", "Is water treated before discharge?", "Are workers protected?", "What energy source powers the factory?"],
     "eco_solution": "Closed-loop dye systems, renewable energy, certified factories"},
    {"stage": "Manufacturing", "icon": "🏭", "impact_areas": ["Carbon emissions", "Waste generation", "Worker conditions", "Chemical exposure"],
     "key_questions": ["How many hands touched this garment?", "What is the factory's safety record?", "Are wages living wages?", "How is waste managed?"],
     "eco_solution": "Fair Trade factories, zero-waste cutting, solar-powered facilities"},
    {"stage": "Transportation", "icon": "🚢", "impact_areas": ["CO2 emissions", "Packaging waste", "Air freight impact", "Last-mile delivery"],
     "key_questions": ["How far did this travel?", "By what mode of transport?", "Is packaging recyclable?", "Can shipping be consolidated?"],
     "eco_solution": "Sea freight over air, local production, biodegradable packaging"},
    {"stage": "Consumer Use", "icon": "👤", "impact_areas": ["Microplastics", "Water in washing", "Energy for drying", "Chemical detergents"],
     "key_questions": ["How many times will this be worn?", "How should it be washed?", "Can it be repaired?", "How long will it last?"],
     "eco_solution": "Cold wash, air dry, wear 30+ times, repair instead of replace"},
    {"stage": "End of Life", "icon": "♻️", "impact_areas": ["Landfill volume", "Microplastic shedding", "Chemical leaching", "Resource loss"],
     "key_questions": ["Can this be recycled?", "Is there a take-back program?", "Can it be composted?", "Will it release toxins in landfill?"],
     "eco_solution": "Take-back programs, textile recycling, composting natural fibers, resale"},
]

# ─── Helper Functions ──────────────────────────────────────────────────────
def get_rating_color(score):
    if score >= 80: return "#22c55e"
    elif score >= 60: return "#eab308"
    elif score >= 40: return "#f97316"
    else: return "#ef4444"

def get_rating_label(score):
    if score >= 90: return "Excellent"
    elif score >= 75: return "Good"
    elif score >= 55: return "Fair"
    elif score >= 35: return "Poor"
    else: return "Very Poor"

def get_condition_color(cond):
    colors = {"Excellent": "#22c55e", "Good": "#3b82f6", "Fair": "#eab308", "Fading": "#f97316", "Worn Out": "#ef4444"}
    return colors.get(cond, "#6b7280")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: BRAND RATINGS
# ═══════════════════════════════════════════════════════════════════════════
def render_brand_ratings():
    st.markdown("### 🏷️ Brand Sustainability Ratings")

    # Overview KPIs
    avg_rating = np.mean([b["rating"] for b in BRANDS])
    best_brand = max(BRANDS, key=lambda x: x["rating"])
    worst_brand = min(BRANDS, key=lambda x: x["rating"])
    certified = sum(1 for b in BRANDS if len(b["certifications"]) >= 2)

    cols = st.columns(5)
    for i, (label, value, color) in enumerate([
        ("Brands Rated", len(BRANDS), "#8b5cf6"),
        ("Avg Rating", f"{avg_rating:.0f}", "#3b82f6"),
        ("Top Rated", best_brand["name"], "#22c55e"),
        ("Most Improved", worst_brand["name"], "#f97316"),
        ("Multi-Certified", f"{certified} brands", "#ec4899"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Rating comparison bar chart
    brands_df = pd.DataFrame([
        {"Brand": b["name"], "Rating": b["rating"], "Sustainability": b["sustainability_score"],
         "Ethics": b["ethics_score"], "Transparency": b["transparency_score"], "Carbon": b["carbon_score"]}
        for b in BRANDS
    ])
    fig = px.bar(brands_df, x="Brand", y=["Sustainability", "Ethics", "Transparency", "Carbon"],
                 barmode="group", title="Brand Score Comparison",
                 color_discrete_map={"Sustainability": "#22c55e", "Ethics": "#3b82f6",
                                     "Transparency": "#8b5cf6", "Carbon": "#f97316"})
    fig.update_layout(template="plotly_dark", height=400, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Brand cards
    st.markdown("#### 📋 Brand Profiles")
    for brand in sorted(BRANDS, key=lambda x: x["rating"], reverse=True):
        with st.expander(f"{'🟢' if brand['rating'] >= 80 else '🟡' if brand['rating'] >= 55 else '🔴'} {brand['name']} — Rating: {brand['rating']}/100 ({get_rating_label(brand['rating'])})", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Category:** {brand['category']} | **Origin:** {brand['origin']} | **Founded:** {brand['founded']}")
                st.markdown(f"**Price Range:** {brand['price_range']} | **Vegan Options:** {'✅' if brand['vegan_options'] else '❌'} | **Animal Friendly:** {'✅' if brand['animal_friendly'] else '❌'}")
                st.markdown(f"**Certifications:** {', '.join(brand['certifications']) if brand['certifications'] else 'None'}")
                # Score breakdown
                for score_name, score_val in [("Sustainability", brand["sustainability_score"]),
                                               ("Ethics", brand["ethics_score"]),
                                               ("Transparency", brand["transparency_score"]),
                                               ("Carbon", brand["carbon_score"])]:
                    st.markdown(f"**{score_name}:**")
                    st.progress(score_val / 100)
            with col2:
                # Material composition donut
                mat_df = pd.DataFrame(list(brand["materials"].items()), columns=["Material", "Percentage"])
                fig = px.pie(mat_df, values="Percentage", names="Material",
                             title="Material Composition",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(template="plotly_dark", height=280, plot_bgcolor="rgba(0,0,0,0)",
                                  paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"),
                                  showlegend=True, legend=dict(orientation="h", y=-0.2))
                st.plotly_chart(fig, use_container_width=True)

            # Supply chain summary
            st.markdown("**🔗 Supply Chain:**")
            for key, val in brand["supply_chain"].items():
                st.markdown(f"  • **{key.replace('_', ' ').title()}:** {val}")

            # Score history
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=["2021", "2022", "2023", "2024", "2025", "2026"],
                                     y=brand["score_history"], mode="lines+markers",
                                     line=dict(color=get_rating_color(brand["rating"]), width=3),
                                     name="Rating"))
            fig.update_layout(template="plotly_dark", height=200, plot_bgcolor="rgba(0,0,0,0)",
                              paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"),
                              margin=dict(t=10, b=10), xaxis_title="", yaxis_title="Rating")
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: MY CLOSET
# ═══════════════════════════════════════════════════════════════════════════
def render_my_closet():
    st.markdown("### 👗 My Closet — Sustainable Fashion Tracker")

    # KPIs
    total_items = len(MY_CLOSET)
    total_spent = sum(item["price"] for item in MY_CLOSET)
    total_co2_saved = sum(float(item["replaced_would_be"].split("—")[1].replace("kg CO2", "")) - item["carbon_footprint"]
                         for item in MY_CLOSET if "—" in item["replaced_would_be"])
    avg_ethical = np.mean([item["ethical_score"] for item in MY_CLOSET])
    avg_wears = np.mean([item["worn"] for item in MY_CLOSET])
    total_water_saved = sum(item["water_usage"] for item in MY_CLOSET)

    cols = st.columns(5)
    for i, (label, value, color) in enumerate([
        ("Items", total_items, "#8b5cf6"),
        ("Total Spent", f"${total_spent:,}", "#3b82f6"),
        ("CO₂ Saved", f"{total_co2_saved:.1f}kg", "#22c55e"),
        ("Avg Ethical Score", f"{avg_ethical:.0f}", "#ec4899"),
        ("Avg Wears/Item", f"{avg_wears:.0f}", "#f97316"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Carbon comparison chart
    carbon_df = pd.DataFrame([
        {"Item": item["item"], "Actual CO₂": item["carbon_footprint"],
         "Fast Fashion CO₂": float(item["replaced_would_be"].split("—")[1].replace("kg CO2", "")) if "—" in item["replaced_would_be"] else item["carbon_footprint"]}
        for item in MY_CLOSET
    ])
    fig = px.bar(carbon_df, x="Item", y=["Actual CO₂", "Fast Fashion CO₂"],
                 barmode="group", title="Carbon Footprint: My Items vs Fast Fashion Equivalent",
                 color_discrete_map={"Actual CO₂": "#22c55e", "Fast Fashion CO₂": "#ef4444"})
    fig.update_layout(template="plotly_dark", height=380, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Closet items
    st.markdown("#### 🧥 My Items")
    for item in sorted(MY_CLOSET, key=lambda x: x["ethical_score"], reverse=True):
        with st.expander(f"{'🟢' if item['ethical_score'] >= 80 else '🟡' if item['ethical_score'] >= 50 else '🔴'} {item['item']} ({item['brand']}) — {item['condition']}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Category:** {item['category']} | **Price:** ${item['price']}")
                st.markdown(f"**Purchased:** {item['purchased']} | **Worn:** {item['worn']} times | **Washes:** {item['washes']}")
                st.markdown(f"**Condition:** :{get_condition_color(item['condition'])}[{item['condition']}]")
                st.markdown(f"**Ethical Score:** {item['ethical_score']}/100")
                st.progress(item["ethical_score"] / 100)
                st.markdown(f"**CO₂ Footprint:** {item['carbon_footprint']}kg | **Water:** {item['water_usage']:,}L")
                st.markdown(f"**End of Life Plan:** {item['end_of_life']}")
            with col2:
                # Material composition
                mat_df = pd.DataFrame(list(item["materials"].items()), columns=["Material", "%"])
                fig = px.pie(mat_df, values="%", names="Material", title="Material Composition",
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(template="plotly_dark", height=240, plot_bgcolor="rgba(0,0,0,0)",
                                  paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
                st.plotly_chart(fig, use_container_width=True)

            st.info(f"💡 **Fast fashion equivalent would be:** {item['replaced_would_be']}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: TEXTILE WASTE
# ═══════════════════════════════════════════════════════════════════════════
def render_textile_waste():
    st.markdown("### 🗑️ Textile Waste — Global Crisis")

    # KPIs
    cols = st.columns(5)
    for i, (label, value, color) in enumerate([
        ("Global Waste", "92M tons/yr", "#ef4444"),
        ("Recycled", "12%", "#22c55e"),
        ("Landfilled", "73%", "#f97316"),
        ("Fashion Emissions", "8% global", "#8b5cf6"),
        ("Decomposition", "200 yrs (poly)", "#3b82f6"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:20px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Waste breakdown pie chart
    waste_df = pd.DataFrame([
        {"Category": "Landfilled", "Percentage": 73, "Color": "#ef4444"},
        {"Category": "Recycled", "Percentage": 12, "Color": "#22c55e"},
        {"Category": "Incinerated", "Percentage": 12, "Color": "#f97316"},
        {"Category": "Downcycled", "Percentage": 3, "Color": "#3b82f6"},
    ])
    fig = px.pie(waste_df, values="Percentage", names="Category",
                 title="Global Textile Waste Breakdown",
                 color_discrete_sequence=["#ef4444", "#22c55e", "#f97316", "#3b82f6"])
    fig.update_layout(template="plotly_dark", height=380, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Material decomposition timeline
    st.markdown("#### ⏰ Material Decomposition Timeline")
    decomp_data = pd.DataFrame([
        {"Material": "Polyester", "Years": 200, "Type": "Synthetic"},
        {"Material": "Nylon", "Years": 40, "Type": "Synthetic"},
        {"Material": "Leather", "Years": 50, "Type": "Animal"},
        {"Material": "Cotton", "Years": 5, "Type": "Natural"},
        {"Material": "Wool", "Years": 1, "Type": "Natural"},
        {"Material": "Silk", "Years": 4, "Type": "Natural"},
        {"Material": "Hemp", "Months": 2, "Type": "Natural"},
    ])
    fig = px.bar(decomp_data, x="Material", y="Years", color="Type",
                 title="How Long Do Fabrics Take to Decompose?",
                 color_discrete_map={"Synthetic": "#ef4444", "Animal": "#f97316", "Natural": "#22c55e"})
    fig.update_layout(template="plotly_dark", height=350, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Recycling methods
    st.markdown("#### ♻️ Textile Recycling Methods")
    for method in RECYCLING_METHODS:
        with st.expander(f"🔄 {method['method']} — Quality Loss: {method['quality_loss']}", expanded=False):
            st.markdown(f"**Process:** {method['process']}")
            st.markdown(f"**Energy Usage:** {method['energy_usage']}")
            st.markdown(f"**Acceptance Rate:** {method['acceptance_rate']}%")
            st.markdown(f"**Compatible Materials:** {', '.join(method['compatible_materials'])}")
            st.markdown(f"**Description:** {method['description']}")
            st.progress(method["acceptance_rate"] / 100)

    # Microplastics warning
    st.markdown("---")
    st.warning("🌊 **Microplastic Alert:** Each wash of synthetic clothing releases ~0.5g of microplastic fibers into waterways. A single polyester jacket can shed 1.7g per wash — that's over 3,400 fibers entering the ocean every cycle.")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: SUPPLY CHAIN TRANSPARENCY
# ═══════════════════════════════════════════════════════════════════════════
def render_supply_chain():
    st.markdown("### 🔗 Supply Chain Transparency")

    # Supply chain journey visualization
    st.markdown("#### 🗺️ Journey of a Garment")
    cols = st.columns(len(SUPPLY_CHAIN_STAGES))
    for i, stage in enumerate(SUPPLY_CHAIN_STAGES):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid rgba(139,92,246,0.3);border-radius:12px;padding:14px;text-align:center;
                        min-height:120px;">
                <div style="font-size:28px;">{stage['icon']}</div>
                <div style="font-size:13px;font-weight:700;color:#e2e8f0;margin:6px 0;">{stage['stage']}</div>
                <div style="font-size:10px;color:#94a3b8;">{stage['eco_solution'][:60]}...</div>
            </div>""", unsafe_allow_html=True)
            if i < len(SUPPLY_CHAIN_STAGES) - 1:
                st.markdown("<div style='text-align:center;font-size:24px;color:#8b5cf6;'>→</div>", unsafe_allow_html=True)

    st.markdown("---")

    # Detailed stage explorer
    for stage in SUPPLY_CHAIN_STAGES:
        with st.expander(f"{stage['icon']} **{stage['stage']}** — Impact & Questions", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**⚠️ Impact Areas:**")
                for area in stage["impact_areas"]:
                    st.markdown(f"  • {area}")
            with col2:
                st.markdown("**❓ Key Questions:**")
                for q in stage["key_questions"]:
                    st.markdown(f"  • {q}")
            with col3:
                st.markdown("**🌱 Eco Solution:**")
                st.info(stage["eco_solution"])

    # Brand transparency scores
    st.markdown("#### 🏷️ Brand Transparency Comparison")
    trans_df = pd.DataFrame([
        {"Brand": b["name"], "Transparency": b["transparency_score"], "Ethics": b["ethics_score"]}
        for b in BRANDS
    ])
    fig = px.scatter(trans_df, x="Transparency", y="Ethics", text="Brand",
                     title="Transparency vs Ethics Score",
                     color="Transparency", color_continuous_scale="Viridis",
                     size=[20] * len(trans_df))
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(template="plotly_dark", height=400, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5: SUSTAINABLE ALTERNATIVES
# ═══════════════════════════════════════════════════════════════════════════
def render_alternatives():
    st.markdown("### 🌿 Sustainable Alternatives — Swap Guide")

    # Overview KPIs
    total_water = sum(a["water_saved_liters"] for a in ALTERNATIVES)
    total_co2 = sum(a["fast_co2"] - a["eco_co2"] for a in ALTERNATIVES)
    avg_price_diff = np.mean([(a["eco_price"] - a["fast_price"]) / a["fast_price"] * 100 for a in ALTERNATIVES])

    cols = st.columns(4)
    for i, (label, value, color) in enumerate([
        ("Water Saved", f"{total_water:,}L", "#3b82f6"),
        ("CO₂ Reduced", f"{total_co2:.1f}kg", "#22c55e"),
        ("Alternatives", f"{len(ALTERNATIVES)} swaps", "#8b5cf6"),
        ("Avg Price Diff", f"+{avg_price_diff:.0f}%", "#f97316"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:16px;text-align:center;">
                <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Comparison chart
    comp_df = pd.DataFrame([
        {"Swap": f"{a['fast_fashion_item'][:20]}...", "Fast Fashion CO₂": a["fast_co2"], "Eco CO₂": a["eco_co2"]}
        for a in ALTERNATIVES
    ])
    fig = px.bar(comp_df, x="Swap", y=["Fast Fashion CO₂", "Eco CO₂"],
                 barmode="group", title="Carbon Footprint: Fast Fashion vs Eco Alternatives",
                 color_discrete_map={"Fast Fashion CO₂": "#ef4444", "Eco CO₂": "#22c55e"})
    fig.update_layout(template="plotly_dark", height=380, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Alternative cards
    st.markdown("#### 🔄 Swap Cards")
    for alt in ALTERNATIVES:
        with st.expander(f"🔄 {alt['fast_fashion_item']} ({alt['fast_brand']}) → {alt['eco_alternative']} ({alt['eco_brand']})", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**❌ Fast Fashion:**")
                st.markdown(f"- Brand: {alt['fast_brand']}")
                st.markdown(f"- Price: ${alt['fast_price']}")
                st.markdown(f"- CO₂: {alt['fast_co2']}kg")
                st.markdown(f"- Microplastic-free: ❌")
            with col2:
                st.markdown(f"**✅ Eco Alternative:**")
                st.markdown(f"- Brand: {alt['eco_brand']}")
                st.markdown(f"- Price: ${alt['eco_price']}")
                st.markdown(f"- CO₂: {alt['eco_co2']}kg")
                st.markdown(f"- Microplastic-free: {'✅' if alt['microplastic_free'] else '❌'}")

            st.markdown(f"**🌊 Water Saved:** {alt['water_saved_liters']:,}L | "
                       f"**🧪 Chemicals Avoided:** {'✅' if alt['chemicals_avoided'] else '❌'} | "
                       f"**♻️ CO₂ Reduction:** {alt['fast_co2'] - alt['eco_co2']:.1f}kg ({(alt['fast_co2'] - alt['eco_co2'])/alt['fast_co2']*100:.0f}%)")

    # Cost-per-wear analysis
    st.markdown("#### 💰 Cost-Per-Wear Analysis")
    cpw_data = []
    for item in MY_CLOSET:
        cpw = item["price"] / max(item["worn"], 1)
        fast_cpw = 15 / 10  # Assume $15 fast fashion, 10 wears
        cpw_data.append({"Item": item["item"], "Sustainable CPW": cpw, "Fast Fashion CPW": fast_cpw})

    cpw_df = pd.DataFrame(cpw_data)
    fig = px.bar(cpw_df, x="Item", y=["Sustainable CPW", "Fast Fashion CPW"],
                 barmode="group", title="Cost Per Wear: Sustainable vs Fast Fashion",
                 color_discrete_map={"Sustainable CPW": "#22c55e", "Fast Fashion CPW": "#ef4444"})
    fig.update_layout(template="plotly_dark", height=380, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Action tips
    st.markdown("---")
    st.markdown("#### 💡 Quick Tips for Sustainable Fashion")
    tips = [
        "🧵 **Buy Less, Choose Well** — Invest in quality pieces that last 30+ wears",
        "🌿 **Natural Fibers First** — Cotton, hemp, wool, silk biodegrade in years, not centuries",
        "♻️ **Check Certifications** — B Corp, Fair Trade, GOTS, OEKO-TEX are gold standards",
        "🔍 **Research Brands** — Use apps like Good On You to check sustainability ratings",
        "🩹 **Repair & Mend** — Extend garment life by 9 months to reduce footprint by 20-30%",
        "👗 **Rent & Swap** — For occasion wear, rent instead of buying rarely-worn pieces",
    ]
    for tip in tips:
        st.markdown(f"  {tip}")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="Eco Fashion Impact Tracker", page_icon="👗", layout="wide")

    # Custom CSS
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: rgba(255,255,255,0.03); border-radius: 12px; padding: 6px; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 10px 20px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #8b5cf6, #3b82f6); color: white; }
    .stExpander { background: rgba(255,255,255,0.02); border: 1px solid rgba(139,92,246,0.2); border-radius: 10px; }
    h1 { background: linear-gradient(135deg, #ec4899, #8b5cf6, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    h2 { background: linear-gradient(135deg, #8b5cf6, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>""", unsafe_allow_html=True)

    st.markdown("# 👗 Eco Fashion Impact Tracker")
    st.markdown("Track brand sustainability, supply chain transparency, textile waste, and make ethical fashion choices.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏷️ Brand Ratings", "👗 My Closet", "🗑️ Textile Waste",
        "🔗 Supply Chain", "🌿 Alternatives"
    ])

    with tab1:
        render_brand_ratings()
    with tab2:
        render_my_closet()
    with tab3:
        render_textile_waste()
    with tab4:
        render_supply_chain()
    with tab5:
        render_alternatives()


if __name__ == "__main__":
    main()
