"""
AI-Powered Waste Management & Recycling Assistant Module
Contributor: Community Developer
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging
import json
import time
import hashlib
from collections import defaultdict
import base64
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class WasteItem:
    """Data structure for waste items"""
    category: str
    sub_category: str
    weight_kg: float
    date: datetime
    recyclable: bool
    co2_impact: float
    disposal_method: str
    image_path: Optional[str] = None

@dataclass
class RecyclingCenter:
    """Data structure for recycling centers"""
    name: str
    address: str
    latitude: float
    longitude: float
    accepted_materials: List[str]
    distance_km: float
    operating_hours: str
    phone: str

@dataclass
class WasteReductionTip:
    """Data structure for waste reduction tips"""
    title: str
    description: str
    difficulty: str
    potential_savings: float
    category: str
    source: str

# ============================================================
# WASTE CLASSIFIER ENGINE
# ============================================================

class WasteClassifier:
    """
    AI-powered waste classification using MobileNetV2 transfer learning
    """
    
    def __init__(self, model_path: str = None):
        self.categories = {
            'plastic': ['bottle', 'container', 'bag', 'packaging', 'straw'],
            'glass': ['bottle', 'jar', 'container', 'window'],
            'paper': ['newspaper', 'cardboard', 'magazine', 'office_paper'],
            'metal': ['can', 'foil', 'container', 'utensil'],
            'organic': ['food_waste', 'yard_waste', 'compost'],
            'electronic': ['battery', 'phone', 'computer', 'charger'],
            'textile': ['clothing', 'fabric', 'carpet'],
            'hazardous': ['chemical', 'paint', 'oil', 'medical']
        }
        
        self.recyclable_mapping = {
            'plastic': True,
            'glass': True,
            'paper': True,
            'metal': True,
            'organic': False,
            'electronic': True,
            'textile': False,
            'hazardous': False
        }
        
        self.disposal_methods = {
            'plastic': 'recycle',
            'glass': 'recycle',
            'paper': 'recycle',
            'metal': 'recycle',
            'organic': 'compost',
            'electronic': 'ewaste',
            'textile': 'donate',
            'hazardous': 'special_handling'
        }
        
        self.co2_factors = {
            'plastic': 6.0,
            'glass': 3.0,
            'paper': 4.0,
            'metal': 12.0,
            'organic': 1.0,
            'electronic': 20.0,
            'textile': 8.0,
            'hazardous': 15.0
        }
        
        # Initialize model (simplified for contribution)
        self.model_initialized = False
        
    def initialize_model(self):
        """Initialize the ML model"""
        try:
            # Simulate model loading
            time.sleep(0.5)
            self.model_initialized = True
            logger.info("Waste classifier model initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Model initialization failed: {e}")
            return False
    
    def classify_item(self, image_array: np.ndarray) -> Dict:
        """
        Classify waste item from image
        
        Args:
            image_array: NumPy array of image
            
        Returns:
            Dictionary with classification results
        """
        # Check if model is initialized
        if not self.model_initialized:
            self.initialize_model()
        
        # Simulate classification (would be actual ML prediction)
        # Random selection for demo
        categories = list(self.categories.keys())
        selected_category = np.random.choice(categories)
        
        # Determine sub-category
        sub_categories = self.categories[selected_category]
        selected_sub = np.random.choice(sub_categories) if sub_categories else selected_category
        
        # Calculate confidence
        confidence = 0.75 + np.random.random() * 0.20  # 75-95%
        
        # Alternative classifications
        alternatives = []
        other_cats = [c for c in categories if c != selected_category]
        for _ in range(3):
            alt_cat = np.random.choice(other_cats)
            alternatives.append({
                'category': alt_cat,
                'confidence': 0.3 + np.random.random() * 0.3
            })
        
        result = {
            'category': selected_category,
            'sub_category': selected_sub,
            'confidence': confidence,
            'alternatives': alternatives,
            'recyclable': self.recyclable_mapping.get(selected_category, False),
            'disposal_method': self.disposal_methods.get(selected_category, 'unknown'),
            'co2_factor': self.co2_factors.get(selected_category, 5.0)
        }
        
        return result
    
    def estimate_weight(self, category: str, image_array: np.ndarray) -> float:
        """Estimate weight based on category and image characteristics"""
        # Simulate weight estimation
        base_weights = {
            'plastic': 0.15,
            'glass': 0.5,
            'paper': 0.2,
            'metal': 0.3,
            'organic': 0.8,
            'electronic': 0.7,
            'textile': 0.4,
            'hazardous': 0.6
        }
        
        weight = base_weights.get(category, 0.2)
        # Add some variation
        weight *= (0.8 + np.random.random() * 0.4)
        
        return round(weight, 2)

# ============================================================
# RECYCLING CENTER LOCATOR
# ============================================================

class RecyclingLocator:
    """
    Find recycling centers using geospatial data
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.default_centers = self._generate_mock_centers()
    
    def _generate_mock_centers(self) -> List[RecyclingCenter]:
        """Generate mock recycling centers for demo"""
        centers = [
            RecyclingCenter(
                name="Green Earth Recycling Center",
                address="123 Main St, City",
                latitude=40.7128 + np.random.normal(0, 0.05),
                longitude=-74.0060 + np.random.normal(0, 0.05),
                accepted_materials=['plastic', 'glass', 'paper', 'metal'],
                distance_km=0,
                operating_hours="Mon-Sat: 8AM-6PM",
                phone="(555) 123-4567"
            ),
            RecyclingCenter(
                name="Eco-Recover Facility",
                address="456 Park Ave, City",
                latitude=40.7128 + np.random.normal(0, 0.08),
                longitude=-74.0060 + np.random.normal(0, 0.08),
                accepted_materials=['electronic', 'metal', 'plastic'],
                distance_km=0,
                operating_hours="Mon-Fri: 9AM-7PM, Sat: 9AM-4PM",
                phone="(555) 234-5678"
            ),
            RecyclingCenter(
                name="Sustainable Materials Recovery",
                address="789 Oak St, City",
                latitude=40.7128 + np.random.normal(0, 0.10),
                longitude=-74.0060 + np.random.normal(0, 0.10),
                accepted_materials=['paper', 'organic', 'glass', 'textile'],
                distance_km=0,
                operating_hours="Mon-Sun: 7AM-8PM",
                phone="(555) 345-6789"
            )
        ]
        
        # Calculate distances
        base_lat = 40.7128
        base_lon = -74.0060
        
        for center in centers:
            lat_diff = center.latitude - base_lat
            lon_diff = center.longitude - base_lon
            # Approximate distance in km (1 degree ~ 111 km)
            center.distance_km = round(np.sqrt((lat_diff * 111)**2 + (lon_diff * 111 * np.cos(np.radians(base_lat)))**2), 1)
        
        return centers
    
    def find_centers(self, latitude: float, longitude: float, radius_km: float = 10.0) -> List[RecyclingCenter]:
        """Find recycling centers within radius"""
        # Use mock data for demo
        centers = self._generate_mock_centers()
        
        # Filter by radius
        filtered_centers = []
        for center in centers:
            lat_diff = center.latitude - latitude
            lon_diff = center.longitude - longitude
            distance = np.sqrt((lat_diff * 111)**2 + (lon_diff * 111 * np.cos(np.radians(latitude)))**2)
            
            center.distance_km = round(distance, 1)
            if distance <= radius_km:
                filtered_centers.append(center)
        
        # Sort by distance
        filtered_centers.sort(key=lambda x: x.distance_km)
        
        return filtered_centers
    
    def get_materials_accepted(self, center: RecyclingCenter) -> str:
        """Format accepted materials as string"""
        return ", ".join(center.accepted_materials)

