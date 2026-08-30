"""
Sustainable Shopping & Product Impact Analyzer - Data Models
Comprehensive models for product sustainability analysis.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
import uuid
import json


class ProductCategory(Enum):
    """Product categories for sustainability analysis."""
    ELECTRONICS = "electronics"
    APPLIANCES = "appliances"
    CLOTHING = "clothing"
    FOOTWEAR = "footwear"
    FURNITURE = "furniture"
    FOOD = "food"
    BEVERAGES = "beverages"
    COSMETICS = "cosmetics"
    CLEANING = "cleaning"
    PAPER = "paper"
    PLASTICS = "plastics"
    METALS = "metals"
    GLASS = "glass"
    TOYS = "toys"
    BOOKS = "books"
    SPORTS = "sports"
    AUTOMOTIVE = "automotive"
    GARDENING = "gardening"
    PET = "pet"
    OFFICE = "office"
    OTHER = "other"


class MaterialType(Enum):
    """Types of materials used in products."""
    PLASTIC = "plastic"
    METAL = "metal"
    GLASS = "glass"
    WOOD = "wood"
    PAPER = "paper"
    CARDBOARD = "cardboard"
    FABRIC = "fabric"
    LEATHER = "leather"
    RUBBER = "rubber"
    CERAMIC = "ceramic"
    STONE = "stone"
    COMPOSITE = "composite"
    BIOPLASTIC = "bioplastic"
    RECYCLED = "recycled"
    ORGANIC = "organic"
    SYNTHETIC = "synthetic"
    NATURAL = "natural"
    OTHER = "other"


class PackagingType(Enum):
    """Types of packaging materials."""
    PLASTIC = "plastic"
    PAPER = "paper"
    CARDBOARD = "cardboard"
    GLASS = "glass"
    METAL = "metal"
    BIODEGRADABLE = "biodegradable"
    COMPOSTABLE = "compostable"
    RECYCLABLE = "recyclable"
    REUSABLE = "reusable"
    NONE = "none"
    MIXED = "mixed"


class ProductCondition(Enum):
    """Product condition states."""
    NEW = "new"
    REFURBISHED = "refurbished"
    USED = "used"
    RENTAL = "rental"
    LEASE = "lease"
    OPEN_BOX = "open_box"
    DEMO = "demo"
    RECYCLED = "recycled"


class RecommendationType(Enum):
    """Types of product recommendations."""
    BUY = "buy"
    CONSIDER = "consider"
    AVOID = "avoid"
    DELAY = "delay"
    UPGRADE = "upgrade"
    ALTERNATIVE = "alternative"


@dataclass
class MaterialComposition:
    """
    Represents material composition of a product.
    """
    material_type: MaterialType = MaterialType.OTHER
    percentage: float = 0.0
    is_recycled: bool = False
    is_renewable: bool = False
    is_biodegradable: bool = False
    is_recyclable: bool = False
    source: str = ""
    certification: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'material_type': self.material_type.value,
            'percentage': self.percentage,
            'is_recycled': self.is_recycled,
            'is_renewable': self.is_renewable,
            'is_biodegradable': self.is_biodegradable,
            'is_recyclable': self.is_recyclable,
            'source': self.source,
            'certification': self.certification,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MaterialComposition':
        return cls(
            material_type=MaterialType(data.get('material_type', 'other')),
            percentage=data.get('percentage', 0.0),
            is_recycled=data.get('is_recycled', False),
            is_renewable=data.get('is_renewable', False),
            is_biodegradable=data.get('is_biodegradable', False),
            is_recyclable=data.get('is_recyclable', False),
            source=data.get('source', ''),
            certification=data.get('certification', ''),
            notes=data.get('notes', '')
        )


@dataclass
class PackagingAssessment:
    """
    Assessment of product packaging.
    """
    packaging_type: PackagingType = PackagingType.PLASTIC
    weight_kg: float = 0.0
    is_recyclable: bool = False
    is_biodegradable: bool = False
    is_reusable: bool = False
    is_compostable: bool = False
    contains_plastic: bool = False
    contains_paper: bool = False
    contains_metal: bool = False
    contains_glass: bool = False
    recycled_content: float = 0.0  # Percentage
    carbon_footprint_kg: float = 0.0
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'packaging_type': self.packaging_type.value,
            'weight_kg': self.weight_kg,
            'is_recyclable': self.is_recyclable,
            'is_biodegradable': self.is_biodegradable,
            'is_reusable': self.is_reusable,
            'is_compostable': self.is_compostable,
            'contains_plastic': self.contains_plastic,
            'contains_paper': self.contains_paper,
            'contains_metal': self.contains_metal,
            'contains_glass': self.contains_glass,
            'recycled_content': self.recycled_content,
            'carbon_footprint_kg': self.carbon_footprint_kg,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PackagingAssessment':
        return cls(
            packaging_type=PackagingType(data.get('packaging_type', 'plastic')),
            weight_kg=data.get('weight_kg', 0.0),
            is_recyclable=data.get('is_recyclable', False),
            is_biodegradable=data.get('is_biodegradable', False),
            is_reusable=data.get('is_reusable', False),
            is_compostable=data.get('is_compostable', False),
            contains_plastic=data.get('contains_plastic', False),
            contains_paper=data.get('contains_paper', False),
            contains_metal=data.get('contains_metal', False),
            contains_glass=data.get('contains_glass', False),
            recycled_content=data.get('recycled_content', 0.0),
            carbon_footprint_kg=data.get('carbon_footprint_kg', 0.0),
            notes=data.get('notes', '')
        )


@dataclass
class Product:
    """
    Represents a product in the shopping system.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    brand: str = ""
    model: str = ""
    category: ProductCategory = ProductCategory.OTHER
    sub_category: str = ""
    
    # Product details
    description: str = ""
    price: float = 0.0
    currency: str = "USD"
    weight_kg: float = 0.0
    dimensions: str = ""
    
    # Condition
    condition: ProductCondition = ProductCondition.NEW
    
    # Sustainability metrics
    materials: List[MaterialComposition] = field(default_factory=list)
    packaging: Optional[PackagingAssessment] = None
    
    # Durability and lifetime
    expected_lifetime_years: float = 1.0
    warranty_years: float = 0.0
    durability_rating: float = 0.0  # 0-100
    
    # Repairability
    repairability_score: float = 0.0  # 0-100
    repair_cost_estimate: float = 0.0
    repair_parts_available: bool = False
    repair_instructions_available: bool = False
    
    # Recyclability
    recyclability_score: float = 0.0  # 0-100
    recyclable_materials: List[str] = field(default_factory=list)
    recycling_program: str = ""
    
    # Reusability
    reusable: bool = False
    reusable_count: int = 0
    reusable_lifetime: float = 0.0
    
    # Certifications
    certifications: List[str] = field(default_factory=list)
    eco_labels: List[str] = field(default_factory=list)
    
    # Transport
    manufacturing_country: str = ""
    shipping_distance_km: float = 0.0
    transport_method: str = ""
    transport_carbon_kg: float = 0.0
    
    # Environmental impact
    carbon_footprint_kg: float = 0.0
    water_footprint_liters: float = 0.0
    energy_consumption_kwh: float = 0.0
    waste_generation_kg: float = 0.0
    
    # Financial
    cost_per_year: float = 0.0
    lifetime_value: float = 0.0
    long_term_savings: float = 0.0
    
    # Overall scores
    sustainability_score: float = 0.0  # 0-100
    environmental_score: float = 0.0  # 0-100
    financial_score: float = 0.0  # 0-100
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    source_url: str = ""
    image_url: str = ""
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'brand': self.brand,
            'model': self.model,
            'category': self.category.value,
            'sub_category': self.sub_category,
            'description': self.description,
            'price': self.price,
            'currency': self.currency,
            'weight_kg': self.weight_kg,
            'dimensions': self.dimensions,
            'condition': self.condition.value,
            'materials': [m.to_dict() for m in self.materials],
            'packaging': self.packaging.to_dict() if self.packaging else None,
            'expected_lifetime_years': self.expected_lifetime_years,
            'warranty_years': self.warranty_years,
            'durability_rating': self.durability_rating,
            'repairability_score': self.repairability_score,
            'repair_cost_estimate': self.repair_cost_estimate,
            'repair_parts_available': self.repair_parts_available,
            'repair_instructions_available': self.repair_instructions_available,
            'recyclability_score': self.recyclability_score,
            'recyclable_materials': self.recyclable_materials,
            'recycling_program': self.recycling_program,
            'reusable': self.reusable,
            'reusable_count': self.reusable_count,
            'reusable_lifetime': self.reusable_lifetime,
            'certifications': self.certifications,
            'eco_labels': self.eco_labels,
            'manufacturing_country': self.manufacturing_country,
            'shipping_distance_km': self.shipping_distance_km,
            'transport_method': self.transport_method,
            'transport_carbon_kg': self.transport_carbon_kg,
            'carbon_footprint_kg': self.carbon_footprint_kg,
            'water_footprint_liters': self.water_footprint_liters,
            'energy_consumption_kwh': self.energy_consumption_kwh,
            'waste_generation_kg': self.waste_generation_kg,
            'cost_per_year': self.cost_per_year,
            'lifetime_value': self.lifetime_value,
            'long_term_savings': self.long_term_savings,
            'sustainability_score': self.sustainability_score,
            'environmental_score': self.environmental_score,
            'financial_score': self.financial_score,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'source_url': self.source_url,
            'image_url': self.image_url,
            'notes': self.notes,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        product = cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            brand=data.get('brand', ''),
            model=data.get('model', ''),
            category=ProductCategory(data.get('category', 'other')),
            sub_category=data.get('sub_category', ''),
            description=data.get('description', ''),
            price=data.get('price', 0.0),
            currency=data.get('currency', 'USD'),
            weight_kg=data.get('weight_kg', 0.0),
            dimensions=data.get('dimensions', ''),
            condition=ProductCondition(data.get('condition', 'new')),
            expected_lifetime_years=data.get('expected_lifetime_years', 1.0),
            warranty_years=data.get('warranty_years', 0.0),
            durability_rating=data.get('durability_rating', 0.0),
            repairability_score=data.get('repairability_score', 0.0),
            repair_cost_estimate=data.get('repair_cost_estimate', 0.0),
            repair_parts_available=data.get('repair_parts_available', False),
            repair_instructions_available=data.get('repair_instructions_available', False),
            recyclability_score=data.get('recyclability_score', 0.0),
            recyclable_materials=data.get('recyclable_materials', []),
            recycling_program=data.get('recycling_program', ''),
            reusable=data.get('reusable', False),
            reusable_count=data.get('reusable_count', 0),
            reusable_lifetime=data.get('reusable_lifetime', 0.0),
            certifications=data.get('certifications', []),
            eco_labels=data.get('eco_labels', []),
            manufacturing_country=data.get('manufacturing_country', ''),
            shipping_distance_km=data.get('shipping_distance_km', 0.0),
            transport_method=data.get('transport_method', ''),
            transport_carbon_kg=data.get('transport_carbon_kg', 0.0),
            carbon_footprint_kg=data.get('carbon_footprint_kg', 0.0),
            water_footprint_liters=data.get('water_footprint_liters', 0.0),
            energy_consumption_kwh=data.get('energy_consumption_kwh', 0.0),
            waste_generation_kg=data.get('waste_generation_kg', 0.0),
            cost_per_year=data.get('cost_per_year', 0.0),
            lifetime_value=data.get('lifetime_value', 0.0),
            long_term_savings=data.get('long_term_savings', 0.0),
            sustainability_score=data.get('sustainability_score', 0.0),
            environmental_score=data.get('environmental_score', 0.0),
            financial_score=data.get('financial_score', 0.0),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            source_url=data.get('source_url', ''),
            image_url=data.get('image_url', ''),
            notes=data.get('notes', ''),
            tags=data.get('tags', [])
        )
        
        # Load materials
        for material_data in data.get('materials', []):
            product.materials.append(MaterialComposition.from_dict(material_data))
        
        # Load packaging
        if data.get('packaging'):
            product.packaging = PackagingAssessment.from_dict(data['packaging'])
        
        return product
    
    def calculate_sustainability_score(self) -> float:
        """Calculate overall sustainability score."""
        scores = []
        weights = []
        
        # Environmental factors (40%)
        if self.environmental_score > 0:
            scores.append(self.environmental_score)
            weights.append(0.4)
        
        # Financial factors (20%)
        if self.financial_score > 0:
            scores.append(self.financial_score)
            weights.append(0.2)
        
        # Durability (15%)
        if self.durability_rating > 0:
            scores.append(self.durability_rating)
            weights.append(0.15)
        
        # Repairability (12.5%)
        if self.repairability_score > 0:
            scores.append(self.repairability_score)
            weights.append(0.125)
        
        # Recyclability (12.5%)
        if self.recyclability_score > 0:
            scores.append(self.recyclability_score)
            weights.append(0.125)
        
        if scores and weights:
            total_weight = sum(weights)
            weighted_sum = sum(s * w for s, w in zip(scores, weights))
            self.sustainability_score = weighted_sum / total_weight
        else:
            self.sustainability_score = 0.0
        
        return self.sustainability_score


