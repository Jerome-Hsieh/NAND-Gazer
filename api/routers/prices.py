import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.db.crud import get_price_history
from api.models.schemas import PricePoint
from api.cache.redis_client import get_cached, set_cached

router = APIRouter(prefix="/products", tags=["prices"])


@router.get("/{product_id}/prices", response_model=list[PricePoint])
async def get_prices(
    product_id: int,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"prices:{product_id}:{days}"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    prices = await get_price_history(db, product_id, days=days)
    await set_cached(cache_key, json.dumps(prices, default=str), ttl=300)
    return prices
