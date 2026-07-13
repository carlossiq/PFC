"""
Endpoint for creating a prospecting session's input parameters.

Unlike the old param_init flow (synced incrementally via POST/PUT/DELETE as the
user typed), everything is kept in the frontend and sent here in one shot -
either as a mid-wizard "save progress" (completed=False) or a full finalization
(completed=True). This endpoint always creates a new research_session; updating
an already-saved session happens via PUT /research-session/{id} instead, which
shares the same upsert logic (see session_persistence.py).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.dependencies import get_db_session
from app.adapters.driving.http.session_persistence import persist_session_input
from core.logging import get_logger
from db.research_session_models import ResearchSession
from schemas.response import SuccessResponse
from schemas.session_input import SessionInputSaveRequest, SessionInputSaveResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/session-input", tags=["session-input"])


@router.post("", response_model=SuccessResponse[SessionInputSaveResponse])
async def finalize_session(
    payload: SessionInputSaveRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[SessionInputSaveResponse]:
    """Cria a research_session e a cadeia de session_input (raiz + gerado) numa transação."""
    research_session = ResearchSession(name=payload.name, completed=payload.completed)
    session.add(research_session)
    await session.flush()

    data = await persist_session_input(session, research_session, payload)

    logger.info(
        "session_finalized",
        session_id=research_session.id,
        root_input_id=data.root.id,
        generated_input_id=data.generated.id if data.generated else None,
        probe_query_count=len(data.probe_queries),
        completed=payload.completed,
    )

    return SuccessResponse(data=data)
