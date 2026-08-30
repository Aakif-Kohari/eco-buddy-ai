"""
Sustainable Shopping & Product Impact Analyzer - Unit Tests
Comprehensive test suite for shopping system.
"""

import unittest
from datetime import datetime, timedelta
from typing import Dict, Any

from shopping.models import (
    Product, ProductCategory, MaterialComposition, PackagingAssessment,
    EnvironmentalImpact, FinancialAnalysis, PurchaseHistory,
    SustainabilityScore, RepairabilityScore, RecyclabilityScore
)
from shopping.analyzer import ShoppingAnalyzer
from shopping.environmental import EnvironmentalCalculator
from shopping.financial import FinancialAnalyzer
from shopping.comparisons import ProductComparator
from shopping.recommendations import RecommendationEngine
from shopping.lifecycle import LifecycleAnalyzer


class TestProductModel(unittest.TestCase):
    """Test cases for Product model."""
    
    def setUp(self):
        """Set up test data."""
        self.product = Product(
            name="Test Product",
            brand="Test Brand",
            category=ProductCategory.ELECTRONICS,
            price=100.0,
            weight_kg=1.5,
            expected_lifetime_years=5,
            durability_rating=80.0,
            repairability_score=70.0,
            recyclability_score=60.0
        )
        
        self.product.materials.append(
            MaterialComposition(
                material_type="metal",
                percentage=60,
                is_recycled=True
            )
        )
        self.product.materials.append(
            MaterialComposition(
                material_type="plastic",
                percentage=40,
                is_recycled=False
            )
        )
    
    def test_product_creation(self):
        """Test product creation and attributes."""
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(self.product.brand, "Test Brand")
        self.assertEqual(self.product.category, ProductCategory.ELECTRONICS)
        self.assertEqual(self.product.price, 100.0)
    
    def test_sustainability_score(self):
        """Test sustainability score calculation."""
        score = self.product.calculate_sustainability_score()
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertEqual(self.product.sustainability_score, score)
    
    def test_materials_composition(self):
        """Test material composition."""
        self.assertEqual(len(self.product.materials), 2)
        self.assertTrue(self.product.materials[0].is_recycled)
        self.assertFalse(self.product.materials[1].is_recycled)
    
    def test_to_dict(self):
        """Test serialization to dictionary."""
        product_dict = self.product.to_dict()
        self.assertEqual(product_dict['name'], "Test Product")
        self.assertEqual(product_dict['brand'], "Test Brand")
        self.assertEqual(len(product_dict['materials']), 2)


class TestEnvironmentalCalculator(unittest.TestCase):
    """Test cases for Environmental Calculator."""
    
    def setUp(self):
        """Set up test data."""
        self.calculator = EnvironmentalCalculator()
        self.product = Product(
            name="Test Product",
            category=ProductCategory.ELECTRONICS,
            price=100.0,
            weight_kg=2.0,
            expected_lifetime_years=3
        )
        self.product.materials.append(
            MaterialComposition(
                material_type="metal",
                percentage=50,
                is_recyclable=True
            )
        )
        self.product.materials.append(
            MaterialComposition(
                material_type="plastic",
                percentage=50,
                is_recyclable=False
            )
        )
        self.product.shipping_distance_km = 5000
        self.product.energy_consumption_kwh = 100
    
    def test_calculate_impact(self):
        """Test environmental impact calculation."""
        impact = self.calculator.calculate_impact(self.product)
        
        self.assertIsInstance(impact, EnvironmentalImpact)
        self.assertGreater(impact.total_carbon_kg, 0)
        self.assertEqual(impact.product_name, "Test Product")
    
    def test_carbon_footprint(self):
        """Test carbon footprint components."""
        impact = self.calculator.calculate_impact(self.product)
        
        self.assertGreaterEqual(impact.manufacturing_carbon_kg, 0)
        self.assertGreaterEqual(impact.transport_carbon_kg, 0)
        self.assertGreaterEqual(impact.usage_carbon_kg, 0)
        self.assertGreaterEqual(impact.disposal_carbon_kg, 0)


class TestFinancialAnalyzer(unittest.TestCase):
    """Test cases for Financial Analyzer."""
    
    def setUp(self):
        """Set up test data."""
        self.analyzer = FinancialAnalyzer()
        self.product = Product(
            name="Test Product",
            price=100.0,
            expected_lifetime_years=5,
            durability_rating=70.0,
            repairability_score=60.0
        )
    
    def test_financial_analysis(self):
        """Test financial analysis."""
        analysis = self.analyzer.analyze(self.product)
        
        self.assertIsInstance(analysis, FinancialAnalysis)
        self.assertEqual(analysis.product_name, "Test Product")
        self.assertEqual(analysis.purchase_price, 100.0)
        self.assertGreater(analysis.total_lifetime_cost, 0)
    
    def test_cost_per_year(self):
        """Test cost per year calculation."""
        analysis = self.analyzer.analyze(self.product)
        self.assertGreater(analysis.cost_per_year, 0)
    
    def test_roi_calculation(self):
        """Test ROI calculation."""
        analysis = self.analyzer.analyze(self.product)
        # ROI should be calculated
        self.assertIsNotNone(analysis.roi_percentage)


class TestProductComparator(unittest.TestCase):
    """Test cases for Product Comparator."""
    
    def setUp(self):
        """Set up test data."""
        self.comparator = ProductComparator()
        self.product1 = Product(
            name="Product A",
            price=100.0,
            sustainability_score=80.0,
            durability_rating=70.0,
            repairability_score=60.0
        )
        self.product2 = Product(
            name="Product B",
            price=150.0,
            sustainability_score=90.0,
            durability_rating=85.0,
            repairability_score=75.0
        )
        self.product3 = Product(
            name="Product C",
            price=80.0,
            sustainability_score=65.0,
            durability_rating=50.0,
            repairability_score=40.0
        )
    
    def test_compare_multiple(self):
        """Test comparing multiple products."""
        comparison = self.comparator.compare([self.product1, self.product2, self.product3])
        
        self.assertEqual(len(comparison.products), 3)
        self.assertIsNotNone(comparison.best_overall)
        self.assertIsNotNone(comparison.best_durability)
    
    def test_get_best_overall(self):
        """Test getting best overall product."""
        best = self.comparator.get_best_overall([self.product1, self.product2, self.product3])
        self.assertIsNotNone(best)
        # Product2 should be best overall
        self.assertEqual(best.name, "Product B")
    
    def test_compare_by_sustainability(self):
        """Test sorting by sustainability."""
        sorted_products = self.comparator.compare_by_sustainability(
            [self.product1, self.product2, self.product3]
        )
        self.assertEqual(sorted_products[0].name, "Product B")  # Highest sustainability


class TestRecommendationEngine(unittest.TestCase):
    """Test cases for Recommendation Engine."""
    
    def setUp(self):
        """Set up test data."""
        self.engine = RecommendationEngine()
        self.user_context = {
            'user_id': 'test_user',
            'goals': ['Reduce carbon footprint', 'Buy sustainable'],
            'habits': ['Weekly shopping', 'Eco-conscious'],
            'budget': 200.0
        }
        self.products = [
            Product(
                name="Eco Product",
                price=50.0,
                sustainability_score=85.0,
                category=ProductCategory.OTHER
            ),
            Product(
                name="Regular Product",
                price=30.0,
                sustainability_score=45.0,
                category=ProductCategory.OTHER
            ),
            Product(
                name="Premium Product",
                price=120.0,
                sustainability_score=90.0,
                category=ProductCategory.OTHER
            )
        ]
    
    def test_generate_recommendations(self):
        """Test generating recommendations."""
        recommendations = self.engine.generate_recommendations(
            self.products,
            self.user_context
        )
        
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
    
    def test_recommendation_types(self):
        """Test different recommendation types."""
        recommendations = self.engine.generate_recommendations(
            self.products,
            self.user_context
        )
        
        for rec in recommendations:
            self.assertIn(rec.recommendation_type.value, 
                         ['buy', 'consider', 'avoid', 'delay', 'upgrade', 'alternative'])
    
    def test_recommendation_reason(self):
        """Test recommendation reasons."""
        recommendations = self.engine.generate_recommendations(
            self.products,
            self.user_context
        )
        
        for rec in recommendations:
            self.assertIsNotNone(rec.reason)
            self.assertGreater(len(rec.reason), 0)


