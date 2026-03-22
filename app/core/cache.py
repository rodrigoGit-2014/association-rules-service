"""Redis caching layer with graceful degradation"""

import json
import hashlib
import logging
import functools
from typing import Optional, Any, Callable

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache wrapper with graceful degradation"""

    def __init__(self):
        self._client: Optional[redis.Redis] = None

    @property
    def client(self) -> Optional[redis.Redis]:
        if self._client is None:
            try:
                self._client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                self._client.ping()
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(f"Redis unavailable: {e}")
                self._client = None
        return self._client

    def get(self, key: str) -> Optional[Any]:
        try:
            client = self.client
            if client is None:
                return None
            data = client.get(key)
            if data:
                return json.loads(data)
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            client = self.client
            if client is None:
                return False
            ttl = ttl or settings.CACHE_TTL_SECONDS
            client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except redis.RedisError as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        try:
            client = self.client
            if client is None:
                return 0
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
        except redis.RedisError as e:
            logger.warning(f"Cache delete error for pattern {pattern}: {e}")
        return 0


cache = RedisCache()


def make_cache_key(prefix: str, **kwargs) -> str:
    """Generate a deterministic cache key from prefix and keyword arguments"""
    sorted_params = json.dumps(kwargs, sort_keys=True, default=str)
    param_hash = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
    return f"v2:{prefix}:{param_hash}"


def cached(prefix: str, ttl: Optional[int] = None) -> Callable:
    """Decorator for caching function results in Redis"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = make_cache_key(prefix, **kwargs)
            result = cache.get(key)
            if result is not None:
                logger.debug(f"Cache hit: {key}")
                return result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator
