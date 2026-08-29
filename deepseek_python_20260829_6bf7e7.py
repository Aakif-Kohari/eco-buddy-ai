"""
Sustainability Experiment & Habit A/B Testing Lab - Analytics
Analytics and history for experiments.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict

from experiments.models import (
    SustainabilityExperiment, ExperimentHistory, ExperimentStatus,
    ExperimentOutcome, ExperimentCategory
)

logger = logging.getLogger(__name__)


class ExperimentAnalytics:
    """
    Analytics for experiment data.
    """
    
    def __init__(self):
        """Initialize the analytics engine."""
        logger.info("Experiment Analytics initialized")
    
    def analyze_user_experiments(self, 
                                experiments: List[SustainabilityExperiment],
                                user_id: str) -> ExperimentHistory:
        """
        Analyze a user's experiment history.
        
        Args:
            experiments: List of experiments
            user_id: User ID
        
        Returns:
            ExperimentHistory: History analysis
        """
        history = ExperimentHistory(
            user_id=user_id,
            experiments=experiments
        )
        
        # Basic statistics
        history.total_experiments = len(experiments)
        history.completed_experiments = sum(1 for e in experiments if e.status == ExperimentStatus.COMPLETED)
        
        # Success statistics
        successful = [e for e in experiments if e.status == ExperimentStatus.COMPLETED 
                     and e.evaluation and e.evaluation.outcome == ExperimentOutcome.SUCCESSFUL]
        partially = [e for e in experiments if e.status == ExperimentStatus.COMPLETED 
                    and e.evaluation and e.evaluation.outcome == ExperimentOutcome.PARTIALLY_SUCCESSFUL]
        unsuccessful = [e for e in experiments if e.status == ExperimentStatus.COMPLETED 
                       and e.evaluation and e.evaluation.outcome == ExperimentOutcome.UNSUCCESSFUL]
        
        history.successful_experiments = len(successful)
        history.partially_successful = len(partially)
        history.unsuccessful_experiments = len(unsuccessful)
        
        # Success rates
        completed = history.completed_experiments
        if completed > 0:
            history.success_rate = (history.successful_experiments / completed) * 100
            history.partial_success_rate = (history.partially_successful / completed) * 100
        
        # Aggregate impact
        for experiment in experiments:
            if experiment.effectiveness:
                history.total_carbon_saved += experiment.effectiveness.carbon_reduction_kg
                history.total_water_saved += experiment.effectiveness.water_savings_liters
                history.total_waste_reduced += experiment.effectiveness.waste_reduction_kg
                history.total_cost_saved += experiment.effectiveness.cost_savings
        
        # Category breakdown
        category_breakdown = defaultdict(int)
        for experiment in experiments:
            category_breakdown[experiment.category.value] += 1
        history.category_breakdown = dict(category_breakdown)
        
        # Category success rates
        category_success = defaultdict(list)
        for experiment in experiments:
            if experiment.status == ExperimentStatus.COMPLETED and experiment.evaluation:
                if experiment.evaluation.outcome == ExperimentOutcome.SUCCESSFUL:
                    category_success[experiment.category.value].append(1)
                else:
                    category_success[experiment.category.value].append(0)
        
        category_success_rates = {}
        for category, outcomes in category_success.items():
            if outcomes:
                category_success_rates[category] = (sum(outcomes) / len(outcomes)) * 100
        
        history.category_success_rates = category_success_rates
        
        history.updated_at = datetime.now()
        
        return history
    
    def get_experiment_trends(self, 
                            experiments: List[SustainabilityExperiment]) -> Dict[str, Any]:
        """
        Get trends across experiments.
        
        Args:
            experiments: List of experiments
        
        Returns:
            Dict: Trend analysis
        """
        if not experiments:
            return {'message': 'No experiments to analyze'}
        
        # Sort by date
        sorted_experiments = sorted(experiments, key=lambda e: e.created_at)
        
        # Track metrics over time
        dates = []
        scores = []
        carbon_savings = []
        cost_savings = []
        
        for exp in sorted_experiments:
            dates.append(exp.created_at.strftime('%Y-%m'))
            if exp.effectiveness:
                scores.append(exp.effectiveness.overall_score)
                carbon_savings.append(exp.effectiveness.carbon_reduction_kg)
                cost_savings.append(exp.effectiveness.cost_savings)
        
        # Calculate trends
        score_trend = self._calculate_trend(scores) if scores else 0
        carbon_trend = self._calculate_trend(carbon_savings) if carbon_savings else 0
        cost_trend = self._calculate_trend(cost_savings) if cost_savings else 0
        
        return {
            'dates': dates,
            'scores': scores,
            'carbon_savings': carbon_savings,
            'cost_savings': cost_savings,
            'score_trend': score_trend,
            'carbon_trend': carbon_trend,
            'cost_trend': cost_trend,
            'overall_trend': 'improving' if score_trend > 0 else 'declining'
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """
        Calculate simple trend from values.
        """
        if len(values) < 2:
            return 0
        
        # Linear regression slope
        n = len(values)
        x = list(range(n))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0
        
        return numerator / denominator
    
    def get_category_performance(self, 
                                experiments: List[SustainabilityExperiment]) -> Dict[str, Any]:
        """
        Get performance by category.
        
        Args:
            experiments: List of experiments
        
        Returns:
            Dict: Category performance
        """
        category_data = defaultdict(lambda: {'count': 0, 'scores': [], 'success_rate': 0})
        
        for exp in experiments:
            category_data[exp.category.value]['count'] += 1
            if exp.effectiveness:
                category_data[exp.category.value]['scores'].append(exp.effectiveness.overall_score)
        
        # Calculate averages
        for category, data in category_data.items():
            if data['scores']:
                data['avg_score'] = statistics.mean(data['scores'])
            else:
                data['avg_score'] = 0
        
        return dict(category_data)
    
    def get_success_patterns(self, 
                            experiments: List[SustainabilityExperiment]) -> Dict[str, Any]:
        """
        Identify patterns in successful experiments.
        
        Args:
            experiments: List of experiments
        
        Returns:
            Dict: Success patterns
        """
        successful = [e for e in experiments if e.status == ExperimentStatus.COMPLETED 
                     and e.evaluation and e.evaluation.outcome == ExperimentOutcome.SUCCESSFUL]
        
        if not successful:
            return {'message': 'No successful experiments to analyze'}
        
        patterns = {
            'average_duration_days': statistics.mean([e.experiment_duration_days for e in successful]),
            'average_baseline_days': statistics.mean([e.baseline_duration_days for e in successful]),
            'common_categories': self._get_common_categories(successful),
            'common_metrics': self._get_common_metrics(successful),
            'avg_improvement': statistics.mean([e.effectiveness.percentage_improvement for e in successful if e.effectiveness]),
            'avg_carbon_saved': statistics.mean([e.effectiveness.carbon_reduction_kg for e in successful if e.effectiveness])
        }
        
        return patterns
    
    def _get_common_categories(self, experiments: List[SustainabilityExperiment]) -> List[str]:
        """
        Get most common categories in a list of experiments.
        """
        counts = defaultdict(int)
        for exp in experiments:
            counts[exp.category.value] += 1
        
        sorted_categories = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_categories[:3]]
    
    def _get_common_metrics(self, experiments: List[SustainabilityExperiment]) -> List[str]:
        """
        Get most common target metrics.
        """
        counts = defaultdict(int)
        for exp in experiments:
            for metric in exp.target_metrics:
                counts[metric.value] += 1
        
        sorted_metrics = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [metric for metric, _ in sorted_metrics[:5]]
    
    def get_impact_summary(self, history: ExperimentHistory) -> Dict[str, Any]:
        """
        Get summary of impact from experiment history.
        
        Args:
            history: Experiment history
        
        Returns:
            Dict: Impact summary
        """
        return {
            'total_experiments': history.total_experiments,
            'success_rate': history.success_rate,
            'total_carbon_saved_kg': history.total_carbon_saved,
            'total_water_saved_liters': history.total_water_saved,
            'total_waste_reduced_kg': history.total_waste_reduced,
            'total_cost_saved': history.total_cost_saved,
            'average_score': self._calculate_average_score(history),
            'monthly_impact_kg': history.total_carbon_saved / 12 if history.total_carbon_saved > 0 else 0,
            'yearly_impact_kg': history.total_carbon_saved,
            'grade': self._get_impact_grade(history)
        }
    
    def _calculate_average_score(self, history: ExperimentHistory) -> float:
        """
        Calculate average effectiveness score.
        """
        scores = []
        for exp in history.experiments:
            if exp.effectiveness:
                scores.append(exp.effectiveness.overall_score)
        
        if scores:
            return statistics.mean(scores)
        return 0
    
    def _get_impact_grade(self, history: ExperimentHistory) -> str:
        """
        Get impact grade.
        """
        if history.total_carbon_saved > 1000:
            return "Excellent"
        elif history.total_carbon_saved > 500:
            return "Good"
        elif history.total_carbon_saved > 100:
            return "Fair"
        elif history.total_carbon_saved > 0:
            return "Poor"
        else:
            return "Needs Improvement"