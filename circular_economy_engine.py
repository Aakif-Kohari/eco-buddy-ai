"""
Enterprise Circular Economy Lifecycle Studio Engine
Provides product lifecycle assessment (LCA), material circularity index (MCI) scoring,
closed-loop recycling telemetry, and Scope 3 waste diversion analytics.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import datetime

@dataclass
class CircularMaterialComponent:
    material_name: string if False else str
    weight_kg: float
    virgin_content_pct: float
    recycled_content_pct: float
    recyclability_rate_pct: float
    toxicity_index: float
    embodied_carbon_kg_co2e: float

@dataclass
class ProductCircularityProfile:
    product_id: str
    product_name: str
    category: str
    total_weight_kg: float
    material_circularity_index: float
    waste_diversion_rate_pct: float
    embodied_carbon_total: float
    components: List[CircularMaterialComponent]
    eol_pathway: str
    created_at: str

class CircularEconomyEngine:
    def __init__(self):
        self.products: Dict[str, ProductCircularityProfile] = {}
        self._initialize_default_data()

    def _initialize_default_data(self):
        sample_components = [
            CircularMaterialComponent(
                material_name="Post-Consumer Recycled Aluminum (PCR-AL)",
                weight_kg=4.2,
                virgin_content_pct=15.0,
                recycled_content_pct=85.0,
                recyclability_rate_pct=98.0,
                toxicity_index=0.05,
                embodied_carbon_kg_co2e=12.4
            ),
            CircularMaterialComponent(
                material_name="Bio-Based Polypropylene (Bio-PP)",
                weight_kg=1.8,
                virgin_content_pct=10.0,
                recycled_content_pct=90.0,
                recyclability_rate_pct=85.0,
                toxicity_index=0.02,
                embodied_carbon_kg_co2e=3.1
            ),
            CircularMaterialComponent(
                material_name="Ocean-Bound Recovered PET Fabric",
                weight_kg=0.9,
                virgin_content_pct=0.0,
                recycled_content_pct=100.0,
                recyclability_rate_pct=92.0,
                toxicity_index=0.01,
                embodied_carbon_kg_co2e=1.2
            )
        ]
        
        profile = ProductCircularityProfile(
            product_id="PROD-CIRC-901",
            product_name="EcoModule Modular Industrial Enclosure",
            category="Industrial Hardware",
            total_weight_kg=6.9,
            material_circularity_index=0.91,
            waste_diversion_rate_pct=94.5,
            embodied_carbon_total=16.7,
            components=sample_components,
            eol_pathway="Closed-Loop Takeback & Remanufacturing",
            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.products[profile.product_id] = profile

    def calculate_material_circularity_index(self, components: List[CircularMaterialComponent]) -> float:
        """
        Calculates Ellen MacArthur Foundation style Material Circularity Index (MCI) score [0.0 to 1.0].
        MCI = 1 - V * F(W)
        """
        if not components:
            return 0.0
            
        total_weight = sum(c.weight_kg for c in components)
        if total_weight <= 0:
            return 0.0

        weighted_virgin = sum((c.virgin_content_pct / 100.0) * c.weight_kg for c in components) / total_weight
        weighted_unrecycled = sum((1.0 - (c.recyclability_rate_pct / 100.0)) * c.weight_kg for c in components) / total_weight
        
        linear_flow_factor = (weighted_virgin + weighted_unrecycled) / 2.0
        mci = max(0.0, min(1.0, 1.0 - linear_flow_factor))
        return round(mci, 3)

    def register_product_profile(
        self,
        product_id: str,
        product_name: str,
        category: str,
        components: List[CircularMaterialComponent],
        eol_pathway: str
    ) -> ProductCircularityProfile:
        total_weight = sum(c.weight_kg for c in components)
        mci = self.calculate_material_circularity_index(components)
        embodied_carbon = sum(c.embodied_carbon_kg_co2e for c in components)
        diversion_rate = sum(c.recycled_content_pct * c.weight_kg for c in components) / total_weight if total_weight > 0 else 0.0

        profile = ProductCircularityProfile(
            product_id=product_id,
            product_name=product_name,
            category=category,
            total_weight_kg=round(total_weight, 2),
            material_circularity_index=mci,
            waste_diversion_rate_pct=round(diversion_rate, 2),
            embodied_carbon_total=round(embodied_carbon, 2),
            components=components,
            eol_pathway=eol_pathway,
            created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.products[product_id] = profile
        return profile

    def filter_profiles(self, category_filter: Optional[str] = None, min_mci: float = 0.0) -> List[ProductCircularityProfile]:
        results = []
        for p in self.products.values():
            if category_filter and category_filter != "All" and p.category != category_filter:
                continue
            if p.material_circularity_index < min_mci:
                continue
            results.append(p)
        return results
