"""
pages/Smart_Waste_Sorter.py
---------------------------
Streamlit page: Smart Waste Sorting Assistant.

Classify waste items, get recycling guidance, detect contamination risks,
find nearby disposal facilities, and track waste reduction progress.
"""

import re
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Smart Waste Sorter",
    page_icon="♻️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Waste database
# ---------------------------------------------------------------------------

WASTE_CATEGORIES = {
    "Recyclable": {
        "color": "#28a745",
        "icon": "♻️",
        "items": {
            "Paper": {
                "items": ["Newspaper", "Magazine", "Cardboard box", "Office paper", "Junk mail",
                          "Paper bag", "Cereal box", "Egg carton", "Paper towel (clean)", "Notebook"],
                "bin_color": "🔵 Blue",
                "tips": "Remove tape and staples. Keep dry and clean. Flatten cardboard boxes.",
                "contamination": ["Greasy pizza box", "Wax-coated paper", "Tissue paper", "Laminated paper"],
                "decomposition": "2-6 weeks",
                "recycling_rate": "68%",
                "co2_saved_per_kg": 3.1,
            },
            "Plastic": {
                "items": ["PET bottle (#1)", "HDPE container (#2)", "Plastic jug", "Shampoo bottle",
                          "Detergent bottle", "Yogurt cup (#5)", "Plastic container (#5)", "Plastic cap"],
                "bin_color": "🔵 Blue",
                "tips": "Rinse containers. Check the recycling number (#1-7). Remove caps if possible.",
                "contamination": ["Plastic wrap", "Styrofoam (#6)", "Plastic bag", "Coffee cup lid", "Cling film"],
                "decomposition": "450-1000 years",
                "recycling_rate": "9%",
                "co2_saved_per_kg": 1.5,
            },
            "Glass": {
                "items": ["Glass bottle", "Glass jar", "Wine bottle", "Beer bottle", "Jam jar",
                          "Glass container", "Perfume bottle"],
                "bin_color": "🟢 Green",
                "tips": "Rinse out contents. Remove metal lids. Sort by color if required.",
                "contamination": ["Window glass", "Mirror", "Light bulb", "Ceramic", "Pyrex"],
                "decomposition": "1 million+ years",
                "recycling_rate": "31%",
                "co2_saved_per_kg": 0.3,
            },
            "Metal": {
                "items": ["Aluminum can", "Tin can", "Steel can", "Aluminum foil (clean)",
                          "Metal lid", "Clean paint can", "Aerosol can (empty)"],
                "bin_color": "🔵 Blue",
                "tips": "Rinse cans. Remove labels if possible. Flatten aluminum cans.",
                "contamination": ["Painted/contaminated metal", "Medical sharps", "Battery"],
                "decomposition": "80-200 years",
                "recycling_rate": "50%",
                "co2_saved_per_kg": 9.0,
            },
            "Cardboard": {
                "items": ["Corrugated box", "Pizza box (clean)", "Shoe box", "Toilet paper roll",
                          "Paper towel roll", "Shipping box"],
                "bin_color": "🔵 Blue",
                "tips": "Flatten all boxes. Remove tape and staples. Keep dry.",
                "contamination": ["Greasy/wet cardboard", "Wax-coated cardboard", "Laminated cardboard"],
                "decomposition": "2 months",
                "recycling_rate": "96%",
                "co2_saved_per_kg": 3.2,
            },
        },
    },
    "Organic": {
        "color": "#8B4513",
        "icon": "🟤",
        "items": {
            "Food Waste": {
                "items": ["Fruit peel", "Vegetable scraps", "Coffee grounds", "Tea bags",
                          "Eggshells", "Bread", "Leftover food", "Rice", "Pasta"],
                "bin_color": "🟢 Green (Compost)",
                "tips": "Use compostable bags. Remove any plastic packaging. Meat scraps OK in commercial compost.",
                "contamination": ["Plastic packaging", "Metal twist ties", "Rubber bands"],
                "decomposition": "2-6 months (compost)",
                "recycling_rate": "composted",
                "co2_saved_per_kg": 0.5,
            },
            "Yard Waste": {
                "items": ["Leaves", "Grass clippings", "Small branches", "Flowers",
                          "Weeds", "Wood chips", "Plant trimmings"],
                "bin_color": "🟢 Green (Compost)",
                "tips": "Bundle branches. Keep separate from trash. Check local collection schedule.",
                "contamination": ["Treated wood", "Plastic plant pots", "Chemical-treated plants"],
                "decomposition": "3-12 months",
                "recycling_rate": "composted",
                "co2_saved_per_kg": 0.3,
            },
            "Wood": {
                "items": ["Untreated lumber", "Wooden pallet", "Branches", "Firewood",
                          "Wooden furniture (untreated)"],
                "bin_color": "🟤 Brown",
                "tips": "No treated/painted wood. Cut to manageable sizes. Check yard waste limits.",
                "contamination": ["Treated/painted wood", "Particle board", "Plywood"],
                "decomposition": "1-5 years",
                "recycling_rate": "40%",
                "co2_saved_per_kg": 1.8,
            },
        },
    },
    "Hazardous": {
        "color": "#dc3545",
        "icon": "🔴",
        "items": {
            "Batteries": {
                "items": ["AA battery", "AAA battery", "9V battery", "Coin cell",
                          "Rechargeable battery", "Lithium battery", "Phone battery"],
                "bin_color": "🔴 Special Collection",
                "tips": "NEVER put in regular trash. Tape terminals to prevent fires. Take to collection point.",
                "contamination": [],
                "decomposition": "Never (toxic)",
                "recycling_rate": "5%",
                "co2_saved_per_kg": 15.0,
            },
            "Electronics": {
                "items": ["Old phone", "Broken laptop", "TV", "Monitor", "Printer",
                          "Cables", "Charger", "Mouse", "Keyboard", "Tablet"],
                "bin_color": "🔴 E-Waste Collection",
                "tips": "Wipe personal data. Find certified e-waste recycler. Many stores accept returns.",
                "contamination": [],
                "decomposition": "1000+ years (toxic leaching)",
                "recycling_rate": "17%",
                "co2_saved_per_kg": 20.0,
            },
            "Chemicals": {
                "items": ["Paint", "Solvent", "Pesticide", "Motor oil", "Antifreeze",
                          "Cleaning chemicals", "Pool chemicals", "Propane tank"],
                "bin_color": "🔴 Hazardous Waste Facility",
                "tips": "Keep in original containers. Never mix chemicals. Take to HHW collection event.",
                "contamination": [],
                "decomposition": "Varies (highly toxic)",
                "recycling_rate": "specialized",
                "co2_saved_per_kg": 8.0,
            },
            "Medical": {
                "items": ["Expired medicine", "Syringes", "Bandages", "Thermometer (mercury)",
                          "Medical gloves", "Sharps"],
                "bin_color": "🔴 Pharmacy/Medical Waste",
                "tips": "Never flush medicines. Use sharps containers. Return to pharmacy take-back programs.",
                "contamination": [],
                "decomposition": "Varies",
                "recycling_rate": "specialized",
                "co2_saved_per_kg": 5.0,
            },
        },
    },
    "General Waste": {
        "color": "#6c757d",
        "icon": "⬛",
        "items": {
            "Non-Recyclable": {
                "items": ["Chip bag", "Candy wrapper", "Styrofoam cup", "Styrofoam packing",
                          "Plastic-coated paper", "Diaper", "Sanitary product", "Dental floss",
                          "Broken ceramics", "Shattered mirror"],
                "bin_color": "⬛ Black (Landfill)",
                "tips": "Minimize use. Consider alternatives. Check if any components can be recycled.",
                "contamination": [],
                "decomposition": "Varies (20-500+ years)",
                "recycling_rate": "0%",
                "co2_saved_per_kg": 0.0,
            },
        },
    },
    "Special": {
        "color": "#6f42c1",
        "icon": "🟣",
        "items": {
            "Textiles": {
                "items": ["Old clothes", "Towels", "Sheets", "Shoes", "Bags",
                          "Fabric scraps", "Curtains"],
                "bin_color": "🟣 Donation/Textile Bin",
                "tips": "Donate wearable items. Textile recycling for worn-out items. Many stores accept old clothes.",
                "contamination": ["Heavily contaminated fabrics", "Asbestos-containing materials"],
                "decomposition": "1-5 months (natural), 20-200 years (synthetic)",
                "recycling_rate": "15%",
                "co2_saved_per_kg": 6.0,
            },
            "Food Packaging": {
                "items": ["Multi-layer pouch", "Tetra Pak", "Coffee capsule", "Chip bag",
                          "Plastic-lined paper cup", "Straw", "Plastic utensil"],
                "bin_color": "⬛ Landfill (most) / Special programs",
                "tips": "Check TerraCycle programs. Some brands have take-back. Tetra Pak may be recyclable locally.",
                "contamination": [],
                "decomposition": "20-500 years",
                "recycling_rate": "<5%",
                "co2_saved_per_kg": 1.0,
            },
        },
    },
}

