"""Where plastic actually goes, rather than which bin it went into.

The rest of the app stops at the bin lid. This page routes material through
sorting, reprocessing and disposal, models the leakage pathways that have
nothing to do with bins, and reports plastic and carbon together so that
substitutions read as trades rather than as improvements.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.environment.plastic_leakage import (
    POLYMERS,
    REGIONS,
    SUBSTITUTIONS,
    PlasticError,
    carbon_break_even,
    delete_profile,
    fate,
    get_plastic_insights,
    get_polymer,
    get_profiles,
    household_leakage,
    list_polymers,
    persistence_profile,
    rank_interventions,
    real_recycling_rate,
    save_profile,
    substitution,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>♻️ Plastic Footprint & Leakage</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Everything else in this app treats a correctly sorted item as a solved "
    "problem. The entire issue lives in the gap between *put in the recycling "
    "bin* and *recycled*."
)

with st.expander("What this models, and what it refuses to tell you"):
    st.markdown(
        """
**Collection is not recycling.** A collected item passes a sorting facility, a
reprocessor and a market, and can be rejected at any of them. This page reports a
fate split — recycled, incinerated, landfilled, leaked — rather than a yes or no
on recyclability.

**Leakage happens to uncollected waste, not to badly sorted src.environment.waste.** Sorting
better changes whether material is recycled or burned. It does not change how
much escapes. That is worth doing and it is not a leakage intervention, and the
intervention ranking lists it with a zero rather than quietly omitting it.

**Most leaked plastic never reaches the sea.** Tyre particles and laundry fibres
mostly end up in soil — fibres via sewage sludge spread on farmland. Modelling
every pathway as an ocean pathway sends effort to the wrong place.

**Mass alone is the wrong ranking.** A gram of expanded polystyrene and a gram of
uncoated paper are not equivalent litter, so leaked mass is reported alongside an
environmental residence time.

