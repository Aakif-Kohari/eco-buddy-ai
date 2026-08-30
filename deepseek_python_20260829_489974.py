"""
Sustainability Behavior Intelligence - Correlation Analysis
Finds relationships between different behaviors and categories.
"""

import logging
import math
import statistics
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict

from intelligence.models import DataPoint, BehaviorCorrelation, CorrelationStrength

logger = logging.getLogger(__name__)


class CorrelationAnalyzer:
    """
    Analyzes correlations between different behaviors and metrics.
    """
    
    def __init__(self):
        """Initialize the correlation analyzer."""
        self.min_data_points = 10
        self.significance_threshold = 0.05
        logger.info("Correlation Analyzer initialized")
    
    def find_correlations(self, 
                         category: str,
                         main_data: List[DataPoint],
                         other_data: List[DataPoint]) -> List[BehaviorCorrelation]:
        """
        Find correlations between a category and other behaviors.
        
        Args:
            category: Main category name
            main_data: Data points for the main category
            other_data: Data points for other categories
        
        Returns:
            List[BehaviorCorrelation]: Found correlations
        """
        correlations = []
        
        if len(main_data) < self.min_data_points:
            logger.warning(f"Insufficient data for correlation analysis: {category}")
            return correlations
        
        # Group other data by category
        grouped_data = defaultdict(list)
        for dp in other_data:
            grouped_data[dp.category].append(dp)
        
        for other_category, data_points in grouped_data.items():
            if len(data_points) < self.min_data_points:
                continue
            
            # Calculate correlation
            correlation = self._calculate_correlation(
                category,
                other_category,
                main_data,
                data_points
            )
            
            if correlation:
                correlations.append(correlation)
        
        # Sort by correlation strength
        correlations.sort(key=lambda x: abs(x.correlation_coefficient), reverse=True)
        
        return correlations
    
    def _calculate_correlation(self, 
                             category1: str,
                             category2: str,
                             data1: List[DataPoint],
                             data2: List[DataPoint]) -> Optional[BehaviorCorrelation]:
        """
        Calculate correlation between two sets of data points.
        """
        # Align data by timestamp (closest timestamps)
        aligned_data = self._align_data(data1, data2)
        
        if len(aligned_data) < self.min_data_points:
            return None
        
        # Extract values
        values1 = [d[0] for d in aligned_data]
        values2 = [d[1] for d in aligned_data]
        
        # Calculate Pearson correlation coefficient
        r = self._pearson_correlation(values1, values2)
        
        # Calculate p-value (approximate)
        n = len(values1)
        if n > 2:
            t = r * math.sqrt((n - 2) / (1 - r**2)) if abs(r) < 1 else 0
            # Approximate p-value using t-distribution
            p_value = self._approximate_p_value(t, n - 2)
        else:
            p_value = 1.0
        
        # Determine correlation strength
        strength = self._get_correlation_strength(abs(r))
        
        # Check if significant
        is_significant = p_value < self.significance_threshold
        
        # Generate description and insight
        description = self._generate_correlation_description(
            category1, category2, r, strength
        )
        
        insight = self._generate_correlation_insight(
            category1, category2, r, is_significant
        )
        
        recommendation = self._generate_correlation_recommendation(
            category1, category2, r, strength
        )
        
        return BehaviorCorrelation(
            behavior1=category1,
            behavior2=category2,
            correlation_coefficient=r,
            strength=strength,
            p_value=p_value,
            sample_size=n,
            is_positive=r > 0,
            is_significant=is_significant,
            description=description,
            insight=insight,
            recommendation=recommendation,
            data_points=aligned_data
        )
    
    def _align_data(self, data1: List[DataPoint], 
                   data2: List[DataPoint]) -> List[Tuple[float, float]]:
        """
        Align two sets of data points by timestamp.
        """
        # Sort by timestamp
        sorted1 = sorted(data1, key=lambda x: x.timestamp)
        sorted2 = sorted(data2, key=lambda x: x.timestamp)
        
        aligned = []
        i = j = 0
        
        while i < len(sorted1) and j < len(sorted2):
            diff = (sorted1[i].timestamp - sorted2[j].timestamp).total_seconds()
            
            if abs(diff) < 86400:  # Within 1 day
                aligned.append((sorted1[i].value, sorted2[j].value))
                i += 1
                j += 1
            elif diff < 0:
                i += 1
            else:
                j += 1
        
        return aligned
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """
        Calculate Pearson correlation coefficient.
        """
        if len(x) != len(y) or len(x) < 2:
            return 0
        
        n = len(x)
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = math.sqrt(
            sum((x[i] - x_mean) ** 2 for i in range(n)) *
            sum((y[i] - y_mean) ** 2 for i in range(n))
        )
        
        if denominator == 0:
            return 0
        
        return numerator / denominator
    
    def _approximate_p_value(self, t: float, df: int) -> float:
        """
        Approximate p-value from t-statistic.
        """
        # Simplified approximation using standard normal
        import math
        
        # Student's t approximation using normal
        if df > 30:
            return 2 * (1 - self._normal_cdf(abs(t)))
        
        # For small df, use a rough approximation
        p = 0.5 * (1 + self._sign(t) * (1 - math.exp(-t**2 / (df + 0.5 * df))))
        return min(1, max(0, p))
    
    def _normal_cdf(self, z: float) -> float:
        """
        Approximate normal CDF.
        """
        if z < -6:
            return 0
        if z > 6:
            return 1
        
        # Polynomial approximation
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911
        
        sign = 1 if z >= 0 else -1
        z = abs(z)
        
        t = 1 / (1 + p * z)
        y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-z * z / 2)
        
        return 0.5 + sign * (y - 0.5)
    
    def _sign(self, x: float) -> int:
        """Sign function."""
        return 1 if x >= 0 else -1
    
    def _get_correlation_strength(self, r: float) -> CorrelationStrength:
        """
        Convert correlation coefficient to strength category.
        """
        if r >= 0.8:
            return CorrelationStrength.VERY_STRONG
        elif r >= 0.6:
            return CorrelationStrength.STRONG
        elif r >= 0.4:
            return CorrelationStrength.MODERATE
        elif r >= 0.2:
            return CorrelationStrength.WEAK
        elif r >= 0:
            return CorrelationStrength.VERY_WEAK
        else:
            return CorrelationStrength.NEGATIVE
    
    def _generate_correlation_description(self, 
                                        cat1: str, 
                                        cat2: str,
                                        r: float,
                                        strength: CorrelationStrength) -> str:
        """
        Generate description of the correlation.
        """
        direction = "positive" if r > 0 else "negative"
        strength_map = {
            CorrelationStrength.VERY_STRONG: "very strong",
            CorrelationStrength.STRONG: "strong",
            CorrelationStrength.MODERATE: "moderate",
            CorrelationStrength.WEAK: "weak",
            CorrelationStrength.VERY_WEAK: "very weak",
            CorrelationStrength.NEGATIVE: "negative"
        }
        
        return f"There is a {strength_map[strength]} {direction} correlation between {cat1} and {cat2} (r={r:.3f})"
    
    def _generate_correlation_insight(self,
                                    cat1: str,
                                    cat2: str,
                                    r: float,
                                    is_significant: bool) -> str:
        """
        Generate insight from the correlation.
        """
        if not is_significant:
            return f"No significant correlation was found between {cat1} and {cat2}."
        
        if r > 0.8:
            return f"{cat1} and {cat2} are strongly linked. Improvements in one are strongly associated with improvements in the other."
        elif r > 0.6:
            return f"Improvements in {cat1} are associated with improvements in {cat2}."
        elif r > 0.4:
            return f"There is a moderate positive relationship between {cat1} and {cat2}."
        elif r < -0.6:
            return f"{cat1} and {cat2} show a strong inverse relationship."
        elif r < -0.4:
            return f"There is a moderate inverse relationship between {cat1} and {cat2}."
        else:
            return f"Little to no meaningful relationship was found between {cat1} and {cat2}."
    
    def _generate_correlation_recommendation(self,
                                           cat1: str,
                                           cat2: str,
                                           r: float,
                                           strength: CorrelationStrength) -> str:
        """
        Generate recommendation based on the correlation.
        """
        if abs(r) < 0.3:
            return f"Focus on improving {cat1} and {cat2} independently."
        
        if r > 0.6:
            return f"Improving {cat1} may also improve {cat2}. Consider strategies that benefit both areas."
        elif r < -0.6:
            return f"High {cat1} is associated with low {cat2}. Consider finding a balance between these areas."
        elif r > 0.4:
            return f"Consider how improvements in {cat1} could contribute to improvements in {cat2}."
        elif r < -0.4:
            return f"Consider how changes in {cat1} might affect {cat2} negatively. Look for more balanced approaches."
        else:
            return f"Work on improving {cat1} and {cat2} through separate targeted interventions."