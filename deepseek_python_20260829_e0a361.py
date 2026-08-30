"""
Sustainable Shopping & Product Impact Analyzer - Streamlit UI Page
User interface for sustainable shopping analysis.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from typing import List, Dict, Any

from shopping.models import (
    Product, ProductCategory, ProductCondition,
    MaterialComposition, PackagingAssessment
)
from shopping.analyzer import ShoppingAnalyzer
from shopping.database import ShoppingDatabase
from shopping.visualizations import ShoppingVisualizer
from shopping.recommendations import RecommendationEngine
from shopping.comparisons import ProductComparator

# Initialize components
analyzer = ShoppingAnalyzer()
database = ShoppingDatabase()
visualizer = ShoppingVisualizer()
recommendation_engine = RecommendationEngine()
comparator = ProductComparator()


def init_session_state():
    """Initialize session state variables."""
    if 'shopping_products' not in st.session_state:
        st.session_state.shopping_products = []
    if 'current_product' not in st.session_state:
        st.session_state.current_product = None
    if 'comparison_products' not in st.session_state:
        st.session_state.comparison_products = []
    if 'purchase_history' not in st.session_state:
        st.session_state.purchase_history = []


def main():
    """Main function for the shopping analyzer page."""
    st.set_page_config(
        page_title="Sustainable Shopping Analyzer",
        page_icon="🛒",
        layout="wide"
    )
    
    init_session_state()
    
    st.title("🛒 Sustainable Shopping & Product Impact Analyzer")
    st.markdown("""
        Evaluate products before purchasing to understand their environmental, 
        financial, and sustainability impact.
    """)
    
    # Sidebar navigation
    with st.sidebar:
        st.header("📋 Navigation")
        page = st.radio(
            "Select Option",
            [
                "🔍 Product Analysis",
                "📊 Product Comparison",
                "📈 Purchase History",
                "💡 Recommendations"
            ]
        )
        
        st.divider()
        st.header("📚 Quick Links")
        st.info("""
        **Features:**
        - Product sustainability scoring
        - Environmental impact analysis
        - Financial comparison
        - Purchase alternatives
        - Personalized recommendations
        """)
    
    if page == "🔍 Product Analysis":
        render_product_analysis()
    elif page == "📊 Product Comparison":
        render_product_comparison()
    elif page == "📈 Purchase History":
        render_purchase_history()
    elif page == "💡 Recommendations":
        render_recommendations()


def render_product_analysis():
    """Render product analysis interface."""
    st.header("🔍 Product Analysis")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Product Input")
        
        product_name = st.text_input("Product Name")
        brand = st.text_input("Brand")
        category = st.selectbox(
            "Category",
            [c.value.replace('_', ' ').title() for c in ProductCategory]
        )
        condition = st.selectbox(
            "Condition",
            [c.value.replace('_', ' ').title() for c in ProductCondition]
        )
        price = st.number_input("Price ($)", min_value=0.0, step=5.0)
        weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)
        expected_lifetime = st.number_input("Expected Lifetime (years)", min_value=0.0, step=0.5)
        
        st.subheader("Material Composition")
        num_materials = st.number_input("Number of Materials", min_value=0, max_value=10, step=1)
        
        materials = []
        for i in range(num_materials):
            with st.container():
                st.write(f"Material {i+1}")
                col_a, col_b = st.columns(2)
                with col_a:
                    material_type = st.selectbox(
                        f"Type {i+1}",
                        ['plastic', 'metal', 'glass', 'wood', 'paper', 'fabric'],
                        key=f"mat_type_{i}"
                    )
                with col_b:
                    percentage = st.number_input(
                        f"Percentage {i+1}",
                        min_value=0.0,
                        max_value=100.0,
                        value=10.0,
                        key=f"mat_pct_{i}"
                    )
                
                materials.append({
                    'type': material_type,
                    'percentage': percentage
                })
        
        if st.button("🔍 Analyze Product", use_container_width=True):
            if product_name and materials:
                product = create_product_from_input(
                    product_name, brand, category, condition,
                    price, weight, expected_lifetime, materials
                )
                
                with st.spinner("Analyzing product..."):
                    analysis = analyzer.analyze_product(product)
                    st.session_state.current_product = product
                    st.session_state.current_analysis = analysis
                    st.success("Product analyzed!")
                    st.rerun()
            else:
                st.error("Please enter product name and materials.")
    
    with col2:
        if st.session_state.current_product:
            display_product_analysis()


def create_product_from_input(name, brand, category, condition, price, weight, lifetime, materials):
    """Create product object from input."""
    product = Product(
        name=name,
        brand=brand,
        category=ProductCategory(category.lower().replace(' ', '_')),
        condition=ProductCondition(condition.lower().replace(' ', '_')),
        price=price,
        weight_kg=weight,
        expected_lifetime_years=lifetime,
        materials=[]
    )
    
    for mat in materials:
        product.materials.append(
            MaterialComposition(
                material_type=mat['type'],
                percentage=mat['percentage']
            )
        )
    
    return product


def display_product_analysis():
    """Display product analysis results."""
    product = st.session_state.current_product
    analysis = st.session_state.current_analysis
    
    st.subheader(f"📋 {product.name}")
    
    # Score overview
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sustainability Score", f"{product.sustainability_score:.1f}%")
    with col2:
        st.metric("Environmental Score", f"{product.environmental_score:.1f}%")
    with col3:
        st.metric("Financial Score", f"{product.financial_score:.1f}%")
    with col4:
        st.metric("Durability", f"{product.durability_rating:.1f}%")
    
    # Tabs for detailed analysis
    tabs = st.tabs([
        "🌍 Environmental Impact",
        "💰 Financial Analysis",
        "♻️ Lifecycle Assessment",
        "🔄 Alternatives",
        "📊 Visualizations"
    ])
    
    with tabs[0]:
        display_environmental_impact(analysis)
    
    with tabs[1]:
        display_financial_analysis(analysis)
    
    with tabs[2]:
        display_lifecycle_assessment(analysis)
    
    with tabs[3]:
        display_alternatives(analysis)
    
    with tabs[4]:
        display_visualizations(product)


def display_environmental_impact(analysis):
    """Display environmental impact analysis."""
    impact = analysis['environmental_impact']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Carbon Footprint")
        st.metric("Total Carbon", f"{impact.total_carbon_kg:.2f} kg CO2e")
        st.metric("Manufacturing", f"{impact.manufacturing_carbon_kg:.2f} kg")
        st.metric("Transport", f"{impact.transport_carbon_kg:.2f} kg")
        st.metric("Usage", f"{impact.usage_carbon_kg:.2f} kg")
        st.metric("Disposal", f"{impact.disposal_carbon_kg:.2f} kg")
    
    with col2:
        st.subheader("Other Impacts")
        st.metric("Total Energy", f"{impact.total_energy_kwh:.2f} kWh")
        st.metric("Total Water", f"{impact.total_water_liters:.2f} L")
        st.metric("Total Waste", f"{impact.total_waste_kg:.2f} kg")
        st.metric("Packaging Waste", f"{impact.packaging_waste_kg:.2f} kg")
        st.metric("Carbon Intensity", f"{impact.carbon_intensity:.3f} kg/$")


def display_financial_analysis(analysis):
    """Display financial analysis."""
    financial = analysis['financial_analysis']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Cost Breakdown")
        st.metric("Purchase Price", f"${financial.purchase_price:.2f}")
        st.metric("Tax", f"${financial.tax:.2f}")
        st.metric("Shipping", f"${financial.shipping_cost:.2f}")
        st.metric("Total Initial", f"${financial.total_initial_cost:.2f}")
        st.metric("Annual Cost", f"${financial.total_annual_cost:.2f}")
    
    with col2:
        st.subheader("Value Metrics")
        st.metric("Cost Per Year", f"${financial.cost_per_year:.2f}")
        st.metric("Cost Per Use", f"${financial.cost_per_use:.3f}")
        st.metric("Lifetime Value", f"${financial.lifetime_value:.2f}")
        st.metric("ROI", f"{financial.roi_percentage:.1f}%")
        st.metric("Financial Score", f"{financial.financial_score:.1f}%")


def display_lifecycle_assessment(analysis):
    """Display lifecycle assessment."""
    lifecycle = analysis['lifecycle_assessment']
    
    st.subheader("Lifecycle Stage Scores")
    
    stages = lifecycle.get('lifecycle_scores', {})
    if stages:
        cols = st.columns(3)
        for i, (stage, score) in enumerate(stages.items()):
            with cols[i % 3]:
                if i < 9:
                    st.metric(
                        stage.replace('_', ' ').title(),
                        f"{score:.1f}%"
                    )
    
    st.subheader("Recommendations")
    for rec in lifecycle.get('lifecycle_recommendations', []):
        st.info(f"💡 {rec}")


def display_alternatives(analysis):
    """Display product alternatives."""
    alternatives = analysis.get('alternatives', [])
    
    if alternatives:
        st.subheader("🔄 Sustainable Alternatives")
        
        for alt in alternatives:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{alt.product_name}**")
                    st.write(alt.description)
                with col2:
                    st.write(f"${alt.price:.2f}")
                with col3:
                    st.write(f"♻️ {alt.sustainability_score:.0f}%")
                with col4:
                    st.write(f"✅ {alt.recommendation_type.value.title()}")
                st.divider()
    else:
        st.info("No alternatives found for this product.")


def display_visualizations(product):
    """Display product visualizations."""
    st.subheader("📊 Sustainability Radar")
    fig = visualizer.create_sustainability_radar_chart(product)
    st.plotly_chart(fig, use_container_width=True)


def render_product_comparison():
    """Render product comparison interface."""
    st.header("📊 Product Comparison")
    
    st.info("Add multiple products to compare their sustainability and value.")
    
    # Product selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Product 1")
        # Would normally select from database
        product1_name = st.text_input("Product 1 Name")
    
    with col2:
        st.subheader("Product 2")
        product2_name = st.text_input("Product 2 Name")
    
    if st.button("Compare Products"):
        if product1_name and product2_name:
            # Create sample products for demo
            product1 = Product(
                name=product1_name,
                category=ProductCategory.OTHER,
                sustainability_score=75.0,
                environmental_score=70.0,
                financial_score=80.0,
                durability_rating=65.0,
                repairability_score=60.0,
                recyclability_score=55.0
            )
            
            product2 = Product(
                name=product2_name,
                category=ProductCategory.OTHER,
                sustainability_score=60.0,
                environmental_score=55.0,
                financial_score=70.0,
                durability_rating=75.0,
                repairability_score=50.0,
                recyclability_score=65.0
            )
            
            comparison = comparator.compare([product1, product2])
            
            st.subheader("Comparison Results")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Best Overall", comparison.best_overall)
                st.metric("Best Environmental", comparison.best_environmental)
            with col2:
                st.metric("Best Financial", comparison.best_financial)
                st.metric("Best Durability", comparison.best_durability)
            
            # Visualization
            fig = visualizer.create_product_comparison_chart([product1, product2])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.error("Please enter both product names.")


def render_purchase_history():
    """Render purchase history interface."""
    st.header("📈 Purchase History")
    
    # Add purchase form
    with st.expander("➕ Add Purchase", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("Product Name")
            price_paid = st.number_input("Price Paid ($)", min_value=0.0)
        with col2:
            quantity = st.number_input("Quantity", min_value=1, value=1)
            product_category = st.selectbox(
                "Category",
                [c.value.replace('_', ' ').title() for c in ProductCategory]
            )
        
        if st.button("Add Purchase"):
            if product_name and price_paid > 0:
                purchase = create_purchase_entry(
                    product_name, price_paid, quantity, product_category
                )
                database.save_purchase(purchase)
                st.success("Purchase added!")
                st.rerun()
    
    # Display purchase history
    user_id = st.session_state.get('user_id', 'demo_user')
    purchases = database.get_user_purchases(user_id)
    
    if purchases:
        st.subheader(f"📋 Purchase History ({len(purchases)} purchases)")
        
        # Summary metrics
        total_spent = sum(p.price_paid * p.quantity for p in purchases)
        total_carbon = sum(p.estimated_carbon_kg for p in purchases)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Spent", f"${total_spent:.2f}")
        with col2:
            st.metric("Total Carbon", f"{total_carbon:.1f} kg CO2e")
        with col3:
            st.metric("Total Purchases", len(purchases))
        
        # Visualization
        fig = visualizer.create_purchase_trends(purchases)
        st.plotly_chart(fig, use_container_width=True)
        
        # Purchase table
        st.subheader("Recent Purchases")
        for purchase in purchases[:10]:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.write(f"**{purchase.product_name}**")
                with col2:
                    st.write(f"${purchase.price_paid:.2f}")
                with col3:
                    st.write(f"♻️ {purchase.estimated_carbon_kg:.1f}kg")
                with col4:
                    st.write(purchase.purchase_date.strftime('%Y-%m-%d'))
                st.divider()
    else:
        st.info("No purchase history found.")


def create_purchase_entry(name, price, quantity, category):
    """Create a purchase entry."""
    return {
        'product_name': name,
        'price_paid': price,
        'quantity': quantity,
        'product_category': category.lower().replace(' ', '_'),
        'purchase_date': datetime.now(),
        'estimated_carbon_kg': price * 0.5  # Simple estimation
    }


def render_recommendations():
    """Render recommendations interface."""
    st.header("💡 Personalized Recommendations")
    
    st.info("Based on your sustainability goals and purchase history.")
    
    # User context
    user_context = {
        'user_id': st.session_state.get('user_id', 'demo_user'),
        'goals': ['Reduce carbon footprint', 'Buy sustainable products'],
        'habits': ['Weekly shopping', 'Eco-conscious'],
        'budget': 500.0,
        'preferred_categories': [ProductCategory.ELECTRONICS, ProductCategory.CLOTHING]
    }
    
    # Generate sample recommendations
    sample_products = create_sample_products()
    
    if st.button("Generate Recommendations"):
        with st.spinner("Generating recommendations..."):
            recommendations = recommendation_engine.generate_recommendations(
                sample_products,
                user_context
            )
            
            if recommendations:
                for rec in recommendations:
                    display_recommendation(rec)
            else:
                st.warning("No recommendations available.")
    
    st.divider()
    st.subheader("💡 Sustainable Alternatives")
    
    # Quick alternative suggestions
    st.markdown("""
    ### Common Sustainable Alternatives
    
    **Clothing**
    - Buy organic cotton or recycled materials
    - Choose durable, classic styles
    - Consider second-hand or vintage
    
    **Electronics**
    - Look for Energy Star certified products
    - Consider refurbished devices
    - Choose products with good repairability
    
    **Food**
    - Buy local and seasonal produce
    - Reduce packaging waste
    - Choose fair trade products
    
    **Cleaning Products**
    - Use eco-friendly ingredients
    - Choose concentrated formulas
    - Opt for refillable containers
    """)


def display_recommendation(rec):
    """Display a single recommendation."""
    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            emoji = {
                'buy': '✅',
                'consider': '💡',
                'avoid': '❌',
                'delay': '⏳',
                'upgrade': '⬆️',
                'alternative': '🔄'
            }.get(rec.recommendation_type.value, 'ℹ️')
            
            st.write(f"{emoji} **{rec.product_name}**")
            st.write(f"*{rec.reason}*")
        
        with col2:
            st.metric("Confidence", f"{rec.confidence:.0%}")
        
        with col3:
            if rec.estimated_savings:
                savings = rec.estimated_savings
                if 'carbon' in savings:
                    st.write(f"🌍 Save {savings['carbon']:.1f}kg CO2e")
        
        st.divider()


def create_sample_products():
    """Create sample products for demonstration."""
    return [
        Product(
            name="Eco-Friendly Bamboo Toothbrush",
            category=ProductCategory.OTHER,
            price=5.99,
            sustainability_score=85.0,
            environmental_score=90.0,
            financial_score=75.0,
            durability_rating=70.0,
            repairability_score=40.0,
            recyclability_score=80.0,
            carbon_footprint_kg=0.5,
            waste_generation_kg=0.05
        ),
        Product(
            name="Reusable Stainless Steel Bottle",
            category=ProductCategory.OTHER,
            price=24.99,
            sustainability_score=78.0,
            environmental_score=82.0,
            financial_score=70.0,
            durability_rating=90.0,
            repairability_score=30.0,
            recyclability_score=85.0,
            carbon_footprint_kg=2.0,
            waste_generation_kg=0.1
        ),
        Product(
            name="Organic Cotton T-Shirt",
            category=ProductCategory.CLOTHING,
            price=29.99,
            sustainability_score=72.0,
            environmental_score=75.0,
            financial_score=68.0,
            durability_rating=80.0,
            repairability_score=50.0,
            recyclability_score=60.0,
            carbon_footprint_kg=5.0,
            waste_generation_kg=0.2
        ),
        Product(
            name="Energy Star Refrigerator",
            category=ProductCategory.APPLIANCES,
            price=800.0,
            sustainability_score=70.0,
            environmental_score=65.0,
            financial_score=75.0,
            durability_rating=85.0,
            repairability_score=55.0,
            recyclability_score=60.0,
            carbon_footprint_kg=100.0,
            energy_consumption_kwh=400.0
        ),
        Product(
            name="LED Light Bulb Pack",
            category=ProductCategory.OTHER,
            price=15.99,
            sustainability_score=82.0,
            environmental_score=85.0,
            financial_score=80.0,
            durability_rating=75.0,
            repairability_score=20.0,
            recyclability_score=65.0,
            carbon_footprint_kg=1.5,
            energy_consumption_kwh=9.0
        )
    ]


if __name__ == "__main__":
    main()