**Carbon is always shown next to plastic.** A cotton tote removes the plastic and
adds the carbon. Roughly fifty uses to break even. A page that counted only
plastic would recommend it without mentioning that.
        """
    )

st.markdown("---")

tab_household, tab_fate, tab_swap, tab_saved = st.tabs(
    [
        "🏠 Household",
        "🔬 One polymer",
        "🔁 Substitutions",
        "💾 Saved profiles",
    ]
)


# ---------------------------------------------------------------------------
# Household
# ---------------------------------------------------------------------------
with tab_household:
    st.markdown("### A year of plastic, bins and everything else")

    region = st.selectbox(
        "Waste infrastructure where you live",
        sorted(REGIONS),
        format_func=lambda k: REGIONS[k]["label"],
        key="plastic_region",
    )
    st.caption(REGIONS[region]["note"])

    st.markdown("#### Packaging (kg per year)")
    packaging = {}
    columns = st.columns(3)
    packaging_polymers = [
        "pet", "hdpe", "ldpe_film", "pp", "ps", "eps", "multilayer", "pla",
    ]
    defaults = {
        "pet": 6.0, "hdpe": 4.0, "ldpe_film": 5.0, "pp": 4.0,
        "ps": 1.5, "eps": 0.8, "multilayer": 3.0, "pla": 0.5,
    }
    for index, polymer in enumerate(packaging_polymers):
        with columns[index % 3]:
            packaging[polymer] = st.number_input(
                get_polymer(polymer)["label"],
                min_value=0.0,
                value=defaults[polymer],
                step=0.5,
                key=f"plastic_pack_{polymer}",
            )

    sorting_accuracy = st.slider(
        "Share of recyclable packaging you put in the right bin",
        min_value=0.0, max_value=1.0, value=0.85, step=0.05,
        key="plastic_sorting",
    )

    st.markdown("#### Everything that is not a bin")
    p1, p2 = st.columns(2)
    with p1:
        vehicle_km = st.number_input(
            "Car kilometres per year", min_value=0.0, value=12000.0, step=500.0,
            key="plastic_vkm",
        )
        laundry_kg = st.number_input(
            "Synthetic laundry washed (kg per year)",
            min_value=0.0, value=90.0, step=10.0, key="plastic_laundry",
        )
    with p2:
        rinse_off_kg = st.number_input(
            "Rinse-off personal care products (kg per year)",
            min_value=0.0, value=2.0, step=0.5, key="plastic_care",
        )
        garden_film_kg = st.number_input(
            "Garden or allotment mulch film (kg per year)",
            min_value=0.0, value=0.0, step=0.5, key="plastic_film",
        )

    pathways = {
        key: value
        for key, value in (
            ("tyre_wear", vehicle_km),
            ("textile_laundry", laundry_kg),
            ("personal_care", rinse_off_kg),
            ("agricultural_film", garden_film_kg),
        )
        if value > 0
    }

    try:
        result = household_leakage(
            {k: v for k, v in packaging.items() if v > 0},
            pathways,
            region=region,
            sorting_accuracy=sorting_accuracy,
        )
    except PlasticError as error:
        st.error(str(error))
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total leakage", f"{result['total_leakage_kg'] * 1000:,.0f} g/yr")
    m2.metric("From bins", f"{result['bin_leakage_kg'] * 1000:,.0f} g/yr")
    m3.metric(
        "From everything else",
        f"{result['pathway_leakage_kg'] * 1000:,.0f} g/yr",
    )
    m4.metric(
        "Packaging actually recycled",
        f"{result['packaging_recycled_share'] * 100:.0f}%",
    )

    st.markdown("#### Where it goes")
    compartment_fig = go.Figure(
        go.Bar(
            x=[v * 1000 for v in result["compartments"].values()],
            y=[k.title() for k in result["compartments"]],
            orientation="h",
            marker_color=["#8a6f4a", "#3d5a80", "#2f6f8f", "#9aa5a0"],
            text=[f"{v * 1000:,.0f} g" for v in result["compartments"].values()],
            textposition="auto",
        )
    )
    compartment_fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="grams per year",
    )
    st.plotly_chart(compartment_fig, use_container_width=True)

    if result["pathways"]:
        st.markdown("#### Leakage by pathway")
        pathway_fig = go.Figure(
            go.Bar(
                x=[row["kg_released"] * 1000 for row in result["pathways"]],
                y=[row["label"] for row in result["pathways"]],
                orientation="h",
                marker_color="#e07a5f",
                text=[
                    f"{row['kg_released'] * 1000:,.0f} g"
                    for row in result["pathways"]
                ],
                textposition="auto",
            )
        )
        pathway_fig.update_layout(
            height=300,
            margin=dict(l=10, r=10, t=20, b=10),
            xaxis_title="grams per year",
        )
        st.plotly_chart(pathway_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Pathway": row["label"],
                        "Activity": f"{row['activity']:,.0f} {row['unit']}",
                        "Released (g/yr)": round(row["kg_released"] * 1000, 1),
                        "Why": row["note"],
                    }
                    for row in result["pathways"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### What this is telling you")
    for insight in get_plastic_insights(result):
        st.markdown(f"- {insight}")

    st.markdown("#### What would actually help, by effect size")
    st.caption(
        "Ranked by modelled leakage avoided rather than by how virtuous each "
        "one feels."
    )
    ranked = rank_interventions(result)
    if ranked:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Intervention": row["intervention"],
                        "Avoided (g/yr)": round(row["avoided_kg"] * 1000, 1),
                        "Why": row["note"],
                    }
                    for row in ranked
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Packaging fates")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Polymer": row["label"],
                    "kg/yr": round(row["kg"], 2),
                    "Recycled": round(row["recycled"], 2),
                    "Incinerated": round(row["incinerated"], 2),
                    "Landfilled": round(row["landfilled"], 2),
                    "Leaked (g)": round(row["leaked"] * 1000, 1),
                    "Real rate": f"{row['real_recycling_rate'] * 100:.1f}%",
                }
                for row in result["packaging"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    with st.form("save_plastic_profile"):
        name = st.text_input("Save this profile as", value="")
        if st.form_submit_button("Save profile") and name.strip():
            try:
                save_profile(user_id, name, result)
                st.success(f"Saved '{name.strip()}'.")
            except PlasticError as error:
                st.error(str(error))


# ---------------------------------------------------------------------------
# One polymer
# ---------------------------------------------------------------------------
with tab_fate:
    st.markdown("### One polymer, followed all the way through")

    f1, f2, f3 = st.columns(3)
    with f1:
        polymer = st.selectbox(
            "Polymer",
            list_polymers(),
            format_func=lambda k: POLYMERS[k]["label"],
            key="fate_polymer",
        )
    with f2:
        mass = st.number_input(
            "Mass (kg)", min_value=0.1, value=10.0, step=1.0, key="fate_mass"
        )
    with f3:
        fate_region = st.selectbox(
            "Region",
            sorted(REGIONS),
            format_func=lambda k: REGIONS[k]["label"],
            key="fate_region",
        )

    sorted_correctly = st.checkbox(
        "Put in the correct bin", value=True, key="fate_sorted"
    )

    single = fate(polymer, mass, fate_region, sorted_correctly)
    st.caption(single["note"])

    if single["pla_warning"]:
        st.warning(single["pla_warning"])

    labels = {
        "recycled": "Mechanically recycled",
        "incinerated": "Incinerated with energy recovery",
        "landfilled": "Landfilled",
        "informally_disposed": "Informally disposed of",
        "leaked": "Leaked to the environment",
    }
    colors = ["#5f8f36", "#e0a35f", "#9aa5a0", "#8a6f4a", "#e07a5f"]

    fate_fig = go.Figure(
        go.Pie(
            labels=list(labels.values()),
            values=[single[key] for key in labels],
            hole=0.45,
            marker=dict(colors=colors),
        )
    )
    fate_fig.update_layout(
        height=380, margin=dict(l=10, r=10, t=20, b=10)
    )
    st.plotly_chart(fate_fig, use_container_width=True)

    r1, r2 = st.columns(2)
    r1.metric(
        "Nominal sorting yield",
        f"{single['nominal_recyclability'] * 100:.0f}%",
        help="What survives the sorting facility.",
    )
    r2.metric(
        "Actually becomes secondary material",
        f"{single['real_recycling_rate'] * 100:.1f}%",
        help="Sorting yield times reprocessing yield times collection. This is "
             "the number the symbol on the pack does not tell you.",
    )

    st.markdown("#### Real recycling rate across every polymer")
    rate_rows = [
        {
            "Polymer": POLYMERS[key]["label"],
            "Sorting yield": f"{POLYMERS[key]['sorting_yield'] * 100:.0f}%",
            "Reprocessing yield": (
                f"{POLYMERS[key]['reprocessing_yield'] * 100:.0f}%"
            ),
            "Real rate": f"{real_recycling_rate(key) * 100:.1f}%",
        }
        for key in list_polymers()
    ]
    st.dataframe(pd.DataFrame(rate_rows), hide_index=True, use_container_width=True)

    st.markdown("#### If it leaks, how long is it there?")
    st.caption(
        "Mass alone files a gram of foam and a gram of paper as equivalent "
        "litter. This is the correction."
    )
    p1, p2 = st.columns(2)
    with p1:
        compartment = st.radio(
            "Compartment",
            ["soil", "marine"],
            horizontal=True,
            key="persist_compartment",
            help="Freshwater is deliberately unavailable: residence there is "
                 "dominated by transport out of the compartment rather than by "
                 "degradation, so a decay curve would be the wrong model.",
        )
    with p2:
        horizon = st.slider(
            "Horizon (years)", min_value=20, max_value=500, value=200, step=20,
            key="persist_horizon",
        )

    profile = persistence_profile(polymer, single["leaked"] or 1.0,
                                  compartment, horizon)
    persist_fig = go.Figure(
        go.Scatter(
            x=profile["years"],
            y=[value * 1000 for value in profile["remaining_kg"]],
            mode="lines",
            line=dict(color="#e07a5f", width=3),
            fill="tozeroy",
        )
    )
    persist_fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="Years after release",
        yaxis_title="grams still present",
    )
    st.plotly_chart(persist_fig, use_container_width=True)
    st.metric(
        f"Still present after {horizon} years",
        f"{profile['share_remaining_at_horizon'] * 100:.0f}%",
    )
    st.caption(profile["caveat"])


# ---------------------------------------------------------------------------
# Substitutions
# ---------------------------------------------------------------------------
with tab_swap:
    st.markdown("### Swapping one for another is a trade")
    st.caption(
        "Both numbers are always on screen. A comparison that reported only "
        "the plastic would recommend a cotton tote without mentioning that it "
        "takes about fifty uses to repay the carbon of the bag it replaced."
    )

    s1, s2, s3 = st.columns(3)
    with s1:
        option_a = st.selectbox(
            "Currently using",
            sorted(SUBSTITUTIONS),
            index=sorted(SUBSTITUTIONS).index("ldpe_bag"),
            format_func=lambda k: SUBSTITUTIONS[k]["label"],
            key="swap_a",
        )
    with s2:
        option_b = st.selectbox(
            "Considering",
            sorted(SUBSTITUTIONS),
            index=sorted(SUBSTITUTIONS).index("cotton_tote"),
            format_func=lambda k: SUBSTITUTIONS[k]["label"],
            key="swap_b",
        )
    with s3:
        uses = st.number_input(
            "Number of uses", min_value=1, value=52, step=1, key="swap_uses"
        )

    if option_a == option_b:
        st.info("Pick two different options to compare.")
    else:
        try:
            comparison = substitution(option_a, option_b, int(uses))
        except PlasticError as error:
            st.error(str(error))
            st.stop()

        rows = comparison["options"]
        swap_fig = go.Figure()
        swap_fig.add_trace(
            go.Bar(
                name="Plastic (g)",
                x=[row["label"] for row in rows],
                y=[row["plastic_kg"] * 1000 for row in rows],
                marker_color="#3d5a80",
                yaxis="y",
            )
        )
        swap_fig.add_trace(
            go.Bar(
                name="Carbon (kg CO₂e)",
                x=[row["label"] for row in rows],
                y=[row["carbon_kg_co2e"] for row in rows],
                marker_color="#e07a5f",
                yaxis="y2",
            )
        )
        swap_fig.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis=dict(title="grams of plastic"),
            yaxis2=dict(title="kg CO₂e", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(swap_fig, use_container_width=True)

        if comparison["is_a_trade"]:
            st.warning(comparison["verdict"])
        else:
            st.info(comparison["verdict"])

        break_even = comparison["carbon_break_even_uses"]
        if break_even is None:
            st.caption(
                f"{SUBSTITUTIONS[option_b]['label']} does not catch up with "
                f"{SUBSTITUTIONS[option_a]['label']} on carbon within a "
                f"thousand uses, or it was already ahead from the first."
            )
        else:
            st.metric(
                "Uses to break even on carbon", f"{break_even}",
                help="Below this many uses, the swap costs more carbon than it "
                     "saves. Whole units are counted, so buying a replacement "
                     "resets part of the ladder.",
            )

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Option": row["label"],
                        "Units needed": row["units_needed"],
                        "Uses per unit": row["reuses"],
                        "Plastic (g)": round(row["plastic_kg"] * 1000, 1),
                        "Carbon (kg CO₂e)": round(row["carbon_kg_co2e"], 2),
                        "Note": row["note"],
                    }
                    for row in rows
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("#### Break-even against the option it replaces")
    baseline = st.selectbox(
        "Baseline",
        sorted(SUBSTITUTIONS),
        index=sorted(SUBSTITUTIONS).index("ldpe_bag"),
        format_func=lambda k: SUBSTITUTIONS[k]["label"],
        key="break_even_baseline",
    )
    break_even_rows = []
    for key in sorted(SUBSTITUTIONS):
        if key == baseline:
            continue
        value = carbon_break_even(baseline, key)
        break_even_rows.append({
            "Option": SUBSTITUTIONS[key]["label"],
            "Uses to break even on carbon": (
                value if value is not None else "never / already ahead"
            ),
        })
    st.dataframe(
        pd.DataFrame(break_even_rows), hide_index=True, use_container_width=True
    )


# ---------------------------------------------------------------------------
# Saved profiles
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved profiles")
    profiles = get_profiles(user_id)
    if not profiles:
        st.info("Nothing saved yet. Build a household profile and save it.")
    else:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Name": row["name"],
                        "Leakage (g/yr)": round(row["total_leakage_kg"] * 1000, 1),
                        "From non-bin pathways": (
                            f"{row['pathway_share'] * 100:.0f}%"
                        ),
                        "Saved": row["created_at"],
                    }
                    for row in profiles
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        to_delete = st.selectbox(
            "Remove a profile",
            [row["id"] for row in profiles],
            format_func=lambda i: next(
                row["name"] for row in profiles if row["id"] == i
            ),
            key="plastic_delete",
        )
        if st.button("Delete", key="plastic_delete_button"):
            if delete_profile(user_id, to_delete):
                st.success("Deleted.")
                st.rerun()
            else:
                st.error("Could not delete that profile.")

    st.markdown("---")
    st.caption(
        "Leakage factors carry real uncertainty — tyre wear estimates in the "
        "literature span roughly a factor of three, and the compartment splits "
        "are catchment-specific. The ranking between pathways is considerably "
        "more robust than any individual number, and the ranking is what this "
        "page is for."
    )
