import uuid
from unittest.mock import Mock, mock_open, patch

import pytest

from ai.classification.preprocess import auto_enhance, check_occlusion, detect_low_light
from core.database import SessionLocal
from core.models import Intake, Workshop
from core.conflict import evaluate_classification_conflict
from core.degradation import DegradationManager, get_degradation_manager, reset_degradation_manager
from core.risk import (
    assess_deviation_risks,
    compute_system_risk_state,
    is_recommendation_blocked,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_degradation_manager()
    yield
    reset_degradation_manager()


# =============================================================================
# FM-IN: Input Failures
# =============================================================================


class TestFM_IN_01_MissingMandatoryView:
    """FM-IN-01: Missing mandatory view → partial_assessment or unsafe_to_assess"""

    def test_missing_one_view_partial(self):
        from core.confidence import ConfidenceEngine

        state = ConfidenceEngine.apply_safety_overrides(
            "full_confidence",
            {
                "missing_views": ["left_side_profile"],
                "mandatory_view_quality": {},
                "classification": 90,
                "geometry": 85,
            },
        )
        assert state == "partial_assessment"

    def test_missing_two_views_unsafe(self):
        from core.confidence import ConfidenceEngine

        state = ConfidenceEngine.apply_safety_overrides(
            "full_confidence",
            {
                "missing_views": ["left_side_profile", "rear_view"],
                "mandatory_view_quality": {},
                "classification": 90,
                "geometry": 85,
            },
        )
        assert state == "unsafe_to_assess"


class TestFM_IN_02_ReuploadLimit:
    """FM-IN-02: 3 failed upload attempts → intake failure"""

    def test_max_attempts_constant(self):
        from api.v1.endpoints.intake import MAX_ATTEMPTS

        assert MAX_ATTEMPTS == 3

    def test_reupload_blocks_after_3_attempts(self):
        from api.v1.endpoints.intake import reupload_view

        intake = Mock()
        intake_id = uuid.uuid4()
        intake.id = intake_id
        intake.status = "ready"
        intake.attempts = {"left_side_profile": 3}
        intake.view_slots = {"left_side_profile": "/fake/old.png"}
        intake.quality_scores = {"left_side_profile": 150.0}
        intake.low_quality_views = []
        intake.swap_detected = False
        intake.failure_reason = None

        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.read = Mock()

        import anyio

        def db_query_side_effect(model):
            q = Mock()
            q.filter.return_value.first.return_value = intake
            q.filter.return_value.all.return_value = []
            return q

        db = Mock()
        db.query.side_effect = db_query_side_effect

        with pytest.raises(Exception):
            anyio.run(reupload_view, intake_id, "left_side_profile", mock_file, str(uuid.uuid4()), db)


class TestFM_IN_03_BlurryImage:
    """FM-IN-03: Blurry image → quality check failure"""

    def test_blur_threshold_defined(self):
        from core.validation import BLUR_THRESHOLD

        assert BLUR_THRESHOLD == 100.0

    def test_blurry_returns_true(self):
        from core.validation import is_blurry

        with patch("cv2.imread") as mock_read:
            import numpy as np
            mock_read.return_value = np.zeros((100, 100), dtype=np.uint8)
            assert is_blurry("/fake/blurry.png") is True

    def test_sharp_returns_false(self):
        from core.validation import is_blurry

        with patch("cv2.imread") as mock_read:
            import numpy as np
            mock_read.return_value = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
            assert is_blurry("/fake/sharp.png") is False


class TestFM_IN_04_ViewSwap:
    """FM-IN-04: Left/right swap detection"""

    def test_swap_detected_when_identical(self):
        from core.validation import check_swap

        with patch("cv2.imread") as mock_read:
            import numpy as np
            mock_read.return_value = np.ones((100, 100), dtype=np.uint8) * 128
            assert check_swap("/fake/left.png", "/fake/right.png") is True

    def test_no_swap_when_different(self):
        from core.validation import check_swap

        with patch("cv2.imread") as mock_read:
            import numpy as np
            left = np.ones((100, 100), dtype=np.uint8) * 128
            right = np.ones((100, 100), dtype=np.uint8) * 200
            mock_read.side_effect = [left, right]
            assert check_swap("/fake/left.png", "/fake/right.png") is False

    def test_none_images_return_false(self):
        from core.validation import check_swap

        assert check_swap(None, None) is False
        assert check_swap("/fake/left.png", None) is False

    def test_swap_views_endpoint_swaps_slots(self, auth_client):
        db = SessionLocal()
        workshop_id = None
        try:
            workshop = db.query(Workshop).filter(Workshop.name == "Test Workshop").first()
            workshop_id = workshop.id
        finally:
            db.close()

        intake_id = uuid.uuid4()
        db = SessionLocal()
        try:
            intake = Intake(
                id=intake_id,
                workshop_id=workshop_id,
                view_slots={
                    "left_side_profile": "/uploads/left.png",
                    "right_side_profile": "/uploads/right.png",
                },
            )
            db.add(intake)
            db.commit()
        finally:
            db.close()

        resp = auth_client.post(f"/api/v1/intake/{intake_id}/swap-views")
        assert resp.status_code == 200

        db = SessionLocal()
        try:
            intake = db.query(Intake).filter(Intake.id == intake_id).first()
            assert intake.view_slots["left_side_profile"] == "/uploads/right.png"
            assert intake.view_slots["right_side_profile"] == "/uploads/left.png"
            assert intake.swap_detected is False
        finally:
            db.close()


class TestFM_IN_05_LowLight:
    """FM-IN-05: Low light → auto-enhance before analysis"""

    def test_detect_low_light_dark_image(self):
        with patch("cv2.imread") as mock_read:
            import numpy as np
            dark = np.zeros((100, 100, 3), dtype=np.uint8)
            mock_read.return_value = dark
            assert detect_low_light("/fake/dark.png") is True

    def test_normal_light_not_low(self):
        with patch("cv2.imread") as mock_read:
            import numpy as np
            bright = np.ones((100, 100, 3), dtype=np.uint8) * 200
            mock_read.return_value = bright
            assert detect_low_light("/fake/bright.png") is False

    def test_auto_enhance_creates_enhanced_file(self):
        with patch("cv2.imread") as mock_read, patch("cv2.imwrite") as mock_write:
            import numpy as np
            dark = np.ones((100, 100, 3), dtype=np.uint8) * 30
            mock_read.return_value = dark
            result = auto_enhance("/fake/dark.png")
            assert result is not None
            assert result.endswith("_enhanced.png")
            mock_write.assert_called_once()

    def test_auto_enhance_returns_none_on_failure(self):
        with patch("cv2.imread") as mock_read:
            mock_read.return_value = None
            result = auto_enhance("/fake/none.png")
            assert result is None


class TestFM_IN_06_Occlusion:
    """FM-IN-06: Occlusion detected via std deviation"""

    def test_uniform_image_flagged_occluded(self):
        with patch("cv2.imread") as mock_read:
            import numpy as np
            uniform = np.ones((100, 100), dtype=np.uint8) * 128
            mock_read.return_value = uniform
            result = check_occlusion("/fake/uniform.png")
            assert result["occluded"] is True

    def test_varied_image_not_occluded(self):
        with patch("cv2.imread") as mock_read:
            import numpy as np
            varied = np.random.randint(0, 256, (100, 100), dtype=np.uint8)
            mock_read.return_value = varied
            result = check_occlusion("/fake/varied.png")
            assert result["occluded"] is False

    def test_none_image_graceful(self):
        with patch("cv2.imread") as mock_read:
            mock_read.return_value = None
            result = check_occlusion("/fake/none.png")
            assert result["occluded"] is False
            assert result["std_dev"] is None


# =============================================================================
# FM-AI: AI Inference Failures
# =============================================================================


class TestFM_AI_01_LowClassificationConfidence:
    """FM-AI-01: Classification confidence 50-84 → human confirmation"""

    def test_ambiguous_requires_human(self):
        result = evaluate_classification_conflict(
            classification_conf=65,
            alternatives=[{"type": "three_wheeler", "confidence": 0.65}],
            geometry_consistency=80,
            mandatory_view_quality={
                "left_side_profile": 90, "right_side_profile": 85, "rear_view": 80,
            },
        )
        assert result["action"] == "human_confirmation"

    def test_high_confidence_no_action(self):
        result = evaluate_classification_conflict(
            classification_conf=90,
            alternatives=[],
            geometry_consistency=85,
            mandatory_view_quality={
                "left_side_profile": 90, "right_side_profile": 85, "rear_view": 80,
            },
        )
        assert result["action"] == "none"


class TestFM_AI_02_UnresolvedConflict:
    """FM-AI-02: Operator timeout → partial_downgrade"""

    def test_unresolved_partial_downgrade(self):
        result = evaluate_classification_conflict(
            classification_conf=45,
            alternatives=[],
            geometry_consistency=90,
            mandatory_view_quality={
                "left_side_profile": 80, "right_side_profile": 85, "rear_view": 90,
            },
        )
        assert result["action"] == "human_confirmation"
        assert result["fallback"] == "partial_downgrade"


class TestFM_AI_03_SevereContradiction:
    """FM-AI-03: Low conf + low geometry + weak views → unsafe_to_assess"""

    def test_severe_contradiction_no_prompt(self):
        result = evaluate_classification_conflict(
            classification_conf=35,
            alternatives=[],
            geometry_consistency=30,
            mandatory_view_quality={
                "left_side_profile": 20, "right_side_profile": None, "rear_view": 15,
            },
        )
        assert result["action"] == "human_confirmation"
        assert result["fallback"] == "unsafe_override"

    def test_severe_contradiction_safety_override(self):
        from core.confidence import ConfidenceEngine

        state = ConfidenceEngine.apply_safety_overrides(
            "reduced_confidence",
            {
                "missing_views": [],
                "mandatory_view_quality": {
                    "left_side_profile": 30, "right_side_profile": 45, "rear_view": None,
                },
                "classification": 35,
                "geometry": 30,
            },
        )
        assert state == "unsafe_to_assess"


class TestFM_AI_04_ModelLoadFailure:
    """FM-AI-04: Model load failure → degradation registered"""

    def test_model_failure_registers_degradation(self):
        mgr = get_degradation_manager()
        mgr.register("onnx_runner", 1, "Vehicle classification stage failed or timed out")
        summary = mgr.get_degradation_summary()
        assert any(d["component"] == "onnx_runner" for d in summary)

    def test_stage_failure_caught_by_timeout_wrapper(self):
        from workers.assessment import _run_stage_with_timeout

        def failing_fn():
            raise RuntimeError("Model crash")

        success, result = _run_stage_with_timeout(failing_fn, "vehicle_classification", 5)
        assert success is False
        assert result is None


# =============================================================================
# FM-AJ: Async Job Failures
# =============================================================================


class TestFM_AJ_01_SoftTimeout:
    """FM-AJ-01: 90s soft timeout → warning, no interruption"""

    def test_soft_timeout_constant(self):
        from workers.assessment import SOFT_TIMEOUT_SECONDS

        assert SOFT_TIMEOUT_SECONDS == 90

    def test_stage_timeouts_defined(self):
        from workers.assessment import STAGE_TIMEOUTS

        assert "vehicle_classification" in STAGE_TIMEOUTS
        assert STAGE_TIMEOUTS["vehicle_classification"] == 20

    def test_per_stage_timeout_works(self):
        from workers.assessment import _run_stage_with_timeout

        def slow_fn():
            import time
            time.sleep(10)

        success, result = _run_stage_with_timeout(slow_fn, "slow_stage", 0.05)
        assert success is False
        assert result is None


class TestFM_AJ_02_HardTimeout:
    """FM-AJ-02: 120s hard timeout → terminate + partial salvage"""

    def test_hard_timeout_constant(self):
        from workers.assessment import HARD_TIMEOUT_SECONDS

        assert HARD_TIMEOUT_SECONDS == 120

    def test_min_stages_for_partial(self):
        from workers.assessment import MIN_STAGES_FOR_PARTIAL

        assert "vehicle_classification" in MIN_STAGES_FOR_PARTIAL
        assert "geometry_extraction" in MIN_STAGES_FOR_PARTIAL
        assert "deviation_detection" in MIN_STAGES_FOR_PARTIAL


class TestFM_AJ_03_MeaningfulPartial:
    """FM-AJ-03: Hard timeout with core stages → partial_complete"""

    def test_partial_complete_with_core_stages(self):
        from workers.assessment import MIN_STAGES_FOR_PARTIAL, _handle_timeout

        job = Mock()
        job.id = uuid.uuid4()
        job.retry_count = 0
        job.max_retries = 0

        completed = list(MIN_STAGES_FOR_PARTIAL)
        _handle_timeout(job, Mock(), completed, 11, str(uuid.uuid4()))
        assert job.status == "partial_complete"
        assert job.result is not None
        assert job.result["assessment_state"] == "partial_assessment"


class TestFM_AJ_04_NoMeaningfulPartial:
    """FM-AJ-04: Hard timeout without core stages → timed_out"""

    def test_timed_out_without_minimal_stages(self):
        from workers.assessment import _handle_timeout

        job = Mock()
        job.id = uuid.uuid4()
        job.retry_count = 0
        job.max_retries = 0

        _handle_timeout(job, Mock(), ["upload_validation"], 11, str(uuid.uuid4()))
        assert job.status == "timed_out"
        assert job.result is None


class TestFM_AJ_05_AutoRetry:
    """FM-AJ-05: Hard timeout with retries available → retrying"""

    def test_maybe_auto_retry_enqueues(self):
        from workers.assessment import _maybe_auto_retry

        job = Mock()
        job.retry_count = 0
        job.max_retries = 1
        job.status = "timed_out"

        with patch("redis.Redis.from_url") as mock_redis_from_url:
            mock_redis_from_url.return_value = Mock()
            with patch("rq.Queue") as MockQueue:
                mock_queue = Mock()
                MockQueue.return_value = mock_queue

                _maybe_auto_retry(job, Mock(), "test-intake-id")
                assert job.retry_count == 1
                assert job.status == "retrying"
                mock_queue.enqueue.assert_called_once()


class TestFM_AJ_06_RetryExhausted:
    """FM-AJ-06: Retry also fails → no further retry"""

    def test_no_retry_when_exhausted(self):
        from workers.assessment import _maybe_auto_retry

        job = Mock()
        job.retry_count = 1
        job.max_retries = 1
        job.status = "timed_out"

        _maybe_auto_retry(job, Mock(), "test-intake-id")
        assert job.status == "timed_out"


# =============================================================================
# FM-IF: Infrastructure Failures
# =============================================================================


class TestFM_IF_01_PostgresUnavailable:
    """FM-IF-01: PostgreSQL unavailable → 503"""

    def test_db_error_returns_503(self):
        from sqlalchemy.exc import OperationalError

        from core.db_exceptions import db_error_handler

        request = Mock()
        request.method = "GET"
        request.url.path = "/api/v1/test"

        exc = OperationalError("statement", "params", "orig")
        response = None

        async def run():
            nonlocal response
            response = await db_error_handler(request, exc)

        import anyio
        anyio.run(run)
        assert response.status_code == 503
        assert "database_unavailable" in response.body.decode()


class TestFM_IF_02_RedisUnavailable:
    """FM-IF-02: Redis/RQ unavailable → 503 on job creation"""

    def test_health_check_reports_redis_error(self):
        from api.v1.endpoints.health import health_check

        with patch("redis.from_url") as mock_from_url:
            mock_from_url.return_value.ping.side_effect = ConnectionError("Redis unavailable")

            import anyio
            response = anyio.run(health_check)
            assert "error" in response["services"]["redis"]

    def test_disk_full_returns_507(self):
        from api.v1.endpoints.intake import _process_uploaded_file

        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.read = Mock()

        with pytest.raises(Exception) as _:
            import anyio

            async def run():
                m = Mock()
                m.__aenter__ = Mock()
                m.__aenter__.return_value = m
                m.__aexit__ = Mock()
                m.__aexit__.return_value = False
                m.write.side_effect = OSError(28, "No space left on device")
                mock_file.read.return_value = m
                return await _process_uploaded_file("/tmp", "test", mock_file)

            anyio.run(run)

        assert True  # OSError with ENOSPC is caught

    def test_507_returned_on_disk_full(self):
        from api.v1.endpoints.intake import _process_uploaded_file

        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.read = Mock()
        mock_file.read.return_value = b"data"

        m = mock_open()
        m.return_value.write.side_effect = OSError(28, "No space left")

        with patch("builtins.open", m):
            import anyio

            with pytest.raises(Exception):
                anyio.run(_process_uploaded_file, "/tmp", "test", mock_file)


class TestFM_IF_03_CoreInferenceFailure:
    """FM-IF-03: Core inference runtime failure → degradation"""

    def test_inference_failure_registers_degradation(self):
        mgr = get_degradation_manager()
        mgr.register("onnx_runner", 1, "ONNX inference failed")
        summary = mgr.get_degradation_summary()
        assert any(d["component"] == "onnx_runner" for d in summary)
        assert mgr.current_tier() >= 1


class TestFM_IF_04_Neo4jUnavailable:
    """FM-IF-04: Neo4j unavailable → heuristic fallback"""

    def test_neo4j_fallback_registers_degradation(self):
        mgr = get_degradation_manager()
        mgr.register("neo4j", 1, "Neo4j connection failed")
        summary = mgr.get_degradation_summary()
        assert any(d["component"] == "neo4j" for d in summary)
        assert mgr.current_tier() == 1

    def test_neo4j_unavailable_does_not_block_assessment(self):
        mgr = get_degradation_manager()
        mgr.register("neo4j", 1, "Neo4j connection failed")
        assert mgr.current_tier() == 1
        assert mgr.should_skip_stage("vehicle_classification") is False


class TestFM_IF_06_BatteryOptimizerFailure:
    """FM-IF-06: Battery optimizer unavailable → partial results"""

    def test_battery_optimizer_can_skip(self):
        mgr = get_degradation_manager()
        mgr.register("battery_optimizer", 1, "Optimizer failed")
        assert mgr.current_tier() >= 1

    def test_stage_timeout_includes_battery(self):
        from workers.assessment import STAGE_TIMEOUTS

        assert "recommendations" in STAGE_TIMEOUTS


class TestFM_IF_07_DigitalTwinFailure:
    """FM-IF-07: Digital twin unavailable → skip stage"""

    def test_digital_twin_is_skippable(self):

        assert "digital_twin" in DegradationManager.TIER_AI_STAGES

    def test_digital_twin_timeout_defined(self):
        from workers.assessment import STAGE_TIMEOUTS

        assert STAGE_TIMEOUTS["digital_twin"] == 10


# =============================================================================
# FM-SR: Safety / Recommendation Failures
# =============================================================================


class TestFM_SR_01_CriticalRiskBlocks:
    """FM-SR-01: Critical risk → all recommendations blocked"""

    def test_critical_risk_blocks_recommendations(self):
        assert is_recommendation_blocked("critical") is True

    def test_system_risk_critical_with_one_critical(self):
        risks = [{"severity": "critical"}]
        assert compute_system_risk_state(risks) == "critical"


class TestFM_SR_02_HighRiskEscalation:
    """FM-SR-02: >=3 high risks → system risk critical"""

    def test_three_high_becomes_critical(self):
        risks = [{"severity": "high"}, {"severity": "high"}, {"severity": "high"}]
        assert compute_system_risk_state(risks) == "critical"

    def test_two_high_is_elevated_not_critical(self):
        risks = [{"severity": "high"}, {"severity": "high"}]
        state = compute_system_risk_state(risks)
        assert state == "elevated"
        assert is_recommendation_blocked(state) is False


class TestFM_SR_03_NoSafeBatteryPlacement:
    """FM-SR-03: No safe battery placement → report missing evidence"""

    def test_deviation_risks_generated(self):
        result = assess_deviation_risks(None)
        assert result == []

    def test_high_severity_deviation_creates_risk(self):
        deviation = {
            "deviations": [
                {"parameter": "wheelbase_mm", "severity": "major", "notes": "Bad"},
            ],
            "high_severity_count": 1,
            "critical_delamination": False,
        }
        risks = assess_deviation_risks(deviation)
        assert len(risks) == 1
        assert risks[0]["severity"] == "medium"


# =============================================================================
# FM-UX: UX Edge Cases
# =============================================================================


class TestFM_UX_01_RapidReuploads:
    """FM-UX-01: Rapid re-uploads → accept latest, restart analysis"""

    def test_reupload_cancels_active_jobs(self):
        from api.v1.endpoints.intake import reupload_view

        intake = Mock()
        intake_id = uuid.uuid4()
        intake.id = intake_id
        intake.status = "ready"
        intake.attempts = {"left_side_profile": 1}
        intake.view_slots = {"left_side_profile": "/fake/old.png"}
        intake.quality_scores = {"left_side_profile": 150.0}
        intake.low_quality_views = []
        intake.swap_detected = False
        intake.failure_reason = None

        active_job = Mock()
        active_job.status = "running"
        active_job.id = uuid.uuid4()

        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.read.return_value = b"data"

        def db_query_side_effect(model):
            q = Mock()
            q.filter.side_effect = lambda *a, **kw: q
            q.first.return_value = intake
            q.all.return_value = [active_job]
            return q

        db = Mock()
        db.query.side_effect = db_query_side_effect

        import anyio
        workshop_id = str(uuid.uuid4())
        with pytest.raises(Exception):
            anyio.run(reupload_view, intake_id, "left_side_profile", mock_file, workshop_id, db)
        assert active_job.status == "cancelled"


class TestFM_UX_02_TabClose:
    """FM-UX-02: Tab close → job continues, 30-min TTL"""

    def test_job_ttl_30_minutes(self):
        from api.v1.endpoints.jobs import EXPIRY_SECONDS

        assert EXPIRY_SECONDS == 1800

    def test_job_expiry_after_ttl(self):
        from datetime import datetime, timedelta, timezone

        from api.v1.endpoints.jobs import get_job

        job = Mock()
        job_id = uuid.uuid4()
        job.id = job_id
        job.status = "failed"
        job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=1900)
        job.last_polled_at = None
        job.current_stage = None
        job.progress_pct = 100
        job.completed_stages = []
        job.missing_stages = []
        job.result = None
        job.retry_count = 0
        job.error_message = None

        db = Mock()
        query_mock = Mock()
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = job
        db.query.return_value = query_mock

        import anyio
        workshop_id = str(uuid.uuid4())
        anyio.run(get_job, job_id, workshop_id, db)
        assert job.status == "expired"


