"""
Sustainability Experiment & Habit A/B Testing Lab - Data Models
Comprehensive models for experiment management.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
import uuid
import json


class ExperimentStatus(Enum):
    """Status of a sustainability experiment."""
    DRAFT = "draft"
    BASELINE = "baseline"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ExperimentCategory(Enum):
    """Categories of sustainability experiments."""
    ENERGY = "energy"
    WATER = "water"
    WASTE = "waste"
    TRANSPORTATION = "transportation"
    FOOD = "food"
    SHOPPING = "shopping"
    RECYCLING = "recycling"
    COMPOSTING = "composting"
    HABIT = "habit"
    LIFESTYLE = "lifestyle"
    FINANCIAL = "financial"
    OTHER = "other"


class MeasurementType(Enum):
    """Types of measurements in experiments."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    PER_EVENT = "per_event"
    CUSTOM = "custom"


class TargetMetric(Enum):
    """Target metrics for experiments."""
    CARBON_EMISSIONS = "carbon_emissions"
    ENERGY_CONSUMPTION = "energy_consumption"
    WATER_CONSUMPTION = "water_consumption"
    WASTE_GENERATION = "waste_generation"
    RECYCLING_RATE = "recycling_rate"
    FOOD_WASTE = "food_waste"
    TRANSPORTATION_IMPACT = "transportation_impact"
    FINANCIAL_COST = "financial_cost"
    FINANCIAL_SAVINGS = "financial_savings"
    HABIT_COMPLETION = "habit_completion"
    SUSTAINABILITY_SCORE = "sustainability_score"
    CUSTOM = "custom"


class ExperimentOutcome(Enum):
    """Outcome of an experiment evaluation."""
    SUCCESSFUL = "successful"
    PARTIALLY_SUCCESSFUL = "partially_successful"
    UNSUCCESSFUL = "unsuccessful"
    UNEXPECTED = "unexpected"
    INCONCLUSIVE = "inconclusive"


