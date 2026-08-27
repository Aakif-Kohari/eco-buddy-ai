import os

with open('pages/Eco_Data_Import_Hub.py', 'r', encoding='utf-8') as src:
    text = src.read()

new_code = """
def render_pdf_extractor_workflow(hh_id: int):
    st.header("Utility Bill PDF Extractor")
    st.markdown("Upload your utility bills in PDF or Text format to automatically extract your usage.")
    
    try:
        import PyPDF2
    except ImportError:
        st.error("PyPDF2 not installed. Use text format instead.")
        
    from data_import_pdf_parser import PDFUtilityBillParser
    
    uploaded_pdf = st.file_uploader("Upload Utility Bill", type=['pdf', 'txt'])
    
    if uploaded_pdf:
        with st.spinner("Parsing document..."):
            raw_text = ""
            if uploaded_pdf.name.endswith('.pdf'):
                try:
                    import PyPDF2
                    pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
                    for page in pdf_reader.pages:
                        raw_text += page.extract_text() + "\\n"
                except Exception as e:
                    st.error(f"Could not read PDF: {e}")
                    return
            else:
                raw_text = uploaded_pdf.read().decode('utf-8')
                
            parser = PDFUtilityBillParser()
            extracted = parser.parse_text(raw_text)
            
            if extracted:
                st.success(f"Successfully extracted {len(extracted)} records!")
                st.dataframe(pd.DataFrame(extracted))
                
                if st.button("Process & Add to Data Quality Dashboard", key='pdf_proc'):
                    st.session_state.raw_import_data = extracted
                    st.session_state.import_filename = uploaded_pdf.name
                    st.session_state.import_mapping = detect_schema_mapping(list(extracted[0].keys()))
                    process_and_clean_data(hh_id)
            else:
                st.warning("Could not extract any standard billing data.")

def render_api_integrations_workflow(hh_id: int):
    st.header("External API Integrations")
    st.markdown("Connect your Smart Home, EV, or travel accounts to automatically sync sustainability data.")
    
    from data_import_api_connectors import ConnectorManager, TeslaAPIConnector, OpowerConnector, FlightAwareConnector
    
    manager = ConnectorManager()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Tesla EV Sync")
        tesla_key = st.text_input("Tesla API Key", type="password", key="tesla_key")
        if st.button("Sync Tesla"):
            with st.spinner("Authenticating and fetching telemetry..."):
                conn = TeslaAPIConnector(tesla_key)
                if conn.authenticate():
                    data = conn.sync("2026-01-01", "2026-12-31")
                    st.success(f"Synced {len(data)} charging/driving records.")
                    manager.register_connector("tesla", conn)
                    push_api_data_to_pipeline(data, "Tesla_Sync.json", hh_id)
                else:
                    st.error("Authentication failed.")
                    
    with col2:
        st.subheader("Smart Meter (Opower)")
        opower_key = st.text_input("Opower Key", type="password", key="opower_key")
        if st.button("Sync Meter"):
            with st.spinner("Fetching smart meter usage..."):
                conn = OpowerConnector(opower_key)
                if conn.authenticate():
                    data = conn.sync("2026-01-01", "2026-12-31")
                    st.success(f"Synced {len(data)} meter readings.")
                    push_api_data_to_pipeline(data, "Opower_Sync.json", hh_id)
                else:
                    st.error("Authentication failed.")
                    
    with col3:
        st.subheader("FlightAware")
        fa_key = st.text_input("FlightAware Key", type="password", key="fa_key")
        if st.button("Sync Flights"):
            with st.spinner("Finding historical flights..."):
                conn = FlightAwareConnector(fa_key)
                if conn.authenticate():
                    data = conn.sync("2026-01-01", "2026-12-31")
                    st.success(f"Synced {len(data)} flights.")
                    push_api_data_to_pipeline(data, "FlightAware_Sync.json", hh_id)
                else:
                    st.error("Authentication failed.")

def push_api_data_to_pipeline(data: list, filename: str, hh_id: int):
    if data:
        st.session_state.raw_import_data = data
        st.session_state.import_filename = filename
        
        # We need to map it correctly. The api connectors map to the standard schema directly.
        from data_import_schema import STANDARD_SCHEMA
        identity_map = {k: k for k in STANDARD_SCHEMA.keys()}
        st.session_state.import_mapping = identity_map
        
        # We don't need to call process_and_clean_data directly if the user wants to review.
        # But for UI simplicity, we will push it through.
        # process_and_clean_data(hh_id) # Let the user review it on the Dashboard.
"""

text = text + '\n' + new_code

with open('pages/Eco_Data_Import_Hub.py', 'w', encoding='utf-8') as dst:
    dst.write(text)
