"""
Sustainability Experiment & Habit A/B Testing Lab - Experiment Evaluator
Evaluates experiment outcomes and provides insights.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from experiments.models import (
    SustainabilityExperiment, ExperimentEvaluation, ExperimentOutcome,
    ExperimentComparison, EffectivenessResult, ExperimentGoal
)

logger = logging.getLogger(__name__)


class ExperimentEvaluator:
    """
    Evaluates experiment outcomes.
    """
    
    def __init__(self):
        """Initialize the experiment evaluator."""
        logger.info("Experiment Evaluator initialized")
    
    def evaluate_experiment(self, experiment: SustainabilityExperiment) -> Optional[ExperimentEvaluation]:
        """
        Evaluate experiment outcome.
        
        Args:
            experiment: The experiment
        
        Returns:
            Optional[ExperimentEvaluation]: Evaluation results
        """
        if not experiment.comparison or not experiment.effectiveness:
            logger.warning("Comparison and effectiveness required for evaluation")
            return None
        
        evaluation = ExperimentEvaluation(
            experiment_id=experiment.id
        )
        
        # Check goal achievement
        evaluation.goals_total = len(experiment.goals)
        evaluation.goals_achieved = self._count_achieved_goals(experiment)
        evaluation.goal_achievement_rate = (
            (evaluation.goals_achieved / evaluation.goals_total * 100) 
            if evaluation.goals_total > 0 else 0
        )
        
        # Determine outcome
        evaluation.outcome = self._determine_outcome(experiment)
        evaluation.outcome_description = self._get_outcome_description(evaluation.outcome)
        
        # Identify factors
        evaluation.factors = self._identify_factors(experiment)
        
        # Generate explanation
        evaluation.explanation = self._generate_explanation(experiment)
        
        # Generate key learnings
        evaluation.key_learnings = self._generate_key_learnings(experiment)
        
        # Make recommendations
        evaluation.should_continue, evaluation.should_modify, evaluation.should_abandon = (
            self._make_recommendations(experiment)
        )
        
        # Generate suggestions
        evaluation.suggested_modifications = self._suggest_modifications(experiment)
        evaluation.next_steps = self._suggest_next_steps(experiment)
        
        experiment.evaluation = evaluation
        experiment.updated_at = datetime.now()
        
        logger.info(f"Evaluated experiment {experiment.name}: {evaluation.outcome.value}")
        return evaluation
    
    def _count_achieved_goals(self, experiment: SustainabilityExperiment) -> int:
        """
        Count achieved goals.
        """
        if not experiment.comparison:
            return 0
        
        achieved = 0
        comparison = experiment.comparison
        
        for goal in experiment.goals:
            if self._check_goal_achieved(goal, comparison):
                goal.achieved = True
                goal.achieved_date = datetime.now()
                achieved += 1
            else:
                goal.achieved = False
        
        return achieved
    
    def _check_goal_achieved(self, goal: ExperimentGoal, comparison: ExperimentComparison) -> bool:
        """
        Check if a goal was achieved.
        """
        metric_value = self._get_comparison_metric(comparison, goal.target_metric)
        
        if metric_value is None:
            return False
        
        if goal.target_value > 0:
            # Check if metric improved to target
            if goal.target_metric.value in ['carbon_emissions', 'energy_consumption', 
                                            'water_consumption', 'waste_generation', 
                                            'financial_cost']:
                # Lower is better
                return metric_value <= goal.target_value
            else:
                # Higher is better
                return metric_value >= goal.target_value
        
        if goal.target_percentage > 0:
            # Check percentage improvement
            percentage_change = self._get_percentage_change(comparison, goal.target_metric)
            if percentage_change is not None:
                if goal.target_metric.value in ['carbon_emissions', 'energy_consumption', 
                                                'water_consumption', 'waste_generation', 
                                                'financial_cost']:
                    return percentage_change <= -goal.target_percentage
                else:
                    return percentage_change >= goal.target_percentage
        
        return False
    
    def _get_comparison_metric(self, comparison: ExperimentComparison, metric: TargetMetric) -> Optional[float]:
        """Get metric value from comparison."""
        mapping = {
            TargetMetric.CARBON_EMISSIONS: comparison.experiment_carbon,
            TargetMetric.ENERGY_CONSUMPTION: comparison.experiment_energy,
            TargetMetric.WATER_CONSUMPTION: comparison.experiment_water,
            TargetMetric.WASTE_GENERATION: comparison.experiment_waste,
            TargetMetric.FINANCIAL_COST: comparison.experiment_cost,
            TargetMetric.HABIT_COMPLETION: comparison.experiment_habit_completion,
            TargetMetric.SUSTAINABILITY_SCORE: comparison.experiment_sustainability
        }
        return mapping.get(metric)
    
    def _get_percentage_change(self, comparison: ExperimentComparison, metric: TargetMetric) -> Optional[float]:
        """Get percentage change from comparison."""
        mapping = {
            TargetMetric.CARBON_EMISSIONS: comparison.carbon_change_percentage,
            TargetMetric.ENERGY_CONSUMPTION: comparison.energy_change_percentage,
            TargetMetric.WATER_CONSUMPTION: comparison.water_change_percentage,
            TargetMetric.WASTE_GENERATION: comparison.waste_change_percentage,
            TargetMetric.FINANCIAL_COST: comparison.cost_change_percentage,
            TargetMetric.HABIT_COMPLETION: comparison.habit_completion_change_percentage,
            TargetMetric.SUSTAINABILITY_SCORE: comparison.sustainability_change_percentage
        }
        return mapping.get(metric)
    
    def _determine_outcome(self, experiment: SustainabilityExperiment) -> ExperimentOutcome:
        """
        Determine experiment outcome.
        """
        if not experiment.effectiveness:
            return ExperimentOutcome.INCONCLUSIVE
        
        effectiveness = experiment.effectiveness
        
        # Check if goals were achieved
        if experiment.goals:
            achieved = sum(1 for g in experiment.goals if g.achieved)
            total = len(experiment.goals)
            
            if achieved == total and total > 0:
                return ExperimentOutcome.SUCCESSFUL
            elif achieved > 0:
                return ExperimentOutcome.PARTIALLY_SUCCESSFUL
        
        # Check effectiveness score
        if effectiveness.overall_score >= 70:
            return ExperimentOutcome.SUCCESSFUL
        elif effectiveness.overall_score >= 40:
            return ExperimentOutcome.PARTIALLY_SUCCESSFUL
        elif effectiveness.overall_score < 20:
            return ExperimentOutcome.UNSUCCESSFUL
        
        # Check if there are unexpected positive results
        if effectiveness.environmental_effectiveness > 60 and experiment.category.value not in ['environmental']:
            return ExperimentOutcome.UNEXPECTED
        
        return ExperimentOutcome.INCONCLUSIVE
    
    def _get_outcome_description(self, outcome: ExperimentOutcome) -> str:
        """Get description for outcome."""
        descriptions = {
            ExperimentOutcome.SUCCESSFUL: "The experiment successfully achieved its goals and showed significant improvement.",
            ExperimentOutcome.PARTIALLY_SUCCESSFUL: "The experiment achieved some but not all of its goals.",
            ExperimentOutcome.UNSUCCESSFUL: "The experiment did not achieve its intended goals.",
            ExperimentOutcome.UNEXPECTED: "The experiment produced unexpected but positive results in other areas.",
            ExperimentOutcome.INCONCLUSIVE: "The experiment results were inconclusive. Consider extending the period."
        }
        return descriptions.get(outcome, "Outcome unknown.")
    
    def _identify_factors(self, experiment: SustainabilityExperiment) -> List[str]:
        """
        Identify factors that influenced the outcome.
        """
        factors = []
        
        if not experiment.comparison:
            return factors
        
        comparison = experiment.comparison
        
        # Check what worked
        if comparison.carbon_change_percentage < -10:
            factors.append("Significant carbon reduction achieved")
        elif comparison.carbon_change_percentage < -5:
            factors.append("Modest carbon reduction observed")
        
        if comparison.energy_change_percentage < -10:
            factors.append("Significant energy reduction achieved")
        
        if comparison.water_change_percentage < -10:
            factors.append("Significant water reduction achieved")
        
        if comparison.waste_change_percentage < -10:
            factors.append("Significant waste reduction achieved")
        
        if comparison.habit_completion_change_percentage > 15:
            factors.append("Strong habit improvement observed")
        
        if comparison.sustainability_change_percentage > 10:
            factors.append("Sustainability score improved")
        
        # Check what didn't work
        if comparison.carbon_change_percentage > 5:
            factors.append("Carbon emissions increased during experiment")
        
        if comparison.habit_completion_change_percentage < -10:
            factors.append("Habit completion decreased")
        
        if not factors:
            factors.append("No significant changes observed. Experiment may need longer duration.")
        
        return factors
    
    def _generate_explanation(self, experiment: SustainabilityExperiment) -> str:
        """
        Generate explanation of results.
        """
        if not experiment.evaluation:
            return "No evaluation available."
        
        evaluation = experiment.evaluation
        
        if evaluation.outcome == ExperimentOutcome.SUCCESSFUL:
            return (f"The experiment was successful! It achieved {evaluation.goals_achieved} out of "
                   f"{evaluation.goals_total} goals with a {evaluation.goal_achievement_rate:.0f}% achievement rate. "
                   f"The sustainability score improved by {experiment.comparison.sustainability_change_percentage:.1f}%.")
        
        elif evaluation.outcome == ExperimentOutcome.PARTIALLY_SUCCESSFUL:
            return (f"The experiment was partially successful, achieving {evaluation.goals_achieved} out of "
                   f"{evaluation.goals_total} goals. Some areas showed improvement while others didn't meet expectations.")
        
        elif evaluation.outcome == ExperimentOutcome.UNSUCCESSFUL:
            return (f"The experiment did not achieve its goals. The sustainability score changed by "
                   f"{experiment.comparison.sustainability_change_percentage:.1f}%. Consider trying a different approach.")
        
        else:
            return (f"The experiment results were inconclusive. The sustainability score changed by "
                   f"{experiment.comparison.sustainability_change_percentage:.1f}%. Consider extending the duration.")
    
    def _generate_key_learnings(self, experiment: SustainabilityExperiment) -> List[str]:
        """
        Generate key learnings from the experiment.
        """
        learnings = []
        
        if not experiment.comparison:
            return learnings
        
        comparison = experiment.comparison
        
        # Carbon learnings
        if comparison.carbon_change_percentage < -15:
            learnings.append("This approach is highly effective for carbon reduction")
        elif comparison.carbon_change_percentage < 0:
            learnings.append("This approach helps reduce carbon emissions")
        else:
            learnings.append("This approach may not be effective for carbon reduction")
        
        # Habit learnings
        if comparison.habit_completion_change_percentage > 10:
            learnings.append("The habit change was well-adopted and sustainable")
        elif comparison.habit_completion_change_percentage < -10:
            learnings.append("The habit change was difficult to maintain")
        else:
            learnings.append("The habit change had moderate adoption")
        
        # Financial learnings
        if comparison.cost_change_percentage < -10:
            learnings.append("Significant cost savings achieved")
        
        # Overall
        if experiment.effectiveness and experiment.effectiveness.overall_score >= 70:
            learnings.append("This is a highly effective sustainability strategy to continue")
        elif experiment.effectiveness and experiment.effectiveness.overall_score >= 40:
            learnings.append("This strategy has potential but may need optimization")
        else:
            learnings.append("This strategy may not be suitable. Consider alternatives")
        
        return learnings
    
    def _make_recommendations(self, experiment: SustainabilityExperiment) -> tuple:
        """
        Make recommendations about the experiment.
        """
        if not experiment.evaluation:
            return False, False, True
        
        evaluation = experiment.evaluation
        
        if evaluation.outcome == ExperimentOutcome.SUCCESSFUL:
            return True, False, False
        elif evaluation.outcome == ExperimentOutcome.PARTIALLY_SUCCESSFUL:
            return False, True, False
        elif evaluation.outcome == ExperimentOutcome.UNSUCCESSFUL:
            return False, False, True
        else:  # INCONCLUSIVE
            return False, True, False
    
    def _suggest_modifications(self, experiment: SustainabilityExperiment) -> List[str]:
        """
        Suggest modifications for the experiment.
        """
        suggestions = []
        
        if not experiment.comparison:
            return suggestions
        
        comparison = experiment.comparison
        
        # Duration suggestions
        if experiment.experiment_duration_days < 21:
            suggestions.append("Consider extending the experiment duration to 3-4 weeks for more reliable results")
        
        # Target suggestions
        if experiment.target_metrics:
            for metric in experiment.target_metrics:
                if metric.value in ['carbon_emissions', 'energy_consumption', 'water_consumption']:
                    if self._get_percentage_change(comparison, metric) is not None:
                        change = self._get_percentage_change(comparison, metric)
                        if change is not None and change < 0:
                            suggestions.append(f"Target {metric.value} is improving. Consider making it more ambitious")
                        elif change is not None and change > 5:
                            suggestions.append(f"Target {metric.value} is not improving. Try a different approach")
        
        # Habit suggestions
        if comparison.habit_completion_change_percentage < 0:
            suggestions.append("Habit completion decreased. Consider simplifying the habit or adding reminders")
        
        # Approach suggestions
        if experiment.effectiveness and experiment.effectiveness.overall_score < 40:
            suggestions.append("Try a different approach or combination of changes")
        
        return suggestions
    
    def _suggest_next_steps(self, experiment: SustainabilityExperiment) -> List[str]:
        """
        Suggest next steps after evaluation.
        """
        steps = []
        
        if not experiment.evaluation:
            return steps
        
        evaluation = experiment.evaluation
        
        if evaluation.should_continue:
            steps.append("Make this experiment a permanent habit")
            steps.append("Track long-term sustainability to ensure continued improvement")
        elif evaluation.should_modify:
            steps.append("Adjust the experiment approach based on learnings")
            steps.append("Try a modified version of the experiment")
        elif evaluation.should_abandon:
            steps.append("Abandon this approach and try a different experiment")
            steps.append("Review what worked and what didn't for future experiments")
        
        # Additional steps
        steps.append("Review the experiment data and identify specific improvement areas")
        steps.append("Consider combining this experiment with other sustainability strategies")
        
        return steps