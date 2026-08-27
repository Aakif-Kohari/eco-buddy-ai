import streamlit as st
import pandas as pd
import random
import time
from src.core.database import save_carbon_budget,get_carbon_budget
from src.core.database import *
from src.carbon.emissions import *
from src.carbon.emissions import (
    calculate_remaining_budget,
    calculate_budget_progress,
    forecast_monthly_emission,
    budget_status,
)
from src.core.assessment_snapshot import build_assessment_snapshot, serialize_snapshotfrom src.ai.recommendations import *
from src.utils.impact_analyzer import analyze_minimal_change
import os
import tempfile
import uuid
import plotly.graph_objects as go
import plotly.express as px
from src.reporting.report import generate_pdf
from src.reporting.treemap_chart import create_emission_treemap
from src.reporting.sankey_chart import create_emission_sankey
from src.community import gamification as gf
from src.utils.marketplace import *
from src.ai.llm_parser import parse_quick_log
from src.utils.ocr_utils import extract_text_from_bytes, parse_energy_consumption
from src.core.background_tasks import submit_background_task, render_task_progress, clear_background_task
from src.energy import energy_audit as ea

from styles.theme import apply_theme
apply_theme()


from src.core.cache import cached
from src.core.cache_config import TTL_LLM_RESPONSE
GLOBAL_POPULATION = 8_200_000_000

CURRENT_GLOBAL_EMISSIONS = 37_400_000_000


