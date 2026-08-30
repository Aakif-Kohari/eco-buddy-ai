"""
Sustainability Behavior Intelligence - Consistency Analysis
Analyzes habit consistency and behavioral patterns.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from collections import defaultdict

from intelligence.models import ConsistencyScore, DataPoint, BehaviorTrend
from intelligence.trends import TrendDetector

logger = logging.getLogger(__name__)


class ConsistencyAnalyzer:
    """
    Analyzes consistency of habits and behaviors over time.
    """
    
    def __init__(self):
        """Initialize the consistency analyzer."""
        self.trend_detector = TrendDetector()
        logger.info("Consistency Analyzer initialized")
    
    def analyze_habits(self, habits: List[Dict[str, Any]]) -> Optional[ConsistencyScore]:
        """
        Analyze consistency of habits.
        
        Args:
            habits: List of habit data
        
        Returns:
            ConsistencyScore: Consistency analysis results
        """
        if not habits:
            return None
        
        # Aggregate habit data
        all_completions = []
        daily_completions = defaultdict(list)
        weekly_completions = defaultdict(list)
        monthly_completions = defaultdict(list)
        
        for habit in habits:
            completions = habit.get('completions', [])
            for completion in completions:
                date = completion.get('date')
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)
                
                if date:
                    all_completions.append(date)
                    day_key = date.strftime('%A')
                    week_key = date.isocalendar()[1]
                    month_key = date.strftime('%Y-%m')
                    
                    daily_completions[day_key].append(date)
                    weekly_completions[week_key].append(date)
                    monthly_completions[month_key].append(date)
        
        if not all_completions:
            return None
        
        # Calculate consistency scores
        consistency = ConsistencyScore(
            category=habits[0].get('category', ''),
            habit_name=habits[0].get('name', ''),
            completion_rate=self._calculate_completion_rate(all_completions, habits),
            weekly_consistency=self._calculate_weekly_consistency(weekly_completions),
            monthly_consistency=self._calculate_monthly_consistency(monthly_completions),
            current_streak=self._calculate_current_streak(all_completions),
            longest_streak=self._calculate_longest_streak(all_completions),
            missed_frequency=self._calculate_missed_frequency(all_completions, habits),
            weekly_patterns=self._calculate_weekly_patterns(daily_completions),
            monthly_patterns=self._calculate_monthly_patterns(monthly_completions)
        )
        
        # Find best and worst days
        if consistency.weekly_patterns:
            if consistency.weekly_patterns:
                consistency.best_day = max(
                    consistency.weekly_patterns,
                    key=consistency.weekly_patterns.get
                )
                consistency.worst_day = min(
                    consistency.weekly_patterns,
                    key=consistency.weekly_patterns.get
                )
        
        # Find best and worst months
        if consistency.monthly_patterns:
            consistency.best_month = max(
                consistency.monthly_patterns,
                key=consistency.monthly_patterns.get
            )
            consistency.worst_month = min(
                consistency.monthly_patterns,
                key=consistency.monthly_patterns.get
            )
        
        # Calculate overall consistency
        consistency.overall_consistency = (
            consistency.completion_rate * 0.4 +
            consistency.weekly_consistency * 0.3 +
            consistency.monthly_consistency * 0.3
        )
        
        # Calculate improvement score
        consistency.improvement_score = self._calculate_improvement_score(habits)
        
        # Generate recommendations
        consistency.recommendations = self._generate_recommendations(consistency)
        
        return consistency
    
    def calculate_habit_consistency(self, habit: Dict[str, Any]) -> Optional[ConsistencyScore]:
        """
        Calculate consistency for a single habit.
        
        Args:
            habit: Habit data
        
        Returns:
            ConsistencyScore: Consistency analysis
        """
        return self.analyze_habits([habit])
    
    def _calculate_completion_rate(self, completions: List[datetime], 
                                  habits: List[Dict[str, Any]]) -> float:
        """
        Calculate overall completion rate.
        """
        if not habits:
            return 0
        
        total_expected = sum(habit.get('frequency', 1) for habit in habits)
        if total_expected == 0:
            return 0
        
        total_completions = len(completions)
        return min(100.0, (total_completions / total_expected) * 100)
    
    def _calculate_weekly_consistency(self, 
                                     weekly_completions: Dict[int, List[datetime]]) -> float:
        """
        Calculate weekly consistency score.
        """
        if not weekly_completions:
            return 0
        
        weekly_counts = [len(completions) for completions in weekly_completions.values()]
        if len(weekly_counts) < 2:
            return weekly_counts[0] * 10 if weekly_counts else 0
        
        # Calculate coefficient of variation (lower = more consistent)
        mean = statistics.mean(weekly_counts)
        if mean == 0:
            return 0
        
        stdev = statistics.stdev(weekly_counts) if len(weekly_counts) > 1 else 0
        cv = stdev / mean
        
        # Convert to consistency score (0-100)
        return max(0, 100 - (cv * 100))
    
    def _calculate_monthly_consistency(self, 
                                      monthly_completions: Dict[str, List[datetime]]) -> float:
        """
        Calculate monthly consistency score.
        """
        if not monthly_completions:
            return 0
        
        monthly_counts = [len(completions) for completions in monthly_completions.values()]
        if len(monthly_counts) < 2:
            return monthly_counts[0] * 10 if monthly_counts else 0
        
        # Calculate coefficient of variation
        mean = statistics.mean(monthly_counts)
        if mean == 0:
            return 0
        
        stdev = statistics.stdev(monthly_counts) if len(monthly_counts) > 1 else 0
        cv = stdev / mean
        
        # Convert to consistency score
        return max(0, 100 - (cv * 100))
    
    def _calculate_current_streak(self, completions: List[datetime]) -> int:
        """
        Calculate current streak of completions.
        """
        if not completions:
            return 0
        
        sorted_dates = sorted(completions, reverse=True)
        streak = 0
        expected_date = datetime.now().date()
        
        for date in sorted_dates:
            date_obj = date.date() if isinstance(date, datetime) else date
            if date_obj == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            elif date_obj < expected_date:
                break
        
        return streak
    
    def _calculate_longest_streak(self, completions: List[datetime]) -> int:
        """
        Calculate longest streak of completions.
        """
        if not completions:
            return 0
        
        sorted_dates = sorted(completions)
        max_streak = 0
        current_streak = 1
        
        for i in range(1, len(sorted_dates)):
            date1 = sorted_dates[i-1].date() if isinstance(sorted_dates[i-1], datetime) else sorted_dates[i-1]
            date2 = sorted_dates[i].date() if isinstance(sorted_dates[i], datetime) else sorted_dates[i]
            
            if (date2 - date1).days == 1:
                current_streak += 1
            else:
                max_streak = max(max_streak, current_streak)
                current_streak = 1
        
        max_streak = max(max_streak, current_streak)
        return max_streak
    
    def _calculate_missed_frequency(self, completions: List[datetime], 
                                   habits: List[Dict[str, Any]]) -> float:
        """
        Calculate frequency of missed completions.
        """
        if not habits:
            return 0
        
        # Determine total expected completions
        total_expected = sum(habit.get('frequency', 1) for habit in habits)
        total_completions = len(completions)
        
        missed = total_expected - total_completions
        if missed <= 0:
            return 0
        
        # Calculate days since first completion
        if completions:
            first_date = min(completions)
            days_active = (datetime.now() - first_date).days
            if days_active > 0:
                return (missed / days_active) * 7  # Missed per week
        
        return 0
    
    def _calculate_weekly_patterns(self, 
                                  daily_completions: Dict[str, List[datetime]]) -> Dict[str, float]:
        """
        Calculate completion patterns by day of week.
        """
        patterns = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in days:
            completions = daily_completions.get(day, [])
            if completions:
                # Calculate completion rate for this day
                total_days = len(set(d.date() for d in completions if isinstance(d, datetime)))
                patterns[day] = (len(completions) / total_days * 100) if total_days > 0 else 0
            else:
                patterns[day] = 0
        
        return patterns
    
    def _calculate_monthly_patterns(self, 
                                   monthly_completions: Dict[str, List[datetime]]) -> Dict[str, float]:
        """
        Calculate completion patterns by month.
        """
        patterns = {}
        
        for month, completions in monthly_completions.items():
            if completions:
                total_days = len(set(d.date() for d in completions if isinstance(d, datetime)))
                patterns[month] = (len(completions) / total_days * 100) if total_days > 0 else 0
            else:
                patterns[month] = 0
        
        return patterns
    
    def _calculate_improvement_score(self, habits: List[Dict[str, Any]]) -> float:
        """
        Calculate improvement score for habits over time.
        """
        if not habits:
            return 0
        
        # Track completion rates over time
        time_series = []
        
        for habit in habits:
            completions = habit.get('completions', [])
            if not completions:
                continue
            
            # Group completions by month
            monthly_counts = defaultdict(int)
            for completion in completions:
                date = completion.get('date')
                if isinstance(date, str):
                    date = datetime.fromisoformat(date)
                
                if date:
                    month_key = date.strftime('%Y-%m')
                    monthly_counts[month_key] += 1
            
            # Convert to time series
            sorted_months = sorted(monthly_counts.keys())
            for i, month in enumerate(sorted_months):
                time_series.append({
                    'period': i,
                    'value': monthly_counts[month]
                })
        
        if len(time_series) < 3:
            return 0
        
        # Calculate trend using linear regression
        periods = [ts['period'] for ts in time_series]
        values = [ts['value'] for ts in time_series]
        
        # Simple linear regression
        n = len(periods)
        x_sum = sum(periods)
        y_sum = sum(values)
        xy_sum = sum(p * v for p, v in zip(periods, values))
        x2_sum = sum(p ** 2 for p in periods)
        
        if n * x2_sum - x_sum ** 2 == 0:
            return 0
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum ** 2)
        
        # Normalize to -1 to 1
        max_change = max(values) - min(values) if max(values) > min(values) else 1
        normalized_slope = slope / (max_change / len(values)) if max_change > 0 else 0
        
        return max(-1, min(1, normalized_slope))
    
    def _generate_recommendations(self, consistency: ConsistencyScore) -> List[str]:
        """
        Generate recommendations based on consistency analysis.
        """
        recommendations = []
        
        if consistency.completion_rate < 50:
            recommendations.append(
                f"Your completion rate for '{consistency.habit_name}' is low ({consistency.completion_rate:.1f}%). "
                f"Try setting smaller, more achievable goals to build momentum."
            )
        
        if consistency.weekly_consistency < 60:
            recommendations.append(
                f"Your weekly consistency for '{consistency.habit_name}' needs improvement. "
                f"Try to maintain a regular schedule throughout the week."
            )
        
        if consistency.overall_consistency < 50:
            recommendations.append(
                f"Overall consistency for '{consistency.habit_name}' is low. "
                f"Consider using reminders or habit tracking apps to stay on track."
            )
        
        if consistency.best_day and consistency.worst_day:
            recommendations.append(
                f"You're most consistent on {consistency.best_day}s and least consistent on {consistency.worst_day}s. "
                f"Try to find ways to make {consistency.worst_day}s more productive."
            )
        
        if consistency.current_streak == 0:
            recommendations.append(
                f"Your streak for '{consistency.habit_name}' has been broken. "
                f"Start fresh today and aim for a new streak!"
            )
        elif consistency.current_streak < 7:
            recommendations.append(
                f"You have a {consistency.current_streak}-day streak for '{consistency.habit_name}'. "
                f"Keep going to reach a full week!"
            )
        elif consistency.current_streak >= 30:
            recommendations.append(
                f"Amazing! You have a {consistency.current_streak}-day streak for '{consistency.habit_name}'. "
                f"You've built a strong habit!"
            )
        
        return recommendations