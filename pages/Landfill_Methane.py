"""Landfill methane by first order decay.

Buried waste does not emit on a schedule the calendar year understands. This
page shows when the methane actually arrives, how much of it the site catches,
and what diverting the bin really buys — which is not what a flat factor says.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.environment.landfill_methane import (
    CLIMATE_ZONES,
    DEFAULT_GRID_INTENSITY,
    DEFAULT_HEAT_INTENSITY,
    METHANE_GWP_100,
    SITE_ARCHETYPES,
    TREATMENT_ROUTES,
    WASTE_STREAMS,
    LandfillError,
    compare_routes,
    compare_to_flat_factor,
    decay_constant,
    delete_profile,
    diversion_scenario,
    get_landfill_insights,
    get_profiles,
    get_site,
    get_stream,
    half_life_years,
    landfill_series,
    list_climate_zones,
    list_sites,
    list_streams,
    methane_potential,
    save_profile,
    sensitivity,
    sequestered_carbon,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🗑️ Landfill Methane</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Buried organic waste decays exponentially, over years to decades. Food "
    "waste in a wet climate is largely gone within five years; timber is still "
    "emitting at thirty. A model that books the whole emission in the year the "
    "bin went out puts methane in a year it was not emitted in, and takes it "
    "out of the twenty years it was."
)

with st.expander("Why the timing is the thing that matters"):
    st.markdown(
        """
For a **stable** waste stream the annual totals come out similar either way,
which is exactly why this error survives unnoticed.

It bites the moment behaviour changes. Start composting today and a flat model
reports the full benefit today. In reality the site is still working through
everything buried before then, so the benefit arrives over decades. Promising
an instant benefit for something whose benefit is slow is the reason nobody
believes the second year's advice.

**The model.** Carbon deposited decays at a rate `k` set by what the waste is
and how wet the site is. What decomposes in a year is what was left at the start
of it, times `1 − e^−k`. Methane generated is that carbon times the methane
fraction of landfill gas, times 16/12.

**Then the site gets its say.** Gas capture takes its share first; whatever
escapes is partly oxidised crossing the cover soil. Applying oxidation to the
gross rather than to the escaping portion would count the captured gas twice.

