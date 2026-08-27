"""Energy that is generated, and energy that is actually available afterwards.

Every other energy page in this app reports gross output. This one reports what
is left once the energy sector has taken its own cut — and shows why that gap
is a cliff rather than a correction.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.carbon.net_energy_eroi import (
    BOUNDARIES,
    DEFAULT_BOUNDARY,
    SOCIETAL_MINIMUM_EROI,
    SOURCES,
    STORAGE,
    NetEnergyError,
    buffered_eroi,
    delete_position,
    energy_payback,
    energy_versus_carbon,
    eroi,
    eroi_across_boundaries,
    get_boundary,
    get_carrier,
    get_positions,
    get_source,
    get_storage,
    get_net_energy_insights,
    household_position,
    list_boundaries,
    list_families,
    list_sources,
    list_storage,
    net_energy_cliff,
    payback_sensitivity,
    quality_comparison,
    save_position,
    societal_position,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⚡ Net Energy & Energy Return on Investment</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A kilowatt-hour from a source returning thirty times its energy "
    "investment and one from a source returning five cost society very "
    "different amounts to obtain. Every other energy page here treats them as "
    "the same kilowatt-hour."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**The boundary is required.** At the wellhead, at the point of use, and
extended to include grid and storage, the same technology gives answers
differing by more than a factor of two. A ratio quoted without its boundary is
not a number — it is a rhetorical device, and it is used as one from both
directions. There is no function here that returns a single unqualified figure.

**The cliff is non-linear.** The share of gross output that has to be
reinvested is one over the ratio: 3% at thirty, 10% at ten, 20% at five, 50% at
two. Flat, and then it is not. A fall from ten to five costs society far more
than a fall from thirty to twenty, and gross figures cannot express that.

**Storage is an energy cost, not a free capability.** Batteries consume energy
to build and lose energy every cycle. The buffered ratio of a solar-plus-storage
system sits well below the panel's own, and for some configurations that gap
crosses the level usually taken as the societal minimum.

**Payback and lifetime ratio are different questions.** Offshore wind pays back
faster than rooftop solar and returns more over its life. A source can be good
at one and middling at the other. This is also *energy* payback, not carbon
payback — a panel built on a coal grid and deployed on a clean one has a short
carbon payback and an unchanged energy payback.

**Energy quality is a choice, not a fact.** Counting joules and weighting them
by what they can do reverse the ranking of electric against thermal options.
Both are computed, both are shown, and neither is presented as the answer.

**Energy return and carbon are separate scarcities.** Coal ranks near the top on
one and the bottom on the other. No combined score is produced, because
weighting a ratio of energies against a mass of CO2 is a political question
rather than an accounting one.
        """
    )

st.markdown("---")

