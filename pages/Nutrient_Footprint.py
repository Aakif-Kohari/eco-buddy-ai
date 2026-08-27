"""Reactive nitrogen and phosphorus, next to the carbon number rather than inside it.

Carbon accounting sees about 1% of a nitrogen loss - the nitrous oxide - and is
blind to the ammonia and nitrate that do most of the damage. This page shows the
whole loss, keeps the pathways apart, and says which part of it the app's carbon
total has already counted.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from nutrient_footprint import (
    BOUNDARY_N_PER_CAPITA,
    BOUNDARY_P_PER_CAPITA,
    APPLICATION_METHODS,
    FERTILISERS,
    P_LOSS_BY_SLOPE,
    NutrientError,
    compare_by_protein,
    compare_methods,
    delete_scenario,
    fertiliser_application,
    food_footprint,
    get_food,
    get_nutrient_insights,
    get_scenarios,
    household_nutrient_balance,
    list_categories,
    list_fertilisers,
    list_foods,
    list_methods,
    planetary_boundary_share,
    save_scenario,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🧪 Reactive Nitrogen & Phosphorus</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Agriculture crosses the nutrient boundaries harder than it crosses the "
    "climate one. Everything else in this app is denominated in kg CO2e, which "
    "sees roughly one percent of a nitrogen loss and misses the rest."
)

with st.expander("What this measures, and why the carbon number cannot"):
    st.markdown(
        """
**One kilogram of applied nitrogen splits four ways.** Ammonia to air, nitrate
to water, nitrous oxide to the atmosphere, and inert N₂ that harms nobody. Only
the nitrous oxide — about 1% — appears in a CO₂e figure. The ammonia and the
nitrate are the ones loading air quality and water, and they are invisible to
every other page in this app.

**The N₂O here is already in your carbon total.** It is shown so the climate
share of the nitrogen loss is visible. Adding it to the app's footprint would
double-count, and this page says so wherever the number appears.

**Two waters, two limiting nutrients.** Freshwater eutrophication responds to
phosphorus; marine eutrophication responds to nitrogen. There is deliberately no
combined score, because a single number would not tell you which system you are
loading.

**Inert N₂ is excluded from the reactive total.** Denitrification is a loss to
the grower and harmless to everyone else. Counting it would overstate the damage
by about a third.

