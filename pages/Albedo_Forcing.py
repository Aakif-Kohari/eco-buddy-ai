"""What a roof's colour does to the planet, not just to the room beneath it.

The Urban Heat Island page uses albedo to estimate how much hotter a surface
gets. This page does the other half: it converts the same reflectivity change
into tonnes of CO2, so a tin of white paint can be compared against a heat pump.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from albedo_forcing import (
    DEFAULT_HORIZON_YEARS,
    LATITUDE_BANDS,
    SURFACES,
    AlbedoError,
    abatement_cost,
    canopy_albedo_penalty,
    canopy_crossover,
    delete_assessment,
    effective_albedo,
    get_albedo_insights,
    get_assessments,
    get_latitude_band,
    get_surface,
    horizon_sensitivity,
    latitude_sensitivity,
    list_horizons,
    list_latitude_bands,
    list_surfaces,
    local_versus_global,
    save_assessment,
    solar_panel_net,
    surface_change,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🪞 Surface Albedo & Radiative Forcing</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Sunlight a surface reflects back to space is energy that never enters the "
    "climate system. Reflect more of it and you have done something with the "
    "same sign as not emitting — measurable, immediate, and until now missing "
    "from this app entirely."
)

with st.expander("How this is calculated, and what it deliberately will not do"):
    st.markdown(
        """
**The horizon is not optional.** An albedo change forces continuously for as
long as the surface stays bright. A CO2 emission is a pulse whose forcing decays
as the carbon is taken up. Comparing them means integrating both to some year,
and the answer grows with the year you pick. Every figure on this page carries
its horizon, because a single kg-CO2e-per-square-metre number has already made
that choice for you and hidden it.

**Four steps, each visible.** Surface forcing, then what escapes through the
atmosphere, then division by the area of the Earth, then CO2-equivalence. The
headline is large enough to deserve scepticism, so the derivation is shown
rather than asserted.

**Cloud is most of the difference between published coefficients.** Only about
three quarters of a surface reflection escapes under clear sky, and around a
seventh under thick cloud. A reflection reabsorbed by the air above the roof has
cooled nothing.

**Latitude changes the answer by a factor of three.** The same white roof is
worth roughly three times as much in the dry subtropics as at sixty degrees
north. The subtropics beat the equator, incidentally, because the equator is
cloudier.

**Soiling is modelled, not ignored.** A cool roof loses close to a fifth of its
datasheet reflectance in the first two or three years. Claims built on day-one
values are that much too high.

**Local cooling and global forcing are never summed.** A white roof cools the
street and the planet by the same mechanism. Irrigated turf cools the street by
evaporating water and does almost nothing globally, while spending water this
app treats as scarce elsewhere. Two benefits, two units, no arithmetic between
them.

