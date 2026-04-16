import logging
import time
from functools import lru_cache
from typing import Any, Callable, Optional
import hashlib
import json

logger = logging.getLogger(__name__)


class QueryCache:
    """In-memory cache for Neo4j queries with TTL support."""

    def __init__(self, default_ttl: int = 300, max_size: int = 1000):
        self._cache = {}
        self._timestamps = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._hits = 0
        self._misses = 0

    def _generate_key(self, query: str, params: dict) -> str:
        """Generate cache key from query and parameters."""
        key_data = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, query: str, params: dict) -> Optional[list]:
        """Get cached result if exists and not expired."""
        key = self._generate_key(query, params)

        if key in self._cache:
            timestamp = self._timestamps.get(key, 0)
            if time.time() - timestamp < self.default_ttl:
                self._hits += 1
                logger.debug(f"Cache HIT for query: {query[:50]}...")
                return self._cache[key]
            else:
                del self._cache[key]
                if key in self._timestamps:
                    del self._timestamps[key]

        self._misses += 1
        return None

    def set(self, query: str, params: dict, result: list):
        """Store result in cache."""
        if len(self._cache) >= self.max_size:
            self._evict_oldest()

        key = self._generate_key(query, params)
        self._cache[key] = result
        self._timestamps[key] = time.time()
        logger.debug(f"Cache SET for query: {query[:50]}...")

    def _evict_oldest(self):
        """Evict oldest entry when cache is full."""
        if not self._timestamps:
            return

        oldest_key = min(self._timestamps, key=self._timestamps.get)
        del self._cache[oldest_key]
        del self._timestamps[oldest_key]
        logger.debug("Evicted oldest cache entry")

    def invalidate(self, query: str = None, params: dict = None):
        """Invalidate specific cache entry or all if no params."""
        if query is None and params is None:
            self._cache.clear()
            self._timestamps.clear()
            logger.info("Cache cleared")
            return

        key = self._generate_key(query, params)
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self._cache),
            "max_size": self.max_size,
        }


class CachedNeo4jClient:
    """Wrapper around Neo4jClient that adds caching capabilities."""

    def __init__(
        self, neo4j_client, ttl: int = 300, max_size: int = 1000, enabled: bool = True
    ):
        self._client = neo4j_client
        self._cache = QueryCache(default_ttl=ttl, max_size=max_size)
        self._enabled = enabled
        logger.info(
            f"Query caching enabled: {enabled}, TTL: {ttl}s, Max size: {max_size}"
        )

    def __getattr__(self, name: str):
        """Proxy attribute access to underlying client."""
        return getattr(self._client, name)

    def run_cached(self, query: str, params: dict = None, ttl: int = None) -> list:
        """Execute query with caching."""
        params = params or {}

        if not self._enabled:
            return self._client.run_raw(query, params)

        cached_result = self._cache.get(query, params)
        if cached_result is not None:
            return cached_result

        result = self._client.run_raw(query, params)

        if ttl is not None:
            original_ttl = self._cache.default_ttl
            self._cache.default_ttl = ttl
            self._cache.set(query, params, result)
            self._cache.default_ttl = original_ttl
        else:
            self._cache.set(query, params, result)

        return result

    def invalidate_cache(self, query: str = None, params: dict = None):
        """Invalidate cache entries."""
        self._cache.invalidate(query, params)

    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        return self._cache.get_stats()

    def enable_cache(self):
        """Enable caching."""
        self._enabled = True
        logger.info("Query cache enabled")

    def disable_cache(self):
        """Disable caching."""
        self._enabled = False
        logger.info("Query cache disabled")
