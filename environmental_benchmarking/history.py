"""
History tracking and trend analysis for Environmental Benchmarking.
"""
from typing import List, Optional
import sqlite3
import pandas as pd
from .models import UserAssessment, HistoricalTrendData
from .engine import BenchmarkEngine

class HistoryAnalyzer:
    """Handles historical DB fetching and trend calculation."""
    
    def __init__(self, db_path: str = "eco_buddy.db"):
        self.db_path = db_path
        self.engine = BenchmarkEngine()
        
    def get_user_history(self, user_id: int, limit: int = 50) -> List[UserAssessment]:
        """Fetch the assessment history for a specific user."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM assessments WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?",
                (user_id, limit)
            )
            rows = cursor.fetchall()
            conn.close()
            
            # Convert to models, reversing to get chronological order
            return [UserAssessment.from_db_row(dict(row)) for row in reversed(rows)]
        except Exception as e:
            # Fallback or empty if table doesn't exist
            print(f"Error fetching history: {e}")
            return []

    def calculate_trends(self, user_id: int, profile_id: str = "global") -> Optional[HistoricalTrendData]:
        """Calculate historical trends against a specific profile."""
        assessments = self.get_user_history(user_id)
        if not assessments:
            return None
            
        dates = []
        footprints = []
        eco_scores = []
        transports = []
        electricities = []
        diets = []
        flights = []
        percentiles = []
        
        for a in assessments:
            dates.append(a.date)
            footprints.append(a.footprint)
            eco_scores.append(a.eco_score)
            
            transports.append(self.engine.extract_carbon_value("transport", a))
            electricities.append(self.engine.extract_carbon_value("electricity", a))
            diets.append(self.engine.extract_carbon_value("diet", a))
            flights.append(self.engine.extract_carbon_value("flights", a))
            
            # Get overall percentile vs chosen profile for this specific assessment
            res = self.engine.compare_assessment(a, profile_id)
            percentiles.append(res.overall_percentile)
            
        return HistoricalTrendData(
            dates=dates,
            footprints=footprints,
            eco_scores=eco_scores,
            transport_vals=transports,
            electricity_vals=electricities,
            diet_vals=diets,
            flights_vals=flights,
            percentiles=percentiles
        )
    def get_forecast(self, user_id: int, periods: int = 3) -> dict:
        """Uses advanced math to project future footprint."""
        from .advanced_math import TrendForecaster
        trends = self.calculate_trends(user_id)
        if not trends or len(trends.footprints) < 2:
            return {"predicted_footprints": [], "confidence": 0.0}
            
        predictions = TrendForecaster.forecast_next_periods(trends.footprints, periods)
        conf = TrendForecaster.calculate_projection_confidence(trends.footprints)
        
        return {
            "predicted_footprints": predictions,
            "confidence": conf
        }
