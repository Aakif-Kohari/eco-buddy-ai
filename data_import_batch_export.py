"""Comprehensive Export Formatting for Import Analytics.

Generates structured JSON, CSV, and formatted string reports spanning
the entire import history, allowing organizations to audit their data ingestion.
"""

import json
import csv
import io
import logging
from typing import Dict, Any, List

from data_import_history import get_import_history, get_imported_records
from data_import_analytics import generate_import_analytics

logger = logging.getLogger(__name__)

from data_import_privacy_filter import PrivacyFilter

def generate_audit_report_json(household_id: int) -> str:
    """Generate a full JSON audit report of all imported data and its analytics."""
    history = get_import_history(household_id)
    records = get_imported_records(household_id)
    
    # Apply Privacy Filter before export
    filter = PrivacyFilter()
    safe_records = filter.sanitize_records(records)
    
    analytics = generate_import_analytics(household_id)
    
    payload = {
        "metadata": {
            "household_id": household_id,
            "report_type": "Import Audit",
            "version": "1.0"
        },
        "analytics_summary": analytics,
        "import_jobs": [
            {
                "import_id": h["import_id"],
                "filename": h["filename"],
                "status": h["status"],
                "records_processed": h["total_records"],
                "valid": h["valid_records"],
                "invalid": h["invalid_records"],
                "date": h["import_date"]
            } for h in history
        ],
        "normalized_records_sample": safe_records[:100] # Cap to 100 for JSON audit size
    }
    
    return json.dumps(payload, indent=2)


def generate_flat_csv_export(household_id: int) -> bytes:
    """Generate a flattened CSV containing all normalized records and their warnings."""
    records = get_imported_records(household_id)
    if not records:
        return b"ID,Import_ID,Date,Category,Activity,Original_Value,Original_Unit,Normalized_Value,Normalized_Unit,Emissions_kg,Record_Hash,Warnings\n"
        
    filter = PrivacyFilter()
    safe_records = filter.sanitize_records(records)
        
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Import_ID", "Date", "Category", "Activity", 
        "Original_Value", "Original_Unit", 
        "Normalized_Value", "Normalized_Unit", 
        "Emissions_kg", "Record_Hash", "Warnings"
    ])
    
    for r in safe_records:
        writer.writerow([
            r.get("id"),
            r.get("import_id"),
            r.get("activity_date"),
            r.get("category"),
            r.get("activity"),
            r.get("original_value"),
            r.get("original_unit"),
            r.get("normalized_value"),
            r.get("normalized_unit"),
            r.get("emissions_kg"),
            r.get("record_hash"),
            r.get("warnings")
        ])
        
    return output.getvalue().encode('utf-8')


def generate_executive_summary_md(household_id: int) -> str:
    """Generate a Markdown string summarizing the imported data impact."""
    analytics = generate_import_analytics(household_id)
    history = get_import_history(household_id)
    
    md = []
    md.append(f"# Executive Import Summary")
    md.append(f"\n## Overall Impact")
    md.append(f"- **Total Imported Records:** {analytics['total_records']}")
    md.append(f"- **Total Imported Footprint:** {analytics['total_emissions_kg']:.1f} kg CO2e")
    
    md.append(f"\n## Category Breakdown")
    for cat, data in analytics['category_distribution'].items():
        md.append(f"- **{cat}:** {data['count']} records, {data['emissions']:.1f} kg CO2e")
        
    md.append(f"\n## Top 5 Highest Impact Activities")
    for idx, act in enumerate(analytics['highest_impact_activities'], 1):
        md.append(f"{idx}. {act['category']} - {act.get('activity', 'Unknown')} on {act['activity_date']} ({act['emissions_kg']:.1f} kg CO2e)")
        
    md.append(f"\n## Import Job History")
    for h in history:
        md.append(f"- **{h['filename']}** ({h['import_date']}): {h['status'].upper()}, {h['valid_records']}/{h['total_records']} valid records.")
        
    return "\n".join(md)
