"""Product Carbon Footprint & Green Shopping Advisor page for EcoBuddy AI.

Estimates the CO₂ footprint of everyday purchases, compares conventional
items against eco-friendly alternatives, and provides a prioritised green
shopping plan with full lifecycle visualisation.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from styles.theme import apply_theme
from product_carbon_footprint import (
    PRODUCT_CATALOGUE,
    LIFECYCLE_STAGES,
    PACKAGING_FACTORS,
    calculate_product_footprint,
    calculate_shopping_cart,
    list_products,
    list_categories,
    save_shopping_cart,
    get_shopping_history,
)

# ── Auth ─────────────────────────────────────────────────────────────────────
user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    "<div class='section-header'>🛒 Product Carbon Footprint & Green Shopping</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Estimate the CO₂ footprint of everyday purchases, compare conventional "
    "vs eco-friendly alternatives, and build a zero-waste shopping strategy."
)
st.markdown("---")

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_lookup, tab_cart, tab_analysis, tab_history = st.tabs([
    "🔍 Product Lookup",
    "🛒 Build Shopping Cart",
    "📊 Cart Analysis",
    "📈 Shopping History",
])


# ── Tab 1: Product Lookup ────────────────────────────────────────────────────
with tab_lookup:
    st.markdown("### 🔍 Product Carbon Footprint Lookup")

    category_filter = st.selectbox(
        "Filter by Category",
        ["All"] + list_categories(),
    )

    products = list_products(
        category=category_filter if category_filter != "All" else None,
    )

    # Display as table
    df_products = pd.DataFrame(products)
    df_products.columns = [
        "Key", "Product", "Icon", "Category", "Weight (kg)",
        "Conventional (kg CO₂)", "Eco (kg CO₂)", "Savings (%)",
    ]
    st.dataframe(df_products, use_container_width=True, hide_index=True)

    # ── Individual product deep-dive ────────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔬 Deep-Dive: Single Product Analysis")

    selected_product = st.selectbox(
        "Select a Product",
        [p["key"] for p in products],
        format_func=lambda k: PRODUCT_CATALOGUE[k]["name"],
    )
    packaging = st.selectbox(
        "Packaging Level",
        list(PACKAGING_FACTORS.keys()),
        index=2,
        format_func=lambda k: PACKAGING_FACTORS[k]["name"],
    )
    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)

    if st.button("🔬 Analyse Product", use_container_width=True, type="primary"):
        result = calculate_product_footprint(selected_product, quantity, packaging)
        st.session_state.product_lookup = result

    lookup_result = st.session_state.get("product_lookup")
    if lookup_result:
        r = lookup_result
        # ── Product banner ──────────────────────────────────────────────
        eco_name = r["eco_alternative"]["name"] or "N/A"
        savings_kg = r["savings"]["kg_total"] or 0
        savings_pct = r["savings"]["pct"] or 0

        st.markdown(
            f"""
            <div style="background:#1e293b;padding:20px;border-radius:14px;
                        border-left:6px solid #38bdf8;margin-bottom:20px;">
                <h3 style="margin:0;color:#38bdf8;">
                    {r['icon']} {r['product_name']} × {r['quantity']}
                </h3>
                <p style="margin:6px 0 0;color:#cbd5e1;">
                    Category: {r['category']} &nbsp;|&nbsp;
                    Weight: {r['unit_weight_kg']} kg/unit &nbsp;|&nbsp;
                    Lifetime Uses: {r['typical_lifetime_uses']}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "🏭 Conventional",
            f"{r['conventional']['total_kg']:,.1f} kg",
            delta=f"{r['conventional']['per_unit_kg']:.1f} kg/unit",
        )
        c2.metric(
            "🌿 Eco Alternative",
            f"{r['eco_alternative']['total_kg'] or 0:,.1f} kg",
            delta=eco_name,
        )
        c3.metric(
            "💚 Potential Savings",
            f"{savings_kg:,.1f} kg",
            delta=f"{savings_pct:.0f}%",
        )
        c4.metric(
            "📦 Packaging Waste",
            f"{r['packaging']['disposal_kg']:.2f} kg",
            delta=r["packaging"]["type"],
        )

        # ── Lifecycle breakdown chart ───────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Lifecycle Breakdown")

        col_conv, col_eco = st.columns(2)
        with col_conv:
            conv_lifecycle = r["conventional"]["lifecycle"]
            fig_conv = px.pie(
                values=list(conv_lifecycle.values()),
                names=[s.replace("_", " ").title() for s in conv_lifecycle.keys()],
                title="Conventional Lifecycle",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Reds_r,
            )
            fig_conv.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_conv, use_container_width=True)

        with col_eco:
            eco_lifecycle = r["eco_alternative"]["lifecycle"] or {}
            if eco_lifecycle:
                fig_eco = px.pie(
                    values=list(eco_lifecycle.values()),
                    names=[s.replace("_", " ").title() for s in eco_lifecycle.keys()],
                    title="Eco Alternative Lifecycle",
                    hole=0.45,
                    color_discrete_sequence=px.colors.sequential.Greens_r,
                )
            else:
                fig_eco = go.Figure()
                fig_eco.update_layout(title="No Eco Alternative Available")
            fig_eco.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_eco, use_container_width=True)

        # ── Stage comparison bar chart ──────────────────────────────────
        if eco_lifecycle:
            stages = list(LIFECYCLE_STAGES)
            stage_labels = [s.replace("_", " ").title() for s in stages]
            fig_compare = go.Figure()
            fig_compare.add_trace(go.Bar(
                name="Conventional",
                x=stage_labels,
                y=[conv_lifecycle.get(s, 0) for s in stages],
                marker_color="#ef4444",
            ))
            fig_compare.add_trace(go.Bar(
                name="Eco Alternative",
                x=stage_labels,
                y=[eco_lifecycle.get(s, 0) for s in stages],
                marker_color="#22c55e",
            ))
            fig_compare.update_layout(
                barmode="group",
                title="Lifecycle Stage Comparison",
                yaxis_title="kg CO₂",
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_compare, use_container_width=True)


