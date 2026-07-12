from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Request

from app.core.services.chat_service import ChatService
from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _svc(request: Request) -> ChatService:
    return request.app.state.container["services"]["chat"]


def _run_id(request: Request) -> str | None:
    return getattr(request.state, "run_id", None)


# ------------------------------------------------------------------
# Config / info
# ------------------------------------------------------------------

@router.get("/apis", response_model=SuccessResponse[dict[str, Any]])
async def get_available_apis(request: Request) -> SuccessResponse[dict[str, Any]]:
    result = await _svc(request).list_available_apis()
    return SuccessResponse(success=result["success"], data=result, run_id=_run_id(request))


@router.get("/models", response_model=SuccessResponse[dict[str, Any]])
async def get_available_models(request: Request) -> SuccessResponse[dict[str, Any]]:
    result = await _svc(request).list_available_models()
    return SuccessResponse(success=result["success"], data=result, run_id=_run_id(request))


@router.get("/current-provider", response_model=SuccessResponse[dict[str, Any]])
async def get_current_provider(request: Request) -> SuccessResponse[dict[str, Any]]:
    result = await _svc(request).get_current_provider()
    return SuccessResponse(success=result["success"], data=result, run_id=_run_id(request))


@router.get("/system-prompt", response_model=SuccessResponse[dict[str, Any]])
async def get_system_prompt(request: Request) -> SuccessResponse[dict[str, Any]]:
    result = await _svc(request).get_system_prompt()
    return SuccessResponse(success=result["success"], data=result, run_id=_run_id(request))


@router.get("/ops-token-status", response_model=SuccessResponse[dict[str, Any]])
async def check_ops_token(request: Request) -> SuccessResponse[dict[str, Any]]:
    result = await _svc(request).check_ops_token_status()
    return SuccessResponse(
        success=result["success"],
        data=result,
        message="OPS token valid" if result.get("is_valid") else result.get("error", ""),
        run_id=_run_id(request),
    )


# ------------------------------------------------------------------
# Topic refinement
# ------------------------------------------------------------------

@router.post("/refine-topic", response_model=SuccessResponse[dict[str, Any]])
async def refine_topic(
    request: Request,
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "artificial intelligence",
            "description": "General AI and machine learning applications",
            "area_of_study": "Computer Science",
            "keywords": ["neural networks", "deep learning"],
        },
    ),
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).generate_candidate_topics(intake)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message="Topic refined with 4 specific variations" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("refine_topic_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


@router.post("/specify-topic", response_model=SuccessResponse[dict[str, Any]])
async def specify_topic(
    request: Request,
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "Deep Learning for Medical Image Analysis",
            "description": "Applying deep learning to diagnostic imaging",
            "area_of_study": "Healthcare",
            "keywords": ["deep learning", "medical imaging"],
        },
    ),
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).specify_topic(intake)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message="Topic specified further" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("specify_topic_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


# ------------------------------------------------------------------
# Query building
# ------------------------------------------------------------------

@router.post("/analyze-query", response_model=SuccessResponse[dict[str, Any]])
async def analyze_query(
    request: Request,
    query: str = Body(..., embed=True, description="CQL or boolean query string to analyze"),
) -> SuccessResponse[dict[str, Any]]:
    result = _svc(request).analyze_query(query)
    return SuccessResponse(success=result["success"], data=result, run_id=_run_id(request))


@router.post("/probe/query", response_model=SuccessResponse[dict[str, Any]])
async def build_probe_query(
    request: Request,
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "e-commerce and digital payments",
            "description": "Online shopping platforms with secure payment processing",
            "area_of_study": "Information Technology",
            "keywords": ["blockchain", "payment gateway"],
        },
    ),
    api: str = "ops",
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).build_probe_query(intake, api)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message=result.get("warning", "Probe query built successfully") if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("probe_query_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


@router.post("/final/query", response_model=SuccessResponse[dict[str, Any]])
async def build_final_query(
    request: Request,
    intake: InputIntake = Body(...),
    api: str = "ops",
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).build_final_query(intake, api)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message=result.get("warning", "Final query built successfully") if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("final_query_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


@router.post("/probe/queries-multi", response_model=SuccessResponse[dict[str, Any]])
async def build_probe_queries_multi(
    request: Request,
    intake: InputIntake = Body(
        ...,
        example={
            "theme": "e-commerce and digital payments",
            "description": "Online shopping platforms with secure payment processing",
            "area_of_study": "Information Technology",
            "keywords": ["blockchain", "payment gateway"],
        },
    ),
    api: str = "ops",
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).build_probe_queries_multi(intake, api)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message="Probe queries built" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("probe_queries_multi_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


@router.post("/probe/rebuild-query", response_model=SuccessResponse[dict[str, Any]])
async def rebuild_probe_query(
    request: Request,
    fields: dict[str, list[str]] = Body(
        ...,
        description=(
            "Campos estruturados (title, abstract, claims, ipc, cpc, applicant, "
            "inventor, year), cada um como lista OR de termos."
        ),
        example={
            "title": ["machine learning"],
            "abstract": [],
            "claims": [],
            "ipc": ["G06N3/08"],
            "cpc": [],
            "applicant": [],
            "inventor": [],
            "year": ["2023"],
        },
    ),
    api: str = "ops",
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).rebuild_probe_query(fields, api)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message="Query reconstruída a partir dos campos estruturados" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("rebuild_probe_query_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


@router.post("/final/queries-multi", response_model=SuccessResponse[dict[str, Any]])
async def build_final_queries_multi(
    request: Request,
    intake: InputIntake = Body(...),
    extracted_terms: list[dict[str, Any]] = Body(default=[]),
    api: str = "ops",
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).build_final_queries_multi(intake, extracted_terms, api)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message="Final queries built (specific/balanced/generic)" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("final_queries_multi_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


# ------------------------------------------------------------------
# Search
# ------------------------------------------------------------------

@router.post("/probe/search", response_model=SuccessResponse[dict[str, Any]])
async def run_probe_search(
    request: Request,
    query: dict[str, Any] = Body(..., description="Query dict returned by /probe/query"),
    api: str = "ops",
    top_k: int = 10,
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).run_probe_search(query, api, top_k)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message=f"Probe search returned {result.get('results_count', 0)} results" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("probe_search_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


@router.post("/final/search", response_model=SuccessResponse[dict[str, Any]])
async def run_final_search(
    request: Request,
    query: dict[str, Any] = Body(..., description="Query dict returned by /final/query"),
    api: str = "ops",
    max_results: int = 500,
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).run_final_search(query, api, max_results)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message=f"Final search returned {result.get('results_count', 0)} results" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("final_search_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)


# ------------------------------------------------------------------
# NLP
# ------------------------------------------------------------------

@router.post("/extract-terms", response_model=SuccessResponse[dict[str, Any]])
async def extract_terms(
    request: Request,
    items: list[dict[str, Any]] = Body(..., description="List of dicts with 'title' and 'abstract'"),
    original_params: dict[str, Any] = Body(default={}),
    top_k: int = 20,
) -> SuccessResponse[dict[str, Any]]:
    run_id = _run_id(request)
    try:
        result = await _svc(request).extract_terms(items, original_params, top_k)
        return SuccessResponse(
            success=result["success"],
            data=result,
            message=f"Extracted {result.get('count', 0)} terms" if result["success"] else result.get("error", ""),
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("extract_terms_error", error=str(exc), run_id=run_id)
        return SuccessResponse(success=False, data={"error": str(exc)}, run_id=run_id)
