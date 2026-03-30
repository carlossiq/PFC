"""
Main intake endpoint for technology prospecting API.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.dependencies import get_db_session
from core.logging import get_logger
from pipeline.orchestrator import PipelineOrchestrator
from schemas.intake import InputIntake
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(tags=["intake"])


@router.post("/intake", response_model=SuccessResponse[dict[str, Any]])
async def create_intake(
    request: Request,
    intake: InputIntake,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    """
    Processa requisição de prospecção tecnológica.

    Executa pipeline completo: estratégia inicial → probe search →
    expansão semântica → busca real → filtragem → deduplicação →
    normalização → persistência.

    Args:
        request: Objeto da requisição HTTP.
        intake: Entrada do usuário com tema, objetivo, keywords.
        session: Sessão de banco de dados.

    Returns:
        Response com resultado da prospecção.

    Raises:
        HTTPException: Se pipeline falhar criticamente.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        logger.info(
            "intake_request_received",
            theme=intake.theme,
            run_id=run_id,
        )

        # Executar pipeline
        orchestrator = PipelineOrchestrator()
        result = await orchestrator.execute(intake, session)

        logger.info(
            "intake_request_completed",
            success=result.success,
            documents_persisted=result.documents_persisted,
            run_id=run_id,
        )

        return SuccessResponse(
            success=result.success,
            data={
                "run_id": result.run_id,
                "statistics": {
                    "documents_found_total": result.documents_found_total,
                    "documents_filtered": result.documents_filtered,
                    "documents_unique": result.documents_unique,
                    "documents_persisted": result.documents_persisted,
                },
                "api_failures": result.api_failures,
                "stages_completed": len([s for s in result.stages if s.success]),
                "total_stages": len(result.stages),
            },
            message="Intake processed successfully" if result.success else "Intake processed with warnings",
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(
            "intake_request_error",
            error=str(exc),
            error_type=type(exc).__name__,
            run_id=run_id,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(exc)}",
        )
