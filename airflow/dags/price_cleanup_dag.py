"""
Price Data Cleanup DAG - runs daily at 02:00.
Removes old data, vacuums tables, refreshes materialized view.
"""

import os
from datetime import datetime, timedelta

import psycopg2

from airflow.sdk import DAG, task

DB_CONN = os.environ.get("PRICETRACKER_DB_CONN", "postgresql://node@localhost:5432/pricetracker")

default_args = {
    "owner": "price-tracker",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="price_data_cleanup",
    default_args=default_args,
    description="Daily cleanup of old price data and DB maintenance",
    schedule="0 2 * * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["maintenance"],
):

    @task
    def delete_old_price_history() -> int:
        """Delete price_history records older than 90 days."""
        conn = psycopg2.connect(DB_CONN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM price_history WHERE scraped_at < NOW() - INTERVAL '90 days'"
                )
                deleted = cur.rowcount
                conn.commit()
                return deleted
        finally:
            conn.close()

    @task
    def delete_old_scrape_jobs() -> int:
        """Delete scrape_jobs records older than 30 days."""
        conn = psycopg2.connect(DB_CONN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM scrape_jobs WHERE started_at < NOW() - INTERVAL '30 days'"
                )
                deleted = cur.rowcount
                conn.commit()
                return deleted
        finally:
            conn.close()

    @task
    def deactivate_stale_products() -> int:
        """Mark products as inactive if not scraped in 14 days."""
        conn = psycopg2.connect(DB_CONN)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE products SET is_active = FALSE, updated_at = NOW()
                    WHERE is_active = TRUE
                    AND id NOT IN (
                        SELECT DISTINCT product_id FROM price_history
                        WHERE scraped_at > NOW() - INTERVAL '14 days'
                    )
                    """
                )
                deactivated = cur.rowcount
                conn.commit()
                return deactivated
        finally:
            conn.close()

    @task
    def vacuum_tables(deleted_prices: int, deleted_jobs: int, deactivated: int) -> str:
        """Run VACUUM ANALYZE on main tables."""
        conn = psycopg2.connect(DB_CONN)
        conn.autocommit = True
        try:
            with conn.cursor() as cur:
                for table in ["price_history", "products", "scrape_jobs", "shops"]:
                    cur.execute(f"VACUUM ANALYZE {table}")
        finally:
            conn.close()

        return (
            f"Cleanup done: {deleted_prices} prices deleted, "
            f"{deleted_jobs} jobs deleted, {deactivated} products deactivated"
        )

    @task
    def refresh_materialized_view(summary: str) -> str:
        """Refresh MV after cleanup."""
        conn = psycopg2.connect(DB_CONN)
        try:
            with conn.cursor() as cur:
                cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_latest_prices")
                conn.commit()
        finally:
            conn.close()
        return f"MV refreshed. {summary}"

    # DAG flow
    prices = delete_old_price_history()
    jobs = delete_old_scrape_jobs()
    stale = deactivate_stale_products()
    vacuum_result = vacuum_tables(prices, jobs, stale)
    refresh_materialized_view(vacuum_result)
