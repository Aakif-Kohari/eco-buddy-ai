import os
import sqlite3
from datetime import datetime
import calendar
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont
from src.core.database_connection import database_connection

DB_NAME = os.getenv("ECO_BUDDY_DB", "eco_buddy.db")

def _fetch_assessments_for_year(user_id: int, year: int):
    """Fetch all assessments for a user within a specific year."""
    start_date = f"{year}-01-01 00:00:00"
    end_date = f"{year}-12-31 23:59:59"
    
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, transport, distance, electricity, diet, flights, footprint, eco_score, created_at
            FROM assessments
            WHERE user_id = ? AND created_at >= ? AND created_at <= ?
            ORDER BY created_at ASC
        """, (user_id, start_date, end_date))
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def aggregate_annual_data(user_id: int, year: int) -> dict:
    """Aggregates a user's environmental data for the given year, grouped by month."""
    assessments = _fetch_assessments_for_year(user_id, year)
    
    monthly_data = {m: {"footprint": 0.0, "count": 0, "eco_score": 0.0} for m in range(1, 13)}
    
    total_footprint = 0.0
    total_transport = 0.0
    total_electricity = 0.0
    total_flights = 0
    total_eco_score = 0
    
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
            
            total_transport += a['distance']
            total_electricity += a['electricity']
            total_flights += a['flights']
            
            # Simple heuristic
            category_emissions["transport"] += (a['distance'] * 0.1)
            category_emissions["electricity"] += (a['electricity'] * 0.3)
            category_emissions["flights"] += (a['flights'] * 500.0)
            
            if a['diet'] == 'meat_heavy': category_emissions["diet"] += 3.0
            elif a['diet'] == 'vegetarian': category_emissions["diet"] += 1.5
            elif a['diet'] == 'vegan': category_emissions["diet"] += 1.0
            else: category_emissions["diet"] += 2.0
            
            # Month grouping
            try:
                dt = datetime.fromisoformat(a['created_at'].replace('Z', ''))
                m = dt.month
                monthly_data[m]["footprint"] += a['footprint']
                monthly_data[m]["eco_score"] += a['eco_score']
                monthly_data[m]["count"] += 1
            except Exception:
                pass
                
    sum_cats = sum(category_emissions.values())
    if sum_cats > 0:
        for k in category_emissions:
            category_emissions[k] = (category_emissions[k] / sum_cats) * total_footprint
            
    # Calculate monthly averages
    monthly_trends = []
    for m in range(1, 13):
        count = monthly_data[m]["count"]
        monthly_trends.append({
            "month": m,
            "month_name": calendar.month_abbr[m],
            "total_footprint": monthly_data[m]["footprint"],
            "avg_eco_score": monthly_data[m]["eco_score"] / count if count > 0 else 0,
            "count": count
        })
    
    return {
        "user_id": user_id,
        "year": year,
        "total_footprint_kg": total_footprint,
        "avg_eco_score": total_eco_score / len(assessments) if assessments else 0,
        "assessments_count": len(assessments),
        "total_transport_km": total_transport,
        "total_electricity_kwh": total_electricity,
        "total_flights": total_flights,
        "category_breakdown": category_emissions,
        "monthly_trends": monthly_trends
    }

def compute_yoy_trends(current_year_data: dict, previous_year_data: dict) -> dict:
    """Computes year-over-year trend changes."""
    def calc_trend(curr, prev):
        if prev == 0:
            return {"change_pct": 0, "direction": "neutral" if curr == 0 else "up"}
        diff = curr - prev
        pct = (diff / prev) * 100
        direction = "up" if diff > 0 else "down" if diff < 0 else "neutral"
        return {"change_pct": round(pct, 2), "direction": direction, "absolute_diff": round(diff, 2)}
        
    return {
        "footprint_trend": calc_trend(current_year_data.get("total_footprint_kg", 0), previous_year_data.get("total_footprint_kg", 0)),
        "eco_score_trend": calc_trend(current_year_data.get("avg_eco_score", 0), previous_year_data.get("avg_eco_score", 0)),
        "assessments_trend": calc_trend(current_year_data.get("assessments_count", 0), previous_year_data.get("assessments_count", 0))
    }

def extract_milestones(user_id: int, year: int, annual_data: dict) -> dict:
    """Analyzes data to find achievements."""
    milestones = {}
    
    monthly = annual_data.get("monthly_trends", [])
    if not monthly:
        return milestones
        
    # Best month (lowest footprint where count > 0)
    active_months = [m for m in monthly if m["count"] > 0]
    if active_months:
        best_month = min(active_months, key=lambda x: x["total_footprint"])
        milestones["Best Month"] = f"{best_month['month_name']} (Lowest Footprint: {best_month['total_footprint']:.1f} kg)"
        
        # Longest streak
        max_streak = 0
        current_streak = 0
        for m in monthly:
            if m["count"] > 0:
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0
        milestones["Longest Streak"] = f"{max_streak} consecutive months"
    
    assessments = _fetch_assessments_for_year(user_id, year)
    if assessments:
        first_date = assessments[0]['created_at'].split(' ')[0]
        milestones["First Assessment"] = f"Logged on {first_date}"
        
        best_score = max(assessments, key=lambda x: x['eco_score'])
        milestones["Highest Eco Score"] = f"{best_score['eco_score']:.0f}/100"
        
    return milestones

