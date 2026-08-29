"""
Sustainable Shopping & Product Impact Analyzer - Environmental Calculator
Calculates environmental impacts of products.
"""

import logging
import math
from typing import Dict, Any, Optional

from shopping.models import Product, EnvironmentalImpact, MaterialType, PackagingType

logger = logging.getLogger(__name__)


class EnvironmentalCalculator:
    """
    Calculates environmental impacts of products.
    """
    
    def __init__(self):
        """Initialize the environmental calculator."""
        self.emission_factors = self._initialize_emission_factors()
        self.water_factors = self._initialize_water_factors()
        self.energy_factors = self._initialize_energy_factors()
        logger.info("Environmental Calculator initialized")
    
    def _initialize_emission_factors(self) -> Dict[str, float]:
        """
        Initialize emission factors for different materials and processes.
        """
        return {
            # Materials (kg CO2e per kg)
            'plastic': 6.0,
            'metal': 8.0,
            'glass': 2.5,
            'wood': 1.5,
            'paper': 1.0,
            'cardboard': 0.8,
            'fabric': 4.0,
            'leather': 12.0,
            'rubber': 3.0,
            'ceramic': 3.0,
            'stone': 1.0,
            'composite': 5.0,
            'bioplastic': 2.0,
            'recycled': 1.0,
            'organic': 0.5,
            'synthetic': 8.0,
            'natural': 2.0,
            
            # Transport (kg CO2e per km)
            'sea': 0.01,
            'air': 0.5,
            'road': 0.1,
            'rail': 0.02,
            
            # Manufacturing (kg CO2e per product)
            'electronics': 50.0,
            'appliances': 100.0,
            'clothing': 20.0,
            'footwear': 15.0,
            'furniture': 30.0,
            'food': 5.0,
            'beverages': 3.0,
            'cosmetics': 10.0,
            'cleaning': 8.0,
            'paper': 5.0,
            'plastics': 10.0,
            'metals': 30.0,
            'glass': 8.0
        }
    
    def _initialize_water_factors(self) -> Dict[str, float]:
        """
        Initialize water footprint factors (liters per kg).
        """
        return {
            'plastic': 200.0,
            'metal': 300.0,
            'glass': 100.0,
            'wood': 50.0,
            'paper': 100.0,
            'cardboard': 80.0,
            'fabric': 500.0,
            'leather': 1000.0,
            'rubber': 200.0,
            'ceramic': 150.0,
            'stone': 50.0,
            'composite': 250.0,
            'bioplastic': 150.0,
            'recycled': 50.0,
            'organic': 80.0,
            'synthetic': 400.0,
            'natural': 100.0
        }
    
    def _initialize_energy_factors(self) -> Dict[str, float]:
        """
        Initialize energy consumption factors (kWh per kg).
        """
        return {
            'plastic': 10.0,
            'metal': 20.0,
            'glass': 8.0,
            'wood': 5.0,
            'paper': 6.0,
            'cardboard': 4.0,
            'fabric': 15.0,
            'leather': 25.0,
            'rubber': 12.0,
            'ceramic': 10.0,
            'stone': 4.0,
            'composite': 18.0,
            'bioplastic': 8.0,
            'recycled': 3.0,
            'organic': 6.0,
            'synthetic': 20.0,
            'natural': 8.0
        }
    
    def calculate_impact(self, product: Product) -> EnvironmentalImpact:
        """
        Calculate complete environmental impact of a product.
        
        Args:
            product: Product to analyze
        
        Returns:
            EnvironmentalImpact: Complete impact assessment
        """
        impact = EnvironmentalImpact(
            product_id=product.id,
            product_name=product.name
        )
        
        # Manufacturing impact
        manufacturing = self._calculate_manufacturing_impact(product)
        impact.manufacturing_carbon_kg = manufacturing['carbon']
        impact.manufacturing_energy_kwh = manufacturing['energy']
        impact.manufacturing_water_liters = manufacturing['water']
        impact.manufacturing_waste_kg = manufacturing['waste']
        
        # Transport impact
        transport = self._calculate_transport_impact(product)
        impact.transport_carbon_kg = transport['carbon']
        
        # Usage impact
        usage = self._calculate_usage_impact(product)
        impact.usage_carbon_kg = usage['carbon']
        impact.usage_energy_kwh = usage['energy']
        impact.usage_water_liters = usage['water']
        
        # Disposal impact
        disposal = self._calculate_disposal_impact(product)
        impact.disposal_carbon_kg = disposal['carbon']
        impact.end_of_life_waste_kg = disposal['waste']
        
        # Packaging impact
        packaging = self._calculate_packaging_impact(product)
        impact.packaging_waste_kg = packaging['waste']
        impact.total_carbon_kg += packaging['carbon']
        
        # Calculate totals
        impact.total_carbon_kg = (
            impact.manufacturing_carbon_kg +
            impact.transport_carbon_kg +
            impact.usage_carbon_kg +
            impact.disposal_carbon_kg +
            packaging['carbon']
        )
        
        impact.total_energy_kwh = (
            impact.manufacturing_energy_kwh +
            impact.usage_energy_kwh
        )
        
        impact.total_water_liters = (
            impact.manufacturing_water_liters +
            impact.usage_water_liters
        )
        
        impact.total_waste_kg = (
            impact.manufacturing_waste_kg +
            impact.packaging_waste_kg +
            impact.end_of_life_waste_kg
        )
        
        # Calculate carbon intensity (kg CO2e per dollar)
        if product.price > 0:
            impact.carbon_intensity = impact.total_carbon_kg / product.price
        
        # Calculate overall impact score (lower is better)
        impact.overall_impact_score = self._calculate_overall_impact_score(impact)
        
        return impact
    
    def _calculate_manufacturing_impact(self, product: Product) -> Dict[str, float]:
        """
        Calculate manufacturing impact.
        """
        results = {'carbon': 0.0, 'energy': 0.0, 'water': 0.0, 'waste': 0.0}
        
        # Calculate based on materials
        for material in product.materials:
            factor_key = material.material_type.value
            weight = material.percentage / 100
            
            # Carbon emissions
            carbon_factor = self.emission_factors.get(factor_key, 1.0)
            results['carbon'] += product.weight_kg * weight * carbon_factor
            
            # Energy consumption
            energy_factor = self.energy_factors.get(factor_key, 5.0)
            results['energy'] += product.weight_kg * weight * energy_factor
            
            # Water usage
            water_factor = self.water_factors.get(factor_key, 100.0)
            results['water'] += product.weight_kg * weight * water_factor
            
            # Waste generation
            results['waste'] += product.weight_kg * weight * 0.1
        
        # Add category-specific manufacturing impact
        category_factor = self.emission_factors.get(product.category.value, 10.0)
        results['carbon'] += category_factor * 0.5
        
        return results
    
    def _calculate_transport_impact(self, product: Product) -> Dict[str, float]:
        """
        Calculate transport impact.
        """
        results = {'carbon': 0.0}
        
        if product.shipping_distance_km > 0:
            transport_method = product.transport_method.lower() if product.transport_method else 'road'
            carbon_per_km = self.emission_factors.get(transport_method, 0.1)
            
            results['carbon'] = product.shipping_distance_km * carbon_per_km * product.weight_kg
        
        return results
    
    def _calculate_usage_impact(self, product: Product) -> Dict[str, float]:
        """
        Calculate usage impact.
        """
        results = {'carbon': 0.0, 'energy': 0.0, 'water': 0.0}
        
        # Energy consumption during usage
        if product.energy_consumption_kwh > 0:
            results['energy'] = product.energy_consumption_kwh
            
            # Carbon from energy usage (assuming average grid)
            results['carbon'] = product.energy_consumption_kwh * 0.5
        
        # Water usage during usage
        if product.water_footprint_liters > 0:
            results['water'] = product.water_footprint_liters
        
        return results
    
    def _calculate_disposal_impact(self, product: Product) -> Dict[str, float]:
        """
        Calculate disposal impact.
        """
        results = {'carbon': 0.0, 'waste': 0.0}
        
        # Waste generation
        results['waste'] = product.weight_kg
        
        # Carbon from disposal (landfill vs recycling)
        if product.recyclability_score > 50:
            # Recycling reduces impact
            results['carbon'] = product.weight_kg * 0.2
        else:
            # Landfill or incineration
            results['carbon'] = product.weight_kg * 1.0
        
        return results
    
    def _calculate_packaging_impact(self, product: Product) -> Dict[str, float]:
        """
        Calculate packaging impact.
        """
        results = {'carbon': 0.0, 'waste': 0.0}
        
        if product.packaging:
            packaging = product.packaging
            weight = packaging.weight_kg
            
            # Carbon emissions
            if packaging.packaging_type == PackagingType.PLASTIC:
                results['carbon'] = weight * 6.0
            elif packaging.packaging_type in [PackagingType.PAPER, PackagingType.CARDBOARD]:
                results['carbon'] = weight * 1.0
            elif packaging.packaging_type == PackagingType.GLASS:
                results['carbon'] = weight * 2.5
            elif packaging.packaging_type == PackagingType.METAL:
                results['carbon'] = weight * 8.0
            else:
                results['carbon'] = weight * 2.0
            
            # Waste
            if packaging.is_recyclable or packaging.is_biodegradable:
                results['waste'] = weight * 0.2
            else:
                results['waste'] = weight
        
        return results
    
    def _calculate_overall_impact_score(self, impact: EnvironmentalImpact) -> float:
        """
        Calculate overall impact score (0-100, lower is better).
        """
        score = 0.0
        
        # Normalize each component
        if impact.total_carbon_kg > 0:
            carbon_score = min(100, impact.total_carbon_kg * 2)
            score += carbon_score * 0.3
        
        if impact.total_energy_kwh > 0:
            energy_score = min(100, impact.total_energy_kwh * 0.5)
            score += energy_score * 0.2
        
        if impact.total_water_liters > 0:
            water_score = min(100, impact.total_water_liters * 0.01)
            score += water_score * 0.2
        
        if impact.total_waste_kg > 0:
            waste_score = min(100, impact.total_waste_kg * 5)
            score += waste_score * 0.2
        
        if impact.packaging_waste_kg > 0:
            packaging_score = min(100, impact.packaging_waste_kg * 10)
            score += packaging_score * 0.1
        
        return min(100, max(0, score))