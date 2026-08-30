"""
Sustainability Behavior Intelligence - Trend Detection
Advanced trend detection algorithms for behavioral data.
"""

import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import numpy as np

from intelligence.models import DataPoint, BehaviorTrend, TrendType, TrendDirection

logger = logging.getLogger(__name__)


class TrendDetector:
    """
    Detects trends in sustainability behavior data using various statistical methods.
    """
    
    def __init__(self):
        """Initialize the trend detector."""
        self.min_data_points = 5
        self.confidence_threshold = 0.5
        self.seasonality_threshold = 0.3
        logger.info("Trend Detector initialized")
    
    def detect_trend(self, data_points: List[DataPoint]) -> Optional[BehaviorTrend]:
        """
        Detect trend in a time series of data points.
        
        Args:
            data_points: List of data points
        
        Returns:
            BehaviorTrend: Detected trend or None
        """
        if len(data_points) < self.min_data_points:
            logger.warning(f"Insufficient data points: {len(data_points)}")
            return None
        
        # Sort by timestamp
        sorted_data = sorted(data_points, key=lambda x: x.timestamp)
        timestamps = [dp.timestamp for dp in sorted_data]
        values = [dp.value for dp in sorted_data]
        
        # Create trend object
        trend = BehaviorTrend(
            category=data_points[0].category if data_points else "",
            metric=data_points[0].unit if data_points else "",
            data_points=sorted_data,
            start_date=timestamps[0],
            end_date=timestamps[-1],
            current_value=values[-1],
            baseline_value=values[0],
            min_value=min(values),
            max_value=max(values),
            volatility=statistics.stdev(values) if len(values) > 1 else 0
        )
        
        # Calculate linear regression
        slope, intercept, r_squared = self._linear_regression(timestamps, values)
        trend.slope = slope
        trend.intercept = intercept
        trend.r_squared = r_squared
        
        # Determine trend type and direction
        trend.trend_type, trend.direction = self._classify_trend(
            values, slope, r_squared
        )
        
        # Calculate percent change
        if trend.baseline_value != 0:
            trend.percent_change = ((trend.current_value - trend.baseline_value) / 
                                   abs(trend.baseline_value)) * 100
        else:
            trend.percent_change = float('inf') if trend.current_value > 0 else 0
        
        # Calculate average change per time step
        if len(values) > 1:
            trend.average_change = (values[-1] - values[0]) / len(values)
        
        # Check for seasonality
        seasonality = self._detect_seasonality(values)
        if seasonality:
            trend.has_seasonality = True
            trend.seasonality_period = seasonality['period']
            trend.seasonality_strength = seasonality['strength']
        
        # Calculate confidence
        trend.confidence = self._calculate_confidence(trend)
        
        # Generate description
        trend.description = self._generate_description(trend)
        
        # Generate recommendations
        trend.recommendations = self._generate_recommendations(trend)
        
        return trend
    
    def _linear_regression(self, timestamps: List[datetime], 
                          values: List[float]) -> Tuple[float, float, float]:
        """
        Perform linear regression on time series data.
        
        Returns:
            Tuple: (slope, intercept, r_squared)
        """
        # Convert timestamps to numeric values (days since first timestamp)
        base_time = timestamps[0]
        x = [(t - base_time).total_seconds() / 86400 for t in timestamps]
        
        n = len(x)
        if n == 0:
            return 0, 0, 0
        
        # Calculate means
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        # Calculate slope and intercept
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0, y_mean, 0
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # Calculate R-squared
        ss_total = sum((values[i] - y_mean) ** 2 for i in range(n))
        ss_residual = sum((values[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0
        
        return slope, intercept, r_squared
    
    def _classify_trend(self, values: List[float], 
                       slope: float, 
                       r_squared: float) -> Tuple[TrendType, TrendDirection]:
        """
        Classify the type and direction of a trend.
        """
        # Determine trend type based on slope and r-squared
        if abs(slope) < 0.01:
            trend_type = TrendType.STABLE
            direction = TrendDirection.NEUTRAL
        elif r_squared > 0.8 and slope > 0:
            trend_type = TrendType.LINEAR
            direction = TrendDirection.POSITIVE
        elif r_squared > 0.8 and slope < 0:
            trend_type = TrendType.LINEAR
            direction = TrendDirection.NEGATIVE
        else:
            # Check for exponential patterns
            if len(values) > 5:
                if self._is_exponential(values):
                    trend_type = TrendType.EXPONENTIAL
                    direction = TrendDirection.POSITIVE if values[-1] > values[0] else TrendDirection.NEGATIVE
                elif self._is_logarithmic(values):
                    trend_type = TrendType.LOGARITHMIC
                    direction = TrendDirection.POSITIVE if values[-1] > values[0] else TrendDirection.NEGATIVE
                elif self._is_s_curve(values):
                    trend_type = TrendType.S_CURVE
                    direction = TrendDirection.POSITIVE if values[-1] > values[0] else TrendDirection.NEGATIVE
                else:
                    # Check for volatility
                    if self._is_volatile(values):
                        trend_type = TrendType.VOLATILE
                        direction = TrendDirection.MIXED
                    else:
                        trend_type = TrendType.UNDEFINED
                        direction = TrendDirection.NEUTRAL
            else:
                trend_type = TrendType.UNDEFINED
                direction = TrendDirection.NEUTRAL
        
        return trend_type, direction
    
    def _is_exponential(self, values: List[float]) -> bool:
        """Check if values follow an exponential pattern."""
        if len(values) < 3 or any(v <= 0 for v in values):
            return False
        
        # Check if log of values is linear
        log_values = [math.log(v) for v in values]
        x = list(range(len(log_values)))
        
        slope, _, r_squared = self._linear_regression_from_arrays(x, log_values)
        return r_squared > 0.85
    
    def _is_logarithmic(self, values: List[float]) -> bool:
        """Check if values follow a logarithmic pattern."""
        if len(values) < 3:
            return False
        
        # Check if values vs log of x is linear
        x = list(range(1, len(values) + 1))
        log_x = [math.log(i) for i in x]
        
        _, _, r_squared = self._linear_regression_from_arrays(log_x, values)
        return r_squared > 0.85
    
    def _is_s_curve(self, values: List[float]) -> bool:
        """Check if values follow an S-curve pattern."""
        if len(values) < 5:
            return False
        
        # Check for sigmoid shape (increasing then decreasing rate of change)
        differences = [values[i+1] - values[i] for i in range(len(values)-1)]
        
        if len(differences) < 4:
            return False
        
        # Check if differences increase then decrease
        mid = len(differences) // 2
        first_half = differences[:mid]
        second_half = differences[mid:]
        
        if len(first_half) < 2 or len(second_half) < 2:
            return False
        
        increasing = all(first_half[i] <= first_half[i+1] for i in range(len(first_half)-1))
        decreasing = all(second_half[i] >= second_half[i+1] for i in range(len(second_half)-1))
        
        return increasing and decreasing
    
    def _is_volatile(self, values: List[float]) -> bool:
        """Check if values are volatile."""
        if len(values) < 3:
            return False
        
        # Calculate coefficient of variation
        mean = statistics.mean(values)
        if mean == 0:
            return False
        
        cv = statistics.stdev(values) / abs(mean)
        return cv > 0.5
    
    def _linear_regression_from_arrays(self, x: List[float], y: List[float]) -> Tuple[float, float, float]:
        """Perform linear regression on numeric arrays."""
        n = len(x)
        if n == 0:
            return 0, 0, 0
        
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0, y_mean, 0
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        ss_total = sum((y[i] - y_mean) ** 2 for i in range(n))
        ss_residual = sum((y[i] - (slope * x[i] + intercept)) ** 2 for i in range(n))
        
        r_squared = 1 - (ss_residual / ss_total) if ss_total != 0 else 0
        
        return slope, intercept, r_squared
    
    def _detect_seasonality(self, values: List[float]) -> Optional[Dict[str, Any]]:
        """
        Detect seasonality in the time series.
        """
        if len(values) < 10:
            return None
        
        # Try different periods
        periods = [7, 14, 21, 30]  # Weekly, bi-weekly, tri-weekly, monthly
        best_period = None
        best_strength = 0
        
        for period in periods:
            if len(values) < period * 2:
                continue
            
            strength = self._calculate_seasonality_strength(values, period)
            
            if strength > self.seasonality_threshold and strength > best_strength:
                best_strength = strength
                best_period = period
        
        if best_period:
            return {
                'period': best_period,
                'strength': best_strength
            }
        
        return None
    
    def _calculate_seasonality_strength(self, values: List[float], period: int) -> float:
        """
        Calculate the strength of seasonality for a given period.
        """
        if len(values) < period * 2:
            return 0
        
        # Calculate seasonal means
        seasonal_means = []
        for i in range(period):
            indices = list(range(i, len(values), period))
            if indices:
                seasonal_values = [values[j] for j in indices]
                seasonal_means.append(statistics.mean(seasonal_values))
        
        if len(seasonal_means) < 2:
            return 0
        
        # Calculate variance of seasonal means vs overall mean
        overall_mean = statistics.mean(values)
        variance_seasonal = statistics.variance(seasonal_means) if len(seasonal_means) > 1 else 0
        variance_overall = statistics.variance(values) if len(values) > 1 else 0
        
        if variance_overall == 0:
            return 0
        
        return min(1.0, variance_seasonal / variance_overall)
    
    def _calculate_confidence(self, trend: BehaviorTrend) -> float:
        """
        Calculate confidence level of the detected trend.
        """
        confidence = 0.0
        
        # R-squared contributes
        confidence += trend.r_squared * 0.4
        
        # Data points count contributes
        data_count_ratio = min(1.0, len(trend.data_points) / 30)
        confidence += data_count_ratio * 0.3
        
        # Volatility contributes (lower volatility = higher confidence)
        if trend.volatility > 0:
            volatility_confidence = min(1.0, 1 / (1 + trend.volatility))
            confidence += volatility_confidence * 0.2
        
        # Time span contributes
        days_span = (trend.end_date - trend.start_date).days
        time_confidence = min(1.0, days_span / 90)
        confidence += time_confidence * 0.1
        
        return min(1.0, confidence)
    
    def _generate_description(self, trend: BehaviorTrend) -> str:
        """
        Generate a human-readable description of the trend.
        """
        if trend.trend_type == TrendType.IMPROVING:
            return f"{trend.metric} is consistently improving with {trend.confidence*100:.0f}% confidence"
        elif trend.trend_type == TrendType.DECLINING:
            return f"{trend.metric} is declining with {trend.confidence*100:.0f}% confidence"
        elif trend.trend_type == TrendType.STABLE:
            return f"{trend.metric} is stable with minimal variation"
        elif trend.trend_type == TrendType.VOLATILE:
            return f"{trend.metric} is volatile with significant fluctuations"
        elif trend.trend_type == TrendType.CYCLICAL:
            return f"{trend.metric} shows cyclical patterns every {trend.seasonality_period} days"
        elif trend.trend_type == TrendType.EXPONENTIAL:
            return f"{trend.metric} is showing exponential growth"
        elif trend.trend_type == TrendType.PLATEAU:
            return f"{trend.metric} has plateaued after significant improvement"
        else:
            return f"{trend.metric} shows {trend.direction.value} trend with confidence {trend.confidence*100:.0f}%"
    
    def _generate_recommendations(self, trend: BehaviorTrend) -> List[str]:
        """
        Generate recommendations based on the trend.
        """
        recommendations = []
        
        if trend.trend_type == TrendType.DECLINING:
            recommendations.append(
                f"Your {trend.metric} is declining. Review recent changes and "
                f"identify what's causing the decline."
            )
            
            if trend.confidence > 0.7:
                recommendations.append(
                    f"The decline in {trend.metric} is significant. "
                    f"Take immediate action to reverse this trend."
                )
        
        elif trend.trend_type == TrendType.IMPROVING:
            recommendations.append(
                f"Great job! Your {trend.metric} is improving. Keep up the good work!"
            )
            
            if trend.percent_change > 20:
                recommendations.append(
                    f"Your {trend.metric} has improved by {trend.percent_change:.1f}%! "
                    f"Can you identify what caused this improvement and replicate it?"
                )
        
        elif trend.trend_type == TrendType.PLATEAU:
            recommendations.append(
                f"Your {trend.metric} has plateaued. Consider setting new targets "
                f"or trying different strategies to continue improving."
            )
        
        elif trend.trend_type == TrendType.VOLATILE:
            recommendations.append(
                f"Your {trend.metric} is volatile. Try to identify the cause of "
                f"fluctuations and work on consistency."
            )
        
        elif trend.trend_type == TrendType.STABLE and trend.current_value < 50:
            recommendations.append(
                f"Your {trend.metric} is stable but below optimal levels. "
                f"Consider setting improvement goals."
            )
        
        if trend.has_seasonality:
            recommendations.append(
                f"Your {trend.metric} shows seasonal patterns. "
                f"Plan activities to leverage your stronger periods."
            )
        
        return recommendations