"""
Sustainable Shopping & Product Impact Analyzer - Financial Analysis
Comprehensive financial analysis of products.
"""

import logging
import math
from typing import Dict, Any, Optional

from shopping.models import Product, FinancialAnalysis

logger = logging.getLogger(__name__)


class FinancialAnalyzer:
    """
    Analyzes financial aspects of products.
    """
    
    def __init__(self):
        """Initialize the financial analyzer."""
        self.discount_rate = 0.05  # 5% for present value calculations
        self.inflation_rate = 0.02  # 2% annual inflation
        logger.info("Financial Analyzer initialized")
    
    def analyze(self, product: Product) -> FinancialAnalysis:
        """
        Perform comprehensive financial analysis.
        
        Args:
            product: Product to analyze
        
        Returns:
            FinancialAnalysis: Complete financial analysis
        """
        analysis = FinancialAnalysis(
            product_id=product.id,
            product_name=product.name,
            purchase_price=product.price,
            expected_lifetime_years=product.expected_lifetime_years
        )
        
        # Calculate initial costs
        analysis.tax = product.price * 0.08  # Assuming 8% tax
        analysis.shipping_cost = product.weight_kg * 2  # Rough shipping estimate
        analysis.total_initial_cost = product.price + analysis.tax + analysis.shipping_cost
        
        # Calculate operating costs
        analysis.annual_operating_cost = self._calculate_operating_cost(product)
        analysis.annual_maintenance_cost = self._calculate_maintenance_cost(product)
        analysis.annual_repair_cost = self._calculate_repair_cost(product)
        analysis.total_annual_cost = (
            analysis.annual_operating_cost +
            analysis.annual_maintenance_cost +
            analysis.annual_repair_cost
        )
        
        # Calculate lifetime costs
        analysis.lifetime_operating_cost = analysis.annual_operating_cost * product.expected_lifetime_years
        analysis.lifetime_maintenance_cost = analysis.annual_maintenance_cost * product.expected_lifetime_years
        analysis.lifetime_repair_cost = analysis.annual_repair_cost * product.expected_lifetime_years
        analysis.total_lifetime_cost = (
            analysis.total_initial_cost +
            analysis.lifetime_operating_cost +
            analysis.lifetime_maintenance_cost +
            analysis.lifetime_repair_cost
        )
        
        # Calculate value metrics
        analysis.cost_per_year = analysis.total_lifetime_cost / product.expected_lifetime_years if product.expected_lifetime_years > 0 else 0
        analysis.cost_per_use = self._calculate_cost_per_use(product)
        analysis.lifetime_value = self._calculate_lifetime_value(product)
        analysis.roi_percentage = self._calculate_roi(product)
        
        # Calculate comparison savings
        analysis.new_vs_refurbished_savings = self._calculate_refurbished_savings(product)
        analysis.disposable_vs_reusable_savings = self._calculate_reusable_savings(product)
        analysis.short_vs_long_term_savings = self._calculate_long_term_savings(product)
        analysis.local_vs_imported_savings = self._calculate_local_savings(product)
        
        # Calculate financial score
        analysis.financial_score = self._calculate_financial_score(analysis)
        
        return analysis
    
    def _calculate_operating_cost(self, product: Product) -> float:
        """
        Calculate annual operating cost.
        """
        cost = 0.0
        
        # Energy cost
        if product.energy_consumption_kwh > 0:
            cost += product.energy_consumption_kwh * 0.15  # $0.15 per kWh
        
        # Water cost
        if product.water_footprint_liters > 0:
            cost += product.water_footprint_liters * 0.001  # $0.001 per liter
        
        # Other operating costs (simplified)
        cost += product.price * 0.01  # 1% of price for general operating costs
        
        return cost
    
    def _calculate_maintenance_cost(self, product: Product) -> float:
        """
        Calculate annual maintenance cost.
        """
        # Base maintenance cost
        base_cost = product.price * 0.02  # 2% of price
        
        # Adjust for durability
        if product.durability_rating > 70:
            base_cost *= 0.5
        elif product.durability_rating < 30:
            base_cost *= 2.0
        
        return base_cost
    
    def _calculate_repair_cost(self, product: Product) -> float:
        """
        Calculate annual repair cost.
        """
        # Base repair cost
        base_cost = product.price * 0.01  # 1% of price
        
        # Adjust for repairability
        if product.repairability_score > 70:
            base_cost *= 0.5
        elif product.repairability_score < 30:
            base_cost *= 3.0
        
        return base_cost
    
    def _calculate_cost_per_use(self, product: Product) -> float:
        """
        Calculate cost per use.
        """
        if product.expected_lifetime_years <= 0:
            return 0
        
        # Estimate uses per year (simplified)
        uses_per_year = 365  # Daily use for most products
        
        if product.category.value in ['clothing', 'footwear']:
            uses_per_year = 150
        elif product.category.value == 'electronics':
            uses_per_year = 365
        elif product.category.value == 'appliances':
            uses_per_year = 250
        elif product.category.value == 'furniture':
            uses_per_year = 365
        elif product.category.value == 'food':
            uses_per_year = 365
        
        total_uses = uses_per_year * product.expected_lifetime_years
        
        if total_uses > 0:
            return product.price / total_uses
        
        return 0
    
    def _calculate_lifetime_value(self, product: Product) -> float:
        """
        Calculate lifetime value.
        """
        if product.expected_lifetime_years <= 0:
            return 0
        
        # Calculate total savings from use
        daily_value = product.price * 0.01  # Value per day of use
        total_uses = 365 * product.expected_lifetime_years
        
        value = daily_value * total_uses
        
        # Add resale value at end of life
        if product.durability_rating > 70:
            resale_value = product.price * 0.3
        elif product.durability_rating > 50:
            resale_value = product.price * 0.15
        else:
            resale_value = product.price * 0.05
        
        value += resale_value
        
        return value
    
    def _calculate_roi(self, product: Product) -> float:
        """
        Calculate return on investment.
        """
        if product.price <= 0:
            return 0
        
        lifetime_value = self._calculate_lifetime_value(product)
        
        if lifetime_value > 0:
            return ((lifetime_value - product.price) / product.price) * 100
        
        return 0
    
    def _calculate_refurbished_savings(self, product: Product) -> float:
        """
        Calculate savings from buying refurbished.
        """
        if product.condition == 'new':
            refurbished_price = product.price * 0.7
            return product.price - refurbished_price
        
        return 0
    
    def _calculate_reusable_savings(self, product: Product) -> float:
        """
        Calculate savings from buying reusable.
        """
        if product.category.value in ['food', 'beverages']:
            # Assume replacing 100 disposable items
            disposable_cost = 100 * 0.5  # $0.50 each for disposable
            reusable_cost = product.price
            savings = disposable_cost - reusable_cost
            
            if savings > 0:
                return savings
            else:
                return 0
        
        return 0
    
    def _calculate_long_term_savings(self, product: Product) -> float:
        """
        Calculate long-term savings vs short-term alternatives.
        """
        if product.expected_lifetime_years <= 0:
            return 0
        
        # Compare with buying cheaper products more frequently
        short_term_price = product.price * 0.4
        short_term_lifetime = product.expected_lifetime_years / 3
        
        long_term_cost = product.price
        short_term_cost = short_term_price * 3  # Buy 3 times
        
        savings = short_term_cost - long_term_cost
        
        return max(0, savings)
    
    def _calculate_local_savings(self, product: Product) -> float:
        """
        Calculate savings from buying local.
        """
        # Local product would have lower shipping costs
        if product.shipping_distance_km > 1000:
            shipping_savings = product.shipping_distance_km * 0.001  # $0.001 per km
            return shipping_savings
        
        return 0
    
    def _calculate_financial_score(self, analysis: FinancialAnalysis) -> float:
        """
        Calculate financial score (0-100).
        """
        score = 0.0
        
        # Cost per year (lower is better)
        if analysis.cost_per_year > 0:
            cost_score = max(0, 100 - (analysis.cost_per_year * 0.5))
            score += cost_score * 0.3
        
        # ROI (higher is better)
        if analysis.roi_percentage > 0:
            roi_score = min(100, analysis.roi_percentage)
            score += roi_score * 0.3
        
        # Lifetime value (higher is better)
        if analysis.lifetime_value > 0:
            value_score = min(100, analysis.lifetime_value / 10)
            score += value_score * 0.2
        
        # Cost savings (higher is better)
        savings = (
            analysis.new_vs_refurbished_savings +
            analysis.disposable_vs_reusable_savings +
            analysis.short_vs_long_term_savings
        )
        if savings > 0:
            savings_score = min(100, savings * 2)
            score += savings_score * 0.2
        
        return min(100, max(0, score))