from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.driving.http.dependencies import get_db_session
from core.logging import get_logger
from db.research_models import Research, ResearchPatentDocument, ResearchScholarlyDocument, ResearchTokenUsage
from schemas.response import SuccessResponse
from app.core.services.metrics_aggregator import MetricsAggregator

logger = get_logger(__name__)

router = APIRouter(prefix="/research", tags=["research-v2"])


def _container(request: Request) -> dict[str, Any]:
    return request.app.state.container


@router.get("/{research_id}", response_model=SuccessResponse[dict[str, Any]])
async def get_research(
    request: Request,
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    run_id = getattr(request.state, "run_id", None)
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

        return SuccessResponse(
            success=True,
            data={
                "id": research.id,
                "research_id": research.research_id,
                "title": research.title,
                "description": research.description,
                "status": research.status,
                "user_input": research.user_input,
                "patent_results_count": research.patent_results_count,
                "scholarly_results_count": research.scholarly_results_count,
                "total_results_count": research.total_results_count,
                "timing": research.timing,
                "created_at": research.created_at.isoformat(),
                "updated_at": research.updated_at.isoformat(),
            },
            message="Research retrieved successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_get_research_error", error=str(exc), research_id=research_id, run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving research: {str(exc)}",
            run_id=run_id,
        )


@router.get("/{research_id}/patents", response_model=SuccessResponse[dict[str, Any]])
async def get_research_patents(
    request: Request,
    research_id: int,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    run_id = getattr(request.state, "run_id", None)
    try:
        limit = min(limit, 500)

        stmt = (
            select(ResearchPatentDocument)
            .where(ResearchPatentDocument.research_id == research_id)
            .order_by(ResearchPatentDocument.relevance_score.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        patents = result.scalars().all()

        count_stmt = select(func.count(ResearchPatentDocument.id)).where(
            ResearchPatentDocument.research_id == research_id
        )
        total = (await session.execute(count_stmt)).scalar() or 0

        patent_list = [
            {
                "publication_number": p.publication_number,
                "title": p.title,
                "abstract": p.abstract,
                "applicants": p.applicants,
                "inventors": p.inventors,
                "ipc_codes": p.ipc_codes,
                "cpc_codes": p.cpc_codes,
                "year": p.year,
                "legal_status": p.legal_status,
                "relevance_score": p.relevance_score,
                "query_variant": p.query_variant,
            }
            for p in patents
        ]

        return SuccessResponse(
            success=True,
            data={"patents": patent_list, "total": total, "limit": limit, "offset": offset},
            message=f"Retrieved {len(patent_list)} patents",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_get_research_patents_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving patents: {str(exc)}",
            run_id=run_id,
        )


@router.get("/{research_id}/articles", response_model=SuccessResponse[dict[str, Any]])
async def get_research_articles(
    request: Request,
    research_id: int,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    run_id = getattr(request.state, "run_id", None)
    try:
        limit = min(limit, 500)

        stmt = (
            select(ResearchScholarlyDocument)
            .where(ResearchScholarlyDocument.research_id == research_id)
            .order_by(ResearchScholarlyDocument.relevance_score.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        articles = result.scalars().all()

        count_stmt = select(func.count(ResearchScholarlyDocument.id)).where(
            ResearchScholarlyDocument.research_id == research_id
        )
        total = (await session.execute(count_stmt)).scalar() or 0

        article_list = [
            {
                "doi": a.doi,
                "title": a.title,
                "abstract": a.abstract,
                "authors": a.authors,
                "journal_or_source": a.journal_or_source,
                "year": a.year,
                "citations": a.citations,
                "keywords": a.keywords,
                "field_of_study": a.field_of_study,
                "relevance_score": a.relevance_score,
                "query_variant": a.query_variant,
            }
            for a in articles
        ]

        return SuccessResponse(
            success=True,
            data={"articles": article_list, "total": total, "limit": limit, "offset": offset},
            message=f"Retrieved {len(article_list)} articles",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_get_research_articles_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving articles: {str(exc)}",
            run_id=run_id,
        )


@router.post("/{research_id}/calculate-metrics", response_model=SuccessResponse[dict[str, Any]])
async def calculate_metrics(
    request: Request,
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    run_id = getattr(request.state, "run_id", None)
    try:
        aggregator = MetricsAggregator(session)
        metrics = await aggregator.calculate_and_store_metrics(research_id)

        if not metrics:
            return SuccessResponse(
                success=False,
                data={},
                message="Failed to calculate metrics",
                run_id=run_id,
            )

        return SuccessResponse(
            success=True,
            data={
                "patent_by_year": metrics.patent_by_year,
                "patent_by_applicant": metrics.patent_by_applicant,
                "patent_by_ipc": metrics.patent_by_ipc,
                "article_by_year": metrics.article_by_year,
                "article_by_journal": metrics.article_by_journal,
                "article_by_field": metrics.article_by_field,
                "top_patent_applicants": metrics.top_patent_applicants,
                "top_article_authors": metrics.top_article_authors,
                "top_article_journals": metrics.top_article_journals,
                "patent_growth_trend": metrics.patent_growth_trend,
                "article_growth_trend": metrics.article_growth_trend,
            },
            message="Metrics calculated successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_calculate_metrics_error", error=str(exc), research_id=research_id, run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error calculating metrics: {str(exc)}",
            run_id=run_id,
        )


@router.post("/{research_id}/generate-report", response_model=SuccessResponse[dict[str, Any]])
async def generate_report(
    request: Request,
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    """Gera LaTeX usando o ReportService do hexágono (sem Ollama)."""
    run_id = getattr(request.state, "run_id", None)
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

        container = _container(request)
        report_svc = container["services"]["report"]

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
            "chosen_candidate": research.chosen_candidate or {},
            "metrics": {
                "patent_by_year":         getattr(research.metrics, "patent_by_year", {}) or {},
                "patent_by_applicant":    getattr(research.metrics, "patent_by_applicant", {}) or {},
                "patent_by_ipc":          getattr(research.metrics, "patent_by_ipc", {}) or {},
                "patent_by_legal_status": getattr(research.metrics, "patent_by_legal_status", {}) or {},
                "article_by_journal":     getattr(research.metrics, "article_by_journal", {}) or {},
                "article_by_field":       getattr(research.metrics, "article_by_field", {}) or {},
                "patent_growth_trend":    getattr(research.metrics, "patent_growth_trend", {}) or {},
                "article_growth_trend":   getattr(research.metrics, "article_growth_trend", {}) or {},
            } if research.metrics else {},
        }

        report_data = report_svc.map_research_data(research_dict, patents, articles)
        latex_content = report_svc.generate_latex(report_data)

        research.latex_content = latex_content
        research.latex_generated_at = datetime.utcnow()
        await session.commit()

        return SuccessResponse(
            success=True,
            data={
                "latex_content": latex_content[:1000] + "..." if len(latex_content) > 1000 else latex_content,
                "size_bytes": len(latex_content),
                "message": "LaTeX report generated. Use 'pdflatex' to compile to PDF.",
            },
            message="Report generated successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_generate_report_error", error=str(exc), research_id=research_id, run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error generating report: {str(exc)}",
            run_id=run_id,
        )


@router.get("/{research_id}/report", response_model=SuccessResponse[dict[str, Any]])
async def get_report(
    request: Request,
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    run_id = getattr(request.state, "run_id", None)
    try:
        stmt = select(Research).where(Research.id == research_id)
        result = await session.execute(stmt)
        research = result.scalar_one_or_none()

        if not research:
            return SuccessResponse(
                success=False,
                data={},
                message=f"Research {research_id} not found",
                run_id=run_id,
            )

        if not research.latex_content:
            return SuccessResponse(
                success=False,
                data={},
                message="No report generated yet. Call POST /api/v2/research/{research_id}/generate-report",
                run_id=run_id,
            )

        return SuccessResponse(
            success=True,
            data={
                "latex_content": research.latex_content,
                "generated_at": research.latex_generated_at.isoformat() if research.latex_generated_at else None,
                "size_bytes": len(research.latex_content),
            },
            message="Report retrieved successfully",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_get_report_error", error=str(exc), run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving report: {str(exc)}",
            run_id=run_id,
        )


@router.get("/{research_id}/token-usage", response_model=SuccessResponse[dict[str, Any]])
async def get_token_usage(
    request: Request,
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    run_id = getattr(request.state, "run_id", None)
    try:
        result = await session.execute(
            select(ResearchTokenUsage)
            .where(ResearchTokenUsage.research_id == research_id)
            .order_by(ResearchTokenUsage.created_at)
        )
        usage_records = result.scalars().all()

        call_history = [
            {
                "timestamp": record.created_at.isoformat(),
                "phase": record.phase_name,
                "call_type": record.llm_call_type,
                "call_number": record.call_number,
                "model": record.model,
                "model_variant": record.model_variant,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "total_tokens": record.total_tokens,
                "input_cost_usd": record.input_cost_usd,
                "output_cost_usd": record.output_cost_usd,
                "total_cost_usd": record.total_cost_usd,
                "api_latency_ms": record.api_latency_ms,
                "status": record.status,
            }
            for record in usage_records
        ]

        total_tokens = sum(r.total_tokens for r in usage_records)
        total_cost = sum(r.total_cost_usd for r in usage_records)

        return SuccessResponse(
            success=True,
            data={
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 4),
                "call_count": len(usage_records),
                "call_history": call_history,
            },
            message=f"Retrieved token usage for {len(usage_records)} API calls",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_get_token_usage_error", error=str(exc), research_id=research_id, run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving token usage: {str(exc)}",
            run_id=run_id,
        )


@router.get("/{research_id}/token-summary", response_model=SuccessResponse[dict[str, Any]])
async def get_token_summary(
    request: Request,
    research_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, Any]]:
    run_id = getattr(request.state, "run_id", None)
    try:
        result = await session.execute(
            select(ResearchTokenUsage)
            .where(ResearchTokenUsage.research_id == research_id)
            .order_by(ResearchTokenUsage.created_at)
        )
        usage_records = result.scalars().all()

        if not usage_records:
            summary: dict[str, Any] = {
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "by_phase": {},
                "by_model": {},
                "call_history": [],
            }
        else:
            by_phase: dict[str, Any] = {}
            for record in usage_records:
                if record.phase_name not in by_phase:
                    by_phase[record.phase_name] = {"tokens": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "calls": 0}
                by_phase[record.phase_name]["tokens"] += record.total_tokens
                by_phase[record.phase_name]["input_tokens"] += record.input_tokens
                by_phase[record.phase_name]["output_tokens"] += record.output_tokens
                by_phase[record.phase_name]["cost_usd"] += record.total_cost_usd
                by_phase[record.phase_name]["calls"] += 1

            by_model: dict[str, Any] = {}
            for record in usage_records:
                model_key = f"{record.model} ({record.model_variant})" if record.model_variant else record.model
                if model_key not in by_model:
                    by_model[model_key] = {"tokens": 0, "cost_usd": 0.0, "calls": 0}
                by_model[model_key]["tokens"] += record.total_tokens
                by_model[model_key]["cost_usd"] += record.total_cost_usd
                by_model[model_key]["calls"] += 1

            summary = {
                "total_tokens": sum(r.total_tokens for r in usage_records),
                "total_cost_usd": sum(r.total_cost_usd for r in usage_records),
                "by_phase": by_phase,
                "by_model": by_model,
                "call_history": [
                    {
                        "timestamp": record.created_at.isoformat(),
                        "phase": record.phase_name,
                        "call_type": record.llm_call_type,
                        "call_number": record.call_number,
                        "model": record.model,
                        "tokens": record.total_tokens,
                        "cost_usd": record.total_cost_usd,
                        "latency_ms": record.api_latency_ms,
                        "status": record.status,
                    }
                    for record in usage_records
                ],
            }

        for phase_data in summary["by_phase"].values():
            phase_data["cost_usd"] = round(phase_data["cost_usd"], 4)
        for model_data in summary["by_model"].values():
            model_data["cost_usd"] = round(model_data["cost_usd"], 4)
        summary["total_cost_usd"] = round(summary["total_cost_usd"], 4)

        return SuccessResponse(
            success=True,
            data=summary,
            message="Token usage summary retrieved",
            run_id=run_id,
        )
    except Exception as exc:
        logger.error("v2_get_token_summary_error", error=str(exc), research_id=research_id, run_id=run_id)
        return SuccessResponse(
            success=False,
            data={"error": str(exc)},
            message=f"Error retrieving token summary: {str(exc)}",
            run_id=run_id,
        )