**Not all carbon is available.** Lignin-bound carbon in timber and woody garden
waste never decomposes, on any timescale. That is a real carbon store, not a
delayed emission, and a model that only counts what comes out cannot see it.
"""
    )

tab_profile, tab_routes, tab_divert, tab_saved = st.tabs(
    ["Your waste", "Where should it go?", "If I change now", "Saved profiles"]
)


with tab_profile:
    st.subheader("What goes in the bin")

    settings = st.columns(3)
    with settings[0]:
        climate = st.selectbox(
            "Climate", options=list_climate_zones(),
            index=list_climate_zones().index("wet_temperate"),
            format_func=lambda key: CLIMATE_ZONES[key]["label"],
        )
    with settings[1]:
        site = st.selectbox(
            "Where does it go?", options=list_sites(),
            format_func=lambda key: SITE_ARCHETYPES[key]["label"],
        )
    with settings[2]:
        horizon = st.select_slider(
            "Horizon", options=[20, 50, 100, 150], value=100,
            format_func=lambda years: f"{years} years",
        )

    st.caption(get_site(site)["note"])

    st.markdown("**Tonnes a year, by stream**")
    mix: dict[str, float] = {}
    columns = st.columns(2)
    defaults = {"food": 0.15, "garden": 0.10, "paper": 0.08, "cardboard": 0.05}
    for n, stream in enumerate(list_streams()):
        entry = WASTE_STREAMS[stream]
        with columns[n % 2]:
            mix[stream] = st.number_input(
                entry["label"], min_value=0.0,
                value=defaults.get(stream, 0.0), step=0.01, format="%.3f",
                key=f"waste_{stream}", help=entry["note"],
            )

    active = {stream: tonnes for stream, tonnes in mix.items() if tonnes > 0}
    if not active:
        st.info("Enter some tonnage above.")
    else:
        try:
            series = landfill_series(
                {1: dict(active)}, climate=climate, site=site, years=horizon
            )
        except LandfillError as exc:
            st.error(str(exc))
            st.stop()

        total_emitted = series[-1]["cumulative_emitted_kg"]
        total_generated = sum(row["generated_kg"] for row in series)
        total_captured = sum(row["captured_kg"] for row in series)
        stored = sum(
            sequestered_carbon(stream) * tonnes for stream, tonnes in active.items()
        )

        a, b, c, d = st.columns(4)
        a.metric("Methane generated", f"{total_generated:,.0f} kg")
        b.metric("Captured at the site", f"{total_captured:,.0f} kg")
        c.metric("Reaching the air", f"{total_emitted:,.0f} kg")
        d.metric("As CO2e", f"{total_emitted * METHANE_GWP_100:,.0f} kg")
        st.caption(
            f"From a single year's disposal, followed for {horizon} years. "
            f"A further {stored:,.0f} kg of carbon never decomposes at all."
        )

        frame = pd.DataFrame(series)
        curve = go.Figure()
        curve.add_trace(go.Scatter(
            x=frame["year"], y=frame["emitted_kg"], name="Reaching the air",
            mode="lines", fill="tozeroy", line=dict(color="#b45309", width=2),
        ))
        curve.add_trace(go.Scatter(
            x=frame["year"], y=frame["generated_kg"], name="Generated",
            mode="lines", line=dict(color="#334155", width=2, dash="dot"),
        ))
        curve.update_layout(
            height=440, xaxis_title="Years after disposal",
            yaxis_title="kg of methane", legend=dict(orientation="h", y=1.1),
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(curve, use_container_width=True)
        st.caption(
            "The gap between the two lines is what the site catches and what "
            "the cover soil oxidises. It is the largest single lever here, and "
            "it is a property of the site rather than of the src.environment.waste."
        )

        st.markdown("#### Against the flat constant")
        focus = st.selectbox(
            "Which stream?", options=list(active),
            format_func=lambda key: WASTE_STREAMS[key]["label"],
        )
        comparison = compare_to_flat_factor(
            focus, active[focus], climate=climate, site=site, years=horizon
        )
        for line in get_landfill_insights(comparison):
            st.markdown(f"- {line}")

        st.markdown("#### Streams do not decay alike")
        stream_rows = pd.DataFrame([
            {
                "Stream": WASTE_STREAMS[stream]["label"],
                "Carbon (kg/t)": round(get_stream(stream)["doc"] * 1000, 0),
                "Available": get_stream(stream)["docf"],
                "k": decay_constant(stream, climate),
                "Half-life (yr)": round(half_life_years(stream, climate), 1),
                "Methane potential (kg/t)": round(methane_potential(stream, site), 1),
                "Stored forever (kgC/t)": round(sequestered_carbon(stream), 0),
            }
            for stream in list_streams()
        ])
        st.dataframe(stream_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Timber has the most carbon per tonne and the least of it "
            "available — most of its carbon is lignin-bound and stays buried. "
            "One coefficient across this table cannot represent any of it."
        )

        st.markdown("#### What moves the answer")
        sensitivity_frame = pd.DataFrame(sensitivity(focus, active[focus]))
        sensitivity_chart = px.bar(
            sensitivity_frame, x="total_kg", y="setting", color="parameter",
            orientation="h",
            labels={"total_kg": "kg of methane reaching the air", "setting": ""},
        )
        sensitivity_chart.update_layout(
            height=620, margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", y=1.06),
        )
        st.plotly_chart(sensitivity_chart, use_container_width=True)

        with st.form("save_waste_profile"):
            name = st.text_input("Name this profile", value="Our bin")
            if st.form_submit_button("Save profile"):
                payload = {"total_emitted_kg": total_emitted, "rows": series}
                if not name.strip():
                    st.error("Give the profile a name.")
                elif save_profile(
                    user_id, name.strip(), active, payload, climate, site
                ):
                    st.success("Saved.")
                else:
                    st.error("Could not save the profile.")


with tab_routes:
    st.subheader("Landfill, compost, digestion or incineration")
    st.markdown(
        "Routes with an output — biogas, heat, compost — displace something "
        "else, and that credit is real. It is also a claim about a system "
        "outside the waste system, so it is reported **separately** here and "
        "never folded into the emission figure."
    )

    route_columns = st.columns(3)
    with route_columns[0]:
        route_stream = st.selectbox(
            "Stream", options=list_streams(),
            format_func=lambda key: WASTE_STREAMS[key]["label"],
            key="route_stream",
        )
    with route_columns[1]:
        route_tonnes = st.number_input(
            "Tonnes", min_value=0.01, value=1.0, step=0.1
        )
    with route_columns[2]:
        route_site = st.selectbox(
            "Landfill type", options=list_sites(),
            format_func=lambda key: SITE_ARCHETYPES[key]["label"],
            key="route_site",
        )

    credit_columns = st.columns(2)
    with credit_columns[0]:
        grid_intensity = st.slider(
            "Electricity displaced (kg CO2e/kWh)",
            min_value=0.0, max_value=0.9, value=DEFAULT_GRID_INTENSITY, step=0.02,
        )
    with credit_columns[1]:
        heat_intensity = st.slider(
            "Heat displaced (kg CO2e/kWh)",
            min_value=0.0, max_value=0.4, value=DEFAULT_HEAT_INTENSITY, step=0.02,
        )

    rows = compare_routes(
        route_stream, route_tonnes, site=route_site,
        grid_intensity=grid_intensity, heat_intensity=heat_intensity,
    )
    route_frame = pd.DataFrame(rows)

    stacked = go.Figure()
    stacked.add_trace(go.Bar(
        x=route_frame["label"], y=route_frame["gross_co2e"],
        name="Emitted", marker_color="#b45309",
    ))
    stacked.add_trace(go.Bar(
        x=route_frame["label"], y=-route_frame["avoided_co2e"],
        name="Avoided elsewhere", marker_color="#0f766e",
    ))
    stacked.add_trace(go.Scatter(
        x=route_frame["label"], y=route_frame["net_co2e"],
        name="Net", mode="markers",
        marker=dict(size=14, color="#1e293b", symbol="diamond"),
    ))
    stacked.add_hline(y=0, line_dash="dot")
    stacked.update_layout(
        barmode="relative", height=460, yaxis_title="kg CO2e",
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(stacked, use_container_width=True)
    st.caption(
        "The bars above and below the line are separate quantities, not one "
        "number. Move the sliders and only the credit moves — the emissions "
        "are unchanged, which is exactly the separation that netting them "
        "into a single figure would destroy."
    )

    st.dataframe(
        route_frame[[
            "label", "methane_co2e", "process_co2e", "gross_co2e",
            "avoided_co2e", "net_co2e"
        ]].rename(columns={
            "label": "Route", "methane_co2e": "Methane",
            "process_co2e": "Running the process", "gross_co2e": "Gross",
            "avoided_co2e": "Credit", "net_co2e": "Net",
        }),
        use_container_width=True, hide_index=True,
    )

    for row in rows:
        st.markdown(f"- **{row['label']}** — {row['note']}")


with tab_divert:
    st.subheader("If I stop landfilling this, when does it help?")
    st.markdown(
        "This is the question the flat constant answers wrongly, and it "
        "answers it wrongly in the flattering direction."
    )

    divert_columns = st.columns(3)
    with divert_columns[0]:
        change_year = st.slider("Change in year", 1, 20, 5)
    with divert_columns[1]:
        diverted_share = st.slider(
            "Divert this much", 0.0, 1.0, 1.0, 0.05, format="%.0f%%"
        )
    with divert_columns[2]:
        divert_climate = st.selectbox(
            "Climate", options=list_climate_zones(),
            index=list_climate_zones().index("wet_temperate"),
            format_func=lambda key: CLIMATE_ZONES[key]["label"],
            key="divert_climate",
        )

    divert_mix = st.session_state.get("divert_mix") or {
        "food": 0.15, "garden": 0.10, "paper": 0.08, "cardboard": 0.05
    }
    scenario = diversion_scenario(
        divert_mix, change_year=change_year, diverted_share=diverted_share,
        climate=divert_climate, years=80,
    )

    a, b, c = st.columns(3)
    a.metric(
        "Saved in the first year",
        f"{scenario['first_year_saving_kg']:,.1f} kg",
    )
    b.metric(
        "Saved once it settles",
        f"{scenario['steady_saving_kg']:,.1f} kg/yr",
    )
    c.metric(
        "Years to 90% of the effect",
        scenario["years_to_ninety_percent_effect"] or "—",
    )

    st.warning(
        f"A flat model would report **{scenario['instant_model_claim_kg']:,.1f} "
        f"kg** saved in the year you change. The real first-year saving is "
        f"**{scenario['first_year_saving_kg']:,.1f} kg**, because the site is "
        "still working through everything buried before then. The full effect "
        "takes decades to arrive — and it does arrive."
    )

    scenario_frame = pd.DataFrame(scenario["rows"])
    divergence = go.Figure()
    divergence.add_trace(go.Scatter(
        x=scenario_frame["year"], y=scenario_frame["baseline_kg"],
        name="Carry on as now", mode="lines",
        line=dict(color="#94a3b8", width=3),
    ))
    divergence.add_trace(go.Scatter(
        x=scenario_frame["year"], y=scenario_frame["changed_kg"],
        name="After diverting", mode="lines",
        line=dict(color="#0f766e", width=3),
    ))
    divergence.add_vline(
        x=change_year, line_dash="dash", annotation_text="you change here"
    )
    divergence.update_layout(
        height=460, xaxis_title="Year",
        yaxis_title="kg of methane reaching the air",
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(divergence, use_container_width=True)
    st.caption(
        "The two lines separate slowly, not at the dashed line. That gap is "
        "the tail of waste already buried, and it is the honest answer to what "
        "changing your bin today does."
    )

    st.metric(
        "Total methane avoided over 80 years",
        f"{scenario['total_saved_kg']:,.0f} kg "
        f"({scenario['total_saved_co2e']:,.0f} kg CO2e)",
    )


with tab_saved:
    st.subheader("Saved profiles")
    saved = get_profiles(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for profile in saved:
            with st.expander(
                f"{profile['name']} — {profile['methane_kg']:,.0f} kg methane "
                f"({SITE_ARCHETYPES.get(profile['site'], {}).get('label', profile['site'])})"
            ):
                a, b, c = st.columns(3)
                a.metric("Tonnes", f"{profile['total_tonnes']:.2f}")
                b.metric("Methane", f"{profile['methane_kg']:,.0f} kg")
                c.metric("As CO2e", f"{profile['methane_co2e']:,.0f} kg")
                st.caption(
                    f"{CLIMATE_ZONES.get(profile['climate'], {}).get('label', profile['climate'])}"
                )
                detail = profile.get("detail") or {}
                if detail.get("mix"):
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "Stream": WASTE_STREAMS[stream]["label"],
                                "Tonnes": tonnes,
                            }
                            for stream, tonnes in detail["mix"].items()
                        ]),
                        use_container_width=True, hide_index=True,
                    )
                if st.button("Delete", key=f"delete_waste_{profile['id']}"):
                    if delete_profile(profile["id"], user_id):
                        st.success("Deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete it.")
