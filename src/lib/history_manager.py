"""
History Manager for EcoBuddy AI
Manages assessment history, filtering, and export operations.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HistoryFilter:
    """Filter configuration for assessment history."""
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_score: int = 0
    max_score: int = 100
    transport_modes: List[str] = field(default_factory=list)
    diet_types: List[str] = field(default_factory=list)
    search_text: str = ""
    limit: int = 100


class HistoryManager:
    """
    Manages assessment history with filtering, sorting, and export capabilities.
    """
    
    def __init__(self, user_id: int):
        """
        Initialize HistoryManager for a specific user.
        
        Args:
            user_id: User ID for the current session
        """
        self.user_id = user_id
        self._assessments: List[Dict[str, Any]] = []
        self._filtered_assessments: List[Dict[str, Any]] = []
        self._filters = HistoryFilter()
        self._sort_by = "date"
        self._sort_descending = True
        self._cache: Dict[str, Any] = {}
        self._last_refresh = None
        
        # Load initial data
        self.refresh_data()
        
        logger.info(f"HistoryManager initialized for user {user_id}")
    
    def refresh_data(self) -> None:
        """Refresh assessment data from database."""
        try:
            from database import get_assessments
            self._assessments = get_assessments(self.user_id)
            self._apply_filters()
            self._last_refresh = datetime.now()
            logger.debug(f"Refreshed {len(self._assessments)} assessments")
        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")
            self._assessments = []
            self._filtered_assessments = []
    
    def _apply_filters(self) -> None:
        """Apply current filters to assessments."""
        filtered = self._assessments.copy()
        
        # Date range filter
        if self._filters.date_from:
            filtered = [a for a in filtered if self._get_date(a) >= self._filters.date_from]
        if self._filters.date_to:
            filtered = [a for a in filtered if self._get_date(a) <= self._filters.date_to]
        
        # Score range filter
        if self._filters.min_score > 0 or self._filters.max_score < 100:
            filtered = [a for a in filtered if self._filters.min_score <= a.get('eco_score', 0) <= self._filters.max_score]
        
        # Transport mode filter
        if self._filters.transport_modes:
            filtered = [a for a in filtered if a.get('transport', '').lower() in [m.lower() for m in self._filters.transport_modes]]
        
        # Diet type filter
        if self._filters.diet_types:
            filtered = [a for a in filtered if a.get('diet', '').lower() in [d.lower() for d in self._filters.diet_types]]
        
        # Search text filter
        if self._filters.search_text:
            search = self._filters.search_text.lower()
            filtered = [
                a for a in filtered 
                if search in str(a.get('date', '')).lower() 
                or search in str(a.get('transport', '')).lower()
                or search in str(a.get('diet', '')).lower()
            ]
        
        # Apply sorting
        filtered.sort(
            key=lambda x: x.get(self._sort_by, 0),
            reverse=self._sort_descending
        )
        
        # Apply limit
        if self._filters.limit > 0:
            filtered = filtered[:self._filters.limit]
        
        self._filtered_assessments = filtered
        self._cache.clear()
    
    def _get_date(self, assessment: Dict[str, Any]) -> datetime:
        """Extract date from assessment dict."""
        date_val = assessment.get('date')
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            try:
                return datetime.fromisoformat(date_val)
            except:
                pass
        return datetime.now()
    
    def set_filters(self, **kwargs) -> None:
        """
        Set filters and refresh data.
        
        Args:
            date_from: Start date
            date_to: End date
            min_score: Minimum eco score
            max_score: Maximum eco score
            transport_modes: List of transport modes
            diet_types: List of diet types
            search_text: Search text
            limit: Max records to return
        """
        for key, value in kwargs.items():
            if hasattr(self._filters, key):
                setattr(self._filters, key, value)
        
        self._apply_filters()
    
    def set_sort(self, sort_by: str = "date", descending: bool = True) -> None:
        """Set sorting options."""
        self._sort_by = sort_by
        self._sort_descending = descending
        self._apply_filters()
    
    def get_assessments(self) -> List[Dict[str, Any]]:
        """Get filtered assessments."""
        return self._filtered_assessments.copy()
    
    def get_all_assessments(self) -> List[Dict[str, Any]]:
        """Get all assessments without filters."""
        return self._assessments.copy()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for filtered data."""
        data = self._filtered_assessments
        
        if not data:
            return {
                "total": 0,
                "avg_footprint": 0,
                "avg_score": 0,
                "min_score": 0,
                "max_score": 0,
                "total_footprint": 0,
                "date_range": {"from": None, "to": None},
                "transport_modes": {},
                "diet_types": {},
                "trend": "stable"
            }
        
        footprints = [a.get('footprint', 0) for a in data if a.get('footprint') is not None]
        scores = [a.get('eco_score', 0) for a in data if a.get('eco_score') is not None]
        dates = [self._get_date(a) for a in data]
        
        # Transport mode distribution
        transport_modes = {}
        for a in data:
            mode = a.get('transport', 'Unknown')
            transport_modes[mode] = transport_modes.get(mode, 0) + 1
        
        # Diet type distribution
        diet_types = {}
        for a in data:
            diet = a.get('diet', 'Unknown')
            diet_types[diet] = diet_types.get(diet, 0) + 1
        
        # Determine trend
        trend = "stable"
        if len(scores) >= 3:
            first_avg = sum(scores[:3]) / 3
            last_avg = sum(scores[-3:]) / 3
            if last_avg > first_avg * 1.05:
                trend = "improving"
            elif last_avg < first_avg * 0.95:
                trend = "declining"
        
        return {
            "total": len(data),
            "avg_footprint": round(sum(footprints) / len(footprints), 2) if footprints else 0,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "total_footprint": sum(footprints) if footprints else 0,
            "date_range": {
                "from": min(dates) if dates else None,
                "to": max(dates) if dates else None
            },
            "transport_modes": transport_modes,
            "diet_types": diet_types,
            "trend": trend
        }
    
    def export_data(self, format: str = "csv") -> Dict[str, Any]:
        """
        Export filtered data to specified format.
        
        Args:
            format: Export format ('csv', 'excel', 'json')
        
        Returns:
            ExportResult dictionary
        """
        from .export_manager import export_assessments
        return export_assessments(self._filtered_assessments, format)
    
    def get_export_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for export.
        
        Returns:
            Summary statistics dictionary
        """
        from .export_manager import get_export_manager
        manager = get_export_manager()
        return manager.export_summary(self._filtered_assessments)
    
    def get_export_options(self) -> Dict[str, Any]:
        """
        Get available export options.
        
        Returns:
            Dictionary of export options
        """
        return {
            "formats": ["csv", "excel", "json", "html", "markdown", "tsv", "multi"],
            "date_ranges": ["All", "Last 7 Days", "Last 30 Days", "Last 90 Days", "This Year"],
            "include_stats": True,
            "max_rows": 100000
        }
    
    def filter_by_date_range(self, date_range: str) -> List[Dict[str, Any]]:
        """
        Filter assessments by date range.
        
        Args:
            date_range: Date range string
        
        Returns:
            Filtered assessments list
        """
        if date_range == "All" or not self._filtered_assessments:
            return self._filtered_assessments
        
        now = datetime.now()
        if date_range == "Last 7 Days":
            cutoff = now - timedelta(days=7)
        elif date_range == "Last 30 Days":
            cutoff = now - timedelta(days=30)
        elif date_range == "Last 90 Days":
            cutoff = now - timedelta(days=90)
        elif date_range == "This Year":
            cutoff = datetime(now.year, 1, 1)
        else:
            return self._filtered_assessments
        
        filtered = []
        for assessment in self._filtered_assessments:
            date = assessment.get("date")
            if date:
                try:
                    if isinstance(date, str):
                        date = datetime.fromisoformat(date)
                    if date >= cutoff:
                        filtered.append(assessment)
                except:
                    pass
        
        return filtered
    
    def get_export_preview(self, limit: int = 10) -> pd.DataFrame:
        """
        Get a preview of data for export.
        
        Args:
            limit: Number of rows to preview
        
        Returns:
            DataFrame with preview data
        """
        if not self._filtered_assessments:
            return pd.DataFrame()
        
        preview_data = self._filtered_assessments[:limit]
        df = pd.DataFrame(preview_data)
        
        # Format for display
        display_columns = ['date', 'transport', 'distance', 'electricity', 'diet', 'flights', 'footprint', 'eco_score']
        existing_cols = [col for col in display_columns if col in df.columns]
        
        if existing_cols:
            df = df[existing_cols]
        
        return df
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "total_assessments": len(self._assessments),
            "filtered_assessments": len(self._filtered_assessments),
            "last_refresh": self._last_refresh,
            "filters": {
                "date_from": self._filters.date_from,
                "date_to": self._filters.date_to,
                "min_score": self._filters.min_score,
                "max_score": self._filters.max_score,
                "search_text": self._filters.search_text,
                "limit": self._filters.limit
            },
            "sort_by": self._sort_by,
            "sort_descending": self._sort_descending,
            "cache_size": len(self._cache)
        }


# Global HistoryManager instance cache
_history_managers: Dict[int, HistoryManager] = {}


def get_history_manager(user_id: int) -> HistoryManager:
    """
    Get or create HistoryManager for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        HistoryManager instance
    """
    if user_id not in _history_managers:
        _history_managers[user_id] = HistoryManager(user_id)
    return _history_managers[user_id]


def clear_history_manager(user_id: int) -> None:
    """
    Clear HistoryManager cache for a user.
    
    Args:
        user_id: User ID
    """
    if user_id in _history_managers:
        del _history_managers[user_id]