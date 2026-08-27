"""Why a footprint changed, rather than only that it did.

Every other trend surface in this app reports a delta. This one splits it into
what the user did and what happened to the user, and refuses to let the second
be read as the first.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.utils.footprint_decomposition import (
    DECOMPOSITION_MODES,
    EFFECTS,
    DecompositionError,
    build_period,
    category_effect_table,
    counterfactual_footprint,
    decompose,
    decompose_chain,
    decompose_multiplicative,
    delete_decomposition,
    dominant_effect,
    get_decomposition_insights,
    get_decompositions,
    get_effect,
    save_decomposition,
    waterfall,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🔍 Footprint Decomposition</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Your footprint went down. The interesting question is what moved it — "
    "and whether any of it was you. This page separates the two, exactly, "
    "with nothing left over."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**Nothing is left unexplained.** This uses the Log-Mean Divisia Index, which is
used in energy and emissions accounting for one specific reason: the effects sum
to the observed change with no residual, by construction. The usual approach —
change one factor, hold the rest, subtract — leaves a remainder that grows with
the size of the change, and a remainder invites you to assume it was yours.

**Grid decarbonisation is not your achievement.** In four-factor mode the
emission factor effect is reported apart from everything else. It is a real
reduction in the world. It is not something you did, and every other page in
this app currently credits it to you.

**Doing less is not the same as doing better.** A footprint that fell because
you lost your job is not a footprint that fell because you insulated a loft.
The activity effect and the structure effect tell those apart; a net figure
cannot.

**New and vanished categories are handled, not skipped.** The method is
undefined at zero, so a vanishingly small substitution is used and an appearing
category lands predominantly in the structure effect. That is the analytical
limit of the method rather than a fudge.

**The labels mean only as much as your categories do.** Decompose a footprint
split into "good" and "bad" and you will get arithmetic that adds up perfectly
and tells you nothing. The category split is the modelling; this page is only
the algebra.

**This attributes, it does not prove.** A large structure effect says the mix
changed. It does not say why, and it is not evidence that anything you did
caused it.
        """
    )

st.markdown("---")

DEFAULT_ROWS = [
    {"Category": "Car", "Activity before": 9000.0, "Energy before": 5400.0,
     "Emissions before": 1350.0, "Activity after": 6000.0,
     "Energy after": 3300.0, "Emissions after": 700.0},
    {"Category": "Rail", "Activity before": 1000.0, "Energy before": 300.0,
     "Emissions before": 60.0, "Activity after": 4000.0,
     "Energy after": 1100.0, "Emissions after": 180.0},
    {"Category": "Flights", "Activity before": 4000.0, "Energy before": 1200.0,
     "Emissions before": 900.0, "Activity after": 0.0,
     "Energy after": 0.0, "Emissions after": 0.0},
    {"Category": "E-bike", "Activity before": 0.0, "Energy before": 0.0,
     "Emissions before": 0.0, "Activity after": 1500.0,
     "Energy after": 25.0, "Emissions after": 4.0},
]

st.markdown("### The two periods")

meta_left, meta_mid, meta_right = st.columns(3)
with meta_left:
    before_label = st.text_input("Earlier period", value="2024", key="fd_before")
with meta_mid:
    after_label = st.text_input("Later period", value="2025", key="fd_after")
with meta_right:
    activity_unit = st.text_input(
        "Activity unit", value="km",
        help="One unit for the whole table. The structure effect is a share of "
             "a total activity, and a total across kilometres and kilowatt-"
             "hours is not a quantity.",
        key="fd_unit",
    )

mode_choice = st.radio(
    "Mode",
    list(DECOMPOSITION_MODES),
    format_func=lambda k: DECOMPOSITION_MODES[k]["label"],
    horizontal=True,
    key="fd_mode",
)
st.caption(DECOMPOSITION_MODES[mode_choice]["note"])

columns = ["Category", "Activity before", "Emissions before",
           "Activity after", "Emissions after"]
if mode_choice == "four_factor":
    columns = ["Category", "Activity before", "Energy before",
               "Emissions before", "Activity after", "Energy after",
               "Emissions after"]

frame = pd.DataFrame(DEFAULT_ROWS)[columns]
edited = st.data_editor(
    frame,
    num_rows="dynamic",
    width="stretch",
    key="fd_editor",
)

before_categories = {}
after_categories = {}
for _, row in edited.iterrows():
    name = str(row.get("Category") or "").strip()
    if not name:
        continue
    key = name.lower().replace(" ", "_").replace("-", "_")
    before_entry = {
        "activity": float(row.get("Activity before") or 0.0),
        "emissions": float(row.get("Emissions before") or 0.0),
        "label": name,
    }
    after_entry = {
        "activity": float(row.get("Activity after") or 0.0),
        "emissions": float(row.get("Emissions after") or 0.0),
        "label": name,
    }
    if mode_choice == "four_factor":
        before_entry["energy"] = float(row.get("Energy before") or 0.0)
        after_entry["energy"] = float(row.get("Energy after") or 0.0)
    before_categories[key] = before_entry
    after_categories[key] = after_entry

