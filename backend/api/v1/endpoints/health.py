from datetime import datetime, timezone

from fastapi import APIRouter

from core.config import settings
from core.degradation import get_degradation_manager

router = APIRouter()


def _check_postgres() -> str:
    try:
        import psycopg2
        conn = psycopg2.connect(settings.database_url)
        conn.close()
        return "connected"
    except Exception as e:
        return f"error: {e}"


def _check_redis() -> str:
    try:
        import redis as redis_lib
        client = redis_lib.from_url(settings.redis_url, socket_connect_timeout=3)
        client.ping()
        client.close()
        return "connected"
    except Exception as e:
        return f"error: {e}"


def _check_neo4j() -> str:
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        driver.verify_connectivity()
        driver.close()
        return "connected"
    except Exception as e:
        return f"error: {e}"


@router.get("/health")
async def health_check():
    deg_mgr = get_degradation_manager()
    tier = deg_mgr.current_tier()

    if tier == 0:
        status = "ok"
    elif tier <= 2:
        status = "degraded"
    else:
        status = "unavailable"

    return {
        "status": status,
        "services": {
            "postgres": _check_postgres(),
            "redis": _check_redis(),
            "neo4j": _check_neo4j(),
        },
        "degradation_tier": tier,
        "degradations": deg_mgr.get_degradation_summary(),
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
