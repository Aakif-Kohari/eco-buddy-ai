"""
Eco-Tips caching module for offline and performance optimization.
"""

import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import streamlit as st


class EcoTipsCache:
    """
    Caches eco-tips and AI responses to reduce API calls.
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["value"]
            else:
                # Expired
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set cached value."""
        self._cache[key] = {
            "value": value,
            "timestamp": time.time()
        }
    
    def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "ttl_seconds": self.ttl,
            "keys": list(self._cache.keys())
        }


# Global cache instance
_eco_tips_cache = None


def get_eco_tips_cache() -> EcoTipsCache:
    """Get global eco-tips cache."""
    global _eco_tips_cache
    if _eco_tips_cache is None:
        _eco_tips_cache = EcoTipsCache()
    return _eco_tips_cache