@dataclass
class ExperimentGoal:
    """
    Represents a goal for a sustainability experiment.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    target_metric: TargetMetric = TargetMetric.CUSTOM
    target_value: float = 0.0
    target_percentage: float = 0.0
    description: str = ""
    achieved: bool = False
    achieved_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'target_metric': self.target_metric.value,
            'target_value': self.target_value,
            'target_percentage': self.target_percentage,
            'description': self.description,
            'achieved': self.achieved,
            'achieved_date': self.achieved_date.isoformat() if self.achieved_date else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentGoal':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            target_metric=TargetMetric(data.get('target_metric', 'custom')),
            target_value=data.get('target_value', 0.0),
            target_percentage=data.get('target_percentage', 0.0),
            description=data.get('description', ''),
            achieved=data.get('achieved', False),
            achieved_date=datetime.fromisoformat(data['achieved_date']) if data.get('achieved_date') else None
        )


@dataclass
class BaselineSnapshot:
    """
    Snapshot of baseline measurements before an experiment.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = ""
    start_date: datetime = field(default_factory=datetime.now)
    end_date: datetime = field(default_factory=datetime.now)
    duration_days: int = 0
    
    # Baseline values
    carbon_emissions_avg: float = 0.0
    energy_consumption_avg: float = 0.0
    water_consumption_avg: float = 0.0
    waste_generation_avg: float = 0.0
    financial_cost_avg: float = 0.0
    habit_completion_avg: float = 0.0
    sustainability_score_avg: float = 0.0
    
    # Daily records
    daily_measurements: List[Dict[str, Any]] = field(default_factory=list)
    
    # Trends
    trend_direction: str = ""  # improving, declining, stable
    trend_rate: float = 0.0
    
    # Metadata
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'duration_days': self.duration_days,
            'carbon_emissions_avg': self.carbon_emissions_avg,
            'energy_consumption_avg': self.energy_consumption_avg,
            'water_consumption_avg': self.water_consumption_avg,
            'waste_generation_avg': self.waste_generation_avg,
            'financial_cost_avg': self.financial_cost_avg,
            'habit_completion_avg': self.habit_completion_avg,
            'sustainability_score_avg': self.sustainability_score_avg,
            'daily_measurements': self.daily_measurements,
            'trend_direction': self.trend_direction,
            'trend_rate': self.trend_rate,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaselineSnapshot':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            experiment_id=data.get('experiment_id', ''),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else datetime.now(),
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else datetime.now(),
            duration_days=data.get('duration_days', 0),
            carbon_emissions_avg=data.get('carbon_emissions_avg', 0.0),
            energy_consumption_avg=data.get('energy_consumption_avg', 0.0),
            water_consumption_avg=data.get('water_consumption_avg', 0.0),
            waste_generation_avg=data.get('waste_generation_avg', 0.0),
            financial_cost_avg=data.get('financial_cost_avg', 0.0),
            habit_completion_avg=data.get('habit_completion_avg', 0.0),
            sustainability_score_avg=data.get('sustainability_score_avg', 0.0),
            daily_measurements=data.get('daily_measurements', []),
            trend_direction=data.get('trend_direction', ''),
            trend_rate=data.get('trend_rate', 0.0),
            notes=data.get('notes', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class ExperimentMeasurement:
    """
    Measurement taken during an experiment.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = ""
    measurement_date: datetime = field(default_factory=datetime.now)
    measurement_type: MeasurementType = MeasurementType.DAILY
    
    # Measurement values
    carbon_emissions: float = 0.0
    energy_consumption: float = 0.0
    water_consumption: float = 0.0
    waste_generation: float = 0.0
    financial_cost: float = 0.0
    financial_savings: float = 0.0
    habit_completion: float = 0.0
    sustainability_score: float = 0.0
    custom_metrics: Dict[str, float] = field(default_factory=dict)
    
    # Notes
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'measurement_date': self.measurement_date.isoformat(),
            'measurement_type': self.measurement_type.value,
            'carbon_emissions': self.carbon_emissions,
            'energy_consumption': self.energy_consumption,
            'water_consumption': self.water_consumption,
            'waste_generation': self.waste_generation,
            'financial_cost': self.financial_cost,
            'financial_savings': self.financial_savings,
            'habit_completion': self.habit_completion,
            'sustainability_score': self.sustainability_score,
            'custom_metrics': self.custom_metrics,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentMeasurement':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            experiment_id=data.get('experiment_id', ''),
            measurement_date=datetime.fromisoformat(data['measurement_date']) if data.get('measurement_date') else datetime.now(),
            measurement_type=MeasurementType(data.get('measurement_type', 'daily')),
            carbon_emissions=data.get('carbon_emissions', 0.0),
            energy_consumption=data.get('energy_consumption', 0.0),
            water_consumption=data.get('water_consumption', 0.0),
            waste_generation=data.get('waste_generation', 0.0),
            financial_cost=data.get('financial_cost', 0.0),
            financial_savings=data.get('financial_savings', 0.0),
            habit_completion=data.get('habit_completion', 0.0),
            sustainability_score=data.get('sustainability_score', 0.0),
            custom_metrics=data.get('custom_metrics', {}),
            notes=data.get('notes', ''),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class SustainabilityExperiment:
    """
    Represents a complete sustainability experiment.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    user_id: str = ""
    household_id: Optional[str] = None
    
    # Category
    category: ExperimentCategory = ExperimentCategory.OTHER
    
    # Status
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    # Timeline
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    baseline_start_date: Optional[datetime] = None
    baseline_end_date: Optional[datetime] = None
    experiment_start_date: Optional[datetime] = None
    experiment_end_date: Optional[datetime] = None
    
    # Duration settings
    baseline_duration_days: int = 14
    experiment_duration_days: int = 14
    
    # Target
    target_habits: List[str] = field(default_factory=list)
    target_categories: List[str] = field(default_factory=list)
    target_metrics: List[TargetMetric] = field(default_factory=list)
    goals: List[ExperimentGoal] = field(default_factory=list)
    
    # Measurements
    baseline_snapshot: Optional[BaselineSnapshot] = None
    measurements: List[ExperimentMeasurement] = field(default_factory=list)
    
    # Results
    comparison: Optional['ExperimentComparison'] = None
    effectiveness: Optional['EffectivenessResult'] = None
    evaluation: Optional['ExperimentEvaluation'] = None
    
    # Expected outcome
    expected_outcome: str = ""
    expected_improvement_percentage: float = 0.0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'household_id': self.household_id,
            'category': self.category.value,
            'status': self.status.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'baseline_start_date': self.baseline_start_date.isoformat() if self.baseline_start_date else None,
            'baseline_end_date': self.baseline_end_date.isoformat() if self.baseline_end_date else None,
            'experiment_start_date': self.experiment_start_date.isoformat() if self.experiment_start_date else None,
            'experiment_end_date': self.experiment_end_date.isoformat() if self.experiment_end_date else None,
            'baseline_duration_days': self.baseline_duration_days,
            'experiment_duration_days': self.experiment_duration_days,
            'target_habits': self.target_habits,
            'target_categories': self.target_categories,
            'target_metrics': [m.value for m in self.target_metrics],
            'goals': [g.to_dict() for g in self.goals],
            'baseline_snapshot': self.baseline_snapshot.to_dict() if self.baseline_snapshot else None,
            'measurements': [m.to_dict() for m in self.measurements],
            'comparison': self.comparison.to_dict() if self.comparison else None,
            'effectiveness': self.effectiveness.to_dict() if self.effectiveness else None,
            'evaluation': self.evaluation.to_dict() if self.evaluation else None,
            'expected_outcome': self.expected_outcome,
            'expected_improvement_percentage': self.expected_improvement_percentage,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'tags': self.tags,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SustainabilityExperiment':
        experiment = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            user_id=data.get('user_id', ''),
            household_id=data.get('household_id'),
            category=ExperimentCategory(data.get('category', 'other')),
            status=ExperimentStatus(data.get('status', 'draft')),
            start_date=datetime.fromisoformat(data['start_date']) if data.get('start_date') else None,
            end_date=datetime.fromisoformat(data['end_date']) if data.get('end_date') else None,
            baseline_start_date=datetime.fromisoformat(data['baseline_start_date']) if data.get('baseline_start_date') else None,
            baseline_end_date=datetime.fromisoformat(data['baseline_end_date']) if data.get('baseline_end_date') else None,
            experiment_start_date=datetime.fromisoformat(data['experiment_start_date']) if data.get('experiment_start_date') else None,
            experiment_end_date=datetime.fromisoformat(data['experiment_end_date']) if data.get('experiment_end_date') else None,
            baseline_duration_days=data.get('baseline_duration_days', 14),
            experiment_duration_days=data.get('experiment_duration_days', 14),
            target_habits=data.get('target_habits', []),
            target_categories=data.get('target_categories', []),
            target_metrics=[TargetMetric(m) for m in data.get('target_metrics', [])],
            expected_outcome=data.get('expected_outcome', ''),
            expected_improvement_percentage=data.get('expected_improvement_percentage', 0.0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            tags=data.get('tags', []),
            notes=data.get('notes', '')
        )
        
        # Load goals
        for goal_data in data.get('goals', []):
            experiment.goals.append(ExperimentGoal.from_dict(goal_data))
        
        # Load baseline snapshot
        if data.get('baseline_snapshot'):
            experiment.baseline_snapshot = BaselineSnapshot.from_dict(data['baseline_snapshot'])
        
        # Load measurements
        for measurement_data in data.get('measurements', []):
            experiment.measurements.append(ExperimentMeasurement.from_dict(measurement_data))
        
        # Load comparison, effectiveness, evaluation if present
        if data.get('comparison'):
            experiment.comparison = ExperimentComparison.from_dict(data['comparison'])
        if data.get('effectiveness'):
            experiment.effectiveness = EffectivenessResult.from_dict(data['effectiveness'])
        if data.get('evaluation'):
            experiment.evaluation = ExperimentEvaluation.from_dict(data['evaluation'])
        
        return experiment
    
    def is_active(self) -> bool:
        """Check if experiment is currently active."""
        return self.status == ExperimentStatus.ACTIVE
    
    def is_completed(self) -> bool:
        """Check if experiment is completed."""
        return self.status == ExperimentStatus.COMPLETED
    
    def get_duration_days(self) -> int:
        """Get total experiment duration in days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return self.baseline_duration_days + self.experiment_duration_days


@dataclass
class ExperimentComparison:
    """
    Comparison between baseline and experimental periods.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = ""
    
    # Baseline averages
    baseline_carbon: float = 0.0
    baseline_energy: float = 0.0
    baseline_water: float = 0.0
    baseline_waste: float = 0.0
    baseline_cost: float = 0.0
    baseline_habit_completion: float = 0.0
    baseline_sustainability: float = 0.0
    
    # Experiment averages
    experiment_carbon: float = 0.0
    experiment_energy: float = 0.0
    experiment_water: float = 0.0
    experiment_waste: float = 0.0
    experiment_cost: float = 0.0
    experiment_habit_completion: float = 0.0
    experiment_sustainability: float = 0.0
    
    # Differences (absolute)
    carbon_difference: float = 0.0
    energy_difference: float = 0.0
    water_difference: float = 0.0
    waste_difference: float = 0.0
    cost_difference: float = 0.0
    habit_completion_difference: float = 0.0
    sustainability_difference: float = 0.0
    
    # Percentage changes
    carbon_change_percentage: float = 0.0
    energy_change_percentage: float = 0.0
    water_change_percentage: float = 0.0
    waste_change_percentage: float = 0.0
    cost_change_percentage: float = 0.0
    habit_completion_change_percentage: float = 0.0
    sustainability_change_percentage: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'baseline_carbon': self.baseline_carbon,
            'baseline_energy': self.baseline_energy,
            'baseline_water': self.baseline_water,
            'baseline_waste': self.baseline_waste,
            'baseline_cost': self.baseline_cost,
            'baseline_habit_completion': self.baseline_habit_completion,
            'baseline_sustainability': self.baseline_sustainability,
            'experiment_carbon': self.experiment_carbon,
            'experiment_energy': self.experiment_energy,
            'experiment_water': self.experiment_water,
            'experiment_waste': self.experiment_waste,
            'experiment_cost': self.experiment_cost,
            'experiment_habit_completion': self.experiment_habit_completion,
            'experiment_sustainability': self.experiment_sustainability,
            'carbon_difference': self.carbon_difference,
            'energy_difference': self.energy_difference,
            'water_difference': self.water_difference,
            'waste_difference': self.waste_difference,
            'cost_difference': self.cost_difference,
            'habit_completion_difference': self.habit_completion_difference,
            'sustainability_difference': self.sustainability_difference,
            'carbon_change_percentage': self.carbon_change_percentage,
            'energy_change_percentage': self.energy_change_percentage,
            'water_change_percentage': self.water_change_percentage,
            'waste_change_percentage': self.waste_change_percentage,
            'cost_change_percentage': self.cost_change_percentage,
            'habit_completion_change_percentage': self.habit_completion_change_percentage,
            'sustainability_change_percentage': self.sustainability_change_percentage,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentComparison':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            experiment_id=data.get('experiment_id', ''),
            baseline_carbon=data.get('baseline_carbon', 0.0),
            baseline_energy=data.get('baseline_energy', 0.0),
            baseline_water=data.get('baseline_water', 0.0),
            baseline_waste=data.get('baseline_waste', 0.0),
            baseline_cost=data.get('baseline_cost', 0.0),
            baseline_habit_completion=data.get('baseline_habit_completion', 0.0),
            baseline_sustainability=data.get('baseline_sustainability', 0.0),
            experiment_carbon=data.get('experiment_carbon', 0.0),
            experiment_energy=data.get('experiment_energy', 0.0),
            experiment_water=data.get('experiment_water', 0.0),
            experiment_waste=data.get('experiment_waste', 0.0),
            experiment_cost=data.get('experiment_cost', 0.0),
            experiment_habit_completion=data.get('experiment_habit_completion', 0.0),
            experiment_sustainability=data.get('experiment_sustainability', 0.0),
            carbon_difference=data.get('carbon_difference', 0.0),
            energy_difference=data.get('energy_difference', 0.0),
            water_difference=data.get('water_difference', 0.0),
            waste_difference=data.get('waste_difference', 0.0),
            cost_difference=data.get('cost_difference', 0.0),
            habit_completion_difference=data.get('habit_completion_difference', 0.0),
            sustainability_difference=data.get('sustainability_difference', 0.0),
            carbon_change_percentage=data.get('carbon_change_percentage', 0.0),
            energy_change_percentage=data.get('energy_change_percentage', 0.0),
            water_change_percentage=data.get('water_change_percentage', 0.0),
            waste_change_percentage=data.get('waste_change_percentage', 0.0),
            cost_change_percentage=data.get('cost_change_percentage', 0.0),
            habit_completion_change_percentage=data.get('habit_completion_change_percentage', 0.0),
            sustainability_change_percentage=data.get('sustainability_change_percentage', 0.0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )
    
    def get_improvement_summary(self) -> Dict[str, Any]:
        """Get summary of improvements."""
        improvements = {}
        if self.carbon_change_percentage < 0:
            improvements['carbon'] = abs(self.carbon_change_percentage)
        if self.energy_change_percentage < 0:
            improvements['energy'] = abs(self.energy_change_percentage)
        if self.water_change_percentage < 0:
            improvements['water'] = abs(self.water_change_percentage)
        if self.waste_change_percentage < 0:
            improvements['waste'] = abs(self.waste_change_percentage)
        if self.cost_change_percentage < 0:
            improvements['cost'] = abs(self.cost_change_percentage)
        if self.habit_completion_change_percentage > 0:
            improvements['habit'] = self.habit_completion_change_percentage
        if self.sustainability_change_percentage > 0:
            improvements['sustainability'] = self.sustainability_change_percentage
        
        return improvements


@dataclass
class EffectivenessResult:
    """
    Effectiveness analysis results.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = ""
    
    # Overall effectiveness
    overall_score: float = 0.0  # 0-100
    effectiveness_grade: str = ""  # A, B, C, D, F
    
    # Component scores
    environmental_effectiveness: float = 0.0
    financial_effectiveness: float = 0.0
    behavioral_effectiveness: float = 0.0
    
    # Impact metrics
    absolute_improvement: float = 0.0
    percentage_improvement: float = 0.0
    improvement_rate: float = 0.0  # Per day
    
    # Projected impact
    monthly_impact: float = 0.0
    yearly_impact: float = 0.0
    
    # Carbon impact
    carbon_reduction_kg: float = 0.0
    water_savings_liters: float = 0.0
    waste_reduction_kg: float = 0.0
    cost_savings: float = 0.0
    
    # Recommendation
    recommendation: str = ""
    confidence: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'overall_score': self.overall_score,
            'effectiveness_grade': self.effectiveness_grade,
            'environmental_effectiveness': self.environmental_effectiveness,
            'financial_effectiveness': self.financial_effectiveness,
            'behavioral_effectiveness': self.behavioral_effectiveness,
            'absolute_improvement': self.absolute_improvement,
            'percentage_improvement': self.percentage_improvement,
            'improvement_rate': self.improvement_rate,
            'monthly_impact': self.monthly_impact,
            'yearly_impact': self.yearly_impact,
            'carbon_reduction_kg': self.carbon_reduction_kg,
            'water_savings_liters': self.water_savings_liters,
            'waste_reduction_kg': self.waste_reduction_kg,
            'cost_savings': self.cost_savings,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EffectivenessResult':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            experiment_id=data.get('experiment_id', ''),
            overall_score=data.get('overall_score', 0.0),
            effectiveness_grade=data.get('effectiveness_grade', ''),
            environmental_effectiveness=data.get('environmental_effectiveness', 0.0),
            financial_effectiveness=data.get('financial_effectiveness', 0.0),
            behavioral_effectiveness=data.get('behavioral_effectiveness', 0.0),
            absolute_improvement=data.get('absolute_improvement', 0.0),
            percentage_improvement=data.get('percentage_improvement', 0.0),
            improvement_rate=data.get('improvement_rate', 0.0),
            monthly_impact=data.get('monthly_impact', 0.0),
            yearly_impact=data.get('yearly_impact', 0.0),
            carbon_reduction_kg=data.get('carbon_reduction_kg', 0.0),
            water_savings_liters=data.get('water_savings_liters', 0.0),
            waste_reduction_kg=data.get('waste_reduction_kg', 0.0),
            cost_savings=data.get('cost_savings', 0.0),
            recommendation=data.get('recommendation', ''),
            confidence=data.get('confidence', 0.0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class ExperimentEvaluation:
    """
    Evaluation of experiment outcome.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    experiment_id: str = ""
    
    # Outcome
    outcome: ExperimentOutcome = ExperimentOutcome.INCONCLUSIVE
    outcome_description: str = ""
    
    # Goal achievement
    goals_achieved: int = 0
    goals_total: int = 0
    goal_achievement_rate: float = 0.0
    
    # Reasoning
    factors: List[str] = field(default_factory=list)
    explanation: str = ""
    key_learnings: List[str] = field(default_factory=list)
    
    # Recommendations
    should_continue: bool = False
    should_modify: bool = False
    should_abandon: bool = False
    suggested_modifications: List[str] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'experiment_id': self.experiment_id,
            'outcome': self.outcome.value,
            'outcome_description': self.outcome_description,
            'goals_achieved': self.goals_achieved,
            'goals_total': self.goals_total,
            'goal_achievement_rate': self.goal_achievement_rate,
            'factors': self.factors,
            'explanation': self.explanation,
            'key_learnings': self.key_learnings,
            'should_continue': self.should_continue,
            'should_modify': self.should_modify,
            'should_abandon': self.should_abandon,
            'suggested_modifications': self.suggested_modifications,
            'next_steps': self.next_steps,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExperimentEvaluation':
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            experiment_id=data.get('experiment_id', ''),
            outcome=ExperimentOutcome(data.get('outcome', 'inconclusive')),
            outcome_description=data.get('outcome_description', ''),
            goals_achieved=data.get('goals_achieved', 0),
            goals_total=data.get('goals_total', 0),
            goal_achievement_rate=data.get('goal_achievement_rate', 0.0),
            factors=data.get('factors', []),
            explanation=data.get('explanation', ''),
            key_learnings=data.get('key_learnings', []),
            should_continue=data.get('should_continue', False),
            should_modify=data.get('should_modify', False),
            should_abandon=data.get('should_abandon', False),
            suggested_modifications=data.get('suggested_modifications', []),
            next_steps=data.get('next_steps', []),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        )


