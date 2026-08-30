"""
Sustainability Behavior Intelligence - Data Models
Comprehensive models for behavioral analysis and trend detection.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import uuid
import json


class TrendType(Enum):
    """Types of trends that can be detected."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    VOLATILE = "volatile"
    CYCLICAL = "cyclical"
    EXPONENTIAL = "exponential"
    LOGARITHMIC = "logarithmic"
    LINEAR = "linear"
    S_CURVE = "s_curve"
    PLATEAU = "plateau"
    UNDEFINED = "undefined"


class TrendDirection(Enum):
    """Direction of a trend."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class InsightType(Enum):
    """Types of behavioral insights."""
    STRENGTH = "strength"
    WEAKNESS = "weakness"
    OPPORTUNITY = "opportunity"
    THREAT = "threat"
    ACHIEVEMENT = "achievement"
    REGRESSION = "regression"
    IMPROVEMENT = "improvement"
    CONSISTENCY = "consistency"
    INCONSISTENCY = "inconsistency"
    MILESTONE = "milestone"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"
    ALERT = "alert"
    CELEBRATION = "celebration"
    CHALLENGE = "challenge"


class InsightPriority(Enum):
    """Priority levels for insights."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class CorrelationStrength(Enum):
    """Strength of correlation between behaviors."""
    VERY_STRONG = "very_strong"  # 0.8-1.0
    STRONG = "strong"            # 0.6-0.8
    MODERATE = "moderate"        # 0.4-0.6
    WEAK = "weak"                # 0.2-0.4
    VERY_WEAK = "very_weak"      # 0.0-0.2
    NEGATIVE = "negative"        # < 0.0


@dataclass
class DataPoint:
    """Represents a single data point in a time series."""
    timestamp: datetime
    value: float
    category: str = ""
    unit: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value,
            'category': self.category,
            'unit': self.unit,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataPoint':
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            value=data['value'],
            category=data.get('category', ''),
            unit=data.get('unit', ''),
            metadata=data.get('metadata', {})
        )


@dataclass
class BehaviorTrend:
    """
    Represents a detected behavioral trend.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    metric: str = ""
    trend_type: TrendType = TrendType.UNDEFINED
    direction: TrendDirection = TrendDirection.NEUTRAL
    slope: float = 0.0
    intercept: float = 0.0
    r_squared: float = 0.0  # Statistical fit
    confidence: float = 0.0  # 0-1
    
    # Time period
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=datetime.now)
    data_points: List[DataPoint] = field(default_factory=list)
    
    # Metrics
    average_change: float = 0.0
    percent_change: float = 0.0
    volatility: float = 0.0  # Standard deviation
    max_value: float = 0.0
    min_value: float = 0.0
    current_value: float = 0.0
    baseline_value: float = 0.0
    
    # Seasonality
    has_seasonality: bool = False
    seasonality_period: int = 0  # Days
    seasonality_strength: float = 0.0
    
    # Metadata
    description: str = ""
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'metric': self.metric,
            'trend_type': self.trend_type.value,
            'direction': self.direction.value,
            'slope': self.slope,
            'intercept': self.intercept,
            'r_squared': self.r_squared,
            'confidence': self.confidence,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'data_points': [dp.to_dict() for dp in self.data_points],
            'average_change': self.average_change,
            'percent_change': self.percent_change,
            'volatility': self.volatility,
            'max_value': self.max_value,
            'min_value': self.min_value,
            'current_value': self.current_value,
            'baseline_value': self.baseline_value,
            'has_seasonality': self.has_seasonality,
            'seasonality_period': self.seasonality_period,
            'seasonality_strength': self.seasonality_strength,
            'description': self.description,
            'recommendations': self.recommendations,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BehaviorTrend':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            category=data.get('category', ''),
            metric=data.get('metric', ''),
            trend_type=TrendType(data.get('trend_type', 'undefined')),
            direction=TrendDirection(data.get('direction', 'neutral')),
            slope=data.get('slope', 0.0),
            intercept=data.get('intercept', 0.0),
            r_squared=data.get('r_squared', 0.0),
            confidence=data.get('confidence', 0.0),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else datetime.now(),
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else datetime.now(),
            data_points=[DataPoint.from_dict(dp) for dp in data.get('data_points', [])],
            average_change=data.get('average_change', 0.0),
            percent_change=data.get('percent_change', 0.0),
            volatility=data.get('volatility', 0.0),
            max_value=data.get('max_value', 0.0),
            min_value=data.get('min_value', 0.0),
            current_value=data.get('current_value', 0.0),
            baseline_value=data.get('baseline_value', 0.0),
            has_seasonality=data.get('has_seasonality', False),
            seasonality_period=data.get('seasonality_period', 0),
            seasonality_strength=data.get('seasonality_strength', 0.0),
            description=data.get('description', ''),
            recommendations=data.get('recommendations', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the trend."""
        direction_map = {
            TrendDirection.POSITIVE: "improving",
            TrendDirection.NEGATIVE: "declining",
            TrendDirection.NEUTRAL: "stable",
            TrendDirection.MIXED: "mixed"
        }
        
        return f"{self.metric} is {direction_map.get(self.direction, 'undefined')} " \
               f"({self.percent_change:+.1f}%) with {self.confidence*100:.0f}% confidence"


