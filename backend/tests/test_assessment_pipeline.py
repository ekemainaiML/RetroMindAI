import uuid

import pytest
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import Intake
from tests.conftest import get_test_workshop_id
from tests.synthetic_images import generate_views
from workers.assessment import _build_result, _compute_factors


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_intake(
    db: Session,
    image_paths: dict[str, str],
    swap_detected: bool = False,
    low_quality: list[str] | None = None,
) -> Intake:
    intake_id = uuid.uuid4()
    intake = Intake(
        id=intake_id,
        workshop_id=uuid.UUID(get_test_workshop_id()),
        view_slots=image_paths,
        attempts={k: 1 for k in image_paths},
        quality_scores={k: 80.0 for k in image_paths},
        low_quality_views=low_quality or [],
        swap_detected=swap_detected,
        status="ready",
    )
    db.add(intake)
    db.commit()
    return intake


class TestComputeFactors:
    def test_three_wheeler_all_views(self, tmp_path):
        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            assert factors["completeness"] == 100.0
            assert factors["quality"] == 100.0
            assert factors["classification"] > 0
            assert factors["geometry"] >= 0
            assert factors["deviation_certainty"] >= 0
            assert len(missing) == 0
            assert class_res is not None
            assert class_res["vehicle_type"] == "three_wheeler"
            assert geo_res is not None
            assert geo_res["geometry_score"] >= 0
        finally:
            db.rollback()
            db.close()

    def test_four_wheeler_all_views(self, tmp_path):
        views = generate_views("four_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            assert factors["completeness"] == 100.0
            assert factors["classification"] > 0
            assert class_res is not None
            assert class_res["vehicle_type"] == "four_wheeler"
            assert geo_res is not None
            assert geo_res["geometry_score"] >= 0
        finally:
            db.rollback()
            db.close()

    def test_motorcycle_all_views(self, tmp_path):
        views = generate_views("motorcycle", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            assert factors["completeness"] == 100.0
            assert class_res is not None
            assert class_res["vehicle_type"] == "motorcycle"
        finally:
            db.rollback()
            db.close()

    def test_missing_two_views_reduces_completeness(self, tmp_path):
        views = generate_views("three_wheeler", str(tmp_path))
        partial_views = {"left_side_profile": views["left_side_profile"]}
        db = SessionLocal()
        try:
            intake = _create_intake(db, partial_views)
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            assert factors["completeness"] == pytest.approx(33.33, rel=0.1)
            assert len(missing) == 2
        finally:
            db.rollback()
            db.close()

    def test_low_quality_views_reduces_quality(self, tmp_path):
        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views, low_quality=["left_side_profile"])
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            assert factors["quality"] == 67.0
            assert len(low_quality) == 1
        finally:
            db.rollback()
            db.close()

    def test_swap_detected_passes_through(self, tmp_path):
        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views, swap_detected=True)
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            assert intake.swap_detected is True
        finally:
            db.rollback()
            db.close()

    def test_no_images_returns_default_factors(self, tmp_path):
        db = SessionLocal()
        try:
            intake = _create_intake(db, {})
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            assert factors["completeness"] == 0.0
            assert factors["classification"] == 85.0
            assert factors["geometry"] == 70.0
            assert class_res is None
            assert geo_res is None
            assert dev_res is None
        finally:
            db.rollback()
            db.close()


class TestBuildResult:
    def test_build_result_has_required_fields(self, tmp_path):
        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            risks = []
            risk_state = "normal"
            score = sum(factors.values()) / len(factors)
            state = "full_confidence"

            result = _build_result(
                factors=factors,
                score=score,
                state=state,
                override_reasons=[],
                risks=risks,
                risk_state=risk_state,
                intake=intake,
                classification_result=class_res,
                geometry_result=geo_res,
                deviation_result=dev_res,
            )

            assert result["assessment_state"] == state
            assert "confidence_score" in result
            assert "confidence_factors" in result
            assert "feasibility_score" in result
            assert "feasibility_label" in result
            assert "vehicle_classification" in result
            assert "deviation_summary" in result
            assert "risk_summary" in result
            assert "risks" in result
            assert "risk_register" in result
            assert "deviations" in result
            assert "needs_confirmation" in result
            assert "compliance_state" in result
            assert "degradations" in result
            assert result["compliance_state"] in (
                "pass", "pass_with_caveats", "fail", "insufficient_evidence"
            )
        finally:
            db.rollback()
            db.close()

    def test_build_result_with_deviations(self, tmp_path):
        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            factors, missing, low_quality, class_res, geo_res, dev_res = (
                _compute_factors(intake)
            )

            result = _build_result(
                factors=factors,
                score=70.0,
                state="reduced_confidence",
                override_reasons=["Test override"],
                risks=[{"severity": "high", "category": "test", "message": "Test"}],
                risk_state="elevated",
                intake=intake,
                classification_result=class_res,
                geometry_result=geo_res,
                deviation_result=dev_res,
            )

            assert result["assessment_state"] == "reduced_confidence"
            assert result["safety_overrides"] == ["Test override"]
            assert result["risk_summary"]["system_risk_state"] == "elevated"
            assert result["risk_summary"]["high_count"] == 1
        finally:
            db.rollback()
            db.close()

    def test_build_result_degradations_tier3(self, tmp_path):
        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            facts = {"completeness": 100.0, "quality": 100.0, "visibility": 100.0,
                     "classification": 85.0, "geometry": 70.0, "deviation_certainty": 65.0}

            result = _build_result(
                factors=facts,
                score=80.0,
                state="full_confidence",
                override_reasons=[],
                risks=[],
                risk_state="normal",
                intake=intake,
                degradations=[{"service": "neo4j", "tier": 3, "severity": "high"}],
            )

            assert result["assessment_state"] == "inconclusive"
            assert result["confidence_score"] == 0
            assert len(result["degradations"]) == 1
        finally:
            db.rollback()
            db.close()
