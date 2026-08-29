"""
Sustainable Shopping & Product Impact Analyzer - Database Operations
Database handlers for shopping data.
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from shopping.models import (
    Product, ProductCategory, ProductCondition,
    MaterialComposition, PackagingAssessment,
    PurchaseHistory, ProductRecommendation
)

logger = logging.getLogger(__name__)


class ShoppingDatabase:
    """
    Database handler for shopping operations.
    """
    
    def __init__(self, db_path: str = 'ecobuddy.db'):
        """
        Initialize the database handler.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self._initialize_tables()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path)
    
    def _initialize_tables(self) -> None:
        """Create shopping tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    category TEXT NOT NULL,
                    sub_category TEXT,
                    description TEXT,
                    price REAL,
                    currency TEXT DEFAULT 'USD',
                    weight_kg REAL,
                    dimensions TEXT,
                    condition TEXT DEFAULT 'new',
                    expected_lifetime_years REAL,
                    warranty_years REAL,
                    durability_rating REAL,
                    repairability_score REAL,
                    repair_cost_estimate REAL,
                    repair_parts_available INTEGER,
                    repair_instructions_available INTEGER,
                    recyclability_score REAL,
                    recyclable_materials TEXT,
                    recycling_program TEXT,
                    reusable INTEGER,
                    reusable_count INTEGER,
                    reusable_lifetime REAL,
                    certifications TEXT,
                    eco_labels TEXT,
                    manufacturing_country TEXT,
                    shipping_distance_km REAL,
                    transport_method TEXT,
                    transport_carbon_kg REAL,
                    carbon_footprint_kg REAL,
                    water_footprint_liters REAL,
                    energy_consumption_kwh REAL,
                    waste_generation_kg REAL,
                    cost_per_year REAL,
                    lifetime_value REAL,
                    long_term_savings REAL,
                    sustainability_score REAL,
                    environmental_score REAL,
                    financial_score REAL,
                    created_at TEXT,
                    updated_at TEXT,
                    source_url TEXT,
                    image_url TEXT,
                    notes TEXT,
                    tags TEXT
                )
            ''')
            
            # Product materials table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_materials (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    material_type TEXT NOT NULL,
                    percentage REAL,
                    is_recycled INTEGER,
                    is_renewable INTEGER,
                    is_biodegradable INTEGER,
                    is_recyclable INTEGER,
                    source TEXT,
                    certification TEXT,
                    notes TEXT,
                    FOREIGN KEY (product_id) REFERENCES shopping_products (id) ON DELETE CASCADE
                )
            ''')
            
            # Product packaging table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_packaging (
                    id TEXT PRIMARY KEY,
                    product_id TEXT NOT NULL,
                    packaging_type TEXT NOT NULL,
                    weight_kg REAL,
                    is_recyclable INTEGER,
                    is_biodegradable INTEGER,
                    is_reusable INTEGER,
                    is_compostable INTEGER,
                    contains_plastic INTEGER,
                    contains_paper INTEGER,
                    contains_metal INTEGER,
                    contains_glass INTEGER,
                    recycled_content REAL,
                    carbon_footprint_kg REAL,
                    notes TEXT,
                    FOREIGN KEY (product_id) REFERENCES shopping_products (id) ON DELETE CASCADE
                )
            ''')
            
            # Purchase history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_purchases (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    purchase_date TEXT NOT NULL,
                    price_paid REAL,
                    quantity INTEGER DEFAULT 1,
                    estimated_carbon_kg REAL,
                    estimated_water_liters REAL,
                    estimated_waste_kg REAL,
                    product_category TEXT,
                    condition TEXT,
                    expected_lifetime_years REAL,
                    notes TEXT,
                    receipt_url TEXT,
                    FOREIGN KEY (product_id) REFERENCES shopping_products (id) ON DELETE CASCADE
                )
            ''')
            
            # Product recommendations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_recommendations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    product_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    recommendation_type TEXT NOT NULL,
                    reason TEXT,
                    confidence REAL,
                    based_on_goals TEXT,
                    based_on_habits TEXT,
                    estimated_savings TEXT,
                    created_at TEXT,
                    expires_at TEXT,
                    FOREIGN KEY (product_id) REFERENCES shopping_products (id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shopping_products_category ON shopping_products(category)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shopping_products_sustainability ON shopping_products(sustainability_score)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shopping_purchases_user_id ON shopping_purchases(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shopping_purchases_date ON shopping_purchases(purchase_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shopping_recommendations_user_id ON shopping_recommendations(user_id)')
            
            conn.commit()
            logger.info("Shopping tables initialized successfully")
    
    def save_product(self, product: Product) -> str:
        """Save a product to the database."""
        product.updated_at = datetime.now()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO shopping_products (
                    id, name, brand, model, category, sub_category, description,
                    price, currency, weight_kg, dimensions, condition,
                    expected_lifetime_years, warranty_years, durability_rating,
                    repairability_score, repair_cost_estimate, repair_parts_available,
                    repair_instructions_available, recyclability_score, recyclable_materials,
                    recycling_program, reusable, reusable_count, reusable_lifetime,
                    certifications, eco_labels, manufacturing_country, shipping_distance_km,
                    transport_method, transport_carbon_kg, carbon_footprint_kg,
                    water_footprint_liters, energy_consumption_kwh, waste_generation_kg,
                    cost_per_year, lifetime_value, long_term_savings, sustainability_score,
                    environmental_score, financial_score, created_at, updated_at,
                    source_url, image_url, notes, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product.id, product.name, product.brand, product.model,
                product.category.value, product.sub_category, product.description,
                product.price, product.currency, product.weight_kg, product.dimensions,
                product.condition.value, product.expected_lifetime_years,
                product.warranty_years, product.durability_rating, product.repairability_score,
                product.repair_cost_estimate, 1 if product.repair_parts_available else 0,
                1 if product.repair_instructions_available else 0, product.recyclability_score,
                json.dumps(product.recyclable_materials), product.recycling_program,
                1 if product.reusable else 0, product.reusable_count, product.reusable_lifetime,
                json.dumps(product.certifications), json.dumps(product.eco_labels),
                product.manufacturing_country, product.shipping_distance_km,
                product.transport_method, product.transport_carbon_kg,
                product.carbon_footprint_kg, product.water_footprint_liters,
                product.energy_consumption_kwh, product.waste_generation_kg,
                product.cost_per_year, product.lifetime_value, product.long_term_savings,
                product.sustainability_score, product.environmental_score, product.financial_score,
                product.created_at.isoformat(), product.updated_at.isoformat(),
                product.source_url, product.image_url, product.notes, json.dumps(product.tags)
            ))
            
            # Save materials
            cursor.execute('DELETE FROM shopping_materials WHERE product_id = ?', (product.id,))
            for material in product.materials:
                cursor.execute('''
                    INSERT INTO shopping_materials (
                        id, product_id, material_type, percentage, is_recycled,
                        is_renewable, is_biodegradable, is_recyclable, source,
                        certification, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(uuid.uuid4()), product.id, material.material_type.value,
                    material.percentage, 1 if material.is_recycled else 0,
                    1 if material.is_renewable else 0, 1 if material.is_biodegradable else 0,
                    1 if material.is_recyclable else 0, material.source,
                    material.certification, material.notes
                ))
            
            # Save packaging
            if product.packaging:
                cursor.execute('DELETE FROM shopping_packaging WHERE product_id = ?', (product.id,))
                cursor.execute('''
                    INSERT INTO shopping_packaging (
                        id, product_id, packaging_type, weight_kg, is_recyclable,
                        is_biodegradable, is_reusable, is_compostable,
                        contains_plastic, contains_paper, contains_metal,
                        contains_glass, recycled_content, carbon_footprint_kg, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(uuid.uuid4()), product.id, product.packaging.packaging_type.value,
                    product.packaging.weight_kg, 1 if product.packaging.is_recyclable else 0,
                    1 if product.packaging.is_biodegradable else 0,
                    1 if product.packaging.is_reusable else 0,
                    1 if product.packaging.is_compostable else 0,
                    1 if product.packaging.contains_plastic else 0,
                    1 if product.packaging.contains_paper else 0,
                    1 if product.packaging.contains_metal else 0,
                    1 if product.packaging.contains_glass else 0,
                    product.packaging.recycled_content,
                    product.packaging.carbon_footprint_kg,
                    product.packaging.notes
                ))
            
            conn.commit()
            logger.info(f"Saved product {product.id} to database")
            return product.id
    
    def get_product(self, product_id: str) -> Optional[Product]:
        """Get a product from the database."""
        # Implementation would load product and all related data
        # Simplified version - would need full implementation
        pass
    
    def save_purchase(self, purchase: PurchaseHistory) -> str:
        """Save a purchase to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO shopping_purchases (
                    id, user_id, product_id, product_name, purchase_date,
                    price_paid, quantity, estimated_carbon_kg, estimated_water_liters,
                    estimated_waste_kg, product_category, condition,
                    expected_lifetime_years, notes, receipt_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                purchase.id, purchase.user_id, purchase.product_id,
                purchase.product_name, purchase.purchase_date.isoformat(),
                purchase.price_paid, purchase.quantity, purchase.estimated_carbon_kg,
                purchase.estimated_water_liters, purchase.estimated_waste_kg,
                purchase.product_category, purchase.condition,
                purchase.expected_lifetime_years, purchase.notes, purchase.receipt_url
            ))
            
            conn.commit()
            logger.info(f"Saved purchase {purchase.id} to database")
            return purchase.id
    
    def get_user_purchases(self, user_id: str) -> List[PurchaseHistory]:
        """Get all purchases for a user."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM shopping_purchases WHERE user_id = ? ORDER BY purchase_date DESC',
                (user_id,)
            )
            rows = cursor.fetchall()
            
            purchases = []
            for row in rows:
                purchase = PurchaseHistory(
                    id=row[0],
                    user_id=row[1],
                    product_id=row[2],
                    product_name=row[3],
                    purchase_date=datetime.fromisoformat(row[4]),
                    price_paid=row[5],
                    quantity=row[6],
                    estimated_carbon_kg=row[7],
                    estimated_water_liters=row[8],
                    estimated_waste_kg=row[9],
                    product_category=row[10],
                    condition=row[11],
                    expected_lifetime_years=row[12],
                    notes=row[13],
                    receipt_url=row[14]
                )
                purchases.append(purchase)
            
            return purchases