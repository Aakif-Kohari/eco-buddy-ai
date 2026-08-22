import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plugins import get_plugin
from plugins.device_lifecycle_engine import DeviceLifecycleEngine
from plugins.digital_screen_time_parser import ScreenTimeParser
from plugins.digital_ml_forecaster import DigitalMLForecaster

# Page configuration
st.set_page_config(page_title="Digital Footprint Pro", page_icon="💻", layout="wide")

@st.cache_resource
def load_plugin():
    return get_plugin("digital_footprint")

plugin = load_plugin()
if not plugin:
    st.error("Digital Footprint plugin not found!")
    st.stop()

st.title("💻 Advanced Digital Footprint Ecosystem")
st.markdown("A complete subsystem featuring direct data imports, lifecycle modeling, and ML predictions.")

# --- SIDEBAR & STATE MANAGEMENT ---
if 'parsed_inputs' not in st.session_state:
    st.session_state.parsed_inputs = None

st.sidebar.header("1. Import Real Data")
st.sidebar.info("Upload your Apple Screen Time JSON or Google Takeout CSV to auto-fill your habits.")
uploaded_file = st.sidebar.file_uploader("Upload Screen Time Data", type=['json', 'csv'])

if uploaded_file is not None:
    raw_text = uploaded_file.getvalue().decode("utf-8")
    format_type = "apple_json" if uploaded_file.name.endswith('.json') else "google_csv"
    
    try:
        parser = ScreenTimeParser(raw_text, format_type)
        parser.parse()
        st.session_state.parsed_inputs = parser.get_daily_averages_for_plugin()
        st.sidebar.success("✅ Data parsed successfully!")
    except Exception as e:
        st.sidebar.error(f"Failed to parse: {str(e)}")
        
if st.sidebar.button("Load Mock Screen Time Data"):
    mock_data = ScreenTimeParser.generate_mock_apple_data(days=14)
    parser = ScreenTimeParser(mock_data, "apple_json")
    parser.parse()
    st.session_state.parsed_inputs = parser.get_daily_averages_for_plugin()
    st.sidebar.success("✅ Mock data loaded!")

st.sidebar.markdown("---")
st.sidebar.header("2. Manual Adjustments")

# Pre-fill with parsed inputs if available
p_inputs = st.session_state.parsed_inputs or {}

user_inputs = {}
with st.sidebar.expander("🌍 Infrastructure & Hardware"):
    user_inputs["region"] = st.selectbox("Region", ["Global_Average", "USA", "European_Union", "United_Kingdom", "India"])
    user_inputs["primary_device"] = st.selectbox("Device", ["Smartphone", "Tablet", "Laptop", "Desktop_PC"])
    user_inputs["primary_network"] = st.selectbox("Network", ["WiFi", "4G", "5G", "Wired"])
    device_age = st.slider("Device Age (Years)", 0.0, 10.0, 2.0, 0.5)
    charge_cycles = st.slider("Daily Charge Cycles", 0.0, 3.0, 1.0, 0.1)

with st.sidebar.expander("🎬 Streaming & Social Media"):
    user_inputs["streaming_hours_daily"] = st.slider("Streaming (hrs)", 0.0, 24.0, p_inputs.get("streaming_hours_daily", 2.0))
    user_inputs["streaming_resolution"] = st.select_slider("Resolution", options=["720p", "1080p", "4K"], value="1080p")
    user_inputs["social_media_hours_daily"] = st.slider("Social Media (hrs)", 0.0, 24.0, p_inputs.get("social_media_hours_daily", 1.5))
    user_inputs["web_browsing_hours_daily"] = st.slider("Web Browsing (hrs)", 0.0, 24.0, p_inputs.get("web_browsing_hours_daily", 4.0))

with st.sidebar.expander("☁️ Cloud, Work & AI"):
    user_inputs["cloud_storage_gb"] = st.number_input("Cloud Storage (GB)", min_value=0.0, value=50.0)
    user_inputs["cloud_provider"] = st.selectbox("Cloud Provider", ["AWS", "GCP", "Azure", "Generic"])
    user_inputs["emails_text_daily"] = st.number_input("Text Emails", min_value=0.0, value=p_inputs.get("emails_text_daily", 30.0))
    user_inputs["ai_queries_daily"] = st.number_input("AI Queries", min_value=0.0, value=p_inputs.get("ai_queries_daily", 5.0))
    user_inputs["crypto_tx_monthly"] = st.number_input("Crypto Tx", min_value=0.0, value=0.0)

