# coach/resource_pool.py
"""Resource pooling utilities for multi-tenant vector stores."""

import logging
import time
from typing import Dict, Optional, Any, Tuple
from collections import OrderedDict
from threading import Lock
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entry in the resource cache."""
    resource: Any
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    
    def touch(self):
        """Update last accessed time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class LRUResourcePool:
    """
    Thread-safe LRU cache for managing shared resources across tenants.
    
    Features:
    - Least Recently Used (LRU) eviction policy
    - Configurable maximum size and TTL
    - Thread-safe operations
    - Access statistics tracking
    """
    
    def __init__(
        self,
        max_size: int = 10,
        ttl_seconds: Optional[int] = 3600,  # 1 hour default TTL
        eviction_callback: Optional[callable] = None
    ):
        """
        Initialize the resource pool.
        
        Args:
            max_size: Maximum number of resources to keep in pool
            ttl_seconds: Time-to-live for cached resources (None for no expiry)
            eviction_callback: Optional callback when resource is evicted
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.eviction_callback = eviction_callback
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0
        }
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a resource from the pool.
        
        Args:
            key: Resource key
            
        Returns:
            The resource if found and valid, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if self._is_expired(entry):
                self._evict(key, reason="expired")
                self._stats["expirations"] += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.touch()
            
            self._stats["hits"] += 1
            return entry.resource
    
    def put(self, key: str, resource: Any) -> None:
        """
        Put a resource in the pool.
        
        Args:
            key: Resource key
            resource: The resource to cache
        """
        with self._lock:
            # If key exists, update and move to end
            if key in self._cache:
                self._cache[key] = CacheEntry(resource)
                self._cache.move_to_end(key)
                return
            
            # If at capacity, evict least recently used
            if len(self._cache) >= self.max_size:
                self._evict_lru()
            
            # Add new entry
            self._cache[key] = CacheEntry(resource)
    
    def remove(self, key: str) -> Optional[Any]:
        """
        Remove a resource from the pool.
        
        Args:
            key: Resource key
            
        Returns:
            The removed resource if found, None otherwise
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache.pop(key)
                return entry.resource
            return None
    
    def clear(self) -> None:
        """Clear all resources from the pool."""
        with self._lock:
            if self.eviction_callback:
                for key, entry in self._cache.items():
                    self.eviction_callback(key, entry.resource, "clear")
            
            self._cache.clear()
            logger.info("Cleared resource pool")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (
                self._stats["hits"] / total_requests if total_requests > 0 else 0
            )
            
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": hit_rate,
                "keys": list(self._cache.keys()),
                "ttl_seconds": self.ttl_seconds
            }
    
    def get_resource_info(self, key: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific cached resource."""
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            age_seconds = (datetime.now() - entry.last_accessed).total_seconds()
            
            return {
                "last_accessed": entry.last_accessed.isoformat(),
                "access_count": entry.access_count,
                "age_seconds": age_seconds,
                "expired": self._is_expired(entry)
            }
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if a cache entry has expired."""
        if self.ttl_seconds is None:
            return False
        
        age = datetime.now() - entry.last_accessed
        return age.total_seconds() > self.ttl_seconds
    
    def _evict(self, key: str, reason: str = "evicted") -> None:
        """Evict a resource from the cache."""
        if key in self._cache:
            entry = self._cache.pop(key)
            
            if self.eviction_callback:
                self.eviction_callback(key, entry.resource, reason)
            
            logger.debug(f"Evicted resource {key}: {reason}")
    
    def _evict_lru(self) -> None:
        """Evict the least recently used resource."""
        if self._cache:
            # Get the first key (least recently used)
            lru_key = next(iter(self._cache))
            self._evict(lru_key, reason="lru")
            self._stats["evictions"] += 1
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.
        
        Returns:
            Number of expired entries removed
        """
        if self.ttl_seconds is None:
            return 0
        
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]
            
            for key in expired_keys:
                self._evict(key, reason="expired")
                self._stats["expirations"] += 1
            
            return len(expired_keys)


# Global resource pools for different resource types
_vector_store_pool: Optional[LRUResourcePool] = None
_pool_lock = Lock()


def get_vector_store_pool(
    max_size: int = 10,
    ttl_seconds: int = 3600
) -> LRUResourcePool:
    """
    Get or create the global vector store resource pool.
    
    Args:
        max_size: Maximum number of vector stores to cache
        ttl_seconds: Time-to-live for cached vector stores
        
    Returns:
        The global vector store resource pool
    """
    global _vector_store_pool
    
    with _pool_lock:
        if _vector_store_pool is None:
            
            def eviction_callback(key: str, resource: Any, reason: str):
                """Log when vector stores are evicted."""
                logger.info(
                    f"Vector store for tenant {key} evicted: {reason}"
                )
            
            _vector_store_pool = LRUResourcePool(
                max_size=max_size,
                ttl_seconds=ttl_seconds,
                eviction_callback=eviction_callback
            )
            
            logger.info(
                f"Created vector store pool (max_size={max_size}, "
                f"ttl_seconds={ttl_seconds})"
            )
        
        return _vector_store_pool


def reset_pools():
    """Reset all resource pools (mainly for testing)."""
    global _vector_store_pool
    
    with _pool_lock:
        if _vector_store_pool:
            _vector_store_pool.clear()
            _vector_store_pool = None
        
        logger.info("Reset all resource pools")