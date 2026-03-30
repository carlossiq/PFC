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
        """
        Processa a requisição e registra logs estruturados.

        Args:
            request: Objeto da requisição HTTP.
            call_next: Função para chamar o próximo middleware/handler.

        Returns:
            Response da aplicação.
        """
        # Gerar run_id único para rastreamento
        run_id = str(uuid.uuid4())
        request.state.run_id = run_id

        # Coletar informações da requisição
        method = request.method
        path = request.url.path
        query_string = request.url.query if request.url.query else None

        # Registrar início da requisição
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
            # Processar requisição
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000

            # Registrar conclusão com sucesso
            logger.info(
                "request_completed",
                run_id=run_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            # Adicionar run_id no header de resposta
            response.headers["X-Run-Id"] = run_id

            return response

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000

            # Registrar erro
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
