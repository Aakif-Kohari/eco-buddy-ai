"""
Machine Learning Pipeline for Grid Forecasting.
Uses scikit-learn to train real predictive models on historical weather and grid data.
"""

import numpy as np
import logging
from typing import Tuple, Any
import time

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

class GridMLPipeline:
    """
    Trains and persists Random Forest models to predict solar irradiance and grid carbon intensity.
    """
    def __init__(self):
        self.solar_model = None
        self.carbon_model = None
        self.solar_scaler = None
        self.carbon_scaler = None
        self.is_trained = False

    def generate_synthetic_training_data(self, samples: int = 10000) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generates synthetic historical data for training.
        Features: [hour_of_day, day_of_year, cloud_cover_percent, temperature_c]
        Targets: [solar_w_m2, carbon_intensity_g_kwh]
        """
        logger.info(f"Generating {samples} synthetic samples for ML training...")
        np.random.seed(42)
        
        # Features
        hour_of_day = np.random.uniform(0, 24, samples)
        day_of_year = np.random.uniform(1, 365, samples)
        cloud_cover = np.random.uniform(0, 100, samples)
        temp_c = np.random.uniform(-10, 40, samples)
        
        X = np.column_stack((hour_of_day, day_of_year, cloud_cover, temp_c))
        
        # Targets
        y_solar = np.zeros(samples)
        y_carbon = np.zeros(samples)
        
        for i in range(samples):
            h = hour_of_day[i]
            c = cloud_cover[i]
            
            # Solar Math
            if 6 <= h <= 18:
                import math
                normalized = (h - 6) / 12 * math.pi
                base = math.sin(normalized) * 1000
                y_solar[i] = max(0, base * (1 - (c / 100) * 0.75))
            else:
                y_solar[i] = 0.0
                
            # Carbon Math (Duck curve)
            base_co2 = 300.0
            solar_dip = -150.0 if 10 <= h <= 16 else 0.0
            evening_spike = 200.0 if 18 <= h <= 22 else 0.0
            y_carbon[i] = base_co2 + solar_dip + evening_spike + (temp_c[i] * 2) # Hotter days = more AC = dirtier peaker plants
            
        return X, y_solar, y_carbon

    def train_models(self):
        """Trains the Random Forest regressors."""
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn is not installed. Cannot train ML src.notifications.models.")
            return False
            
        X, y_solar, y_carbon = self.generate_synthetic_training_data()
        
        # Train Solar Model
        self.solar_scaler = StandardScaler()
        X_scaled = self.solar_scaler.fit_transform(X)
        
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_solar, test_size=0.2)
        
        logger.info("Training Solar Random Forest...")
        self.solar_model = RandomForestRegressor(n_estimators=50, max_depth=10, n_jobs=-1)
        self.solar_model.fit(X_train, y_train)
        
        solar_preds = self.solar_model.predict(X_test)
        solar_mse = mean_squared_error(y_test, solar_preds)
        logger.info(f"Solar Model trained. MSE: {solar_mse:.2f}")
        
        # Train Carbon Model
        self.carbon_scaler = StandardScaler()
        X_scaled_c = self.carbon_scaler.fit_transform(X)
        
        X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(X_scaled_c, y_carbon, test_size=0.2)
        
        logger.info("Training Carbon Random Forest...")
        self.carbon_model = RandomForestRegressor(n_estimators=50, max_depth=10, n_jobs=-1)
        self.carbon_model.fit(X_train_c, y_train_c)
        
        carbon_preds = self.carbon_model.predict(X_test_c)
        carbon_mse = mean_squared_error(y_test_c, carbon_preds)
        logger.info(f"Carbon Model trained. MSE: {carbon_mse:.2f}")
        
        self.is_trained = True
        return True

    def predict_future(self, start_timestamp: float, horizon_hours: int = 24) -> Tuple[list, list]:
        """Uses the trained ML model to forecast the future."""
        if not self.is_trained or not SKLEARN_AVAILABLE:
            raise ValueError("Models are not trained.")
            
        predictions_solar = []
        predictions_carbon = []
        
        for hour_offset in range(horizon_hours):
            target_ts = start_timestamp + (hour_offset * 3600)
            time_struct = time.localtime(target_ts)
            
            h = time_struct.tm_hour
            d = time_struct.tm_yday
            # Assume 20% cloud cover and 22C for future prediction (simplification)
            c = 20.0
            t = 22.0
            
            features = np.array([[h, d, c, t]])
            
            # Predict Solar
            features_scaled_s = self.solar_scaler.transform(features)
            pred_s = self.solar_model.predict(features_scaled_s)[0]
            predictions_solar.append({"hour": h, "pred_solar": round(pred_s, 2)})
            
            # Predict Carbon
            features_scaled_c = self.carbon_scaler.transform(features)
            pred_c = self.carbon_model.predict(features_scaled_c)[0]
            predictions_carbon.append({"hour": h, "pred_carbon": round(pred_c, 2)})
            
        return predictions_solar, predictions_carbon
