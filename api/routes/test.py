"""
Test routes for development and debugging.

Exposes internals of each pipeline stage for detailed inspection.
"""

from typing import Any, Optional

from fastapi import APIRouter, Request

from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from schemas.response import SuccessResponse
from services.llm import (
    LLMOutputNormalizer,
    LLMServiceFactory,
    FieldSchemaService,
)
from services.nlp import (
    EmbeddingService,
    KeywordService,
    RelevanceService,
)
from services.prompt import PromptLoader
from services.query_builders import QueryBuilderFactory

logger = get_logger(__name__)

router = APIRouter(prefix="/test", tags=["test"])


@router.post("/llm", response_model=SuccessResponse[dict[str, Any]])
async def test_llm(
    request: Request,
    intake: InputIntake,
    search_mode: str = "general",
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa LLM processing e estratégia inicial.

    Expõe: run_id, prompt, raw response, normalized output.

    Args:
        request: Objeto da requisição.
        intake: Entrada do usuário.
        search_mode: 'probe' ou 'general'.

    Returns:
        Response com detalhes do processamento LLM.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # Carregar prompt
        if search_mode == "probe":
            system_prompt = PromptLoader.load_probe_system_prompt()
        else:
            system_prompt = PromptLoader.load_general_system_prompt()

        # Processar com LLM
        llm_service = LLMServiceFactory.get_instance()
        llm_output = await llm_service.process_intake(
            intake=intake,
            system_prompt=system_prompt,
        )

        # Normalizar
        normalized = LLMOutputNormalizer.normalize(llm_output)

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "search_mode": search_mode,
                "provider": llm_service.provider_name,
                "system_prompt_length": len(system_prompt),
                "intake_theme": intake.theme,
                "active_fields": normalized.get_active_fields(),
                "active_fields_count": sum(normalized.get_active_fields().values()),
                "raw_output_fields": {
                    "title": bool(llm_output.title.groups),
                    "abstract": bool(llm_output.abstract.groups),
                    "claims": bool(llm_output.claims.groups),
                    "ipc": bool(llm_output.ipc.values),
                    "cpc": bool(llm_output.cpc.values),
                },
                "normalized_output_fields": {
                    "title": bool(normalized.title.groups),
                    "abstract": bool(normalized.abstract.groups),
                    "claims": bool(normalized.claims.groups),
                    "ipc": bool(normalized.ipc.values),
                    "cpc": bool(normalized.cpc.values),
                },
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_llm_error: {exc}", run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/nlp", response_model=SuccessResponse[dict[str, Any]])
async def test_nlp(
    request: Request,
    text: str,
    top_k_keywords: int = 10,
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa NLP services (keyword extraction + embeddings).

    Expõe: keywords extraídos, embedding dimensionality.

    Args:
        request: Objeto da requisição.
        text: Texto para processar.
        top_k_keywords: Número de keywords.

    Returns:
        Response com resultados NLP.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # Extrair keywords
        keyword_service = KeywordService()
        keywords = keyword_service.extract_keywords(text, top_k=top_k_keywords)

        # Gerar embedding
        embedding_service = EmbeddingService()
        embedding = embedding_service.embed_text(text)

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "text_length": len(text),
                "keywords_extracted": len(keywords),
                "top_keywords": keywords[:5],
                "embedding_dimension": len(embedding) if embedding is not None else None,
                "embedding_available": embedding is not None,
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_nlp_error: {exc}", run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/query-builder", response_model=SuccessResponse[dict[str, Any]])
async def test_query_builder(
    request: Request,
    api_name: str,
    intake: InputIntake,
    search_mode: str = "general",
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa query builder para uma API.

    Expõe: API usada, modo de busca, query gerada.

    Args:
        request: Objeto da requisição.
        api_name: Nome da API (lens_patent, ops, scopus, etc).
        intake: Entrada do usuário.
        search_mode: 'probe' ou 'general'.

    Returns:
        Response com query gerada.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        # Gerar estratégia LLM
        llm_service = LLMServiceFactory.get_instance()
        system_prompt = PromptLoader.load_general_system_prompt()
        llm_output = await llm_service.process_intake(intake, system_prompt)
        normalized = LLMOutputNormalizer.normalize(llm_output)

        # Construir query
        builder = QueryBuilderFactory.create(api_name, search_mode=search_mode)
        query = builder.build_query(
            llm_output=normalized,
            year_from=2015,
            year_to=2024,
        )

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "api_name": api_name,
                "search_mode": search_mode,
                "builder_class": builder.__class__.__name__,
                "query_type": type(query).__name__,
                "max_query_length": builder.max_query_length,
                "query_length": len(str(query)),
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_query_builder_error: {exc}", run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )


@router.post("/field-schema", response_model=SuccessResponse[dict[str, Any]])
async def test_field_schema(
    request: Request,
    api_name: str,
    search_mode: str = "general",
) -> SuccessResponse[dict[str, Any]]:
    """
    Testa field schema service.

    Expõe: campos textuais, campos simples, campos obrigatórios.

    Args:
        request: Objeto da requisição.
        api_name: Nome da API.
        search_mode: Modo de busca.

    Returns:
        Response com schema de campos.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        field_service = FieldSchemaService()
        contract = field_service.build_llm_output_contract(
            api_name=api_name,
            search_mode=search_mode,
        )

        return SuccessResponse(
            success=True,
            data={
                "run_id": run_id,
                "api": api_name,
                "search_mode": search_mode,
                "textual_fields": len(contract.get("textual_fields", [])),
                "simple_fields": len(contract.get("simple_fields", [])),
                "required_fields": contract.get("required_fields", []),
            },
            run_id=run_id,
        )

    except Exception as exc:
        logger.error(f"test_field_schema_error: {exc}", run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            run_id=run_id,
        )
