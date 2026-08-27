"""Whether a reported change is real, or the same number with different noise.

Every other trend surface in this app reports a difference. This one reports
whether the difference could have been detected at all, which is a question the
app has never asked and which changes the answer more often than not.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from styles.theme import apply_theme
from src.utils.change_detection import (
    DEFAULT_ALPHA,
    DEFAULT_POWER,
    VERDICTS,
    ChangeDetectionError,
    benjamini_hochberg,
    characterise_baseline,
    compare_periods,
    delete_test,
    get_detection_insights,
    get_tests,
    minimum_detectable_effect,
    required_periods,
    save_test,
    sequential_boundary,
    sequential_verdict,
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

apply_theme()

st.markdown(
    "<div class='section-header'>📉 Change Detection</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "Your footprint moved 4%. Your data moves more than that on its own most "
    "months. This page works out whether the change was ever within reach of "
    "the measurement — and if it was not, when it will be."
)

with st.expander("How this is counted, and what it deliberately will not do"):
    st.markdown(
        """
**There are three answers here, not two.** Detected, not detected, and *cannot
tell yet*. The third one is the reason this page exists. "Your data could not
have found an effect this size even if one was there" is a completely different
statement from "it did not work", and a user who abandons a working change
because the app said the second when it meant the first has been actively
misled.

**Consecutive months are not independent.** Treating them as though they were
understates the error and therefore *overstates* significance — the mistake
points towards more false alarms, not fewer. Everything here runs on an
effective sample size instead.

**Seasonality is not noise.** A footprint that rises every winter is not a
noisy footprint. Charging that variation to the error term would make every
real change undetectable, so trend and seasonality are estimated together and
removed before anything is measured against them.

**Shared emission factors cancel.** Both periods use the same factors, so that
uncertainty largely cancels in the difference. Treating the two estimates as
independent adds error proportional to the levels, which for a small change
against a large footprint is the difference between a finding and nothing.

**Checking constantly is itself a problem.** Testing an accumulating series at
p < 0.05 every time you look guarantees a false positive eventually. At twelve
monthly looks the chance of at least one spurious result is around one in
three. There is a boundary tab for this.

