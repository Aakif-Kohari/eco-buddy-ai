"""
Sustainable Shopping & Product Impact Analyzer - Core Analysis Engine
Main analysis engine for product sustainability evaluation.
"""

import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple

from shopping.models import (
    Product, ProductCategory, MaterialComposition, PackagingAssessment,
    EnvironmentalImpact, FinancialAnalysis, PurchaseAlternative,
    PurchaseHistory, ProductComparison, SustainabilityScore,
    RepairabilityScore, RecyclabilityScore, ProductRecommendation,
    RecommendationType, ProductCondition, MaterialType, PackagingType
)

logger = logging.getLogger(__name__)


class ShoppingAnalyzer:
    """
    Core analyzer for sustainable shopping.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.environmental_calculator = None
        self.financial_analyzer = None
        self.lifecycle_analyzer = None
        self.comparator = None
        
        # Initialize sub-analyzers
        from shopping.environmental import EnvironmentalCalculator
        from shopping.financial import FinancialAnalyzer
        from shopping.lifecycle import LifecycleAnalyzer
        from shopping.comparisons import ProductComparator
        
        self.environmental_calculator = EnvironmentalCalculator()
        self.financial_analyzer = FinancialAnalyzer()
        self.lifecycle_analyzer = LifecycleAnalyzer()
        self.comparator = ProductComparator()
        
        logger.info("Shopping Analyzer initialized")
    
    def analyze_product(self, product: Product, 
                       user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Comprehensive product analysis.
        
        Args:
            product: Product to analyze
            user_context: Optional user preferences and goals
        
        Returns:
            Dict containing complete analysis results
        """
        logger.info(f"Analyzing product: {product.name}")
        
        results = {
            'product': product.to_dict(),
            'environmental_impact': None,
            'financial_analysis': None,
            'lifecycle_assessment': None,
            'sustainability_score': None,
            'repairability': None,
            'recyclability': None,
            'recommendations': [],
            'alternatives': []
        }
        
        # Calculate environmental impact
        results['environmental_impact'] = self.environmental_calculator.calculate_impact(product)
        
        # Perform financial analysis
        results['financial_analysis'] = self.financial_analyzer.analyze(product)
        
        # Assess lifecycle
        results['lifecycle_assessment'] = self.lifecycle_analyzer.assess_lifecycle(product)
        
        # Calculate sustainability score
        results['sustainability_score'] = self._calculate_sustainability_score(product)
        
        # Assess repairability
        results['repairability'] = self._assess_repairability(product)
        
        # Assess recyclability
        results['recyclability'] = self._assess_recyclability(product)
        
        # Generate recommendations
        if user_context:
            results['recommendations'] = self._generate_recommendations(product, user_context)
            results['alternatives'] = self._find_alternatives(product, user_context)
        
        logger.info(f"Completed analysis for product: {product.name}")
        return results
    
    def _calculate_sustainability_score(self, product: Product) -> SustainabilityScore:
        """
        Calculate comprehensive sustainability score.
        """
        score = SustainabilityScore(
            product_id=product.id,
            product_name=product.name
        )
        
        # Calculate component scores
        score.environmental_score = self._calculate_environmental_score(product)
        score.social_score = self._calculate_social_score(product)
        score.economic_score = self._calculate_economic_score(product)
        score.lifecycle_score = self._calculate_lifecycle_score(product)
        
        # Calculate overall score
        score.overall_score = (
            score.environmental_score * 0.4 +
            score.social_score * 0.2 +
            score.economic_score * 0.2 +
            score.lifecycle_score * 0.2
        )
        
        # Determine grade
        if score.overall_score >= 80:
            score.grade = "A"
        elif score.overall_score >= 65:
            score.grade = "B"
        elif score.overall_score >= 50:
            score.grade = "C"
        elif score.overall_score >= 35:
            score.grade = "D"
        else:
            score.grade = "F"
        
        # Calculate additional metrics
        score.carbon_emissions = product.carbon_footprint_kg
        score.water_usage = product.water_footprint_liters
        score.waste_generated = product.waste_generation_kg
        
        # Calculate material metrics
        if product.materials:
            total_materials = len(product.materials)
            recycled = sum(1 for m in product.materials if m.is_recycled)
            renewable = sum(1 for m in product.materials if m.is_renewable)
            
            score.recycled_materials = (recycled / total_materials) * 100 if total_materials > 0 else 0
            score.renewable_energy = (renewable / total_materials) * 100 if total_materials > 0 else 0
        
        # Ratings
        score.durability_rating = product.durability_rating
        score.repairability_rating = product.repairability_score
        score.recyclability_rating = product.recyclability_score
        
        return score
    
    def _calculate_environmental_score(self, product: Product) -> float:
        """
        Calculate environmental score.
        """
        scores = []
        weights = []
        
        # Carbon footprint (lower is better, max 100)
        if product.carbon_footprint_kg > 0:
            carbon_score = max(0, 100 - (product.carbon_footprint_kg / 10))
            scores.append(carbon_score)
            weights.append(0.3)
        
        # Water footprint (lower is better)
        if product.water_footprint_liters > 0:
            water_score = max(0, 100 - (product.water_footprint_liters / 100))
            scores.append(water_score)
            weights.append(0.2)
        
        # Waste generation (lower is better)
        if product.waste_generation_kg > 0:
            waste_score = max(0, 100 - (product.waste_generation_kg / 5))
            scores.append(waste_score)
            weights.append(0.2)
        
        # Recyclability
        if product.recyclability_score > 0:
            scores.append(product.recyclability_score)
            weights.append(0.15)
        
        # Packaging impact
        if product.packaging:
            packaging_score = self._assess_packaging_impact(product.packaging)
            scores.append(packaging_score)
            weights.append(0.15)
        
        if scores and weights:
            total_weight = sum(weights)
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            return weighted_sum / total_weight
        
        return 50.0
    
    def _assess_packaging_impact(self, packaging: PackagingAssessment) -> float:
        """
        Assess packaging environmental impact.
        """
        score = 100.0
        
        # Penalties
        if packaging.contains_plastic:
            score -= 20
        if not packaging.is_recyclable:
            score -= 15
        if not packaging.is_biodegradable and not packaging.is_compostable:
            score -= 10
        if packaging.weight_kg > 0.5:
            score -= min(20, packaging.weight_kg * 10)
        
        # Bonuses
        if packaging.is_reusable:
            score += 10
        if packaging.recycled_content > 50:
            score += 10
        
        return max(0, min(100, score))
    
    def _calculate_social_score(self, product: Product) -> float:
        """
        Calculate social score.
        """
        score = 50.0
        
        # Certifications
        if product.certifications:
            score += min(20, len(product.certifications) * 5)
        
        # Eco labels
        if product.eco_labels:
            score += min(20, len(product.eco_labels) * 5)
        
        # Fair trade or ethical sourcing indicators
        if any('fair' in cert.lower() or 'ethical' in cert.lower() 
               for cert in product.certifications + product.eco_labels):
            score += 15
        
        # Manufacturing location (rough proxy)
        if product.manufacturing_country:
            # Simplified: assume developed countries have better labor standards
            developed = ['USA', 'Canada', 'UK', 'Germany', 'France', 'Japan', 'Australia']
            if product.manufacturing_country in developed:
                score += 10
        
        return min(100, max(0, score))
    
    def _calculate_economic_score(self, product: Product) -> float:
        """
        Calculate economic score.
        """
        score = 50.0
        
        # Cost per year (lower is better)
        if product.cost_per_year > 0:
            cost_score = max(0, 100 - (product.cost_per_year / 100))
            score += cost_score * 0.3
        
        # Lifetime value (higher is better)
        if product.lifetime_value > 0:
            lifetime_score = min(100, product.lifetime_value / 10)
            score += lifetime_score * 0.3
        
        # Long-term savings
        if product.long_term_savings > 0:
            savings_score = min(100, product.long_term_savings / 50)
            score += savings_score * 0.2
        
        # Price competitiveness
        if product.price > 0:
            # Compare to average prices (simplified)
            avg_price = self._get_average_price(product.category)
            if avg_price > 0:
                ratio = product.price / avg_price
                if ratio < 0.8:
                    price_score = 80 + (1 - ratio) * 100
                elif ratio < 1.2:
                    price_score = 70
                else:
                    price_score = max(0, 100 - (ratio - 1) * 100)
                score += price_score * 0.2
        
        return min(100, max(0, score))
    
    def _get_average_price(self, category: ProductCategory) -> float:
        """
        Get average price for a category.
        """
        # Simplified average prices
        averages = {
            ProductCategory.ELECTRONICS: 500,
            ProductCategory.APPLIANCES: 400,
            ProductCategory.CLOTHING: 50,
            ProductCategory.FOOTWEAR: 75,
            ProductCategory.FURNITURE: 300,
            ProductCategory.FOOD: 20,
            ProductCategory.BEVERAGES: 10,
            ProductCategory.COSMETICS: 25,
            ProductCategory.CLEANING: 15
        }
        return averages.get(category, 100)
    
    def _calculate_lifecycle_score(self, product: Product) -> float:
        """
        Calculate lifecycle score.
        """
        score = 50.0
        
        # Expected lifetime
        if product.expected_lifetime_years > 0:
            lifetime_score = min(100, product.expected_lifetime_years * 10)
            score += lifetime_score * 0.3
        
        # Durability
        if product.durability_rating > 0:
            score += product.durability_rating * 0.25
        
        # Repairability
        if product.repairability_score > 0:
            score += product.repairability_score * 0.25
        
        # Recyclability
        if product.recyclability_score > 0:
            score += product.recyclability_score * 0.2
        
        return min(100, max(0, score))
    
    def _assess_repairability(self, product: Product) -> RepairabilityScore:
        """
        Assess product repairability.
        """
        score = RepairabilityScore(
            product_id=product.id,
            product_name=product.name
        )
        
        # Parts availability
        score.parts_availability = 50
        if product.repair_parts_available:
            score.parts_availability = 80
        
        # Repair instructions
        score.repair_instructions = 30
        if product.repair_instructions_available:
            score.repair_instructions = 80
        
        # Tool requirements
        score.tool_requirements = 50  # Simplified
        
        # Repair complexity
        score.repair_complexity = 50  # Simplified
        
        # Cost effectiveness
        if product.repair_cost_estimate > 0:
            if product.repair_cost_estimate < product.price * 0.2:
                score.cost_effectiveness = 80
            elif product.repair_cost_estimate < product.price * 0.4:
                score.cost_effectiveness = 60
            else:
                score.cost_effectiveness = 40
        
        # Calculate overall
        score.overall_score = (
            score.parts_availability * 0.3 +
            score.repair_instructions * 0.25 +
            score.tool_requirements * 0.15 +
            score.repair_complexity * 0.15 +
            score.cost_effectiveness * 0.15
        )
        
        return score
    
    def _assess_recyclability(self, product: Product) -> RecyclabilityScore:
        """
        Assess product recyclability.
        """
        score = RecyclabilityScore(
            product_id=product.id,
            product_name=product.name
        )
        
        # Material recyclability
        if product.materials:
            scores = []
            for material in product.materials:
                if material.is_recyclable:
                    scores.append(70)
                elif material.is_biodegradable:
                    scores.append(50)
                else:
                    scores.append(30)
            score.material_recyclability = statistics.mean(scores) if scores else 50
        else:
            score.material_recyclability = 50
        
        # Product disassembly
        score.product_disassembly = 50  # Simplified
        
        # Recycling infrastructure
        score.recycling_infrastructure = 60  # Simplified
        
        # Recycled content
        if product.materials:
            total_materials = len(product.materials)
            recycled_materials = sum(1 for m in product.materials if m.is_recycled)
            score.recycled_content = (recycled_materials / total_materials) * 100 if total_materials > 0 else 0
        
        # Calculate overall
        score.overall_score = (
            score.material_recyclability * 0.4 +
            score.product_disassembly * 0.2 +
            score.recycling_infrastructure * 0.2 +
            score.recycled_content * 0.2
        )
        
        return score
    
    def _generate_recommendations(self, product: Product, 
                                 user_context: Dict[str, Any]) -> List[ProductRecommendation]:
        """
        Generate personalized product recommendations.
        """
        recommendations = []
        
        # Check user goals
        user_goals = user_context.get('goals', [])
        user_habits = user_context.get('habits', [])
        user_budget = user_context.get('budget', float('inf'))
        
        # Based on sustainability score
        if product.sustainability_score >= 70:
            rec = ProductRecommendation(
                user_id=user_context.get('user_id', ''),
                product_id=product.id,
                product_name=product.name,
                recommendation_type=RecommendationType.BUY,
                reason="This product has excellent sustainability credentials.",
                confidence=0.9
            )
            recommendations.append(rec)
        elif product.sustainability_score >= 50:
            rec = ProductRecommendation(
                user_id=user_context.get('user_id', ''),
                product_id=product.id,
                product_name=product.name,
                recommendation_type=RecommendationType.CONSIDER,
                reason="This product has good sustainability features.",
                confidence=0.7
            )
            recommendations.append(rec)
        else:
            rec = ProductRecommendation(
                user_id=user_context.get('user_id', ''),
                product_id=product.id,
                product_name=product.name,
                recommendation_type=RecommendationType.AVOID,
                reason="This product has poor sustainability credentials.",
                confidence=0.8
            )
            recommendations.append(rec)
        
        # Check budget
        if user_budget < product.price:
            rec = ProductRecommendation(
                user_id=user_context.get('user_id', ''),
                product_id=product.id,
                product_name=product.name,
                recommendation_type=RecommendationType.DELAY,
                reason="Consider saving for this product or finding a more affordable alternative.",
                confidence=0.6
            )
            recommendations.append(rec)
        
        # Check if product matches goals
        if user_goals:
            for goal in user_goals:
                if goal.lower() in product.name.lower() or goal.lower() in product.category.value.lower():
                    rec = ProductRecommendation(
                        user_id=user_context.get('user_id', ''),
                        product_id=product.id,
                        product_name=product.name,
                        recommendation_type=RecommendationType.UPGRADE,
                        reason=f"This product aligns with your goal: {goal}",
                        confidence=0.8
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    def _find_alternatives(self, product: Product, 
                          user_context: Dict[str, Any]) -> List[PurchaseAlternative]:
        """
        Find sustainable alternatives to a product.
        """
        alternatives = []
        
        # Refurbished alternative
        if product.condition == ProductCondition.NEW:
            refurbed = PurchaseAlternative(
                product_id=product.id,
                alternative_type="refurbished",
                description=f"Refurbished version of {product.name}",
                product_name=f"Refurbished {product.name}",
                price=product.price * 0.7,
                expected_lifetime_years=product.expected_lifetime_years * 0.8,
                carbon_savings_kg=product.carbon_footprint_kg * 0.3,
                cost_savings=product.price * 0.3,
                waste_reduction_kg=product.waste_generation_kg * 0.5,
                sustainability_score=product.sustainability_score * 1.1,
                recommendation_type=RecommendationType.CONSIDER
            )
            alternatives.append(refurbed)
        
        # Reusable alternative
        if product.category in [ProductCategory.FOOD, ProductCategory.BEVERAGES]:
            reusable = PurchaseAlternative(
                product_id=product.id,
                alternative_type="reusable",
                description=f"Reusable alternative to {product.name}",
                product_name=f"Reusable {product.name}",
                price=product.price * 2,
                expected_lifetime_years=5,
                carbon_savings_kg=product.carbon_footprint_kg * 5,
                cost_savings=product.price * 10,
                waste_reduction_kg=product.waste_generation_kg * 10,
                sustainability_score=80,
                recommendation_type=RecommendationType.BUY
            )
            alternatives.append(reusable)
        
        # Local alternative
        if product.shipping_distance_km > 1000:
            local = PurchaseAlternative(
                product_id=product.id,
                alternative_type="local",
                description=f"Locally sourced alternative to {product.name}",
                product_name=f"Local {product.name}",
                price=product.price * 1.2,
                expected_lifetime_years=product.expected_lifetime_years,
                carbon_savings_kg=product.transport_carbon_kg,
                cost_savings=0,
                waste_reduction_kg=0,
                sustainability_score=product.sustainability_score * 1.15,
                recommendation_type=RecommendationType.CONSIDER
            )
            alternatives.append(local)
        
        return alternatives
    
    def compare_products(self, products: List[Product]) -> ProductComparison:
        """
        Compare multiple products.
        """
        return self.comparator.compare(products)
    
    def analyze_purchase_history(self, 
                                history: List[PurchaseHistory]) -> Dict[str, Any]:
        """
        Analyze purchase history for trends.
        """
        if not history:
            return {'error': 'No purchase history available'}
        
        analysis = {
            'total_purchases': len(history),
            'total_spent': sum(h.price_paid * h.quantity for h in history),
            'total_carbon': sum(h.estimated_carbon_kg for h in history),
            'total_water': sum(h.estimated_water_liters for h in history),
            'total_waste': sum(h.estimated_waste_kg for h in history),
            'category_breakdown': {},
            'monthly_trend': {},
            'improvement_trend': 0.0
        }
        
        # Category breakdown
        for purchase in history:
            category = purchase.product_category or 'other'
            if category not in analysis['category_breakdown']:
                analysis['category_breakdown'][category] = {
                    'count': 0,
                    'spent': 0,
                    'carbon': 0
                }
            analysis['category_breakdown'][category]['count'] += 1
            analysis['category_breakdown'][category]['spent'] += purchase.price_paid * purchase.quantity
            analysis['category_breakdown'][category]['carbon'] += purchase.estimated_carbon_kg
        
        # Monthly trend
        for purchase in sorted(history, key=lambda x: x.purchase_date):
            month = purchase.purchase_date.strftime('%Y-%m')
            if month not in analysis['monthly_trend']:
                analysis['monthly_trend'][month] = {
                    'count': 0,
                    'spent': 0,
                    'carbon': 0
                }
            analysis['monthly_trend'][month]['count'] += 1
            analysis['monthly_trend'][month]['spent'] += purchase.price_paid * purchase.quantity
            analysis['monthly_trend'][month]['carbon'] += purchase.estimated_carbon_kg
        
        # Calculate improvement trend
        if len(analysis['monthly_trend']) >= 2:
            months = sorted(analysis['monthly_trend'].keys())
            first = months[0]
            last = months[-1]
            
            first_carbon = analysis['monthly_trend'][first]['carbon']
            last_carbon = analysis['monthly_trend'][last]['carbon']
            
            if first_carbon > 0:
                analysis['improvement_trend'] = ((first_carbon - last_carbon) / first_carbon) * 100
        
        return analysis