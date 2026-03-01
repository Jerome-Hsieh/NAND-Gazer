import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from api.config import settings

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_cached(key: str) -> Optional[str]:
    try:
        r = await get_redis()
        return await r.get(f"pricetracker:{key}")
    except Exception as e:
        logger.warning(f"Redis get error: {e}")
        return None


async def set_cached(key: str, value: str, ttl: int = 300) -> None:
    try:
        r = await get_redis()
        await r.set(f"pricetracker:{key}", value, ex=ttl)
    except Exception as e:
        logger.warning(f"Redis set error: {e}")
