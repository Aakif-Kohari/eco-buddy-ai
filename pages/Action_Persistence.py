"""How long an adopted action actually lasts.

Every recommendation surface in this app multiplies a per-occurrence saving by
a year. This page models the lapse that multiplication assumes away, and
re-ranks the options once it is accounted for.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.lifestyle.action_persistence import (
    ACTION_CLASSES,
    DEFAULT_DISCOUNT_RATE,
    PersistenceError,
    blend_with_prior,
    class_summary,
    delete_plan,
    get_persistence_insights,
    get_plans,
    kaplan_meier,
    list_action_classes,
    persistence_adjusted_ranking,
    portfolio_persistence,
    reengagement_window,
    save_plan,
    seasonal_reactivation,
    survival_curve,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⏳ Action Persistence</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "This app takes a saving you made once and multiplies it by fifty-two. "
    "That arithmetic assumes you are still doing it in twelve months. Most "
    "people are not, and which options that changes is the interesting part."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**The principle is already in this codebase.** `permanence_accounting.py` says
a tonne of stored carbon that leaks back is not a tonne saved. The same is true
of a habit that stops, and nothing here represented it until now.

**The first month is the hard part, and that needs a shape parameter.** Survive
the early weeks and the odds improve — a *falling* hazard. An exponential decay
model has constant hazard by definition and cannot express that at all, which
is why these are Weibull curves and why the shape is stated for every class.

**Fragile options currently outrank durable ones.** The abatement curve sorts
on undiscounted annual savings, which cannot see durability. A commitment with
a half-life of four months and a loft insulation job come out on the same
footing. Re-ranking on expected savings is the whole point of this page.

**A still-running action is not a lapse.** Anything ongoing at the end of your
history is censored, not failed. Counting it as failed biases every estimate
downward, and it is the most common way this kind of number goes wrong.

**Stopping in January and restarting in March is not abandonment.** Seasonal
patterns are detected on the circle rather than the line, because December and
January are adjacent and a linear measure calls that pattern diffuse.

**None of this is an argument against fragile actions.** A plan resting mostly
on them needs re-engagement built in rather than assumed. That is a design
conclusion, not a judgement about the person.
        """
    )

st.markdown("---")

DEFAULT_PLAN = pd.DataFrame([
    {"Action": "Shorter showers", "Weekly saving (kg CO2e)": 2.4,
     "Class": "daily_effort", "Upfront cost": 0.0},
    {"Action": "Loft insulation", "Weekly saving (kg CO2e)": 1.9,
     "Class": "structural_one_off", "Upfront cost": 600.0},
    {"Action": "Car share to work", "Weekly saving (kg CO2e)": 3.1,
     "Class": "social_dependent", "Upfront cost": 0.0},
    {"Action": "Drying rack", "Weekly saving (kg CO2e)": 1.2,
     "Class": "equipment_mediated", "Upfront cost": 25.0},
    {"Action": "Weekly meal plan", "Weekly saving (kg CO2e)": 1.6,
     "Class": "periodic_effort", "Upfront cost": 0.0},
])

st.markdown("### Your plan")
st.caption(
    "One row per action. The class is what determines the decay curve, so it "
    "is the field worth getting right."
)

plan_edit = st.data_editor(
    DEFAULT_PLAN,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "Class": st.column_config.SelectboxColumn(
            "Class", options=list_action_classes(), required=True,
        ),
    },
    key="ap_plan",
)

horizon_col, discount_col = st.columns(2)
with horizon_col:
    horizon = st.slider(
        "Horizon (weeks)", 52, 520, 260, 52, key="ap_horizon",
        help="How far ahead to count savings. Past a point the discounting "
             "makes further weeks irrelevant.",
    )
with discount_col:
    discount = st.slider(
        "Annual discount rate", 0.0, 0.12, DEFAULT_DISCOUNT_RATE, 0.01,
        key="ap_discount",
    )

options = []
for _, row in plan_edit.iterrows():
    name = str(row.get("Action") or "").strip()
    action_class = row.get("Class")
    if not name or action_class not in ACTION_CLASSES:
        continue
    options.append({
        "name": name,
        "weekly_saving": float(row.get("Weekly saving (kg CO2e)") or 0.0),
        "action_class": action_class,
        "cost": float(row.get("Upfront cost") or 0.0),
    })

if not options:
    st.info("Add at least one action with a valid class.")
    st.stop()

try:
    ranking = persistence_adjusted_ranking(options, horizon, discount)
    portfolio = portfolio_persistence(options)
except PersistenceError as error:
    st.error(str(error))
    st.stop()

st.markdown("---")

