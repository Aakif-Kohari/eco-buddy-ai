"""
Sustainability Experiment & Habit A/B Testing Lab - Experiment Builder
Creates and manages sustainability experiments.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from experiments.models import (
    SustainabilityExperiment, ExperimentStatus, ExperimentCategory,
    TargetMetric, ExperimentGoal, ExperimentTemplate
)

logger = logging.getLogger(__name__)


class ExperimentBuilder:
    """
    Builds and manages sustainability experiments.
    """
    
    def __init__(self):
        """Initialize the experiment builder."""
        logger.info("Experiment Builder initialized")
    
    def create_experiment(self, 
                         name: str,
                         user_id: str,
                         category: ExperimentCategory,
                         description: str = "",
                         household_id: Optional[str] = None) -> SustainabilityExperiment:
        """
        Create a new sustainability experiment.
        
        Args:
            name: Experiment name
            user_id: User ID
            category: Experiment category
            description: Experiment description
            household_id: Optional household ID
        
        Returns:
            SustainabilityExperiment: Created experiment
        """
        experiment = SustainabilityExperiment(
            name=name,
            description=description,
            user_id=user_id,
            household_id=household_id,
            category=category,
            status=ExperimentStatus.DRAFT,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        logger.info(f"Created experiment: {name} for user {user_id}")
        return experiment
    
    def set_experiment_timeline(self, 
                               experiment: SustainabilityExperiment,
                               baseline_duration_days: int = 14,
                               experiment_duration_days: int = 14) -> None:
        """
        Set experiment timeline.
        
        Args:
            experiment: The experiment
            baseline_duration_days: Baseline duration in days
            experiment_duration_days: Experiment duration in days
        """
        experiment.baseline_duration_days = baseline_duration_days
        experiment.experiment_duration_days = experiment_duration_days
        
        # Set dates
        now = datetime.now()
        experiment.start_date = now
        experiment.baseline_start_date = now
        experiment.baseline_end_date = now + timedelta(days=baseline_duration_days)
        experiment.experiment_start_date = experiment.baseline_end_date
        experiment.experiment_end_date = experiment.baseline_end_date + timedelta(days=experiment_duration_days)
        experiment.end_date = experiment.experiment_end_date
        
        experiment.updated_at = datetime.now()
        logger.info(f"Set timeline for experiment {experiment.name}")
    
    def add_goal(self, 
                experiment: SustainabilityExperiment,
                target_metric: TargetMetric,
                target_value: float,
                target_percentage: float = 0.0,
                description: str = "") -> None:
        """
        Add a goal to the experiment.
        
        Args:
            experiment: The experiment
            target_metric: Target metric
            target_value: Target value
            target_percentage: Target percentage improvement
            description: Goal description
        """
        goal = ExperimentGoal(
            target_metric=target_metric,
            target_value=target_value,
            target_percentage=target_percentage,
            description=description or f"Achieve {target_value} in {target_metric.value}"
        )
        experiment.goals.append(goal)
        experiment.updated_at = datetime.now()
        logger.info(f"Added goal to experiment {experiment.name}")
    
    def add_target_metric(self, 
                         experiment: SustainabilityExperiment,
                         metric: TargetMetric) -> None:
        """
        Add a target metric to the experiment.
        
        Args:
            experiment: The experiment
            metric: Target metric
        """
        if metric not in experiment.target_metrics:
            experiment.target_metrics.append(metric)
            experiment.updated_at = datetime.now()
    
    def add_target_habit(self, 
                        experiment: SustainabilityExperiment,
                        habit: str) -> None:
        """
        Add a target habit to the experiment.
        
        Args:
            experiment: The experiment
            habit: Habit name
        """
        if habit not in experiment.target_habits:
            experiment.target_habits.append(habit)
            experiment.updated_at = datetime.now()
    
    def start_baseline_phase(self, experiment: SustainabilityExperiment) -> bool:
        """
        Start the baseline measurement phase.
        
        Args:
            experiment: The experiment
        
        Returns:
            bool: True if started successfully
        """
        if experiment.status not in [ExperimentStatus.DRAFT, ExperimentStatus.BASELINE]:
            logger.warning(f"Cannot start baseline for experiment in {experiment.status.value} status")
            return False
        
        experiment.status = ExperimentStatus.BASELINE
        experiment.baseline_start_date = datetime.now()
        experiment.updated_at = datetime.now()
        
        logger.info(f"Started baseline phase for experiment {experiment.name}")
        return True
    
    def start_experiment_phase(self, experiment: SustainabilityExperiment) -> bool:
        """
        Start the experiment phase.
        
        Args:
            experiment: The experiment
        
        Returns:
            bool: True if started successfully
        """
        if experiment.status != ExperimentStatus.BASELINE:
            logger.warning(f"Cannot start experiment phase from {experiment.status.value} status")
            return False
        
        if not experiment.baseline_snapshot:
            logger.warning("Baseline snapshot is required before starting experiment phase")
            return False
        
        experiment.status = ExperimentStatus.ACTIVE
        experiment.experiment_start_date = datetime.now()
        experiment.updated_at = datetime.now()
        
        logger.info(f"Started experiment phase for {experiment.name}")
        return True
    
    def complete_experiment(self, experiment: SustainabilityExperiment) -> bool:
        """
        Complete the experiment.
        
        Args:
            experiment: The experiment
        
        Returns:
            bool: True if completed successfully
        """
        if experiment.status != ExperimentStatus.ACTIVE:
            logger.warning(f"Cannot complete experiment in {experiment.status.value} status")
            return False
        
        experiment.status = ExperimentStatus.COMPLETED
        experiment.completed_at = datetime.now()
        experiment.updated_at = datetime.now()
        
        logger.info(f"Completed experiment {experiment.name}")
        return True
    
    def validate_experiment(self, experiment: SustainabilityExperiment) -> Dict[str, Any]:
        """
        Validate experiment configuration.
        
        Args:
            experiment: The experiment
        
        Returns:
            Dict: Validation results
        """
        errors = []
        warnings = []
        
        # Check required fields
        if not experiment.name:
            errors.append("Experiment name is required")
        
        if not experiment.user_id:
            errors.append("User ID is required")
        
        if experiment.baseline_duration_days < 3:
            warnings.append("Baseline duration should be at least 3 days for meaningful results")
        
        if experiment.experiment_duration_days < 3:
            warnings.append("Experiment duration should be at least 3 days for meaningful results")
        
        if not experiment.target_metrics:
            warnings.append("No target metrics defined")
        
        if not experiment.target_habits:
            warnings.append("No target habits defined")
        
        if experiment.goals:
            for goal in experiment.goals:
                if goal.target_value <= 0 and goal.target_percentage <= 0:
                    warnings.append(f"Goal '{goal.description}' has no meaningful target")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def create_from_template(self, 
                            template: ExperimentTemplate,
                            user_id: str,
                            household_id: Optional[str] = None) -> SustainabilityExperiment:
        """
        Create an experiment from a template.
        
        Args:
            template: Experiment template
            user_id: User ID
            household_id: Optional household ID
        
        Returns:
            SustainabilityExperiment: Created experiment
        """
        experiment = self.create_experiment(
            name=template.name,
            user_id=user_id,
            category=template.category,
            description=template.description,
            household_id=household_id
        )
        
        # Apply template settings
        experiment.baseline_duration_days = template.baseline_duration_days
        experiment.experiment_duration_days = template.experiment_duration_days
        experiment.target_metrics = template.target_metrics
        experiment.target_habits = template.target_habits
        experiment.expected_improvement_percentage = template.expected_improvement_percentage
        
        # Set timeline
        self.set_experiment_timeline(
            experiment,
            template.baseline_duration_days,
            template.experiment_duration_days
        )
        
        # Add goal based on template
        if template.estimated_carbon_savings > 0:
            self.add_goal(
                experiment,
                TargetMetric.CARBON_EMISSIONS,
                template.estimated_carbon_savings,
                template.expected_improvement_percentage,
                f"Reduce carbon emissions by {template.estimated_carbon_savings}kg"
            )
        
        if template.estimated_cost_savings > 0:
            self.add_goal(
                experiment,
                TargetMetric.FINANCIAL_SAVINGS,
                template.estimated_cost_savings,
                template.expected_improvement_percentage * 0.5,
                f"Save ${template.estimated_cost_savings} through {template.name}"
            )
        
        # Update template usage
        template.usage_count += 1
        
        logger.info(f"Created experiment from template {template.name}")
        return experiment