tab_source, tab_cliff, tab_storage, tab_quality, tab_household, tab_saved = st.tabs(
    [
        "🔌 One source",
        "📉 The cliff",
        "🔋 Storage",
        "⚖️ Energy quality",
        "🏠 A household",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# One source
# ---------------------------------------------------------------------------
with tab_source:
    st.markdown("### One source, at a stated boundary")

    c1, c2, c3 = st.columns(3)
    with c1:
        family = st.selectbox(
            "Family", ["(all)"] + list_families(), key="nx_family"
        )
    with c2:
        available = (
            list_sources() if family == "(all)" else list_sources(family)
        )
        source = st.selectbox(
            "Source",
            available,
            format_func=lambda k: SOURCES[k]["label"],
            key="nx_source",
        )
    with c3:
        boundary = st.selectbox(
            "System boundary",
            list_boundaries(),
            index=list_boundaries().index(DEFAULT_BOUNDARY),
            format_func=lambda k: BOUNDARIES[k]["label"],
            key="nx_boundary",
        )

    st.caption(f"**{get_source(source)['label']}** — {get_source(source)['note']}")
    st.caption(f"**{get_boundary(boundary)['label']}** — {get_boundary(boundary)['note']}")

    try:
        position = societal_position(source, boundary)
        payback = energy_payback(source)
        spread = eroi_across_boundaries(source)
    except NetEnergyError as error:
        st.error(str(error))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Return on investment", f"{position['eroi']:.1f} : 1")
    m2.metric(
        "Reinvested to sustain supply",
        f"{position['reinvestment_fraction']:.1%}",
    )
    m3.metric("Energy payback", f"{payback['payback_years']:.2f} yr")
    m4.metric("Lifetime ratio", f"{payback['lifetime_ratio']:.1f} : 1")

    if position["below_societal_minimum"]:
        st.warning(
            f"At this boundary the ratio sits below {SOCIETAL_MINIMUM_EROI:.0f}, "
            f"the level usually taken as the minimum for an industrial society "
            f"with a meaningful non-energy sector. That threshold is contested; "
            f"the shape of the curve beneath it is not."
        )

    st.markdown("#### The same source at all three boundaries")
    boundary_fig = go.Figure(
        go.Bar(
            x=[row["label"] for row in spread["rows"]],
            y=[row["eroi"] for row in spread["rows"]],
            marker_color=[
                "#e07a5f" if row["boundary"] == boundary else "#3d5a80"
                for row in spread["rows"]
            ],
            text=[f"{row['eroi']:.1f}" for row in spread["rows"]],
            textposition="auto",
        )
    )
    boundary_fig.add_hline(
        y=SOCIETAL_MINIMUM_EROI,
        line_dash="dash",
        line_color="#c1666b",
        annotation_text=f"contested societal minimum ({SOCIETAL_MINIMUM_EROI:.0f})",
    )
    boundary_fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="energy returned per energy invested",
        xaxis_tickangle=-15,
    )
    st.plotly_chart(boundary_fig, use_container_width=True)
    st.info(spread["note"])

    st.markdown("#### Payback against yield")
    st.caption(
        "Location drives payback almost entirely, which is why a single "
        "published payback figure travels badly."
    )
    sensitivity = payback_sensitivity(source)
    payback_fig = go.Figure(
        go.Scatter(
            x=[row["capacity_factor"] for row in sensitivity],
            y=[row["payback_years"] for row in sensitivity],
            mode="lines+markers",
            line=dict(color="#3d5a80", width=3),
            marker=dict(
                size=[16 if row["is_reference"] else 9 for row in sensitivity],
                color=[
                    "#e07a5f" if row["is_reference"] else "#3d5a80"
                    for row in sensitivity
                ],
            ),
        )
    )
    payback_fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="capacity factor",
        yaxis_title="energy payback (years)",
    )
    st.plotly_chart(payback_fig, use_container_width=True)
    st.caption(payback["carbon_payback_note"])

    st.markdown("#### What this is telling you")
    for insight in get_net_energy_insights(source, boundary):
        st.markdown(f"- {insight}")