if not before_categories:
    st.info("Add at least one category to decompose.")
    st.stop()

try:
    before = build_period(before_label or "Earlier", before_categories,
                          activity_unit=activity_unit or "activity units")
    after = build_period(after_label or "Later", after_categories,
                         activity_unit=activity_unit or "activity units")
    result = decompose(before, after)
except DecompositionError as error:
    st.error(str(error))
    st.stop()
except (TypeError, ValueError) as error:
    st.error(f"That table could not be read as numbers: {error}")
    st.stop()

if not result["perfectly_decomposed"]:
    st.error(
        f"This decomposition did not close — {result['residual']:.9f} kg CO2e "
        f"is unaccounted for. Nothing below should be trusted until that is "
        f"resolved."
    )

st.markdown("---")

tab_split, tab_categories, tab_credit, tab_ratio, tab_chain, tab_saved = st.tabs(
    [
        "⚖️ The split",
        "📦 By category",
        "🔌 Grid credit",
        "％ In percent",
        "🔗 Over time",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# The split
# ---------------------------------------------------------------------------
with tab_split:
    st.markdown("### What moved the number")

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Observed change",
        f"{result['observed_change']:+,.0f} kg CO2e",
        delta=f"from {result['before_total']:,.0f} to "
              f"{result['after_total']:,.0f}",
        delta_color="off",
    )
    m2.metric(
        "What you did",
        f"{result['attributable_change']:+,.0f} kg CO2e",
        help="Activity, structure and intensity combined.",
    )
    m3.metric(
        "What happened to you",
        f"{result['exogenous_change']:+,.0f} kg CO2e",
        help="The emission factor of the energy supplied to you.",
    )

    rows = waterfall(result)
    measures = ["absolute"] + ["relative"] * (len(rows) - 2) + ["total"]
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=[row["label"] for row in rows],
            y=[row["value"] for row in rows],
            connector={"line": {"color": "#9aa5a0"}},
            decreasing={"marker": {"color": "#2e7d63"}},
            increasing={"marker": {"color": "#b4553f"}},
            totals={"marker": {"color": "#5b6b78"}},
        )
    )
    fig.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="kg CO2e",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### What each bar means")
    for effect in result["effect_keys"]:
        meta = get_effect(effect)
        value = result["effects"][effect]
        badge = "you" if meta["attributable"] else "not you"
        st.markdown(
            f"**{meta['label']}** ({meta['short']}) — `{value:+,.0f} kg CO2e` "
            f"· _{badge}_"
        )
        st.caption(meta["note"])

    top = dominant_effect(result)
    if not top["attributable"]:
        st.warning(
            f"The largest single effect here is **{top['label'].lower()}**, "
            f"which is not this household's doing. Read the headline number "
            f"with that in mind."
        )

    st.markdown("#### Findings")
    for line in get_decomposition_insights(result):
        st.markdown(f"- {line}")

    st.caption(
        f"Residual: {result['residual']:.9f} kg CO2e. It is shown because a "
        f"decomposition that does not close is a broken one, and hiding that "
        f"would be worse than not drawing the chart."
    )


# ---------------------------------------------------------------------------
# By category
# ---------------------------------------------------------------------------
with tab_categories:
    st.markdown("### Which categories produced each effect")

    effect_choice = st.selectbox(
        "Effect",
        [e for e in result["effect_keys"]],
        format_func=lambda k: EFFECTS[k]["label"],
        key="fd_effect_pick",
    )
    st.caption(get_effect(effect_choice)["note"])

    table = category_effect_table(result, effect_choice)
    contribution = go.Figure(
        go.Bar(
            x=[row["value"] for row in table],
            y=[row["label"] for row in table],
            orientation="h",
            marker_color=[
                "#2e7d63" if row["value"] < 0 else "#b4553f" for row in table
            ],
        )
    )
    contribution.update_layout(
        height=90 + 42 * len(table),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title=f"{EFFECTS[effect_choice]['label']} effect (kg CO2e)",
    )
    st.plotly_chart(contribution, width="stretch")

    st.markdown("#### Every category, every effect")
    detail = []
    for row in result["categories"]:
        entry = {
            "Category": row["label"],
            f"{result['before_label']} (kg)": row["before_emissions"],
            f"{result['after_label']} (kg)": row["after_emissions"],
            "Change (kg)": row["change"],
        }
        for effect in result["effect_keys"]:
            entry[EFFECTS[effect]["label"]] = round(row["effects"][effect], 1)
        detail.append(entry)
    st.dataframe(pd.DataFrame(detail), width="stretch", hide_index=True)

    appeared = [r["label"] for r in result["categories"]
                if r["appeared"] and r["after_emissions"] > 0]
    gone = [r["label"] for r in result["categories"]
            if r["disappeared"] and r["before_emissions"] > 0]
    if appeared:
        st.info(
            f"Appeared this period: {', '.join(appeared)}. These land "
            f"predominantly in the structure effect — the analytical limit of "
            f"the method at zero, not a rounding choice."
        )
    if gone:
        st.warning(
            f"Vanished this period: {', '.join(gone)}. Worth confirming the "
            f"activity stopped rather than the logging. The arithmetic cannot "
            f"tell those apart and will score both as a reduction."
        )


