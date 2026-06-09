import asyncio
import time
from datetime import datetime, timezone

from fastapi import APIRouter

from core.config import settings
from core.degradation import get_degradation_manager

router = APIRouter()

START_TIME = time.time()


def _check_postgres() -> dict:
    start = time.time()
    try:
        import psycopg2
        conn = psycopg2.connect(settings.database_url, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return {"status": "ok", "latency_ms": int((time.time() - start) * 1000)}
    except Exception as e:
        return {"status": "down", "latency_ms": int((time.time() - start) * 1000), "message": str(e)}


def _check_redis() -> dict:
    start = time.time()
    try:
        import redis as redis_lib
        client = redis_lib.from_url(settings.redis_url, socket_connect_timeout=3)
        client.ping()
        info = client.info("memory")
        used_memory = info.get("used_memory_human", "unknown")
        client.close()
        return {"status": "ok", "latency_ms": int((time.time() - start) * 1000), "used_memory": used_memory}
    except Exception as e:
        return {"status": "down", "latency_ms": int((time.time() - start) * 1000), "message": str(e)}


def _check_neo4j() -> dict:
    start = time.time()
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
            connection_acquisition_timeout=3,
        )
        driver.verify_connectivity()
        driver.close()
        return {"status": "ok", "latency_ms": int((time.time() - start) * 1000)}
    except Exception as e:
        return {"status": "down", "latency_ms": int((time.time() - start) * 1000), "message": str(e)}


def _check_queue_depth() -> dict:
    try:
        import redis as redis_lib
        client = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        queue_length = client.llen("default") if client.exists("default") else 0
        failed_length = client.llen("failed") if client.exists("failed") else 0
        client.close()
        return {"status": "ok", "queued": queue_length, "failed": failed_length}
    except Exception as e:
        return {"status": "degraded", "message": str(e)}


def _check_model() -> dict:
    import os
    model_path = settings.ai_model_path
    if model_path and os.path.isfile(model_path):
        size_mb = round(os.path.getsize(model_path) / (1024 * 1024), 1)
        return {"status": "ok", "path": model_path, "size_mb": size_mb}
    return {"status": "not_found", "path": model_path}


async def _check_object_store() -> dict:
    start = time.time()
    try:
        def _sync_check():
            from core.storage import get_storage
            storage = get_storage()
            test_key = f"healthcheck_{time.time()}"
            storage.save(test_key, b"ok")
            data = storage.load(test_key)
            storage.delete(test_key)
            return data
        data = await asyncio.wait_for(asyncio.to_thread(_sync_check), timeout=8)
        if data == b"ok":
            return {"status": "ok", "latency_ms": int((time.time() - start) * 1000)}
        return {"status": "degraded", "message": "read/write mismatch"}
    except asyncio.TimeoutError:
        return {"status": "down", "latency_ms": int((time.time() - start) * 1000), "message": "object store check timed out"}
    except Exception as e:
        return {"status": "down", "latency_ms": int((time.time() - start) * 1000), "message": str(e)}


def _overall_status(checks: dict[str, dict]) -> str:
    down = any(c.get("status") == "down" for c in checks.values())
    degraded = any(c.get("status") == "degraded" for c in checks.values())

    critical = {"postgresql", "redis"}
    critical_down = any(
        checks.get(s, {}).get("status") == "down" for s in critical
    )
    if critical_down:
        return "down"
    if down or degraded:
        return "degraded"
    return "ok"


@router.get("/health")
async def health_check():
    checks = {
        "postgresql": _check_postgres(),
        "redis": _check_redis(),
        "neo4j": _check_neo4j(),
        "queue_depth": _check_queue_depth(),
        "model": _check_model(),
        "object_store": await _check_object_store(),
    }

    deg_mgr = get_degradation_manager()
    overall = _overall_status(checks)

    return {
        "status": overall,
        "uptime_seconds": int(time.time() - START_TIME),
        "checks": checks,
        "degradation_tier": deg_mgr.current_tier(),
        "degradations": deg_mgr.get_degradation_summary(),
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check():
    pg = _check_postgres()
    rd = _check_redis()
    critical_failing = []
    if pg.get("status") == "down":
        critical_failing.append("postgresql")
    if rd.get("status") == "down":
        critical_failing.append("redis")

    if critical_failing:
        return {"status": "not_ready", "failing": critical_failing}
    return {"status": "ok"}
