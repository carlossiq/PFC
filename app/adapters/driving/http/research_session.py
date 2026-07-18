"""
Endpoint for searching/listing research sessions by their session_input theme.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.driving.http.dependencies import get_db_session
from app.adapters.driving.http.session_persistence import persist_session_input
from app.adapters.driving.http.session_probe_documents import article_to_raw_item, patent_to_raw_item
from core.logging import get_logger
from db.research_session_models import (
    ProbeQueryArticle,
    ProbeQueryPatent,
    ResearchSession,
    SessionInput,
    SessionProbeQuery,
)
from schemas.research_session import ResearchSessionSummary
from schemas.response import SuccessResponse
from schemas.session_input import SessionInputSaveRequest, SessionInputSaveResponse, TermInput

logger = get_logger(__name__)

router = APIRouter(prefix="/research-session", tags=["research-session"])


@router.get("", response_model=SuccessResponse[list[ResearchSessionSummary]])
async def search_sessions(
    theme: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[list[ResearchSessionSummary]]:
    """
    Busca sessões pelo tema de qualquer um de seus session_input (raiz ou gerado
    por IA). Sem `theme`, retorna as sessões mais recentes. Cada sessão já vem
    com todas as suas linhas de session_input carregadas.
    """
    stmt = select(ResearchSession).options(
        selectinload(ResearchSession.inputs),
        selectinload(ResearchSession.probe_queries),
        selectinload(ResearchSession.ai_calls),
    )

    if theme and theme.strip():
        stmt = (
            stmt.join(SessionInput, SessionInput.session_id == ResearchSession.id)
            .where(SessionInput.theme.ilike(f"%{theme.strip()}%"))
            .distinct()
        )

    stmt = stmt.order_by(ResearchSession.created_at.desc()).limit(limit)

    result = await session.execute(stmt)
    sessions = result.scalars().all()

    logger.info("research_session_search", theme=theme, limit=limit, results_count=len(sessions))

    return SuccessResponse(
        data=[ResearchSessionSummary.model_validate(s) for s in sessions]
    )


@router.get("/{session_id}", response_model=SuccessResponse[ResearchSessionSummary])
async def get_session(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ResearchSessionSummary]:
    """Busca uma sessão específica com todas as suas linhas de session_input e
    session_probe_query - usado ao retomar uma sessão pendente no frontend."""
    stmt = (
        select(ResearchSession)
        .where(ResearchSession.id == session_id)
        .options(
            selectinload(ResearchSession.inputs),
            selectinload(ResearchSession.probe_queries)
            .selectinload(SessionProbeQuery.patent_links)
            .selectinload(ProbeQueryPatent.patent),
            selectinload(ResearchSession.probe_queries)
            .selectinload(SessionProbeQuery.article_links)
            .selectinload(ProbeQueryArticle.article),
            selectinload(ResearchSession.probe_queries).selectinload(SessionProbeQuery.term_links),
            selectinload(ResearchSession.ai_calls),
        )
    )
    result = await session.execute(stmt)
    research_session = result.scalar_one_or_none()

    if research_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    summary = ResearchSessionSummary.model_validate(research_session)
    # Reconstrói os documentos persistidos (patent/article) de cada probe query
    # no formato "cru" que o probe search devolveria, pra retomar uma sessão
    # sem precisar rebuscar na OPS/Scopus (ver session_probe_documents.py).
    for row, probe_query in zip(summary.probe_queries, research_session.probe_queries):
        if probe_query.fonte == "ops":
            row.documents = [patent_to_raw_item(link.patent) for link in probe_query.patent_links]
        elif probe_query.fonte == "scopus":
            row.documents = [article_to_raw_item(link.article) for link in probe_query.article_links]
        row.terms = [
            TermInput(term=t.term, score=t.score, frequency=t.frequency, selected=t.selected)
            for t in probe_query.term_links
        ]

    return SuccessResponse(data=summary)


@router.put("/{session_id}", response_model=SuccessResponse[SessionInputSaveResponse])
async def update_session(
    session_id: int,
    payload: SessionInputSaveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[SessionInputSaveResponse]:
    """Atualiza uma sessão já salva (root/generated/probe_queries em upsert)
    ao invés de criar linhas novas - usado tanto para salvar progresso de novo
    quanto para finalizar uma sessão retomada anteriormente."""
    stmt = (
        select(ResearchSession)
        .where(ResearchSession.id == session_id)
        .options(selectinload(ResearchSession.inputs), selectinload(ResearchSession.probe_queries))
    )
    result = await session.execute(stmt)
    research_session = result.scalar_one_or_none()

    if research_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    data = await persist_session_input(session, research_session, payload)

    logger.info("research_session_updated", session_id=session_id, completed=payload.completed)

    return SuccessResponse(data=data)


@router.delete("/{session_id}", response_model=SuccessResponse[dict])
async def delete_session(
    session_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict]:
    """Apaga a research_session e, em cascata (cascade='all, delete-orphan' nas
    relationships ResearchSession.inputs e ResearchSession.probe_queries), todas
    as suas linhas de session_input e session_probe_query."""
    stmt = (
        select(ResearchSession)
        .where(ResearchSession.id == session_id)
        .options(selectinload(ResearchSession.inputs), selectinload(ResearchSession.probe_queries))
    )
    result = await session.execute(stmt)
    research_session = result.scalar_one_or_none()

    if research_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    await session.delete(research_session)
    await session.commit()

    logger.info("research_session_deleted", session_id=session_id)

    return SuccessResponse(data={"id": session_id, "deleted": True})