# ---------------------------------------------------------------------------
# Grid credit
# ---------------------------------------------------------------------------
with tab_credit:
    st.markdown("### What you would have shown if the supply had not changed")

    if result["mode"] != "four_factor":
        st.info(
            "This needs the four-factor mode. Without an energy figure per "
            "category, supply-side decarbonisation is folded into the "
            "intensity effect and cannot be pulled back out of it."
        )
    else:
        counter = counterfactual_footprint(result)
        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Reported footprint",
            f"{counter['reported_after']:,.0f} kg CO2e",
        )
        c2.metric(
            "Without the supply change",
            f"{counter['without_supply_change']:,.0f} kg CO2e",
        )
        c3.metric(
            "Credit you were handed",
            f"{counter['supply_credit']:+,.0f} kg CO2e",
            help="Positive means the cleaner supply flattered your number.",
        )

        comparison = go.Figure()
        comparison.add_trace(go.Bar(
            name=result["before_label"],
            x=["Footprint"], y=[result["before_total"]],
            marker_color="#5b6b78",
        ))
        comparison.add_trace(go.Bar(
            name=f"{result['after_label']} (reported)",
            x=["Footprint"], y=[counter["reported_after"]],
            marker_color="#2e7d63",
        ))
        comparison.add_trace(go.Bar(
            name=f"{result['after_label']} (your doing only)",
            x=["Footprint"], y=[counter["without_supply_change"]],
            marker_color="#c0873f",
        ))
        comparison.update_layout(
            barmode="group", height=400,
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="kg CO2e",
        )
        st.plotly_chart(comparison, width="stretch")

        st.markdown(
            f"Your own change over the period was "
            f"**{counter['own_change']:+,.0f} kg CO2e** "
            f"({counter['own_change_percent']:+.1f}% of where you started). "
            f"That is the figure to hold yourself to."
        )

        if counter["supply_credit"] > 0 and result["observed_change"] < 0:
            share = counter["supply_credit_share"]
            st.warning(
                f"{share * 100:.0f}% of the reduction on the headline came "
                f"from the energy supply getting cleaner. Nothing in this "
                f"household caused it."
            )
        if result["attributable_change"] > 0 and result["observed_change"] < 0:
            st.error(
                "The footprint fell while this household's own contribution "
                "rose. The supply improved faster than behaviour worsened, "
                "which is not the same thing as progress."
            )


# ---------------------------------------------------------------------------
# In percent
# ---------------------------------------------------------------------------
with tab_ratio:
    st.markdown("### The same decomposition, in percentages")
    st.caption(
        "Multiplicative LMDI. The indices multiply back to the total ratio, "
        "which is the ratio-form counterpart of the additive version leaving "
        "no residual."
    )

    try:
        ratio = decompose_multiplicative(before, after)
    except DecompositionError as error:
        st.error(str(error))
    else:
        percent_fig = go.Figure(
            go.Bar(
                x=[EFFECTS[e]["label"] for e in ratio["percent_change"]],
                y=list(ratio["percent_change"].values()),
                marker_color=[
                    "#2e7d63" if v < 0 else "#b4553f"
                    for v in ratio["percent_change"].values()
                ],
            )
        )
        percent_fig.update_layout(
            height=380, margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="Effect on the footprint (%)",
        )
        st.plotly_chart(percent_fig, width="stretch")

        st.dataframe(
            pd.DataFrame([
                {
                    "Effect": EFFECTS[effect]["label"],
                    "Index": ratio["indices"][effect],
                    "Change (%)": ratio["percent_change"][effect],
                    "Yours": "yes" if EFFECTS[effect]["attributable"] else "no",
                }
                for effect in ratio["indices"]
            ]),
            width="stretch", hide_index=True,
        )

        if ratio["closes"]:
            st.success(
                f"The indices multiply to {ratio['product']:.4f}, which is the "
                f"total ratio {ratio['total_ratio']:.4f}. Nothing is missing."
            )
        else:
            st.error(
                "The indices do not multiply back to the total ratio. The "
                "result is wrong and should not be read."
            )


