"""
Chat API routes for step-by-step prospecting workflow.

Exposes tools as HTTP endpoints. Later, ChatService will sit in between
to add LLM coordination and multi-turn conversation management.
"""

from typing import Any, Optional

from fastapi import APIRouter, Request

from core.logging import get_logger
from schemas.response import SuccessResponse
from services.tools import pipeline

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/apis", response_model=SuccessResponse[dict[str, Any]])
async def get_available_apis(request: Request) -> SuccessResponse[dict[str, Any]]:
    """
    Lista as APIs de busca disponíveis.

    Returns:
        Lista de APIs e seu status de habilitação.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        apis = await pipeline.list_available_apis()

        logger.info("available_apis_listed", run_id=run_id, apis=list(apis.keys()))

        return SuccessResponse(
            success=True,
            data=apis,
            message="Available APIs listed successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("list_apis_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={},
            message=f"Error listing APIs: {str(exc)}",
            run_id=run_id,
        )


@router.get("/models", response_model=SuccessResponse[dict[str, Any]])
async def get_available_models(request: Request) -> SuccessResponse[dict[str, Any]]:
    """
    Lista os modelos LLM disponíveis.

    Returns:
        Dicionário com modelos e disponibilidade.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        models = await pipeline.list_available_models()

        logger.info("available_models_listed", run_id=run_id)

        return SuccessResponse(
            success=True,
            data=models,
            message="Available models listed successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("list_models_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={},
            message=f"Error listing models: {str(exc)}",
            run_id=run_id,
        )


@router.post("/topics", response_model=SuccessResponse[dict[str, Any]])
async def generate_topics(
    request: Request,
    theme: str,
    description: Optional[str] = None,
    area_of_study: Optional[str] = None,
    keywords: Optional[list[str]] = None,
) -> SuccessResponse[dict[str, Any]]:
    """
    Gera tópicos candidatos para a busca.

    Args:
        theme: Tema principal.
        description: Descrição detalhada (opcional).
        area_of_study: Área de estudo (opcional).
        keywords: Palavras-chave iniciais (opcional).

    Returns:
        Lista de tópicos sugeridos.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.generate_candidate_topics(
            theme=theme,
            description=description,
            area_of_study=area_of_study,
            keywords=keywords,
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message="Topics generated successfully" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("generate_topics_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error generating topics: {str(exc)}",
            run_id=run_id,
        )


@router.post("/probe/query", response_model=SuccessResponse[dict[str, Any]])
async def build_probe_query_endpoint(
    request: Request,
    theme: str,
    keywords: Optional[list[str]] = None,
    api: Optional[str] = None,
) -> SuccessResponse[dict[str, Any]]:
    """
    Constrói query de probe search.

    Args:
        theme: Tema de busca.
        keywords: Palavras-chave (opcional).
        api: API específica (opcional, usa default se não fornecido).

    Returns:
        Query construída pronta para busca.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.build_probe_query(
            theme=theme,
            keywords=keywords,
            api=api,
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message="Probe query built successfully" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("build_probe_query_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error building probe query: {str(exc)}",
            run_id=run_id,
        )


@router.post("/probe/search", response_model=SuccessResponse[dict[str, Any]])
async def run_probe_search_endpoint(
    request: Request,
    query: dict[str, Any],
    api: str,
) -> SuccessResponse[dict[str, Any]]:
    """
    Executa probe search.

    Args:
        query: Query já construída (do /probe/query endpoint).
        api: Nome da API (ops, scopus, lens_patent, lens_scholarly).

    Returns:
        Resultados da busca probe (max 10-25 documentos).
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.run_probe_search(query=query, api=api)

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=f"Probe search completed: {result.get('results_count', 0)} results" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("run_probe_search_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error running probe search: {str(exc)}",
            run_id=run_id,
        )


@router.post("/extract-terms", response_model=SuccessResponse[dict[str, Any]])
async def extract_terms_endpoint(
    request: Request,
    documents: list[dict[str, Any]],
    top_k: int = 20,
) -> SuccessResponse[dict[str, Any]]:
    """
    Extrai termos relevantes de documentos.

    Args:
        documents: Documentos do probe search.
        top_k: Número de termos a extrair (default 20).

    Returns:
        Lista de termos relevantes com scores.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.extract_relevant_terms(documents=documents, top_k=top_k)

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=f"Extracted {result.get('count', 0)} terms" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("extract_terms_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error extracting terms: {str(exc)}",
            run_id=run_id,
        )


@router.post("/final/query", response_model=SuccessResponse[dict[str, Any]])
async def build_final_query_endpoint(
    request: Request,
    theme: str,
    expanded_keywords: Optional[list[str]] = None,
    api: Optional[str] = None,
) -> SuccessResponse[dict[str, Any]]:
    """
    Constrói query final usando termos expandidos.

    Args:
        theme: Tema original.
        expanded_keywords: Keywords expandidas (opcional).
        api: API específica (opcional).

    Returns:
        Query final pronta para busca de produção.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.build_final_query(
            theme=theme,
            expanded_keywords=expanded_keywords,
            api=api,
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message="Final query built successfully" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("build_final_query_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error building final query: {str(exc)}",
            run_id=run_id,
        )


@router.post("/final/search", response_model=SuccessResponse[dict[str, Any]])
async def run_final_search_endpoint(
    request: Request,
    query: dict[str, Any],
    api: str,
    max_results: int = 500,
) -> SuccessResponse[dict[str, Any]]:
    """
    Executa busca final (busca de produção).

    Args:
        query: Query final construída.
        api: Nome da API.
        max_results: Máximo de resultados (default 500).

    Returns:
        Resultados da busca final (até max_results documentos).
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.run_final_search(query=query, api=api, max_results=max_results)

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=f"Final search completed: {result.get('results_count', 0)} results" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("run_final_search_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error running final search: {str(exc)}",
            run_id=run_id,
        )