@dataclass
class EnvironmentalImpact:
    """
    Comprehensive environmental impact analysis.
    """
    product_id: str = ""
    product_name: str = ""
    
    # Carbon emissions
    manufacturing_carbon_kg: float = 0.0
    transport_carbon_kg: float = 0.0
    usage_carbon_kg: float = 0.0
    disposal_carbon_kg: float = 0.0
    total_carbon_kg: float = 0.0
    
    # Energy
    manufacturing_energy_kwh: float = 0.0
    usage_energy_kwh: float = 0.0
    total_energy_kwh: float = 0.0
    
    # Water
    manufacturing_water_liters: float = 0.0
    usage_water_liters: float = 0.0
    total_water_liters: float = 0.0
    
    # Waste
    manufacturing_waste_kg: float = 0.0
    packaging_waste_kg: float = 0.0
    end_of_life_waste_kg: float = 0.0
    total_waste_kg: float = 0.0
    
    # Impact categories
    ozone_depletion_kg: float = 0.0
    smog_potential_kg: float = 0.0
    acidification_kg: float = 0.0
    eutrophication_kg: float = 0.0
    
    # Overall scores
    overall_impact_score: float = 0.0  # 0-100 (lower is better)
    carbon_intensity: float = 0.0  # kg CO2e per dollar
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'manufacturing_carbon_kg': self.manufacturing_carbon_kg,
            'transport_carbon_kg': self.transport_carbon_kg,
            'usage_carbon_kg': self.usage_carbon_kg,
            'disposal_carbon_kg': self.disposal_carbon_kg,
            'total_carbon_kg': self.total_carbon_kg,
            'manufacturing_energy_kwh': self.manufacturing_energy_kwh,
            'usage_energy_kwh': self.usage_energy_kwh,
            'total_energy_kwh': self.total_energy_kwh,
            'manufacturing_water_liters': self.manufacturing_water_liters,
            'usage_water_liters': self.usage_water_liters,
            'total_water_liters': self.total_water_liters,
            'manufacturing_waste_kg': self.manufacturing_waste_kg,
            'packaging_waste_kg': self.packaging_waste_kg,
            'end_of_life_waste_kg': self.end_of_life_waste_kg,
            'total_waste_kg': self.total_waste_kg,
            'ozone_depletion_kg': self.ozone_depletion_kg,
            'smog_potential_kg': self.smog_potential_kg,
            'acidification_kg': self.acidification_kg,
            'eutrophication_kg': self.eutrophication_kg,
            'overall_impact_score': self.overall_impact_score,
            'carbon_intensity': self.carbon_intensity
        }


