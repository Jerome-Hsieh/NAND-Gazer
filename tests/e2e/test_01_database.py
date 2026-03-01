"""Test 01: Database schema, seed data, and indexes."""

import pytest


class TestDatabaseSchema:
    """Verify the database schema is correctly set up."""

    CORE_TABLES = ["shops", "products", "price_history", "tracked_keywords", "scrape_jobs"]

    def test_core_tables_exist(self, db_conn):
        """All 5 core tables exist in the public schema."""
        cur = db_conn.cursor()
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
        tables = {row[0] for row in cur.fetchall()}
        for table in self.CORE_TABLES:
            assert table in tables, f"Table '{table}' not found. Existing: {tables}"

    def test_materialized_view_exists(self, db_conn):
        """mv_latest_prices materialized view exists."""
        cur = db_conn.cursor()
        cur.execute(
            "SELECT matviewname FROM pg_matviews WHERE schemaname = 'public'"
        )
        views = {row[0] for row in cur.fetchall()}
        assert "mv_latest_prices" in views

    def test_pchome_shop_exists(self, db_conn):
        """PChome 24h shop record exists (platform='pchome')."""
        cur = db_conn.cursor()
        cur.execute("SELECT id, platform FROM shops WHERE platform = 'pchome'")
        row = cur.fetchone()
        assert row is not None, "PChome shop not found"
        assert row[0] == 1  # shop_id = 1

    def test_seed_products_count(self, db_conn):
        """At least 10 seed products exist."""
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products")
        count = cur.fetchone()[0]
        assert count >= 10, f"Expected >= 10 products, got {count}"

    def test_seed_price_history_count(self, db_conn):
        """At least 1000 price history records from seed data."""
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM price_history")
        count = cur.fetchone()[0]
        assert count >= 1000, f"Expected >= 1000 price_history rows, got {count}"

    def test_tracked_keywords(self, db_conn):
        """tracked_keywords contains DDR5 and DDR4 keywords."""
        cur = db_conn.cursor()
        cur.execute("SELECT keyword FROM tracked_keywords WHERE is_active = true")
        keywords = {row[0] for row in cur.fetchall()}
        assert "DDR5 記憶體" in keywords
        assert "DDR4 記憶體" in keywords

    def test_key_indexes_exist(self, db_conn):
        """Critical indexes exist on price_history and products."""
        cur = db_conn.cursor()
        cur.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
        )
        indexes = {row[0] for row in cur.fetchall()}
        expected = [
            "idx_price_history_product_scraped",
            "idx_products_platform_item",
            "idx_price_history_scraped_at",
            "idx_products_active",
        ]
        for idx in expected:
            assert idx in indexes, f"Index '{idx}' not found. Existing: {indexes}"
