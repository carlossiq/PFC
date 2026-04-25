"""
Chat API routes for step-by-step prospecting workflow.

Exposes tools as HTTP endpoints. Later, ChatService will sit in between
to add LLM coordination and multi-turn conversation management.
"""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Request

from core.logging import get_logger
from schemas.intake import InputIntake
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


@router.get("/current-provider", response_model=SuccessResponse[dict[str, Any]])
async def get_current_provider(request: Request) -> SuccessResponse[dict[str, Any]]:
    """
    Retorna o provider e model LLM atualmente em uso.

    Returns:
        Provider (gemini, anthropic, mock), model (versão), e disponibilidade.
        Ex: {
            "provider": "gemini",
            "model": "gemini-2.0-flash-exp",
            "available": true
        }
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.get_current_llm_provider()

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=f"Current LLM provider: {result.get('provider', 'unknown')}" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("get_current_provider_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving current provider: {str(exc)}",
            run_id=run_id,
        )


@router.post("/analyze-query", response_model=SuccessResponse[dict[str, Any]])
async def analyze_query_complexity_endpoint(
    request: Request,
    query: str = Body(..., embed=True),
) -> SuccessResponse[dict[str, Any]]:
    """
    Analisa complexidade de uma query booleana.

    Util para entender por que queries estao falhando.
    Score alto (>70) geralmente significa que a query eh muito complexa para o OPS.

    Args:
        query: Query string a analisar (CQL, SQL, ou expressao booleana).

    Returns:
        Metricas de complexidade com warnings e recomendacoes.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.analyze_query_complexity(query)

        status_msg = (
            f"Query complexity: {result.get('complexity_level')} (Score: {result.get('complexity_score')}/100)"
            if result.get("success")
            else f"Error: {result.get('error')}"
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=status_msg,
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("analyze_query_complexity_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error analyzing query: {str(exc)}",
            run_id=run_id,
        )


@router.get("/ops-token-status", response_model=SuccessResponse[dict[str, Any]])
async def check_ops_token(request: Request) -> SuccessResponse[dict[str, Any]]:
    """
    Verifica o status do token OAuth2 do OPS.

    Útil para debug: mostra se o token é válido, quando expira, etc.
    Tenta renovar automaticamente se expirado.

    Returns:
        Status do token com campos:
        - is_valid: Token é válido
        - is_expired: Token expirou
        - access_token: Token (truncado por segurança)
        - created_at: Data/hora de criação
        - expiration_time: Data/hora de expiração
        - time_until_expiration_seconds: Segundos até expiração
        - expires_in_seconds: Duração total do token em segundos
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.check_ops_token_status()

        status_msg = (
            "OPS token is valid"
            if result.get("success") and result.get("is_valid")
            else "OPS token is expired or invalid"
            if result.get("success")
            else f"Error: {result.get('error')}"
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=status_msg,
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("check_ops_token_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error checking OPS token: {str(exc)}",
            run_id=run_id,
        )


@router.post("/refine-topic", response_model=SuccessResponse[dict[str, Any]])
async def refine_topic(
    request: Request,
    intake: InputIntake,
) -> SuccessResponse[dict[str, Any]]:
    """
    Refina e especifica o tema fornecido em 4 variações mais focadas.

    A LLM analisa os parâmetros genéricos e sugere 4 tópicos mais específicos,
    preenchendo todos os campos (theme, description, area_of_study, keywords)
    para cada variação.

    Args:
        intake: Objeto com theme (obrigatório), description, area_of_study, keywords.

    Returns:
        Lista de 4 tópicos refinados, cada um com campos completos.
        Os campos fornecidos pelo usuário são incluídos em cada candidato.
        Ex: {
            "candidates": [
                {
                    "theme": "Deep Learning for Medical Image Analysis",
                    "description": "...",
                    "area_of_study": "...",
                    "keywords": [...],
                    "user_input": { campos originais do usuário }
                },
                ...
            ]
        }
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.generate_candidate_topics(intake)

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message="Topic refined successfully with 4 specific variations" if result.get("success") else f"Error: {result.get('error')}",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("refine_topic_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error refining topic: {str(exc)}",
            run_id=run_id,
        )


@router.post("/probe/query", response_model=SuccessResponse[dict[str, Any]])
async def build_probe_query_endpoint(
    request: Request,
    intake: InputIntake,
    api: str = "ops",
) -> SuccessResponse[dict[str, Any]]:
    """
    Constrói query de probe search.

    Args:
        intake: Objeto com theme (obrigatório), description, area_of_study, keywords.
        api: API específica (default: ops).

    Returns:
        Query construída pronta para busca.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.build_probe_query(intake, api)

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
    query: dict[str, Any] = Body(...),
    api: str = Body(...),
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
    documents: list[dict[str, Any]] = Body(...),
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
    intake: InputIntake,
    api: str = "ops",
) -> SuccessResponse[dict[str, Any]]:
    """
    Constrói query final usando termos expandidos.

    Args:
        intake: Objeto com theme (obrigatório), description, area_of_study, keywords.
        api: API específica (default: ops).

    Returns:
        Query final pronta para busca de produção.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.build_final_query(intake, api)

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


@router.get("/system-prompt", response_model=SuccessResponse[dict[str, Any]])
async def get_system_prompt(request: Request) -> SuccessResponse[dict[str, Any]]:
    """
    Retorna o system prompt atual para copiar/colar no Open WebUI.

    Returns:
        Conteúdo completo do system prompt.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        prompt_path = Path(__file__).parent.parent.parent / "prompts" / "system_prompt.md"

        if not prompt_path.exists():
            return SuccessResponse(
                success=False,
                data={},
                message="System prompt file not found",
                run_id=run_id,
            )

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()

        return SuccessResponse(
            success=True,
            data={
                "content": prompt_content,
                "file": str(prompt_path),
                "size_bytes": len(prompt_content),
                "instructions": "Cole este conteúdo em: Open WebUI → Settings → System Prompt"
            },
            message="System prompt retrieved successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("get_system_prompt_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving system prompt: {str(exc)}",
            run_id=run_id,
        )


@router.post("/final/search", response_model=SuccessResponse[dict[str, Any]])
async def run_final_search_endpoint(
    request: Request,
    query: dict[str, Any] = Body(...),
    api: str = Body(...),
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
