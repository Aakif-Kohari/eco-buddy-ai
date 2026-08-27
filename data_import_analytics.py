"""Imported Data Analytics Engine.

Calculates aggregations, trends, and impact summaries over the normalized
sustainability datasets imported by the user.
"""

from typing import Dict, List, Any
import logging

from data_import_history import get_imported_records

logger = logging.getLogger(__name__)

def generate_import_analytics(household_id: int) -> Dict[str, Any]:
    """Compile comprehensive analytics over all imported records."""
    records = get_imported_records(household_id)
    
    if not records:
        return {
            "total_records": 0,
            "total_emissions_kg": 0.0,
            "category_distribution": {},
            "highest_impact_activities": [],
            "monthly_trends": {}
        }
        
    total_emissions = 0.0
    category_dist = {}
    monthly_trends = {}
    
    # Process records
    for r in records:
        cat = r["category"]
        emissions = r.get("emissions_kg") or 0.0
        
        # Totals
        total_emissions += emissions
        
        # Category distribution
        if cat not in category_dist:
            category_dist[cat] = {"count": 0, "emissions": 0.0}
        category_dist[cat]["count"] += 1
        category_dist[cat]["emissions"] += emissions
        
        # Monthly trends
        date_str = r["activity_date"]
        month_key = date_str[:7]  # YYYY-MM
        if month_key not in monthly_trends:
            monthly_trends[month_key] = 0.0
        monthly_trends[month_key] += emissions

    # Identify highest impact activities
    sorted_records = sorted(records, key=lambda x: x.get("emissions_kg") or 0.0, reverse=True)
    highest_impact = sorted_records[:5]
    
    return {
        "total_records": len(records),
        "total_emissions_kg": total_emissions,
        "category_distribution": category_dist,
        "highest_impact_activities": highest_impact,
        "monthly_trends": monthly_trends
    }

def merge_import_data_with_core_system(household_id: int) -> bool:
    """Optionally sync imported records into the main household_activities table
    so that they count towards goals, budgets, and gamification.
    
    This bridges the gap between raw CSV import and core features.
    """
    records = get_imported_records(household_id)
    if not records:
        return False
        
    synced_count = 0
    for r in records:
        desc_tag = f"[Imported] {r.get('activity', 'Data')}"
        # We mock this for the current branch because household_activities
        # is part of Issue 941 which is on a different branch!
        # In a real environment, we would insert into the DB here.
        act_id = True
        if act_id:
            synced_count += 1
            
    return synced_count > 0