tab_rank, tab_curves, tab_plan, tab_timing, tab_history, tab_saved = st.tabs(
    [
        "🔀 Re-ranked",
        "📉 Decay curves",
        "🧺 Your plan over time",
        "🔔 When to nudge",
        "🗓️ Your own history",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# Re-ranked
# ---------------------------------------------------------------------------
with tab_rank:
    st.markdown("### What the order looks like once decay is counted")

    moved = ranking["moved"]
    if ranking["ranking_changed"]:
        st.warning(
            f"{len(moved)} of {len(ranking['options'])} options change "
            f"position. The ranking they came from cannot see durability, so "
            f"it favours whichever option is most fragile."
        )
    else:
        st.info(
            "The order is unchanged. Either these options are similarly "
            "durable, or the savings are far enough apart that decay does not "
            "reorder them."
        )

    table = pd.DataFrame([
        {
            "Rank": row["adjusted_rank"],
            "Was": row["naive_rank"],
            "Move": (
                f"↑{row['rank_change']}" if row["rank_change"] > 0
                else f"↓{abs(row['rank_change'])}" if row["rank_change"] < 0
                else "—"
            ),
            "Action": row["name"],
            "Class": row["class_label"],
            "Assumed year 1": row["naive_annual_saving"],
            "Expected year 1": row["expected_first_year"],
            "Overstated by": f"{row['overstatement_share'] * 100:.0f}%",
            "Expected lifetime": row["expected_lifetime_saving"],
        }
        for row in ranking["options"]
    ])
    st.dataframe(table, width="stretch", hide_index=True)

    compare = go.Figure()
    compare.add_trace(go.Bar(
        name="Assumed year 1",
        x=[row["name"] for row in ranking["options"]],
        y=[row["naive_annual_saving"] for row in ranking["options"]],
        marker_color="#b4553f",
    ))
    compare.add_trace(go.Bar(
        name="Expected year 1",
        x=[row["name"] for row in ranking["options"]],
        y=[row["expected_first_year"] for row in ranking["options"]],
        marker_color="#2e7d63",
    ))
    compare.update_layout(
        barmode="group", height=420,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="kg CO2e in the first year",
    )
    st.plotly_chart(compare, width="stretch")
    st.caption(
        "The red bar is what this app currently reports. The gap is the "
        "overstatement, and it is not the same size for every option — which "
        "is exactly why the ranking moves."
    )

    priced = [
        row for row in ranking["options"]
        if row["cost"] > 0 and row["adjusted_cost_per_unit"] is not None
    ]
    if priced:
        st.markdown("#### Cost per kg CO2e")
        st.dataframe(
            pd.DataFrame([
                {
                    "Action": row["name"],
                    "Cost": row["cost"],
                    "Naive (per annual kg)": row["naive_cost_per_unit"],
                    "Adjusted (per lifetime kg)": row["adjusted_cost_per_unit"],
                }
                for row in priced
            ]),
            width="stretch", hide_index=True,
        )
        st.caption(
            "A retrofit looks expensive against one year of savings and "
            "reasonable against the savings it will actually deliver. The "
            "naive column is the one every abatement curve in this app uses."
        )

    st.markdown("#### Findings")
    for line in get_persistence_insights(ranking, portfolio):
        st.markdown(f"- {line}")


# ---------------------------------------------------------------------------
# Decay curves
# ---------------------------------------------------------------------------
with tab_curves:
    st.markdown("### What each class of action does over time")

    curve_fig = go.Figure()
    palette = ["#2e7d63", "#5b6b78", "#c0873f", "#b4553f", "#7a5c9e"]
    for index, key in enumerate(list_action_classes()):
        points = survival_curve(key, horizon_weeks=min(horizon, 260))
        curve_fig.add_trace(go.Scatter(
            x=[point["week"] for point in points],
            y=[point["survival"] * 100 for point in points],
            mode="lines", name=ACTION_CLASSES[key]["label"],
            line=dict(color=palette[index % len(palette)], width=3),
        ))
    curve_fig.add_hline(
        y=50, line_dash="dot", line_color="#9aa5a0",
        annotation_text="half stopped",
    )
    curve_fig.update_layout(
        height=440, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Weeks since adoption",
        yaxis_title="Still doing it (%)",
    )
    st.plotly_chart(curve_fig, width="stretch")

    st.markdown("#### The classes")
    for key in list_action_classes():
        summary = class_summary(key)
        with st.container(border=True):
            st.markdown(
                f"**{summary['label']}** — median "
                f"{summary['median_weeks']:,.0f} weeks "
                f"({summary['median_months']:,.1f} months), shape "
                f"k = {summary['shape']:.2f} "
                f"({summary['hazard_direction']} hazard)"
            )
            share = st.columns(3)
            share[0].metric("At 13 weeks",
                            f"{summary['survival_at_13_weeks'] * 100:.0f}%")
            share[1].metric("At 26 weeks",
                            f"{summary['survival_at_26_weeks'] * 100:.0f}%")
            share[2].metric("At 52 weeks",
                            f"{summary['survival_at_52_weeks'] * 100:.0f}%")
            st.caption(summary["note"])
            st.caption(f"_Evidence:_ {summary['evidence']}")

    st.info(
        "A shape below one means the hazard falls: the risk of stopping is "
        "highest early and improves for anyone who gets past it. That is the "
        "effect worth telling a user about, and a constant-hazard model cannot "
        "represent it."
    )


# ---------------------------------------------------------------------------
# Your plan over time
# ---------------------------------------------------------------------------
with tab_plan:
    st.markdown("### What survives, and for how long")

    points = portfolio["horizon_points"]
    retention = go.Figure()
    retention.add_trace(go.Scatter(
        x=[point["months"] for point in points],
        y=[point["surviving_weekly_saving"] for point in points],
        mode="lines+markers", name="Expected",
        line=dict(color="#2e7d63", width=3),
    ))
    retention.add_hline(
        y=portfolio["assumed_weekly_saving"],
        line_dash="dash", line_color="#b4553f",
        annotation_text="what the app currently assumes",
    )
    retention.update_layout(
        height=400, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Months", yaxis_title="Weekly saving (kg CO2e)",
    )
    st.plotly_chart(retention, width="stretch")

    st.dataframe(
        pd.DataFrame([
            {
                "Horizon": f"{point['months']:.0f} months",
                "Assumed": point["assumed_weekly_saving"],
                "Expected": point["surviving_weekly_saving"],
                "Retained": f"{point['retained_share'] * 100:.0f}%",
            }
            for point in points
        ]),
        width="stretch", hide_index=True,
    )

    st.markdown("#### Where the risk sits")
    st.dataframe(
        pd.DataFrame([
            {
                "Action": row["name"],
                "Class": row["class_label"],
                "Weekly saving": row["weekly_saving"],
                "Chance of surviving a year":
                    f"{row['survival_at_52'] * 100:.0f}%",
                "Expected at 12 months": row["surviving_at_52"],
            }
            for row in portfolio["actions"]
        ]),
        width="stretch", hide_index=True,
    )

    if portfolio["fragile_actions"]:
        st.warning(
            f"{portfolio['fragile_share_of_plan'] * 100:.0f}% of this plan's "
            f"projected saving sits in actions with under a 40% chance of "
            f"lasting a year. That is not a reason to drop them — it is a "
            f"reason to build re-engagement in rather than assume it."
        )


# ---------------------------------------------------------------------------
# When to nudge
# ---------------------------------------------------------------------------
with tab_timing:
    st.markdown("### When a prompt would actually change something")
    st.markdown(
        "The hazard peaks at week one for every effortful class, so prompting "
        "at the peak reaches people who have barely started. What a "
        "notification schedule needs is the window carrying the most lapses, "
        "which is a different quantity."
    )

    windows = []
    for key in list_action_classes():
        window = reengagement_window(key)
        windows.append({
            "Class": ACTION_CLASSES[key]["label"],
            "Peak hazard week": window["peak_week"] or "—",
            "Window": (
                f"weeks {window['window'][0]}–{window['window'][1]}"
                if window["window"] else "no useful window"
            ),
            "Lapses inside window":
                f"{window['share_in_window'] * 100:.0f}%",
            "Lapsing within 2 years":
                f"{window['share_lapsing_in_horizon'] * 100:.0f}%",
        })
    st.dataframe(pd.DataFrame(windows), width="stretch", hide_index=True)

    st.markdown("#### For the actions in your plan")
    for option in options:
        window = reengagement_window(option["action_class"])
        with st.container(border=True):
            st.markdown(f"**{option['name']}**")
            st.caption(window["note"])

    st.caption(
        "The structural class has no window because almost nothing lapses. "
        "Scheduling a nudge for it would reach people who were never going to "
        "stop, which is how notification fatigue starts."
    )


# ---------------------------------------------------------------------------
# Your own history
# ---------------------------------------------------------------------------
with tab_history:
    st.markdown("### Estimating from what you have actually done")
    st.caption(
        "One row per action you have adopted. Duration is how long it ran. "
        "Tick *still going* for anything that has not stopped — that is a "
        "censored observation, not a lapse, and counting it as a lapse would "
        "bias the estimate downward."
    )

    default_history = pd.DataFrame([
        {"Action": "Cycling to work", "Weeks": 6.0, "Still going": False},
        {"Action": "Meat-free Mondays", "Weeks": 14.0, "Still going": False},
        {"Action": "Washing at 30", "Weeks": 30.0, "Still going": True},
        {"Action": "Batch cooking", "Weeks": 9.0, "Still going": False},
        {"Action": "Line drying", "Weeks": 22.0, "Still going": True},
    ])
    history_edit = st.data_editor(
        default_history, num_rows="dynamic", width="stretch",
        key="ap_history",
    )

    events = []
    for _, row in history_edit.iterrows():
        weeks = row.get("Weeks")
        if weeks is None or (isinstance(weeks, float) and pd.isna(weeks)):
            continue
        events.append({
            "duration_weeks": float(weeks),
            "censored": bool(row.get("Still going")),
        })

    if not events:
        st.info("Add at least one adoption to estimate from.")
    else:
        try:
            empirical = kaplan_meier(events)
        except PersistenceError as error:
            st.error(str(error))
        else:
            h1, h2, h3 = st.columns(3)
            h1.metric("Adoptions", f"{empirical['events']}")
            h2.metric("Lapses observed", f"{empirical['observed_lapses']}")
            h3.metric(
                "Median duration",
                f"{empirical['median_weeks']:.0f} weeks"
                if empirical["median_weeks"] is not None else "not reached",
            )

            if empirical["fully_censored"]:
                st.success(
                    "Nothing in this history has lapsed, so the estimated "
                    "survival is 100%. A version of this that counted "
                    "still-running actions as failures would have reported "
                    "the opposite."
                )

            km_fig = go.Figure()
            km_fig.add_trace(go.Scatter(
                x=[point["week"] for point in empirical["curve"]],
                y=[point["survival"] * 100 for point in empirical["curve"]],
                mode="lines+markers", line_shape="hv",
                name="Your history", line=dict(color="#2e7d63", width=3),
            ))

            reference_class = st.selectbox(
                "Compare against class",
                list_action_classes(),
                index=list_action_classes().index("daily_effort"),
                format_func=lambda k: ACTION_CLASSES[k]["label"],
                key="ap_reference",
            )
            prior_points = survival_curve(reference_class, horizon_weeks=104)
            km_fig.add_trace(go.Scatter(
                x=[point["week"] for point in prior_points],
                y=[point["survival"] * 100 for point in prior_points],
                mode="lines", name="Class prior",
                line=dict(color="#5b6b78", width=2, dash="dash"),
            ))
            km_fig.update_layout(
                height=400, margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="Weeks", yaxis_title="Still going (%)",
            )
            st.plotly_chart(km_fig, width="stretch")

            blend = blend_with_prior(empirical, reference_class)
            b1, b2, b3 = st.columns(3)
            b1.metric("Class prior at 52w",
                      f"{blend['prior_survival'] * 100:.0f}%")
            b2.metric("Your history at 52w",
                      f"{blend['empirical_survival'] * 100:.0f}%")
            b3.metric("Blended",
                      f"{blend['blended_survival'] * 100:.0f}%")
            st.caption(blend["note"])

        st.markdown("#### Seasonal or abandoned?")
        st.caption(
            "Months in which actions lapsed. A cluster around the same time of "
            "year is a seasonal gap, not an exit, and the two produce very "
            "different expected savings from identical data."
        )
        month_input = st.text_input(
            "Lapse months (1-12, comma separated)",
            value="11, 12, 1, 12, 11", key="ap_months",
        )
        months = []
        for chunk in month_input.split(","):
            chunk = chunk.strip()
            if chunk:
                try:
                    months.append(int(chunk))
                except ValueError:
                    continue
        if months:
            try:
                season = seasonal_reactivation(months)
            except PersistenceError as error:
                st.error(str(error))
            else:
                (st.warning if season["seasonal"] else st.info)(season["note"])


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Save this plan")
    name = st.text_input("Name", value="Action plan", key="ap_save_name")
    if st.button("Save", key="ap_save"):
        try:
            save_plan(user_id, name, portfolio)
            st.success("Saved.")
        except PersistenceError as error:
            st.error(str(error))

    st.markdown("---")
    saved = get_plans(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for entry in saved:
            with st.container(border=True):
                head, action = st.columns([5, 1])
                with head:
                    st.markdown(f"**{entry['name']}** · {entry['created_at']}")
                    st.caption(
                        f"Assumed {entry['assumed_weekly_saving']:,.1f} kg/week "
                        f"· expected at two years "
                        f"{entry['expected_year_two_saving']:,.1f} kg/week"
                    )
                with action:
                    if st.button("Delete", key=f"ap_del_{entry['id']}"):
                        if delete_plan(user_id, entry["id"]):
                            st.rerun()

st.markdown("---")
st.caption(
    "Method: Weibull survival by action class, Kaplan-Meier with right "
    "censoring for empirical history, circular concentration for seasonality. "
    "Related: src.carbon.permanence_accounting.py, "
    "src.carbon.abatement_curve.py, src.utils.rebound_effect.py."
)