@dataclass
class FinancialAnalysis:
    """
    Comprehensive financial analysis of a product.
    """
    product_id: str = ""
    product_name: str = ""
    
    # Purchase costs
    purchase_price: float = 0.0
    tax: float = 0.0
    shipping_cost: float = 0.0
    total_initial_cost: float = 0.0
    
    # Operating costs
    annual_operating_cost: float = 0.0
    annual_maintenance_cost: float = 0.0
    annual_repair_cost: float = 0.0
    total_annual_cost: float = 0.0
    
    # Lifetime costs
    expected_lifetime_years: float = 0.0
    lifetime_operating_cost: float = 0.0
    lifetime_maintenance_cost: float = 0.0
    lifetime_repair_cost: float = 0.0
    total_lifetime_cost: float = 0.0
    
    # Value metrics
    cost_per_year: float = 0.0
    cost_per_use: float = 0.0
    lifetime_value: float = 0.0
    roi_percentage: float = 0.0
    
    # Comparisons
    new_vs_refurbished_savings: float = 0.0
    disposable_vs_reusable_savings: float = 0.0
    short_vs_long_term_savings: float = 0.0
    local_vs_imported_savings: float = 0.0
    
    # Overall scores
    financial_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'purchase_price': self.purchase_price,
            'tax': self.tax,
            'shipping_cost': self.shipping_cost,
            'total_initial_cost': self.total_initial_cost,
            'annual_operating_cost': self.annual_operating_cost,
            'annual_maintenance_cost': self.annual_maintenance_cost,
            'annual_repair_cost': self.annual_repair_cost,
            'total_annual_cost': self.total_annual_cost,
            'expected_lifetime_years': self.expected_lifetime_years,
            'lifetime_operating_cost': self.lifetime_operating_cost,
            'lifetime_maintenance_cost': self.lifetime_maintenance_cost,
            'lifetime_repair_cost': self.lifetime_repair_cost,
            'total_lifetime_cost': self.total_lifetime_cost,
            'cost_per_year': self.cost_per_year,
            'cost_per_use': self.cost_per_use,
            'lifetime_value': self.lifetime_value,
            'roi_percentage': self.roi_percentage,
            'new_vs_refurbished_savings': self.new_vs_refurbished_savings,
            'disposable_vs_reusable_savings': self.disposable_vs_reusable_savings,
            'short_vs_long_term_savings': self.short_vs_long_term_savings,
            'local_vs_imported_savings': self.local_vs_imported_savings,
            'financial_score': self.financial_score
        }


