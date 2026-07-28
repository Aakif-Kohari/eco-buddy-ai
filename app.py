import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from database import init_db, save_assessment, get_assessments, get_assessments_df
from emissions import calculate_footprint, calculate_eco_score
from recommendations import generate_recommendations


# -------------------------
# INIT
# -------------------------
init_db()

st.set_page_config(
    page_title="EcoBuddy 🌱",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)


# -------------------------
# ADVANCED STYLING
# -------------------------
st.markdown("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        background: linear-gradient(-45deg, #0a2818, #0f3d1f, #1a5c2a, #0d4a27);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        min-height: 100vh;
        font-family: 'Inter', sans-serif;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* TITLE AND HEADER ANIMATIONS */
    .title {
        font-size: 64px;
        font-weight: 900;
        background: linear-gradient(135deg, #22c55e 0%, #4ade80 50%, #86efac 100%);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 12px;
        text-align: center;
        letter-spacing: -1px;
        animation: slideDown 0.8s cubic-bezier(0.23, 1, 0.320, 1), 
                   shimmer 3s ease-in-out infinite;
    }
    
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes shimmer {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .subtitle {
        color: #e5e7eb;
        margin-bottom: 28px;
        text-align: center;
        font-size: 18px;
        font-weight: 400;
        letter-spacing: 0.5px;
        animation: fadeInUp 0.8s 0.2s cubic-bezier(0.23, 1, 0.320, 1) both;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* METRIC CARDS - Enhanced with Animation */
    .metric-card {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.12) 0%, rgba(74, 222, 128, 0.08) 100%);
        padding: 28px;
        border-radius: 20px;
        border: 1.5px solid rgba(74, 222, 128, 0.35);
        margin-bottom: 14px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.25), 
                    inset 0 1px 2px rgba(255, 255, 255, 0.05);
        transition: all 0.4s cubic-bezier(0.23, 1, 0.320, 1);
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
        animation: popIn 0.6s cubic-bezier(0.23, 1, 0.320, 1);
    }
    
    @keyframes popIn {
        0% {
            opacity: 0;
            transform: scale(0.9) translateY(20px);
        }
        100% {
            opacity: 1;
            transform: scale(1) translateY(0);
        }
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    }
    
    .metric-card::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
        transition: all 0.5s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-12px);
        box-shadow: 0 24px 48px rgba(34, 197, 94, 0.35),
                    inset 0 1px 2px rgba(255, 255, 255, 0.1);
        border-color: rgba(74, 222, 128, 0.7);
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.18) 0%, rgba(74, 222, 128, 0.12) 100%);
    }
    
    .metric-card:hover::after {
        right: -20%;
        top: -20%;
    }
    
    /* CARDS - Enhanced */
    .card {
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.5) 0%, rgba(55, 65, 81, 0.3) 100%);
        padding: 24px;
        border-radius: 18px;
        border: 1.5px solid rgba(74, 222, 128, 0.25);
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2),
                    inset 0 1px 2px rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(12px);
        transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1);
        position: relative;
        animation: slideInLeft 0.6s cubic-bezier(0.23, 1, 0.320, 1);
    }
    
    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
    }
    
    .card:hover {
        border-color: rgba(74, 222, 128, 0.5);
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.65) 0%, rgba(55, 65, 81, 0.45) 100%);
        transform: translateY(-6px);
        box-shadow: 0 16px 40px rgba(74, 222, 128, 0.2),
                    inset 0 1px 2px rgba(255, 255, 255, 0.08);
    }
    
    /* HIGHLIGHT CARDS */
    .card-highlight {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(74, 222, 128, 0.08) 100%);
        padding: 28px;
        border-radius: 20px;
        border: 2px solid rgba(74, 222, 128, 0.45);
        margin-bottom: 16px;
        box-shadow: 0 12px 40px rgba(34, 197, 94, 0.2),
                    inset 0 1px 3px rgba(255, 255, 255, 0.1);
        position: relative;
        backdrop-filter: blur(12px);
        animation: fadeInScale 0.6s 0.2s cubic-bezier(0.23, 1, 0.320, 1) both;
    }
    
    @keyframes fadeInScale {
        from {
            opacity: 0;
            transform: scale(0.95);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    
    .card-highlight::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(34, 197, 94, 0.6), transparent);
        animation: shimmerLine 2s ease-in-out infinite;
    }
    
    @keyframes shimmerLine {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 1; }
    }
    
    /* BADGES - Enhanced */
    .badge {
        display: inline-block;
        padding: 14px 32px;
        border-radius: 50px;
        font-weight: 800;
        font-size: 17px;
        background: linear-gradient(135deg, #22c55e, #4ade80);
        color: #0a2818;
        box-shadow: 0 8px 24px rgba(34, 197, 94, 0.35),
                    inset 0 1px 2px rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.15);
        letter-spacing: 0.5px;
        animation: bounceIn 0.6s 0.3s cubic-bezier(0.68, -0.55, 0.265, 1.55) both;
    }
    
    @keyframes bounceIn {
        0% {
            opacity: 0;
            transform: scale(0.3);
        }
        50% {
            opacity: 1;
            transform: scale(1.05);
        }
        100% {
            transform: scale(1);
        }
    }
    
    .badge-champion {
        background: linear-gradient(135deg, #f59e0b, #fbbf24);
        color: #78350f;
        box-shadow: 0 8px 24px rgba(245, 158, 11, 0.35);
    }
    
    .badge-guardian {
        background: linear-gradient(135deg, #22c55e, #4ade80);
        color: #0a2818;
        box-shadow: 0 8px 24px rgba(34, 197, 94, 0.35);
    }
    
    .badge-learner {
        background: linear-gradient(135deg, #3b82f6, #60a5fa);
        color: #082f49;
        box-shadow: 0 8px 24px rgba(59, 130, 246, 0.35);
    }
    
    .badge-high {
        background: linear-gradient(135deg, #ef4444, #f87171);
        color: #7c2d12;
        box-shadow: 0 8px 24px rgba(239, 68, 68, 0.35);
    }
    
    /* INPUT SECTION */
    .input-section {
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.4) 0%, rgba(55, 65, 81, 0.2) 100%);
        padding: 36px;
        border-radius: 22px;
        border: 1.5px solid rgba(74, 222, 128, 0.25);
        margin-bottom: 24px;
        backdrop-filter: blur(12px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15),
                    inset 0 1px 2px rgba(255, 255, 255, 0.03);
        position: relative;
        animation: slideInUp 0.8s 0.1s cubic-bezier(0.23, 1, 0.320, 1) both;
    }
    
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .input-section::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        border-radius: 22px 22px 0 0;
    }
    
    /* SECTION HEADERS */
    .section-header {
        font-size: 32px;
        font-weight: 900;
        background: linear-gradient(135deg, #22c55e 0%, #4ade80 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-top: 36px;
        margin-bottom: 24px;
        letter-spacing: -0.5px;
        position: relative;
        animation: fadeInLeft 0.6s cubic-bezier(0.23, 1, 0.320, 1);
    }
    
    @keyframes fadeInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .section-header::after {
        content: '';
        display: block;
        width: 60px;
        height: 3px;
        background: linear-gradient(90deg, #22c55e, #4ade80);
        margin-top: 12px;
        border-radius: 2px;
        animation: expandWidth 0.6s 0.2s cubic-bezier(0.23, 1, 0.320, 1) both;
    }
    
    @keyframes expandWidth {
        from {
            width: 0;
        }
        to {
            width: 60px;
        }
    }
    
    /* PROGRESS BAR */
    .progress-bar {
        width: 100%;
        height: 14px;
        background: rgba(74, 222, 128, 0.08);
        border-radius: 12px;
        overflow: hidden;
        margin-top: 10px;
        border: 1px solid rgba(74, 222, 128, 0.2);
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #22c55e, #4ade80, #86efac);
        border-radius: 12px;
        transition: width 0.8s cubic-bezier(0.23, 1, 0.320, 1);
        box-shadow: 0 0 12px rgba(34, 197, 94, 0.5);
        animation: fillPulse 2s ease-in-out infinite;
    }
    
    @keyframes fillPulse {
        0%, 100% { box-shadow: 0 0 12px rgba(34, 197, 94, 0.5); }
        50% { box-shadow: 0 0 20px rgba(34, 197, 94, 0.8); }
    }
    
    /* SEPARATORS */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(74, 222, 128, 0.2), transparent);
        margin: 32px 0;
    }
    
    /* INPUT STYLING */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select {
        background-color: rgba(31, 41, 55, 0.6) !important;
        border: 1.5px solid rgba(74, 222, 128, 0.3) !important;
        border-radius: 12px !important;
        color: #e5e7eb !important;
        padding: 12px 16px !important;
        font-weight: 500;
        transition: all 0.3s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus {
        border-color: rgba(74, 222, 128, 0.8) !important;
        box-shadow: 0 0 12px rgba(34, 197, 94, 0.3) !important;
        background-color: rgba(31, 41, 55, 0.8) !important;
    }
    
    .stInfo, .stWarning, .stSuccess {
        border-radius: 14px !important;
        border-left: 4px solid !important;
        padding: 16px !important;
        animation: slideInRight 0.5s cubic-bezier(0.23, 1, 0.320, 1);
    }
    
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    .stInfo {
        background-color: rgba(59, 130, 246, 0.1) !important;
        border-left-color: #3b82f6 !important;
    }
    
    .stWarning {
        background-color: rgba(245, 158, 11, 0.1) !important;
        border-left-color: #f59e0b !important;
    }
    
    .stSuccess {
        background-color: rgba(34, 197, 94, 0.1) !important;
        border-left-color: #22c55e !important;
    }
    
    /* BUTTON STYLING */
    .stButton > button {
        background: linear-gradient(135deg, #22c55e, #4ade80) !important;
        color: #0a2818 !important;
        font-weight: 800 !important;
        font-size: 16px !important;
        padding: 14px 32px !important;
        border: none !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 24px rgba(34, 197, 94, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.23, 1, 0.320, 1) !important;
        letter-spacing: 0.5px !important;
        animation: slideInUp 0.6s 0.4s cubic-bezier(0.23, 1, 0.320, 1) both;
        position: relative;
        overflow: hidden;
    }
    
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
    }
    
    .stButton > button:hover::before {
        width: 300px;
        height: 300px;
    }
    
    .stButton > button:hover {
        transform: translateY(-4px) !important;
        box-shadow: 0 16px 40px rgba(34, 197, 94, 0.5) !important;
    }
    
    .stButton > button:active {
        transform: translateY(-2px) !important;
    }
    
    /* FLOATING ANIMATION */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    .floating {
        animation: float 3s ease-in-out infinite;
    }
    
    /* GLOW ANIMATION */
    @keyframes glow {
        0%, 100% {
            box-shadow: 0 0 5px rgba(34, 197, 94, 0.3), inset 0 0 5px rgba(34, 197, 94, 0.1);
        }
        50% {
            box-shadow: 0 0 20px rgba(34, 197, 94, 0.6), inset 0 0 10px rgba(34, 197, 94, 0.2);
        }
    }
    
    /* STAGGER ANIMATION DELAYS */
    .stagger-1 { animation-delay: 0.1s !important; }
    .stagger-2 { animation-delay: 0.2s !important; }
    .stagger-3 { animation-delay: 0.3s !important; }
    .stagger-4 { animation-delay: 0.4s !important; }
    .stagger-5 { animation-delay: 0.5s !important; }
</style>
""", unsafe_allow_html=True)


# -------------------------
# HEADER
# -------------------------
st.markdown("<div class='title'>🌱 EcoBuddy AI+</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Your Personal AI-Powered Carbon Footprint Tracker & Eco Assistant</div>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; margin-bottom: 32px;'>
    <div style='display: inline-flex; gap: 16px; padding: 12px 24px; background: rgba(34, 197, 94, 0.08); border-radius: 50px; border: 1px solid rgba(74, 222, 128, 0.2);'>
        <span style='color: #d1d5db; font-size: 13px; font-weight: 600;'>✨ Track • 📊 Analyze • 💡 Improve</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")


# -------------------------
# INPUTS SECTION
# -------------------------
st.markdown("<div class='section-header'>📝 Your Lifestyle Profile</div>", unsafe_allow_html=True)

st.markdown("<div class='input-section'>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 16px;'>
        <span style='font-size: 24px;'>🚗</span>
        <span style='font-size: 18px; font-weight: 700; color: #e5e7eb;'>Transportation</span>
    </div>
    """, unsafe_allow_html=True)
    transport = st.selectbox("Primary Transport", ["Car", "Public Transport", "Bike", "Walking"])
    distance = st.number_input("Daily Distance (km)", min_value=0.0, value=10.0, step=1.0)

with col2:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 16px;'>
        <span style='font-size: 24px;'>⚡</span>
        <span style='font-size: 18px; font-weight: 700; color: #e5e7eb;'>Energy & Diet</span>
    </div>
    """, unsafe_allow_html=True)
    electricity = st.number_input("Monthly Electricity (kWh)", min_value=0.0, value=200.0, step=10.0)
    diet = st.selectbox("Diet Type", ["Vegetarian", "Non-Vegetarian"])

with col3:
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 16px;'>
        <span style='font-size: 24px;'>✈️</span>
        <span style='font-size: 18px; font-weight: 700; color: #e5e7eb;'>Travel</span>
    </div>
    """, unsafe_allow_html=True)
    flights = st.number_input("Annual Flights", min_value=0, value=0, step=1)
    st.info("💡 How many long-distance flights per year?")

