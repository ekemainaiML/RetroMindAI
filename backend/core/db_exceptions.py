import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError

logger = logging.getLogger(__name__)


async def db_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    if isinstance(exc, (OperationalError, TimeoutError)):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database temporarily unavailable. Please retry shortly.",
                "error_type": "database_unavailable",
            },
        )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal database error occurred.",
            "error_type": "database_error",
        },
    )
