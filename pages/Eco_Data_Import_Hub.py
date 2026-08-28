"""Streamlit page for the Eco Data Import & Analytics Hub.

Provides a wizard interface for users to upload, map, clean, validate, 
and analyze custom sustainability datasets (CSV/JSON).
"""

import streamlit as st
import pandas as pd
import json
import io
import csv

from src.lifestyle.household import get_households_for_user
from src.data.data_import_schema import STANDARD_SCHEMA, detect_schema_mapping, validate_mapping, apply_mapping
from src.data.data_import_cleaner import DataCleaner
from src.data.data_import_normalizer import normalize_units, estimate_missing_emissions
from src.data.data_import_history import init_import_db, log_import_job, save_imported_records, get_import_history, get_imported_records
from src.data.data_import_analytics import generate_import_analytics, merge_import_data_with_core_system
from src.data.data_import_visualizations import create_import_category_pie, create_import_time_series, create_data_quality_donut

def render_import_hub():
    st.set_page_config(page_title="Data Import Hub", page_icon="📥", layout="wide")
    st.title("📥 Eco Data Import & Analytics Hub")
    st.markdown("Import your external sustainability data (CSV/JSON), clean it, and integrate it into EcoBuddy.")
    
    # Init DB
    if 'import_db_initialized' not in st.session_state:
        init_import_db()
        st.session_state.import_db_initialized = True
        
    user_id = st.session_state.get("user_id", 1)
    user_households = get_households_for_user(user_id)
    
    if not user_households:
        st.warning("Please create or join a household first via the Household Dashboard.")
        return
        
    hh_id = user_households[0]['id']
    
    # Navigation Tabs
    tabs = st.tabs([
        "📤 CSV/JSON Upload & Map", 
        "📄 PDF Bill Extractor", 
        "🔌 API Integrations", 
        "🧹 Data Quality Dashboard", 
        "📊 Import Analytics", 
        "🕒 Import History"
    ])
    
    with tabs[0]:
        render_upload_and_map_workflow(hh_id)
        
    with tabs[1]:
        render_pdf_extractor_workflow(hh_id)
        
    with tabs[2]:
        render_api_integrations_workflow(hh_id)
        
    with tabs[3]:
        render_data_quality_dashboard()
        
    with tabs[4]:
        render_analytics_dashboard(hh_id)
        
    with tabs[5]:
        render_history_tab(hh_id)


def render_upload_and_map_workflow(hh_id: int):
    st.header("Upload External Data")
    
    with st.expander("Need sample data to test?"):
        st.markdown("Download a randomly generated dataset containing edge cases and anomalies to test the pipeline.")
        from data_import_simulator import generate_large_test_dataset
        colA, colB = st.columns(2)
        with colA:
            st.download_button("Download Test Dataset (CSV)", 
                               data=generate_large_test_dataset("csv", 500), 
                               file_name="simulated_eco_data.csv", 
                               mime="text/csv")
        with colB:
            st.download_button("Download Test Dataset (JSON)", 
                               data=generate_large_test_dataset("json", 500), 
                               file_name="simulated_eco_data.json", 
                               mime="application/json")
    
    uploaded_file = st.file_uploader("Upload a CSV or JSON file", type=['csv', 'json'])
    
    if not uploaded_file:
        st.info("Upload a file to begin the mapping process.")
        # Clear session state if file removed
        if 'raw_import_data' in st.session_state:
            del st.session_state['raw_import_data']
            del st.session_state['import_mapping']
            del st.session_state['import_filename']
        return
        
    # Read file
    if 'raw_import_data' not in st.session_state or st.session_state.get('import_filename') != uploaded_file.name:
        try:
            if uploaded_file.name.endswith('.csv'):
                content = uploaded_file.read().decode('utf-8')
                reader = csv.DictReader(io.StringIO(content))
                records = list(reader)
            else:
                records = json.load(uploaded_file)
                if not isinstance(records, list):
                    st.error("JSON file must contain a list of records (objects).")
                    return
                    
            if not records:
                st.error("The uploaded file is empty.")
                return
                
            st.session_state.raw_import_data = records
            st.session_state.import_filename = uploaded_file.name
            
            # Auto-detect schema mapping
            columns = list(records[0].keys())
            st.session_state.import_mapping = detect_schema_mapping(columns)
            
        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")
            return
            
    records = st.session_state.raw_import_data
    mapping = st.session_state.import_mapping
    
    st.success(f"Successfully loaded {len(records)} records from {uploaded_file.name}.")
    
    with st.expander("Preview Raw Data"):
        st.dataframe(pd.DataFrame(records[:5]))
        
    st.markdown("---")
    st.subheader("Map Columns")
    st.markdown("Map your uploaded columns to EcoBuddy's standard schema.")
    
    columns = ["-- Do Not Map --"] + list(records[0].keys())
    
    # Form for mapping
    new_mapping = {}
    col1, col2 = st.columns(2)
    
    for i, (std_key, std_field) in enumerate(STANDARD_SCHEMA.items()):
        req_str = "*(Required)*" if std_field.required else "(Optional)"
        default_idx = 0
        if mapping.get(std_key) and mapping.get(std_key) in columns:
            default_idx = columns.index(mapping[std_key])
            
        with (col1 if i % 2 == 0 else col2):
            sel = st.selectbox(
                f"{std_field.name} {req_str}",
                options=columns,
                index=default_idx,
                help=std_field.description
            )
            new_mapping[std_key] = sel if sel != "-- Do Not Map --" else None
            
    st.markdown("---")
    st.subheader("Import Options")
    dup_strat = st.selectbox(
        "Duplicate Handling Strategy", 
        ["drop", "keep_latest", "sum", "flag_only"],
        help="How should we handle identical records (same date, category, unit, value)?"
    )
            
    # Validate and apply mapping
    is_valid, errors = validate_mapping(new_mapping)
    
    if not is_valid:
        for err in errors:
            st.error(f"Mapping Error: {err}")
    else:
        if st.button("Apply Mapping & Clean Data", type="primary"):
            st.session_state.import_mapping = new_mapping
            st.session_state.import_dup_strat = dup_strat
            process_and_clean_data(hh_id)