# ── Tab 2: Build Shopping Cart ──────────────────────────────────────────────
with tab_cart:
    st.markdown("### 🛒 Build Your Shopping Cart")
    st.markdown(
        "Add products to your cart with quantities and packaging preferences "
        "to see the total carbon impact of your shopping trip."
    )

    if "shopping_cart" not in st.session_state:
        st.session_state.shopping_cart = []

    # ── Add item form ───────────────────────────────────────────────────
    with st.form("add_to_cart"):
        col_add1, col_add2, col_add3, col_add4 = st.columns(4)
        with col_add1:
            add_product = st.selectbox(
                "Product",
                list(PRODUCT_CATALOGUE.keys()),
                format_func=lambda k: f"{PRODUCT_CATALOGUE[k]['icon']} {PRODUCT_CATALOGUE[k]['name']}",
            )
        with col_add2:
            add_qty = st.number_input("Qty", min_value=1, value=1, step=1)
        with col_add3:
            add_pkg = st.selectbox(
                "Packaging",
                list(PACKAGING_FACTORS.keys()),
                index=2,
                format_func=lambda k: PACKAGING_FACTORS[k]["name"],
            )
        with col_add4:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            add_btn = st.form_submit_button("➕ Add to Cart", use_container_width=True)

        if add_btn:
            st.session_state.shopping_cart.append({
                "product_key": add_product,
                "quantity": add_qty,
                "packaging": add_pkg,
            })
            st.success(f"Added {PRODUCT_CATALOGUE[add_product]['name']} × {add_qty}")
            st.rerun()

    # ── Current cart ────────────────────────────────────────────────────
    cart = st.session_state.shopping_cart
    if cart:
        st.markdown("---")
        st.markdown("### 📦 Current Cart")

        cart_rows = []
        for idx, item in enumerate(cart):
            info = PRODUCT_CATALOGUE[item["product_key"]]
            result = calculate_product_footprint(
                item["product_key"], item["quantity"], item.get("packaging", "standard"),
            )
            cart_rows.append({
                "#": idx + 1,
                "Product": f"{info['icon']} {info['name']}",
                "Qty": item["quantity"],
                "Packaging": PACKAGING_FACTORS.get(item.get("packaging", "standard"), {}).get("name", ""),
                "CO₂ (kg)": f"{result['conventional']['total_kg']:.1f}",
            })

        st.dataframe(pd.DataFrame(cart_rows), use_container_width=True, hide_index=True)

        # Total quick view
        total = sum(
            calculate_product_footprint(
                item["product_key"], item["quantity"], item.get("packaging", "standard"),
            )["conventional"]["total_kg"]
            for item in cart
        )
        st.metric("🛒 Cart Total", f"{total:,.1f} kg CO₂")

        # Remove item
        remove_col, clear_col = st.columns(2)
        with remove_col:
            remove_idx = st.number_input(
                "Remove item #",
                min_value=1,
                max_value=len(cart) if cart else 1,
                value=1,
                step=1,
            )
            if st.button("🗑️ Remove Item"):
                if 1 <= remove_idx <= len(cart):
                    removed = st.session_state.shopping_cart.pop(remove_idx - 1)
                    st.success(f"Removed {PRODUCT_CATALOGUE[removed['product_key']]['name']}")
                    st.rerun()
        with clear_col:
            if st.button("🧹 Clear Cart", type="secondary"):
                st.session_state.shopping_cart = []
                st.rerun()
    else:
        st.info("Your cart is empty. Add products above to start analysing.")


