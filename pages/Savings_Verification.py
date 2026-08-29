"""Did the action cause the saving, or did the season?

`intervention_effectiveness.py` computes a before-and-after difference and says
in its own docstring that it is not a causal claim. It is right. The trouble is
that the number is still the one on the screen, and on a seasonal series it
credits spring to whatever the user happened to log in April.

This page uses a comparison group, tests the assumption that makes a comparison
group valid, and reports standard errors that survive the fact that consecutive
months are correlated.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.utils.savings_verification import (
    DEFAULT_ALPHA,
    VerificationError,
    build_panel,
    delete_verification,
    durbin_watson,
    estimate_did,
    event_study,
    get_verifications,
    get_verification_notes,
    minimum_detectable_effect,
    option_c_regression,
    parallel_trends,
    placebo_test,
    save_verification,
    seasonal_panel,
    single_unit_series,
    summarise,
    verify,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🔬 Savings Verification</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Before-and-after measures the intervention plus the season plus the trend "
    "plus whatever else changed that month, and hands the whole sum to the "
    "action that was logged."
)

with st.expander("What a comparison group buys, and what it costs"):
    st.markdown(
        """
**The confounders are larger than the effect.** On heating-dominated
consumption the seasonal swing routinely exceeds the intervention by a factor
of several. A thermostat installed in April and evaluated in May against March
will look excellent whatever it does.

**Difference-in-differences.** Treated units against control units, before
against after. The controls absorb everything common to both — season, weather,
tariff, national trend — and what survives is the part the intervention
plausibly did.

**The assumption is checkable, so it gets checked first.** DiD is valid only if
the two arms were moving in parallel beforehand. If they were not, they were
already on different paths and DiD attributes that divergence to the
intervention. A failed test blocks the estimate here rather than appearing as a
caveat under it.

**Regression to the mean is why this matters most for the motivated.** People
adopt interventions after a bad month. A bad month is partly noise, and noise
reverts. Before-and-after therefore overstates savings for exactly the users
most likely to be using this feature.

**Serial correlation.** Consecutive months are correlated, so twelve
households observed for twelve months are not a hundred and forty-four
independent observations. Collapsing each unit to one pre and one post mean
and clustering by unit removes the problem rather than modelling it.

