import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.db.crud import get_products, get_product_by_id
from api.models.schemas import PaginatedProducts, ProductDetail
from api.cache.redis_client import get_cached, set_cached

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=PaginatedProducts)
async def list_products(
    search: Optional[str] = Query(None, description="Search keyword"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("updated_at"),
    order: str = Query("desc"),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"products:{search}:{page}:{page_size}:{sort_by}:{order}"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    result = await get_products(db, search=search, page=page, page_size=page_size, sort_by=sort_by, order=order)
    await set_cached(cache_key, json.dumps(result, default=str), ttl=300)
    return result


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    cache_key = f"product:{product_id}"
    cached = await get_cached(cache_key)
    if cached:
        return json.loads(cached)

    product = await get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    await set_cached(cache_key, json.dumps(product, default=str), ttl=300)
    return product
