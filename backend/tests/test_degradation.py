from unittest.mock import Mock

import pytest
from fastapi import Request
from sqlalchemy.exc import OperationalError

from core.db_exceptions import db_error_handler
from core.degradation import DegradationManager, get_degradation_manager, reset_degradation_manager
from core.retry import with_retry


@pytest.fixture(autouse=True)
def _reset_degradation():
    reset_degradation_manager()
    yield
    reset_degradation_manager()


class TestDegradationManager:
    def test_register_and_resolve(self):
        mgr = get_degradation_manager()
        assert mgr.current_tier() == 0
        mgr.register("neo4j", 1, "Connection failed")
        assert mgr.current_tier() == 1
        assert len(mgr.get_degradation_summary()) == 1
        mgr.resolve("neo4j")
        assert mgr.current_tier() == 0
        assert len(mgr.get_degradation_summary()) == 0

    def test_tier_escalation(self):
        mgr = get_degradation_manager()
        mgr.register("onnx_runner", 1, "Model failed")
        assert mgr.current_tier() == 1
        mgr.register("redis", 2, "Redis unavailable")
        assert mgr.current_tier() == 2
        mgr.register("postgres", 3, "PG down")
        assert mgr.current_tier() == 3
        mgr.resolve("postgres")
        assert mgr.current_tier() == 2

    def test_stage_skipping_logic(self):
        mgr = get_degradation_manager()
        assert mgr.should_skip_stage("vehicle_classification") is False
        mgr.register("redis", 2, "Redis unavailable")
        assert mgr.should_skip_stage("vehicle_classification") is True
        assert mgr.should_skip_stage("upload_validation") is False
        assert mgr.should_skip_stage("risk_analysis") is False
        mgr.register("neo4j", 1, "Neo4j degraded")
        # Tier is still 2 (max)
        assert mgr.should_skip_stage("geometry_extraction") is True
        assert mgr.should_skip_stage("digital_twin") is True

    def test_tier_zero_no_skip(self):
        mgr = get_degradation_manager()
        assert mgr.current_tier() == 0
        for stage in DegradationManager.TIER_AI_STAGES:
            assert mgr.should_skip_stage(stage) is False, f"Stage {stage} should not be skipped at tier 0"


class TestRetry:
    def test_retry_success_after_transient_failure(self):
        mock_fn = Mock()
        mock_fn.side_effect = [ConnectionError("transient"), "success"]

        @with_retry(max_attempts=2, delay=0.01)
        def test_func():
            return mock_fn()

        result = test_func()
        assert result == "success"
        assert mock_fn.call_count == 2

    def test_retry_exhaustion_re_raises(self):
        mock_fn = Mock()
        mock_fn.side_effect = TimeoutError("always fails")

        @with_retry(max_attempts=2, delay=0.01)
        def test_func():
            return mock_fn()

        with pytest.raises(TimeoutError):
            test_func()
        assert mock_fn.call_count == 2

    def test_retry_non_retryable_exception_propagates(self):
        @with_retry(max_attempts=2, delay=0.01, retryable_exceptions=(ConnectionError,))
        def test_func():
            raise ValueError("permanent error")

        with pytest.raises(ValueError):
            test_func()


class TestStageTimeout:
    def test_per_stage_timeout(self):
        from workers.assessment import _run_stage_with_timeout

        def slow_func():
            import time
            time.sleep(10)
            return "done"

        success, result = _run_stage_with_timeout(slow_func, "test_stage", 0.05)
        assert success is False
        assert result is None

    def test_per_stage_completes_in_time(self):
        from workers.assessment import _run_stage_with_timeout

        success, result = _run_stage_with_timeout(lambda: "fast_result", "test_stage", 5)
        assert success is True
        assert result == "fast_result"

    def test_per_stage_failure(self):
        from workers.assessment import _run_stage_with_timeout

        def failing_func():
            raise ValueError("something went wrong")

        success, result = _run_stage_with_timeout(failing_func, "test_stage", 5)
        assert success is False
        assert result is None


class TestHealthEndpoint:
    def test_health_reports_degradation(self):
        from api.v1.endpoints.health import health_check

        mgr = get_degradation_manager()
        mgr.register("neo4j", 1, "Connection failed")

        import anyio
        response = anyio.run(health_check)
        assert response["status"] == "degraded"
        assert response["degradation_tier"] == 1
        assert len(response["degradations"]) == 1
        assert response["degradations"][0]["component"] == "neo4j"


class TestDbErrorHandler:
    @pytest.mark.asyncio
    async def test_operational_error_returns_503(self):
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/test"
        exc = OperationalError("statement", "params", "orig")
        response = await db_error_handler(request, exc)
        assert response.status_code == 503
        body = response.body.decode()
        assert "database_unavailable" in body
        assert "temporarily unavailable" in body

    @pytest.mark.asyncio
    async def test_generic_sqla_error_returns_500(self):
        from sqlalchemy.exc import SQLAlchemyError

        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/test"
        exc = SQLAlchemyError("generic error")
        response = await db_error_handler(request, exc)
        assert response.status_code == 500
        body = response.body.decode()
        assert "database_error" in body
