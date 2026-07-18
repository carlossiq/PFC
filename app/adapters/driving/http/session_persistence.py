"""
Shared persistence logic for creating or updating a research_session and its
session_input/session_probe_query rows from a SessionInputSaveRequest.

Used by both POST /session-input (new session) and PUT /research-session/{id}
(update an existing, previously-saved session) - kept as a plain adapter-layer
helper (not a repository/service abstraction) to match the direct-ORM style
already used throughout this session-centric flow.
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.session_probe_documents import (
    sync_probe_query_articles,
    sync_probe_query_patents,
    sync_probe_query_terms,
)
from db.research_session_models import ResearchSession, SessionAiCall, SessionInput, SessionProbeQuery
from schemas.session_input import (
    SessionAiCallInput,
    SessionAiCallRow,
    SessionInputGenerated,
    SessionInputRoot,
    SessionInputRow,
    SessionInputSaveRequest,
    SessionInputSaveResponse,
    SessionProbeQueryInput,
    SessionProbeQueryRow,
)


def apply_root_fields(row: SessionInput, root: SessionInputRoot) -> None:
    row.theme = root.theme
    row.description = root.description
    row.area_of_study = root.area_of_study
    row.keywords = root.keywords
    row.year_from = root.year_from
    row.year_to = root.year_to


def apply_generated_fields(
    row: SessionInput, generated: SessionInputGenerated, root: SessionInputRoot
) -> None:
    row.theme = generated.theme
    row.description = generated.description
    row.area_of_study = root.area_of_study
    row.keywords = root.keywords
    row.year_from = root.year_from
    row.year_to = root.year_to
    row.iterations = generated.iterations


def apply_probe_query_fields(row: SessionProbeQuery, item: SessionProbeQueryInput) -> None:
    row.tipo = item.tipo
    row.query_text = item.query_text
    row.fields = item.fields
    row.year_from = item.year_from
    row.year_to = item.year_to
    row.complexity_score = item.complexity_score
    row.complexity_level = item.complexity_level
    row.iterations = item.iterations
    row.result_count = item.result_count


async def persist_session_input(
    session: AsyncSession,
    research_session: ResearchSession,
    payload: SessionInputSaveRequest,
) -> SessionInputSaveResponse:
    """Upsert de root/generated/probe_queries em `research_session` (nova ou
    existente); espera `.inputs`/`.probe_queries` já carregados (vazios numa
    sessão recém-criada)."""
    research_session.name = payload.name
    # completed_at só é setado na transição pra completed (ou se a sessão já
    # tiver sido finalizada antes e completed_at ainda não existir, ex: linha
    # antiga anterior a essa coluna) - salvar progresso de novo numa sessão já
    # completa não deve empurrar a data de conclusão pra frente.
    if payload.completed and research_session.completed_at is None:
        research_session.completed_at = datetime.utcnow()
    elif not payload.completed:
        research_session.completed_at = None
    research_session.completed = payload.completed

    root = next((i for i in research_session.inputs if i.parent_id is None), None)
    if root is None:
        root = SessionInput(session_id=research_session.id, parent_id=None, iterations=0)
        session.add(root)
        research_session.inputs.append(root)
    apply_root_fields(root, payload.root)
    await session.flush()

    generated_row = next(
        (i for i in research_session.inputs if i.parent_id == root.id), None
    )
    if payload.generated is not None:
        if generated_row is None:
            generated_row = SessionInput(
                session_id=research_session.id, parent_id=root.id, iterations=0
            )
            session.add(generated_row)
            research_session.inputs.append(generated_row)
        apply_generated_fields(generated_row, payload.generated, payload.root)
    elif generated_row is not None:
        # payload sem `generated`: usuário voltou pro input cru - remove o
        # resquício da geração/refinamento anterior.
        research_session.inputs.remove(generated_row)
        await session.delete(generated_row)
        generated_row = None

    existing_by_fonte_tipo = {(q.fonte, q.tipo): q for q in research_session.probe_queries}
    probe_query_rows = []
    # Linhas de probe (tipo=None) primeiro, garantindo que a linha da query
    # final (tipo=variante escolhida) já encontre o id da linha de probe da
    # mesma fonte pra preencher parent_id (auto-relacionamento, mesma ideia
    # de SessionInput.parent_id).
    probe_row_by_fonte: dict[str, SessionProbeQuery] = {}
    sorted_items = sorted(payload.probe_queries, key=lambda item: item.tipo is not None)
    for item in sorted_items:
        row = existing_by_fonte_tipo.get((item.fonte, item.tipo))
        if row is None:
            row = SessionProbeQuery(session_id=research_session.id, fonte=item.fonte, tipo=item.tipo)
            session.add(row)
        apply_probe_query_fields(row, item)
        if item.tipo is not None:
            parent = probe_row_by_fonte.get(item.fonte)
            if parent is not None:
                row.parent_id = parent.id
        probe_query_rows.append(row)
        await session.flush()  # garante row.id antes de sincronizar os links de documentos
        if item.tipo is None:
            probe_row_by_fonte[item.fonte] = row
        if item.fonte == "ops" and item.patents:
            await sync_probe_query_patents(session, row, item.patents)
        elif item.fonte == "scopus" and item.articles:
            await sync_probe_query_articles(session, row, item.articles)
        if item.tipo is None and item.terms:
            await sync_probe_query_terms(session, row, [t.model_dump() for t in item.terms])
    # Fontes/tipos que existiam no banco mas não vieram no payload são
    # preservados - não há hoje um fluxo de "desselecionar" uma query já
    # escolhida (nem de probe, nem de query final).

    # ai_calls é um log append-only (não upsert): o frontend só reenvia as
    # chamadas de IA medidas desde o último save, então cada item vira uma
    # linha nova.
    ai_call_rows = [
        SessionAiCall(session_id=research_session.id, **item.model_dump())
        for item in payload.ai_calls
    ]
    for row in ai_call_rows:
        session.add(row)

    await session.commit()
    await session.refresh(research_session)
    await session.refresh(root)
    if generated_row is not None:
        await session.refresh(generated_row)
    for row in probe_query_rows:
        await session.refresh(row)
    for row in ai_call_rows:
        await session.refresh(row)

    return SessionInputSaveResponse(
        session_id=research_session.id,
        session_public_id=research_session.public_id,
        session_name=research_session.name,
        completed=research_session.completed,
        root=SessionInputRow.model_validate(root),
        generated=SessionInputRow.model_validate(generated_row) if generated_row else None,
        probe_queries=[SessionProbeQueryRow.model_validate(row) for row in probe_query_rows],
        ai_calls=[SessionAiCallRow.model_validate(row) for row in ai_call_rows],
    )