@dataclass
class PurchaseAlternative:
    """
    Represents a purchase alternative for comparison.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str = ""
    alternative_type: str = ""  # new, refurbished, reusable, local, etc.
    description: str = ""
    
    # Product details
    product_name: str = ""
    price: float = 0.0
    expected_lifetime_years: float = 0.0
    
    # Impact differences
    carbon_savings_kg: float = 0.0
    cost_savings: float = 0.0
    waste_reduction_kg: float = 0.0
    
    # Scores
    sustainability_score: float = 0.0
    recommendation_type: RecommendationType = RecommendationType.CONSIDER
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'product_id': self.product_id,
            'alternative_type': self.alternative_type,
            'description': self.description,
            'product_name': self.product_name,
            'price': self.price,
            'expected_lifetime_years': self.expected_lifetime_years,
            'carbon_savings_kg': self.carbon_savings_kg,
            'cost_savings': self.cost_savings,
            'waste_reduction_kg': self.waste_reduction_kg,
            'sustainability_score': self.sustainability_score,
            'recommendation_type': self.recommendation_type.value,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class PurchaseHistory:
    """
    Records a product purchase with impact tracking.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    product_id: str = ""
    product_name: str = ""
    purchase_date: datetime = field(default_factory=datetime.now)
    price_paid: float = 0.0
    quantity: int = 1
    
    # Impact tracking
    estimated_carbon_kg: float = 0.0
    estimated_water_liters: float = 0.0
    estimated_waste_kg: float = 0.0
    
    # Product details at time of purchase
    product_category: str = ""
    condition: str = "new"
    expected_lifetime_years: float = 0.0
    
    # Notes
    notes: str = ""
    receipt_url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'purchase_date': self.purchase_date.isoformat(),
            'price_paid': self.price_paid,
            'quantity': self.quantity,
            'estimated_carbon_kg': self.estimated_carbon_kg,
            'estimated_water_liters': self.estimated_water_liters,
            'estimated_waste_kg': self.estimated_waste_kg,
            'product_category': self.product_category,
            'condition': self.condition,
            'expected_lifetime_years': self.expected_lifetime_years,
            'notes': self.notes,
            'receipt_url': self.receipt_url
        }


