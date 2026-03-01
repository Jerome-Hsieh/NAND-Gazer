"""
PChome Price Scraper DAG - runs every 6 hours.
Uses Airflow 3.x TaskFlow API with dynamic task mapping.
"""

import logging
import os
from datetime import datetime, timedelta

import psycopg2
import psycopg2.extras
import redis

from airflow.sdk import DAG, task

logger = logging.getLogger(__name__)

DB_CONN = os.environ.get("PRICETRACKER_DB_CONN", "postgresql://node@localhost:5432/pricetracker")
REDIS_URL = os.environ.get("PRICETRACKER_REDIS_URL", "redis://localhost:6379/0")

default_args = {
    "owner": "price-tracker",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="pchome_price_scraper",
    default_args=default_args,
    description="Scrape PChome 24h product prices every 6 hours",
    schedule="0 */6 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["scraper", "pchome"],
    max_active_runs=1,
):

    @task
    def get_active_keywords() -> list[dict]:
        """Fetch active keywords from the database."""
        conn = psycopg2.connect(DB_CONN)
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, keyword, max_pages FROM tracked_keywords WHERE is_active = TRUE"
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        finally:
            conn.close()

    @task
    def scrape_keyword(kw: dict) -> dict:
        """Scrape a single keyword from PChome."""
        from scraper.pchome import PChomeClient, parse_search_response

        keyword = kw["keyword"]
        max_pages = kw.get("max_pages", 2)
        logger.info("Scraping keyword: %s, max_pages: %d", keyword, max_pages)

        all_products = []
        with PChomeClient() as client:
            responses = client.search_pages(keyword, pages=max_pages)
            for data in responses:
                products = parse_search_response(data)
                for p in products:
                    # Determine price and original_price for DB
                    # If sale_price exists: price=sale_price, original_price=price (the display/origin price)
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

        logger.info("Keyword '%s': found %d products", keyword, len(all_products))
        return {"keyword": keyword, "products": all_products}

    @task
    def upsert_products_and_prices(result: dict) -> dict:
        """Upsert products and record prices into the database."""
        keyword = result["keyword"]
        products = result["products"]
        conn = psycopg2.connect(DB_CONN)
        products_upserted = 0
        prices_recorded = 0

        # PChome 24h is a single shop — ensure it exists
        PCHOME_SHOP_ID = 1  # platform shop_id

        try:
            with conn.cursor() as cur:
                # Ensure PChome 24h shop exists
                cur.execute(
                    """
                    INSERT INTO shops (platform, shop_id, name)
                    VALUES ('pchome', %s, 'PChome 24h')
                    ON CONFLICT (platform, shop_id) DO UPDATE SET
                        updated_at = NOW()
                    RETURNING id
                    """,
                    (PCHOME_SHOP_ID,),
                )
                db_shop_id = cur.fetchone()[0]

                # Log scrape job
                cur.execute(
                    "INSERT INTO scrape_jobs (keyword, status) VALUES (%s, 'running') RETURNING id",
                    (keyword,),
                )
                job_id = cur.fetchone()[0]

                for p in products:
                    # Upsert product
                    cur.execute(
                        """
                        INSERT INTO products (platform, item_id, shop_id, name, url,
                                              category, brand)
                        VALUES ('pchome', %(item_id)s, %(shop_id)s, %(name)s, %(url)s,
                                %(category)s, %(brand)s)
                        ON CONFLICT (platform, item_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            url = EXCLUDED.url,
                            category = COALESCE(EXCLUDED.category, products.category),
                            brand = COALESCE(EXCLUDED.brand, products.brand),
                            updated_at = NOW()
                        RETURNING id
                        """,
                        {
                            "item_id": p["item_id"],
                            "shop_id": db_shop_id,
                            "name": p["name"],
                            "url": p["url"],
                            "category": p.get("category"),
                            "brand": p.get("brand"),
                        },
                    )
                    db_product_id = cur.fetchone()[0]
                    products_upserted += 1

                    # Insert price history
                    cur.execute(
                        """
                        INSERT INTO price_history (product_id, price, original_price, discount_percent)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (db_product_id, p["price"], p.get("original_price"), p.get("discount_percent")),
                    )
                    prices_recorded += 1

                # Update job
                cur.execute(
                    """
                    UPDATE scrape_jobs SET status = 'success',
                        products_found = %s, prices_recorded = %s, finished_at = NOW()
                    WHERE id = %s
                    """,
                    (products_upserted, prices_recorded, job_id),
                )
                conn.commit()

        except Exception as e:
            conn.rollback()
            logger.error("DB error for keyword '%s': %s", keyword, e)
            raise
        finally:
            conn.close()

        return {"keyword": keyword, "products_upserted": products_upserted, "prices_recorded": prices_recorded}

    @task
    def refresh_materialized_view(results: list[dict]) -> str:
        """Refresh the materialized view after all data is inserted."""
        total_products = sum(r.get("products_upserted", 0) for r in results)
        total_prices = sum(r.get("prices_recorded", 0) for r in results)

        conn = psycopg2.connect(DB_CONN)
        try:
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_latest_prices")
                conn.commit()
        finally:
            conn.close()

        msg = f"Refreshed MV. Total: {total_products} products, {total_prices} prices"
        logger.info(msg)
        return msg

    @task
    def invalidate_cache(summary: str) -> str:
        """Clear Redis cache after data update."""
        r = redis.from_url(REDIS_URL)
        keys = r.keys("pricetracker:*")
        if keys:
            r.delete(*keys)
            logger.info("Cleared %d cache keys", len(keys))
        return f"Cache invalidated. {summary}"

    # DAG flow
    keywords = get_active_keywords()
    scraped = scrape_keyword.expand(kw=keywords)
    db_results = upsert_products_and_prices.expand(result=scraped)
    mv_summary = refresh_materialized_view(db_results)
    invalidate_cache(mv_summary)
