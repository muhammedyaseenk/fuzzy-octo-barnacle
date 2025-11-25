# app/core/cache.py
import json
import redis.asyncio as redis
from typing import Optional, Any
from app.core.config import settings

# Redis client
redis_client = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        decode_responses=True
    )


async def get_redis():
    """Get Redis client"""
    if redis_client is None:
        await init_redis()
    return redis_client


async def cache_set(key: str, value: Any, expire: int = 3600):
    """Set cache value with expiration"""
    client = await get_redis()
    serialized_value = json.dumps(value) if not isinstance(value, str) else value
    await client.setex(key, expire, serialized_value)


async def cache_get(key: str) -> Optional[Any]:
    """Get cache value"""
    client = await get_redis()
    value = await client.get(key)
    if value is None:
        return None
    
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


async def cache_delete(key: str):
    """Delete cache key"""
    client = await get_redis()
    await client.delete(key)


async def cache_exists(key: str) -> bool:
    """Check if cache key exists"""
    client = await get_redis()
    return await client.exists(key)


# Cache key generators
def get_user_profile_cache_key(user_id: int) -> str:
    return f"profile:{user_id}"


def get_matching_feed_cache_key(user_id: int, page: int = 1) -> str:
    return f"feed:{user_id}:page:{page}"


def get_search_results_cache_key(filters: dict) -> str:
    # Create a consistent key from filter parameters
    filter_str = "&".join(f"{k}={v}" for k, v in sorted(filters.items()))
    return f"search:{hash(filter_str)}"