class TestLifecycleAnalyzer(unittest.TestCase):
    """Test cases for Lifecycle Analyzer."""
    
    def setUp(self):
        """Set up test data."""
        self.analyzer = LifecycleAnalyzer()
        self.product = Product(
            name="Test Product",
            expected_lifetime_years=5,
            durability_rating=75.0,
            repairability_score=70.0,
            recyclability_score=65.0,
            carbon_footprint_kg=50.0
        )
        self.product.certifications = ['Energy Star', 'EPEAT']
        self.product.eco_labels = ['Eco-Friendly']
    
    def test_assess_lifecycle(self):
        """Test lifecycle assessment."""
        assessment = self.analyzer.assess_lifecycle(self.product)
        
        self.assertIsInstance(assessment, dict)
        self.assertEqual(assessment['product_name'], "Test Product")
        self.assertIn('lifecycle_scores', assessment)
    
    def test_lifecycle_stages(self):
        """Test lifecycle stages."""
        assessment = self.analyzer.assess_lifecycle(self.product)
        
        stages = assessment['lifecycle_stages']
        self.assertIn('raw_materials', stages)
        self.assertIn('manufacturing', stages)
        self.assertIn('transportation', stages)
        self.assertIn('usage', stages)
        self.assertIn('disposal', stages)
    
    def test_lifecycle_recommendations(self):
        """Test lifecycle recommendations."""
        assessment = self.analyzer.assess_lifecycle(self.product)
        
        recommendations = assessment['lifecycle_recommendations']
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)


class TestPurchaseHistory(unittest.TestCase):
    """Test cases for Purchase History."""
    
    def test_purchase_creation(self):
        """Test purchase history creation."""
        purchase = PurchaseHistory(
            user_id="test_user",
            product_id="prod123",
            product_name="Test Product",
            price_paid=99.99,
            estimated_carbon_kg=10.5
        )
        
        self.assertEqual(purchase.user_id, "test_user")
        self.assertEqual(purchase.product_name, "Test Product")
        self.assertEqual(purchase.price_paid, 99.99)
    
    def test_purchase_to_dict(self):
        """Test purchase serialization."""
        purchase = PurchaseHistory(
            user_id="test_user",
            product_id="prod123",
            product_name="Test Product",
            price_paid=99.99
        )
        
        purchase_dict = purchase.to_dict()
        self.assertEqual(purchase_dict['user_id'], "test_user")
        self.assertEqual(purchase_dict['product_name'], "Test Product")


class TestShoppingAnalyzer(unittest.TestCase):
    """Test cases for Shopping Analyzer."""
    
    def setUp(self):
        """Set up test data."""
        self.analyzer = ShoppingAnalyzer()
        self.product = Product(
            name="Test Product",
            category=ProductCategory.ELECTRONICS,
            price=100.0,
            weight_kg=2.0,
            expected_lifetime_years=5
        )
        self.product.materials.append(
            MaterialComposition(
                material_type="metal",
                percentage=50,
                is_recyclable=True
            )
        )
    
    def test_full_analysis(self):
        """Test comprehensive product analysis."""
        analysis = self.analyzer.analyze_product(self.product)
        
        self.assertIsInstance(analysis, dict)
        self.assertIn('product', analysis)
        self.assertIn('environmental_impact', analysis)
        self.assertIn('financial_analysis', analysis)
        self.assertIn('lifecycle_assessment', analysis)
        self.assertIn('sustainability_score', analysis)
    
    def test_sustainability_score(self):
        """Test sustainability score generation."""
        analysis = self.analyzer.analyze_product(self.product)
        
        score = analysis['sustainability_score']
        self.assertIsInstance(score, SustainabilityScore)
        self.assertEqual(score.product_name, "Test Product")
        self.assertGreaterEqual(score.overall_score, 0)
        self.assertLessEqual(score.overall_score, 100)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""
    
    def test_empty_product(self):
        """Test empty product handling."""
        product = Product()
        analyzer = ShoppingAnalyzer()
        analysis = analyzer.analyze_product(product)
        
        self.assertIsInstance(analysis, dict)
        self.assertIsNotNone(analysis)
    
    def test_zero_values(self):
        """Test zero values handling."""
        product = Product(
            name="Zero Product",
            price=0.0,
            weight_kg=0.0
        )
        
        analyzer = ShoppingAnalyzer()
        analysis = analyzer.analyze_product(product)
        
        self.assertIsInstance(analysis, dict)
        self.assertIsNotNone(analysis)
    
    def test_negative_values(self):
        """Test negative values handling."""
        product = Product(
            name="Negative Product",
            price=-100.0,
            weight_kg=-1.0
        )
        
        analyzer = ShoppingAnalyzer()
        analysis = analyzer.analyze_product(product)
        
        # Should handle gracefully without crashing
        self.assertIsInstance(analysis, dict)
    
    def test_missing_materials(self):
        """Test product without materials."""
        product = Product(
            name="No Materials Product",
            category=ProductCategory.OTHER,
            price=50.0
        )
        
        analyzer = ShoppingAnalyzer()
        analysis = analyzer.analyze_product(product)
        
        self.assertIsInstance(analysis, dict)
        # Should still work with defaults


def run_tests():
    """Run all test cases."""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()