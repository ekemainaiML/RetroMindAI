from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from fastapi import APIRouter, Response

router = APIRouter()

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

DEMO_ASSESSMENTS_TOTAL = Counter(
    "demo_assessments_total",
    "Total demo assessments launched",
)

JOBS_CREATED_TOTAL = Counter(
    "jobs_created_total",
    "Total jobs created",
)

JOBS_COMPLETED_TOTAL = Counter(
    "jobs_completed_total",
    "Total jobs completed",
    ["status"],
)


@router.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4",
    )
