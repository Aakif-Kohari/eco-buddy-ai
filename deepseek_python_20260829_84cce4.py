"""
Sustainability Behavior Intelligence - Predictive Analytics
Predicts future sustainability performance based on historical data.
"""

import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

from intelligence.models import DataPoint, PredictionResult
from intelligence.trends import TrendDetector

logger = logging.getLogger(__name__)


class PredictiveAnalyzer:
    """
    Analyzes historical data to make predictions about future performance.
    """
    
    def __init__(self):
        """Initialize the predictive analyzer."""
        self.trend_detector = TrendDetector()
        self.min_data_points = 10
        self.confidence_levels = {
            'high': 0.95,
            'medium': 0.85,
            'low': 0.70
        }
        logger.info("Predictive Analyzer initialized")
    
    def predict_future(self,
                      data_points: List[DataPoint],
                      horizon_days: int = 30,
                      confidence_level: str = 'medium') -> List[PredictionResult]:
        """
        Predict future values based on historical data.
        
        Args:
            data_points: Historical data points
            horizon_days: Number of days to predict into the future
            confidence_level: 'high', 'medium', or 'low'
        
        Returns:
            List[PredictionResult]: Predictions for future time points
        """
        if len(data_points) < self.min_data_points:
            logger.warning(f"Insufficient data for prediction: {len(data_points)} points")
            return []
        
        # Sort data by timestamp
        sorted_data = sorted(data_points, key=lambda x: x.timestamp)
        values = [dp.value for dp in sorted_data]
        timestamps = [dp.timestamp for dp in sorted_data]
        
        # Detect trend
        trend = self.trend_detector.detect_trend(sorted_data)
        
        if not trend:
            logger.warning("Could not detect trend for prediction")
            return []
        
        # Choose prediction model based on trend type
        if trend.trend_type == TrendType.LINEAR:
            predictions = self._predict_linear(trend, horizon_days)
        elif trend.trend_type == TrendType.EXPONENTIAL:
            predictions = self._predict_exponential(trend, horizon_days)
        elif trend.trend_type == TrendType.STABLE:
            predictions = self._predict_stable(trend, horizon_days)
        else:
            predictions = self._predict_linear(trend, horizon_days)  # Fallback
        
        # Calculate confidence intervals
        confidence = self.confidence_levels.get(confidence_level, 0.85)
        predictions = self._add_confidence_intervals(predictions, values, confidence)
        
        return predictions
    
    def predict_goal_achievement(self, 
                                data_points: List[DataPoint],
                                target_value: float,
                                target_date: Optional[datetime] = None) -> Optional[datetime]:
        """
        Predict when a goal will be achieved.
        
        Args:
            data_points: Historical data points
            target_value: Target value to achieve
            target_date: Optional target date (for confidence check)
        
        Returns:
            Optional[datetime]: Predicted achievement date
        """
        if len(data_points) < self.min_data_points:
            return None
        
        sorted_data = sorted(data_points, key=lambda x: x.timestamp)
        values = [dp.value for dp in sorted_data]
        
        # Check if target already achieved
        if values[-1] >= target_value:
            return sorted_data[-1].timestamp
        
        # Calculate rate of change
        current_value = values[-1]
        days_elapsed = (sorted_data[-1].timestamp - sorted_data[0].timestamp).days
        
        if days_elapsed == 0:
            return None
        
        # Average improvement per day
        improvement_rate = (current_value - values[0]) / days_elapsed
        
        if improvement_rate <= 0:
            return None
        
        # Calculate days needed
        days_needed = (target_value - current_value) / improvement_rate
        
        # Check if target date is reasonable
        if target_date:
            target_days = (target_date - datetime.now()).days
            if days_needed > target_days * 1.5:
                return None  # Target date seems unrealistic
        
        return datetime.now() + timedelta(days=days_needed)
    
    def _predict_linear(self, trend: Any, horizon_days: int) -> List[PredictionResult]:
        """Generate linear predictions."""
        predictions = []
        
        for i in range(1, horizon_days + 1):
            predicted_value = trend.intercept + (trend.slope * i)
            prediction_date = datetime.now() + timedelta(days=i)
            
            predictions.append(
                PredictionResult(
                    category=trend.category,
                    metric=trend.metric,
                    predicted_value=predicted_value,
                    prediction_date=datetime.now(),
                    target_date=prediction_date,
                    horizon_days=i,
                    model_type='linear',
                    data_points_used=len(trend.data_points)
                )
            )
        
        return predictions
    
    def _predict_exponential(self, trend: Any, horizon_days: int) -> List[PredictionResult]:
        """Generate exponential predictions."""
        predictions = []
        
        # Use exponential model: y = a * e^(b*t)
        values = [dp.value for dp in trend.data_points]
        if len(values) < 2:
            return self._predict_linear(trend, horizon_days)
        
        # Calculate growth rate
        current = values[-1]
        previous = values[-2]
        
        if previous <= 0:
            return self._predict_linear(trend, horizon_days)
        
        growth_rate = current / previous
        
        for i in range(1, horizon_days + 1):
            predicted_value = current * (growth_rate ** i)
            prediction_date = datetime.now() + timedelta(days=i)
            
            predictions.append(
                PredictionResult(
                    category=trend.category,
                    metric=trend.metric,
                    predicted_value=predicted_value,
                    prediction_date=datetime.now(),
                    target_date=prediction_date,
                    horizon_days=i,
                    model_type='exponential',
                    data_points_used=len(trend.data_points)
                )
            )
        
        return predictions
    
    def _predict_stable(self, trend: Any, horizon_days: int) -> List[PredictionResult]:
        """Generate stable predictions."""
        predictions = []
        current_value = trend.current_value
        volatility = trend.volatility
        
        for i in range(1, horizon_days + 1):
            # Add small random noise based on volatility
            noise = (statistics.stdev([dp.value for dp in trend.data_points]) * 
                    (i / horizon_days) * 0.1) if trend.data_points else 0
            predicted_value = current_value + noise
            prediction_date = datetime.now() + timedelta(days=i)
            
            predictions.append(
                PredictionResult(
                    category=trend.category,
                    metric=trend.metric,
                    predicted_value=predicted_value,
                    prediction_date=datetime.now(),
                    target_date=prediction_date,
                    horizon_days=i,
                    model_type='stable',
                    data_points_used=len(trend.data_points)
                )
            )
        
        return predictions
    
    def _add_confidence_intervals(self,
                                 predictions: List[PredictionResult],
                                 historical_values: List[float],
                                 confidence: float) -> List[PredictionResult]:
        """
        Add confidence intervals to predictions.
        """
        if len(historical_values) < 2:
            return predictions
        
        # Calculate standard deviation of historical values
        stdev = statistics.stdev(historical_values)
        
        # Calculate margin of error (using z-score for confidence level)
        z_scores = {
            0.70: 1.04,
            0.85: 1.44,
            0.95: 1.96
        }
        z_score = z_scores.get(round(confidence, 2), 1.44)
        
        margin_of_error = z_score * stdev / math.sqrt(len(historical_values))
        
        # Apply confidence intervals to each prediction
        for pred in predictions:
            pred.confidence_level = confidence
            pred.confidence_interval_lower = pred.predicted_value - margin_of_error
            pred.confidence_interval_upper = pred.predicted_value + margin_of_error
            pred.is_reliable = confidence >= 0.85
            
            # Check if prediction seems reasonable
            if pred.predicted_value < 0:
                pred.predicted_value = 0
                pred.confidence_interval_lower = 0
        
        return predictions
    
    def calculate_prediction_accuracy(self,
                                     predictions: List[PredictionResult],
                                     actual_values: List[DataPoint]) -> float:
        """
        Calculate accuracy of predictions against actual values.
        
        Args:
            predictions: List of predictions
            actual_values: Actual data points
        
        Returns:
            float: MAPE (Mean Absolute Percentage Error)
        """
        if not predictions or not actual_values:
            return 0
        
        # Align predictions with actual values
        errors = []
        
        for pred in predictions:
            # Find closest actual value
            closest = min(
                actual_values,
                key=lambda x: abs((x.timestamp - pred.target_date).total_seconds())
            )
            
            if closest.value == 0:
                continue
            
            error = abs((pred.predicted_value - closest.value) / closest.value) * 100
            errors.append(error)
        
        if not errors:
            return 0
        
        return 100 - statistics.mean(errors)  # Convert to accuracy percentage