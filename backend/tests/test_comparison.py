import uuid
from uuid import uuid4

import pytest

from core.database import SessionLocal
from core.models import Intake, Job

from tests.conftest import auth_headers, get_test_workshop_id


def _seed_two_jobs():
    workshop_id = get_test_workshop_id()
    db = SessionLocal()
    try:
        intake = Intake(workshop_id=uuid.UUID(workshop_id))
        db.add(intake)
        db.flush()

        job_a = Job(
            intake_id=intake.id,
            status="completed",
            result={
                "vehicle_classification": {"type": "three_wheeler"},
                "confidence_score": 0.85,
                "compliance_state": "pass",
                "feasibility_score": 72,
                "feasibility_label": "feasible_with_adaptation",
                "risk_summary": {"system_risk_state": "elevated", "critical_count": 1, "high_count": 2, "medium_count": 3, "low_count": 4},
                "deviation_result": {"deviation_score": 65, "deviation_certainty": 0.8, "salvage_potential": 70},
                "deviation_summary": {"top_issues": ["Frame misalignment detected"]},
                "recommendations": [{"title": "Reinforce frame"}],
                "degradations": [],
            },
        )
        job_b = Job(
            intake_id=intake.id,
            status="completed",
            result={
                "vehicle_classification": {"type": "four_wheeler"},
                "confidence_score": 0.72,
                "compliance_state": "pass_with_caveats",
                "feasibility_score": 45,
                "feasibility_label": "feasible_with_adaptation",
                "risk_summary": {"system_risk_state": "high", "critical_count": 2, "high_count": 3, "medium_count": 1, "low_count": 0},
                "deviation_result": {"deviation_score": 40, "deviation_certainty": 0.9, "salvage_potential": 55},
                "deviation_summary": {"top_issues": ["Battery bay undersized", "Wiring harness clearance"]},
                "recommendations": [{"title": "Enlarge battery bay"}, {"title": "Reroute harness"}],
                "degradations": [{"service": "cv_model", "message": "Model degraded"}],
            },
        )
        db.add(job_a)
        db.add(job_b)
        db.commit()
        return str(job_a.id), str(job_b.id)
    finally:
        db.close()


def test_comparison_requires_at_least_two(auth_client):
    resp = auth_client.get("/api/v1/comparison?job_ids=" + str(uuid4()))
    assert resp.status_code == 400


def test_comparison_returns_comparison(auth_client):
    id_a, id_b = _seed_two_jobs()
    resp = auth_client.get(f"/api/v1/comparison?job_ids={id_a},{id_b}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["jobs"]) == 2
    types = [j["vehicle_type"] for j in body["jobs"]]
    assert "three_wheeler" in types
    assert "four_wheeler" in types


def test_comparison_risk_counts(auth_client):
    id_a, id_b = _seed_two_jobs()
    resp = auth_client.get(f"/api/v1/comparison?job_ids={id_a},{id_b}")
    body = resp.json()
    for j in body["jobs"]:
        rc = j["risk_counts"]
        assert "critical" in rc
        assert "high" in rc


def test_comparison_rejects_more_than_six(auth_client):
    resp = auth_client.get("/api/v1/comparison?job_ids=" + ",".join(str(uuid4()) for _ in range(7)))
    assert resp.status_code == 400


def teardown_module():
    pass
