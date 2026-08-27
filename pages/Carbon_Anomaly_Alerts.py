"""
Carbon Anomaly Alerts Page.
Streamlit page featuring an interactive timeline of footprint history, highlighted anomaly markers, and an alert resolution dashboard.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from anomaly_detector import AnomalyDetector
from alert_manager import AlertManager
from database import get_assessments_for_anomaly_detection, save_alert_resolution

st.set_page_config(page_title="Carbon Anomaly Alerts", page_icon="📈", layout="wide")

st.title("📈 AI-Powered Carbon Footprint Anomaly Detection")
st.markdown(
    "Intelligent analysis of your historical carbon footprint to identify unusual spikes and provide actionable corrective alerts."
)

# Initialize components
detector = AnomalyDetector(z_score_threshold=2.0)
alert_manager = AlertManager()

# Fetch historical data (Mocked for demonstration if DB is empty)
# In a real scenario, this fetches from the user's actual assessment history
historical_data = get_assessments_for_anomaly_detection("demo_user")

if not historical_data:
    # Fallback mock data for demonstration purposes
    historical_data = [
        {"date": "2023-01", "carbon_kg": 450},
        {"date": "2023-02", "carbon_kg": 460},
        {"date": "2023-03", "carbon_kg": 440},
        {"date": "2023-04", "carbon_kg": 455},
        {"date": "2023-05", "carbon_kg": 1200},  # Anomaly: Flight
        {"date": "2023-06", "carbon_kg": 470},
        {"date": "2023-07", "carbon_kg": 465},
        {"date": "2023-08", "carbon_kg": 850},  # Anomaly: High energy usage
    ]

# Process data
analyzed_data = detector.detect_anomalies(historical_data)
alerts = [
    alert_manager.generate_alert(entry)
    for entry in analyzed_data
    if entry.get("is_anomaly", False)
]

# --- Dashboard Layout ---
tab1, tab2 = st.tabs(["📊 Footprint Timeline", "🔔 Active Alerts"])

with tab1:
    st.subheader("Historical Footprint with Anomaly Markers")

    df = pd.DataFrame(analyzed_data)

    # Create Plotly figure
    fig = go.Figure()

    # Normal data points
    normal_df = df[~df["is_anomaly"]]
    fig.add_trace(
        go.Scatter(
            x=normal_df["date"],
            y=normal_df["carbon_kg"],
            mode="lines+markers",
            name="Normal Footprint",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=8),
        )
    )

    # Anomalous data points
    anomaly_df = df[df["is_anomaly"]]
    fig.add_trace(
        go.Scatter(
            x=anomaly_df["date"],
            y=anomaly_df["carbon_kg"],
            mode="markers",
            name="Anomaly Detected",
            marker=dict(color="#dc3545", size=12, symbol="x"),
        )
    )

    # Mean baseline line
    if not df.empty:
        mean_val = df["mean_baseline"].iloc[0]
        fig.add_hline(
            y=mean_val,
            line_dash="dash",
            line_color="gray",
            annotation_text=f"Baseline Mean: {mean_val:.0f} kg",
        )

    fig.update_layout(
        title="Monthly Carbon Footprint Trajectory",
        xaxis_title="Month",
        yaxis_title="Carbon Footprint (kg CO₂e)",
        template="plotly_white",
        hovermode="x unified",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 📋 Data Summary")
    st.dataframe(
        df[["date", "carbon_kg", "z_score", "is_anomaly"]],
        use_container_width=True,
        hide_index=True,
    )

with tab2:
    st.subheader("Active Anomaly Alerts")

    if not alerts:
        st.success(
            "✅ No anomalies detected. Your carbon footprint is consistently within your normal baseline range!"
        )
    else:
        for i, alert in enumerate(alerts):
            with st.expander(
                f"{alert['severity_icon']} {alert['date']}: High Carbon Spike ({alert['deviation_pct']}% above baseline)",
                expanded=True,
            ):
                col1, col2 = st.columns([1, 2])

                with col1:
                    st.markdown(
                        f"**Severity:** <span style='color:{alert['severity_color']}; font-weight:bold;'>{alert['severity'].upper()}</span>",
                        unsafe_allow_html=True,
                    )
                    st.metric(
                        "Footprint",
                        f"{alert['carbon_kg']} kg",
                        delta=f"+{alert['deviation_pct']}%",
                    )
                    st.metric("Z-Score", f"{alert['z_score']}")

                with col2:
                    st.markdown("🔍 **Simulated Root Cause Hypothesis:**")
                    st.info(alert["hypothesis"])

                    st.markdown("💡 **Recommended Actions:**")
                    for rec in alert["recommendations"]:
                        st.markdown(f"- {rec}")

                if st.button("✅ Mark as Resolved", key=f"resolve_{i}"):
                    save_alert_resolution(
                        "demo_user", alert["date"], alert["carbon_kg"]
                    )
                    st.success("Alert marked as resolved. Keep up the good work!")
                    st.rerun()
