import uuid
from unittest.mock import patch

from core.database import SessionLocal
from core.models import Intake
from tests.conftest import get_test_workshop_id
from tests.synthetic_images import generate_views


def _create_intake(db, image_paths: dict[str, str]) -> Intake:
    intake_id = uuid.uuid4()
    intake = Intake(
        id=intake_id,
        workshop_id=uuid.UUID(get_test_workshop_id()),
        view_slots=image_paths,
        attempts={k: 1 for k in image_paths},
        quality_scores={k: 80.0 for k in image_paths},
        low_quality_views=[],
        swap_detected=False,
        status="ready",
    )
    db.add(intake)
    db.commit()
    return intake


MOCK_CLASSIFICATION = {
    "vehicle_type": "three_wheeler",
    "confidence": 0.82,
    "alternatives": [
        {"type": "four_wheeler", "confidence": 0.12},
        {"type": "motorcycle", "confidence": 0.04},
        {"type": "unknown", "confidence": 0.02},
    ],
    "human_confirmed": False,
    "model_loaded": True,
    "classifier_used": "heuristic",
}


class TestIdentifyVehicleAuth:
    def test_requires_auth(self, client):
        resp = client.post(
            "/api/v1/intake/00000000-0000-0000-0000-000000000000/identify-vehicle"
        )
        assert resp.status_code == 401

    def test_404_for_missing_intake(self, auth_client):
        resp = auth_client.post(
            "/api/v1/intake/00000000-0000-0000-0000-000000000000/identify-vehicle"
        )
        assert resp.status_code == 404


class TestIdentifyVehicle:
    @patch("ai.classification.classifier.VehicleClassifier")
    def test_returns_classification(self, mock_cls, auth_client, tmp_path):
        mock_instance = mock_cls.return_value
        mock_instance.classify.return_value = MOCK_CLASSIFICATION

        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            resp = auth_client.post(
                f"/api/v1/intake/{intake.id}/identify-vehicle"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["intake_id"] == str(intake.id)
            assert data["classification"]["vehicle_type"] == "three_wheeler"
            assert data["classification"]["confidence"] == 0.82
            assert "suggestions" in data
        finally:
            db.close()

    @patch("ai.classification.classifier.VehicleClassifier")
    def test_suggestions_from_oem(self, mock_cls, auth_client, tmp_path):
        mock_instance = mock_cls.return_value
        mock_instance.classify.return_value = MOCK_CLASSIFICATION

        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            resp = auth_client.post(
                f"/api/v1/intake/{intake.id}/identify-vehicle"
            )
            assert resp.status_code == 200
            data = resp.json()
            # Should have OEM suggestions for three_wheeler type
            assert len(data["suggestions"]) >= 1
            sug = data["suggestions"][0]
            assert "id" in sug
            assert "manufacturer_name" in sug
            assert "model_name" in sug
            assert sug["vehicle_type"] == "three_wheeler"
        finally:
            db.close()

    def test_400_for_no_images(self, auth_client):
        db = SessionLocal()
        try:
            intake = _create_intake(db, {})
            resp = auth_client.post(
                f"/api/v1/intake/{intake.id}/identify-vehicle"
            )
            assert resp.status_code == 400
        finally:
            db.close()

    @patch("ai.classification.classifier.VehicleClassifier")
    def test_empty_suggestions_for_unknown_type(self, mock_cls, auth_client, tmp_path):
        mock_instance = mock_cls.return_value
        mock_instance.classify.return_value = {
            **MOCK_CLASSIFICATION,
            "vehicle_type": "unknown",
        }

        views = generate_views("three_wheeler", str(tmp_path))
        db = SessionLocal()
        try:
            intake = _create_intake(db, views)
            resp = auth_client.post(
                f"/api/v1/intake/{intake.id}/identify-vehicle"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["classification"]["vehicle_type"] == "unknown"
            assert data["suggestions"] == []
        finally:
            db.close()
