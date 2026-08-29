"""Whether reducing carbon made something else worse.

This app computes climate, water, land, biodiversity, nutrient, toxicity,
resource and plastic impacts on eight separate pages in eight separate units.
This is the page that puts them in one frame and asks the question the others
cannot.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.environment.burden_shifting import (
    DEFAULT_SHIFT_THRESHOLD,
    IMPACT_CATEGORIES,
    REFERENCES,
    WEIGHTING_SETS,
    BurdenShiftError,
    coverage_report,
    delete_assessment,
    detect_burden_shift,
    get_assessments,
    get_burden_insights,
    get_impact,
    get_weighting,
    list_impacts,
    list_references,
    list_weightings,
    normalise,
    pareto_front,
    save_assessment,
    trade_off_ratios,
    weighted_score,
    weighting_robustness,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⚖️ Burden Shifting</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Biofuels for land. Batteries for mining. Almond milk for water. Every one "
    "is a defensible carbon recommendation and a potentially poor "
    "environmental one, and nothing in this app could tell the difference."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**No single score by default.** A number summing kilograms to cubic metres to
DALYs is meaningless, and confidently presented meaninglessness is the worst
outcome available here. Normalisation comes first, weighting is always named,
and the disaggregated profile stays the primary output.

**This app already weights — it just does not say so.** By devoting most of its
surface to carbon it has made a choice. The carbon-only weighting set here
reproduces that choice exactly, so you can switch away from it and watch what
changes.

**Some categories have no safe level, and inventing one would be worse.**
Toxicity and plastic leakage have no agreed per-person boundary. They are shown
in their own units and excluded from any weighted total, rather than given a
fabricated reference that would produce a confident number resting on nothing.

**Coverage is stated.** A favourable profile across four categories says
nothing about the three that were not measured. Absence of evidence is the most
likely way a cross-impact view misleads.

**Options that dominate need no value judgement.** Where one choice is better
everywhere, no weighting is required and none is applied. Only the remainder
needs you to choose, and separating the two is the honest way to present this.

**Burden shifting is detected on the disaggregated movement.** A change that
improves the weighted total and triples freshwater impact is still flagged. A
detector reading only the total would miss exactly the cases it exists for.
        """
    )

st.markdown("---")

DEFAULT_PROFILES = {
    "Dairy milk": {
        "climate_change": 1400.0, "water_scarcity": 900.0, "land_use": 1800.0,
        "biodiversity_loss": 42000.0, "eutrophication_freshwater": 0.09,
        "eutrophication_marine": 3.4, "resource_depletion": 0.002,
        "human_toxicity": 2.1e-5, "ecotoxicity": 2600.0,
        "plastic_leakage": 0.4,
    },
    "Almond milk": {
        "climate_change": 520.0, "water_scarcity": 4200.0, "land_use": 900.0,
        "biodiversity_loss": 31000.0, "eutrophication_freshwater": 0.05,
        "eutrophication_marine": 1.1, "resource_depletion": 0.003,
        "human_toxicity": 4.4e-5, "ecotoxicity": 9100.0,
        "plastic_leakage": 0.9,
    },
    "Oat milk": {
        "climate_change": 600.0, "water_scarcity": 700.0, "land_use": 1100.0,
        "biodiversity_loss": 26000.0, "eutrophication_freshwater": 0.06,
        "eutrophication_marine": 1.6, "resource_depletion": 0.002,
        "human_toxicity": 1.8e-5, "ecotoxicity": 2100.0,
        "plastic_leakage": 0.5,
    },
}

st.markdown("### Two options to compare")
st.caption(
    "Annual impacts in each category's own unit. Blank rows are treated as "
    "missing data and reported as such rather than as zero."
)

frame = pd.DataFrame([
    {
        "Category": key,
        "Unit": IMPACT_CATEGORIES[key]["unit"],
        "Before": DEFAULT_PROFILES["Dairy milk"].get(key, 0.0),
        "After": DEFAULT_PROFILES["Almond milk"].get(key, 0.0),
        "Alternative": DEFAULT_PROFILES["Oat milk"].get(key, 0.0),
    }
    for key in list_impacts()
])

label_before, label_after, label_alt = st.columns(3)
with label_before:
    name_before = st.text_input("Before", value="Dairy milk", key="bs_before")
with label_after:
    name_after = st.text_input("After", value="Almond milk", key="bs_after")
with label_alt:
    name_alt = st.text_input("Alternative", value="Oat milk", key="bs_alt")

