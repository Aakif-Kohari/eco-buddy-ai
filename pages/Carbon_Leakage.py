"""Reductions that are relocations, and the frame that hides them.

Every national target and every "emissions fell 40% since 1990" headline is
territorial. Every footprint this app computes is consumption-based. The two
are different quantities, and for a net-importing country they differ by
twenty to forty percent — always in the flattering direction.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.carbon.carbon_leakage import (
    CBAM_PHASE_IN,
    FREIGHT_MODES,
    REGIONS,
    SECTORS,
    LeakageError,
    accounting_split,
    benchmark_correction,
    build_basket,
    build_item,
    cbam_exposure,
    cbam_trajectory,
    delete_basket,
    freight_versus_origin,
    get_baskets,
    get_leakage_insights,
    intensity_breakdown,
    leakage_rate,
    list_freight_modes,
    list_regions,
    list_sectors,
    save_basket,
    substitution,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🌍 Carbon Leakage and Trade Adjustment</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Buy a washing machine made abroad and every kilogram of carbon in it is "
    "counted in someone else's national inventory. Replace a domestic product "
    "with an imported one and your territorially-framed exposure falls while "
    "the emissions carry on somewhere with a dirtier grid. This page finds "
    "those cases and puts a number on them."
)

with st.expander("Two frames, and why mixing them flatters everybody"):
    st.markdown(
        """
**Territorial** counts what was emitted inside a border. It is what national
targets are written against and what news headlines quote.

**Consumption-based** counts what a person's purchases caused, wherever it
happened. It is what every footprint in this app computes.

The gap between them is the balance of embodied trade, and it is not small.
`carbon_benchmarking.py` currently compares a user's consumption footprint
against production-based national averages, which is a comparison between two
different quantities. This page will not do that: `compare_to_territorial_target`
raises rather than returning a caveated number that would be quoted without the
caveat.

**Relocation and improvement are separate questions.** Moving aluminium
production from Europe to Brazil relocates emissions *and* reduces them,
because the Brazilian grid is cleaner. Moving a washing machine to a
coal-heavy grid relocates them and increases them. Both are leakage; only one
is bad, and a single flag would hide the difference.

