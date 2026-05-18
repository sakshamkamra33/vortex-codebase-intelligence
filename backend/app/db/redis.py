"""
VortexRAG — Redis Client (Semantic Cache + Rate Limiting)
"""
import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("vortex")

_redis: aioredis.Redis | None = None


async def init_redis() -> None:
    global _redis
    if settings.REDIS_URL:
        logger.info("🔮 Connecting to Redis Cloud (Upstash)...")
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    else:
        logger.info(f"🔮 Connecting to local Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        _redis = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            max_connections=20,
        )
    # Verify connection
    await _redis.ping()
    logger.info("✅ Redis connected.")


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis client not initialized. Call init_redis() first.")
    return _redis
