import logging
import time
import subprocess
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.logging_config import setup_logging

setup_logging(settings.environment)
logger = structlog.get_logger(__name__)
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402
from slowapi.middleware import SlowAPIMiddleware  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from api.v1.endpoints.admin import router as admin_router  # noqa: E402
from api.v1.endpoints.analytics import router as analytics_router  # noqa: E402
from api.v1.endpoints.auth import router as auth_router  # noqa: E402
from api.v1.endpoints.billing import router as billing_router  # noqa: E402
from api.v1.endpoints.demo import router as demo_router  # noqa: E402
from api.v1.endpoints.health import router as health_router  # noqa: E402
from api.v1.endpoints.history import router as history_router  # noqa: E402
from api.v1.endpoints.intake import router as intake_router  # noqa: E402
from api.v1.endpoints.jobs import router as jobs_router  # noqa: E402
from api.v1.endpoints.comparison import router as comparison_router  # noqa: E402
from api.v1.endpoints.knowledge_graph import router as kg_router  # noqa: E402
from api.v1.endpoints.metrics import router as metrics_router  # noqa: E402
from api.v1.endpoints.reports import router as reports_router  # noqa: E402
from api.v1.endpoints.setup import router as setup_router  # noqa: E402
from api.v1.endpoints.sso_auth import router as sso_router  # noqa: E402
from api.v1.endpoints.training import router as training_router  # noqa: E402
from api.v1.endpoints.user_auth import router as user_auth_router  # noqa: E402
from api.v1.endpoints.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION  # noqa: E402
from api.v2.main import router as v2_router  # noqa: E402
from core.audit import AuditLog  # noqa: E402
from core.auth import seed_demo_workshop  # noqa: E402
from core.database import SessionLocal  # noqa: E402
from core.db_exceptions import db_error_handler  # noqa: E402
from core.limiter import get_tier_from_workshop, limiter  # noqa: E402

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.25,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    db = SessionLocal()
    try:
        seed_demo_workshop(db)
        from seed_data.seed_oem import seed_oem_data
        seed_oem_data(db)
        from ai.classification.seed_clip import seed_clip_embeddings
        seed_clip_embeddings(db)
    finally:
        db.close()
    if settings.admin_api_key:
        import logging
        logging.getLogger(__name__).info(
            "Admin API key: %s", settings.admin_api_key
        )
    from core.feature_flags import FeatureFlagStore
    FeatureFlagStore.init()

    from core.tracing import setup_tracing, instrument_fastapi, instrument_sqlalchemy, instrument_httpx, instrument_redis
    setup_tracing("retromind-api")
    instrument_fastapi(app)
    from core.database import engine
    instrument_sqlalchemy(engine)
    instrument_httpx()
    instrument_redis()
    yield


app = FastAPI(
    title="RetroMind AI API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter

async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    tier = getattr(request.state, "workshop_tier", "guest")
    return JSONResponse(
        status_code=429,
        content={
            "detail": f"Rate limit exceeded for tier '{tier}'. Upgrade at /settings/billing for higher limits.",
        },
        headers={
            "Retry-After": "60",
            "X-RateLimit-Tier": tier,
        },
    )

app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)  # type: ignore[arg-type]
app.add_exception_handler(SQLAlchemyError, db_error_handler)  # type: ignore[arg-type]

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
    )
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.middleware("http")
async def version_middleware(request: Request, call_next):
    accept_version = request.headers.get("Accept-Version", "")
    if accept_version == "2.0" and not request.url.path.startswith("/api/v2/"):
        logger.warning(
            "Client requested Accept-Version: 2.0 but hit v1 endpoint '%s'",
            request.url.path,
        )
    response = await call_next(request)
    if accept_version:
        response.headers["X-API-Version"] = accept_version
        response.headers["X-API-Latest"] = "/api/v2/"
    return response


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    route = request.url.path
    HTTP_REQUESTS_TOTAL.labels(method=request.method, endpoint=route, status=response.status_code).inc()
    HTTP_REQUEST_DURATION.labels(method=request.method, endpoint=route).observe(duration)
    return response


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    api_key = request.headers.get("X-API-Key", "")
    try:
        from core.auth import hash_api_key
        from core.models import Workshop
        db = SessionLocal()
        workshop_id = None
        if api_key:
            key_hash = hash_api_key(api_key)
            workshop = (
                db.query(Workshop)
                .filter(Workshop.api_key_hash == key_hash, Workshop.is_active.is_(True))
                .first()
            )
            if workshop:
                workshop_id = workshop.id
        log = AuditLog(
            workshop_id=workshop_id,
            method=request.method,
            path=request.url.path,
            status_code=str(response.status_code),
            duration_ms=str(duration_ms),
            ip_address=request.client.host if request.client else None,
        )
        db.add(log)
        db.commit()
    except Exception:
        pass
    finally:
        db.close()
    return response


@app.middleware("http")
async def tier_middleware(request: Request, call_next):
    request.state.workshop_tier = "guest"
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        try:
            from core.auth import hash_api_key
            from core.models import Workshop
            from core.database import SessionLocal as _DB
            db = _DB()
            try:
                key_hash = hash_api_key(api_key)
                workshop = (
                    db.query(Workshop)
                    .filter(Workshop.api_key_hash == key_hash, Workshop.is_active.is_(True))
                    .first()
                )
                if workshop:
                    request.state.workshop_tier = get_tier_from_workshop(workshop.tier)
            finally:
                db.close()
        except Exception:
            pass
    response = await call_next(request)
    response.headers["X-RateLimit-Tier"] = request.state.workshop_tier
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SlowAPIMiddleware)

app.include_router(admin_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(sso_router, prefix="/api/v1")
app.include_router(user_auth_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")
app.include_router(intake_router, prefix="/api/v1")
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(comparison_router, prefix="/api/v1")
app.include_router(kg_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(setup_router, prefix="/api/v1")
app.include_router(training_router, prefix="/api/v1")

from optimization.hyperparameter.admin_endpoints import router as optimization_router  # noqa: E402
app.include_router(optimization_router, prefix="/api/v1")

from ai.recommendations.admin_endpoints import router as rl_admin_router  # noqa: E402
app.include_router(rl_admin_router, prefix="/api/v1")

from api.v1.endpoints.cad_export import router as cad_router  # noqa: E402
app.include_router(cad_router, prefix="/api/v1")

from api.v1.endpoints.oem import router as oem_router  # noqa: E402
app.include_router(oem_router, prefix="/api/v1")

app.include_router(v2_router, prefix="/api/v2")

import os
uploads_path = settings.upload_dir
if os.path.isdir(uploads_path):
    app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")
    logger.info("Serving static uploads from %s at /uploads", uploads_path)
