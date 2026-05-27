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
from schemas.request import (
    FinalSearchRequest,
    ProbeSearchRequest,
    TermExtractionRequest,
)
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
    query: str = Body(
        ...,
        example="(TITLE:(e-commerce OR online shopping) OR ABSTRACT:(digital payment)) AND (IPC:G06Q) AND (PD>=20150101 AND PD<=20261231)",
        embed=True,
        description="Query string a analisar (CQL, SQL, ou expressão booleana)"
    ),
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
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "artificial intelligence",
            "description": "General AI and machine learning applications",
            "area_of_study": "Computer Science",
            "keywords": ["neural networks", "deep learning"]
        }
    ),
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
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "e-commerce and digital payments",
            "description": "Online shopping platforms with secure payment processing",
            "area_of_study": "Information Technology",
            "keywords": ["blockchain", "cryptocurrency", "payment gateway"]
        }
    ),
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
    probe_request: ProbeSearchRequest = Body(...),
) -> SuccessResponse[dict[str, Any]]:
    """
    Executa probe search com abstracts.

    Usa o endpoint /search/abstract do OPS que já retorna abstracts,
    eliminando a necessidade de enriquecimento posterior.

    Args:
        probe_request: Query construída, API a usar e número de resultados.

    Returns:
        Resultados da busca probe com abstracts e dados bibliográficos.
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.run_probe_search(
            query=probe_request.query.model_dump(),
            api=probe_request.api,
            top_k=probe_request.top_k,
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=f"Probe search completed: {result.get('results_count', 0)} results with abstracts" if result.get("success") else f"Error: {result.get('error')}",
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
    extract_request: TermExtractionRequest = Body(...),
) -> SuccessResponse[dict[str, Any]]:
    """
    Extrai termos relevantes de uma lista de items (title + abstract) usando KeyBERT e TF-IDF.

    Processa título e abstract separadamente com pesos configuráveis:
    - Título: peso 3.0 (padrão) - mais específico e relevante
    - Abstract: peso 1.0 (padrão) - mais genérico e contextual

    Combina:
    - KeyBERT: relevância semântica (60%)
    - TF-IDF: importância estatística (40%)
    - Pesos por fonte: título 3x mais importante que abstract

    Remove automaticamente termos presentes nos parâmetros originais.

    Args:
        extract_request: Lista de items com title/abstract, parâmetros originais, e número de termos.

    Returns:
        Lista de termos com scores e fonte:
        {
            "term": "machine learning",
            "score": 2.85,
            "keybert_score_title": 0.92,
            "keybert_score_abstract": 0.85,
            "tf_idf_score_title": 0.88,
            "tf_idf_score_abstract": 0.72,
            "frequency": 5,
            "sources": ["title", "abstract"],
            "title_weight": 3.0,
            "abstract_weight": 1.0
        }
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.extract_relevant_terms(
            items=extract_request.items,
            original_params=extract_request.original_params,
            top_k=extract_request.top_k,
        )

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
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "machine learning for cybersecurity",
            "description": "AI-based intrusion detection and threat prevention",
            "area_of_study": "Computer Science & Security",
            "keywords": ["anomaly detection", "neural networks", "classification"]
        }
    ),
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


@router.post("/final/queries-multi", response_model=SuccessResponse[dict[str, Any]])
async def build_final_queries_endpoint(
    request: Request,
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "quantum computing applications",
            "description": "Quantum algorithms and hardware implementations",
            "area_of_study": "Physics & Computer Science",
            "keywords": ["qubits", "superposition", "entanglement"]
        }
    ),
    extracted_terms: list[dict[str, Any]] = Body(
        default=[],
        example=[
            {
                "term": "quantum gates",
                "score": 0.92,
                "keybert_score": 0.90,
                "tf_idf_score": 0.95,
                "frequency": 8,
                "sources": ["title", "abstract"]
            },
            {
                "term": "quantum error correction",
                "score": 0.88,
                "keybert_score": 0.85,
                "tf_idf_score": 0.92,
                "frequency": 5,
                "sources": ["abstract"]
            }
        ],
        description="Termos extraídos com scores (do /extract-terms endpoint)"
    ),
    api: str = Body("ops", example="ops", description="API específica (ops, scopus, lens_patent, lens_scholarly)"),
) -> SuccessResponse[dict[str, Any]]:
    """
    Constrói 3 variações de query final (specific, balanced, generic)
    usando parâmetros originais e termos extraídos com scores.

    Gera queries em diferentes níveis de especificidade, validando complexidade
    de cada uma contra o limite máximo estipulado no .env (llm_max_query_complexity).

    Args:
        intake: Objeto com theme (obrigatório), description, area_of_study, keywords.
        extracted_terms: Termos extraídos do /extract-terms endpoint com {term, score, frequency, sources}.
        api: API específica (default: ops). Pode ser: ops, scopus, lens_patent, lens_scholarly.

    Returns:
        3 queries com diferentes especificidades:
        {
            "specific": { "query": {...}, "rationale": "...", "complexity": {...} },
            "balanced": { "query": {...}, "rationale": "...", "complexity": {...} },
            "generic": { "query": {...}, "rationale": "...", "complexity": {...} }
        }
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.build_final_queries_with_extraction(
            intake=intake,
            extracted_terms=extracted_terms,
            api=api,
        )

        # Contar queries bem-sucedidas
        successful_queries = sum(
            1 for q in result.get("queries", {}).values()
            if isinstance(q, dict) and q.get("success", False)
        )

        message = (
            f"Generated 3 query variations with {successful_queries} within complexity limits"
            if result.get("success", False)
            else f"Error: {result.get('error')}"
        )

        return SuccessResponse(
            success=result.get("success", False),
            data=result,
            message=message,
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("build_final_queries_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error building final queries: {str(exc)}",
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
    final_request: FinalSearchRequest = Body(...),
) -> SuccessResponse[dict[str, Any]]:
    """
    Executa busca final (busca de produção).

    Args:
        final_request: Query final construída, API e máximo de resultados.

    Returns:
        Resultados da busca final (até max_results documentos).
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        result = await pipeline.run_final_search(
            query=final_request.query.model_dump(),
            api=final_request.api,
            max_results=final_request.max_results,
        )

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
