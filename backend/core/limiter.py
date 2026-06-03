from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings


def _key_func(request):
    key = request.headers.get("X-API-Key", "")
    if key:
        return f"api_key:{key[:20]}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    default_limits=[settings.rate_limit],
    enabled=settings.environment != "test",
)
