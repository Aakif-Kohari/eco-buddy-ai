"""The impact category where mass tells you nothing.

Every other page in this app is mass-weighted. A few grams of something
persistent and bioaccumulative outweighs tonnes of something inert, which is
why toxicity has been structurally invisible here rather than merely absent.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.carbon.toxicity_characterisation import (
    COMPARTMENTS,
    ECO_UNIT,
    HUMAN_UNIT,
    SUBSTANCES,
    ToxicityError,
    assess_emission,
    assess_inventory,
    characterisation_factor,
    compare_options,
    compartment_sensitivity,
    delete_assessment,
    dominant_contributors,
    ecotoxicity_factor,
    effect_factors,
    get_assessments,
    get_compartment,
    get_substance,
    get_toxicity_insights,
    list_compartments,
    list_families,
    list_interim_substances,
    list_substances,
    save_assessment,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>☣️ Toxicity & Ecotoxicity Impact</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "The word *toxicity* appears three times in this codebase, every time as "
    "an unquantified adjective inside a recommendation. This page gives it a "
    "unit — and shows why it cannot be added to anything else."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**Mass is not the variable.** A few grams of something persistent and
bioaccumulative outweighs tonnes of something inert. Every other module here is
mass-weighted, which is why toxicity had no place in the existing data model
rather than simply being overlooked.

**Three steps, kept visible.** Fate, exposure and effect — how long the
substance persists, how much of it reaches people or organisms, and what it
does when it gets there. The product on its own is an assertion; the
decomposition is an argument.

**The compartment is required.** The same kilogram of cadmium differs by a
factor of several thousand in human toxicity depending only on where it was
released. There is no default, because a caller who does not know the
compartment does not have enough information to be given an answer.

**Cancer and non-cancer are never added.** Different effect factors, different
evidence, and summing them discards the distinction that drives regulation.

**Human and ecosystem indicators do not substitute for each other.** Copper has
the lowest human hazard in this table and one of the highest aquatic ones.
Benzene is the reverse. Either one alone would rank a substitution wrongly.

**Interim factors keep their flag.** Every metal here is interim: its
uncertainty spans orders of magnitude. Where a comparison's winning margin sits
inside that uncertainty, this page says the comparison does not distinguish the
options rather than declaring a winner.

**There is no single environmental score, and there will not be.** Toxicity
spans more orders of magnitude than any other category in this app. Normalised
into a weighted composite it would either dominate the total or vanish from it,
and either way nothing in the total stays readable.
        """
    )

st.markdown("---")

