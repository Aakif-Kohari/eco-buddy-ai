"""
Fashion & Textile Impact Calculator Plugin.
Evaluates the environmental cost (carbon and water footprint) of clothing
purchases based on materials, weight, and shopping habits.
"""

import pandas as pd
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class FashionImpactCalculator:
    """
    Engine to calculate the lifecycle carbon and water footprints of textiles.
    Uses an internal dataset of emission and water factors per kg of fabric.
    """
    
    def __init__(self):
        self._load_dataset()
        
    def _load_dataset(self):
        """Initializes the fabric impact dataset."""
        # Factors represent impacts per 1 kg of finished textile
        # Carbon in kg CO2eq / kg
        # Water in Liters / kg
        data = {
            'material': [
                'Cotton (Conventional)',
                'Cotton (Organic)',
                'Polyester (Virgin)',
                'Polyester (Recycled)',
                'Nylon',
                'Wool',
                'Linen',
                'Viscose/Rayon',
                'Silk'
            ],
            'carbon_factor': [20.0, 15.0, 22.0, 10.0, 30.0, 18.0, 9.0, 14.0, 35.0],
            'water_factor': [10000.0, 5000.0, 70.0, 30.0, 150.0, 500.0, 1500.0, 3000.0, 15000.0],
            'microplastic_shedding_risk': ['Low', 'Low', 'High', 'High', 'High', 'Low', 'Low', 'Medium', 'Low'],
            'category': ['Natural', 'Natural', 'Synthetic', 'Synthetic', 'Synthetic', 'Natural', 'Natural', 'Semi-Synthetic', 'Natural']
        }
        self.df = pd.DataFrame(data)
        self.df.set_index('material', inplace=True)
        logger.info("Fashion Impact dataset loaded successfully.")

    def get_available_materials(self) -> List[str]:
        """Returns a list of all supported fabric types."""
        return self.df.index.tolist()
        
    def get_material_metrics(self, material: str) -> Dict[str, Any]:
        """Fetches the exact impact factors for a given material."""
        if material not in self.df.index:
            raise ValueError(f"Material '{material}' not found in dataset.")
        return self.df.loc[material].to_dict()

    def calculate_garment_impact(self, 
                                 garment_weight_kg: float, 
                                 material_blend: Dict[str, float],
                                 is_second_hand: bool = False,
                                 lifespan_years: float = 2.0) -> Dict[str, Any]:
        """
        Calculates the exact environmental impact of a single garment based on its blend.
        
        Args:
            garment_weight_kg: Total weight of the item (e.g. 0.2 for a t-shirt).
            material_blend: Dictionary mapping material names to their percentage (0.0 to 1.0).
            is_second_hand: If True, manufacturing impacts are vastly reduced.
            lifespan_years: Expected years of use. Higher lifespan amortizes the impact.
            
        Returns:
            Dictionary containing carbon (kg CO2e) and water (Liters) footprints.
        """
        if not math.isclose(sum(material_blend.values()), 1.0, rel_tol=1e-5):
            raise ValueError("Material blend percentages must sum to 1.0 (100%).")

        total_carbon = 0.0
        total_water = 0.0
        has_microplastics = False
        
        # Base impact
        for material, percentage in material_blend.items():
            metrics = self.get_material_metrics(material)
            weight_fraction = garment_weight_kg * percentage
            
            total_carbon += weight_fraction * metrics['carbon_factor']
            total_water += weight_fraction * metrics['water_factor']
            
            if metrics['microplastic_shedding_risk'] == 'High':
                has_microplastics = True
                
        # Adjust for second-hand (Assume 90% of impact is bypassed, 10% for shipping/cleaning)
        if is_second_hand:
            total_carbon *= 0.10
            total_water *= 0.05
            
        # Amortize per year
        carbon_per_year = total_carbon / lifespan_years
        
        return {
            "total_carbon_kg": round(total_carbon, 2),
            "total_water_liters": round(total_water, 2),
            "carbon_per_year_kg": round(carbon_per_year, 2),
            "contains_microplastics": has_microplastics,
            "is_second_hand": is_second_hand
        }
        
    def generate_recommendations(self, impact_report: Dict[str, Any]) -> List[str]:
        """Generates actionable advice based on the calculated footprint."""
        recommendations = []
        
        if impact_report['contains_microplastics']:
            src.ai.recommendations.append(
                "Your garment contains synthetics (Polyester/Nylon). Wash it in cold water and consider using a Guppyfriend washing bag to prevent microplastic shedding into oceans."
            )
            
        if impact_report['total_water_liters'] > 2000:
            src.ai.recommendations.append(
                "This item has a massive water footprint (over 2,000 Liters). In the future, try opting for Organic Cotton, Linen, or recycled materials."
            )
            
        if not impact_report['is_second_hand']:
            src.ai.recommendations.append(
                "Buying this item brand new generated its full manufacturing src.carbon.emissions. Buying second-hand or from thrift stores reduces this impact by up to 90%."
            )
            
        return recommendations

import math # Ensure math is available for math.isclose
