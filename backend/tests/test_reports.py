import uuid
from datetime import datetime, timezone

import pytest

from core.database import SessionLocal
from core.models import Intake, Job

from tests.conftest import auth_headers, get_test_workshop_id


@pytest.fixture
def completed_job_id():
    workshop_id = get_test_workshop_id()
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
            status="completed",
            current_stage=None,
            progress_pct=100,
            completed_stages=["vehicle_classification", "geometry_extraction"],
            missing_stages=[],
            result={
                "assessment_state": "full_confidence",
                "confidence_score": 85,
                "confidence_factors": {"quality": 80, "classification": 90},
                "safety_overrides": [],
                "feasibility_score": 80,
                "feasibility_label": "feasible",
                "vehicle_classification": {
                    "type": "three_wheeler",
                    "confidence": 0.88,
                    "human_confirmed": False,
                    "classifier": "Heuristic",
                    "alternatives": [],
                },
                "deviation_summary": {
                    "anomalies_detected": 1,
                    "severity": "low",
                    "top_issues": ["Minor frame asymmetry"],
                },
                "deviation_result": {
                    "deviation_score": 90,
                    "deviation_certainty": 70,
                    "critical_delamination": False,
                    "salvage_potential": 90,
                    "deviations": [],
                },
                "risk_summary": {
                    "system_risk_state": "normal",
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 1,
                },
                "risks": [],
                "risk_register": [],
                "deviations": [],
                "needs_confirmation": False,
                "compliance_state": "pass",
                "degradations": [],
                "recommendations": [
                    {
                        "title": "Under-Seat Battery",
                        "priority": "essential",
                        "category": "battery_placement",
                        "description": "Mount battery under seat",
                        "blocking": True,
                        "depends_on": [],
                        "cost_estimate": {"min": 38000, "max": 45000},
                    },
                    {
                        "title": "Wiring Harness",
                        "priority": "recommended",
                        "category": "electrical",
                        "description": "Route HV harness",
                        "blocking": False,
                        "depends_on": ["battery_pack"],
                        "cost_estimate": {"min": 3500, "max": 5000},
                    },
                ],
                "estimated_total_cost_inr": 50000,
                "tooling_required": ["Basic tools", "Multimeter"],
                "skill_level_required": "intermediate",
                "estimated_days": 5,
                "digital_twin": {
                    "dimensions": {"length": 3100, "width": 1400},
                    "deviations_3d": [],
                    "retrofit_components": [],
                },
                "similar_retrofits": [
                    {"vehicle_id": "demo-001", "type": "three_wheeler", "confidence": 0.78}
                ],
            },
        )
        db.add(job)
        db.commit()
        yield str(job_id)
    finally:
        db.rollback()
        db.close()


class TestReports:
    def test_get_report_returns_200(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        assert response.status_code == 200

    def test_report_has_13_sections(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        data = response.json()
        assert len(data["sections"]) == 13

    def test_report_contains_metadata(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        data = response.json()
        assert data["job_id"] == completed_job_id
        assert data["report_id"] is not None
        assert data["generated_at"] is not None

    def test_report_section_ids(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        data = response.json()
        expected_ids = [
            "assessment_metadata",
            "vehicle_classification",
            "deviation_summary",
            "confidence_and_risk",
            "compliance_state",
            "recommendations_overview",
            "battery_placement",
            "wiring_guidance",
            "cost_estimation",
            "tooling_and_skills",
            "digital_twin",
            "infrastructure_degradation",
            "retrofit_dna",
        ]
        actual_ids = [s["id"] for s in data["sections"]]
        assert actual_ids == expected_ids

    def test_vehicle_classification_section(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        sections = {s["id"]: s["content"] for s in response.json()["sections"]}
        vc = sections["vehicle_classification"]
        assert vc["type"] == "three_wheeler"
        assert vc["confidence"] == 0.88

    def test_compliance_state_section(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        sections = {s["id"]: s["content"] for s in response.json()["sections"]}
        cs = sections["compliance_state"]
        assert cs["compliance_state"] == "pass"

    def test_cost_estimation_section(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        sections = {s["id"]: s["content"] for s in response.json()["sections"]}
        cost = sections["cost_estimation"]
        assert cost["estimated_total_cost_inr"]["mid"] == 50000

    def test_recommendations_section(self, completed_job_id, auth_client):
        response = auth_client.get(f"/api/v1/reports/{completed_job_id}")
        sections = {s["id"]: s["content"] for s in response.json()["sections"]}
        recs = sections["recommendations_overview"]
        assert recs["total_recommendations"] == 2
        assert recs["essential_count"] == 1

    def test_404_for_nonexistent_job(self, auth_client):
        response = auth_client.get(f"/api/v1/reports/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_400_for_job_without_result(self, auth_client):
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

            response = auth_client.get(f"/api/v1/reports/{job_id}")
            assert response.status_code == 400
        finally:
            db.rollback()
            db.close()