def render_eco_clone_simulator(user_footprint, contributors):
    """Show what the world would look like if everyone lived like this user.

Needs a completed assessment: it reads the user's total footprint and
their per-category contributors, so it can only run once those exist.
"""

    projected_global = user_footprint * GLOBAL_POPULATION

    difference = projected_global - CURRENT_GLOBAL_EMISSIONS

    percentage = (
                difference / CURRENT_GLOBAL_EMISSIONS
            ) * 100
    col1, col2, col3 = st.columns(3)

    with col1:
                st.metric(
                    "Your Footprint",
                    f"{user_footprint:.2f} kg CO₂"
                )

    with col2:
                st.metric(
                    "Projected Global",
                    f"{projected_global/1_000_000_000:.2f} B kg"
                )

    with col3:
                st.metric(
                    "Difference",
                    f"{percentage:.2f}%"
                )
    st.markdown("### 📊 Global Emission Comparison")

    comparison = pd.DataFrame({
        "Scenario": [
            "Current Earth",
            "If Everyone Lived Like You"
        ],
        "CO₂ Emissions (Billion kg)": [
            CURRENT_GLOBAL_EMISSIONS / 1_000_000_000,
            projected_global / 1_000_000_000
        ]
    })

    fig = px.bar(
        comparison,
        x="Scenario",
        y="CO₂ Emissions (Billion kg)",
        color="Scenario",
        title="Global Carbon Emissions Comparison",
        text="CO₂ Emissions (Billion kg)"
    )

    fig.update_layout(
        xaxis_title="Scenario",
        yaxis_title="Billion kg CO₂"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown("### 🌎 Environmental Impact")

    if difference < 0:

        st.success(
            f"""
    🌱 Amazing!

    If everyone adopted your lifestyle:

    • Global emissions would decrease by **{abs(percentage):.2f}%**

    • Your lifestyle promotes sustainability.

    • Keep inspiring greener living.
    """
        )

    else:

        st.error(
            f"""
    ⚠ Warning!

    If everyone adopted your lifestyle:

    • Global emissions would increase by **{percentage:.2f}%**

    • More sustainable habits are recommended.
    """
        )
    largest = max(
        contributors,
        key=contributors.get
    )

    if largest == "Transport":

        st.info("🚶 Consider walking, cycling, or public transport more often.")

    elif largest == "Electricity":

        st.info("⚡ Reduce electricity usage and switch to energy-efficient appliances.")

    elif largest == "Diet":

        st.info("🥗 Try adding more plant-based meals to reduce emissions.")

    elif largest == "Flights":

        st.info("✈ Reduce unnecessary flights whenever possible.")
    st.markdown("### 🌍 Eco Clone Score")

    score = max(0, 100 - abs(percentage))

    st.metric(
        "Eco Clone Score",
        f"{score:.1f}/100"
    )
    st.markdown("---")

    st.markdown("""
### 🌱 Final Insight

The Eco Clone Simulator estimates the environmental impact if everyone on Earth adopted your current lifestyle.

Remember, this is an educational simulation designed to help visualize how individual choices can scale globally.

Every small sustainable action contributes to a healthier planet.
""")
    st.markdown("### 🥧 Global Impact Distribution")

    pie = pd.DataFrame({
        "Category": [
            "Current Global Emissions",
            "Difference"
        ],
        "Value": [
            CURRENT_GLOBAL_EMISSIONS,
            abs(difference)
        ]
    })

    fig = px.pie(
        pie,
        values="Value",
        names="Category",
        title="Current vs Simulated Impact"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown("### 🤖 AI Sustainability Insight")

    if percentage < -10:

        st.success("""
### Excellent 🌱

Your lifestyle is significantly more sustainable than the current global average.

If everyone adopted similar habits:

✅ Global emissions would reduce dramatically.

🌍 This would contribute positively toward climate goals.
""")

    elif percentage < 0:

        st.info("""
### Good 👍

Your lifestyle is slightly greener than average.

Small improvements in transportation and electricity usage could create an even greater impact.
""")

    elif percentage < 15:

        st.warning("""
### Moderate Impact

Your lifestyle is close to the current global average.

A few sustainable changes could noticeably reduce global emissions.
""")

    else:

        st.error("""
### High Environmental Impact

If everyone lived this way,

global emissions would increase considerably.

Consider reducing:

• Transportation emissions

• Electricity usage

• Flight frequency

• High-carbon diet
""")
    st.markdown("### 🌍 Sustainability Score")

    st.progress(score / 100)

    st.metric(
        "Global Sustainability Score",
        f"{score:.1f}/100"
    )
    st.markdown("### 🌎 Did You Know?")

    facts = [
        "🌱 Walking instead of driving for short trips can significantly reduce emissions over time.",
        "💡 LED bulbs use much less electricity than traditional bulbs.",
        "🚲 Cycling produces almost zero direct carbon emissions.",
        "🥗 Plant-based meals generally have a lower carbon footprint than meat-heavy diets."
    ]


    st.info(random.choice(facts))
    st.markdown("### 📄 Export Simulation")

    report = f"""
Eco Clone Simulator

Your Footprint: {user_footprint:.2f} kg CO₂

Projected Global Emissions:
{projected_global:.2f} kg CO₂

Difference:
{percentage:.2f}%

Eco Clone Score:
{score:.2f}/100
"""

    st.download_button(
        "📥 Download Simulation Report",
        report,
        file_name="eco_clone_simulation.txt"
    )
    st.markdown("---")

    st.caption(
        "🌍 Eco Clone Simulator is an educational feature that helps visualize the potential global impact of individual lifestyle choices."
    )


@cached(ttl=TTL_LLM_RESPONSE)
def compute_arima_forecast(ts_data):
    import warnings
    from statsmodels.tsa.arima.model import ARIMA
    import numpy as np

    warnings.filterwarnings('ignore')
    arr = np.array(ts_data)
    model = ARIMA(arr, order=(1, 1, 0))
    fitted_model = model.fit()

    forecast_steps = 5
    forecast = fitted_model.get_forecast(steps=forecast_steps)
    forecast_mean = forecast.predicted_mean
    conf_int = forecast.conf_int(alpha=0.05)

    forecast_line = [float(arr[-1])] + [float(v) for v in forecast_mean]
    conf_lower = [float(arr[-1])] + [float(v) for v in conf_int[:, 0]]
    conf_upper = [float(arr[-1])] + [float(v) for v in conf_int[:, 1]]

    return forecast_line, conf_lower, conf_upper

user_id = st.session_state.get('user_id')
if not user_id:
    st.warning('Please log in from the main application page.')
    st.stop()

# -------------------------
# DRAFT RECOVERY & DEFAULT FORM VALUES
# -------------------------
from src.core.database import save_assessment_draft, get_assessment_draft, delete_assessment_draft
from src.core.session_state_utils import ensure_session_state

DEFAULT_VALUES = {
    "region": "Global",
    "transport": "Car",
    "distance": 10.0,
    "electricity": 200.0,
    "diet": "Vegetarian",
    "flights": 0,
}

if 'draft_status' not in st.session_state:
    st.session_state.draft_status = None

draft = None
if user_id and st.session_state.draft_status is None:
    draft = get_assessment_draft(user_id)

ensure_session_state(DEFAULT_VALUES)

tab_assess, tab_forecast, tab_clone = st.tabs([
    "📝 Assessment",
    "📈 Forecasting",
    "🌍 Eco Clone Simulator"
])
with tab_assess:
    st.markdown("<div class='section-header'>📝 Your Lifestyle Profile</div>", unsafe_allow_html=True)

    # Draft recovery prompt
    if user_id and draft:
        st.info("📝 We found an unfinished assessment from your previous session. Would you like to restore it?")
        col_rest, col_disc, _ = st.columns([1, 1, 4])
        with col_rest:
            if st.button("✅ Restore Session", key="restore_session_cf_btn"):
                st.session_state.draft_status = 'restored'
                for key, val in draft.items():
                    st.session_state[key] = val
                st.success("Session restored successfully!")
                st.rerun()
        with col_disc:
            if st.button("🗑️ Discard Draft", key="discard_draft_cf_btn"):
                delete_assessment_draft(user_id)
                st.session_state.draft_status = 'discarded'
                st.success("Draft discarded.")
                st.rerun()

    st.markdown("### Region Setting")
    region = st.selectbox("Select Your Region for API Emissions Factor", ["Global", "US", "UK", "EU"], key="region")

    # -------------------------
    # QUICK LOG (AI)
    # -------------------------
    st.markdown("### 🤖 AI Quick Log")
    col_ai_input, col_ai_btn = st.columns([4, 1], vertical_alignment="bottom")
    with col_ai_input:
        quick_log_text = st.text_area("Let AI auto-fill your profile! Describe your day naturally.", placeholder="e.g., 'I drove 15 miles in my SUV and had a beef steak'", key="quick_log_input", height=68)
    with col_ai_btn:
        parse_btn = st.button("✨ Parse with AI", use_container_width=True)
    
    if parse_btn:
        if quick_log_text.strip():
            submit_background_task(
                "quick_log_parse",
                parse_quick_log,
                quick_log_text,
                task_name="Parsing with AI"
            )
        else:
            st.warning("Please enter some text first.")

    is_done_ai, parsed_data = render_task_progress(
        "quick_log_parse",
        success_msg="Text analyzed successfully!",
        error_msg="AI Quick Log failed",
    )
    if is_done_ai and parsed_data:
        st.session_state.temp_parsed = parsed_data
        clear_background_task("quick_log_parse")

    if "temp_parsed" in st.session_state:
        tp = st.session_state.temp_parsed
        st.info(f"**We found:** {tp.get('distance', 10.0)} km by {tp.get('transport', 'Car')}, and {tp.get('diet', 'Vegetarian')} diet. Is this correct?")
        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button("✅ Yes, use this", key="confirm_yes"):
                st.session_state.transport = tp.get('transport', 'Car')
                st.session_state.distance = float(tp.get('distance', 10.0))
                st.session_state.diet = tp.get('diet', 'Vegetarian')
                del st.session_state.temp_parsed
                if user_id:
                    save_assessment_draft(user_id, st.session_state.transport, st.session_state.distance, st.session_state.get("electricity", 200.0), st.session_state.diet, st.session_state.get("flights", 0), st.session_state.get("region", "Global"))
                st.rerun()
        with c_no:
            if st.button("❌ No, cancel", key="confirm_no"):
                del st.session_state.temp_parsed
                st.rerun()

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div style='display: flex; align-items: center; gap: 8px; margin-bottom: 16px;'><span style='font-size: 24px;'>🚗</span><span style='font-size: 18px; font-weight: 700; color: #000;'>Transportation</span></div>", unsafe_allow_html=True)
        transport = st.selectbox("Primary Transport", ["Car", "Public Transport", "Bike", "Walking"], key="transport")
        distance = st.number_input("Daily Distance (km)", min_value=0.0, key="distance", step=1.0)

    with col2:
        st.markdown("<div style='display: flex; align-items: center; gap: 8px; margin-bottom: 16px;'><span style='font-size: 24px;'>⚡</span><span style='font-size: 18px; font-weight: 700; color: #000;'>Energy & Diet</span></div>", unsafe_allow_html=True)
        uploaded_bill = st.file_uploader("Upload Utility Bill (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"])
        if uploaded_bill is not None:
            # Reject oversize bills up front so the user gets feedback before
            # the background task even starts. `ocr_utils.extract_text_from_bytes`
            # enforces the same cap and is the authoritative gate, but doing it
            # here too means the OCR button never even becomes clickable for a
            # multi-hundred-MB phone dump that would have OOM-ed the worker.
            try:
                _bill_size = getattr(uploaded_bill, "size", None) or len(uploaded_bill.getvalue())
            except Exception:
                _bill_size = 0
            if _bill_size and _bill_size > 10 * 1024 * 1024:
                st.warning(
                    f"That bill is {_bill_size / (1024*1024):.1f} MB. "
                    "Please upload a PDF or image under 10 MB."
                )
            elif st.button("Extract Energy Usage"):
                file_bytes = uploaded_bill.getvalue()
                file_type = uploaded_bill.type

                # Adapter that translates the per-page progress callback the
                # OCR utility reports into the (progress, message) signature the
                # background-task framework expects. Keeping the adapter here
                # (rather than in `ocr_utils`) means the utility module stays
                # unaware of Streamlit and the background-task machinery.
                def _ocr_with_progress(file_bytes, file_type, progress_callback=None):
                    if progress_callback is None:
                        return extract_text_from_bytes(file_bytes, file_type)

                    def _on_page(done, total):
                        fraction = (done / total) if total else 1.0
                        progress_callback(fraction, f"Reading page {done}/{total}")

                    return extract_text_from_bytes(
                        file_bytes,
                        file_type,
                        on_progress=_on_page,
                    )

                submit_background_task(
                    "ocr_bill_extract",
                    _ocr_with_progress,
                    file_bytes,
                    file_type,
                    task_name="Extracting Energy Usage"
                )

        is_done_ocr, extracted_text = render_task_progress("ocr_bill_extract", success_msg="Bill OCR complete!")
        if is_done_ocr and extracted_text:
            parsed_val = parse_energy_consumption(extracted_text)
            if parsed_val is not None:
                st.session_state.extracted_kwh = float(parsed_val)
                st.session_state.electricity = float(parsed_val)
                st.success(f"Extracted {parsed_val} kWh from bill!")
            else:
                st.warning("Could not extract energy consumption. Please enter manually.")
            clear_background_task("ocr_bill_extract")

        electricity = st.number_input("Monthly Electricity (kWh)", min_value=0.0, key="electricity", step=10.0)
        diet = st.selectbox("Diet Type", ["Vegetarian", "Non-Vegetarian"], key="diet_main")

    with col3:
        st.markdown("<div style='display: flex; align-items: center; gap: 8px; margin-bottom: 16px;'><span style='font-size: 24px;'>✈️</span><span style='font-size: 18px; font-weight: 700; color: #000;'>Travel</span></div>", unsafe_allow_html=True)
        flights = st.number_input("Annual Flights", min_value=0, key="flights", step=1)
        st.info("💡 How many long-distance flights per year?")

    # Auto-save draft inputs on change
    if user_id and (st.session_state.draft_status in ['restored', 'discarded'] or not get_assessment_draft(user_id)):
        is_modified = (
            st.session_state.get("region") != "Global" or
            st.session_state.get("transport") != "Car" or
            st.session_state.get("distance") != 10.0 or
            st.session_state.get("electricity") != 200.0 or
            st.session_state.get("diet") != "Vegetarian" or
            st.session_state.get("flights") != 0
        )
        if is_modified:
            save_assessment_draft(
                user_id,
                st.session_state.get("transport", "Car"),
                st.session_state.get("distance", 10.0),
                st.session_state.get("electricity", 200.0),
                st.session_state.get("diet", "Vegetarian"),
                st.session_state.get("flights", 0),
                st.session_state.get("region", "Global")
            )

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
    with col_btn1:
        reset_btn = st.button("🔄 Reset Assessment", use_container_width=True)
        if reset_btn:
            st.session_state.show_reset_confirm = True
            st.session_state.show_reset_confirm_cf = True
            st.rerun()

    if st.session_state.get("show_reset_confirm", False) or st.session_state.get("show_reset_confirm_cf", False):
        st.warning("⚠️ Are you sure you want to reset the assessment? All entered data will be lost.")
        confirm_col, cancel_col, _ = st.columns([1, 1, 3])
        with confirm_col:
            if st.button("✅ Confirm Reset", key="confirm_reset_cf"):
                for key in DEFAULT_VALUES:
                    st.session_state[key] = DEFAULT_VALUES[key]
                st.session_state.pop("extracted_kwh", None)
                st.session_state.pop("analysis", None)
                st.session_state.show_reset_confirm = False
                st.session_state.show_reset_confirm_cf = False
                if user_id:
                    delete_assessment_draft(user_id)
                st.success("✅ Assessment form has been reset.")
                st.rerun()
        with cancel_col:
            if st.button("❌ Cancel", key="cancel_reset_cf"):
                st.session_state.show_reset_confirm = False
                st.session_state.show_reset_confirm_cf = False
                st.rerun()

    with col_btn2:
        st.caption("✔ All input fields are validated before analysis.")
        analyze_btn = st.button("🌿 Analyze My Impact", use_container_width=True)

    if analyze_btn:
        with st.spinner("🌍 Analyzing your carbon footprint..."):
            total, contributors, footprint_audit = calculate_footprint(transport, distance, electricity, diet, flights, region, return_audit=True)
        eco_score = calculate_eco_score(total, contributors)
        footprint_range = calculate_footprint_range(transport, distance, electricity, diet, flights, region)
        audit_log = generate_full_audit_log(transport, distance, electricity, diet, flights, region)        insight, recommendations = generate_recommendations(transport, electricity, diet, flights, contributors)
        # Stamp the assessment with the factor set that produced it, and
        # freeze the full calculation context into an immutable snapshot, so
        # the result stays reproducible even after factors, category
        # weights, or the eco-score formula change later.
        snapshot = build_assessment_snapshot(
            inputs=footprint_audit.get("inputs", {}),
            footprint_audit=footprint_audit,
            contributors=contributors,
            total=total,
            eco_score=eco_score,
        )
        save_assessment(
            user_id, transport, distance, electricity, diet, flights, total, eco_score,
            factor_version=footprint_audit.get("factor_version"),
            snapshot_json=serialize_snapshot(snapshot),
        )        if user_id:
            delete_assessment_draft(user_id)
        gf.check_badge_eligibility(user_id)
        st.session_state.analysis = {
            "transport": transport, "distance": distance, "electricity": electricity,
            "diet": diet, "flights": flights, "total": total, "eco_score": eco_score,
            "contributors": contributors, "insight": insight, "recommendations": recommendations,
            "audit_log": audit_log, "footprint_range": footprint_range,
        }
if "analysis" in st.session_state:
    data = st.session_state.analysis

    st.success("✅ Analysis completed!")
    st.markdown("---")

    st.markdown("### 👤 Your Inputs")
    c1, c2 = st.columns(2)

    with c1:
        st.write(f"**🚗 Transport:** {data['transport']}")
        st.write(f"**📍 Daily Distance:** {data['distance']} km")
        st.write(f"**⚡ Electricity:** {data['electricity']} kWh")

    with c2:
        st.write(f"**🥗 Diet:** {data['diet']}")
        st.write(f"**✈️ Annual Flights:** {data['flights']}")

    st.markdown("---")
    st.markdown(
        "<div class='section-header'>📊 Your Carbon Footprint Analysis</div>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        fr = data.get("footprint_range")
        if fr:
            st.metric(
                "🌍 Total Footprint (estimated)",
                f"{fr['central_kg']:.2f} kg CO₂",
                help=(
                    f"Estimated range: {fr['low_kg']:.2f}–{fr['high_kg']:.2f} kg CO₂ "
                    f"(±{fr['uncertainty_percent']:.0f}%, factor set {fr['factor_version']})"
                ),
            )
            st.caption(f"📊 Estimated range: {fr['low_kg']:.2f}–{fr['high_kg']:.2f} kg CO₂")
            top = fr["top_uncertainty_contributors"][0]
            st.caption(
                f"🔍 Biggest uncertainty driver: {top['category'].title()} "
                f"({top['share_percent']:.0f}% of the range)"
            )
        else:
            st.metric("🌍 Total Footprint", f"{data['total']:.2f} kg CO₂")
    with col2:
        st.metric("🌱 Eco Score", f"{data['eco_score']}/100")

    st.markdown("---")
    st.subheader("📅 Monthly Carbon Footprint Summary")

    current_month = data["total"]
    last_month = current_month * 1.12
    change = ((current_month - last_month) / last_month) * 100

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Monthly Emissions",
            f"{current_month:.2f} kg CO₂"
        )

    with col2:
        st.metric(
            "Change vs Last Month",
            f"{change:.1f}%",
            delta=f"{change:.1f}%"
        )

    with col3:
        st.metric(
            "Average Eco Score",
            f"{data['eco_score']}/100"
        )

    with col4:
        progress = min(data["eco_score"], 100)
        st.metric(
            "Eco Progress",
            f"{progress}%"
        )

    st.markdown("### 📈 Monthly Trend")

    trend = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "CO₂": [340, 315, 300, 285, 270, current_month]
    })

    fig = px.line(
        trend,
        x="Month",
        y="CO₂",
        markers=True,
        title="Monthly Carbon Footprint Trend"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 🌊 Carbon Emission Flow (Sankey Diagram)")
    st.caption("See how each activity category flows into your total carbon footprint.")
    sankey_fig = create_emission_sankey(data["contributors"], data["total"])
    st.plotly_chart(sankey_fig, use_container_width=True)

    st.markdown("### 🗺️ Carbon Footprint Breakdown (Tree Map)")
    st.caption("See which categories take up the largest share of your total footprint.")
    treemap_fig = create_emission_treemap(data["contributors"], data["total"])
    st.plotly_chart(treemap_fig, use_container_width=True)

    st.markdown("### 💡 AI Insight")
    st.info(data["insight"])

    st.markdown("### 🧠 Explainable AI (XAI) Recommendation & Eco Score Panel")
    with st.expander("🔍 View AI Reasoning & Feature Importance Breakdown", expanded=False):
        st.markdown("#### 📊 Feature Importance Breakdown (Emissions Contribution)")
        contribs = data["contributors"]
        tot = data["total"] if data["total"] > 0 else 1.0
        feat_df = pd.DataFrame([
            {
                "Category": cat,
                "Emissions (kg CO₂)": val,
                "Contribution Share (%)": round((val / tot) * 100, 1)
            }
            for cat, val in contribs.items()
        ]).sort_values(by="Emissions (kg CO₂)", ascending=False)
        
        fig_feat = px.bar(
            feat_df,
            x="Contribution Share (%)",
            y="Category",
            orientation="h",
            text="Contribution Share (%)",
            color="Contribution Share (%)",
            color_continuous_scale="Viridis",
            title="Feature Importance by Category Contribution (%)"
        )
        fig_feat.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_feat, use_container_width=True)

        st.markdown("#### 💡 Transparent Recommendation Reasoning")
        st.write(
            f"The primary driver for your recommendation stack is **{max(contribs, key=contribs.get)}**, "
            f"accounting for **{contribs[max(contribs, key=contribs.get)]:.2f} kg CO₂/year** "
            f"({(contribs[max(contribs, key=contribs.get)]/tot)*100:.1f}% of total)."
        )
        st.markdown("""
- **Transport Impact**: Daily distance x Mode emission factor x 365 days.
- **Electricity Impact**: Monthly kWh x Grid emission factor x 12 months.
- **Diet Impact**: Annual baseline emission factor based on dietary choices.
- **Flight Impact**: Annual flight count x Average per-flight emission factor.
        """)

        st.markdown("#### 🎯 Eco Score Sigmoid Curve Breakdown")
        audit_log = data.get("audit_log", {})
        score_audit = audit_log.get("eco_score_audit", {})
        if "category_scores" in score_audit and score_audit["category_scores"]:
            cat_scores_df = pd.DataFrame([
                {
                    "Category": cat,
                    "Weight": details.get("weight"),
                    "Category Footprint (kg)": details.get("cat_total_kg"),
                    "Raw Score (0-100)": round(details.get("raw_cat_score", 0), 1),
                    "Weighted Score Contribution": round(details.get("weighted_component", 0), 1)
                }
                for cat, details in score_audit["category_scores"].items()
            ])
            st.dataframe(cat_scores_df, use_container_width=True)
            st.caption(f"Final Weighted Eco Score: **{data['eco_score']} / 100**")

    st.markdown("### 🌱 Recommendations")
    for rec in data["recommendations"]:
        st.success(rec)

    st.markdown("### 🎯 Minimal Change, Maximum Impact")
    ranked_changes = analyze_minimal_change(
        data["transport"], data["distance"], data["electricity"],
        data["diet"], data["flights"], st.session_state.get("region", "Global"),
        data["total"]
    )
    if ranked_changes:
        best = ranked_changes[0]
        st.success(
            f"⭐ **Best small change:** {best['change']}\n\n"
            f"**Estimated savings:** {best['savings']:.2f} kg CO₂/year "
            f"(Effort: {best['effort']})\n\n"
            f"**Why it works:** {best['reason']}"
        )
        with st.expander("📊 See all ranked lifestyle changes"):
            for c in ranked_changes:
                st.write(
                    f"- **{c['change']}** — Effort: {c['effort']}, "
                    f"Estimated savings: {c['savings']:.2f} kg CO₂/year"
                )
    else:
        st.info("No further small changes detected — your lifestyle is already optimized!")

    st.markdown("---")
    st.markdown("### 🌍 Eco Clone Simulator")
    st.caption("What the world would look like if everyone lived the way you do.")
    render_eco_clone_simulator(data["total"], data["contributors"])

    st.markdown("### 🔍 Calculation Audit Log & Step-by-Step Transparency")
    with st.expander("📋 View Calculation Audit Log"):
        audit = data.get("audit_log", {})
        fp_audit = audit.get("footprint_audit", {})
        steps = fp_audit.get("intermediate_calculations", {})
        factors = fp_audit.get("emission_factors", {})

        st.markdown("#### 1. Category Emission Calculations")
        for cat, details in steps.items():
            st.markdown(f"**{cat}**: `{details.get('formula')}`")
            st.markdown(
                f"↳ *Calculation*: `{details.get('expression')}` = **{details.get('rounded_result_kg')} kg CO₂**"
            )

        st.markdown("#### 2. Emission Factors Used")
        st.json(factors)

        st.markdown("#### 3. Eco Score Continuous Sigmoid Audit")
        score_audit = audit.get("eco_score_audit", {})
        st.json(score_audit.get("category_scores", {}))

        audit_json = export_audit_log_json(audit) if audit else "{}"

        st.download_button(
            label="📥 Export Calculation Audit Log (JSON)",
            data=audit_json,
            file_name="carbon_calculation_audit_log.json",
            mime="application/json",
            key="download_audit_log_btn"
        )

