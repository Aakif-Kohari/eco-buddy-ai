"""
Smart Circular Economy & Upcycling Exchange Engine for EcoBuddy AI
Provides item lifecycle tracking, circularity scoring, material value retention,
and smart repair/upcycling recommendations.
"""

from typing import Dict, List, Any, Optional
import math
from datetime import datetime

MATERIAL_CIRCULARITY_FACTORS = {
    "electronics": {"recyclability": 0.45, "repairability": 0.60, "carbon_intensity_kg": 45.0},
    "textiles": {"recyclability": 0.55, "repairability": 0.85, "carbon_intensity_kg": 15.0},
    "furniture_wood": {"recyclability": 0.80, "repairability": 0.90, "carbon_intensity_kg": 22.0},
    "plastics": {"recyclability": 0.30, "repairability": 0.40, "carbon_intensity_kg": 6.5},
    "metals": {"recyclability": 0.92, "repairability": 0.88, "carbon_intensity_kg": 35.0},
    "glass": {"recyclability": 0.95, "repairability": 0.30, "carbon_intensity_kg": 4.2},
    "paper_cardboard": {"recyclability": 0.88, "repairability": 0.20, "carbon_intensity_kg": 1.8},
}

UPCYCLING_IDEAS = {
    "textiles": [
        {"title": "Produce Reusable Tote Bags", "difficulty": "Easy", "co2_saved_kg": 4.5, "tools_needed": ["Needle & Thread", "Scissors"]},
        {"title": "Braided Rug / Mat", "difficulty": "Medium", "co2_saved_kg": 8.0, "tools_needed": ["Fabric Scissors", "Sewing Machine / Strong Thread"]},
        {"title": "Thermal Insulation Patchwork", "difficulty": "Hard", "co2_saved_kg": 12.5, "tools_needed": ["Sewing Kit", "Lining Material"]}
    ],
    "electronics": [
        {"title": "Home Media Server / Retro Emulator", "difficulty": "Medium", "co2_saved_kg": 35.0, "tools_needed": ["MicroSD Card", "OS Flasher"]},
        {"title": "Digital Photo Frame", "difficulty": "Easy", "co2_saved_kg": 18.0, "tools_needed": ["Stand", "Display Cable", "Power Supply"]},
        {"title": "Component Harvesting (Sensors/Motors)", "difficulty": "Hard", "co2_saved_kg": 25.0, "tools_needed": ["Soldering Iron", "Multimeter"]}
    ],
    "furniture_wood": [
        {"title": "Planter Box / Herb Garden", "difficulty": "Easy", "co2_saved_kg": 15.0, "tools_needed": ["Screws", "Screwdriver", "Waterproof Sealant"]},
        {"title": "Modular Shelving Unit", "difficulty": "Medium", "co2_saved_kg": 20.0, "tools_needed": ["Sandpaper", "Brackets", "Drill"]},
        {"title": "Upcycled Side Table", "difficulty": "Hard", "co2_saved_kg": 28.0, "tools_needed": ["Wood Stain", "Screws", "Saw"]}
    ],
    "plastics": [
        {"title": "Drip Irrigation Bottle System", "difficulty": "Easy", "co2_saved_kg": 2.0, "tools_needed": ["Perforating Needle", "Plastic Bottle"]},
        {"title": "Hanging Seedling Nursery", "difficulty": "Easy", "co2_saved_kg": 3.5, "tools_needed": ["Twine", "Utility Knife"]},
        {"title": "Desk Cable Organizers", "difficulty": "Easy", "co2_saved_kg": 1.2, "tools_needed": ["Scissors", "Adhesive"]}
    ],
    "metals": [
        {"title": "Rustic Utensil / Tool Caddy", "difficulty": "Easy", "co2_saved_kg": 5.0, "tools_needed": ["Can Opener", "Enamel Paint"]},
        {"title": "Outdoor Wind Chime", "difficulty": "Medium", "co2_saved_kg": 7.5, "tools_needed": ["Drill", "Weatherproof Cord"]},
        {"title": "Magnetic Workshop Board", "difficulty": "Medium", "co2_saved_kg": 14.0, "tools_needed": ["Wall Mounts", "Magnets"]}
    ]
}


