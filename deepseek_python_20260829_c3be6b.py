"""
Sustainability Experiment & Habit A/B Testing Lab - Experiment Templates
Provides reusable experiment templates.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from experiments.models import (
    ExperimentTemplate, ExperimentCategory, TargetMetric
)

logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Manages experiment templates.
    """
    
    def __init__(self):
        """Initialize the template manager."""
        self.templates = self._initialize_templates()
        logger.info("Template Manager initialized")
    
    def _initialize_templates(self) -> List[ExperimentTemplate]:
        """
        Initialize default experiment templates.
        """
        templates = []
        
        # 1. Reduce Electricity Usage
        templates.append(ExperimentTemplate(
            id="template_energy_1",
            name="Reduce Electricity Usage",
            description="Test whether reducing electricity usage through mindful habits reduces overall consumption",
            category=ExperimentCategory.ENERGY,
            baseline_duration_days=14,
            experiment_duration_days=14,
            target_metrics=[TargetMetric.ENERGY_CONSUMPTION, TargetMetric.CARBON_EMISSIONS, TargetMetric.FINANCIAL_COST],
            target_habits=["Turn off lights", "Unplug devices", "Use energy-efficient appliances"],
            expected_improvement_percentage=15,
            estimated_carbon_savings=25,
            estimated_cost_savings=30,
            instructions="Track daily electricity usage. Implement energy-saving habits during the experiment.",
            tips=[
                "Turn off lights when leaving rooms",
                "Unplug electronics when not in use",
                "Use appliances during off-peak hours",
                "Set thermostat a few degrees lower/higher"
            ],
            resources=["Energy monitoring app", "Smart plugs", "Energy efficiency guide"]
        ))
        
        # 2. Reduce Water Consumption
        templates.append(ExperimentTemplate(
            id="template_water_1",
            name="Reduce Water Consumption",
            description="Test the impact of water conservation habits on total water usage",
            category=ExperimentCategory.WATER,
            baseline_duration_days=14,
            experiment_duration_days=14,
            target_metrics=[TargetMetric.WATER_CONSUMPTION],
            target_habits=["Shorter showers", "Fix leaks", "Use water-efficient appliances"],
            expected_improvement_percentage=20,
            estimated_carbon_savings=10,
            estimated_cost_savings=25,
            instructions="Track daily water usage. Implement water-saving habits during the experiment.",
            tips=[
                "Limit showers to 5 minutes",
                "Fix dripping taps immediately",
                "Use full loads for laundry and dishwasher",
                "Install water-efficient showerheads"
            ],
            resources=["Water meter", "Water efficiency guide", "Leak detection kit"]
        ))
        
        # 3. Reduce Food Waste
        templates.append(ExperimentTemplate(
            id="template_waste_1",
            name="Reduce Food Waste",
            description="Test whether meal planning and conscious shopping reduces food waste",
            category=ExperimentCategory.WASTE,
            baseline_duration_days=14,
            experiment_duration_days=14,
            target_metrics=[TargetMetric.WASTE_GENERATION, TargetMetric.FINANCIAL_COST],
            target_habits=["Meal planning", "Shopping list", "Portion control"],
            expected_improvement_percentage=25,
            estimated_carbon_savings=15,
            estimated_cost_savings=40,
            instructions="Track food waste daily. Implement waste-reduction habits during the experiment.",
            tips=[
                "Plan meals for the week",
                "Create a shopping list and stick to it",
                "Store food properly to extend shelf life",
                "Use leftovers for new meals"
            ],
            resources=["Meal planning app", "Food storage guide", "Leftover recipes"]
        ))
        
        # 4. Increase Public Transportation
        templates.append(ExperimentTemplate(
            id="template_transport_1",
            name="Increase Public Transportation",
            description="Test the impact of using public transit instead of personal vehicles",
            category=ExperimentCategory.TRANSPORTATION,
            baseline_duration_days=14,
            experiment_duration_days=14,
            target_metrics=[TargetMetric.CARBON_EMISSIONS, TargetMetric.FINANCIAL_COST],
            target_habits=["Use public transit", "Carpool", "Walk short distances"],
            expected_improvement_percentage=30,
            estimated_carbon_savings=50,
            estimated_cost_savings=60,
            instructions="Track transportation modes and costs. Use public transit during the experiment.",
            tips=[
                "Plan routes using transit apps",
                "Get a transit pass for better value",
                "Combine errands to maximize efficiency",
                "Walk or bike for short trips"
            ],
            resources=["Transit app", "Route planner", "Bike sharing program"]
        ))
        
        # 5. Reduce Single-Use Products
        templates.append(ExperimentTemplate(
            id="template_waste_2",
            name="Reduce Single-Use Products",
            description="Test the impact of reducing single-use plastics and disposables",
            category=ExperimentCategory.RECYCLING,
            baseline_duration_days=14,
            experiment_duration_days=14,
            target_metrics=[TargetMetric.WASTE_GENERATION, TargetMetric.RECYCLING_RATE],
            target_habits=["Use reusable bags", "Avoid plastic packaging", "Bring own containers"],
            expected_improvement_percentage=20,
            estimated_carbon_savings=20,
            estimated_cost_savings=15,
            instructions="Track single-use product usage. Avoid single-use items during the experiment.",
            tips=[
                "Carry reusable shopping bags",
                "Use a reusable water bottle",
                "Buy products with minimal packaging",
                "Bring your own containers for takeout"
            ],
            resources=["Reusable bag set", "Water bottle", "Eco-friendly shopping guide"]
        ))
        
        # 6. Increase Recycling
        templates.append(ExperimentTemplate(
            id="template_recycling_1",
            name="Increase Recycling",
            description="Test whether improved recycling habits increase recycling rates",
            category=ExperimentCategory.RECYCLING,
            baseline_duration_days=14,
            experiment_duration_days=14,
            target_metrics=[TargetMetric.RECYCLING_RATE, TargetMetric.WASTE_GENERATION],
            target_habits=["Sort recyclables", "Rinse containers", "Check recycling guidelines"],
            expected_improvement_percentage=25,
            estimated_carbon_savings=15,
            estimated_cost_savings=5,
            instructions="Track recycling volume. Implement better recycling habits during the experiment.",
            tips=[
                "Set up separate bins for different materials",
                "Rinse containers before recycling",
                "Check local recycling guidelines",
                "Recycle electronics and hazardous materials properly"
            ],
            resources=["Recycling guide", "Sorting bins", "Recycling app"]
        ))
        
        # 7. Reduce Unnecessary Purchases
        templates.append(ExperimentTemplate(
            id="template_shopping_1",
            name="Reduce Unnecessary Purchases",
            description="Test whether mindful shopping reduces unnecessary purchases and saves money",
            category=ExperimentCategory.SHOPPING,
            baseline_duration_days=14,
            experiment_duration_days=14,
            target_metrics=[TargetMetric.FINANCIAL_COST, TargetMetric.CARBON_EMISSIONS],
            target_habits=["Wait before buying", "Buy only what's needed", "Second-hand shopping"],
            expected_improvement_percentage=20,
            estimated_carbon_savings=10,
            estimated_cost_savings=80,
            instructions="Track all purchases. Practice mindful shopping during the experiment.",
            tips=[
                "Wait 24 hours before making non-essential purchases",
                "Make a list and stick to it",
                "Consider second-hand options",
                "Buy quality items that last longer"
            ],
            resources=["Shopping list app", "Budget tracker", "Second-hand marketplace guide"]
        ))
        
        return templates
    
    def get_all_templates(self) -> List[ExperimentTemplate]:
        """
        Get all available templates.
        
        Returns:
            List[ExperimentTemplate]: All templates
        """
        return [t for t in self.templates if t.is_active]
    
    def get_template(self, template_id: str) -> Optional[ExperimentTemplate]:
        """
        Get a specific template by ID.
        
        Args:
            template_id: Template ID
        
        Returns:
            Optional[ExperimentTemplate]: Template if found
        """
        for template in self.templates:
            if template.id == template_id:
                return template
        return None
    
    def get_templates_by_category(self, 
                                 category: ExperimentCategory) -> List[ExperimentTemplate]:
        """
        Get templates by category.
        
        Args:
            category: Experiment category
        
        Returns:
            List[ExperimentTemplate]: Templates in category
        """
        return [t for t in self.templates if t.category == category and t.is_active]
    
    def get_templates_by_metric(self, metric: TargetMetric) -> List[ExperimentTemplate]:
        """
        Get templates that target a specific metric.
        
        Args:
            metric: Target metric
        
        Returns:
            List[ExperimentTemplate]: Templates targeting the metric
        """
        return [t for t in self.templates if metric in t.target_metrics and t.is_active]
    
    def get_template_count(self) -> Dict[str, int]:
        """
        Get template count by category.
        
        Returns:
            Dict: Count by category
        """
        counts = {}
        for template in self.templates:
            if template.category.value not in counts:
                counts[template.category.value] = 0
            counts[template.category.value] += 1
        return counts
    
    def get_popular_templates(self, limit: int = 5) -> List[ExperimentTemplate]:
        """
        Get most popular templates by usage count.
        
        Args:
            limit: Number of templates to return
        
        Returns:
            List[ExperimentTemplate]: Popular templates
        """
        sorted_templates = sorted(self.templates, key=lambda t: t.usage_count, reverse=True)
        return sorted_templates[:limit]
    
    def get_templates_for_user(self, user_context: Dict[str, Any]) -> List[ExperimentTemplate]:
        """
        Get recommended templates based on user context.
        
        Args:
            user_context: User preferences and goals
        
        Returns:
            List[ExperimentTemplate]: Recommended templates
        """
        recommended = []
        user_goals = user_context.get('goals', [])
        
        # Match templates with user goals
        for template in self.templates:
            if not template.is_active:
                continue
            
            # Check if template matches any user goals
            for goal in user_goals:
                if goal.lower() in template.name.lower():
                    recommended.append(template)
                    break
                
                # Check category match
                if goal.lower() in template.category.value:
                    if template not in recommended:
                        recommended.append(template)
                        break
        
        # If no matches, return all templates
        if not recommended:
            return self.get_all_templates()
        
        return recommended[:5]
    
    def create_custom_template(self, 
                              name: str,
                              category: ExperimentCategory,
                              description: str = "",
                              baseline_duration_days: int = 14,
                              experiment_duration_days: int = 14,
                              target_metrics: List[TargetMetric] = None,
                              target_habits: List[str] = None,
                              expected_improvement_percentage: float = 0.0) -> ExperimentTemplate:
        """
        Create a custom template.
        
        Args:
            name: Template name
            category: Experiment category
            description: Template description
            baseline_duration_days: Baseline duration
            experiment_duration_days: Experiment duration
            target_metrics: Target metrics
            target_habits: Target habits
            expected_improvement_percentage: Expected improvement
        
        Returns:
            ExperimentTemplate: Created template
        """
        template = ExperimentTemplate(
            name=name,
            description=description,
            category=category,
            baseline_duration_days=baseline_duration_days,
            experiment_duration_days=experiment_duration_days,
            target_metrics=target_metrics or [],
            target_habits=target_habits or [],
            expected_improvement_percentage=expected_improvement_percentage
        )
        
        self.templates.append(template)
        logger.info(f"Created custom template: {name}")
        
        return template