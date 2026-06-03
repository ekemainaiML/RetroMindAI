import uuid

import pytest
from fastapi.testclient import TestClient

from core.database import SessionLocal
from core.models import Intake, Job

from tests.conftest import auth_headers, get_test_workshop_id


def seed_job(workshop_id: str, status="completed", vehicle_type="three_wheeler"):
    db = SessionLocal()
    try:
        intake_id = uuid.uuid4()
        job_id = uuid.uuid4()

        intake = Intake(
            id=intake_id,
            workshop_id=uuid.UUID(workshop_id),
            view_slots={"left_side_profile": "/test/left.png"},
            attempts={},
            quality_scores={"left_side_profile": 85.0},
            low_quality_views=[],
            swap_detected=False,
            status="ready",
        )
        db.add(intake)

        job = Job(
            id=job_id,
            intake_id=intake_id,
            status=status,
            result={
                "vehicle_classification": {"type": vehicle_type, "confidence": 0.9},
                "compliance_state": "pass",
                "confidence_score": 85,
                "feasibility_label": "feasible",
            },
        )
        db.add(job)
        db.commit()
        return str(job_id)
    finally:
        db.close()


class TestHistory:
    def test_returns_empty_list_when_no_jobs(self, auth_client):
        resp = auth_client.get("/api/v1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_single_job(self, auth_client):
        workshop_id = get_test_workshop_id()
        seed_job(workshop_id)
        resp = auth_client.get("/api/v1/history")
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_item_has_all_required_fields(self, auth_client):
        workshop_id = get_test_workshop_id()
        jid = seed_job(workshop_id)
        resp = auth_client.get("/api/v1/history")
        item = resp.json()["items"][0]
        assert item["job_id"] == jid
        assert item["status"] == "completed"
        assert item["vehicle_type"] == "three_wheeler"
        assert item["compliance_state"] == "pass"
        assert item["confidence_score"] == 85
        assert item["feasibility_label"] == "feasible"
        assert item["view_count"] == 1
        assert item["created_at"] != ""
        assert item["updated_at"] != ""

    def test_items_ordered_by_updated_at_desc(self, auth_client):
        import time
        workshop_id = get_test_workshop_id()
        seed_job(workshop_id, "completed", "three_wheeler")
        time.sleep(0.1)
        seed_job(workshop_id, "failed", "four_wheeler")
        resp = auth_client.get("/api/v1/history")
        items = resp.json()["items"]
        assert items[0]["vehicle_type"] == "four_wheeler"
        assert items[1]["vehicle_type"] == "three_wheeler"

    def test_pagination_limit(self, auth_client):
        workshop_id = get_test_workshop_id()
        for _ in range(5):
            seed_job(workshop_id, "completed", "three_wheeler")
        resp = auth_client.get("/api/v1/history?limit=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5

    def test_pagination_offset(self, auth_client):
        workshop_id = get_test_workshop_id()
        for _ in range(3):
            seed_job(workshop_id, "completed", "three_wheeler")
        resp = auth_client.get("/api/v1/history?limit=1&offset=1")
        data = resp.json()
        assert len(data["items"]) == 1

    def test_handles_job_without_result(self, auth_client):
        workshop_id = get_test_workshop_id()
        db = SessionLocal()
        try:
            intake_id = uuid.uuid4()
            job_id = uuid.uuid4()

            intake = Intake(
                id=intake_id,
                workshop_id=uuid.UUID(workshop_id),
                view_slots={},
                attempts={},
                quality_scores={},
                low_quality_views=[],
                swap_detected=False,
                status="ready",
            )
            db.add(intake)

            job = Job(
                id=job_id,
                intake_id=intake_id,
                status="queued",
                result=None,
            )
            db.add(job)
            db.commit()

            resp = auth_client.get("/api/v1/history")
            data = resp.json()
            item = next(i for i in data["items"] if i["job_id"] == str(job_id))
            assert item["status"] == "queued"
            assert item["vehicle_type"] is None
            assert item["compliance_state"] is None
        finally:
            db.rollback()
            db.close()
