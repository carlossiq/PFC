"""
Endpoint de inferência estatística: enriquece o compilado de uma busca final
(OPS ou Scopus, ver /chat/final/search) pedindo mais iterações até a amostra
saturar (Chao1) ou o tempo configurado acabar, e resume o resultado em
top-10 (com estabilidade de ranking via bootstrap) + relevância semântica
(SBERT) com o tema da pesquisa.

Não persiste nada - rota puramente computacional, mesmo espírito de
/chat/final/search.
"""

from fastapi import APIRouter, Request

from app.core.services.statistical_inference_service import StatisticalInferenceService
from core.logging import get_logger
from schemas.inference import StatisticalInferenceRequest, StatisticalInferenceResponse
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/inference", tags=["inference"])


def _svc(request: Request) -> StatisticalInferenceService:
    return request.app.state.container["services"]["inference"]


@router.post("/final-search", response_model=SuccessResponse[StatisticalInferenceResponse])
async def infer_final_search(
    payload: StatisticalInferenceRequest,
    request: Request,
) -> SuccessResponse[StatisticalInferenceResponse]:
    result = await _svc(request).run(
        api=payload.api,
        query=payload.query,
        final_search_result=payload.final_search_result,
        theme=payload.theme,
    )

    logger.info(
        "statistical_inference_requested",
        api=payload.api,
        success=result.get("success"),
        iterations_used=result.get("iterations_used"),
        stopped_reason=result.get("stopped_reason"),
    )

    if not result.get("success"):
        return SuccessResponse(success=False, data=None, message=result.get("error"))

    return SuccessResponse(success=True, data=StatisticalInferenceResponse(**result))
