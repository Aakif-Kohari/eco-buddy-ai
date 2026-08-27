"""Meal Carbon Footprint Calculator – Analyze the carbon footprint of your meals, compare ingredients, discover low-carbon alternatives, and track your dietary environmental impact."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
import math

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meal Carbon Calculator", page_icon="🍽️", layout="wide")

# ─── Theme ──────────────────────────────────────────────────────────────────
try:
    from styles.theme import apply_theme
    apply_theme()
except Exception:
    pass

# ─── Carbon Footprint Database (kg CO₂e per kg of food) ────────────────────
FOOD_CATEGORIES = {
    "meat_beef": {"label": "🥩 Beef", "color": "#dc2626", "co2_per_kg": 27.0, "water_per_kg": 15400, "land_per_kg": 164},
    "meat_lamb": {"label": "🐑 Lamb", "color": "#f97316", "co2_per_kg": 24.0, "water_per_kg": 10400, "land_per_kg": 185},
    "meat_pork": {"label": "🐷 Pork", "color": "#f59e0b", "co2_per_kg": 7.2, "water_per_kg": 5990, "land_per_kg": 11},
    "meat_chicken": {"label": "🐔 Chicken", "color": "#eab308", "co2_per_kg": 6.1, "water_per_kg": 4325, "land_per_kg": 7.1},
    "meat_turkey": {"label": "🦃 Turkey", "color": "#a16207", "co2_per_kg": 5.5, "water_per_kg": 4000, "land_per_kg": 6.5},
    "fish_farmed": {"label": "🐟 Farmed Fish", "color": "#0ea5e9", "co2_per_kg": 5.1, "water_per_kg": 3500, "land_per_kg": 3.7},
    "fish_wild": {"label": "🐠 Wild Fish", "color": "#0284c7", "co2_per_kg": 3.5, "water_per_kg": 2800, "land_per_kg": 2.0},
    "eggs": {"label": "🥚 Eggs", "color": "#d97706", "co2_per_kg": 4.2, "water_per_kg": 3300, "land_per_kg": 3.5},
    "dairy_milk": {"label": "🥛 Milk", "color": "#fbbf24", "co2_per_kg": 3.2, "water_per_kg": 6280, "land_per_kg": 8.9},
    "dairy_cheese": {"label": "🧀 Cheese", "color": "#facc15", "co2_per_kg": 13.5, "water_per_kg": 5060, "land_per_kg": 87},
    "dairy_yogurt": {"label": "🥛 Yogurt", "color": "#fde047", "co2_per_kg": 2.2, "water_per_kg": 2500, "land_per_kg": 3.5},
    "rice": {"label": "🍚 Rice", "color": "#a3a3a3", "co2_per_kg": 2.7, "water_per_kg": 2500, "land_per_kg": 2.8},
    "wheat": {"label": "🌾 Wheat/ Bread", "color": "#ca8a04", "co2_per_kg": 1.4, "water_per_kg": 1827, "land_per_kg": 3.4},
    "pasta": {"label": "🍝 Pasta", "color": "#eab308", "co2_per_kg": 1.2, "water_per_kg": 1600, "land_per_kg": 2.5},
    "potatoes": {"label": "🥔 Potatoes", "color": "#a16207", "co2_per_kg": 0.5, "water_per_kg": 287, "land_per_kg": 0.8},
    "vegetables": {"label": "🥬 Vegetables", "color": "#22c55e", "co2_per_kg": 0.7, "water_per_kg": 322, "land_per_kg": 0.3},
    "fruits": {"label": "🍎 Fruits", "color": "#ef4444", "co2_per_kg": 0.8, "water_per_kg": 450, "land_per_kg": 0.5},
    "nuts": {"label": "🥜 Nuts", "color": "#92400e", "co2_per_kg": 2.3, "water_per_kg": 4000, "land_per_kg": 2.0},
    "tofu": {"label": "🧊 Tofu", "color": "#d4d4d8", "co2_per_kg": 2.0, "water_per_kg": 2500, "land_per_kg": 2.2},
    "legumes": {"label": "🫘 Legumes", "color": "#65a30d", "co2_per_kg": 0.9, "water_per_kg": 4055, "land_per_kg": 7.4},
    "oils": {"label": "🫒 Oils & Fats", "color": "#eab308", "co2_per_kg": 3.5, "water_per_kg": 1500, "land_per_kg": 1.5},
    "sugar": {"label": "🍬 Sugar", "color": "#fda4af", "co2_per_kg": 1.8, "water_per_kg": 1770, "land_per_kg": 2.5},
    "coffee": {"label": "☕ Coffee", "color": "#78350f", "co2_per_kg": 16.0, "water_per_kg": 18900, "land_per_kg": 12},
    "chocolate": {"label": "🍫 Chocolate", "color": "#7c2d12", "co2_per_kg": 21.0, "water_per_kg": 17000, "land_per_kg": 12},
    "wine": {"label": "🍷 Wine", "color": "#9f1239", "co2_per_kg": 1.5, "water_per_kg": 870, "land_per_kg": 0.8},
    "beer": {"label": "🍺 Beer", "color": "#ca8a04", "co2_per_kg": 0.8, "water_per_kg": 300, "land_per_kg": 0.5},
}

SAMPLE_RECIPES = {
    "Beef Burger": {
        "ingredients": {"meat_beef": 0.2, "wheat": 0.15, "vegetables": 0.1, "dairy_cheese": 0.05, "oils": 0.02},
        "servings": 1, "prep_time": 15, "cook_time": 20,
        "description": "Classic beef burger with cheese, lettuce, tomato on a sesame bun",
        "cuisine": "American",
    },
    "Chicken Stir-Fry": {
        "ingredients": {"meat_chicken": 0.25, "rice": 0.15, "vegetables": 0.2, "oils": 0.03, "tofu": 0.05},
        "servings": 2, "prep_time": 10, "cook_time": 15,
        "description": "Quick chicken and vegetable stir-fry with steamed rice",
        "cuisine": "Asian",
    },
    "Vegetable Pasta": {
        "ingredients": {"pasta": 0.2, "vegetables": 0.3, "oils": 0.03, "tomatoes": 0.1},
        "servings": 2, "prep_time": 5, "cook_time": 15,
        "description": "Penne with roasted seasonal vegetables and olive oil",
        "cuisine": "Italian",
    },
    "Lentil Curry": {
        "ingredients": {"legumes": 0.2, "rice": 0.15, "vegetables": 0.15, "oils": 0.03},
        "servings": 3, "prep_time": 10, "cook_time": 25,
        "description": "Creamy red lentil curry with basmati rice",
        "cuisine": "Indian",
    },
    "Fish Tacos": {
        "ingredients": {"fish_wild": 0.2, "wheat": 0.1, "vegetables": 0.15, "oils": 0.02, "dairy_yogurt": 0.05},
        "servings": 2, "prep_time": 10, "cook_time": 10,
        "description": "Grilled fish tacos with cabbage slaw and lime crema",
        "cuisine": "Mexican",
    },
    "Tofu Buddha Bowl": {
        "ingredients": {"tofu": 0.2, "rice": 0.12, "vegetables": 0.25, "nuts": 0.03, "oils": 0.02},
        "servings": 1, "prep_time": 10, "cook_time": 15,
        "description": "Colorful bowl with crispy tofu, grains, and tahini dressing",
        "cuisine": "Fusion",
    },
    "Lamb Kofta": {
        "ingredients": {"meat_lamb": 0.25, "wheat": 0.1, "vegetables": 0.15, "yogurt": 0.05},
        "servings": 2, "prep_time": 15, "cook_time": 20,
        "description": "Spiced lamb kofta with flatbread and tzatziki",
        "cuisine": "Mediterranean",
    },
    "Veggie Burger": {
        "ingredients": {"legumes": 0.15, "wheat": 0.12, "vegetables": 0.15, "potatoes": 0.1},
        "servings": 1, "prep_time": 10, "cook_time": 15,
        "description": "Black bean and quinoa burger with sweet potato fries",
        "cuisine": "American",
    },
    "Pad Thai": {
        "ingredients": {"tofu": 0.15, "rice": 0.15, "vegetables": 0.1, "nuts": 0.03, "eggs": 0.05},
        "servings": 2, "prep_time": 10, "cook_time": 10,
        "description": "Classic pad thai with tofu, peanuts, and tamarind sauce",
        "cuisine": "Thai",
    },
    "Mushroom Risotto": {
        "ingredients": {"rice": 0.15, "vegetables": 0.2, "dairy_cheese": 0.05, "oils": 0.03},
        "servings": 2, "prep_time": 10, "cook_time": 30,
        "description": "Creamy arborio rice with wild mushrooms and parmesan",
        "cuisine": "Italian",
    },
}

DIETARY_PROFILES = {
    "omnivore": {"label": "🍖 Omnivore", "avg_daily_co2": 7.2, "color": "#ef4444"},
    "flexitarian": {"label": "🥩🥗 Flexitarian", "avg_daily_co2": 5.3, "color": "#f59e0b"},
    "pescatarian": {"label": "🐟 Pescatarian", "avg_daily_co2": 4.6, "color": "#0ea5e9"},
    "vegetarian": {"label": "🥬 Vegetarian", "avg_daily_co2": 3.8, "color": "#22c55e"},
    "vegan": {"label": "🌱 Vegan", "avg_daily_co2": 2.9, "color": "#10b981"},
}

ALT_SUGGESTIONS = {
    "meat_beef": {"replace": "legumes", "savings_pct": 97, "tip": "Replace beef with lentils or beans for a protein-rich, low-carbon alternative"},
    "meat_lamb": {"replace": "tofu", "savings_pct": 92, "tip": "Tofu provides similar texture with 92% less carbon"},
    "meat_pork": {"replace": "meat_chicken", "savings_pct": 15, "tip": "Chicken has a lower footprint, or try tofu for bigger savings"},
    "meat_chicken": {"replace": "tofu", "savings_pct": 67, "tip": "Tofu is a versatile protein swap with much lower emissions"},
    "dairy_cheese": {"replace": "tofu", "savings_pct": 85, "tip": "Nutritional yeast or tofu can mimic cheese in many dishes"},
    "dairy_milk": {"replace": "oats", "savings_pct": 70, "tip": "Oat milk has the lowest carbon footprint of plant milks"},
    "rice": {"replace": "potatoes", "savings_pct": 81, "tip": "Potatoes produce 81% less CO₂ than rice per kg"},
    "coffee": {"replace": "tea", "savings_pct": 80, "tip": "Tea has a much lower footprint than coffee"},
    "chocolate": {"replace": "fruits", "savings_pct": 90, "tip": "Fruit-based desserts are delicious and much lower impact"},
}

# ─── Session State ──────────────────────────────────────────────────────────
if "meal_log" not in st.session_state:
    st.session_state.meal_log = _generate_sample_log() if False else []
if "custom_recipe" not in st.session_state:
    st.session_state.custom_recipe = {}


def _generate_sample_log():
    """Generate sample meal log."""
    log = []
    recipes = list(SAMPLE_RECIPES.keys())
    for i in range(14):
        day = datetime.now() - timedelta(days=13 - i)
        meal_type = random.choice(["breakfast", "lunch", "dinner", "snack"])
        recipe = random.choice(recipes)
        ingredients = SAMPLE_RECIPES[recipe]["ingredients"]
        co2 = sum(qty * FOOD_CATEGORIES.get(cat, {}).get("co2_per_kg", 1) for cat, qty in ingredients.items())
        log.append({
            "date": day.strftime("%Y-%m-%d"),
            "meal_type": meal_type,
            "recipe": recipe,
            "co2_kg": round(co2, 2),
            "servings": SAMPLE_RECIPES[recipe]["servings"],
        })
    return log


# ─── Helpers ────────────────────────────────────────────────────────────────

def calculate_recipe_co2(ingredients):
    """Calculate total CO₂ for a recipe."""
    total = 0
    for cat, qty in ingredients.items():
        co2_per = FOOD_CATEGORIES.get(cat, {}).get("co2_per_kg", 1)
        total += qty * co2_per
    return round(total, 2)


def calculate_recipe_water(ingredients):
    """Calculate total water footprint."""
    total = 0
    for cat, qty in ingredients.items():
        water_per = FOOD_CATEGORIES.get(cat, {}).get("water_per_kg", 1000)
        total += qty * water_per
    return round(total, 0)


def calculate_recipe_land(ingredients):
    """Calculate total land use."""
    total = 0
    for cat, qty in ingredients.items():
        land_per = FOOD_CATEGORIES.get(cat, {}).get("land_per_kg", 1)
        total += qty * land_per
    return round(total, 2)


def get_carbon_rating(co2_kg):
    """Get a carbon rating for a meal."""
    if co2_kg < 1:
        return "🌟", "Excellent", "#22c55e"
    elif co2_kg < 3:
        return "✅", "Good", "#3b82f6"
    elif co2_kg < 6:
        return "⚠️", "Moderate", "#f59e0b"
    elif co2_kg < 10:
        return "🔶", "High", "#f97316"
    else:
        return "🔴", "Very High", "#ef4444"


# ─── Main Rendering ─────────────────────────────────────────────────────────

def render_meal_carbon_hub():
    st.title("🍽️ Meal Carbon Footprint Calculator")
    st.markdown("Analyze the carbon footprint of your meals, compare ingredients, discover low-carbon alternatives, and track your dietary impact.")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔬 Recipe Analyzer",
        "📊 Ingredient Comparison",
        "🔄 Low-Carbon Alternatives",
        "📅 Meal Log & Trends",
        "🥗 Diet Impact",
        "📖 Recipe Library",
    ])

    # ═══════════════════════════════════════════
    # TAB 1: Recipe Analyzer
    # ═══════════════════════════════════════════
    with tab1:
        st.subheader("🔬 Analyze a Recipe")

        analyzer_mode = st.radio("Mode", ["Select a Recipe", "Build Custom Recipe"], horizontal=True)

        if analyzer_mode == "Select a Recipe":
            recipe_name = st.selectbox("Choose a recipe", list(SAMPLE_RECIPES.keys()))
            recipe = SAMPLE_RECIPES[recipe_name]

            st.info(f"📖 {recipe['description']} • 🍳 {recipe['cuisine']} • ⏱️ {recipe['prep_time']}min prep + {recipe['cook_time']}min cook • 👥 Serves {recipe['servings']}")
        else:
            recipe_name = st.text_input("Recipe Name", "My Custom Recipe")
            st.markdown("**Add Ingredients:**")
            ingredients = {}
            ing_cols = st.columns(3)
            for i, (cat, meta) in enumerate(sorted(FOOD_CATEGORIES.items(), key=lambda x: x[1]["co2_per_kg"], reverse=True)):
                with ing_cols[i % 3]:
                    qty = st.number_input(
                        f"{meta['label']} (kg)",
                        min_value=0.0, max_value=5.0, value=0.0, step=0.05,
                        key=f"custom_{cat}", format="%.2f",
                    )
                    if qty > 0:
                        ingredients[cat] = qty

            servings = st.number_input("Servings", 1, 20, 2)
            recipe = {"ingredients": ingredients, "servings": servings, "prep_time": 0, "cook_time": 0,
                      "description": f"Custom recipe with {len(ingredients)} ingredients", "cuisine": "Custom"}

        # Calculate
        if recipe.get("ingredients"):
            co2 = calculate_recipe_co2(recipe["ingredients"])
            water = calculate_recipe_water(recipe["ingredients"])
            land = calculate_recipe_land(recipe["ingredients"])
            co2_per_serving = co2 / recipe["servings"]
            rating_icon, rating_label, rating_color = get_carbon_rating(co2_per_serving)

            st.divider()

            # KPI Cards
            c1, c2, c3, c4, c4 = st.columns(5)
            with c1:
                st.metric("🌍 Total CO₂", f"{co2:.2f} kg")
            with c2:
                st.metric("💧 Water", f"{water:,.0f} L")
            with c3:
                st.metric("🌾 Land", f"{land:.2f} m²")
            with c4:
                st.metric("🍽️ Per Serving", f"{co2_per_serving:.2f} kg CO₂")
            with c4:
                st.metric(f"{rating_icon} Rating", rating_label)

            st.divider()

            col_left, col_right = st.columns(2)

            with col_left:
                # Ingredient breakdown
                st.subheader("📋 Ingredient Breakdown")
                ing_data = []
                for cat, qty in recipe["ingredients"].items():
                    meta = FOOD_CATEGORIES.get(cat, {"label": cat, "co2_per_kg": 1, "color": "#999"})
                    item_co2 = qty * meta["co2_per_kg"]
                    ing_data.append({
                        "Ingredient": meta["label"],
                        "Qty (kg)": qty,
                        "CO₂/kg": meta["co2_per_kg"],
                        "Total CO₂": round(item_co2, 2),
                        "% of Total": round(item_co2 / co2 * 100, 1) if co2 > 0 else 0,
                    })

                ing_df = pd.DataFrame(ing_data).sort_values("Total CO₂", ascending=False)
                st.dataframe(ing_df, use_container_width=True, hide_index=True)

                # Pie chart
                fig = go.Figure(data=[go.Pie(
                    labels=ing_df["Ingredient"], values=ing_df["Total CO₂"],
                    hole=0.4,
                    textinfo="label+percent", textposition="outside",
                )])
                fig.update_layout(height=350, title="CO₂ by Ingredient", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with col_right:
                # Bar chart
                fig = px.bar(ing_df, x="Ingredient", y="Total CO₂", color="Ingredient",
                             title="CO₂ Contribution by Ingredient",
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=300, showlegend=False, xaxis_title="", yaxis_title="kg CO₂")
                st.plotly_chart(fig, use_container_width=True)

                # Environmental comparison
                st.subheader("🌍 Environmental Impact")
                beef_co2 = 27.0  # kg CO₂ per kg beef
                trees_needed = co2 / 21 * 365  # annual trees
                st.markdown(f"""
                - 🌳 Equivalent to **{co2 / 21 * 1000:.0f}g** of a tree's annual CO₂ absorption
                - 🚗 Similar to driving **{co2 * 3.7:.1f} km** in a car
                - 💧 Uses **{water:,.0f} liters** of water
                - 🌾 Requires **{land:.2f} m²** of land
                - 📊 This meal is **{co2_per_serving / 2.5 * 100:.0f}%** of a daily vegan diet target (2.5 kg)
                """)

                # Add to log
                if st.button("📝 Add to Meal Log", type="primary"):
                    st.session_state.meal_log.append({
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "meal_type": "custom",
                        "recipe": recipe_name,
                        "co2_kg": co2_per_serving,
                        "servings": recipe["servings"],
                    })
                    st.success(f"✅ Added '{recipe_name}' to your meal log!")

        else:
            st.warning("Add ingredients to analyze the recipe.")

    # ═══════════════════════════════════════════
    # TAB 2: Ingredient Comparison
    # ═══════════════════════════════════════════
    with tab2:
        st.subheader("📊 Ingredient Carbon Comparison")

        compare_cats = st.multiselect(
            "Select ingredients to compare",
            list(FOOD_CATEGORIES.keys()),
            default=["meat_beef", "meat_chicken", "tofu", "legumes", "vegetables", "rice", "potatoes"],
            format_func=lambda x: FOOD_CATEGORIES[x]["label"],
        )

        if compare_cats:
            df_data = []
            for cat in compare_cats:
                meta = FOOD_CATEGORIES[cat]
                df_data.append({
                    "Ingredient": meta["label"],
                    "CO₂ (kg/kg)": meta["co2_per_kg"],
                    "Water (L/kg)": meta["water_per_kg"],
                    "Land (m²/kg)": meta["land_per_kg"],
                    "Category": cat.split("_")[0],
                })

            comp_df = pd.DataFrame(df_data)

            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(comp_df.sort_values("CO₂ (kg/kg)", ascending=True),
                             x="CO₂ (kg/kg)", y="Ingredient", orientation="h",
                             title="CO₂ Emissions per kg",
                             color="Ingredient", color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=max(300, len(compare_cats) * 35), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fig = px.bar(comp_df.sort_values("Water (L/kg)", ascending=True),
                             x="Water (L/kg)", y="Ingredient", orientation="h",
                             title="Water Footprint per kg",
                             color="Ingredient", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=max(300, len(compare_cats) * 35), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            # Scatter: CO₂ vs Water
            fig = px.scatter(comp_df, x="CO₂ (kg/kg)", y="Water (L/kg)", size="Land (m²/kg)",
                             hover_name="Ingredient", title="CO₂ vs Water Footprint",
                             color="Ingredient", size_max=40)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

            # Data table
            st.dataframe(comp_df, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════════
    # TAB 3: Low-Carbon Alternatives
    # ═══════════════════════════════════════════
    with tab3:
        st.subheader("🔄 Low-Carbon Alternatives")
        st.markdown("Discover sustainable swaps to reduce your meal's carbon footprint.")

        for orig_cat, alt_info in ALT_SUGGESTIONS.items():
            orig_meta = FOOD_CATEGORIES.get(orig_cat, {"label": orig_cat, "co2_per_kg": 1, "color": "#999"})
            alt_meta = FOOD_CATEGORIES.get(alt_info["replace"], {"label": alt_info["replace"], "co2_per_kg": 1, "color": "#999"})
            savings = orig_meta["co2_per_kg"] - alt_meta["co2_per_kg"]

            with st.container():
                cols = st.columns([3, 1, 3, 2])
                with cols[0]:
                    st.markdown(f"**{orig_meta['label']}** → **{alt_meta['label']}**")
                    st.caption(alt_info["tip"])
                with cols[1]:
                    st.metric("Savings", f"{alt_info['savings_pct']}%")
                with cols[2]:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=["Original"], y=[orig_meta["co2_per_kg"]], marker_color="#ef4444", name="Original"))
                    fig.add_trace(go.Bar(x=["Alternative"], y=[alt_meta["co2_per_kg"]], marker_color="#22c55e", name="Alternative"))
                    fig.update_layout(height=120, margin=dict(t=5, b=5, l=5, r=5), showlegend=False, yaxis_title="kg CO₂/kg")
                    st.plotly_chart(fig, use_container_width=True)
                with cols[3]:
                    st.markdown(f"**{orig_meta['co2_per_kg']}** → **{alt_meta['co2_per_kg']}** kg CO₂/kg")
                    st.markdown(f"**Save {savings:.1f} kg CO₂** per kg swapped")
                st.divider()

    # ═══════════════════════════════════════════
    # TAB 4: Meal Log & Trends
    # ═══════════════════════════════════════════
    with tab4:
        st.subheader("📅 Meal Log & Trends")

        # Quick log form
        with st.expander("➕ Quick Log a Meal", expanded=False):
            with st.form("quick_log"):
                qc1, qc2, qc3 = st.columns(3)
                with qc1:
                    log_recipe = st.selectbox("Recipe", list(SAMPLE_RECIPES.keys()), key="log_recipe")
                with qc2:
                    log_meal = st.selectbox("Meal", ["breakfast", "lunch", "dinner", "snack"])
                with qc3:
                    log_date = st.date_input("Date", datetime.now())

                if st.form_submit_button("Add to Log"):
                    ingredients = SAMPLE_RECIPES[log_recipe]["ingredients"]
                    co2 = calculate_recipe_co2(ingredients)
                    st.session_state.meal_log.append({
                        "date": log_date.strftime("%Y-%m-%d"),
                        "meal_type": log_meal,
                        "recipe": log_recipe,
                        "co2_kg": round(co2, 2),
                        "servings": SAMPLE_RECIPES[log_recipe]["servings"],
                    })
                    st.success(f"✅ Logged '{log_recipe}'!")
                    st.rerun()

        log = st.session_state.meal_log

        if log:
            log_df = pd.DataFrame(log)
            log_df["date"] = pd.to_datetime(log_df["date"])

            # Summary stats
            total_co2 = log_df["co2_kg"].sum()
            avg_co2 = log_df["co2_kg"].mean()
            meals_logged = len(log_df)
            days = (log_df["date"].max() - log_df["date"].min()).days + 1
            avg_daily = total_co2 / max(1, days)

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("🍽️ Meals Logged", meals_logged)
            with c2:
                st.metric("🌍 Total CO₂", f"{total_co2:.1f} kg")
            with c3:
                st.metric("📊 Avg per Meal", f"{avg_co2:.2f} kg")
            with c4:
                st.metric("📅 Avg Daily", f"{avg_daily:.2f} kg")

            st.divider()

            # Daily CO₂ trend
            daily = log_df.groupby("date")["co2_kg"].sum().reset_index()
            fig = px.bar(daily, x="date", y="co2_kg", title="Daily Carbon Footprint",
                         color_discrete_sequence=["#22c55e"])
            fig.add_hline(y=2.5, line_dash="dash", line_color="#f59e0b", annotation_text="Vegan Target (2.5kg)")
            fig.add_hline(y=7.2, line_dash="dash", line_color="#ef4444", annotation_text="Omnivore Avg (7.2kg)")
            fig.update_layout(height=350, xaxis_title="", yaxis_title="kg CO₂")
            st.plotly_chart(fig, use_container_width=True)

            # Meal type breakdown
            meal_co2 = log_df.groupby("meal_type")["co2_kg"].mean().reset_index()
            fig = px.pie(meal_co2, values="co2_kg", names="meal_type", title="Avg CO₂ by Meal Type",
                         hole=0.4, color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

            # Full log table
            st.subheader("📋 Full Meal Log")
            display_log = log_df.copy()
            display_log["rating"] = display_log["co2_kg"].apply(lambda x: get_carbon_rating(x)[0])
            st.dataframe(display_log[["date", "meal_type", "recipe", "co2_kg", "rating"]].sort_values("date", ascending=False),
                         use_container_width=True, hide_index=True)
        else:
            st.info("No meals logged yet. Use the Quick Log form or analyze a recipe to get started!")

    # ═══════════════════════════════════════════
    # TAB 5: Diet Impact
    # ═══════════════════════════════════════════
    with tab5:
        st.subheader("🥗 Dietary Profile Impact")

        diet = st.selectbox("Your dietary profile", list(DIETARY_PROFILES.keys()),
                            format_func=lambda x: DIETARY_PROFILES[x]["label"])

        profile = DIETARY_PROFILES[diet]
        annual_co2 = profile["avg_daily_co2"] * 365

        # Comparison across diets
        diet_data = []
        for d, info in DIETARY_PROFILES.items():
            diet_data.append({
                "Diet": info["label"],
                "Daily CO₂ (kg)": info["avg_daily_co2"],
                "Annual CO₂ (kg)": info["avg_daily_co2"] * 365,
                "Selected": "✅" if d == diet else "",
            })

        diet_df = pd.DataFrame(diet_data)

        c1, c2 = st.columns(2)
        with c1:
            fig = px.bar(diet_df, x="Diet", y="Daily CO₂ (kg)", color="Diet",
                         color_discrete_map={info["label"]: info["color"] for info in DIETARY_PROFILES.values()},
                         title="Daily CO₂ by Diet")
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            # Your impact
            trees = int(annual_co2 / 21)
            cars = round(annual_co2 / 4600, 1)
            flights = round(annual_co2 / 255, 1)

            st.metric("🌍 Your Annual CO₂", f"{annual_co2:,.0f} kg")
            st.metric("🌳 Trees Needed", f"{trees}")
            st.metric("🚗 Cars Equivalent", f"{cars}")
            st.metric("✈️ Short Flights", f"{flights}")

            # Savings vs worst diet
            worst = max(DIETARY_PROFILES.values(), key=lambda x: x["avg_daily_co2"])
            savings = (worst["avg_daily_co2"] - profile["avg_daily_co2"]) * 365
            st.metric("💡 Savings vs Omnivore", f"{savings:,.0f} kg/year")

        # Weekly meal plan suggestion
        st.divider()
        st.subheader("🗓️ Suggested Low-Carbon Weekly Plan")

        weekly_plan = {
            "Monday": {"meal": "Lentil Curry", "co2": 1.8, "icon": "🫘"},
            "Tuesday": {"meal": "Tofu Buddha Bowl", "co2": 1.5, "icon": "🥗"},
            "Wednesday": {"meal": "Veggie Pasta", "co2": 1.2, "icon": "🍝"},
            "Thursday": {"meal": "Bean Tacos", "co2": 1.4, "icon": "🌮"},
            "Friday": {"meal": "Mushroom Risotto", "co2": 1.6, "icon": "🍄"},
            "Saturday": {"meal": "Pad Thai", "co2": 1.8, "icon": "🍜"},
            "Sunday": {"meal": "Vegetable Stir-Fry", "co2": 1.3, "icon": "🥘"},
        }

        plan_cols = st.columns(7)
        for i, (day, info) in enumerate(weekly_plan.items()):
            with plan_cols[i]:
                rating_icon, _, _ = get_carbon_rating(info["co2"])
                st.markdown(f"""
                <div style="text-align:center;padding:12px;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0">
                    <div style="font-size:11px;font-weight:600;color:#6b7280">{day[:3]}</div>
                    <div style="font-size:28px;margin:8px 0">{info['icon']}</div>
                    <div style="font-size:11px;font-weight:500">{info['meal']}</div>
                    <div style="font-size:11px;color:#22c55e;font-weight:600;margin-top:4px">{info['co2']} kg</div>
                    <div style="font-size:10px">{rating_icon}</div>
                </div>
                """, unsafe_allow_html=True)

        total_weekly = sum(info["co2"] for info in weekly_plan.values())
        st.metric("📅 Weekly Total", f"{total_weekly:.1f} kg CO₂", delta=f"{total_weekly / 7:.2f} kg/day avg")

    # ═══════════════════════════════════════════
    # TAB 6: Recipe Library
    # ═══════════════════════════════════════════
    with tab6:
        st.subheader("📖 Recipe Library")
        st.markdown("Browse recipes sorted by carbon footprint to find the greenest options.")

        sort_by = st.selectbox("Sort by", ["Carbon Footprint (Low)", "Carbon Footprint (High)", "Cuisine", "Name"])

        recipes_data = []
        for name, recipe in SAMPLE_RECIPES.items():
            co2 = calculate_recipe_co2(recipe["ingredients"])
            co2_per = co2 / recipe["servings"]
            water = calculate_recipe_water(recipe["ingredients"])
            rating_icon, rating_label, rating_color = get_carbon_rating(co2_per)
            recipes_data.append({
                "Name": name,
                "Cuisine": recipe.get("cuisine", "Unknown"),
                "Total CO₂ (kg)": co2,
                "Per Serving (kg)": co2_per,
                "Water (L)": water,
                "Servings": recipe["servings"],
                "Rating": f"{rating_icon} {rating_label}",
                "Description": recipe.get("description", ""),
            })

        recipes_df = pd.DataFrame(recipes_data)

        if sort_by == "Carbon Footprint (Low)":
            recipes_df = recipes_df.sort_values("Per Serving (kg)")
        elif sort_by == "Carbon Footprint (High)":
            recipes_df = recipes_df.sort_values("Per Serving (kg)", ascending=False)
        elif sort_by == "Cuisine":
            recipes_df = recipes_df.sort_values("Cuisine")
        else:
            recipes_df = recipes_df.sort_values("Name")

        # Visual cards
        for _, row in recipes_df.iterrows():
            co2_per = row["Per Serving (kg)"]
            rating_icon, _, rating_color = get_carbon_rating(co2_per)

            with st.container():
                cols = st.columns([4, 2, 2, 2])
                with cols[0]:
                    st.markdown(f"**{row['Name']}**")
                    st.caption(f"{row['Cuisine']} • {row['Description']}")
                with cols[1]:
                    st.metric("🌍 CO₂/Serving", f"{co2_per:.2f} kg")
                with cols[2]:
                    st.metric("💧 Water", f"{row['Water (L)']:,.0f} L")
                with cols[3]:
                    color = "#22c55e" if co2_per < 3 else "#f59e0b" if co2_per < 6 else "#ef4444"
                    st.markdown(f"""
                    <div style="text-align:center;padding:12px;background:{color}15;border:2px solid {color};border-radius:12px">
                        <div style="font-size:24px">{rating_icon}</div>
                        <div style="font-size:12px;font-weight:600;color:{color}">{row['Rating'].split(' ')[1]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                st.divider()


# ─── Run ────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    render_meal_carbon_hub()