# Build flat lookup
ITEM_LOOKUP: dict[str, dict] = {}
for cat_name, cat_data in WASTE_CATEGORIES.items():
    for subcat_name, subcat_data in cat_data["items"].items():
        for item in subcat_data["items"]:
            ITEM_LOOKUP[item.lower()] = {
                "category": cat_name,
                "subcategory": subcat_name,
                "color": cat_data["color"],
                "icon": cat_data["icon"],
                "bin_color": subcat_data["bin_color"],
                "tips": subcat_data["tips"],
                "decomposition": subcat_data["decomposition"],
                "recycling_rate": subcat_data["recycling_rate"],
                "co2_saved_per_kg": subcat_data["co2_saved_per_kg"],
            }


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _generate_mock_disposal_sites() -> list[dict[str, Any]]:
    """Generate mock disposal facility data."""
    return [
        {"name": "City Recycling Center", "type": "Recycling", "distance_km": 2.3, "rating": 4.5,
         "accepts": ["Paper", "Plastic", "Glass", "Metal", "Cardboard"], "hours": "Mon-Sat 8AM-6PM",
         "address": "123 Green Street"},
        {"name": "EcoDrop Hazardous Waste", "type": "Hazardous", "distance_km": 5.1, "rating": 4.8,
         "accepts": ["Batteries", "Electronics", "Chemicals", "Paint"], "hours": "Sat 9AM-3PM",
         "address": "456 Safety Ave"},
        {"name": "Community Compost Hub", "type": "Composting", "distance_km": 1.8, "rating": 4.3,
         "accepts": ["Food Waste", "Yard Waste", "Wood"], "hours": "Daily 7AM-7PM",
         "address": "789 Garden Lane"},
        {"name": "TechRecycle Electronics", "type": "E-Waste", "distance_km": 3.7, "rating": 4.7,
         "accepts": ["Electronics", "Cables", "Batteries"], "hours": "Mon-Fri 10AM-5PM",
         "address": "321 Circuit Road"},
        {"name": "Goodwill Donation Center", "type": "Donation", "distance_km": 1.2, "rating": 4.2,
         "accepts": ["Textiles", "Clothes", "Shoes", "Bags"], "hours": "Mon-Sat 9AM-8PM",
         "address": "555 Charity Blvd"},
        {"name": "Municipal Transfer Station", "type": "Landfill", "distance_km": 8.5, "rating": 3.8,
         "accepts": ["General Waste", "Construction"], "hours": "Mon-Sat 7AM-5PM",
         "address": "999 Industrial Way"},
    ]