@dataclass
class ProductComparison:
    """
    Comparison between multiple products.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    products: List[Product] = field(default_factory=list)
    comparison_type: str = ""  # price, sustainability, lifecycle, etc.
    created_at: datetime = field(default_factory=datetime.now)
    
    # Comparison results
    best_overall: str = ""
    best_environmental: str = ""
    best_financial: str = ""
    best_durability: str = ""
    best_repairability: str = ""
    
    # Metrics
    price_range: Tuple[float, float] = (0.0, 0.0)
    sustainability_range: Tuple[float, float] = (0.0, 0.0)
    carbon_range: Tuple[float, float] = (0.0, 0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'products': [p.to_dict() for p in self.products],
            'comparison_type': self.comparison_type,
            'created_at': self.created_at.isoformat(),
            'best_overall': self.best_overall,
            'best_environmental': self.best_environmental,
            'best_financial': self.best_financial,
            'best_durability': self.best_durability,
            'best_repairability': self.best_repairability,
            'price_range': self.price_range,
            'sustainability_range': self.sustainability_range,
            'carbon_range': self.carbon_range
        }


@dataclass
class ProductRecommendation:
    """
    Personalized product recommendation.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    product_id: str = ""
    product_name: str = ""
    recommendation_type: RecommendationType = RecommendationType.CONSIDER
    reason: str = ""
    confidence: float = 0.0
    
    # Context
    based_on_goals: List[str] = field(default_factory=list)
    based_on_habits: List[str] = field(default_factory=list)
    
    # Impact
    estimated_savings: Dict[str, float] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'product_name': self.product_name,
            'recommendation_type': self.recommendation_type.value,
            'reason': self.reason,
            'confidence': self.confidence,
            'based_on_goals': self.based_on_goals,
            'based_on_habits': self.based_on_habits,
            'estimated_savings': self.estimated_savings,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }


