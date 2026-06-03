import functools
import logging
import time

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts=2, delay=1.0, backoff=2.0, retryable_exceptions=(ConnectionError, TimeoutError)
):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        logger.error(
                            "Retry exhausted for %s after %d attempts",
                            func.__name__,
                            attempt,
                        )
                        raise
                    logger.warning(
                        "Retry %d/%d for %s failed: %s. Retrying in %.1fs",
                        attempt,
                        max_attempts,
                        func.__name__,
                        e,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            raise last_exception

        return wrapper

    return decorator
