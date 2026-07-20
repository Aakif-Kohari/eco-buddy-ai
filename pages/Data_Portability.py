import streamlit as st
from data_io import export_data_json, export_data_csv_zip, import_data_json

from styles.theme import apply_theme
apply_theme()
from datetime import datetime

def render_export_card(
    title,
    description,
    button_label,
    export_function,
    session_key,
    filename,
    mime_type,
    empty_check,
    format_name,
    download_key,
):
    st.subheader(title)
    st.markdown(description)

    if st.button(button_label):
        with st.spinner(f"Generating {format_name}..."):
            export_data = export_function()

            if not empty_check(export_data):
                st.session_state[session_key] = export_data
            else:
                st.warning(
                    "⚠️ No data available to export. Add some data before exporting."
                )

    if st.session_state.get(session_key):
        st.success("✅ Export generated successfully!")

        st.markdown("#### Export Details")
        st.markdown(f"**📄 File Name:** `{filename}`")
        st.markdown(f"**🗂 Format:** {format_name}")
        st.markdown(
            f"**🕒 Generated At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        st.download_button(
            label=f"⬇️ Download {format_name}",
            data=st.session_state[session_key],
            file_name=filename,
            mime=mime_type,
            key=download_key,
        )
st.title("💾 Data Portability")
st.markdown("Manage your EcoBuddy data. You can export your data to take it with you, or import previously exported data to restore your profile.")

st.markdown("---")
st.header("📤 Export Data")
st.markdown("Export your assessments, appliances, gamification progress, and more.")

col1, col2 = st.columns(2)

with col1:
    render_export_card(
        title="CSV Export",
        description=(
            "Download your core data tables as CSV files bundled in a ZIP archive. "
            "This format is great for analyzing your data in Excel or other tools."
        ),
        button_label="Generate CSV Archive",
        export_function=export_data_csv_zip,
        session_key="csv_export",
        filename="ecobuddy_export.zip",
        mime_type="application/zip",
        empty_check=lambda data: not data,
        format_name="ZIP (CSV Archive)",
        download_key="download_csv_zip",
    )

with col2:
    render_export_card(
        title="JSON Export",
        description=(
            "Download a full dump of your data in JSON format. "
            "This format is required if you want to import your data back into EcoBuddy later."
        ),
        button_label="Generate JSON Export",
        export_function=export_data_json,
        session_key="json_export",
        filename="ecobuddy_export.json",
        mime_type="application/json",
        empty_check=lambda data: data == "{}",
        format_name="JSON",
        download_key="download_json",
    )


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
    if st.button("Restore Data"):
        json_content = uploaded_file.read().decode("utf-8")
        with st.spinner("Importing data..."):
            success, message = import_data_json(json_content, strategy=import_strategy.lower())
            if success:
                st.success(message)
                st.info("Please refresh the page or navigate to another section to see the restored data.")
            else:
                st.error(message)

