import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.db.crud import get_stats
from api.models.schemas import StatsResponse
from api.cache.redis_client import get_cached, set_cached

router = APIRouter(tags=["stats"])


@router.get("/stats", response_model=StatsResponse)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    cache_key = "stats"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    stats = await get_stats(db)
    await set_cached(cache_key, json.dumps(stats, default=str), ttl=60)
    return stats