# ---------------------------------------------------------------------------
# The cliff
# ---------------------------------------------------------------------------
with tab_cliff:
    st.markdown("### The net energy cliff")
    st.caption(
        "The share of gross output that has to go back into producing energy "
        "is one over the ratio. The curve is flat across the top of the range "
        "and very steep at the bottom, and a difference that looks like a "
        "rounding error at thirty is decisive at three."
    )

    cliff = net_energy_cliff()

    cliff_fig = go.Figure()
    cliff_fig.add_trace(
        go.Scatter(
            name="Available to society",
            x=[row["eroi"] for row in cliff["rows"]],
            y=[row["surplus_fraction"] for row in cliff["rows"]],
            mode="lines+markers",
            fill="tozeroy",
            line=dict(color="#4f772d", width=3),
        )
    )
    cliff_fig.add_vline(
        x=SOCIETAL_MINIMUM_EROI,
        line_dash="dash",
        line_color="#c1666b",
        annotation_text="contested minimum",
    )
    cliff_fig.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="energy returned per energy invested",
        yaxis_title="share of gross output available for everything else",
        yaxis_tickformat=".0%",
        xaxis_type="log",
    )
    st.plotly_chart(cliff_fig, use_container_width=True)
    st.caption(cliff["minimum_caveat"])

    st.markdown("#### Every source against the cliff")
    cliff_boundary = st.selectbox(
        "At boundary",
        list_boundaries(),
        index=list_boundaries().index(DEFAULT_BOUNDARY),
        format_func=lambda k: BOUNDARIES[k]["label"],
        key="nx_cliff_boundary",
    )
    positions = sorted(
        (societal_position(key, cliff_boundary) for key in list_sources()),
        key=lambda p: -p["eroi"],
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Source": p["label"],
                    "EROI": round(p["eroi"], 1),
                    "Reinvested": f"{p['reinvestment_fraction']:.1%}",
                    "Available": f"{p['surplus_fraction']:.1%}",
                    "Below minimum": (
                        "Yes" if p["below_societal_minimum"] else "No"
                    ),
                }
                for p in positions
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### Where energy and carbon disagree")
    versus = energy_versus_carbon(boundary=cliff_boundary)
    versus_fig = go.Figure(
        go.Scatter(
            x=[row["eroi"] for row in versus["rows"]],
            y=[row["co2_g_per_kwh"] for row in versus["rows"]],
            mode="markers+text",
            text=[row["label"] for row in versus["rows"]],
            textposition="top center",
            marker=dict(size=12, color="#3d5a80"),
        )
    )
    versus_fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="energy returned per energy invested (log)",
        yaxis_title="g CO2 per kWh",
        xaxis_type="log",
    )
    st.plotly_chart(versus_fig, use_container_width=True)

    if versus["conflicts"]:
        st.markdown("**Sources ranked very differently by the two measures**")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Source": c["label"],
                        "Energy rank": c["energy_rank"],
                        "Carbon rank": c["carbon_rank"],
                        "EROI": round(c["eroi"], 1),
                        "g CO2/kWh": c["co2_g_per_kwh"],
                    }
                    for c in versus["conflicts"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )
    st.info(versus["no_composite_note"])


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------
with tab_storage:
    st.markdown("### What dispatchability costs in energy")
    st.caption(
        "The storage modules in this app treat batteries as something that "
        "makes intermittent supply usable. They do — and they consume energy "
        "to build and lose energy every cycle."
    )

    variable = [k for k in list_sources() if SOURCES[k]["intermittent"]]

    c1, c2, c3 = st.columns(3)
    with c1:
        buf_source = st.selectbox(
            "Variable source",
            variable,
            index=variable.index("solar_pv_utility"),
            format_func=lambda k: SOURCES[k]["label"],
            key="nx_buf_source",
        )
    with c2:
        storage = st.selectbox(
            "Storage",
            list_storage(),
            index=list_storage().index("lithium_ion"),
            format_func=lambda k: STORAGE[k]["label"],
            key="nx_storage",
        )
    with c3:
        buf_boundary = st.selectbox(
            "Boundary",
            list_boundaries(),
            index=list_boundaries().index(DEFAULT_BOUNDARY),
            format_func=lambda k: BOUNDARIES[k]["label"],
            key="nx_buf_boundary",
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        hours = st.slider("Storage (hours of rated capacity)", 0.0, 16.0, 4.0,
                          0.5, key="nx_hours")
    with c5:
        share = st.slider("Share of output cycled through storage", 0.0, 1.0,
                          0.35, 0.05, key="nx_share")
    with c6:
        curtail = st.slider("Curtailment", 0.0, 0.4, 0.05, 0.01,
                            key="nx_curtail")

    st.caption(f"**{get_storage(storage)['label']}** — {get_storage(storage)['note']}")

    buffered = buffered_eroi(
        buf_source, buf_boundary, storage,
        storage_hours=hours, buffered_share=share, curtailment=curtail,
    )

    b1, b2, b3 = st.columns(3)
    b1.metric("Unbuffered", f"{buffered['unbuffered_eroi']:.1f} : 1")
    b2.metric(
        "Buffered",
        f"{buffered['buffered_eroi']:.1f} : 1",
        delta=f"-{buffered['penalty_fraction']:.0%}",
        delta_color="inverse",
    )
    b3.metric(
        "Reinvested",
        f"{1 / buffered['buffered_eroi']:.1%}"
        if buffered["buffered_eroi"] > 0 else "n/a",
    )

    if buffered["crosses_societal_minimum"]:
        st.warning(
            "Buffering takes this source from above the contested societal "
            "minimum to below it. Whether it clears that bar depends entirely "
            "on whether the storage is counted — which is the point."
        )
    st.caption(buffered["note"])

    if buffered["intermittent"] and storage != "none":
        st.markdown("#### Where the energy went")
        waterfall = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=["absolute", "relative", "relative", "total"],
                x=[
                    "Lifetime generation",
                    "Curtailed",
                    "Lost round-tripping",
                    "Delivered",
                ],
                y=[
                    buffered["lifetime_output_kwh_per_kw"],
                    -buffered["lifetime_output_kwh_per_kw"] * curtail,
                    -(
                        buffered["lifetime_output_kwh_per_kw"] * (1 - curtail)
                        - buffered["delivered_kwh_per_kw"]
                    ),
                    0,
                ],
                decreasing=dict(marker=dict(color="#c1666b")),
                increasing=dict(marker=dict(color="#4f772d")),
                totals=dict(marker=dict(color="#1d3557")),
            )
        )
        waterfall.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="kWh per kW of capacity, over the lifetime",
        )
        st.plotly_chart(waterfall, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Term": "Energy invested in generation",
                        "kWh/kW": round(
                            buffered["generation_invested_kwh_per_kw"]
                        ),
                    },
                    {
                        "Term": "Energy invested in storage",
                        "kWh/kW": round(
                            buffered["storage_invested_kwh_per_kw"]
                        ),
                    },
                    {
                        "Term": "Storage replacements over the life",
                        "kWh/kW": round(buffered["storage_replacements"], 2),
                    },
                    {
                        "Term": "Round-trip efficiency",
                        "kWh/kW": buffered["round_trip_efficiency"],
                    },
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Every storage option, same source")
    storage_rows = []
    for key in list_storage():
        entry = buffered_eroi(
            buf_source, buf_boundary, key,
            storage_hours=hours, buffered_share=share, curtailment=curtail,
        )
        storage_rows.append({
            "Storage": STORAGE[key]["label"],
            "Round trip": f"{STORAGE[key]['round_trip_efficiency']:.0%}",
            "Embodied (kWh/kWh)": STORAGE[key]["embodied_energy_kwh_per_kwh"],
            "Buffered EROI": round(entry["buffered_eroi"], 2),
            "Penalty": f"{entry['penalty_fraction']:.0%}",
        })
    st.dataframe(pd.DataFrame(storage_rows), hide_index=True,
                 use_container_width=True)
    st.caption(
        "Efficiency alone does not rank these. Hydrogen loses nearly two "
        "thirds of every round trip and costs a fraction of lithium-ion's "
        "embodied energy per kilowatt-hour of capacity, so which wins depends "
        "on how much of the output is being cycled."
    )


