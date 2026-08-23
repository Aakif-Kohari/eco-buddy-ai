import streamlit as st
import datetime
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_portability_engine import DataPortabilityEngine
from data_deletion_service import DataDeletionService

st.set_page_config(page_title="Privacy & Data Control Center", layout="centered", page_icon="🔒")

# Assume user is logged in
current_user_id = "USR_89237BCA"

st.markdown("""
<style>
    .privacy-header { text-align: center; margin-bottom: 30px; }
    .privacy-card {
        background: #1e1e1e; padding: 25px; border-radius: 12px;
        border-left: 4px solid #3b82f6; margin-bottom: 20px;
    }
    .danger-zone {
        border-left: 4px solid #ef4444; background: rgba(239, 68, 68, 0.05);
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='privacy-header'><h1>🔒 Privacy & Data Control Center</h1><p>Manage your data, export your footprints, and control your privacy settings.</p></div>", unsafe_allow_html=True)

portability_engine = DataPortabilityEngine(current_user_id)
deletion_service = DataDeletionService()

tabs = st.tabs(["📤 Download My Data", "⚙️ Privacy Settings", "❌ Danger Zone"])

with tabs[0]:
    st.markdown("<div class='privacy-card'>", unsafe_allow_html=True)
    st.subheader("Data Portability (Article 20)")
    st.write("You have the right to receive the personal data concerning you in a structured, commonly used, and machine-readable format.")
    
    st.write("**Summary of your data:**")
    st.code(portability_engine.generate_personal_data_summary())
    
    c1, c2 = st.columns(2)
    with c1:
        json_data = portability_engine.export_as_json()
        st.download_button("Download as JSON", data=json_data, file_name=f"privacy_export_{current_user_id}.json", mime="application/json", use_container_width=True)
    with c2:
        csv_data = portability_engine.export_as_csv()
        st.download_button("Download Footprints CSV", data=csv_data, file_name=f"footprints_{current_user_id}.csv", mime="text/csv", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


with tabs[1]:
    st.markdown("<div class='privacy-card'>", unsafe_allow_html=True)
    st.subheader("Consent & Analytics")
    st.write("Manage what data we process to improve the Eco Buddy AI experience.")
    
    v1 = st.checkbox("Allow anonymous telemtry (Helps us improve accuracy)", value=True)
    v2 = st.checkbox("Allow personalized green marketing", value=False)
    
    if st.button("Save Preferences"):
        st.success("Preferences saved successfully.")
    st.markdown("</div>", unsafe_allow_html=True)


with tabs[2]:
    st.markdown("<div class='privacy-card danger-zone'>", unsafe_allow_html=True)
    st.subheader("Account Deletion (Right to be Forgotten)")
    st.write("If you no longer wish to use Eco Buddy AI, you can request your data be erased. You can choose to completely wipe your account, or anonymize your data to help the global model without tracking you.")
    
    action = st.radio("Choose Deletion Scope", ["Anonymize Profile (Recommended)", "Hard Delete Everything"])
    
    confirm = st.text_input("Type 'DELETE' to confirm")
    if st.button("Execute", type="primary"):
        if confirm == "DELETE":
            with st.spinner("Processing request..."):
                if "Hard" in action:
                    res = deletion_service.execute_hard_delete(current_user_id)
                    action_msg = "permanently wiped"
                else:
                    res = deletion_service.execute_anonymization(current_user_id)
                    action_msg = "successfully anonymized"
                
                if res:
                    st.success(f"Your account and data have been {action_msg}. You will be logged out automatically.")
                    st.balloons()
                else:
                    st.error("Failed to process deletion. Please contact support.")
        else:
            st.error("Confirmation string was incorrect.")
            
    st.markdown("</div>", unsafe_allow_html=True)
