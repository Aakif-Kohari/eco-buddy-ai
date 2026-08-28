"""
Advanced Caching Layer for Resource-Intensive Analytics
Purpose: Reduce computation time for dashboard analytics by caching frequent results.
"""

import time
from typing import Any, Callable, Dict


class TTLCache:
    """
    A simple Time-To-Live (TTL) cache implementation.
    """

    def __init__(self, ttl_seconds: int = 60):
        self.ttl_seconds = ttl_seconds
        self.cache_store: Dict[str, tuple] = {}

    def get(self, key: str) -> Any:
        """
        Retrieves a cached value if it exists and hasn't expired.
        """
        if key in self.cache_store:
            timestamp, value = self.cache_store[key]
            if time.time() - timestamp < self.ttl_seconds:
                return value
            else:
                # Expired
                del self.cache_store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """
        Stores a value in the cache with a timestamp.
        """
        self.cache_store[key] = (time.time(), value)


def cached(ttl_seconds: int = 60):
    """
    Decorator to cache function results.
    """
    cache = TTLCache(ttl_seconds=ttl_seconds)

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{args}:{kwargs}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result)
            return result
        return wrapper
    return decorator


# Global cache instance
analytics_cache = TTLCache(ttl_seconds=300)


def cache_analytics_data(key: str, data: Any) -> None:
    """
    Stores analytics data in the global cache.
    """
    analytics_cache.set(key, data)


def get_cached_analytics_data(key: str) -> Any:
    """
    Retrieves analytics data from the global cache.
    """
    return analytics_cache.get(key)