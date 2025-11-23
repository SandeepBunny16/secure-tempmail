"""
Redis Client

Provides Redis connection and utilities:
- Connection pooling
- TTL management
- Rate limiting helpers
"""

import logging
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from app.config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)

# Global Redis client
_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """
    Get Redis client instance.
    
    Creates a connection pool on first call and reuses it.
    
    Returns:
        Redis: Redis client instance
    """
    global _redis_client
    
    if _redis_client is None:
        logger.info("Creating Redis connection pool...")
        
        try:
            _redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=settings.REDIS_POOL_SIZE,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                socket_keepalive=True,
                health_check_interval=30,
            )
            
            # Test connection
            await _redis_client.ping()
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise
    
    return _redis_client


async def close_redis_client():
    """
    Close Redis connection.
    
    Should be called on application shutdown.
    """
    global _redis_client
    
    if _redis_client is not None:
        logger.info("Closing Redis connection...")
        await _redis_client.close()
        await _redis_client.connection_pool.disconnect()
        _redis_client = None
        logger.info("Redis connection closed")


# ===================================
# Redis Utilities
# ===================================

async def set_with_ttl(
    redis_client: Redis,
    key: str,
    value: str,
    ttl_seconds: int,
) -> bool:
    """
    Set a key with TTL.
    
    Args:
        redis_client: Redis client
        key: Key name
        value: Value to store
        ttl_seconds: TTL in seconds
    
    Returns:
        bool: True if successful
    """
    try:
        await redis_client.setex(key, ttl_seconds, value)
        return True
    except Exception as e:
        logger.error(f"Redis SET failed: {e}")
        return False


async def get_ttl(
    redis_client: Redis,
    key: str,
) -> int:
    """
    Get remaining TTL for a key.
    
    Args:
        redis_client: Redis client
        key: Key name
    
    Returns:
        int: TTL in seconds (-2 if key doesn't exist, -1 if no TTL)
    """
    try:
        return await redis_client.ttl(key)
    except Exception as e:
        logger.error(f"Redis TTL check failed: {e}")
        return -2


async def delete_keys(
    redis_client: Redis,
    pattern: str,
) -> int:
    """
    Delete all keys matching pattern.
    
    Args:
        redis_client: Redis client
        pattern: Key pattern (e.g., "inbox:*")
    
    Returns:
        int: Number of keys deleted
    """
    try:
        keys = []
        async for key in redis_client.scan_iter(match=pattern):
            keys.append(key)
        
        if keys:
            return await redis_client.delete(*keys)
        return 0
        
    except Exception as e:
        logger.error(f"Redis DELETE pattern failed: {e}")
        return 0


async def increment_with_ttl(
    redis_client: Redis,
    key: str,
    ttl_seconds: int,
) -> int:
    """
    Increment a counter with TTL.
    
    If key doesn't exist, creates it with value 1 and sets TTL.
    
    Args:
        redis_client: Redis client
        key: Key name
        ttl_seconds: TTL in seconds
    
    Returns:
        int: New value after increment
    """
    try:
        # Use pipeline for atomicity
        async with redis_client.pipeline() as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds)
            results = await pipe.execute()
            return results[0]
    except Exception as e:
        logger.error(f"Redis INCR failed: {e}")
        return 0