**Nothing here proves causation.** A detected change says the level moved. It
does not say what moved it.
        """
    )

st.markdown("---")

DEFAULT_SERIES = pd.DataFrame({
    "Period": [f"M{index + 1}" for index in range(16)],
    "Value": [420.0, 455.0, 398.0, 510.0, 530.0, 470.0, 405.0, 388.0,
              412.0, 449.0, 505.0, 540.0, 430.0, 462.0, 401.0, 515.0],
})

st.markdown("### Your series")
st.caption(
    "One row per period, oldest first. Values in whatever unit you track — "
    "kg CO2e, kWh, litres."
)

series_edit = st.data_editor(
    DEFAULT_SERIES, num_rows="dynamic", width="stretch", key="cx_series"
)

split_col, season_col, meaningful_col = st.columns(3)
with split_col:
    split_at = st.number_input(
        "Change happened after period",
        min_value=2, max_value=max(3, len(series_edit) - 2),
        value=min(8, max(3, len(series_edit) - 2)), step=1,
        help="Everything up to and including this period is the baseline.",
        key="cx_split",
    )
with season_col:
    season_length = st.number_input(
        "Seasonal cycle length (0 for none)",
        min_value=0, max_value=52, value=0, step=1,
        help="12 for monthly data with an annual cycle. Needs two full "
             "cycles of history.",
        key="cx_season",
    )
with meaningful_col:
    meaningful = st.number_input(
        "Change worth acting on",
        min_value=0.0, value=25.0, step=5.0,
        help="The smallest change you would actually do something about. "
             "Without it there is no way to tell 'no effect' from 'no power'.",
        key="cx_meaningful",
    )

alpha_col, power_col, cv_col = st.columns(3)
with alpha_col:
    alpha = st.slider(
        "Significance level", 0.01, 0.20, DEFAULT_ALPHA, 0.01, key="cx_alpha"
    )
with power_col:
    power = st.slider(
        "Power", 0.50, 0.99, DEFAULT_POWER, 0.05, key="cx_power"
    )
with cv_col:
    shared_cv = st.slider(
        "Emission factor uncertainty (shared)", 0.0, 0.6, 0.0, 0.05,
        help="Relative uncertainty on factors used in both periods. It "
             "cancels in the difference; this page shows by how much.",
        key="cx_cv",
    )

values = []
labels = []
for _, row in series_edit.iterrows():
    raw = row.get("Value")
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        continue
    values.append(float(raw))
    labels.append(str(row.get("Period") or len(labels) + 1))

if len(values) < 6:
    st.info("Add at least six periods before anything can be said about noise.")
    st.stop()

split_at = int(min(max(2, split_at), len(values) - 2))

try:
    baseline = characterise_baseline(
        values, season_length=int(season_length) or None
    )
    comparison = compare_periods(
        values[:split_at], values[split_at:],
        meaningful_effect=meaningful or None,
        alpha=alpha, power=power, shared_factor_cv=shared_cv,
    )
except ChangeDetectionError as error:
    st.error(str(error))
    st.stop()

st.markdown("---")

tab_verdict, tab_noise, tab_wait, tab_looks, tab_many, tab_saved = st.tabs(
    [
        "⚖️ The verdict",
        "📊 Your noise",
        "⏳ How long to wait",
        "🔁 Repeated looks",
        "🗂️ Many categories",
        "💾 Saved",
    ]
)


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------
with tab_verdict:
    st.markdown("### Is this change real?")

    banner = {
        "detected": st.success,
        "not_detected": st.info,
        "underpowered": st.warning,
    }[comparison["verdict"]]
    banner(f"**{comparison['verdict_label']}** — {comparison['verdict_note']}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Observed change",
        f"{comparison['difference']:+,.1f}",
        delta=f"{comparison['relative_change'] * 100:+.1f}%",
        delta_color="inverse",
    )
    m2.metric(
        "Smallest detectable",
        f"{comparison['minimum_detectable_effect']:,.1f}",
        help="Given this much data and this much noise.",
    )
    m3.metric("p-value", f"{comparison['p_value']:.4f}")
    m4.metric(
        "Achieved power",
        f"{comparison['achieved_power'] * 100:.0f}%",
        help="The chance this test would have found the effect it observed.",
    )

    interval = comparison["confidence_interval"]
    interval_fig = go.Figure()
    interval_fig.add_trace(go.Scatter(
        x=[interval[0], interval[1]], y=["Difference", "Difference"],
        mode="lines", line=dict(color="#5b6b78", width=8),
        name=f"{(1 - alpha) * 100:.0f}% interval",
    ))
    interval_fig.add_trace(go.Scatter(
        x=[comparison["difference"]], y=["Difference"],
        mode="markers", marker=dict(size=16, color="#2e7d63"),
        name="Observed",
    ))
    interval_fig.add_vline(
        x=0, line_dash="dash", line_color="#b4553f",
        annotation_text="no change",
    )
    for sign in (1, -1):
        interval_fig.add_vline(
            x=sign * comparison["minimum_detectable_effect"],
            line_dash="dot", line_color="#c0873f",
        )
    interval_fig.update_layout(
        height=250, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Change (same units as the series)",
        showlegend=True,
    )
    st.plotly_chart(interval_fig, width="stretch")
    st.caption(
        "Dotted lines mark the smallest effect this data could have detected. "
        "A difference inside them was never measurable, whatever its p-value "
        "happened to be."
    )

    series_fig = go.Figure()
    series_fig.add_trace(go.Scatter(
        x=labels[:split_at], y=values[:split_at],
        mode="lines+markers", name="Before", line=dict(color="#5b6b78"),
    ))
    series_fig.add_trace(go.Scatter(
        x=labels[split_at:], y=values[split_at:],
        mode="lines+markers", name="After", line=dict(color="#2e7d63"),
    ))
    series_fig.add_hline(
        y=comparison["mean_before"], line_dash="dot", line_color="#5b6b78",
        annotation_text=f"before mean {comparison['mean_before']:,.0f}",
    )
    series_fig.add_hline(
        y=comparison["mean_after"], line_dash="dot", line_color="#2e7d63",
        annotation_text=f"after mean {comparison['mean_after']:,.0f}",
    )
    series_fig.update_layout(
        height=400, margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Value",
    )
    st.plotly_chart(series_fig, width="stretch")

    st.markdown("#### Findings")
    for line in get_detection_insights(comparison, baseline):
        st.markdown(f"- {line}")

    if shared_cv > 0:
        st.caption(
            f"Shared factor treatment saved "
            f"{comparison['shared_factor_saving']:,.2f} units of standard "
            f"error against treating the two estimates as independent "
            f"({comparison['naive_standard_error']:,.2f} → "
            f"{comparison['standard_error']:,.2f})."
        )

    st.markdown("#### What each verdict means")
    for key, meta in VERDICTS.items():
        marker = "**← this one**" if key == comparison["verdict"] else ""
        st.markdown(f"**{meta['label']}** {marker}")
        st.caption(meta["note"])


# ---------------------------------------------------------------------------
# Your noise
# ---------------------------------------------------------------------------
with tab_noise:
    st.markdown("### What this series does on its own")

    n1, n2, n3, n4 = st.columns(4)
    n1.metric("Observations", f"{baseline['n']}")
    n2.metric(
        "Effective observations",
        f"{baseline['effective_n']:.1f}",
        delta=f"-{baseline['independence_loss'] * 100:.0f}% to correlation",
        delta_color="off",
    )
    n3.metric("Residual σ", f"{baseline['residual_sd']:,.1f}")
    n4.metric(
        "Variation",
        f"{baseline['coefficient_of_variation'] * 100:.1f}%",
        help="Residual standard deviation as a share of the mean.",
    )

    st.markdown(
        f"Trend: **{baseline['trend_per_period']:+,.2f} per period**. "
        f"Lag-1 autocorrelation: **{baseline['lag1_autocorrelation']:.2f}**, "
        f"inflating the variance of a mean by "
        f"**{baseline['variance_inflation']:.2f}×**."
    )

    if baseline["seasonal_profile"]:
        season_fig = go.Figure(go.Bar(
            x=[f"Phase {phase + 1}" for phase in baseline["seasonal_profile"]],
            y=list(baseline["seasonal_profile"].values()),
            marker_color="#5b6b78",
        ))
        season_fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="Seasonal offset",
        )
        st.plotly_chart(season_fig, width="stretch")
        st.caption(
            "Estimated jointly with the trend rather than after it. Removing "
            "either one first biases the other, and a seasonal pattern that is "
            "not symmetric about the midpoint invents a trend of its own."
        )

    for warning in baseline["warnings"]:
        st.warning(warning)

    st.markdown("#### Detectable effect against the data you have")
    detectable = []
    for periods in (3, 6, 9, 12, 18, 24, 36):
        mde = minimum_detectable_effect(
            baseline["residual_sd"], periods, periods,
            baseline["lag1_autocorrelation"], alpha, power,
        )
        detectable.append({
            "Periods each side": periods,
            "Effective": mde["effective_n_before"],
            "Smallest detectable": round(mde["mde"], 1),
            "As % of mean": (
                round(mde["mde"] / baseline["mean"] * 100, 1)
                if baseline["mean"] else 0.0
            ),
        })
    st.dataframe(pd.DataFrame(detectable), width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# How long to wait
# ---------------------------------------------------------------------------
with tab_wait:
    st.markdown("### When will you be able to tell?")
    st.markdown(
        "The most useful thing this page can produce. It turns *did it work?* "
        "into *ask again in N periods*, which is a question your data can "
        "eventually answer."
    )

    target = st.number_input(
        "Effect you want to be able to detect",
        min_value=0.0,
        value=float(meaningful or round(baseline["residual_sd"], 1) or 1.0),
        step=1.0, key="cx_target",
    )

    if target <= 0:
        st.info("Set a target effect above zero.")
    else:
        answer = required_periods(
            baseline["residual_sd"], target,
            baseline["lag1_autocorrelation"], alpha, power,
        )
        if not answer["achievable"]:
            st.error(answer["note"])
        else:
            needed = answer["periods_per_arm"]
            have = min(split_at, len(values) - split_at)
            st.metric(
                "Periods needed on each side",
                f"{needed}",
                delta=(
                    f"{max(0, needed - have)} more than you have"
                    if needed > have else "you already have enough"
                ),
                delta_color="off",
            )
            st.caption(answer["note"])

        curve = []
        for periods in range(2, 61):
            mde = minimum_detectable_effect(
                baseline["residual_sd"], periods, periods,
                baseline["lag1_autocorrelation"], alpha, power,
            )["mde"]
            curve.append({"periods": periods, "mde": mde})

        curve_fig = go.Figure()
        curve_fig.add_trace(go.Scatter(
            x=[row["periods"] for row in curve],
            y=[row["mde"] for row in curve],
            mode="lines", line=dict(color="#2e7d63", width=3),
            name="Smallest detectable effect",
        ))
        curve_fig.add_hline(
            y=target, line_dash="dash", line_color="#b4553f",
            annotation_text=f"your target ({target:,.0f})",
        )
        curve_fig.update_layout(
            height=400, margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="Periods on each side",
            yaxis_title="Smallest detectable effect",
        )
        st.plotly_chart(curve_fig, width="stretch")
        st.caption(
            "The curve flattens. Past a point, waiting longer stops buying "
            "resolution and the answer is a less noisy measurement rather than "
            "more of a noisy one."
        )


# ---------------------------------------------------------------------------
# Repeated looks
# ---------------------------------------------------------------------------
with tab_looks:
    st.markdown("### Checking constantly is its own problem")
    st.markdown(
        "Testing an accumulating series at the nominal level every time it "
        "updates will produce a significant result eventually whether or not "
        "anything happened."
    )

    look_col, total_col = st.columns(2)
    with look_col:
        total_looks = st.number_input(
            "Times you expect to check", min_value=1, max_value=52,
            value=12, step=1, key="cx_total_looks",
        )
    with total_col:
        this_look = st.number_input(
            "Which check is this", min_value=1, max_value=int(total_looks),
            value=min(3, int(total_looks)), step=1, key="cx_this_look",
        )

    try:
        z_now = (
            comparison["difference"] / comparison["standard_error"]
            if comparison["standard_error"] else 0.0
        )
        verdict = sequential_verdict(z_now, int(this_look), int(total_looks),
                                     alpha)
    except ChangeDetectionError as error:
        st.error(str(error))
    else:
        b1, b2, b3 = st.columns(3)
        b1.metric("Your z", f"{verdict['z']:.2f}")
        b2.metric("Boundary for this check", f"{verdict['critical_z']:.2f}")
        b3.metric(
            "False alarm risk if uncorrected",
            f"{verdict['naive_family_error'] * 100:.0f}%",
        )
        (st.success if verdict["crossed"] else st.warning)(verdict["note"])

        boundary_rows = [
            sequential_boundary(look, int(total_looks), alpha)
            for look in range(1, int(total_looks) + 1)
        ]
        boundary_fig = go.Figure()
        boundary_fig.add_trace(go.Scatter(
            x=[row["look"] for row in boundary_rows],
            y=[row["critical_z"] for row in boundary_rows],
            mode="lines+markers", name="Boundary",
            line=dict(color="#c0873f", width=3),
        ))
        boundary_fig.add_hline(
            y=1.96, line_dash="dash", line_color="#5b6b78",
            annotation_text="nominal 5% level",
        )
        boundary_fig.add_trace(go.Scatter(
            x=[verdict["look"]], y=[abs(verdict["z"])],
            mode="markers", marker=dict(size=16, color="#2e7d63"),
            name="Your result",
        ))
        boundary_fig.update_layout(
            height=400, margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="Check number", yaxis_title="|z| required",
        )
        st.plotly_chart(boundary_fig, width="stretch")
        st.caption(
            "Strict early, relaxing to the nominal level at the final check. "
            "A result that clears 1.96 at check three has not cleared the bar "
            "that accounts for you having looked twice already."
        )


# ---------------------------------------------------------------------------
# Many categories
# ---------------------------------------------------------------------------
with tab_many:
    st.markdown("### Testing eight categories at once")
    st.markdown(
        "A grid of category cards each carrying its own significance test is "
        "a multiple comparison problem. At eight categories and a 5% level, "
        "the chance of at least one spurious result is around one in three."
    )

    default_p = pd.DataFrame({
        "Category": ["Home energy", "Car", "Flights", "Food",
                     "Goods", "Water", "Waste", "Digital"],
        "p-value": [0.003, 0.021, 0.038, 0.049, 0.12, 0.31, 0.55, 0.80],
    })
    p_edit = st.data_editor(
        default_p, num_rows="dynamic", width="stretch", key="cx_pvalues"
    )

    mapping = {}
    for _, row in p_edit.iterrows():
        name = str(row.get("Category") or "").strip()
        raw = row.get("p-value")
        if not name or raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        mapping[name] = float(raw)

    if not mapping:
        st.info("Add at least one category.")
    else:
        try:
            corrected = benjamini_hochberg(mapping, alpha)
        except ChangeDetectionError as error:
            st.error(str(error))
        else:
            table = pd.DataFrame([
                {
                    "Category": name,
                    "Raw p": mapping[name],
                    "Adjusted p": corrected["adjusted"][name],
                    "Significant uncorrected":
                        "yes" if name in corrected["naive_significant"] else "",
                    "Survives correction":
                        "yes" if corrected["rejected"][name] else "",
                }
                for name in mapping
            ])
            st.dataframe(table, width="stretch", hide_index=True)

            lost = [
                name for name in corrected["naive_significant"]
                if not corrected["rejected"][name]
            ]
            if lost:
                st.warning(
                    f"{', '.join(str(name) for name in lost)} would have been "
                    f"reported as significant without the correction and does "
                    f"not survive it. Across "
                    f"{corrected['tests']} categories the chance of at least "
                    f"one such result by chance alone is "
                    f"{corrected['family_error_if_uncorrected'] * 100:.0f}%."
                )
            else:
                st.success(
                    "Every category significant at the nominal level survives "
                    "the correction."
                )


# ---------------------------------------------------------------------------
# Saved
# ---------------------------------------------------------------------------
with tab_saved:
    st.markdown("### Save this test")
    name = st.text_input(
        "Name", value="Change test", key="cx_save_name"
    )
    if st.button("Save", key="cx_save"):
        try:
            save_test(user_id, name, comparison)
            st.success("Saved.")
        except ChangeDetectionError as error:
            st.error(str(error))

    st.markdown("---")
    saved = get_tests(user_id)
    if not saved:
        st.info("Nothing saved yet.")
    else:
        for entry in saved:
            with st.container(border=True):
                head, action = st.columns([5, 1])
                with head:
                    st.markdown(f"**{entry['name']}** · {entry['created_at']}")
                    st.caption(
                        f"{VERDICTS.get(entry['verdict'], {}).get('label', entry['verdict'])} · "
                        f"difference {entry['difference']:+,.1f} · "
                        f"p = {entry['p_value']:.4f}"
                    )
                with action:
                    if st.button("Delete", key=f"cx_del_{entry['id']}"):
                        if delete_test(user_id, entry["id"]):
                            st.rerun()

st.markdown("---")
st.caption(
    "Method: Welch's t on an autocorrelation-adjusted effective sample size, "
    "power from the non-central approximation, O'Brien-Fleming style alpha "
    "spending for repeated looks, Benjamini-Hochberg across categories. "
    "Related: src.carbon.confidence_scoring.py, "
    "src.utils.sustainability_trends.py, src.environment.env_anomoly.py."
)
