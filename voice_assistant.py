# ============================================================
# FILE: voice_assessment.py
# EcoBuddy AI+ Voice-Powered Carbon Assessment
# ============================================================

import streamlit as st
import json
import re
from datetime import datetime
import random
from typing import Any

# ============================================================
# VOICE COMMAND PARSER
# ============================================================

class VoiceCommandParser:
    """Parse natural language voice commands for carbon assessment"""
    
    # Keywords and patterns for extraction
    PATTERNS = {
        "transport": {
            "car": ["car", "drive", "driving", "automobile", "vehicle"],
            "public_transport": ["bus", "train", "subway", "metro", "public transport", "transit"],
            "bike": ["bike", "bicycle", "cycling", "cycle"],
            "walking": ["walk", "walking", "on foot"]
        },
        "diet": {
            "vegetarian": ["vegetarian", "veggie", "plant-based", "no meat", "meat-free"],
            "non_vegetarian": ["non-vegetarian", "meat", "meat eater", "carnivore", "flexitarian"]
        },
        "distance": {
            "pattern": r"(\d+\.?\d*)\s*(?:km|kilometer|mile|miles|kms?)",
            "default": 10
        },
        "electricity": {
            "pattern": r"(\d+\.?\d*)\s*(?:kWh|kilowatt|kwh|units?|electricity)",
            "default": 200
        },
        "flights": {
            "pattern": r"(\d+)\s*(?:flight|flights|plane|planes|air travel)",
            "default": 0
        }
    }
    
    @staticmethod
    def parse_voice_input(text: str) -> dict[str, Any] | None:
        """Parse voice input into structured assessment data"""
        
        # Clean text
        text = text.lower().strip()
        
        # Initialize result
        result = {
            "transport": "Car",  # Default
            "diet": "Vegetarian",  # Default
            "distance": 10.0,
            "electricity": 200.0,
            "flights": 0,
            "confidence": 0.0,
            "parsed_elements": [],
            "unknown_elements": []
        }
        
        parsed_count = 0
        total_patterns = 4  # transport, diet, distance, flights
        
        # Parse transport
        transport_found = False
        for mode, keywords in VoiceCommandParser.PATTERNS["transport"].items():
            for keyword in keywords:
                if keyword in text:
                    result["transport"] = mode.replace("_", " ").title()
                    result["parsed_elements"].append(f"Transport: {result['transport']}")
                    transport_found = True
                    parsed_count += 1
                    break
            if transport_found:
                break
        
        # Parse diet
        diet_found = False
        for diet_type, keywords in VoiceCommandParser.PATTERNS["diet"].items():
            for keyword in keywords:
                if keyword in text:
                    result["diet"] = diet_type.replace("_", " ").title()
                    result["parsed_elements"].append(f"Diet: {result['diet']}")
                    diet_found = True
                    parsed_count += 1
                    break
            if diet_found:
                break
        
        # Parse distance
        distance_match = re.search(VoiceCommandParser.PATTERNS["distance"]["pattern"], text)
        if distance_match:
            result["distance"] = float(distance_match.group(1))
            result["parsed_elements"].append(f"Distance: {result['distance']} km")
            parsed_count += 1
        
        # Parse electricity
        electricity_match = re.search(VoiceCommandParser.PATTERNS["electricity"]["pattern"], text)
        if electricity_match:
            result["electricity"] = float(electricity_match.group(1))
            result["parsed_elements"].append(f"Electricity: {result['electricity']} kWh")
            parsed_count += 1
        
        # Parse flights
        flights_match = re.search(VoiceCommandParser.PATTERNS["flights"]["pattern"], text)
        if flights_match:
            result["flights"] = int(flights_match.group(1))
            result["parsed_elements"].append(f"Flights: {result['flights']} per year")
            parsed_count += 1
        
        # Calculate confidence
        result["confidence"] = (parsed_count / total_patterns) * 100
        
        # Check for unknown elements
        if "unknown" in text or "not sure" in text or "maybe" in text:
            result["unknown_elements"].append("Some elements were unclear")
        
        return result
    
    @staticmethod
    def get_example_commands() -> list[str]:
        """Get example voice commands"""
        return [
            "I drive 15 kilometers every day to work and I'm vegetarian",
            "I take the bus to work, use 250 kWh of electricity monthly, and I eat meat",
            "I bike 5 km daily, my electricity is 180 kWh, and I take 2 flights per year",
            "I walk everywhere, use 120 kWh of electricity, and I'm plant-based",
            "I drive my car 20 miles daily, use 300 kWh electricity, and I'm non-vegetarian",
            "I use public transport, my electricity is 150 kWh, and I don't fly"
        ]

# ============================================================
# SPEECH-TO-TEXT SIMULATOR (for demo)
# ============================================================

