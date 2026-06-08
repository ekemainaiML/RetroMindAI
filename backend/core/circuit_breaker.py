import enum
import logging
import time
from functools import wraps

from prometheus_client import Gauge

logger = logging.getLogger(__name__)

circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half-open, 2=open)",
    ["service"],
)

circuit_breaker_failures = Gauge(
    "circuit_breaker_failures",
    "Consecutive failure count",
    ["service"],
)


class CircuitState(enum.IntEnum):
    CLOSED = 0
    HALF_OPEN = 1
    OPEN = 2


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._last_state_change = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_state_change >= self.recovery_timeout:
                self._set_state(CircuitState.HALF_OPEN)
        return self._state

    def _set_state(self, new_state: CircuitState):
        self._state = new_state
        self._last_state_change = time.time()
        circuit_breaker_state.labels(service=self.name).set(int(new_state))
        logger.info(
            "Circuit breaker '%s' state changed to %s",
            self.name, new_state.name,
        )

    def record_success(self):
        self._failure_count = 0
        if self._state != CircuitState.CLOSED:
            self._set_state(CircuitState.CLOSED)
        circuit_breaker_failures.labels(service=self.name).set(0)

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        circuit_breaker_failures.labels(service=self.name).set(self._failure_count)

        if self._failure_count >= self.failure_threshold:
            self._set_state(CircuitState.OPEN)

    def call(self, fn, fallback=None, *args, **kwargs):
        current_state = self.state

        if current_state == CircuitState.OPEN:
            logger.warning("Circuit breaker '%s' is OPEN — failing fast", self.name)
            if fallback:
                return fallback(*args, **kwargs)
            raise CircuitBreakerOpenError(self.name)

        try:
            result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            if current_state == CircuitState.HALF_OPEN:
                self._set_state(CircuitState.OPEN)
            if fallback:
                logger.info("Circuit breaker '%s' calling fallback", self.name)
                return fallback(*args, **kwargs)
            raise

    async def call_async(self, fn, fallback=None, *args, **kwargs):
        current_state = self.state

        if current_state == CircuitState.OPEN:
            logger.warning("Circuit breaker '%s' is OPEN — failing fast", self.name)
            if fallback:
                if hasattr(fallback, "__call__"):
                    result = fallback(*args, **kwargs)
                    if hasattr(result, "__await__"):
                        return await result
                    return result
                return fallback
            raise CircuitBreakerOpenError(self.name)

        try:
            result = await fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure()
            if current_state == CircuitState.HALF_OPEN:
                self._set_state(CircuitState.OPEN)
            if fallback:
                logger.info("Circuit breaker '%s' calling fallback", self.name)
                if hasattr(fallback, "__call__"):
                    result = fallback(*args, **kwargs)
                    if hasattr(result, "__await__"):
                        return await result
                    return result
                return fallback
            raise


class CircuitBreakerOpenError(Exception):
    def __init__(self, service: str):
        self.service = service
        super().__init__(f"Circuit breaker '{service}' is open")


_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    if name not in _breakers:
        _breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _breakers[name]


def circuit_breaker(name: str, fallback=None, **breaker_kwargs):
    def decorator(func):
        cb = get_circuit_breaker(name, **breaker_kwargs)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, fallback=fallback, *args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await cb.call_async(func, fallback=fallback, *args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


def list_circuit_breakers() -> dict[str, dict]:
    return {
        name: {
            "state": cb.state.name,
            "failure_count": cb._failure_count,
            "failure_threshold": cb.failure_threshold,
            "recovery_timeout": cb.recovery_timeout,
        }
        for name, cb in _breakers.items()
    }