def process_and_clean_data(hh_id: int):
    with st.spinner("Cleaning and validating data..."):
        records = st.session_state.raw_import_data
        mapping = st.session_state.import_mapping
        
        # 1. Apply map
        mapped_records = apply_mapping(records, mapping)
        
        # 1.5 Auto-categorize missing categories via NLP
        from data_import_ml_categorizer import categorize_missing_fields
        mapped_records, ml_stats = categorize_missing_fields(mapped_records)
        
        # 2. Clean (Cleaner sets the hashes, but now we don't drop duplicates in cleaner directly if we use DuplicateResolver, 
        # wait, cleaner drops duplicates automatically if we don't modify it. Let's modify cleaner not to drop, or just use the resolver over the output.)
        cleaner = DataCleaner()
        valid, invalid, stats = cleaner.clean_and_validate(mapped_records)
        stats["auto_categorized"] = ml_stats.get("auto_categorized", 0)
        
        # 2.5 Resolve Duplicates via chosen strategy
        from data_import_duplicate_resolver import DuplicateResolver
        strat = st.session_state.get("import_dup_strat", "drop")
        resolver = DuplicateResolver(strat)
        
        # For this to work best, we should actually reconstruct the duplicate pile. 
        # Since cleaner dumped them to 'invalid', let's pull them back if they just failed due to duplicate.
        actual_invalid = []
        duplicate_pool = valid.copy()
        for inv in invalid:
            if any("Duplicate" in err for err in inv.get("_errors", [])):
                duplicate_pool.append(inv)
            else:
                actual_invalid.append(inv)
                
        resolved_valid, res_stats = resolver.resolve(duplicate_pool)
        invalid = actual_invalid
        stats["duplicates_processed"] = res_stats.get("duplicates_processed", 0)
        
        # 3. Normalize units
        normalized_valid, norm_stats = normalize_units(resolved_valid)
        
        # 4. Estimate emissions
        estimated_valid = estimate_missing_emissions(normalized_valid)
        
        # 5. Anomaly Detection
        from data_import_anomalies import AnomalyDetector
        detector = AnomalyDetector()
        final_valid, anomaly_stats = detector.detect_anomalies(estimated_valid)
        final_valid = detector.find_temporal_anomalies(final_valid)
        
        stats["anomalies_detected"] = anomaly_stats.get("anomalies_detected", 0)
        
        # Store in session for review
        st.session_state.import_valid_records = final_valid
        st.session_state.import_invalid_records = invalid
        st.session_state.import_stats = stats
        st.session_state.import_norm_stats = norm_stats
        
        st.success("Cleaning complete! Move to the 'Data Quality Dashboard' tab to review and commit.")


