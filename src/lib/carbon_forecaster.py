"""
Carbon Forecaster for EcoBuddy AI
Projects carbon emissions based on current trends and goals.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import threading
import numpy as np
from sklearn.linear_model import LinearRegression

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    """Data class for forecast results."""
    success: bool
    message: str
    predictions: Optional[List[float]] = None
    dates: Optional[List[str]] = None
    confidence_intervals: Optional[List[Tuple[float, float]]] = None
    trend: str = "stable"
    projected_total: float = 0.0
    projected_average: float = 0.0
    days_forecasted: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CarbonForecaster:
    """
    Projects carbon emissions using various forecasting methods.
    """
    
    def __init__(self):
        self._cache: Dict[str, ForecastResult] = {}
        self._lock = threading.Lock()
        
        logger.info("CarbonForecaster initialized")
    
    def forecast(
        self,
        assessments: List[Dict[str, Any]],
        days: int = 30,
        method: str = "linear"
    ) -> ForecastResult:
        """
        Generate carbon emission forecast.
        
        Args:
            assessments: List of assessment dictionaries
            days: Number of days to forecast
            method: Forecasting method ('linear', 'moving_average', 'exponential')
        
        Returns:
            ForecastResult object
        """
        try:
            if not assessments or len(assessments) < 3:
                return ForecastResult(
                    success=False,
                    message="Insufficient data for forecasting (need at least 3 assessments)"
                )
            
            # Prepare data
            df = self._prepare_data(assessments)
            
            if len(df) < 3:
                return ForecastResult(
                    success=False,
                    message="Insufficient data points after preparation"
                )
            
            # Generate forecast based on method
            if method == "linear":
                result = self._linear_forecast(df, days)
            elif method == "moving_average":
                result = self._moving_average_forecast(df, days)
            elif method == "exponential":
                result = self._exponential_forecast(df, days)
            else:
                result = self._linear_forecast(df, days)
            
            return result
            
        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            return ForecastResult(
                success=False,
                message=f"Forecast failed: {str(e)}"
            )
    
    def _prepare_data(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data for forecasting."""
        # Sort assessments by date
        assessments = sorted(
            assessments,
            key=lambda x: x.get('date', ''),
            reverse=False
        )
        
        dates = []
        values = []
        scores = []
        
        for assessment in assessments:
            date = assessment.get('date')
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date)
                except:
                    continue
            elif isinstance(date, datetime):
                pass
            else:
                continue
            
            footprint = assessment.get('footprint', 0)
            eco_score = assessment.get('eco_score', 0)
            
            dates.append(date)
            values.append(footprint)
            scores.append(eco_score)
        
        return {
            'dates': dates,
            'values': values,
            'scores': scores,
            'count': len(dates)
        }
    
    def _linear_forecast(self, data: Dict[str, Any], days: int) -> ForecastResult:
        """Generate linear regression forecast."""
        values = data['values']
        dates = data['dates']
        
        if len(values) < 3:
            return ForecastResult(
                success=False,
                message="Need at least 3 data points for linear forecast"
            )
        
        # Create feature matrix (days since first assessment)
        X = np.array(range(len(values))).reshape(-1, 1)
        y = np.array(values)
        
        # Fit linear regression
        model = LinearRegression()
        model.fit(X, y)
        
        # Generate predictions
        last_date = dates[-1]
        future_X = np.array(range(len(values), len(values) + days)).reshape(-1, 1)
        predictions = model.predict(future_X)
        
        # Ensure positive predictions
        predictions = np.maximum(predictions, 0)
        
        # Calculate confidence intervals
        residuals = y - model.predict(X)
        residual_std = np.std(residuals)
        z_score = 1.96  # 95% confidence
        
        confidence_intervals = [
            (max(0, p - z_score * residual_std), p + z_score * residual_std)
            for p in predictions
        ]
        
        # Generate dates
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        
        # Calculate statistics
        total = sum(predictions)
        avg = np.mean(predictions)
        
        # Determine trend
        slope = model.coef_[0]
        if slope < -0.01:
            trend = "decreasing"
        elif slope > 0.01:
            trend = "increasing"
        else:
            trend = "stable"
        
        return ForecastResult(
            success=True,
            message="Linear forecast generated successfully",
            predictions=predictions.tolist(),
            dates=[d.isoformat() for d in future_dates],
            confidence_intervals=confidence_intervals,
            trend=trend,
            projected_total=total,
            projected_average=avg,
            days_forecasted=days,
            metadata={
                'slope': float(slope),
                'intercept': float(model.intercept_),
                'r_squared': float(model.score(X, y)),
                'residual_std': float(residual_std)
            }
        )
    
    def _moving_average_forecast(self, data: Dict[str, Any], days: int) -> ForecastResult:
        """Generate moving average forecast."""
        values = data['values']
        dates = data['dates']
        
        if len(values) < 5:
            return ForecastResult(
                success=False,
                message="Need at least 5 data points for moving average forecast"
            )
        
        # Calculate moving average
        window = min(3, len(values) // 2)
        ma = np.convolve(values, np.ones(window)/window, mode='valid')
        last_ma = ma[-1] if len(ma) > 0 else values[-1]
        
        # Standard deviation for confidence intervals
        std = np.std(values[-window:]) if len(values) >= window else np.std(values)
        
        # Generate predictions (constant)
        predictions = [last_ma] * days
        
        # Add slight trend based on recent changes
        if len(values) >= 2:
            recent_change = (values[-1] - values[-2]) / max(1, abs(values[-2]))
            trend_factor = min(0.05, max(-0.05, recent_change))  # Cap at ±5%
            
            for i in range(days):
                predictions[i] = predictions[i] * (1 + trend_factor * (i + 1) / days)
        
        predictions = np.maximum(predictions, 0)
        
        # Confidence intervals
        z_score = 1.96
        confidence_intervals = [
            (max(0, p - z_score * std), p + z_score * std)
            for p in predictions
        ]
        
        # Generate dates
        last_date = dates[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        
        total = sum(predictions)
        avg = np.mean(predictions)
        
        return ForecastResult(
            success=True,
            message="Moving average forecast generated successfully",
            predictions=predictions.tolist(),
            dates=[d.isoformat() for d in future_dates],
            confidence_intervals=confidence_intervals,
            trend="stable",
            projected_total=total,
            projected_average=avg,
            days_forecasted=days,
            metadata={
                'window': window,
                'last_ma': float(last_ma),
                'std': float(std)
            }
        )
    
    def _exponential_forecast(self, data: Dict[str, Any], days: int) -> ForecastResult:
        """Generate exponential smoothing forecast."""
        values = data['values']
        dates = data['dates']
        
        if len(values) < 3:
            return ForecastResult(
                success=False,
                message="Need at least 3 data points for exponential forecast"
            )
        
        # Simple exponential smoothing
        alpha = 0.3  # Smoothing factor
        smoothed = [values[0]]
        
        for value in values[1:]:
            smoothed.append(alpha * value + (1 - alpha) * smoothed[-1])
        
        last_smoothed = smoothed[-1]
        
        # Calculate trend
        if len(smoothed) >= 2:
            trend = (smoothed[-1] - smoothed[-2])
        else:
            trend = 0
        
        # Generate predictions
        predictions = []
        for i in range(days):
            pred = last_smoothed + trend * (i + 1)
            predictions.append(max(0, pred))
        
        # Confidence intervals
        std = np.std(values)
        z_score = 1.96
        confidence_intervals = [
            (max(0, p - z_score * std), p + z_score * std)
            for p in predictions
        ]
        
        # Generate dates
        last_date = dates[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(days)]
        
        total = sum(predictions)
        avg = np.mean(predictions)
        
        if trend < -0.01:
            trend_direction = "decreasing"
        elif trend > 0.01:
            trend_direction = "increasing"
        else:
            trend_direction = "stable"
        
        return ForecastResult(
            success=True,
            message="Exponential forecast generated successfully",
            predictions=predictions.tolist(),
            dates=[d.isoformat() for d in future_dates],
            confidence_intervals=confidence_intervals,
            trend=trend_direction,
            projected_total=total,
            projected_average=avg,
            days_forecasted=days,
            metadata={
                'alpha': alpha,
                'last_smoothed': float(last_smoothed),
                'trend': float(trend)
            }
        )
    
    def forecast_goal(self, assessments: List[Dict[str, Any]], target_value: float) -> Dict[str, Any]:
        """
        Calculate when a user will reach a target value.
        
        Args:
            assessments: List of assessment dictionaries
            target_value: Target value
        
        Returns:
            Dictionary with forecast information
        """
        result = self.forecast(assessments, days=365)  # Forecast up to 1 year
        
        if not result.success:
            return {
                'success': False,
                'message': result.message
            }
        
        predictions = result.predictions
        dates = result.dates
        
        if not predictions:
            return {
                'success': False,
                'message': "No predictions available"
            }
        
        # Find when prediction crosses target
        target_date = None
        for i, pred in enumerate(predictions):
            if pred <= target_value:
                target_date = dates[i]
                break
        
        if target_date:
            days_to_target = (datetime.fromisoformat(target_date) - datetime.now()).days
            return {
                'success': True,
                'target_date': target_date,
                'days_to_target': days_to_target,
                'current_value': assessments[0].get('footprint', 0) if assessments else 0,
                'target_value': target_value,
                'trend': result.trend
            }
        else:
            return {
                'success': True,
                'target_date': None,
                'days_to_target': None,
                'current_value': assessments[0].get('footprint', 0) if assessments else 0,
                'target_value': target_value,
                'trend': result.trend,
                'message': "Target not reached within forecast period"
            }


# Global carbon forecaster instance
_carbon_forecaster: Optional[CarbonForecaster] = None
_carbon_forecaster_lock = threading.Lock()


def get_carbon_forecaster() -> CarbonForecaster:
    """Get or create global carbon forecaster instance."""
    global _carbon_forecaster
    with _carbon_forecaster_lock:
        if _carbon_forecaster is None:
            _carbon_forecaster = CarbonForecaster()
        return _carbon_forecaster


def forecast_carbon(assessments: List[Dict[str, Any]], days: int = 30) -> ForecastResult:
    """Convenience function to forecast carbon emissions."""
    forecaster = get_carbon_forecaster()
    return forecaster.forecast(assessments, days)


def forecast_goal(assessments: List[Dict[str, Any]], target_value: float) -> Dict[str, Any]:
    """Convenience function to forecast goal achievement."""
    forecaster = get_carbon_forecaster()
    return forecaster.forecast_goal(assessments, target_value)