# Calculate
if st.sidebar.button("Run Advanced Engine", type="primary", use_container_width=True):
    with st.spinner("Processing Data, Hardware, and ML Models..."):
        
        # 1. Base Operations
        result = plugin.calculate(user_inputs)
        recs = plugin.get_recommendations(result)
        
        # 2. Lifecycle Engine
        lifecycle_engine = DeviceLifecycleEngine(user_inputs["primary_device"], device_age, charge_cycles)
        lifecycle_report = lifecycle_engine.generate_lifecycle_report()
        
        # 3. Generate Mock Historical Data for ML (since we don't have a real DB hooked up here yet)
        import random
        from datetime import datetime, timedelta
        hist_data = []
        base_co2 = result.total / 365.0
        for i in range(30, 0, -1):
            date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            # Create a slight upward trend with noise
            noise = random.uniform(-0.1, 0.3)
            hist_data.append({"date": date_str, "daily_kg_co2": base_co2 + noise + (i * 0.01)})
        
        ml_forecaster = DigitalMLForecaster(pd.DataFrame(hist_data))
        forecast = ml_forecaster.predict_future_emissions(days_ahead=14)
        anomalies = ml_forecaster.detect_anomalies()

        # --- UI DISPLAY ---
        st.subheader("Your Holistic Digital Footprint")
        holistic_total = result.total + lifecycle_report["amortized_carbon_per_year"]
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Holistic Carbon Footprint", f"{round(holistic_total, 1)} kg CO₂e/yr")
        col2.metric("Equivalent to", f"{round(holistic_total / 8.9, 1)} gallons of gas")
        col3.metric("ML Trajectory", forecast["trajectory"])
        
        st.divider()
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Operations", "🔋 Hardware Lifecycle", "🤖 ML Analytics", "💡 Action Plan"])
        
        with tab1:
            contrib_data = {"Category": list(result.contributors.keys()), "kg CO2e": list(result.contributors.values())}
            df_plot = pd.DataFrame(contrib_data).sort_values(by="kg CO2e", ascending=False)
            fig_bar = px.bar(df_plot, x='kg CO2e', y='Category', orientation='h', title="Operational Impact")
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with tab2:
            st.markdown(f"**Device:** {lifecycle_report['device']} | **Age:** {lifecycle_report['age_years']} years")
            health = lifecycle_report['battery_health']
            st.progress(health, text=f"Estimated Battery Health: {int(health)}%")
            
            analysis = lifecycle_report['upgrade_analysis']
            st.info(f"**AI Recommendation:** {analysis['recommendation']}")
            if analysis['carbon_saved_by_not_upgrading'] > 0:
                st.success(f"🌱 Saves **{analysis['carbon_saved_by_not_upgrading']:.1f} kg CO₂e**!")
                
        with tab3:
            st.markdown("### Scikit-Learn Predictive Modeling")
            if forecast["success"]:
                st.warning(forecast["ai_warning"])
                
                df_hist = ml_forecaster.df
                df_fore = pd.DataFrame(forecast["forecast_series"])
                df_fore["date"] = pd.to_datetime(df_fore["date"])
                
                fig_ml = go.Figure()
                fig_ml.add_trace(go.Scatter(x=df_hist['date'], y=df_hist['daily_kg_co2'], mode='lines', name='Historical'))
                fig_ml.add_trace(go.Scatter(x=df_fore['date'], y=df_fore['predicted_kg_co2'], mode='lines+markers', name='Predicted Trend', line=dict(dash='dash')))
                st.plotly_chart(fig_ml, use_container_width=True)
                
                if anomalies:
                    st.error(f"Detected {len(anomalies)} anomalies in your past usage. Did you binge watch Netflix?")
                    for a in anomalies:
                        st.write(f"- {a['message']}")
            else:
                st.error("ML Model failed to train.")

        with tab4:
            for i, rec in enumerate(recs):
                st.success(f"**Tip {i+1}:** {rec}")
else:
    st.info("👈 Upload data or adjust habits, then click 'Run Advanced Engine'.")
