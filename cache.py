"""
Centralized caching utilities for EcoBuddy AI.

Provides a unified `cached()` decorator that wraps Streamlit's `st.cache_data`
with configurable TTL, automatic invalidation registration, and hit/miss tracking.

Usage:
    from cache import cached
    from cache_config import TTL_DB_READ, CACHE_CATEGORY_DB_READS

    @cached(category=CACHE_CATEGORY_DB_READS, ttl=TTL_DB_READ)
    def get_data(user_id):
        ...
"""

import functools
import time

from cache_config import CACHE_CATEGORIES, TTL_DB_READ, CACHE_CATEGORY_DB_READS
from cache_metrics import record_hit, record_miss, record_invalidation


def cached(
    ttl=None,
    category=None,
    max_entries=None,
    show_spinner=False,
    func_name=None,
):
    """
    Decorator that wraps st.cache_data with centralized configuration.

    Args:
        ttl: Time-to-live in seconds. If None, uses category default.
        category: Cache category string (from cache_config). Used for grouping
                  invalidation and applying default TTL.
        max_entries: Max cache entries. If None, uses category default.
        show_spinner: Whether to show Streamlit spinner during computation.
        func_name: Override function name for cache key (auto-detected if None).

    Returns:
        Decorated function with .clear() and .cache_info() methods.
    """
    def decorator(func):
        # Resolve TTL from category if not explicitly set
        if ttl is None and category and category in CACHE_CATEGORIES:
            resolved_ttl = CACHE_CATEGORIES[category]["ttl"]
        else:
            resolved_ttl = ttl

        # Resolve max_entries from category if not explicitly set
        if max_entries is None and category and category in CACHE_CATEGORIES:
            resolved_max = CACHE_CATEGORIES[category]["max_entries"]
        else:
            resolved_max = max_entries

        cache_name = func_name or func.__qualname__

        # Build st.cache_data kwargs
        cache_kwargs = {}
        if resolved_ttl is not None:
            cache_kwargs["ttl"] = resolved_ttl
        if resolved_max is not None:
            cache_kwargs["max_entries"] = resolved_max
        if show_spinner:
            cache_kwargs["show_spinner"] = show_spinner

        # Lazy initialization: defer st.cache_data application until the
        # decorated function is first called. This avoids importing streamlit
        # (and its heavy dependency chain) at module import time.
        _cached_wrapper = None

        @functools.wraps(func)
        def lazy_wrapper(*args, **kwargs):
            nonlocal _cached_wrapper
            if _cached_wrapper is None:
                import streamlit as st
                @st.cache_data(**cache_kwargs)
                @functools.wraps(func)
                def _inner(*a, **kw):
                    return func(*a, **kw)
                _cached_wrapper = _inner
            return _cached_wrapper(*args, **kwargs)

        # clear() delegates to the underlying st.cache_data wrapper once initialized
        def tracked_clear(*clear_args, **clear_kwargs):
            record_invalidation(cache_name)
            if _cached_wrapper is not None and hasattr(_cached_wrapper, "clear"):
                return _cached_wrapper.clear(*clear_args, **clear_kwargs)

        lazy_wrapper.clear = tracked_clear

        # Store metadata for introspection
        lazy_wrapper._cache_category = category
        lazy_wrapper._cache_ttl = resolved_ttl
        lazy_wrapper._cache_name = cache_name

        return lazy_wrapper

    return decorator


def invalidate_category(category):
    """
    Invalidate all cached functions registered under a given category.

    This inspects all registered Streamlit cache entries and clears those
    matching the specified category.

    Args:
        category: The cache category string to invalidate.
    """
    from invalidation import get_cached_functions_for_category

    functions = get_cached_functions_for_category(category)
    for func in functions:
        if hasattr(func, 'clear'):
            func.clear()


def bulk_invalidate(*categories):
    """
    Invalidate all cached functions across multiple categories.

    Args:
        *categories: Variable number of category strings.
    """
    for category in categories:
        invalidate_category(category)
