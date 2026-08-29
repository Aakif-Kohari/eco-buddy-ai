"""
Sustainability Behavior Intelligence & Trend Analyzer
A comprehensive system for analyzing sustainability behavior patterns.
"""

from intelligence.models import (
    BehaviorTrend, TrendType, TrendDirection, BehaviorInsight,
    InsightType, InsightPriority, ConsistencyScore, BehaviorCorrelation,
    PredictionResult, CategoryIntelligence, BehaviorSummary,
    MonthlyComparison, WeeklyPattern, BehavioralPattern
)
from intelligence.analyzer import BehaviorIntelligenceAnalyzer
from intelligence.trends import TrendDetector
from intelligence.consistency import ConsistencyAnalyzer
from intelligence.correlations import CorrelationAnalyzer
from intelligence.predictions import PredictiveAnalyzer
from intelligence.insights import InsightGenerator
from intelligence.visualizations import IntelligenceVisualizer
from intelligence.dashboard import IntelligenceDashboard

__all__ = [
    'BehaviorTrend',
    'TrendType',
    'TrendDirection',
    'BehaviorInsight',
    'InsightType',
    'InsightPriority',
    'ConsistencyScore',
    'BehaviorCorrelation',
    'PredictionResult',
    'CategoryIntelligence',
    'BehaviorSummary',
    'MonthlyComparison',
    'WeeklyPattern',
    'BehavioralPattern',
    'BehaviorIntelligenceAnalyzer',
    'TrendDetector',
    'ConsistencyAnalyzer',
    'CorrelationAnalyzer',
    'PredictiveAnalyzer',
    'InsightGenerator',
    'IntelligenceVisualizer',
    'IntelligenceDashboard'
]