def _generate_mock_waste_log() -> list[dict[str, Any]]:
    """Generate mock waste tracking log."""
    import random
    random.seed(44)

    items = list(ITEM_LOOKUP.keys())
    log = []
    for i in range(50):
        item = random.choice(items)
        info = ITEM_LOOKUP.get(item, {})
        log.append({
            "date": (datetime.now() - timedelta(days=random.randint(0, 60))).strftime("%Y-%m-%d"),
            "item": item.title(),
            "category": info.get("category", "General"),
            "weight_kg": round(random.uniform(0.05, 2.5), 2),
            "properly_sorted": random.choices([True, False], weights=[85, 15], k=1)[0],
        })
    return log


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _render_overview(log: list[dict]):
    """Render waste sorting overview."""
    st.subheader("📊 Waste Overview")

    total = len(log)
    total_weight = sum(l["weight_kg"] for l in log)
    properly = sum(1 for l in log if l["properly_sorted"])
    sort_rate = (properly / total * 100) if total else 0
    recyclable = sum(1 for l in log if l["category"] == "Recyclable")
    organic = sum(1 for l in log if l["category"] == "Organic")
    landfill = sum(1 for l in log if l["category"] == "General Waste")

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Items", total)
    c2.metric("Total Weight", f"{total_weight:.1f} kg")
    c3.metric("Sort Accuracy", f"{sort_rate:.0f}%")
    c4.metric("♻️ Recyclable", recyclable)
    c5.metric("🟤 Organic", organic)
    c6.metric("⬛ Landfill", landfill)

    st.markdown(
        f"Out of **{total}** items tracked, **{sort_rate:.0f}%** were sorted correctly. "
        f"**{recyclable}** items are recyclable, **{organic}** are organic, and **{landfill}** went to landfill."
    )
    if sort_rate < 80:
        st.warning(f"⚠️ Sort accuracy is **{sort_rate:.0f}%** — below the 80% target. Check the sorting guide below!")
    else:
        st.success(f"✅ Sort accuracy of **{sort_rate:.0f}%** — great job!")


