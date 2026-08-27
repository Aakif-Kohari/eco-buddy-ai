"""The particles emitted alongside the CO2, which change the answer.

The multi-gas page handles every well-mixed greenhouse gas this app emits. It
handles none of the aerosols coming out of the same chimney — and those carry a
near-term forcing that is large, has both signs, and reorders options the app
already recommends between.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from aerosol_forcing import (
    DEPOSITION_REGIONS,
    HORIZONS,
    SOURCES,
    SPECIES,
    AerosolError,
    assess_activity,
    co2_only_error,
    compare_sources,
    delete_assessment,
    get_aerosol_insights,
    get_assessments,
    get_region,
    get_source,
    get_species,
    list_regions,
    list_sectors,
    list_sources,
    list_species,
    save_assessment,
    uncertainty_range,
    unmasking,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🌫️ Aerosols & Short-Lived Climate Forcers</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Black carbon absorbs and warms. Sulphate and organic carbon scatter and "
    "cool. Both come out of the same chimney as the CO2, both are gone within "
    "weeks, and between them they decide whether a near-term climate ranking "
    "matches the carbon one."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**Both signs, always.** Warming and cooling species are accumulated separately
and netted only at the end. A module that reported only the warming half would
be an argument for dirty air rather than an inventory — and the cooling half is
made of particles that kill people, so it is not a benefit worth preserving.

**Both horizons, always.** These species live for days. On a twenty-year view
black carbon dominates a traditional cookstove; on a hundred-year view it is a
rounding error beside the CO2. Any single-horizon figure has taken a side in a
live policy argument without saying so, so there is no way to request just one.

**The fuel label is not the emission factor.** A diesel with a particulate
filter and one without are identical on the CO2 line and differ by more than an
order of magnitude in black carbon. The source table is organised on emission
control technology for exactly that reason.

**Deposition on snow is a separate line.** Black carbon that lands on ice keeps
absorbing after it has left the air, at several times its global-average
efficacy. Folding that into one worldwide factor would erase the region where
it matters most.

**Nothing is reported without bounds.** Black carbon's hundred-year GWP spans a
factor of seventeen in the published literature, and the indirect effect of
aerosols on cloud is the single largest uncertainty in the forcing budget.
Where the bounds straddle zero this page says the sign is undetermined rather
than quoting the central sign.

**This is an overlay, not a replacement.** Nothing here redefines a total
reported elsewhere. Results are additive to the well-mixed gas inventory and
are labelled short-lived throughout, so you always know which part of a figure
will still be there in fifty years.
        """
    )

st.markdown("---")

