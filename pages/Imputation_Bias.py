"""Zero is not a placeholder. It is an assertion that the activity did not happen.

`data_quality.detect_missing_fields` finds the gaps. Everything downstream
fills them with zero, which reads a forgotten flight entry as a flight not
taken and therefore makes every incomplete assessment look better than a
complete one.

This page diagnoses why the data is missing, imputes under a stated mechanism,
and carries the imputation's own uncertainty through to the answer instead of
discarding it.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.data.imputation_bias import (
    DEFAULT_IMPUTATIONS,
    MISSINGNESS_CEILING,
    STRATEGIES,
    ImputationError,
    compare_periods,
    compare_strategies,
    default_fields,
    delete_analysis,
    delta_sensitivity,
    get_analyses,
    get_imputation_notes,
    mechanism_report,
    missingness_map,
    normalise_records,
    sample_history,
    save_analysis,
    summarise,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🕳️ Missing Data & Imputation Bias</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "A gap that gets filled with zero is not a gap that was handled. It is a "
    "question answered in the one direction that always lowers the footprint."
)

with st.expander("Three mechanisms, three different answers"):
    st.markdown(
        """
**MCAR — missing completely at random.** The gaps carry no information.
Dropping incomplete rows is unbiased and any sensible fill works.

**MAR — missing at random given what was observed.** Whether a field is
missing depends on things that *were* recorded. Recoverable: condition on
those things and impute.

**MNAR — missing not at random.** Whether a field is missing depends on the
value that is missing. Somebody skips the flights question in the months they
flew. **This is not testable from observed data**, by definition, and any tool
claiming to detect it is wrong. The honest response is a sensitivity analysis:
state a departure, and report how large it has to be before the conclusion
changes.

The app currently treats all three identically, which means it treats the
dangerous one as though it were the harmless one.

---

**Why single imputation is not the fix.** Mean fill and last-value-carried-
forward remove the bias in the point estimate and destroy the variance. One
filled value becomes a measured value, so the imputed series looks *more*
certain than the measured one.

Rubin's rules keep the part that single imputation throws away:

    T = U_bar + (1 + 1/m) B

