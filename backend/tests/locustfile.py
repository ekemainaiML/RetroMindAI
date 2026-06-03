import hashlib
import os
import time
import uuid
from pathlib import Path

from locust import FastHttpUser, between, task

BASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = BASE_DIR / "fixtures" / "images"

API_KEY = os.environ.get("LOCUST_API_KEY", "rm_int_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
BASE_URL = os.environ.get("LOCUST_BASE_URL", "http://localhost:8000")


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


def _load_fixture(vehicle: str) -> list[tuple[str, bytes]]:
    vehicle_dir = FIXTURE_DIR / vehicle
    files = []
    for view in ("left_side_profile", "right_side_profile", "rear_view"):
        path = vehicle_dir / f"{view}.png"
        if path.exists():
            files.append((view, path.read_bytes()))
    return files


class RetroMindUser(FastHttpUser):
    host = BASE_URL
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.intake_ids: list[str] = []
        self.job_ids: list[str] = []

    @task(3)
    def health_check(self):
        with self.rest("GET", "/health", headers=_auth_headers()):
            pass

    @task(2)
    def poll_job(self):
        if not self.job_ids:
            return
        job_id = self.job_ids[-1]
        with self.rest(
            "GET", f"/api/v1/jobs/{job_id}", headers=_auth_headers(), name="/api/v1/jobs/[id]"
        ):
            pass

    @task(1)
    def upload_and_analyze(self):
        files = _load_fixture("three_wheeler")
        if not files:
            return

        with self.rest("POST", "/api/v1/intake", files=files, headers=_auth_headers()) as resp:
            if resp.status_code != 201:
                return
            intake_id = resp.js.get("intake_id")
            if intake_id:
                self.intake_ids.append(intake_id)

        if intake_id:
            with self.rest(
                "POST",
                f"/api/v1/intake/{intake_id}/analyze",
                headers=_auth_headers(),
                name="/api/v1/intake/[id]/analyze",
            ) as resp:
                if resp.status_code == 201:
                    job_id = resp.js.get("job_id")
                    if job_id:
                        self.job_ids.append(job_id)

    @task(1)
    def get_intake(self):
        if not self.intake_ids:
            return
        intake_id = self.intake_ids[-1]
        with self.rest(
            "GET",
            f"/api/v1/intake/{intake_id}",
            headers=_auth_headers(),
            name="/api/v1/intake/[id]",
        ):
            pass