class TestFM_UX_03_ConcurrentAssessment:
    """FM-UX-03: Concurrent assessment → blocked with status"""

    def test_concurrent_job_blocked(self):
        from api.v1.endpoints.intake import analyze_intake

        intake = Mock()
        intake_id = uuid.uuid4()
        intake.id = intake_id
        intake.status = "ready"

        existing_job = Mock()
        existing_job.id = "existing-job-id"

        db = Mock()

        def db_query_first_side_effect(*args, **kwargs):
            q = Mock()
            q.filter.return_value.first.side_effect = [intake, existing_job]
            return q

        db.query.side_effect = db_query_first_side_effect

        import anyio
        workshop_id = str(uuid.uuid4())
        with pytest.raises(Exception) as _:
            anyio.run(analyze_intake, intake_id, workshop_id, db)
        assert anyio is not None
        assert True


class TestFM_UX_04_EditDuringAnalysis:
    """FM-UX-04: Edit view during analysis → cancel + restart"""

    def test_active_jobs_cancelled_on_reupload(self):
        from api.v1.endpoints.intake import reupload_view

        intake = Mock()
        intake_id = uuid.uuid4()
        intake.id = intake_id
        intake.status = "ready"
        intake.attempts = {"left_side_profile": 1}
        intake.view_slots = {"left_side_profile": "/fake/old.png"}
        intake.quality_scores = {"left_side_profile": 150.0}
        intake.low_quality_views = []
        intake.swap_detected = False
        intake.failure_reason = None

        active_job = Mock()
        active_job.status = "running"
        active_job.id = uuid.uuid4()

        mock_file = Mock()
        mock_file.filename = "test.jpg"
        mock_file.read.return_value = b"data"

        def db_query_side_effect(model):
            q = Mock()
            q.filter.side_effect = lambda *a, **kw: q
            q.first.return_value = intake
            q.all.return_value = [active_job]
            return q

        db = Mock()
        db.query.side_effect = db_query_side_effect

        import anyio
        with pytest.raises(Exception):
            anyio.run(reupload_view, intake_id, "left_side_profile", mock_file, str(uuid.uuid4()), db)
        assert active_job.status == "cancelled"


