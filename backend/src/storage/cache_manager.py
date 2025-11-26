"""
Cache Manager - In-memory caching with Redis fallback
"""
import asyncio
from typing import Optional, Any, Callable
from datetime import datetime, timedelta
import functools
import hashlib
import json

from src.storage.redis_manager import RedisManager
import logging


logger = logging.getLogger(__name__)


class CacheManager:
    """
    Two-tier caching system: Memory (fast) + Redis (persistent)
    """
    
    def __init__(self, redis_manager: RedisManager):
        self.redis_manager = redis_manager
        self._memory_cache: dict = {}
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'memory_hits': 0,
            'redis_hits': 0
        }
    
    def cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from cache (memory first, then Redis)"""
        # Try memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if entry['expires_at'] > datetime.utcnow():
                self._cache_stats['hits'] += 1
                self._cache_stats['memory_hits'] += 1
                return entry['value']
            else:
                # Expired
                del self._memory_cache[key]
        
        # Try Redis
        value = await self.redis_manager.get(f"cache:{key}")
        if value is not None:
            self._cache_stats['hits'] += 1
            self._cache_stats['redis_hits'] += 1
            # Store in memory for faster subsequent access
            self._memory_cache[key] = {
                'value': value,
                'expires_at': datetime.utcnow() + timedelta(seconds=60)
            }
            return value
        
        self._cache_stats['misses'] += 1
        return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = 300,
        memory_only: bool = False
    ) -> None:
        """Set cache value"""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        # Store in memory
        self._memory_cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
        
        # Store in Redis (unless memory_only)
        if not memory_only:
            await self.redis_manager.set(f"cache:{key}", value, expire=ttl_seconds)
    
    async def delete(self, key: str) -> None:
        """Delete from both caches"""
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        await self.redis_manager.delete(f"cache:{key}")
    
    async def clear_memory_cache(self) -> None:
        """Clear memory cache"""
        self._memory_cache.clear()
        logger.info("Memory cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = self._cache_stats['hits'] / total_requests if total_requests > 0 else 0
        
        return {
            **self._cache_stats,
            'hit_rate': round(hit_rate, 3),
            'memory_cache_size': len(self._memory_cache)
        }
    
    def cached(self, ttl_seconds: int = 300):
        """Decorator for caching function results"""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = f"{func.__name__}:{self.cache_key(*args, **kwargs)}"
                
                # Try to get from cache
                cached_result = await self.get(cache_key)
                if cached_result is not None:
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await self.set(cache_key, result, ttl_seconds=ttl_seconds)
                
                return result
            
            return wrapper
        return decorator