tab_emission, tab_compartment, tab_inventory, tab_substitute, tab_saved = st.tabs(
    [
        "🧪 One emission",
        "📍 Where it went",
        "📋 An inventory",
        "🔄 Substitution",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# One emission
# ---------------------------------------------------------------------------
with tab_emission:
    st.markdown("### One substance, one compartment")

    c1, c2, c3 = st.columns(3)
    with c1:
        family = st.selectbox(
            "Family",
            ["(all)"] + list_families(),
            key="tx_family",
        )
    with c2:
        available = (
            list_substances() if family == "(all)" else list_substances(family)
        )
        substance = st.selectbox(
            "Substance",
            available,
            format_func=lambda k: SUBSTANCES[k]["label"],
            key="tx_substance",
        )
    with c3:
        compartment = st.selectbox(
            "Emitted to",
            list_compartments(),
            format_func=lambda k: COMPARTMENTS[k]["label"],
            key="tx_compartment",
        )

    mass = st.number_input(
        "Mass emitted (kg)", min_value=0.0, value=1.0, step=0.1,
        format="%.4f", key="tx_mass",
    )

    st.caption(f"**{get_substance(substance)['label']}** — {get_substance(substance)['note']}")
    st.caption(f"**{get_compartment(compartment)['label']}** — {get_compartment(compartment)['note']}")

    try:
        result = assess_emission(substance, mass, compartment)
    except ToxicityError as error:
        st.error(str(error))
        st.stop()

    if result["interim"]:
        st.warning(result["interim_note"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Human toxicity, cancer", f"{result['cancer_ctuh']:.3e} {HUMAN_UNIT}")
    m2.metric(
        "Human toxicity, non-cancer",
        f"{result['noncancer_ctuh']:.3e} {HUMAN_UNIT}",
    )
    m3.metric(
        "Freshwater ecotoxicity", f"{result['ecotoxicity_ctue']:.3e} {ECO_UNIT}"
    )
    st.caption(result["aggregation_note"])

    st.markdown("#### Fate × exposure × effect")
    cf = characterisation_factor(substance, compartment)
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Step": "1. Fate",
                    "Quantity": f"{cf['fate_factor_days']:,.1f} days residence",
                    "What it captures": (
                        "How long the substance stays in this compartment. "
                        "This is the step that makes a persistent substance "
                        "dangerous at small mass."
                    ),
                },
                {
                    "Step": "2. Exposure",
                    "Quantity": f"{cf['exposure_factor_per_day']:.3e} /day",
                    "What it captures": (
                        "The compartment's intake rate scaled by how "
                        "bioavailable the substance is."
                    ),
                },
                {
                    "Step": "= Intake fraction",
                    "Quantity": f"{cf['intake_fraction']:.3e}",
                    "What it captures": (
                        "Kilograms taken in per kilogram emitted — fate "
                        "multiplied by exposure."
                    ),
                },
                {
                    "Step": "3. Effect (cancer)",
                    "Quantity": f"{cf['effect_cancer']:.4g} cases/kg intake",
                    "What it captures": "Carcinogenic potency.",
                },
                {
                    "Step": "3. Effect (non-cancer)",
                    "Quantity": f"{cf['effect_noncancer']:.4g} cases/kg intake",
                    "What it captures": "Everything else, on separate evidence.",
                },
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(cf["not_summed_note"])

    eco = ecotoxicity_factor(substance, compartment)
    st.markdown("#### The ecotoxicity path")
    e1, e2, e3 = st.columns(3)
    e1.metric("Reaching freshwater", f"{eco['water_transfer_fraction']:.0%}")
    e2.metric(
        "Freshwater residence", f"{eco['freshwater_residence_days']:,.0f} days"
    )
    e3.metric(
        f"Factor ({ECO_UNIT}/kg)", f"{eco['cf_ctue_per_kg']:.3e}"
    )
    st.caption(eco["boundary_note"])

    st.markdown("#### What this is telling you")
    for insight in get_toxicity_insights(result):
        st.markdown(f"- {insight}")


# ---------------------------------------------------------------------------
# Where it went
# ---------------------------------------------------------------------------
with tab_compartment:
    st.markdown("### Why the compartment is required and not defaulted")

    sens_substance = st.selectbox(
        "Substance",
        list_substances(),
        index=list_substances().index("cadmium"),
        format_func=lambda k: SUBSTANCES[k]["label"],
        key="tx_sens_substance",
    )
    sensitivity = compartment_sensitivity(sens_substance)

    st.warning(sensitivity["note"])

    sens_fig = go.Figure(
        go.Bar(
            x=[row["label"] for row in sensitivity["rows"]],
            y=[
                row["cancer_ctuh"] + row["noncancer_ctuh"]
                for row in sensitivity["rows"]
            ],
            marker_color="#7b506f",
        )
    )
    sens_fig.update_layout(
        height=340,
        margin=dict(l=10, r=10, t=20, b=10),
        yaxis_title=f"{HUMAN_UNIT} per kg emitted",
        yaxis_type="log",
        xaxis_tickangle=-25,
    )
    st.plotly_chart(sens_fig, use_container_width=True)
    st.caption("Log scale — a linear axis would show one bar and five slivers.")

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Compartment": row["label"],
                    "Intake fraction": f"{row['intake_fraction']:.3e}",
                    f"Cancer ({HUMAN_UNIT})": f"{row['cancer_ctuh']:.3e}",
                    f"Non-cancer ({HUMAN_UNIT})": f"{row['noncancer_ctuh']:.3e}",
                    f"Ecotoxicity ({ECO_UNIT})": f"{row['ecotoxicity_ctue']:.3e}",
                }
                for row in sensitivity["rows"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### The compartments")
    for key in list_compartments():
        st.caption(f"**{COMPARTMENTS[key]['label']}** — {COMPARTMENTS[key]['note']}")


# ---------------------------------------------------------------------------
# An inventory
# ---------------------------------------------------------------------------
with tab_inventory:
    st.markdown("### Several substances at once")
    st.caption(
        "Totalled per indicator. There is no grand total, because cancer "
        "cases, non-cancer cases and potentially affected fractions of "
        "freshwater species are not commensurable."
    )

    inv_compartment = st.selectbox(
        "Emitted to",
        list_compartments(),
        index=list_compartments().index("agricultural_soil"),
        format_func=lambda k: COMPARTMENTS[k]["label"],
        key="tx_inv_compartment",
    )

    chosen = st.multiselect(
        "Substances",
        list_substances(),
        default=["mercury", "zinc_ion", "glyphosate"],
        format_func=lambda k: SUBSTANCES[k]["label"],
        key="tx_inv_substances",
    )

    if not chosen:
        st.info("Pick at least one substance.")
    else:
        masses = {}
        cols = st.columns(min(3, len(chosen)))
        for i, key in enumerate(chosen):
            with cols[i % len(cols)]:
                masses[key] = st.number_input(
                    f"{SUBSTANCES[key]['label']} (kg)",
                    min_value=0.0,
                    value=1.0,
                    step=0.01,
                    format="%.4f",
                    key=f"tx_mass_{key}",
                )

        inventory = assess_inventory(masses, inv_compartment)

        t1, t2, t3 = st.columns(3)
        t1.metric(
            f"Cancer ({HUMAN_UNIT})",
            f"{inventory['totals']['cancer_ctuh']:.3e}",
        )
        t2.metric(
            f"Non-cancer ({HUMAN_UNIT})",
            f"{inventory['totals']['noncancer_ctuh']:.3e}",
        )
        t3.metric(
            f"Ecotoxicity ({ECO_UNIT})",
            f"{inventory['totals']['ecotoxicity_ctue']:.3e}",
        )
        st.info(inventory["no_grand_total_note"])

        interim = inventory["interim_share"]["noncancer_ctuh"]
        if interim > 0.5:
            st.warning(
                f"{interim:.0%} of the non-cancer total comes from interim "
                f"factors, whose uncertainty spans orders of magnitude. Use "
                f"this to rank, not to quantify."
            )

        st.markdown("#### Where the impact sits, against where the mass sits")
        indicator = st.radio(
            "Indicator",
            ["noncancer_ctuh", "cancer_ctuh", "ecotoxicity_ctue"],
            format_func=lambda k: {
                "noncancer_ctuh": f"Non-cancer ({HUMAN_UNIT})",
                "cancer_ctuh": f"Cancer ({HUMAN_UNIT})",
                "ecotoxicity_ctue": f"Freshwater ecotoxicity ({ECO_UNIT})",
            }[k],
            horizontal=True,
            key="tx_indicator",
        )
        focus = dominant_contributors(inventory, indicator, top_n=3)

        f1, f2 = st.columns(2)
        f1.metric(
            "Top three, share of impact",
            f"{focus['top_share_of_impact']:.0%}",
        )
        f2.metric(
            "...for this share of the mass",
            f"{focus['top_share_of_mass']:.2%}",
        )
        st.caption(
            "The gap between those two numbers is the entire argument for an "
            "impact indicator over a mass-weighted one."
        )

        inv_fig = go.Figure()
        inv_fig.add_trace(
            go.Bar(
                name="Share of impact",
                x=[row["label"] for row in focus["top"]],
                y=[row["share_of_impact"] for row in focus["top"]],
                marker_color="#7b506f",
            )
        )
        inv_fig.add_trace(
            go.Bar(
                name="Share of mass",
                x=[row["label"] for row in focus["top"]],
                y=[row["share_of_mass"] for row in focus["top"]],
                marker_color="#9aa5a0",
            )
        )
        inv_fig.update_layout(
            height=320,
            barmode="group",
            margin=dict(l=10, r=10, t=20, b=10),
            yaxis_title="share",
            yaxis_tickformat=".0%",
            legend=dict(orientation="h", y=1.15),
        )
        st.plotly_chart(inv_fig, use_container_width=True)

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Substance": row["label"],
                        "Mass (kg)": row["mass_kg"],
                        f"Cancer ({HUMAN_UNIT})": f"{row['cancer_ctuh']:.3e}",
                        f"Non-cancer ({HUMAN_UNIT})": f"{row['noncancer_ctuh']:.3e}",
                        f"Ecotoxicity ({ECO_UNIT})": f"{row['ecotoxicity_ctue']:.3e}",
                        "Factor status": "Interim" if row["interim"] else "Recommended",
                    }
                    for row in inventory["substances"]
                ]
            ),
            hide_index=True,
            use_container_width=True,
        )

        with st.form("save_toxicity_assessment"):
            name = st.text_input("Save this as", value="")
            if st.form_submit_button("Save") and name.strip():
                try:
                    save_assessment(user_id, name, inventory)
                    st.success(f"Saved '{name.strip()}'.")
                except ToxicityError as error:
                    st.error(str(error))


