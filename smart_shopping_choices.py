"""
smart_shopping_choices.py
====================================
Smart Shopping Choices Module
Version: 1.0.0

This module evaluates everyday purchasing habits from a sustainability perspective:
- Product category analysis
- Packaging impact assessment
- Reusable alternatives comparison
- Consumption insights and recommendations
- Carbon footprint of shopping choices

Author: Carbon Footprint Team
Date: 2026-08-27
"""

import json
import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProductCategory(Enum):
    """Enumeration of product categories."""
    FOOD_FRESH = "food_fresh"
    FOOD_PACKAGED = "food_packaged"
    FOOD_FROZEN = "food_frozen"
    FOOD_CANNED = "food_canned"
    FOOD_ORGANIC = "food_organic"
    FOOD_LOCAL = "food_local"
    BEVERAGES = "beverages"
    ALCOHOL = "alcohol"
    CLOTHING = "clothing"
    FOOTWEAR = "footwear"
    ELECTRONICS = "electronics"
    FURNITURE = "furniture"
    HOME_GOODS = "home_goods"
    CLEANING_PRODUCTS = "cleaning_products"
    PERSONAL_CARE = "personal_care"
    BEAUTY_PRODUCTS = "beauty_products"
    PAPER_PRODUCTS = "paper_products"
    PLASTIC_PRODUCTS = "plastic_products"
    TOYS = "toys"
    BOOKS = "books"
    GARDENING = "gardening"
    PET_SUPPLIES = "pet_supplies"
    OFFICE_SUPPLIES = "office_supplies"
    SPORTS_EQUIPMENT = "sports_equipment"
    VEHICLE_ACCESSORIES = "vehicle_accessories"
    MEDICINE = "medicine"
    SUPPLEMENTS = "supplements"


class PackagingType(Enum):
    """Enumeration of packaging types."""
    NONE = "none"
    PLASTIC_SINGLE = "plastic_single"
    PLASTIC_MULTI = "plastic_multi"
    PLASTIC_BIO = "plastic_bio"
    PAPER = "paper"
    CARDBOARD = "cardboard"
    GLASS = "glass"
    METAL = "metal"
    ALUMINUM = "aluminum"
    COMPOSTABLE = "compostable"
    RECYCLED = "recycled"
    REUSABLE = "reusable"
    FOAM = "foam"
    MIXED = "mixed"


