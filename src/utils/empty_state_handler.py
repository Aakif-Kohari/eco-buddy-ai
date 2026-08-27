"""
src.utils.empty_state_handler.py
====================================
Empty State Handler for Eco-Friendly Recommendations
Version: 1.0.0

This module provides comprehensive empty state handling for missing eco-friendly 
recommendations including:
- Graceful fallback UI states
- Helpful guidance messages
- Progressive loading states
- Error recovery suggestions
- Educational content for empty states

Author: Carbon Footprint Team
Date: 2026-08-27
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass, field
from enum import Enum
import math

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmptyStateType(Enum):
    """Enumeration of empty state types."""
    NO_RECOMMENDATIONS = "no_recommendations"
    NO_PRODUCTS = "no_products"
    NO_ALTERNATIVES = "no_alternatives"
    NO_DATA = "no_data"
    NO_CATEGORY = "no_category"
    NO_PREFERENCES = "no_preferences"
    NO_HISTORY = "no_history"
    NO_SAVED = "no_saved"
    LOADING = "loading"
    ERROR = "error"
    SEARCH_NO_RESULTS = "search_no_results"
    FILTER_NO_RESULTS = "filter_no_results"
    OUT_OF_STOCK = "out_of_stock"
    REGION_UNAVAILABLE = "region_unavailable"
    MAINTENANCE = "maintenance"


class EmptyStateSeverity(Enum):
    """Enumeration of empty state severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    SUCCESS = "success"


@dataclass
class EmptyStateConfig:
    """Data class for empty state configuration."""
    state_type: EmptyStateType
    title: str
    message: str
    severity: EmptyStateSeverity
    icon: str
    color: str
    suggestions: List[str] = field(default_factory=list)
    actions: List[Dict[str, str]] = field(default_factory=list)
    educational_content: Optional[Dict[str, str]] = None
    fallback_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    loading_timeout_seconds: int = 30
    retry_count: int = 3


@dataclass
class EmptyStateResponse:
    """Data class for empty state response."""
    state_type: EmptyStateType
    config: EmptyStateConfig
    timestamp: datetime
    user_context: Dict[str, Any]
    recovery_steps: List[str]
    alternative_actions: List[Dict[str, str]]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressiveState:
    """Data class for progressive loading state."""
    is_loading: bool
    progress_percentage: float
    current_step: str
    steps: List[str]
    estimated_time_seconds: int
    start_time: datetime
    last_update: datetime


