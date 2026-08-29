"""
Analytics Engine for EcoBuddy AI
Provides advanced analytics, trend analysis, and statistical calculations for sustainability data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass, field
from collections import defaultdict
import json
import math
from scipy import stats
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class AnalyticsConfig:
    """Configuration for analytics engine."""
    min_data_points: int = 5
    confidence_interval: float = 0.95
    forecast_horizon_days: List[int] = field(default_factory=lambda: [30, 90, 180, 365])
    seasonal_period: int = 30  # Days for seasonal decomposition
    anomaly_threshold: float = 2.0  # Standard deviations
    smoothing_window: int = 7  # Days for rolling average
    enable_machine_learning: bool = True
    max_forecast_points: int = 365


@dataclass
class AnalyticsResult:
    """Result container for analytics operations."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    data_points_analyzed: int = 0


class AnalyticsEngine:
    """
    Advanced analytics engine for carbon footprint data.
    Provides statistical analysis, trend detection, forecasting, and anomaly detection.
    """
    
    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        self._cache: Dict[str, Any] = {}
        self._stats_cache: Dict[str, Any] = {}
        
    def analyze_assessments(
        self, 
        assessments: List[Dict[str, Any]]
    ) -> AnalyticsResult:
        """
        Perform comprehensive analysis on assessment data.
        
        Args:
            assessments: List of assessment dictionaries
        
        Returns:
            AnalyticsResult with analysis results
        """
        import time
        start_time = time.time()
        
        try:
            if not assessments:
                return AnalyticsResult(
                    success=False,
                    message="No data to analyze",
                    data_points_analyzed=0
                )
            
            # Convert to DataFrame
            df = self._prepare_dataframe(assessments)
            
            if len(df) < self.config.min_data_points:
                return AnalyticsResult(
                    success=False,
                    message=f"Need at least {self.config.min_data_points} data points",
                    data_points_analyzed=len(df)
                )
            
            # Run analyses
            results = {
                "descriptive_stats": self._calculate_descriptive_stats(df),
                "trend_analysis": self._analyze_trends(df),
                "seasonal_patterns": self._detect_seasonal_patterns(df),
                "anomalies": self._detect_anomalies(df),
                "forecasts": self._generate_forecasts(df),
                "correlation_analysis": self._analyze_correlations(df),
                "progress_metrics": self._calculate_progress_metrics(df),
                "insights": []
            }
            
            # Generate insights
            results["insights"] = self._generate_insights(df, results)
            
            # Cache results
            cache_key = self._generate_cache_key(assessments)
            self._cache[cache_key] = results
            
            processing_time = (time.time() - start_time) * 1000
            
            return AnalyticsResult(
                success=True,
                message="Analysis completed successfully",
                data=results,
                data_points_analyzed=len(df),
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return AnalyticsResult(
                success=False,
                message=f"Analysis failed: {str(e)}",
                warnings=[str(e)]
            )
    
    def _prepare_dataframe(self, assessments: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare DataFrame for analysis."""
        df = pd.DataFrame(assessments)
        
        # Ensure date column exists
        if 'date' not in df.columns and 'created_at' in df.columns:
            df['date'] = df['created_at']
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Ensure numeric columns are float
        numeric_cols = ['footprint', 'eco_score', 'distance', 'electricity', 'flights']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Drop rows with missing critical data
        df = df.dropna(subset=['footprint', 'date'])
        
        return df
    
    def _calculate_descriptive_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate descriptive statistics."""
        stats_dict = {}
        
        # Footprint stats
        if 'footprint' in df.columns:
            footprint = df['footprint']
            stats_dict['footprint'] = {
                'mean': float(footprint.mean()),
                'median': float(footprint.median()),
                'std': float(footprint.std()),
                'min': float(footprint.min()),
                'max': float(footprint.max()),
                'q1': float(footprint.quantile(0.25)),
                'q3': float(footprint.quantile(0.75)),
                'iqr': float(footprint.quantile(0.75) - footprint.quantile(0.25)),
                'skewness': float(footprint.skew()),
                'kurtosis': float(footprint.kurtosis()),
                'variance': float(footprint.var()),
                'range': float(footprint.max() - footprint.min())
            }
        
        # Eco score stats
        if 'eco_score' in df.columns:
            scores = df['eco_score']
            stats_dict['eco_score'] = {
                'mean': float(scores.mean()),
                'median': float(scores.median()),
                'std': float(scores.std()),
                'min': float(scores.min()),
                'max': float(scores.max()),
                'q1': float(scores.quantile(0.25)),
                'q3': float(scores.quantile(0.75)),
                'iqr': float(scores.quantile(0.75) - scores.quantile(0.25))
            }
        
        # Calculate confidence intervals
        for key in ['footprint', 'eco_score']:
            if key in stats_dict:
                mean = stats_dict[key]['mean']
                std = stats_dict[key]['std']
                n = len(df)
                if n > 1:
                    z_score = stats.norm.ppf((1 + self.config.confidence_interval) / 2)
                    margin = z_score * (std / math.sqrt(n))
                    stats_dict[key]['ci_lower'] = mean - margin
                    stats_dict[key]['ci_upper'] = mean + margin
                    stats_dict[key]['ci_level'] = self.config.confidence_interval
        
        # Data quality metrics
        stats_dict['data_quality'] = {
            'total_records': len(df),
            'date_range_days': (df['date'].max() - df['date'].min()).days,
            'avg_days_between': (df['date'].diff().dt.days.mean()),
            'completeness': 1 - (df.isnull().sum().sum() / (len(df) * len(df.columns)))
        }
        
        return stats_dict
    
    def _analyze_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze trends in the data."""
        trend_results = {}
        
        # Calculate moving averages
        window = self.config.smoothing_window
        if 'footprint' in df.columns:
            df['footprint_ma'] = df['footprint'].rolling(window=window, min_periods=1).mean()
            df['footprint_ema'] = df['footprint'].ewm(span=window, adjust=False).mean()
            
            # Trend direction
            if len(df) > window:
                recent_avg = df['footprint_ma'].iloc[-window:].mean()
                older_avg = df['footprint_ma'].iloc[:window].mean()
                
                trend_results['footprint_trend'] = {
                    'direction': 'decreasing' if recent_avg < older_avg else 'increasing' if recent_avg > older_avg else 'stable',
                    'percent_change': ((recent_avg - older_avg) / older_avg) * 100 if older_avg != 0 else 0,
                    'recent_avg': float(recent_avg),
                    'older_avg': float(older_avg)
                }
                
                # Linear regression for trend
                x = np.arange(len(df))
                y = df['footprint'].values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                
                trend_results['footprint_regression'] = {
                    'slope': float(slope),
                    'intercept': float(intercept),
                    'r_squared': float(r_value ** 2),
                    'p_value': float(p_value),
                    'std_error': float(std_err),
                    'trend_per_day': float(slope)
                }
                
                # Monthly trend
                df['month'] = df['date'].dt.to_period('M')
                monthly_avg = df.groupby('month')['footprint'].mean()
                trend_results['monthly_trend'] = {
                    str(k): float(v) for k, v in monthly_avg.items()
                }
        
        # Eco score trend
        if 'eco_score' in df.columns:
            df['score_ma'] = df['eco_score'].rolling(window=window, min_periods=1).mean()
            
            if len(df) > window:
                recent_score = df['score_ma'].iloc[-window:].mean()
                older_score = df['score_ma'].iloc[:window].mean()
                
                trend_results['score_trend'] = {
                    'direction': 'improving' if recent_score > older_score else 'declining' if recent_score < older_score else 'stable',
                    'percent_change': ((recent_score - older_score) / older_score) * 100 if older_score != 0 else 0,
                    'recent_avg': float(recent_score),
                    'older_avg': float(older_score)
                }
                
                # Linear regression for score
                x = np.arange(len(df))
                y = df['eco_score'].values
                slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
                
                trend_results['score_regression'] = {
                    'slope': float(slope),
                    'intercept': float(intercept),
                    'r_squared': float(r_value ** 2),
                    'p_value': float(p_value),
                    'std_error': float(std_err)
                }
        
        return trend_results
    
    def _detect_seasonal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect seasonal patterns in the data."""
        season_results = {}
        
        if len(df) < self.config.seasonal_period * 2:
            season_results['message'] = "Insufficient data for seasonal analysis"
            return season_results
        
        try:
            # Resample to daily data
            df_daily = df.set_index('date').resample('D').mean().fillna(method='ffill')
            
            if 'footprint' in df_daily.columns:
                footprint = df_daily['footprint'].values
                
                # Seasonal decomposition (simplified)
                period = self.config.seasonal_period
                
                if len(footprint) > period:
                    # Simple seasonal decomposition using moving averages
                    trend = pd.Series(footprint).rolling(window=period, center=True, min_periods=1).mean()
                    detrended = footprint - trend.values if len(trend) == len(footprint) else footprint
                    
                    # Calculate seasonal component
                    seasonal = []
                    for i in range(len(footprint)):
                        idx = i % period
                        season_values = detrended[idx::period]
                        if len(season_values) > 0:
                            seasonal.append(np.mean(season_values))
                        else:
                            seasonal.append(0)
                    
                    # Detect weekly patterns (day of week)
                    df['day_of_week'] = df['date'].dt.dayofweek
                    weekly_pattern = df.groupby('day_of_week')['footprint'].mean().to_dict()
                    
                    season_results['weekly_pattern'] = {
                        f"Day_{k}": float(v) for k, v in weekly_pattern.items()
                    }
                    
                    # Detect monthly patterns
                    df['month_of_year'] = df['date'].dt.month
                    monthly_pattern = df.groupby('month_of_year')['footprint'].mean().to_dict()
                    
                    season_results['monthly_pattern'] = {
                        str(k): float(v) for k, v in monthly_pattern.items()
                    }
                    
                    # Calculate seasonal strength
                    seasonal_strength = 1 - (np.var(seasonal) / np.var(footprint)) if np.var(footprint) > 0 else 0
                    season_results['seasonal_strength'] = float(seasonal_strength)
                    
                    # Detect peaks
                    peaks, _ = find_peaks(footprint, distance=7)
                    valleys, _ = find_peaks(-footprint, distance=7)
                    
                    season_results['seasonal_peaks'] = {
                        'count': len(peaks),
                        'avg_magnitude': float(np.mean(footprint[peaks])) if len(peaks) > 0 else 0
                    }
                    season_results['seasonal_valleys'] = {
                        'count': len(valleys),
                        'avg_magnitude': float(np.mean(footprint[valleys])) if len(valleys) > 0 else 0
                    }
                    
        except Exception as e:
            logger.warning(f"Seasonal analysis failed: {e}")
            season_results['error'] = str(e)
        
        return season_results
    
    def _detect_anomalies(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect anomalies in the data using statistical methods."""
        anomaly_results = {
            'anomalies': [],
            'anomaly_count': 0,
            'anomaly_ratio': 0
        }
        
        if 'footprint' not in df.columns or len(df) < 10:
            return anomaly_results
        
        footprint = df['footprint'].values
        mean = np.mean(footprint)
        std = np.std(footprint)
        threshold = self.config.anomaly_threshold * std
        
        anomalies = []
        for idx, value in enumerate(footprint):
            z_score = (value - mean) / std if std > 0 else 0
            if abs(z_score) > self.config.anomaly_threshold:
                anomalies.append({
                    'index': int(idx),
                    'date': df.iloc[idx]['date'].isoformat(),
                    'value': float(value),
                    'z_score': float(z_score),
                    'deviation': float(value - mean)
                })
        
        anomaly_results['anomalies'] = anomalies
        anomaly_results['anomaly_count'] = len(anomalies)
        anomaly_results['anomaly_ratio'] = len(anomalies) / len(footprint) if len(footprint) > 0 else 0
        anomaly_results['mean'] = float(mean)
        anomaly_results['std'] = float(std)
        anomaly_results['threshold'] = float(threshold)
        
        return anomaly_results
    
    def _generate_forecasts(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate forecasts for future periods."""
        forecast_results = {}
        
        if 'footprint' not in df.columns or len(df) < 10:
            return forecast_results
        
        footprint = df['footprint'].values
        dates = df['date'].values
        
        # Simple moving average forecast
        window = self.config.smoothing_window
        ma = pd.Series(footprint).rolling(window=window, min_periods=1).mean()
        last_ma = ma.iloc[-1]
        
        # Exponential smoothing forecast
        ema = pd.Series(footprint).ewm(span=window, adjust=False).mean()
        last_ema = ema.iloc[-1]
        
        # Linear regression forecast
        x = np.arange(len(footprint))
        slope, intercept, _, _, _ = stats.linregress(x, footprint)
        
        # Generate forecasts for different horizons
        for horizon in self.config.forecast_horizon_days:
            if horizon > self.config.max_forecast_points:
                continue
                
            forecast_values = []
            for i in range(horizon):
                # Combine methods: weighted average of MA, EMA, and regression
                ma_forecast = last_ma
                ema_forecast = last_ema
                reg_forecast = intercept + slope * (len(footprint) + i)
                
                # Weighted combination (can be tuned)
                combined = 0.3 * ma_forecast + 0.3 * ema_forecast + 0.4 * reg_forecast
                forecast_values.append(float(combined))
            
            # Calculate confidence intervals
            residuals = footprint - (intercept + slope * x)
            residual_std = np.std(residuals)
            z_score = stats.norm.ppf((1 + self.config.confidence_interval) / 2)
            
            last_date = dates[-1]
            future_dates = [last_date + timedelta(days=i+1) for i in range(horizon)]
            
            forecast_results[f'{horizon}_days'] = {
                'dates': [d.isoformat() for d in future_dates],
                'forecast': forecast_values,
                'lower_bound': [v - z_score * residual_std for v in forecast_values],
                'upper_bound': [v + z_score * residual_std for v in forecast_values],
                'trend_direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
                'average_change': float(slope * horizon)
            }
        
        return forecast_results
    
    def _analyze_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze correlations between different variables."""
        corr_results = {}
        
        numeric_cols = ['footprint', 'eco_score', 'distance', 'electricity', 'flights']
        available_cols = [col for col in numeric_cols if col in df.columns]
        
        if len(available_cols) < 2:
            return corr_results
        
        corr_matrix = df[available_cols].corr()
        
        # Extract meaningful correlations
        correlations = []
        for i in range(len(available_cols)):
            for j in range(i+1, len(available_cols)):
                col1 = available_cols[i]
                col2 = available_cols[j]
                corr_value = corr_matrix.iloc[i, j]
                
                if abs(corr_value) > 0.3:  # Only report moderate to strong correlations
                    correlations.append({
                        'variable1': col1,
                        'variable2': col2,
                        'correlation': float(corr_value),
                        'strength': 'strong' if abs(corr_value) > 0.7 else 'moderate',
                        'direction': 'positive' if corr_value > 0 else 'negative'
                    })
        
        corr_results['correlations'] = correlations
        
        # Most correlated pair
        if correlations:
            max_corr = max(correlations, key=lambda x: abs(x['correlation']))
            corr_results['strongest_correlation'] = max_corr
        
        return corr_results
    
    def _calculate_progress_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate progress metrics over time."""
        progress = {}
        
        if len(df) < 2:
            return progress
        
        # Overall improvement
        first_footprint = df['footprint'].iloc[0]
        last_footprint = df['footprint'].iloc[-1]
        
        if first_footprint != 0:
            total_reduction = ((first_footprint - last_footprint) / first_footprint) * 100
            progress['total_footprint_reduction'] = {
                'percentage': float(total_reduction),
                'absolute': float(first_footprint - last_footprint),
                'first_value': float(first_footprint),
                'last_value': float(last_footprint)
            }
        
        # Improvement rate
        if len(df) > 2:
            # Calculate slope of improvement
            x = np.arange(len(df))
            slope, _, _, _, _ = stats.linregress(x, df['footprint'].values)
            progress['improvement_rate'] = {
                'per_day': float(slope),
                'per_week': float(slope * 7),
                'per_month': float(slope * 30)
            }
        
        # Consistency score
        if 'footprint' in df.columns:
            std = df['footprint'].std()
            mean = df['footprint'].mean()
            cv = std / mean if mean != 0 else 0  # Coefficient of variation
            
            progress['consistency'] = {
                'coefficient_variation': float(cv),
                'score': float(max(0, 100 - (cv * 100))),  # Higher is more consistent
                'interpretation': 'highly consistent' if cv < 0.2 else 'moderately consistent' if cv < 0.4 else 'inconsistent'
            }
        
        # Best and worst performance
        best_idx = df['footprint'].idxmin()
        worst_idx = df['footprint'].idxmax()
        
        progress['best_performance'] = {
            'date': df.iloc[best_idx]['date'].isoformat(),
            'footprint': float(df.iloc[best_idx]['footprint'])
        }
        progress['worst_performance'] = {
            'date': df.iloc[worst_idx]['date'].isoformat(),
            'footprint': float(df.iloc[worst_idx]['footprint'])
        }
        
        return progress
    
    def _generate_insights(self, df: pd.DataFrame, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable insights from analysis results."""
        insights = []
        
        # Trend insights
        if 'trend_analysis' in results and 'footprint_trend' in results['trend_analysis']:
            trend = results['trend_analysis']['footprint_trend']
            direction = trend['direction']
            
            if direction == 'decreasing':
                insights.append({
                    'type': 'positive',
                    'title': '📉 Footprint Decreasing',
                    'description': f"Your carbon footprint is decreasing! You've reduced by {abs(trend['percent_change']):.1f}%.",
                    'priority': 'high',
                    'category': 'trend'
                })
            elif direction == 'increasing':
                insights.append({
                    'type': 'warning',
                    'title': '📈 Footprint Increasing',
                    'description': f"Your carbon footprint has increased by {trend['percent_change']:.1f}%. Consider reviewing your habits.",
                    'priority': 'high',
                    'category': 'trend'
                })
            else:
                insights.append({
                    'type': 'info',
                    'title': '➡️ Stable Footprint',
                    'description': "Your carbon footprint is stable. Try making small changes to start reducing it.",
                    'priority': 'medium',
                    'category': 'trend'
                })
        
        # Anomaly insights
        if 'anomalies' in results and results['anomalies']['anomaly_count'] > 0:
            anomalies = results['anomalies']['anomalies']
            insights.append({
                'type': 'warning',
                'title': f"⚠️ {len(anomalies)} Anomalies Detected",
                'description': f"Found {len(anomalies)} unusual patterns in your data. The largest deviation was {abs(anomalies[0]['deviation']):.1f} kg CO₂.",
                'priority': 'medium',
                'category': 'anomaly',
                'details': anomalies[:3]  # Show top 3
            })
        
        # Correlation insights
        if 'correlation_analysis' in results and 'strongest_correlation' in results['correlation_analysis']:
            corr = results['correlation_analysis']['strongest_correlation']
            insights.append({
                'type': 'info',
                'title': f"🔗 Strong Correlation Found",
                'description': f"{corr['variable1']} and {corr['variable2']} have a {corr['strength']} {corr['direction']} correlation (r={corr['correlation']:.2f}).",
                'priority': 'low',
                'category': 'correlation'
            })
        
        # Progress insights
        if 'progress_metrics' in results:
            progress = results['progress_metrics']
            
            if 'total_footprint_reduction' in progress:
                reduction = progress['total_footprint_reduction']
                if reduction['percentage'] > 10:
                    insights.append({
                        'type': 'achievement',
                        'title': '🏆 Significant Progress!',
                        'description': f"You've reduced your footprint by {reduction['percentage']:.1f}%! Keep up the great work!",
                        'priority': 'high',
                        'category': 'achievement'
                    })
            
            if 'consistency' in progress:
                consistency = progress['consistency']
                if consistency['score'] > 70:
                    insights.append({
                        'type': 'positive',
                        'title': '✅ Consistent Habits',
                        'description': f"Your habits are {consistency['interpretation']} (score: {consistency['score']:.0f}/100).",
                        'priority': 'medium',
                        'category': 'consistency'
                    })
        
        # Forecast insights
        if 'forecasts' in results and '30_days' in results['forecasts']:
            forecast = results['forecasts']['30_days']
            direction = forecast['trend_direction']
            
            if direction == 'decreasing':
                insights.append({
                    'type': 'positive',
                    'title': '🔮 Positive Forecast',
                    'description': f"Based on your trend, your footprint is projected to decrease by {abs(forecast['average_change']):.1f} kg CO₂ in the next 30 days.",
                    'priority': 'low',
                    'category': 'forecast'
                })
            elif direction == 'increasing':
                insights.append({
                    'type': 'warning',
                    'title': '🔮 Forecast Warning',
                    'description': f"Your footprint is projected to increase by {forecast['average_change']:.1f} kg CO₂ in the next 30 days. Consider taking action.",
                    'priority': 'medium',
                    'category': 'forecast'
                })
        
        # Sort insights by priority
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        insights.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
        
        return insights
    
    def _generate_cache_key(self, assessments: List[Dict[str, Any]]) -> str:
        """Generate cache key for assessments."""
        import hashlib
        import json
        
        # Use last modified timestamps or assessment IDs
        data_str = json.dumps(assessments, default=str)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def get_cached_analysis(self, assessments: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Retrieve cached analysis results."""
        cache_key = self._generate_cache_key(assessments)
        return self._cache.get(cache_key)
    
    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        self._cache.clear()
        self._stats_cache.clear()
    
    def get_analysis_summary(self, assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get a quick summary of analysis results."""
        result = self.analyze_assessments(assessments)
        
        if not result.success or not result.data:
            return {
                'success': False,
                'message': result.message
            }
        
        data = result.data
        
        return {
            'success': True,
            'total_assessments': result.data_points_analyzed,
            'average_footprint': data.get('descriptive_stats', {}).get('footprint', {}).get('mean', 0),
            'average_score': data.get('descriptive_stats', {}).get('eco_score', {}).get('mean', 0),
            'trend': data.get('trend_analysis', {}).get('footprint_trend', {}).get('direction', 'stable'),
            'improvement': data.get('progress_metrics', {}).get('total_footprint_reduction', {}).get('percentage', 0),
            'anomalies': data.get('anomalies', {}).get('anomaly_count', 0),
            'insights_count': len(data.get('insights', []))
        }


# Global analytics engine instance
_analytics_engine: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get or create global analytics engine instance."""
    global _analytics_engine
    if _analytics_engine is None:
        _analytics_engine = AnalyticsEngine()
    return _analytics_engine


def analyze_assessments(assessments: List[Dict[str, Any]]) -> AnalyticsResult:
    """
    Convenience function to analyze assessments.
    
    Args:
        assessments: List of assessment dictionaries
    
    Returns:
        AnalyticsResult with analysis results
    """
    engine = get_analytics_engine()
    return engine.analyze_assessments(assessments)


def get_analysis_summary(assessments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convenience function to get analysis summary.
    
    Args:
        assessments: List of assessment dictionaries
    
    Returns:
        Analysis summary dictionary
    """
    engine = get_analytics_engine()
    return engine.get_analysis_summary(assessments)