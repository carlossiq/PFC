"""
Endpoint for searching/listing research sessions by their session_input theme.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.driving.http.dependencies import get_db_session
from core.logging import get_logger
from db.research_session_models import ResearchSession, SessionInput
from schemas.research_session import ResearchSessionSummary
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/research-session", tags=["research-session"])


@router.get("", response_model=SuccessResponse[list[ResearchSessionSummary]])
async def search_sessions(
    theme: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[list[ResearchSessionSummary]]:
    """
    Busca sessões pelo tema de qualquer um de seus session_input (raiz ou gerado
    por IA). Sem `theme`, retorna as sessões mais recentes. Cada sessão já vem
    com todas as suas linhas de session_input carregadas.
    """
    stmt = select(ResearchSession).options(
        selectinload(ResearchSession.inputs), selectinload(ResearchSession.probe_queries)
    )

    if theme and theme.strip():
        stmt = (
            stmt.join(SessionInput, SessionInput.session_id == ResearchSession.id)
            .where(SessionInput.theme.ilike(f"%{theme.strip()}%"))
            .distinct()
        )

    stmt = stmt.order_by(ResearchSession.created_at.desc()).limit(50)

    result = await session.execute(stmt)
    sessions = result.scalars().all()

    logger.info("research_session_search", theme=theme, results_count=len(sessions))

    return SuccessResponse(
        data=[ResearchSessionSummary.model_validate(s) for s in sessions]
    )


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