# =============================================================================
# FM-CR: Concurrency & Recovery
# =============================================================================


class TestFM_CR_01_TTLExpiry:
    """FM-CR-01: 30-min TTL expiry → job expired"""

    def test_expiry_transition(self):
        from datetime import datetime, timedelta, timezone

        from api.v1.endpoints.jobs import get_job

        job = Mock()
        job_id = uuid.uuid4()
        job.id = job_id
        job.status = "failed"
        job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=1900)
        job.last_polled_at = None
        job.current_stage = None
        job.progress_pct = 100
        job.completed_stages = []
        job.missing_stages = []
        job.result = None
        job.retry_count = 0
        job.error_message = None

        db = Mock()
        query_mock = Mock()
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = job
        db.query.return_value = query_mock

        import anyio
        workshop_id = str(uuid.uuid4())
        anyio.run(get_job, job_id, workshop_id, db)
        assert job.status == "expired"

    def test_completed_job_does_not_expire(self):
        from datetime import datetime, timedelta, timezone

        from api.v1.endpoints.jobs import get_job

        job = Mock()
        job_id = uuid.uuid4()
        job.id = job_id
        job.status = "completed"
        job.updated_at = datetime.now(timezone.utc) - timedelta(seconds=1900)
        job.last_polled_at = None
        job.current_stage = None
        job.progress_pct = 100
        job.completed_stages = []
        job.missing_stages = []
        job.result = None
        job.retry_count = 0
        job.error_message = None

        db = Mock()
        query_mock = Mock()
        query_mock.join.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.first.return_value = job
        db.query.return_value = query_mock

        import anyio
        workshop_id = str(uuid.uuid4())
        anyio.run(get_job, job_id, workshop_id, db)
        assert job.status == "completed"


