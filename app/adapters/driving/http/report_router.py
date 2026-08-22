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
from fastapi.responses import FileResponse
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
    SessionChart,
    SessionProbeQuery,
)
from schemas.report import (
    ArticleSCurveRequest,
    ArticleSCurveResponse,
    PatentSCurveRequest,
    PatentYearlyVolumeRequest,
    PatentYearlyVolumeResponse,
    ReportGraphicsResponse,
    Top10HeatmapRequest,
    Top10HeatmapResponse,
)
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/report", tags=["report"])


def _svc(request: Request) -> ReportService:
    return request.app.state.container["services"]["report"]


async def _resolve_final_probe_query_id(session: AsyncSession, session_id: int, fonte: str) -> int:
    """Resolve o id da linha de query final (tipo IS NOT NULL) de uma fonte
    pra essa sessão - usado pra vincular um gráfico gerado à query que
    produziu os dados (ver SessionChart). Levanta 422 se não achar: com o
    salvamento garantido antes de pedir qualquer gráfico (ver
    useFinalSCurve.ts) e uma sessão finalizada não podendo mais ser reaberta
    (ver OutrosSteps.tsx), essa linha deveria sempre existir nesse ponto -
    não achá-la indica uma inconsistência real, não um caminho normal."""
    result = await session.execute(
        select(SessionProbeQuery.id).where(
            SessionProbeQuery.session_id == session_id,
            SessionProbeQuery.fonte == fonte,
            SessionProbeQuery.tipo.isnot(None),
        )
    )
    probe_query_id = result.scalar_one_or_none()
    if probe_query_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"Sessão {session_id} ainda não tem uma query final salva para a fonte '{fonte}'.",
        )
    return probe_query_id


async def _upsert_session_chart(
    session: AsyncSession,
    probe_query_id: int,
    document_type: str,
    chart_type: str,
    object_key: str,
    content_type: str = "image/png",
) -> None:
    """Grava (ou sobrescreve) a linha session_chart pra essa
    (probe_query_id, chart_type) - mesmo padrão de upsert por chave natural
    já usado em session_persistence.py."""
    existing = await session.execute(
        select(SessionChart).where(
            SessionChart.probe_query_id == probe_query_id,
            SessionChart.chart_type == chart_type,
        )
    )
    row = existing.scalar_one_or_none()
    if row is None:
        row = SessionChart(probe_query_id=probe_query_id, chart_type=chart_type)
        session.add(row)
    row.document_type = document_type
    row.object_key = object_key
    row.content_type = content_type
    await session.commit()


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


