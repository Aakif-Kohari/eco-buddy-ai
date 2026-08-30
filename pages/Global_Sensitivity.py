"""Which input drives the spread — not which line item it landed in.

`footprint_uncertainty.sensitivity_ranking` pins components, which is exactly
right for a sum of independent terms and undefined for everything else. When
one grid factor multiplies into three components, or when the model compounds
rather than adds, the question has to be asked about parameters instead.

Sobol variance decomposition, estimated by Saltelli cross-sampling, with the
interaction share reported as a headline because it is the number that says
whether the simpler tools in this app can be trusted on a given model.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.utils.global_sensitivity import (
    DEFAULT_BASE_SAMPLES,
    DEMO_MODELS,
    MAX_PARAMETERS,
    SensitivityError,
    analyse,
    build_parameter,
    convergence,
    delete_study,
    demo_parameters,
    get_sensitivity_notes,
    get_studies,
    list_demo_models,
    list_distributions,
    measurement_priorities,
    morris_screening,
    save_study,
    validate_against_ishigami,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>🎛️ Global Sensitivity</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Which *input* drives the uncertainty in a result — including the inputs "
    "that only matter in combination with something else, which a "
    "one-at-a-time analysis reports as zero."
)

with st.expander("Why component pinning is not enough"):
    st.markdown(
        """
**Parameters are shared; components are not.** Grid intensity multiplies into
home electricity, EV charging and heat pump heating. Pinning "home
electricity" to its point estimate leaves grid intensity varying inside two
other components, so it gets charged with a fraction of the variance it
actually causes. The user can go and look up their grid intensity. They cannot
go and look up "home electricity as a line item".

**Most of the interesting models here do not have components.** A compounding
pathway, a backward induction over replacement years, a discounted time
series — there is no column to pin. The one sensitivity tool this repo has
does not apply to the engines whose answers move the most.

**One-at-a-time analysis is blind to interactions by construction.** Vary A,
then vary B, and you learn nothing about what happens when both move. Two
indices are reported here for exactly that reason:

- **First order (S₁)** — variance caused by that input acting alone.
- **Total effect (S_T)** — that input plus every interaction it takes part in.

If they are equal the model is additive and the cheaper tools are fine. If
S_T is much larger than S₁, the input matters mainly *in combination*, and
anything that varies one thing at a time will have missed it.