class SpeechToTextSimulator:
    """Simulate speech-to-text functionality for demo purposes"""
    
    SAMPLE_RESPONSES = [
        "I drive 15 kilometers every day and I'm vegetarian",
        "I take the bus to work and use about 250 kWh of electricity monthly",
        "I bike 5 km daily and I don't eat meat",
        "I walk to work, my electricity is 180 kWh, and I take 2 flights per year",
        "I drive my car 20 miles daily and I'm non-vegetarian",
        "I use public transport, my electricity is 150 kWh, and I don't fly"
    ]
    
    @staticmethod
    def get_simulated_voice_input() -> str:
        """Get a simulated voice input"""
        return random.choice(SpeechToTextSimulator.SAMPLE_RESPONSES)
    
    @staticmethod
    def process_voice_button() -> str:
        """Handle voice input button click"""
        # In production, this would connect to a real speech-to-text API
        return SpeechToTextSimulator.get_simulated_voice_input()

# ============================================================
# VOICE ASSESSMENT UI
# ============================================================

class VoiceAssessmentUI:
    """UI for voice-powered carbon assessment"""
    
    @staticmethod
    def render_voice_assessment() -> None:
        """Render the voice assessment interface"""
        st.markdown("""
        <div class='card-highlight'>
            <div style='display: flex; align-items: center; gap: 15px;'>
                <div style='font-size: 48px;'>🎤</div>
                <div>
                    <h4 style='margin: 0; color: #4ade80;'>Voice-Powered Carbon Assessment</h4>
                    <p style='margin: 8px 0 0 0; color: #6b7280; font-size: 14px;'>
                        Simply speak your lifestyle details and EcoBuddy will auto-fill your assessment form
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Example commands
        with st.expander("💡 Example Voice Commands", expanded=False):
            st.markdown("Try saying something like:")
            examples = VoiceCommandParser.get_example_commands()
            for example in examples:
                st.markdown(f"• *\"{example}\"*")
            
            st.caption("Tip: Include transportation, distance, electricity usage, diet, and flights if possible")
        
        # Voice input section
        st.markdown("### 🎙️ Voice Input")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.button("🎤 Start Speaking", use_container_width=True, type="primary"):
                st.session_state.voice_input = SpeechToTextSimulator.process_voice_button()
                st.rerun()
        
        with col2:
            if st.button("📝 Type Instead", use_container_width=True):
                st.session_state.voice_mode = "typing"
                st.rerun()
        
        with col3:
            if st.button("🔄 Reset Voice", use_container_width=True):
                st.session_state.pop("voice_input", None)
                st.session_state.pop("voice_parsed", None)
                st.rerun()
        
        # Voice input display
        if "voice_input" in st.session_state:
            st.markdown("### 📝 What You Said")
            st.markdown(f"""
            <div style='
                background: #1f2937;
                border-radius: 12px;
                padding: 20px;
                border-left: 4px solid #4ade80;
                font-size: 16px;
                line-height: 1.8;
                color: #e5e7eb;
            '>
                " {st.session_state.voice_input} "
            </div>
            """, unsafe_allow_html=True)
            
            # Parse the voice input
            if "voice_parsed" not in st.session_state:
                parser = VoiceCommandParser()
                st.session_state.voice_parsed = parser.parse_voice_input(st.session_state.voice_input)
            
            # Show parsed results
            VoiceAssessmentUI.render_parsed_results(st.session_state.voice_parsed)
        
        else:
            st.info("👆 Click 'Start Speaking' and speak your lifestyle details clearly")
            
            # Show a demo of what will happen
            st.markdown("#### 🎯 How It Works")
            steps = [
                "1. Click 'Start Speaking' and speak your lifestyle details",
                "2. EcoBuddy will transcribe your voice to text",
                "3. AI will parse key information (transport, diet, distance, etc.)",
                "4. Review and confirm the extracted data",
                "5. Auto-fill the assessment form with a single click"
            ]
            for step in steps:
                st.markdown(f"• {step}")
    
    @staticmethod
    def render_parsed_results(parsed: dict[str, Any]) -> None:
        """Render the parsed voice results"""
        st.markdown("### 🔍 What We Understood")
        
        # Confidence indicator
        confidence = parsed.get("confidence", 0)
        if confidence >= 80:
            color = "#4ade80"
            label = "High Confidence"
            emoji = "✅"
        elif confidence >= 50:
            color = "#fbbf24"
            label = "Medium Confidence"
            emoji = "⚠️"
        else:
            color = "#f87171"
            label = "Low Confidence"
            emoji = "❌"
        
        st.markdown(f"""
        <div style='
            padding: 12px 20px;
            border-radius: 10px;
            background: {color}15;
            border: 1px solid {color};
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        '>
            <span style='font-size: 24px;'>{emoji}</span>
            <div>
                <div style='font-weight: 700;'>Confidence: {confidence:.0f}% - {label}</div>
                <div style='font-size: 13px; color: #6b7280;'>
                    {parsed.get('parsed_elements', [])}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Extracted data
        st.markdown("#### 📊 Extracted Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
            <div class='metric-card'>
                <div style='font-size: 14px; color: #6b7280;'>🚗 Transportation</div>
                <div style='font-size: 24px; font-weight: 700; color: #4ade80;'>{parsed['transport']}</div>
                <div style='font-size: 12px; color: #6b7280;'>Mode of transport</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='metric-card'>
                <div style='font-size: 14px; color: #6b7280;'>⚡ Electricity</div>
                <div style='font-size: 24px; font-weight: 700; color: #4ade80;'>{parsed['electricity']:.1f} kWh</div>
                <div style='font-size: 12px; color: #6b7280;'>Monthly usage</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class='metric-card'>
                <div style='font-size: 14px; color: #6b7280;'>🚶 Distance</div>
                <div style='font-size: 24px; font-weight: 700; color: #4ade80;'>{parsed['distance']:.1f} km</div>
                <div style='font-size: 12px; color: #6b7280;'>Daily commute</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class='metric-card'>
                <div style='font-size: 14px; color: #6b7280;'>🥗 Diet</div>
                <div style='font-size: 24px; font-weight: 700; color: #4ade80;'>{parsed['diet']}</div>
                <div style='font-size: 12px; color: #6b7280;'>Eating habits</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Flights
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 14px; color: #6b7280;'>✈️ Flights</div>
            <div style='font-size: 24px; font-weight: 700; color: #4ade80;'>{parsed['flights']} per year</div>
            <div style='font-size: 12px; color: #6b7280;'>Annual air travel</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Unknown elements
        if parsed.get("unknown_elements"):
            st.warning(f"⚠️ {', '.join(parsed['unknown_elements'])}")
        
        # Action buttons
        st.markdown("### 📝 Next Steps")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ Apply to Form", use_container_width=True, type="primary"):
                # Update session state with parsed values
                st.session_state.transport = parsed['transport']
                st.session_state.distance = parsed['distance']
                st.session_state.electricity = parsed['electricity']
                st.session_state.diet = parsed['diet']
                st.session_state.flights = parsed['flights']
                
                st.success("✅ Assessment form updated with voice data!")
                st.rerun()
        
        with col2:
            if st.button("✏️ Edit Manually", use_container_width=True):
                st.session_state.voice_edit_mode = True
                st.rerun()
        
        with col3:
            if st.button("🔄 Try Again", use_container_width=True):
                st.session_state.pop("voice_input", None)
                st.session_state.pop("voice_parsed", None)
                st.rerun()
        
        # Manual edit mode
        if st.session_state.get("voice_edit_mode", False):
            st.markdown("### ✏️ Manual Correction")
            st.caption("Edit any values that were extracted incorrectly")
            
            col1, col2 = st.columns(2)
            with col1:
                edit_transport = st.selectbox(
                    "Transportation",
                    ["Car", "Public Transport", "Bike", "Walking"],
                    index=["Car", "Public Transport", "Bike", "Walking"].index(parsed['transport'])
                )
                edit_distance = st.number_input("Distance (km)", value=parsed['distance'], step=1.0)
                edit_electricity = st.number_input("Electricity (kWh)", value=parsed['electricity'], step=10.0)
            
            with col2:
                edit_diet = st.selectbox(
                    "Diet",
                    ["Vegetarian", "Non-Vegetarian"],
                    index=["Vegetarian", "Non-Vegetarian"].index(parsed['diet'])
                )
                edit_flights = st.number_input("Flights (per year)", value=parsed['flights'], step=1, min_value=0)
            
            if st.button("✅ Apply Corrections", use_container_width=True):
                st.session_state.transport = edit_transport
                st.session_state.distance = edit_distance
                st.session_state.electricity = edit_electricity
                st.session_state.diet = edit_diet
                st.session_state.flights = edit_flights
                
                st.session_state.voice_edit_mode = False
                st.success("✅ Corrections applied!")
                st.rerun()

# ============================================================
# RENDER FUNCTION
# ============================================================

def render_voice_assessment() -> None:
    """Render the complete voice assessment interface"""
    VoiceAssessmentUI.render_voice_assessment()

# ============================================================
# INTEGRATION WITH MAIN APP
# ============================================================

def integrate_voice_assessment() -> None:
    """Integration function for main app"""
    st.markdown("<div class='section-header'>🎤 Voice Assessment</div>", unsafe_allow_html=True)
    render_voice_assessment()