**The canopy answer can be negative.** A conifer stand over seasonal snow hides
a surface reflecting 0.72 behind one reflecting 0.21, and boreal forests hold
little carbon. Above a certain latitude the darkening beats the sequestration,
and this page will say so.
        """
    )

st.markdown("---")

tab_surface, tab_canopy, tab_solar, tab_cost, tab_saved = st.tabs(
    [
        "🏠 A surface",
        "🌲 The canopy question",
        "☀️ Solar panels",
        "💷 Cost per tonne",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# A surface
# ---------------------------------------------------------------------------
with tab_surface:
    st.markdown("### Changing one surface for another")

    c1, c2, c3 = st.columns(3)
    with c1:
        from_surface = st.selectbox(
            "From",
            list_surfaces(),
            index=list_surfaces().index("dark_roof"),
            format_func=lambda k: SURFACES[k]["label"],
            key="af_from",
        )
    with c2:
        to_surface = st.selectbox(
            "To",
            list_surfaces(),
            index=list_surfaces().index("cool_white_roof"),
            format_func=lambda k: SURFACES[k]["label"],
            key="af_to",
        )
    with c3:
        area = st.number_input(
            "Area (m²)", min_value=1.0, value=100.0, step=10.0, key="af_area"
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        band = st.selectbox(
            "Latitude band",
            list_latitude_bands(),
            index=list_latitude_bands().index("temperate"),
            format_func=lambda k: LATITUDE_BANDS[k]["label"],
            key="af_band",
        )
    with c5:
        horizon = st.selectbox(
            "Time horizon (years)",
            list_horizons(),
            index=list_horizons().index(DEFAULT_HORIZON_YEARS),
            key="af_horizon",
        )
    with c6:
        apply_soiling = st.checkbox(
            "Allow for soiling",
            value=True,
            help="Off uses datasheet reflectance, which overstates a cool roof.",
            key="af_soiling",
        )

    st.caption(f"**{get_surface(to_surface)['label']}** — {get_surface(to_surface)['note']}")
    st.caption(f"**{get_latitude_band(band)['label']}** — {get_latitude_band(band)['note']}")

    try:
        result = surface_change(
            from_surface, to_surface, area, band,
            horizon_years=horizon, apply_soiling=apply_soiling,
        )
    except AlbedoError as error:
        st.error(str(error))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Albedo change", f"{result['delta_albedo']:+.3f}")
    m2.metric(
        "Forcing at the surface",
        f"{result['local_forcing_w_m2']:+.1f} W/m²",
        help="Negative is cooling, matching the usual forcing convention.",
    )
    m3.metric(
        "CO2 equivalent",
        f"{result['co2_equivalent_kg'] / 1000:+,.2f} t",
        delta="offset" if result["is_offset"] else "emission",
        delta_color="normal" if result["is_offset"] else "inverse",
    )
    m4.metric(
        "Per square metre",
        f"{result['co2_equivalent_kg_per_m2']:+,.1f} kg",
    )

    st.markdown("#### The four steps, so the headline can be checked")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Step": "1. Sunlight arriving at the surface",
                    "Value": f"{result['insolation_w_m2']:,.0f} W/m²",
                    "Why it matters": "Annual mean for this latitude band.",
                },
                {
                    "Step": "2. Albedo change applied",
                    "Value": f"{result['delta_albedo']:+.3f}",
                    "Why it matters": (
                        "Time-averaged for soiling."
                        if result["soiling_applied"]
                        else "Datasheet values — an overstatement."
                    ),
                },
                {
                    "Step": "3. Fraction escaping to space",
                    "Value": f"{result['upward_transmittance']:.0%}",
                    "Why it matters": (
                        f"At {result['cloud_fraction']:.0%} cloud. The rest is "
                        f"reabsorbed and cools nothing."
                    ),
                },
                {
                    "Step": "4. Spread over the Earth, then converted",
                    "Value": f"{result['global_forcing_w_m2']:.3e} W/m²",
                    "Why it matters": (
                        f"Sustained for {result['horizon_years']:.0f} years and "
                        f"matched against a CO2 pulse."
                    ),
                },
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### The horizon changes the answer")
    horizon_rows = horizon_sensitivity(
        from_surface, to_surface, area, band, apply_soiling=apply_soiling
    )
    horizon_fig = go.Figure(
        go.Bar(
            x=[f"{row['horizon_years']} yr" for row in horizon_rows],
            y=[abs(row["co2_equivalent_kg"]) / 1000 for row in horizon_rows],
            marker_color="#3d5a80",
            text=[
                f"{abs(row['co2_equivalent_kg']) / 1000:,.1f} t"
                for row in horizon_rows
            ],
            textposition="auto",
        )
    )
    horizon_fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="tonnes CO2 equivalent",
    )
    st.plotly_chart(horizon_fig, use_container_width=True)
    st.caption(
        "The roof does exactly the same thing in every bar. What changes is "
        "the CO2 pulse it is being compared against, which decays while the "
        "roof does not."
    )

    st.markdown("#### The same intervention, by latitude")
    lat_rows = latitude_sensitivity(
        from_surface, to_surface, area,
        horizon_years=horizon, apply_soiling=apply_soiling,
    )
    lat_fig = go.Figure(
        go.Bar(
            x=[row["label"] for row in lat_rows],
            y=[abs(row["co2_equivalent_kg"]) / 1000 for row in lat_rows],
            marker_color=[
                "#e07a5f" if row["latitude_band"] == band else "#3d5a80"
                for row in lat_rows
            ],
        )
    )
    lat_fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="tonnes CO2 equivalent",
        xaxis_tickangle=-30,
    )
    st.plotly_chart(lat_fig, use_container_width=True)

    if result["soiling_applied"] and result["soiling_to"] \
            and result["soiling_to"]["soils"]:
        st.markdown("#### What soiling costs the claim")
        soiling = result["soiling_to"]
        s1, s2, s3 = st.columns(3)
        s1.metric("Datasheet", f"{soiling['initial_albedo']:.2f}")
        s2.metric("Effective average", f"{soiling['effective_albedo']:.3f}")
        s3.metric(
            "Of nameplate", f"{soiling['fraction_of_nameplate']:.0%}"
        )
        recoat = st.slider(
            "Recoating interval (years)", 2, 30, 10, key="af_recoat"
        )
        recoated = effective_albedo(to_surface, horizon, recoat)
        st.caption(
            f"Recoating every {recoat} years holds the average at "
            f"{recoated['effective_albedo']:.3f} instead of "
            f"{soiling['effective_albedo']:.3f}."
        )

    st.markdown("#### Local and global, side by side and never added")
    split = local_versus_global(result)
    l1, l2 = st.columns(2)
    l1.metric(
        "Surface temperature",
        f"{split['local_surface_temp_delta_c']:+.1f} °C",
        help="The street-level effect.",
    )
    l2.metric(
        "Global equivalent",
        f"{split['global_co2_equivalent_kg'] / 1000:+,.2f} t CO2",
        help="The planetary effect.",
    )
    st.info(split["explanation"])

    st.markdown("#### What this is telling you")
    for insight in get_albedo_insights(result):
        st.markdown(f"- {insight}")

    with st.form("save_albedo_assessment"):
        name = st.text_input("Save this as", value="")
        if st.form_submit_button("Save") and name.strip():
            try:
                save_assessment(user_id, name, result)
                st.success(f"Saved '{name.strip()}'.")
            except AlbedoError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# The canopy question
# ---------------------------------------------------------------------------
with tab_canopy:
    st.markdown("### Where planting trees stops paying")
    st.caption(
        "Both the canopy planner and the heat island page recommend planting, "
        "on cooling and sequestration grounds. Both are right about what they "
        "measure. Neither checks the albedo, and over seasonal snow the albedo "
        "can win."
    )

    c1, c2 = st.columns(2)
    with c1:
        forest = st.selectbox(
            "Species",
            ["conifer_forest", "deciduous_forest"],
            format_func=lambda k: SURFACES[k]["label"],
            key="af_forest",
        )
    with c2:
        canopy_horizon = st.selectbox(
            "Horizon (years)",
            list_horizons(),
            index=list_horizons().index(DEFAULT_HORIZON_YEARS),
            key="af_canopy_horizon",
        )

    crossover = canopy_crossover(forest, horizon_years=canopy_horizon)

    if crossover["crossover_band"]:
        st.warning(crossover["note"])
    else:
        st.success(crossover["note"])

    canopy_fig = go.Figure()
    canopy_fig.add_trace(
        go.Bar(
            name="Albedo penalty (warming)",
            x=[row["label"] for row in crossover["bands"]],
            y=[row["albedo_co2_kg"] / 1000 for row in crossover["bands"]],
            marker_color="#c1666b",
        )
    )
    canopy_fig.add_trace(
        go.Bar(
            name="Sequestration (cooling)",
            x=[row["label"] for row in crossover["bands"]],
            y=[row["sequestration_co2_kg"] / 1000 for row in crossover["bands"]],
            marker_color="#4f772d",
        )
    )
    canopy_fig.add_trace(
        go.Scatter(
            name="Net",
            x=[row["label"] for row in crossover["bands"]],
            y=[row["net_co2_kg"] / 1000 for row in crossover["bands"]],
            mode="lines+markers",
            line=dict(color="#1d3557", width=3),
            marker=dict(size=10),
        )
    )
    canopy_fig.update_layout(
        height=420,
        barmode="relative",
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="tonnes CO2 per hectare (negative is cooling)",
        xaxis_tickangle=-30,
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(canopy_fig, use_container_width=True)

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Band": row["label"],
                    "Snow cover": f"{row['snow_fraction']:.0%}",
                    "Albedo penalty (t)": round(row["albedo_co2_kg"] / 1000, 1),
                    "Sequestration (t)": round(
                        row["sequestration_co2_kg"] / 1000, 1
                    ),
                    "Net (t)": round(row["net_co2_kg"] / 1000, 1),
                    "Verdict": "Net cooling" if row["beneficial"]
                               else "Net warming",
                }
                for row in crossover["bands"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### One band in detail")
    detail_band = st.selectbox(
        "Band",
        list_latitude_bands(),
        index=list_latitude_bands().index("boreal"),
        format_func=lambda k: LATITUDE_BANDS[k]["label"],
        key="af_canopy_band",
    )
    detail = canopy_albedo_penalty(
        forest, 10000, detail_band, horizon_years=canopy_horizon
    )
    d1, d2, d3 = st.columns(3)
    d1.metric("Open ground albedo", f"{detail['open_annual_albedo']:.3f}")
    d2.metric("Under canopy", f"{detail['forest_annual_albedo']:.3f}")
    d3.metric(
        "Net, per hectare",
        f"{detail['net_co2_kg'] / 1000:+,.1f} t",
        delta="cooling" if detail["planting_is_net_beneficial"] else "warming",
        delta_color="normal" if detail["planting_is_net_beneficial"]
                    else "inverse",
    )
    st.caption(detail["note"])
    st.caption(
        f"Growth saturates: after {detail['growth_years']:.0f} years this stand "
        f"holds {detail['growth']['accumulated_t_co2_ha']:,.0f} tCO2/ha, "
        f"{detail['growth']['share_of_asymptote']:.0%} of what it can ever hold. "
        f"A flat early-growth rate applied for a century would claim far more "
        f"and bury this comparison."
    )


# ---------------------------------------------------------------------------
# Solar panels
# ---------------------------------------------------------------------------
with tab_solar:
    st.markdown("### The albedo cost of a solar array")
    st.caption(
        "A panel is dark by design. The warming term is small against the "
        "generation benefit and it is not zero, and it is normally left out "
        "of the sum entirely."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        pv_area = st.number_input(
            "Array area (m²)", min_value=1.0, value=30.0, step=5.0, key="af_pv_area"
        )
    with c2:
        pv_yield = st.number_input(
            "Yield (kWh/m²/yr)", min_value=1.0, value=150.0, step=10.0,
            key="af_pv_yield",
        )
    with c3:
        grid = st.number_input(
            "Grid intensity (kg CO2/kWh)", min_value=0.0, value=0.25,
            step=0.05, key="af_pv_grid",
        )

    c4, c5 = st.columns(2)
    with c4:
        pv_band = st.selectbox(
            "Latitude band",
            list_latitude_bands(),
            index=list_latitude_bands().index("temperate"),
            format_func=lambda k: LATITUDE_BANDS[k]["label"],
            key="af_pv_band",
        )
    with c5:
        covered = st.selectbox(
            "What the panels cover",
            list_surfaces("roof"),
            index=list_surfaces("roof").index("grey_roof"),
            format_func=lambda k: SURFACES[k]["label"],
            key="af_pv_covered",
        )

    pv = solar_panel_net(
        pv_area, pv_band, pv_yield, grid, replaced_surface=covered
    )

    p1, p2, p3 = st.columns(3)
    p1.metric("Displaced generation", f"{pv['displaced_co2_kg'] / 1000:,.1f} t")
    p2.metric("Albedo penalty", f"{pv['albedo_co2_kg'] / 1000:+,.2f} t")
    p3.metric("Net", f"{pv['net_co2_kg'] / 1000:,.1f} t")

    pv_fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["relative", "relative", "total"],
            x=["Displaced generation", "Albedo penalty", "Net"],
            y=[
                pv["displaced_co2_kg"] / 1000,
                pv["albedo_co2_kg"] / 1000,
                0,
            ],
            decreasing=dict(marker=dict(color="#4f772d")),
            increasing=dict(marker=dict(color="#c1666b")),
            totals=dict(marker=dict(color="#1d3557")),
        )
    )
    pv_fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title="tonnes CO2 (negative is avoided)",
    )
    st.plotly_chart(pv_fig, use_container_width=True)
    st.caption(pv["note"])
    st.caption(
        "Covering a white roof rather than a dark one costs more, because more "
        "reflectance is being given up. Worth checking before painting a roof "
        "white and then putting panels on it."
    )


# ---------------------------------------------------------------------------
# Cost per tonne
# ---------------------------------------------------------------------------
with tab_cost:
    st.markdown("### Priced against everything else")
    st.caption(
        "The reason for converting reflectance into tonnes at all: once it is "
        "in tonnes it can sit on the same abatement curve as a heat pump."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        coat_cost = st.number_input(
            "Coating cost (£/m²)", min_value=0.0, value=12.0, step=1.0,
            key="af_cost_m2",
        )
    with c2:
        upkeep = st.number_input(
            "Annual upkeep (£/m²/yr)", min_value=0.0, value=0.0, step=0.1,
            key="af_cost_upkeep",
        )
    with c3:
        recoat_years = st.number_input(
            "Recoat every (years, 0 for never)", min_value=0, value=15, step=1,
            key="af_cost_recoat",
        )

    cost = abatement_cost(
        result,
        cost_per_m2=coat_cost,
        maintenance_cost_per_m2_yr=upkeep,
        recoat_interval_years=recoat_years or None,
    )

    if cost["is_abatement"]:
        k1, k2, k3 = st.columns(3)
        k1.metric("Total cost", f"£{cost['total_cost']:,.0f}")
        k2.metric("Tonnes abated", f"{cost['tonnes_abated']:,.2f} t")
        k3.metric("Cost per tonne", f"£{cost['cost_per_tonne']:,.0f}/t")
        st.caption(
            f"Includes {cost['recoats']} recoat(s) over the "
            f"{result['horizon_years']:.0f}-year horizon. {cost['note']}"
        )
    else:
        st.warning(cost["note"])

    st.markdown("#### Cost per tonne, by latitude")
    cost_rows = []
    for band_key in list_latitude_bands():
        band_result = surface_change(
            from_surface, to_surface, area, band_key,
            horizon_years=horizon, apply_soiling=apply_soiling,
        )
        band_cost = abatement_cost(
            band_result,
            cost_per_m2=coat_cost,
            maintenance_cost_per_m2_yr=upkeep,
            recoat_interval_years=recoat_years or None,
        )
        cost_rows.append({
            "Band": get_latitude_band(band_key)["label"],
            "Tonnes abated": round(band_cost["tonnes_abated"], 2),
            "£/tonne": (
                round(band_cost["cost_per_tonne"])
                if band_cost["cost_per_tonne"] else None
            ),
        })
    st.dataframe(pd.DataFrame(cost_rows), hide_index=True,
                 use_container_width=True)
    st.caption(
        "The same tin of paint, the same price, and a cost per tonne that "
        "varies by a factor of three with nothing but where the roof is."
    )


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
                f"{record['name']} — "
                f"{record['co2_equivalent_kg'] / 1000:+,.2f} t CO2e "
                f"over {record['horizon_years']:.0f} years"
            ):
                payload = record["payload"]
                st.write(
                    f"**{payload.get('from_surface')}** → "
                    f"**{payload.get('to_surface')}**, "
                    f"{record['area_m2']:,.0f} m², "
                    f"{payload.get('latitude_band')}"
                )
                st.write(
                    f"Albedo change {payload.get('delta_albedo', 0):+.3f}, "
                    f"surface forcing "
                    f"{payload.get('local_forcing_w_m2', 0):+.1f} W/m², "
                    f"local temperature "
                    f"{payload.get('local_temp_delta_c', 0):+.1f} °C"
                )
                st.caption(f"Saved {record['created_at']}")
                if st.button("Delete", key=f"af_del_{record['id']}"):
                    if delete_assessment(user_id, record["id"]):
                        st.success("Deleted.")
                        st.rerun()