def compute_community_percentiles(user_id: int, year: int, total_footprint: float) -> dict:
    """Calculates percentile against the community."""
    with database_connection(DB_NAME) as conn:
        cursor = conn.cursor()
        
        start_date = f"{year}-01-01 00:00:00"
        end_date = f"{year}-12-31 23:59:59"
        
        # Get total footprint per user for the year
        cursor.execute("""
            SELECT user_id, SUM(footprint) as total
            FROM assessments
            WHERE created_at >= ? AND created_at <= ?
            GROUP BY user_id
        """, (start_date, end_date))
        
        all_users = cursor.fetchall()
        
    if not all_users:
        return {"percentile": 50, "narrative": "Insufficient community data"}
        
    # Filter out users with 0 footprint
    valid_users = [row[1] for row in all_users if row[1] > 0]
    if not valid_users:
        return {"percentile": 50, "narrative": "Insufficient community data"}
        
    valid_users.sort()
    
    # Find rank
    rank = 0
    for i, score in enumerate(valid_users):
        if total_footprint <= score:
            rank = i
            break
    else:
        rank = len(valid_users)
        
    percentile = (rank / len(valid_users)) * 100
    
    better_than = 100 - percentile
    narrative = f"Your footprint was lower than {better_than:.0f}% of the community!"
    
    return {"percentile": better_than, "narrative": narrative}

def generate_annual_pdf(report_data: dict, output_path: str) -> str:
    """Generates a PDF report summarizing the annual data."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.darkgreen)
    c.drawString(50, height - 60, f"Year in Review: {report_data['year']}")
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 14)
    c.drawString(50, height - 100, f"Total Carbon Footprint: {report_data.get('total_footprint_kg', 0):.2f} kg CO2")
    c.drawString(50, height - 125, f"Average Eco Score: {report_data.get('avg_eco_score', 0):.1f} / 100")
    c.drawString(50, height - 150, f"Total Assessments: {report_data.get('assessments_count', 0)}")
    
    # Milestones
    y_pos = height - 200
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y_pos, "Milestones & Achievements")
    y_pos -= 30
    
    c.setFont("Helvetica", 12)
    milestones = report_data.get("milestones", {})
    for k, v in milestones.items():
        c.drawString(70, y_pos, f"• {k}: {v}")
        y_pos -= 20
        
    # Percentile
    y_pos -= 20
    c.setFont("Helvetica-Bold", 14)
    percentile_data = report_data.get("percentile_data", {})
    c.drawString(50, y_pos, "Community Standing: " + percentile_data.get("narrative", ""))
    y_pos -= 40
        
    # Breakdown
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y_pos, "Annual Category Breakdown")
    y_pos -= 30
    
    c.setFont("Helvetica", 12)
    for cat, val in report_data.get('category_breakdown', {}).items():
        c.drawString(70, y_pos, f"- {cat.capitalize()}: {val:.2f} kg CO2")
        y_pos -= 20
        
    # Tree equivalence
    y_pos -= 30
    trees = report_data.get('total_footprint_kg', 0) / 21.77
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(50, y_pos, f"Your emissions are roughly equivalent to what {trees:.1f} mature trees absorb in a year.")
    
    c.showPage()
    c.save()
    return output_path

def generate_social_card(report_data: dict, output_path: str) -> str:
    """Generates an image card using Pillow for social media sharing."""
    width, height = 1080, 1080
    
    img = Image.new('RGB', (width, height), color=(20, 60, 40))
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("arial.ttf", 80)
        font_subtitle = ImageFont.truetype("arial.ttf", 50)
        font_metric = ImageFont.truetype("arial.ttf", 60)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_metric = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    draw.text((80, 100), f"My {report_data['year']} Eco-Journey", fill=(200, 255, 200), font=font_title)
    
    draw.text((80, 250), f"{report_data.get('total_footprint_kg', 0):.0f} kg", fill=(255, 255, 255), font=font_title)
    draw.text((80, 350), "Total CO2 Emissions", fill=(150, 200, 150), font=font_subtitle)
    
    y = 500
    milestones = report_data.get("milestones", {})
    if milestones:
        draw.text((80, y), "Highlights:", fill=(200, 255, 200), font=font_metric)
        y += 80
        for k, v in list(milestones.items())[:3]:
            draw.text((80, y), f"• {k}: {v}", fill=(255, 255, 255), font=font_small)
            y += 60
            
    y += 40
    percentile = report_data.get('percentile_data', {}).get('narrative', '')
    draw.text((80, y), percentile, fill=(150, 255, 150), font=font_small)
    
    draw.text((width - 350, height - 100), "#EcoBuddyApp", fill=(100, 150, 100), font=font_subtitle)
    
    img.save(output_path)
    return output_path
