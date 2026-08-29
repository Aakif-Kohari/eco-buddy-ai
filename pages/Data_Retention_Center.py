import streamlit as st
import json
import pandas as pd
import sys
import os

# Add src module to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.data_retention_engine import engine

st.set_page_config(page_title="Data Retention Center", layout="wide", page_icon="🛡️")

st.title("🛡️ Data Retention & Privacy Center")

# Dummy authentication
user_id = st.session_state.get('user_id', 1)
# For demo purposes, we can toggle admin mode
is_admin = st.sidebar.checkbox("Enable Admin Mode", value=True)

tab1, tab2 = st.tabs(["User Privacy Settings", "Admin Policy Management"])

with tab1:
    st.header("Your Data Footprint")
    st.write("Review the data currently stored in your account and manage your privacy preferences.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Data Stale Preview (Dry Run)")
        if st.button("Compute Stale Data Footprint"):
            with st.spinner("Computing..."):
                stale_info = engine.compute_stale_rows(user_id=user_id)
                if stale_info['total_stale_rows'] > 0:
                    st.warning(f"Found {stale_info['total_stale_rows']} stale records across your account that are eligible for cleanup based on current policies.")
                    st.json(stale_info['stale_data'])
                else:
                    st.success("No stale records found based on current policies.")
                
    with col2:
        st.subheader("Right to Erasure")
        st.warning("Requesting full data deletion will permanently remove all your records across all tables. This action cannot be undone.")
        
        confirm_deletion = st.checkbox("I understand that my data will be permanently deleted.")
        
        if st.button("Delete All My Data", type="primary", disabled=not confirm_deletion):
            with st.spinner("Purging records..."):
                try:
                    manifest = engine.purge_user_data(user_id)
                    st.success("Your data has been successfully purged.")
                    
                    st.download_button(
                        label="Download Deletion Manifest (JSON)",
                        data=json.dumps(manifest, indent=2),
                        file_name=f"deletion_manifest_user_{user_id}.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.error(f"Failed to delete data: {e}")

with tab2:
    if is_admin:
        st.header("Admin: Policy Management")
        
        with st.expander("Add New Retention Policy", expanded=False):
            with st.form("new_policy_form"):
                p_table = st.text_input("Table Name", help="e.g. eco_journal_entries")
                p_cat = st.text_input("Category", help="e.g. Logs, Assessments")
                p_days = st.number_input("Retention Days", min_value=1, value=30)
                p_action = st.selectbox("Action", ["delete", "anonymize"])
                
                if st.form_submit_button("Save Policy"):
                    engine.set_policy(p_table, p_cat, p_days, p_action)
                    st.success(f"Policy saved for {p_table}.")
                    
        st.subheader("Current Policies")
        policies = engine.get_policies()
        if policies:
            df_pol = pd.DataFrame(policies)
            st.dataframe(df_pol, use_container_width=True, hide_index=True)
        else:
            st.info("No retention policies configured.")
            
        st.subheader("Audit Logs")
        logs = engine.get_audit_logs(limit=20)
        if logs:
            df_logs = pd.DataFrame(logs)
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
        else:
            st.info("No audit logs available.")
    else:
        st.warning("You must be an administrator to view this section.")
