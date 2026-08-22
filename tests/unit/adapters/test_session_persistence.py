"""
Testa a lógica de upsert/substituição de session_probe_query em
persist_session_input - em especial, que trocar a variante da query final
(tipo) para uma mesma fonte deleta a linha anterior em vez de deixá-la
órfã (ver session_persistence.py).

Usa um banco SQLite em memória com o schema ativo (db.research_session_models.Base),
diferente do fixture `db_session` em tests/conftest.py, que cria tabelas a
partir do schema legado (db.models.Base) e não serve pra este módulo.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker

from app.adapters.driving.http.session_persistence import persist_session_input
from db.research_session_models import Base, ResearchSession, SessionChart, SessionProbeQuery
from schemas.session_input import (
    SessionInputRoot,
    SessionInputSaveRequest,
    SessionProbeQueryInput,
)


class FakeStoragePort:
    """StoragePort fake em memória - substitui o MinIO real nos testes."""

    def __init__(self) -> None:
        self.uploaded: dict[str, bytes] = {}
        self.deleted_keys: list[str] = []

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.uploaded[key] = data

    async def download(self, key: str) -> bytes:
        return self.uploaded[key]

    async def delete(self, key: str) -> None:
        self.deleted_keys.append(key)
        self.uploaded.pop(key, None)

    async def ensure_bucket(self) -> None:
        pass


@pytest_asyncio.fixture
async def session_maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield maker

    await engine.dispose()


@pytest.fixture
def storage():
    return FakeStoragePort()


async def _create_empty_session(session_maker) -> int:
    async with session_maker() as session:
        research_session = ResearchSession(name="sessao teste", completed=False)
        session.add(research_session)
        await session.commit()
        return research_session.id


async def _save(session_maker, storage, session_id: int, fonte: str, tipo: str, query_text: str) -> None:
    """Simula um save/update real: recarrega a sessão (com as coleções que
    persist_session_input acessa de forma síncrona), manda a linha de probe
    da fonte + a linha final com o `tipo` escolhido, como o frontend faz."""
    async with session_maker() as session:
        stmt = (
            select(ResearchSession)
            .where(ResearchSession.id == session_id)
            .options(
                selectinload(ResearchSession.inputs),
                selectinload(ResearchSession.probe_queries).selectinload(SessionProbeQuery.charts),
            )
        )
        research_session = (await session.execute(stmt)).scalar_one()

        payload = SessionInputSaveRequest(
            name="sessao teste",
            root=SessionInputRoot(theme="tema de teste"),
            probe_queries=[
                SessionProbeQueryInput(fonte=fonte, tipo=None, query_text="query probe"),
                SessionProbeQueryInput(fonte=fonte, tipo=tipo, query_text=query_text),
            ],
        )
        await persist_session_input(session, research_session, payload, storage)


@pytest.mark.asyncio
async def test_trocar_variante_da_query_final_deleta_a_antiga(session_maker, storage):
    session_id = await _create_empty_session(session_maker)

    await _save(session_maker, storage, session_id, fonte="ops", tipo="balanced", query_text="query balanced")
    await _save(session_maker, storage, session_id, fonte="ops", tipo="specific", query_text="query specific")

    async with session_maker() as session:
        final_rows = (
            (
                await session.execute(
                    select(SessionProbeQuery).where(
                        SessionProbeQuery.session_id == session_id,
                        SessionProbeQuery.fonte == "ops",
                        SessionProbeQuery.tipo.isnot(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert [row.tipo for row in final_rows] == ["specific"]
        assert final_rows[0].query_text == "query specific"

        probe_rows = (
            (
                await session.execute(
                    select(SessionProbeQuery).where(
                        SessionProbeQuery.session_id == session_id,
                        SessionProbeQuery.fonte == "ops",
                        SessionProbeQuery.tipo.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(probe_rows) == 1


@pytest.mark.asyncio
async def test_resalvar_a_mesma_variante_atualiza_a_linha_em_vez_de_duplicar(session_maker, storage):
    session_id = await _create_empty_session(session_maker)

    await _save(session_maker, storage, session_id, fonte="ops", tipo="balanced", query_text="query v1")
    await _save(session_maker, storage, session_id, fonte="ops", tipo="balanced", query_text="query v2")

    async with session_maker() as session:
        final_rows = (
            (
                await session.execute(
                    select(SessionProbeQuery).where(
                        SessionProbeQuery.session_id == session_id,
                        SessionProbeQuery.fonte == "ops",
                        SessionProbeQuery.tipo.isnot(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(final_rows) == 1
        assert final_rows[0].query_text == "query v2"


@pytest.mark.asyncio
async def test_duas_fontes_diferentes_nao_se_afetam(session_maker, storage):
    session_id = await _create_empty_session(session_maker)

    await _save(session_maker, storage, session_id, fonte="ops", tipo="balanced", query_text="query ops")
    await _save(session_maker, storage, session_id, fonte="scopus", tipo="generic", query_text="query scopus")

    async with session_maker() as session:
        final_rows = (
            (
                await session.execute(
                    select(SessionProbeQuery).where(
                        SessionProbeQuery.session_id == session_id,
                        SessionProbeQuery.tipo.isnot(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        assert {(row.fonte, row.tipo) for row in final_rows} == {("ops", "balanced"), ("scopus", "generic")}


@pytest.mark.asyncio
async def test_trocar_variante_deleta_grafico_do_storage_tambem(session_maker, storage):
    """Se a query final superada tinha um session_chart (gráfico já gerado
    pra ela), trocar de variante não pode só apagar a linha do Postgres
    (via cascade) - o objeto correspondente no MinIO também precisa sumir,
    senão fica órfão lá."""
    session_id = await _create_empty_session(session_maker)
    await _save(session_maker, storage, session_id, fonte="ops", tipo="balanced", query_text="query balanced")

    object_key = "sessions/1/probe_query_1/patent_s_curve.png"
    async with session_maker() as session:
        stale_row = (
            await session.execute(
                select(SessionProbeQuery).where(
                    SessionProbeQuery.session_id == session_id,
                    SessionProbeQuery.fonte == "ops",
                    SessionProbeQuery.tipo == "balanced",
                )
            )
        ).scalar_one()
        session.add(
            SessionChart(probe_query_id=stale_row.id, document_type="patent", chart_type="s_curve", object_key=object_key)
        )
        await session.commit()
    storage.uploaded[object_key] = b"fake-png-bytes"

    await _save(session_maker, storage, session_id, fonte="ops", tipo="specific", query_text="query specific")

    assert object_key in storage.deleted_keys
    assert object_key not in storage.uploaded

    async with session_maker() as session:
        remaining_charts = (await session.execute(select(SessionChart))).scalars().all()
        assert remaining_charts == []