class CircularEconomyEngine:
    """Calculates circularity index, lifespan extension benefits, and material retention."""

    def __init__(self, custom_factors: Optional[Dict[str, Dict[str, float]]] = None):
        self.factors = custom_factors or MATERIAL_CIRCULARITY_FACTORS

    def calculate_circularity_score(
        self,
        category: str,
        current_age_years: float,
        expected_lifespan_years: float,
        condition_rating: int,
        repair_attempts: int = 0
    ) -> Dict[str, Any]:
        """
        Calculates the Circularity Performance Index (0-100) and Material Retention Score.
        """
        category_key = category.lower().replace(" ", "_")
        factor = self.factors.get(category_key, {"recyclability": 0.5, "repairability": 0.5, "carbon_intensity_kg": 10.0})
        
        if expected_lifespan_years <= 0:
            expected_lifespan_years = 1.0
        
        life_ratio = min(max(current_age_years / expected_lifespan_years, 0.0), 3.0)
        condition_norm = min(max(condition_rating / 5.0, 0.2), 1.0)
        
        repair_boost = 1.0 + (repair_attempts * 0.15)
        
        circularity_index = round(
            ((factor["repairability"] * 0.4 + factor["recyclability"] * 0.3 + (1.0 - min(life_ratio * 0.3, 0.5)) * 0.3) 
             * condition_norm * repair_boost) * 100, 
            1
        )
        circularity_index = min(max(circularity_index, 5.0), 100.0)

        embodied_co2 = factor["carbon_intensity_kg"]
        retained_co2_kg = round(embodied_co2 * condition_norm * (factor["repairability"] * 0.7 + 0.3), 2)
        avoided_replacement_co2_kg = round(embodied_co2 * (1.0 if life_ratio >= 1.0 else life_ratio), 2)

        if condition_rating >= 4:
            pathway = "Direct Reuse / Resell / Community Exchange"
        elif condition_rating >= 2:
            pathway = "Upcycling & Repair Refurbishment"
        else:
            pathway = "Material Harvesting & High-Grade Recycling"

        return {
            "category": category,
            "circularity_index": circularity_index,
            "retained_embodied_co2_kg": retained_co2_kg,
            "avoided_replacement_co2_kg": avoided_replacement_co2_kg,
            "condition_norm": condition_norm,
            "recommended_pathway": pathway,
            "upcycling_recommendations": UPCYCLING_IDEAS.get(category_key, [])
        }

    def assess_item_exchange_impact(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregates environmental impact metrics across multiple exchanged or upcycled items.
        """
        total_co2_saved = 0.0
        total_embodied_retained = 0.0
        avg_circularity = 0.0
        category_breakdown = {}

        if not items:
            return {
                "total_items": 0,
                "total_co2_saved_kg": 0.0,
                "total_embodied_retained_kg": 0.0,
                "average_circularity_score": 0.0,
                "category_breakdown": {}
            }

        for item in items:
            res = self.calculate_circularity_score(
                category=item.get("category", "plastics"),
                current_age_years=float(item.get("age_years", 1.0)),
                expected_lifespan_years=float(item.get("expected_lifespan_years", 3.0)),
                condition_rating=int(item.get("condition", 3)),
                repair_attempts=int(item.get("repairs", 0))
            )
            total_co2_saved += res["avoided_replacement_co2_kg"]
            total_embodied_retained += res["retained_embodied_co2_kg"]
            avg_circularity += res["circularity_index"]
            
            cat = item.get("category", "other")
            category_breakdown[cat] = category_breakdown.get(cat, 0) + 1

        return {
            "total_items": len(items),
            "total_co2_saved_kg": round(total_co2_saved, 2),
            "total_embodied_retained_kg": round(total_embodied_retained, 2),
            "average_circularity_score": round(avg_circularity / len(items), 1),
            "category_breakdown": category_breakdown
        }
