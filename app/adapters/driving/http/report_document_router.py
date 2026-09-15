"""
Endpoints do relatório de prospecção em LaTeX (padrão REPTEC/AGITEC - ver
notes/REPTEC_001_2023_TETRA.pdf e app/core/services/report_writer_service.py).

Processo fatiado em rotas independentes por seção (pedido explícito do
usuário): uma rota calcula/persiste o contexto de RAG, outra envia esse
contexto pro LLM e persiste o texto gerado - cada seção de IA passa pelas
duas, em sequência, permitindo o front mostrar exatamente qual etapa está
em andamento e mantendo cada chamada de LLM restrita ao prompt de UMA
seção (não o relatório inteiro). Seções fixas/locais (Metodologia,
Referências, Referências Bibliográficas, Capa/Sumário/Assinaturas) têm rota
própria, sem LLM/RAG. A montagem do .tex é sempre só-texto (nunca compila
PDF); compilação é rota separada, sob demanda.

Nenhuma rota aqui toca nos dados/rotas de app/adapters/driving/http/report_router.py
(gráficos) - só lê o que já foi persistido por elas (SessionChart).
"""

from __future__ import annotations

import base64
from collections import Counter
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.dependencies import get_db_session
from app.adapters.driving.http.report_router import _resolve_final_probe_query_id
from app.core.services.report_writer_service import RAGUnavailableError, ReportWriterService, escape_latex
from config.prompts.report_static_sections import DEFAULT_BIBLIOGRAPHY, DEFAULT_SIGNATURES, render_metodologia
from core.config import settings
from core.logging import get_logger
from db.research_session_models import (
    Article,
    Patent,
    ProbeQueryArticle,
    ProbeQueryPatent,
    ResearchSession,
    SessionChart,
    SessionInput,
    SessionProbeQuery,
    SessionReport,
    SessionReportSection,
)
from schemas.report_document import (
    AssembleRequest,
    AssembleResponse,
    CompilePdfResponse,
    LLMTestRequest,
    LLMTestResponse,
    SectionGenerateResponse,
    SectionRagResponse,
    SignaturesInput,
    StaticSectionsRequest,
    StaticSectionsResponse,
)
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/report", tags=["report-document"])

_CHART_CAPTIONS: dict[tuple[str, str], str] = {
    ("patent", "s_curve"): "Curva S e Evolução Temporal — Patentes",
    ("article", "s_curve"): "Curva S e Evolução Temporal — Artigos",
    ("patent", "top_applicants"): "Top Depositantes",
    ("patent", "top_inventors"): "Top Inventores",
    ("article", "top_authors"): "Top Autores",
    ("article", "top_journals"): "Top Periódicos",
    ("patent", "cpc_distribution"): "Distribuição por CPC",
    ("patent", "ipc_distribution"): "Distribuição por IPC",
    ("article", "field_of_study_distribution"): "Distribuição por Área de Estudo",
    ("patent", "geographic_distribution"): "Distribuição Geográfica — Patentes",
    ("article", "geographic_distribution"): "Distribuição Geográfica — Artigos",
    ("patent", "yearly_volume"): "Patentes por Ano",
    ("patent", "top10_heatmap"): "Top 10 — Patentes",
    ("article", "top10_heatmap"): "Top 10 — Artigos",
}


def _writer(request: Request) -> ReportWriterService:
    return request.app.state.container["services"]["report_writer"]


def _latex_svc(request: Request):
    return request.app.state.container["services"]["report_latex"]


def _text_generation(request: Request):
    return request.app.state.container["services"]["text_generation"]