# ---------------------------------------------------------------------------
# Substitution
# ---------------------------------------------------------------------------
with tab_substitute:
    st.markdown("### Comparing two options, without resolving the disagreement")
    st.caption(
        "Several classic green substitutions are better on carbon and worse on "
        "human toxicity. This page will tell you when that has happened. It "
        "will not invent a weighting between cancer cases and kilograms of "
        "CO2 to make the decision for you."
    )

    sub_compartment = st.selectbox(
        "Both emitted to",
        list_compartments(),
        index=list_compartments().index("freshwater"),
        format_func=lambda k: COMPARTMENTS[k]["label"],
        key="tx_sub_compartment",
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Option A**")
        name_a = st.text_input("Name", "Current material", key="tx_name_a")
        sub_a = st.selectbox(
            "Substance",
            list_substances(),
            index=list_substances().index("benzene"),
            format_func=lambda k: SUBSTANCES[k]["label"],
            key="tx_sub_a",
        )
        mass_a = st.number_input(
            "kg emitted", min_value=0.0, value=1.0, step=0.1,
            format="%.4f", key="tx_mass_a",
        )
        carbon_a = st.number_input(
            "kg CO2e", min_value=0.0, value=3.0, step=0.5, key="tx_carbon_a"
        )
    with c2:
        st.markdown("**Option B**")
        name_b = st.text_input("Name", "Proposed substitute", key="tx_name_b")
        sub_b = st.selectbox(
            "Substance",
            list_substances(),
            index=list_substances().index("imidacloprid"),
            format_func=lambda k: SUBSTANCES[k]["label"],
            key="tx_sub_b",
        )
        mass_b = st.number_input(
            "kg emitted", min_value=0.0, value=1.0, step=0.1,
            format="%.4f", key="tx_mass_b",
        )
        carbon_b = st.number_input(
            "kg CO2e", min_value=0.0, value=2.0, step=0.5, key="tx_carbon_b"
        )

    try:
        comparison = compare_options([
            {
                "name": name_a or "Option A",
                "emissions": {sub_a: mass_a},
                "compartment": sub_compartment,
                "carbon_kg": carbon_a,
            },
            {
                "name": name_b or "Option B",
                "emissions": {sub_b: mass_b},
                "compartment": sub_compartment,
                "carbon_kg": carbon_b,
            },
        ])
    except ToxicityError as error:
        st.error(str(error))
        st.stop()

    if comparison["too_close_to_call"]:
        st.warning(comparison["verdict"])
    elif comparison["indicators_disagree"]:
        st.warning(comparison["verdict"])
    else:
        st.success(comparison["verdict"])

    v1, v2, v3 = st.columns(3)
    v1.metric("Better for people", comparison["best_human_toxicity"])
    v2.metric("Better for freshwater", comparison["best_ecotoxicity"])
    v3.metric(
        "Better on carbon",
        comparison["best_carbon"] or "not compared",
    )

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Option": option["name"],
                    "kg CO2e": option["carbon_kg"],
                    f"Cancer ({HUMAN_UNIT})": f"{option['cancer_ctuh']:.3e}",
                    f"Non-cancer ({HUMAN_UNIT})": f"{option['noncancer_ctuh']:.3e}",
                    f"Ecotoxicity ({ECO_UNIT})": f"{option['ecotoxicity_ctue']:.3e}",
                    "Interim share": f"{option['interim_share']['noncancer_ctuh']:.0%}",
                }
                for option in comparison["options"]
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.info(comparison["no_composite_note"])

    st.markdown("#### Effect factors, where the divergence actually lives")
    st.caption(
        "A characterisation factor mixes hazard with persistence. The effect "
        "factor is the hazard on its own, and it is what a substitution "
        "decision turns on."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Substance": SUBSTANCES[key]["label"],
                    "Cancer (cases/kg intake)": effect_factors(key)["cancer"],
                    "Non-cancer (cases/kg intake)": effect_factors(key)["noncancer"],
                    "Aquatic (PAF·m³/kg)": SUBSTANCES[key]["eco_effect_paf_m3_per_kg"],
                    "Status": (
                        "Interim" if key in list_interim_substances()
                        else "Recommended"
                    ),
                }
                for key in (sub_a, sub_b)
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Saved assessments")
    saved = get_assessments(user_id)
    if not saved:
        st.info("Nothing saved yet. Save an inventory from the third tab.")
    else:
        for record in saved:
            with st.expander(
                f"{record['name']} — "
                f"{record['noncancer_ctuh']:.3e} {HUMAN_UNIT} non-cancer, "
                f"{record['ecotoxicity_ctue']:.3e} {ECO_UNIT}"
            ):
                payload = record["payload"]
                st.write(
                    f"Emitted to "
                    f"**{COMPARTMENTS.get(record['compartment'], {}).get('label', record['compartment'])}**"
                )
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Substance": SUBSTANCES.get(
                                    row["substance"], {}
                                ).get("label", row["substance"]),
                                "Mass (kg)": row["mass_kg"],
                                f"Non-cancer ({HUMAN_UNIT})":
                                    f"{row['noncancer_ctuh']:.3e}",
                                f"Ecotoxicity ({ECO_UNIT})":
                                    f"{row['ecotoxicity_ctue']:.3e}",
                                "Status": (
                                    "Interim" if row["interim"]
                                    else "Recommended"
                                ),
                            }
                            for row in payload.get("substances", [])
                        ]
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
                st.caption(f"Saved {record['created_at']}")
                if st.button("Delete", key=f"tx_del_{record['id']}"):
                    if delete_assessment(user_id, record["id"]):
                        st.success("Deleted.")
                        st.rerun()
