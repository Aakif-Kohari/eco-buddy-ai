"""Streamlit UI for Sustainability Intervention Outcome Tracking."""

from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from src.utils.intervention_effectiveness import (
    EvidenceLevel,
    InterventionStatus,
    OutcomeDirection,
    InterventionStore,
    analyze_intervention,
    build_summary,
    create_intervention,
    create_observation,
    export_summary_csv,
    serialize_intervention_bundle,
)


st.set_page_config(page_title="Intervention Effectiveness", page_icon="📈", layout="wide")
st.title("📈 Sustainability Intervention Effectiveness")
st.caption(
    "Record adopted actions, compare baseline and observation periods, and inspect "
    "evidence quality without claiming causal certainty."
)

user_id = st.session_state.get("user_id", 1)
store = InterventionStore()
store.initialize()

with st.expander("ℹ️ How effectiveness is interpreted", expanded=False):
    st.markdown(
        """
**Measured change** is the difference between the baseline and observed values.
**Effectiveness** is a bounded evidence-weighted score, not a guaranteed carbon
saving. **Attribution confidence** describes how strongly the available data can
associate a change with the intervention.

No control group means the result is observational. Add repeated observations
and a comparison period where available to strengthen evidence.
"""
    )

tab_create, tab_record, tab_analyze, tab_summary = st.tabs(
    ["➕ Adopt intervention", "📝 Record outcome", "🔎 Analyze", "📊 Summary"]
)

