"""Test 05: Full pipeline — DAG trigger → DB → API → Frontend verification."""

import re

import pytest
from tests.utils.airflow_client import AirflowAPIClient

DAG_TIMEOUT = 60


@pytest.mark.slow
@pytest.mark.frontend
class TestFullPipeline:
    """End-to-end: trigger scraper DAG and verify results appear in API and frontend."""

    @pytest.mark.timeout(DAG_TIMEOUT + 60)
    def test_dag_results_visible_everywhere(self, api_client, db_conn, browser):
        """Full E2E: DAG → DB → API → Frontend."""
        af_client = AirflowAPIClient()
        try:
            # 1. Record baseline
            cur = db_conn.cursor()
            cur.execute("SELECT COUNT(*) FROM scrape_jobs")
            jobs_before = cur.fetchone()[0]

            stats_before = api_client.get("/api/v1/stats").json()
            records_before = stats_before["total_price_records"]

            # 2. Unpause & trigger scraper DAG
            af_client.unpause_dag("pchome_price_scraper")
            trigger_result = af_client.trigger_dag("pchome_price_scraper")
            run_id = trigger_result["dag_run_id"]

            # 3. Wait for completion
            dag_run = af_client.wait_for_dag_run(
                "pchome_price_scraper", run_id, timeout=DAG_TIMEOUT
            )
            assert dag_run["state"] == "success", (
                f"DAG run ended with state={dag_run['state']}"
            )

            # 4. Verify DB — new scrape_jobs record
            cur.execute("SELECT COUNT(*) FROM scrape_jobs")
            jobs_after = cur.fetchone()[0]
            assert jobs_after > jobs_before, (
                f"scrape_jobs count did not increase: {jobs_before} → {jobs_after}"
            )

            # 5. Verify API — total_price_records >= before
            stats_after = api_client.get("/api/v1/stats").json()
            assert stats_after["total_price_records"] >= records_before

            # 6. Playwright — verify homepage stats
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            page = context.new_page()
            try:
                page.goto("http://localhost:5173")
                page.wait_for_selector(".text-3xl.font-bold", timeout=10000)

                # Stats card for Price Records should show a number > 0
                stat_values = page.locator(".text-3xl.font-bold").all_text_contents()
                assert len(stat_values) >= 4, f"Expected 4 stat values, got {len(stat_values)}"
                # At least one should be a non-zero number
                has_nonzero = any(
                    v.replace(",", "").isdigit() and int(v.replace(",", "")) > 0
                    for v in stat_values
                )
                assert has_nonzero, f"No non-zero stat values: {stat_values}"

                # 7. Navigate to search — should show products
                page.goto("http://localhost:5173/search")
                page.wait_for_selector("a[href^='/product/']", timeout=10000)
                cards = page.locator("a[href^='/product/']")
                assert cards.count() > 0

                # 8. Navigate to product detail — chart should be visible
                cards.first.click()
                page.wait_for_url(re.compile(r"/product/\d+"))
                page.wait_for_selector("h2", timeout=10000)
                h2 = page.locator("h2", has_text="Price History")
                assert h2.count() > 0, "Price History heading not found"
                # SVG chart should exist
                svg_count = page.locator("svg").count()
                assert svg_count > 0, "No SVG chart found on product detail page"
            finally:
                page.close()
                context.close()
        finally:
            af_client.close()
