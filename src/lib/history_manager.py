"""
Assessment History Manager
Handles pagination, filtering, and sorting of assessment history.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class HistoryFilter:
    """Filters for assessment history."""
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    min_eco_score: Optional[int] = None
    max_eco_score: Optional[int] = None
    transport_modes: List[str] = field(default_factory=list)
    diet_types: List[str] = field(default_factory=list)
    min_footprint: Optional[float] = None
    max_footprint: Optional[float] = None
    search_text: str = ""


@dataclass
class HistoryPagination:
    """Pagination settings for assessment history."""
    page: int = 1
    page_size: int = 10
    total_items: int = 0
    total_pages: int = 0
    
    def update(self, total_items: int) -> None:
        self.total_items = total_items
        self.total_pages = (total_items + self.page_size - 1) // self.page_size
        if self.page > self.total_pages:
            self.page = max(1, self.total_pages)


class HistoryManager:
    """
    Manages assessment history with pagination and filtering.
    """
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.filter = HistoryFilter()
        self.pagination = HistoryPagination(page_size=10)
        self._all_assessments: List[Dict[str, Any]] = []
        self._filtered_assessments: List[Dict[str, Any]] = []
    
    def load_assessments(self) -> None:
        """Load assessments from src.core.database."""
        from src.core.database import get_assessments
        
        raw_data = get_assessments(self.user_id)
        
        self._all_assessments = []
        for row in raw_data:
            if len(row) >= 10:
                assessment = {
                    "id": row[0],
                    "date": row[1],
                    "created_at": row[2],
                    "transport": row[3],
                    "distance": row[4],
                    "electricity": row[5],
                    "diet": row[6],
                    "flights": row[7],
                    "footprint": row[8],
                    "eco_score": row[9],
                }
                self._all_assessments.append(assessment)
        
        self._filter_assessments()
    
    def _filter_assessments(self) -> None:
        """Apply filters to assessments."""
        filtered = self._all_assessments.copy()
        
        # Date range filter
        if self.filter.date_from:
            try:
                date_from = datetime.strptime(self.filter.date_from, "%Y-%m-%d")
                filtered = [a for a in filtered if datetime.strptime(a["date"], "%Y-%m-%d") >= date_from]
            except:
                pass
        
        if self.filter.date_to:
            try:
                date_to = datetime.strptime(self.filter.date_to, "%Y-%m-%d")
                filtered = [a for a in filtered if datetime.strptime(a["date"], "%Y-%m-%d") <= date_to]
            except:
                pass
        
        # Eco score filter
        if self.filter.min_eco_score is not None:
            filtered = [a for a in filtered if a["eco_score"] >= self.filter.min_eco_score]
        if self.filter.max_eco_score is not None:
            filtered = [a for a in filtered if a["eco_score"] <= self.filter.max_eco_score]
        
        # Transport modes filter
        if self.filter.transport_modes:
            filtered = [a for a in filtered if a["transport"] in self.filter.transport_modes]
        
        # Diet types filter
        if self.filter.diet_types:
            filtered = [a for a in filtered if a["diet"] in self.filter.diet_types]
        
        # Footprint filter
        if self.filter.min_footprint is not None:
            filtered = [a for a in filtered if a["footprint"] >= self.filter.min_footprint]
        if self.filter.max_footprint is not None:
            filtered = [a for a in filtered if a["footprint"] <= self.filter.max_footprint]
        
        # Search text
        if self.filter.search_text:
            search_lower = self.filter.search_text.lower()
            filtered = [
                a for a in filtered
                if search_lower in str(a["date"]).lower()
                or search_lower in a["transport"].lower()
                or search_lower in a["diet"].lower()
                or search_lower in str(a["eco_score"])
                or search_lower in str(a["footprint"])
            ]
        
        self._filtered_assessments = filtered
        self.pagination.update(len(filtered))
    
    def get_current_page(self) -> List[Dict[str, Any]]:
        """Get current page of assessments."""
        start = (self.pagination.page - 1) * self.pagination.page_size
        end = start + self.pagination.page_size
        return self._filtered_assessments[start:end]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about assessments."""
        if not self._all_assessments:
            return {
                "total": 0,
                "avg_footprint": 0,
                "avg_eco_score": 0,
                "best_eco_score": 0,
                "worst_eco_score": 0,
                "total_footprint": 0,
            }
        
        footprints = [a["footprint"] for a in self._all_assessments]
        eco_scores = [a["eco_score"] for a in self._all_assessments]
        
        return {
            "total": len(self._all_assessments),
            "avg_footprint": sum(footprints) / len(footprints),
            "avg_eco_score": sum(eco_scores) / len(eco_scores),
            "best_eco_score": max(eco_scores) if eco_scores else 0,
            "worst_eco_score": min(eco_scores) if eco_scores else 0,
            "total_footprint": sum(footprints),
        }
    
    def get_unique_values(self) -> Dict[str, List[str]]:
        """Get unique values for filters."""
        transports = sorted(set(a["transport"] for a in self._all_assessments))
        diets = sorted(set(a["diet"] for a in self._all_assessments))
        return {
            "transports": transports,
            "diets": diets,
        }
    
    def set_filter(self, **kwargs) -> None:
        """Set filter values."""
        for key, value in kwargs.items():
            if hasattr(self.filter, key):
                setattr(self.filter, key, value)
        self._filter_assessments()
    
    def reset_filters(self) -> None:
        """Reset all filters."""
        self.filter = HistoryFilter()
        self.pagination.page = 1
        self._filter_assessments()
    
    def set_page(self, page: int) -> None:
        """Set current page."""
        self.pagination.page = max(1, min(page, self.pagination.total_pages))
    
    def next_page(self) -> None:
        """Go to next page."""
        if self.pagination.page < self.pagination.total_pages:
            self.pagination.page += 1
    
    def prev_page(self) -> None:
        """Go to previous page."""
        if self.pagination.page > 1:
            self.pagination.page -= 1
    
    def export_csv(self) -> str:
        """Export filtered data to CSV string."""
        if not self._filtered_assessments:
            return ""
        
        df = pd.DataFrame(self._filtered_assessments)
        return df.to_csv(index=False)