**A tornado chart is not this.** Tornado plots move each input to its 5th and
95th percentile with everything else held at the median. That describes the
edges of the input space, not the variance, and on a non-monotonic response it
can rank an input as unimportant precisely because the median sits near a
turning point.
        """
    )

tab_study, tab_interactions, tab_screening, tab_validation = st.tabs(
    ["Decomposition", "Interactions & priorities", "Screening & convergence", "Validation"]
)


def _parameter_editor(key_prefix):
    """Let the user build a parameter list by hand."""
    distributions = {spec["key"]: spec["label"] for spec in list_distributions()}
    count = st.number_input(
        "How many parameters",
        min_value=1,
        max_value=MAX_PARAMETERS,
        value=4,
        step=1,
        key="%s_count" % key_prefix,
    )
    built = []
    for index in range(int(count)):
        with st.expander("Parameter %d" % (index + 1), expanded=index < 2):
            columns = st.columns([2, 2])
            name = columns[0].text_input(
                "Name", value="x%d" % (index + 1), key="%s_name_%d" % (key_prefix, index)
            )
            kind = columns[1].selectbox(
                "Distribution",
                options=list(distributions),
                format_func=lambda value: distributions[value],
                key="%s_dist_%d" % (key_prefix, index),
            )
            unit = st.text_input(
                "Unit (optional)", value="", key="%s_unit_%d" % (key_prefix, index)
            )
            fields = st.columns(3)
            try:
                if kind in ("uniform", "triangular"):
                    low = fields[0].number_input(
                        "Low", value=0.0, key="%s_low_%d" % (key_prefix, index)
                    )
                    high = fields[1].number_input(
                        "High", value=1.0, key="%s_high_%d" % (key_prefix, index)
                    )
                    mode = None
                    if kind == "triangular":
                        mode = fields[2].number_input(
                            "Mode",
                            value=float((low + high) / 2.0),
                            key="%s_mode_%d" % (key_prefix, index),
                        )
                    built.append(
                        build_parameter(name, kind, low=low, high=high, mode=mode, unit=unit)
                    )
                elif kind == "normal":
                    mean = fields[0].number_input(
                        "Mean", value=1.0, key="%s_mean_%d" % (key_prefix, index)
                    )
                    sigma = fields[1].number_input(
                        "Sigma", value=0.2, min_value=0.0001,
                        key="%s_sigma_%d" % (key_prefix, index),
                    )
                    built.append(build_parameter(name, kind, mean=mean, sigma=sigma, unit=unit))
                else:
                    median = fields[0].number_input(
                        "Median", value=1.0, min_value=0.0001,
                        key="%s_median_%d" % (key_prefix, index),
                    )
                    gsd = fields[1].number_input(
                        "GSD", value=1.3, min_value=1.0001,
                        key="%s_gsd_%d" % (key_prefix, index),
                    )
                    built.append(build_parameter(name, kind, median=median, gsd=gsd, unit=unit))
            except SensitivityError as error:
                st.error(str(error))
    return built


def _model_choice(key_prefix):
    """Pick one of the worked example models."""
    options = list_demo_models()
    labels = {spec["key"]: spec["label"] for spec in options}
    notes = {spec["key"]: spec["note"] for spec in options}
    chosen = st.selectbox(
        "Model",
        options=list(labels),
        format_func=lambda value: labels[value],
        key="%s_model" % key_prefix,
    )
    st.caption(notes[chosen])
    return chosen


with tab_study:
    st.subheader("Variance decomposition")

    chosen = _model_choice("study")
    samples = st.select_slider(
        "Base samples (N)",
        options=[128, 256, 512, 1024, 2048, 4096],
        value=DEFAULT_BASE_SAMPLES,
        help="Total model runs are N x (parameters + 2).",
    )
    bootstrap = st.slider(
        "Bootstrap resamples", min_value=20, max_value=500, value=150, step=10,
        help="Intervals come from resampling the stored evaluations, not from re-running the model.",
    )

    if st.button("Run decomposition", type="primary"):
        try:
            parameters = demo_parameters(chosen)
            result = analyse(
                DEMO_MODELS[chosen]["model"],
                parameters,
                base_samples=samples,
                bootstrap=bootstrap,
                label=DEMO_MODELS[chosen]["label"],
            )
            st.session_state["gs_result"] = result
        except SensitivityError as error:
            st.error(str(error))

    result = st.session_state.get("gs_result")
    if result:
        head = st.columns(4)
        head[0].metric("Model runs", "%d" % result["evaluations"])
        head[1].metric("Output mean", "%.0f" % result["output_mean"])
        head[2].metric(
            "5th–95th",
            "%.0f – %.0f" % (result["output_p5"], result["output_p95"]),
        )
        head[3].metric("Interaction share", "%.0f%%" % (result["interaction_share"] * 100.0))

        verdict = result["additivity"]
        if verdict["verdict"] == "additive":
            st.success("**%s** %s" % (verdict["headline"], verdict["detail"]))
        elif verdict["verdict"] == "strongly_interacting":
            st.warning("**%s** %s" % (verdict["headline"], verdict["detail"]))
        else:
            st.info("**%s** %s" % (verdict["headline"], verdict["detail"]))

        frame = pd.DataFrame(
            [
                {
                    "Parameter": row["name"],
                    "Unit": row["unit"],
                    "S₁": round(row["first_order"], 3),
                    "S₁ 5–95%": "%.2f – %.2f"
                    % (row["first_order_low"], row["first_order_high"]),
                    "S_T": round(row["total_effect"], 3),
                    "S_T 5–95%": "%.2f – %.2f"
                    % (row["total_effect_low"], row["total_effect_high"]),
                    "Interaction": round(row["interaction"], 3),
                }
                for row in result["rows"]
            ]
        )
        st.dataframe(frame, use_container_width=True, hide_index=True)

        names = [row["name"] for row in result["rows"]]
        figure = go.Figure()
        figure.add_trace(
            go.Bar(
                x=names,
                y=[row["first_order"] for row in result["rows"]],
                name="First order (alone)",
                marker_color="#2E86AB",
            )
        )
        figure.add_trace(
            go.Bar(
                x=names,
                y=[row["interaction"] for row in result["rows"]],
                name="Interaction (only in combination)",
                marker_color="#F6AE2D",
            )
        )
        figure.update_layout(
            barmode="stack",
            title="Total effect, split into the part that acts alone and the part that does not",
            yaxis_title="Share of output variance",
            height=430,
        )
        st.plotly_chart(figure, use_container_width=True)

        for note in get_sensitivity_notes(result):
            st.markdown("- %s" % note)

        for problem in result["diagnostics"]:
            if problem["severity"] == "error":
                st.error(problem["message"])
            elif problem["severity"] == "warning":
                st.warning(problem["message"])
            else:
                st.caption(problem["message"])

        if st.button("Save this study"):
            if save_study(user_id, result):
                st.success("Saved.")
            else:
                st.info("Could not save — storage unavailable.")

with tab_interactions:
    st.subheader("What is worth measuring, and what cannot be separated")
    result = st.session_state.get("gs_result")
    if not result:
        st.info("Run a decomposition first.")
    else:
        st.markdown("**Measurement priorities**")
        st.caption(
            "Fixing a parameter to a known value removes its total effect from "
            "the variance. The residual spread is what would be left after "
            "going and measuring it."
        )
        priorities = measurement_priorities(result)
        priority_frame = pd.DataFrame(
            [
                {
                    "Parameter": item["name"],
                    "Removes": "%.0f%% of variance" % (item["variance_removed"] * 100.0),
                    "Spread now": "±%.0f" % item["current_stdev"],
                    "Spread after": "±%.0f" % item["residual_stdev"],
                    "Worth it": "yes" if item["worth_measuring"] else "marginal",
                }
                for item in priorities
            ]
        )
        st.dataframe(priority_frame, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("**Rank bands**")
        st.caption(
            "Parameters whose total-effect intervals overlap have not been "
            "separated by this sample. Ordering them anyway would invent a "
            "distinction the study cannot support."
        )
        for band in result["ranking"]:
            if band["separated"]:
                st.markdown(
                    "**%d.** %s — S_T %.3f"
                    % (band["band"], band["names"][0], band["total_effect_high"])
                )
            else:
                st.markdown(
                    "**%d.** %s — *tied* between S_T %.3f and %.3f"
                    % (
                        band["band"],
                        ", ".join(band["names"]),
                        band["total_effect_low"],
                        band["total_effect_high"],
                    )
                )

        st.divider()
        st.markdown("**Interaction detail**")
        interaction_frame = pd.DataFrame(
            [
                {
                    "Parameter": row["name"],
                    "Alone (S₁)": round(row["first_order"], 3),
                    "With interactions (S_T)": round(row["total_effect"], 3),
                    "Only in combination": round(row["interaction"], 3),
                    "Missed by one-at-a-time": "yes" if row["interaction_dominated"] else "no",
                }
                for row in result["rows"]
            ]
        )
        st.dataframe(interaction_frame, use_container_width=True, hide_index=True)

with tab_screening:
    st.subheader("Screening and convergence")
    st.caption(
        "Morris elementary effects cost r(k+1) runs instead of N(k+2). They "
        "cannot give variance shares and are not trying to — they separate the "
        "parameters that plainly do nothing from the ones worth a full study."
    )

    chosen = _model_choice("screen")
    columns = st.columns(2)
    trajectories = columns[0].slider("Trajectories (r)", 4, 100, 24, step=4)
    levels = columns[1].slider("Grid levels (p)", 4, 20, 8, step=2)

    if st.button("Screen"):
        try:
            screening = morris_screening(
                DEMO_MODELS[chosen]["model"],
                demo_parameters(chosen),
                trajectories=trajectories,
                levels=levels,
            )
            st.session_state["gs_screen"] = screening
        except SensitivityError as error:
            st.error(str(error))

    screening = st.session_state.get("gs_screen")
    if screening:
        st.caption("%d model runs." % screening["evaluations"])
        screen_frame = pd.DataFrame(
            [
                {
                    "Parameter": row["name"],
                    "μ* (mean |effect|)": round(row["mu_star"], 4),
                    "σ (spread of effect)": round(row["sigma"], 4),
                    "Relative": "%.0f%%" % (row["mu_star_relative"] * 100.0),
                    "Non-linear / interacting": "yes" if row["non_linear"] else "no",
                    "Screen out": "yes" if row["screen_out"] else "no",
                }
                for row in screening["rows"]
            ]
        )
        st.dataframe(screen_frame, use_container_width=True, hide_index=True)

        scatter = go.Figure()
        scatter.add_trace(
            go.Scatter(
                x=[row["mu_star"] for row in screening["rows"]],
                y=[row["sigma"] for row in screening["rows"]],
                mode="markers+text",
                text=[row["name"] for row in screening["rows"]],
                textposition="top center",
                marker={"size": 12, "color": "#2E86AB"},
            )
        )
        scatter.update_layout(
            title="High μ* with high σ means the effect changes across the input space",
            xaxis_title="μ* — mean absolute elementary effect",
            yaxis_title="σ — spread of the effect",
            height=420,
        )
        st.plotly_chart(scatter, use_container_width=True)

        if screening["drop"]:
            st.info("Screened out: %s" % ", ".join(screening["drop"]))

    st.divider()
    st.markdown("**Convergence**")
    st.caption(
        "A Sobol index is an estimate. Watching it settle across nested "
        "prefixes of the same sample is the cheapest evidence that it has "
        "settled at all."
    )
    conv_samples = st.select_slider(
        "Base samples for the convergence run",
        options=[256, 512, 1024, 2048],
        value=512,
        key="conv_samples",
    )
    if st.button("Test convergence"):
        try:
            history = convergence(
                DEMO_MODELS[chosen]["model"],
                demo_parameters(chosen),
                base_samples=conv_samples,
                stages=4,
            )
            if history["converged"]:
                st.success(history["verdict"])
            else:
                st.warning(history["verdict"])

            trace = go.Figure()
            names = list(history["history"][-1]["total_effect"]) if history["history"] else []
            for name in names:
                trace.add_trace(
                    go.Scatter(
                        x=[step["samples"] for step in history["history"]],
                        y=[step["total_effect"][name] for step in history["history"]],
                        mode="lines+markers",
                        name=name,
                    )
                )
            trace.update_layout(
                title="Total-effect indices against sample size",
                xaxis_title="Base samples used",
                yaxis_title="S_T",
                height=400,
            )
            st.plotly_chart(trace, use_container_width=True)
        except SensitivityError as error:
            st.error(str(error))

with tab_validation:
    st.subheader("Does the estimator actually work")
    st.markdown(
        """
