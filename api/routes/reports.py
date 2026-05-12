"""
API routes for report generation using Ollama and RAG.

Endpoints for generating technology prospecting reports
in REPTEC/AGITEC style with local LLM.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from core.logging import get_logger
from schemas.report import (
    HealthCheckResponse,
    RAGIndexRequest,
    RAGStatsResponse,
    ReportGenerationRequest,
    ReportResponse,
    ReportSectionRequest,
    ReportSectionResponse,
)
from services.ollama_service import OllamaService
from services.rag_service import RAGService
from services.report_service import ReportService, ReportGenerationError

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])

# Global service instances (initialize on startup)
_ollama_service: OllamaService = None
_rag_service: RAGService = None
_report_service: ReportService = None


def get_report_service() -> ReportService:
    """Dependency to get report service."""
    if _report_service is None:
        raise HTTPException(
            status_code=503,
            detail="Report service not initialized. Check if Ollama is running.",
        )
    return _report_service


async def initialize_services():
    """Initialize Ollama and RAG services. Call from FastAPI startup event."""
    global _ollama_service, _rag_service, _report_service

    logger.info("initializing_report_services")

    try:
        # Initialize Ollama service
        _ollama_service = OllamaService(
            base_url="http://localhost:11434",
            text_model="qwen2.5:3b-instruct",
            embedding_model="nomic-embed-text",
        )

        # Check Ollama health
        is_healthy = await _ollama_service.health_check()
        if not is_healthy:
            logger.error("ollama_not_healthy")
            return False

        # Initialize RAG service
        _rag_service = RAGService(
            ollama_service=_ollama_service,
            db_path=".chroma_db",
            collection_name="research_documents",
        )

        # Initialize report service
        _report_service = ReportService(
            ollama_service=_ollama_service,
            rag_service=_rag_service,
        )

        logger.info("report_services_initialized")
        return True

    except Exception as exc:
        logger.error("service_initialization_failed", error=str(exc))
        return False


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    request: Request,
    service: ReportService = Depends(get_report_service),
) -> HealthCheckResponse:
    """
    Check health of report generation services.

    Returns:
        Health status of Ollama and RAG services
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        health = await service.health_check()

        return HealthCheckResponse(
            ollama=health["ollama"],
            rag=health["rag"],
            timestamp=health["timestamp"],
        )
    except Exception as exc:
        logger.error("health_check_error", error=str(exc), run_id=run_id)
        raise HTTPException(
            status_code=503,
            detail=f"Health check failed: {str(exc)}",
        )


