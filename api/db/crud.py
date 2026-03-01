from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_products(
    db: AsyncSession,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "updated_at",
    order: str = "desc",
) -> dict:
    """Get products with optional search, pagination, and sorting."""
    offset = (page - 1) * page_size
    allowed_sorts = {"updated_at", "name", "created_at"}
    sort_col = sort_by if sort_by in allowed_sorts else "updated_at"
    sort_order = "ASC" if order.lower() == "asc" else "DESC"

    where_clause = ""
    params: dict = {"limit": page_size, "offset": offset}

    if search:
        where_clause = "WHERE p.is_active = TRUE AND p.name ILIKE :search"
        params["search"] = f"%{search}%"
    else:
        where_clause = "WHERE p.is_active = TRUE"

    count_q = text(f"SELECT COUNT(*) FROM products p {where_clause}")
    count_result = await db.execute(count_q, params)
    total = count_result.scalar()

    query = text(f"""
        SELECT p.id, p.platform, p.item_id, p.name, p.url,
               p.category, p.brand,
               p.created_at, p.updated_at,
               lp.price, lp.original_price, lp.discount_percent, lp.scraped_at AS last_price_at
        FROM products p
        LEFT JOIN mv_latest_prices lp ON lp.product_id = p.id
        {where_clause}
        ORDER BY {sort_col} {sort_order}
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(query, params)
    rows = result.mappings().all()

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


async def get_product_by_id(db: AsyncSession, product_id: int) -> Optional[dict]:
    """Get a single product with its latest price."""
    query = text("""
        SELECT p.id, p.platform, p.item_id, p.name, p.url,
               p.category, p.brand,
               p.created_at, p.updated_at,
               s.name AS shop_name, s.shop_id AS shop_platform_id,
               lp.price, lp.original_price, lp.discount_percent, lp.scraped_at AS last_price_at
        FROM products p
        LEFT JOIN shops s ON s.id = p.shop_id
        LEFT JOIN mv_latest_prices lp ON lp.product_id = p.id
        WHERE p.id = :product_id
    """)
    result = await db.execute(query, {"product_id": product_id})
    row = result.mappings().first()
    return dict(row) if row else None


async def get_price_history(
    db: AsyncSession,
    product_id: int,
    days: int = 30,
) -> list[dict]:
    """Get price history for a product."""
    since = datetime.utcnow() - timedelta(days=days)
    query = text("""
        SELECT id, price, original_price, discount_percent, currency, scraped_at
        FROM price_history
        WHERE product_id = :product_id AND scraped_at >= :since
        ORDER BY scraped_at ASC
    """)
    result = await db.execute(query, {"product_id": product_id, "since": since})
    return [dict(r) for r in result.mappings().all()]


async def get_stats(db: AsyncSession) -> dict:
    """Get dashboard statistics."""
    query = text("""
        SELECT
            (SELECT COUNT(*) FROM products WHERE is_active = TRUE) AS total_products,
            (SELECT COUNT(*) FROM shops) AS total_shops,
            (SELECT COUNT(*) FROM price_history) AS total_price_records,
            (SELECT COUNT(*) FROM tracked_keywords WHERE is_active = TRUE) AS active_keywords,
            (SELECT COUNT(*) FROM price_history WHERE scraped_at > NOW() - INTERVAL '24 hours') AS prices_last_24h,
            (SELECT MAX(scraped_at) FROM price_history) AS last_scrape_at
    """)
    result = await db.execute(query)
    row = result.mappings().first()
    return dict(row) if row else {}