else:
    st.markdown("""
        <style>
        @keyframes bounce {
            0%,100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .empty-card{
            background: linear-gradient(135deg,#132238,#0f172a);
            border:1px solid rgba(74,222,128,0.25);
            border-radius:20px;
            padding:45px 35px;
            text-align:center;
            box-shadow:0 12px 30px rgba(0,0,0,.25);
            margin-top:20px;
        }

        .empty-title{
            font-size:32px;
            font-weight:800;
            color:#4ade80;
            margin-bottom:12px;
        }

        .empty-subtitle{
            color:#cbd5e1;
            font-size:17px;
            line-height:1.8;
            max-width:650px;
            margin:auto;
        }

        .empty-checklist{
            margin-top:28px;
            text-align:left;
            display:inline-block;
            color:#e2e8f0;
            font-size:16px;
            line-height:2;
        }

        .empty-icon{
            font-size:72px;
            animation:bounce 2s infinite;
            margin-bottom:20px;
        }

        .tip-box{
            margin-top:28px;
            background:rgba(74,222,128,.08);
            border-left:5px solid #4ade80;
            padding:18px;
            border-radius:12px;
            color:#d1fae5;
            font-size:15px;
        }
        </style>

        <div class="empty-card">

            <div class="empty-icon">🌱</div>

            <div class="empty-title">
                Welcome to Your Eco Journey
            </div>

            <div class="empty-subtitle">
                Complete your lifestyle profile above and click
                <b>"Analyze My Impact"</b> to generate your first carbon footprint report.
            </div>

            <div class="empty-checklist">
                ✅ Personalized Eco Score<br>
                ✅ Carbon Footprint Dashboard<br>
                ✅ AI Insights & Recommendations<br>
                ✅ Emission Charts & Trends<br>
                ✅ Downloadable PDF Report
            </div>

            <div class="tip-box">
                💡 <b>Tip:</b> Even small lifestyle changes can make a meaningful impact over time.
                Start with your first assessment and track your progress.
            </div>

        </div>
        """, unsafe_allow_html=True)


    st.markdown("---")

    st.markdown("## 🌱 What You'll Unlock")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.success("📊 Carbon Footprint Dashboard")
        st.caption("Track your yearly emissions.")

    with col2:
        st.success("🤖 AI Insights")
        st.caption("Get AI-powered analysis.")

    with col3:
        st.success("💡 Smart Recommendations")
        st.caption("Receive personalized eco tips.")


    st.markdown("---")

    st.markdown("## 🚀 How It Works")

    st.info("1️⃣ Fill in your lifestyle details")
    st.info("2️⃣ Click **Analyze My Impact**")
    st.info("3️⃣ Review your carbon footprint")
    st.info("4️⃣ Get personalized AI recommendations")
    st.info("5️⃣ Download your PDF report")

    st.markdown("---")
    st.markdown("## ✨ Why Use EcoBuddy AI?")

    feature1, feature2 = st.columns(2)

    with feature1:
        st.success("📈 Track your carbon footprint over time")
        st.success("🤖 AI-powered personalized insights")
        st.success("📄 Export reports as PDF")

    with feature2:
        st.success("🌍 Build sustainable habits")
        st.success("📊 Interactive charts and trends")
        st.success("🏆 Improve your Eco Score")


    st.markdown("---")

    st.markdown("## 💡 Eco Tips")

    tip_col1, tip_col2 = st.columns(2)

    with tip_col1:
        st.success("🚶 Walk or cycle for short trips")
        st.success("💧 Save water whenever possible")
        st.success("♻️ Recycle household waste")

    with tip_col2:
        st.success("⚡ Turn off unused appliances")
        st.success("🚌 Use public transport")
        st.success("🌱 Plant more trees")

    
        st.markdown("---")

    st.markdown(
        """
        ### 🌍 Every small action matters

        Your sustainability journey starts with a single assessment.
        Complete your profile today and discover simple ways to reduce
        your carbon footprint and make a positive environmental impact.
        """
    )

    st.markdown("---")

    st.markdown("## 🚀 Ready to Begin?")

    st.success(
        "Complete the lifestyle form above and click **Analyze My Impact** "
        "to generate your first carbon footprint assessment."
    )

