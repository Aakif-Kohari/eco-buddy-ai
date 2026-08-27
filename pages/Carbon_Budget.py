"""Remaining personal carbon budget, and the equity choice behind it.

A percentage target is a statement about the person who set it. A budget is a
statement about the climate. This page computes the second, under four
different ideas of what a fair share is.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.carbon.carbon_budget_equity import (
    BUDGET_BASE_YEAR,
    DEFAULT_CONVERGENCE_YEAR,
    DEFAULT_LIKELIHOOD,
    DEFAULT_TARGET,
    FEASIBLE_ANNUAL_REDUCTION,
    PATHWAY_LABELS,
    PATHWAYS,
    PRINCIPLE_LABELS,
    PRINCIPLES,
    WORLD_AVERAGE_INCOME,
    BudgetError,
    compare_principles,
    cost_of_delay,
    current_year,
    delete_scenario,
    get_budget_insights,
    get_scenarios,
    list_likelihoods,
    list_targets,
    pathway_series,
    personal_budget,
    remaining_global_budget,
    required_rate,
    save_scenario,
    sensitivity,
    shortfall,
)
from styles.theme import apply_theme

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🌍 Carbon Budget</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A household emitting 20 tonnes that cuts 40% is at 12. One emitting 4 "
    "tonnes that cuts 40% is at 2.4. Both hit a 40% target. Only one is "
    "anywhere near a fair share — and a target that never references an "
    "outside limit cannot tell them apart."
)

with st.expander("Why a budget is not a target"):
    st.markdown(
        """
**Warming responds to the total, not the rate.** Two pathways ending at the same
2050 number can differ by a decade of emissions in the area underneath them, and
the one that delays is the one that overshoots. So arriving on time is not
enough, and starting late cannot be made up by finishing harder — past a certain
delay the rate you would need exceeds anything anyone has ever achieved and the
budget is simply gone.

**Fair share is contested, and that is the point.** Four principles are shown
below, all of them defensible, and they differ by more than a factor of six for
the same person. Picking one and calling it *the* answer would be a political
choice dressed as arithmetic. The most common choice is the one nobody notices
they are making: every "cut 40%" target is grandfathering, which gives the
largest share to whoever already emits the most.

