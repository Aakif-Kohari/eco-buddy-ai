"""
Smart Waste Sorting Assistant
=============================
AI-powered waste classification, recycling guidance, contamination detection,
waste audit tools, and reduction analytics.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# ─── Waste Item Database ──────────────────────────────────────────────────
WASTE_ITEMS = [
    {"name": "Plastic Water Bottle", "category": "Recyclable", "bin": "Blue ♻️",
     "material": "PET Plastic (#1)", "decomposition": "450 years",
     "recycling_rate": 29, "contamination_risk": "Low",
     "prep": "Rinse, remove cap, crush if possible",
     "fun_facts": "Only 1 in 5 plastic bottles are actually recycled in the US"],
    {"name": "Pizza Cardboard Box", "category": "Conditionally Recyclable", "bin": "Check for grease",
     "material": "Corrugated Cardboard", "decomposition": "2 months",
     "recycling_rate": 68, "contamination_risk": "High if greasy",
     "prep": "Remove food scraps. If heavily greased → compost or trash",
     "fun_facts": "Grease contaminates an entire batch of recycled paper"],
    {"name": "Banana Peel", "category": "Compostable", "bin": "Green 🌱",
     "material": "Organic Matter", "decomposition": "2-5 weeks",
     "recycling_rate": 0, "contamination_risk": "None",
     "prep": "No prep needed — toss in compost",
     "fun_facts": "Banana peels can be used to polish leather and silver"],
    {"name": "Aluminum Can", "category": "Recyclable", "bin": "Blue ♻️",
     "material": "Aluminum", "decomposition": "80-200 years",
     "recycling_rate": 50, "contamination_risk": "Low",
     "prep": "Rinse, crush to save space",
     "fun_facts": "Recycling one aluminum can saves enough energy to run a TV for 3 hours"],
    {"name": "Styrofoam Cup", "category": "Landfill", "bin": "Black 🗑️",
     "material": "Polystyrene (#6)", "decomposition": "Never (500+ years)",
     "recycling_rate": 1, "contamination_risk": "N/A",
     "prep": "Cannot be recycled curbside. Few specialty facilities accept it",
     "fun_facts": "Styrofoam is 95% air and makes up ~30% of landfill waste by volume"],
    {"name": "Glass Jar", "category": "Recyclable", "bin": "Blue ♻️",
     "material": "Glass", "decomposition": "1 million years",
     "recycling_rate": 33, "contamination_risk": "Low",
     "prep": "Rinse, remove metal lids (recycle separately)",
     "fun_facts": "Glass is 100% recyclable and can be recycled endlessly without quality loss"],
    {"name": "Chip Bag", "category": "Landfill", "bin": "Black 🗑️",
     "material": "Multi-layer Plastic/Aluminum", "decomposition": "300+ years",
     "recycling_rate": 0, "contamination_risk": "N/A",
     "prep": "Not recyclable — mixed materials. TerraCycle programs may accept",
     "fun_facts": "Most chip bags are made of 7+ layers of different materials fused together"],
    {"name": "Used Napkin", "category": "Compostable / Landfill", "bin": "Green 🌱 or Black 🗑️",
     "material": "Paper (contaminated)", "decomposition": "1 month",
     "recycling_rate": 0, "contamination_risk": "N/A",
     "prep": "Compost if food-stained only. If chemical-contaminated → trash",
     "fun_facts": "Used paper napkins cannot be recycled due to food contamination"],
    {"name": "Egg Carton (Cardboard)", "category": "Compostable", "bin": "Green 🌱",
     "material": "Molded Pulp", "decomposition": "2-3 months",
     "recycling_rate": 0, "contamination_risk": "Low",
     "prep": "Tear into small pieces for faster composting. Great for garden mulch",
     "fun_facts": "Cardboard egg cartons can be planted directly into soil"],
    {"name": "Plastic Grocery Bag", "category": "Special Recycling", "bin": "Store Drop-off 🏪",
     "material": "HDPE Film (#2)", "decomposition": "500+ years",
     "recycling_rate": 5, "contamination_risk": "High — jams sorting machines",
     "prep": "Collect bags, return to grocery store collection bin",
     "fun_facts": "Plastic bags kill over 100,000 marine animals annually"],
    {"name": "Coffee Grounds", "category": "Compostable", "bin": "Green 🌱",
     "material": "Organic Matter", "decomposition": "3-4 months",
     "recycling_rate": 0, "contamination_risk": "None",
     "prep": "Can go directly in compost. Also great as garden fertilizer",
     "fun_facts": "Coffee grounds repel slugs and snails from garden beds"],
    {"name": "Battery (AA)", "category": "Hazardous Waste", "bin": "Hazardous ☣️",
     "material": "Zinc-Manganese / Lithium", "decomposition": "100+ years",
     "recycling_rate": 5, "contamination_risk": "High — toxic leaching",
     "prep": "Never put in regular trash or recycling. Take to e-waste facility",
     "fun_facts": "Batteries contain heavy metals that can contaminate 600,000 gallons of water"],
    {"name": "Wine Cork", "category": "Compostable", "bin": "Green 🌱",
     "material": "Natural Cork", "decomposition": "3-6 months",
     "recycling_rate": 0, "contamination_risk": "None",
     "prep": "Real cork is compostable. Synthetic cork → trash",
     "fun_facts": "Portugal produces 50% of the world's cork supply"],
    {"name": "Receipt Paper", "category": "Landfill", "bin": "Black 🗑️",
     "material": "Thermal Paper (BPA-coated)", "decomposition": "1-2 years",
     "recycling_rate": 0, "contamination_risk": "Medium — BPA contamination",
     "prep": "Contains BPA — cannot be recycled. May be compostable in small amounts",
     "fun_facts": "BPA on receipts can absorb through skin; handle minimally"],
    {"name": "Tetra Pak Carton", "category": "Conditionally Recyclable", "bin": "Check local 🏠",
     "material": "Paperboard/Plastic/Aluminum laminate", "decomposition": "500+ years",
     "recycling_rate": 26, "contamination_risk": "Medium",
     "prep": "Rinse, flatten. Only recyclable at specialty facilities",
     "fun_facts": "Tetra Paks are made of 6 layers of different materials"],
    {"name": "Used Diaper", "category": "Landfill", "bin": "Black 🗑️",
     "material": "Super Absorbent Polymer / Cellulose", "decomposition": "500+ years",
     "recycling_rate": 0, "contamination_risk": "N/A",
     "prep": "Seal in bag before disposing. Consider compostable diaper alternatives",
     "fun_facts": "A single child uses ~6,000 diapers before potty training"],
    {"name": "Soda Can (Rinsed)", "category": "Recyclable", "bin": "Blue ♻️",
     "material": "Aluminum", "decomposition": "80-200 years",
     "recycling_rate": 50, "contamination_risk": "Low when rinsed",
     "prep": "Rinse clean, crush, lid can stay attached",
     "fun_facts": "A recycled can returns to the shelf as a new can in just 60 days"],
    {"name": "Broken Plate (Ceramic)", "category": "Landfill", "bin": "Black 🗑️",
     "material": "Ceramic/Porcelain", "decomposition": "1 million+ years",
     "recycling_rate": 0, "contamination_risk": "N/A",
     "prep": "Wrap in newspaper before disposing — sharp edges. Cannot be recycled with glass",
     "fun_facts": "Ceramic cannot be recycled with glass because it has a much higher melting point"],
    {"name": "Wax Paper", "category": "Compostable", "bin": "Green 🌱",
     "material": "Paper with Wax Coating", "decomposition": "1-2 months",
     "recycling_rate": 0, "contamination_risk": "None",
     "prep": "Compostable — wax coating is biodegradable (unlike plastic wrap)",
     "fun_facts": "Wax paper is different from parchment paper — wax paper is not heat-resistant"],
    {"name": "Eyeglasses", "category": "Special Recycling", "bin": "Donation 👓",
     "material": "Plastic/Metal/Glass", "decomposition": "400+ years",
     "recycling_rate": 0, "contamination_risk": "N/A",
     "prep": "Donate to Lions Club, Goodwill, or optometrist collection boxes",
     "fun_facts": "Lions Club collects 30 million pairs of glasses annually for redistribution"],
]

# ─── Contamination Scenarios ──────────────────────────────────────────────
CONTAMINATION_SCENARIOS = [
    {"scenario": "Pizza box in paper recycling", "contaminant": "Grease/Food",
     "impact": "Grease coats paper fibers, making them unrecyclable. Can contaminate an entire batch (500+ lbs).",
     "correct_action": "Tear off clean top → recycle. Put greasy bottom in compost or trash.",
     "severity": "High", "cost_of_mistake": "$2,000+ per contaminated batch"},
    {"scenario": "Plastic bag in single-stream recycling", "contaminant": "Film Plastic",
     "impact": "Bags jam sorting machinery, causing $1M+ in damage annually at facilities. 1 bag can shut down a line for hours.",
     "correct_action": "Return to grocery store collection bin. Never in curbside recycling.",
     "severity": "Critical", "cost_of_mistake": "$25,000+ per equipment repair"},
    {"scenario": "Styrofoam in recycling bin", "contaminant": "Polystyrene (#6)",
     "impact": "Breaks into tiny pieces that contaminate other materials. Not accepted at most facilities.",
     "correct_action": "Place in trash, or find a TerraCycle drop-off location.",
     "severity": "Medium", "cost_of_mistake": "$500 per contaminated batch"},
    {"scenario": "Food-soiled paper towel in compost", "contaminant": "Acceptable!",
     "impact": "Paper towels with food residue are actually compostable. They break down quickly.",
     "correct_action": "Tear into pieces and add to compost bin. Great brown/green mix material.",
     "severity": "None", "cost_of_mistake": "$0 — correct behavior!"},
    {"scenario": "Battery in household trash", "contaminant": "Heavy Metals",
     "impact": "Can leach lead, mercury, cadmium into groundwater. One battery can contaminate 600,000 gallons of water.",
     "correct_action": "Take to e-waste collection point, Home Depot, or Best Buy battery recycling.",
     "severity": "Critical", "cost_of_mistake": "$50,000+ environmental cleanup"},
    {"scenario": "Plastic bag tied around recyclables", "contaminant": "Bagged Recyclables",
     "impact": "Workers cannot see inside bags. Bagged items are often automatically trashed as contamination risk.",
     "correct_action": "Place recyclables loose in the bin. Never bag your recycling.",
     "severity": "High", "cost_of_mistake": "All items in bag end up in landfill"},
    {"scenario": "Broken glass in recycling bin", "contaminant": "Glass shards",
     "impact": "Presents safety hazard to sorting workers. Different glass types (window, drinking, Pyrex) cannot be mixed.",
     "correct_action": "Wrap in thick cardboard, label 'BROKEN GLASS', place on top of bin.",
     "severity": "High", "cost_of_mistake": "$10,000+ worker injury claims"},
    {"scenario": "Receipt paper in paper recycling", "contaminant": "BPA/Thermal coating",
     "impact": "BPA transfers to recycled paper products. Contaminates entire paper bale.",
     "correct_action": "Place in trash. Consider going digital for receipts.",
     "severity": "Medium", "cost_of_mistake": "$1,000 per contaminated bale"},
]

# ─── Waste Audit Data (Simulated 30-day) ─────────────────────────────────
def generate_waste_audit():
    np.random.seed(42)
    days = pd.date_range(end=datetime.now(), periods=30, freq="D")
    categories = ["Paper/Cardboard", "Plastic", "Glass", "Metal", "Organic", "Landfill", "Hazardous"]
    data = []
    for day in days:
        row = {"Date": day}
        row["Paper/Cardboard"] = random.randint(2, 8)
        row["Plastic"] = random.randint(3, 10)
        row["Glass"] = random.randint(0, 3)
        row["Metal"] = random.randint(1, 4)
        row["Organic"] = random.randint(4, 12)
        row["Landfill"] = random.randint(2, 7)
        row["Hazardous"] = random.randint(0, 1)
        data.append(row)
    return pd.DataFrame(data)

# ─── Recycling Rules by Material ──────────────────────────────────────────
RECYCLING_RULES = {
    "Plastic (#1 PET)": {"recyclable": True, "rinse": True, "crush": True, "special": "Check number",
                         "items": ["Water bottles", "Soda bottles", "Food jars", "Peanut butter jars"],
                         "not_recyclable": ["Plastic bags", "Styrofoam", "Coffee cups", "Chip bags"]},
    "Plastic (#2 HDPE)": {"recyclable": True, "rinse": True, "crush": False, "special": "Most accepted plastic",
                          "items": ["Milk jugs", "Detergent bottles", "Shampoo bottles", "Butter tubs"],
                          "not_recyclable": ["Plastic bags", "Film wrap", "Toys"]},
    "Plastic (#5 PP)": {"recyclable": "Some areas", "rinse": True, "crush": False, "special": "Check locally",
                        "items": ["Yogurt cups", "Takeout containers", "Ketchup bottles"],
                        "not_recyclable": ["Straws", "Cutlery", "Coffee pods"]},
    "Paper": {"recyclable": True, "rinse": False, "crush": False, "special": "Keep dry, flatten boxes",
              "items": ["Newspapers", "Magazines", "Office paper", "Cardboard boxes", "Junk mail"],
              "not_recyclable": ["Wet paper", "Paper towels", "Receipts", "Wax paper"]},
    "Glass": {"recyclable": True, "rinse": True, "crush": False, "special": "Separate by color if required",
              "items": ["Bottles", "Jars", "Food containers"],
              "not_recyclable": ["Window glass", "Mirrors", "Pyrex", "Light bulbs", "Ceramics"]},
    "Metal": {"recyclable": True, "rinse": True, "crush": True, "special": "Remove food residue",
              "items": ["Aluminum cans", "Steel cans", "Tin cans", "Clean foil"],
              "not_recyclable": ["Aerosol cans (if full)", "Paint cans", "Propane tanks"]},
    "Organic": {"recyclable": "Compostable", "rinse": False, "crush": False, "special": "Green bin",
                "items": ["Fruit/vegetable scraps", "Coffee grounds", "Eggshells", "Yard waste", "Food scraps"],
                "not_recyclable": ["Meat/dairy (some systems)", "Cooking oil", "Pet waste"]},
    "E-Waste": {"recyclable": "Special drop-off", "rinse": False, "crush": False, "special": "Never trash!",
                "items": ["Batteries", "Phones", "Chargers", "Cables", "Computers", "TVs"],
                "not_recyclable": ["Smoke detectors", "Microwave ovens"]},
}

# ─── Waste Reduction Tips by Category ─────────────────────────────────────
REDUCTION_TIPS = {
    "Plastic": [
        {"tip": "Switch to reusable water bottle", "impact": "Saves 156 bottles/year", "difficulty": "Easy", "co2_saved": 8.5},
        {"tip": "Use beeswax wraps instead of cling film", "impact": "Eliminates 300ft of plastic wrap/year", "difficulty": "Easy", "co2_saved": 2.1},
        {"tip": "Buy in bulk with reusable containers", "impact": "Reduces packaging waste by 40%", "difficulty": "Medium", "co2_saved": 12.0},
        {"tip": "Switch to bar soap/shampoo", "impact": "Eliminates 2-3 plastic bottles/year", "difficulty": "Easy", "co2_saved": 1.5},
    ],
    "Paper": [
        {"tip": "Go paperless for bills and statements", "impact": "Saves 18 trees and 700 gallons of water/year", "difficulty": "Easy", "co2_saved": 4.2},
        {"tip": "Use cloth napkins instead of paper", "impact": "Saves ~5,000 napkins over lifetime", "difficulty": "Easy", "co2_saved": 3.0},
        {"tip": "Read news on devices instead of print", "impact": "Saves 24 newspapers/week = 125 lbs/year", "difficulty": "Easy", "co2_saved": 6.8},
    ],
    "Food/Organic": [
        {"tip": "Meal prep to reduce food waste", "impact": "Reduces food waste by 25-30%", "difficulty": "Medium", "co2_saved": 15.0},
        {"tip": "Compost food scraps at home", "impact": "Diverts 30% of household waste from landfill", "difficulty": "Easy", "co2_saved": 10.5},
        {"tip": "Use food-saving apps (Too Good To Go)", "impact": "Saves 200+ lbs of food/year", "difficulty": "Easy", "co2_saved": 8.0},
    ],
    "Metal": [
        {"tip": "Bring reusable coffee cup", "impact": "Saves 500+ disposable cups/year", "difficulty": "Easy", "co2_saved": 5.5},
        {"tip": "Use stainless steel straws", "impact": "Eliminates 584 plastic straws/year", "difficulty": "Easy", "co2_saved": 1.2},
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: SORT GUIDE
# ═══════════════════════════════════════════════════════════════════════════
def render_sort_guide():
    st.markdown("### 🗂️ Smart Waste Sort Guide")

    # Search & Filter
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 Search for an item...", placeholder="e.g., pizza box, battery, glass jar")
    with col2:
        category_filter = st.selectbox("Filter by disposal", ["All", "Recyclable", "Compostable", "Landfill",
                                                               "Hazardous Waste", "Special Recycling",
                                                               "Conditionally Recyclable"])

    filtered = WASTE_ITEMS
    if search:
        filtered = [item for item in filtered if search.lower() in item["name"].lower() or search.lower() in item["material"].lower()]
    if category_filter != "All":
        filtered = [item for item in filtered if category_filter.lower() in item["category"].lower()]

    # Stats
    cols = st.columns(4)
    for i, (label, value, color) in enumerate([
        ("Total Items", len(WASTE_ITEMS), "#8b5cf6"),
        ("Recyclable", sum(1 for i in WASTE_ITEMS if "Recyclable" in i["category"] and "Conditionally" not in i["category"]), "#22c55e"),
        ("Compostable", sum(1 for i in WASTE_ITEMS if "Compostable" in i["category"]), "#3b82f6"),
        ("Landfill Only", sum(1 for i in WASTE_ITEMS if "Landfill" in i["category"] and "Compostable" not in i["category"]), "#ef4444"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:14px;text-align:center;">
                <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Item cards
    for item in filtered:
        cat_icon = "♻️" if "Recyclable" in item["category"] and "Conditionally" not in item["category"] else \
                   "🌱" if "Compostable" in item["category"] else \
                   "☠️" if "Hazardous" in item["category"] else "🗑️"
        risk_color = {"Low": "#22c55e", "Medium": "#eab308", "High": "#f97316",
                      "Critical": "#ef4444", "None": "#22c55e"}.get(item["contamination_risk"].split(" ")[0], "#6b7280")

        with st.expander(f"{cat_icon} **{item['name']}** → {item['bin']} | Risk: :{risk_color}[{item['contamination_risk']}]", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**Material:** {item['material']}")
                st.markdown(f"**Decomposition:** {item['decomposition']}")
                st.markdown(f"**Prep:** {item['prep']}")
            with col2:
                st.markdown(f"**Recycling Rate:** {item['recycling_rate']}%")
                st.progress(item["recycling_rate"] / 100)
                st.markdown(f"**Category:** {item['category']}")
            with col3:
                st.info(f"💡 {item['fun_facts']}")
            st.markdown(f"**🗑️ Bin:** {item['bin']} | **⚠️ Contamination Risk:** {item['contamination_risk']}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: RECYCLING RULES
# ═══════════════════════════════════════════════════════════════════════════
def render_recycling_rules():
    st.markdown("### 📋 Recycling Rules by Material")

    # Category breakdown chart
    cat_counts = {}
    for item in WASTE_ITEMS:
        cat = item["category"].split(" / ")[0].split(" (")[0]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    fig = px.pie(values=list(cat_counts.values()), names=list(cat_counts.keys()),
                 title="Waste Item Distribution by Category",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(template="plotly_dark", height=350, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Material rules
    for material, rules in RECYCLING_RULES.items():
        with st.expander(f"{'✅' if rules['recyclable'] == True else '⚠️' if rules['recyclable'] != False else '❌'} **{material}** — {'Recyclable' if rules['recyclable'] == True else rules['recyclable']}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Rinse:** {'✅ Required' if rules['rinse'] else '❌ Not needed'}")
                st.markdown(f"**Crush:** {'✅ Recommended' if rules['crush'] else '❌ Not needed'}")
                st.markdown(f"**Special Note:** {rules['special']}")
                st.markdown("**✅ Acceptable Items:**")
                for item_name in rules["items"]:
                    st.markdown(f"  • {item_name}")
            with col2:
                st.markdown("**❌ Non-Recyclable Items:**")
                for item_name in rules["not_recyclable"]:
                    st.markdown(f"  • {item_name}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 3: CONTAMINATION DETECTOR
# ═══════════════════════════════════════════════════════════════════════════
def render_contamination():
    st.markdown("### ⚠️ Contamination Detector")

    # Severity breakdown
    sev_counts = {}
    for s in CONTAMINATION_SCENARIOS:
        sev = s["severity"]
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    cols = st.columns(4)
    for i, (label, value, color) in enumerate([
        ("Scenarios", len(CONTAMINATION_SCENARIOS), "#8b5cf6"),
        ("Critical", sev_counts.get("Critical", 0), "#ef4444"),
        ("High Risk", sev_counts.get("High", 0), "#f97316"),
        ("Safe Actions", sev_counts.get("None", 0), "#22c55e"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:14px;text-align:center;">
                <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Interactive scenario quiz
    st.markdown("#### 🧪 Interactive Contamination Quiz")
    selected_scenario = st.selectbox("Pick a contamination scenario to analyze:",
                                     [s["scenario"] for s in CONTAMINATION_SCENARIOS])

    scenario = next(s for s in CONTAMINATION_SCENARIOS if s["scenario"] == selected_scenario)
    severity_color = {"Critical": "#ef4444", "High": "#f97316", "Medium": "#eab308", "None": "#22c55e"}

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                border:2px solid {severity_color[scenario['severity']]}40;border-radius:16px;padding:24px;">
        <div style="font-size:20px;font-weight:700;color:{severity_color[scenario['severity']]};">
            {scenario['scenario']}
        </div>
        <div style="margin-top:12px;">
            <div style="color:#94a3b8;"><strong>Contaminant:</strong> {scenario['contaminant']}</div>
            <div style="color:#e2e8f0;margin-top:8px;"><strong>Impact:</strong> {scenario['impact']}</div>
            <div style="color:#22c55e;margin-top:8px;"><strong>✅ Correct Action:</strong> {scenario['correct_action']}</div>
            <div style="color:#f97316;margin-top:8px;"><strong>💸 Cost of Mistake:</strong> {scenario['cost_of_mistake']}</div>
            <div style="margin-top:8px;"><strong>Severity:</strong>
                <span style="color:{severity_color[scenario['severity']]};font-weight:700;">
                    {scenario['severity']}</span></div>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # All scenarios list
    st.markdown("#### 📋 All Contamination Scenarios")
    for s in CONTAMINATION_SCENARIOS:
        sev_color = severity_color.get(s["severity"], "#6b7280")
        with st.expander(f"{'🔴' if s['severity'] == 'Critical' else '🟠' if s['severity'] == 'High' else '🟡' if s['severity'] == 'Medium' else '🟢'} {s['scenario']} [{s['severity']}]", expanded=False):
            st.markdown(f"**Impact:** {s['impact']}")
            st.markdown(f"**Correct Action:** {s['correct_action']}")
            st.markdown(f"**Cost of Mistake:** {s['cost_of_mistake']}")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 4: WASTE AUDIT
# ═══════════════════════════════════════════════════════════════════════════
def render_waste_audit():
    st.markdown("### 📊 30-Day Waste Audit")

    df = generate_waste_audit()

    # KPIs
    totals = {col: df[col].sum() for col in ["Paper/Cardboard", "Plastic", "Glass", "Metal", "Organic", "Landfill", "Hazardous"]}
    total_waste = sum(totals.values())
    recycle_rate = (totals["Paper/Cardboard"] + totals["Plastic"] + totals["Glass"] + totals["Metal"]) / total_waste * 100
    compost_rate = totals["Organic"] / total_waste * 100
    landfill_rate = totals["Landfill"] / total_waste * 100

    cols = st.columns(5)
    for i, (label, value, color) in enumerate([
        ("Total Items", f"{total_waste}", "#8b5cf6"),
        ("Recycle Rate", f"{recycle_rate:.1f}%", "#22c55e"),
        ("Compost Rate", f"{compost_rate:.1f}%", "#3b82f6"),
        ("Landfill Rate", f"{landfill_rate:.1f}%", "#ef4444"),
        ("Avg/Day", f"{total_waste/30:.1f}", "#f97316"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:14px;text-align:center;">
                <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Stacked area chart
    fig = go.Figure()
    colors = {"Paper/Cardboard": "#3b82f6", "Plastic": "#ef4444", "Glass": "#22c55e",
              "Metal": "#8b5cf6", "Organic": "#f97316", "Landfill": "#6b7280", "Hazardous": "#ec4899"}
    for col in ["Paper/Cardboard", "Plastic", "Glass", "Metal", "Organic", "Landfill", "Hazardous"]:
        fig.add_trace(go.Scatter(x=df["Date"], y=df[col], name=col, stackgroup="one",
                                 line=dict(color=colors[col], width=0.5)))
    fig.update_layout(title="Daily Waste by Category (Stacked)", template="plotly_dark",
                      height=400, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#e2e8f0"), yaxis_title="Items")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        # Pie chart
        pie_df = pd.DataFrame(list(totals.items()), columns=["Category", "Count"])
        fig = px.pie(pie_df, values="Count", names="Category", title="30-Day Waste Composition",
                     color_discrete_sequence=list(colors.values()))
        fig.update_layout(template="plotly_dark", height=350, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Category bar chart
        fig = px.bar(pie_df, x="Category", y="Count", title="Total by Category",
                     color="Category", color_discrete_sequence=list(colors.values()))
        fig.update_layout(template="plotly_dark", height=350, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Daily trend
    daily_total = df[["Paper/Cardboard", "Plastic", "Glass", "Metal", "Organic", "Landfill", "Hazardous"]].sum(axis=1)
    df["Total"] = daily_total
    fig = px.line(df, x="Date", y="Total", title="Daily Total Waste Trend",
                  markers=True, color_discrete_sequence=["#8b5cf6"])
    fig.update_layout(template="plotly_dark", height=300, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# TAB 5: REDUCTION TIPS
# ═══════════════════════════════════════════════════════════════════════════
def render_reduction_tips():
    st.markdown("### 💡 Waste Reduction Action Plan")

    total_co2 = sum(tip["co2_saved"] for tips in REDUCTION_TIPS.values() for tip in tips)
    total_tips = sum(len(tips) for tips in REDUCTION_TIPS.values())
    easy_count = sum(1 for tips in REDUCTION_TIPS.values() for tip in tips if tip["difficulty"] == "Easy")

    cols = st.columns(4)
    for i, (label, value, color) in enumerate([
        ("Action Tips", total_tips, "#8b5cf6"),
        ("CO₂ Savings", f"{total_co2:.1f}kg", "#22c55e"),
        ("Easy Wins", easy_count, "#3b82f6"),
        ("Categories", len(REDUCTION_TIPS), "#f97316"),
    ]):
        with cols[i]:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.05),rgba(255,255,255,0.02));
                        border:1px solid {color}30;border-radius:12px;padding:14px;text-align:center;">
                <div style="font-size:22px;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:11px;color:#94a3b8;margin-top:4px;">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # CO2 savings chart
    tip_data = []
    for cat, tips in REDUCTION_TIPS.items():
        for tip in tips:
            tip_data.append({"Category": cat, "Action": tip["tip"][:30], "CO₂ Saved (kg)": tip["co2_saved"],
                             "Difficulty": tip["difficulty"]})
    tip_df = pd.DataFrame(tip_data)
    fig = px.bar(tip_df, x="Action", y="CO₂ Saved (kg)", color="Category",
                 title="CO₂ Savings by Action", barmode="group",
                 color_discrete_sequence=px.colors.qualitative.Set2)
    fig.update_layout(template="plotly_dark", height=400, plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#e2e8f0"))
    st.plotly_chart(fig, use_container_width=True)

    # Tip cards by category
    for category, tips in REDUCTION_TIPS.items():
        st.markdown(f"#### 🏷️ {category}")
        for tip in tips:
            diff_color = "#22c55e" if tip["difficulty"] == "Easy" else "#eab308"
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,rgba(255,255,255,0.04),rgba(255,255,255,0.01));
                        border:1px solid rgba(139,92,246,0.2);border-radius:12px;padding:16px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <strong style="color:#e2e8f0;">{tip['tip']}</strong>
                        <div style="color:#94a3b8;font-size:12px;margin-top:4px;">{tip['impact']}</div>
                    </div>
                    <div style="text-align:right;">
                        <span style="color:#22c55e;font-weight:700;">-{tip['co2_saved']}kg CO₂</span>
                        <div style="color:{diff_color};font-size:11px;">{tip['difficulty']}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

    # Impact calculator
    st.markdown("---")
    st.markdown("#### 🧮 Your Impact Calculator")
    st.markdown("Select actions you'll commit to and see your projected savings:")

    selected_actions = []
    for category, tips in REDUCTION_TIPS.items():
        st.markdown(f"**{category}:**")
        cols = st.columns(len(tips))
        for j, tip in enumerate(tips):
            with cols[j]:
                if st.checkbox(tip["tip"][:30], key=f"tip_{category}_{j}"):
                    selected_actions.append(tip)

    if selected_actions:
        total_savings = sum(t["co2_saved"] for t in selected_actions)
        st.success(f"🌱 **Your Impact:** {len(selected_actions)} actions = **{total_savings:.1f}kg CO₂ saved/year**")
        st.metric("Annual CO₂ Reduction", f"-{total_savings:.1f}kg",
                  delta=f"Equivalent to {total_savings/22:.0f} trees planted")


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════════════════
def main():
    st.set_page_config(page_title="Smart Waste Sorting Assistant", page_icon="🗑️", layout="wide")

    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: rgba(255,255,255,0.03); border-radius: 12px; padding: 6px; }
    .stTabs [data-baseweb="tab"] { border-radius: 10px; padding: 10px 20px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #22c55e, #3b82f6); color: white; }
    .stExpander { background: rgba(255,255,255,0.02); border: 1px solid rgba(34,197,94,0.2); border-radius: 10px; }
    h1 { background: linear-gradient(135deg, #22c55e, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    h2 { background: linear-gradient(135deg, #22c55e, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    </style>""", unsafe_allow_html=True)

    st.markdown("# 🗑️ Smart Waste Sorting Assistant")
    st.markdown("Classify waste items, learn recycling rules, detect contamination, audit your waste, and reduce your impact.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗂️ Sort Guide", "📋 Recycling Rules", "⚠️ Contamination", "📊 Waste Audit", "💡 Reduction Tips"
    ])

    with tab1:
        render_sort_guide()
    with tab2:
        render_recycling_rules()
    with tab3:
        render_contamination()
    with tab4:
        render_waste_audit()
    with tab5:
        render_reduction_tips()


if __name__ == "__main__":
    main()