# ============================================================
# WASTE ANALYTICS ENGINE
# ============================================================

class WasteAnalytics:
    """
    Analyze waste patterns and generate insights
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.history = []
        self.scores = []
        
    def add_waste_item(self, item: WasteItem):
        """Add waste item to history"""
        self.history.append(item)
        
        # Calculate score for this item
        score = self._calculate_item_score(item)
        self.scores.append({
            'date': item.date,
            'score': score,
            'category': item.category,
            'weight': item.weight_kg
        })
    
    def _calculate_item_score(self, item: WasteItem) -> float:
        """Calculate environmental impact score for waste item"""
        # Base score: recyclable = good, non-recyclable = bad
        base_score = 50 if item.recyclable else 10
        
        # Adjust for weight
        weight_factor = max(1, item.weight_kg * 0.5)
        base_score -= (weight_factor - 1) * 2
        
        # Adjust for disposal method
        method_multipliers = {
            'recycle': 1.0,
            'compost': 0.9,
            'donate': 0.8,
            'ewaste': 0.6,
            'special_handling': 0.4,
            'unknown': 0.3
        }
        
        score = base_score * method_multipliers.get(item.disposal_method, 0.5)
        score = max(10, min(100, score))
        
        return round(score, 1)
    
    def get_reduction_tips(self) -> List[WasteReductionTip]:
        """Generate personalized waste reduction tips"""
        tips = [
            WasteReductionTip(
                title="Start Composting",
                description="Compost food waste to reduce landfill impact and create nutrient-rich soil",
                difficulty="Medium",
                potential_savings=0.5,
                category="organic",
                source="EPA Recommendation"
            ),
            WasteReductionTip(
                title="Switch to Reusable Products",
                description="Replace single-use items with reusable alternatives",
                difficulty="Easy",
                potential_savings=0.8,
                category="plastic",
                source="Zero Waste Initiative"
            ),
            WasteReductionTip(
                title="Proper Electronic Waste Disposal",
                description="Recycle electronics at certified e-waste facilities",
                difficulty="Medium",
                potential_savings=0.3,
                category="electronic",
                source="Environmental Protection Agency"
            ),
            WasteReductionTip(
                title="Buy in Bulk",
                description="Reduce packaging waste by buying in bulk",
                difficulty="Easy",
                potential_savings=0.4,
                category="paper",
                source="Green Living Guide"
            ),
            WasteReductionTip(
                title="Donate Usable Items",
                description="Donate gently used items instead of throwing them away",
                difficulty="Easy",
                potential_savings=0.2,
                category="textile",
                source="Local Charities"
            )
        ]
        
        # Filter tips based on user's waste patterns
        categories_found = set(item.category for item in self.history[-30:])
        relevant_tips = [tip for tip in tips if tip.category in categories_found or tip.category == "general"]
        
        # If no matching categories, return all tips
        if not relevant_tips:
            relevant_tips = tips
        
        return relevant_tips
    
    def get_total_co2_impact(self) -> float:
        """Calculate total CO2 impact from all waste"""
        return sum(item.co2_impact for item in self.history)
    
    def get_waste_by_category(self) -> Dict:
        """Get waste distribution by category"""
        distribution = defaultdict(float)
        for item in self.history:
            distribution[item.category] += item.weight_kg
        return dict(distribution)
    
    def get_waste_timeline(self) -> pd.DataFrame:
        """Get timeline data for visualization"""
        if not self.history:
            return pd.DataFrame()
        
        data = []
        for item in self.history:
            data.append({
                'date': item.date,
                'category': item.category,
                'weight': item.weight_kg,
                'recyclable': item.recyclable,
                'co2_impact': item.co2_impact
            })
        
        return pd.DataFrame(data)

# ============================================================
# WASTE MANAGEMENT UI
# ============================================================

class WasteManagementUI:
    """
    Main UI for waste management module
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.classifier = WasteClassifier()
        self.locator = RecyclingLocator()
        self.analytics = WasteAnalytics(user_id)
        self._initialize_session_state()
        
    def _initialize_session_state(self):
        """Initialize session state variables"""
        if 'waste_items' not in st.session_state:
            st.session_state.waste_items = []
        if 'captured_image' not in st.session_state:
            st.session_state.captured_image = None
        if 'classification_result' not in st.session_state:
            st.session_state.classification_result = None
        if 'waste_analytics' not in st.session_state:
            st.session_state.waste_analytics = {
                'total_items': 0,
                'total_weight': 0,
                'total_co2': 0,
                'recycling_rate': 0
            }
    
    def render(self):
        """Render the complete waste management interface"""
        st.markdown("""
        <style>
        .waste-header {
            background: linear-gradient(135deg, #1a2e1a, #0f172a);
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 20px;
            border: 1px solid rgba(74, 222, 128, 0.3);
        }
        .waste-header h2 {
            color: #4ade80;
            margin: 0;
        }
        .waste-header p {
            color: #94a3b8;
            margin: 5px 0 0 0;
        }
        .category-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin: 2px 4px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown("""
        <div class="waste-header">
            <h2>♻️ Waste Management & Recycling</h2>
            <p>AI-powered waste classification and recycling guidance</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📸 Classify Waste",
            "📊 Analytics",
            "📍 Recycling Centers",
            "💡 Reduction Tips"
        ])
        
        with tab1:
            self._render_classifier()
        
        with tab2:
            self._render_analytics()
        
        with tab3:
            self._render_centers()
        
        with tab4:
            self._render_tips()
    
    def _render_classifier(self):
        """Render waste classification interface"""
        st.subheader("📸 Identify Your Waste")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # Image capture
            st.markdown("### 📷 Capture Image")
            
            # File uploader
            uploaded_file = st.file_uploader(
                "Upload waste image",
                type=['jpg', 'jpeg', 'png'],
                help="Take a photo or upload an image of the waste item"
            )
            
            if uploaded_file is not None:
                # Display image
                image = Image.open(uploaded_file)
                st.image(image, caption="Uploaded Image", use_column_width=True)
                
                # Store for classification
                st.session_state.captured_image = image
                
                # Additional input
                st.markdown("### 📝 Additional Details")
                weight_est = st.number_input(
                    "Estimated Weight (kg)",
                    min_value=0.01,
                    value=0.1,
                    step=0.01,
                    help="If you know the approximate weight"
                )
                
                # Classify button
                if st.button("🔍 Classify Waste", use_container_width=True):
                    with st.spinner("Analyzing with AI..."):
                        # Convert image for classification
                        image_array = np.array(image)
                        result = self.classifier.classify_item(image_array)
                        
                        # Estimate weight if not provided
                        if weight_est == 0.1:
                            weight_est = self.classifier.estimate_weight(
                                result['category'],
                                image_array
                            )
                        
                        # Store result
                        result['weight'] = weight_est
                        st.session_state.classification_result = result
                        
                        # Add to analytics
                        waste_item = WasteItem(
                            category=result['category'],
                            sub_category=result['sub_category'],
                            weight_kg=weight_est,
                            date=datetime.now(),
                            recyclable=result['recyclable'],
                            co2_impact=weight_est * result['co2_factor'],
                            disposal_method=result['disposal_method']
                        )
                        
                        self.analytics.add_waste_item(waste_item)
                        st.session_state.waste_items.append(waste_item)
                        
                        st.success("✅ Classification complete!")
                        st.rerun()
        
        with col2:
            # Display results
            if st.session_state.classification_result:
                st.markdown("### 🎯 Classification Result")
                result = st.session_state.classification_result
                
                # Category with icon
                category_icons = {
                    'plastic': '🥤',
                    'glass': '🍾',
                    'paper': '📄',
                    'metal': '🥫',
                    'organic': '🍎',
                    'electronic': '💻',
                    'textile': '👕',
                    'hazardous': '☣️'
                }
                
                icon = category_icons.get(result['category'], '♻️')
                
                # Display main result
                st.markdown(f"""
                <div style="background: #0f172a; padding: 20px; border-radius: 10px; border: 1px solid #4ade80;">
                    <h3 style="color: #4ade80; margin: 0;">
                        {icon} {result['category'].upper()}
                    </h3>
                    <p style="color: #94a3b8; margin: 5px 0;">
                        Sub-category: <strong>{result['sub_category']}</strong>
                    </p>
                    <p style="color: #94a3b8; margin: 5px 0;">
                        Confidence: <strong>{result['confidence']*100:.1f}%</strong>
                    </p>
                    <p style="color: #94a3b8; margin: 5px 0;">
                        Weight Estimate: <strong>{result['weight']:.2f} kg</strong>
                    </p>
                    <p style="color: {'#4ade80' if result['recyclable'] else '#ef4444'}; margin: 5px 0;">
                        {'♻️ Recyclable' if result['recyclable'] else '❌ Not Recyclable'}
                    </p>
                    <p style="color: #94a3b8; margin: 5px 0;">
                        Recommended: <strong>{result['disposal_method'].upper()}</strong>
                    </p>
                    <p style="color: #94a3b8; margin: 5px 0;">
                        CO2 Impact: <strong>{result['weight'] * result['co2_factor']:.2f} kg CO2e</strong>
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                # Alternative classifications
                if result.get('alternatives'):
                    st.markdown("### 🤔 Also Consider")
                    for alt in result['alternatives'][:2]:
                        st.info(f"{alt['category']} ({alt['confidence']*100:.1f}% confidence)")
                
                # Action buttons
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Correct", use_container_width=True):
                        st.success("Thanks for the feedback!")
                with col_btn2:
                    if st.button("❌ Incorrect", use_container_width=True):
                        st.info("Please try a different image or provide more details")
                
                # Add to history button
                if st.button("📝 Add to Waste Log", use_container_width=True):
                    # Already added via analytics
                    st.success("Added to your waste log!")
                    
                    # Update session stats
                    st.session_state.waste_analytics['total_items'] += 1
                    st.session_state.waste_analytics['total_weight'] += result['weight']
                    st.session_state.waste_analytics['total_co2'] += result['weight'] * result['co2_factor']
                    if result['recyclable']:
                        st.session_state.waste_analytics['recycling_rate'] = (
                            sum(1 for item in st.session_state.waste_items if item.recyclable) /
                            max(1, len(st.session_state.waste_items)) * 100
                        )
            
            else:
                st.info("👆 Upload an image to classify your waste")
    
    def _render_analytics(self):
        """Render waste analytics dashboard"""
        st.subheader("📊 Waste Analytics")
        
        # Overall stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Items Logged",
                st.session_state.waste_analytics['total_items']
            )
        with col2:
            st.metric(
                "Total Weight",
                f"{st.session_state.waste_analytics['total_weight']:.2f} kg"
            )
        with col3:
            st.metric(
                "CO2 Impact",
                f"{st.session_state.waste_analytics['total_co2']:.2f} kg"
            )
        with col4:
            st.metric(
                "Recycling Rate",
                f"{st.session_state.waste_analytics['recycling_rate']:.1f}%"
            )
        
        # Chart: Waste by category
        if st.session_state.waste_items:
            st.markdown("### 📊 Waste Distribution")
            
            # Prepare data
            distribution = defaultdict(float)
            for item in st.session_state.waste_items:
                distribution[item.category] += item.weight_kg
            
            df = pd.DataFrame([
                {'Category': k, 'Weight (kg)': v}
                for k, v in distribution.items()
            ])
            
            # Bar chart
            fig = px.bar(
                df,
                x='Category',
                y='Weight (kg)',
                color='Category',
                title='Waste Distribution by Category',
                color_discrete_sequence=px.colors.qualitative.G10
            )
            
            fig.update_layout(
                height=400,
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Timeline chart
            st.markdown("### 📈 Waste Timeline")
            
            df_timeline = self.analytics.get_waste_timeline()
            if not df_timeline.empty:
                # Group by date
                df_timeline['date'] = pd.to_datetime(df_timeline['date'])
                df_daily = df_timeline.groupby(df_timeline['date'].dt.date).agg({
                    'weight': 'sum',
                    'co2_impact': 'sum'
                }).reset_index()
                
                # Line chart
                fig2 = go.Figure()
                
                fig2.add_trace(go.Scatter(
                    x=df_daily['date'],
                    y=df_daily['weight'],
                    mode='lines+markers',
                    name='Weight (kg)',
                    line=dict(color='#4ade80', width=2),
                    marker=dict(size=8)
                ))
                
                fig2.add_trace(go.Scatter(
                    x=df_daily['date'],
                    y=df_daily['co2_impact'],
                    mode='lines+markers',
                    name='CO2 Impact (kg)',
                    line=dict(color='#fbbf24', width=2),
                    marker=dict(size=8)
                ))
                
                fig2.update_layout(
                    title='Waste Generated Over Time',
                    xaxis_title='Date',
                    yaxis_title='Weight / CO2 Impact',
                    height=350,
                    template='plotly_dark',
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig2, use_container_width=True)
            
            # Recent items
            st.markdown("### 📋 Recent Items")
            
            recent_items = st.session_state.waste_items[-5:][::-1]
            for item in recent_items:
                with st.expander(f"{item.date.strftime('%Y-%m-%d %H:%M')} - {item.category} ({item.weight_kg:.2f} kg)"):
                    st.write(f"**Sub-category:** {item.sub_category}")
                    st.write(f"**Recyclable:** {'Yes' if item.recyclable else 'No'}")
                    st.write(f"**CO2 Impact:** {item.co2_impact:.2f} kg CO2e")
                    st.write(f"**Disposal:** {item.disposal_method}")
        
        else:
            st.info("No waste items logged yet. Classify some waste to see analytics.")
    
    def _render_centers(self):
        """Render recycling center locator"""
        st.subheader("📍 Find Recycling Centers")
        
        # Location input
        col1, col2 = st.columns(2)
        
        with col1:
            address = st.text_input(
                "Enter your address or ZIP code",
                placeholder="123 Main St, City, State"
            )
        
        with col2:
            radius = st.slider(
                "Search radius (km)",
                min_value=1,
                max_value=20,
                value=5
            )
        
        if st.button("🔍 Find Centers", use_container_width=True):
            with st.spinner("Searching for recycling centers..."):
                # Simulate geocoding (always use NYC for demo)
                latitude = 40.7128
                longitude = -74.0060
                
                centers = self.locator.find_centers(latitude, longitude, radius)
                
                if centers:
                    st.success(f"Found {len(centers)} recycling centers within {radius}km")
                    
                    # Display centers
                    for center in centers:
                        with st.expander(f"♻️ {center.name} ({center.distance_km:.1f} km away)"):
                            st.write(f"**Address:** {center.address}")
                            st.write(f"**Phone:** {center.phone}")
                            st.write(f"**Hours:** {center.operating_hours}")
                            st.write(f"**Accepts:** {self.locator.get_materials_accepted(center)}")
                            
                            # Directions link
                            st.markdown(
                                f"[Get Directions](https://www.google.com/maps/search/?api=1&query={center.latitude},{center.longitude})",
                                unsafe_allow_html=True
                            )
                else:
                    st.warning("No recycling centers found within the specified radius")
    
    def _render_tips(self):
        """Render waste reduction tips"""
        st.subheader("💡 Waste Reduction Tips")
        
        # Get personalized tips
        tips = self.analytics.get_reduction_tips()
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            category_filter = st.selectbox(
                "Filter by category",
                ["All"] + list(set(tip.category for tip in tips))
            )
        with col2:
            difficulty_filter = st.selectbox(
                "Filter by difficulty",
                ["All", "Easy", "Medium", "Hard"]
            )
        
        # Filter tips
        filtered_tips = tips
        if category_filter != "All":
            filtered_tips = [tip for tip in filtered_tips if tip.category == category_filter]
        if difficulty_filter != "All":
            filtered_tips = [tip for tip in filtered_tips if tip.difficulty == difficulty_filter]
        
        # Display tips
        for tip in filtered_tips:
            difficulty_color = {
                'Easy': '#4ade80',
                'Medium': '#fbbf24',
                'Hard': '#ef4444'
            }.get(tip.difficulty, '#94a3b8')
            
            st.markdown(f"""
            <div style="background: #0f172a; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid {difficulty_color};">
                <h4 style="color: #4ade80; margin: 0;">{tip.title}</h4>
                <p style="color: #94a3b8; margin: 5px 0;">{tip.description}</p>
                <div style="display: flex; gap: 20px; margin-top: 8px;">
                    <span style="color: #94a3b8;">Difficulty: <span style="color: {difficulty_color};">{tip.difficulty}</span></span>
                    <span style="color: #94a3b8;">Potential Savings: {tip.potential_savings:.1f} kg/day</span>
                    <span style="color: #94a3b8;">Source: {tip.source}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Show eco impact of following tips
        if filtered_tips:
            total_savings = sum(tip.potential_savings for tip in filtered_tips)
            st.info(f"🌱 Following these tips could reduce waste by {total_savings:.1f} kg/day!")
    
    def _get_category_color(self, category: str) -> str:
        """Get color for category badge"""
        colors = {
            'plastic': '#4ade80',
            'glass': '#60a5fa',
            'paper': '#fbbf24',
            'metal': '#f87171',
            'organic': '#34d399',
            'electronic': '#a78bfa',
            'textile': '#f472b6',
            'hazardous': '#ef4444'
        }
        return colors.get(category, '#94a3b8')

# ============================================================
# DATABASE INTEGRATION HELPERS
# ============================================================

def init_waste_db():
    """Initialize waste management database tables"""
    if 'waste_db' not in st.session_state:
        st.session_state.waste_db = {
            'items': [],
            'classifications': [],
            'centers': [],
            'user_preferences': {}
        }

def get_waste_summary(user_id: int) -> Dict:
    """Get waste summary for user"""
    return {
        'total_items': len(st.session_state.get('waste_items', [])),
        'total_weight': sum(item.weight_kg for item in st.session_state.get('waste_items', [])),
        'recyclable_count': sum(1 for item in st.session_state.get('waste_items', []) if item.recyclable),
        'co2_saved': sum(item.co2_impact for item in st.session_state.get('waste_items', []))
    }

# ============================================================
# MAIN RENDER FUNCTION
# ============================================================

def render_waste_hub():
    """Main entry point for waste management module"""
    user_id = st.session_state.get('user_id', 1)
    
    # Initialize
    init_waste_db()
    
    # Render UI
    ui = WasteManagementUI(user_id)
    ui.render()

# ============================================================
# STANDALONE TESTING
# ============================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Waste Management", layout="wide")
    render_waste_hub()