"""
Real-Time Carbon Footprint Tracker
Provides live updates as user modifies inputs
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
import streamlit as st

logger = logging.getLogger(__name__)


@dataclass
class CarbonFootprintData:
    """Real-time carbon footprint data structure."""
    transport_emission: float = 0.0
    electricity_emission: float = 0.0
    diet_emission: float = 0.0
    flight_emission: float = 0.0
    total_footprint: float = 0.0
    eco_score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    contributors: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": round(self.total_footprint, 2),
            "eco_score": round(self.eco_score, 1),
            "transport": round(self.transport_emission, 2),
            "electricity": round(self.electricity_emission, 2),
            "diet": round(self.diet_emission, 2),
            "flights": round(self.flight_emission, 2),
            "contributors": self.contributors,
            "timestamp": self.timestamp
        }


class CarbonTracker:
    """
    Real-time carbon footprint tracker with live updates.
    """
    
    def __init__(self):
        self._last_update = 0
        self._current_data: Optional[CarbonFootprintData] = None
        self._update_history: List[Dict[str, Any]] = []
        self._max_history = 50
        self._listeners: List[callable] = []
    
    def register_listener(self, callback: callable) -> None:
        """Register a callback for updates."""
        self._listeners.append(callback)
    
    def notify_listeners(self, data: CarbonFootprintData) -> None:
        """Notify all registered listeners of update."""
        for callback in self._listeners:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Listener callback failed: {e}")
    
    def update(self, data: Dict[str, Any]) -> CarbonFootprintData:
        """
        Update carbon footprint with new data.
        
        Args:
            data: Dictionary containing transport, electricity, diet, flights, region
        
        Returns:
            Updated CarbonFootprintData
        """
        from src.carbon.emissions import calculate_footprint, calculate_eco_score
        
        try:
            # Extract values
            transport = data.get("transport", "Car")
            distance = float(data.get("distance", 10.0))
            electricity = float(data.get("electricity", 200.0))
            diet = data.get("diet", "Vegetarian")
            flights = int(data.get("flights", 0))
            region = data.get("region", "Global")
            
            # Calculate footprint
            total, contributors = calculate_footprint(
                transport, distance, electricity, diet, flights, region
            )
            
            # Calculate eco score
            eco_score = calculate_eco_score(total)
            
            # Create data object
            footprint_data = CarbonFootprintData(
                transport_emission=contributors.get("Transport", 0),
                electricity_emission=contributors.get("Electricity", 0),
                diet_emission=contributors.get("Diet", 0),
                flight_emission=contributors.get("Flights", 0),
                total_footprint=total,
                eco_score=eco_score,
                contributors=contributors
            )
            
            # Store current data
            self._current_data = footprint_data
            self._last_update = time.time()
            
            # Add to history
            self._update_history.append(footprint_data.to_dict())
            if len(self._update_history) > self._max_history:
                self._update_history.pop(0)
            
            # Notify listeners
            self.notify_listeners(footprint_data)
            
            return footprint_data
            
        except Exception as e:
            logger.error(f"Carbon tracker update failed: {e}")
            raise
    
    def get_current_data(self) -> Optional[CarbonFootprintData]:
        """Get current carbon footprint data."""
        return self._current_data
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get update history."""
        return self._update_history[-limit:] if self._update_history else []
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current summary."""
        if not self._current_data:
            return {
                "has_data": False,
                "message": "No data yet. Start tracking your carbon footprint!"
            }
        
        data = self._current_data
        return {
            "has_data": True,
            "total_footprint": round(data.total_footprint, 2),
            "eco_score": round(data.eco_score, 1),
            "transport": round(data.transport_emission, 2),
            "electricity": round(data.electricity_emission, 2),
            "diet": round(data.diet_emission, 2),
            "flights": round(data.flight_emission, 2),
            "biggest_contributor": max(data.contributors, key=data.contributors.get),
            "last_updated": datetime.fromtimestamp(data.timestamp).strftime("%H:%M:%S")
        }
    
    def get_contributor_breakdown(self) -> Dict[str, float]:
        """Get contributor breakdown as percentages."""
        if not self._current_data:
            return {}
        
        total = self._current_data.total_footprint
        if total == 0:
            return {}
        
        contributors = self._current_data.contributors
        return {
            key: round((value / total) * 100, 1)
            for key, value in contributors.items()
        }


def get_carbon_tracker():
    """Get or create carbon tracker instance."""
    if "carbon_tracker" not in st.session_state:
        st.session_state.carbon_tracker = CarbonTracker()
    return st.session_state.carbon_tracker


def update_carbon_tracker(data: Dict[str, Any]) -> CarbonFootprintData:
    """Update carbon tracker with new data."""
    tracker = get_carbon_tracker()
    return tracker.update(data)


def get_carbon_tracker_data() -> Optional[CarbonFootprintData]:
    """Get current carbon tracker data."""
    tracker = get_carbon_tracker()
    return tracker.get_current_data()


def render_carbon_widget():
    """Render live carbon footprint widget."""
    tracker = get_carbon_tracker()
    current = tracker.get_current_data()
    
    if not current:
        st.info("🌱 Start tracking your carbon footprint to see live updates!")
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "🌍 Total Footprint",
            f"{current.total_footprint:.1f} kg CO₂",
            help="Annual carbon footprint"
        )
    
    with col2:
        st.metric(
            "🏆 Eco Score",
            f"{current.eco_score:.0f}/100",
            help="Sustainability score"
        )
    
    with col3:
        biggest = max(current.contributors, key=current.contributors.get)
        st.metric(
            "📈 Biggest Impact",
            biggest,
            help="Largest contributor to your footprint"
        )