profile_edit = st.data_editor(
    frame,
    width="stretch",
    disabled=["Category", "Unit"],
    key="bs_profiles",
)

reference = st.radio(
    "Normalise against",
    list_references(),
    format_func=lambda k: REFERENCES[k]["label"],
    horizontal=True,
    key="bs_reference",
)
st.caption(REFERENCES[reference]["note"])

before = {}
after = {}
alternative = {}
for _, row in profile_edit.iterrows():
    key = row.get("Category")
    if key not in IMPACT_CATEGORIES:
        continue
    for target, column in ((before, "Before"), (after, "After"),
                           (alternative, "Alternative")):
        value = row.get(column)
        if value is None or pd.isna(value):
            continue
        target[key] = float(value)

if not before or not after:
    st.info("Fill in at least one category for both options.")
    st.stop()

try:
    normalised_before = normalise(before, reference)
    normalised_after = normalise(after, reference)
    shift = detect_burden_shift(before, after, reference)
except BurdenShiftError as error:
    st.error(str(error))
    st.stop()

st.markdown("---")

tab_shift, tab_profile, tab_weight, tab_options, tab_table, tab_saved = st.tabs(
    [
        "🔀 Did it shift",
        "🌍 The profile",
        "🎚️ Weighting",
        "🏁 Choosing",
        "📚 References",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# Did it shift
# ---------------------------------------------------------------------------
with tab_shift:
    st.markdown(f"### {name_before} → {name_after}")

    if shift["burden_shifted"]:
        st.error(
            f"**Burden shifting.** This change improves "
            f"{len(shift['improved'])} categor"
            f"{'ies' if len(shift['improved']) > 1 else 'y'} and materially "
            f"worsens {len(shift['material_worsening'])}. It is flagged "
            f"whatever any weighted total does."
        )
    else:
        st.success(shift["note"])

    movement = [
        row for row in shift["categories"] if row["share_change"] is not None
    ]
    move_fig = go.Figure(go.Bar(
        x=[row["share_change"] for row in movement],
        y=[row["label"] for row in movement],
        orientation="h",
        marker_color=[
            "#2e7d63" if row["share_change"] < 0 else "#b4553f"
            for row in movement
        ],
    ))
    move_fig.add_vline(x=0, line_color="#5b6b78")
    move_fig.update_layout(
        height=110 + 40 * len(movement),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title=f"Change in {REFERENCES[reference]['label'].lower()}",
    )
    st.plotly_chart(move_fig, width="stretch")
    st.caption(
        f"Net movement across the normalisable categories is "
        f"{shift['net_share_change']:+.3f} reference shares. A net improvement "
        f"does not clear a shift — that is the point of reading the bars "
        f"rather than the sum."
    )

    st.dataframe(
        pd.DataFrame([
            {
                "Category": row["label"],
                "Unit": row["unit"],
                name_before: row["before"],
                name_after: row["after"],
                "Change": row["amount_change"],
                "Relative": (
                    f"{row['relative_change'] * 100:+.0f}%"
                    if row["relative_change"] is not None else "—"
                ),
                "Reference shares": (
                    round(row["share_change"], 4)
                    if row["share_change"] is not None else "not normalisable"
                ),
            }
            for row in shift["categories"]
        ]),
        width="stretch", hide_index=True,
    )

    ratios = trade_off_ratios(shift)
    if ratios:
        st.markdown("#### What you are trading for what")
        st.dataframe(
            pd.DataFrame([
                {
                    "Gained on": row["improved_label"],
                    "Paid in": row["worsened_label"],
                    "Reference shares gained": row["share_gained"],
                    "Reference shares lost": row["share_lost"],
                    "Exchange rate": row["ratio"],
                }
                for row in ratios[:8]
            ]),
            width="stretch", hide_index=True,
        )
        st.caption(
            "Expressed in reference shares rather than raw units, because a "
            "ratio of kilograms to cubic metres is arithmetic rather than "
            "information."
        )

    if shift["unnormalisable_worsening"]:
        names = ", ".join(
            IMPACT_CATEGORIES[key]["label"]
            for key in shift["unnormalisable_worsening"]
        )
        st.warning(
            f"{names} got worse and have no boundary to normalise against, so "
            f"no weighted total will ever reflect it. Read them in their own "
            f"units before deciding."
        )

    st.markdown("#### Findings")
    for line in get_burden_insights(normalised_after, shift):
        st.markdown(f"- {line}")


# ---------------------------------------------------------------------------
# The profile
# ---------------------------------------------------------------------------
with tab_profile:
    st.markdown(f"### {name_after} against the {REFERENCES[reference]['label'].lower()}")

    scored = normalised_after["ranked"]
    profile_fig = go.Figure(go.Bar(
        x=[row["share"] for row in scored],
        y=[row["label"] for row in scored],
        orientation="h",
        marker_color=[
            "#b4553f" if row["share"] > 1.0 else "#2e7d63" for row in scored
        ],
    ))
    profile_fig.add_vline(
        x=1.0, line_dash="dash", line_color="#5b6b78",
        annotation_text=REFERENCES[reference]["label"],
    )
    profile_fig.update_layout(
        height=110 + 40 * len(scored),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Share of the reference",
    )
    st.plotly_chart(profile_fig, width="stretch")

    if normalised_after["worst_category"]:
        worst = get_impact(normalised_after["worst_category"])
        st.markdown(
            f"Furthest beyond its reference: **{worst['label']}** at "
            f"**{normalised_after['worst_share']:.2f}×**. That is the category "
            f"to act on first, and no single-impact page in this app could "
            f"have told you which it was."
        )

    coverage = coverage_report(normalised_after)
    c1, c2 = st.columns(2)
    c1.metric(
        "Categories with data",
        f"{coverage['measured']}/{coverage['total_categories']}",
    )
    c2.metric(
        "Normalisable against this reference",
        f"{normalised_after['scored_coverage'] * 100:.0f}%",
    )
    for warning in coverage["warnings"]:
        st.warning(warning)

    st.markdown("#### Both options side by side")
    comparison_fig = go.Figure()
    for label, normalised in (
        (name_before, normalised_before), (name_after, normalised_after)
    ):
        rows = normalised["ranked"]
        comparison_fig.add_trace(go.Scatterpolar(
            r=[row["share"] for row in rows],
            theta=[row["label"] for row in rows],
            fill="toself", name=label,
        ))
    comparison_fig.update_layout(
        height=520, margin=dict(l=40, r=40, t=40, b=40),
        polar=dict(radialaxis=dict(visible=True)),
    )
    st.plotly_chart(comparison_fig, width="stretch")


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------
with tab_weight:
    st.markdown("### The value judgement, made visible")
    st.markdown(
        "Each of these is a choice. Switching between them and watching the "
        "ranking move is the intended experience, not a caveat on it."
    )

    rows = []
    for key in list_weightings():
        try:
            first = weighted_score(normalised_before, key)["score"]
            second = weighted_score(normalised_after, key)["score"]
        except BurdenShiftError:
            continue
        rows.append({
            "Weighting": WEIGHTING_SETS[key]["label"],
            name_before: round(first, 4),
            name_after: round(second, 4),
            "Change": round(second - first, 4),
            "Verdict": "better" if second < first else "worse",
        })
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    verdicts = {row["Verdict"] for row in rows}
    if len(verdicts) > 1:
        st.error(
            "The verdict on this change depends on which weighting set you "
            "pick. That is a value judgement, not a finding, and presenting "
            "any one of these as the answer would be presenting a choice as a "
            "result."
        )
    else:
        st.success(
            f"Every weighting set here agrees the change is "
            f"{next(iter(verdicts))}. That conclusion does not rest on the "
            f"value judgement."
        )

    chosen = st.selectbox(
        "Show the breakdown for",
        list_weightings(),
        format_func=lambda k: WEIGHTING_SETS[k]["label"],
        key="bs_weighting",
    )
    st.caption(get_weighting(chosen)["note"])

    score = weighted_score(normalised_after, chosen)
    contribution_fig = go.Figure(go.Bar(
        x=[row["contribution"] for row in score["contributions"]],
        y=[row["label"] for row in score["contributions"]],
        orientation="h",
        marker_color="#5b6b78",
    ))
    contribution_fig.update_layout(
        height=110 + 40 * len(score["contributions"]),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Weighted contribution",
    )
    st.plotly_chart(contribution_fig, width="stretch")

    if score["excluded"]:
        names = ", ".join(
            IMPACT_CATEGORIES[key]["label"] for key in score["excluded"]
            if key in IMPACT_CATEGORIES
        )
        st.info(
            f"Excluded from this total: {names}. Either no data or no "
            f"boundary to normalise against. A total that quietly dropped them "
            f"would look more complete than it is."
        )


# ---------------------------------------------------------------------------
# Choosing
# ---------------------------------------------------------------------------
with tab_options:
    st.markdown("### Which option, and does it need a value judgement")

    options = [
        {"name": name_before, "profile": before},
        {"name": name_after, "profile": after},
    ]
    if alternative:
        options.append({"name": name_alt, "profile": alternative})

    try:
        front = pareto_front(options, reference)
        robustness = weighting_robustness(options, reference)
    except BurdenShiftError as error:
        st.error(str(error))
    else:
        if front["needs_value_judgement"]:
            st.warning(front["note"])
        else:
            st.success(front["note"])

        st.markdown("#### Non-dominated options")
        st.markdown(
            ", ".join(f"**{name}**" for name in front["front"])
            or "_none_"
        )
        if front["dominated"]:
            for row in front["dominated"]:
                st.caption(
                    f"{row['name']} is beaten in every category with data by "
                    f"{', '.join(row['dominated_by'])}. No weighting could "
                    f"rescue it."
                )

        st.markdown("#### Who wins under each weighting")
        st.dataframe(
            pd.DataFrame([
                {
                    "Weighting": row["label"],
                    "Winner": row["winner"],
                    **{
                        name: value
                        for name, value in row["scores"].items()
                    },
                }
                for row in robustness["by_weighting"]
            ]),
            width="stretch", hide_index=True,
        )

        (st.success if robustness["robust"] else st.error)(robustness["note"])

        if not robustness["robust"]:
            carbon_winner = robustness["winners"].get("carbon_only")
            equal_winner = robustness["winners"].get("equal")
            if carbon_winner and equal_winner and carbon_winner != equal_winner:
                st.markdown(
                    f"Optimising on carbon alone picks **{carbon_winner}**. "
                    f"Counting every category equally picks **{equal_winner}**. "
                    f"The first is what the rest of this app does, without "
                    f"saying so."
                )


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------
with tab_table:
    st.markdown("### Every reference, its source and how solid it is")
    st.markdown(
        "These are not equally well founded. Downscaling a planetary boundary "
        "to a person involves an allocation choice that is itself contested, "
        "and for three categories there is no agreed boundary at all."
    )

    st.dataframe(
        pd.DataFrame([
            {
                "Category": IMPACT_CATEGORIES[key]["label"],
                "Unit": IMPACT_CATEGORIES[key]["unit"],
                "Global average / person / yr":
                    IMPACT_CATEGORIES[key]["global_average"],
                "Boundary share": (
                    IMPACT_CATEGORIES[key]["boundary"]
                    if IMPACT_CATEGORIES[key]["boundary"] is not None
                    else "none defined"
                ),
                "Confidence": IMPACT_CATEGORIES[key]["confidence"],
                "Produced by": IMPACT_CATEGORIES[key]["module"],
            }
            for key in list_impacts()
        ]),
        width="stretch", hide_index=True,
    )

    for key in list_impacts():
        meta = get_impact(key)
        st.markdown(f"**{meta['label']}** — _{meta['confidence']}_")
        st.caption(meta["note"])


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Save this assessment")
    name = st.text_input(
        "Name", value=f"{name_before} → {name_after}", key="bs_save_name"
    )
    if st.button("Save", key="bs_save"):
        try:
            save_assessment(user_id, name, normalised_after, shift)
            st.success("Saved.")
        except BurdenShiftError as error:
            st.error(str(error))

    st.markdown("---")
    saved = get_assessments(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for entry in saved:
            with st.container(border=True):
                head, action = st.columns([5, 1])
                with head:
                    st.markdown(f"**{entry['name']}** · {entry['created_at']}")
                    worst = (
                        IMPACT_CATEGORIES.get(
                            entry["worst_category"], {}
                        ).get("label", "—")
                    )
                    st.caption(
                        f"{'Burden shifting' if entry['burden_shifted'] else 'No shift detected'}"
                        f" · worst category: {worst}"
                        f" · against {REFERENCES.get(entry['reference'], {}).get('label', entry['reference'])}"
                    )
                with action:
                    if st.button("Delete", key=f"bs_del_{entry['id']}"):
                        if delete_assessment(user_id, entry["id"]):
                            st.rerun()

st.markdown("---")
st.caption(
    f"Threshold for a material worsening: "
    f"{DEFAULT_SHIFT_THRESHOLD:.0%} of a category's reference share. "
    "Read-only with respect to every impact module — it consumes their "
    "outputs and modifies nothing. Related: "
    "src.environment.water_scarcity.py, "
    "src.environment.biodiversity_footprint.py, "
    "src.carbon.toxicity_characterisation.py, src.carbon.abatement_curve.py."
)
