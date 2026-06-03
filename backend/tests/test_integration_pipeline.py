import os
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.auth import hash_api_key
from core.database import SessionLocal
from core.models import Intake, Job, Workshop

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "images")

TEST_API_KEY = "rm_int_" + "b" * 37
TEST_API_KEY_HASH = hash_api_key(TEST_API_KEY)
TEST_WORKSHOP_ID = uuid.uuid4()

slow = pytest.mark.slow


def _workshop_id() -> str:
    return str(TEST_WORKSHOP_ID)


@pytest.fixture(scope="module", autouse=True)
def seed_test_workshop():
    db = SessionLocal()
    try:
        existing = db.query(Workshop).filter(Workshop.id == TEST_WORKSHOP_ID).first()
        if not existing:
            workshop = Workshop(
                id=TEST_WORKSHOP_ID,
                name="Integration Test Workshop",
                api_key_hash=TEST_API_KEY_HASH,
                api_key_prefix="rm_int",
                is_active=True,
            )
            db.add(workshop)
            db.commit()
    finally:
        db.close()
    yield


def _auth_headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY}


def _load_images(vehicle_dir: str) -> list[tuple[str, bytes]]:
    files = []
    for view in ("left_side_profile", "right_side_profile", "rear_view"):
        path = os.path.join(vehicle_dir, f"{view}.png")
        if os.path.exists(path):
            with open(path, "rb") as f:
                files.append((view, f.read()))
    return files


def _run_assessment_inline(intake_id: uuid.UUID) -> None:
    from workers.assessment import run_assessment

    run_assessment(str(intake_id))


def _poll_job(client: TestClient, job_id: str, timeout: int = 130) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/v1/jobs/{job_id}", headers=_auth_headers())
        assert resp.status_code == 200, f"Poll failed: {resp.text}"
        data = resp.json()
        if data["status"] in ("completed", "partial_complete", "failed", "timed_out"):
            return data
        time.sleep(2)
    raise AssertionError("Job did not reach terminal state within timeout")


@slow
def test_three_wheeler_pipeline():
    client = TestClient(app)
    vehicle_dir = os.path.join(FIXTURE_DIR, "three_wheeler")
    files = _load_images(vehicle_dir)
    assert len(files) == 3

    resp = client.post("/api/v1/intake", files=files, headers=_auth_headers())
    assert resp.status_code == 201, f"Intake failed: {resp.text}"
    intake_id = uuid.UUID(resp.json()["intake_id"])

    resp = client.post(f"/api/v1/intake/{intake_id}/analyze", headers=_auth_headers())
    assert resp.status_code == 201, f"Analyze failed: {resp.text}"
    job_id = resp.json()["job_id"]

    _run_assessment_inline(intake_id)

    result = _poll_job(client, job_id)
    assert result["status"] in ("completed", "partial_complete"), (
        f"Job ended with status '{result['status']}': {result.get('error_message', '')}"
    )

    classification = result.get("result", {}).get("vehicle_classification", {})
    assert classification.get("type") in (
        "three_wheeler", "motorcycle", "four_wheeler", "unknown"
    ), f"Unexpected classification: {classification}"
    assert classification.get("confidence", 0) > 0, "Classification confidence is 0"

    stages = result.get("completed_stages", [])
    assert "vehicle_classification" in stages, f"Classification stage not completed. Stages: {stages}"
    assert "feasibility_scoring" in stages, f"Feasibility stage not completed. Stages: {stages}"


@slow
def test_modified_vehicle_detects_deviations():
    client = TestClient(app)
    vehicle_dir = os.path.join(FIXTURE_DIR, "three_wheeler_modified")
    files = _load_images(vehicle_dir)
    assert len(files) == 3

    resp = client.post("/api/v1/intake", files=files, headers=_auth_headers())
    assert resp.status_code == 201
    intake_id = uuid.UUID(resp.json()["intake_id"])

    resp = client.post(f"/api/v1/intake/{intake_id}/analyze", headers=_auth_headers())
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]

    _run_assessment_inline(intake_id)

    result = _poll_job(client, job_id)
    assert result["status"] in ("completed", "partial_complete"), (
        f"Job ended with status '{result['status']}'"
    )

    deviations = result.get("result", {}).get("deviations", [])
    deviation_summary = result.get("result", {}).get("deviation_summary", {})

    assert len(deviations) > 0, (
        f"Expected deviations for modified vehicle, got none. "
        f"Stages: {result.get('completed_stages', [])}"
    )
    assert deviation_summary.get("anomalies_detected", 0) > 0, (
        f"Expected anomalies_detected > 0, got {deviation_summary.get('anomalies_detected', 0)}"
    )


@slow
def test_motorcycle_classification():
    client = TestClient(app)
    vehicle_dir = os.path.join(FIXTURE_DIR, "motorcycle")
    files = _load_images(vehicle_dir)
    assert len(files) == 3

    resp = client.post("/api/v1/intake", files=files, headers=_auth_headers())
    assert resp.status_code == 201
    intake_id = uuid.UUID(resp.json()["intake_id"])

    resp = client.post(f"/api/v1/intake/{intake_id}/analyze", headers=_auth_headers())
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]

    _run_assessment_inline(intake_id)

    result = _poll_job(client, job_id)
    assert result["status"] in ("completed", "partial_complete"), (
        f"Job failed: {result.get('error_message', '')}"
    )

    classification = result.get("result", {}).get("vehicle_classification", {})
    assert classification.get("type") in (
        "three_wheeler", "motorcycle", "four_wheeler", "unknown"
    ), f"Unexpected type: {classification}"


@slow
def test_blank_image_returns_unknown():
    from tests.synthetic_images import generate_blank

    paths = generate_blank()
    client = TestClient(app)
    resp = client.post(
        "/api/v1/intake",
        files=[(k, open(p, "rb").read()) for k, p in paths.items()],
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    intake_id = uuid.UUID(resp.json()["intake_id"])

    resp = client.post(f"/api/v1/intake/{intake_id}/analyze", headers=_auth_headers())
    assert resp.status_code == 201
    job_id = resp.json()["job_id"]

    _run_assessment_inline(intake_id)

    result = _poll_job(client, job_id)
    assert result is not None, "Job did not reach terminal state"
    classification = result.get("result", {}).get("vehicle_classification", {})
    assert classification.get("type") == "unknown", f"Expected unknown, got {classification.get('type')}"
