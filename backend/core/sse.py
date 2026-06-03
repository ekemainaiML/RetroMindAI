import json
import logging

logger = logging.getLogger(__name__)


def publish_job_event(intake_id: str, event_type: str, data: dict) -> None:
    try:
        from redis import Redis
        from core.config import settings
        conn = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        channel = f"job:{intake_id}:events"
        message = json.dumps({"event": event_type, "data": data}, default=str)
        conn.publish(channel, message)
    except Exception:
        logger.exception("Failed to publish job event for intake %s", intake_id)