@dataclass
class ExperimentTemplate:
    """
    Reusable experiment template.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    category: ExperimentCategory = ExperimentCategory.OTHER
    
    # Template settings
    baseline_duration_days: int = 14
    experiment_duration_days: int = 14
    target_metrics: List[TargetMetric] = field(default_factory=list)
    target_habits: List[str] = field(default_factory=list)
    
    # Expected impact
    expected_improvement_percentage: float = 0.0
    estimated_carbon_savings: float = 0.0
    estimated_cost_savings: float = 0.0
    
    # Instructions
    instructions: str = ""
    tips: List[str] = field(default_factory=list)
    resources: List[str] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    usage_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'baseline_duration_days': self.baseline_duration_days,
            'experiment_duration_days': self.experiment_duration_days,
            'target_metrics': [m.value for m in self.target_metrics],
            'target_habits': self.target_habits,
            'expected_improvement_percentage': self.expected_improvement_percentage,
            'estimated_carbon_savings': self.estimated_carbon_savings,
            'estimated_cost_savings': self.estimated_cost_savings,
            'instructions': self.instructions,
            'tips': self.tips,
            'resources': self.resources,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'usage_count': self.usage_count
        }


@dataclass
class ExperimentRecommendation:
    """
    Personalized experiment recommendation.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    template_id: Optional[str] = None
    recommendation_type: str = ""  # suggested, based_on_weakness, based_on_goal
    title: str = ""
    description: str = ""
    reason: str = ""
    confidence: float = 0.0
    
    # Expected impact
    expected_improvement_percentage: float = 0.0
    estimated_carbon_savings: float = 0.0
    estimated_cost_savings: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'template_id': self.template_id,
            'recommendation_type': self.recommendation_type,
            'title': self.title,
            'description': self.description,
            'reason': self.reason,
            'confidence': self.confidence,
            'expected_improvement_percentage': self.expected_improvement_percentage,
            'estimated_carbon_savings': self.estimated_carbon_savings,
            'estimated_cost_savings': self.estimated_cost_savings,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class ExperimentHistory:
    """
    History of user experiments.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    experiments: List[SustainabilityExperiment] = field(default_factory=list)
    
    # Statistics
    total_experiments: int = 0
    completed_experiments: int = 0
    successful_experiments: int = 0
    partially_successful: int = 0
    unsuccessful_experiments: int = 0
    
    # Success rates
    success_rate: float = 0.0
    partial_success_rate: float = 0.0
    
    # Aggregate impact
    total_carbon_saved: float = 0.0
    total_water_saved: float = 0.0
    total_waste_reduced: float = 0.0
    total_cost_saved: float = 0.0
    
    # Category breakdown
    category_breakdown: Dict[str, int] = field(default_factory=dict)
    category_success_rates: Dict[str, float] = field(default_factory=dict)
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'experiments': [e.to_dict() for e in self.experiments],
            'total_experiments': self.total_experiments,
            'completed_experiments': self.completed_experiments,
            'successful_experiments': self.successful_experiments,
            'partially_successful': self.partially_successful,
            'unsuccessful_experiments': self.unsuccessful_experiments,
            'success_rate': self.success_rate,
            'partial_success_rate': self.partial_success_rate,
            'total_carbon_saved': self.total_carbon_saved,
            'total_water_saved': self.total_water_saved,
            'total_waste_reduced': self.total_waste_reduced,
            'total_cost_saved': self.total_cost_saved,
            'category_breakdown': self.category_breakdown,
            'category_success_rates': self.category_success_rates,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }