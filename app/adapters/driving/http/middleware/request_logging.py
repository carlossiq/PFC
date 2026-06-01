"""
Request logging middleware for tracking HTTP requests with structured logging.
"""

import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.logging import get_logger

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware que adiciona rastreamento de requisições HTTP com run_id único.

    Cada requisição recebe um identificador único (run_id) e logs estruturados
    com informações de duração, status e contexto.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        run_id = str(uuid.uuid4())
        request.state.run_id = run_id

        method = request.method
        path = request.url.path
        query_string = request.url.query if request.url.query else None

        start_time = time.time()
        logger.info(
            "request_started",
            run_id=run_id,
            method=method,
            path=path,
            query_string=query_string,
            client_host=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "request_completed",
                run_id=run_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            response.headers["X-Run-Id"] = run_id
            return response

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                "request_failed",
                run_id=run_id,
                method=method,
                path=path,
                duration_ms=round(duration_ms, 2),
                error=str(exc),
                error_type=type(exc).__name__,
            )

            raise