# ---------------------------------------------------------------------------
# Over time
# ---------------------------------------------------------------------------
with tab_chain:
    st.markdown("### Chaining across more than two periods")
    st.markdown(
        "Decomposing each step and adding the effects is not the same as "
        "decomposing the endpoints. Where they differ, the route mattered — "
        "which is itself worth knowing, and is usually hidden."
    )

    st.caption(
        "Add a middle period below to see the difference. Values are in the "
        "same units as the table above."
    )

    middle_rows = []
    for row in result["categories"]:
        middle_rows.append({
            "Category": row["label"],
            "Activity": round(
                (before["categories"].get(row["category"], {}).get("activity", 0.0)
                 + after["categories"].get(row["category"], {}).get("activity", 0.0)) / 2, 1
            ),
            "Energy": round(
                (before["categories"].get(row["category"], {}).get("energy", 0.0)
                 + after["categories"].get(row["category"], {}).get("energy", 0.0)) / 2, 1
            ),
            "Emissions": round(
                (row["before_emissions"] + row["after_emissions"]) / 2, 1
            ),
        })
    if result["mode"] != "four_factor":
        middle_rows = [
            {k: v for k, v in row.items() if k != "Energy"}
            for row in middle_rows
        ]

    middle_label = st.text_input(
        "Middle period label", value="Mid", key="fd_mid_label"
    )
    middle_edit = st.data_editor(
        pd.DataFrame(middle_rows), num_rows="dynamic",
        width="stretch", key="fd_mid_editor",
    )

    middle_categories = {}
    for _, row in middle_edit.iterrows():
        name = str(row.get("Category") or "").strip()
        if not name:
            continue
        key = name.lower().replace(" ", "_").replace("-", "_")
        entry = {
            "activity": float(row.get("Activity") or 0.0),
            "emissions": float(row.get("Emissions") or 0.0),
            "label": name,
        }
        if result["mode"] == "four_factor":
            entry["energy"] = float(row.get("Energy") or 0.0)
        middle_categories[key] = entry

    if middle_categories:
        try:
            middle = build_period(
                middle_label or "Mid", middle_categories,
                activity_unit=activity_unit or "activity units",
            )
            chain = decompose_chain([before, middle, after])
        except DecompositionError as error:
            st.error(str(error))
        else:
            chain_frame = pd.DataFrame([
                {
                    "Effect": EFFECTS[effect]["label"],
                    "Chained (kg)": chain["chained_effects"].get(effect, 0.0),
                    "Endpoints only (kg)": chain["direct_effects"].get(effect, 0.0),
                    "Difference (kg)": chain["path_dependence"].get(effect, 0.0),
                }
                for effect in chain["direct_effects"]
            ])
            st.dataframe(chain_frame, width="stretch", hide_index=True)

            if chain["path_dependent"]:
                st.warning(
                    f"The route taken changed the attribution by up to "
                    f"{chain['path_dependence_share'] * 100:.0f}% of the total "
                    f"movement. What happened in between was not incidental, "
                    f"and reporting only the endpoints would have hidden it."
                )
            else:
                st.success(
                    "Chaining and the endpoint comparison agree closely. The "
                    "route did not materially change the attribution."
                )


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Save this decomposition")
    name = st.text_input(
        "Name",
        value=f"{result['before_label']} → {result['after_label']}",
        key="fd_save_name",
    )
    if st.button("Save", key="fd_save"):
        try:
            save_decomposition(user_id, name, result)
            st.success("Saved.")
        except DecompositionError as error:
            st.error(str(error))

    st.markdown("---")
    saved = get_decompositions(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for entry in saved:
            with st.container(border=True):
                head, action = st.columns([5, 1])
                with head:
                    st.markdown(f"**{entry['name']}** · {entry['created_at']}")
                    st.caption(
                        f"Observed {entry['observed_change']:+,.0f} kg · "
                        f"yours {entry['attributable_change']:+,.0f} kg · "
                        f"supply {entry['exogenous_change']:+,.0f} kg"
                    )
                with action:
                    if st.button("Delete", key=f"fd_del_{entry['id']}"):
                        if delete_decomposition(user_id, entry["id"]):
                            st.rerun()

st.markdown("---")
st.caption(
    "Method: Log-Mean Divisia Index (LMDI-I), additive and multiplicative "
    "forms, with the analytical-limit treatment of zero terms after Ang and "
    "Liu (2007). Related: src.utils.weather_normalised_energy.py, "
    "src.carbon.ghg_inventory.py, src.carbon.marginal_emissions.py."
)
