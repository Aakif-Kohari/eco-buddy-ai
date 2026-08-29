"""
Sustainable Shopping & Product Impact Analyzer - Recommendations Engine
Generates personalized product recommendations.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from shopping.models import (
    Product, ProductRecommendation, RecommendationType,
    PurchaseHistory, ProductCategory
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Generates personalized product recommendations.
    """
    
    def __init__(self):
        """Initialize the recommendation engine."""
        self.weights = {
            'sustainability': 0.3,
            'financial': 0.25,
            'durability': 0.15,
            'repairability': 0.1,
            'recyclability': 0.1,
            'user_preference': 0.1
        }
        logger.info("Recommendation Engine initialized")
    
    def generate_recommendations(self, 
                                products: List[Product],
                                user_context: Dict[str, Any],
                                purchase_history: List[PurchaseHistory] = None) -> List[ProductRecommendation]:
        """
        Generate personalized product recommendations.
        
        Args:
            products: Available products
            user_context: User preferences and goals
            purchase_history: Optional purchase history for personalization
        
        Returns:
            List[ProductRecommendation]: Personalized recommendations
        """
        recommendations = []
        
        if not products:
            return recommendations
        
        # Score each product
        scored_products = []
        for product in products:
            score = self._calculate_recommendation_score(product, user_context, purchase_history)
            scored_products.append((product, score))
        
        # Sort by score
        scored_products.sort(key=lambda x: x[1], reverse=True)
        
        # Generate recommendations
        for product, score in scored_products[:10]:  # Top 10
            rec_type = self._determine_recommendation_type(product, user_context, score)
            
            rec = ProductRecommendation(
                user_id=user_context.get('user_id', ''),
                product_id=product.id,
                product_name=product.name,
                recommendation_type=rec_type,
                reason=self._generate_reason(product, rec_type, user_context),
                confidence=min(1.0, score / 100),
                based_on_goals=self._match_goals(product, user_context.get('goals', [])),
                based_on_habits=self._match_habits(product, user_context.get('habits', [])),
                estimated_savings=self._calculate_estimated_savings(product, user_context)
            )
            
            recommendations.append(rec)
        
        return recommendations
    
    def _calculate_recommendation_score(self, 
                                       product: Product,
                                       user_context: Dict[str, Any],
                                       purchase_history: List[PurchaseHistory]) -> float:
        """
        Calculate recommendation score for a product.
        """
        scores = []
        weights = []
        
        # Sustainability score
        if product.sustainability_score > 0:
            scores.append(product.sustainability_score)
            weights.append(self.weights['sustainability'])
        
        # Financial score
        if product.financial_score > 0:
            scores.append(product.financial_score)
            weights.append(self.weights['financial'])
        
        # Durability
        if product.durability_rating > 0:
            scores.append(product.durability_rating)
            weights.append(self.weights['durability'])
        
        # Repairability
        if product.repairability_score > 0:
            scores.append(product.repairability_score)
            weights.append(self.weights['repairability'])
        
        # Recyclability
        if product.recyclability_score > 0:
            scores.append(product.recyclability_score)
            weights.append(self.weights['recyclability'])
        
        # User preference (based on goals and habits)
        preference_score = self._calculate_preference_score(product, user_context)
        scores.append(preference_score)
        weights.append(self.weights['user_preference'])
        
        # Purchase history adjustment
        if purchase_history:
            history_score = self._calculate_history_score(product, purchase_history)
            scores.append(history_score)
            weights.append(0.1)  # Additional weight for history
        
        # Calculate weighted average
        if scores and weights:
            total_weight = sum(weights)
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            return weighted_sum / total_weight
        
        return 50.0
    
    def _calculate_preference_score(self, 
                                   product: Product,
                                   user_context: Dict[str, Any]) -> float:
        """
        Calculate user preference score.
        """
        score = 50.0  # Base score
        
        # Check if product matches goals
        goals = user_context.get('goals', [])
        if goals:
            for goal in goals:
                if goal.lower() in product.category.value.lower():
                    score += 20
                if goal.lower() in product.name.lower():
                    score += 15
        
        # Check if product matches habits
        habits = user_context.get('habits', [])
        if habits:
            for habit in habits:
                if habit.lower() in product.category.value.lower():
                    score += 10
                if habit.lower() in product.name.lower():
                    score += 5
        
        # Check budget
        budget = user_context.get('budget', float('inf'))
        if product.price <= budget:
            score += 10
        elif product.price <= budget * 1.5:
            score += 5
        
        # Check preferred categories
        preferred_categories = user_context.get('preferred_categories', [])
        if product.category in preferred_categories:
            score += 15
        
        return min(100, max(0, score))
    
    def _calculate_history_score(self, 
                                product: Product,
                                purchase_history: List[PurchaseHistory]) -> float:
        """
        Calculate score based on purchase history.
        """
        if not purchase_history:
            return 50.0
        
        # Check if user has purchased similar products before
        similar_purchases = [
            p for p in purchase_history 
            if p.product_category == product.category.value
        ]
        
        if not similar_purchases:
            return 50.0
        
        # Calculate average spend in this category
        avg_spend = statistics.mean([p.price_paid for p in similar_purchases])
        
        # Score based on price similarity
        if product.price <= avg_spend * 1.2:
            return 70.0  # Within budget range
        elif product.price <= avg_spend * 1.5:
            return 50.0  # Slightly above budget
        else:
            return 30.0  # Significantly above budget
    
    def _determine_recommendation_type(self, 
                                      product: Product,
                                      user_context: Dict[str, Any],
                                      score: float) -> RecommendationType:
        """
        Determine recommendation type.
        """
        # Check if product is too expensive
        budget = user_context.get('budget', float('inf'))
        if product.price > budget * 1.5:
            return RecommendationType.DELAY
        
        # Check if product is sustainable
        if product.sustainability_score >= 70 and score >= 70:
            return RecommendationType.BUY
        elif product.sustainability_score >= 50 and score >= 50:
            return RecommendationType.CONSIDER
        
        # Check if product is an upgrade to existing
        if product.sustainability_score > 70 and score >= 60:
            return RecommendationType.UPGRADE
        
        # Check if there are better alternatives
        if product.sustainability_score < 50:
            return RecommendationType.AVOID
        
        return RecommendationType.CONSIDER
    
    def _generate_reason(self, 
                        product: Product,
                        rec_type: RecommendationType,
                        user_context: Dict[str, Any]) -> str:
        """
        Generate reason for recommendation.
        """
        reasons = {
            RecommendationType.BUY: f"Excellent choice! This product has a high sustainability score of {product.sustainability_score:.1f}%.",
            RecommendationType.CONSIDER: f"Good option with a sustainability score of {product.sustainability_score:.1f}%. Consider comparing with alternatives.",
            RecommendationType.AVOID: f"This product has a low sustainability score of {product.sustainability_score:.1f}%. Look for more sustainable alternatives.",
            RecommendationType.DELAY: f"This product is above your budget. Consider saving or finding a more affordable option.",
            RecommendationType.UPGRADE: f"Upgrade to this product for better sustainability ({product.sustainability_score:.1f}%).",
            RecommendationType.ALTERNATIVE: f"Consider this alternative product with similar quality but better sustainability."
        }
        
        # Add additional context based on user goals
        goals = user_context.get('goals', [])
        if goals and any(g in product.name.lower() or g in product.category.value.lower() for g in goals):
            return f"{reasons.get(rec_type, '')} This product aligns with your sustainability goals."
        
        return reasons.get(rec_type, "Consider this product based on your preferences.")
    
    def _match_goals(self, product: Product, goals: List[str]) -> List[str]:
        """
        Match product with user goals.
        """
        matched_goals = []
        
        if not goals:
            return matched_goals
        
        for goal in goals:
            if goal.lower() in product.name.lower() or goal.lower() in product.category.value.lower():
                matched_goals.append(goal)
        
        return matched_goals
    
    def _match_habits(self, product: Product, habits: List[str]) -> List[str]:
        """
        Match product with user habits.
        """
        matched_habits = []
        
        if not habits:
            return matched_habits
        
        for habit in habits:
            if habit.lower() in product.name.lower() or habit.lower() in product.category.value.lower():
                matched_habits.append(habit)
        
        return matched_habits
    
    def _calculate_estimated_savings(self, 
                                    product: Product,
                                    user_context: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate estimated savings from purchase.
        """
        savings = {
            'carbon': 0.0,
            'water': 0.0,
            'waste': 0.0,
            'cost': 0.0
        }
        
        # Carbon savings
        if product.carbon_footprint_kg > 0:
            # Compare to average product
            avg_carbon = product.carbon_footprint_kg * 1.2
            savings['carbon'] = max(0, avg_carbon - product.carbon_footprint_kg)
        
        # Water savings
        if product.water_footprint_liters > 0:
            avg_water = product.water_footprint_liters * 1.2
            savings['water'] = max(0, avg_water - product.water_footprint_liters)
        
        # Waste savings
        if product.waste_generation_kg > 0:
            avg_waste = product.waste_generation_kg * 1.2
            savings['waste'] = max(0, avg_waste - product.waste_generation_kg)
        
        # Cost savings (over lifetime)
        if product.long_term_savings > 0:
            savings['cost'] = product.long_term_savings
        elif product.cost_per_year > 0 and product.expected_lifetime_years > 0:
            avg_cost_per_year = product.cost_per_year * 1.1
            savings['cost'] = max(0, (avg_cost_per_year - product.cost_per_year) * product.expected_lifetime_years)
        
        return savings
    
    def get_sustainable_alternatives(self, 
                                    product: Product,
                                    products: List[Product]) -> List[Product]:
        """
        Find sustainable alternatives to a product.
        """
        alternatives = []
        
        for p in products:
            if p.id == product.id:
                continue
            
            # Check if it's a better alternative
            if (p.sustainability_score > product.sustainability_score and 
                p.price <= product.price * 1.2):
                alternatives.append(p)
        
        return sorted(alternatives, key=lambda x: x.sustainability_score, reverse=True)