**Minimum detectable effect.** A user with six months of noisy data cannot
detect a 5% saving no matter what they install. "No significant change" and
"this design could never have found one" look identical on a dashboard and mean
entirely different things, so both are always reported.
        """
    )

tab_design, tab_effect, tab_event, tab_option_c = st.tabs(
    ["Design & assumption", "Effect", "Event study & placebo", "Single unit (Option C)"]
)


def _panel_controls(prefix):
    columns = st.columns(4)
    treated = columns[0].slider("Treated units", 2, 40, 12, key="%s_treated" % prefix)
    control = columns[1].slider("Control units", 2, 40, 12, key="%s_control" % prefix)
    effect = columns[2].slider("True effect", -200.0, 0.0, -40.0, step=5.0, key="%s_effect" % prefix)
    rho = columns[3].slider(
        "Serial correlation", 0.0, 0.95, 0.7, step=0.05, key="%s_rho" % prefix,
        help="How much this month's shock carries into next month.",
    )
    return seasonal_panel(
        treated_units=treated,
        control_units=control,
        true_effect=effect,
        autocorrelation=rho,
    )


with tab_design:
    st.subheader("Were the two arms moving together beforehand?")
    observations = _panel_controls("design")
    st.session_state["sv_observations"] = observations

    try:
        panel = build_panel(observations, 14)
    except VerificationError as error:
        st.error(str(error))
        st.stop()

    trends = parallel_trends(panel)
    if trends["passes"]:
        st.success(trends["headline"])
    else:
        st.error(trends["headline"])

    st.caption(
        "The threshold here is p = 0.10 rather than 0.05, on purpose. This is a "
        "test the analysis wants to pass, so a lenient threshold makes it "
        "easier to proceed — which is the opposite of what a validity check is "
        "for. The stricter threshold blocks more analyses, and that is the "
        "intended direction of the error."
    )

    by_period = {}
    for entry in panel["units"]:
        for item in entry["readings"]:
            bucket = by_period.setdefault(item["period"], {"treated": [], "control": []})
            bucket["treated" if entry["treated"] else "control"].append(item["value"])

    periods = sorted(by_period)
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=periods,
            y=[sum(by_period[p]["treated"]) / len(by_period[p]["treated"]) for p in periods],
            mode="lines+markers",
            name="Treated",
            line={"color": "#C1443C"},
        )
    )
    figure.add_trace(
        go.Scatter(
            x=periods,
            y=[sum(by_period[p]["control"]) / len(by_period[p]["control"]) for p in periods],
            mode="lines+markers",
            name="Control",
            line={"color": "#2E86AB"},
        )
    )
    figure.add_vline(x=14, line_dash="dash", annotation_text="intervention")
    figure.update_layout(
        title="Both arms fall in spring. Only one of them installed anything.",
        xaxis_title="Period",
        yaxis_title="Consumption",
        height=430,
    )
    st.plotly_chart(figure, use_container_width=True)

    head = st.columns(3)
    head[0].metric("Treated pre-slope", "%.2f / period" % trends["treated_slope"])
    head[1].metric("Control pre-slope", "%.2f / period" % trends["control_slope"])
    head[2].metric(
        "p",
        "%.3f" % trends["p_value"] if trends["p_value"] is not None else "—",
    )

with tab_effect:
    st.subheader("The estimate, and what it would have been without a control group")
    observations = st.session_state.get("sv_observations")
    if not observations:
        st.info("Set up a design on the first tab.")
    else:
        alpha = st.select_slider(
            "Significance level", options=[0.01, 0.05, 0.10], value=DEFAULT_ALPHA
        )
        if st.button("Estimate", type="primary"):
            try:
                report = verify(observations, 14, alpha=alpha)
                st.session_state["sv_report"] = report
            except VerificationError as error:
                st.error(str(error))

        report = st.session_state.get("sv_report")
        if report:
            result = report["did"]
            if not result.get("usable"):
                st.error(result["headline"])
                st.info(
                    "No effect is reported because the design cannot support "
                    "one. That is the result, not a missing result."
                )
            else:
                head = st.columns(4)
                head[0].metric("DiD estimate", "%.1f" % result["effect"])
                head[1].metric(
                    "Before/after would say", "%.1f" % result["before_after_estimate"]
                )
                head[2].metric("p", "%.4f" % result["p_value"])
                head[3].metric(
                    "Min. detectable",
                    "%.1f" % result["minimum_detectable_effect"]["effect"],
                )

                st.warning(
                    "**%.0f%% of the before-and-after figure is not the "
                    "intervention.** It is the season, the trend, and everything "
                    "else the comparison group absorbed."
                    % abs(result["confounded_share"])
                )

                comparison = go.Figure()
                comparison.add_trace(
                    go.Bar(
                        x=["Before/after", "Difference-in-differences"],
                        y=[result["before_after_estimate"], result["effect"]],
                        marker_color=["#C1443C", "#2E86AB"],
                        error_y={
                            "type": "data",
                            "array": [0.0, result["effect"] - result["lower"]],
                        },
                    )
                )
                comparison.update_layout(
                    title="Same data, two designs",
                    yaxis_title="Estimated change",
                    height=400,
                )
                st.plotly_chart(comparison, use_container_width=True)

                st.markdown("**Standard errors**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Method": "Clustered by unit (used)",
                                "Std. error": round(result["clustered_standard_error"], 2),
                                "What it assumes": "Each household is one observation.",
                            },
                            {
                                "Method": "Every reading independent",
                                "Std. error": round(result["unclustered_standard_error"], 2),
                                "What it assumes": "12 households × 12 months = 144 observations.",
                            },
                            {
                                "Method": "Raw four-group comparison",
                                "Std. error": round(result["naive_standard_error"], 2),
                                "What it assumes": "No period effects — the season counts as noise.",
                            },
                        ]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )
                st.caption(
                    "The clustered error is %.1fx the unclustered one. Some gap "
                    "remains even with independent shocks, because every "
                    "post-period deviation shares the same estimated baseline; "
                    "the size of the gap is the diagnostic."
                    % result["clustered_over_unclustered"]
                )

                for note in get_verification_notes(report):
                    st.markdown("- %s" % note)

                st.caption(summarise(report))

                label = st.text_input("Label", value="thermostat rollout")
                if st.button("Save verification"):
                    if save_verification(user_id, report, label):
                        st.success("Saved.")
                    else:
                        st.info("Could not save — storage unavailable.")

with tab_event:
    st.subheader("When the effect appears, and whether it lasts")
    report = st.session_state.get("sv_report")
    if not report or "event_study" not in report:
        st.info("Run an estimate first.")
    else:
        study = report["event_study"]
        st.markdown("**%s**" % study["headline"])

        figure = go.Figure()
        figure.add_trace(
            go.Scatter(
                x=[point["relative"] for point in study["points"]],
                y=[point["effect"] for point in study["points"]],
                mode="lines+markers",
                marker={
                    "color": [
                        "#2E86AB" if point["post"] else "#9AA5B1"
                        for point in study["points"]
                    ],
                    "size": 9,
                },
                line={"color": "#2E86AB"},
                name="Treated − control, normalised",
            )
        )
        figure.add_vline(x=-0.5, line_dash="dash", annotation_text="intervention")
        figure.add_hline(y=0.0, line_color="#9AA5B1")
        figure.update_layout(
            title="Effect by period relative to the intervention",
            xaxis_title="Periods from intervention",
            yaxis_title="Effect",
            height=430,
        )
        st.plotly_chart(figure, use_container_width=True)

        if study["anticipation_warning"]:
            st.error(
                "A sizeable gap opens *before* the intervention date. That is "
                "anticipation or a mis-dated event, and either way part of the "
                "measured effect is not the intervention."
            )
        else:
            st.success(
                "Nothing much happens before the intervention date, which is "
                "what should happen."
            )

        st.divider()
        placebo = report.get("placebo", {})
        if placebo.get("ran"):
            if placebo["passed"]:
                st.success(placebo["headline"])
            else:
                st.error(placebo["headline"])
        else:
            st.info(placebo.get("headline", "Placebo not run."))

with tab_option_c:
    st.subheader("One meter, no comparison group")
    st.caption(
        "IPMVP Option C: fit a baseline on the pre-period drivers, project it "
        "into the reporting period, and take the avoided consumption as the "
        "residual. This is the weaker design and is labelled as one — it "
        "cannot separate the intervention from anything else that changed at "
        "the same time and does not correlate with the drivers."
    )

    if st.button("Run Option C"):
        series = single_unit_series()
        try:
            result = option_c_regression(series, 18, ["degree_days"])
            st.session_state["sv_option_c"] = result
        except VerificationError as error:
            st.error(str(error))

    result = st.session_state.get("sv_option_c")
    if result:
        head = st.columns(4)
        head[0].metric("Total avoided", "%.0f" % result["total_avoided"])
        head[1].metric("Per period", "%.1f" % result["mean_avoided"])
        head[2].metric("Baseline R²", "%.3f" % result["r_squared"])
        head[3].metric("CV(RMSE)", "%.1f%%" % result["cv_rmse"])

        st.info(result["headline"])

        if result["autocorrelated"]:
            st.warning(
                "Durbin-Watson %.2f — the baseline residuals are "
                "autocorrelated, so a naive standard error on this fit would be "
                "too narrow. The interval above uses a Newey-West HAC variance "
                "and includes the uncertainty of the baseline fit itself, which "
                "routine M&V write-ups usually omit."
                % result["durbin_watson"]
            )
        else:
            st.success(
                "Durbin-Watson %.2f — no strong autocorrelation in the baseline "
                "residuals." % result["durbin_watson"]
            )

        figure = go.Figure()
        figure.add_trace(
            go.Bar(
                x=list(range(len(result["avoided_per_period"]))),
                y=result["avoided_per_period"],
                marker_color="#2E86AB",
                name="Avoided per period",
            )
        )
        figure.update_layout(
            title="Projected baseline minus actual, by reporting period",
            xaxis_title="Reporting period",
            yaxis_title="Avoided consumption",
            height=400,
        )
        st.plotly_chart(figure, use_container_width=True)

st.divider()
st.subheader("Saved verifications")
saved = get_verifications(user_id)
if not saved:
    st.info("Nothing saved yet.")
for record in saved:
    with st.expander(
        "%s — %s"
        % (
            record["label"],
            "effect %.1f (p=%.3f)" % (record["effect"], record["p_value"])
            if record["usable"] and record["effect"] is not None
            else "not usable",
        )
    ):
        st.write("Design: %s" % record["design"])
        payload = record["payload"]
        if payload.get("parallel_trends", {}).get("headline"):
            st.write(payload["parallel_trends"]["headline"])
        st.write("Saved: %s" % record["created_at"])
        if st.button("Delete", key="sv_delete_%s" % record["id"]):
            delete_verification(user_id, record["id"])
            st.rerun()