# ── Tab 3: Cart Analysis ────────────────────────────────────────────────────
with tab_analysis:
    st.markdown("### 📊 Shopping Cart Analysis")

    cart = st.session_state.get("shopping_cart", [])
    if not cart:
        st.info("Build a shopping cart in the **Build Shopping Cart** tab first.")
    else:
        with st.spinner("Analysing shopping cart footprint..."):
            cart_result = calculate_shopping_cart(cart)

        # ── Summary metrics ─────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🏭 Total CO₂", f"{cart_result.total_conventional_kg:,.1f} kg")
        c2.metric(
            "🌿 Eco Total",
            f"{cart_result.total_eco_kg or 0:,.1f} kg",
            delta=f"Save {cart_result.total_potential_savings_kg or 0:,.1f} kg",
        )
        c3.metric("🌳 Equivalent Trees", f"{cart_result.equivalent_trees}")
        c4.metric("🚗 Equivalent km Driven", f"{cart_result.equivalent_km_driven:,.0f}")

        # ── Category breakdown ──────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Category Breakdown")

        col_pie, col_bar = st.columns(2)
        with col_pie:
            cats = list(cart_result.category_breakdown.keys())
            fig_cat = px.pie(
                values=list(cart_result.category_breakdown.values()),
                names=cats,
                title="Emissions by Category",
                hole=0.45,
                color_discrete_sequence=px.colors.sequential.Teal_r,
            )
            fig_cat.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_bar:
            stages = list(LIFECYCLE_STAGES)
            fig_lifecycle = px.bar(
                x=[s.replace("_", " ").title() for s in stages],
                y=[cart_result.lifecycle_totals[s] for s in stages],
                title="Emissions by Lifecycle Stage",
                color=[cart_result.lifecycle_totals[s] for s in stages],
                color_continuous_scale="Reds",
            )
            fig_lifecycle.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
            )
            st.plotly_chart(fig_lifecycle, use_container_width=True)

        # ── Item comparison ──────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Per-Item Comparison: Conventional vs Eco")

        item_names = [f"{i.icon} {i.product_name}" for i in cart_result.items]
        fig_items = go.Figure()
        fig_items.add_trace(go.Bar(
            name="Conventional",
            x=item_names,
            y=[i.total_conventional_kg for i in cart_result.items],
            marker_color="#ef4444",
        ))
        eco_vals = [i.total_eco_kg if i.total_eco_kg is not None else 0 for i in cart_result.items]
        fig_items.add_trace(go.Bar(
            name="Eco Alternative",
            x=item_names,
            y=eco_vals,
            marker_color="#22c55e",
        ))
        fig_items.update_layout(
            barmode="group",
            title="Conventional vs Eco Per Item",
            yaxis_title="kg CO₂",
            template="plotly_dark",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_items, use_container_width=True)

        # ── Recommendations ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 💡 Green Shopping Recommendations")

        if cart_result.recommendations:
            for rec in cart_result.recommendations:
                impact_badge = {"high": "🔥", "medium": "💪", "low": "🌱"}.get(
                    rec["impact"], ""
                )
                st.markdown(
                    f"""
                    <div style="border:1px solid #334155;border-radius:10px;padding:14px;
                                margin-bottom:10px;background:rgba(30,41,59,0.5);">
                        <h4 style="margin:0 0 6px;color:#38bdf8;">
                            {rec['icon']} {rec['action']}
                            <span style="font-size:0.85em;color:#4ade80;">
                                (Save {rec['savings_kg']:,.1f} kg CO₂)
                            </span>
                            {impact_badge}
                        </h4>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("🌟 No improvement recommendations — your cart is already optimised!")

        # ── Save to history ─────────────────────────────────────────────
        st.markdown("---")
        if st.button("💾 Save Cart Analysis to History", use_container_width=True):
            row_id = save_shopping_cart(user_id, cart_result)
            if row_id:
                st.success(f"✅ Cart analysis saved (ID: {row_id})!")
            else:
                st.error("Failed to save cart analysis.")


# ── Tab 4: Shopping History ─────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📈 Shopping History")

    history = get_shopping_history(user_id)

    if not history:
        st.info(
            "No shopping history found. Run a cart analysis and save it "
            "to start tracking your shopping carbon footprint."
        )
    else:
        # ── Summary table ───────────────────────────────────────────────
        rows = []
        for entry in history:
            rows.append({
                "Date": entry.get("created_at", ""),
                "Total CO₂ (kg)": entry.get("total_conventional_kg", 0),
                "Eco CO₂ (kg)": entry.get("total_eco_kg", 0) or "N/A",
                "Savings (kg)": entry.get("total_savings_kg", 0) or "N/A",
                "Packaging (kg)": entry.get("total_packaging_kg", 0),
            })

        df_hist = pd.DataFrame(rows)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)

        # ── Trend chart ─────────────────────────────────────────────────
        if len(history) >= 2:
            st.markdown("---")
            st.markdown("### 📉 Shopping Footprint Trend")
            dates = [e.get("created_at", "") for e in reversed(history)]
            totals = [e.get("total_conventional_kg", 0) for e in reversed(history)]

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(
                x=dates,
                y=totals,
                mode="lines+markers",
                name="Total CO₂",
                line=dict(color="#38bdf8", width=3),
                marker=dict(size=8),
            ))
            fig_trend.update_layout(
                title="Shopping Footprint Over Time",
                xaxis_title="Date",
                yaxis_title="kg CO₂",
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        # ── Export ──────────────────────────────────────────────────────
        csv_data = df_hist.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Export Shopping History (CSV)",
            data=csv_data,
            file_name="shopping_footprint_history.csv",
            mime="text/csv",
        )
