import streamlit as st
from data_io import export_data_json, export_data_csv_zip, import_data_json

from styles.theme import apply_theme
apply_theme()

st.title("💾 Data Portability")
st.markdown("Manage your EcoBuddy data. You can export your data to take it with you, or import previously exported data to restore your profile.")

st.markdown("---")
st.header("📤 Export Data")
st.markdown("Export your assessments, appliances, gamification progress, and more.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("CSV Export")
    st.markdown("Download your core data tables as CSV files bundled in a ZIP archive. This format is great for analyzing your data in Excel or other tools.")
    if st.button("Generate CSV Archive"):
        with st.spinner("Generating CSV..."):
            zip_data = export_data_csv_zip()
            if zip_data:
                st.download_button(
                    label="⬇️ Download ZIP",
                    data=zip_data,
                    file_name="ecobuddy_export.zip",
                    mime="application/zip",
                    key="download_csv_zip"
                )
            else:
                st.info("No data available to export.")

with col2:
    st.subheader("JSON Export")
    st.markdown("Download a full dump of your data in JSON format. This format is required if you want to import your data back into EcoBuddy later.")
    if st.button("Generate JSON Export"):
        with st.spinner("Generating JSON..."):
            json_data = export_data_json()
            if json_data != "{}":
                st.download_button(
                    label="⬇️ Download JSON",
                    data=json_data,
                    file_name="ecobuddy_export.json",
                    mime="application/json",
                    key="download_json"
                )
            else:
                st.info("No data available to export.")


st.markdown("---")
st.header("📥 Import Data")
st.markdown("Restore your data from a previously exported JSON file.")

import_strategy = st.radio(
    "Import Strategy",
    options=["Merge", "Replace"],
    index=0,
    help="Merge: Keeps your existing data and adds new non-duplicate entries. Replace: Deletes your current data and replaces it entirely with the imported data."
)

uploaded_file = st.file_uploader("Upload JSON Export File", type=["json"])

import json

if uploaded_file is not None:
    if st.button("Restore Data"):

        # Read uploaded file
        file_bytes = uploaded_file.read()

        # Empty file validation
        if not file_bytes:
            st.error("❌ The uploaded file is empty. Please upload a valid EcoBuddy JSON export.")
            st.stop()

        # Decode validation
        try:
            json_content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            st.error("❌ Unable to read the file. Please upload a UTF-8 encoded JSON file.")
            st.stop()

        # Empty content validation
        if not json_content.strip():
            st.error("❌ The uploaded file contains no data.")
            st.stop()

        # JSON validation
        try:
            json.loads(json_content)
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON file.\n\nDetails: {e}")
            st.stop()

        # Import only after validation passes
        with st.spinner("Importing data..."):
            success, message = import_data_json(
                json_content,
                strategy=import_strategy.lower(),
            )

            if success:
                st.success(message)
                st.info(
                    "Please refresh the page or navigate to another section "
                    "to see the restored data."
                )
            else:
                st.error(message)