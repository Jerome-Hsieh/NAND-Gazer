"""Test 03: Airflow DAGs — metadata, trigger, and execution verification."""

import pytest
from tests.utils.airflow_client import AirflowAPIClient

DAG_TIMEOUT = 60


@pytest.fixture(scope="module")
def af_client():
    """Airflow API client for this module."""
    client = AirflowAPIClient()
    yield client
    client.close()


class TestDAGMetadata:
    """Verify DAG listing and metadata."""

    def test_dag_list_contains_scraper(self, af_client):
        """DAG list contains pchome_price_scraper."""
        dags = af_client.list_dags()
        dag_ids = [d["dag_id"] for d in dags.get("dags", [])]
        assert "pchome_price_scraper" in dag_ids

    def test_dag_list_contains_cleanup(self, af_client):
        """DAG list contains price_data_cleanup."""
        dags = af_client.list_dags()
        dag_ids = [d["dag_id"] for d in dags.get("dags", [])]
        assert "price_data_cleanup" in dag_ids

    def test_scraper_dag_tags(self, af_client):
        """Scraper DAG has 'scraper' and 'pchome' tags."""
        dag = af_client.get_dag("pchome_price_scraper")
        tags = [t["name"] if isinstance(t, dict) else t for t in dag.get("tags", [])]
        assert "scraper" in tags
        assert "pchome" in tags

    def test_cleanup_dag_tags(self, af_client):
        """Cleanup DAG has 'maintenance' tag."""
        dag = af_client.get_dag("price_data_cleanup")
        tags = [t["name"] if isinstance(t, dict) else t for t in dag.get("tags", [])]
        assert "maintenance" in tags

    def test_unpause_scraper_dag(self, af_client):
        """Unpause the scraper DAG via PATCH."""
        result = af_client.unpause_dag("pchome_price_scraper")
        assert result.get("is_paused") is False


@pytest.mark.slow
class TestScraperDAGExecution:
    """Trigger and verify pchome_price_scraper DAG run."""

    @pytest.fixture(autouse=True)
    def _setup(self, af_client):
        """Ensure DAG is unpaused before testing."""
        af_client.unpause_dag("pchome_price_scraper")

    def test_trigger_scraper_dag(self, af_client):
        """Trigger pchome_price_scraper and verify initial state."""
        result = af_client.trigger_dag("pchome_price_scraper")
        assert "dag_run_id" in result
        assert result["state"] in ("queued", "running")

    @pytest.mark.timeout(DAG_TIMEOUT + 30)
    def test_scraper_dag_completes(self, af_client):
        """Scraper DAG run completes successfully within timeout."""
        trigger_result = af_client.trigger_dag("pchome_price_scraper")
        run_id = trigger_result["dag_run_id"]

        dag_run = af_client.wait_for_dag_run(
            "pchome_price_scraper", run_id, timeout=DAG_TIMEOUT
        )
        assert dag_run["state"] == "success", (
            f"DAG run ended with state={dag_run['state']}"
        )

    @pytest.mark.timeout(DAG_TIMEOUT + 30)
    def test_scraper_all_tasks_success(self, af_client):
        """All task instances in the scraper DAG run are successful."""
        trigger_result = af_client.trigger_dag("pchome_price_scraper")
        run_id = trigger_result["dag_run_id"]
        af_client.wait_for_dag_run(
            "pchome_price_scraper", run_id, timeout=DAG_TIMEOUT
        )

        ti_data = af_client.get_task_instances("pchome_price_scraper", run_id)
        task_instances = ti_data.get("task_instances", [])
        assert len(task_instances) > 0, "No task instances found"
        for ti in task_instances:
            assert ti["state"] == "success", (
                f"Task {ti['task_id']} has state={ti['state']}"
            )

    @pytest.mark.timeout(DAG_TIMEOUT + 30)
    def test_scraper_creates_scrape_job(self, af_client, db_conn):
        """After scraper DAG run, scrape_jobs has a new success record."""
        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM scrape_jobs")
        before_count = cur.fetchone()[0]

        trigger_result = af_client.trigger_dag("pchome_price_scraper")
        run_id = trigger_result["dag_run_id"]
        af_client.wait_for_dag_run(
            "pchome_price_scraper", run_id, timeout=DAG_TIMEOUT
        )

        cur.execute("SELECT COUNT(*) FROM scrape_jobs")
        after_count = cur.fetchone()[0]
        assert after_count > before_count, (
            f"scrape_jobs count did not increase: {before_count} → {after_count}"
        )


@pytest.mark.slow
class TestCleanupDAGExecution:
    """Trigger and verify price_data_cleanup DAG run."""

    @pytest.fixture(autouse=True)
    def _setup(self, af_client):
        af_client.unpause_dag("price_data_cleanup")

    @pytest.mark.timeout(DAG_TIMEOUT + 30)
    def test_cleanup_dag_completes(self, af_client):
        """Cleanup DAG run completes successfully."""
        trigger_result = af_client.trigger_dag("price_data_cleanup")
        run_id = trigger_result["dag_run_id"]

        dag_run = af_client.wait_for_dag_run(
            "price_data_cleanup", run_id, timeout=DAG_TIMEOUT
        )
        assert dag_run["state"] == "success", (
            f"Cleanup DAG ended with state={dag_run['state']}"
        )

    @pytest.mark.timeout(DAG_TIMEOUT + 30)
    def test_cleanup_preserves_seed_data(self, af_client, db_conn):
        """Cleanup DAG does not delete seed data (< 90 days old)."""
        trigger_result = af_client.trigger_dag("price_data_cleanup")
        run_id = trigger_result["dag_run_id"]
        af_client.wait_for_dag_run(
            "price_data_cleanup", run_id, timeout=DAG_TIMEOUT
        )

        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM price_history")
        count = cur.fetchone()[0]
        assert count >= 1000, (
            f"Price history count dropped below 1000 after cleanup: {count}"
        )
