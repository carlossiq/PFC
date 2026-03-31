"""
Test routes for debugging and development.

Rotas de teste para visualizar o fluxo do pipeline
e debugar componentes individuais.
"""

from typing import Any
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.config import settings
from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.response import SuccessResponse
from services.llm import LLMServiceFactory, FieldSchemaService, LLMOutputNormalizer
from services.prompt import PromptLoader
from services.query_builders import QueryBuilderFactory
from services.search import LensService

logger = get_logger(__name__)

router = APIRouter(tags=["test"])


class ProbeSearchTestRequest(BaseModel):
    """Requisição para teste de busca probe."""

    theme: str = Field(..., description="Tema/tecnologia para buscar")
    objective: str = Field(
        default="",
        description="Objetivo específico da busca",
    )
    initial_keywords: list[str] = Field(
        default_factory=list,
        description="Palavras-chave iniciais",
    )


class ProbeSearchTestResponse(BaseModel):
    """Resposta do teste de busca probe."""

    run_id: str
    llm_strategy: dict[str, Any]
    query_generated: dict[str, Any]
    api_results: dict[str, Any]
    documents_sample: list[dict[str, Any]]


@router.post("/test/probe-search", response_model=SuccessResponse[ProbeSearchTestResponse])
async def test_probe_search(
    request: ProbeSearchTestRequest,
) -> SuccessResponse[ProbeSearchTestResponse]:
    """
    Rota de teste para visualizar busca probe completa.

    Executa:
    1. Geração de estratégia via LLM
    2. Construção de query
    3. Busca na API Lens Patent
    4. Retorna resultados estruturados

    Args:
        request: Requisição com tema e objetivo.

    Returns:
        Response com LLM output, query gerada e resultados da busca.

    Raises:
        HTTPException: Se alguma etapa falhar.
    """
    run_id = str(uuid.uuid4())

    try:
        logger.info(
            "probe_search_test_started",
            run_id=run_id,
            theme=request.theme,
        )

        # Etapa 1: Criar InputIntake a partir da requisição
        intake = InputIntake(
            theme=request.theme,
            objective=request.objective or request.theme,
            initial_keywords=request.initial_keywords or [request.theme],
        )

        logger.info("probe_search_intake_created", run_id=run_id)

        # Etapa 2: Gerar estratégia via LLM
        llm_service = LLMServiceFactory.get_instance()
        field_schema_service = FieldSchemaService()

        # Carregar prompt para probe
        system_prompt = PromptLoader.load_probe_system_prompt()

        # Obter campos dinâmicos para probe
        probe_fields = field_schema_service.get_fields_for_probe()
        probe_api = getattr(settings, "probe_api", "lens_patent")

        logger.info(
            "probe_search_llm_started",
            run_id=run_id,
            probe_api=probe_api,
        )

        # Processar com LLM
        llm_output = await llm_service.process_intake(
            intake=intake,
            system_prompt=system_prompt,
        )

        # Normalizar saída
        normalized_output = LLMOutputNormalizer.normalize(
            llm_output,
            enabled_fields=probe_fields,
        )

        logger.info(
            "probe_search_llm_completed",
            run_id=run_id,
            active_fields=sum(normalized_output.get_active_fields().values()),
        )

        # Etapa 3: Construir query
        builder = QueryBuilderFactory.create(probe_api, search_mode="probe")
        query = builder.build_query(
            llm_output=normalized_output,
            year_from=getattr(settings, "search_year_from", 2015),
            year_to=getattr(settings, "search_year_to", 2026),
        )

        logger.info(
            "probe_search_query_built",
            run_id=run_id,
            query_size=query.get("size"),
        )

        # Etapa 4: Executar busca
        lens_service = LensService()

        logger.info("probe_search_api_started", run_id=run_id)

        search_result = await lens_service.search_patent(
            query=query,
            run_id=run_id,
        )

        lens_service.close()

        logger.info(
            "probe_search_api_completed",
            run_id=run_id,
            success=search_result.success,
            documents_found=search_result.results_returned,
            total_available=search_result.total_count,
        )

        # Etapa 5: Extrair amostra de documentos
        documents_sample = []
        if search_result.success and search_result.results:
            for doc in search_result.results[:5]:  # Primeiros 5 documentos
                documents_sample.append(
                    {
                        "lens_id": doc.get("lens_id"),
                        "title": _extract_title(doc),
                        "abstract": doc.get("abstract"),
                        "publication_date": doc.get("date_published"),
                        "jurisdiction": doc.get("jurisdiction"),
                        "applicant": _extract_applicant(doc),
                        "inventor": _extract_inventor(doc),
                    }
                )

        # Preparar resposta
        response_data = ProbeSearchTestResponse(
            run_id=run_id,
            llm_strategy={
                "active_fields": normalized_output.get_active_fields(),
                "title": normalized_output.title.model_dump() if not normalized_output.title.is_empty() else None,
                "abstract": normalized_output.abstract.model_dump() if not normalized_output.abstract.is_empty() else None,
                "claims": normalized_output.claims.model_dump() if not normalized_output.claims.is_empty() else None,
                "ipc": normalized_output.ipc.model_dump() if not normalized_output.ipc.is_empty() else None,
                "cpc": normalized_output.cpc.model_dump() if not normalized_output.cpc.is_empty() else None,
            },
            query_generated=query,
            api_results={
                "api": "lens_patent",
                "success": search_result.success,
                "total_available": search_result.total_count,
                "results_returned": search_result.results_returned,
                "duration_seconds": search_result.duration_seconds,
                "error": search_result.error_message if not search_result.success else None,
            },
            documents_sample=documents_sample,
        )

        logger.info(
            "probe_search_test_completed",
            run_id=run_id,
            success=True,
        )

        return SuccessResponse(
            success=True,
            data=response_data,
            message="Probe search test completed successfully",
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(
            "probe_search_test_error",
            error=str(exc),
            error_type=type(exc).__name__,
            run_id=run_id,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Probe search test failed: {str(exc)}",
        )


def _extract_title(doc: dict) -> str:
    """Extrai título do documento."""
    # Lens Patent usa structure aninhada
    biblio = doc.get("biblio", {})
    invention_titles = biblio.get("invention_title", [])
    if invention_titles:
        return invention_titles[0].get("text", "N/A")
    return "N/A"


def _extract_applicant(doc: dict) -> str:
    """Extrai requerente do documento."""
    biblio = doc.get("biblio", {})
    parties = biblio.get("parties", {})
    applicants = parties.get("applicants", [])
    if applicants:
        return applicants[0].get("extracted_name", {}).get("value", "N/A")
    return "N/A"


def _extract_inventor(doc: dict) -> str:
    """Extrai inventor do documento."""
    biblio = doc.get("biblio", {})
    parties = biblio.get("parties", {})
    inventors = parties.get("inventors", [])
    if inventors:
        return inventors[0].get("extracted_name", {}).get("value", "N/A")
    return "N/A"
