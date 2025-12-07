"""Memory caching system for fast retrieval of STM/LTM entries."""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    LRU cache for memory retrieval results.
    
    Features:
    - Thread-safe caching
    - Time-based expiration (TTL)
    - Separate caches for STM and LTM
    - Cache invalidation on updates
    - Cache statistics
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum cache entries (default: 100)
            ttl_seconds: Time-to-live for cached entries (default: 300s / 5min)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        
        # Separate caches for different memory types
        self.stm_cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self.ltm_cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        self.context_cache: OrderedDict[str, Tuple[float, Any]] = OrderedDict()
        
        # Thread safety
        self.lock = Lock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        
        logger.info(f"✅ MemoryCache initialized (max_size={max_size}, ttl={ttl_seconds}s)")
    
    def _get_from_cache(self, cache: OrderedDict, key: str) -> Optional[Any]:
        """Get value from specific cache if exists and not expired."""
        if key in cache:
            timestamp, value = cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Move to end (LRU)
                cache.move_to_end(key)
                self.hits += 1
                return value
            else:
                # Expired
                del cache[key]
                logger.debug(f"🕐 Cache expired: {key[:50]}...")
        self.misses += 1
        return None
    
    def _set_in_cache(self, cache: OrderedDict, key: str, value: Any):
        """Set value in specific cache."""
        cache[key] = (time.time(), value)
        cache.move_to_end(key)
        
        # Evict oldest if over size
        if len(cache) > self.max_size:
            evicted_key, _ = cache.popitem(last=False)
            logger.debug(f"🗑️  Cache evicted (size limit): {evicted_key[:50]}...")
    
    def get_stm(self, query: str, intent: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached STM results.
        
        Args:
            query: User query
            intent: Optional intent classification
            
        Returns:
            Cached STM list or None if not cached
        """
        with self.lock:
            cache_key = f"stm:{query[:100]}:{intent}"
            result = self._get_from_cache(self.stm_cache, cache_key)
            if result:
                logger.debug(f"🚀 STM cache hit: {query[:30]}...")
            return result
    
    def set_stm(self, query: str, intent: Optional[str], memories: List[Dict[str, Any]]):
        """
        Cache STM results.
        
        Args:
            query: User query
            intent: Optional intent classification
            memories: STM list to cache
        """
        with self.lock:
            cache_key = f"stm:{query[:100]}:{intent}"
            self._set_in_cache(self.stm_cache, cache_key, memories)
            logger.debug(f"💾 STM cached: {query[:30]}... ({len(memories)} entries)")
    
    def get_ltm(self, query: str, intent: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached LTM results.
        
        Args:
            query: User query
            intent: Optional intent classification
            
        Returns:
            Cached LTM list or None if not cached
        """
        with self.lock:
            cache_key = f"ltm:{query[:100]}:{intent}"
            result = self._get_from_cache(self.ltm_cache, cache_key)
            if result:
                logger.debug(f"🚀 LTM cache hit: {query[:30]}...")
            return result
    
    def set_ltm(self, query: str, intent: Optional[str], memories: List[Dict[str, Any]]):
        """
        Cache LTM results.
        
        Args:
            query: User query
            intent: Optional intent classification
            memories: LTM list to cache
        """
        with self.lock:
            cache_key = f"ltm:{query[:100]}:{intent}"
            self._set_in_cache(self.ltm_cache, cache_key, memories)
            logger.debug(f"💾 LTM cached: {query[:30]}... ({len(memories)} entries)")
    
    def get_context(self, query: str, intent: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached full context (STM + LTM).
        
        Args:
            query: User query
            intent: Optional intent classification
            
        Returns:
            Cached context dict or None if not cached
        """
        with self.lock:
            cache_key = f"ctx:{query[:100]}:{intent}"
            result = self._get_from_cache(self.context_cache, cache_key)
            if result:
                logger.debug(f"🚀 Context cache hit: {query[:30]}...")
            return result
    
    def set_context(self, query: str, intent: Optional[str], context: Dict[str, Any]):
        """
        Cache full context.
        
        Args:
            query: User query
            intent: Optional intent classification
            context: Context dict to cache
        """
        with self.lock:
            cache_key = f"ctx:{query[:100]}:{intent}"
            self._set_in_cache(self.context_cache, cache_key, context)
            logger.debug(f"💾 Context cached: {query[:30]}...")
    
    def invalidate_stm(self):
        """Invalidate all STM cache entries."""
        with self.lock:
            self.stm_cache.clear()
            logger.info("🗑️  STM cache invalidated")
    
    def invalidate_ltm(self):
        """Invalidate all LTM cache entries."""
        with self.lock:
            self.ltm_cache.clear()
            logger.info("🗑️  LTM cache invalidated")
    
    def invalidate_context(self):
        """Invalidate all context cache entries."""
        with self.lock:
            self.context_cache.clear()
            logger.info("🗑️  Context cache invalidated")
    
    def invalidate_all(self):
        """Clear all caches."""
        with self.lock:
            self.stm_cache.clear()
            self.ltm_cache.clear()
            self.context_cache.clear()
            logger.info("🗑️  All caches cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'stm_size': len(self.stm_cache),
                'ltm_size': len(self.ltm_cache),
                'context_size': len(self.context_cache),
                'total_size': len(self.stm_cache) + len(self.ltm_cache) + len(self.context_cache)
            }
    
    def __repr__(self) -> str:
        stats = self.get_stats()
        return (
            f"<MemoryCache hits={stats['hits']} misses={stats['misses']} "
            f"hit_rate={stats['hit_rate']:.1f}% size={stats['total_size']}>"
        )