**Freight is real and usually small.** Ten thousand kilometres of sea freight
adds about 0.11 kg per kilogram of cargo. Conflating that with the production
difference is why "local" and "low-carbon" get treated as the same claim. They
are reported apart here.
        """
    )

DEFAULT_ITEMS = [
    {
        "name": "Washing machine", "sector": "machinery", "origin": "china",
        "quantity": 60.0, "distance_km": 19_000.0, "freight_mode": "sea_container",
    },
    {
        "name": "Structural steel", "sector": "steel", "origin": "turkey",
        "quantity": 200.0, "distance_km": 2_500.0, "freight_mode": "sea_container",
    },
    {
        "name": "Aluminium frames", "sector": "aluminium", "origin": "china",
        "quantity": 25.0, "distance_km": 19_000.0, "freight_mode": "sea_container",
    },
    {
        "name": "Sofa", "sector": "furniture", "origin": "eu",
        "quantity": 45.0, "distance_km": 400.0, "freight_mode": "road_truck",
    },
]


tab_basket, tab_swap, tab_cbam, tab_reference = st.tabs([
    "Your basket",
    "Reduction or relocation",
    "Border carbon price",
    "Origins and saved work",
])


# ---------------------------------------------------------------------------
# Basket
# ---------------------------------------------------------------------------

with tab_basket:
    st.subheader("Where your purchases were actually made")

    home_region = st.selectbox(
        "Where you live",
        sorted(REGIONS),
        index=sorted(REGIONS).index("eu"),
        format_func=lambda key: REGIONS[key]["label"],
    )

    basket_frame = st.data_editor(
        pd.DataFrame(DEFAULT_ITEMS),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "name": st.column_config.TextColumn("Item"),
            "sector": st.column_config.SelectboxColumn(
                "Sector", options=sorted(SECTORS)
            ),
            "origin": st.column_config.SelectboxColumn(
                "Made in", options=sorted(REGIONS)
            ),
            "quantity": st.column_config.NumberColumn(
                "Quantity (kg or kWh)", min_value=0.0
            ),
            "distance_km": st.column_config.NumberColumn(
                "Distance (km)", min_value=0.0
            ),
            "freight_mode": st.column_config.SelectboxColumn(
                "Freight", options=sorted(FREIGHT_MODES)
            ),
        },
        key="leakage_basket",
    )

    basket = None
    split = None
    try:
        items = [
            build_item(
                row["name"], row["sector"], row["origin"], row["quantity"],
                row["distance_km"], row["freight_mode"],
            )
            for row in basket_frame.to_dict("records")
            if row.get("name") and (row.get("quantity") or 0) > 0
        ]
        basket = build_basket("Household basket", items)
        split = accounting_split(basket, home_region)
    except (LeakageError, KeyError, TypeError) as error:
        st.error(str(error))

    if split:
        first, second, third, fourth = st.columns(4)
        first.metric("Emitted at home", "%.0f kg CO2e" % split["territorial_kg_co2"])
        second.metric("Emitted abroad", "%.0f kg CO2e" % split["imported_kg_co2"])
        third.metric(
            "Your consumption footprint",
            "%.0f kg CO2e" % split["consumption_kg_co2"],
        )
        fourth.metric("Imported share", "%.0f%%" % (split["import_share"] * 100.0))

        st.caption(
            "The three reconcile by construction — territorial plus imports "
            "equals consumption — and there is a test asserting it. They are "
            "shown separately because they answer different questions and get "
            "quoted interchangeably."
        )

        item_rows = []
        for row in split["items"]:
            item_rows.append({
                "Item": row["name"],
                "Sector": SECTORS[row["sector"]]["label"],
                "Made in": REGIONS[row["origin"]]["label"],
                "Counted at home": "yes" if row["domestic"] else "no",
                "Production": round(row["production_kg_co2"], 1),
                "Freight": round(row["freight_kg_co2"], 1),
                "Total": round(row["total_kg_co2"], 1),
                "Freight share": "%.1f%%" % ((row["freight_share"] or 0) * 100.0),
            })
        st.dataframe(
            pd.DataFrame(item_rows), use_container_width=True, hide_index=True
        )

        figure = go.Figure()
        figure.add_bar(
            name="Production",
            x=[row["name"] for row in split["items"]],
            y=[row["production_kg_co2"] for row in split["items"]],
        )
        figure.add_bar(
            name="Freight",
            x=[row["name"] for row in split["items"]],
            y=[row["freight_kg_co2"] for row in split["items"]],
        )
        figure.update_layout(
            barmode="stack",
            yaxis_title="kg CO2e",
            height=380,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)
        st.caption(
            "Look at the freight slivers. For anything moving by sea the "
            "production difference dominates by an order of magnitude, which "
            "is the argument against treating distance as the thing that "
            "matters."
        )

        st.divider()
        st.markdown("#### Is 'buy local' about the factory or the shipping?")
        which = st.selectbox(
            "Item", [item["name"] for item in basket["items"]],
            key="leakage_local_item",
        )
        chosen = next(
            item for item in basket["items"] if item["name"] == which
        )
        comparison = freight_versus_origin(chosen, home_region)
        first, second, third = st.columns(3)
        first.metric(
            "Production difference", "%+.1f kg CO2e" % comparison["production_gap"]
        )
        second.metric(
            "Freight difference", "%+.1f kg CO2e" % comparison["freight_gap"]
        )
        third.metric("Net", "%+.1f kg CO2e" % comparison["net_gap"])
        if comparison["local_is_better"]:
            st.success(
                "Making it at home would be lower, and the **%s** term is "
                "doing most of the work."
                % comparison["dominant_term"]
            )
        else:
            st.warning(
                "Making it at home would be **higher**. The origin's grid is "
                "cleaner than yours by more than the shipping costs, which is "
                "the case that stops 'imported' being a synonym for 'dirtier'."
            )

        st.divider()
        st.markdown("#### Correcting the benchmark you are being compared against")
        first, second = st.columns(2)
        with first:
            territorial_benchmark = st.number_input(
                "Territorial average per capita (kg CO2e)",
                min_value=100.0, value=6_000.0, step=100.0,
            )
        with second:
            import_share = st.slider("Embodied import share", 0.0, 0.6, 0.28, 0.01)
        correction = benchmark_correction(territorial_benchmark, import_share)
        first, second, third = st.columns(3)
        first.metric(
            "As published", "%.0f kg" % correction["territorial_per_capita_kg"]
        )
        second.metric(
            "On a consumption footing",
            "%.0f kg" % correction["consumption_per_capita_kg"],
        )
        third.metric(
            "Correction", "%+.0f%%" % (correction["adjustment_share"] * 100.0)
        )
        st.info(correction["note"])

        if st.button("Save this basket"):
            try:
                save_basket(user_id, basket, split)
                st.success("Saved.")
            except LeakageError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# Reduction or relocation
# ---------------------------------------------------------------------------

with tab_swap:
    st.subheader("A single swap")
    st.caption(
        "The decomposition is exact: the quantity, intensity and freight "
        "effects sum to the observed change with no residual. A remainder in "
        "an analysis of whether a reduction was real invites you to assume it "
        "was the real part."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("**Before**")
        before_sector = st.selectbox(
            "Sector (before)", sorted(SECTORS),
            index=sorted(SECTORS).index("machinery"),
            format_func=lambda key: SECTORS[key]["label"],
        )
        before_origin = st.selectbox(
            "Made in (before)", sorted(REGIONS),
            index=sorted(REGIONS).index("eu"),
            format_func=lambda key: REGIONS[key]["label"],
        )
        before_quantity = st.number_input(
            "Quantity (before)", min_value=0.0, value=60.0, step=5.0
        )
        before_distance = st.number_input(
            "Distance km (before)", min_value=0.0, value=300.0, step=100.0
        )
    with right:
        st.markdown("**After**")
        after_sector = st.selectbox(
            "Sector (after)", sorted(SECTORS),
            index=sorted(SECTORS).index("machinery"),
            format_func=lambda key: SECTORS[key]["label"],
        )
        after_origin = st.selectbox(
            "Made in (after)", sorted(REGIONS),
            index=sorted(REGIONS).index("china"),
            format_func=lambda key: REGIONS[key]["label"],
        )
        after_quantity = st.number_input(
            "Quantity (after)", min_value=0.0, value=60.0, step=5.0
        )
        after_distance = st.number_input(
            "Distance km (after)", min_value=0.0, value=19_000.0, step=500.0
        )

    try:
        swap = substitution(
            build_item("Before", before_sector, before_origin,
                       before_quantity, before_distance),
            build_item("After", after_sector, after_origin,
                       after_quantity, after_distance),
            home_region,
        )
    except LeakageError as error:
        swap = None
        st.error(str(error))

    if swap:
        first, second, third, fourth = st.columns(4)
        first.metric("Quantity effect", "%+.0f kg" % swap["quantity_effect"])
        second.metric("Origin effect", "%+.0f kg" % swap["intensity_effect"])
        third.metric("Freight effect", "%+.0f kg" % swap["freight_effect"])
        fourth.metric("Global change", "%+.0f kg" % swap["global_change"])

        st.caption(
            "Residual: %.2g kg. The three effects account for the whole "
            "change." % swap["residual"]
        )

        if swap["leakage_detected"] and not swap["net_global_improvement"]:
            st.error(swap["note"])
        elif swap["leakage_detected"]:
            st.warning(swap["note"])
        else:
            st.success(swap["note"])

        waterfall = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "relative", "total"],
            x=["Quantity", "Origin", "Freight", "Net"],
            y=[
                swap["quantity_effect"],
                swap["intensity_effect"],
                swap["freight_effect"],
                swap["global_change"],
            ],
        ))
        waterfall.update_layout(
            yaxis_title="kg CO2e",
            height=360,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(waterfall, use_container_width=True)

    st.divider()
    st.subheader("A whole basket, two years apart")
    st.caption(
        "The personal-scale version of the argument about whether wealthy "
        "countries decarbonised or outsourced. Items are matched by name; "
        "anything appearing or disappearing counts as a quantity change, "
        "because buying something new is a change in what is consumed."
    )

    earlier_frame = st.data_editor(
        pd.DataFrame([
            {"name": "Washing machine", "sector": "machinery",
             "origin": "eu", "quantity": 60.0},
            {"name": "Structural steel", "sector": "steel",
             "origin": "eu", "quantity": 200.0},
        ]),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "sector": st.column_config.SelectboxColumn(
                "Sector", options=sorted(SECTORS)
            ),
            "origin": st.column_config.SelectboxColumn(
                "Made in", options=sorted(REGIONS)
            ),
        },
        key="leakage_earlier",
    )
    later_frame = st.data_editor(
        pd.DataFrame([
            {"name": "Washing machine", "sector": "machinery",
             "origin": "china", "quantity": 60.0},
            {"name": "Structural steel", "sector": "steel",
             "origin": "turkey", "quantity": 200.0},
        ]),
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "sector": st.column_config.SelectboxColumn(
                "Sector", options=sorted(SECTORS)
            ),
            "origin": st.column_config.SelectboxColumn(
                "Made in", options=sorted(REGIONS)
            ),
        },
        key="leakage_later",
    )


    def _period(frame, label):
        return build_basket(label, [
            build_item(
                row["name"], row["sector"], row["origin"], row["quantity"]
            )
            for row in frame.to_dict("records")
            if row.get("name") and (row.get("quantity") or 0) > 0
        ])


    try:
        period = leakage_rate(
            _period(earlier_frame, "Earlier"),
            _period(later_frame, "Later"),
            home_region,
        )
    except (LeakageError, KeyError, TypeError) as error:
        period = None
        st.error(str(error))

    if period:
        first, second, third = st.columns(3)
        first.metric(
            "Territorial change", "%+.0f kg" % period["territorial_change"]
        )
        second.metric(
            "Consumption change", "%+.0f kg" % period["consumption_change"]
        )
        third.metric(
            "Of the reduction, relocated",
            "%.0f%%" % ((period["leakage_share_of_reduction"] or 0.0) * 100.0),
        )

        for insight in get_leakage_insights(period):
            if insight["level"] == "warning":
                st.warning("**%s**\n\n%s" % (insight["title"], insight["body"]))
            else:
                st.info("**%s**\n\n%s" % (insight["title"], insight["body"]))

        st.dataframe(
            pd.DataFrame([{
                "Item": row["name"],
                "Was made in": (
                    REGIONS[row["before_origin"]]["label"]
                    if row["before_origin"] else "—"
                ),
                "Now made in": (
                    REGIONS[row["after_origin"]]["label"]
                    if row["after_origin"] else "—"
                ),
                "Quantity effect": round(row["quantity_effect"], 1),
                "Origin effect": round(row["origin_effect"], 1),
            } for row in period["items"]]),
            use_container_width=True,
            hide_index=True,
        )


# ---------------------------------------------------------------------------
# CBAM
# ---------------------------------------------------------------------------

with tab_cbam:
    st.subheader("What a border carbon price costs this basket")
    st.caption(
        "Cement, iron and steel, aluminium, fertilisers, electricity and "
        "hydrogen. Imported only, production emissions only, and the free "
        "allocation withdraws on a legislated schedule rather than all at "
        "once."
    )

    first, second = st.columns(2)
    with first:
        carbon_price = st.slider("Carbon price per tonne", 20.0, 200.0, 85.0, 5.0)
    with second:
        cbam_year = st.select_slider(
            "Year", options=sorted(CBAM_PHASE_IN), value=2030
        )

    if basket:
        try:
            exposure = cbam_exposure(basket, carbon_price, cbam_year, home_region)
        except LeakageError as error:
            exposure = None
            st.error(str(error))

        if exposure:
            first, second, third, fourth = st.columns(4)
            first.metric("Charged this year", "%.2f" % exposure["cost"])
            second.metric(
                "At full phase-in", "%.2f" % exposure["cost_at_full_phase_in"]
            )
            third.metric(
                "Phase-in share", "%.1f%%" % (exposure["phase_in_share"] * 100.0)
            )
            fourth.metric(
                "Imports in scope",
                "%.0f%%" % ((exposure["coverage_share"] or 0.0) * 100.0),
            )

            st.caption(exposure["note"])

            if exposure["covered"]:
                st.markdown("**Covered imports**")
                st.dataframe(
                    pd.DataFrame([{
                        "Item": row["name"],
                        "Sector": SECTORS[row["sector"]]["label"],
                        "Origin": REGIONS[row["origin"]]["label"],
                        "Production kg CO2e": round(row["production_kg_co2"], 1),
                        "Chargeable kg CO2e": round(row["chargeable_kg_co2"], 1),
                        "Cost": round(row["cost"], 2),
                    } for row in exposure["covered"]]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Nothing in this basket falls inside the covered sectors.")

            if exposure["uncovered"]:
                st.warning(
                    "**%.0f kg CO2e of imported emissions is out of scope**, "
                    "not zero-rated. Electronics and machinery are not "
                    "covered even where they contain covered materials, which "
                    "is one of the more obvious gaps in the current design "
                    "and a live subject of review."
                    % exposure["uncovered_emissions_kg"]
                )

            trajectory = cbam_trajectory(basket, carbon_price, home_region)
            figure = go.Figure()
            figure.add_bar(
                x=[row["year"] for row in trajectory],
                y=[row["cost"] for row in trajectory],
                name="Cost",
            )
            figure.update_layout(
                xaxis_title="Year",
                yaxis_title="Border charge",
                height=360,
                margin=dict(l=10, r=10, t=30, b=10),
            )
            st.plotly_chart(figure, use_container_width=True)
            st.caption(
                "The shape is the free-allocation withdrawal, not a rising "
                "carbon price — the price is held constant across this chart. "
                "Most of the cost arrives after 2029."
            )
    else:
        st.info("Build a basket on the first tab.")


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------

with tab_reference:
    st.subheader("Grid intensity by origin")

    st.dataframe(
        pd.DataFrame([{
            "Origin": entry["label"],
            "Grid (kg CO2e/kWh)": entry["grid_intensity"],
        } for entry in list_regions()]),
        use_container_width=True,
        hide_index=True,
    )

    for entry in list_regions():
        with st.expander(entry["label"]):
            st.markdown(entry["note"])

    st.markdown("#### The same product from every origin")
    reference_sector = st.selectbox(
        "Sector", sorted(SECTORS),
        index=sorted(SECTORS).index("aluminium"),
        format_func=lambda key: SECTORS[key]["label"],
        key="leakage_reference_sector",
    )
    st.caption(SECTORS[reference_sector]["note"])

    breakdowns = [
        intensity_breakdown(reference_sector, key) for key in sorted(REGIONS)
    ]
    figure = go.Figure()
    figure.add_bar(
        name="Process",
        x=[REGIONS[row["region"]]["label"] for row in breakdowns],
        y=[row["process"] for row in breakdowns],
    )
    figure.add_bar(
        name="Electricity",
        x=[REGIONS[row["region"]]["label"] for row in breakdowns],
        y=[row["electricity"] for row in breakdowns],
    )
    figure.update_layout(
        barmode="stack",
        yaxis_title="kg CO2e per %s" % SECTORS[reference_sector]["unit"],
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Where the electricity band is tall, origin matters. Where it is thin "
        "— cement is the clearest case — the chemistry sets the number and "
        "sourcing barely moves it."
    )

    st.markdown("#### Sectors and border adjustment coverage")
    st.dataframe(
        pd.DataFrame([{
            "Sector": entry["label"],
            "Unit": entry["unit"],
            "Process": entry["process_intensity"],
            "kWh per unit": entry["electricity_kwh_per_unit"],
            "In CBAM scope": "yes" if entry["cbam_covered"] else "no",
        } for entry in list_sectors()]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Freight")
    st.dataframe(
        pd.DataFrame([{
            "Mode": entry["label"],
            "kg CO2e per tonne-km": entry["intensity"],
        } for entry in list_freight_modes()]),
        use_container_width=True,
        hide_index=True,
    )
    for entry in list_freight_modes():
        st.caption("**%s** — %s" % (entry["label"], entry["note"]))

    st.divider()
    st.subheader("Saved baskets")
    saved = get_baskets(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    for record in saved:
        with st.expander(
            "%s — %.0f kg CO2e consumption, %.0f kg of it abroad"
            % (record["name"], record["consumption_kg"], record["imported_kg"])
        ):
            st.write("Home region: %s" % REGIONS[record["home_region"]]["label"])
            st.write("Emitted at home: %.0f kg CO2e" % record["territorial_kg"])
            share = record["payload"].get("import_share")
            if share is not None:
                st.write("Imported share: %.0f%%" % (share * 100.0))
            st.write("Saved: %s" % record["created_at"])
            if st.button("Delete", key="leakage_delete_%s" % record["id"]):
                delete_basket(user_id, record["id"])
                st.rerun()
