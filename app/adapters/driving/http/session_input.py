"""
Endpoint for finalizing a prospecting session's input parameters.

Unlike the old param_init flow (synced incrementally via POST/PUT/DELETE as the
user typed), everything is kept in the frontend until the whole research session
is finalized - at which point this single endpoint creates the research_session
plus the session_input chain (root user input, and the AI-refined child if any)
in one transaction.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.dependencies import get_db_session
from core.logging import get_logger
from db.research_session_models import ResearchSession, SessionInput
from schemas.response import SuccessResponse
from schemas.session_input import SessionInputFinalizeRequest, SessionInputFinalizeResponse, SessionInputRow

logger = get_logger(__name__)

router = APIRouter(prefix="/session-input", tags=["session-input"])


@router.post("", response_model=SuccessResponse[SessionInputFinalizeResponse])
async def finalize_session(
    payload: SessionInputFinalizeRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[SessionInputFinalizeResponse]:
    """Cria a research_session e a cadeia de session_input (raiz + gerado) numa transação."""
    research_session = ResearchSession(name=payload.name)
    session.add(research_session)
    await session.flush()

    root = SessionInput(
        session_id=research_session.id,
        parent_id=None,
        theme=payload.root.theme,
        description=payload.root.description,
        area_of_study=payload.root.area_of_study,
        keywords=payload.root.keywords,
        year_from=payload.root.year_from,
        year_to=payload.root.year_to,
        iterations=0,
    )
    session.add(root)
    await session.flush()

    generated_row = None
    if payload.generated is not None:
        generated_row = SessionInput(
            session_id=research_session.id,
            parent_id=root.id,
            theme=payload.generated.theme,
            description=payload.generated.description,
            area_of_study=payload.root.area_of_study,
            keywords=payload.root.keywords,
            year_from=payload.root.year_from,
            year_to=payload.root.year_to,
            iterations=payload.generated.iterations,
        )
        session.add(generated_row)

    await session.commit()
    await session.refresh(research_session)
    await session.refresh(root)
    if generated_row is not None:
        await session.refresh(generated_row)

    logger.info(
        "session_finalized",
        session_id=research_session.id,
        root_input_id=root.id,
        generated_input_id=generated_row.id if generated_row else None,
    )

    return SuccessResponse(
        data=SessionInputFinalizeResponse(
            session_id=research_session.id,
            session_public_id=research_session.public_id,
            session_name=research_session.name,
            root=SessionInputRow.model_validate(root),
            generated=SessionInputRow.model_validate(generated_row) if generated_row else None,
        )
    )
