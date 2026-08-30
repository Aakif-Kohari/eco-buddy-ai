"""
Sustainable Shopping & Product Impact Analyzer - Lifecycle Assessment
Assesses product lifecycle impacts.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from shopping.models import Product

logger = logging.getLogger(__name__)


class LifecycleAnalyzer:
    """
    Analyzes product lifecycle impacts.
    """
    
    def __init__(self):
        """Initialize the lifecycle analyzer."""
        logger.info("Lifecycle Analyzer initialized")
    
    def assess_lifecycle(self, product: Product) -> Dict[str, Any]:
        """
        Assess product lifecycle impact.
        
        Args:
            product: Product to assess
        
        Returns:
            Dict: Lifecycle assessment results
        """
        return {
            'product_id': product.id,
            'product_name': product.name,
            'expected_lifetime_years': product.expected_lifetime_years,
            'durability_rating': product.durability_rating,
            'repairability_score': product.repairability_score,
            'recyclability_score': product.recyclability_score,
            'lifecycle_stages': self._assess_lifecycle_stages(product),
            'lifecycle_scores': self._calculate_lifecycle_scores(product),
            'lifecycle_recommendations': self._generate_lifecycle_recommendations(product)
        }
    
    def _assess_lifecycle_stages(self, product: Product) -> Dict[str, Dict[str, float]]:
        """
        Assess impact at each lifecycle stage.
        """
        return {
            'raw_materials': {
                'score': self._assess_raw_materials(product),
                'carbon_impact': product.carbon_footprint_kg * 0.3
            },
            'manufacturing': {
                'score': self._assess_manufacturing(product),
                'carbon_impact': product.carbon_footprint_kg * 0.4
            },
            'transportation': {
                'score': self._assess_transportation(product),
                'carbon_impact': product.carbon_footprint_kg * 0.1
            },
            'usage': {
                'score': self._assess_usage(product),
                'carbon_impact': product.carbon_footprint_kg * 0.15
            },
            'disposal': {
                'score': self._assess_disposal(product),
                'carbon_impact': product.carbon_footprint_kg * 0.05
            }
        }
    
    def _assess_raw_materials(self, product: Product) -> float:
        """
        Assess raw materials impact.
        """
        score = 50.0
        
        if product.materials:
            material_scores = []
            for material in product.materials:
                m_score = 50.0
                
                # Recycled materials bonus
                if material.is_recycled:
                    m_score += 20
                
                # Renewable materials bonus
                if material.is_renewable:
                    m_score += 15
                
                # Biodegradable materials bonus
                if material.is_biodegradable:
                    m_score += 15
                
                # Penalty for non-recyclable
                if not material.is_recyclable:
                    m_score -= 20
                
                material_scores.append(m_score)
            
            if material_scores:
                score = statistics.mean(material_scores)
        
        return min(100, max(0, score))
    
    def _assess_manufacturing(self, product: Product) -> float:
        """
        Assess manufacturing impact.
        """
        score = 50.0
        
        # Certifications bonus
        if product.certifications:
            score += min(20, len(product.certifications) * 5)
        
        # Eco labels bonus
        if product.eco_labels:
            score += min(20, len(product.eco_labels) * 5)
        
        # Energy efficiency
        if product.energy_consumption_kwh > 0:
            if product.energy_consumption_kwh < 100:
                score += 15
            elif product.energy_consumption_kwh < 500:
                score += 5
            else:
                score -= 10
        
        return min(100, max(0, score))
    
    def _assess_transportation(self, product: Product) -> float:
        """
        Assess transportation impact.
        """
        score = 70.0
        
        # Long distance penalty
        if product.shipping_distance_km > 10000:
            score -= 30
        elif product.shipping_distance_km > 5000:
            score -= 20
        elif product.shipping_distance_km > 1000:
            score -= 10
        
        # Transport method
        if product.transport_method:
            if product.transport_method.lower() == 'sea':
                score += 10
            elif product.transport_method.lower() == 'rail':
                score += 5
            elif product.transport_method.lower() == 'air':
                score -= 20
        
        return min(100, max(0, score))
    
    def _assess_usage(self, product: Product) -> float:
        """
        Assess usage impact.
        """
        score = 50.0
        
        # Energy efficiency
        if product.energy_consumption_kwh > 0:
            if product.energy_consumption_kwh < 10:
                score += 30
            elif product.energy_consumption_kwh < 50:
                score += 20
            elif product.energy_consumption_kwh < 100:
                score += 10
            else:
                score -= 10
        
        # Water efficiency
        if product.water_footprint_liters > 0:
            if product.water_footprint_liters < 10:
                score += 20
            elif product.water_footprint_liters < 50:
                score += 10
            else:
                score -= 10
        
        # Durability (longer usage reduces impact)
        if product.durability_rating > 70:
            score += 10
        elif product.durability_rating < 30:
            score -= 10
        
        return min(100, max(0, score))
    
    def _assess_disposal(self, product: Product) -> float:
        """
        Assess disposal impact.
        """
        score = 50.0
        
        # Recyclability bonus
        if product.recyclability_score > 70:
            score += 30
        elif product.recyclability_score > 50:
            score += 15
        
        # Biodegradability bonus
        if product.materials:
            biodegradable = sum(1 for m in product.materials if m.is_biodegradable)
            if biodegradable > 0:
                score += min(20, biodegradable * 5)
        
        # Recycled materials bonus
        if product.materials:
            recycled = sum(1 for m in product.materials if m.is_recycled)
            if recycled > 0:
                score += min(20, recycled * 5)
        
        return min(100, max(0, score))
    
    def _calculate_lifecycle_scores(self, product: Product) -> Dict[str, float]:
        """
        Calculate overall lifecycle scores.
        """
        return {
            'overall': product.sustainability_score,
            'environmental': product.environmental_score,
            'economic': product.financial_score,
            'raw_materials': self._assess_raw_materials(product),
            'manufacturing': self._assess_manufacturing(product),
            'transportation': self._assess_transportation(product),
            'usage': self._assess_usage(product),
            'disposal': self._assess_disposal(product)
        }
    
    def _generate_lifecycle_recommendations(self, product: Product) -> List[str]:
        """
        Generate lifecycle recommendations.
        """
        recommendations = []
        
        # Raw materials recommendations
        raw_materials_score = self._assess_raw_materials(product)
        if raw_materials_score < 60:
            recommendations.append(
                "Consider products with more recycled or renewable materials."
            )
        
        # Manufacturing recommendations
        manufacturing_score = self._assess_manufacturing(product)
        if manufacturing_score < 60:
            recommendations.append(
                "Look for products with sustainability certifications."
            )
        
        # Transportation recommendations
        transport_score = self._assess_transportation(product)
        if transport_score < 60:
            recommendations.append(
                "Consider locally manufactured products to reduce transportation impact."
            )
        
        # Usage recommendations
        usage_score = self._assess_usage(product)
        if usage_score < 60:
            recommendations.append(
                "Choose more energy-efficient products to reduce usage impact."
            )
        
        # Disposal recommendations
        disposal_score = self._assess_disposal(product)
        if disposal_score < 60:
            recommendations.append(
                "Look for products with better recyclability or biodegradable materials."
            )
        
        # Overall recommendations
        if product.expected_lifetime_years < 3:
            recommendations.append(
                "Consider longer-lasting products to reduce overall lifecycle impact."
            )
        
        if product.repairability_score < 50:
            recommendations.append(
                "Choose products that are easier to repair to extend their life."
            )
        
        return recommendations