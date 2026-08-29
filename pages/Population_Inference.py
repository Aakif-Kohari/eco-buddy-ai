"""The community average is a convenience sample wearing a population's clothes.

`get_leaderboard()` ranks whoever is in the database. `community_dashboard.py`
reports community totals. The people in the database are people who downloaded
a carbon footprint app and finished an assessment, which is about the most
efficiently self-selected group imaginable for this particular variable.

This page weights that sample back toward stated population marginals, reports
the effective sample size the weighting costs, bounds the part it cannot reach,
and declines to publish aggregates that have not earned it.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.community.population_inference import (
    DEFAULT_PARTICIPATION_CORRELATION,
    DEFAULT_TRIM_RATIO,
    MIN_EFFECTIVE_SAMPLE,
    PopulationError,
    build_variable,
    compare_groups,
    coverage_holes,
    delete_estimate,
    demo_respondents,
    demo_variables,
    design_effect,
    estimate_population_mean,
    get_estimates,
    get_inference_notes,
    percentile_of,
    rake,
    representation_gaps,
    save_estimate,
    summarise,
    trim_weights,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>⚖️ Population Inference</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "What the community average would be if the community were the population "
    "rather than the people who happened to sign up."
)

with st.expander("Why an unweighted community average is not an average of anything"):
    st.markdown(
        """
**Participation correlates with the outcome.** People who install a carbon
footprint app are younger, more urban, more likely to live in flats and
considerably more climate-engaged than the population they implicitly stand in
for. Every one of those correlates with footprint — several in opposite
directions, which is worse, because it means the bias cannot even be assumed
to be conservative.

**Sample size is reported as a count, which is the wrong number.** Twenty
responses from one housing type are not twenty independent observations about
a mixed neighbourhood. Kish's design effect and the effective sample size that
follows from it are what decide whether a comparison means anything:

    deff  = n · Σw² / (Σw)²
    n_eff = n / deff

**Weighting fixes what was observed, and nothing else.** If detached houses are
30% of the population and 8% of respondents, weighting brings them up to 30%.
It does nothing about climate engagement, because engagement was never
collected — so that residual is *bounded* here and shown as a range around the
corrected figure, rather than being left out and forgotten.

