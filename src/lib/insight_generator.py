"""
Insight Generator for EcoBuddy AI
Generates actionable insights, recommendations, and smart suggestions from analytics data.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import random
import json

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """Container for a single insight."""
    id: str
    type: str  # positive, warning, achievement, info, suggestion
    title: str
    description: str
    priority: str  # high, medium, low
    category: str  # trend, anomaly, achievement, recommendation, forecast, consistency
    actionable: bool
    action_links: List[Dict[str, str]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class InsightResult:
    """Container for insight generation results."""
    success: bool
    message: str
    insights: List[Insight] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0


class InsightGenerator:
    """
    Generates personalized insights and recommendations from sustainability data.
    Uses rule-based logic and pattern matching to identify meaningful insights.
    """
    
    def __init__(self):
        self._insight_history: List[Dict[str, Any]] = []
        self._insight_templates = self._load_templates()
        self._generated_count = 0
        
    def generate_insights(
        self, 
        assessments: List[Dict[str, Any]],
        analytics_data: Dict[str, Any]
    ) -> InsightResult:
        """
        Generate insights from assessments and analytics data.
        
        Args:
            assessments: List of assessment dictionaries
            analytics_data: Analytics results from AnalyticsEngine
        
        Returns:
            InsightResult with generated insights
        """
        import time
        start_time = time.time()
        
        try:
            if not assessments:
                return InsightResult(
                    success=False,
                    message="No data to generate insights"
                )
            
            insights = []
            
            # Generate insights from different categories
            insights.extend(self._generate_trend_insights(analytics_data))
            insights.extend(self._generate_anomaly_insights(analytics_data))
            insights.extend(self._generate_achievement_insights(assessments, analytics_data))
            insights.extend(self._generate_recommendation_insights(assessments, analytics_data))
            insights.extend(self._generate_forecast_insights(analytics_data))
            insights.extend(self._generate_consistency_insights(assessments, analytics_data))
            insights.extend(self._generate_comparison_insights(assessments))
            insights.extend(self._generate_milestone_insights(assessments))
            
            # Sort by priority
            priority_order = {'high': 0, 'medium': 1, 'low': 2}
            insights.sort(key=lambda x: priority_order.get(x.priority, 3))
            
            # Generate summary
            summary = self._generate_summary(insights)
            
            # Store history
            self._insight_history.append({
                'timestamp': datetime.now().isoformat(),
                'insight_count': len(insights),
                'summary': summary
            })
            
            self._generated_count += len(insights)
            
            processing_time = (time.time() - start_time) * 1000
            
            return InsightResult(
                success=True,
                message=f"Generated {len(insights)} insights",
                insights=insights,
                summary=summary,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return InsightResult(
                success=False,
                message=f"Failed to generate insights: {str(e)}"
            )
    
    def _load_templates(self) -> Dict[str, Any]:
        """Load insight templates."""
        return {
            'trend': {
                'decreasing': {
                    'title': '📉 Carbon Footprint Decreasing',
                    'description': 'Your carbon footprint is on a downward trend! You\'ve reduced by {percentage:.1f}%. Keep up the great work!',
                    'type': 'positive',
                    'priority': 'high'
                },
                'increasing': {
                    'title': '📈 Carbon Footprint Increasing',
                    'description': 'Your carbon footprint has increased by {percentage:.1f}%. Consider reviewing your daily habits and making small changes.',
                    'type': 'warning',
                    'priority': 'high'
                },
                'stable': {
                    'title': '➡️ Footprint Stable',
                    'description': 'Your carbon footprint has remained stable. Try making small changes to start reducing it.',
                    'type': 'info',
                    'priority': 'medium'
                }
            },
            'achievement': {
                'milestone': {
                    'title': '🏆 {milestone} Milestone Reached!',
                    'description': 'You\'ve reached {milestone} milestone! {next_milestone} is within reach.',
                    'type': 'achievement',
                    'priority': 'high'
                },
                'streak': {
                    'title': '🔥 {streak} Day Streak!',
                    'description': 'You\'ve maintained a {streak} day streak of consistent assessments. Keep going!',
                    'type': 'achievement',
                    'priority': 'high'
                },
                'improvement': {
                    'title': '📈 Improvement Detected!',
                    'description': 'Your {metric} has improved by {improvement:.1f}% compared to {comparison}.',
                    'type': 'achievement',
                    'priority': 'medium'
                }
            },
            'recommendation': {
                'transport': {
                    'title': '🚗 Transportation Recommendation',
                    'description': 'Consider switching to public transport or cycling for short trips. This could reduce your footprint by {savings:.0f} kg CO₂.',
                    'type': 'suggestion',
                    'priority': 'high'
                },
                'energy': {
                    'title': '⚡ Energy Saving Tip',
                    'description': 'Reduce electricity consumption by turning off unused appliances. Potential saving: {savings:.0f} kg CO₂.',
                    'type': 'suggestion',
                    'priority': 'medium'
                },
                'diet': {
                    'title': '🥗 Diet Recommendation',
                    'description': 'Incorporate more plant-based meals into your diet. This could reduce your footprint by {savings:.0f} kg CO₂.',
                    'type': 'suggestion',
                    'priority': 'medium'
                },
                'flights': {
                    'title': '✈️ Travel Recommendation',
                    'description': 'Consider reducing unnecessary air travel or offsetting your flights. Potential saving: {savings:.0f} kg CO₂.',
                    'type': 'suggestion',
                    'priority': 'high'
                }
            },
            'forecast': {
                'positive': {
                    'title': '🔮 Positive Forecast',
                    'description': 'Based on your trend, your footprint is projected to decrease by {change:.1f}% in the next {days} days.',
                    'type': 'positive',
                    'priority': 'medium'
                },
                'warning': {
                    'title': '🔮 Forecast Warning',
                    'description': 'Your footprint is projected to increase by {change:.1f}% in the next {days} days. Consider taking action.',
                    'type': 'warning',
                    'priority': 'medium'
                }
            }
        }
    
    def _generate_trend_insights(self, analytics_data: Dict[str, Any]) -> List[Insight]:
        """Generate insights from trend analysis."""
        insights = []
        
        if 'trend_analysis' not in analytics_data:
            return insights
        
        trend_data = analytics_data['trend_analysis']
        
        # Footprint trend insight
        if 'footprint_trend' in trend_data:
            trend = trend_data['footprint_trend']
            direction = trend['direction']
            percentage = abs(trend['percent_change'])
            
            if direction in self._insight_templates['trend']:
                template = self._insight_templates['trend'][direction]
                
                # Only generate if change is significant (>5%)
                if percentage > 5:
                    insights.append(Insight(
                        id=f"trend_{direction}_{self._generated_count + len(insights)}",
                        type=template['type'],
                        title=template['title'],
                        description=template['description'].format(percentage=percentage),
                        priority=template['priority'],
                        category='trend',
                        actionable=direction == 'increasing',
                        metrics={
                            'change_percentage': percentage,
                            'direction': direction,
                            'recent_avg': trend.get('recent_avg', 0),
                            'older_avg': trend.get('older_avg', 0)
                        },
                        action_links=[
                            {'label': 'View Recommendations', 'target': 'recommendations'},
                            {'label': 'Take Action', 'target': 'carbon_footprint'}
                        ] if direction == 'increasing' else []
                    ))
        
        # Score trend insight
        if 'score_trend' in trend_data:
            score_trend = trend_data['score_trend']
            direction = score_trend['direction']
            
            if direction == 'improving' and abs(score_trend['percent_change']) > 5:
                insights.append(Insight(
                    id=f"score_improvement_{self._generated_count + len(insights)}",
                    type='positive',
                    title='⭐ Eco Score Improving!',
                    description=f"Your Eco Score has improved by {abs(score_trend['percent_change']):.1f}%. You're making great progress!",
                    priority='high',
                    category='trend',
                    actionable=False,
                    metrics={
                        'change_percentage': abs(score_trend['percent_change']),
                        'direction': direction
                    }
                ))
        
        return insights
    
    def _generate_anomaly_insights(self, analytics_data: Dict[str, Any]) -> List[Insight]:
        """Generate insights from anomaly detection."""
        insights = []
        
        if 'anomalies' not in analytics_data:
            return insights
        
        anomaly_data = analytics_data['anomalies']
        
        if anomaly_data.get('anomaly_count', 0) > 0:
            anomalies = anomaly_data['anomalies'][:3]
            
            for anomaly in anomalies:
                insights.append(Insight(
                    id=f"anomaly_{anomaly['date']}_{self._generated_count + len(insights)}",
                    type='warning',
                    title='⚠️ Unusual Pattern Detected',
                    description=f"On {anomaly['date']}, your footprint was {abs(anomaly['deviation']):.1f} kg CO₂ {'above' if anomaly['deviation'] > 0 else 'below'} your average.",
                    priority='medium',
                    category='anomaly',
                    actionable=True,
                    metrics={
                        'date': anomaly['date'],
                        'deviation': anomaly['deviation'],
                        'z_score': anomaly['z_score'],
                        'value': anomaly['value']
                    },
                    action_links=[
                        {'label': 'Review This Date', 'target': 'history'},
                        {'label': 'Learn More', 'target': 'analytics'}
                    ] if anomaly['deviation'] > 0 else []
                ))
            
            if anomaly_data['anomaly_count'] > 3:
                insights.append(Insight(
                    id=f"anomaly_summary_{self._generated_count + len(insights)}",
                    type='info',
                    title=f"📊 {anomaly_data['anomaly_count']} Anomalies Detected",
                    description=f"Found {anomaly_data['anomaly_count']} unusual patterns in your data. Review your assessment history for details.",
                    priority='low',
                    category='anomaly',
                    actionable=True,
                    metrics={'count': anomaly_data['anomaly_count']},
                    action_links=[
                        {'label': 'View All Anomalies', 'target': 'analytics'}
                    ]
                ))
        
        return insights
    
    def _generate_achievement_insights(
        self, 
        assessments: List[Dict[str, Any]], 
        analytics_data: Dict[str, Any]
    ) -> List[Insight]:
        """Generate achievement-based insights."""
        insights = []
        
        if not assessments:
            return insights
        
        # Streak achievement
        if len(assessments) >= 3:
            # Check if assessments are consecutive
            dates = [datetime.fromisoformat(a.get('date', '')) if isinstance(a.get('date'), str) else a.get('date', datetime.now()) for a in assessments]
            dates = sorted([d for d in dates if d])
            
            if len(dates) >= 3:
                streak = 1
                for i in range(1, len(dates)):
                    diff = (dates[i] - dates[i-1]).days
                    if diff <= 7:  # Within a week
                        streak += 1
                    else:
                        break
                
                if streak >= 5:
                    insights.append(Insight(
                        id=f"streak_{streak}_{self._generated_count + len(insights)}",
                        type='achievement',
                        title=f'🔥 {streak} Week Streak!',
                        description=f"You've maintained a {streak} week streak of consistent assessments. Keep going to build sustainable habits!",
                        priority='high',
                        category='achievement',
                        actionable=False,
                        metrics={'streak': streak}
                    ))
        
        # Improvement achievement
        if 'progress_metrics' in analytics_data:
            progress = analytics_data['progress_metrics']
            if 'total_footprint_reduction' in progress:
                reduction = progress['total_footprint_reduction']
                if reduction['percentage'] > 10:
                    insights.append(Insight(
                        id=f"improvement_{int(reduction['percentage'])}_{self._generated_count + len(insights)}",
                        type='achievement',
                        title=f'📈 {int(reduction["percentage"])}% Reduction!',
                        description=f"You've reduced your carbon footprint by {reduction['percentage']:.1f}%! This is a significant achievement.",
                        priority='high',
                        category='achievement',
                        actionable=False,
                        metrics={
                            'percentage': reduction['percentage'],
                            'absolute': reduction['absolute']
                        }
                    ))
        
        # Milestone achievement
        footprint_avg = np.mean([a.get('footprint', 0) for a in assessments if a.get('footprint') is not None])
        
        milestones = [
            (1000, '💚 1000 kg CO₂', '2000 kg CO₂'),
            (2000, '🌱 2000 kg CO₂', '1000 kg CO₂'),
            (3000, '🌿 3000 kg CO₂', '2000 kg CO₂'),
            (5000, '🌳 5000 kg CO₂', '3000 kg CO₂')
        ]
        
        for threshold, milestone, next_milestone in milestones:
            if footprint_avg < threshold:
                insights.append(Insight(
                    id=f"milestone_{threshold}_{self._generated_count + len(insights)}",
                    type='achievement',
                    title=f'🏆 {milestone}',
                    description=f"You've reached the {milestone} milestone! {next_milestone} is your next goal.",
                    priority='high' if footprint_avg < threshold else 'low',
                    category='achievement',
                    actionable=False,
                    metrics={'threshold': threshold, 'current': footprint_avg}
                ))
                break
        
        return insights
    
    def _generate_recommendation_insights(
        self, 
        assessments: List[Dict[str, Any]], 
        analytics_data: Dict[str, Any]
    ) -> List[Insight]:
        """Generate recommendation insights."""
        insights = []
        
        if not assessments:
            return insights
        
        # Get latest assessment
        latest = assessments[0] if assessments else {}
        
        # Transport recommendation
        transport = latest.get('transport', '').lower()
        if transport in ['car', 'taxi']:
            savings = latest.get('footprint', 0) * 0.15  # 15% reduction potential
            insights.append(Insight(
                id=f"rec_transport_{self._generated_count + len(insights)}",
                type='suggestion',
                title=self._insight_templates['recommendation']['transport']['title'],
                description=self._insight_templates['recommendation']['transport']['description'].format(savings=savings),
                priority='high',
                category='recommendation',
                actionable=True,
                metrics={'savings': savings, 'current_mode': transport},
                action_links=[
                    {'label': 'View Transport Options', 'target': 'route_planning'},
                    {'label': 'Calculate Impact', 'target': 'carbon_footprint'}
                ]
            ))
        
        # Energy recommendation
        electricity = latest.get('electricity', 0)
        if electricity > 200:
            savings = electricity * 0.1  # 10% reduction potential
            insights.append(Insight(
                id=f"rec_energy_{self._generated_count + len(insights)}",
                type='suggestion',
                title=self._insight_templates['recommendation']['energy']['title'],
                description=self._insight_templates['recommendation']['energy']['description'].format(savings=savings),
                priority='medium',
                category='recommendation',
                actionable=True,
                metrics={'savings': savings, 'current_usage': electricity},
                action_links=[
                    {'label': 'Energy Audit', 'target': 'home_energy'},
                    {'label': 'Energy Tips', 'target': 'analytics'}
                ]
            ))
        
        # Diet recommendation
        diet = latest.get('diet', '').lower()
        if diet == 'non-vegetarian':
            savings = latest.get('footprint', 0) * 0.12  # 12% reduction potential
            insights.append(Insight(
                id=f"rec_diet_{self._generated_count + len(insights)}",
                type='suggestion',
                title=self._insight_templates['recommendation']['diet']['title'],
                description=self._insight_templates['recommendation']['diet']['description'].format(savings=savings),
                priority='medium',
                category='recommendation',
                actionable=True,
                metrics={'savings': savings, 'current_diet': diet},
                action_links=[
                    {'label': 'Learn More', 'target': 'learning_center'},
                    {'label': 'Try Plant-Based', 'target': 'carbon_footprint'}
                ]
            ))
        
        # Flight recommendation
        flights = latest.get('flights', 0)
        if flights > 2:
            savings = flights * 50  # 50kg per flight reduction
            insights.append(Insight(
                id=f"rec_flights_{self._generated_count + len(insights)}",
                type='suggestion',
                title=self._insight_templates['recommendation']['flights']['title'],
                description=self._insight_templates['recommendation']['flights']['description'].format(savings=savings),
                priority='high',
                category='recommendation',
                actionable=True,
                metrics={'savings': savings, 'current_flights': flights},
                action_links=[
                    {'label': 'Offset Flights', 'target': 'route_planning'},
                    {'label': 'Alternatives', 'target': 'travel_planner'}
                ]
            ))
        
        return insights
    
    def _generate_forecast_insights(self, analytics_data: Dict[str, Any]) -> List[Insight]:
        """Generate forecast insights."""
        insights = []
        
        if 'forecasts' not in analytics_data:
            return insights
        
        forecast_data = analytics_data['forecasts']
        
        if '30_days' in forecast_data:
            forecast = forecast_data['30_days']
            direction = forecast.get('trend_direction', 'stable')
            change = abs(forecast.get('average_change', 0))
            
            if direction == 'decreasing' and change > 5:
                insights.append(Insight(
                    id=f"forecast_positive_{self._generated_count + len(insights)}",
                    type='positive',
                    title=self._insight_templates['forecast']['positive']['title'],
                    description=self._insight_templates['forecast']['positive']['description'].format(
                        change=change,
                        days=30
                    ),
                    priority='medium',
                    category='forecast',
                    actionable=False,
                    metrics={'change': change, 'days': 30, 'direction': direction}
                ))
            elif direction == 'increasing' and change > 5:
                insights.append(Insight(
                    id=f"forecast_warning_{self._generated_count + len(insights)}",
                    type='warning',
                    title=self._insight_templates['forecast']['warning']['title'],
                    description=self._insight_templates['forecast']['warning']['description'].format(
                        change=change,
                        days=30
                    ),
                    priority='medium',
                    category='forecast',
                    actionable=True,
                    metrics={'change': change, 'days': 30, 'direction': direction},
                    action_links=[
                        {'label': 'View Full Forecast', 'target': 'analytics'},
                        {'label': 'Take Action', 'target': 'carbon_footprint'}
                    ]
                ))
        
        return insights
    
    def _generate_consistency_insights(
        self, 
        assessments: List[Dict[str, Any]], 
        analytics_data: Dict[str, Any]
    ) -> List[Insight]:
        """Generate consistency insights."""
        insights = []
        
        if 'progress_metrics' not in analytics_data:
            return insights
        
        progress = analytics_data['progress_metrics']
        
        if 'consistency' in progress:
            consistency = progress['consistency']
            score = consistency.get('score', 0)
            
            if score > 80:
                insights.append(Insight(
                    id=f"consistency_high_{self._generated_count + len(insights)}",
                    type='positive',
                    title='✅ Highly Consistent Habits',
                    description=f"Your habits are highly consistent (score: {score:.0f}/100). This stability is great for long-term sustainability.",
                    priority='medium',
                    category='consistency',
                    actionable=False,
                    metrics={'score': score}
                ))
            elif score < 40:
                insights.append(Insight(
                    id=f"consistency_low_{self._generated_count + len(insights)}",
                    type='warning',
                    title='⚠️ Inconsistent Habits Detected',
                    description=f"Your habits show significant variation (score: {score:.0f}/100). Consider building more consistent routines.",
                    priority='medium',
                    category='consistency',
                    actionable=True,
                    metrics={'score': score},
                    action_links=[
                        {'label': 'Build Routine', 'target': 'habit_tracker'},
                        {'label': 'Learn More', 'target': 'learning_center'}
                    ]
                ))
        
        return insights
    
    def _generate_comparison_insights(self, assessments: List[Dict[str, Any]]) -> List[Insight]:
        """Generate comparison insights."""
        insights = []
        
        if len(assessments) < 2:
            return insights
        
        # Compare best and worst
        best = min(assessments, key=lambda x: x.get('footprint', 0))
        worst = max(assessments, key=lambda x: x.get('footprint', 0))
        
        if best.get('footprint', 0) > 0 and worst.get('footprint', 0) > 0:
            difference = worst['footprint'] - best['footprint']
            
            if difference > 100:
                insights.append(Insight(
                    id=f"comparison_best_vs_worst_{self._generated_count + len(insights)}",
                    type='info',
                    title='📊 Your Best vs Worst Performance',
                    description=f"Your best assessment was {best['footprint']:.0f} kg CO₂, while your worst was {worst['footprint']:.0f} kg CO₂. That's a difference of {difference:.0f} kg CO₂!",
                    priority='medium',
                    category='info',
                    actionable=True,
                    metrics={
                        'best': best['footprint'],
                        'worst': worst['footprint'],
                        'difference': difference
                    },
                    action_links=[
                        {'label': 'View Best Assessment', 'target': 'history'},
                        {'label': 'Learn From Worst', 'target': 'analytics'}
                    ]
                ))
        
        return insights
    
    def _generate_milestone_insights(self, assessments: List[Dict[str, Any]]) -> List[Insight]:
        """Generate milestone insights."""
        insights = []
        
        total_assessments = len(assessments)
        
        milestones = [10, 25, 50, 100, 250, 500]
        
        for milestone in milestones:
            if total_assessments >= milestone:
                # Check if not already generated
                if not any(f"assessment_count_{milestone}" in i.id for i in insights):
                    insights.append(Insight(
                        id=f"assessment_count_{milestone}_{self._generated_count + len(insights)}",
                        type='achievement',
                        title=f'🎯 {milestone} Assessments Completed!',
                        description=f"You've completed {milestone} assessments! This is an incredible achievement. Your commitment to sustainability is inspiring.",
                        priority='high',
                        category='achievement',
                        actionable=False,
                        metrics={'count': milestone}
                    ))
                break
        
        return insights
    
    def _generate_summary(self, insights: List[Insight]) -> Dict[str, Any]:
        """Generate summary of insights."""
        if not insights:
            return {
                'total': 0,
                'by_type': {},
                'by_priority': {},
                'by_category': {},
                'actionable_count': 0,
                'top_priority': None
            }
        
        summary = {
            'total': len(insights),
            'by_type': {},
            'by_priority': {},
            'by_category': {},
            'actionable_count': sum(1 for i in insights if i.actionable),
            'top_priority': None
        }
        
        for insight in insights:
            summary['by_type'][insight.type] = summary['by_type'].get(insight.type, 0) + 1
            summary['by_priority'][insight.priority] = summary['by_priority'].get(insight.priority, 0) + 1
            summary['by_category'][insight.category] = summary['by_category'].get(insight.category, 0) + 1
        
        # Find top priority
        for priority in ['high', 'medium', 'low']:
            if summary['by_priority'].get(priority, 0) > 0:
                summary['top_priority'] = priority
                break
        
        return summary
    
    def get_insight_history(self) -> List[Dict[str, Any]]:
        """Get insight generation history."""
        return self._insight_history
    
    def clear_history(self) -> None:
        """Clear insight history."""
        self._insight_history.clear()
    
    def get_insight_stats(self) -> Dict[str, Any]:
        """Get insight generation statistics."""
        return {
            'total_generated': self._generated_count,
            'total_history_entries': len(self._insight_history),
            'last_generated': self._insight_history[-1] if self._insight_history else None
        }


# Global insight generator instance
_insight_generator: Optional[InsightGenerator] = None


def get_insight_generator() -> InsightGenerator:
    """Get or create global insight generator instance."""
    global _insight_generator
    if _insight_generator is None:
        _insight_generator = InsightGenerator()
    return _insight_generator


def generate_insights(
    assessments: List[Dict[str, Any]],
    analytics_data: Dict[str, Any]
) -> InsightResult:
    """
    Convenience function to generate insights.
    
    Args:
        assessments: List of assessment dictionaries
        analytics_data: Analytics results
    
    Returns:
        InsightResult with generated insights
    """
    generator = get_insight_generator()
    return generator.generate_insights(assessments, analytics_data)