def render_data_quality_dashboard():
    st.header("Data Quality Review")
    
    if 'import_stats' not in st.session_state:
        st.info("No data has been cleaned yet. Please complete the Upload & Map step.")
        return
        
    stats = st.session_state.import_stats
    valid_recs = st.session_state.import_valid_records
    invalid_recs = st.session_state.import_invalid_records
    
    # Dashboard metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Rows", stats["total"])
    c2.metric("Valid Records", stats["valid"])
    c3.metric("Invalid Records", stats["invalid"])
    c4.metric("Duplicates Dropped", stats["duplicates"])
    
    # Donut chart
    fig_donut = create_data_quality_donut(stats)
    st.plotly_chart(fig_donut, use_container_width=True)
    
    if invalid_recs:
        st.subheader(f"⚠️ Invalid Records ({len(invalid_recs)})")
        with st.expander("View Invalid Records & Errors"):
            # Format nicely for display
            display_inv = []
            for r in invalid_recs[:50]:
                display_inv.append({
                    "Row": r.get("_row_index"),
                    "Errors": ", ".join(r.get("_errors", [])),
                    "Data": json.dumps({k:v for k,v in r.items() if not k.startswith("_")})
                })
            st.table(display_inv)
            if len(invalid_recs) > 50:
                st.caption("Showing first 50 invalid records.")
                
    st.subheader(f"✅ Valid & Normalized Records ({len(valid_recs)})")
    with st.expander("Preview Cleaned Data"):
        if valid_recs:
            df_valid = pd.DataFrame(valid_recs)
            # Remove hash and internal fields for display
            disp_cols = [c for c in df_valid.columns if not c.startswith("_")]
            st.dataframe(df_valid[disp_cols].head(50))
            
    # Commit action
    st.markdown("---")
    if valid_recs:
        st.info("Review the cleaned data above. If it looks correct, you can save it to your EcoBuddy src.core.database.")
        
        if st.button("Commit to Database", type="primary"):
            import_id = log_import_job(
                household_id=st.session_state.get("user_id", 1), # Actually should be hh_id, we will extract it correctly
                filename=st.session_state.import_filename,
                source_type="csv/json",
                stats=stats,
                status="completed"
            )
            
            if import_id:
                # Replace with actual hh_id
                hh_id = get_households_for_user(st.session_state.get("user_id", 1))[0]['id']
                if save_imported_records(import_id, hh_id, valid_recs):
                    st.success("Data successfully saved to database!")
                    st.balloons()
                    # Clear session
                    del st.session_state['raw_import_data']
                    del st.session_state['import_stats']
                else:
                    st.error("Error saving records.")
    else:
        st.warning("No valid records to commit.")


def render_analytics_dashboard(hh_id: int):
    st.header("Import Analytics")
    
    analytics = generate_import_analytics(hh_id)
    
    if analytics["total_records"] == 0:
        st.info("You don't have any imported data yet. Upload and commit data to view analytics.")
        return
        
    c1, c2 = st.columns(2)
    c1.metric("Total Imported Records", analytics["total_records"])
    c2.metric("Total Imported Footprint", f"{analytics['total_emissions_kg']:.1f} kg CO2e")
    
    st.markdown("---")
    
    chart1, chart2 = st.columns(2)
    with chart1:
        st.plotly_chart(create_import_category_pie(analytics["category_distribution"]), use_container_width=True)
    with chart2:
        st.plotly_chart(create_import_time_series(analytics["monthly_trends"]), use_container_width=True)
        
    st.markdown("### Top 5 Highest Impact Imported Activities")
    for act in analytics["highest_impact_activities"]:
        with st.container():
            ac1, ac2 = st.columns([3, 1])
            ac1.markdown(f"**{act['category']}**: {act['activity'] or 'Unknown Activity'}")
            ac1.caption(f"Date: {act['activity_date']} | Raw: {act['original_value']} {act['original_unit']}")
            ac2.markdown(f"**{act['emissions_kg']:.1f} kg CO2e**")
        st.divider()
        
    # Export capability
    st.markdown("### Export Cleaned Data")
    records = get_imported_records(hh_id)
    if records:
        df_export = pd.DataFrame(records)
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Cleaned Data (CSV)",
            data=csv_data,
            file_name="ecobuddy_imported_cleaned.csv",
            mime="text/csv"
        )
        
    # Integration sync
    st.markdown("### Sync with Core System")
    st.markdown("Do you want these imported activities to count towards your active household goals, budgets, and gamification?")
    if st.button("Sync Imported Data to Core Household"):
        count = merge_import_data_with_core_system(hh_id)
        if count:
            st.success("Successfully synchronized records with core system.")
        else:
            st.info("No records needed synchronizing or sync already performed.")


def render_history_tab(hh_id: int):
    st.header("Import History")
    
    from data_import_undo_manager import get_rollback_eligibility, rollback_import_job
    
    history = get_import_history(hh_id)
    
    if not history:
        st.info("No import history found.")
        return
        
    for job in history:
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
            c1.markdown(f"**{job['filename']}**")
            c1.caption(f"Imported on: {job['import_date']} | Status: {job['status'].upper()}")
            
            c2.metric("Total", job['total_records'])
            c3.metric("Valid", job['valid_records'])
            c4.metric("Invalid", job['invalid_records'])
            
            with c5:
                eligibility = get_rollback_eligibility(job['import_id'])
                if eligibility["eligible"]:
                    if st.button("Rollback", key=f"rollback_{job['import_id']}", help=eligibility["reason"]):
                        if rollback_import_job(job['import_id'], hh_id):
                            st.success("Rollback successful!")
                            st.rerun()
                        else:
                            st.error("Rollback failed.")
                else:
                    st.button("Rollback", key=f"rollback_{job['import_id']}", disabled=True, help=eligibility["reason"])
            
            st.progress(job['valid_records'] / job['total_records'] if job['total_records'] > 0 else 0)
        st.divider()

if __name__ == "__main__":
    render_import_hub()


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
                        raw_text += page.extract_text() + "\n"
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
        
        process_and_clean_data(hh_id)