def _render_item_classifier():
    """Render the waste item classifier/search."""
    st.subheader("🔍 Waste Item Classifier")

    search = st.text_input("Search for an item (e.g., 'plastic bottle', 'newspaper', 'battery')", placeholder="Type an item name...")

    if search:
        matches = []
        search_lower = search.lower()
        for item_key, info in ITEM_LOOKUP.items():
            if search_lower in item_key:
                matches.append((item_key.title(), info))

        if not matches:
            # Fuzzy: check subcategory names
            for cat_name, cat_data in WASTE_CATEGORIES.items():
                for subcat_name, subcat_data in cat_data["items"].items():
                    if search_lower in subcat_name.lower():
                        for item in subcat_data["items"][:3]:
                            matches.append((item, {
                                "category": cat_name,
                                "subcategory": subcat_name,
                                "color": cat_data["color"],
                                "icon": cat_data["icon"],
                                "bin_color": subcat_data["bin_color"],
                                "tips": subcat_data["tips"],
                                "decomposition": subcat_data["decomposition"],
                                "recycling_rate": subcat_data["recycling_rate"],
                                "co2_saved_per_kg": subcat_data["co2_saved_per_kg"],
                            }))

        if matches:
            st.success(f"Found **{len(matches)}** matching items:")
            for item_name, info in matches[:10]:
                with st.expander(f"{info['icon']} **{item_name}** — {info['category']}", expanded=True):
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Category", info["category"])
                    c2.metric("Bin", info["bin_color"])
                    c3.metric("Decomposition", info["decomposition"])
                    c4.metric("Recycling Rate", info["recycling_rate"])
                    st.info(f"💡 **Tips:** {info['tips']}")
                    if info["co2_saved_per_kg"] > 0:
                        st.markdown(f"🌍 **CO₂ saved if recycled:** {info['co2_saved_per_kg']} kg per kg")
        else:
            st.warning(f"No matches found for **{search}**. Try a different term or check the category browser below.")


