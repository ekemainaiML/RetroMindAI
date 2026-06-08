import logging

from core.config import settings

logger = logging.getLogger(__name__)

_tracing_enabled = False


def setup_tracing(service_name: str = "retromind-api"):
    global _tracing_enabled
    if not settings.otel_endpoint:
        logger.info("OTEL_ENDPOINT not set — tracing disabled")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.environment,
        })

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        _tracing_enabled = True
        logger.info("OpenTelemetry tracing enabled, exporting to %s", settings.otel_endpoint)
    except Exception as e:
        logger.warning("Failed to initialize OpenTelemetry: %s", e)


def instrument_fastapi(app):
    if not _tracing_enabled:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI auto-instrumented for tracing")
    except Exception as e:
        logger.warning("Failed to instrument FastAPI: %s", e)


def instrument_sqlalchemy(engine):
    if not _tracing_enabled:
        return
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("SQLAlchemy instrumented for tracing")
    except Exception as e:
        logger.warning("Failed to instrument SQLAlchemy: %s", e)


def instrument_httpx():
    if not _tracing_enabled:
        return
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
        logger.info("httpx instrumented for tracing")
    except Exception as e:
        logger.warning("Failed to instrument httpx: %s", e)


def instrument_redis():
    if not _tracing_enabled:
        return
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.info("Redis instrumented for tracing")
    except Exception as e:
        logger.warning("Failed to instrument Redis: %s", e)


def is_tracing_enabled() -> bool:
    return _tracing_enabled
