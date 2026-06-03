import uuid
from uuid import uuid4

import pytest

from core.database import SessionLocal
from core.models import Intake, Job

from tests.conftest import auth_headers, get_test_workshop_id


def _seed_jobs():
    workshop_id = get_test_workshop_id()
    db = SessionLocal()
    try:
        intake = Intake(workshop_id=uuid.UUID(workshop_id))
        db.add(intake)
        db.flush()

        for vtype, score in [
            ("three_wheeler", 0.85),
            ("four_wheeler", 0.72),
            ("three_wheeler", 0.91),
        ]:
            devs = [
                {"parameter": "wheelbase", "severity": "high"},
                {"parameter": "ground_clearance", "severity": "medium"},
            ]
            if vtype == "four_wheeler":
                devs.append({"parameter": "track_width", "severity": "low"})

            job = Job(
                intake_id=intake.id,
                status="completed",
                result={
                    "vehicle_classification": {"type": vtype},
                    "confidence_score": score,
                    "risk_summary": {"system_risk_state": "normal"},
                    "compliance_state": "compliant",
                    "deviation_result": {"deviations": devs},
                    "risks": [],
                },
            )
            db.add(job)
        db.commit()
    finally:
        db.close()


def test_empty_graph_returns_empty(auth_client):
    resp = auth_client.get("/api/v1/knowledge-graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes"] == []
    assert body["edges"] == []


def test_graph_with_jobs(auth_client):
    _seed_jobs()
    resp = auth_client.get("/api/v1/knowledge-graph")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["nodes"]) == 3
    assert all(n["type"] in ("three_wheeler", "four_wheeler") for n in body["nodes"])
    edges = body["edges"]
    assert len(edges) > 0
    for e in edges:
        assert isinstance(e["weight"], int)
        assert e["weight"] >= 1


def test_incomplete_jobs_excluded(auth_client):
    workshop_id = get_test_workshop_id()
    db = SessionLocal()
    try:
        intake = Intake(workshop_id=uuid.UUID(workshop_id))
        db.add(intake)
        db.flush()
        job = Job(
            intake_id=intake.id,
            status="queued",
            result={"vehicle_classification": {"type": "motorcycle"}},
        )
        db.add(job)
        db.commit()

        resp = auth_client.get("/api/v1/knowledge-graph")
        types = [n["type"] for n in resp.json()["nodes"]]
        assert "motorcycle" not in types
    finally:
        db.close()


def teardown_module():
    pass