class ShoppingFrequency(Enum):
    """Enumeration of shopping frequencies."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BI_WEEKLY = "bi_weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    RARELY = "rarely"


class SustainabilityRating(Enum):
    """Enumeration of sustainability ratings."""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    VERY_POOR = "very_poor"


@dataclass
class Product:
    """Data class representing a product."""
    product_id: str
    name: str
    category: ProductCategory
    price_usd: float
    weight_kg: float
    packaging_type: PackagingType
    packaging_weight_kg: float = 0.0
    is_reusable: bool = False
    is_recyclable: bool = False
    is_compostable: bool = False
    is_organic: bool = False
    is_local: bool = False
    is_fair_trade: bool = False
    carbon_footprint_kg: float = 0.0
    water_footprint_liters: float = 0.0
    shelf_life_days: int = 30
    brand: str = "generic"
    manufacturer_location: str = "unknown"
    ingredients: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    sustainability_score: float = 0.0
    alternative_products: List[str] = field(default_factory=list)


@dataclass
class ShoppingCartItem:
    """Data class for items in a shopping cart."""
    product: Product
    quantity: int
    purchase_date: datetime
    price_paid_usd: float
    is_on_sale: bool = False
    discount_percentage: float = 0.0


@dataclass
class ShoppingTrip:
    """Data class representing a shopping trip."""
    trip_id: str
    date: datetime
    store_name: str
    location: str
    items: List[ShoppingCartItem]
    total_items: int
    total_cost_usd: float
    total_weight_kg: float
    packaging_total_kg: float
    carbon_footprint_kg: float
    water_footprint_liters: float
    transport_mode: str = "car"
    transport_distance_km: float = 0.0
    trip_duration_minutes: float = 0.0
    sustainability_rating: SustainabilityRating = SustainabilityRating.MODERATE
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ShoppingHabit:
    """Data class representing shopping habits."""
    user_id: str
    category: ProductCategory
    frequency: ShoppingFrequency
    average_spend_usd: float
    average_items: int
    preferred_store: str
    preferred_packaging: PackagingType
    sustainability_score: float
    total_annual_carbon_kg: float
    total_annual_waste_kg: float
    improvement_opportunities: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class SustainableAlternative:
    """Data class for sustainable product alternatives."""
    original_product: Product
    alternative_product: Product
    carbon_savings_kg: float
    cost_difference_usd: float
    packaging_reduction_kg: float
    water_savings_liters: float
    implementation_ease: float  # 0-1
    recommendation_priority: int
    explanation: str
    payback_period_months: float = 0.0


class ProductDatabase:
    """
    Database of products and their sustainability metrics.
    """
    
    def __init__(self):
        self._products = self._initialize_products()
        self._last_updated = datetime.now()
    
    def _initialize_products(self) -> Dict[str, Product]:
        """
        Initializes product database with sample products.
        
        Returns:
            Dictionary mapping product IDs to Product objects
        """
        products = {}
        
        # Food products
        products["FOOD001"] = Product(
            product_id="FOOD001",
            name="Fresh Organic Apples (1kg)",
            category=ProductCategory.FOOD_ORGANIC,
            price_usd=4.99,
            weight_kg=1.0,
            packaging_type=PackagingType.NONE,
            packaging_weight_kg=0.0,
            is_reusable=False,
            is_recyclable=False,
            is_compostable=True,
            is_organic=True,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=0.5,
            water_footprint_liters=500,
            shelf_life_days=14,
            brand="Organic Farms",
            manufacturer_location="Local",
            certifications=["USDA Organic"],
            sustainability_score=8.5,
            alternative_products=["FOOD002", "FOOD003"]
        )
        
        products["FOOD002"] = Product(
            product_id="FOOD002",
            name="Conventional Apples (1kg)",
            category=ProductCategory.FOOD_FRESH,
            price_usd=2.99,
            weight_kg=1.0,
            packaging_type=PackagingType.PLASTIC_SINGLE,
            packaging_weight_kg=0.02,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=1.2,
            water_footprint_liters=600,
            shelf_life_days=10,
            brand="Fruit Co",
            manufacturer_location="Mexico",
            certifications=[],
            sustainability_score=4.5,
            alternative_products=["FOOD001"]
        )
        
        products["FOOD003"] = Product(
            product_id="FOOD003",
            name="Local Fresh Apples (1kg)",
            category=ProductCategory.FOOD_LOCAL,
            price_usd=3.99,
            weight_kg=1.0,
            packaging_type=PackagingType.PAPER,
            packaging_weight_kg=0.01,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=True,
            is_organic=False,
            is_local=True,
            is_fair_trade=False,
            carbon_footprint_kg=0.3,
            water_footprint_liters=450,
            shelf_life_days=14,
            brand="Local Farm",
            manufacturer_location="Local",
            certifications=["Local Produce"],
            sustainability_score=7.8,
            alternative_products=["FOOD001"]
        )
        
        products["BEV001"] = Product(
            product_id="BEV001",
            name="Filtered Tap Water (1L)",
            category=ProductCategory.BEVERAGES,
            price_usd=0.01,
            weight_kg=1.0,
            packaging_type=PackagingType.NONE,
            packaging_weight_kg=0.0,
            is_reusable=True,
            is_recyclable=False,
            is_compostable=False,
            is_organic=False,
            is_local=True,
            is_fair_trade=False,
            carbon_footprint_kg=0.001,
            water_footprint_liters=1.0,
            shelf_life_days=365,
            brand="Municipal",
            manufacturer_location="Local",
            certifications=["Safe Drinking Water"],
            sustainability_score=9.8,
            alternative_products=["BEV002", "BEV003"]
        )
        
        products["BEV002"] = Product(
            product_id="BEV002",
            name="Bottled Spring Water (1L)",
            category=ProductCategory.BEVERAGES,
            price_usd=2.50,
            weight_kg=1.0,
            packaging_type=PackagingType.PLASTIC_SINGLE,
            packaging_weight_kg=0.04,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=0.5,
            water_footprint_liters=2.0,
            shelf_life_days=730,
            brand="Spring Water Co",
            manufacturer_location="Fiji",
            certifications=[],
            sustainability_score=2.5,
            alternative_products=["BEV001"]
        )
        
        products["BEV003"] = Product(
            product_id="BEV003",
            name="Sparkling Water in Glass (1L)",
            category=ProductCategory.BEVERAGES,
            price_usd=3.50,
            weight_kg=1.2,
            packaging_type=PackagingType.GLASS,
            packaging_weight_kg=0.5,
            is_reusable=True,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=0.4,
            water_footprint_liters=1.5,
            shelf_life_days=365,
            brand="Premium Glass",
            manufacturer_location="Italy",
            certifications=[],
            sustainability_score=7.0,
            alternative_products=["BEV001", "BEV002"]
        )
        
        # Clothing products
        products["CLO001"] = Product(
            product_id="CLO001",
            name="Organic Cotton T-Shirt",
            category=ProductCategory.CLOTHING,
            price_usd=29.99,
            weight_kg=0.2,
            packaging_type=PackagingType.PAPER,
            packaging_weight_kg=0.02,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=True,
            is_organic=True,
            is_local=False,
            is_fair_trade=True,
            carbon_footprint_kg=5.0,
            water_footprint_liters=2500,
            shelf_life_days=1000,
            brand="EcoWear",
            manufacturer_location="India",
            certifications=["GOTS", "Fair Trade"],
            sustainability_score=8.2,
            alternative_products=["CLO002", "CLO003"]
        )
        
        products["CLO002"] = Product(
            product_id="CLO002",
            name="Standard Cotton T-Shirt",
            category=ProductCategory.CLOTHING,
            price_usd=14.99,
            weight_kg=0.2,
            packaging_type=PackagingType.PLASTIC_SINGLE,
            packaging_weight_kg=0.03,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=8.0,
            water_footprint_liters=3500,
            shelf_life_days=800,
            brand="FastFashion",
            manufacturer_location="Bangladesh",
            certifications=[],
            sustainability_score=3.5,
            alternative_products=["CLO001"]
        )
        
        products["CLO003"] = Product(
            product_id="CLO003",
            name="Recycled Polyester T-Shirt",
            category=ProductCategory.CLOTHING,
            price_usd=24.99,
            weight_kg=0.18,
            packaging_type=PackagingType.RECYCLED,
            packaging_weight_kg=0.02,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=True,
            carbon_footprint_kg=6.0,
            water_footprint_liters=2000,
            shelf_life_days=900,
            brand="RecycleWear",
            manufacturer_location="Vietnam",
            certifications=["Fair Trade", "Recycled Content"],
            sustainability_score=7.0,
            alternative_products=["CLO001"]
        )
        
        # Electronics
        products["ELE001"] = Product(
            product_id="ELE001",
            name="Energy Efficient LED Bulb",
            category=ProductCategory.ELECTRONICS,
            price_usd=8.99,
            weight_kg=0.1,
            packaging_type=PackagingType.CARDBOARD,
            packaging_weight_kg=0.03,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=2.0,
            water_footprint_liters=100,
            shelf_life_days=10000,
            brand="GreenEnergy",
            manufacturer_location="China",
            certifications=["Energy Star"],
            sustainability_score=7.5,
            alternative_products=["ELE002"]
        )
        
        products["ELE002"] = Product(
            product_id="ELE002",
            name="Standard Incandescent Bulb",
            category=ProductCategory.ELECTRONICS,
            price_usd=2.99,
            weight_kg=0.08,
            packaging_type=PackagingType.PLASTIC_SINGLE,
            packaging_weight_kg=0.02,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=6.0,
            water_footprint_liters=50,
            shelf_life_days=365,
            brand="StandardLight",
            manufacturer_location="China",
            certifications=[],
            sustainability_score=2.0,
            alternative_products=["ELE001"]
        )
        
        # Cleaning products
        products["CLE001"] = Product(
            product_id="CLE001",
            name="Eco-Friendly Cleaner (1L)",
            category=ProductCategory.CLEANING_PRODUCTS,
            price_usd=12.99,
            weight_kg=1.0,
            packaging_type=PackagingType.COMPOSTABLE,
            packaging_weight_kg=0.05,
            is_reusable=True,
            is_recyclable=True,
            is_compostable=True,
            is_organic=True,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=0.5,
            water_footprint_liters=50,
            shelf_life_days=365,
            brand="GreenClean",
            manufacturer_location="USA",
            certifications=["EcoLogo"],
            sustainability_score=8.8,
            alternative_products=["CLE002"]
        )
        
        products["CLE002"] = Product(
            product_id="CLE002",
            name="Conventional Cleaner (1L)",
            category=ProductCategory.CLEANING_PRODUCTS,
            price_usd=5.99,
            weight_kg=1.0,
            packaging_type=PackagingType.PLASTIC_SINGLE,
            packaging_weight_kg=0.08,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=2.0,
            water_footprint_liters=100,
            shelf_life_days=730,
            brand="ChemClean",
            manufacturer_location="China",
            certifications=[],
            sustainability_score=2.5,
            alternative_products=["CLE001"]
        )
        
        # Personal care
        products["PER001"] = Product(
            product_id="PER001",
            name="Natural Shampoo Bar",
            category=ProductCategory.PERSONAL_CARE,
            price_usd=14.99,
            weight_kg=0.1,
            packaging_type=PackagingType.PAPER,
            packaging_weight_kg=0.01,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=True,
            is_organic=True,
            is_local=False,
            is_fair_trade=True,
            carbon_footprint_kg=0.3,
            water_footprint_liters=30,
            shelf_life_days=365,
            brand="NaturalBar",
            manufacturer_location="UK",
            certifications=["Cruelty Free", "Vegan"],
            sustainability_score=9.2,
            alternative_products=["PER002"]
        )
        
        products["PER002"] = Product(
            product_id="PER002",
            name="Liquid Shampoo (500ml)",
            category=ProductCategory.PERSONAL_CARE,
            price_usd=8.99,
            weight_kg=0.5,
            packaging_type=PackagingType.PLASTIC_MULTI,
            packaging_weight_kg=0.04,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=False,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=0.8,
            water_footprint_liters=80,
            shelf_life_days=365,
            brand="HairCare",
            manufacturer_location="USA",
            certifications=[],
            sustainability_score=3.8,
            alternative_products=["PER001"]
        )
        
        # Paper products
        products["PAP001"] = Product(
            product_id="PAP001",
            name="Recycled Toilet Paper (12 rolls)",
            category=ProductCategory.PAPER_PRODUCTS,
            price_usd=8.99,
            weight_kg=1.5,
            packaging_type=PackagingType.PAPER,
            packaging_weight_kg=0.1,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=True,
            is_organic=False,
            is_local=False,
            is_fair_trade=False,
            carbon_footprint_kg=2.0,
            water_footprint_liters=200,
            shelf_life_days=730,
            brand="GreenPaper",
            manufacturer_location="Canada",
            certifications=["FSC", "Recycled Content"],
            sustainability_score=7.8,
            alternative_products=["PAP002"]
        )
        
        products["PAP002"] = Product(
            product_id="PAP002",
            name="Premium Bamboo Toilet Paper (12 rolls)",
            category=ProductCategory.PAPER_PRODUCTS,
            price_usd=12.99,
            weight_kg=1.3,
            packaging_type=PackagingType.COMPOSTABLE,
            packaging_weight_kg=0.05,
            is_reusable=False,
            is_recyclable=True,
            is_compostable=True,
            is_organic=False,
            is_local=False,
            is_fair_trade=True,
            carbon_footprint_kg=1.5,
            water_footprint_liters=150,
            shelf_life_days=730,
            brand="EcoBamboo",
            manufacturer_location="China",
            certifications=["FSC", "Bamboo Certified"],
            sustainability_score=8.5,
            alternative_products=["PAP001"]
        )
        
        return products
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """Gets a product by ID."""
        return self._products.get(product_id)
    
    def get_products_by_category(self, category: ProductCategory) -> List[Product]:
        """Gets all products in a category."""
        return [p for p in self._products.values() if p.category == category]
    
    def get_sustainable_alternatives(self, product_id: str) -> List[Product]:
        """Gets sustainable alternatives for a product."""
        product = self.get_product(product_id)
        if not product:
            return []
        
        alternatives = []
        for alt_id in product.alternative_products:
            alt_product = self.get_product(alt_id)
            if alt_product and alt_product.sustainability_score > product.sustainability_score:
                alternatives.append(alt_product)
        
        return alternatives


class ShoppingImpactCalculator:
    """
    Calculates environmental impact of shopping choices.
    """
    
    def __init__(self):
        self._product_db = ProductDatabase()
        self._packaging_impacts = self._initialize_packaging_impacts()
    
    def _initialize_packaging_impacts(self) -> Dict[PackagingType, Dict[str, float]]:
        """
        Initializes packaging impact factors.
        
        Returns:
            Dictionary mapping packaging types to impact factors
        """
        return {
            PackagingType.NONE: {
                "carbon_factor": 0.0,
                "waste_factor": 0.0,
                "recyclability": 1.0,
                "reusability": 1.0
            },
            PackagingType.PLASTIC_SINGLE: {
                "carbon_factor": 2.0,
                "waste_factor": 1.0,
                "recyclability": 0.4,
                "reusability": 0.1
            },
            PackagingType.PLASTIC_MULTI: {
                "carbon_factor": 3.5,
                "waste_factor": 1.5,
                "recyclability": 0.3,
                "reusability": 0.2
            },
            PackagingType.PLASTIC_BIO: {
                "carbon_factor": 1.2,
                "waste_factor": 0.6,
                "recyclability": 0.6,
                "reusability": 0.3
            },
            PackagingType.PAPER: {
                "carbon_factor": 0.8,
                "waste_factor": 0.8,
                "recyclability": 0.8,
                "reusability": 0.4
            },
            PackagingType.CARDBOARD: {
                "carbon_factor": 0.6,
                "waste_factor": 0.7,
                "recyclability": 0.9,
                "reusability": 0.5
            },
            PackagingType.GLASS: {
                "carbon_factor": 1.5,
                "waste_factor": 0.3,
                "recyclability": 0.9,
                "reusability": 0.9
            },
            PackagingType.METAL: {
                "carbon_factor": 2.5,
                "waste_factor": 0.4,
                "recyclability": 0.9,
                "reusability": 0.8
            },
            PackagingType.ALUMINUM: {
                "carbon_factor": 3.0,
                "waste_factor": 0.5,
                "recyclability": 0.8,
                "reusability": 0.7
            },
            PackagingType.COMPOSTABLE: {
                "carbon_factor": 0.3,
                "waste_factor": 0.2,
                "recyclability": 0.7,
                "reusability": 0.2
            },
            PackagingType.RECYCLED: {
                "carbon_factor": 0.5,
                "waste_factor": 0.4,
                "recyclability": 0.9,
                "reusability": 0.5
            },
            PackagingType.REUSABLE: {
                "carbon_factor": 0.2,
                "waste_factor": 0.1,
                "recyclability": 0.9,
                "reusability": 1.0
            },
            PackagingType.FOAM: {
                "carbon_factor": 4.0,
                "waste_factor": 2.0,
                "recyclability": 0.1,
                "reusability": 0.0
            },
            PackagingType.MIXED: {
                "carbon_factor": 2.5,
                "waste_factor": 1.0,
                "recyclability": 0.4,
                "reusability": 0.3
            }
        }
    
    def calculate_product_impact(self, product: Product, quantity: int = 1) -> Dict[str, float]:
        """
        Calculates the environmental impact of a product.
        
        Args:
            product: Product object
            quantity: Number of items
            
        Returns:
            Dictionary with impact metrics
        """
        # Base carbon footprint
        carbon_footprint = product.carbon_footprint_kg * quantity
        
        # Packaging impact
        packaging_impact = self._packaging_impacts.get(product.packaging_type, {})
        packaging_carbon = packaging_impact.get("carbon_factor", 1.0) * product.packaging_weight_kg * quantity
        packaging_waste = product.packaging_weight_kg * quantity
        
        # Water footprint
        water_footprint = product.water_footprint_liters * quantity
        
        # Reusability factor (lower is better for new purchase)
        reusability_factor = 1.0 if not product.is_reusable else 0.2
        
        # Organic impact
        organic_factor = 0.8 if product.is_organic else 1.0
        
        # Local factor
        local_factor = 0.7 if product.is_local else 1.0
        
        total_carbon = (carbon_footprint + packaging_carbon) * organic_factor * local_factor * reusability_factor
        
        return {
            "carbon_footprint_kg": total_carbon,
            "packaging_carbon_kg": packaging_carbon,
            "packaging_waste_kg": packaging_waste,
            "water_footprint_liters": water_footprint,
            "raw_material_impact": carbon_footprint,
            "recyclability_score": packaging_impact.get("recyclability", 0.5),
            "reusability_score": packaging_impact.get("reusability", 0.5)
        }
    
    def calculate_shopping_trip_impact(self, trip: ShoppingTrip) -> Dict[str, float]:
        """
        Calculates total impact of a shopping trip.
        
        Args:
            trip: ShoppingTrip object
            
        Returns:
            Dictionary with total impact metrics
        """
        total_carbon = 0.0
        total_packaging_waste = 0.0
        total_water = 0.0
        total_packaging_carbon = 0.0
        
        for item in trip.items:
            impact = self.calculate_product_impact(item.product, item.quantity)
            total_carbon += impact["carbon_footprint_kg"]
            total_packaging_carbon += impact["packaging_carbon_kg"]
            total_packaging_waste += impact["packaging_waste_kg"]
            total_water += impact["water_footprint_liters"]
        
        # Add transport impact (simplified)
        if trip.transport_distance_km > 0:
            transport_carbon = trip.transport_distance_km * 0.15  # 0.15 kg CO2 per km
            total_carbon += transport_carbon
        
        # Calculate sustainability score
        sustainability_score = self._calculate_sustainability_score(
            total_carbon, total_packaging_waste, len(trip.items)
        )
        
        return {
            "total_carbon_kg": total_carbon,
            "total_packaging_waste_kg": total_packaging_waste,
            "total_water_liters": total_water,
            "packaging_carbon_kg": total_packaging_carbon,
            "transport_carbon_kg": transport_carbon if trip.transport_distance_km > 0 else 0,
            "sustainability_score": sustainability_score,
            "items_per_kg_waste": len(trip.items) / max(total_packaging_waste, 0.001)
        }
    
    def _calculate_sustainability_score(self, total_carbon: float, 
                                       total_waste: float, 
                                       num_items: int) -> float:
        """
        Calculates sustainability score (0-10).
        
        Args:
            total_carbon: Total carbon emissions in kg
            total_waste: Total waste in kg
            num_items: Number of items
            
        Returns:
            Sustainability score (0-10)
        """
        # Carbon score (lower is better)
        carbon_per_item = total_carbon / max(num_items, 1)
        if carbon_per_item <= 0.5:
            carbon_score = 10.0
        elif carbon_per_item <= 1.0:
            carbon_score = 8.0
        elif carbon_per_item <= 2.0:
            carbon_score = 6.0
        elif carbon_per_item <= 4.0:
            carbon_score = 4.0
        elif carbon_per_item <= 6.0:
            carbon_score = 2.0
        else:
            carbon_score = 0.0
        
        # Waste score (lower is better)
        waste_per_item = total_waste / max(num_items, 1)
        if waste_per_item <= 0.01:
            waste_score = 10.0
        elif waste_per_item <= 0.05:
            waste_score = 8.0
        elif waste_per_item <= 0.1:
            waste_score = 6.0
        elif waste_per_item <= 0.2:
            waste_score = 4.0
        elif waste_per_item <= 0.5:
            waste_score = 2.0
        else:
            waste_score = 0.0
        
        # Combined score
        combined_score = (carbon_score * 0.6 + waste_score * 0.4)
        
        return round(combined_score, 1)


class ShoppingChoiceOptimizer:
    """
    Optimizes shopping choices for sustainability.
    """
    
    def __init__(self):
        self._product_db = ProductDatabase()
        self._calculator = ShoppingImpactCalculator()
    
    def get_sustainable_alternatives(self, product_id: str, 
                                   max_alternatives: int = 3) -> List[SustainableAlternative]:
        """
        Gets sustainable alternatives for a product.
        
        Args:
            product_id: Product ID
            max_alternatives: Maximum number of alternatives to return
            
        Returns:
            List of SustainableAlternative objects
        """
        product = self._product_db.get_product(product_id)
        if not product:
            return []
        
        alternatives = self._product_db.get_sustainable_alternatives(product_id)
        results = []
        
        for alt in alternatives[:max_alternatives]:
            original_impact = self._calculator.calculate_product_impact(product)
            alt_impact = self._calculator.calculate_product_impact(alt)
            
            carbon_savings = original_impact["carbon_footprint_kg"] - alt_impact["carbon_footprint_kg"]
            packaging_reduction = original_impact["packaging_waste_kg"] - alt_impact["packaging_waste_kg"]
            water_savings = original_impact["water_footprint_liters"] - alt_impact["water_footprint_liters"]
            
            cost_diff = alt.price_usd - product.price_usd
            
            # Calculate payback period if applicable
            payback_period = 0.0
            if cost_diff > 0 and carbon_savings > 0:
                # Rough estimate: if it costs more but saves carbon
                payback_period = (cost_diff * 12) / 5  # Simple calculation
            elif cost_diff < 0:
                payback_period = 0.0  # Saves money immediately
            
            # Implementation ease
            implementation_ease = 0.9 if alt.is_local else 0.7
            if alt.is_organic:
                implementation_ease *= 0.9
            
            # Priority score
            priority = 1
            if carbon_savings > 2.0:
                priority = 1
            elif carbon_savings > 1.0:
                priority = 2
            else:
                priority = 3
            
            explanation = self._generate_explanation(product, alt, carbon_savings, packaging_reduction)
            
            results.append(SustainableAlternative(
                original_product=product,
                alternative_product=alt,
                carbon_savings_kg=round(carbon_savings, 2),
                cost_difference_usd=round(cost_diff, 2),
                packaging_reduction_kg=round(packaging_reduction, 3),
                water_savings_liters=round(water_savings, 2),
                implementation_ease=implementation_ease,
                recommendation_priority=priority,
                explanation=explanation,
                payback_period_months=payback_period
            ))
        
        # Sort by priority
        results.sort(key=lambda x: x.recommendation_priority)
        
        return results
    
    def _generate_explanation(self, original: Product, alternative: Product, 
                             carbon_savings: float, packaging_reduction: float) -> str:
        """
        Generates explanation for the alternative recommendation.
        
        Args:
            original: Original product
            alternative: Alternative product
            carbon_savings: Carbon savings in kg
            packaging_reduction: Packaging reduction in kg
            
        Returns:
            Explanation string
        """
        explanations = []
        
        if carbon_savings > 0:
            explanations.append(f"Reduces carbon emissions by {carbon_savings:.1f} kg per item")
        
        if packaging_reduction > 0:
            explanations.append(f"Reduces packaging waste by {packaging_reduction:.0f} g")
        
        if alternative.is_organic:
            explanations.append("Made with organic ingredients/materials")
        
        if alternative.is_local:
            explanations.append("Locally sourced/produced")
        
        if alternative.is_fair_trade:
            explanations.append("Fair Trade certified")
        
        if alternative.packaging_type != original.packaging_type:
            explanations.append(f"Uses {alternative.packaging_type.value.replace('_', ' ')} packaging instead of {original.packaging_type.value.replace('_', ' ')}")
        
        if alternative.is_reusable:
            explanations.append("Reusable option available")
        
        if alternative.is_recyclable and not original.is_recyclable:
            explanations.append("Recyclable packaging")
        if not explanations:
            explanations.append("A more sustainable shopping choice")
            
        return ". ".join(explanations) + "."
