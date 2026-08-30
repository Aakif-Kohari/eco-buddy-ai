"""
Sustainability Behavior Intelligence - Core Analyzer
Main analysis engine for behavioral intelligence.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import statistics
import math

from intelligence.models import (
    DataPoint, BehaviorTrend, TrendType, TrendDirection,
    BehaviorInsight, InsightType, InsightPriority,
    ConsistencyScore, BehaviorCorrelation, PredictionResult,
    CategoryIntelligence, BehaviorSummary, MonthlyComparison,
    WeeklyPattern, BehavioralPattern
)
from intelligence.trends import TrendDetector
from intelligence.consistency import ConsistencyAnalyzer
from intelligence.correlations import CorrelationAnalyzer
from intelligence.predictions import PredictiveAnalyzer
from intelligence.insights import InsightGenerator

logger = logging.getLogger(__name__)


class BehaviorIntelligenceAnalyzer:
    """
    Main analyzer for sustainability behavior intelligence.
    Integrates all analysis components to provide comprehensive insights.
    """
    
    def __init__(self):
        """Initialize the analyzer with all sub-analyzers."""
        self.trend_detector = TrendDetector()
        self.consistency_analyzer = ConsistencyAnalyzer()
        self.correlation_analyzer = CorrelationAnalyzer()
        self.predictive_analyzer = PredictiveAnalyzer()
        self.insight_generator = InsightGenerator()
        
        self.categories = [
            'carbon_footprint',
            'energy_consumption',
            'water_usage',
            'waste_generation',
            'transportation_impact',
            'food_impact',
            'habit_completion',
            'goal_progress',
            'recommendation_adoption',
            'roadmap_progress'
        ]
        
        logger.info("Behavior Intelligence Analyzer initialized")
    
    def analyze_user_behavior(self, user_id: str, 
                             historical_data: Dict[str, List[Dict[str, Any]]],
                             habits: List[Dict[str, Any]],
                             goals: List[Dict[str, Any]],
                             roadmap_data: Optional[Dict[str, Any]] = None) -> BehaviorSummary:
        """
        Perform comprehensive behavioral analysis for a user.
        
        Args:
            user_id: The user ID
            historical_data: Dictionary of historical data by category
            habits: List of user habits
            goals: List of user goals
            roadmap_data: Optional roadmap data
        
        Returns:
            BehaviorSummary: Comprehensive behavioral summary        """
        logger.info(f"Analyzing behavior for user {user_id}")
        
        # Convert historical data to data points
        data_points = self._convert_to_data_points(historical_data)
        
        # Analyze each category
        category_intelligence = []
        category_scores = {}
        
        for category in self.categories:
            if category in historical_data and historical_data[category]:
                cat_data = self._get_category_data(category, historical_data)
                
                if len(cat_data) >= 3:  # Need at least 3 points for analysis
                    intelligence = self._analyze_category(
                        category, 
                        cat_data, 
                        habits,
                        goals
                    )
                    category_intelligence.append(intelligence)
                    category_scores[category] = intelligence.current_score
        
        # Generate overall summary
        summary = self._generate_summary(
            user_id,
            category_intelligence,
            category_scores,
            habits,
            goals,
            roadmap_data
        )
        
        # Generate insights
        summary.top_insights = self.insight_generator.generate_insights(
            category_intelligence,
            habits,
            goals,
            summary
        )
        
        # Generate recommendations
        summary.top_recommendations = self._generate_recommendations(
            category_intelligence,
            habits,
            summary
        )
        
        # Analyze monthly patterns
        summary.monthly_comparisons = self._analyze_monthly_patterns(historical_data)
        
        # Analyze weekly patterns
        summary.weekly_patterns = self._analyze_weekly_patterns(historical_data)
        
        # Generate top insights
        summary.top_insights = summary.top_insights[:5]  # Top 5 insights
        
        logger.info(f"Completed behavior analysis for user {user_id}")
        return summary
    
    def _convert_to_data_points(self, historical_data: Dict[str, List[Dict[str, Any]]]) -> List[DataPoint]:
        """Convert historical data to DataPoint objects."""
        data_points = []
        
        for category, records in historical_data.items():
            for record in records:
                if 'timestamp' in record and 'value' in record:
                    data_points.append(
                        DataPoint(
                            timestamp=record['timestamp'],
                            value=record['value'],
                            category=category,
                            unit=record.get('unit', ''),
                            metadata=record.get('metadata', {})
                        )
                    )
        
        return sorted(data_points, key=lambda x: x.timestamp)
    
    def _get_category_data(self, category: str, 
                          historical_data: Dict[str, List[Dict[str, Any]]]) -> List[DataPoint]:
        """Get data points for a specific category."""
        data = []
        for record in historical_data.get(category, []):
            data.append(
                DataPoint(
                    timestamp=record.get('timestamp', datetime.now()),
                    value=record.get('value', 0.0),
                    category=category,
                    unit=record.get('unit', ''),
                    metadata=record.get('metadata', {})
                )
            )
        return sorted(data, key=lambda x: x.timestamp)
    
    def _analyze_category(self, category: str,
                         data_points: List[DataPoint],
                         habits: List[Dict[str, Any]],
                         goals: List[Dict[str, Any]]) -> CategoryIntelligence:
        """Analyze a single category."""
        logger.info(f"Analyzing category: {category}")
        
        intelligence = CategoryIntelligence(
            category=category,
            data_points=len(data_points)
        )
        
        # Calculate scores
        values = [dp.value for dp in data_points]
        intelligence.baseline_score = values[0] if values else 0
        intelligence.current_score = values[-1] if values else 0
        intelligence.improvement = ((intelligence.current_score - intelligence.baseline_score) / 
                                   (intelligence.baseline_score + 0.001) * 100)
        
        # Detect trend
        if len(data_points) >= 3:
            intelligence.trend = self.trend_detector.detect_trend(data_points)
            if intelligence.trend:
                intelligence.trend_type = intelligence.trend.trend_type
        
        # Analyze consistency for related habits
        related_habits = [h for h in habits if h.get('category') == category]
        if related_habits:
            intelligence.consistency_score = self.consistency_analyzer.analyze_habits(
                related_habits
            )
        
        # Find correlations
        intelligence.correlations = self.correlation_analyzer.find_correlations(
            category,
            data_points,
            [dp for dp in data_points if dp.category != category]
        )
        
        # Generate predictions
        if len(data_points) >= 10:
            intelligence.predictions = self.predictive_analyzer.predict_future(
                data_points,
                horizon_days=30
            )
        
        # Generate insights
        intelligence.insights = self.insight_generator.generate_category_insights(
            intelligence
        )
        
        # Generate recommendations
        intelligence.recommendations = self._generate_category_recommendations(
            intelligence
        )
        
        return intelligence
    
    def _generate_summary(self, user_id: str,
                         category_intelligence: List[CategoryIntelligence],
                         category_scores: Dict[str, float],
                         habits: List[Dict[str, Any]],
                         goals: List[Dict[str, Any]],
                         roadmap_data: Optional[Dict[str, Any]]) -> BehaviorSummary:
        """Generate overall behavior summary."""
        summary = BehaviorSummary(
            user_id=user_id,
            category_intelligence=category_intelligence
        )
        
        # Calculate overall scores
        if category_scores:
            summary.current_sustainability_score = statistics.mean(category_scores.values())
            summary.improvement_percentage = statistics.mean(
                [c.improvement for c in category_intelligence if c.improvement != 0]
            ) if category_intelligence else 0
        
        # Find strongest and weakest categories
        if category_intelligence:
            sorted_categories = sorted(
                category_intelligence,
                key=lambda x: x.current_score,
                reverse=True
            )
            
            summary.strongest_category = sorted_categories[0].category if sorted_categories else ""
            summary.weakest_category = sorted_categories[-1].category if sorted_categories else ""
            
            # Find fastest improving
            improving = [c for c in category_intelligence if c.improvement > 0]
            if improving:
                fastest = max(improving, key=lambda x: x.improvement)
                summary.fastest_improving_category = fastest.category
            
            # Find most regressing
            regressing = [c for c in category_intelligence if c.improvement < 0]
            if regressing:
                worst = min(regressing, key=lambda x: x.improvement)
                summary.most_regressing_category = worst.category
            
            # Find highest impact
            highest_impact = max(
                category_intelligence,
                key=lambda x: abs(x.improvement),
                default=None
            )
            if highest_impact:
                summary.highest_impact_category = highest_impact.category
        
        # Analyze habits
        if habits:
            consistency_scores = []
            for habit in habits:
                score = self.consistency_analyzer.calculate_habit_consistency(habit)
                if score:
                    consistency_scores.append((habit.get('name', ''), score))
            
            if consistency_scores:
                # Most consistent
                best = max(consistency_scores, key=lambda x: x[1].overall_consistency)
                summary.most_consistent_habit = best[0]
                
                # Biggest regression
                worst = min(consistency_scores, key=lambda x: x[1].improvement_score)
                if worst[1].improvement_score < 0:
                    summary.biggest_regression = worst[0]
                
                # Streaks
                summary.current_streak = max(
                    [s[1].current_streak for s in consistency_scores],
                    default=0
                )
                summary.longest_streak = max(
                    [s[1].longest_streak for s in consistency_scores],
                    default=0
                )
        
        # Analyze goals
        if goals:
            completed = [g for g in goals if g.get('status') == 'completed']
            in_progress = [g for g in goals if g.get('status') == 'in_progress']
            
            summary.goals_on_track = len(in_progress)
            summary.goals_at_risk = len([g for g in in_progress if g.get('progress', 0) < 30])
            
            if in_progress:
                summary.goal_progress = statistics.mean(
                    [g.get('progress', 0) for g in in_progress]
                )
        
        # Calculate data span
        if category_intelligence:
            all_dates = []
            for cat in category_intelligence:
                if cat.trend and cat.trend.data_points:
                    all_dates.extend([dp.timestamp for dp in cat.trend.data_points])
            
            if all_dates:
                summary.data_span_days = (max(all_dates) - min(all_dates)).days
                summary.data_points_total = sum(
                    c.data_points for c in category_intelligence
                )
        
        # Determine overall trend
        if category_intelligence:
            trend_types = [c.trend_type for c in category_intelligence if c.trend_type != TrendType.UNDEFINED]
            if trend_types:
                summary.overall_trend = max(set(trend_types), key=trend_types.count)
        
        return summary
    
    def _generate_category_recommendations(self, 
                                          intelligence: CategoryIntelligence) -> List[str]:
        """Generate recommendations for a specific category."""
        recommendations = []
        
        if intelligence.trend_type == TrendType.DECLINING:
            recommendations.append(
                f"Your {intelligence.category} is declining. Consider reviewing "
                f"your approach and identifying areas for improvement."
            )
        
        if intelligence.needs_attention:
            recommendations.append(
                f"Your {intelligence.category} needs immediate attention. "
                f"Focus on this area to improve your overall sustainability."
            )
        
        if intelligence.current_score < 50 and intelligence.improvement < 0:
            recommendations.append(
                f"Your {intelligence.category} is below average and declining. "
                f"Consider seeking expert advice or resources to improve."
            )
        
        if intelligence.consistency_score and intelligence.consistency_score.overall_consistency < 40:
            recommendations.append(
                f"Your consistency in {intelligence.category} is low. "
                f"Try to establish a regular routine to build better habits."
            )
        
        if intelligence.trend_type == TrendType.PLATEAU:
            recommendations.append(
                f"Your {intelligence.category} has plateaued. "
                f"Try new strategies or set more ambitious goals to progress further."
            )
        
        return recommendations
    
    def _generate_recommendations(self,
                                 category_intelligence: List[CategoryIntelligence],
                                 habits: List[Dict[str, Any]],
                                 summary: BehaviorSummary) -> List[str]:
        """Generate overall recommendations."""
        recommendations = []
        
        # Priority recommendations based on critical categories
        critical_categories = [
            c for c in category_intelligence 
            if c.needs_attention and c.current_score < 40
        ]
        
        for cat in sorted(critical_categories, key=lambda x: x.current_score):
            recommendations.append(
                f"🚨 Critical: Your {cat.category} is at {cat.current_score:.1f}% and requires "
                f"immediate attention. Focus on this area first."
            )
        
        # Recommendations for declining trends
        declining = [
            c for c in category_intelligence 
            if c.trend_type == TrendType.DECLINING
        ]
        
        for cat in declining:
            recommendations.append(
                f"📉 Your {cat.category} is declining. Review your recent actions "
                f"and consider adjusting your approach."
            )
        
        # Recommendations for improving consistency
        low_consistency = [
            c for c in category_intelligence 
            if c.consistency_score and c.consistency_score.overall_consistency < 50
        ]
        
        for cat in low_consistency:
            recommendations.append(
                f"🔄 Your consistency in {cat.category} needs improvement. "
                f"Try to establish a regular routine or set daily reminders."
            )
        
        # Specific habit recommendations
        for habit in habits:
            if habit.get('streak', 0) == 0:
                recommendations.append(
                    f"💪 Start building the habit '{habit.get('name', '')}' today. "
                    f"Even a small step counts toward progress."
                )
        
        return recommendations
    
    def _analyze_monthly_patterns(self, 
                                 historical_data: Dict[str, List[Dict[str, Any]]]) -> List[MonthlyComparison]:
        """Analyze monthly patterns from historical data."""
        monthly_patterns = []
        
        # Group data by month
        monthly_data = {}
        for category, records in historical_data.items():
            for record in records:
                if 'timestamp' in record and 'value' in record:
                    month_key = record['timestamp'].strftime('%Y-%m')
                    if month_key not in monthly_data:
                        monthly_data[month_key] = {}
                    if category not in monthly_data[month_key]:
                        monthly_data[month_key][category] = []
                    monthly_data[month_key][category].append(record['value'])
        
        # Calculate monthly averages
        sorted_months = sorted(monthly_data.keys())
        
        for i, month in enumerate(sorted_months):
            category_scores = {}
            for category, values in monthly_data[month].items():
                category_scores[category] = statistics.mean(values) if values else 0
            
            avg_score = statistics.mean(category_scores.values()) if category_scores else 0
            
            pattern = MonthlyComparison(
                month=month,
                score=avg_score,
                category_scores=category_scores
            )
            
            # Calculate change from previous month
            if i > 0:
                prev_month = sorted_months[i-1]
                prev_scores = []
                for category, values in monthly_data[prev_month].items():
                    prev_scores.append(statistics.mean(values) if values else 0)
                prev_avg = statistics.mean(prev_scores) if prev_scores else 0
                
                pattern.change_from_previous = avg_score - prev_avg
                pattern.percent_change = ((avg_score - prev_avg) / (prev_avg + 0.001)) * 100
            
            monthly_patterns.append(pattern)
        
        return monthly_patterns
    
    def _analyze_weekly_patterns(self, 
                                historical_data: Dict[str, List[Dict[str, Any]]]) -> List[WeeklyPattern]:
        """Analyze weekly patterns from historical data."""
        weekly_patterns = []
        
        # Group data by week
        weekly_data = {}
        for category, records in historical_data.items():
            for record in records:
                if 'timestamp' in record and 'value' in record:
                    week_start = record['timestamp'] - timedelta(
                        days=record['timestamp'].weekday()
                    )
                    week_key = week_start.strftime('%Y-%m-%d')
                    
                    if week_key not in weekly_data:
                        weekly_data[week_key] = {}
                    if category not in weekly_data[week_key]:
                        weekly_data[week_key][category] = []
                    weekly_data[week_key][category].append(record['value'])
        
        # Calculate weekly patterns
        for week_key, categories in weekly_data.items():
            daily_scores = {}
            day_totals = {}
            
            for category, values in categories.items():
                avg = statistics.mean(values) if values else 0
                daily_scores[category] = avg
            
            avg_score = statistics.mean(daily_scores.values()) if daily_scores else 0
            consistency_score = 100 - (statistics.stdev(daily_scores.values()) if len(daily_scores) > 1 else 0)
            
            pattern = WeeklyPattern(
                week_start=datetime.strptime(week_key, '%Y-%m-%d'),
                week_end=datetime.strptime(week_key, '%Y-%m-%d') + timedelta(days=6),
                average_score=avg_score,
                daily_scores=daily_scores,
                consistency_score=consistency_score
            )
            
            # Find best and worst days
            if daily_scores:
                best_day = max(daily_scores, key=daily_scores.get)
                worst_day = min(daily_scores, key=daily_scores.get)
                pattern.best_day = best_day
                pattern.worst_day = worst_day
            
            weekly_patterns.append(pattern)
        
        return sorted(weekly_patterns, key=lambda x: x.week_start, reverse=True)
    
    def generate_trend_analysis(self, data_points: List[DataPoint]) -> Dict[str, Any]:
        """
        Generate detailed trend analysis for a set of data points.
        
        Args:
            data_points: List of data points to analyze
        
        Returns:
            Dict containing trend analysis results
        """
        if len(data_points) < 3:
            return {'error': 'Insufficient data points for trend analysis'}
        
        trend = self.trend_detector.detect_trend(data_points)
        
        if not trend:
            return {'error': 'Could not detect trend'}
        
        return {
            'trend_type': trend.trend_type.value,
            'direction': trend.direction.value,
            'slope': trend.slope,
            'r_squared': trend.r_squared,
            'confidence': trend.confidence,
            'percent_change': trend.percent_change,
            'volatility': trend.volatility,
            'has_seasonality': trend.has_seasonality,
            'description': trend.description,
            'recommendations': trend.recommendations
        }
    
    def get_behavior_summary_text(self, summary: BehaviorSummary) -> str:
        """
        Generate a human-readable summary text.
        
        Args:
            summary: The behavior summary
        
        Returns:
            str: Human-readable summary
        """
        lines = []
        
        lines.append("=" * 60)
        lines.append("🌍 SUSTAINABILITY BEHAVIOR SUMMARY")
        lines.append("=" * 60)
        lines.append("")
        
        # Overall status
        lines.append(f"📊 Overall Trend: {summary.overall_trend.value.title()}")
        lines.append(f"🎯 Sustainability Score: {summary.current_sustainability_score:.1f}%")
        lines.append(f"📈 Improvement: {summary.improvement_percentage:+.1f}%")
        lines.append("")
        
        # Category rankings
        lines.append("🏆 CATEGORY RANKINGS:")
        lines.append(f"   Strongest: {summary.strongest_category.replace('_', ' ').title()}")
        lines.append(f"   Weakest: {summary.weakest_category.replace('_', ' ').title()}")
        lines.append(f"   Fastest Improving: {summary.fastest_improving_category.replace('_', ' ').title()}")
        lines.append(f"   Needs Attention: {summary.most_regressing_category.replace('_', ' ').title()}")
        lines.append("")
        
        # Habits
        lines.append("💪 HABIT ANALYSIS:")
        lines.append(f"   Most Consistent: {summary.most_consistent_habit}")
        if summary.biggest_regression:
            lines.append(f"   Biggest Regression: {summary.biggest_regression}")
        lines.append(f"   Current Streak: {summary.current_streak} days")
        lines.append(f"   Longest Streak: {summary.longest_streak} days")
        lines.append("")
        
        # Goals
        lines.append("🎯 GOAL PROGRESS:")
        lines.append(f"   Overall Progress: {summary.goal_progress:.1f}%")
        lines.append(f"   Goals On Track: {summary.goals_on_track}")
        lines.append(f"   Goals At Risk: {summary.goals_at_risk}")
        lines.append("")
        
        # Top recommendations
        if summary.top_recommendations:
            lines.append("💡 TOP RECOMMENDATIONS:")
            for i, rec in enumerate(summary.top_recommendations[:3], 1):
                lines.append(f"   {i}. {rec}")
            lines.append("")
        
        # Data span
        lines.append(f"📊 Data Span: {summary.data_span_days} days")
        lines.append(f"📈 Data Points: {summary.data_points_total}")
        lines.append("")
        lines.append("=" * 60)
        
        return '\n'.join(lines)