"""
Trend Analyzer for EcoBuddy AI
Advanced trend detection, pattern recognition, and change point analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
from dataclasses import dataclass, field
from scipy import stats
from scipy.signal import savgol_filter, find_peaks
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class TrendResult:
    """Result container for trend analysis."""
    success: bool
    message: str
    trends: Optional[Dict[str, Any]] = None
    change_points: Optional[List[Dict[str, Any]]] = None
    patterns: Optional[List[Dict[str, Any]]] = None
    summary: Optional[Dict[str, Any]] = None
    visualizations: Optional[Dict[str, Any]] = None


class TrendAnalyzer:
    """
    Advanced trend analyzer for sustainability data.
    Detects trends, patterns, and change points in time series data.
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        
    def analyze_trends(self, assessments: List[Dict[str, Any]]) -> TrendResult:
        """
        Perform comprehensive trend analysis.
        
        Args:
            assessments: List of assessment dictionaries
        
        Returns:
            TrendResult with analysis results
        """
        try:
            if not assessments:
                return TrendResult(
                    success=False,
                    message="No data to analyze"
                )
            
            # Prepare data
            df = self._prepare_dataframe(assessments)
            
            if len(df) < 3:
                return TrendResult(
                    success=False,
                    message="Insufficient data for trend analysis"
                )
            
            # Detect trends
            trends = self._detect_trends(df)
            
            # Detect change points
            change_points = self._detect_change_points(df)
            
            # Detect patterns
            patterns = self._detect_patterns(df)
            
            # Generate summary
            summary = self._generate_summary(df, trends, change_points, patterns)
            
            return TrendResult(
                success=True,
                message="Trend analysis completed",
                trends=trends,
                change_points=change_points,
                patterns=patterns,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return TrendResult(
                success=False,
                message=f"Analysis failed: {str(e)}"
            )
    
    def _prepare_dataframe(self, assessments: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare DataFrame for analysis."""
        df = pd.DataFrame(assessments)
        
        if 'date' not in df.columns and 'created_at' in df.columns:
            df['date'] = df['created_at']
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Fill missing values
        numeric_cols = ['footprint', 'eco_score', 'distance', 'electricity', 'flights']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(df[col].mean())
        
        return df
    
    def _detect_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Detect trends in the data."""
        trend_results = {
            'footprint': {},
            'eco_score': {},
            'overall': {}
        }
        
        # Footprint trends
        if 'footprint' in df.columns:
            y = df['footprint'].values
            x = np.arange(len(y))
            
            # Linear trend
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            # Polynomial trend (degree 2)
            coeffs = np.polyfit(x, y, 2)
            poly_trend = np.poly1d(coeffs)
            
            # Smooth trend using Savitzky-Golay filter
            smoothed = savgol_filter(y, min(len(y), 5), 2) if len(y) >= 5 else y
            
            # Calculate trend strength
            trend_strength = abs(slope) / (np.std(y) if np.std(y) > 0 else 1)
            
            trend_results['footprint'] = {
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_value ** 2),
                'p_value': float(p_value),
                'std_error': float(std_err),
                'direction': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
                'magnitude': abs(slope),
                'strength': 'strong' if trend_strength > 0.5 else 'moderate' if trend_strength > 0.2 else 'weak',
                'polynomial_coefficients': [float(c) for c in coeffs],
                'smoothed': smoothed.tolist() if isinstance(smoothed, np.ndarray) else list(smoothed)
            }
        
        # Eco score trends
        if 'eco_score' in df.columns:
            y = df['eco_score'].values
            x = np.arange(len(y))
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
            
            trend_results['eco_score'] = {
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': float(r_value ** 2),
                'p_value': float(p_value),
                'std_error': float(std_err),
                'direction': 'improving' if slope > 0 else 'declining' if slope < 0 else 'stable',
                'magnitude': abs(slope)
            }
        
        # Overall trend assessment
        if 'footprint' in trend_results and 'eco_score' in trend_results:
            fp_trend = trend_results['footprint']['direction']
            sc_trend = trend_results['eco_score']['direction']
            
            if fp_trend == 'decreasing' and sc_trend == 'improving':
                overall = 'positive'
                description = 'Your sustainability is improving!'
            elif fp_trend == 'increasing' and sc_trend == 'declining':
                overall = 'negative'
                description = 'Your sustainability is declining. Consider making changes.'
            else:
                overall = 'mixed'
                description = 'Mixed trends detected. Some areas are improving while others need attention.'
            
            trend_results['overall'] = {
                'status': overall,
                'description': description,
                'footprint_trend': fp_trend,
                'score_trend': sc_trend
            }
        
        return trend_results
    
    def _detect_change_points(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect change points in the time series."""
        change_points = []
        
        if 'footprint' not in df.columns:
            return change_points
        
        y = df['footprint'].values
        dates = df['date'].values
        
        if len(y) < 5:
            return change_points
        
        # Use cumulative sum method for change point detection
        n = len(y)
        max_cusum = 0
        change_point_idx = 0
        
        # Calculate cumulative sum
        mean = np.mean(y)
        cusum = np.cumsum(y - mean)
        
        # Find maximum deviation
        for i in range(1, n):
            if abs(cusum[i]) > max_cusum:
                max_cusum = abs(cusum[i])
                change_point_idx = i
        
        # Add significant change points
        if max_cusum > 2 * np.std(y):
            change_points.append({
                'index': int(change_point_idx),
                'date': dates[change_point_idx].isoformat(),
                'value': float(y[change_point_idx]),
                'significance': 'significant',
                'direction': 'increasing' if cusum[change_point_idx] > 0 else 'decreasing',
                'impact': float(max_cusum)
            })
        
        # Detect additional change points using sliding window
        window_size = min(3, n // 4)
        if window_size >= 2:
            for i in range(window_size, n - window_size):
                left_mean = np.mean(y[i-window_size:i])
                right_mean = np.mean(y[i:i+window_size])
                diff = abs(right_mean - left_mean)
                
                if diff > 2 * np.std(y[i-window_size:i+window_size]):
                    change_points.append({
                        'index': int(i),
                        'date': dates[i].isoformat(),
                        'value': float(y[i]),
                        'significance': 'moderate',
                        'direction': 'increasing' if right_mean > left_mean else 'decreasing',
                        'impact': float(diff)
                    })
        
        # Sort by significance
        change_points.sort(key=lambda x: x.get('impact', 0), reverse=True)
        
        return change_points[:5]  # Return top 5
    
    def _detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect patterns in the data."""
        patterns = []
        
        if 'footprint' not in df.columns:
            return patterns
        
        y = df['footprint'].values
        
        # Detect repeating patterns (cycles)
        if len(y) > 10:
            # Autocorrelation
            autocorr = np.correlate(y, y, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find peaks in autocorrelation
            peaks, _ = find_peaks(autocorr, height=0.5)
            if len(peaks) > 0:
                # Patterns cycle length
                cycle_length = peaks[0] if len(peaks) > 0 else 0
                if cycle_length > 1 and cycle_length < len(y) // 2:
                    patterns.append({
                        'type': 'cyclical',
                        'cycle_length': int(cycle_length),
                        'description': f'Repeating cycle detected every {cycle_length} data points',
                        'strength': float(autocorr[peaks[0]]) if len(peaks) > 0 else 0
                    })
        
        # Detect level shifts
        if len(y) > 5:
            # Split data into two halves
            mid = len(y) // 2
            first_half = y[:mid]
            second_half = y[mid:]
            
            if len(first_half) > 2 and len(second_half) > 2:
                first_mean = np.mean(first_half)
                second_mean = np.mean(second_half)
                diff_pct = abs((second_mean - first_mean) / first_mean) * 100 if first_mean != 0 else 0
                
                if diff_pct > 20:
                    patterns.append({
                        'type': 'level_shift',
                        'change_percentage': float(diff_pct),
                        'direction': 'increasing' if second_mean > first_mean else 'decreasing',
                        'description': f'Significant level shift of {diff_pct:.1f}% detected',
                        'first_half_mean': float(first_mean),
                        'second_half_mean': float(second_mean)
                    })
        
        # Detect volatility patterns
        if len(y) > 10:
            rolling_std = pd.Series(y).rolling(window=5, min_periods=2).std()
            avg_std = np.mean(rolling_std)
            
            if avg_std > 0.3 * np.mean(y):
                patterns.append({
                    'type': 'high_volatility',
                    'description': 'High variability detected in your data',
                    'average_std': float(avg_std),
                    'suggestion': 'Your habits show significant variation. Consider building more consistent routines.'
                })
            elif avg_std < 0.1 * np.mean(y):
                patterns.append({
                    'type': 'low_volatility',
                    'description': 'Low variability detected in your data',
                    'average_std': float(avg_std),
                    'suggestion': 'Your habits are very consistent. Great job maintaining stability!'
                })
        
        return patterns
    
    def _generate_summary(
        self, 
        df: pd.DataFrame, 
        trends: Dict[str, Any],
        change_points: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate summary of trend analysis."""
        summary = {
            'data_points': len(df),
            'date_range': {
                'start': df['date'].min().isoformat(),
                'end': df['date'].max().isoformat()
            },
            'trends_count': len(trends),
            'change_points_count': len(change_points),
            'patterns_count': len(patterns),
            'key_findings': []
        }
        
        # Extract key findings
        if 'overall' in trends:
            summary['key_findings'].append(f"Overall trend: {trends['overall']['status']}")
            summary['key_findings'].append(trends['overall']['description'])
        
        if change_points:
            for cp in change_points[:2]:
                summary['key_findings'].append(
                    f"Change point detected on {cp['date']}: {cp['direction']} trend"
                )
        
        if patterns:
            for p in patterns[:2]:
                summary['key_findings'].append(p['description'])
        
        # Calculate improvement metrics
        if 'footprint' in df.columns:
            first = df['footprint'].iloc[0]
            last = df['footprint'].iloc[-1]
            improvement = ((first - last) / first) * 100 if first != 0 else 0
            
            summary['improvement'] = {
                'percentage': float(improvement),
                'absolute': float(first - last),
                'status': 'improving' if improvement > 0 else 'declining' if improvement < 0 else 'stable'
            }
        
        return summary
    
    def get_trend_forecast(
        self, 
        assessments: List[Dict[str, Any]], 
        horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate trend-based forecast.
        
        Args:
            assessments: List of assessment dictionaries
            horizon_days: Number of days to forecast
        
        Returns:
            Forecast dictionary
        """
        if not assessments:
            return {'success': False, 'message': 'No data available'}
        
        df = self._prepare_dataframe(assessments)
        
        if 'footprint' not in df.columns or len(df) < 3:
            return {'success': False, 'message': 'Insufficient data'}
        
        y = df['footprint'].values
        x = np.arange(len(y))
        
        # Fit trend model
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Generate forecast
        forecast = []
        dates = []
        last_date = df['date'].iloc[-1]
        
        for i in range(horizon_days):
            future_idx = len(y) + i
            predicted = intercept + slope * future_idx
            forecast.append(max(0, float(predicted)))
            dates.append((last_date + timedelta(days=i+1)).isoformat())
        
        # Confidence intervals
        residual_std = np.std(y - (intercept + slope * x))
        confidence = 1.96 * residual_std
        
        return {
            'success': True,
            'forecast': forecast,
            'dates': dates,
            'trend': 'decreasing' if slope < 0 else 'increasing' if slope > 0 else 'stable',
            'slope': float(slope),
            'confidence_interval': float(confidence),
            'r_squared': float(r_value ** 2)
        }


# Global trend analyzer instance
_trend_analyzer: Optional[TrendAnalyzer] = None


def get_trend_analyzer() -> TrendAnalyzer:
    """Get or create global trend analyzer instance."""
    global _trend_analyzer
    if _trend_analyzer is None:
        _trend_analyzer = TrendAnalyzer()
    return _trend_analyzer


def analyze_trends(assessments: List[Dict[str, Any]]) -> TrendResult:
    """
    Convenience function to analyze trends.
    
    Args:
        assessments: List of assessment dictionaries
    
    Returns:
        TrendResult with analysis results
    """
    analyzer = get_trend_analyzer()
    return analyzer.analyze_trends(assessments)


def get_trend_forecast(assessments: List[Dict[str, Any]], horizon_days: int = 30) -> Dict[str, Any]:
    """
    Convenience function to get trend forecast.
    
    Args:
        assessments: List of assessment dictionaries
        horizon_days: Number of days to forecast
    
    Returns:
        Forecast dictionary
    """
    analyzer = get_trend_analyzer()
    return analyzer.get_trend_forecast(assessments, horizon_days)