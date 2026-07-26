import streamlit as st
import json
import sys
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


if uploaded_file is not None:

    try:
        json_content = uploaded_file.read().decode("utf-8")
        preview = json.loads(json_content)

        st.success("✅ Valid backup file detected")

        st.subheader("📋 Backup Preview")

        total_records = 0

        for key, value in preview.items():
            if isinstance(value, list):
                total_records += len(value)
                st.write(f"**{key.replace('_',' ').title()}** : {len(value)} records")

        st.info(f"📦 Total Records: {total_records}")

        file_size = uploaded_file.size / 1024

        st.caption(f"File Size: {file_size:.2f} KB")

        uploaded_file.seek(0)

    except Exception:
        st.error("❌ Invalid JSON file.")

if uploaded_file is not None:
    if st.button("Restore Data"):
        json_content = uploaded_file.read().decode("utf-8")
        with st.spinner("Importing data..."):
            success, message = import_data_json(json_content, strategy=import_strategy.lower())
            if success:
                st.success(message)
                st.info("Please refresh the page or navigate to another section to see the restored data.")
            else:
                st.error(message)

