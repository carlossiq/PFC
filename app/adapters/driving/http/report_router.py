from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.driving.http.dependencies import get_db_session
from core.logging import get_logger
from db.research_models import Research
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/reports", tags=["reports-v2"])


class GenerateLatexRequest(BaseModel):
    research_id: int


def _report_svc(request: Request):
    return request.app.state.container["services"]["report"]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "report", "version": "v2"}


@router.post("/generate-latex", response_model=SuccessResponse[dict[str, Any]])
async def generate_latex(
    request: Request,
    body: GenerateLatexRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    """
    Gera LaTeX para uma pesquisa existente usando ReportService do hexágono.

    Alternativa ao endpoint legado /api/v1/research/{id}/generate-report:
    usa o core service puro (sem Ollama, sem dependências externas).
    """
    run_id = getattr(request.state, "run_id", None)
    research_id = body.research_id

    try:
        stmt = (
            select(Research)
            .where(Research.id == research_id)
            .options(
                selectinload(Research.patent_documents),
                selectinload(Research.scholarly_documents),
                selectinload(Research.metrics),
            )
        )
        result = await session.execute(stmt)
        research = result.scalar_one_or_none()

        if not research:
            return SuccessResponse(
                success=False,
                data={},
                message=f"Research {research_id} not found",
                run_id=run_id,
            )

        report_svc = _report_svc(request)

        patents = [
            {
                "title": p.title,
                "abstract": p.abstract,
                "applicants": p.applicants or [],
                "inventors": p.inventors or [],
                "cpc_codes": p.cpc_codes or [],
                "ipc_codes": p.ipc_codes or [],
                "year": p.year,
                "legal_status": p.legal_status,
                "publication_number": p.publication_number,
            }
            for p in research.patent_documents
        ]
        articles = [
            {
                "title": a.title,
                "abstract": a.abstract,
                "authors": a.authors or [],
                "affiliations": getattr(a, "affiliations", []) or [],
                "journal_or_source": a.journal_or_source,
                "field_of_study": a.field_of_study or [],
                "keywords": a.keywords or [],
                "year": a.year,
                "citations": a.citations or 0,
                "doi": a.doi,
            }
            for a in research.scholarly_documents
        ]

        research_dict = {
            "research_id": research.research_id,
            "theme": research.title,
            "description": research.description,
            "status": research.status,
            "created_at": research.created_at.isoformat(),
            "updated_at": research.updated_at.isoformat(),
            "patent_results_count": research.patent_results_count or 0,
            "scholarly_results_count": research.scholarly_results_count or 0,
            "total_results_count": research.total_results_count or 0,
            "user_input": research.user_input or {},
            "timing": research.timing or {},
            "metrics": {},
        }

        report_data = report_svc.map_research_data(research_dict, patents, articles)
        latex_content = report_svc.generate_latex(report_data)

        logger.info(
            "v2_latex_generated research_id=%s size=%d",
            research_id,
            len(latex_content),
        )

        return SuccessResponse(
            success=True,
            data={
                "latex_content": latex_content,
                "size_bytes": len(latex_content),
                "research_id": research_id,
                "preview": latex_content[:500] + "..." if len(latex_content) > 500 else latex_content,
            },
            message="LaTeX report generated successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_generate_latex_error", error=str(exc), research_id=research_id, run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error generating LaTeX: {str(exc)}",
            run_id=run_id,
        )


@router.post("/rag/index")
async def rag_index() -> None:
    raise HTTPException(
        status_code=501,
        detail="RAG indexing not available in v2 yet (VectorStorePort adapter pending).",
    )


@router.get("/rag/stats")
async def rag_stats() -> None:
    raise HTTPException(
        status_code=501,
        detail="RAG stats not available in v2 yet (VectorStorePort adapter pending).",
    )
