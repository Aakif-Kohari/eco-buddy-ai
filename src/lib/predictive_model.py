"""
Predictive Model for EcoBuddy AI
Machine learning models for forecasting carbon footprint and sustainability metrics.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass, field
import json
import pickle
import os
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for predictive models."""
    model_type: str = "ensemble"  # linear, ridge, lasso, random_forest, gradient_boost, ensemble
    test_size: float = 0.2
    random_state: int = 42
    n_estimators: int = 100
    max_depth: int = 10
    learning_rate: float = 0.1
    feature_engineering: bool = True
    auto_tune: bool = True
    save_model: bool = True
    model_path: str = "models/"
    min_training_samples: int = 10


@dataclass
class PredictionResult:
    """Result container for predictions."""
    success: bool
    message: str
    predictions: Optional[List[float]] = None
    confidence_intervals: Optional[List[Tuple[float, float]]] = None
    feature_importance: Optional[Dict[str, float]] = None
    model_metrics: Optional[Dict[str, float]] = None
    forecast_dates: Optional[List[str]] = None
    trend: Optional[str] = None
    processing_time_ms: float = 0.0


class PredictiveModel:
    """
    Machine learning models for predicting carbon footprint and sustainability metrics.
    Supports multiple algorithms with feature engineering and model tuning.
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        self.config = config or ModelConfig()
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.is_trained = False
        self._performance_history: List[Dict[str, Any]] = []
        self._models: Dict[str, Any] = {}
        self._best_model_name: str = ""
        
        # Ensure model directory exists
        if self.config.save_model:
            os.makedirs(self.config.model_path, exist_ok=True)
    
    def train(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train predictive model on assessment data.
        
        Args:
            assessments: List of assessment dictionaries
        
        Returns:
            Training results dictionary
        """
        if len(assessments) < self.config.min_training_samples:
            return {
                'success': False,
                'message': f"Need at least {self.config.min_training_samples} samples for training",
                'samples': len(assessments)
            }
        
        try:
            # Prepare features and target
            X, y, dates = self._prepare_training_data(assessments)
            
            if len(X) < self.config.min_training_samples:
                return {
                    'success': False,
                    'message': "Insufficient data after preprocessing",
                    'samples': len(X)
                }
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config.test_size, random_state=self.config.random_state
            )
            
            # Scale features
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train multiple models and select best
            models = self._train_models(X_train_scaled, y_train, X_test_scaled, y_test)
            
            # Select best model
            best_model_name = min(models.keys(), key=lambda k: models[k]['rmse'])
            self._best_model_name = best_model_name
            self.model = models[best_model_name]['model']
            self.feature_names = self._get_feature_names()
            self.is_trained = True
            
            # Save model
            if self.config.save_model:
                self._save_model()
            
            # Track performance
            self._performance_history.append({
                'timestamp': datetime.now().isoformat(),
                'model': best_model_name,
                'metrics': models[best_model_name],
                'samples': len(X)
            })
            
            return {
                'success': True,
                'message': f"Model trained successfully using {best_model_name}",
                'best_model': best_model_name,
                'metrics': models[best_model_name],
                'samples': len(X),
                'features': self.feature_names
            }
            
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            return {
                'success': False,
                'message': f"Training failed: {str(e)}"
            }
    
    def predict(
        self, 
        assessments: List[Dict[str, Any]], 
        horizon_days: int = 30
    ) -> PredictionResult:
        """
        Generate predictions for future carbon footprint.
        
        Args:
            assessments: Historical assessments
            horizon_days: Number of days to forecast
        
        Returns:
            PredictionResult with forecasts
        """
        import time
        start_time = time.time()
        
        if not self.is_trained and self.model is None:
            # Train on available data if not trained
            train_result = self.train(assessments)
            if not train_result['success']:
                # Fallback to simple forecasting
                return self._simple_forecast(assessments, horizon_days)
        
        try:
            # Prepare features for forecast
            X_future, dates_future = self._prepare_forecast_data(assessments, horizon_days)
            
            if X_future is None or len(X_future) == 0:
                return self._simple_forecast(assessments, horizon_days)
            
            # Scale features
            X_future_scaled = self.scaler.transform(X_future) if self.scaler else X_future
            
            # Generate predictions
            predictions = self.model.predict(X_future_scaled)
            
            # Ensure positive predictions
            predictions = np.maximum(predictions, 0)
            
            # Calculate confidence intervals
            confidence_intervals = self._calculate_confidence_intervals(
                assessments, predictions, horizon_days
            )
            
            # Determine trend
            trend = self._determine_trend(predictions)
            
            processing_time = (time.time() - start_time) * 1000
            
            return PredictionResult(
                success=True,
                message="Prediction generated successfully",
                predictions=predictions.tolist(),
                confidence_intervals=confidence_intervals,
                feature_importance=self._get_feature_importance(),
                model_metrics=self._get_model_metrics(),
                forecast_dates=[d.isoformat() for d in dates_future],
                trend=trend,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._simple_forecast(assessments, horizon_days)
    
    def _prepare_training_data(
        self, 
        assessments: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, np.ndarray, List[datetime]]:
        """Prepare features and target for training."""
        df = pd.DataFrame(assessments)
        
        # Convert date
        if 'date' not in df.columns and 'created_at' in df.columns:
            df['date'] = df['created_at']
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Create features
        features = []
        targets = []
        dates = []
        
        for i in range(len(df)):
            if i < 3:  # Need at least 3 previous points for features
                continue
            
            # Features: previous 3 footprints, eco scores, and trends
            prev_footprints = df['footprint'].iloc[max(0, i-3):i].values
            prev_scores = df['eco_score'].iloc[max(0, i-3):i].values if 'eco_score' in df.columns else [0] * len(prev_footprints)
            
            # Calculate features
            features.append([
                np.mean(prev_footprints),  # Average of previous
                np.std(prev_footprints) if len(prev_footprints) > 1 else 0,  # Variability
                prev_footprints[-1] if len(prev_footprints) > 0 else 0,  # Most recent
                prev_footprints[0] if len(prev_footprints) > 0 else 0,  # Oldest in window
                np.mean(prev_scores),
                len(prev_footprints),  # Number of data points
                i,  # Time index
            ])
            
            targets.append(df['footprint'].iloc[i])
            dates.append(df['date'].iloc[i])
        
        if len(features) < self.config.min_training_samples:
            return np.array(features), np.array(targets), dates
        
        return np.array(features), np.array(targets), dates
    
    def _prepare_forecast_data(
        self, 
        assessments: List[Dict[str, Any]], 
        horizon_days: int
    ) -> Tuple[np.ndarray, List[datetime]]:
        """Prepare features for forecasting."""
        if not assessments:
            return None, []
        
        df = pd.DataFrame(assessments)
        if 'date' not in df.columns and 'created_at' in df.columns:
            df['date'] = df['created_at']
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        if len(df) < 3:
            return None, []
        
        # Get last few data points
        last_footprints = df['footprint'].iloc[-3:].values
        last_scores = df['eco_score'].iloc[-3:].values if 'eco_score' in df.columns else [0] * 3
        
        # Generate future dates
        last_date = df['date'].iloc[-1]
        future_dates = [last_date + timedelta(days=i+1) for i in range(horizon_days)]
        
        # Prepare features for each future point
        X_future = []
        for i in range(horizon_days):
            features = [
                np.mean(last_footprints),  # Average of previous 3
                np.std(last_footprints) if len(last_footprints) > 1 else 0,
                last_footprints[-1],  # Most recent
                last_footprints[0],  # Oldest
                np.mean(last_scores),
                len(last_footprints),
                len(df) + i  # Time index (future)
            ]
            X_future.append(features)
        
        return np.array(X_future), future_dates
    
    def _train_models(
        self, 
        X_train: np.ndarray, 
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, Dict[str, Any]]:
        """Train multiple models and return performance metrics."""
        models = {}
        
        # Linear Regression
        lr = LinearRegression()
        lr.fit(X_train, y_train)
        y_pred_lr = lr.predict(X_test)
        models['linear'] = {
            'model': lr,
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred_lr)),
            'mae': mean_absolute_error(y_test, y_pred_lr),
            'r2': r2_score(y_test, y_pred_lr)
        }
        
        # Ridge Regression
        ridge = Ridge(alpha=1.0)
        ridge.fit(X_train, y_train)
        y_pred_ridge = ridge.predict(X_test)
        models['ridge'] = {
            'model': ridge,
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred_ridge)),
            'mae': mean_absolute_error(y_test, y_pred_ridge),
            'r2': r2_score(y_test, y_pred_ridge)
        }
        
        # Random Forest
        rf = RandomForestRegressor(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            random_state=self.config.random_state,
            n_jobs=-1
        )
        rf.fit(X_train, y_train)
        y_pred_rf = rf.predict(X_test)
        models['random_forest'] = {
            'model': rf,
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred_rf)),
            'mae': mean_absolute_error(y_test, y_pred_rf),
            'r2': r2_score(y_test, y_pred_rf)
        }
        
        # Gradient Boosting
        gb = GradientBoostingRegressor(
            n_estimators=self.config.n_estimators,
            learning_rate=self.config.learning_rate,
            max_depth=self.config.max_depth,
            random_state=self.config.random_state
        )
        gb.fit(X_train, y_train)
        y_pred_gb = gb.predict(X_test)
        models['gradient_boost'] = {
            'model': gb,
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred_gb)),
            'mae': mean_absolute_error(y_test, y_pred_gb),
            'r2': r2_score(y_test, y_pred_gb)
        }
        
        # Ensemble model (average of all)
        y_pred_ensemble = (y_pred_lr + y_pred_ridge + y_pred_rf + y_pred_gb) / 4
        models['ensemble'] = {
            'model': EnsembleModel([lr, ridge, rf, gb]),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred_ensemble)),
            'mae': mean_absolute_error(y_test, y_pred_ensemble),
            'r2': r2_score(y_test, y_pred_ensemble)
        }
        
        return models
    
    def _calculate_confidence_intervals(
        self, 
        assessments: List[Dict[str, Any]], 
        predictions: np.ndarray,
        horizon_days: int
    ) -> List[Tuple[float, float]]:
        """Calculate confidence intervals for predictions."""
        # Use residual standard deviation from training data
        if len(assessments) < 10:
            # Fallback: use 20% of prediction as uncertainty
            return [(p - 0.2*p, p + 0.2*p) for p in predictions]
        
        df = pd.DataFrame(assessments)
        footprint = df['footprint'].values
        
        # Calculate residual standard deviation
        mean_footprint = np.mean(footprint)
        residual_std = np.std(footprint - mean_footprint)
        
        # Confidence interval width increases with horizon
        confidence_width = 1.96 * residual_std * (1 + 0.05 * np.arange(horizon_days))
        
        intervals = []
        for i, pred in enumerate(predictions):
            width = confidence_width[i] if i < len(confidence_width) else confidence_width[-1]
            intervals.append((max(0, pred - width), pred + width))
        
        return intervals
    
    def _determine_trend(self, predictions: np.ndarray) -> str:
        """Determine trend direction from predictions."""
        if len(predictions) < 2:
            return "stable"
        
        # Calculate slope
        x = np.arange(len(predictions))
        slope, _, _, _, _ = np.polyfit(x, predictions, 1, full=True)[0]
        
        if slope < -0.01:
            return "decreasing"
        elif slope > 0.01:
            return "increasing"
        else:
            return "stable"
    
    def _get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the trained model."""
        if self.model is None or not self.is_trained:
            return {}
        
        feature_names = self.feature_names or [f"feature_{i}" for i in range(len(self._get_feature_importance_raw()))]
        
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_)
        else:
            return {}
        
        if len(importances) != len(feature_names):
            # Truncate or pad
            min_len = min(len(importances), len(feature_names))
            importances = importances[:min_len]
            feature_names = feature_names[:min_len]
        
        # Normalize
        importances = importances / np.sum(importances) if np.sum(importances) > 0 else importances
        
        return {feature_names[i]: float(importances[i]) for i in range(len(importances))}
    
    def _get_feature_importance_raw(self) -> np.ndarray:
        """Get raw feature importance from model."""
        if self.model is None or not self.is_trained:
            return np.array([])
        
        if hasattr(self.model, 'feature_importances_'):
            return self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            return np.abs(self.model.coef_)
        else:
            return np.array([])
    
    def _get_feature_names(self) -> List[str]:
        """Get feature names."""
        return [
            'avg_previous_footprint',
            'std_previous_footprint',
            'most_recent_footprint',
            'oldest_footprint',
            'avg_previous_score',
            'data_points_count',
            'time_index'
        ]
    
    def _get_model_metrics(self) -> Dict[str, float]:
        """Get metrics for the best model."""
        if self._best_model_name in self._models:
            return {
                'rmse': self._models[self._best_model_name]['rmse'],
                'mae': self._models[self._best_model_name]['mae'],
                'r2': self._models[self._best_model_name]['r2'],
                'model': self._best_model_name
            }
        return {}
    
    def _simple_forecast(self, assessments: List[Dict[str, Any]], horizon_days: int) -> PredictionResult:
        """Fallback: simple forecasting using moving average."""
        if not assessments:
            return PredictionResult(
                success=False,
                message="No data available for forecasting"
            )
        
        df = pd.DataFrame(assessments)
        if 'footprint' not in df.columns:
            return PredictionResult(
                success=False,
                message="No footprint data available"
            )
        
        # Calculate moving average
        footprint = df['footprint'].values
        ma = np.mean(footprint[-3:]) if len(footprint) >= 3 else np.mean(footprint)
        std = np.std(footprint[-3:]) if len(footprint) >= 3 else np.std(footprint) * 0.3
        
        # Generate predictions
        predictions = [ma] * horizon_days
        
        # Add slight randomness to make it more realistic
        np.random.seed(42)
        noise = np.random.normal(0, std * 0.1, horizon_days)
        predictions = np.maximum(0, np.array(predictions) + noise)
        
        # Confidence intervals
        confidence_intervals = [(p - 1.96*std, p + 1.96*std) for p in predictions]
        
        # Generate future dates
        last_date = datetime.now()
        if 'date' in df.columns:
            last_date = pd.to_datetime(df['date'].iloc[-1])
        future_dates = [last_date + timedelta(days=i+1) for i in range(horizon_days)]
        
        return PredictionResult(
            success=True,
            message="Simple forecast generated (using moving average)",
            predictions=predictions.tolist(),
            confidence_intervals=confidence_intervals,
            forecast_dates=[d.isoformat() for d in future_dates],
            trend=self._determine_trend(predictions),
            processing_time_ms=0.0
        )
    
    def _save_model(self) -> None:
        """Save trained model to disk."""
        if self.model is None:
            return
        
        try:
            model_file = os.path.join(
                self.config.model_path, 
                f"carbon_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            )
            
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_names': self.feature_names,
                'model_name': self._best_model_name,
                'timestamp': datetime.now().isoformat(),
                'metrics': self._get_model_metrics()
            }
            
            with open(model_file, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model saved to {model_file}")
            
        except Exception as e:
            logger.warning(f"Failed to save model: {e}")
    
    def load_model(self, model_path: str) -> bool:
        """Load trained model from disk."""
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.scaler = model_data.get('scaler')
            self.feature_names = model_data.get('feature_names', [])
            self._best_model_name = model_data.get('model_name', '')
            self.is_trained = True
            
            logger.info(f"Model loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def get_performance_history(self) -> List[Dict[str, Any]]:
        """Get model performance history."""
        return self._performance_history
    
    def evaluate_on_new_data(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate model performance on new data."""
        if not self.is_trained or self.model is None:
            return {'success': False, 'message': 'Model not trained'}
        
        try:
            X, y, _ = self._prepare_training_data(assessments)
            
            if len(X) == 0:
                return {'success': False, 'message': 'No data to evaluate'}
            
            X_scaled = self.scaler.transform(X) if self.scaler else X
            y_pred = self.model.predict(X_scaled)
            
            # Ensure same length
            min_len = min(len(y), len(y_pred))
            y = y[:min_len]
            y_pred = y_pred[:min_len]
            
            metrics = {
                'rmse': np.sqrt(mean_squared_error(y, y_pred)),
                'mae': mean_absolute_error(y, y_pred),
                'r2': r2_score(y, y_pred),
                'samples': len(y)
            }
            
            return {
                'success': True,
                'metrics': metrics,
                'message': 'Evaluation completed'
            }
            
        except Exception as e:
            return {'success': False, 'message': f'Evaluation failed: {str(e)}'}