**The global budget is a distribution.** It is quoted at a probability of
staying below a temperature — the 83% figure is little more than half the 50%
one — and it shrinks every year. The figure here is computed forward from
"""
        + f"{BUDGET_BASE_YEAR} by subtracting the emissions that have actually "
        "happened since, rather than stored as a constant that quietly goes "
        "stale."
    )

tab_budget, tab_pathway, tab_delay, tab_saved = st.tabs(
    ["Your share", "What it takes", "The cost of waiting", "Saved scenarios"]
)


with tab_budget:
    st.subheader("Start with what you emit")

    inputs = st.columns(3)
    with inputs[0]:
        annual_tonnes = st.number_input(
            "Your annual footprint (tonnes CO2e)",
            min_value=0.1, value=8.0, step=0.5,
        )
    with inputs[1]:
        target = st.selectbox(
            "Temperature target", options=list_targets(),
            index=list_targets().index(DEFAULT_TARGET),
            format_func=lambda value: f"{value} °C",
        )
    with inputs[2]:
        likelihood = st.selectbox(
            "Likelihood of staying below it",
            options=list_likelihoods(target),
            index=list_likelihoods(target).index(DEFAULT_LIKELIHOOD),
            format_func=lambda value: f"{value}%",
        )

    try:
        global_budget = remaining_global_budget(target, likelihood)
    except BudgetError as exc:
        st.error(str(exc))
        st.stop()

    st.markdown("#### The global budget it comes out of")
    a, b, c, d = st.columns(4)
    a.metric(
        f"At {BUDGET_BASE_YEAR}", f"{global_budget['at_base_year_gt']:,.0f} Gt"
    )
    b.metric("Spent since", f"{global_budget['elapsed_gt']:,.0f} Gt")
    c.metric("Left now", f"{global_budget['remaining_gt']:,.0f} Gt")
    d.metric(
        "At current global emissions",
        f"{global_budget['years_at_current_rate']:.1f} yr",
    )
    st.caption(
        f"{global_budget['spent_share']:.0%} of the {target} °C budget at "
        f"{likelihood}% likelihood has already gone. {global_budget['note']}"
    )

    settings = st.columns(2)
    with settings[0]:
        convergence_year = st.slider(
            "Converge to equal per capita by",
            min_value=current_year() + 1, max_value=2100,
            value=DEFAULT_CONVERGENCE_YEAR,
            help=(
                "Only used by contraction and convergence — and it is the "
                "entire negotiation. Set it far enough out and the principle "
                "becomes grandfathering."
            ),
        )
    with settings[1]:
        income = st.number_input(
            "Your income (for ability to pay)",
            min_value=0.0, value=float(WORLD_AVERAGE_INCOME), step=1000.0,
            help=(
                f"The world average is around {WORLD_AVERAGE_INCOME:,.0f}. At "
                "exactly the average this principle returns the equal share."
            ),
        )

    comparison = compare_principles(
        annual_tonnes, target, likelihood, convergence_year,
        income if income > 0 else None,
    )

    frame = pd.DataFrame([
        {
            "Principle": row["principle_label"],
            "Budget (tonnes)": row["budget_tonnes"],
            "Years at your rate": row["years_at_current_rate"],
            "Against an equal share": row["relative_to_equal_share"],
        }
        for row in comparison["rows"]
    ])

    principle_chart = px.bar(
        frame, x="Budget (tonnes)", y="Principle", orientation="h",
        text="Years at your rate",
    )
    principle_chart.update_traces(
        marker_color="#0f766e", texttemplate="%{text:.1f} yr", textposition="outside"
    )
    principle_chart.update_layout(
        height=360, margin=dict(l=10, r=60, t=30, b=10)
    )
    st.plotly_chart(principle_chart, use_container_width=True)

    st.dataframe(frame, use_container_width=True, hide_index=True)

    if comparison["ratio"]:
        st.error(
            f"Same person, same target, same likelihood: "
            f"**{comparison['low_tonnes']:,.0f} to "
            f"{comparison['high_tonnes']:,.0f} tonnes**, a factor of "
            f"**{comparison['ratio']:.1f}**. Choosing between these is not a "
            "calculation."
        )

    for row in comparison["rows"]:
        st.markdown(f"- **{row['principle_label']}** — {row['principle_note']}")

    st.markdown("#### What this says")
    for line in get_budget_insights(comparison):
        st.markdown(f"- {line}")

    st.markdown("#### What moves the answer")
    sensitivity_frame = pd.DataFrame(
        sensitivity(annual_tonnes, convergence_year, income if income > 0 else None)
    )
    sensitivity_chart = px.bar(
        sensitivity_frame, x="budget_tonnes", y="setting", color="parameter",
        orientation="h",
        labels={"budget_tonnes": "Personal budget (tonnes)", "setting": ""},
    )
    sensitivity_chart.update_layout(
        height=680, margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(sensitivity_chart, use_container_width=True)
    st.caption(
        "The budget definition and the equity principle each move this by more "
        "than most people's entire footprint. Neither is a detail."
    )


with tab_pathway:
    st.subheader("What staying inside it would take")

    principle = st.radio(
        "Under which principle?", options=PRINCIPLES,
        format_func=lambda key: PRINCIPLE_LABELS[key], horizontal=True,
    )
    chosen = personal_budget(
        annual_tonnes, principle, target, likelihood, convergence_year,
        income if income > 0 else None,
    )

    a, b = st.columns(2)
    a.metric("Your budget", f"{chosen['budget_tonnes']:,.1f} t")
    b.metric(
        "At your current rate",
        f"{chosen['years_at_current_rate']:.1f} years",
    )

    rows = []
    for pathway in PATHWAYS:
        result = required_rate(annual_tonnes, chosen["budget_tonnes"], pathway)
        rows.append({
            "Pathway": result["pathway_label"],
            "Cut per year": (
                f"{result['annual_reduction']:.1%}"
                if result["annual_reduction"] is not None else "—"
            ),
            "Achievable at all": "yes" if result["achievable"] else "no",
            "Within what anyone has managed": "yes" if result["feasible"] else "no",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    headline = required_rate(annual_tonnes, chosen["budget_tonnes"])
    if not headline["achievable"]:
        st.error(headline["reason"])
    elif not headline["feasible"]:
        st.warning(headline["reason"])
    else:
        st.success(
            f"A steady {headline['annual_reduction']:.1%} a year stays inside "
            "this budget, and that is within what has been managed before."
        )

    gap = shortfall(annual_tonnes, chosen["budget_tonnes"])
    if not gap["closable_by_reduction"]:
        st.error(
            f"Even cutting at **{FEASIBLE_ANNUAL_REDUCTION:.0%} a year** — "
            "faster than any society has sustained outside a collapse — the "
            f"total still comes to {gap['best_case_cumulative_tonnes']:,.0f} "
            f"tonnes against a budget of {gap['budget_tonnes']:,.0f}. "
            f"**{gap['shortfall_tonnes']:,.0f} tonnes would have to be removed "
            "rather than avoided.** That is not an argument against cutting; it "
            "is what the arithmetic says is left over after cutting as hard as "
            "anyone ever has."
        )

    st.markdown("#### The budget draining underneath")
    series_frame = pd.DataFrame(
        pathway_series(annual_tonnes, chosen["budget_tonnes"], years=45)
    )
    drain = go.Figure()
    drain.add_trace(go.Scatter(
        x=series_frame["year"], y=series_frame["emissions_tonnes"],
        name="Your emissions", mode="lines", fill="tozeroy",
        line=dict(color="#0f766e", width=2),
    ))
    drain.add_trace(go.Scatter(
        x=series_frame["year"], y=series_frame["remaining_budget"],
        name="Budget left", mode="lines", yaxis="y2",
        line=dict(color="#b45309", width=3),
    ))
    drain.add_hline(y=0, line_dash="dot", yref="y2")
    drain.update_layout(
        height=440, xaxis_title="Years from now",
        yaxis_title="tonnes a year",
        yaxis2=dict(title="tonnes left", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(drain, use_container_width=True)
    st.caption(
        "The area under the green curve is what binds — not the value it ends "
        "at. Two plans reaching the same number in 2050 are not equivalent."
    )

    with st.form("save_budget_scenario"):
        name = st.text_input(
            "Name this scenario",
            value=f"{target}C {likelihood}% — {PRINCIPLE_LABELS[principle]}",
        )
        if st.form_submit_button("Save scenario"):
            if not name.strip():
                st.error("Give the scenario a name.")
            elif save_scenario(user_id, name.strip(), chosen):
                st.success("Saved.")
            else:
                st.error("Could not save the scenario.")


with tab_delay:
    st.subheader("What waiting costs")
    st.markdown(
        "Each year of delay spends a year's emissions out of the budget, and "
        "the rate needed afterwards is inversely proportional to what is left. "
        "So the cost of waiting **compounds** — it does not add. This is the "
        "least intuitive thing about a carbon budget and the most important."
    )

    delay_budget = personal_budget(
        annual_tonnes, principle, target, likelihood, convergence_year,
        income if income > 0 else None,
    )["budget_tonnes"]

    delay_rows = cost_of_delay(
        annual_tonnes, delay_budget, delays=(0, 1, 2, 3, 5, 8, 12, 20)
    )
    delay_frame = pd.DataFrame([
        {
            "Wait (years)": row["delay_years"],
            "Budget left": row["budget_left"],
            "Then cut per year": (
                f"{row['annual_reduction']:.1%}"
                if row["annual_reduction"] is not None else "impossible"
            ),
            "Times harder than now": row["multiple_of_acting_now"] or "—",
            "Achievable": "yes" if row["achievable"] else "no",
        }
        for row in delay_rows
    ])
    st.dataframe(delay_frame, use_container_width=True, hide_index=True)

    plottable = [row for row in delay_rows if row["annual_reduction"] is not None]
    if plottable:
        delay_chart = go.Figure()
        delay_chart.add_trace(go.Scatter(
            x=[row["delay_years"] for row in plottable],
            y=[row["annual_reduction"] for row in plottable],
            mode="lines+markers", name="Rate needed afterwards",
            line=dict(color="#b45309", width=3),
        ))
        delay_chart.add_hline(
            y=FEASIBLE_ANNUAL_REDUCTION, line_dash="dash",
            annotation_text="fastest anyone has sustained",
        )
        delay_chart.update_layout(
            height=420, xaxis_title="Years waited before starting",
            yaxis_title="Annual reduction then required",
            yaxis_tickformat=".0%",
            margin=dict(l=10, r=10, t=40, b=10),
        )
        st.plotly_chart(delay_chart, use_container_width=True)

    impossible = [row for row in delay_rows if not row["achievable"]]
    if impossible:
        st.error(
            f"After **{impossible[0]['delay_years']} years** of waiting there "
            "is no reduction rate that stays inside this budget at all — a "
            "single further year at the current rate would already exceed what "
            "is left. Beyond that point the question stops being how fast to "
            "cut."
        )

    st.caption(
        "The dashed line is roughly the fastest sustained reduction any "
        "society has achieved, and it took a collapse to do it. Where the "
        "curve crosses it, delay has turned a hard plan into a different kind "
        "of problem."
    )


with tab_saved:
    st.subheader("Saved scenarios")
    saved = get_scenarios(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for scenario in saved:
            with st.expander(
                f"{scenario['name']} — {scenario['budget_tonnes']:,.0f} t"
            ):
                a, b, c = st.columns(3)
                a.metric("Footprint", f"{scenario['annual_tonnes']:.1f} t/yr")
                b.metric("Budget", f"{scenario['budget_tonnes']:,.1f} t")
                c.metric("Years left", f"{scenario['years_left']:.1f}")
                st.caption(
                    f"{scenario['target']} °C at {scenario['likelihood']}% "
                    "likelihood, under "
                    f"{PRINCIPLE_LABELS.get(scenario['principle'], scenario['principle'])}."
                )
                if st.button("Delete", key=f"delete_scenario_{scenario['id']}"):
                    if delete_scenario(scenario["id"], user_id):
                        st.success("Deleted.")
                        st.rerun()
                    else:
                        st.error("Could not delete it.")