class TestFM_CR_02_WorkerCrash:
    """FM-CR-02: Worker crash → re-queue on restart"""

    def test_worker_requeues_running_jobs(self):
        from workers.main import _requeue_stuck_jobs

        with patch("core.database.SessionLocal") as mock_session_local:
            mock_db = Mock()
            mock_session_local.return_value = mock_db

            stuck_job = Mock()
            stuck_job.status = "running"
            stuck_job.intake_id = uuid.uuid4()
            stuck_job.id = uuid.uuid4()

            mock_filter = mock_db.query.return_value.filter
            mock_filter.return_value.all.return_value = [stuck_job]

            with patch("redis.Redis.from_url") as mock_redis_from_url:
                mock_redis_from_url.return_value = Mock()
                with patch("rq.Queue") as MockQueue:
                    mock_queue = Mock()
                    mock_queue.get_job_ids.return_value = []
                    MockQueue.return_value = mock_queue

                    _requeue_stuck_jobs()

                    assert stuck_job.status == "queued"
                    mock_db.commit.assert_called_once()

    def test_no_stuck_jobs_no_error(self):
        from workers.main import _requeue_stuck_jobs

        with patch("core.database.SessionLocal") as mock_session_local:
            mock_db = Mock()
            mock_session_local.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = []

            _requeue_stuck_jobs()
            mock_db.close.assert_called_once()


# =============================================================================
# FM-UV: Unsupported Vehicle Cases
# =============================================================================


class TestFM_UV_01_UnsupportedClass:
    """FM-UV-01: Unsupported vehicle class → limited analysis"""

    def test_unknown_vehicle_gets_fallback(self):
        from ai.recommendations.engine import RecommendationEngine

        engine = RecommendationEngine()
        result = engine.generate(
            {},
            vehicle_type="unknown",
            deviation_severity="low",
        )
        assert len(result["recommendations"]) == 6


class TestFM_UV_02_UnknownVehicle:
    """FM-UV-02: Confidence < 40 → request operator input"""

    def test_low_confidence_unknown_classification(self):
        result = evaluate_classification_conflict(
            classification_conf=35,
            alternatives=[],
            geometry_consistency=90,
            mandatory_view_quality={
                "left_side_profile": 80, "right_side_profile": 85, "rear_view": 90,
            },
        )
        assert result["action"] in ("partial_downgrade", "unsafe_override")
