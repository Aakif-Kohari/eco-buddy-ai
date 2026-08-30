"""
Sustainable Shopping & Product Impact Analyzer - Product Comparison
Compares multiple products for sustainability and value.
"""

import logging
import statistics
from typing import List, Dict, Any, Tuple

from shopping.models import Product, ProductComparison

logger = logging.getLogger(__name__)


class ProductComparator:
    """
    Compares products for sustainability and financial value.
    """
    
    def __init__(self):
        """Initialize the comparator."""
        logger.info("Product Comparator initialized")
    
    def compare(self, products: List[Product]) -> ProductComparison:
        """
        Compare multiple products.
        
        Args:
            products: List of products to compare
        
        Returns:
            ProductComparison: Comparison results
        """
        if len(products) < 2:
            return ProductComparison(
                products=products,
                comparison_type="single"
            )
        
        comparison = ProductComparison(
            products=products,
            comparison_type="multi"
        )
        
        # Calculate metrics
        prices = [p.price for p in products]
        sustainability_scores = [p.sustainability_score for p in products]
        environmental_scores = [p.environmental_score for p in products]
        financial_scores = [p.financial_score for p in products]
        durability_ratings = [p.durability_rating for p in products]
        repairability_scores = [p.repairability_score for p in products]
        
        # Determine ranges
        comparison.price_range = (min(prices), max(prices))
        comparison.sustainability_range = (min(sustainability_scores), max(sustainability_scores))
        comparison.carbon_range = (min(p.carbon_footprint_kg for p in products), 
                                   max(p.carbon_footprint_kg for p in products))
        
        # Determine best in each category
        if sustainability_scores:
            best_idx = sustainability_scores.index(max(sustainability_scores))
            comparison.best_overall = products[best_idx].name
        
        if environmental_scores:
            best_idx = environmental_scores.index(max(environmental_scores))
            comparison.best_environmental = products[best_idx].name
        
        if financial_scores:
            best_idx = financial_scores.index(max(financial_scores))
            comparison.best_financial = products[best_idx].name
        
        if durability_ratings:
            best_idx = durability_ratings.index(max(durability_ratings))
            comparison.best_durability = products[best_idx].name
        
        if repairability_scores:
            best_idx = repairability_scores.index(max(repairability_scores))
            comparison.best_repairability = products[best_idx].name
        
        return comparison
    
    def compare_by_price(self, products: List[Product]) -> List[Product]:
        """
        Sort products by price.
        """
        return sorted(products, key=lambda p: p.price)
    
    def compare_by_sustainability(self, products: List[Product]) -> List[Product]:
        """
        Sort products by sustainability score.
        """
        return sorted(products, key=lambda p: p.sustainability_score, reverse=True)
    
    def compare_by_environmental_impact(self, products: List[Product]) -> List[Product]:
        """
        Sort products by environmental score.
        """
        return sorted(products, key=lambda p: p.environmental_score, reverse=True)
    
    def compare_by_financial_value(self, products: List[Product]) -> List[Product]:
        """
        Sort products by financial score.
        """
        return sorted(products, key=lambda p: p.financial_score, reverse=True)
    
    def compare_by_lifetime_value(self, products: List[Product]) -> List[Product]:
        """
        Sort products by lifetime value.
        """
        return sorted(products, key=lambda p: p.lifetime_value, reverse=True)
    
    def get_best_overall(self, products: List[Product]) -> Product:
        """
        Get the best overall product.
        """
        if not products:
            return None
        
        # Calculate weighted scores
        scored_products = []
        for product in products:
            score = (
                product.sustainability_score * 0.4 +
                product.financial_score * 0.3 +
                product.durability_rating * 0.15 +
                product.repairability_score * 0.15
            )
            scored_products.append((product, score))
        
        if scored_products:
            return max(scored_products, key=lambda x: x[1])[0]
        
        return None
    
    def get_most_sustainable(self, products: List[Product]) -> Product:
        """
        Get the most sustainable product.
        """
        if not products:
            return None
        
        return max(products, key=lambda p: p.sustainability_score)
    
    def get_best_value(self, products: List[Product]) -> Product:
        """
        Get the best value product.
        """
        if not products:
            return None
        
        # Calculate value for money
        scored_products = []
        for product in products:
            if product.price > 0:
                value = product.sustainability_score / product.price
                scored_products.append((product, value))
            else:
                scored_products.append((product, 0))
        
        if scored_products:
            return max(scored_products, key=lambda x: x[1])[0]
        
        return None
    
    def compare_new_vs_refurbished(self, new_product: Product, 
                                   refurbished_product: Product) -> Dict[str, Any]:
        """
        Compare new vs refurbished versions.
        """
        return {
            'new_product': new_product.name,
            'refurbished_product': refurbished_product.name,
            'price_difference': new_product.price - refurbished_product.price,
            'savings_percentage': ((new_product.price - refurbished_product.price) / 
                                  new_product.price * 100) if new_product.price > 0 else 0,
            'sustainability_difference': new_product.sustainability_score - refurbished_product.sustainability_score,
            'lifetime_difference': new_product.expected_lifetime_years - refurbished_product.expected_lifetime_years,
            'recommendation': 'Refurbished' if refurbished_product.sustainability_score >= new_product.sustainability_score * 0.8 else 'New'
        }
    
    def compare_short_vs_long_term(self, short_term: Product, 
                                   long_term: Product, 
                                   years: int = 10) -> Dict[str, Any]:
        """
        Compare short-term vs long-term products.
        """
        short_term_cost = short_term.price * (years / short_term.expected_lifetime_years)
        long_term_cost = long_term.price * (years / long_term.expected_lifetime_years)
        
        return {
            'short_term_product': short_term.name,
            'long_term_product': long_term.name,
            'short_term_cost': short_term_cost,
            'long_term_cost': long_term_cost,
            'savings': short_term_cost - long_term_cost,
            'savings_percentage': ((short_term_cost - long_term_cost) / 
                                  short_term_cost * 100) if short_term_cost > 0 else 0,
            'environmental_saving': short_term.carbon_footprint_kg - long_term.carbon_footprint_kg,
            'recommendation': 'Long-term' if long_term_cost < short_term_cost else 'Short-term'
        }
    
    def compare_disposable_vs_reusable(self, disposable: Product, 
                                       reusable: Product, 
                                       uses: int = 100) -> Dict[str, Any]:
        """
        Compare disposable vs reusable products.
        """
        disposable_cost = disposable.price * uses
        reusable_cost = reusable.price
        
        return {
            'disposable_product': disposable.name,
            'reusable_product': reusable.name,
            'disposable_cost': disposable_cost,
            'reusable_cost': reusable_cost,
            'savings': disposable_cost - reusable_cost,
            'savings_percentage': ((disposable_cost - reusable_cost) / 
                                  disposable_cost * 100) if disposable_cost > 0 else 0,
            'waste_reduction': (disposable.waste_generation_kg * uses) - reusable.waste_generation_kg,
            'carbon_saving': (disposable.carbon_footprint_kg * uses) - reusable.carbon_footprint_kg,
            'recommendation': 'Reusable' if reusable_cost < disposable_cost else 'Disposable'
        }