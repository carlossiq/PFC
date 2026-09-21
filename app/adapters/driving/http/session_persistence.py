"""
Shared persistence logic for creating or updating a research_session and its
session_input/session_probe_query rows from a SessionInputSaveRequest.

Used by both POST /session-input (new session) and PUT /research-session/{id}
(update an existing, previously-saved session) - kept as a plain adapter-layer
helper (not a repository/service abstraction) to match the direct-ORM style
already used throughout this session-centric flow.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.session_probe_documents import (
    sync_probe_query_articles,
    sync_probe_query_patents,
    sync_probe_query_terms,
)
from app.core.ports.outbound.storage_port import StoragePort
from core.logging import get_logger
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

logger = get_logger(__name__)


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


_PROBE_QUERY_UNIQUE_CONSTRAINT = "uq_session_probe_query_session_fonte_tipo"


async def _get_or_create_probe_query(
    session: AsyncSession,
    session_id: int,
    item: SessionProbeQueryInput,
    existing_by_fonte_tipo: dict[tuple[str, Optional[str]], SessionProbeQuery],
) -> SessionProbeQuery:
    """
    Busca a linha (session_id, fonte, tipo) já carregada em
    `existing_by_fonte_tipo` (lookup construído a partir de
    research_session.probe_queries no início de persist_session_input); se
    não existir, cria - protegido contra a corrida de duas requisições
    concorrentes pra mesma sessão criando a mesma linha ao mesmo tempo
    (gerava um IntegrityError bruto em uq_session_probe_query_session_fonte_tipo -
    caso real observado quando o React 18 StrictMode disparava
    useChartCreation.ts duas vezes; ver o fix lá também, que evita a
    corrida na origem - isso aqui é a segunda camada de defesa, pra
    qualquer outra causa de requisições concorrentes na mesma sessão).

    Cria dentro de um SAVEPOINT (begin_nested): se a constraint única
    disparar (a outra requisição venceu a corrida e commitou primeiro),
    descarta só essa tentativa (rollback até o savepoint, não a transação
    inteira) e busca no banco a linha que a outra requisição acabou de
    criar, em vez de deixar o erro subir pro chamador.

    Aplica apply_probe_query_fields ANTES do flush (não depois) pro caso de
    linha nova - query_text é NOT NULL, então flushar só
    session_id/fonte/tipo sem o resto dos campos violaria essa constraint
    antes mesmo de chegar na de unicidade. O chamador aplica os campos de
    novo depois (idempotente) pro caso "já existia"/"recuperado da corrida".
    """
    fonte, tipo = item.fonte, item.tipo
    row = existing_by_fonte_tipo.get((fonte, tipo))
    if row is not None:
        return row

    row = SessionProbeQuery(session_id=session_id, fonte=fonte, tipo=tipo)
    apply_probe_query_fields(row, item)
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
    except IntegrityError as exc:
        # exc.orig aqui é o wrapper do dialect asyncpg do SQLAlchemy
        # (AsyncAdapt_asyncpg_dbapi.IntegrityError), não a exceção asyncpg
        # crua - não expõe `constraint_name` como atributo (só existiria na
        # exceção original do asyncpg, um nível abaixo). `sqlstate` (código
        # Postgres padrão, "23505" = unique_violation) e o texto da mensagem
        # são o que sobra pra identificar a violação com segurança sem
        # confundir com qualquer outra IntegrityError (ex: NOT NULL).
        is_unique_violation = getattr(exc.orig, "sqlstate", None) == "23505"
        if not is_unique_violation or _PROBE_QUERY_UNIQUE_CONSTRAINT not in str(exc.orig):
            raise
        # Nada de session.expunge(row) aqui - begin_nested() já expunge
        # sozinho qualquer objeto novo adicionado dentro do bloco quando dá
        # rollback pro savepoint (comportamento documentado do SQLAlchemy);
        # chamar expunge() de novo bateria em "Instance ... is not present
        # in this Session".
        logger.warning(
            "session_probe_query_race_recovered",
            session_id=session_id,
            fonte=fonte,
            tipo=tipo,
        )
        result = await session.execute(
            select(SessionProbeQuery).where(
                SessionProbeQuery.session_id == session_id,
                SessionProbeQuery.fonte == fonte,
                SessionProbeQuery.tipo == tipo,
            )
        )
        row = result.scalar_one()

    existing_by_fonte_tipo[(fonte, tipo)] = row
    return row


async def persist_session_input(
    session: AsyncSession,
    research_session: ResearchSession,
    payload: SessionInputSaveRequest,
    storage: StoragePort,
) -> SessionInputSaveResponse:
    """Upsert de root/generated/probe_queries em `research_session` (nova ou
    existente); espera `.inputs`/`.probe_queries` já carregados (vazios numa
    sessão recém-criada), e `.probe_queries[].charts` também já carregado
    (`selectinload`) se a sessão já existir - necessário pra deletar os
    gráficos no MinIO de uma query final superada sem lazy-load assíncrono
    (ver o loop de "Query final superada" abaixo)."""
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
        row = await _get_or_create_probe_query(session, research_session.id, item, existing_by_fonte_tipo)
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

    # Query final superada: se o payload traz um tipo novo pra uma fonte que
    # já tinha outro tipo final persistido (ex.: usuário trocou de "balanced"
    # pra "specific"), a linha antiga não serve pra mais nada - é deletada
    # (cascade cuida de patent_links/article_links/term_links). Linhas de
    # probe (tipo=None) e fontes/tipos que simplesmente não vieram no payload
    # continuam preservadas como antes - não há fluxo de "desselecionar" pra
    # esses casos, só pra variante de query final substituída.
    incoming_final_tipo_by_fonte = {
        item.fonte: item.tipo for item in payload.probe_queries if item.tipo is not None
    }
    for (fonte, tipo), row in list(existing_by_fonte_tipo.items()):
        if tipo is None:
            continue
        incoming_tipo = incoming_final_tipo_by_fonte.get(fonte)
        if incoming_tipo is not None and incoming_tipo != tipo:
            # Antes de deletar a linha, apaga os objetos dela no MinIO -
            # cascade="all, delete-orphan" em SessionProbeQuery.charts cuida
            # da linha session_chart em si (Postgres), mas não alcança o
            # storage externo, então sem isso o objeto ficaria "sem pai" lá.
            # Falha de storage aqui não impede o resto do save (mesma
            # filosofia de "melhor esforço" do upload em ReportService) -
            # só fica um objeto órfão no MinIO pra limpar depois.
            for chart in row.charts:
                try:
                    await storage.delete(chart.object_key)
                except Exception as exc:
                    logger.warning(
                        "session_chart_storage_delete_failed",
                        probe_query_id=row.id,
                        object_key=chart.object_key,
                        error=str(exc),
                    )
            # Removê-la da coleção basta - cascade="all, delete-orphan" em
            # probe_queries já marca a linha órfã pra deleção no flush
            # (delete() explícito aqui também colidia com esse cascade e
            # quebrava o flush).
            research_session.probe_queries.remove(row)

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
        # `charts` faz parte de SessionProbeQueryRow (ver SessionCard no
        # frontend) e é uma relationship ORM de verdade - sem carregá-la
        # aqui, o model_validate abaixo tentaria lazy-load-lá num contexto
        # async e quebraria (MissingGreenlet). `attribute_names` faz o
        # refresh carregar essa relationship especificamente, sem re-buscar
        # as colunas escalares de novo (já cobertas pelo refresh acima).
        await session.refresh(row, attribute_names=["charts"])
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