# ---------------------------------------------------------------------------
# Energy quality
# ---------------------------------------------------------------------------
with tab_quality:
    st.markdown("### A joule of electricity and a joule of heat")
    st.caption(
        "Counting joules treats them as equal. Weighting them by what they "
        "can do does not. The two conventions reverse the ranking of electric "
        "against thermal options, so this page reports both and picks neither."
    )

    chosen = st.multiselect(
        "Sources",
        list_sources(),
        default=["heat_pump_displacement", "solar_pv_utility",
                 "efficiency_insulation"],
        format_func=lambda k: SOURCES[k]["label"],
        key="nx_quality_sources",
    )
    q_boundary = st.selectbox(
        "Boundary",
        list_boundaries(),
        index=list_boundaries().index(DEFAULT_BOUNDARY),
        format_func=lambda k: BOUNDARIES[k]["label"],
        key="nx_quality_boundary",
    )

    if len(chosen) < 2:
        st.info("Pick at least two sources.")
    else:
        comparison = quality_comparison(chosen, q_boundary)

        if comparison["conventions_disagree"]:
            st.warning(comparison["note"])
        else:
            st.success(comparison["note"])

        q_fig = go.Figure()
        for convention, colour in (
            ("thermal_equivalent", "#9aa5a0"),
            ("exergy", "#3d5a80"),
            ("primary_equivalent", "#7b506f"),
        ):
            q_fig.add_trace(
                go.Bar(
                    name=convention.replace("_", " ").title(),
                    x=[row["label"] for row in comparison["rows"]],
                    y=[row[convention] for row in comparison["rows"]],
                    marker_color=colour,
                )
            )
        q_fig.update_layout(
            height=380,
            barmode="group",
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="weighted energy return",
            xaxis_tickangle=-20,
            legend=dict(orientation="h", y=1.15),
        )
        st.plotly_chart(q_fig, use_container_width=True)

        r1, r2, r3 = st.columns(3)
        for column, convention in (
            (r1, "thermal_equivalent"),
            (r2, "exergy"),
            (r3, "primary_equivalent"),
        ):
            column.markdown(f"**{convention.replace('_', ' ').title()}**")
            for i, key in enumerate(comparison["rankings"][convention], 1):
                column.markdown(f"{i}. {SOURCES[key]['label']}")

        st.markdown("#### The carriers")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Carrier": get_carrier(key)["label"],
                        "Exergy factor": get_carrier(key)["exergy_factor"],
                        "Primary equivalent": get_carrier(key)["primary_equivalent"],
                        "Note": get_carrier(key)["note"],
                    }
                    for key in sorted(
                        {SOURCES[s]["carrier"] for s in chosen}
                    )
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# A household
# ---------------------------------------------------------------------------
with tab_household:
    st.markdown("### A household's own net energy position")
    st.caption(
        "Efficiency measures count as supply here, because a negawatt has a "
        "return on investment like anything else and usually a better one."
    )

    h_boundary = st.selectbox(
        "Boundary",
        list_boundaries(),
        index=list_boundaries().index(DEFAULT_BOUNDARY),
        format_func=lambda k: BOUNDARIES[k]["label"],
        key="nx_h_boundary",
    )
    household_sources = st.multiselect(
        "Measures installed",
        list_sources(),
        default=["solar_pv_rooftop_temperate", "efficiency_insulation",
                 "heat_pump_displacement"],
        format_func=lambda k: SOURCES[k]["label"],
        key="nx_h_sources",
    )

    if not household_sources:
        st.info("Pick at least one measure.")
    else:
        installations = {}
        cols = st.columns(min(3, len(household_sources)))
        for i, key in enumerate(household_sources):
            with cols[i % len(cols)]:
                installations[key] = st.number_input(
                    f"{SOURCES[key]['label']} (kW)",
                    min_value=0.1, value=4.0, step=0.5,
                    key=f"nx_kw_{key}",
                )

        h_storage = st.selectbox(
            "Household storage",
            list_storage(),
            index=list_storage().index("none"),
            format_func=lambda k: STORAGE[k]["label"],
            key="nx_h_storage",
        )
        h_hours = st.slider(
            "Storage hours", 0.0, 16.0, 0.0, 0.5, key="nx_h_hours"
        )

        position = household_position(
            installations, h_boundary, h_storage, h_hours
        )

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Gross", f"{position['gross_annual_kwh']:,.0f} kWh/yr")
        p2.metric("Invested", f"{position['invested_annual_kwh']:,.0f} kWh/yr")
        p3.metric("Net", f"{position['net_annual_kwh']:,.0f} kWh/yr")
        p4.metric("Combined EROI", f"{position['combined_eroi']:.1f} : 1")

        st.caption(position["note"])
        if position["below_societal_minimum"]:
            st.warning(
                "This household's own supply sits below the contested societal "
                "minimum. That is a statement about the mix, not about the "
                "src.lifestyle.household."
            )

        h_fig = go.Figure()
        h_fig.add_trace(
            go.Bar(
                name="Net to the household",
                x=[row["label"] for row in position["installations"]],
                y=[row["annual_net_kwh"] for row in position["installations"]],
                marker_color="#4f772d",
            )
        )
        h_fig.add_trace(
            go.Bar(
                name="Consumed producing it",
                x=[row["label"] for row in position["installations"]],
                y=[
                    row["annual_invested_kwh"]
                    for row in position["installations"]
                ],
                marker_color="#c1666b",
            )
        )
        h_fig.update_layout(
            height=360,
            barmode="stack",
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="kWh per year",
            xaxis_tickangle=-20,
            legend=dict(orientation="h", y=1.15),
        )
        st.plotly_chart(h_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Measure": row["label"],
                        "kW": row["kw"],
                        "EROI": round(row["eroi"], 1),
                        "Gross (kWh/yr)": round(row["annual_kwh"]),
                        "Net (kWh/yr)": round(row["annual_net_kwh"]),
                    }
                    for row in position["installations"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        with st.form("save_net_energy_position"):
            name = st.text_input("Save this as", value="")
            if st.form_submit_button("Save") and name.strip():
                try:
                    save_position(user_id, name, position)
                    st.success(f"Saved '{name.strip()}'.")
                except NetEnergyError as error:
                    st.error(str(error))


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved positions")
    saved = get_positions(user_id)
    if not saved:
        st.info("Nothing saved yet. Save a position from the household tab.")
    else:
        for record in saved:
            with st.expander(
                f"{record['name']} — {record['combined_eroi']:.1f} : 1, "
                f"{record['net_annual_kwh']:,.0f} kWh/yr net"
            ):
                payload = record["payload"]
                st.write(
                    f"Boundary: "
                    f"**{BOUNDARIES.get(record['boundary'], {}).get('label', record['boundary'])}**"
                )
                st.write(
                    f"Gross {payload.get('gross_annual_kwh', 0):,.0f} kWh/yr, "
                    f"{payload.get('reinvestment_fraction', 0):.0%} consumed "
                    f"producing it. Storage: {payload.get('storage', 'none')}."
                )
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Measure": SOURCES.get(
                                    row["source"], {}
                                ).get("label", row["source"]),
                                "kW": row["kw"],
                                "EROI": round(row["eroi"], 1),
                                "Net (kWh/yr)": round(row["annual_net_kwh"]),
                            }
                            for row in payload.get("installations", [])
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(f"Saved {record['created_at']}")
                if st.button("Delete", key=f"nx_del_{record['id']}"):
                    if delete_position(user_id, record["id"]):
                        st.success("Deleted.")
                        st.rerun()