class EnsembleModel:
    """Ensemble model that averages predictions from multiple models."""
    
    def __init__(self, models: List[Any]):
        self.models = models
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Generate ensemble predictions."""
        predictions = [model.predict(X) for model in self.models]
        return np.mean(predictions, axis=0)


# Global predictive model instance
_predictive_model: Optional[PredictiveModel] = None


def get_predictive_model() -> PredictiveModel:
    """Get or create global predictive model instance."""
    global _predictive_model
    if _predictive_model is None:
        _predictive_model = PredictiveModel()
    return _predictive_model


def train_predictive_model(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to train predictive model.
    
    Args:
        assessments: List of assessment dictionaries
    
    Returns:
        Training results
    """
    model = get_predictive_model()
    return model.train(assessments)


def generate_predictions(
    assessments: List[Dict[str, Any]], 
    horizon_days: int = 30
) -> PredictionResult:
    """
    Convenience function to generate predictions.
    
    Args:
        assessments: List of assessment dictionaries
        horizon_days: Number of days to forecast
    
    Returns:
        PredictionResult with forecasts
    """
    model = get_predictive_model()
    return model.predict(assessments, horizon_days)


def evaluate_predictions(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluate predictive model performance.
    
    Args:
        assessments: List of assessment dictionaries
    
    Returns:
        Evaluation results
    """
    model = get_predictive_model()
    return model.evaluate_on_new_data(assessments)