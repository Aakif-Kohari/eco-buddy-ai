"""Household Reporting System.

Generates detailed, exportable reports (Markdown/HTML/CSV equivalents) 
for a household's sustainability performance over a selected period.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from household import get_household, get_members
from household_activities import get_category_breakdown, get_activities, get_member_contribution_breakdown
from household_goals import get_goals
from household_metrics import get_household_analytics_summary

logger = logging.getLogger(__name__)

def generate_markdown_report(household_id: int, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """Generate a comprehensive Markdown string report for a household.
    
    Args:
        household_id: ID of the household.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        
    Returns:
        A formatted Markdown string.
    """
    hh = get_household(household_id)
    if not hh:
        return "# Error\nHousehold not found."
        
    members = get_members(household_id)
    analytics = get_household_analytics_summary(household_id)
    
    score_data = analytics["score_data"]
    metrics = analytics["metrics"]
    member_brk = analytics["member_breakdown"]
    
    today = datetime.now().strftime("%Y-%m-%d")
    period_str = f"{start_date or 'Beginning'} to {end_date or 'Present'}"
    
    md = []
    md.append(f"# Sustainability Report: {hh['name']}")
    md.append(f"**Generated On:** {today}")
    md.append(f"**Period:** {period_str}")
    md.append(f"**Region:** {hh['region']}")
    md.append("\n---\n")
    
    # 1. Executive Summary
    md.append("## 1. Executive Summary")
    md.append(f"- **Sustainability Score:** {score_data['score']} / 100")
    md.append(f"- **Total Carbon Footprint:** {metrics['total_footprint_kg']:.1f} kg CO2e")
    md.append(f"- **Active Members:** {metrics['total_members']}")
    md.append(f"- **Goal Completion Rate:** {metrics['goal_completion_rate']:.1f}%")
    if score_data.get("feedback"):
        md.append(f"\n> **Insight:** {score_data['feedback']}")
    md.append("\n---\n")
    
    # 2. Category Breakdown
    md.append("## 2. Category Breakdown")
    cat_data = score_data.get("category_breakdown", {})
    if not cat_data or sum(cat_data.values()) == 0:
        md.append("No activity data available.")
    else:
        md.append("| Category | Footprint (kg CO2e) |")
        md.append("|----------|---------------------|")
        for cat, val in sorted(cat_data.items(), key=lambda x: x[1], reverse=True):
            if val > 0:
                md.append(f"| {cat} | {val:.1f} |")
    md.append("\n---\n")
        
    # 3. Member Contributions
    md.append("## 3. Member Contributions")
    md.append(f"**Total Shared Footprint:** {member_brk['shared_total']:.1f} kg CO2e")
    md.append("\n| Member | Individual | Shared (Allocated) | Total |")
    md.append("|--------|------------|--------------------|-------|")
    
    for m_id, m_data in member_brk["members"].items():
        ind = m_data["individual"]
        alloc = m_data["allocated"]
        tot = m_data["total"]
        md.append(f"| {m_data['name']} | {ind:.1f} | {alloc:.1f} | {tot:.1f} |")
    md.append("\n---\n")
        
    # 4. Goals Status
    md.append("## 4. Goals Status")
    goals = get_goals(household_id)
    if not goals:
        md.append("No goals set.")
    else:
        for g in goals:
            status_icon = "🟢" if g['status'] == 'active' else "✅" if g['status'] == 'completed' else "❌"
            progress = min(100.0, (g['current_value'] / g['target_value'] * 100) if g['target_value'] > 0 else 0)
            md.append(f"### {status_icon} {g['title']}")
            md.append(f"- **Metric:** {g['metric'].title()}")
            md.append(f"- **Progress:** {g['current_value']} / {g['target_value']} {g['unit']} ({progress:.1f}%)")
            md.append(f"- **Deadline:** {g['deadline'] or 'None'}")
            md.append("")
    md.append("\n---\n")
            
    # 5. Recent Log
    md.append("## 5. Recent Activities")
    activities = get_activities(household_id, limit=20)
    if not activities:
        md.append("No recent activities.")
    else:
        md.append("| Date | Category | Description | Value | Impact |")
        md.append("|------|----------|-------------|-------|--------|")
        for act in activities:
            desc = act['description'] or "None"
            val = f"{act['value']} {act['unit']}"
            imp = f"{act['impact_kg_co2']:.1f} kg"
            md.append(f"| {act['activity_date']} | {act['category']} | {desc} | {val} | {imp} |")
            
    return "\n".join(md)


def generate_csv_export(household_id: int) -> str:
    """Generate a raw CSV string of all household activities for export."""
    import csv
    import io
    
    activities = get_activities(household_id, limit=10000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(["ID", "Date", "Category", "Member", "Value", "Unit", "Impact_kg_CO2", "Description", "Logged_At"])
    
    for act in activities:
        member_name = act['member_name'] if act['member_id'] else "Shared"
        writer.writerow([
            act['id'],
            act['activity_date'],
            act['category'],
            member_name,
            act['value'],
            act['unit'],
            act['impact_kg_co2'],
            act['description'],
            act['created_at']
        ])
        
    return output.getvalue()