st.markdown("</div>", unsafe_allow_html=True)


# -------------------------
# PDF REPORT GENERATION
# -------------------------
def generate_pdf(total, eco_score, insight):
    file_name = "eco_report.pdf"
    doc = SimpleDocTemplate(file_name)
    styles = getSampleStyleSheet()

    content = [
        Paragraph("EcoBuddy AI Report", styles["Title"]),
        Paragraph(f"Carbon Footprint: {total:.2f} kg CO₂", styles["Normal"]),
        Paragraph(f"Eco Score: {eco_score}/100", styles["Normal"]),
        Paragraph("Key Insight:", styles["Heading2"]),
        Paragraph(insight, styles["Normal"])
    ]

    doc.build(content)
    return file_name


# -------------------------
# CALCULATE & ANALYZE
# -------------------------
col_btn1, col_btn2, col_btn3 = st.columns([1, 1.5, 1])
with col_btn2:
    analyze_btn = st.button("🌿 Analyze My Impact", use_container_width=True)

if analyze_btn:

    with st.spinner("🌍 Analyzing your carbon footprint..."):
        total, contributors = calculate_footprint(
            transport, distance, electricity, diet, flights
        )

    eco_score = calculate_eco_score(total)

    insight, recommendations = generate_recommendations(
        transport, electricity, diet, flights, contributors
    )

    save_assessment(
        transport, distance, electricity, diet, flights, total, eco_score
    )

    st.success("✅ Analysis completed!")

    st.markdown("---")

    # -------------------------
    # RESULTS DASHBOARD
    # -------------------------
    st.markdown("<div class='section-header'>📊 Your Carbon Footprint Analysis</div>", unsafe_allow_html=True)

    # Top metrics row
    met1, met2, met3, met4 = st.columns(4)
    
    with met1:
        st.markdown("""
        <div class='metric-card'>
            <div style='font-size: 14px; color: #d1d5db; margin-bottom: 8px;'>🌍 Total Footprint</div>
            <div style='font-size: 36px; font-weight: 900; color: #4ade80;'>{:.0f}</div>
            <div style='font-size: 12px; color: #9ca3af;'>kg CO₂/year</div>
        </div>
        """.format(total), unsafe_allow_html=True)
    
    with met2:
        st.markdown("""
        <div class='metric-card'>
            <div style='font-size: 14px; color: #d1d5db; margin-bottom: 8px;'>🏆 Eco Score</div>
            <div style='font-size: 36px; font-weight: 900; color: #4ade80;'>{}</div>
            <div style='font-size: 12px; color: #9ca3af;'>out of 100</div>
        </div>
        """.format(eco_score), unsafe_allow_html=True)
    
    with met3:
        st.markdown("""
        <div class='metric-card'>
            <div style='font-size: 14px; color: #d1d5db; margin-bottom: 8px;'>📈 Biggest Impact</div>
            <div style='font-size: 24px; font-weight: 700; color: #4ade80;'>{}</div>
            <div style='font-size: 12px; color: #9ca3af;'>{:.0f} kg CO₂</div>
        </div>
        """.format(max(contributors, key=contributors.get), max(contributors.values())), unsafe_allow_html=True)
    
    with met4:
        st.markdown("""
        <div class='metric-card'>
            <div style='font-size: 14px; color: #d1d5db; margin-bottom: 8px;'>🎯 Status</div>
            <div style='font-size: 18px; font-weight: 700; color: #4ade80;'>Active</div>
            <div style='font-size: 12px; color: #9ca3af;'>Tracking enabled</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------
    # ECO SCORE PROGRESS & BADGE
    # -------------------------
    col_badge1, col_badge2 = st.columns([1, 1])
    
    with col_badge1:
        st.markdown("<div class='section-header' style='margin-top: 0;'>🏅 Eco Achievement</div>", unsafe_allow_html=True)
        
        if eco_score >= 85:
            badge_text = "🌟 Eco Champion"
            badge_class = "badge badge-champion"
        elif eco_score >= 70:
            badge_text = "🌿 Green Guardian"
            badge_class = "badge badge-guardian"
        elif eco_score >= 50:
            badge_text = "🍃 Eco Learner"
            badge_class = "badge badge-learner"
        else:
            badge_text = "🔥 High Impact User"
            badge_class = "badge badge-high"
        
        st.markdown(f"<div class='{badge_class}'>{badge_text}</div>", unsafe_allow_html=True)
        
        # Progress bar
        st.markdown(f"""
        <div style='margin-top: 16px;'>
            <div style='display: flex; justify-content: space-between; margin-bottom: 6px;'>
                <span style='color: #d1d5db; font-size: 14px;'>Score Progress</span>
                <span style='color: #4ade80; font-weight: 700;'>{eco_score}%</span>
            </div>
            <div class='progress-bar'>
                <div class='progress-fill' style='width: {eco_score}%;'></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Description
        if eco_score >= 85:
            st.info("🌟 Excellent! You're making exceptional environmental choices. Keep it up!")
        elif eco_score >= 70:
            st.info("🌿 Great work! Your footprint is below average. Focus on small improvements.")
        elif eco_score >= 50:
            st.info("🍃 Good start! There's room to improve. Check recommendations below.")
        else:
            st.warning("🔥 Your carbon footprint is above average. Let's work on reducing it!")
    
    with col_badge2:
        st.markdown("<div class='section-header' style='margin-top: 0;'>📊 Emission Sources</div>", unsafe_allow_html=True)
        
        # Pie chart with Plotly
        fig = go.Figure(data=[go.Pie(
            labels=list(contributors.keys()),
            values=list(contributors.values()),
            hole=0.4,
            marker=dict(
                colors=['#4ade80', '#60a5fa', '#fbbf24', '#f87171'],
                line=dict(color='rgba(0,0,0,0.1)', width=2)
            ),
            textposition='auto',
            hovertemplate='<b>%{label}</b><br>%{value:.0f} kg CO₂<br>%{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            showlegend=True,
            height=280,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#d1d5db', size=12),
            legend=dict(
                x=-0.15,
                y=1,
                bgcolor='rgba(0,0,0,0.3)',
                bordercolor='rgba(74, 222, 128, 0.3)',
                borderwidth=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    # -------------------------
    # DETAILED BREAKDOWN
    # -------------------------
    st.markdown("<div class='section-header'>📋 Detailed Breakdown</div>", unsafe_allow_html=True)
    
    # Bar chart
    breakdown_fig = go.Figure(data=[
        go.Bar(
            x=list(contributors.keys()),
            y=list(contributors.values()),
            marker=dict(
                color=['#4ade80', '#60a5fa', '#fbbf24', '#f87171'],
                line=dict(color='rgba(255,255,255,0.2)', width=2)
            ),
            text=[f'{v:.0f} kg' for v in contributors.values()],
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>%{y:.0f} kg CO₂<extra></extra>'
        )
    ])
    
    breakdown_fig.update_layout(
        height=350,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(55, 65, 81, 0.2)',
        font=dict(color='#d1d5db', size=12),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            color='#9ca3af'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(74, 222, 128, 0.1)',
            zeroline=False,
            color='#9ca3af'
        ),
        showlegend=False
    )
    
    st.plotly_chart(breakdown_fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    # -------------------------
    # AI INSIGHT
    # -------------------------
    st.markdown("<div class='section-header'>🤖 AI Insights & Analysis</div>", unsafe_allow_html=True)
    
    col_insight1, col_insight2 = st.columns([1.2, 0.8])
    
    with col_insight1:
        st.markdown(f"""
        <div class='card-highlight'>
            <div style='display: flex; gap: 12px; align-items: flex-start;'>
                <div style='font-size: 32px;'>💡</div>
                <div style='flex: 1;'>
                    <div style='font-size: 16px; font-weight: 800; color: #4ade80; margin-bottom: 12px;'>Key Finding</div>
                    <div style='font-size: 15px; color: #d1d5db; line-height: 1.8;'>{insight}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_insight2:
        st.markdown("""
        <div class='card'>
            <div style='display: flex; gap: 12px; align-items: flex-start;'>
                <div style='font-size: 32px;'>🎯</div>
                <div style='flex: 1;'>
                    <div style='font-size: 16px; font-weight: 800; color: #4ade80; margin-bottom: 12px;'>Quick Tips</div>
                    <ul style='color: #d1d5db; font-size: 14px; line-height: 2.2; padding-left: 20px; margin: 0;'>
                        <li>Start with small daily changes</li>
                        <li>Track progress regularly</li>
                        <li>Share with friends & family</li>
                        <li>Focus on your biggest source</li>
                    </ul>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------
    # RECOMMENDATIONS
    # -------------------------
    st.markdown("<div class='section-header'>💡 Personalized Recommendations</div>", unsafe_allow_html=True)
    
    if len(recommendations) > 0:
        for idx, r in enumerate(recommendations):
            st.markdown(f"""
            <div class='card' style='border-left: 4px solid #22c55e;'>
                <div style='display: flex; gap: 12px;'>
                    <div style='font-size: 24px;'>💚</div>
                    <div style='flex: 1;'>
                        <div style='font-size: 15px; line-height: 1.8; color: #d1d5db;'>{r}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='card-highlight'>
            <div style='display: flex; gap: 16px; align-items: center;'>
                <div style='font-size: 48px;'>🌟</div>
                <div>
                    <div style='font-size: 18px; font-weight: 700; color: #4ade80; margin-bottom: 4px;'>Excellent Work!</div>
                    <div style='color: #d1d5db;'>Your lifestyle is already very eco-friendly. Keep maintaining these amazing habits!</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------
    # PDF DOWNLOAD
    # -------------------------
    report = generate_pdf(total, eco_score, insight)

    with open(report, "rb") as f:
        st.download_button(
            "📄 Download Eco Report (PDF)",
            f,
            file_name="EcoBuddy_Report.pdf"
        )


# -------------------------
# HISTORY & TRACKING
# -------------------------
st.markdown("---")

st.markdown("<div class='section-header'>📈 Your Eco Journey</div>", unsafe_allow_html=True)

history = get_assessments()

if history:

    df = pd.DataFrame(history, columns=[
        "id", "date", "transport", "distance",
        "electricity", "diet", "flights",
        "footprint", "eco_score"
    ])

    latest = history[0]

    # Latest stats
    stat1, stat2, stat3, stat4 = st.columns(4)
    
    with stat1:
        st.markdown(f"""
        <div class='card'>
            <div style='font-size: 12px; color: #9ca3af;'>Latest Footprint</div>
            <div style='font-size: 28px; font-weight: 900; color: #4ade80;'>{latest[7]:.0f}</div>
            <div style='font-size: 11px; color: #9ca3af;'>kg CO₂</div>
        </div>
        """, unsafe_allow_html=True)
    
    with stat2:
        st.markdown(f"""
        <div class='card'>
            <div style='font-size: 12px; color: #9ca3af;'>Latest Score</div>
            <div style='font-size: 28px; font-weight: 900; color: #4ade80;'>{latest[8]}</div>
            <div style='font-size: 11px; color: #9ca3af;'>out of 100</div>
        </div>
        """, unsafe_allow_html=True)

    if len(history) >= 2:
        prev = history[1][7]
        change = ((prev - latest[7]) / prev) * 100 if prev else 0

        with stat3:
            if change > 0:
                color = "#4ade80"
                emoji = "📉"
                label = "Reduced"
            elif change < 0:
                color = "#f87171"
                emoji = "📈"
                label = "Increased"
            else:
                color = "#60a5fa"
                emoji = "→"
                label = "No Change"
            
            st.markdown(f"""
            <div class='card'>
                <div style='font-size: 12px; color: #9ca3af;'>{emoji} {label}</div>
                <div style='font-size: 28px; font-weight: 900; color: {color};'>{abs(change):.1f}%</div>
                <div style='font-size: 11px; color: #9ca3af;'>vs previous</div>
            </div>
            """, unsafe_allow_html=True)

    with stat4:
        st.markdown(f"""
        <div class='card'>
            <div style='font-size: 12px; color: #9ca3af;'>Total Records</div>
            <div style='font-size: 28px; font-weight: 900; color: #4ade80;'>{len(history)}</div>
            <div style='font-size: 11px; color: #9ca3af;'>assessments</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # -------------------------
    # TREND VISUALIZATION
    # -------------------------
    st.markdown("<div style='font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #4ade80, #86efac); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 16px;'>📉 Carbon Footprint Trend</div>", unsafe_allow_html=True)

    trend_df = df[["date", "footprint"]].iloc[::-1].reset_index(drop=True)
    trend_df['date'] = pd.to_datetime(trend_df['date'])
    
    trend_fig = go.Figure()
    trend_fig.add_trace(go.Scatter(
        x=trend_df['date'],
        y=trend_df['footprint'],
        mode='lines+markers',
        name='Carbon Footprint',
        line=dict(color='#4ade80', width=3),
        marker=dict(size=8, color='#4ade80', line=dict(color='#86efac', width=2)),
        fill='tozeroy',
        fillcolor='rgba(74, 222, 128, 0.2)',
        hovertemplate='<b>%{x|%b %d}</b><br>%{y:.0f} kg CO₂<extra></extra>'
    ))
    
    trend_fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(55, 65, 81, 0.2)',
        font=dict(color='#d1d5db', size=12),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            color='#9ca3af'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(74, 222, 128, 0.1)',
            zeroline=False,
            color='#9ca3af'
        ),
        showlegend=False,
        hovermode='x unified'
    )
    
    st.plotly_chart(trend_fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    # -------------------------
    # HISTORY TABLE
    # -------------------------
    st.markdown("<div style='font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #4ade80, #86efac); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 16px;'>📋 Assessment History</div>", unsafe_allow_html=True)

    # Create a nice table display
    display_df = df[["date", "transport", "electricity", "footprint", "eco_score"]].copy()
    display_df.columns = ["📅 Date", "🚗 Transport", "⚡ Electricity (kWh)", "🌍 Footprint (kg CO₂)", "🏆 Score"]
    display_df = display_df.iloc[::-1].reset_index(drop=True)
    
    st.dataframe(display_df)

    # -------------------------
    # CSV EXPORT
    # -------------------------
    export_df = get_assessments_df()
    csv_data = export_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download Assessment History (CSV)",
        data=csv_data,
        file_name="EcoBuddy_Assessment_History.csv",
        mime="text/csv",
        help="Export your complete assessment history as a CSV file for analysis in Excel or Google Sheets."
    )

    st.markdown("---")

    # -------------------------
    # STATS & INSIGHTS
    # -------------------------
    st.markdown("<div style='font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #4ade80, #86efac); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 16px;'>📊 Your Statistics</div>", unsafe_allow_html=True)

    stats_col1, stats_col2, stats_col3 = st.columns(3)
    
    avg_footprint = df['footprint'].mean()
    avg_score = df['eco_score'].mean()
    max_footprint = df['footprint'].max()
    min_footprint = df['footprint'].min()
    
    with stats_col1:
        st.markdown(f"""
        <div class='card'>
            <div style='font-size: 13px; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;'>📊 Average Footprint</div>
            <div style='font-size: 36px; font-weight: 900; color: #4ade80;'>{avg_footprint:.0f}</div>
            <div style='font-size: 12px; color: #9ca3af; margin-top: 8px;'>kg CO₂ across {len(history)} records</div>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col2:
        st.markdown(f"""
        <div class='card'>
            <div style='font-size: 13px; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;'>🎯 Average Score</div>
            <div style='font-size: 36px; font-weight: 900; color: #4ade80;'>{avg_score:.0f}</div>
            <div style='font-size: 12px; color: #9ca3af; margin-top: 8px;'>out of 100 points</div>
        </div>
        """, unsafe_allow_html=True)
    
    with stats_col3:
        range_val = max_footprint - min_footprint
        st.markdown(f"""
        <div class='card'>
            <div style='font-size: 13px; color: #9ca3af; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; font-weight: 700;'>📈 Range Variation</div>
            <div style='font-size: 28px; font-weight: 700; color: #4ade80;'>{min_footprint:.0f}</div>
            <div style='font-size: 14px; color: #9ca3af;'>to</div>
            <div style='font-size: 28px; font-weight: 700; color: #4ade80;'>{max_footprint:.0f}</div>
        </div>
        """, unsafe_allow_html=True)

else:
    st.markdown("""
    <div class='card-highlight'>
        <div style='text-align: center; padding: 48px 32px;'>
            <div style='font-size: 72px; margin-bottom: 20px; animation: bounce 2s infinite;'>🌱</div>
            <div style='font-size: 26px; font-weight: 800; background: linear-gradient(135deg, #22c55e, #4ade80); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 12px;'>No Data Yet</div>
            <div style='color: #d1d5db; font-size: 16px; line-height: 1.6; max-width: 400px; margin: 0 auto;'>
                Start your eco journey! Complete the lifestyle profile above and click "Analyze My Impact" to generate your personalized carbon footprint report.
            </div>
        </div>
    </div>
    <style>
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }
    </style>
    """, unsafe_allow_html=True)