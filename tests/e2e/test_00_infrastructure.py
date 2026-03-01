"""Test 00: Infrastructure connectivity — verify all services are reachable."""

import pytest


class TestInfrastructure:
    """Verify that all backing services are up and reachable."""

    def test_postgresql_connection(self, db_conn):
        """PostgreSQL responds to SELECT 1."""
        cur = db_conn.cursor()
        cur.execute("SELECT 1")
        assert cur.fetchone()[0] == 1

    def test_redis_connection(self, redis_client):
        """Redis responds to PING."""
        assert redis_client.ping() is True

    def test_fastapi_health(self, api_client):
        """FastAPI /api/v1/health returns 200."""
        resp = api_client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_airflow_health(self, airflow_client):
        """Airflow metadatabase is healthy."""
        resp = airflow_client.get("/api/v2/monitor/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["metadatabase"]["status"] == "healthy"

    def test_frontend_reachable(self):
        """Frontend dev server returns 200 with HTML."""
        import httpx

        resp = httpx.get("http://localhost:5173", timeout=10)
        assert resp.status_code == 200
        assert "html" in resp.headers.get("content-type", "").lower()