@router.get("/{session_id}/chart/{filename}")
async def get_report_chart(session_id: int, filename: str, request: Request) -> FileResponse:
    """Serve os bytes de um PNG já gerado por /graphics,
    /patents-yearly-volume ou /top10-heatmap para essa sessão - essas rotas
    só devolvem o manifesto (filename/path) do arquivo já salvo em disco
    pelo ReportService; esta é quem entrega a imagem de fato, pro <img> do
    frontend exibir e pro botão de download baixar.
    """
    path = _svc(request).resolve_chart_path(session_id, filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Chart not found")
    return FileResponse(path, media_type="image/png")


@router.post("/{session_id}/graphics", response_model=SuccessResponse[ReportGraphicsResponse])
async def generate_session_graphics(
    session_id: int,
    payload: PatentSCurveRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReportGraphicsResponse]:
    """Gera os gráficos de report para uma sessão.

    A curva S de patentes é calculada a partir do `patents_by_year`
    enviado no corpo da requisição, NÃO derivada do banco - normalmente é
    o mesmo dict que `/chat/final/search` já devolve para a fonte OPS, o
    que permite chamar esta rota logo após a busca final, sem depender da
    sessão já ter sido persistida. Os demais gráficos (top entidades,
    CPC/IPC, distribuição geográfica, curva S de artigos) continuam vindo
    dos documentos já persistidos da busca final (tipo != None) - não
    dispara nenhuma busca nova.
    """
    exists = await session.execute(select(ResearchSession.id).where(ResearchSession.id == session_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    ops_probe_query_id = await _resolve_final_probe_query_id(session, session_id, "ops")

    # IN (subquery) em vez de JOIN + .distinct() na linha inteira: Patent/Article
    # têm colunas JSON (applicants, cpc_codes, ...), e o tipo `json` do Postgres
    # não tem operador de igualdade - um SELECT DISTINCT sobre a linha completa
    # estoura "could not identify an equality operator for type json". A
    # subquery só precisa comparar patent_id/article_id (inteiro), então nunca
    # esbarra nisso, e dedup é automático (cada id aparece uma vez na tabela).
    patent_stmt = select(Patent).where(
        Patent.id.in_(
            select(ProbeQueryPatent.patent_id)
            .join(SessionProbeQuery, SessionProbeQuery.id == ProbeQueryPatent.probe_query_id)
            .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
        )
    )
    article_stmt = select(Article).where(
        Article.id.in_(
            select(ProbeQueryArticle.article_id)
            .join(SessionProbeQuery, SessionProbeQuery.id == ProbeQueryArticle.probe_query_id)
            .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
        )
    )
    patents = (await session.execute(patent_stmt)).scalars().all()
    articles = (await session.execute(article_stmt)).scalars().all()

    svc = _svc(request)
    result = svc.generate_session_report(
        session_id=session_id,
        patents=[_patent_to_dict(p) for p in patents],
        articles=[_article_to_dict(a) for a in articles],
    )

    try:
        patent_curve = await svc.generate_patent_s_curve(
            session_id=session_id,
            probe_query_id=ops_probe_query_id,
            patents_by_year=payload.patents_by_year,
            growth_threshold=payload.growth_threshold,
            saturation_threshold=payload.saturation_threshold,
            projection_end_year=payload.projection_end_year,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if patent_curve["chart"] is not None:
        result["charts"].append(patent_curve["chart"])
        object_key = patent_curve["chart"].get("object_key")
        if object_key:
            await _upsert_session_chart(session, ops_probe_query_id, "patent", "s_curve", object_key)
    else:
        result["skipped"].append(f"patent:s_curve ({patent_curve['skipped_reason']})")
    result["patent_s_curve_fit"] = patent_curve["fit"]

    logger.info(
        "report_graphics_requested",
        session_id=session_id,
        patents_used=result["patents_used"],
        articles_used=result["articles_used"],
        charts_count=len(result["charts"]),
        skipped_count=len(result["skipped"]),
    )

    return SuccessResponse(data=ReportGraphicsResponse(**result))


@router.post(
    "/{session_id}/article-s-curve",
    response_model=SuccessResponse[ArticleSCurveResponse],
)
async def generate_article_s_curve(
    session_id: int,
    payload: ArticleSCurveRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ArticleSCurveResponse]:
    """Gera a curva S (Fisher-Pry) de artigos, a partir do `articles_by_year`
    já enviado no corpo da requisição - equivalente à parte de curva S de
    `/graphics`, mas isolada numa rota própria porque não precisa (e não
    deveria) rodar `generate_session_report` junto: diferente de patentes,
    os documentos de artigo da busca final nunca são persistidos no banco
    hoje (ver buildProbeQueryPayload no frontend), então essa parte do
    report sempre viria vazia - sem sentido pagar esse custo aqui. Igual à
    curva S de patentes, o PNG é sempre devolvido em base64 na resposta;
    também tenta subir pro MinIO e vincular à query final de `scopus` (ver
    SessionChart), melhor-esforço - falha de storage não afeta a resposta.
    """
    exists = await session.execute(select(ResearchSession.id).where(ResearchSession.id == session_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    scopus_probe_query_id = await _resolve_final_probe_query_id(session, session_id, "scopus")

    svc = _svc(request)
    try:
        result = await svc.generate_article_s_curve(
            session_id=session_id,
            probe_query_id=scopus_probe_query_id,
            articles_by_year=payload.articles_by_year,
            growth_threshold=payload.growth_threshold,
            saturation_threshold=payload.saturation_threshold,
            projection_end_year=payload.projection_end_year,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if result["chart"] is not None:
        object_key = result["chart"].get("object_key")
        if object_key:
            await _upsert_session_chart(session, scopus_probe_query_id, "article", "s_curve", object_key)

    logger.info(
        "report_article_s_curve_requested",
        session_id=session_id,
        chart_generated=result["chart"] is not None,
    )

    return SuccessResponse(data=ArticleSCurveResponse(**result))


@router.post(
    "/{session_id}/patents-yearly-volume",
    response_model=SuccessResponse[PatentYearlyVolumeResponse],
)
async def generate_patent_yearly_volume(
    session_id: int,
    payload: PatentYearlyVolumeRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[PatentYearlyVolumeResponse]:
    """Gera o gráfico de barras de patentes por ano.

    Separado de `/graphics` porque o estilo atual da curva S
    (`ReportService._render_s_curve_chart`) não sobrepõe mais um gráfico de
    barras ao eixo de acumulado - o volume por ano de patentes passou a ser
    um gráfico próprio, gerado a partir do mesmo `patents_by_year` que
    `/chat/final/search` devolve para a fonte OPS, assim como o corpo desta
    rota é o mesmo formato aceito por `/graphics`.
    """
    exists = await session.execute(select(ResearchSession.id).where(ResearchSession.id == session_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    svc = _svc(request)
    result = svc.generate_patent_yearly_volume(session_id=session_id, patents_by_year=payload.patents_by_year)

    logger.info(
        "report_patent_yearly_volume_requested",
        session_id=session_id,
        chart_generated=result["chart"] is not None,
    )

    return SuccessResponse(data=PatentYearlyVolumeResponse(**result))


@router.post(
    "/{session_id}/top10-heatmap",
    response_model=SuccessResponse[Top10HeatmapResponse],
)
async def generate_top10_heatmap(
    session_id: int,
    payload: Top10HeatmapRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[Top10HeatmapResponse]:
    """Gera o heatmap top-10 (grid 5x2 + legenda em gradiente) a partir de
    uma distribuição label->contagem já agregada pelo chamador.

    Mesmo componente serve tanto para CPC de patentes (o dict `cpc` que
    `/chat/final/search` devolve para a fonte OPS) quanto para área de
    estudo de artigos ou qualquer outra distribuição desse formato - basta
    trocar `title`/`document_type` no corpo da requisição. Não depende de
    documentos persistidos no banco (só valida que a sessão existe).
    """
    exists = await session.execute(select(ResearchSession.id).where(ResearchSession.id == session_id))
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Session not found")

    svc = _svc(request)
    result = svc.generate_top10_heatmap(
        session_id=session_id,
        top10=payload.top10,
        title=payload.title,
        document_type=payload.document_type,
    )

    logger.info(
        "report_top10_heatmap_requested",
        session_id=session_id,
        document_type=payload.document_type,
        chart_generated=result["chart"] is not None,
    )

    return SuccessResponse(data=Top10HeatmapResponse(**result))
