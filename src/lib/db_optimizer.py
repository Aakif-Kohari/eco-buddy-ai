"""
Database Query Optimizer for EcoBuddy AI
Provides query optimization, caching, and connection pooling for faster dashboard loading.
"""

import time
import logging
import functools
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from collections import OrderedDict
import sqlite3
import threading
import hashlib
import json

logger = logging.getLogger(__name__)


# ============================================================================
# QUERY CACHE
# ============================================================================

class QueryCache:
    """LRU cache for database query results."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0
        }
    
    def _get_cache_key(self, query: str, params: tuple = ()) -> str:
        """Generate cache key from query and parameters."""
        key_data = {"query": query, "params": params}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, query: str, params: tuple = ()) -> Optional[Any]:
        """Get cached query result."""
        key = self._get_cache_key(query, params)
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry["timestamp"] < self.ttl:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    self._stats["hits"] += 1
                    return entry["value"]
                else:
                    # Expired
                    del self._cache[key]
                    self._stats["evictions"] += 1
            
            self._stats["misses"] += 1
            return None
    
    def set(self, query: str, params: tuple, value: Any) -> None:
        """Cache query result."""
        key = self._get_cache_key(query, params)
        
        with self._lock:
            if len(self._cache) >= self.max_size:
                # Evict oldest
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
            
            self._cache[key] = {
                "value": value,
                "timestamp": time.time()
            }
            self._stats["size"] = len(self._cache)
    
    def invalidate(self, pattern: Optional[str] = None) -> None:
        """Invalidate cache entries."""
        with self._lock:
            if pattern is None:
                self._cache.clear()
                logger.info("Query cache cleared")
                return
            
            keys_to_remove = []
            for key in self._cache:
                if pattern in key:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._cache[key]
                self._stats["evictions"] += 1
            
            self._stats["size"] = len(self._cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
            
            return {
                **self._stats,
                "hit_rate": round(hit_rate, 2),
                "ttl_seconds": self.ttl,
                "max_size": self.max_size
            }


# ============================================================================
# CONNECTION POOL
# ============================================================================

class ConnectionPool:
    """Simple connection pool for SQLite."""
    
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._connections: List[sqlite3.Connection] = []
        self._lock = threading.RLock()
        self._stats = {
            "created": 0,
            "reused": 0,
            "closed": 0
        }
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a connection from the pool."""
        with self._lock:
            if self._connections:
                conn = self._connections.pop()
                self._stats["reused"] += 1
                return conn
            
            self._stats["created"] += 1
            return sqlite3.connect(self.db_path, timeout=10.0)
    
    def return_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        with self._lock:
            if len(self._connections) < self.max_connections:
                self._connections.append(conn)
            else:
                conn.close()
                self._stats["closed"] += 1
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
            self._stats["closed"] += len(self._connections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            return {
                **self._stats,
                "available": len(self._connections),
                "max_connections": self.max_connections
            }


# ============================================================================
# QUERY OPTIMIZER
# ============================================================================

class QueryOptimizer:
    """Main query optimizer with caching and connection pooling."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.cache = QueryCache()
        self.pool = ConnectionPool(db_path)
        self._lock = threading.RLock()
    
    def execute_query(
        self,
        query: str,
        params: tuple = (),
        use_cache: bool = True,
        ttl: int = 300
    ) -> List[tuple]:
        """
        Execute a query with caching and connection pooling.
        
        Args:
            query: SQL query string
            params: Query parameters
            use_cache: Whether to use cache
            ttl: Cache TTL in seconds
        
        Returns:
            List of query results
        """
        # Check cache
        if use_cache:
            cached = self.cache.get(query, params)
            if cached is not None:
                return cached
        
        # Execute query
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(query, params)
            results = cursor.fetchall()
            conn.commit()
            
            # Cache results
            if use_cache:
                self.cache.set(query, params, results)
            
            return results
        finally:
            self.pool.return_connection(conn)
    
    def execute_many(
        self,
        queries: List[tuple],
        use_cache: bool = True
    ) -> List[List[tuple]]:
        """
        Execute multiple queries in a single connection.
        
        Args:
            queries: List of (query, params) tuples
            use_cache: Whether to use cache
        
        Returns:
            List of query results
        """
        results = []
        
        # Check cache first
        if use_cache:
            cached_results = []
            all_cached = True
            for query, params in queries:
                cached = self.cache.get(query, params)
                if cached is not None:
                    cached_results.append(cached)
                else:
                    all_cached = False
                    break
            
            if all_cached and len(cached_results) == len(queries):
                return cached_results
        
        # Execute queries
        conn = self.pool.get_connection()
        try:
            for query, params in queries:
                cursor = conn.execute(query, params)
                result = cursor.fetchall()
                results.append(result)
                
                if use_cache:
                    self.cache.set(query, params, result)
            conn.commit()
            return results
        finally:
            self.pool.return_connection(conn)
    
    def execute_with_cursor(
        self,
        query: str,
        params: tuple = (),
        callback: Callable = None
    ) -> Any:
        """
        Execute a query with a callback for custom processing.
        
        Args:
            query: SQL query string
            params: Query parameters
            callback: Function to process cursor results
        
        Returns:
            Processed results
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.execute(query, params)
            if callback:
                return callback(cursor)
            return cursor.fetchall()
        finally:
            self.pool.return_connection(conn)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        return {
            "cache": self.cache.get_stats(),
            "pool": self.pool.get_stats()
        }
    
    def clear_cache(self, pattern: Optional[str] = None) -> None:
        """Clear query cache."""
        self.cache.invalidate(pattern)
    
    def close(self) -> None:
        """Close all connections."""
        self.pool.close_all()


# ============================================================================
# DECORATORS
# ============================================================================

def cached_query(ttl: int = 300):
    """
    Decorator to cache function results.
    
    Usage:
        @cached_query(ttl=600)
        def get_user_assessments(user_id):
            # Database query
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = {"func": func.__name__, "args": args, "kwargs": kwargs}
            key_str = json.dumps(key_data, sort_keys=True)
            cache_key = hashlib.md5(key_str.encode()).hexdigest()
            
            # Check cache
            cache = QueryCache()
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(cache_key, result)
            return result
        return wrapper
    return decorator


def batch_queries(max_batch_size: int = 10):
    """
    Decorator to batch multiple queries.
    
    Usage:
        @batch_queries(max_batch_size=20)
        def get_multiple_assessments(user_ids):
            # Query multiple users
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(items, *args, **kwargs):
            if len(items) <= max_batch_size:
                return func(items, *args, **kwargs)
            
            # Split into batches
            results = []
            for i in range(0, len(items), max_batch_size):
                batch = items[i:i + max_batch_size]
                batch_results = func(batch, *args, **kwargs)
                results.extend(batch_results)
            return results
        return wrapper
    return decorator


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_optimizer: Optional[QueryOptimizer] = None
_optimizer_lock = threading.Lock()


def get_query_optimizer() -> QueryOptimizer:
    """Get global query optimizer instance."""
    global _optimizer
    with _optimizer_lock:
        if _optimizer is None:
            from src.core.app_config import CORPUS_DB_PATH
            _optimizer = QueryOptimizer(str(CORPUS_DB_PATH))
        return _optimizer


def close_db_connections() -> None:
    """Close all database connections."""
    global _optimizer
    if _optimizer is not None:
        _optimizer.close()
        _optimizer = None