The Ishigami function is the standard test case, and it is deliberately nasty:
strongly non-linear, non-monotonic, and **x₃ has a first-order index of exactly
zero while carrying about a quarter of the variance** through its interaction
with x₁.

That last property is why it is here. A tornado chart, a one-at-a-time sweep,
or any component-pinning scheme will report x₃ as irrelevant. If this page ever
agrees, it is broken.
        """
    )
    validation_samples = st.select_slider(
        "Base samples",
        options=[512, 1024, 2048, 4096, 8192],
        value=2048,
        key="validation_samples",
    )
    if st.button("Run validation"):
        report = validate_against_ishigami(base_samples=validation_samples)
        st.metric("Largest absolute error", "%.4f" % report["max_error"])
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Input": item["name"],
                        "S₁ estimated": round(item["first_order"], 4),
                        "S₁ analytic": round(item["first_order_expected"], 4),
                        "S_T estimated": round(item["total_effect"], 4),
                        "S_T analytic": round(item["total_effect_expected"], 4),
                    }
                    for item in report["comparison"]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(report["note"])

st.divider()
st.subheader("Saved studies")
saved = get_studies(user_id)
if not saved:
    st.info("Nothing saved yet.")
for record in saved:
    with st.expander(
        "%s — %s carries %.0f%% of the variance"
        % (record["label"], record["top_parameter"], record["top_total_effect"] * 100.0)
    ):
        st.write("Interaction share: %.0f%%" % (record["interaction_share"] * 100.0))
        st.write("Base samples: %d" % record["base_samples"])
        payload = record["payload"]
        if payload.get("additivity"):
            st.write(payload["additivity"]["headline"])
        st.write("Saved: %s" % record["created_at"])
        if st.button("Delete", key="gs_delete_%s" % record["id"]):
            delete_study(user_id, record["id"])
            st.rerun()
