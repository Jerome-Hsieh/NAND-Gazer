"""Root fixtures for E2E tests."""

import os

import httpx
import psycopg2
import pytest
import redis as redis_lib

API_URL = os.getenv("API_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://localhost:8081")
DB_CONN = os.getenv("DB_CONN", "postgresql://pricetracker:pricetracker@localhost:5432/pricetracker")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="session")
def api_url():
    return API_URL


@pytest.fixture(scope="session")
def frontend_url():
    return FRONTEND_URL


@pytest.fixture(scope="session")
def airflow_url():
    return AIRFLOW_URL


@pytest.fixture(scope="session")
def api_client():
    """httpx client for FastAPI."""
    with httpx.Client(base_url=API_URL, timeout=30) as client:
        yield client


@pytest.fixture(scope="session")
def airflow_client():
    """httpx client for Airflow REST API v2."""
    with httpx.Client(base_url=AIRFLOW_URL, timeout=30) as client:
        yield client


@pytest.fixture(scope="session")
def db_conn():
    """psycopg2 connection to the pricetracker database."""
    conn = psycopg2.connect(DB_CONN)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture(scope="session")
def redis_client():
    """Redis client."""
    client = redis_lib.from_url(REDIS_URL)
    yield client
    client.close()
