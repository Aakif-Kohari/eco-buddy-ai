import os
import json
import sqlite3
from datetime import datetime
import calendar
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from database_connection import database_connection

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

def _fetch_assessments_for_month(user_id: int, year: int, month: int):
    """Fetch all assessments for a user within a specific month and year."""
    start_date = f"{year}-{month:02d}-01 00:00:00"
    _, last_day = calendar.monthrange(year, month)
    end_date = f"{year}-{month:02d}-{last_day} 23:59:59"
    
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, transport, distance, electricity, diet, flights, footprint, eco_score, created_at
            FROM assessments
            WHERE user_id = ? AND created_at >= ? AND created_at <= ?
        """, (user_id, start_date, end_date))
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def aggregate_monthly_data(user_id: int, year: int, month: int) -> dict:
    """Aggregates a user's environmental data for the given month."""
    assessments = _fetch_assessments_for_month(user_id, year, month)
    
    total_footprint = 0.0
    total_transport = 0.0
    total_electricity = 0.0
    total_flights = 0
    total_eco_score = 0
    
    # Category aggregation logic (assuming distances/kwh are proportional to footprint, 
    # but we'll use a simplified breakdown for the pie chart).
    # Since diet is text, we'll assign an average footprint value per diet entry, 
    # but actual footprint is precalculated. 
    # We will approximate category emissions for the pie chart based on raw metrics.
    # A more sophisticated approach would recalculate using emission_factors, but we'll approximate.
    
    category_emissions = {
        "transport": 0.0,
        "electricity": 0.0,
        "diet": 0.0,
        "flights": 0.0
    }
    
    if assessments:
        for a in assessments:
            total_footprint += a['footprint']
            total_eco_score += a['eco_score']
            
            # Simple heuristic to split footprint into categories
            total_transport += a['distance']
            total_electricity += a['electricity']
            total_flights += a['flights']
            
            # Example approximation of footprint split
            # For simplicity, assign generic percentages if we can't recalculate perfectly,
            # or use some rough factors.
            # In a real scenario we'd re-run the engine or store granular footprints.
            # Here we'll just store raw totals and calculate rough splits
            
            category_emissions["transport"] += (a['distance'] * 0.1) # rough factor
            category_emissions["electricity"] += (a['electricity'] * 0.3)
            category_emissions["flights"] += (a['flights'] * 500.0)
            
            # diet footprint is roughly baseline
            if a['diet'] == 'meat_heavy': category_emissions["diet"] += 3.0
            elif a['diet'] == 'vegetarian': category_emissions["diet"] += 1.5
            elif a['diet'] == 'vegan': category_emissions["diet"] += 1.0
            else: category_emissions["diet"] += 2.0
            
    # Normalize category emissions so they sum up to total_footprint
    sum_cats = sum(category_emissions.values())
    if sum_cats > 0:
        for k in category_emissions:
            category_emissions[k] = (category_emissions[k] / sum_cats) * total_footprint
    
    # Fetch total XP for the user (overall, or we could filter by month if xp_transactions had timestamps)
    # We will just report the assessment counts for now.
    
    return {
        "user_id": user_id,
        "year": year,
        "month": month,
        "total_footprint_kg": total_footprint,
        "avg_eco_score": total_eco_score / len(assessments) if assessments else 0,
        "assessments_count": len(assessments),
        "total_transport_km": total_transport,
        "total_electricity_kwh": total_electricity,
        "total_flights": total_flights,
        "category_breakdown": category_emissions
    }

def compute_monthly_trends(current_month_data: dict, previous_month_data: dict) -> dict:
    """Computes month-over-month trend changes."""
    def calc_trend(curr, prev):
        if prev == 0:
            return {"change_pct": 0, "direction": "neutral" if curr == 0 else "up"}
        diff = curr - prev
        pct = (diff / prev) * 100
        direction = "up" if diff > 0 else "down" if diff < 0 else "neutral"
        return {"change_pct": round(pct, 2), "direction": direction, "absolute_diff": round(diff, 2)}
        
    return {
        "footprint_trend": calc_trend(current_month_data.get("total_footprint_kg", 0), previous_month_data.get("total_footprint_kg", 0)),
        "eco_score_trend": calc_trend(current_month_data.get("avg_eco_score", 0), previous_month_data.get("avg_eco_score", 0)),
        "assessments_trend": calc_trend(current_month_data.get("assessments_count", 0), previous_month_data.get("assessments_count", 0))
    }

def generate_actionable_insights(user_data: dict) -> list[str]:
    """Generates personalized insights based on the weakest categories."""
    insights = []
    
    if user_data.get("assessments_count", 0) == 0:
        return ["Log more assessments this month to get personalized insights."]
        
    cats = user_data.get("category_breakdown", {})
    if not cats:
        return ["Keep logging data to see category insights."]
        
    # Find the top 2 highest emission categories
    sorted_cats = sorted(cats.items(), key=lambda x: x[1], reverse=True)
    
    for cat, val in sorted_cats[:2]:
        if val > 0:
            if cat == "transport":
                insights.append("Your transport emissions are high. Consider carpooling, biking, or public transit for short trips.")
            elif cat == "electricity":
                insights.append("Electricity usage is a major factor. Try upgrading to LED bulbs or unplugging devices when not in use.")
            elif cat == "diet":
                insights.append("Diet is contributing significantly to your footprint. Try incorporating more plant-based meals each week.")
            elif cat == "flights":
                insights.append("Air travel has a massive impact. Look into direct flights, economy class, or alternative travel for closer destinations.")
                
    if not insights:
        insights.append("You are doing great! Keep maintaining your sustainable habits.")
        
    return insights

def generate_monthly_pdf(report_data: dict, output_path: str) -> str:
    """Generates a PDF report summarizing the monthly data."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 24)
    month_name = calendar.month_name[report_data['month']]
    c.drawString(50, height - 50, f"Monthly Report - {month_name} {report_data['year']}")
    
    c.setFont("Helvetica", 14)
    c.drawString(50, height - 100, f"Total Carbon Footprint: {report_data.get('total_footprint_kg', 0):.2f} kg CO2")
    c.drawString(50, height - 130, f"Average Eco Score: {report_data.get('avg_eco_score', 0):.2f}")
    c.drawString(50, height - 160, f"Assessments Logged: {report_data.get('assessments_count', 0)}")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 210, "Category Breakdown")
    c.setFont("Helvetica", 12)
    y_pos = height - 240
    for cat, val in report_data.get('category_breakdown', {}).items():
        c.drawString(70, y_pos, f"- {cat.capitalize()}: {val:.2f} kg CO2")
        y_pos -= 20
        
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y_pos - 30, "Actionable Insights")
    c.setFont("Helvetica", 12)
    y_pos -= 60
    
    # Needs a dummy 'insights' passed or we generate it here
    insights = report_data.get("insights", generate_actionable_insights(report_data))
    for insight in insights:
        c.drawString(70, y_pos, f"• {insight}")
        y_pos -= 20
        
    c.showPage()
    c.save()
    return output_path