**Some things are not fixable at all.** A stratum with a population share and
no respondents is a coverage hole. Dropping it is what turns "we have no data
on detached rural houses" into "detached rural houses are like everyone else",
which is a claim nobody made and everybody reads.
        """
    )

tab_sample, tab_weights, tab_estimate, tab_groups = st.tabs(
    ["The sample", "Weights & design effect", "Estimate", "Comparing groups"]
)

variables = demo_variables()


def _load_sample():
    columns = st.columns(2)
    count = columns[0].slider("Respondents", 20, 400, 120, step=10, key="pop_count")
    seed = columns[1].number_input("Seed", value=20241015, step=1, key="pop_seed")
    return demo_respondents(int(count), int(seed))


with tab_sample:
    st.subheader("Who actually answered")
    respondents = _load_sample()
    st.session_state["pop_respondents"] = respondents

    gaps = representation_gaps(respondents, variables)
    frame = pd.DataFrame(
        [
            {
                "Variable": entry["variable"],
                "Level": entry["level"],
                "Respondents": entry["respondents"],
                "Sample": "%.0f%%" % (entry["sample_share"] * 100.0),
                "Population": "%.0f%%" % (entry["population_share"] * 100.0),
                "Gap": "%+.0f pts" % (entry["difference"] * 100.0),
            }
            for entry in gaps
        ]
    )
    st.dataframe(frame, use_container_width=True, hide_index=True)

    figure = go.Figure()
    labels = ["%s / %s" % (entry["variable"], entry["level"]) for entry in gaps]
    figure.add_trace(
        go.Bar(
            x=labels,
            y=[entry["sample_share"] * 100.0 for entry in gaps],
            name="Sample",
            marker_color="#C1443C",
        )
    )
    figure.add_trace(
        go.Bar(
            x=labels,
            y=[entry["population_share"] * 100.0 for entry in gaps],
            name="Population",
            marker_color="#2E86AB",
        )
    )
    figure.update_layout(
        barmode="group",
        title="Who signed up against who lives here",
        yaxis_title="Share (%)",
        height=430,
    )
    st.plotly_chart(figure, use_container_width=True)

    holes = coverage_holes(respondents, variables)
    if holes:
        st.error(
            "%d stratum/strata have a population share and no respondents, "
            "covering %.1f%% of the population. Weighting cannot reach them."
            % (len(holes), sum(hole["population_share"] for hole in holes) * 100.0)
        )
    else:
        st.success("Every population stratum has at least one respondent.")

with tab_weights:
    st.subheader("What the correction costs")
    respondents = st.session_state.get("pop_respondents")
    if not respondents:
        st.info("Load a sample on the first tab.")
    else:
        try:
            raked = rake(respondents, variables)
        except PopulationError as error:
            st.error(str(error))
            raked = None

        if raked:
            if raked["converged"]:
                st.success(raked["verdict"])
            else:
                st.error(raked["verdict"])

            ratio = st.slider(
                "Trim weights above this multiple of the mean",
                1.5, 12.0, DEFAULT_TRIM_RATIO, step=0.5,
                help="Extreme weights are variance disasters. Trimming caps them and reintroduces some bias.",
            )
            trimmed = trim_weights(raked["weights"], ratio)
            effect = design_effect(trimmed["weights"])

            head = st.columns(4)
            head[0].metric("Respondents", "%d" % effect["respondents"])
            head[1].metric("Design effect", "%.2f" % effect["design_effect"])
            head[2].metric("Effective sample", "%.1f" % effect["effective_sample"])
            head[3].metric("Information lost", "%.0f%%" % (effect["loss_share"] * 100.0))

            st.caption(trimmed["headline"])

            if effect["effective_sample"] < MIN_EFFECTIVE_SAMPLE:
                st.error(
                    "Effective sample below %d. Nothing computed from this "
                    "should be published as a community figure."
                    % MIN_EFFECTIVE_SAMPLE
                )

            weights_figure = go.Figure()
            weights_figure.add_trace(
                go.Histogram(
                    x=trimmed["weights"],
                    nbinsx=30,
                    marker_color="#2E86AB",
                )
            )
            weights_figure.update_layout(
                title="Weight distribution — a long right tail is where precision goes to die",
                xaxis_title="Weight (1.0 = average respondent)",
                yaxis_title="Respondents",
                height=380,
            )
            st.plotly_chart(weights_figure, use_container_width=True)

            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Variable": entry["variable"],
                            "Level": entry["level"],
                            "Target": "%.3f" % entry["target"],
                            "Achieved": "%.3f" % entry["achieved"],
                            "Residual": "%+.5f" % entry["residual"],
                        }
                        for entry in raked["residuals"]
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

with tab_estimate:
    st.subheader("The corrected figure, and what it is still missing")
    respondents = st.session_state.get("pop_respondents")
    if not respondents:
        st.info("Load a sample on the first tab.")
    else:
        columns = st.columns(3)
        trim_ratio = columns[0].slider(
            "Trim ratio", 1.5, 12.0, DEFAULT_TRIM_RATIO, step=0.5, key="est_trim"
        )
        correlation = columns[1].slider(
            "Assumed participation correlation",
            0.0, 0.10, DEFAULT_PARTICIPATION_CORRELATION, step=0.005,
            help=(
                "Correlation between signing up and footprint, after weighting. "
                "The range looks small because it is multiplied by sqrt((1-f)/f) "
                "— about 10 at a 1% sample — so 0.02 already shifts the estimate "
                "by a fifth of a standard deviation."
            ),
        )
        fraction = columns[2].select_slider(
            "Sample as a share of the population",
            options=[0.001, 0.005, 0.01, 0.05, 0.1, 0.25],
            value=0.01,
        )

        if st.button("Estimate", type="primary"):
            try:
                result = estimate_population_mean(
                    respondents,
                    variables,
                    trim_ratio=trim_ratio,
                    participation_correlation=correlation,
                    sample_fraction=fraction,
                )
                st.session_state["pop_result"] = result
            except PopulationError as error:
                st.error(str(error))

        result = st.session_state.get("pop_result")
        if result:
            head = st.columns(3)
            head[0].metric("Unweighted", "%.0f kg" % result["unweighted_mean"])
            head[1].metric(
                "Weighted",
                "%.0f kg" % result["weighted_mean"],
                delta="%+.0f" % result["correction"],
            )
            head[2].metric("Effective sample", "%.1f" % result["design"]["effective_sample"])

            if result["publishable"]:
                st.success(result["headline"])
            else:
                st.error(result["headline"])
                for refusal in result["refusals"]:
                    st.warning("Refused: %s" % refusal)

            bound = result["coverage_bias"]
            interval = go.Figure()
            interval.add_trace(
                go.Bar(
                    x=["Unweighted", "Weighted"],
                    y=[result["unweighted_mean"], result["weighted_mean"]],
                    marker_color=["#C1443C", "#2E86AB"],
                    error_y={
                        "type": "data",
                        "array": [
                            0.0,
                            result["weighted_mean"] - result["lower"],
                        ],
                    },
                )
            )
            interval.add_hrect(
                y0=bound["lower"],
                y1=bound["upper"],
                fillcolor="#F6AE2D",
                opacity=0.18,
                line_width=0,
                annotation_text="residual coverage-bias bound",
            )
            interval.update_layout(
                title="Sampling interval inside, coverage-bias bound outside",
                yaxis_title="Mean footprint (kg CO2e)",
                height=430,
            )
            st.plotly_chart(interval, use_container_width=True)

            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Statistic": "Median",
                            "Unweighted": round(result["unweighted_median"], 0),
                            "Weighted": round(result["weighted_median"], 0),
                        },
                        {
                            "Statistic": "25th percentile",
                            "Unweighted": "—",
                            "Weighted": round(result["weighted_p25"], 0),
                        },
                        {
                            "Statistic": "75th percentile",
                            "Unweighted": "—",
                            "Weighted": round(result["weighted_p75"], 0),
                        },
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

            own = st.number_input(
                "Compare a footprint against the weighted distribution",
                value=3000.0,
                step=100.0,
            )
            st.write(
                "That sits at the **%.0fth percentile** of the weighted "
                "distribution."
                % percentile_of(own, respondents, result["weights"])
            )

            for note in get_inference_notes(result):
                st.markdown("- %s" % note)

            st.caption(summarise(result))

            label = st.text_input("Label", value="community estimate")
            if st.button("Save estimate"):
                if save_estimate(user_id, result, label):
                    st.success("Saved.")
                else:
                    st.info("Could not save — storage unavailable.")

with tab_groups:
    st.subheader("Ranking, and declining to rank")
    st.caption(
        "Groups whose intervals overlap are reported as a tie. Groups below "
        "the effective-sample floor are excluded from the ranking rather than "
        "placed at a position their data cannot support."
    )
    respondents = st.session_state.get("pop_respondents")
    if not respondents:
        st.info("Load a sample on the first tab.")
    elif st.button("Split into blocks and rank"):
        blocks = {}
        block_count = 4
        for index, respondent in enumerate(respondents):
            blocks.setdefault("Block %d" % (index % block_count + 1), []).append(respondent)
        try:
            comparison = compare_groups(blocks, variables)
        except PopulationError as error:
            st.error(str(error))
            comparison = None

        if comparison:
            st.markdown("**%s**" % comparison["headline"])
            for band in comparison["bands"]:
                if band["separated"]:
                    st.markdown(
                        "**%d.** %s — %.0f kg"
                        % (band["band"], band["groups"][0], band["lowest_mean"])
                    )
                else:
                    st.markdown(
                        "**%d.** %s — *tied*, between %.0f and %.0f kg"
                        % (
                            band["band"],
                            ", ".join(band["groups"]),
                            band["lowest_mean"],
                            band["highest_mean"],
                        )
                    )
            if comparison["excluded"]:
                st.warning(
                    "Excluded: %s"
                    % ", ".join(entry["group"] for entry in comparison["excluded"])
                )
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Group": entry["group"],
                            "Weighted": round(entry["mean"], 0),
                            "Unweighted": round(entry["unweighted_mean"], 0),
                            "95% interval": "%.0f – %.0f" % (entry["lower"], entry["upper"]),
                            "n_eff": round(entry["effective_sample"], 1),
                        }
                        for entry in comparison["entries"]
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )

st.divider()
st.subheader("Saved estimates")
saved = get_estimates(user_id)
if not saved:
    st.info("Nothing saved yet.")
for record in saved:
    with st.expander(
        "%s — unweighted %.0f, weighted %.0f%s"
        % (
            record["label"],
            record["unweighted_mean"],
            record["weighted_mean"],
            "" if record["publishable"] else " (withheld)",
        )
    ):
        st.write("Respondents: %d" % record["respondents"])
        st.write("Effective sample: %.1f" % record["effective_sample"])
        payload = record["payload"]
        if payload.get("headline"):
            st.write(payload["headline"])
        st.write("Saved: %s" % record["created_at"])
        if st.button("Delete", key="pop_delete_%s" % record["id"]):
            delete_estimate(user_id, record["id"])
            st.rerun()
