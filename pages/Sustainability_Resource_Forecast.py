"""Streamlit UI for Sustainability Resource Consumption Forecasting (#1297)."""

from __future__ import annotations

import streamlit as st

from resource_forecasting import (
    DEFAULT_ALPHA,
    DEFAULT_HORIZON,
    DEFAULT_WINDOW,
    METHOD_EXPONENTIAL,
    METHOD_LINEAR,
    METHOD_MOVING_AVERAGE,
    RESOURCE_LABELS,
    RESOURCE_UNITS,
    ForecastValidationError,
    build_forecast_report,
    compare_forecasts,
    explain_forecast,
    generate_scenario,
    load_user_observations,
    serialize_report,
)


st.set_page_config(page_title="Resource Consumption Forecast", page_icon="📈", layout="wide")

st.title("📈 Sustainability Resource Consumption Forecast")
st.caption(
    "Project future resource consumption from your saved assessment history. "
    "Forecasts are estimates, not guarantees, and historical assessments are never changed."
)

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning("Please log in from the main application page.")
    st.stop()

with st.sidebar:
    st.header("Forecast settings")
    horizon = st.slider("Future periods", 1, 24, DEFAULT_HORIZON)
    method_label = st.selectbox(
        "Forecast method",
        ["Linear trend", "Moving average", "Exponential smoothing"],
        help="Use linear for a clear trend, moving average for noisy data, or exponential smoothing for a responsive baseline.",
    )
    method = {
        "Linear trend": METHOD_LINEAR,
        "Moving average": METHOD_MOVING_AVERAGE,
        "Exponential smoothing": METHOD_EXPONENTIAL,
    }[method_label]
    window = DEFAULT_WINDOW
    alpha = DEFAULT_ALPHA
    if method == METHOD_MOVING_AVERAGE:
        window = st.slider("Moving-average window", 1, 8, DEFAULT_WINDOW)
    if method == METHOD_EXPONENTIAL:
        alpha = st.slider("Smoothing alpha", 0.05, 1.0, DEFAULT_ALPHA, 0.05)

try:
    observations = load_user_observations(user_id)
except ForecastValidationError as exc:
    st.error(f"Unable to load assessment history: {exc}")
    st.stop()

if not observations:
    st.info("Complete at least two assessments to begin trend forecasting.")
    st.stop()

st.subheader("Historical data quality")
quality_columns = st.columns(len(RESOURCE_LABELS))
for column, resource in zip(quality_columns, RESOURCE_LABELS):
    count = sum(item.value_for(resource) is not None for item in observations)
    column.metric(RESOURCE_LABELS[resource], f"{count} observations")

try:
    report = build_forecast_report(
        user_id,
        observations,
        horizon,
        method,
        window=window,
        alpha=alpha,
    )
except ForecastValidationError as exc:
    st.error(f"Could not create the forecast: {exc}")
    st.stop()

if report.unavailable:
    with st.expander("Resources without enough data", expanded=False):
        for resource, message in report.unavailable.items():
            st.write(f"**{RESOURCE_LABELS[resource]}:** {message}")

if not report.results:
    st.warning("No supported resource has enough data for this forecast method.")
    st.stop()

st.subheader("Projected consumption")
metric_columns = st.columns(min(4, len(report.results)))
for column, result in zip(metric_columns, report.results):
    direction = "↑" if result.change_absolute > 0 else "↓" if result.change_absolute < 0 else "→"
    column.metric(
        result.label,
        f"{result.end_value:g} {result.unit}",
        f"{direction} {result.change_percent:.1f}%" if result.change_percent is not None else "Change unavailable",
    )

for result in report.results:
    st.divider()
    left, right = st.columns([2, 1])
    with left:
        st.markdown(f"### {result.label}")
        chart_data = {
            "Period": [point.period for point in result.forecast],
            result.unit: [point.value for point in result.forecast],
        }
        st.line_chart(chart_data, x="Period", y=result.unit)
    with right:
        st.write(f"**Baseline:** {result.baseline:g} {result.unit}")
        st.write(f"**Projected:** {result.end_value:g} {result.unit}")
        st.write(f"**Quality:** {result.quality.title()}")
        st.write(f"**Historical points:** {result.data_points}")
        with st.expander("How this forecast was produced"):
            for explanation in explain_forecast(result):
                st.write(f"• {explanation}")

st.divider()
st.subheader("Planning scenario")
st.caption(
    "A planning scenario applies a transparent multiplier to the projection. "
    "It does not alter your history and is not presented as a behavioral prediction."
)
scenario_resource = st.selectbox(
    "Resource",
    [result.resource for result in report.results],
    format_func=lambda value: RESOURCE_LABELS[value],
)
scenario_multiplier = st.slider("Projected usage multiplier", 0.0, 2.0, 1.0, 0.05)
selected_result = next(result for result in report.results if result.resource == scenario_resource)
scenario_result = generate_scenario(selected_result, scenario_multiplier)
scenario_cols = st.columns(3)
scenario_cols[0].metric("Scenario endpoint", f"{scenario_result.end_value:g} {scenario_result.unit}")
scenario_cols[1].metric("Scenario change", f"{scenario_result.change_percent:.1f}%" if scenario_result.change_percent is not None else "N/A")
scenario_cols[2].metric("Compared with forecast", f"{scenario_result.end_value - selected_result.end_value:+g} {scenario_result.unit}")

st.divider()
st.subheader("Method comparison")
st.caption("Comparing methods can reveal whether the projection is sensitive to the modeling approach.")
comparison_results = []
for candidate in (METHOD_LINEAR, METHOD_MOVING_AVERAGE, METHOD_EXPONENTIAL):
    try:
        candidate_report = build_forecast_report(
            user_id,
            observations,
            horizon,
            candidate,
            window=window,
            alpha=alpha,
        )
        candidate_result = next(
            (item for item in candidate_report.results if item.resource == scenario_resource),
            None,
        )
        if candidate_result:
            comparison_results.append(candidate_result)
    except ForecastValidationError:
        continue

if len(comparison_results) >= 2:
    comparison = compare_forecasts(comparison_results)
    st.dataframe(
        [{"Method": method_name, "Projected endpoint": value, "Unit": RESOURCE_UNITS[scenario_resource]} for method_name, value in comparison.end_values.items()],
        use_container_width=True,
        hide_index=True,
    )
    st.info(f"Method agreement: **{comparison.agreement}** (endpoint spread {comparison.spread:g} {RESOURCE_UNITS[scenario_resource]}).")
else:
    st.info("Not enough history to compare multiple forecasting methods.")

st.divider()
json_payload = serialize_report(report)
st.download_button(
    "Download forecast report (JSON)",
    data=json_payload,
    file_name="sustainability_resource_forecast.json",
    mime="application/json",
)

st.caption(
    "Important: forecasts extrapolate patterns from available assessments. "
    "They should not be interpreted as guaranteed future consumption or emissions."
)