def _render_category_browser():
    """Render the waste category browser."""
    st.subheader("🗂️ Waste Categories")

    for cat_name, cat_data in WASTE_CATEGORIES.items():
        total_items = sum(len(s["items"]) for s in cat_data["items"].values())
        with st.expander(f"{cat_data['icon']} **{cat_name}** — {total_items} items", expanded=False):
            for subcat_name, subcat_data in cat_data["items"].items():
                st.markdown(f"**{subcat_name}** ({subcat_data['bin_color']}):")
                items_str = ", ".join(subcat_data["items"][:8])
                if len(subcat_data["items"]) > 8:
                    items_str += f" +{len(subcat_data['items']) - 8} more"
                st.markdown(f"  {items_str}")

                if subcat_data["contamination"]:
                    contam = ", ".join(subcat_data["contamination"][:5])
                    st.markdown(f"  <span style='color:#dc3545;font-size:0.85em'>⚠️ NOT recyclable with these: {contam}</span>", unsafe_allow_html=True)

                st.caption(f"Tips: {subcat_data['tips']}")


def _render_contamination_detector():
    """Render contamination risk analysis."""
    st.subheader("⚠️ Contamination Detector")

    st.markdown("Select items to check for cross-contamination risks:")
    all_items = sorted(ITEM_LOOKUP.keys())
    selected = st.multiselect("Select items", [i.title() for i in all_items], max_selections=8)

    if not selected:
        st.info("Select items above to check for contamination risks.")
        return

    # Check for conflicts
    risks = []
    categories_found = set()
    for item in selected:
        info = ITEM_LOOKUP.get(item.lower(), {})
        cat = info.get("category", "")
        subcat = info.get("subcategory", "")
        categories_found.add(cat)

        # Check if this item is in any contamination list
        for cat_name, cat_data in WASTE_CATEGORIES.items():
            for subcat_name, subcat_data in cat_data["items"].items():
                if item.lower() in [c.lower() for c in subcat_data["contamination"]]:
                    risks.append({
                        "item": item,
                        "conflicts_with": subcat_name,
                        "category": cat_name,
                        "severity": "high" if cat_name == "Recyclable" else "medium",
                        "message": f"**{item}** should NOT be placed in {subcat_name} recycling",
                    })

    # Category mixing warnings
    if "Recyclable" in categories_found and "General Waste" in categories_found:
        risks.append({
            "item": "Mix",
            "conflicts_with": "General Waste + Recyclable",
            "category": "Sorting",
            "severity": "high",
            "message": "⚠️ Mixing recyclable and general waste contaminates the recyclable batch!",
        })

    if "Hazardous" in categories_found and len(categories_found) > 1:
        risks.append({
            "item": "Mix",
            "conflicts_with": "Non-hazardous items",
            "category": "Safety",
            "severity": "critical",
            "message": "🚨 Hazardous materials MUST be kept separate from all other waste types!",
        })

    if risks:
        for risk in risks:
            icon = "🔴" if risk["severity"] in ("high", "critical") else "🟡"
            st.error(f"{icon} {risk['message']}")
    else:
        st.success("✅ No contamination risks detected for the selected items.")

    # Sorting summary
    st.markdown("**Sorting Guide for Selected Items:**")
    for item in selected:
        info = ITEM_LOOKUP.get(item.lower(), {})
        st.markdown(
            f'<div style="border-left:3px solid {info.get("color", "#666")};padding:6px 10px;margin:4px 0;background:#f8f9fa;border-radius:3px">'
            f'{info.get("icon", "📦")} **{item}** → {info.get("bin_color", "Check locally")} '
            f'<span style="color:#666;font-size:0.82em">({info.get("category", "Unknown")})</span></div>',
            unsafe_allow_html=True,
        )


