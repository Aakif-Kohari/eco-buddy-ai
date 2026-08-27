"""
Environmental Anomaly Detection and Early Warning Framework
============================================================

A comprehensive framework for detecting environmental anomalies and providing
early warnings using statistical methods, machine learning, and time series analysis.

Author: AI Assistant
Version: 1.0.0
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import warnings
import json
import logging
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
from scipy.stats import zscore, median_abs_deviation
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.svm import OneClassSVM
from sklearn.neighbors import LocalOutlierFactor
from sklearn.decomposition import PCA
from sklearn.covariance import EllipticEnvelope
import joblib
import os
from collections import deque
import threading
import time
import pickle
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AnomalySeverity(Enum):
    """Anomaly severity levels."""
    NORMAL = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AnomalyType(Enum):
    """Types of environmental anomalies."""
    TEMPERATURE_SPIKE = "temperature_spike"
    TEMPERATURE_DROP = "temperature_drop"
    PRESSURE_ANOMALY = "pressure_anomaly"
    HUMIDITY_ANOMALY = "humidity_anomaly"
    AIR_QUALITY_DEGRADATION = "air_quality_degradation"
    WIND_SPEED_ANOMALY = "wind_speed_anomaly"
    PRECIPITATION_ANOMALY = "precipitation_anomaly"
    MULTIVARIATE_ANOMALY = "multivariate_anomaly"
    SEASONAL_ANOMALY = "seasonal_anomaly"
    TREND_SHIFT = "trend_shift"


@dataclass
class AnomalyReport:
    """Data structure for anomaly reports."""
    timestamp: datetime
    parameter: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    value: float
    expected_value: float
    threshold: float
    confidence_score: float
    description: str
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EarlyWarning:
    """Data structure for early warnings."""
    timestamp: datetime
    parameter: str
    predicted_anomaly_type: AnomalyType
    predicted_severity: AnomalySeverity
    prediction_time_horizon: int  # hours ahead
    current_trend: str
    risk_score: float
    confidence: float
    mitigation_strategies: List[str]
    affected_areas: List[str]


class DataPreprocessor:
    """
    Data preprocessing class for environmental data.
    Handles missing values, outliers, normalization, and feature engineering.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.scalers = {}
        self.rolling_windows = self.config.get('rolling_windows', [1, 3, 6, 12, 24])
        self.outlier_method = self.config.get('outlier_method', 'iqr')
        self.normalization_method = self.config.get('normalization_method', 'standard')
        
    def handle_missing_values(self, df: pd.DataFrame, method: str = 'interpolate') -> pd.DataFrame:
        """
        Handle missing values in the dataset.
        
        Args:
            df: Input dataframe
            method: Method to handle missing values ('interpolate', 'ffill', 'bfill', 'drop')
            
        Returns:
            DataFrame with handled missing values
        """
        df_clean = df.copy()
        
        if method == 'interpolate':
            df_clean = df_clean.interpolate(method='time', limit_area='inside')
            df_clean = df_clean.bfill().ffill()
        elif method == 'ffill':
            df_clean = df_clean.ffill()
        elif method == 'bfill':
            df_clean = df_clean.bfill()
        elif method == 'drop':
            df_clean = df_clean.dropna()
        else:
            raise ValueError(f"Unknown method: {method}")
            
        logger.info(f"Handled missing values using {method} method")
        return df_clean
    
    def remove_outliers(self, df: pd.DataFrame, method: str = None) -> pd.DataFrame:
        """
        Remove outliers from the dataset.
        
        Args:
            df: Input dataframe
            method: Outlier removal method ('iqr', 'zscore', 'mad')
            
        Returns:
            DataFrame with outliers removed
        """
        method = method or self.outlier_method
        df_clean = df.copy()
        
        for column in df_clean.select_dtypes(include=[np.number]).columns:
            if method == 'iqr':
                Q1 = df_clean[column].quantile(0.25)
                Q3 = df_clean[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                df_clean[column] = df_clean[column].clip(lower_bound, upper_bound)
                
            elif method == 'zscore':
                z_scores = np.abs(zscore(df_clean[column].values))
                threshold = self.config.get('zscore_threshold', 3)
                df_clean[column] = df_clean[column].mask(z_scores > threshold, df_clean[column].mean())
                
            elif method == 'mad':
                median = df_clean[column].median()
                mad = median_abs_deviation(df_clean[column].values)
                threshold = self.config.get('mad_threshold', 3)
                df_clean[column] = df_clean[column].mask(
                    np.abs(df_clean[column] - median) > threshold * mad,
                    median
                )
                
        logger.info(f"Removed outliers using {method} method")
        return df_clean
    
    def normalize_data(self, df: pd.DataFrame, method: str = None) -> pd.DataFrame:
        """
        Normalize the data.
        
        Args:
            df: Input dataframe
            method: Normalization method ('standard', 'minmax', 'robust')
            
        Returns:
            Normalized dataframe
        """
        method = method or self.normalization_method
        df_norm = df.copy()
        numeric_cols = df_norm.select_dtypes(include=[np.number]).columns
        
        if method == 'standard':
            for col in numeric_cols:
                scaler = StandardScaler()
                df_norm[col] = scaler.fit_transform(df_norm[[col]].values)
                self.scalers[f'{col}_scaler'] = scaler
                
        elif method == 'minmax':
            for col in numeric_cols:
                min_val = df_norm[col].min()
                max_val = df_norm[col].max()
                df_norm[col] = (df_norm[col] - min_val) / (max_val - min_val)
                
        elif method == 'robust':
            for col in numeric_cols:
                median = df_norm[col].median()
                q1 = df_norm[col].quantile(0.25)
                q3 = df_norm[col].quantile(0.75)
                iqr = q3 - q1
                df_norm[col] = (df_norm[col] - median) / iqr if iqr != 0 else df_norm[col]
                
        logger.info(f"Normalized data using {method} method")
        return df_norm
    
    def create_features(self, df: pd.DataFrame, target_col: str = None) -> pd.DataFrame:
        """
        Create additional features from the data.
        
        Args:
            df: Input dataframe
            target_col: Target column for lag features
            
        Returns:
            DataFrame with additional features
        """
        df_features = df.copy()
        
        # Add rolling statistics
        for window in self.rolling_windows:
            for col in df_features.select_dtypes(include=[np.number]).columns:
                df_features[f'{col}_rolling_mean_{window}'] = df_features[col].rolling(window=window).mean()
                df_features[f'{col}_rolling_std_{window}'] = df_features[col].rolling(window=window).std()
                df_features[f'{col}_rolling_min_{window}'] = df_features[col].rolling(window=window).min()
                df_features[f'{col}_rolling_max_{window}'] = df_features[col].rolling(window=window).max()
        
        # Add lag features
        if target_col:
            for lag in [1, 3, 6, 12, 24]:
                df_features[f'{target_col}_lag_{lag}'] = df_features[target_col].shift(lag)
        
        # Add rate of change features
        for col in df_features.select_dtypes(include=[np.number]).columns:
            df_features[f'{col}_diff_1'] = df_features[col].diff()
            df_features[f'{col}_diff_3'] = df_features[col].diff(3)
            df_features[f'{col}_pct_change'] = df_features[col].pct_change()
        
        # Add time-based features
        if 'timestamp' in df_features.columns:
            df_features['hour'] = df_features['timestamp'].dt.hour
            df_features['day_of_week'] = df_features['timestamp'].dt.dayofweek
            df_features['month'] = df_features['timestamp'].dt.month
            df_features['quarter'] = df_features['timestamp'].dt.quarter
            df_features['is_weekend'] = df_features['timestamp'].dt.dayofweek.isin([5, 6]).astype(int)
            df_features['day_of_year'] = df_features['timestamp'].dt.dayofyear
            df_features['week_of_year'] = df_features['timestamp'].dt.isocalendar().week
        
        logger.info("Created additional features")
        return df_features


class AnomalyDetector(ABC):
    """
    Abstract base class for anomaly detection algorithms.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = None
        self.threshold = src.core.config.get('threshold', 0.95)
        
    @abstractmethod
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the anomaly detection model."""
        pass
    
    @abstractmethod
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies in the data."""
        pass
    
    @abstractmethod
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores for the data."""
        pass


class StatisticalAnomalyDetector(AnomalyDetector):
    """
    Statistical methods for anomaly detection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.method = self.config.get('method', 'zscore')
        self.window_size = self.config.get('window_size', 30)
        self.upper_threshold = self.config.get('upper_threshold', 3.0)
        self.lower_threshold = self.config.get('lower_threshold', 3.0)
        self.seasonal_period = self.config.get('seasonal_period', 24)
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit statistical model parameters."""
        self.data_stats = {}
        
        for col in data.select_dtypes(include=[np.number]).columns:
            self.data_stats[col] = {
                'mean': data[col].mean(),
                'std': data[col].std(),
                'median': data[col].median(),
                'mad': median_abs_deviation(data[col].values),
                'q1': data[col].quantile(0.25),
                'q3': data[col].quantile(0.75),
                'min': data[col].min(),
                'max': data[col].max(),
                'seasonal_pattern': self._compute_seasonal_pattern(data, col)
            }
            
        logger.info("Statistical model fitted successfully")
    
    def _compute_seasonal_pattern(self, data: pd.DataFrame, col: str) -> np.ndarray:
        """Compute seasonal pattern for a column."""
        if len(data) < self.seasonal_period * 2:
            return np.array([])
            
        # Compute average pattern for each period
        n_periods = len(data) // self.seasonal_period
        if n_periods < 1:
            return np.array([])
            
        pattern = np.zeros(self.seasonal_period)
        for i in range(self.seasonal_period):
            values = data[col].iloc[i::self.seasonal_period]
            if len(values) > 0:
                pattern[i] = values.mean()
                
        return pattern
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using statistical methods."""
        reports = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats_info = self.data_stats.get(col, {})
            
            for idx, value in enumerate(values):
                if idx < len(data):
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    
                    if self.method == 'zscore':
                        zscore_value = (value - stats_info.get('mean', 0)) / (stats_info.get('std', 1) + 1e-10)
                        if abs(zscore_value) > self.upper_threshold:
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, zscore_value, 
                                'zscore_anomaly', AnomalySeverity.MEDIUM
                            ))
                    elif self.method == 'mad':
                        mad_score = (value - stats_info.get('median', 0)) / (stats_info.get('mad', 1) + 1e-10)
                        if abs(mad_score) > self.upper_threshold:
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, mad_score,
                                'mad_anomaly', AnomalySeverity.MEDIUM
                            ))
                    elif self.method == 'iqr':
                        q1 = stats_info.get('q1', 0)
                        q3 = stats_info.get('q3', 0)
                        iqr = q3 - q1
                        lower_bound = q1 - 1.5 * iqr
                        upper_bound = q3 + 1.5 * iqr
                        
                        if value < lower_bound or value > upper_bound:
                            severity = AnomalySeverity.HIGH if abs(value - stats_info.get('median', 0)) > 3 * iqr else AnomalySeverity.MEDIUM
                            reports.append(self._create_anomaly_report(
                                timestamp, col, value, (value - stats_info.get('median', 0)) / (iqr + 1e-10),
                                'iqr_anomaly', severity
                            ))
                            
        return reports
    
    def _create_anomaly_report(self, timestamp, col, value, score, anomaly_type, severity):
        """Create an anomaly src.reporting.report."""
        return AnomalyReport(
            timestamp=timestamp or datetime.now(),
            parameter=col,
            anomaly_type=AnomalyType.TEMPERATURE_SPIKE,  # Placeholder
            severity=severity,
            value=float(value),
            expected_value=float(self.data_stats.get(col, {}).get('mean', value)),
            threshold=float(self.upper_threshold),
            confidence_score=min(1.0, abs(score) / self.upper_threshold),
            description=f"Statistical anomaly detected in {col} with score {score:.2f}",
            recommendations=["Investigate data source", "Check sensor calibration"],
            metadata={'score': score, 'method': self.method}
        )
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores for the data."""
        scores = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats_info = self.data_stats.get(col, {})
            
            if self.method == 'zscore':
                col_scores = (values - stats_info.get('mean', 0)) / (stats_info.get('std', 1) + 1e-10)
            elif self.method == 'mad':
                col_scores = (values - stats_info.get('median', 0)) / (stats_info.get('mad', 1) + 1e-10)
            else:
                col_scores = np.zeros_like(values)
                
            scores.append(np.abs(col_scores))
            
        return np.column_stack(scores) if scores else np.array([])


class MachineLearningAnomalyDetector(AnomalyDetector):
    """
    Machine learning-based anomaly detection.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.algorithm = self.config.get('algorithm', 'isolation_forest')
        self.contamination = self.config.get('contamination', 0.1)
        self.n_estimators = self.config.get('n_estimators', 100)
        self.feature_columns = self.config.get('feature_columns', [])
        self.scaler = StandardScaler()
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the machine learning model."""
        features = self._prepare_features(data)
        
        if self.algorithm == 'isolation_forest':
            self.model = IsolationForest(
                contamination=self.contamination,
                n_estimators=self.n_estimators,
                random_state=42
            )
        elif self.algorithm == 'one_class_svm':
            self.model = OneClassSVM(
                nu=self.contamination,
                kernel='rbf',
                gamma='auto'
            )
        elif self.algorithm == 'local_outlier_factor':
            self.model = LocalOutlierFactor(
                contamination=self.contamination,
                novelty=True
            )
        elif self.algorithm == 'elliptic_envelope':
            self.model = EllipticEnvelope(
                contamination=self.contamination,
                random_state=42
            )
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
            
        self.model.fit(features)
        logger.info(f"ML model {self.algorithm} fitted successfully")
    
    def _prepare_features(self, data: pd.DataFrame) -> np.ndarray:
        """Prepare features for the model."""
        if self.feature_columns:
            features = data[self.feature_columns].values
        else:
            features = data.select_dtypes(include=[np.number]).values
            
        # Handle missing values
        features = np.nan_to_num(features, nan=0.0)
        
        # Scale features
        features = self.scaler.fit_transform(features)
        
        return features
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using ML model."""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features = self._prepare_features(data)
        predictions = self.model.predict(features)
        scores = self.model.score_samples(features) if hasattr(self.model, 'score_samples') else None
        
        reports = []
        for idx, pred in enumerate(predictions):
            if pred == -1:  # Anomaly
                timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                severity = self._determine_severity(scores[idx] if scores is not None else 0)
                
                reports.append(AnomalyReport(
                    timestamp=timestamp or datetime.now(),
                    parameter="multivariate",
                    anomaly_type=AnomalyType.MULTIVARIATE_ANOMALY,
                    severity=severity,
                    value=float(scores[idx] if scores is not None else 0),
                    expected_value=0.0,
                    threshold=0.0,
                    confidence_score=1.0 if scores is None else min(1.0, abs(scores[idx])),
                    description=f"ML-based anomaly detected by {self.algorithm}",
                    recommendations=["Check all environmental parameters", "Validate sensor data"],
                    metadata={'algorithm': self.algorithm, 'prediction': int(pred)}
                ))
                
        return reports
    
    def _determine_severity(self, score: float) -> AnomalySeverity:
        """Determine severity based on anomaly score."""
        if abs(score) > 0.8:
            return AnomalySeverity.CRITICAL
        elif abs(score) > 0.6:
            return AnomalySeverity.HIGH
        elif abs(score) > 0.4:
            return AnomalySeverity.MEDIUM
        elif abs(score) > 0.2:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores."""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features = self._prepare_features(data)
        
        if hasattr(self.model, 'score_samples'):
            return -self.model.score_samples(features)
        else:
            predictions = self.model.predict(features)
            return np.where(predictions == -1, 1.0, 0.0)


class TimeSeriesAnomalyDetector(AnomalyDetector):
    """
    Time series-based anomaly detection using decomposition and forecasting.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.method = self.config.get('method', 'stl_decomposition')
        self.forecast_horizon = self.config.get('forecast_horizon', 24)
        self.confidence_interval = self.config.get('confidence_interval', 0.95)
        self.trend_window = self.config.get('trend_window', 30)
        self.seasonal_period = self.config.get('seasonal_period', 24)
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit time series src.notifications.models."""
        self.time_series_stats = {}
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            n = len(values)
            
            # Store basic statistics
            self.time_series_stats[col] = {
                'mean': np.mean(values),
                'std': np.std(values),
                'trend': self._compute_trend(values),
                'seasonal': self._compute_seasonal(values),
                'residual': self._compute_residual(values),
                'acf': self._compute_acf(values),
                'pacf': self._compute_pacf(values)
            }
            
        logger.info("Time series model fitted successfully")
    
    def _compute_trend(self, values: np.ndarray) -> np.ndarray:
        """Compute trend component using smoothing."""
        if len(values) < self.trend_window:
            return np.zeros_like(values)
        return savgol_filter(values, window_length=min(self.trend_window, len(values)-1), polyorder=3)
    
    def _compute_seasonal(self, values: np.ndarray) -> np.ndarray:
        """Compute seasonal component."""
        if len(values) < self.seasonal_period * 2:
            return np.zeros_like(values)
            
        n = len(values)
        seasonal = np.zeros(n)
        for i in range(self.seasonal_period):
            indices = range(i, n, self.seasonal_period)
            if len(indices) > 0:
                seasonal[indices] = np.mean(values[indices]) - np.mean(values)
                
        return seasonal
    
    def _compute_residual(self, values: np.ndarray) -> np.ndarray:
        """Compute residual component."""
        trend = self._compute_trend(values)
        seasonal = self._compute_seasonal(values)
        return values - trend - seasonal
    
    def _compute_acf(self, values: np.ndarray, nlags: int = 20) -> np.ndarray:
        """Compute autocorrelation function."""
        n = len(values)
        mean = np.mean(values)
        var = np.var(values)
        if var == 0:
            return np.zeros(nlags + 1)
            
        acf = np.zeros(nlags + 1)
        for lag in range(nlags + 1):
            if lag < n:
                acf[lag] = np.corrcoef(values[:-lag] if lag > 0 else values, 
                                      values[lag:] if lag > 0 else values)[0, 1]
        return acf
    
    def _compute_pacf(self, values: np.ndarray, nlags: int = 20) -> np.ndarray:
        """Compute partial autocorrelation function."""
        n = len(values)
        pacf = np.zeros(nlags + 1)
        pacf[0] = 1.0
        
        if n > 1:
            for lag in range(1, min(nlags + 1, n)):
                # Simple approximation using OLS
                y = values[lag:]
                X = np.column_stack([values[i:-(lag-i)] for i in range(lag+1)])
                if X.shape[0] > 0:
                    try:
                        coeff = np.linalg.lstsq(X, y, rcond=None)[0]
                        pacf[lag] = coeff[-1]
                    except:
                        pacf[lag] = 0
                        
        return pacf
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using time series analysis."""
        reports = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            stats = self.time_series_stats.get(col, {})
            
            if len(values) < 2:
                continue
                
            # Decompose time series
            trend = self._compute_trend(values)
            seasonal = self._compute_seasonal(values)
            residual = values - trend - seasonal
            
            # Calculate anomaly scores
            residual_std = np.std(residual)
            z_scores = np.abs(residual / (residual_std + 1e-10))
            
            # Detect anomalies
            threshold = stats.norm.ppf(self.confidence_interval)
            
            for idx, z_score in enumerate(z_scores):
                if z_score > threshold:
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    
                    severity = self._determine_severity(z_score)
                    
                    reports.append(AnomalyReport(
                        timestamp=timestamp or datetime.now(),
                        parameter=col,
                        anomaly_type=AnomalyType.SEASONAL_ANOMALY if abs(seasonal[idx]) > 0.5 * abs(values[idx]) else AnomalyType.TREND_SHIFT,
                        severity=severity,
                        value=float(values[idx]),
                        expected_value=float(trend[idx] + seasonal[idx]),
                        threshold=float(threshold * residual_std),
                        confidence_score=min(1.0, z_score / (threshold * 2)),
                        description=f"Time series anomaly detected in {col} with z-score {z_score:.2f}",
                        recommendations=["Check for sudden environmental changes", "Validate with other sensors"],
                        metadata={
                            'z_score': float(z_score),
                            'trend': float(trend[idx]),
                            'seasonal': float(seasonal[idx]),
                            'residual': float(residual[idx])
                        }
                    ))
                    
        return reports
    
    def _determine_severity(self, z_score: float) -> AnomalySeverity:
        """Determine severity based on z-score."""
        if z_score > 6.0:
            return AnomalySeverity.CRITICAL
        elif z_score > 4.0:
            return AnomalySeverity.HIGH
        elif z_score > 3.0:
            return AnomalySeverity.MEDIUM
        elif z_score > 2.0:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores based on residuals."""
        scores = []
        
        for col in data.select_dtypes(include=[np.number]).columns:
            values = data[col].values
            trend = self._compute_trend(values)
            seasonal = self._compute_seasonal(values)
            residual = values - trend - seasonal
            
            residual_std = np.std(residual) + 1e-10
            col_scores = np.abs(residual / residual_std)
            scores.append(col_scores)
            
        return np.column_stack(scores) if scores else np.array([])


class EnsembleAnomalyDetector(AnomalyDetector):
    """
    Ensemble approach combining multiple anomaly detection methods.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config or {})
        self.detectors = []
        self.weights = self.config.get('weights', [])
        self.voting_method = self.config.get('voting_method', 'weighted')
        self._initialize_detectors()
        
    def _initialize_detectors(self) -> None:
        """Initialize individual detectors."""
        detector_configs = self.config.get('detectors', [
            {'type': 'statistical', 'method': 'zscore'},
            {'type': 'statistical', 'method': 'mad'},
            {'type': 'machine_learning', 'algorithm': 'isolation_forest'},
            {'type': 'time_series', 'method': 'stl_decomposition'}
        ])
        
        for config in detector_configs:
            detector_type = src.core.config.get('type')
            if detector_type == 'statistical':
                detector = StatisticalAnomalyDetector(config)
            elif detector_type == 'machine_learning':
                detector = MachineLearningAnomalyDetector(config)
            elif detector_type == 'time_series':
                detector = TimeSeriesAnomalyDetector(config)
            else:
                continue
                
            self.detectors.append(detector)
            
        if not self.weights:
            self.weights = [1.0 / len(self.detectors)] * len(self.detectors)
            
    def fit(self, data: pd.DataFrame) -> None:
        """Fit all detectors."""
        for detector in self.detectors:
            detector.fit(data)
        logger.info("All ensemble detectors fitted successfully")
    
    def detect(self, data: pd.DataFrame) -> List[AnomalyReport]:
        """Detect anomalies using ensemble approach."""
        all_reports = []
        detector_scores = []
        
        for detector in self.detectors:
            reports = detector.detect(data)
            all_reports.extend(reports)
            
            # Get scores for voting
            scores = detector.predict_score(data)
            if scores.size > 0:
                detector_scores.append(scores.mean(axis=1))
                
        # Apply ensemble voting
        if detector_scores and self.voting_method == 'weighted':
            ensemble_scores = np.average(detector_scores, weights=self.weights, axis=0)
            
            # Create ensemble reports
            for idx, score in enumerate(ensemble_scores):
                if score > self.threshold:
                    timestamp = data.index[idx] if isinstance(data.index, pd.DatetimeIndex) else None
                    all_reports.append(AnomalyReport(
                        timestamp=timestamp or datetime.now(),
                        parameter="ensemble",
                        anomaly_type=AnomalyType.MULTIVARIATE_ANOMALY,
                        severity=self._determine_severity(score),
                        value=float(score),
                        expected_value=0.0,
                        threshold=float(self.threshold),
                        confidence_score=min(1.0, score / self.threshold),
                        description=f"Ensemble anomaly detected with score {score:.2f}",
                        recommendations=["Verify with multiple data sources", "Cross-check all parameters"],
                        metadata={'ensemble_score': float(score), 'n_detectors': len(self.detectors)}
                    ))
                    
        return all_reports
    
    def _determine_severity(self, score: float) -> AnomalySeverity:
        """Determine severity based on ensemble score."""
        if score > 0.8 * self.threshold:
            return AnomalySeverity.CRITICAL
        elif score > 0.6 * self.threshold:
            return AnomalySeverity.HIGH
        elif score > 0.4 * self.threshold:
            return AnomalySeverity.MEDIUM
        elif score > 0.2 * self.threshold:
            return AnomalySeverity.LOW
        else:
            return AnomalySeverity.NORMAL
    
    def predict_score(self, data: pd.DataFrame) -> np.ndarray:
        """Predict anomaly scores using ensemble."""
        scores = []
        
        for detector in self.detectors:
            detector_scores = detector.predict_score(data)
            if detector_scores.size > 0:
                scores.append(detector_scores)
                
        if scores:
            weighted_scores = np.average(scores, weights=self.weights, axis=0)
            return weighted_scores
        else:
            return np.array([])


class EarlyWarningSystem:
    """
    Early warning system for environmental anomalies.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.historical_data = deque(maxlen=self.config.get('history_length', 1000))
        self.warning_thresholds = self.config.get('warning_thresholds', {})
        self.trend_analysis_window = self.config.get('trend_window', 24)
        self.forecast_horizons = self.config.get('forecast_horizons', [1, 3, 6, 12, 24])
        self.detector = None
        self.monitoring_active = False
        self.monitoring_thread = None
        self.warning_history = deque(maxlen=100)
        self.alert_callbacks = []
        
    def initialize_detector(self, detector_type: str = 'ensemble', **kwargs) -> None:
        """Initialize the anomaly detector."""
        config = self.config.copy()
        src.core.config.update(kwargs)
        
        if detector_type == 'statistical':
            self.detector = StatisticalAnomalyDetector(config)
        elif detector_type == 'machine_learning':
            self.detector = MachineLearningAnomalyDetector(config)
        elif detector_type == 'time_series':
            self.detector = TimeSeriesAnomalyDetector(config)
        elif detector_type == 'ensemble':
            self.detector = EnsembleAnomalyDetector(config)
        else:
            raise ValueError(f"Unknown detector type: {detector_type}")
            
        logger.info(f"Initialized {detector_type} detector for early warning system")
    
    def fit(self, data: pd.DataFrame) -> None:
        """Fit the detector with historical data."""
        if self.detector is None:
            raise ValueError("Detector not initialized. Call initialize_detector() first.")
            
        self.detector.fit(data)
        self.historical_data.extend(data.values.tolist())
        logger.info("Early warning system fitted with historical data")
    
    def detect_anomalies(self, data: pd.DataFrame) -> Tuple[List[AnomalyReport], List[EarlyWarning]]:
        """
        Detect anomalies and generate early warnings.
        
        Returns:
            Tuple of (anomaly_reports, early_warnings)
        """
        if self.detector is None:
            raise ValueError("Detector not initialized. Call initialize_detector() first.")
            
        # Detect anomalies
        anomaly_reports = self.detector.detect(data)
        
        # Generate early warnings
        early_warnings = self._generate_early_warnings(data, anomaly_reports)
        
        # Update historical data
        self.historical_data.extend(data.values.tolist())
        self.warning_history.extend(early_warnings)
        
        # Trigger alerts
        self._trigger_alerts(anomaly_reports, early_warnings)
        
        return anomaly_reports, early_warnings
    
    def _generate_early_warnings(self, data: pd.DataFrame, anomalies: List[AnomalyReport]) -> List[EarlyWarning]:
        """Generate early warnings based