class EmptyStateMessageGenerator:
    """
    Generates contextual empty state messages and content.
    """
    
    def __init__(self):
        self._message_templates = self._initialize_message_templates()
        self._suggestion_pools = self._initialize_suggestion_pools()
        self._educational_content = self._initialize_educational_content()
    
    def _initialize_message_templates(self) -> Dict[EmptyStateType, Dict[str, str]]:
        """
        Initializes message templates for each empty state type.
        
        Returns:
            Dictionary mapping state types to message templates
        """
        return {
            EmptyStateType.NO_RECOMMENDATIONS: {
                "title": "No Eco-Friendly Recommendations Found",
                "message": "We couldn't find any specific eco-friendly recommendations for your current selection. Try adjusting your preferences or explore our general sustainability tips.",
                "subtitle": "Don't worry! Here are some ways to get started with sustainable shopping."
            },
            EmptyStateType.NO_PRODUCTS: {
                "title": "No Products Available",
                "message": "There are currently no products matching your criteria in this category. We're constantly adding new sustainable products.",
                "subtitle": "Explore other categories or check back later for new arrivals."
            },
            EmptyStateType.NO_ALTERNATIVES: {
                "title": "No Sustainable Alternatives Found",
                "message": "We couldn't find any eco-friendly alternatives for this product. This might be a specialized item where sustainable options are limited.",
                "subtitle": "Consider these suggestions for making your choice more sustainable."
            },
            EmptyStateType.NO_DATA: {
                "title": "Insufficient Data",
                "message": "We don't have enough information to provide eco-friendly src.ai.recommendations. This could be because the product is new or from a less common category.",
                "subtitle": "Help us improve by providing feedback or checking our general sustainability guides."
            },
            EmptyStateType.NO_CATEGORY: {
                "title": "Category Not Found",
                "message": "The selected product category doesn't have eco-friendly recommendations yet. We're working on expanding our src.core.database.",
                "subtitle": "Browse other categories or discover general sustainable living tips."
            },
            EmptyStateType.NO_PREFERENCES: {
                "title": "Set Your Sustainability Preferences",
                "message": "You haven't set your sustainability preferences yet. Tell us what matters most to you - organic, local, fair trade, or low carbon footprint.",
                "subtitle": "Customize your preferences to get personalized src.ai.recommendations."
            },
            EmptyStateType.NO_HISTORY: {
                "title": "No Shopping History",
                "message": "We don't have any shopping history to analyze. Start by logging your purchases to get personalized eco-friendly src.ai.recommendations.",
                "subtitle": "Your journey to sustainable shopping starts here."
            },
            EmptyStateType.NO_SAVED: {
                "title": "No Saved Favorites",
                "message": "You haven't saved any eco-friendly products yet. Explore our recommendations and save items you're interested in.",
                "subtitle": "Start building your sustainable shopping list today."
            },
            EmptyStateType.LOADING: {
                "title": "Loading Recommendations",
                "message": "We're analyzing your preferences and finding the best eco-friendly recommendations for you.",
                "subtitle": "This may take a few moments. Thank you for your patience!"
            },
            EmptyStateType.ERROR: {
                "title": "Something Went Wrong",
                "message": "We encountered an error while fetching your eco-friendly src.ai.recommendations. Please try again later.",
                "subtitle": "Our team has been notified of this issue."
            },
            EmptyStateType.SEARCH_NO_RESULTS: {
                "title": "No Search Results",
                "message": "We couldn't find any eco-friendly products matching your search terms. Try using different keywords or browse our categories.",
                "subtitle": "Here are some popular sustainable products you might like."
            },
            EmptyStateType.FILTER_NO_RESULTS: {
                "title": "No Results with Current Filters",
                "message": "No eco-friendly products match your current filter selections. Try adjusting your filters to see more options.",
                "subtitle": "Consider removing some filters or broadening your search criteria."
            },
            EmptyStateType.OUT_OF_STOCK: {
                "title": "Out of Stock",
                "message": "The eco-friendly product you're looking for is currently out of stock. We're working to restock it soon.",
                "subtitle": "Here are some similar sustainable alternatives."
            },
            EmptyStateType.REGION_UNAVAILABLE: {
                "title": "Not Available in Your Region",
                "message": "These eco-friendly recommendations aren't available in your region yet. We're expanding our reach globally.",
                "subtitle": "Discover other sustainable options that are available to you."
            },
            EmptyStateType.MAINTENANCE: {
                "title": "Recommendations Temporarily Unavailable",
                "message": "Our eco-friendly recommendation engine is undergoing maintenance. We'll be back shortly with improved suggestions.",
                "subtitle": "Check back in a few minutes or explore our static sustainability guides."
            }
        }
    
    def _initialize_suggestion_pools(self) -> Dict[str, List[str]]:
        """
        Initializes suggestion pools for different contexts.
        
        Returns:
            Dictionary mapping context to suggestions
        """
        return {
            "general": [
                "Choose products with minimal packaging",
                "Opt for reusable alternatives when possible",
                "Look for products with recyclable materials",
                "Support local businesses to reduce transport emissions",
                "Choose organic and sustainably sourced products",
                "Reduce single-use plastic consumption",
                "Buy in bulk to reduce packaging waste",
                "Select energy-efficient products",
                "Choose products with longer lifespans",
                "Consider product lifecycle and end-of-life options"
            ],
            "food": [
                "Buy locally grown produce",
                "Choose seasonal fruits and vegetables",
                "Reduce food waste by planning meals",
                "Opt for organic and pesticide-free options",
                "Choose plant-based alternatives",
                "Support fair trade products",
                "Choose products with minimal packaging",
                "Buy from farmers markets",
                "Compost food scraps"
            ],
            "clothing": [
                "Choose organic cotton or sustainable materials",
                "Look for fair trade certification",
                "Buy second-hand or vintage clothing",
                "Choose quality over quantity",
                "Support sustainable fashion brands",
                "Repair and upcycle clothing",
                "Choose clothes with natural fibers",
                "Consider clothing rental services"
            ],
            "electronics": [
                "Choose energy-efficient devices",
                "Look for EPEAT certification",
                "Consider refurbished products",
                "Recycle old electronics properly",
                "Choose products with repairability in mind",
                "Consider cloud-based alternatives",
                "Choose products with less packaging"
            ],
            "cleaning": [
                "Choose biodegradable cleaning products",
                "Use natural cleaning alternatives",
                "Choose concentrated or refillable products",
                "Avoid toxic chemicals",
                "Look for eco-certifications",
                "Make DIY cleaning solutions",
                "Choose products with recyclable packaging"
            ],
            "personal_care": [
                "Choose products with natural ingredients",
                "Look for cruelty-free certification",
                "Choose products with minimal packaging",
                "Consider solid alternatives (shampoo bars, etc.)",
                "Choose biodegradable products",
                "Avoid microplastics",
                "Support sustainable beauty brands"
            ]
        }
    
    def _initialize_educational_content(self) -> Dict[str, Dict[str, str]]:
        """
        Initializes educational content for empty states.
        
        Returns:
            Dictionary mapping topics to educational content
        """
        return {
            "sustainability_basics": {
                "title": "Understanding Sustainable Shopping",
                "content": "Sustainable shopping involves considering the environmental, social, and economic impacts of your purchases. It's about making choices that minimize harm to the planet and support ethical practices.",
                "key_points": "1. Reduce: Buy less, choose quality\n2. Reuse: Opt for reusable items\n3. Recycle: Choose recyclable materials\n4. Rethink: Consider the full lifecycle"
            },
            "carbon_footprint": {
                "title": "What is Carbon Footprint?",
                "content": "Your carbon footprint is the total greenhouse gas emissions caused directly and indirectly by your actions. In shopping, this includes production, packaging, transport, and disposal of products.",
                "key_points": "1. Production: Raw materials and manufacturing\n2. Transport: Shipping and distribution\n3. Packaging: Materials and waste\n4. Disposal: Recycling and landfill"
            },
            "packaging_impact": {
                "title": "The Impact of Packaging",
                "content": "Packaging contributes significantly to environmental pollution and src.environment.waste. Choosing products with minimal or sustainable packaging can greatly reduce your environmental impact.",
                "key_points": "1. Plastic: Takes 500+ years to decompose\n2. Glass: 100% recyclable but energy-intensive\n3. Paper: Biodegradable but resource-intensive\n4. Compostable: Biodegradable under right conditions"
            },
            "local_shopping": {
                "title": "Benefits of Local Shopping",
                "content": "Buying local reduces transport emissions, supports local economy, and often means products are fresher and more seasonal. It's a simple way to reduce your carbon footprint.",
                "key_points": "1. Reduces transport emissions by up to 80%\n2. Supports local jobs and economy\n3. Products are often fresher\n4. Builds community connections"
            }
        }
    
    def generate_empty_state_config(self, state_type: EmptyStateType, 
                                   context: Dict[str, Any] = None) -> EmptyStateConfig:
        """
        Generates empty state configuration based on type and context.
        
        Args:
            state_type: Type of empty state
            context: Additional context for customization
            
        Returns:
            EmptyStateConfig object
        """
        template = self._message_templates.get(state_type, self._message_templates[EmptyStateType.NO_DATA])
        suggestions = self._get_contextual_suggestions(context)
        educational = self._get_educational_content(context)
        
        # Define icons and colors
        icon_map = {
            EmptyStateType.NO_RECOMMENDATIONS: "🌿",
            EmptyStateType.NO_PRODUCTS: "📦",
            EmptyStateType.NO_ALTERNATIVES: "🔄",
            EmptyStateType.NO_DATA: "📊",
            EmptyStateType.NO_CATEGORY: "📁",
            EmptyStateType.NO_PREFERENCES: "⚙️",
            EmptyStateType.NO_HISTORY: "📜",
            EmptyStateType.NO_SAVED: "⭐",
            EmptyStateType.LOADING: "⏳",
            EmptyStateType.ERROR: "⚠️",
            EmptyStateType.SEARCH_NO_RESULTS: "🔍",
            EmptyStateType.FILTER_NO_RESULTS: "🔎",
            EmptyStateType.OUT_OF_STOCK: "🚫",
            EmptyStateType.REGION_UNAVAILABLE: "🌍",
            EmptyStateType.MAINTENANCE: "🔧"
        }
        
        color_map = {
            EmptyStateType.NO_RECOMMENDATIONS: "#FFA500",
            EmptyStateType.NO_PRODUCTS: "#808080",
            EmptyStateType.NO_ALTERNATIVES: "#4CAF50",
            EmptyStateType.NO_DATA: "#2196F3",
            EmptyStateType.NO_CATEGORY: "#9E9E9E",
            EmptyStateType.NO_PREFERENCES: "#FF9800",
            EmptyStateType.NO_HISTORY: "#607D8B",
            EmptyStateType.NO_SAVED: "#FFD700",
            EmptyStateType.LOADING: "#42A5F5",
            EmptyStateType.ERROR: "#F44336",
            EmptyStateType.SEARCH_NO_RESULTS: "#78909C",
            EmptyStateType.FILTER_NO_RESULTS: "#78909C",
            EmptyStateType.OUT_OF_STOCK: "#FF5722",
            EmptyStateType.REGION_UNAVAILABLE: "#9C27B0",
            EmptyStateType.MAINTENANCE: "#FF6F00"
        }
        
        severity_map = {
            EmptyStateType.NO_RECOMMENDATIONS: EmptyStateSeverity.INFO,
            EmptyStateType.NO_PRODUCTS: EmptyStateSeverity.INFO,
            EmptyStateType.NO_ALTERNATIVES: EmptyStateSeverity.WARNING,
            EmptyStateType.NO_DATA: EmptyStateSeverity.WARNING,
            EmptyStateType.NO_CATEGORY: EmptyStateSeverity.INFO,
            EmptyStateType.NO_PREFERENCES: EmptyStateSeverity.WARNING,
            EmptyStateType.NO_HISTORY: EmptyStateSeverity.INFO,
            EmptyStateType.NO_SAVED: EmptyStateSeverity.INFO,
            EmptyStateType.LOADING: EmptyStateSeverity.INFO,
            EmptyStateType.ERROR: EmptyStateSeverity.ERROR,
            EmptyStateType.SEARCH_NO_RESULTS: EmptyStateSeverity.INFO,
            EmptyStateType.FILTER_NO_RESULTS: EmptyStateSeverity.INFO,
            EmptyStateType.OUT_OF_STOCK: EmptyStateSeverity.WARNING,
            EmptyStateType.REGION_UNAVAILABLE: EmptyStateSeverity.WARNING,
            EmptyStateType.MAINTENANCE: EmptyStateSeverity.ERROR
        }
        
        # Generate actions
        actions = self._generate_actions(state_type, context)
        
        return EmptyStateConfig(
            state_type=state_type,
            title=template.get("title", "No Recommendations Available"),
            message=template.get("message", "We couldn't find any src.ai.recommendations."),
            severity=severity_map.get(state_type, EmptyStateSeverity.INFO),
            icon=icon_map.get(state_type, "ℹ️"),
            color=color_map.get(state_type, "#808080"),
            suggestions=suggestions,
            actions=actions,
            educational_content=educational,
            fallback_recommendations=self._generate_fallback_recommendations(state_type, context),
            loading_timeout_seconds=30,
            retry_count=3
        )
    
    def _get_contextual_suggestions(self, context: Dict[str, Any] = None) -> List[str]:
        """
        Gets contextual suggestions based on the context.
        
        Args:
            context: Context dictionary
            
        Returns:
            List of suggestions
        """
        if not context:
            return self._suggestion_pools["general"][:5]
        
        category = context.get("category", "general")
        suggestions = self._suggestion_pools.get(category, self._suggestion_pools["general"])
        
        # Return 3-5 random suggestions
        num_suggestions = min(5, len(suggestions))
        return random.sample(suggestions, num_suggestions)
    
    def _get_educational_content(self, context: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Gets educational content based on context.
        
        Args:
            context: Context dictionary
            
        Returns:
            Educational content dictionary
        """
        if not context:
            return self._educational_content["sustainability_basics"]
        
        topic = context.get("education_topic", "sustainability_basics")
        return self._educational_content.get(topic, self._educational_content["sustainability_basics"])
    
    def _generate_actions(self, state_type: EmptyStateType, 
                         context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """
        Generates action buttons for the empty state.
        
        Args:
            state_type: Empty state type
            context: Context dictionary
            
        Returns:
            List of action dictionaries
        """
        actions = []
        
        if state_type == EmptyStateType.NO_RECOMMENDATIONS:
            actions.append({"label": "Explore Categories", "action": "browse_categories"})
            actions.append({"label": "Set Preferences", "action": "set_preferences"})
            actions.append({"label": "Learn More", "action": "learn_more"})
        
        elif state_type == EmptyStateType.NO_PREFERENCES:
            actions.append({"label": "Set Preferences", "action": "set_preferences"})
            actions.append({"label": "Explore Default", "action": "explore_default"})
        
        elif state_type == EmptyStateType.NO_HISTORY:
            actions.append({"label": "Start Logging", "action": "start_logging"})
            actions.append({"label": "Explore Products", "action": "explore_products"})
        
        elif state_type == EmptyStateType.ERROR:
            actions.append({"label": "Retry", "action": "retry"})
            actions.append({"label": "Contact Support", "action": "contact_support"})
        
        elif state_type == EmptyStateType.SEARCH_NO_RESULTS:
            actions.append({"label": "Clear Search", "action": "clear_search"})
            actions.append({"label": "Browse Categories", "action": "browse_categories"})
        
        elif state_type == EmptyStateType.FILTER_NO_RESULTS:
            actions.append({"label": "Clear Filters", "action": "clear_filters"})
            actions.append({"label": "Adjust Filters", "action": "adjust_filters"})
        
        elif state_type == EmptyStateType.OUT_OF_STOCK:
            actions.append({"label": "Notify Me", "action": "notify_me"})
            actions.append({"label": "View Alternatives", "action": "view_alternatives"})
        
        else:
            actions.append({"label": "Explore", "action": "explore"})
            actions.append({"label": "Learn More", "action": "learn_more"})
        
        return actions
    
    def _generate_fallback_recommendations(self, state_type: EmptyStateType, 
                                         context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generates fallback recommendations when no specific recommendations exist.
        
        Args:
            state_type: Empty state type
            context: Context dictionary
            
        Returns:
            List of fallback recommendations
        """
        fallbacks = []
        
        # Generic fallback recommendations
        generic_recommendations = [
            {
                "title": "Choose Reusable Products",
                "description": "Reduce waste by choosing reusable alternatives.",
                "impact": "High",
                "category": "general"
            },
            {
                "title": "Buy Local When Possible",
                "description": "Support local businesses and reduce transport src.carbon.emissions.",
                "impact": "Medium",
                "category": "general"
            },
            {
                "title": "Opt for Minimal Packaging",
                "description": "Choose products with less packaging or recyclable materials.",
                "impact": "High",
                "category": "general"
            },
            {
                "title": "Choose Organic Products",
                "description": "Support sustainable farming practices.",
                "impact": "Medium",
                "category": "general"
            },
            {
                "title": "Consider Product Lifespan",
                "description": "Choose durable products that last longer.",
                "impact": "High",
                "category": "general"
            }
        ]
        
        # Category-specific fallbacks
        if context and context.get("category"):
            category = context.get("category")
            if category == "food":
                fallbacks = [
                    {"title": "Seasonal Produce", "description": "Choose fruits and vegetables in season.", "impact": "High"},
                    {"title": "Plant-Based Options", "description": "Try plant-based alternatives to meat.", "impact": "High"},
                    {"title": "Bulk Buying", "description": "Buy in bulk to reduce packaging src.environment.waste.", "impact": "Medium"}
                ]
            elif category == "clothing":
                fallbacks = [
                    {"title": "Organic Cotton", "description": "Choose organic cotton over conventional.", "impact": "High"},
                    {"title": "Second-Hand", "description": "Consider thrift or vintage clothing.", "impact": "High"},
                    {"title": "Quality Over Quantity", "description": "Invest in durable, timeless pieces.", "impact": "Medium"}
                ]
            elif category == "electronics":
                fallbacks = [
                    {"title": "Energy Star", "description": "Look for Energy Star certified products.", "impact": "High"},
                    {"title": "Refurbished Options", "description": "Consider refurbished electronics.", "impact": "Medium"},
                    {"title": "Repairable Design", "description": "Choose products designed for repair.", "impact": "Medium"}
                ]
        
        if not fallbacks:
            fallbacks = generic_recommendations
        
        return fallbacks[:5]


class EmptyStateHandler:
    """
    Main handler for empty states.
    """
    
    def __init__(self):
        self._generator = EmptyStateMessageGenerator()
        self._progressive_states: Dict[str, ProgressiveState] = {}
        self._empty_state_history: List[EmptyStateResponse] = []
        self._max_history = 1000
    
    def handle_empty_state(self, state_type: EmptyStateType, 
                          user_id: Optional[str] = None,
                          context: Dict[str, Any] = None) -> EmptyStateResponse:
        """
        Handles an empty state and returns appropriate response.
        
        Args:
            state_type: Type of empty state
            user_id: Optional user identifier
            context: Additional context
            
        Returns:
            EmptyStateResponse object
        """
        config = self._generator.generate_empty_state_config(state_type, context)
        
        # Generate recovery steps
        recovery_steps = self._generate_recovery_steps(state_type, context)
        
        # Generate alternative actions
        alternative_actions = self._generate_alternative_actions(state_type, context)
        
        # Build metadata
        metadata = {
            "state_type": state_type.value,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "context": context or {},
            "has_fallback": bool(src.core.config.fallback_recommendations),
            "has_suggestions": bool(src.core.config.suggestions)
        }
        
        response = EmptyStateResponse(
            state_type=state_type,
            config=config,
            timestamp=datetime.now(),
            user_context=context or {},
            recovery_steps=recovery_steps,
            alternative_actions=alternative_actions,
            metadata=metadata
        )
        
        # Log history
        self._empty_state_history.append(response)
        if len(self._empty_state_history) > self._max_history:
            self._empty_state_history = self._empty_state_history[-self._max_history:]
        
        logger.info(f"Empty state handled: {state_type.value} for user {user_id}")
        
        return response
    
    def _generate_recovery_steps(self, state_type: EmptyStateType, 
                                context: Dict[str, Any] = None) -> List[str]:
        """
        Generates recovery steps for the empty state.
        
        Args:
            state_type: Empty state type
            context: Context dictionary
            
        Returns:
            List of recovery steps
        """
        recovery_steps = []
        
        if state_type == EmptyStateType.NO_RECOMMENDATIONS:
            recovery_steps = [
                "Try adjusting your search or filter criteria",
                "Explore products in different categories",
                "Check back later as new products are added",
                "Set your sustainability preferences for better recommendations"
            ]
        elif state_type == EmptyStateType.NO_PREFERENCES:
            recovery_steps = [
                "Go to settings to set your sustainability priorities",
                "Choose what matters most: organic, local, fair trade, or carbon footprint",
                "Save your preferences to get personalized recommendations"
            ]
        elif state_type == EmptyStateType.NO_ALTERNATIVES:
            recovery_steps = [
                "Consider making your current choice more sustainable",
                "Look for ways to reduce waste with your current product",
                "Suggest this product for alternative recommendations"
            ]
        elif state_type == EmptyStateType.ERROR:
            recovery_steps = [
                "Refresh the page and try again",
                "Check your internet connection",
                "Wait a few minutes and retry",
                "Contact support if the issue persists"
            ]
        elif state_type == EmptyStateType.SEARCH_NO_RESULTS:
            recovery_steps = [
                "Try using simpler or different keywords",
                "Browse categories instead of searching",
                "Check your spelling and try again"
            ]
        elif state_type == EmptyStateType.FILTER_NO_RESULTS:
            recovery_steps = [
                "Remove some filters to broaden results",
                "Try a different combination of filters",
                "Clear all filters and start over"
            ]
        elif state_type == EmptyStateType.OUT_OF_STOCK:
            recovery_steps = [
                "Set up a notification for when it's back in stock",
                "Browse similar sustainable alternatives",
                "Check other retailers for the same product"
            ]
        elif state_type == EmptyStateType.REGION_UNAVAILABLE:
            recovery_steps = [
                "Browse products available in your region",
                "Suggest products to be added in your area",
                "Check back as we expand our offerings"
            ]
        else:
            recovery_steps = [
                "Explore our general sustainability guides",
                "Browse products to get started",
                "Set up your preferences for better recommendations"
            ]
        
        return recovery_steps[:5]
    
    def _generate_alternative_actions(self, state_type: EmptyStateType, 
                                    context: Dict[str, Any] = None) -> List[Dict[str, str]]:
        """
        Generates alternative actions for the empty state.
        
        Args:
            state_type: Empty state type
            context: Context dictionary
            
        Returns:
            List of alternative actions
        """
        actions = []
        
        if state_type == EmptyStateType.NO_RECOMMENDATIONS:
            actions.append({"label": "View All Products", "action": "view_all_products", "icon": "📦"})
            actions.append({"label": "Sustainability Tips", "action": "sustainability_tips", "icon": "💡"})
            actions.append({"label": "Community Recommendations", "action": "community_recs", "icon": "👥"})
        
        elif state_type == EmptyStateType.NO_PREFERENCES:
            actions.append({"label": "Quick Start Guide", "action": "quick_start", "icon": "🚀"})
            actions.append({"label": "Default Preferences", "action": "default_prefs", "icon": "⚙️"})
        
        elif state_type == EmptyStateType.ERROR:
            actions.append({"label": "Report Issue", "action": "report_issue", "icon": "🐛"})
            actions.append({"label": "View Knowledge Base", "action": "knowledge_base", "icon": "📚"})
        
        elif state_type == EmptyStateType.SEARCH_NO_RESULTS:
            actions.append({"label": "Popular Searches", "action": "popular_searches", "icon": "🔥"})
            actions.append({"label": "Browse All", "action": "browse_all", "icon": "📋"})
        
        else:
            actions.append({"label": "Explore", "action": "explore", "icon": "🔍"})
            actions.append({"label": "Learn More", "action": "learn_more", "icon": "📖"})
            actions.append({"label": "Get Help", "action": "get_help", "icon": "❓"})
        
        return actions[:3]
    
    def start_progressive_loading(self, session_id: str, steps: List[str]) -> ProgressiveState:
        """
        Starts progressive loading state.
        
        Args:
            session_id: Unique session identifier
            steps: List of loading steps
            
        Returns:
            ProgressiveState object
        """
        state = ProgressiveState(
            is_loading=True,
            progress_percentage=0.0,
            current_step=steps[0] if steps else "Loading...",
            steps=steps,
            estimated_time_seconds=len(steps) * 5,
            start_time=datetime.now(),
            last_update=datetime.now()
        )
        
        self._progressive_states[session_id] = state
        return state
    
    def update_progressive_loading(self, session_id: str, step_index: int) -> ProgressiveState:
        """
        Updates progressive loading state.
        
        Args:
            session_id: Session identifier
            step_index: Current step index
            
        Returns:
            Updated ProgressiveState object
        """
        if session_id not in self._progressive_states:
            raise ValueError(f"Progressive state not found for session: {session_id}")
        
        state = self._progressive_states[session_id]
        
        if step_index < len(state.steps):
            state.current_step = state.steps[step_index]
            state.progress_percentage = ((step_index + 1) / len(state.steps)) * 100
            state.last_update = datetime.now()
            
            if step_index == len(state.steps) - 1:
                state.is_loading = False
        
        return state
    
    def get_progressive_state(self, session_id: str) -> Optional[ProgressiveState]:
        """
        Gets progressive loading state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ProgressiveState object or None
        """
        return self._progressive_states.get(session_id)
    
    def clear_progressive_state(self, session_id: str) -> None:
        """
        Clears progressive loading state.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self._progressive_states:
            del self._progressive_states[session_id]


class EmptyStateRenderer:
    """
    Renders empty state UI components.
    """
    
    def __init__(self):
        self._handler = EmptyStateHandler()
    
    def render_empty_state(self, state_type: EmptyStateType, 
                          user_id: Optional[str] = None,
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Renders empty state as a dictionary for UI consumption.
        
        Args:
            state_type: Empty state type
            user_id: Optional user identifier
            context: Additional context
            
        Returns:
            Dictionary with rendered empty state data
        """
        response = self._handler.handle_empty_state(state_type, user_id, context)
        config = response.config
        
        return {
            "type": state_type.value,
            "title": src.core.config.title,
            "message": src.core.config.message,
            "severity": src.core.config.severity.value,
            "icon": src.core.config.icon,
            "color": src.core.config.color,
            "suggestions": src.core.config.suggestions,
            "actions": src.core.config.actions,
            "recovery_steps": response.recovery_steps,
            "alternative_actions": response.alternative_actions,
            "educational_content": src.core.config.educational_content,
            "fallback_recommendations": src.core.config.fallback_recommendations,
            "timestamp": response.timestamp.isoformat(),
            "metadata": response.metadata
        }
    
    def render_progressive_state(self, session_id: str) -> Dict[str, Any]:
        """
        Renders progressive loading state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with rendered progressive state
        """
        state = self._handler.get_progressive_state(session_id)
        
        if not state:
            return {
                "is_loading": False,
                "progress_percentage": 100,
                "current_step": "Complete",
                "message": "Loading complete"
            }
        
        return {
            "is_loading": state.is_loading,
            "progress_percentage": state.progress_percentage,
            "current_step": state.current_step,
            "steps": state.steps,
            "estimated_time_seconds": state.estimated_time_seconds,
            "elapsed_seconds": (datetime.now() - state.start_time).seconds,
            "message": f"Loading: {state.current_step} ({int(state.progress_percentage)}%)"
        }


class EnhancedEmptyStateHandler:
    """
    Enhanced handler with intelligent recovery and fallback strategies.
    """
    
    def __init__(self):
        self.base_handler = EmptyStateHandler()
        self.renderer = EmptyStateRenderer()
        self._fallback_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._recovery_attempts: Dict[str, int] = {}
    
    def handle_with_intelligence(self, state_type: EmptyStateType,
                                user_id: Optional[str] = None,
                                context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handles empty state with intelligent recovery strategies.
        
        Args:
            state_type: Empty state type
            user_id: Optional user identifier
            context: Additional context
            
        Returns:
            Dictionary with enhanced empty state data
        """
        # Check if we have cached fallbacks
        cache_key = f"{user_id}_{state_type.value}" if user_id else state_type.value
        
        if cache_key in self._fallback_cache:
            context = context or {}
            context['fallbacks'] = self._fallback_cache[cache_key]
        
        # Generate response
        rendered = self.renderer.render_empty_state(state_type, user_id, context)
        
        # Apply intelligence
        if state_type == EmptyStateType.NO_RECOMMENDATIONS:
            rendered = self._enrich_no_recommendations(rendered, user_id)
        elif state_type == EmptyStateType.NO_ALTERNATIVES:
            rendered = self._enrich_no_alternatives(rendered, user_id)
        elif state_type == EmptyStateType.ERROR:
            rendered = self._enrich_error_state(rendered, user_id)
        
        # Cache fallbacks for future use
        if rendered.get('fallback_recommendations'):
            self._fallback_cache[cache_key] = rendered['fallback_recommendations']
        
        return rendered
    
    def _enrich_no_recommendations(self, rendered: Dict[str, Any], 
                                  user_id: Optional[str]) -> Dict[str, Any]:
        return rendered
    
    def _enrich_no_alternatives(self, rendered: Dict[str, Any], 
                               user_id: Optional[str]) -> Dict[str, Any]:
        return rendered
        
    def _enrich_error_state(self, rendered: Dict[str, Any], 
                           user_id: Optional[str]) -> Dict[str, Any]:
        return rendered
