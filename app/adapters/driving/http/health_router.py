"""
Health check endpoint for application status verification.
"""

from typing import Any

from fastapi import APIRouter, Request

from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=dict[str, Any])
async def health_check(request: Request) -> dict[str, Any]:
    """
    Verifica a saúde da aplicação e retorna informações de status.

    Args:
        request: Objeto da requisição HTTP para acessar run_id.

    Returns:
        Dicionário com status de saúde da aplicação.
    """
    run_id = getattr(request.state, "run_id", None)

    logger.info("health_check_called", run_id=run_id)

    return {
        "status": "healthy",
        "message": "Application is running",
        "run_id": run_id,
    }
