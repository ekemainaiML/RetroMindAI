import logging

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings

logger = logging.getLogger(__name__)

TIER_LIMITS: dict[str, str] = {
    "guest": "100/minute",
    "free": "100/minute",
    "standard": "500/minute",
    "pro": "500/minute",
    "enterprise": "5000/minute",
}

TIER_BURST: dict[str, str] = {
    "guest": "200/10second",
    "free": "200/10second",
    "standard": "1000/10second",
    "pro": "1000/10second",
    "enterprise": "10000/10second",
}


def _key_func(request: Request) -> str:
    key = request.headers.get("X-API-Key", "")
    if key:
        return f"api_key:{key[:20]}"
    return get_remote_address(request)


def _rate_limit_key_func(request: Request) -> str:
    base_key = _key_func(request)
    tier = getattr(request.state, "workshop_tier", "guest")
    return f"{base_key}:{tier}"


limiter = Limiter(
    key_func=_rate_limit_key_func,
    default_limits=["100/minute"],
    enabled=settings.environment != "test",
)


def get_tier_limits(tier: str) -> tuple[str, str]:
    return TIER_LIMITS.get(tier, "100/minute"), TIER_BURST.get(tier, "200/10second")


def get_tier_from_workshop(workshop_tier: str) -> str:
    tier = (workshop_tier or "guest").lower()
    if tier in TIER_LIMITS:
        return tier
    return "guest"