def _render_disposal_finder(sites: list[dict]):
    """Render nearby disposal facility finder."""
    st.subheader("📍 Disposal Facility Finder")

    type_filter = st.multiselect(
        "Filter by type",
        list(set(s["type"] for s in sites)),
        default=list(set(s["type"] for s in sites)),
    )

    filtered = [s for s in sites if s["type"] in type_filter]
    filtered.sort(key=lambda x: x["distance_km"])

    for site in filtered:
        type_colors = {
            "Recycling": "#28a745", "Hazardous": "#dc3545", "Composting": "#8B4513",
            "E-Waste": "#fd7e14", "Donation": "#6f42c1", "Landfill": "#6c757d",
        }
        color = type_colors.get(site["type"], "#666")

        with st.expander(f"📍 **{site['name']}** — {site['distance_km']} km away", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("Type", site["type"])
            c2.metric("Distance", f"{site['distance_km']} km")
            c3.metric("Rating", f"⭐ {site['rating']}")

            st.markdown(f"**Address:** {site['address']}")
            st.markdown(f"**Hours:** {site['hours']}")
            accepts_str = ", ".join(site["accepts"])
            st.markdown(f"**Accepts:** {accepts_str}")


def _render_waste_tips():
    """Render waste reduction tips and facts."""
    st.subheader("💡 Waste Reduction Tips")

    tips = [
        {"title": "🔄 Refuse First", "text": "The best waste is waste never created. Refuse single-use items and bring reusable alternatives.", "impact": "Reduces waste by 40-60%"},
        {"title": "🛒 Smart Shopping", "text": "Buy in bulk, choose minimal packaging, bring reusable bags. Avoid products with excessive plastic wrap.", "impact": "Reduces packaging waste by 30%"},
        {"title": "🍱 Meal Planning", "text": "Plan meals to reduce food waste. Use leftovers creatively. Compost unavoidable food scraps.", "impact": "Reduces food waste by 50%"},
        {"title": "📦 Packaging Awareness", "text": "Choose products with recyclable packaging. Glass > Metal > Paper > Plastic.", "impact": "Improves recycling rate by 25%"},
        {"title": "🧹 Clean Recycling", "text": "Rinse containers, remove food residue. Contaminated recycling gets sent to landfill.", "impact": "Prevents 25% of recycling from being landfilled"},
        {"title": "📱 Digital First", "text": "Go paperless for bills, notes, and documents. Use digital alternatives.", "impact": "Saves 500+ sheets per person per year"},
        {"title": "🪴 Compost at Home", "text": "Start a compost bin for food scraps and yard waste. Returns nutrients to soil.", "impact": "Diverts 30% of household waste from landfill"},
        {"title": "🧵 Repair & Reuse", "text": "Fix broken items before replacing. Donate usable items. Buy secondhand.", "impact": "Extends product life by 50%"},
    ]

    for tip in tips:
        st.markdown(
            f'<div style="border:1px solid #333;border-radius:8px;padding:12px;margin:8px 0;background:#0d1117">'
            f'<strong style="color:#28a745">{tip["title"]}</strong><br/>'
            f'{tip["text"]}<br/>'
            f'<span style="color:#4a90d9;font-size:0.85em">📈 Impact: {tip["impact"]}</span></div>',
            unsafe_allow_html=True,
        )

    # Fun facts
    st.markdown("---")
    st.subheader("🌍 Did You Know?")
    facts = [
        "The average person generates 4.5 lbs of waste per day in the US.",
        "Only 9% of all plastic ever produced has been recycled.",
        "A glass bottle takes 1 million years to decompose in a landfill.",
        "Recycling one aluminum can saves enough energy to run a TV for 3 hours.",
        "Food waste in landfills produces methane, a greenhouse gas 25x more potent than CO₂.",
        "The Great Pacific Garbage Patch is 3x the size of France.",
        "Paper can be recycled up to 7 times before fibers become too short.",
        "E-waste represents only 2% of trash but equals 70% of toxic waste.",
    ]
    for fact in facts:
        st.markdown(f"- 🌟 {fact}")


def _render_waste_analytics(log: list[dict]):
    """Render waste sorting analytics and trends."""
    st.subheader("📈 Waste Analytics")

    # Category distribution
    cat_counts = {}
    for l in log:
        cat_counts[l["category"]] = cat_counts.get(l["category"], 0) + 1

    st.markdown("**Waste by Category:**")
    colors = {"Recyclable": "#28a745", "Organic": "#8B4513", "Hazardous": "#dc3545", "General Waste": "#6c757d", "Special": "#6f42c1"}
    max_count = max(cat_counts.values()) if cat_counts else 1
    for cat, count in sorted(cat_counts.items(), key=lambda x: x[1], reverse=True):
        pct = count / max_count * 100
        color = colors.get(cat, "#666")
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:4px 0">'
            f'<span style="width:120px;font-size:0.88em">{cat}</span>'
            f'<div style="width:50%;background:#1e1e2e;border-radius:4px;height:16px">'
            f'<div style="width:{pct:.0f}%;background:{color};border-radius:4px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.85em">{count} items</span></div>',
            unsafe_allow_html=True,
        )

    # Sorting accuracy over time
    st.markdown("**Sorting Accuracy Over Time:**")
    weekly = {}
    for l in log:
        day = datetime.strptime(l["date"], "%Y-%m-%d")
        wk = day.strftime("%Y-W%U")
        weekly.setdefault(wk, {"total": 0, "correct": 0})
        weekly[wk]["total"] += 1
        if l["properly_sorted"]:
            weekly[wk]["correct"] += 1

    for wk in sorted(weekly.keys())[-8:]:
        total = weekly[wk]["total"]
        correct = weekly[wk]["correct"]
        acc = correct / total * 100 if total else 0
        color = "#28a745" if acc >= 80 else "#ffc107" if acc >= 60 else "#dc3545"
        st.markdown(
            f'<div style="display:flex;align-items:center;margin:3px 0">'
            f'<span style="width:100px;font-size:0.85em">{wk}</span>'
            f'<div style="width:40%;background:#1e1e2e;border-radius:3px;height:14px">'
            f'<div style="width:{acc:.0f}%;background:{color};border-radius:3px;height:100%"></div></div>'
            f'<span style="margin-left:8px;font-size:0.82em">{correct}/{total} correct ({acc:.0f}%)</span></div>',
            unsafe_allow_html=True,
        )

    # Export
    csv = pd.DataFrame(log).to_csv(index=False)
    st.download_button("📥 Export Waste Log (CSV)", csv, file_name="waste_log.csv", mime="text/csv")


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def render_smart_waste_sorter():
    """Render the Smart Waste Sorter page."""
    st.title("♻️ Smart Waste Sorter")
    st.markdown(
        "Classify waste items, get recycling guidance, find disposal facilities, and track your sorting accuracy."
    )

    log = _generate_mock_waste_log()
    sites = _generate_mock_disposal_sites()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        show_overview = st.checkbox("Overview", True)
        show_classifier = st.checkbox("Item Classifier", True)
        show_categories = st.checkbox("Category Browser", True)
        show_contamination = st.checkbox("Contamination Detector", True)
        show_disposal = st.checkbox("Disposal Finder", True)
        show_tips = st.checkbox("Tips & Facts", True)
        show_analytics = st.checkbox("Analytics", True)

    if show_overview:
        _render_overview(log)

    if show_classifier:
        st.markdown("---")
        _render_item_classifier()

    if show_categories:
        st.markdown("---")
        _render_category_browser()

    if show_contamination:
        st.markdown("---")
        _render_contamination_detector()

    if show_disposal:
        st.markdown("---")
        _render_disposal_finder(sites)

    if show_tips:
        st.markdown("---")
        _render_waste_tips()

    if show_analytics:
        st.markdown("---")
        _render_waste_analytics(log)

    st.markdown("---")
    total_items = sum(len(s["items"]) for cat in WASTE_CATEGORIES.values() for s in cat["items"].values())
    st.caption(f"Smart Waste Sorter | {total_items} items in database | {len(log)} items tracked | Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# Entry point
if __name__ == "__main__" or True:
    render_smart_waste_sorter()