def render_history_filters(manager: HistoryManager) -> None:
    """
    Render filter UI for assessment history.
    """
    with st.expander("🔍 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range
            st.markdown("**📅 Date Range**")
            date_from = st.date_input(
                "From",
                value=None,
                key="history_date_from",
                help="Start date for filtering"
            )
            date_to = st.date_input(
                "To",
                value=None,
                key="history_date_to",
                help="End date for filtering"
            )
            
            if date_from:
                manager.filter.date_from = date_from.strftime("%Y-%m-%d")
            else:
                manager.filter.date_from = None
            
            if date_to:
                manager.filter.date_to = date_to.strftime("%Y-%m-%d")
            else:
                manager.filter.date_to = None
        
        with col2:
            # Eco score range
            st.markdown("**⭐ Eco Score Range**")
            min_score = st.slider(
                "Min Score",
                min_value=0,
                max_value=100,
                value=0,
                key="history_min_score",
                help="Minimum Eco Score"
            )
            max_score = st.slider(
                "Max Score",
                min_value=0,
                max_value=100,
                value=100,
                key="history_max_score",
                help="Maximum Eco Score"
            )
            manager.filter.min_eco_score = min_score if min_score > 0 else None
            manager.filter.max_eco_score = max_score if max_score < 100 else None
        
        with col3:
            # Transport and diet filters
            st.markdown("**🚗 Transport & Diet**")
            unique = manager.get_unique_values()
            
            transports = st.multiselect(
                "Transport Modes",
                options=unique["transports"],
                default=[],
                key="history_transports",
                help="Filter by transport mode"
            )
            manager.filter.transport_modes = transports
            
            diets = st.multiselect(
                "Diet Types",
                options=unique["diets"],
                default=[],
                key="history_diets",
                help="Filter by diet type"
            )
            manager.filter.diet_types = diets
        
        # Search and actions
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            search_text = st.text_input(
                "🔍 Search",
                placeholder="Search by date, transport, diet...",
                key="history_search",
                help="Search across all fields"
            )
            manager.filter.search_text = search_text
        
        with col2:
            if st.button("🔄 Apply Filters", key="history_apply_filters", use_container_width=True):
                manager._filter_assessments()
                st.rerun()
        
        with col3:
            if st.button("🗑️ Reset Filters", key="history_reset_filters", use_container_width=True):
                manager.reset_filters()
                st.rerun()


def render_history_pagination(manager: HistoryManager) -> None:
    """
    Render pagination controls for assessment history.
    """
    pagination = manager.pagination
    
    if pagination.total_pages <= 1:
        return
    
    col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
    
    with col1:
        if st.button("⬅️ Previous", key="history_prev", disabled=(pagination.page <= 1)):
            manager.prev_page()
            st.rerun()
    
    with col2:
        st.caption(f"Page {pagination.page} of {pagination.total_pages}")
    
    with col3:
        # Page selector
        page_options = list(range(1, pagination.total_pages + 1))
        selected_page = st.selectbox(
            "Go to page",
            options=page_options,
            index=pagination.page - 1,
            key="history_page_select",
            label_visibility="collapsed"
        )
        if selected_page != pagination.page:
            manager.set_page(selected_page)
            st.rerun()
    
    with col4:
        st.caption(f"Showing {min(pagination.page * pagination.page_size, pagination.total_items)} of {pagination.total_items}")
    
    with col5:
        if st.button("Next ➡️", key="history_next", disabled=(pagination.page >= pagination.total_pages)):
            manager.next_page()
            st.rerun()


def render_history_stats(manager: HistoryManager) -> None:
    """
    Render statistics for assessment history.
    """
    stats = manager.get_stats()
    
    if stats["total"] == 0:
        st.info("No assessments found. Complete your first assessment to start tracking!")
        return
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Total Assessments", stats["total"])
    
    with col2:
        st.metric("⭐ Avg Eco Score", f"{stats['avg_eco_score']:.0f}")
    
    with col3:
        st.metric("🌍 Avg Footprint", f"{stats['avg_footprint']:.0f} kg")
    
    with col4:
        st.metric("🏆 Best Score", stats["best_eco_score"])
    
    with col5:
        st.metric("📉 Worst Score", stats["worst_eco_score"])

_history_managers = {}

def get_history_manager(user_id: int) -> HistoryManager:
    if user_id not in _history_managers:
        _history_managers[user_id] = HistoryManager(user_id)
    return _history_managers[user_id]

def clear_history_manager(user_id: Optional[int] = None) -> None:
    if user_id is None:
        _history_managers.clear()
    else:
        _history_managers.pop(user_id, None)