with tab_create:
    st.subheader("Adopt a sustainability action")
    with st.form("create_intervention"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Intervention name", placeholder="Cycle to work twice a week")
        category = c1.text_input("Category", value="Transportation")
        action_id = c1.text_input("Existing action/recommendation ID", value="")
        metric = c1.selectbox(
            "Measured metric",
            ["carbon", "electricity", "transport", "distance", "water", "waste", "food", "flights", "eco_score", "custom"],
        )
        unit = c1.text_input("Unit", value="kg CO2e")
        baseline = c2.number_input("Baseline value", min_value=0.0, value=100.0, step=1.0)
        target_enabled = c2.checkbox("Set a target")
        target = c2.number_input("Target value", min_value=0.0, value=80.0, step=1.0) if target_enabled else None
        adopted = c2.date_input("Adopted on", value=date.today())
        status = c2.selectbox("Status", [item.value for item in InterventionStatus], index=1)
        st.markdown("**Baseline period**")
        b1, b2 = st.columns(2)
        baseline_start = b1.date_input("Baseline start", value=date.today() - timedelta(days=60), key="baseline_start")
        baseline_end = b2.date_input("Baseline end", value=date.today() - timedelta(days=31), key="baseline_end")
        st.markdown("**Observation period**")
        o1, o2 = st.columns(2)
        observation_start = o1.date_input("Observation start", value=date.today() - timedelta(days=30), key="observation_start")
        observation_end = o2.date_input("Observation end", value=date.today() + timedelta(days=30), key="observation_end")
        description = st.text_area("Description")
        notes = st.text_area("Notes")
        submitted = st.form_submit_button("Save intervention", type="primary")
        if submitted:
            try:
                item = create_intervention(
                    name=name,
                    category=category,
                    action_id=action_id,
                    adopted_on=adopted,
                    baseline_start=baseline_start,
                    baseline_end=baseline_end,
                    observation_start=observation_start,
                    observation_end=observation_end,
                    metric=metric,
                    baseline_value=baseline,
                    target_value=target,
                    unit=unit,
                    status=status,
                    description=description,
                    notes=notes,
                    user_id=user_id,
                )
                store.save_intervention(item)
                st.success(f"Saved intervention: {item.name}")
            except Exception as exc:
                st.error(str(exc))

with tab_record:
    st.subheader("Record a measured outcome")
    interventions = store.list_interventions(user_id)
    if not interventions:
        st.info("Create an intervention first.")
    else:
        labels = {f"{item.name} · {item.id}": item for item in interventions}
        selected_label = st.selectbox("Intervention", list(labels))
        selected = labels[selected_label]
        st.caption(
            f"Observation window: {selected.observation_start.isoformat()} → "
            f"{selected.observation_end.isoformat()} · unit: {selected.unit}"
        )
        with st.form("record_observation"):
            observed_on = st.date_input(
                "Observed on", value=max(selected.observation_start, min(date.today(), selected.observation_end))
            )
            value = st.number_input("Measured value", min_value=0.0, value=float(selected.baseline_value), step=1.0)
            quality = st.slider("Measurement quality", 0.0, 1.0, 1.0, 0.05)
            source = st.text_input("Source", value="manual")
            notes = st.text_area("Observation notes")
            saved = st.form_submit_button("Save outcome", type="primary")
            if saved:
                try:
                    obs = create_observation(
                        selected,
                        observed_on=observed_on,
                        value=value,
                        quality=quality,
                        source=source,
                        notes=notes,
                    )
                    store.save_observation(obs)
                    st.success("Outcome observation saved.")
                except Exception as exc:
                    st.error(str(exc))
        observations = store.list_observations(selected.id)
        if observations:
            st.dataframe(
                pd.DataFrame([item.to_dict() for item in observations]),
                use_container_width=True,
                hide_index=True,
            )

with tab_analyze:
    st.subheader("Analyze an intervention")
    interventions = store.list_interventions(user_id)
    if not interventions:
        st.info("Create an intervention first.")
    else:
        labels = {f"{item.name} · {item.id}": item for item in interventions}
        selected_label = st.selectbox("Intervention to analyze", list(labels), key="analysis_intervention")
        selected = labels[selected_label]
        observations = store.list_observations(selected.id)
        c1, c2 = st.columns(2)
        has_control = c1.checkbox("I have a comparison/control period")
        confounders_raw = c2.text_input(
            "Potential confounders (comma separated)",
            placeholder="seasonality, price change",
        )
        confounders = [item.strip() for item in confounders_raw.split(",") if item.strip()]
        if st.button("Calculate effectiveness", type="primary"):
            try:
                analysis = analyze_intervention(
                    selected,
                    observations,
                    has_control=has_control,
                    confounders=confounders,
                )
                store.save_analysis(analysis)
                st.session_state["latest_intervention_analysis"] = analysis.to_dict()
                st.success("Analysis snapshot saved.")
            except Exception as exc:
                st.error(str(exc))

        latest = store.latest_analysis(selected.id)
        if latest:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Effectiveness", f"{latest.effectiveness_score:.1f}/100")
            m2.metric("Improvement", "—" if latest.improvement_pct is None else f"{latest.improvement_pct:.1f}%")
            m3.metric("Evidence", latest.evidence_level.value.title())
            m4.metric("Attribution", f"{latest.attribution_confidence * 100:.1f}%")
            st.write(f"**Outcome direction:** {latest.direction.value.title()}")
            if latest.warnings:
                for warning in latest.warnings:
                    st.warning(warning)
            if latest.limitations:
                st.info("**Limitations:** " + " ".join(latest.limitations))
            st.subheader("Calculation details")
            detail = {
                "Baseline": latest.baseline_value,
                "Observed": latest.observation_value,
                "Absolute change": latest.absolute_change,
                "Percentage change": latest.percentage_change,
                "Target attainment": latest.target_attainment_pct,
                "Observations": latest.observation_count,
                "Measurement consistency": latest.measurement_consistency,
                "Trend slope": latest.trend_slope,
                "Inputs fingerprint": latest.inputs_fingerprint,
            }
            st.dataframe(pd.DataFrame([detail]), use_container_width=True, hide_index=True)
            st.subheader("Recommendations")
            for recommendation in latest.recommendations:
                st.write(f"• {recommendation}")
            bundle = serialize_intervention_bundle(selected, observations, latest)
            st.download_button(
                "⬇️ Export intervention audit JSON",
                bundle,
                file_name=f"intervention_{selected.id}.json",
                mime="application/json",
            )

with tab_summary:
    st.subheader("Intervention portfolio")
    interventions = store.list_interventions(user_id)
    analyses = [store.latest_analysis(item.id) for item in interventions]
    analyses = [item for item in analyses if item is not None]
    summary = build_summary(interventions, analyses)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Interventions", summary.intervention_count)
    c2.metric("Analyzed", summary.analyzed_count)
    c3.metric("Improved", summary.improved_count)
    c4.metric("Avg effectiveness", f"{summary.average_effectiveness:.1f}/100")
    if interventions:
        rows = []
        for item in interventions:
            analysis = next((a for a in analyses if a.intervention_id == item.id), None)
            rows.append({
                "Intervention": item.name,
                "Category": item.category,
                "Status": item.status.value,
                "Effectiveness": analysis.effectiveness_score if analysis else None,
                "Improvement %": analysis.improvement_pct if analysis else None,
                "Evidence": analysis.evidence_level.value if analysis else "not analyzed",
                "Observations": analysis.observation_count if analysis else 0,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Export portfolio CSV",
            export_summary_csv(interventions, analyses),
            file_name="intervention_effectiveness.csv",
            mime="text/csv",
        )
    if summary.recommendations:
        st.subheader("Next steps")
        for recommendation in summary.recommendations:
            st.write(f"• {recommendation}")
