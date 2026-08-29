"""
Sustainability Experiment & Habit A/B Testing Lab - Measurement Tracker
Tracks measurements during experiments.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from experiments.models import (
    SustainabilityExperiment, ExperimentMeasurement, MeasurementType,
    ExperimentStatus, TargetMetric
)

logger = logging.getLogger(__name__)


class MeasurementTracker:
    """
    Tracks measurements during experiments.
    """
    
    def __init__(self):
        """Initialize the measurement tracker."""
        logger.info("Measurement Tracker initialized")
    
    def record_measurement(self,
                          experiment: SustainabilityExperiment,
                          measurement_type: MeasurementType = MeasurementType.DAILY,
                          **kwargs) -> Optional[ExperimentMeasurement]:
        """
        Record a measurement for an experiment.
        
        Args:
            experiment: The experiment
            measurement_type: Type of measurement
            **kwargs: Measurement values
        
        Returns:
            Optional[ExperimentMeasurement]: Recorded measurement
        """
        if experiment.status not in [ExperimentStatus.BASELINE, ExperimentStatus.ACTIVE]:
            logger.warning(f"Cannot record measurement in {experiment.status.value} status")
            return None
        
        measurement = ExperimentMeasurement(
            experiment_id=experiment.id,
            measurement_date=kwargs.get('measurement_date', datetime.now()),
            measurement_type=measurement_type,
            carbon_emissions=kwargs.get('carbon_emissions', 0.0),
            energy_consumption=kwargs.get('energy_consumption', 0.0),
            water_consumption=kwargs.get('water_consumption', 0.0),
            waste_generation=kwargs.get('waste_generation', 0.0),
            financial_cost=kwargs.get('financial_cost', 0.0),
            financial_savings=kwargs.get('financial_savings', 0.0),
            habit_completion=kwargs.get('habit_completion', 0.0),
            sustainability_score=kwargs.get('sustainability_score', 0.0),
            custom_metrics=kwargs.get('custom_metrics', {}),
            notes=kwargs.get('notes', '')
        )
        
        experiment.measurements.append(measurement)
        experiment.updated_at = datetime.now()
        
        logger.info(f"Recorded {measurement_type.value} measurement for experiment {experiment.name}")
        return measurement
    
    def record_daily_measurement(self,
                                 experiment: SustainabilityExperiment,
                                 **kwargs) -> Optional[ExperimentMeasurement]:
        """
        Record a daily measurement.
        
        Args:
            experiment: The experiment
            **kwargs: Measurement values
        
        Returns:
            Optional[ExperimentMeasurement]: Recorded measurement
        """
        return self.record_measurement(experiment, MeasurementType.DAILY, **kwargs)
    
    def record_weekly_measurement(self,
                                 experiment: SustainabilityExperiment,
                                 **kwargs) -> Optional[ExperimentMeasurement]:
        """
        Record a weekly measurement.
        
        Args:
            experiment: The experiment
            **kwargs: Measurement values
        
        Returns:
            Optional[ExperimentMeasurement]: Recorded measurement
        """
        return self.record_measurement(experiment, MeasurementType.WEEKLY, **kwargs)
    
    def record_monthly_measurement(self,
                                  experiment: SustainabilityExperiment,
                                  **kwargs) -> Optional[ExperimentMeasurement]:
        """
        Record a monthly measurement.
        
        Args:
            experiment: The experiment
            **kwargs: Measurement values
        
        Returns:
            Optional[ExperimentMeasurement]: Recorded measurement
        """
        return self.record_measurement(experiment, MeasurementType.MONTHLY, **kwargs)
    
    def get_measurements_by_period(self,
                                  experiment: SustainabilityExperiment,
                                  start_date: datetime,
                                  end_date: datetime) -> List[ExperimentMeasurement]:
        """
        Get measurements within a date range.
        
        Args:
            experiment: The experiment
            start_date: Start date
            end_date: End date
        
        Returns:
            List[ExperimentMeasurement]: Measurements in range
        """
        return [
            m for m in experiment.measurements
            if start_date <= m.measurement_date <= end_date
        ]
    
    def get_experiment_measurements(self,
                                   experiment: SustainabilityExperiment) -> List[ExperimentMeasurement]:
        """
        Get all experiment measurements after baseline.
        
        Args:
            experiment: The experiment
        
        Returns:
            List[ExperimentMeasurement]: Experiment measurements
        """
        if not experiment.experiment_start_date:
            return []
        
        return [
            m for m in experiment.measurements
            if m.measurement_date >= experiment.experiment_start_date
        ]
    
    def get_measurement_averages(self,
                                measurements: List[ExperimentMeasurement]) -> Dict[str, float]:
        """
        Calculate averages from a list of measurements.
        
        Args:
            measurements: List of measurements
        
        Returns:
            Dict: Average values
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
    
    def get_latest_measurement(self, 
                              experiment: SustainabilityExperiment) -> Optional[ExperimentMeasurement]:
        """
        Get the latest measurement for an experiment.
        
        Args:
            experiment: The experiment
        
        Returns:
            Optional[ExperimentMeasurement]: Latest measurement
        """
        if not experiment.measurements:
            return None
        
        return max(experiment.measurements, key=lambda m: m.measurement_date)
    
    def get_measurement_history(self,
                               experiment: SustainabilityExperiment,
                               metric: TargetMetric) -> List[Dict[str, Any]]:
        """
        Get historical values for a specific metric.
        
        Args:
            experiment: The experiment
            metric: Target metric
        
        Returns:
            List[Dict]: Historical values
        """
        history = []
        
        for measurement in sorted(experiment.measurements, key=lambda m: m.measurement_date):
            value = self._get_metric_value(measurement, metric)
            if value is not None:
                history.append({
                    'date': measurement.measurement_date.isoformat(),
                    'value': value,
                    'type': measurement.measurement_type.value
                })
        
        return history
    
    def _get_metric_value(self, measurement: ExperimentMeasurement, metric: TargetMetric) -> Optional[float]:
        """Get value for a specific metric from a measurement."""
        mapping = {
            TargetMetric.CARBON_EMISSIONS: measurement.carbon_emissions,
            TargetMetric.ENERGY_CONSUMPTION: measurement.energy_consumption,
            TargetMetric.WATER_CONSUMPTION: measurement.water_consumption,
            TargetMetric.WASTE_GENERATION: measurement.waste_generation,
            TargetMetric.FINANCIAL_COST: measurement.financial_cost,
            TargetMetric.FINANCIAL_SAVINGS: measurement.financial_savings,
            TargetMetric.HABIT_COMPLETION: measurement.habit_completion,
            TargetMetric.SUSTAINABILITY_SCORE: measurement.sustainability_score
        }
        
        if metric in mapping:
            return mapping[metric]
        
        # Check custom metrics
        if metric.value in measurement.custom_metrics:
            return measurement.custom_metrics[metric.value]
        
        return None
    
    def is_measurement_due(self, 
                          experiment: SustainabilityExperiment,
                          measurement_type: MeasurementType) -> bool:
        """
        Check if a measurement is due.
        
        Args:
            experiment: The experiment
            measurement_type: Type of measurement
        
        Returns:
            bool: True if measurement is due
        """
        latest = self.get_latest_measurement(experiment)
        
        if not latest:
            return True
        
        if measurement_type == MeasurementType.DAILY:
            return (datetime.now() - latest.measurement_date).days >= 1
        elif measurement_type == MeasurementType.WEEKLY:
            return (datetime.now() - latest.measurement_date).days >= 7
        elif measurement_type == MeasurementType.MONTHLY:
            return (datetime.now() - latest.measurement_date).days >= 30
        
        return False