**These boundaries are already crossed.** Unlike carbon, where a positive
per-capita allowance remains, global reactive nitrogen runs at roughly two and a
half times the proposed safe level. A share below one here is not "within
budget" in any collective sense.
        """
    )

st.markdown("---")

tab_diet, tab_garden, tab_balance, tab_saved = st.tabs(
    [
        "🥗 Diet",
        "🌱 Fertiliser",
        "🏡 Household balance",
        "💾 Saved scenarios",
    ]
)


# ---------------------------------------------------------------------------
# Diet
# ---------------------------------------------------------------------------
with tab_diet:
    st.markdown("### What a basket applies to the land")
    st.caption(
        "Quantities are kilograms consumed over the period you care about — a "
        "week, a month, a year. The comparison is what matters, not the window."
    )

    if "nutrient_basket" not in st.session_state:
        st.session_state.nutrient_basket = {
            "chicken": 2.0,
            "milk": 8.0,
            "wheat": 4.0,
            "vegetables_field": 6.0,
        }

    category = st.selectbox(
        "Category",
        list_categories(),
        format_func=lambda c: c.replace("_", " ").title(),
        key="nutrient_category",
    )

    add_col, qty_col, button_col = st.columns([3, 1, 1])
    with add_col:
        food_key = st.selectbox(
            "Food",
            list_foods(category),
            format_func=lambda k: get_food(k)["label"],
            key="nutrient_food",
        )
    with qty_col:
        quantity = st.number_input(
            "kg", min_value=0.0, value=1.0, step=0.5, key="nutrient_qty"
        )
    with button_col:
        st.write("")
        st.write("")
        if st.button("Add", use_container_width=True, key="nutrient_add"):
            current = st.session_state.nutrient_basket.get(food_key, 0.0)
            st.session_state.nutrient_basket[food_key] = current + quantity
            st.rerun()

    st.caption(get_food(food_key)["note"])

    basket = {k: v for k, v in st.session_state.nutrient_basket.items() if v > 0}

    if not basket:
        st.info("Add at least one food to see a footprint.")
    else:
        edit_col, clear_col = st.columns([4, 1])
        with edit_col:
            st.markdown("**Current basket**")
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Food": get_food(k)["label"], "kg": round(v, 2)}
                        for k, v in sorted(basket.items())
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
        with clear_col:
            st.write("")
            if st.button("Clear", use_container_width=True, key="nutrient_clear"):
                st.session_state.nutrient_basket = {}
                st.rerun()

        method_col, slope_col = st.columns(2)
        with method_col:
            method = st.selectbox(
                "Assumed field application method",
                list_methods(),
                index=list_methods().index("broadcast_incorporated"),
                format_func=lambda m: APPLICATION_METHODS[m]["label"],
                key="nutrient_method",
            )
        with slope_col:
            slope = st.selectbox(
                "Assumed land and cover",
                sorted(P_LOSS_BY_SLOPE),
                index=sorted(P_LOSS_BY_SLOPE).index("gentle"),
                format_func=lambda s: P_LOSS_BY_SLOPE[s]["label"],
                key="nutrient_slope",
            )

        try:
            result = food_footprint(basket, method=method, slope=slope)
        except NutrientError as error:
            st.error(str(error))
            st.stop()

        st.markdown("#### Applied, and where it went")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Nitrogen applied", f"{result['n_applied_kg']:.1f} kg N")
        m2.metric("Reactive N lost", f"{result['reactive_n_lost_kg']:.1f} kg N")
        m3.metric("Phosphorus applied", f"{result['p_applied_kg']:.2f} kg P")
        m4.metric(
            "N per 100 g protein",
            f"{result['n_per_100g_protein']:.3f} kg"
            if result["n_per_100g_protein"] else "n/a",
        )

        split = result["n_split"]
        pathway_labels = {
            "volatilisation": "Ammonia to air",
            "leaching": "Nitrate to water",
            "n2o": "Nitrous oxide (climate)",
            "denitrification": "Inert N₂ (harmless)",
            "uptake": "Taken up by the crop",
        }
        pathway_colors = {
            "volatilisation": "#e07a5f",
            "leaching": "#3d5a80",
            "n2o": "#8d5a97",
            "denitrification": "#9aa5a0",
            "uptake": "#5f8f36",
        }
        fig = go.Figure(
            go.Bar(
                x=[split[p] for p in pathway_labels],
                y=[pathway_labels[p] for p in pathway_labels],
                orientation="h",
                marker_color=[pathway_colors[p] for p in pathway_labels],
                text=[f"{split[p]:.2f} kg" for p in pathway_labels],
                textposition="auto",
            )
        )
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="kg nitrogen",
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        eutro = result["eutrophication"]
        e1, e2 = st.columns(2)
        e1.metric(
            "Freshwater loading",
            f"{eutro['freshwater_po4_eq']:.2f} kg PO₄-eq",
            help="Phosphorus-limited. Driven by runoff, not by leaching.",
        )
        e2.metric(
            "Marine loading",
            f"{eutro['marine_n_eq']:.2f} kg N-eq",
            help="Nitrogen-limited. Driven by nitrate leaching.",
        )
        st.caption(eutro["caveat"])

        overlap = result["climate_overlap"]
        st.warning(
            f"**Climate share: {overlap['kg_co2e']:.1f} kg CO₂e** at GWP100 "
            f"{overlap['gwp100']:.0f}. {overlap['warning']}"
        )

        st.markdown("#### What this basket is telling you")
        for insight in get_nutrient_insights(result):
            st.markdown(f"- {insight}")

        st.markdown("#### Contribution by food")
        contributions = pd.DataFrame(
            [
                {
                    "Food": row["label"],
                    "kg consumed": round(row["kg"], 2),
                    "kg N applied": round(row["n_applied"], 3),
                    "kg P applied": round(row["p_applied"], 4),
                    "kg N / 100 g protein": (
                        round(row["n_per_100g_protein"], 4)
                        if row["n_per_100g_protein"] is not None else None
                    ),
                }
                for row in result["items"]
            ]
        )
        st.dataframe(contributions, hide_index=True, use_container_width=True)

        boundary = planetary_boundary_share(
            result["n_applied_kg"], result["p_applied_kg"]
        )
        st.markdown("#### Against a per-capita safe operating space")
        b1, b2 = st.columns(2)
        b1.metric(
            "Nitrogen",
            f"{boundary['n_share_of_boundary']:.2f}×",
            help=f"Boundary is {BOUNDARY_N_PER_CAPITA:.1f} kg N/cap/yr.",
        )
        b2.metric(
            "Phosphorus",
            f"{boundary['p_share_of_boundary']:.2f}×",
            help=f"Boundary is {BOUNDARY_P_PER_CAPITA:.2f} kg P/cap/yr.",
        )
        st.caption(boundary["context"])

        with st.form("save_nutrient_scenario"):
            name = st.text_input("Save this basket as", value="")
            if st.form_submit_button("Save scenario") and name.strip():
                try:
                    save_scenario(user_id, name, result)
                    st.success(f"Saved '{name.strip()}'.")
                except NutrientError as error:
                    st.error(str(error))

    st.markdown("---")
    st.markdown("### The ranking that disagrees with carbon")
    st.caption(
        "Reactive nitrogen per 100 g of protein. Comparing a kilogram of "
        "lentils with a kilogram of beef by mass is not a comparison worth "
        "showing anyone, so foods below 30 g protein per kg are excluded "
        "rather than ranked badly."
    )
    ranking = compare_by_protein()
    rank_fig = go.Figure(
        go.Bar(
            x=[row["n_per_100g_protein"] for row in ranking],
            y=[row["label"] for row in ranking],
            orientation="h",
            marker_color=[
                "#e07a5f" if row["category"] in ("meat", "animal_product")
                else "#5f8f36"
                for row in ranking
            ],
        )
    )
    rank_fig.update_layout(
        height=520,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="kg reactive N applied per 100 g protein",
    )
    st.plotly_chart(rank_fig, use_container_width=True)
    st.caption(
        "Pork sits above pasture beef here and below it on carbon. That "
        "inversion is the reason this page exists."
    )


# ---------------------------------------------------------------------------
# Fertiliser
# ---------------------------------------------------------------------------
with tab_garden:
    st.markdown("### A bag of fertiliser on a garden bed")
    st.caption(
        "This is the part of the nutrient cycle a household controls directly. "
        "Domestic application at three to four times crop requirement is common, "
        "and the excess has nothing to take it up."
    )

    f1, f2 = st.columns(2)
    with f1:
        fertiliser = st.selectbox(
            "Product",
            list_fertilisers(),
            format_func=lambda k: FERTILISERS[k]["label"],
            key="fert_product",
        )
        kg_product = st.number_input(
            "Kilograms applied", min_value=0.1, value=2.0, step=0.5,
            key="fert_kg",
        )
    with f2:
        area = st.number_input(
            "Area (m²)", min_value=1.0, value=20.0, step=5.0, key="fert_area"
        )
        method_override = st.selectbox(
            "Application method",
            list_methods(),
            index=list_methods().index(FERTILISERS[fertiliser]["default_method"]),
            format_func=lambda m: APPLICATION_METHODS[m]["label"],
            key="fert_method",
        )

    st.caption(FERTILISERS[fertiliser]["note"])

    know_requirement = st.checkbox(
        "I know roughly what the crop needs", value=True, key="fert_know_req"
    )
    requirement = None
    if know_requirement:
        requirement = st.number_input(
            "Crop nitrogen requirement over the season (kg N)",
            min_value=0.01, value=0.30, step=0.05, key="fert_req",
            help="A typical vegetable bed wants roughly 15 g N per m² per "
                 "season, so 20 m² is about 0.3 kg.",
        )

    slope_choice = st.selectbox(
        "Slope and cover",
        sorted(P_LOSS_BY_SLOPE),
        format_func=lambda s: P_LOSS_BY_SLOPE[s]["label"],
        key="fert_slope",
    )

    try:
        applied = fertiliser_application(
            fertiliser,
            kg_product,
            area,
            method=method_override,
            slope=slope_choice,
            crop_requirement_kg_n=requirement,
        )
    except NutrientError as error:
        st.error(str(error))
        st.stop()

    a1, a2, a3 = st.columns(3)
    a1.metric("Nitrogen applied", f"{applied['kg_n']:.2f} kg N")
    a2.metric("Rate", f"{applied['n_rate_kg_per_ha']:.0f} kg N/ha")
    a3.metric("Reactive N lost", f"{applied['n_split']['reactive_lost']:.2f} kg N")

    if "over_application_ratio" in applied:
        ratio = applied["over_application_ratio"]
        message = (
            f"**{ratio:.1f}× the crop requirement.** "
            f"{applied['over_application_verdict']}"
        )
        if ratio > 1.5:
            st.error(message)
        elif ratio > 1.05:
            st.warning(message)
        else:
            st.success(message)

    st.info(f"**{applied['method_label']}.** {applied['method_note']}")

    st.markdown("#### The same nitrogen, applied every way")
    st.caption(
        "Method changes the answer by more than product choice does, which is "
        "the practical finding worth taking away from this page."
    )
    method_rows = compare_methods(applied["kg_n"])
    method_fig = go.Figure()
    for pathway, color, label in (
        ("volatilisation", "#e07a5f", "Ammonia to air"),
        ("leaching", "#3d5a80", "Nitrate to water"),
        ("n2o", "#8d5a97", "Nitrous oxide"),
    ):
        method_fig.add_trace(
            go.Bar(
                name=label,
                y=[row["label"] for row in method_rows],
                x=[row[pathway] for row in method_rows],
                orientation="h",
                marker_color=color,
            )
        )
    method_fig.update_layout(
        barmode="stack",
        height=380,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="kg reactive nitrogen lost",
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(method_fig, use_container_width=True)

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Method": row["label"],
                    "Reactive N lost (kg)": round(row["reactive_lost"], 3),
                    "Crop uptake": f"{row['uptake_fraction'] * 100:.0f}%",
                    "Why": row["note"],
                }
                for row in method_rows
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.caption(
        "Bag labels quote phosphorus as P₂O₅, which is 43.6% phosphorus. This "
        "page converts to elemental phosphorus, so a 7-7-7 product is treated "
        "as 3.1% P rather than 7%."
    )


# ---------------------------------------------------------------------------
# Household balance
# ---------------------------------------------------------------------------
with tab_balance:
    st.markdown("### Nutrients in, nutrients recovered, net import")
    st.caption(
        "Composting is framed elsewhere in this app as waste diversion. It is "
        "also nutrient recovery, and that is the framing with a number attached."
    )

    basket = {k: v for k, v in st.session_state.get("nutrient_basket", {}).items() if v > 0}
    if not basket:
        st.info("Build a basket on the Diet tab first.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            compost_kg = st.number_input(
                "Compost produced (kg)", min_value=0.0, value=120.0, step=10.0,
                key="balance_compost",
            )
        with c2:
            returned = st.checkbox(
                "Returned to my own soil", value=True, key="balance_returned",
                help="Composted and sent away is still diversion from landfill. "
                     "It is not recovery for this household.",
            )

        balance = household_nutrient_balance(
            basket, compost_kg=compost_kg, compost_returned_to_soil=returned
        )

        b1, b2, b3 = st.columns(3)
        b1.metric(
            "Nitrogen in (virtual)",
            f"{balance['footprint']['n_applied_kg']:.1f} kg N",
        )
        b2.metric("Recovered via compost", f"{balance['recovered_n_kg']:.2f} kg N")
        b3.metric(
            "Recovery share",
            f"{balance['recovery_fraction_n'] * 100:.1f}%",
        )

        st.info(balance["note"])

        flow = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "total"],
                x=["Virtual nitrogen in food", "Recovered via compost", "Net import"],
                y=[
                    balance["footprint"]["n_applied_kg"],
                    -balance["recovered_n_kg"],
                    None,
                ],
                decreasing=dict(marker=dict(color="#5f8f36")),
                increasing=dict(marker=dict(color="#e07a5f")),
                totals=dict(marker=dict(color="#3d5a80")),
            )
        )
        flow.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="kg nitrogen",
        )
        st.plotly_chart(flow, use_container_width=True)


# ---------------------------------------------------------------------------
# Saved scenarios
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved scenarios")
    scenarios = get_scenarios(user_id)
    if not scenarios:
        st.info("Nothing saved yet. Build a basket on the Diet tab and save it.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": row["name"],
                        "kg N applied": round(row["n_applied_kg"], 2),
                        "kg P applied": round(row["p_applied_kg"], 3),
                        "Reactive N lost": round(row["reactive_n_lost_kg"], 2),
                        "Saved": row["created_at"],
                    }
                    for row in scenarios
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        to_delete = st.selectbox(
            "Remove a scenario",
            [row["id"] for row in scenarios],
            format_func=lambda i: next(
                row["name"] for row in scenarios if row["id"] == i
            ),
            key="scenario_delete",
        )
        if st.button("Delete", key="scenario_delete_button"):
            if delete_scenario(user_id, to_delete):
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("Could not delete that scenario.")
