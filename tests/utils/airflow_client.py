"""Airflow REST API v2 helper client."""

import time
from datetime import datetime, timezone

import httpx


class AirflowAPIClient:
    """Helper class for interacting with the Airflow 3.x REST API v2."""

    def __init__(self, base_url: str = "http://localhost:8081", timeout: float = 30):
        self.client = httpx.Client(base_url=base_url, timeout=timeout)

    def close(self):
        self.client.close()

    def list_dags(self) -> dict:
        resp = self.client.get("/api/v2/dags")
        resp.raise_for_status()
        return resp.json()

    def get_dag(self, dag_id: str) -> dict:
        resp = self.client.get(f"/api/v2/dags/{dag_id}")
        resp.raise_for_status()
        return resp.json()

    def unpause_dag(self, dag_id: str) -> dict:
        resp = self.client.patch(
            f"/api/v2/dags/{dag_id}",
            json={"is_paused": False},
        )
        resp.raise_for_status()
        return resp.json()

    def trigger_dag(self, dag_id: str) -> dict:
        # Use current UTC time; each trigger must have a unique logical_date
        logical_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        resp = self.client.post(
            f"/api/v2/dags/{dag_id}/dagRuns",
            json={"logical_date": logical_date},
        )
        resp.raise_for_status()
        return resp.json()

    def get_dag_run(self, dag_id: str, run_id: str) -> dict:
        resp = self.client.get(f"/api/v2/dags/{dag_id}/dagRuns/{run_id}")
        resp.raise_for_status()
        return resp.json()

    def get_task_instances(self, dag_id: str, run_id: str) -> dict:
        resp = self.client.get(
            f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances"
        )
        resp.raise_for_status()
        return resp.json()

    def get_task_logs(
        self, dag_id: str, run_id: str, task_id: str, try_number: int = 1
    ) -> str:
        resp = self.client.get(
            f"/api/v2/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}",
            headers={"Accept": "text/plain"},
        )
        # Don't raise — logs may not be available
        if resp.status_code == 200:
            return resp.text
        return f"[No logs available: HTTP {resp.status_code}]"

    def wait_for_dag_run(
        self, dag_id: str, run_id: str, timeout: int = 60, poll_interval: float = 3
    ) -> dict:
        """Poll until the DAG run reaches a terminal state or timeout."""
        deadline = time.time() + timeout
        last_state = None

        while time.time() < deadline:
            dag_run = self.get_dag_run(dag_id, run_id)
            state = dag_run.get("state")
            last_state = state
            if state in ("success", "failed"):
                return dag_run
            time.sleep(poll_interval)

        # Timeout — diagnose
        diagnosis = self.diagnose_timeout(dag_id, run_id)
        raise TimeoutError(
            f"DAG run {dag_id}/{run_id} did not complete within {timeout}s. "
            f"Last state: {last_state}\n\n{diagnosis}"
        )

    def diagnose_timeout(self, dag_id: str, run_id: str) -> str:
        """Collect task instance states and logs for non-success tasks."""
        lines = ["=== DAG Run Timeout Diagnosis ==="]
        try:
            ti_data = self.get_task_instances(dag_id, run_id)
            task_instances = ti_data.get("task_instances", [])
            for ti in task_instances:
                task_id = ti.get("task_id", "?")
                state = ti.get("state", "?")
                lines.append(f"  Task: {task_id} — State: {state}")
                if state not in ("success",):
                    try_number = ti.get("try_number", 1)
                    log_text = self.get_task_logs(
                        dag_id, run_id, task_id, try_number
                    )
                    # Truncate long logs
                    if len(log_text) > 2000:
                        log_text = log_text[-2000:]
                    lines.append(f"    Log (last 2000 chars): {log_text}")
        except Exception as exc:
            lines.append(f"  [Error fetching diagnostics: {exc}]")
        return "\n".join(lines)
