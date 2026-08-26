import os

base_dir = r"F:\ECSoC'26 Contributions\eco-buddy-ai"
eb_dir = os.path.join(base_dir, "environmental_benchmarking")

# 1. advanced_math.py
advanced_math_code = '''\
"""
Advanced mathematical normalizations and forecasting for benchmarking.
"""
import math
from typing import List, Tuple

class DataNormalizer:
    """Provides various normalization techniques for environmental data."""
    
    @staticmethod
    def min_max_normalize(value: float, min_val: float, max_val: float, invert: bool = False) -> float:
        """Standard Min-Max normalization mapping to 0-1."""
        if math.isnan(value):
            return 0.5
        range_val = max_val - min_val
        if range_val <= 0:
            return 0.5
        clamped = max(min_val, min(max_val, value))
        norm = (clamped - min_val) / range_val
        return 1.0 - norm if invert else norm
        
    @staticmethod
    def z_score_normalize(value: float, mean: float, std_dev: float) -> float:
        """Z-Score normalization (standard score)."""
        if std_dev <= 0:
            return 0.0
        return (value - mean) / std_dev
        
    @staticmethod
    def sigmoid_normalize(value: float, mean: float, scale: float = 1.0) -> float:
        """Sigmoid normalization mapping to 0-1, useful for unbounded high-variance data."""
        if scale == 0:
            return 0.5
        z = (value - mean) / scale
        return 1.0 / (1.0 + math.exp(-z))
        
    @staticmethod
    def robust_scale(value: float, median: float, p25: float, p75: float) -> float:
        """Robust scaling using IQR to handle extreme outliers like excessive flights."""
        iqr = p75 - p25
        if iqr <= 0:
            return 0.0
        return (value - median) / iqr

class TrendForecaster:
    """Forecasting logic for predicting future environmental footprints."""
    
    @staticmethod
    def simple_linear_regression(x: List[float], y: List[float]) -> Tuple[float, float]:
        """Returns (slope, intercept) for simple linear regression."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0, sum(y) / len(y) if y else 0.0
            
        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_xx = sum(xi * xi for xi in x)
        
        denominator = (n * sum_xx - sum_x * sum_x)
        if denominator == 0:
            return 0.0, sum_y / n
            
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        return slope, intercept
        
    @classmethod
    def forecast_next_periods(cls, historical_values: List[float], periods: int = 3) -> List[float]:
        """Forecast the next 'periods' values using linear trend."""
        if not historical_values:
            return []
        if len(historical_values) == 1:
            return [historical_values[0]] * periods
            
        x = list(range(len(historical_values)))
        slope, intercept = cls.simple_linear_regression(x, historical_values)
        
        predictions = []
        last_x = x[-1]
        for i in range(1, periods + 1):
            val = slope * (last_x + i) + intercept
            predictions.append(max(0.0, val)) # Footprint can't be negative
            
        return predictions

    @classmethod
    def calculate_projection_confidence(cls, historical_values: List[float]) -> float:
        """Calculate a pseudo-confidence score (0-100) based on variance around the trend."""
        if len(historical_values) < 3:
            return 50.0
            
        x = list(range(len(historical_values)))
        slope, intercept = cls.simple_linear_regression(x, historical_values)
        
        # Calculate R-squared
        mean_y = sum(historical_values) / len(historical_values)
        ss_tot = sum((y - mean_y) ** 2 for y in historical_values)
        if ss_tot == 0:
            return 100.0
            
        ss_res = sum((y - (slope * xi + intercept)) ** 2 for xi, y in zip(x, historical_values))
        r_squared = 1.0 - (ss_res / ss_tot)
        
        return max(0.0, min(100.0, r_squared * 100.0))
'''

# 2. recommendations.py
recommendations_code = '''\
"""
Detailed rule engine for actionable sustainability recommendations based on benchmarks.
"""
from typing import List
from .models import CategoryComparison

class RecommendationEngine:
    """Generates highly specific recommendations from benchmark data."""
    
    def generate_recommendations(self, comparisons: dict) -> List[str]:
        """Process all category comparisons and return a list of actionable advice."""
        recs = []
        
        if "transport" in comparisons:
            recs.extend(self._transport_recs(comparisons["transport"]))
        if "electricity" in comparisons:
            recs.extend(self._electricity_recs(comparisons["electricity"]))
        if "diet" in comparisons:
            recs.extend(self._diet_recs(comparisons["diet"]))
        if "flights" in comparisons:
            recs.extend(self._flight_recs(comparisons["flights"]))
            
        return recs
        
    def _transport_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.percentile <= 20:
            recs.append("CRITICAL: Your transport emissions are in the bottom 20%. Switch to EV, carpooling, or public transit immediately to see massive reductions.")
        elif comp.percentile <= 40:
            recs.append("Your transport emissions are below average. Try replacing 2 car trips a week with cycling or walking.")
        elif comp.percentile >= 80:
            recs.append("EXCELLENT: Your transport emissions are very low! Consider sharing your commuting habits with the community.")
        return recs

    def _electricity_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.percentile <= 20:
            recs.append("CRITICAL: Your home energy usage is extremely high. Schedule a home energy audit, check insulation, and upgrade to a smart thermostat.")
            recs.append("Consider switching to a green energy provider or installing solar panels if feasible.")
        elif comp.percentile <= 40:
            recs.append("Your electricity footprint is above average. Ensure all bulbs are LED and unplug phantom loads.")
        return recs

    def _diet_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.percentile <= 20:
            recs.append("CRITICAL: Dietary footprint is very high. Reducing red meat consumption by just 50% can dramatically improve this score.")
        elif comp.percentile <= 40:
            recs.append("Consider adopting a 'Meatless Monday' routine to lower your dietary carbon impact.")
        elif comp.percentile >= 90:
            recs.append("EXCELLENT: Your diet is highly sustainable! Your food choices are actively fighting climate change.")
        return recs

    def _flight_recs(self, comp: CategoryComparison) -> List[str]:
        recs = []
        if comp.user_value > 2000: # high absolute flights
            recs.append("Air travel is dominating your footprint. For every necessary flight, consider high-quality carbon offsets.")
            recs.append("Can any of your recent flights be replaced with high-speed rail or virtual meetings?")
        return recs
'''

# 3. Add to existing HistoryAnalyzer in history.py
history_extension = '''\
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
'''

with open(os.path.join(eb_dir, "advanced_math.py"), "w") as f:
    f.write(advanced_math_code)
with open(os.path.join(eb_dir, "recommendations.py"), "w") as f:
    f.write(recommendations_code)

# Append to history.py
with open(os.path.join(eb_dir, "history.py"), "a") as f:
    f.write(history_extension)

