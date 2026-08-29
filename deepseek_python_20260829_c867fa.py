"""
Sustainability Experiment & Habit A/B Testing Lab - Recommendations
Generates personalized experiment recommendations.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from experiments.models import (
    ExperimentRecommendation, ExperimentTemplate,
    SustainabilityExperiment, ExperimentCategory,
    TargetMetric, ExperimentStatus
)
from experiments.templates import TemplateManager

logger = logging.getLogger(__name__)


class ExperimentRecommendationEngine:
    """
    Generates personalized experiment recommendations.
    """
    
    def __init__(self):
        """Initialize the recommendation engine."""
        self.template_manager = TemplateManager()
        logger.info("Experiment Recommendation Engine initialized")
    
    def generate_recommendations(self,
                                user_id: str,
                                user_context: Dict[str, Any],
                                previous_experiments: List[SustainabilityExperiment]) -> List[ExperimentRecommendation]:
        """
        Generate personalized experiment recommendations.
        
        Args:
            user_id: User ID
            user_context: User preferences and goals
            previous_experiments: Previous experiments
        
        Returns:
            List[ExperimentRecommendation]: Recommendations
        """
        recommendations = []
        
        # 1. Based on weak categories
        weak_categories = self._identify_weak_categories(previous_experiments)
        recs = self._recommend_for_weak_categories(weak_categories, user_id)
        recommendations.extend(recs)
        
        # 2. Based on user goals
        recs = self._recommend_for_goals(user_context.get('goals', []), user_id)
        recommendations.extend(recs)
        
        # 3. Based on successful previous experiments
        recs = self._recommend_similar_to_successful(previous_experiments, user_id)
        recommendations.extend(recs)
        
        # 4. Based on unsuccessful previous experiments (different approach)
        recs = self._recommend_different_approach(previous_experiments, user_id)
        recommendations.extend(recs)
        
        # 5. General recommendations (new users)
        if not previous_experiments:
            recs = self._recommend_general(user_id)
            recommendations.extend(recs)
        
        # Remove duplicates and sort by confidence
        unique_recs = self._deduplicate(recommendations)
        sorted_recs = sorted(unique_recs, key=lambda x: x.confidence, reverse=True)
        
        return sorted_recs[:5]  # Return top 5
    
    def _identify_weak_categories(self, 
                                 experiments: List[SustainabilityExperiment]) -> List[ExperimentCategory]:
        """
        Identify weak sustainability categories from previous experiments.
        """
        category_scores = {}
        
        for exp in experiments:
            if exp.status == ExperimentStatus.COMPLETED and exp.effectiveness:
                if exp.category not in category_scores:
                    category_scores[exp.category] = []
                category_scores[exp.category].append(exp.effectiveness.overall_score)
        
        weak_categories = []
        for category, scores in category_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score < 50:
                weak_categories.append(category)
        
        return weak_categories
    
    def _recommend_for_weak_categories(self, 
                                      weak_categories: List[ExperimentCategory],
                                      user_id: str) -> List[ExperimentRecommendation]:
        """
        Generate recommendations for weak categories.
        """
        recommendations = []
        
        for category in weak_categories:
            templates = self.template_manager.get_templates_by_category(category)
            
            for template in templates[:2]:  # Top 2 templates per category
                recommendation = ExperimentRecommendation(
                    user_id=user_id,
                    template_id=template.id,
                    recommendation_type="based_on_weakness",
                    title=f"Improve Your {category.value.title()} Performance",
                    description=template.description,
                    reason=f"This experiment targets {category.value}, which has room for improvement based on your history",
                    confidence=0.7,
                    expected_improvement_percentage=template.expected_improvement_percentage,
                    estimated_carbon_savings=template.estimated_carbon_savings,
                    estimated_cost_savings=template.estimated_cost_savings
                )
                recommendations.append(recommendation)
        
        return recommendations
    
    def _recommend_for_goals(self, 
                            goals: List[str],
                            user_id: str) -> List[ExperimentRecommendation]:
        """
        Generate recommendations based on user goals.
        """
        recommendations = []
        
        if not goals:
            return recommendations
        
        all_templates = self.template_manager.get_all_templates()
        
        for goal in goals:
            for template in all_templates:
                if goal.lower() in template.name.lower() or goal.lower() in template.category.value:
                    recommendation = ExperimentRecommendation(
                        user_id=user_id,
                        template_id=template.id,
                        recommendation_type="based_on_goal",
                        title=f"Experiment to Achieve: {goal}",
                        description=template.description,
                        reason=f"This experiment aligns with your goal: {goal}",
                        confidence=0.8,
                        expected_improvement_percentage=template.expected_improvement_percentage,
                        estimated_carbon_savings=template.estimated_carbon_savings,
                        estimated_cost_savings=template.estimated_cost_savings
                    )
                    recommendations.append(recommendation)
                    break  # One recommendation per goal
        
        return recommendations
    
    def _recommend_similar_to_successful(self, 
                                        experiments: List[SustainabilityExperiment],
                                        user_id: str) -> List[ExperimentRecommendation]:
        """
        Recommend similar experiments to successful ones.
        """
        recommendations = []
        
        successful = [e for e in experiments if e.status == ExperimentStatus.COMPLETED 
                     and e.effectiveness and e.effectiveness.overall_score >= 70]
        
        if not successful:
            return recommendations
        
        all_templates = self.template_manager.get_all_templates()
        
        for success in successful[:2]:  # Top 2 successful experiments
            for template in all_templates:
                if (template.category == success.category and 
                    template.id != success.id and
                    template.is_active):
                    recommendation = ExperimentRecommendation(
                        user_id=user_id,
                        template_id=template.id,
                        recommendation_type="similar_to_success",
                        title=f"Try: {template.name}",
                        description=template.description,
                        reason=f"Similar to your successful experiment in {success.category.value}",
                        confidence=0.75,
                        expected_improvement_percentage=template.expected_improvement_percentage,
                        estimated_carbon_savings=template.estimated_carbon_savings,
                        estimated_cost_savings=template.estimated_cost_savings
                    )
                    recommendations.append(recommendation)
                    break
        
        return recommendations
    
    def _recommend_different_approach(self, 
                                     experiments: List[SustainabilityExperiment],
                                     user_id: str) -> List[ExperimentRecommendation]:
        """
        Recommend different approaches for unsuccessful experiments.
        """
        recommendations = []
        
        unsuccessful = [e for e in experiments if e.status == ExperimentStatus.COMPLETED 
                       and e.effectiveness and e.effectiveness.overall_score < 40]
        
        if not unsuccessful:
            return recommendations
        
        all_templates = self.template_manager.get_all_templates()
        
        for fail in unsuccessful[:2]:  # Top 2 unsuccessful experiments
            for template in all_templates:
                if (template.category == fail.category and 
                    template.id != fail.id and
                    template.is_active):
                    recommendation = ExperimentRecommendation(
                        user_id=user_id,
                        template_id=template.id,
                        recommendation_type="different_approach",
                        title=f"Different Approach: {template.name}",
                        description=template.description,
                        reason=f"Try a different approach for {fail.category.value}",
                        confidence=0.6,
                        expected_improvement_percentage=template.expected_improvement_percentage,
                        estimated_carbon_savings=template.estimated_carbon_savings,
                        estimated_cost_savings=template.estimated_cost_savings
                    )
                    recommendations.append(recommendation)
                    break
        
        return recommendations
    
    def _recommend_general(self, user_id: str) -> List[ExperimentRecommendation]:
        """
        General recommendations for new users.
        """
        recommendations = []
        
        popular_templates = self.template_manager.get_popular_templates(3)
        
        for template in popular_templates:
            recommendation = ExperimentRecommendation(
                user_id=user_id,
                template_id=template.id,
                recommendation_type="general",
                title=f"Start with: {template.name}",
                description=template.description,
                reason=f"This is a popular experiment that many users have tried successfully",
                confidence=0.8,
                expected_improvement_percentage=template.expected_improvement_percentage,
                estimated_carbon_savings=template.estimated_carbon_savings,
                estimated_cost_savings=template.estimated_cost_savings
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _deduplicate(self, 
                    recommendations: List[ExperimentRecommendation]) -> List[ExperimentRecommendation]:
        """
        Remove duplicate recommendations.
        """
        seen = set()
        unique = []
        
        for rec in recommendations:
            key = (rec.template_id, rec.recommendation_type)
            if key not in seen:
                seen.add(key)
                unique.append(rec)
        
        return unique
    
    def get_recommendation_for_user(self,
                                   user_id: str,
                                   user_context: Dict[str, Any],
                                   previous_experiments: List[SustainabilityExperiment]) -> Optional[ExperimentRecommendation]:
        """
        Get the best recommendation for a user.
        
        Args:
            user_id: User ID
            user_context: User preferences
            previous_experiments: Previous experiments
        
        Returns:
            Optional[ExperimentRecommendation]: Best recommendation
        """
        recommendations = self.generate_recommendations(user_id, user_context, previous_experiments)
        
        if recommendations:
            return recommendations[0]
        
        return None