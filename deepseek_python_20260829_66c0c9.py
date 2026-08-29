"""
Sustainable Shopping & Product Impact Analyzer
A comprehensive system for evaluating product sustainability.
"""

from shopping.models import (
    Product, ProductCategory, ProductSustainabilityProfile,
    MaterialComposition, PackagingAssessment, EnvironmentalImpact,
    FinancialAnalysis, PurchaseAlternative, PurchaseHistory,
    ProductComparison, SustainabilityScore, RepairabilityScore,
    RecyclabilityScore, ProductRecommendation
)
from shopping.analyzer import ShoppingAnalyzer
from shopping.environmental import EnvironmentalCalculator
from shopping.financial import FinancialAnalyzer
from shopping.comparisons import ProductComparator
from shopping.recommendations import RecommendationEngine
from shopping.lifecycle import LifecycleAnalyzer
from shopping.database import ShoppingDatabase
from shopping.visualizations import ShoppingVisualizer

__all__ = [
    'Product',
    'ProductCategory',
    'ProductSustainabilityProfile',
    'MaterialComposition',
    'PackagingAssessment',
    'EnvironmentalImpact',
    'FinancialAnalysis',
    'PurchaseAlternative',
    'PurchaseHistory',
    'ProductComparison',
    'SustainabilityScore',
    'RepairabilityScore',
    'RecyclabilityScore',
    'ProductRecommendation',
    'ShoppingAnalyzer',
    'EnvironmentalCalculator',
    'FinancialAnalyzer',
    'ProductComparator',
    'RecommendationEngine',
    'LifecycleAnalyzer',
    'ShoppingDatabase',
    'ShoppingVisualizer'
]