"""
Sustainable Shopping & Product Impact Analyzer - Visualizations
Chart and visualization functions for shopping analysis.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from shopping.models import Product, EnvironmentalImpact, FinancialAnalysis, PurchaseHistory

logger = logging.getLogger(__name__)


class ShoppingVisualizer:
    """
    Creates visualizations for shopping analysis.
    """
    
    def __init__(self):
        """Initialize the visualizer."""
        logger.info("Shopping Visualizer initialized")
    
    def create_product_comparison_chart(self, products: List[Product]) -> go.Figure:
        """
        Create a product comparison chart.
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Sustainability Scores',
                'Environmental Impact',
                'Cost Analysis',
                'Durability & Repairability'
            )
        )
        
        # Sustainability scores
        names = [p.name[:20] for p in products]
        
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.sustainability_score for p in products],
                name='Sustainability',
                marker_color='green'
            ),
            row=1, col=1
        )
        
        # Environmental impact
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.carbon_footprint_kg for p in products],
                name='Carbon (kg)',
                marker_color='orange'
            ),
            row=1, col=2
        )
        
        # Cost analysis
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.price for p in products],
                name='Price ($)',
                marker_color='blue'
            ),
            row=2, col=1
        )
        
        # Durability and repairability
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.durability_rating for p in products],
                name='Durability',
                marker_color='purple'
            ),
            row=2, col=2
        )
        
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.repairability_score for p in products],
                name='Repairability',
                marker_color='pink'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=600,
            showlegend=True,
            title_text="Product Comparison Dashboard"
        )
        
        return fig
    
    def create_sustainability_radar_chart(self, product: Product) -> go.Figure:
        """
        Create a sustainability radar chart.
        """
        categories = ['Environmental', 'Social', 'Economic', 'Lifecycle', 'Durability', 'Repairability']
        
        values = [
            product.environmental_score,
            self._calculate_social_score(product),
            product.financial_score,
            self._calculate_lifecycle_score(product),
            product.durability_rating,
            product.repairability_score
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=product.name,
            line_color='green'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            title=f"Sustainability Radar: {product.name}"
        )
        
        return fig
    
    def create_environmental_breakdown(self, impact: EnvironmentalImpact) -> go.Figure:
        """
        Create environmental impact breakdown chart.
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Carbon Footprint Breakdown',
                'Water Footprint',
                'Energy Consumption',
                'Waste Generation'
            )
        )
        
        # Carbon breakdown
        fig.add_trace(
            go.Bar(
                x=['Manufacturing', 'Transport', 'Usage', 'Disposal'],
                y=[
                    impact.manufacturing_carbon_kg,
                    impact.transport_carbon_kg,
                    impact.usage_carbon_kg,
                    impact.disposal_carbon_kg
                ],
                name='Carbon (kg CO2e)',
                marker_color='red'
            ),
            row=1, col=1
        )
        
        # Water footprint
        fig.add_trace(
            go.Bar(
                x=['Manufacturing', 'Usage'],
                y=[
                    impact.manufacturing_water_liters,
                    impact.usage_water_liters
                ],
                name='Water (liters)',
                marker_color='blue'
            ),
            row=1, col=2
        )
        
        # Energy consumption
        fig.add_trace(
            go.Bar(
                x=['Manufacturing', 'Usage'],
                y=[
                    impact.manufacturing_energy_kwh,
                    impact.usage_energy_kwh
                ],
                name='Energy (kWh)',
                marker_color='yellow'
            ),
            row=2, col=1
        )
        
        # Waste generation
        fig.add_trace(
            go.Bar(
                x=['Manufacturing', 'Packaging', 'Disposal'],
                y=[
                    impact.manufacturing_waste_kg,
                    impact.packaging_waste_kg,
                    impact.end_of_life_waste_kg
                ],
                name='Waste (kg)',
                marker_color='brown'
            ),
            row=2, col=2
        )
        
        fig.update_layout(height=600, showlegend=True)
        
        return fig
    
    def create_financial_comparison(self, products: List[Product]) -> go.Figure:
        """
        Create financial comparison chart.
        """
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                'Cost Comparison',
                'Long-term Savings'
            )
        )
        
        names = [p.name[:20] for p in products]
        
        # Cost comparison
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.price for p in products],
                name='Initial Cost ($)',
                marker_color='blue'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.cost_per_year for p in products],
                name='Cost Per Year ($)',
                marker_color='orange'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.lifetime_value for p in products],
                name='Lifetime Value ($)',
                marker_color='green'
            ),
            row=1, col=1
        )
        
        # Long-term savings
        fig.add_trace(
            go.Bar(
                x=names,
                y=[p.long_term_savings for p in products],
                name='Long-term Savings',
                marker_color='purple'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=600,
            showlegend=True,
            title_text="Financial Comparison"
        )
        
        return fig
    
    def create_purchase_trends(self, purchases: List[PurchaseHistory]) -> go.Figure:
        """
        Create purchase trends chart.
        """
        if not purchases:
            return go.Figure()
        
        # Sort purchases by date
        sorted_purchases = sorted(purchases, key=lambda x: x.purchase_date)
        dates = [p.purchase_date for p in sorted_purchases]
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Monthly Spending',
                'Carbon Impact Trend',
                'Category Breakdown',
                'Impact per Purchase'
            )
        )
        
        # Monthly spending
        monthly_spending = {}
        for p in sorted_purchases:
            month = p.purchase_date.strftime('%Y-%m')
            monthly_spending[month] = monthly_spending.get(month, 0) + p.price_paid * p.quantity
        
        fig.add_trace(
            go.Scatter(
                x=list(monthly_spending.keys()),
                y=list(monthly_spending.values()),
                mode='lines+markers',
                name='Monthly Spending ($)'
            ),
            row=1, col=1
        )
        
        # Carbon impact trend
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=[p.estimated_carbon_kg for p in sorted_purchases],
                mode='lines+markers',
                name='Carbon Impact (kg)',
                line_color='red'
            ),
            row=1, col=2
        )
        
        # Category breakdown
        categories = {}
        for p in sorted_purchases:
            cat = p.product_category or 'Other'
            categories[cat] = categories.get(cat, 0) + p.price_paid * p.quantity
        
        fig.add_trace(
            go.Pie(
                labels=list(categories.keys()),
                values=list(categories.values()),
                name='Category Spending'
            ),
            row=2, col=1
        )
        
        # Impact per purchase
        fig.add_trace(
            go.Bar(
                x=[p.product_name[:15] for p in sorted_purchases],
                y=[p.estimated_carbon_kg for p in sorted_purchases],
                name='Carbon per Purchase',
                marker_color='orange'
            ),
            row=2, col=2
        )
        
        fig.update_layout(height=600, showlegend=True)
        
        return fig
    
    def create_lifecycle_comparison(self, products: List[Product]) -> go.Figure:
        """
        Create lifecycle comparison chart.
        """
        fig = go.Figure()
        
        stages = ['Raw Materials', 'Manufacturing', 'Transport', 'Usage', 'Disposal']
        
        for product in products:
            scores = self._get_lifecycle_scores(product)
            fig.add_trace(go.Scatter(
                x=stages,
                y=scores,
                mode='lines+markers',
                name=product.name[:20]
            ))
        
        fig.update_layout(
            title="Lifecycle Impact Comparison",
            xaxis_title="Lifecycle Stage",
            yaxis_title="Score (0-100)",
            yaxis_range=[0, 100],
            height=500,
            showlegend=True
        )
        
        return fig
    
    def create_sustainability_heatmap(self, products: List[Product]) -> go.Figure:
        """
        Create sustainability heatmap.
        """
        metrics = ['Sustainability', 'Environmental', 'Financial', 'Durability', 'Repairability', 'Recyclability']
        
        data = []
        for product in products:
            data.append([
                product.sustainability_score,
                product.environmental_score,
                product.financial_score,
                product.durability_rating,
                product.repairability_score,
                product.recyclability_score
            ])
        
        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=metrics,
            y=[p.name[:20] for p in products],
            colorscale='RdYlGn',
            zmin=0,
            zmax=100
        ))
        
        fig.update_layout(
            title="Sustainability Heatmap",
            height=400,
            xaxis_title="Metric",
            yaxis_title="Product"
        )
        
        return fig
    
    def _calculate_social_score(self, product: Product) -> float:
        """Helper to calculate social score."""
        score = 50.0
        if product.certifications:
            score += min(20, len(product.certifications) * 5)
        if product.eco_labels:
            score += min(20, len(product.eco_labels) * 5)
        return min(100, max(0, score))
    
    def _calculate_lifecycle_score(self, product: Product) -> float:
        """Helper to calculate lifecycle score."""
        score = (
            product.durability_rating * 0.4 +
            product.repairability_score * 0.3 +
            product.recyclability_score * 0.3
        )
        return min(100, max(0, score))
    
    def _get_lifecycle_scores(self, product: Product) -> List[float]:
        """Get lifecycle stage scores."""
        # Simplified scores for each stage
        return [
            70.0,  # Raw materials
            65.0,  # Manufacturing
            75.0,  # Transport
            product.durability_rating,  # Usage
            product.recyclability_score  # Disposal
        ]