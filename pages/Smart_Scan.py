import streamlit as st

from bill_categorizer import categorize_bill, get_available_categories
from database import save_scanned_receipt
from receipt_parser import mock_ocr_extraction, parse_receipt_text

st.set_page_config(page_title="Smart Scan", page_icon="📸", layout="wide")

st.title("📸 Automated Receipt & Bill Analysis")
st.markdown(
    "Upload utility bills or grocery receipts to automatically extract, categorize, and log your carbon footprint data."
)

# --- Session State ---
if "scanned_data" not in st.session_state:
    st.session_state.scanned_data = None

# --- Upload Interface ---
uploaded_file = st.file_uploader(
    "Upload Receipt or Bill (PDF/Image)", type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    st.info(
        f"File uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)"
    )

    if st.button("🔍 Extract & Analyze", type="primary"):
        with st.spinner("Running OCR and categorization pipeline..."):
            # 1. Mock OCR Extraction
            raw_text = mock_ocr_extraction(uploaded_file.name)

            # 2. Parse Text
            parsed = parse_receipt_text(raw_text)

            # 3. Categorize
            categorized = categorize_bill(parsed)

            st.session_state.scanned_data = categorized
            st.success("Analysis complete! Please review the extracted data below.")

# --- Review and Confirmation ---
if st.session_state.scanned_data is not None:
    data = st.session_state.scanned_data

    st.subheader("📝 Extracted Data Preview")
    st.markdown(
        "You can edit the values below before saving to your assessment history."
    )

    col1, col2 = st.columns(2)
    with col1:
        edit_vendor = st.text_input("Vendor", value=data["vendor"])
        edit_date = st.date_input("Date", value=data["date"])
    with col2:
        edit_cost = st.number_input(
            "Total Cost ($)", min_value=0.0, step=0.01, value=data["total_cost"]
        )
        edit_category = st.selectbox(
            "Category",
            get_available_categories(),
            index=get_available_categories().index(data["primary_category"]),
        )

    edit_kwh = st.number_input(
        "Energy Used (kWh) - Optional",
        min_value=0.0,
        step=1.0,
        value=float(data["energy_kwh"]) if data["energy_kwh"] else 0.0,
    )

    st.markdown("**Raw OCR Text:**")
    st.code(data["raw_text"], language="text")

    colA, colB = st.columns(2)
    if colA.button("✅ Confirm & Save to History"):
        save_scanned_receipt(
            vendor=edit_vendor,
            date=str(edit_date),
            total_cost=edit_cost,
            energy_kwh=edit_kwh if edit_kwh > 0 else None,
            category=edit_category,
        )
        st.success("Receipt saved to your assessment history!")
        st.session_state.scanned_data = None  # Reset

    if colB.button("❌ Discard"):
        st.session_state.scanned_data = None
        st.info("Scan discarded.")
