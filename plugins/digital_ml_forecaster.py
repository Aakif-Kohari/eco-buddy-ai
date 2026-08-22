import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from typing import Dict, Any, List

class DigitalMLForecaster:
    """
    Advanced Machine Learning module that predicts a user's future digital carbon footprint
    based on their historical screen time and usage trends.
    """

    def __init__(self, historical_emissions_df: pd.DataFrame):
        """
        Expects a DataFrame with columns: ['date', 'daily_kg_co2']
        Dates should be sorted chronologically.
        """
        self.df = historical_emissions_df.copy()
        if not self.df.empty and 'date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['date'])
            self.df = self.df.sort_values('date').reset_index(drop=True)
            # Create a numerical time index for regression (days since start)
            self.df['day_index'] = (self.df['date'] - self.df['date'].min()).dt.days
            
        self.model = None
        self.poly = None

    def _train_model(self, degree: int = 2) -> bool:
        """Trains a polynomial regression model to capture curved trends (e.g., escalating usage)."""
        if self.df.empty or len(self.df) < 5:
            # Not enough data to train a meaningful ML model
            return False
            
        X = self.df[['day_index']].values
        y = self.df['daily_kg_co2'].values
        
        self.poly = PolynomialFeatures(degree=degree)
        X_poly = self.poly.fit_transform(X)
        
        self.model = LinearRegression()
        self.model.fit(X_poly, y)
        return True

    def predict_future_emissions(self, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Predicts future daily emissions and detects if the trajectory is dangerous.
        """
        if not self._train_model():
            return {
                "success": False,
                "error": "Insufficient historical data (need at least 5 days)."
            }
            
        # Generate future day indices
        last_day_index = self.df['day_index'].max()
        future_indices = np.arange(last_day_index + 1, last_day_index + 1 + days_ahead).reshape(-1, 1)
        
        # Predict
        future_poly = self.poly.transform(future_indices)
        predictions = self.model.predict(future_poly)
        
        # Prevent negative emissions in predictions
        predictions = np.maximum(predictions, 0)
        
        # Analyze trend
        current_avg = self.df['daily_kg_co2'].tail(7).mean()
        future_avg = np.mean(predictions[-7:]) # Average of the last week of predictions
        
        percent_change = ((future_avg - current_avg) / current_avg) * 100 if current_avg > 0 else 0
        
        if percent_change > 15:
            trajectory = "Escalating Rapidly"
            warning = "🚨 ML Warning: Your screen time is compounding. If this trend continues, your footprint will spike next month."
        elif percent_change > 5:
            trajectory = "Creeping Upward"
            warning = "⚠️ ML Notice: Your digital emissions are slowly rising. Keep an eye on your streaming habits."
        elif percent_change < -5:
            trajectory = "Improving"
            warning = "✅ ML Praise: Great job! The model detects a strong downward trend in your digital footprint."
        else:
            trajectory = "Stable"
            warning = "ℹ️ ML Status: Your digital footprint is stable and predictable."

        # Format output
        forecast_dates = [self.df['date'].max() + pd.Timedelta(days=i) for i in range(1, days_ahead + 1)]
        
        forecast_data = [
            {"date": date.strftime("%Y-%m-%d"), "predicted_kg_co2": round(float(pred), 3)}
            for date, pred in zip(forecast_dates, predictions)
        ]

        return {
            "success": True,
            "current_7d_average": round(float(current_avg), 3),
            "predicted_end_average": round(float(future_avg), 3),
            "trend_percent": round(float(percent_change), 1),
            "trajectory": trajectory,
            "ai_warning": warning,
            "forecast_series": forecast_data
        }

    def detect_anomalies(self, threshold_z_score: float = 2.0) -> List[Dict[str, Any]]:
        """
        Scans historical data for massive spikes (e.g. binge-watching weekends).
        Returns a list of anomalous dates.
        """
        if self.df.empty or len(self.df) < 5:
            return []
            
        mean_co2 = self.df['daily_kg_co2'].mean()
        std_co2 = self.df['daily_kg_co2'].std()
        
        if std_co2 == 0:
            return []
            
        self.df['z_score'] = (self.df['daily_kg_co2'] - mean_co2) / std_co2
        
        # Filter where z-score exceeds threshold
        anomalies = self.df[self.df['z_score'] > threshold_z_score]
        
        results = []
        for _, row in anomalies.iterrows():
            results.append({
                "date": row['date'].strftime("%Y-%m-%d"),
                "kg_co2": round(row['daily_kg_co2'], 2),
                "severity": "High" if row['z_score'] > 3.0 else "Medium",
                "message": f"Unusual spike detected on {row['date'].strftime('%b %d')}. You generated {round(row['daily_kg_co2'], 1)} kg CO2e, which is way above your {round(mean_co2, 1)} kg average."
            })
            
        return results