@dataclass
class SustainabilityScore:
    """
    Comprehensive sustainability score for a product.
    """
    product_id: str = ""
    product_name: str = ""
    
    # Component scores
    environmental_score: float = 0.0  # 0-100
    social_score: float = 0.0  # 0-100
    economic_score: float = 0.0  # 0-100
    lifecycle_score: float = 0.0  # 0-100
    
    # Overall
    overall_score: float = 0.0  # 0-100
    grade: str = ""  # A, B, C, D, F
    
    # Breakdown
    carbon_emissions: float = 0.0  # kg CO2e
    water_usage: float = 0.0  # liters
    waste_generated: float = 0.0  # kg
    renewable_energy: float = 0.0  # percentage
    recycled_materials: float = 0.0  # percentage
    
    # Ratings
    durability_rating: float = 0.0
    repairability_rating: float = 0.0
    recyclability_rating: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'environmental_score': self.environmental_score,
            'social_score': self.social_score,
            'economic_score': self.economic_score,
            'lifecycle_score': self.lifecycle_score,
            'overall_score': self.overall_score,
            'grade': self.grade,
            'carbon_emissions': self.carbon_emissions,
            'water_usage': self.water_usage,
            'waste_generated': self.waste_generated,
            'renewable_energy': self.renewable_energy,
            'recycled_materials': self.recycled_materials,
            'durability_rating': self.durability_rating,
            'repairability_rating': self.repairability_rating,
            'recyclability_rating': self.recyclability_rating
        }


@dataclass
class RepairabilityScore:
    """
    Detailed repairability scoring for a product.
    """
    product_id: str = ""
    product_name: str = ""
    overall_score: float = 0.0
    
    # Component scores
    parts_availability: float = 0.0  # 0-100
    repair_instructions: float = 0.0  # 0-100
    tool_requirements: float = 0.0  # 0-100
    repair_complexity: float = 0.0  # 0-100
    cost_effectiveness: float = 0.0  # 0-100
    
    # Additional factors
    replaceable_parts: List[str] = field(default_factory=list)
    repair_guide_available: bool = False
    service_centers_available: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'overall_score': self.overall_score,
            'parts_availability': self.parts_availability,
            'repair_instructions': self.repair_instructions,
            'tool_requirements': self.tool_requirements,
            'repair_complexity': self.repair_complexity,
            'cost_effectiveness': self.cost_effectiveness,
            'replaceable_parts': self.replaceable_parts,
            'repair_guide_available': self.repair_guide_available,
            'service_centers_available': self.service_centers_available
        }


@dataclass
class RecyclabilityScore:
    """
    Detailed recyclability scoring for a product.
    """
    product_id: str = ""
    product_name: str = ""
    overall_score: float = 0.0
    
    # Component scores
    material_recyclability: float = 0.0  # 0-100
    product_disassembly: float = 0.0  # 0-100
    recycling_infrastructure: float = 0.0  # 0-100
    recycled_content: float = 0.0  # 0-100
    
    # Additional factors
    recyclable_materials: List[str] = field(default_factory=list)
    recycling_program_available: bool = False
    recycling_rate: float = 0.0  # Percentage
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'product_id': self.product_id,
            'product_name': self.product_name,
            'overall_score': self.overall_score,
            'material_recyclability': self.material_recyclability,
            'product_disassembly': self.product_disassembly,
            'recycling_infrastructure': self.recycling_infrastructure,
            'recycled_content': self.recycled_content,
            'recyclable_materials': self.recyclable_materials,
            'recycling_program_available': self.recycling_program_available,
            'recycling_rate': self.recycling_rate
        }