@dataclass
class ConsistencyScore:
    """
    Represents consistency analysis for a behavior or habit.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    habit_name: str = ""
    
    # Overall metrics
    completion_rate: float = 0.0  # 0-100
    weekly_consistency: float = 0.0  # 0-100
    monthly_consistency: float = 0.0  # 0-100
    overall_consistency: float = 0.0  # 0-100
    
    # Streak metrics
    current_streak: int = 0
    longest_streak: int = 0
    missed_frequency: float = 0.0  # Times per week
    missed_days: List[datetime] = field(default_factory=list)
    
    # Improvement trends
    improvement_score: float = 0.0  # -1 to 1
    improvement_trend: Optional[BehaviorTrend] = None
    
    # Weekly patterns
    weekly_patterns: Dict[str, float] = field(default_factory=dict)  # Day -> completion rate
    best_day: str = ""
    worst_day: str = ""
    
    # Monthly patterns
    monthly_patterns: Dict[str, float] = field(default_factory=dict)  # Month -> completion rate
    best_month: str = ""
    worst_month: str = ""
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'habit_name': self.habit_name,
            'completion_rate': self.completion_rate,
            'weekly_consistency': self.weekly_consistency,
            'monthly_consistency': self.monthly_consistency,
            'overall_consistency': self.overall_consistency,
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'missed_frequency': self.missed_frequency,
            'missed_days': [d.isoformat() for d in self.missed_days],
            'improvement_score': self.improvement_score,
            'improvement_trend': self.improvement_trend.to_dict() if self.improvement_trend else None,
            'weekly_patterns': self.weekly_patterns,
            'best_day': self.best_day,
            'worst_day': self.worst_day,
            'monthly_patterns': self.monthly_patterns,
            'best_month': self.best_month,
            'worst_month': self.worst_month,
            'recommendations': self.recommendations,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConsistencyScore':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            category=data.get('category', ''),
            habit_name=data.get('habit_name', ''),
            completion_rate=data.get('completion_rate', 0.0),
            weekly_consistency=data.get('weekly_consistency', 0.0),
            monthly_consistency=data.get('monthly_consistency', 0.0),
            overall_consistency=data.get('overall_consistency', 0.0),
            current_streak=data.get('current_streak', 0),
            longest_streak=data.get('longest_streak', 0),
            missed_frequency=data.get('missed_frequency', 0.0),
            missed_days=[datetime.fromisoformat(d) for d in data.get('missed_days', [])],
            improvement_score=data.get('improvement_score', 0.0),
            improvement_trend=BehaviorTrend.from_dict(data['improvement_trend']) if data.get('improvement_trend') else None,
            weekly_patterns=data.get('weekly_patterns', {}),
            best_day=data.get('best_day', ''),
            worst_day=data.get('worst_day', ''),
            monthly_patterns=data.get('monthly_patterns', {}),
            best_month=data.get('best_month', ''),
            worst_month=data.get('worst_month', ''),
            recommendations=data.get('recommendations', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )
    
    def get_consistency_level(self) -> str:
        """Get a human-readable consistency level."""
        if self.overall_consistency >= 80:
            return "Excellent"
        elif self.overall_consistency >= 60:
            return "Good"
        elif self.overall_consistency >= 40:
            return "Average"
        elif self.overall_consistency >= 20:
            return "Below Average"
        else:
            return "Needs Improvement"


@dataclass
class BehaviorCorrelation:
    """
    Represents a correlation between two behaviors or metrics.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    behavior1: str = ""
    behavior2: str = ""
    correlation_coefficient: float = 0.0
    strength: CorrelationStrength = CorrelationStrength.VERY_WEAK
    p_value: float = 0.0  # Statistical significance
    sample_size: int = 0
    
    # Direction
    is_positive: bool = True
    is_significant: bool = False
    
    # Description
    description: str = ""
    insight: str = ""
    recommendation: str = ""
    
    # Data points
    data_points: List[Tuple[float, float]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'behavior1': self.behavior1,
            'behavior2': self.behavior2,
            'correlation_coefficient': self.correlation_coefficient,
            'strength': self.strength.value,
            'p_value': self.p_value,
            'sample_size': self.sample_size,
            'is_positive': self.is_positive,
            'is_significant': self.is_significant,
            'description': self.description,
            'insight': self.insight,
            'recommendation': self.recommendation,
            'data_points': [(x, y) for x, y in self.data_points],
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BehaviorCorrelation':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            behavior1=data.get('behavior1', ''),
            behavior2=data.get('behavior2', ''),
            correlation_coefficient=data.get('correlation_coefficient', 0.0),
            strength=CorrelationStrength(data.get('strength', 'very_weak')),
            p_value=data.get('p_value', 0.0),
            sample_size=data.get('sample_size', 0),
            is_positive=data.get('is_positive', True),
            is_significant=data.get('is_significant', False),
            description=data.get('description', ''),
            insight=data.get('insight', ''),
            recommendation=data.get('recommendation', ''),
            data_points=data.get('data_points', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class PredictionResult:
    """
    Represents a prediction about future sustainability performance.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = ""
    metric: str = ""
    
    # Prediction
    predicted_value: float = 0.0
    confidence_interval_lower: float = 0.0
    confidence_interval_upper: float = 0.0
    confidence_level: float = 0.0  # 0-1
    
    # Timeline
    prediction_date: datetime = field(default_factory=datetime.now)
    target_date: datetime = field(default_factory=datetime.now)
    horizon_days: int = 0
    
    # Model information
    model_type: str = ""  # linear, exponential, arima, etc.
    model_accuracy: float = 0.0  # MAPE or similar
    data_points_used: int = 0
    
    # Projections
    projected_trend: List[DataPoint] = field(default_factory=list)
    goal_achievement_date: Optional[datetime] = None
    
    # Metadata
    is_reliable: bool = False
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'metric': self.metric,
            'predicted_value': self.predicted_value,
            'confidence_interval_lower': self.confidence_interval_lower,
            'confidence_interval_upper': self.confidence_interval_upper,
            'confidence_level': self.confidence_level,
            'prediction_date': self.prediction_date.isoformat(),
            'target_date': self.target_date.isoformat(),
            'horizon_days': self.horizon_days,
            'model_type': self.model_type,
            'model_accuracy': self.model_accuracy,
            'data_points_used': self.data_points_used,
            'projected_trend': [dp.to_dict() for dp in self.projected_trend],
            'goal_achievement_date': self.goal_achievement_date.isoformat() if self.goal_achievement_date else None,
            'is_reliable': self.is_reliable,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PredictionResult':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            category=data.get('category', ''),
            metric=data.get('metric', ''),
            predicted_value=data.get('predicted_value', 0.0),
            confidence_interval_lower=data.get('confidence_interval_lower', 0.0),
            confidence_interval_upper=data.get('confidence_interval_upper', 0.0),
            confidence_level=data.get('confidence_level', 0.0),
            prediction_date=datetime.fromisoformat(data['prediction_date']) if data.get('prediction_date') else datetime.now(),
            target_date=datetime.fromisoformat(data['target_date']) if data.get('target_date') else datetime.now(),
            horizon_days=data.get('horizon_days', 0),
            model_type=data.get('model_type', ''),
            model_accuracy=data.get('model_accuracy', 0.0),
            data_points_used=data.get('data_points_used', 0),
            projected_trend=[DataPoint.from_dict(dp) for dp in data.get('projected_trend', [])],
            goal_achievement_date=datetime.fromisoformat(data['goal_achievement_date']) if data.get('goal_achievement_date') else None,
            is_reliable=data.get('is_reliable', False),
            notes=data.get('notes', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class CategoryIntelligence:
    """
    Intelligence analysis for a specific sustainability category.
    """
    category: str = ""
    
    # Performance metrics
    current_score: float = 0.0
    baseline_score: float = 0.0
    improvement: float = 0.0  # Percentage
    rank: int = 0
    
    # Category rankings
    is_strongest: bool = False
    is_weakest: bool = False
    is_fastest_improving: bool = False
    is_most_regressing: bool = False
    is_highest_impact: bool = False
    needs_attention: bool = False
    
    # Trends
    trend: Optional[BehaviorTrend] = None
    trend_type: TrendType = TrendType.UNDEFINED
    
    # Consistency
    consistency_score: Optional[ConsistencyScore] = None
    
    # Correlations
    correlations: List[BehaviorCorrelation] = field(default_factory=list)
    
    # Insights
    insights: List['BehaviorInsight'] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    # Predictions
    predictions: List[PredictionResult] = field(default_factory=list)
    
    # Metadata
    data_points: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'category': self.category,
            'current_score': self.current_score,
            'baseline_score': self.baseline_score,
            'improvement': self.improvement,
            'rank': self.rank,
            'is_strongest': self.is_strongest,
            'is_weakest': self.is_weakest,
            'is_fastest_improving': self.is_fastest_improving,
            'is_most_regressing': self.is_most_regressing,
            'is_highest_impact': self.is_highest_impact,
            'needs_attention': self.needs_attention,
            'trend': self.trend.to_dict() if self.trend else None,
            'trend_type': self.trend_type.value,
            'consistency_score': self.consistency_score.to_dict() if self.consistency_score else None,
            'correlations': [c.to_dict() for c in self.correlations],
            'insights': [i.to_dict() for i in self.insights],
            'recommendations': self.recommendations,
            'predictions': [p.to_dict() for p in self.predictions],
            'data_points': self.data_points,
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class BehaviorInsight:
    """
    Represents a behavioral insight generated by the intelligence system.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: InsightType = InsightType.INFORMATIONAL
    priority: InsightPriority = InsightPriority.MEDIUM
    
    # Content
    title: str = ""
    description: str = ""
    detailed_explanation: str = ""
    
    # Context
    category: str = ""
    related_metrics: List[str] = field(default_factory=list)
    related_data: Dict[str, Any] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    # Metadata
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    # Tracking
    is_actioned: bool = False
    actioned_at: Optional[datetime] = None
    feedback_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'description': self.description,
            'detailed_explanation': self.detailed_explanation,
            'category': self.category,
            'related_metrics': self.related_metrics,
            'related_data': self.related_data,
            'recommendations': self.recommendations,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_actioned': self.is_actioned,
            'actioned_at': self.actioned_at.isoformat() if self.actioned_at else None,
            'feedback_score': self.feedback_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BehaviorInsight':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            type=InsightType(data.get('type', 'informational')),
            priority=InsightPriority(data.get('priority', 'medium')),
            title=data.get('title', ''),
            description=data.get('description', ''),
            detailed_explanation=data.get('detailed_explanation', ''),
            category=data.get('category', ''),
            related_metrics=data.get('related_metrics', []),
            related_data=data.get('related_data', {}),
            recommendations=data.get('recommendations', []),
            confidence=data.get('confidence', 0.0),
            timestamp=datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.now(),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            is_actioned=data.get('is_actioned', False),
            actioned_at=datetime.fromisoformat(data['actioned_at']) if data.get('actioned_at') else None,
            feedback_score=data.get('feedback_score')
        )


@dataclass
class BehaviorSummary:
    """
    Comprehensive summary of a user's sustainability behavior.
    """
    user_id: str = ""
    
    # Overall metrics
    overall_trend: TrendType = TrendType.UNDEFINED
    current_sustainability_score: float = 0.0
    improvement_percentage: float = 0.0
    
    # Category rankings
    strongest_category: str = ""
    weakest_category: str = ""
    fastest_improving_category: str = ""
    most_regressing_category: str = ""
    highest_impact_category: str = ""
    
    # Habit metrics
    most_consistent_habit: str = ""
    biggest_regression: str = ""
    current_streak: int = 0
    longest_streak: int = 0
    
    # Goals
    goal_progress: float = 0.0
    goals_on_track: int = 0
    goals_at_risk: int = 0
    
    # Insights
    top_insights: List[BehaviorInsight] = field(default_factory=list)
    top_recommendations: List[str] = field(default_factory=list)
    
    # Category intelligence
    category_intelligence: List[CategoryIntelligence] = field(default_factory=list)
    
    # Temporal analysis
    monthly_comparisons: List['MonthlyComparison'] = field(default_factory=list)
    weekly_patterns: List['WeeklyPattern'] = field(default_factory=list)
    
    # Metadata
    generated_at: datetime = field(default_factory=datetime.now)
    data_span_days: int = 0
    data_points_total: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'overall_trend': self.overall_trend.value,
            'current_sustainability_score': self.current_sustainability_score,
            'improvement_percentage': self.improvement_percentage,
            'strongest_category': self.strongest_category,
            'weakest_category': self.weakest_category,
            'fastest_improving_category': self.fastest_improving_category,
            'most_regressing_category': self.most_regressing_category,
            'highest_impact_category': self.highest_impact_category,
            'most_consistent_habit': self.most_consistent_habit,
            'biggest_regression': self.biggest_regression,
            'current_streak': self.current_streak,
            'longest_streak': self.longest_streak,
            'goal_progress': self.goal_progress,
            'goals_on_track': self.goals_on_track,
            'goals_at_risk': self.goals_at_risk,
            'top_insights': [i.to_dict() for i in self.top_insights],
            'top_recommendations': self.top_recommendations,
            'category_intelligence': [c.to_dict() for c in self.category_intelligence],
            'monthly_comparisons': [m.to_dict() for m in self.monthly_comparisons],
            'weekly_patterns': [w.to_dict() for w in self.weekly_patterns],
            'generated_at': self.generated_at.isoformat(),
            'data_span_days': self.data_span_days,
            'data_points_total': self.data_points_total
        }