@router.get("/rag/stats", response_model=RAGStatsResponse)
async def get_rag_stats(
    request: Request,
    service: ReportService = Depends(get_report_service),
) -> RAGStatsResponse:
    """
    Get RAG (ChromaDB) collection statistics.

    Returns:
        Collection stats
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        stats = service.get_rag_stats()

        return RAGStatsResponse(
            collection_name=stats["collection_name"],
            document_count=stats["document_count"],
            db_path=stats["db_path"],
            status=stats["status"],
        )
    except Exception as exc:
        logger.error("rag_stats_error", error=str(exc), run_id=run_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/rag/index")
async def index_documents(
    request: Request,
    req: RAGIndexRequest,
    service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    """
    Index documents in RAG for retrieval.

    These documents will be used as context for report generation.

    Args:
        req: RAG index request with documents

    Returns:
        Number of chunks indexed
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        chunk_count = await service.add_documents_to_rag(req.documents)

        return {
            "success": True,
            "chunks_indexed": chunk_count,
            "documents_indexed": len(req.documents),
            "run_id": run_id,
        }
    except Exception as exc:
        logger.error("rag_index_error", error=str(exc), run_id=run_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/rag/clear")
async def clear_rag(
    request: Request,
    service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    """
    Clear all documents from RAG collection.

    Returns:
        Success status
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        success = await service.clear_rag()

        return {
            "success": success,
            "message": "RAG collection cleared" if success else "Failed to clear",
            "run_id": run_id,
        }
    except Exception as exc:
        logger.error("rag_clear_error", error=str(exc), run_id=run_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: Request,
    req: ReportGenerationRequest,
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    """
    Generate complete technology prospecting report.

    Generates all sections (Finalidade, Objetivo, Introdução, etc.)
    using Ollama LLM and RAG for context retrieval.

    Args:
        req: Report generation request

    Returns:
        Generated report in Markdown format
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        logger.info("report_generation_requested", theme=req.theme, run_id=run_id)

        # Generate report
        report = await service.generate_full_report(
            theme=req.theme,
            description=req.description or "",
            data={
                "area_of_study": req.area_of_study,
                "keywords": req.keywords,
                "period_start": req.period_start,
                "period_end": req.period_end,
                "scientific_data": req.scientific_data,
                "patent_data": req.patent_data,
                "s_curve_data": req.s_curve_data,
                "references": req.references,
            },
            chart_paths=req.chart_paths,
            metadata={
                "area_of_study": req.area_of_study,
                "keywords": req.keywords,
                "period_start": req.period_start,
                "period_end": req.period_end,
            },
        )

        return ReportResponse(
            success=True,
            report=report,
            metadata={
                "theme": req.theme,
                "run_id": run_id,
            },
        )

    except ReportGenerationError as exc:
        logger.error("report_generation_error", error=str(exc), theme=req.theme, run_id=run_id)
        return ReportResponse(
            success=False,
            report=None,
            error=str(exc),
            metadata={"theme": req.theme, "run_id": run_id},
        )
    except Exception as exc:
        logger.error(
            "report_generation_unexpected_error",
            error=str(exc),
            theme=req.theme,
            run_id=run_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(exc)}",
        )


@router.post("/generate-section", response_model=ReportSectionResponse)
async def generate_section(
    request: Request,
    req: ReportSectionRequest,
    service: ReportService = Depends(get_report_service),
) -> ReportSectionResponse:
    """
    Generate a single report section.

    Useful for generating sections individually with specific data.

    Args:
        req: Section generation request

    Returns:
        Generated section in Markdown format
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        logger.info(
            "section_generation_requested",
            section=req.section_name,
            theme=req.theme,
            run_id=run_id,
        )

        result = await service.generate_section_sync(
            section_name=req.section_name,
            section_type=req.section_type,
            theme=req.theme,
            data=req.data,
        )

        return ReportSectionResponse(
            success=result["success"],
            section=result["section"],
            content=result.get("content"),
            error=result.get("error"),
            generated_at=result["generated_at"],
        )

    except Exception as exc:
        logger.error(
            "section_generation_error",
            section=req.section_name,
            error=str(exc),
            run_id=run_id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Section generation failed: {str(exc)}",
        )


@router.post("/models/list")
async def list_models(
    request: Request,
    service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    """
    List available Ollama models.

    Returns:
        List of model names
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        models = await service.ollama.list_models()

        return {
            "success": True,
            "models": models,
            "count": len(models),
            "run_id": run_id,
        }
    except Exception as exc:
        logger.error("list_models_error", error=str(exc), run_id=run_id)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/generate-from-research", response_model=ReportResponse)
async def generate_report_from_research(
    request: Request,
    research_id: int,
    service: ReportService = Depends(get_report_service),
) -> ReportResponse:
    """
    Generate report from existing Research object.

    Convenient endpoint that:
    1. Loads Research from database (requires external session)
    2. Consolidates OPS (patents) + Scopus (articles) data
    3. Creates RAG documents from both sources
    4. Generates complete report

    Note: This endpoint requires the Research to be pre-loaded and passed.
    For actual implementation, you may want to inject the session and load
    the Research directly here.

    Args:
        research_id: ID of research to generate report for
        service: Report service instance

    Returns:
        Generated report in Markdown format
    """
    run_id = getattr(request.state, "run_id", None)

    try:
        logger.info("research_report_generation_requested", research_id=research_id, run_id=run_id)

        # Note: In production, you would:
        # 1. Inject AsyncSession dependency
        # 2. Load Research: research = await session.get(Research, research_id)
        # 3. Call: report = await service.generate_report_from_research(research)

        # For now, return error indicating this needs proper integration
        raise HTTPException(
            status_code=501,
            detail="This endpoint requires database session injection. "
            "Use example_research_to_report.py for reference implementation.",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "research_report_generation_error",
            error=str(exc),
            research_id=research_id,
            run_id=run_id,
        )
        raise HTTPException(status_code=500, detail=str(exc))
