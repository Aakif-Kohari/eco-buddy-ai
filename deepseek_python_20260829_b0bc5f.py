"""
Sustainability Experiment & Habit A/B Testing Lab - Effectiveness Analysis
Analyzes experiment effectiveness and impact.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from experiments.models import (
    SustainabilityExperiment, EffectivenessResult, ExperimentComparison,
    ExperimentMeasurement, TargetMetric
)

logger = logging.getLogger(__name__)


class EffectivenessAnalyzer:
    """
    Analyzes effectiveness of experiments.
    """
    
    def __init__(self):
        """Initialize the effectiveness analyzer."""
        self.effectiveness_thresholds = {
            'excellent': 80,
            'good': 60,
            'fair': 40,
            'poor': 20
        }
        logger.info("Effectiveness Analyzer initialized")
    
    def calculate_effectiveness(self, 
                               experiment: SustainabilityExperiment) -> Optional[EffectivenessResult]:
        """
        Calculate effectiveness of an experiment.
        
        Args:
            experiment: The experiment
        
        Returns:
            Optional[EffectivenessResult]: Effectiveness results
        """
        if not experiment.comparison:
            logger.warning("Comparison required for effectiveness analysis")
            return None
        
        comparison = experiment.comparison
        
        result = EffectivenessResult(
            experiment_id=experiment.id
        )
        
        # Calculate component effectiveness scores
        result.environmental_effectiveness = self._calculate_environmental_effectiveness(comparison)
        result.financial_effectiveness = self._calculate_financial_effectiveness(comparison)
        result.behavioral_effectiveness = self._calculate_behavioral_effectiveness(comparison)
        
        # Calculate overall score
        result.overall_score = (
            result.environmental_effectiveness * 0.4 +
            result.financial_effectiveness * 0.3 +
            result.behavioral_effectiveness * 0.3
        )
        
        # Determine grade
        result.effectiveness_grade = self._get_grade(result.overall_score)
        
        # Calculate impact metrics
        result.absolute_improvement = self._calculate_absolute_improvement(comparison)
        result.percentage_improvement = self._calculate_percentage_improvement(comparison)
        result.improvement_rate = self._calculate_improvement_rate(experiment)
        
        # Project impact
        result.monthly_impact = self._project_monthly_impact(experiment)
        result.yearly_impact = result.monthly_impact * 12
        
        # Calculate carbon reductions
        result.carbon_reduction_kg = self._calculate_carbon_reduction(comparison)
        result.water_savings_liters = self._calculate_water_savings(comparison)
        result.waste_reduction_kg = self._calculate_waste_reduction(comparison)
        result.cost_savings = self._calculate_cost_savings(comparison)
        
        # Generate recommendation
        result.recommendation = self._generate_recommendation(result)
        result.confidence = self._calculate_confidence(experiment)
        
        experiment.effectiveness = result
        experiment.updated_at = datetime.now()
        
        logger.info(f"Calculated effectiveness for experiment {experiment.name}")
        return result
    
    def _calculate_environmental_effectiveness(self, comparison: ExperimentComparison) -> float:
        """
        Calculate environmental effectiveness score.
        """
        scores = []
        
        # Carbon reduction
        if comparison.carbon_change_percentage < 0:
            carbon_score = min(100, abs(comparison.carbon_change_percentage) * 2)
            scores.append(carbon_score)
        
        # Energy reduction
        if comparison.energy_change_percentage < 0:
            energy_score = min(100, abs(comparison.energy_change_percentage) * 2)
            scores.append(energy_score)
        
        # Water reduction
        if comparison.water_change_percentage < 0:
            water_score = min(100, abs(comparison.water_change_percentage) * 2)
            scores.append(water_score)
        
        # Waste reduction
        if comparison.waste_change_percentage < 0:
            waste_score = min(100, abs(comparison.waste_change_percentage) * 2)
            scores.append(waste_score)
        
        if scores:
            return statistics.mean(scores)
        
        return 50.0  # Neutral score
    
    def _calculate_financial_effectiveness(self, comparison: ExperimentComparison) -> float:
        """
        Calculate financial effectiveness score.
        """
        scores = []
        
        # Cost reduction
        if comparison.cost_change_percentage < 0:
            cost_score = min(100, abs(comparison.cost_change_percentage) * 2)
            scores.append(cost_score)
        
        # Cost savings value
        if comparison.cost_difference < -10:
            savings_score = min(100, abs(comparison.cost_difference) * 5)
            scores.append(savings_score)
        
        if scores:
            return statistics.mean(scores)
        
        return 50.0
    
    def _calculate_behavioral_effectiveness(self, comparison: ExperimentComparison) -> float:
        """
        Calculate behavioral effectiveness score.
        """
        scores = []
        
        # Habit completion improvement
        if comparison.habit_completion_change_percentage > 0:
            habit_score = min(100, comparison.habit_completion_change_percentage * 2)
            scores.append(habit_score)
        
        # Sustainability score improvement
        if comparison.sustainability_change_percentage > 0:
            sust_score = min(100, comparison.sustainability_change_percentage * 2)
            scores.append(sust_score)
        
        if scores:
            return statistics.mean(scores)
        
        return 50.0
    
    def _get_grade(self, score: float) -> str:
        """
        Get grade based on score.
        """
        if score >= self.effectiveness_thresholds['excellent']:
            return "A"
        elif score >= self.effectiveness_thresholds['good']:
            return "B"
        elif score >= self.effectiveness_thresholds['fair']:
            return "C"
        elif score >= self.effectiveness_thresholds['poor']:
            return "D"
        else:
            return "F"
    
    def _calculate_absolute_improvement(self, comparison: ExperimentComparison) -> float:
        """
        Calculate absolute improvement across all metrics.
        """
        improvements = []
        
        # Carbon improvement (reduction is positive)
        if comparison.carbon_change_percentage < 0:
            improvements.append(abs(comparison.carbon_change_percentage))
        
        # Energy improvement
        if comparison.energy_change_percentage < 0:
            improvements.append(abs(comparison.energy_change_percentage))
        
        # Water improvement
        if comparison.water_change_percentage < 0:
            improvements.append(abs(comparison.water_change_percentage))
        
        # Waste improvement
        if comparison.waste_change_percentage < 0:
            improvements.append(abs(comparison.waste_change_percentage))
        
        # Habit improvement
        if comparison.habit_completion_change_percentage > 0:
            improvements.append(comparison.habit_completion_change_percentage)
        
        # Sustainability improvement
        if comparison.sustainability_change_percentage > 0:
            improvements.append(comparison.sustainability_change_percentage)
        
        if improvements:
            return statistics.mean(improvements)
        
        return 0.0
    
    def _calculate_percentage_improvement(self, comparison: ExperimentComparison) -> float:
        """
        Calculate percentage improvement across all metrics.
        """
        # Average of all positive improvements
        positive_changes = []
        
        if comparison.carbon_change_percentage < 0:
            positive_changes.append(abs(comparison.carbon_change_percentage))
        if comparison.energy_change_percentage < 0:
            positive_changes.append(abs(comparison.energy_change_percentage))
        if comparison.water_change_percentage < 0:
            positive_changes.append(abs(comparison.water_change_percentage))
        if comparison.waste_change_percentage < 0:
            positive_changes.append(abs(comparison.waste_change_percentage))
        if comparison.habit_completion_change_percentage > 0:
            positive_changes.append(comparison.habit_completion_change_percentage)
        if comparison.sustainability_change_percentage > 0:
            positive_changes.append(comparison.sustainability_change_percentage)
        
        if positive_changes:
            return statistics.mean(positive_changes)
        
        return 0.0
    
    def _calculate_improvement_rate(self, experiment: SustainabilityExperiment) -> float:
        """
        Calculate improvement rate per day.
        """
        if not experiment.comparison:
            return 0.0
        
        # Calculate improvement based on experiment duration
        duration_days = experiment.experiment_duration_days
        
        if duration_days == 0:
            return 0.0
        
        improvement = self._calculate_percentage_improvement(experiment.comparison)
        
        return improvement / duration_days
    
    def _project_monthly_impact(self, experiment: SustainabilityExperiment) -> float:
        """
        Project monthly impact.
        """
        if not experiment.comparison:
            return 0.0
        
        # Calculate daily impact and multiply by 30
        daily_carbon_savings = abs(experiment.comparison.carbon_difference / experiment.experiment_duration_days)
        monthly_impact = daily_carbon_savings * 30
        
        return monthly_impact
    
    def _calculate_carbon_reduction(self, comparison: ExperimentComparison) -> float:
        """
        Calculate carbon reduction.
        """
        if comparison.carbon_change_percentage < 0:
            return abs(comparison.carbon_difference)
        return 0.0
    
    def _calculate_water_savings(self, comparison: ExperimentComparison) -> float:
        """
        Calculate water savings.
        """
        if comparison.water_change_percentage < 0:
            return abs(comparison.water_difference)
        return 0.0
    
    def _calculate_waste_reduction(self, comparison: ExperimentComparison) -> float:
        """
        Calculate waste reduction.
        """
        if comparison.waste_change_percentage < 0:
            return abs(comparison.waste_difference)
        return 0.0
    
    def _calculate_cost_savings(self, comparison: ExperimentComparison) -> float:
        """
        Calculate cost savings.
        """
        if comparison.cost_change_percentage < 0:
            return abs(comparison.cost_difference)
        return 0.0
    
    def _generate_recommendation(self, result: EffectivenessResult) -> str:
        """
        Generate recommendation based on effectiveness.
        """
        if result.overall_score >= self.effectiveness_thresholds['excellent']:
            return "Excellent! This experiment is highly effective. Consider making it a permanent habit."
        elif result.overall_score >= self.effectiveness_thresholds['good']:
            return "Good effectiveness. Continue the practice and look for ways to optimize further."
        elif result.overall_score >= self.effectiveness_thresholds['fair']:
            return "Moderate effectiveness. Consider adjusting the approach or extending the experiment period."
        elif result.overall_score >= self.effectiveness_thresholds['poor']:
            return "Limited effectiveness. Review the approach and consider trying a different strategy."
        else:
            return "Not effective. Consider abandoning this approach and trying a different experiment."
    
    def _calculate_confidence(self, experiment: SustainabilityExperiment) -> float:
        """
        Calculate confidence in the results.
        """
        confidence = 50.0  # Base
        
        # More measurements = higher confidence
        measurement_count = len(experiment.measurements)
        if measurement_count >= 30:
            confidence += 20
        elif measurement_count >= 15:
            confidence += 10
        
        # Longer duration = higher confidence
        duration = experiment.get_duration_days()
        if duration >= 28:
            confidence += 20
        elif duration >= 14:
            confidence += 10
        
        # Stability of measurements
        if experiment.comparison:
            variance = self._calculate_variance(experiment)
            if variance < 10:
                confidence += 10
        
        return min(100, confidence)
    
    def _calculate_variance(self, experiment: SustainabilityExperiment) -> float:
        """
        Calculate variance of measurements.
        """
        values = [m.carbon_emissions for m in experiment.measurements]
        
        if len(values) < 2:
            return 100.0
        
        mean = statistics.mean(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        
        return variance