@dataclass
class MonthlyComparison:
    """
    Comparison of behavior across months.
    """
    month: str = ""  # YYYY-MM
    score: float = 0.0
    change_from_previous: float = 0.0
    percent_change: float = 0.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'month': self.month,
            'score': self.score,
            'change_from_previous': self.change_from_previous,
            'percent_change': self.percent_change,
            'category_scores': self.category_scores,
            'insights': self.insights
        }


@dataclass
class WeeklyPattern:
    """
    Weekly behavioral pattern analysis.
    """
    week_start: datetime = field(default_factory=datetime.now)
    week_end: datetime = field(default_factory=datetime.now)
    average_score: float = 0.0
    best_day: str = ""
    worst_day: str = ""
    daily_scores: Dict[str, float] = field(default_factory=dict)
    consistency_score: float = 0.0
    insights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'week_start': self.week_start.isoformat(),
            'week_end': self.week_end.isoformat(),
            'average_score': self.average_score,
            'best_day': self.best_day,
            'worst_day': self.worst_day,
            'daily_scores': self.daily_scores,
            'consistency_score': self.consistency_score,
            'insights': self.insights
        }


@dataclass
class BehavioralPattern:
    """
    Represents a recurring behavioral pattern.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: str = ""  # daily, weekly, monthly
    category: str = ""
    description: str = ""
    frequency: float = 0.0  # How often it occurs
    strength: float = 0.0  # 0-1
    impact: float = 0.0  # Impact on sustainability
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)