tab_activity, tab_compare, tab_unmask, tab_uncertainty, tab_saved = st.tabs(
    [
        "🔥 One activity",
        "⚖️ The horizon flip",
        "🚢 Unmasking",
        "📊 Uncertainty",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# One activity
# ---------------------------------------------------------------------------
with tab_activity:
    st.markdown("### What comes out alongside the carbon dioxide")

    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        source = st.selectbox(
            "Source",
            list_sources(),
            index=list_sources().index("wood_stove_traditional"),
            format_func=lambda k: SOURCES[k]["label"],
            key="ae_source",
        )
    with c2:
        units = st.number_input(
            f"Quantity ({get_source(source)['unit']})",
            min_value=0.1, value=100.0, step=10.0, key="ae_units",
        )
    with c3:
        region = st.selectbox(
            "Where it is emitted",
            list_regions(),
            index=list_regions().index("temperate"),
            format_func=lambda k: DEPOSITION_REGIONS[k]["label"],
            key="ae_region",
        )

    st.caption(f"**{get_source(source)['label']}** — {get_source(source)['note']}")
    if get_region(region)["bc_efficacy"] != 1.0:
        st.caption(f"**{get_region(region)['label']}** — {get_region(region)['note']}")

    try:
        result = assess_activity(source, units, region)
    except AerosolError as error:
        st.error(str(error))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("CO2 alone", f"{result['co2_kg']:,.0f} kg")
    m2.metric(
        "Total, 20-year view",
        f"{result['horizons'][20]['total_co2e']:,.0f} kg CO2e",
        delta=f"{result['near_term_multiple']:.2f}× the CO2",
    )
    m3.metric(
        "Total, 100-year view",
        f"{result['horizons'][100]['total_co2e']:,.0f} kg CO2e",
        delta=f"{result['long_term_multiple']:.2f}× the CO2",
    )
    m4.metric(
        "Short-lived share, 20 yr",
        f"{result['horizons'][20]['slcf_share_of_total']:.0%}",
    )

    if result["sign_flips_between_horizons"]:
        st.warning(
            "The net short-lived effect changes sign between the two horizons "
            "for this source. Any single-horizon figure would be taking a side."
        )
    if result["slcf_dominates_near_term"]:
        st.warning(
            "In the near term the short-lived species outweigh the CO2 "
            "entirely. A CO2-only inventory is measuring the smaller half here."
        )

    st.markdown("#### Species, with the sign kept")
    for horizon in HORIZONS:
        entry = result["horizons"][horizon]
        if not entry["species"]:
            continue
        st.markdown(f"**{horizon}-year horizon**")
        species_fig = go.Figure(
            go.Bar(
                x=[row["co2e_central"] for row in entry["species"]],
                y=[row["label"] for row in entry["species"]],
                orientation="h",
                marker_color=[
                    "#c1666b" if row["warms"] else "#3d5a80"
                    for row in entry["species"]
                ],
                error_x=dict(
                    type="data",
                    symmetric=False,
                    array=[
                        row["co2e_high"] - row["co2e_central"]
                        for row in entry["species"]
                    ],
                    arrayminus=[
                        row["co2e_central"] - row["co2e_low"]
                        for row in entry["species"]
                    ],
                    color="#555",
                ),
            )
        )
        species_fig.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="kg CO2e (positive warms, negative cools)",
            showlegend=False,
        )
        species_fig.add_vline(x=0, line_width=1, line_color="#888")
        st.plotly_chart(species_fig, use_container_width=True,
                        key=f"ae_species_{horizon}")

    st.caption(
        "Error bars are the published low and high bounds, not a confidence "
        "interval this app computed. They are wide because the science is."
    )

    st.markdown("#### The warming half and the cooling half, before netting")
    ledger_rows = []
    for horizon in HORIZONS:
        entry = result["horizons"][horizon]
        ledger_rows.append({
            "Horizon": f"{horizon} yr",
            "Warming species": round(entry["warming_co2e"], 1),
            "Cooling species": round(entry["cooling_co2e"], 1),
            "Net short-lived": round(entry["net_co2e"], 1),
            "Plus CO2": round(entry["total_co2e"], 1),
        })
    st.dataframe(pd.DataFrame(ledger_rows), hide_index=True,
                 use_container_width=True)
    st.info(result["horizons"][20]["sign_note"])

    st.markdown("#### How wrong a CO2-only inventory is about this")
    error = co2_only_error(source, units, region)
    error_fig = go.Figure()
    error_fig.add_trace(
        go.Bar(
            name="CO2 only",
            x=[f"{row['horizon_years']} yr" for row in error["rows"]],
            y=[row["co2_only_kg"] for row in error["rows"]],
            marker_color="#9aa5a0",
        )
    )
    error_fig.add_trace(
        go.Bar(
            name="With short-lived species",
            x=[f"{row['horizon_years']} yr" for row in error["rows"]],
            y=[row["with_slcf_kg"] for row in error["rows"]],
            marker_color="#1d3557",
        )
    )
    error_fig.update_layout(
        height=320,
        barmode="group",
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="kg CO2e",
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(error_fig, use_container_width=True)

    st.markdown("#### What this is telling you")
    for insight in get_aerosol_insights(result):
        st.markdown(f"- {insight}")

    st.caption(result["overlay_note"])

    with st.form("save_aerosol_assessment"):
        name = st.text_input("Save this as", value="")
        if st.form_submit_button("Save") and name.strip():
            try:
                save_assessment(user_id, name, result)
                st.success(f"Saved '{name.strip()}'.")
            except AerosolError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# The horizon flip
# ---------------------------------------------------------------------------
with tab_compare:
    st.markdown("### Where the horizon changes which option is better")
    st.caption(
        "Not the magnitude — the ordering. Where two options swap places "
        "between the twenty-year and hundred-year views, that swap is the "
        "finding, and a report quoting one horizon has hidden it."
    )

    default_pair = ["wood_stove_traditional", "lpg_cooking"]
    chosen = st.multiselect(
        "Sources to compare",
        list_sources(),
        default=default_pair,
        format_func=lambda k: SOURCES[k]["label"],
        key="ae_compare",
    )

    if len(chosen) < 2:
        st.info("Pick at least two sources.")
    else:
        compare_units = st.number_input(
            "Per unit of fuel or biomass", min_value=0.1, value=1.0, step=0.5,
            key="ae_compare_units",
        )
        comparison = compare_sources(chosen, compare_units, region)

        if comparison["ranking_changes_with_horizon"]:
            st.warning(comparison["note"])
        else:
            st.success(comparison["note"])

        compare_fig = go.Figure()
        compare_fig.add_trace(
            go.Bar(
                name="20-year view",
                x=[row["label"] for row in comparison["results"]],
                y=[row["total_co2e_20"] for row in comparison["results"]],
                marker_color="#c1666b",
            )
        )
        compare_fig.add_trace(
            go.Bar(
                name="100-year view",
                x=[row["label"] for row in comparison["results"]],
                y=[row["total_co2e_100"] for row in comparison["results"]],
                marker_color="#3d5a80",
            )
        )
        compare_fig.add_trace(
            go.Scatter(
                name="CO2 alone",
                x=[row["label"] for row in comparison["results"]],
                y=[row["co2_kg"] for row in comparison["results"]],
                mode="markers",
                marker=dict(size=14, symbol="diamond", color="#1d3557"),
            )
        )
        compare_fig.update_layout(
            height=400,
            barmode="group",
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="kg CO2e per unit",
            xaxis_tickangle=-25,
            legend=dict(orientation="h", y=1.15),
        )
        st.plotly_chart(compare_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Source": row["label"],
                        "CO2 alone": round(row["co2_kg"], 2),
                        "Total, 20 yr": round(row["total_co2e_20"], 2),
                        "Total, 100 yr": round(row["total_co2e_100"], 2),
                        "Net SLCF, 20 yr": round(row["net_slcf_20"], 2),
                        "Net SLCF, 100 yr": round(row["net_slcf_100"], 2),
                    }
                    for row in comparison["results"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        r1, r2 = st.columns(2)
        r1.markdown("**Best first, 20-year view**")
        for i, key in enumerate(comparison["ranking_20"], 1):
            r1.markdown(f"{i}. {SOURCES[key]['label']}")
        r2.markdown("**Best first, 100-year view**")
        for i, key in enumerate(comparison["ranking_100"], 1):
            r2.markdown(f"{i}. {SOURCES[key]['label']}")


# ---------------------------------------------------------------------------
# Unmasking
# ---------------------------------------------------------------------------
with tab_unmask:
    st.markdown("### Cleaning the air, and what it gives back")
    st.caption(
        "Removing a cooling aerosol unmasks warming that was previously being "
        "suppressed. This is a real, measured effect. It is not an argument "
        "for keeping the particles, so the avoided exposure is reported "
        "alongside it rather than left out."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        before = st.selectbox(
            "Before",
            list_sources(),
            index=list_sources().index("shipping_hfo_high_sulphur"),
            format_func=lambda k: SOURCES[k]["label"],
            key="ae_before",
        )
    with c2:
        after = st.selectbox(
            "After",
            list_sources(),
            index=list_sources().index("shipping_low_sulphur"),
            format_func=lambda k: SOURCES[k]["label"],
            key="ae_after",
        )
    with c3:
        unmask_units = st.number_input(
            "Fuel (kg)", min_value=1.0, value=1000.0, step=100.0,
            key="ae_unmask_units",
        )

    change = unmasking(before, after, unmask_units, region)

    u1, u2, u3 = st.columns(3)
    u1.metric(
        "Near-term change (20 yr)",
        f"{change['horizons'][20]['delta_co2e']:+,.0f} kg CO2e",
        delta="warming" if change["horizons"][20]["is_near_term_warming"]
              else "cooling",
        delta_color="inverse" if change["horizons"][20]["is_near_term_warming"]
                    else "normal",
    )
    u2.metric(
        "Long-term change (100 yr)",
        f"{change['horizons'][100]['delta_co2e']:+,.0f} kg CO2e",
    )
    u3.metric(
        "Particulate avoided",
        f"{change['pm_avoided_kg']:,.1f} kg",
        help="Direct particulate plus secondary sulphate.",
    )

    if change["is_unmasking"]:
        st.warning(change["note"])
    else:
        st.success(change["note"])

    unmask_fig = go.Figure()
    for horizon in HORIZONS:
        entry = change["horizons"][horizon]
        unmask_fig.add_trace(
            go.Bar(
                name=f"{horizon}-year view",
                x=["Before", "After"],
                y=[entry["before_co2e"], entry["after_co2e"]],
            )
        )
    unmask_fig.update_layout(
        height=340,
        barmode="group",
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="kg CO2e",
        legend=dict(orientation="h", y=1.15),
    )
    unmask_fig.add_hline(y=0, line_width=1, line_color="#888")
    st.plotly_chart(unmask_fig, use_container_width=True)

    st.markdown("#### The trade-off, stated as one")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Effect": "Near-term climate (20 yr)",
                    "Direction": (
                        "Worse" if change["horizons"][20]["is_near_term_warming"]
                        else "Better"
                    ),
                    "Size": f"{change['horizons'][20]['delta_co2e']:+,.0f} kg CO2e",
                },
                {
                    "Effect": "Long-term climate (100 yr)",
                    "Direction": (
                        "Worse" if change["horizons"][100]["is_near_term_warming"]
                        else "Better"
                    ),
                    "Size": f"{change['horizons'][100]['delta_co2e']:+,.0f} kg CO2e",
                },
                {
                    "Effect": "Sulphur dioxide avoided",
                    "Direction": "Better",
                    "Size": f"{change['so2_avoided_kg']:,.1f} kg",
                },
                {
                    "Effect": "Indicative mortality avoided",
                    "Direction": "Better",
                    "Size": f"{change['indicative_deaths_avoided']:.4f} deaths",
                },
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(change["mortality_caveat"])


# ---------------------------------------------------------------------------
# Uncertainty
# ---------------------------------------------------------------------------
with tab_uncertainty:
    st.markdown("### The bounds, which are the honest part")

    unc_source = st.selectbox(
        "Source",
        list_sources(),
        index=list_sources().index("wood_stove_traditional"),
        format_func=lambda k: SOURCES[k]["label"],
        key="ae_unc_source",
    )
    unc = uncertainty_range(unc_source, units, region)

    for row in unc["rows"]:
        st.markdown(f"**{row['horizon_years']}-year horizon**")
        b1, b2, b3 = st.columns(3)
        b1.metric("Low", f"{row['low']:,.0f} kg CO2e")
        b2.metric("Central", f"{row['central']:,.0f} kg CO2e")
        b3.metric("High", f"{row['high']:,.0f} kg CO2e")
        if not row["sign_determined"]:
            st.warning(
                "The bounds straddle zero at this horizon, so whether this "
                "activity warms or cools in net terms is not determined by "
                "the current science. The central estimate's sign is not a "
                "finding."
            )

    unc_fig = go.Figure()
    unc_fig.add_trace(
        go.Bar(
            x=[f"{row['horizon_years']} yr" for row in unc["rows"]],
            y=[row["central"] for row in unc["rows"]],
            marker_color="#1d3557",
            error_y=dict(
                type="data",
                symmetric=False,
                array=[row["high"] - row["central"] for row in unc["rows"]],
                arrayminus=[row["central"] - row["low"] for row in unc["rows"]],
                color="#555",
            ),
        )
    )
    unc_fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="kg CO2e",
    )
    unc_fig.add_hline(y=0, line_width=1, line_color="#888")
    st.plotly_chart(unc_fig, use_container_width=True)
    st.info(unc["note"])

    st.markdown("#### The underlying species ranges")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Species": SPECIES[key]["label"],
                    "Lifetime (days)": SPECIES[key]["lifetime_days"],
                    "GWP20 low": SPECIES[key]["gwp"][20]["low"],
                    "GWP20 central": SPECIES[key]["gwp"][20]["central"],
                    "GWP20 high": SPECIES[key]["gwp"][20]["high"],
                    "GWP100 central": SPECIES[key]["gwp"][100]["central"],
                    "Deposits on snow": (
                        "Yes" if SPECIES[key]["deposition_sensitive"] else "No"
                    ),
                }
                for key in list_species()
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    for key in list_species():
        st.caption(f"**{get_species(key)['label']}** — {get_species(key)['note']}")


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved assessments")
    saved = get_assessments(user_id)
    if not saved:
        st.info("Nothing saved yet. Save an assessment from the first tab.")
    else:
        for record in saved:
            with st.expander(
                f"{record['name']} — {record['co2_kg']:,.0f} kg CO2, "
                f"{record['net_slcf_20']:+,.0f} kg CO2e short-lived over 20 yr"
            ):
                payload = record["payload"]
                st.write(
                    f"**{SOURCES.get(record['source'], {}).get('label', record['source'])}**, "
                    f"{payload.get('units', 0):,.0f} {payload.get('unit', '')}, "
                    f"{payload.get('region', '')}"
                )
                st.write(
                    f"{payload.get('near_term_multiple', 0):.2f}× the CO2 over "
                    f"20 years, {payload.get('long_term_multiple', 0):.2f}× "
                    f"over 100."
                )
                if payload.get("sign_flips_between_horizons"):
                    st.caption(
                        "The net short-lived effect changed sign between the "
                        "two horizons for this one."
                    )
                st.caption(f"Saved {record['created_at']}")
                if st.button("Delete", key=f"ae_del_{record['id']}"):
                    if delete_assessment(user_id, record["id"]):
                        st.success("Deleted.")
                        st.rerun()
