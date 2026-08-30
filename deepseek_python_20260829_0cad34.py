"""
Database migration for shopping tables.
Run this script to add shopping tables to existing database.
"""

import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_database(db_path: str = 'ecobuddy.db') -> None:
    """
    Add shopping tables to the existing database.
    
    Args:
        db_path: Path to the SQLite database
    """
    if not os.path.exists(db_path):
        logger.warning(f"Database {db_path} not found. Creating new database.")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if shopping tables already exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shopping_products'")
    if cursor.fetchone():
        logger.info("Shopping tables already exist. Skipping migration.")
        conn.close()
        return
    
    logger.info("Creating shopping tables...")
    
    # Products table
    cursor.execute('''
        CREATE TABLE shopping_products (
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
        CREATE TABLE shopping_materials (
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
        CREATE TABLE shopping_packaging (
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
        CREATE TABLE shopping_purchases (
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
        CREATE TABLE shopping_recommendations (
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
    cursor.execute('CREATE INDEX idx_shopping_products_category ON shopping_products(category)')
    cursor.execute('CREATE INDEX idx_shopping_products_sustainability ON shopping_products(sustainability_score)')
    cursor.execute('CREATE INDEX idx_shopping_purchases_user_id ON shopping_purchases(user_id)')
    cursor.execute('CREATE INDEX idx_shopping_purchases_date ON shopping_purchases(purchase_date)')
    cursor.execute('CREATE INDEX idx_shopping_recommendations_user_id ON shopping_recommendations(user_id)')
    
    conn.commit()
    conn.close()
    
    logger.info("✅ Shopping tables created successfully!")


def rollback_migration(db_path: str = 'ecobuddy.db') -> None:
    """
    Rollback the migration (drop shopping tables).
    
    Args:
        db_path: Path to the SQLite database
    """
    if not os.path.exists(db_path):
        logger.warning(f"Database {db_path} not found.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop tables
    cursor.execute('DROP TABLE IF EXISTS shopping_recommendations')
    cursor.execute('DROP TABLE IF EXISTS shopping_purchases')
    cursor.execute('DROP TABLE IF EXISTS shopping_packaging')
    cursor.execute('DROP TABLE IF EXISTS shopping_materials')
    cursor.execute('DROP TABLE IF EXISTS shopping_products')
    
    conn.commit()
    conn.close()
    
    logger.info("✅ Migration rolled back successfully!")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Shopping database migration')
    parser.add_argument('--db-path', default='ecobuddy.db', help='Path to SQLite database')
    parser.add_argument('--rollback', action='store_true', help='Rollback migration')
    
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration(args.db_path)
    else:
        migrate_database(args.db_path)