where `U_bar` is the average within-imputation variance and `B` is the variance
*between* the m imputations. The fraction of missing information that falls out
of `B` is the number that says how much of a footprint is measured and how much
is model.
        """
    )

tab_map, tab_mechanism, tab_strategies, tab_sensitivity = st.tabs(
    ["Missingness map", "Mechanism", "Fill strategies", "MNAR sensitivity & trend"]
)

fields = default_fields()


def _load_rows():
    """Synthetic history so the page is usable before real data is wired in."""
    columns = st.columns(3)
    months = columns[0].slider("Months of history", 8, 48, 24, key="rows_months")
    rate = columns[1].slider("Missingness rate", 0.05, 0.5, 0.2, step=0.05, key="rows_rate")
    mechanism = columns[2].selectbox(
        "Mechanism",
        options=["mnar", "mcar"],
        format_func=lambda value: {
            "mnar": "MNAR — skipped in the months it mattered",
            "mcar": "MCAR — skipped at random",
        }[value],
        key="rows_mechanism",
    )
    raw = sample_history(months, rate, mnar=(mechanism == "mnar"))
    return normalise_records(raw, fields), raw


with tab_map:
    st.subheader("Where the gaps are")
    rows, raw = _load_rows()
    st.session_state["imp_rows"] = rows

    try:
        overview = missingness_map(rows, fields)
    except ImputationError as error:
        st.error(str(error))
        st.stop()

    head = st.columns(4)
    head[0].metric("Records", "%d" % overview["records"])
    head[1].metric("Complete", "%d" % overview["complete_cases"])
    head[2].metric("Values missing", "%.0f%%" % (overview["overall_rate"] * 100.0))
    head[3].metric("Patterns", "%d" % overview["pattern_count"])

    if overview["overall_rate"] > MISSINGNESS_CEILING:
        st.error(
            "Above the %.0f%% ceiling — a pooled estimate here would be mostly "
            "model and barely data." % (MISSINGNESS_CEILING * 100.0)
        )

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Field": entry["name"],
                    "Observed": entry["observed"],
                    "Missing": entry["missing"],
                    "Rate": "%.0f%%" % (entry["rate"] * 100.0),
                }
                for entry in overview["per_field"]
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("**Patterns**")
    st.caption(
        "A 1 means observed, a 0 means missing, in field order. Fields that "
        "always vanish together usually vanish for one reason, and that is "
        "often more diagnostic than any test statistic."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Pattern": entry["pattern"],
                    "Records": entry["records"],
                    "Share": "%.0f%%" % (entry["share"] * 100.0),
                }
                for entry in overview["patterns"]
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    if overview["monotone"]:
        st.info(
            "Missingness is monotone — the fields can be ordered so the gaps "
            "nest. That admits a simpler sequential imputation."
        )
    else:
        st.caption(
            "Missingness is arbitrary rather than monotone, so imputation has "
            "to condition on whatever happens to be present in each row."
        )

with tab_mechanism:
    st.subheader("Why is it missing")
    rows = st.session_state.get("imp_rows")
    if not rows:
        st.info("Load a history on the first tab.")
    else:
        try:
            report = mechanism_report(rows, fields)
        except ImputationError as error:
            st.error(str(error))
            report = None

        if report:
            mcar = report["mcar"]
            if mcar["verdict"] == "mcar_rejected":
                st.warning(mcar["headline"])
            elif mcar["verdict"] == "untestable":
                st.info(mcar["headline"])
            else:
                st.success(mcar["headline"])

            st.markdown("**Is the missingness predictable from what we did record?**")
            for entry in report["mar"]:
                with st.expander(
                    "%s — %d records missing (%.0f%%)"
                    % (entry["target"], entry["missing_records"], entry["missing_rate"] * 100.0)
                ):
                    st.write(entry["headline"])
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "Predictor": item["name"],
                                    "Mean when present": round(item["mean_when_present"], 1),
                                    "Mean when missing": round(item["mean_when_missing"], 1),
                                    "Std. difference": round(item["standardised_difference"], 2),
                                    "p": round(item["p_value"], 4),
                                    "Informative": "yes" if item["informative"] else "no",
                                }
                                for item in entry["predictors"]
                            ]
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

            st.error(report["mnar"]["headline"])

with tab_strategies:
    st.subheader("What the choice of fill is worth")
    rows = st.session_state.get("imp_rows")
    if not rows:
        st.info("Load a history on the first tab.")
    else:
        imputations = st.slider(
            "Imputations (m)", 2, 100, DEFAULT_IMPUTATIONS, step=2,
            help="More imputations stabilise the between-imputation variance.",
        )
        if st.button("Compare strategies", type="primary"):
            try:
                comparison = compare_strategies(rows, fields, imputations=imputations)
                st.session_state["imp_comparison"] = comparison
            except ImputationError as error:
                st.error(str(error))

        comparison = st.session_state.get("imp_comparison")
        if comparison:
            pooled = comparison["pooled"]
            head = st.columns(3)
            head[0].metric("Pooled estimate", "%.0f kg" % pooled["estimate"])
            head[1].metric(
                "Zero-fill bias",
                "%+.0f kg" % comparison["zero_fill_bias"],
            )
            head[2].metric(
                "Missing information",
                "%.0f%%" % (pooled["fraction_missing_information"] * 100.0),
            )

            verdict = pooled["information_verdict"]
            if verdict["level"] == "high":
                st.error("**%s** %s" % (verdict["headline"], verdict["detail"]))
            elif verdict["level"] == "moderate":
                st.warning("**%s** %s" % (verdict["headline"], verdict["detail"]))
            else:
                st.success("**%s** %s" % (verdict["headline"], verdict["detail"]))

            frame = pd.DataFrame(
                [
                    {
                        "Strategy": entry["label"],
                        "Estimate": round(entry["estimate"], 0),
                        "Std. error": round(entry["standard_error"], 1),
                        "vs pooled": "%+.0f kg (%+.1f%%)"
                        % (entry["difference_from_pooled"], entry["percent_from_pooled"]),
                        "Problem": entry["note"],
                    }
                    for entry in comparison["results"]
                ]
            )
            st.dataframe(frame, use_container_width=True, hide_index=True)

            figure = go.Figure()
            figure.add_trace(
                go.Bar(
                    x=[entry["label"] for entry in comparison["results"]],
                    y=[entry["estimate"] for entry in comparison["results"]],
                    error_y={
                        "type": "data",
                        "array": [
                            1.96 * entry["standard_error"] for entry in comparison["results"]
                        ],
                    },
                    marker_color=[
                        "#C1443C" if entry["strategy"] == "zero" else "#2E86AB"
                        for entry in comparison["results"]
                    ],
                )
            )
            figure.update_layout(
                title="Same data, six answers. Only the last one carries its own uncertainty.",
                yaxis_title="Mean footprint per record (kg CO2e)",
                height=430,
            )
            st.plotly_chart(figure, use_container_width=True)

            for note in get_imputation_notes(comparison):
                st.markdown("- %s" % note)

            st.caption(summarise(comparison))

            label = st.text_input("Label for this analysis", value="assessment history")
            if st.button("Save analysis"):
                if save_analysis(user_id, comparison, label):
                    st.success("Saved.")
                else:
                    st.info("Could not save — storage unavailable.")

with tab_sensitivity:
    st.subheader("How wrong would the imputation model have to be?")
    st.caption(
        "MNAR cannot be tested. It can be bounded: shift the imputed values by "
        "a stated amount and find the point at which the conclusion changes. A "
        "tipping point of 5% means the conclusion is fragile; one of 200% means "
        "it is not."
    )
    rows = st.session_state.get("imp_rows")
    if not rows:
        st.info("Load a history on the first tab.")
    else:
        if st.button("Run delta sensitivity"):
            try:
                sensitivity = delta_sensitivity(
                    rows, fields, deltas=(0.0, 0.1, 0.25, 0.5, 0.75, 1.0), imputations=15
                )
                st.session_state["imp_sensitivity"] = sensitivity
            except ImputationError as error:
                st.error(str(error))

        sensitivity = st.session_state.get("imp_sensitivity")
        if sensitivity:
            st.markdown("**%s**" % sensitivity["headline"])
            curve = go.Figure()
            curve.add_trace(
                go.Scatter(
                    x=[entry["delta"] * 100.0 for entry in sensitivity["curve"]],
                    y=[entry["estimate"] for entry in sensitivity["curve"]],
                    mode="lines+markers",
                    name="Pooled estimate",
                    line={"color": "#2E86AB"},
                )
            )
            curve.add_hline(
                y=sensitivity["threshold"],
                line_dash="dash",
                annotation_text="conclusion threshold",
            )
            curve.update_layout(
                title="Estimate against an assumed MNAR departure",
                xaxis_title="Imputed values assumed higher by (%)",
                yaxis_title="Mean footprint (kg CO2e)",
                height=400,
            )
            st.plotly_chart(curve, use_container_width=True)

            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Delta": "%+.0f%%" % (entry["delta"] * 100.0),
                            "Estimate": round(entry["estimate"], 0),
                            "95% interval": "%.0f – %.0f" % (entry["lower"], entry["upper"]),
                            "Shift": "%+.0f kg" % entry["shift_from_base"],
                        }
                        for entry in sensitivity["curve"]
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.divider()
        st.markdown("**Year-on-year change, with the imputation uncertainty carried through**")
        st.caption(
            "A change entirely inside the pooled interval is reported as not "
            "distinguishable, rather than as progress."
        )
        if st.button("Compare two halves of the history"):
            midpoint = len(rows) // 2
            try:
                periods = compare_periods(
                    rows[:midpoint], rows[midpoint:], fields, imputations=15
                )
                if periods["distinguishable"]:
                    st.success(periods["headline"])
                else:
                    st.warning(periods["headline"])
                st.write(
                    "Earlier %.0f kg (SE %.0f) — later %.0f kg (SE %.0f)"
                    % (
                        periods["earlier"]["estimate"],
                        periods["earlier"]["standard_error"],
                        periods["later"]["estimate"],
                        periods["later"]["standard_error"],
                    )
                )
            except ImputationError as error:
                st.error(str(error))

st.divider()
st.subheader("Saved analyses")
saved = get_analyses(user_id)
if not saved:
    st.info("Nothing saved yet.")
for record in saved:
    with st.expander(
        "%s — pooled %.0f kg, zero fill %+.0f kg"
        % (record["label"], record["pooled_estimate"], record["zero_fill_bias"])
    ):
        st.write(
            "Missing information: %.0f%%"
            % (record["fraction_missing_information"] * 100.0)
        )
        st.write("Records: %d" % record["records"])
        payload = record["payload"]
        if payload.get("headline"):
            st.write(payload["headline"])
        st.write("Saved: %s" % record["created_at"])
        if st.button("Delete", key="imp_delete_%s" % record["id"]):
            delete_analysis(user_id, record["id"])
            st.rerun()
