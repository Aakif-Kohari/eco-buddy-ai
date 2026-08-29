"""
Sustainability Experiment & Habit A/B Testing Lab - Comparison Analyzer
Compares baseline and experimental results.
"""

import logging
import statistics
from datetime import datetime
from typing import List, Optional, Dict, Any

from experiments.models import (
    SustainabilityExperiment, ExperimentComparison, ExperimentMeasurement,
    BaselineSnapshot, TargetMetric
)

logger = logging.getLogger(__name__)


class ComparisonAnalyzer:
    """
    Compares baseline and experimental periods.
    """
    
    def __init__(self):
        """Initialize the comparison analyzer."""
        logger.info("Comparison Analyzer initialized")
    
    def compare_experiment(self, 
                          experiment: SustainabilityExperiment) -> Optional[ExperimentComparison]:
        """
        Compare baseline and experimental periods.
        
        Args:
            experiment: The experiment
        
        Returns:
            Optional[ExperimentComparison]: Comparison results
        """
        if not experiment.baseline_snapshot:
            logger.warning("No baseline snapshot available")
            return None
        
        # Get experimental measurements
        exp_measurements = self._get_experimental_measurements(experiment)
        
        if len(exp_measurements) < 3:
            logger.warning(f"Insufficient experimental measurements: {len(exp_measurements)}")
            return None
        
        # Calculate experimental averages
        exp_avg = self._calculate_averages(exp_measurements)
        
        # Get baseline values
        baseline = experiment.baseline_snapshot
        
        # Create comparison
        comparison = ExperimentComparison(
            experiment_id=experiment.id
        )
        
        # Baseline values
        comparison.baseline_carbon = baseline.carbon_emissions_avg
        comparison.baseline_energy = baseline.energy_consumption_avg
        comparison.baseline_water = baseline.water_consumption_avg
        comparison.baseline_waste = baseline.waste_generation_avg
        comparison.baseline_cost = baseline.financial_cost_avg
        comparison.baseline_habit_completion = baseline.habit_completion_avg
        comparison.baseline_sustainability = baseline.sustainability_score_avg
        
        # Experimental values
        comparison.experiment_carbon = exp_avg.get('carbon_emissions', 0.0)
        comparison.experiment_energy = exp_avg.get('energy_consumption', 0.0)
        comparison.experiment_water = exp_avg.get('water_consumption', 0.0)
        comparison.experiment_waste = exp_avg.get('waste_generation', 0.0)
        comparison.experiment_cost = exp_avg.get('financial_cost', 0.0)
        comparison.experiment_habit_completion = exp_avg.get('habit_completion', 0.0)
        comparison.experiment_sustainability = exp_avg.get('sustainability_score', 0.0)
        
        # Calculate differences (absolute)
        comparison.carbon_difference = comparison.experiment_carbon - comparison.baseline_carbon
        comparison.energy_difference = comparison.experiment_energy - comparison.baseline_energy
        comparison.water_difference = comparison.experiment_water - comparison.baseline_water
        comparison.waste_difference = comparison.experiment_waste - comparison.baseline_waste
        comparison.cost_difference = comparison.experiment_cost - comparison.baseline_cost
        comparison.habit_completion_difference = (
            comparison.experiment_habit_completion - comparison.baseline_habit_completion
        )
        comparison.sustainability_difference = (
            comparison.experiment_sustainability - comparison.baseline_sustainability
        )
        
        # Calculate percentage changes
        comparison.carbon_change_percentage = self._calculate_percentage(
            comparison.carbon_difference, comparison.baseline_carbon
        )
        comparison.energy_change_percentage = self._calculate_percentage(
            comparison.energy_difference, comparison.baseline_energy
        )
        comparison.water_change_percentage = self._calculate_percentage(
            comparison.water_difference, comparison.baseline_water
        )
        comparison.waste_change_percentage = self._calculate_percentage(
            comparison.waste_difference, comparison.baseline_waste
        )
        comparison.cost_change_percentage = self._calculate_percentage(
            comparison.cost_difference, comparison.baseline_cost
        )
        comparison.habit_completion_change_percentage = self._calculate_percentage(
            comparison.habit_completion_difference, comparison.baseline_habit_completion
        )
        comparison.sustainability_change_percentage = self._calculate_percentage(
            comparison.sustainability_difference, comparison.baseline_sustainability
        )
        
        experiment.comparison = comparison
        experiment.updated_at = datetime.now()
        
        logger.info(f"Completed comparison for experiment {experiment.name}")
        return comparison
    
    def _get_experimental_measurements(self, 
                                      experiment: SustainabilityExperiment) -> List[ExperimentMeasurement]:
        """
        Get measurements from the experimental period.
        """
        if not experiment.experiment_start_date:
            return []
        
        return [
            m for m in experiment.measurements
            if m.measurement_date >= experiment.experiment_start_date
        ]
    
    def _calculate_averages(self, 
                           measurements: List[ExperimentMeasurement]) -> Dict[str, float]:
        """
        Calculate averages from measurements.
        """
        if not measurements:
            return {}
        
        n = len(measurements)
        
        return {
            'carbon_emissions': sum(m.carbon_emissions for m in measurements) / n,
            'energy_consumption': sum(m.energy_consumption for m in measurements) / n,
            'water_consumption': sum(m.water_consumption for m in measurements) / n,
            'waste_generation': sum(m.waste_generation for m in measurements) / n,
            'financial_cost': sum(m.financial_cost for m in measurements) / n,
            'financial_savings': sum(m.financial_savings for m in measurements) / n,
            'habit_completion': sum(m.habit_completion for m in measurements) / n,
            'sustainability_score': sum(m.sustainability_score for m in measurements) / n
        }
    
    def _calculate_percentage(self, difference: float, baseline: float) -> float:
        """
        Calculate percentage change.
        """
        if baseline == 0:
            return 0.0
        
        return (difference / baseline) * 100
    
    def get_comparison_summary(self, comparison: ExperimentComparison) -> Dict[str, Any]:
        """
        Get summary of comparison results.
        
        Args:
            comparison: Experiment comparison
        
        Returns:
            Dict: Summary
        """
        improvements = comparison.get_improvement_summary()
        
        return {
            'improvements_found': len(improvements) > 0,
            'improvements': improvements,
            'best_improvement': max(improvements.items(), key=lambda x: x[1])[0] if improvements else None,
            'largest_reduction': min(
                [v for v in [
                    comparison.carbon_change_percentage,
                    comparison.energy_change_percentage,
                    comparison.water_change_percentage,
                    comparison.waste_change_percentage,
                    comparison.cost_change_percentage
                ] if v < 0],
                default=None
            ),
            'overall_trend': self._determine_trend(comparison)
        }
    
    def _determine_trend(self, comparison: ExperimentComparison) -> str:
        """
        Determine overall trend from comparison.
        """
        positive_changes = 0
        negative_changes = 0
        
        metrics = [
            comparison.carbon_change_percentage,
            comparison.energy_change_percentage,
            comparison.water_change_percentage,
            comparison.waste_change_percentage,
            comparison.cost_change_percentage
        ]
        
        # Negative changes are good (reductions)
        for change in metrics:
            if change < -5:
                positive_changes += 1
            elif change > 5:
                negative_changes += 1
        
        if positive_changes > negative_changes:
            return 'improving'
        elif negative_changes > positive_changes:
            return 'declining'
        else:
            return 'stable'
    
    def get_metric_comparison(self,
                             comparison: ExperimentComparison,
                             metric: TargetMetric) -> Dict[str, Any]:
        """
        Get comparison for a specific metric.
        
        Args:
            comparison: Experiment comparison
            metric: Target metric
        
        Returns:
            Dict: Metric comparison
        """
        metric_mapping = {
            TargetMetric.CARBON_EMISSIONS: {
                'baseline': comparison.baseline_carbon,
                'experiment': comparison.experiment_carbon,
                'difference': comparison.carbon_difference,
                'percentage': comparison.carbon_change_percentage
            },
            TargetMetric.ENERGY_CONSUMPTION: {
                'baseline': comparison.baseline_energy,
                'experiment': comparison.experiment_energy,
                'difference': comparison.energy_difference,
                'percentage': comparison.energy_change_percentage
            },
            TargetMetric.WATER_CONSUMPTION: {
                'baseline': comparison.baseline_water,
                'experiment': comparison.experiment_water,
                'difference': comparison.water_difference,
                'percentage': comparison.water_change_percentage
            },
            TargetMetric.WASTE_GENERATION: {
                'baseline': comparison.baseline_waste,
                'experiment': comparison.experiment_waste,
                'difference': comparison.waste_difference,
                'percentage': comparison.waste_change_percentage
            },
            TargetMetric.FINANCIAL_COST: {
                'baseline': comparison.baseline_cost,
                'experiment': comparison.experiment_cost,
                'difference': comparison.cost_difference,
                'percentage': comparison.cost_change_percentage
            },
            TargetMetric.HABIT_COMPLETION: {
                'baseline': comparison.baseline_habit_completion,
                'experiment': comparison.experiment_habit_completion,
                'difference': comparison.habit_completion_difference,
                'percentage': comparison.habit_completion_change_percentage
            },
            TargetMetric.SUSTAINABILITY_SCORE: {
                'baseline': comparison.baseline_sustainability,
                'experiment': comparison.experiment_sustainability,
                'difference': comparison.sustainability_difference,
                'percentage': comparison.sustainability_change_percentage
            }
        }
        
        if metric in metric_mapping:
            data = metric_mapping[metric]
            return {
                'metric': metric.value,
                'baseline': data['baseline'],
                'experiment': data['experiment'],
                'difference': data['difference'],
                'percentage_change': data['percentage'],
                'is_improvement': data['percentage'] < 0 if metric.value not in ['habit_completion', 'sustainability_score'] else data['percentage'] > 0
            }
        
        return {'error': f'Metric {metric.value} not found'}