async def _get_session_or_404(session: AsyncSession, session_id: int) -> ResearchSession:
    result = await session.execute(select(ResearchSession).where(ResearchSession.id == session_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


async def _get_session_theme_input(session: AsyncSession, session_id: int) -> Optional[SessionInput]:
    result = await session.execute(select(SessionInput).where(SessionInput.session_id == session_id))
    inputs = list(result.scalars().all())
    root = next((i for i in inputs if i.parent_id is None), None)
    if root is None:
        return None
    chosen = next((i for i in inputs if i.parent_id == root.id), None)
    return chosen or root


async def _fetch_final_patents_and_articles(
    session: AsyncSession, session_id: int
) -> tuple[list[Patent], list[Article]]:
    # Mesma abordagem de subquery IN (não JOIN + distinct) de report_router.py
    # - colunas JSON (applicants, cpc_codes, ...) não têm operador de
    # igualdade no Postgres, então SELECT DISTINCT na linha inteira quebra.
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
    patents = list((await session.execute(patent_stmt)).scalars().all())
    articles = list((await session.execute(article_stmt)).scalars().all())
    return patents, articles


def _patent_to_rag_dict(patent: Patent) -> dict[str, Any]:
    return {
        "title": patent.title,
        "abstract": patent.abstract,
        "year": patent.year,
        "applicants": patent.applicants,
        "cpc_codes": patent.cpc_codes,
        "country": patent.country,
    }


def _article_to_rag_dict(article: Article) -> dict[str, Any]:
    return {
        "title": article.title,
        "abstract": article.abstract,
        "year": article.year,
        "authors": article.authors,
        "journal_or_source": article.journal_or_source,
        "field_of_study": article.field_of_study,
    }


def _top_values(documents: list[dict[str, Any]], field: str, is_list: bool, n: int = 5) -> list[str]:
    if is_list:
        values = [str(v) for doc in documents for v in (doc.get(field) or []) if v]
    else:
        values = [str(doc[field]) for doc in documents if doc.get(field)]
    return [value for value, _ in Counter(values).most_common(n)]


def _build_report_data(
    theme_input: Optional[SessionInput],
    patents: list[dict[str, Any]],
    articles: list[dict[str, Any]],
) -> dict[str, Any]:
    """Monta o `data: dict` passado pra report_prompts.get_section_prompt -
    reaproveita só o que já está persistido (SessionInput + Patent/Article
    da busca final), sem recalcular nada que report_service.py já resolve
    de outra forma (curva S etc. ficam só nos gráficos embutidos no .tex,
    não recomputados aqui em número)."""
    return {
        "area_of_study": (theme_input.area_of_study if theme_input else None) or "",
        "keywords": (theme_input.keywords if theme_input else None) or [],
        "period_start": theme_input.year_from if theme_input else None,
        "period_end": theme_input.year_to if theme_input else None,
        "patent_count": len(patents),
        "article_count": len(articles),
        "top_applicants": [{"name": v} for v in _top_values(patents, "applicants", True)],
        "top_cpc_codes": _top_values(patents, "cpc_codes", True),
        "top_journals": [{"journal": v} for v in _top_values(articles, "journal_or_source", False)],
        "top_fields": _top_values(articles, "field_of_study", True),
    }


def _merge_signatures(payload: Optional[SignaturesInput]) -> dict[str, dict[str, str]]:
    """Assinaturas: nomes/postos default de config
    (config/prompts/report_static_sections.py), sobrescrevíveis por
    requisição - e mais tarde pelo front, sem mudar essa rota."""
    merged = {k: dict(v) for k, v in DEFAULT_SIGNATURES.items()}
    if payload is None:
        return merged
    for field in ("elaborado_por", "revisado_por", "aprovado_por"):
        block = getattr(payload, field)
        if block is not None:
            merged[field] = {"nome": escape_latex(block.nome), "posto_funcao": escape_latex(block.posto_funcao)}
    return merged


def _validate_ai_section_key(section_key: str) -> None:
    if not ReportWriterService.is_ai_section(section_key):
        raise HTTPException(
            status_code=422,
            detail=f"'{section_key}' não é uma seção de IA. Válidas: {ReportWriterService.ai_section_keys()}",
        )


async def _get_or_create_section_row(
    session: AsyncSession, session_id: int, section_key: str
) -> SessionReportSection:
    result = await session.execute(
        select(SessionReportSection).where(
            SessionReportSection.session_id == session_id,
            SessionReportSection.section_key == section_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = SessionReportSection(session_id=session_id, section_key=section_key)
        session.add(row)
    return row


@router.post("/llm-test", response_model=SuccessResponse[LLMTestResponse])
async def test_llm(payload: LLMTestRequest, request: Request) -> SuccessResponse[LLMTestResponse]:
    """Sanity check manual do LLM configurado (OLLAMA_BASE_URL/OLLAMA_API_KEY/
    OLLAMA_MODEL - Ollama local em dev ou endpoint da intranet em produção):
    envia um prompt livre e devolve a resposta crua, sem sessão/RAG. Não
    escreve nada no banco."""
    text_generation = _text_generation(request)
    try:
        response_text = await text_generation.generate(payload.prompt, system=payload.system)
    except Exception as exc:
        logger.error("llm_test_failed base_url=%s model=%s error=%s", settings.ollama_base_url, settings.ollama_model, exc)
        raise HTTPException(status_code=502, detail=f"Falha ao chamar o LLM: {exc}") from exc

    return SuccessResponse(
        data=LLMTestResponse(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            response=response_text,
        )
    )


@router.post(
    "/{session_id}/sections/{section_key}/rag",
    response_model=SuccessResponse[SectionRagResponse],
)
async def compute_section_rag_context(
    session_id: int,
    section_key: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[SectionRagResponse]:
    """Indexa (se ainda não indexado) os documentos da busca final dessa
    sessão no ChromaDB e recupera o contexto relevante pra essa seção -
    persiste em session_report_section.rag_context. Não chama o LLM."""
    _validate_ai_section_key(section_key)
    await _get_session_or_404(session, session_id)

    writer = _writer(request)
    patents, articles = await _fetch_final_patents_and_articles(session, session_id)

    try:
        await writer.ensure_session_indexed(
            session_id,
            [_patent_to_rag_dict(p) for p in patents],
            [_article_to_rag_dict(a) for a in articles],
        )
        rag_context = await writer.build_rag_context(session_id, section_key)
    except RAGUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    row = await _get_or_create_section_row(session, session_id, section_key)
    row.rag_context = rag_context
    row.status = "rag_done"
    await session.commit()

    logger.info("report_section_rag_computed session_id=%d section=%s", session_id, section_key)
    return SuccessResponse(data=SectionRagResponse(section_key=section_key, rag_context=rag_context, status=row.status))


@router.post(
    "/{session_id}/sections/{section_key}/generate",
    response_model=SuccessResponse[SectionGenerateResponse],
)
async def generate_section_text(
    session_id: int,
    section_key: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[SectionGenerateResponse]:
    """Gera o texto dessa seção via LLM, usando o contexto de RAG já
    persistido pela rota /rag (422 se ela ainda não rodou pra essa seção) -
    carrega só o prompt dessa seção, não o relatório inteiro."""
    _validate_ai_section_key(section_key)
    await _get_session_or_404(session, session_id)

    result = await session.execute(
        select(SessionReportSection).where(
            SessionReportSection.session_id == session_id,
            SessionReportSection.section_key == section_key,
        )
    )
    row = result.scalar_one_or_none()
    if row is None or row.rag_context is None:
        raise HTTPException(
            status_code=422,
            detail=f"Contexto de RAG ainda não calculado pra seção '{section_key}' - "
            "chame POST .../sections/{section_key}/rag primeiro.",
        )

    theme_input = await _get_session_theme_input(session, session_id)
    theme = theme_input.theme if theme_input else ""
    patents, articles = await _fetch_final_patents_and_articles(session, session_id)
    data = _build_report_data(
        theme_input,
        [_patent_to_rag_dict(p) for p in patents],
        [_article_to_rag_dict(a) for a in articles],
    )

    writer = _writer(request)
    try:
        generated_text = await writer.generate_section_text(section_key, theme, row.rag_context, data)
    except Exception as exc:
        logger.error("report_section_generate_failed session_id=%d section=%s error=%s", session_id, section_key, exc)
        raise HTTPException(status_code=502, detail=f"Falha ao gerar texto via LLM: {exc}") from exc

    row.generated_text = generated_text
    row.status = "generated"
    await session.commit()

    logger.info("report_section_generated session_id=%d section=%s", session_id, section_key)
    return SuccessResponse(
        data=SectionGenerateResponse(section_key=section_key, generated_text=generated_text, status=row.status)
    )


@router.post(
    "/{session_id}/sections/static",
    response_model=SuccessResponse[StaticSectionsResponse],
)
async def build_static_sections(
    session_id: int,
    payload: StaticSectionsRequest,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[StaticSectionsResponse]:
    """Monta Metodologia (fixa + interpolada localmente) e Referências
    Bibliográficas (fixas + adicionadas pelo usuário) - nunca passa por
    LLM/RAG (evita citação inventada). Capa/assinaturas ficam guardadas
    junto do payload, usadas só na montagem final (/assemble)."""
    await _get_session_or_404(session, session_id)
    theme_input = await _get_session_theme_input(session, session_id)

    # escape_latex aqui pelo mesmo motivo de ReportWriterService.generate_section_text:
    # texto solto (mesmo fixo, como o boilerplate da Metodologia que contém "P&D") não
    # é LaTeX válido por si só - invariante do sistema: tudo em
    # session_report_section.generated_text já sai daqui pronto pra injetar no
    # template, nunca precisa ser escapado de novo em /assemble.
    metodologia_text = escape_latex(
        render_metodologia(
            keywords=(theme_input.keywords if theme_input else None) or [],
            period_start=theme_input.year_from if theme_input else None,
            period_end=theme_input.year_to if theme_input else None,
            databases=payload.databases,
        )
    )
    bibliografia = [
        escape_latex(ref) for ref in (*DEFAULT_BIBLIOGRAPHY, *payload.referencias_bibliograficas_adicionais)
    ]

    for section_key, text in (
        ("metodologia", metodologia_text),
        ("referencias_bibliograficas", "\n".join(bibliografia)),
    ):
        row = await _get_or_create_section_row(session, session_id, section_key)
        row.generated_text = text
        row.status = "generated"
    await session.commit()

    return SuccessResponse(
        data=StaticSectionsResponse(
            metodologia=metodologia_text,
            referencias_administrativas=payload.referencias_administrativas,
            referencias_bibliograficas=bibliografia,
        )
    )


@router.post("/{session_id}/assemble", response_model=SuccessResponse[AssembleResponse])
async def assemble_report_tex(
    session_id: int,
    payload: AssembleRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[AssembleResponse]:
    """Monta o .tex a partir de tudo já persistido (seções de IA +
    estáticas) e dos gráficos já salvos no MinIO (SessionChart) - nunca
    dispara geração de gráfico novo nem compila PDF (ver /compile-pdf,
    rota separada, só sob demanda)."""
    await _get_session_or_404(session, session_id)

    sections_result = await session.execute(
        select(SessionReportSection).where(SessionReportSection.session_id == session_id)
    )
    sections_by_key = {row.section_key: row for row in sections_result.scalars().all()}

    all_keys = [*ReportWriterService.ai_section_keys(), "metodologia", "referencias_bibliograficas"]
    sections_missing = [key for key in all_keys if key not in sections_by_key or not sections_by_key[key].generated_text]

    def _text(key: str) -> str:
        row = sections_by_key.get(key)
        return row.generated_text if row and row.generated_text else "[Seção ainda não gerada]"

    charts_result = await session.execute(
        select(SessionChart)
        .join(SessionProbeQuery, SessionProbeQuery.id == SessionChart.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
    )
    charts_cientificas: list[dict[str, str]] = []
    charts_tecnologicas: list[dict[str, str]] = []
    charts_ciclo_vida: list[dict[str, str]] = []
    chart_object_keys: list[str] = []
    for chart in charts_result.scalars().all():
        caption = _CHART_CAPTIONS.get((chart.document_type, chart.chart_type), chart.chart_type)
        entry = {"filename": chart.object_key.rsplit("/", 1)[-1], "caption": caption}
        chart_object_keys.append(chart.object_key)
        if chart.chart_type == "s_curve":
            charts_ciclo_vida.append(entry)
        elif chart.document_type == "article":
            charts_cientificas.append(entry)
        else:
            charts_tecnologicas.append(entry)

    # numero/ano/tema/referencias_administrativas vêm direto do corpo da
    # requisição (nunca passaram por session_report_section, diferente das
    # demais chaves abaixo, todas já pré-escapadas na hora de serem
    # persistidas) - escapar aqui, no único ponto onde entram no pipeline.
    ref_biblio_text = _text("referencias_bibliograficas")
    context = {
        "numero": escape_latex(payload.numero),
        "ano": escape_latex(payload.ano),
        "tema": escape_latex(payload.tema),
        "finalidade": _text("finalidade"),
        "objetivo": _text("objetivo"),
        "introducao": _text("introducao"),
        "referencias_administrativas": [escape_latex(ref) for ref in payload.referencias_administrativas],
        "metodologia": _text("metodologia"),
        "informacoes_cientificas": _text("informacoes_cientificas"),
        "informacoes_tecnologicas": _text("informacoes_tecnologicas"),
        "tendencias_ciclo_vida": _text("tendencias_ciclo_vida"),
        "charts_cientificas": charts_cientificas,
        "charts_tecnologicas": charts_tecnologicas,
        "charts_ciclo_vida": charts_ciclo_vida,
        "conclusao": _text("conclusao"),
        "referencias_bibliograficas": ref_biblio_text.split("\n") if ref_biblio_text else [],
        "assinaturas": _merge_signatures(payload.assinaturas),
    }

    latex_svc = _latex_svc(request)
    result = await latex_svc.render_and_upload_tex(session_id, context, chart_object_keys)

    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    if report_row is None:
        report_row = SessionReport(session_id=session_id, tex_object_key=result["tex_object_key"])
        session.add(report_row)
    else:
        report_row.tex_object_key = result["tex_object_key"]
        report_row.status = "tex_ready"
        report_row.pdf_object_key = None
    await session.commit()

    logger.info(
        "report_assembled session_id=%d sections_missing=%d charts_missing=%d",
        session_id,
        len(sections_missing),
        len(result["charts_missing"]),
    )
    return SuccessResponse(
        data=AssembleResponse(
            tex_object_key=result["tex_object_key"],
            tex_content=result["tex_content"],
            sections_missing=sections_missing,
            charts_missing=result["charts_missing"],
        )
    )


@router.post("/{session_id}/compile-pdf", response_model=SuccessResponse[CompilePdfResponse])
async def compile_report_pdf(
    session_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[CompilePdfResponse]:
    """Compila o .tex já montado (/assemble) em PDF - só roda quando o
    usuário decide (nunca automaticamente). Falha de compilação não apaga
    o .tex já persistido."""
    await _get_session_or_404(session, session_id)

    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    if report_row is None:
        raise HTTPException(
            status_code=422, detail="Relatório ainda não montado - chame POST .../assemble primeiro."
        )

    charts_result = await session.execute(
        select(SessionChart)
        .join(SessionProbeQuery, SessionProbeQuery.id == SessionChart.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
    )
    image_object_keys = [
        f"sessions/{session_id}/report/{chart.object_key.rsplit('/', 1)[-1]}"
        for chart in charts_result.scalars().all()
    ]

    latex_svc = _latex_svc(request)
    result = await latex_svc.compile_pdf(session_id, report_row.tex_object_key, image_object_keys)

    if not result["success"]:
        report_row.status = "pdf_failed"
        await session.commit()
        logger.warning("report_pdf_compile_failed session_id=%d", session_id)
        return SuccessResponse(data=CompilePdfResponse(success=False, log=result.get("log")))

    report_row.pdf_object_key = result["pdf_object_key"]
    report_row.status = "complete"
    await session.commit()

    logger.info("report_pdf_compiled session_id=%d", session_id)
    return SuccessResponse(
        data=CompilePdfResponse(
            success=True,
            pdf_object_key=result["pdf_object_key"],
            pdf_base64=base64.b64encode(result["pdf_bytes"]).decode("ascii"),
        )
    )