with tab_forecast:
    st.markdown("<div class='section-header'>📈 Carbon Emissions Forecasting</div>", unsafe_allow_html=True)
    st.write("Based on your historical logs, here is a projection of your future carbon footprint.")
    
    assessments = get_assessments(user_id)
    if len(assessments) < 5:
        st.info("We need at least 5 logs to generate a reliable forecast. Keep logging your footprint!")
    else:
        try:
            import pandas as pd
            import plotly.graph_objects as go
            from statsmodels.tsa.arima.model import ARIMA
            import warnings
            warnings.filterwarnings('ignore')
            
            df = pd.DataFrame(assessments, columns=['id', 'date', 'transport', 'distance', 'electricity', 'diet', 'flights', 'footprint', 'eco_score'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            ts_data = df['footprint'].values
            
            forecast_line, conf_lower, conf_upper = compute_arima_forecast(tuple(ts_data))
            
            hist_x = list(range(1, len(ts_data) + 1))
            future_x = list(range(len(ts_data), len(ts_data) + len(forecast_line)))
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist_x, y=list(ts_data), mode='lines+markers', name='Historical Data',
                line=dict(color='#4ade80', width=3)
            ))
            
            fig.add_trace(go.Scatter(
                x=future_x, y=forecast_line, mode='lines+markers', name='Forecast',
                line=dict(color='#f43f5e', width=3, dash='dot')
            ))
            
            fig.add_trace(go.Scatter(
                x=future_x + future_x[::-1],
                y=list(conf_upper) + list(conf_lower)[::-1],
                fill='toself',
                fillcolor='rgba(244, 63, 94, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name='95% Confidence Interval',
                showlegend=True
            ))
            
            fig.update_layout(
                title='Carbon Footprint Forecast',
                xaxis_title='Assessment #',
                yaxis_title='CO₂ Emissions (kg)',
                template='plotly_dark',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            if forecast_line[-1] > ts_data[-1]:
                st.warning("Your footprint is projected to increase. Try adopting more eco-friendly habits!")
            else:
                st.success("Great job! Your footprint is on a downward trend. Keep it up!")
        except Exception as e:
            st.error(f"Error generating forecast: {e}")
st.subheader("🌱 Carbon Budget Planner")
with tab_clone:

    st.markdown("<div class='section-header'>🌍 Eco Clone Simulator</div>", unsafe_allow_html=True)

    st.write(
        "Imagine if everyone on Earth lived exactly like you. "
        "This simulator estimates the impact on global carbon emissions."
    )

    if "analysis" not in st.session_state:

        st.info("Please complete a Carbon Footprint Assessment first.")

    else:
                user_footprint = data["total"]

                data = st.session_state.analysis
budget_type=st.selectbox(
    "Budget Type",
    ["Monthly","Yearly"]
)

budget_limit=st.number_input(
    "Carbon Budget (kg CO₂)",
    min_value=0.0,
    step=10.0
)

if st.button("Save Budget"):
    save_carbon_budget(
        st.session_state.user["id"],
        budget_type,
        budget_limit
    )

    st.success("Budget saved successfully.")
if progress>=0.9:
    st.error("⚠ You are close to exceeding your carbon budget.")

elif progress>=0.7:
    st.warning("Approaching your carbon budget.")

else:
    st.success("Within budget.")
forecast=total*1.10

st.metric(
    "Forecast",
    f"{forecast:.2f} kg CO₂"
)
budget = get_carbon_budget(
    st.session_state.user["id"]
)

if budget:

    st.info(
        f"Current Budget: {budget[1]} kg CO₂ ({budget[0]})"
    )
budget = get_carbon_budget(
    st.session_state.user["id"]
)

if budget:

    budget_limit = budget[1]

    used = total

    remaining = max(
        budget_limit - used,
        0
    )

    progress = min(
        used / budget_limit,
        1.0
    )

    st.subheader("📊 Budget Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Budget",
            f"{budget_limit:.2f} kg"
        )

    with col2:
        st.metric(
            "Remaining",
            f"{remaining:.2f} kg"
        )

    st.progress(progress)
if progress >= 0.9:

    st.error(
        "⚠ You are very close to exceeding your carbon budget."
    )

elif progress >= 0.7:

    st.warning(
        "Approaching your carbon budget."
    )

else:

    st.success(
        "Great! You are within your carbon budget."
    )
forecast = used * 1.10

st.metric(
    "Estimated End-of-Month Emissions",
    f"{forecast:.2f} kg CO₂"
)

if forecast > budget_limit:

    st.error(
        "Forecast indicates you may exceed your budget."
    )

else:

    st.success(
        "Forecast indicates you are likely to stay within budget."
    )
col1,col2,col3 = st.columns(3)

with col1:
    st.metric(
        "Budget",
        f"{budget_limit:.2f}"
    )

with col2:
    st.metric(
        "Used",
        f"{total:.2f}"
    )

with col3:
    st.metric(
        "Remaining",
        f"{remaining:.2f}"
    )
st.progress(progress)
st.subheader("Suggestions")

if forecast > budget_limit:

    st.write("• Reduce electricity consumption")

    st.write("• Prefer walking or cycling")

    st.write("• Use public transport")

    st.write("• Reduce unnecessary flights")

else:

    st.success(
        "You're on track to stay within your carbon budget."
    )