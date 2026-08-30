"""
Sustainability Experiment & Habit A/B Testing Lab - Baseline Analysis
Captures and analyzes baseline measurements.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from experiments.models import (
    SustainabilityExperiment, BaselineSnapshot, ExperimentMeasurement,
    ExperimentStatus, TargetMetric
)

logger = logging.getLogger(__name__)


class BaselineAnalyzer:
    """
    Analyzes baseline measurements for experiments.
    """
    
    def __init__(self):
        """Initialize the baseline analyzer."""
        logger.info("Baseline Analyzer initialized")
    
    def capture_baseline(self, experiment: SustainabilityExperiment) -> Optional[BaselineSnapshot]:
        """
        Capture baseline snapshot for an experiment.
        
        Args:
            experiment: The experiment
        
        Returns:
            Optional[BaselineSnapshot]: Baseline snapshot
        """
        if experiment.status not in [ExperimentStatus.DRAFT, ExperimentStatus.BASELINE]:
            logger.warning(f"Cannot capture baseline in {experiment.status.value} status")
            return None
        
        # Check if we have enough data
        if not experiment.measurements:
            logger.warning("No measurements available for baseline")
            return None
        
        # Filter measurements for baseline period
        baseline_measurements = self._get_baseline_measurements(experiment)
        
        if len(baseline_measurements) < 3:
            logger.warning(f"Insufficient baseline measurements: {len(baseline_measurements)}")
            return None
        
        # Calculate averages
        snapshot = BaselineSnapshot(
            experiment_id=experiment.id,
            start_date=experiment.baseline_start_date or min(m.measurement_date for m in baseline_measurements),
            end_date=experiment.baseline_end_date or max(m.measurement_date for m in baseline_measurements),
            duration_days=experiment.baseline_duration_days
        )
        
        # Calculate average values
        snapshot.carbon_emissions_avg = statistics.mean([m.carbon_emissions for m in baseline_measurements])
        snapshot.energy_consumption_avg = statistics.mean([m.energy_consumption for m in baseline_measurements])
        snapshot.water_consumption_avg = statistics.mean([m.water_consumption for m in baseline_measurements])
        snapshot.waste_generation_avg = statistics.mean([m.waste_generation for m in baseline_measurements])
        snapshot.financial_cost_avg = statistics.mean([m.financial_cost for m in baseline_measurements])
        snapshot.sustainability_score_avg = statistics.mean([m.sustainability_score for m in baseline_measurements])
        
        # Calculate habit completion average (from custom metrics or habit tracking)
        habit_values = [m.custom_metrics.get('habit_completion', 0) for m in baseline_measurements]
        if habit_values:
            snapshot.habit_completion_avg = statistics.mean(habit_values)
        
        # Analyze baseline trend
        trend = self._analyze_baseline_trend(baseline_measurements)
        snapshot.trend_direction = trend['direction']
        snapshot.trend_rate = trend['rate']
        
        # Store daily measurements
        snapshot.daily_measurements = [
            {
                'date': m.measurement_date.isoformat(),
                'carbon': m.carbon_emissions,
                'energy': m.energy_consumption,
                'water': m.water_consumption,
                'waste': m.waste_generation,
                'cost': m.financial_cost
            }
            for m in baseline_measurements
        ]
        
        experiment.baseline_snapshot = snapshot
        experiment.updated_at = datetime.now()
        
        logger.info(f"Captured baseline snapshot for experiment {experiment.name}")
        return snapshot
    
    def _get_baseline_measurements(self, 
                                  experiment: SustainabilityExperiment) -> List[ExperimentMeasurement]:
        """
        Get measurements from the baseline period.
        """
        if not experiment.baseline_start_date:
            return experiment.measurements[:experiment.baseline_duration_days]
        
        baseline_start = experiment.baseline_start_date
        baseline_end = experiment.baseline_end_date or datetime.now()
        
        return [
            m for m in experiment.measurements
            if baseline_start <= m.measurement_date <= baseline_end
        ]
    
    def _analyze_baseline_trend(self, 
                               measurements: List[ExperimentMeasurement]) -> Dict[str, Any]:
        """
        Analyze trend in baseline measurements.
        """
        if len(measurements) < 3:
            return {'direction': 'stable', 'rate': 0.0}
        
        # Use carbon emissions as primary trend indicator
        values = [m.carbon_emissions for m in measurements]
        
        if len(values) < 2:
            return {'direction': 'stable', 'rate': 0.0}
        
        # Simple linear trend
        first = values[0]
        last = values[-1]
        
        if first == 0:
            return {'direction': 'stable', 'rate': 0.0}
        
        percent_change = ((last - first) / first) * 100
        
        if percent_change < -5:
            direction = 'improving'
        elif percent_change > 5:
            direction = 'declining'
        else:
            direction = 'stable'
        
        rate = percent_change / len(measurements)
        
        return {
            'direction': direction,
            'rate': rate
        }
    
    def get_baseline_summary(self, snapshot: BaselineSnapshot) -> Dict[str, Any]:
        """
        Get summary of baseline snapshot.
        
        Args:
            snapshot: Baseline snapshot
        
        Returns:
            Dict: Baseline summary
        """
        return {
            'duration_days': snapshot.duration_days,
            'carbon_emissions_avg': snapshot.carbon_emissions_avg,
            'energy_consumption_avg': snapshot.energy_consumption_avg,
            'water_consumption_avg': snapshot.water_consumption_avg,
            'waste_generation_avg': snapshot.waste_generation_avg,
            'financial_cost_avg': snapshot.financial_cost_avg,
            'habit_completion_avg': snapshot.habit_completion_avg,
            'sustainability_score_avg': snapshot.sustainability_score_avg,
            'trend_direction': snapshot.trend_direction,
            'trend_rate': snapshot.trend_rate,
            'measurement_count': len(snapshot.daily_measurements)
        }
    
    def compare_baseline_to_target(self, 
                                  snapshot: BaselineSnapshot,
                                  target_metric: TargetMetric,
                                  target_value: float) -> Dict[str, Any]:
        """
        Compare baseline to target value.
        
        Args:
            snapshot: Baseline snapshot
            target_metric: Target metric
            target_value: Target value
        
        Returns:
            Dict: Comparison results
        """
        current_value = self._get_metric_value(snapshot, target_metric)
        
        if current_value is None:
            return {'error': f'Metric {target_metric.value} not found in baseline'}
        
        if current_value == 0:
            return {'error': 'Baseline value is zero'}
        
        difference = current_value - target_value
        percentage_change = ((target_value - current_value) / current_value) * 100
        
        return {
            'baseline_value': current_value,
            'target_value': target_value,
            'difference': difference,
            'percentage_change': percentage_change,
            'improvement_needed': percentage_change > 0,
            'status': 'achieved' if current_value <= target_value else 'needs_improvement'
        }
    
    def _get_metric_value(self, snapshot: BaselineSnapshot, metric: TargetMetric) -> Optional[float]:
        """Get baseline value for a specific metric."""
        mapping = {
            TargetMetric.CARBON_EMISSIONS: snapshot.carbon_emissions_avg,
            TargetMetric.ENERGY_CONSUMPTION: snapshot.energy_consumption_avg,
            TargetMetric.WATER_CONSUMPTION: snapshot.water_consumption_avg,
            TargetMetric.WASTE_GENERATION: snapshot.waste_generation_avg,
            TargetMetric.FINANCIAL_COST: snapshot.financial_cost_avg,
            TargetMetric.HABIT_COMPLETION: snapshot.habit_completion_avg,
            TargetMetric.SUSTAINABILITY_SCORE: snapshot.sustainability_score_avg
        }
        return mapping.get(metric)