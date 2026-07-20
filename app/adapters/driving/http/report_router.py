"""
Endpoint for generating the technology-prospecting report charts (S-curve,
top entities, classification/geographic distributions) from a research
session's final-search documents.

"Final search" documents = Patent/Article rows linked (via
ProbeQueryPatent/ProbeQueryArticle) to a SessionProbeQuery of this session
with tipo IS NOT NULL - tipo=None is the probe/Resultados Iniciais query,
tipo=specific|balanced|generic is the chosen final query variant (see
session_persistence.py/session_probe_documents.py for how these get
persisted when a session is saved/finalized).
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.dependencies import get_db_session
from app.core.services.report_service import ReportService
from core.logging import get_logger
from db.research_session_models import (
    Article,
    Patent,
    ProbeQueryArticle,
    ProbeQueryPatent,
    ResearchSession,
    SessionProbeQuery,
)
from schemas.report import ReportGraphicsResponse
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/report", tags=["report"])


def _svc(request: Request) -> ReportService:
    return request.app.state.container["services"]["report"]


def _patent_to_dict(patent: Patent) -> dict[str, Any]:
    return {
        "year": patent.year,
        "applicants": patent.applicants,
        "inventors": patent.inventors,
        "cpc_codes": patent.cpc_codes,
        "ipc_codes": patent.ipc_codes,
        "country": patent.country,
    }


def _article_to_dict(article: Article) -> dict[str, Any]:
    return {
        "year": article.year,
        "authors": article.authors,
        "journal_or_source": article.journal_or_source,
        "field_of_study": article.field_of_study,
        "affiliation_countries": article.affiliation_countries,
    }


@router.post("/{session_id}/graphics", response_model=SuccessResponse[ReportGraphicsResponse])
async def generate_session_graphics(
    session_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReportGraphicsResponse]:
    """Gera os gráficos de report a partir dos documentos já persistidos da
    busca final (tipo != None) da sessão - não dispara nenhuma busca nova."""
    exists = await session.execute(select(ResearchSession.id).where(ResearchSession.id == session_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    patent_stmt = (
        select(Patent)
        .join(ProbeQueryPatent, ProbeQueryPatent.patent_id == Patent.id)
        .join(SessionProbeQuery, SessionProbeQuery.id == ProbeQueryPatent.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
        .distinct()
    )
    article_stmt = (
        select(Article)
        .join(ProbeQueryArticle, ProbeQueryArticle.article_id == Article.id)
        .join(SessionProbeQuery, SessionProbeQuery.id == ProbeQueryArticle.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
        .distinct()
    )
    patents = (await session.execute(patent_stmt)).scalars().all()
    articles = (await session.execute(article_stmt)).scalars().all()

    result = _svc(request).generate_session_report(
        session_id=session_id,
        patents=[_patent_to_dict(p) for p in patents],
        articles=[_article_to_dict(a) for a in articles],
    )

    logger.info(
        "report_graphics_requested",
        session_id=session_id,
        patents_used=result["patents_used"],
        articles_used=result["articles_used"],
        charts_count=len(result["charts"]),
        skipped_count=len(result["skipped"]),
    )

    return SuccessResponse(data=ReportGraphicsResponse(**result))
