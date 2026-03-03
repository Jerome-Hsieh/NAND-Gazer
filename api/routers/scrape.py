"""Manual scrape endpoint — triggers PChome product scraping on demand."""

import asyncio
import logging
import sys
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.database import get_db
from api.cache.redis_client import get_redis
from api.models.schemas import ScrapeResponse

# Make the airflow/include package importable so we can reuse the scraper
_include_path = str(Path(__file__).resolve().parents[2] / "airflow" / "include")
if _include_path not in sys.path:
    sys.path.insert(0, _include_path)

from scraper.pchome import PChomeClient, parse_search_response  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["scrape"])


def _run_scrape(keywords: list[dict]) -> list[dict]:
    """Run synchronous PChome scraping for all keywords. Returns list of product dicts."""
    all_products: list[dict] = []
    with PChomeClient() as client:
        for kw in keywords:
            keyword = kw["keyword"]
            max_pages = kw.get("max_pages", 2)
            try:
                responses = client.search_pages(keyword, pages=max_pages)
                for data in responses:
                    products = parse_search_response(data)
                    for p in products:
                        if p.sale_price is not None:
                            db_price = p.sale_price
                            db_original_price = p.price
                        else:
                            db_price = p.price
                            db_original_price = None

                        discount = None
                        if db_original_price and db_original_price > 0 and db_price < db_original_price:
                            discount = round((1 - db_price / db_original_price) * 100, 2)

                        all_products.append({
                            "item_id": p.product_id,
                            "name": p.name,
                            "price": db_price,
                            "original_price": db_original_price,
                            "discount_percent": discount,
                            "category": p.category,
                            "brand": p.brand,
                            "url": p.url,
                        })
            except Exception:
                logger.exception("Failed to scrape keyword '%s'", keyword)
    return all_products


@router.post("", response_model=ScrapeResponse)
async def trigger_scrape(db: AsyncSession = Depends(get_db)):
    # 1. Fetch active keywords
    result = await db.execute(
        text("SELECT id, keyword, max_pages FROM tracked_keywords WHERE is_active = TRUE")
    )
    keywords = [dict(r._mapping) for r in result]

    if not keywords:
        return ScrapeResponse(
            keywords_scraped=0,
            products_found=0,
            prices_recorded=0,
            message="No active keywords configured",
        )

    # 2. Run sync scraping in a thread executor
    loop = asyncio.get_event_loop()
    all_products = await loop.run_in_executor(None, _run_scrape, keywords)

    # 3. Ensure PChome shop exists
    shop_result = await db.execute(
        text(
            """
            INSERT INTO shops (platform, shop_id, name)
            VALUES ('pchome', 1, 'PChome 24h')
            ON CONFLICT (platform, shop_id) DO UPDATE SET updated_at = NOW()
            RETURNING id
            """
        )
    )
    db_shop_id = shop_result.scalar_one()

    # 4. Upsert products and insert prices
    products_found = 0
    prices_recorded = 0

    for p in all_products:
        prod_result = await db.execute(
            text(
                """
                INSERT INTO products (platform, item_id, shop_id, name, url, category, brand)
                VALUES ('pchome', :item_id, :shop_id, :name, :url, :category, :brand)
                ON CONFLICT (platform, item_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    url = EXCLUDED.url,
                    category = COALESCE(EXCLUDED.category, products.category),
                    brand = COALESCE(EXCLUDED.brand, products.brand),
                    updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "item_id": p["item_id"],
                "shop_id": db_shop_id,
                "name": p["name"],
                "url": p["url"],
                "category": p.get("category"),
                "brand": p.get("brand"),
            },
        )
        db_product_id = prod_result.scalar_one()
        products_found += 1

        await db.execute(
            text(
                """
                INSERT INTO price_history (product_id, price, original_price, discount_percent)
                VALUES (:product_id, :price, :original_price, :discount_percent)
                """
            ),
            {
                "product_id": db_product_id,
                "price": p["price"],
                "original_price": p.get("original_price"),
                "discount_percent": p.get("discount_percent"),
            },
        )
        prices_recorded += 1

    # 5. Refresh materialized view
    await db.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_latest_prices"))
    await db.commit()

    # 6. Invalidate Redis cache
    try:
        r = await get_redis()
        keys = []
        async for key in r.scan_iter(match="pricetracker:*"):
            keys.append(key)
        if keys:
            await r.delete(*keys)
            logger.info("Cleared %d cache keys", len(keys))
    except Exception:
        logger.warning("Failed to invalidate cache", exc_info=True)

    return ScrapeResponse(
        keywords_scraped=len(keywords),
        products_found=products_found,
        prices_recorded=prices_recorded,
        message=f"Scraped {len(keywords)} keywords, found {products_found} products",
    )
