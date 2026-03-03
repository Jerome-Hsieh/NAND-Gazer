"""Test 02: FastAPI endpoint tests."""

import pytest


class TestHealthEndpoint:
    def test_health_response(self, api_client):
        """GET /api/v1/health returns status=ok and version=1.0.0."""
        resp = api_client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"


class TestProductsEndpoint:
    def test_list_products(self, api_client):
        """GET /api/v1/products returns PaginatedProducts structure."""
        resp = api_client.get("/api/v1/products")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "pages" in data
        assert data["total"] >= 10

    def test_pagination(self, api_client):
        """page_size=3 limits the returned items."""
        resp = api_client.get("/api/v1/products", params={"page_size": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 3
        assert data["page_size"] == 3

    def test_search_ddr5(self, api_client):
        """search=DDR5 returns matching results."""
        resp = api_client.get("/api/v1/products", params={"search": "DDR5"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert "DDR5" in item["name"].upper() or "DDR5" in (item.get("category") or "").upper()

    def test_search_no_results(self, api_client):
        """search=ZZZZNONEXISTENT returns total=0."""
        resp = api_client.get("/api/v1/products", params={"search": "ZZZZNONEXISTENT"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_product_fields(self, api_client):
        """Product items have all expected fields."""
        resp = api_client.get("/api/v1/products", params={"page_size": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) >= 1
        item = data["items"][0]
        required_fields = ["id", "platform", "item_id", "name", "created_at", "updated_at"]
        for field in required_fields:
            assert field in item, f"Missing field: {field}"

    def test_product_detail(self, api_client):
        """GET /api/v1/products/{id} returns detail with shop_name."""
        # Get first product id
        resp = api_client.get("/api/v1/products", params={"page_size": 1})
        product_id = resp.json()["items"][0]["id"]

        resp = api_client.get(f"/api/v1/products/{product_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == product_id
        assert "shop_name" in data

    def test_product_not_found(self, api_client):
        """GET /api/v1/products/999999 returns 404."""
        resp = api_client.get("/api/v1/products/999999")
        assert resp.status_code == 404


class TestPricesEndpoint:
    def test_price_history(self, api_client):
        """GET /api/v1/products/{id}/prices returns price points."""
        # Get first product id
        resp = api_client.get("/api/v1/products", params={"page_size": 1})
        product_id = resp.json()["items"][0]["id"]

        resp = api_client.get(f"/api/v1/products/{product_id}/prices")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        point = data[0]
        assert "price" in point
        assert "currency" in point
        assert point["currency"] == "TWD"
        assert "scraped_at" in point

    def test_prices_sorted_asc(self, api_client):
        """Price history is sorted by scraped_at ascending."""
        resp = api_client.get("/api/v1/products", params={"page_size": 1})
        product_id = resp.json()["items"][0]["id"]

        resp = api_client.get(f"/api/v1/products/{product_id}/prices")
        data = resp.json()
        timestamps = [p["scraped_at"] for p in data]
        assert timestamps == sorted(timestamps), "Prices not sorted by scraped_at ASC"


class TestStatsEndpoint:
    def test_stats_response(self, api_client):
        """GET /api/v1/stats returns all expected fields with reasonable values."""
        resp = api_client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_products"] >= 10
        assert data["total_shops"] >= 1
        assert data["total_price_records"] >= 1000
        assert data["active_keywords"] >= 2
        assert "keyword_names" in data
        assert isinstance(data["keyword_names"], list)
        assert len(data["keyword_names"]) >= 2

    def test_stats_matches_db(self, api_client, db_conn):
        """Stats total_products matches DB count of active products."""
        resp = api_client.get("/api/v1/stats")
        api_total = resp.json()["total_products"]

        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM products WHERE is_active = true")
        db_total = cur.fetchone()[0]

        assert api_total == db_total
