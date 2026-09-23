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
import io
import re
import unicodedata
from collections import Counter
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.dependencies import get_db_session
from app.adapters.driving.http.report_router import _resolve_final_probe_query_id
from app.core.services.report_writer_service import (
    RAGUnavailableError,
    ReportWriterService,
    escape_latex,
    latex_comment,
)
from app.core.services.report_cover_image import REPORT_COVER_IMAGE_FILENAME, REPORT_COVER_IMAGE_OBJECT_KEY
from app.core.services.report_static_figures import REPORT_STATIC_FIGURES
from config.prompts.report_static_sections import (
    DEFAULT_BIBLIOGRAPHY,
    DEFAULT_SIGNATURES,
    legacy_metodologia_to_paragraph,
    merge_bibliography,
    render_metodologia,
)
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
    CompilePdfRequest,
    CompilePdfResponse,
    ReportChartItem,
    ReportChartsResponse,
    ReportDocumentResponse,
    ReportPdfResponse,
    ReportSectionStatus,
    SectionGenerateRequest,
    SectionGenerateResponse,
    SectionRagResponse,
    SignaturesInput,
    StaticSectionsRequest,
    StaticSectionsResponse,
)
from schemas.response import SuccessResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/report", tags=["report-document"])

# Título de cada figura no .tex (acima da imagem - a imagem em si não tem
# título desenhado, ver report_service.py) e, ao mesmo tempo, a LISTA DE
# GRÁFICOS PERMITIDOS no relatório: SessionChart pode ter linhas de
# chart_type fora daqui (ex.: top_inventors/top_authors/geographic_
# distribution do pipeline antigo de POST /report/{id}/graphics, gerados em
# sessões anteriores à remoção dele) - essas nunca entram no .tex nem no
# painel de imagens do editor (ver _is_report_chart).
# A distribuição de classificações de patentes é tratada como CPC no texto
# do relatório (pedido explícito do usuário), mesmo sendo IPC na origem (a
# OPS não devolve CPC na busca final, ver ChatService._aggregate_ops_final_items).
_CHART_CAPTIONS: dict[tuple[str, str], str] = {
    ("patent", "s_curve"): "Curva S e Evolução Temporal — Patentes",
    ("article", "s_curve"): "Curva S e Evolução Temporal — Artigos",
    ("patent", "top_depositants"): "Top 10 Depositantes",
    ("article", "top_institutions"): "Top 10 Instituições",
    ("patent", "yearly_volume"): "Patentes por Ano",
    ("article", "yearly_volume"): "Artigos por Ano",
    ("patent", "top10_heatmap"): "Top 10 Classificações (CPC)",
    ("article", "top10_heatmap"): "Top 10 Áreas de Estudo",
}


def _is_report_chart(chart: SessionChart) -> bool:
    return (chart.document_type, chart.chart_type) in _CHART_CAPTIONS



def _writer(request: Request) -> ReportWriterService:
    return request.app.state.container["services"]["report_writer"]


def _latex_svc(request: Request):
    return request.app.state.container["services"]["report_latex"]


def _storage(request: Request):
    return request.app.state.container["services"]["storage"]


# fonte (SessionProbeQuery.fonte) -> nome de exibição da base de dados, pra
# auto-preencher a Metodologia com a base REALMENTE usada nessa sessão (não
# a que está ativa em Configurações > Busca agora, que pode ter mudado desde
# então). lens_patent/lens_scholarly nunca aparecem como fonte de uma query
# final hoje (Lens ainda não tem paridade de busca final com OPS/Scopus),
# mas já ficam mapeados pra quando essa paridade existir.
_FONTE_DATABASE_LABELS: dict[str, str] = {
    "ops": "Espacenet (EPO/OPS)",
    "scopus": "Scopus",
    "lens_patent": "Lens.org",
    "lens_scholarly": "Lens.org",
}


async def _cover_image_exists(storage) -> bool:
    """StoragePort não tem `exists()` - só upload/download/delete (ver
    app/core/ports/outbound/storage_port.py) - então checar existência é
    tentar baixar e ver se estoura. A imagem de capa é pequena (padronizada
    em PROCESS_COVER_IMAGE_TARGET_SIZE, ver report_cover_image.py), então o
    custo de baixar só pra checar é desprezível."""
    try:
        await storage.download(REPORT_COVER_IMAGE_OBJECT_KEY)
        return True
    except Exception:
        return False


# Anexos: imagens avulsas que o usuário sobe no painel "Imagens" do editor
# do .tex (subpainel "Anexos") pra referenciar à mão no documento - ficam só
# no MinIO, sob um prefixo por sessão (sem tabela própria: a listagem é o
# próprio conteúdo do prefixo). Diferente dos gráficos gerados, podem ser
# excluídos pelo usuário.
_ATTACHMENT_EXTENSIONS = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}
_ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
_ATTACHMENT_FILENAME_RE = re.compile(r"^anexo-[a-z0-9-]+\.(png|jpg|jpeg)$")


def _attachments_prefix(session_id: int) -> str:
    return f"sessions/{session_id}/report/attachments/"


async def _list_attachment_keys(storage, session_id: int) -> list[str]:
    try:
        return sorted(await storage.list_keys(_attachments_prefix(session_id)))
    except Exception as exc:
        logger.warning("report_attachments_list_failed", session_id=session_id, error=str(exc))
        return []


def _attachment_filename(original: str, taken: set[str]) -> str:
    """Nome seguro pro \\includegraphics: "anexo-<slug>.<ext>" (só
    [a-z0-9-], sem espaço/acento/"_"), com sufixo numérico se já existir
    - o prefixo "anexo-" também impede colisão com os PNGs dos gráficos
    gerados, que dividem o mesmo diretório de compilação."""
    stem, _, ext = original.rpartition(".")
    ext = ext.lower()
    if not stem or ext not in _ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Formato não suportado - envie uma imagem PNG ou JPG.")
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_stem).strip("-")[:50] or "imagem"
    candidate = f"anexo-{slug}.{ext}"
    counter = 2
    while candidate in taken:
        candidate = f"anexo-{slug}-{counter}.{ext}"
        counter += 1
    return candidate


async def _detect_databases_used(session: AsyncSession, session_id: int) -> list[str]:
    detected: list[str] = []
    for fonte, label in _FONTE_DATABASE_LABELS.items():
        probe_query_id = await _resolve_final_probe_query_id(session, session_id, fonte, required=False)
        if probe_query_id is not None and label not in detected:
            detected.append(label)
    return detected


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
        # Inventores (pessoa), não depositantes (empresa) - usado pra
        # citação de autoria no texto gerado (ver
        # ReportWriterService._build_source_citation/ensure_session_indexed).
        "inventors": patent.inventors,
        "cpc_codes": patent.cpc_codes,
        "ipc_codes": patent.ipc_codes,
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
        # "top_cpc_codes" é lido de ipc_codes de propósito - patent.cpc_codes
        # fica sempre vazio (a OPS não retorna CPC nesse endpoint, só IPC;
        # ver ChatService._aggregate_ops_final_items). Chave preservada por
        # compatibilidade com SectionGenerateOverrides.top_cpc_codes.
        "top_cpc_codes": _top_values(patents, "ipc_codes", True),
        "top_journals": [{"journal": v} for v in _top_values(articles, "journal_or_source", False)],
        "top_fields": _top_values(articles, "field_of_study", True),
    }


def _apply_section_generate_overrides(data: dict[str, Any], payload: Optional[SectionGenerateRequest]) -> None:
    """Sobrescreve campos de `data` (ver _build_report_data, quase sempre
    0/vazio hoje) com as estatísticas agregadas que o front já tem em
    memória - None/lista vazia em `payload` preserva o valor já calculado,
    sem sobrescrever com "nada" por engano."""
    if payload is None:
        return
    if payload.article_count is not None:
        data["article_count"] = payload.article_count
    if payload.top_journals:
        data["top_journals"] = [{"journal": v} for v in payload.top_journals]
    if payload.top_fields:
        data["top_fields"] = payload.top_fields
    if payload.patent_count is not None:
        data["patent_count"] = payload.patent_count
    if payload.top_applicants:
        data["top_applicants"] = [{"name": v} for v in payload.top_applicants]
    if payload.top_cpc_codes:
        data["top_cpc_codes"] = payload.top_cpc_codes
    if payload.s_curve_phase is not None:
        data["s_curve_phase"] = payload.s_curve_phase
    if payload.growth_rate is not None:
        data["growth_rate"] = payload.growth_rate
    if payload.peak_year is not None:
        data["peak_year"] = payload.peak_year


_SIGNATURE_ROLE_LABELS = {
    "elaborado_por": "Elaborado por",
    "revisado_por": "Revisado por",
    "aprovado_por": "Aprovado por",
}


def _merge_signatures(payload: Optional[SignaturesInput]) -> dict[str, Any]:
    """Assinaturas: nomes/postos default de config
    (config/prompts/report_static_sections.py), sobrescrevíveis por
    requisição - cada papel aceita 1+ assinantes (ver SignaturesInput).

    Blocos em branco (nome OU posto/função vazios - inclusive o bloco
    default acima, nunca preenchido) são filtrados fora: "elaborado_por"
    nunca deveria sobrar vazio depois disso (o front bloqueia "Montar .tex"
    até ter pelo menos um assinante válido, ver ReportGeneration.tsx), mas
    "revisado_por"/"aprovado_por" são opcionais - quando sobram vazios,
    `{role}_comment` é preenchido com uma linha LaTeX comentada (ver
    latex_comment) pro template usar no lugar do bloco de assinatura (ver
    config/prompts/report_latex_template.py)."""
    merged: dict[str, Any] = {k: [dict(block) for block in v] for k, v in DEFAULT_SIGNATURES.items()}
    if payload is not None:
        for field in ("elaborado_por", "revisado_por", "aprovado_por"):
            blocks = getattr(payload, field)
            if blocks:
                merged[field] = [
                    {"nome": escape_latex(block.nome), "posto_funcao": escape_latex(block.posto_funcao)}
                    for block in blocks
                ]

    for field, label in _SIGNATURE_ROLE_LABELS.items():
        merged[field] = [block for block in merged[field] if block["nome"].strip() and block["posto_funcao"].strip()]
        merged[f"{field}_comment"] = latex_comment(label) if not merged[field] else None

    return merged


def _format_count_pt(count: int) -> str:
    """1800 -> "1.800" (separador de milhar pt-BR)."""
    return f"{count:,}".replace(",", ".")


def _quadro_busca_cell(label: str, query: Optional[str], count: Optional[int]) -> str:
    """Conteúdo (já escapado) de uma célula do Quadro de estratégias de
    busca - "Patentes (1.800) = <query>". "Disponível" exige query E
    contagem juntos - só um dos dois não é informação suficiente pra valer
    a pena mostrar como se fosse real; sem isso a célula fica com "—"."""
    if not query or count is None:
        return "—"
    return f"{label} ({_format_count_pt(count)}) = {escape_latex(query)}"


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
    payload: Optional[SectionGenerateRequest] = None,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[SectionGenerateResponse]:
    """Gera o texto dessa seção via LLM, usando o contexto de RAG já
    persistido pela rota /rag (422 se ela ainda não rodou pra essa seção) -
    carrega só o prompt dessa seção, não o relatório inteiro.

    `payload`, quando vem preenchido, sobrescreve os campos de
    `_build_report_data` com as estatísticas agregadas que o FRONT já tem em
    memória (ver SectionGenerateRequest) - necessário porque
    `_fetch_final_patents_and_articles` fica vazio na prática (os documentos
    da busca final nunca são persistidos em patent/article, só os da probe)."""
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
    _apply_section_generate_overrides(data, payload)

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

    detected_databases = await _detect_databases_used(session, session_id)
    all_databases = [*detected_databases, *(db for db in payload.databases if db not in detected_databases)]

    # escape_latex aqui pelo mesmo motivo de ReportWriterService.generate_section_text:
    # texto solto (mesmo fixo, como o boilerplate da Metodologia que contém "P&D") não
    # é LaTeX válido por si só - invariante do sistema: tudo em
    # session_report_section.generated_text já sai daqui pronto pra injetar no
    # template, nunca precisa ser escapado de novo em /assemble.
    # SessionInput.year_from/year_to (root do Step1) fica quase sempre null -
    # o ano é escolhido por query, não numa etapa global do wizard (ver
    # mapInputToSessionInputRoot no front) - payload.period_start/end (o
    # year_range da query final que o front já tem em mãos) tem prioridade
    # quando vier preenchido.
    period_start = payload.period_start if payload.period_start is not None else (
        theme_input.year_from if theme_input else None
    )
    period_end = payload.period_end if payload.period_end is not None else (
        theme_input.year_to if theme_input else None
    )
    metodologia_text = escape_latex(
        render_metodologia(
            keywords=(theme_input.keywords if theme_input else None) or [],
            period_start=period_start,
            period_end=period_end,
            databases=all_databases,
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
            databases_detected=detected_databases,
        )
    )


async def _assemble_document(
    session: AsyncSession,
    session_id: int,
    payload: AssembleRequest,
    request: Request,
) -> AssembleResponse:
    """Monta o .tex a partir de tudo já persistido (seções de IA +
    estáticas) e dos gráficos já salvos no MinIO (SessionChart) - nunca
    dispara geração de gráfico novo nem compila PDF (ver /compile-pdf, rota
    separada, só sob demanda). Persiste `payload` em
    SessionReport.assemble_payload, pra POST /{session_id}/reassemble poder
    remontar do zero (pegando correções de template/seções/gráficos/capa)
    sem pedir esses dados de novo - ver docstring do endpoint /reassemble
    pra por que isso importa (ponto de não-retorno do wizard)."""
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
    storage = _storage(request)
    charts_cientificas: list[dict[str, str]] = []
    charts_tecnologicas: list[dict[str, str]] = []
    charts_ciclo_vida: list[dict[str, str]] = []
    chart_object_keys: list[str] = []
    for chart in charts_result.scalars().all():
        if not _is_report_chart(chart):
            continue
        # Confere ANTES de referenciar no .tex - SessionChart.object_key
        # pode apontar pra um objeto que não existe mais no MinIO (dados
        # apagados/resetados fora de banda, por exemplo) - sem essa
        # checagem, o `\includegraphics{...}` do bloco abaixo sobreviveria
        # no documento apontando pra um arquivo que render_and_upload_tex
        # nunca conseguiria copiar, e o pdflatex falharia com "File not
        # found" na hora de compilar.
        try:
            await storage.download(chart.object_key)
        except Exception as exc:
            logger.warning(
                "report_chart_unavailable_at_assemble",
                session_id=session_id,
                object_key=chart.object_key,
                error=str(exc),
            )
            continue

        caption = escape_latex(_CHART_CAPTIONS[(chart.document_type, chart.chart_type)])
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
    quadro_busca = None
    if payload.quadro_busca is not None:
        qb = payload.quadro_busca
        if any((qb.patente_query, qb.patente_count is not None, qb.artigo_query, qb.artigo_count is not None)):
            quadro_busca = {
                "patente": _quadro_busca_cell("Patentes", qb.patente_query, qb.patente_count),
                "artigo": _quadro_busca_cell("Artigos", qb.artigo_query, qb.artigo_count),
            }

    # Decide se o bloco da imagem de capa entra no .tex (estrutura, fixada
    # aqui) - a montagem não roda de novo depois do ponto de não-retorno
    # (ver ReportGeneration.tsx), então uma sessão montada ANTES de qualquer
    # imagem ter sido configurada em Configurações > Geral nunca ganha o
    # bloco de volta sozinha. Já o CONTEÚDO da imagem (que bytes realmente
    # aparecem no PDF) é sempre resolvido de novo em cada recompilação (ver
    # compile_report_pdf), então atualizar a imagem afeta toda sessão cujo
    # .tex já referencia esse arquivo.
    has_cover_image = await _cover_image_exists(storage)

    # Obras fixas SEMPRE entram (merge_bibliography) - sessões montadas
    # antes de a Metodologia completa ir pro template persistiram só as 3
    # obras que o texto antigo citava.
    stored_biblio = sections_by_key.get("referencias_bibliograficas")
    stored_biblio_refs = (
        stored_biblio.generated_text.split("\n") if stored_biblio and stored_biblio.generated_text else []
    )
    context = {
        "numero": escape_latex(payload.numero),
        "ano": escape_latex(payload.ano),
        "tema": escape_latex(payload.tema),
        "capa_imagem": REPORT_COVER_IMAGE_FILENAME if has_cover_image else None,
        "finalidade": _text("finalidade"),
        "objetivo": _text("objetivo"),
        "introducao": _text("introducao"),
        "referencias_administrativas": [escape_latex(ref) for ref in payload.referencias_administrativas],
        "metodologia": legacy_metodologia_to_paragraph(_text("metodologia")),
        "quadro_busca": quadro_busca,
        "informacoes_cientificas": _text("informacoes_cientificas"),
        "informacoes_tecnologicas": _text("informacoes_tecnologicas"),
        "tendencias_ciclo_vida": _text("tendencias_ciclo_vida"),
        "charts_cientificas": charts_cientificas,
        "charts_tecnologicas": charts_tecnologicas,
        "charts_ciclo_vida": charts_ciclo_vida,
        "conclusao": _text("conclusao"),
        "referencias_bibliograficas": merge_bibliography(
            [escape_latex(ref) for ref in DEFAULT_BIBLIOGRAPHY], stored_biblio_refs
        ),
        "assinaturas": _merge_signatures(payload.assinaturas),
    }

    latex_svc = _latex_svc(request)
    result = await latex_svc.render_and_upload_tex(session_id, context, chart_object_keys)

    assemble_payload = payload.model_dump(mode="json")
    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    if report_row is None:
        report_row = SessionReport(
            session_id=session_id, tex_object_key=result["tex_object_key"], assemble_payload=assemble_payload
        )
        session.add(report_row)
    else:
        report_row.tex_object_key = result["tex_object_key"]
        report_row.status = "tex_ready"
        report_row.pdf_object_key = None
        report_row.assemble_payload = assemble_payload
    await session.commit()

    logger.info(
        "report_assembled session_id=%d sections_missing=%d charts_missing=%d",
        session_id,
        len(sections_missing),
        len(result["charts_missing"]),
    )
    return AssembleResponse(
        tex_object_key=result["tex_object_key"],
        tex_content=result["tex_content"],
        sections_missing=sections_missing,
        charts_missing=result["charts_missing"],
    )


@router.post("/{session_id}/assemble", response_model=SuccessResponse[AssembleResponse])
async def assemble_report_tex(
    session_id: int,
    payload: AssembleRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[AssembleResponse]:
    return SuccessResponse(data=await _assemble_document(session, session_id, payload, request))


@router.post("/{session_id}/reassemble", response_model=SuccessResponse[AssembleResponse])
async def reassemble_report_tex(
    session_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[AssembleResponse]:
    """Remonta o .tex do ZERO (mesma lógica de /assemble), reaproveitando os
    dados da capa (número/ano/tema/referências administrativas/assinaturas/
    quadro de busca) da última montagem bem-sucedida - existe pra recuperar
    uma sessão já finalizada (ponto de não-retorno, ver ReportGeneration.tsx)
    de um bug/ajuste no template ou nos dados (ex.: um gráfico que sumiu do
    MinIO, uma correção de LaTeX) sem precisar reabrir o wizard de pesquisa
    nem pedir esses dados de novo pro usuário. Sobrescreve qualquer edição
    manual feita no `.tex` desde a última montagem - por isso é uma ação
    explícita do usuário (botão "Remontar" na tela do documento), nunca
    automática."""
    await _get_session_or_404(session, session_id)

    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    if report_row is None or not report_row.assemble_payload:
        raise HTTPException(
            status_code=422,
            detail="Essa sessão ainda não tem uma montagem anterior pra reaproveitar - chame POST .../assemble primeiro.",
        )

    payload = AssembleRequest.model_validate(report_row.assemble_payload)
    return SuccessResponse(data=await _assemble_document(session, session_id, payload, request))


@router.post("/{session_id}/compile-pdf", response_model=SuccessResponse[CompilePdfResponse])
async def compile_report_pdf(
    session_id: int,
    request: Request,
    payload: Optional[CompilePdfRequest] = None,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[CompilePdfResponse]:
    """Compila o .tex já montado (/assemble) em PDF - só roda quando o
    usuário decide (nunca automaticamente). Falha de compilação não apaga
    o .tex já persistido.

    `payload.tex_content`, quando vem preenchido, é a edição livre feita na
    tela do documento (ver ReportDocumentEditor.tsx) - como essa edição só
    existe no front até este ponto (nenhuma outra rota a persiste), ela
    sobrescreve o `.tex` no storage ANTES de compilar, senão o backend
    compilaria a última versão MONTADA (/assemble), ignorando o que o
    usuário escreveu depois."""
    await _get_session_or_404(session, session_id)

    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    if report_row is None:
        raise HTTPException(
            status_code=422, detail="Relatório ainda não montado - chame POST .../assemble primeiro."
        )

    if payload is not None and payload.tex_content is not None:
        await _storage(request).upload(
            report_row.tex_object_key, payload.tex_content.encode("utf-8"), "text/x-tex"
        )

    charts_result = await session.execute(
        select(SessionChart)
        .join(SessionProbeQuery, SessionProbeQuery.id == SessionChart.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
    )
    storage = _storage(request)
    image_object_keys: list[str] = []
    for chart in charts_result.scalars().all():
        if not _is_report_chart(chart):
            continue
        candidate_key = f"sessions/{session_id}/report/{chart.object_key.rsplit('/', 1)[-1]}"
        # Confere que o "recorte" da imagem pra essa sessão (feito em
        # /assemble) realmente existe antes de mandar pro compilador -
        # ReportLatexService.compile_pdf baixa cada chave sem try/except, um
        # 404 aqui derrubaria a rota inteira em vez de devolver um "log" de
        # falha organizado (ex.: gráfico pulado no /assemble por já estar
        # ausente do MinIO na época, ver report_chart_unavailable_at_assemble).
        try:
            await storage.download(candidate_key)
            image_object_keys.append(candidate_key)
        except Exception as exc:
            logger.warning(
                "report_chart_snapshot_missing_at_compile",
                session_id=session_id,
                object_key=candidate_key,
                error=str(exc),
            )

    # Sempre a versão MAIS RECENTE da imagem de capa (chave global, não por
    # sessão) - diferente dos gráficos acima, que são fixados no momento do
    # /assemble, a capa é resolvida de novo em toda recompilação, pra
    # atualizar a imagem em Configurações > Geral valer pra qualquer sessão
    # que recompilar depois (mesmo uma já montada há tempos). Se o .tex não
    # referenciar o arquivo (sessão montada antes de existir capa
    # configurada), ele só fica sem uso no diretório de compilação - o
    # pdflatex não reclama de arquivo extra não referenciado.
    if await _cover_image_exists(storage):
        image_object_keys.append(REPORT_COVER_IMAGE_OBJECT_KEY)

    # Figuras fixas da Metodologia (madeo/kucharavy, chaves globais - ver
    # report_static_figures.py) e anexos enviados pelo usuário no editor -
    # mesmo raciocínio da capa: arquivo extra não referenciado não atrapalha.
    for object_key in REPORT_STATIC_FIGURES.values():
        try:
            await storage.download(object_key)
            image_object_keys.append(object_key)
        except Exception as exc:
            logger.warning("report_static_figure_missing_at_compile", object_key=object_key, error=str(exc))
    image_object_keys.extend(await _list_attachment_keys(storage, session_id))

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


@router.get("/{session_id}/document", response_model=SuccessResponse[ReportDocumentResponse])
async def get_report_document(
    session_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReportDocumentResponse]:
    """Estado atual do relatório dessa sessão - usado tanto pra retomar o
    checklist de seções (front decide, pelas seções já `generated`, de onde
    continuar) quanto pra reabrir uma sessão já finalizada direto na tela de
    documento (`.tex` + PDF), sem refazer o wizard de pesquisa. `has_report=False`
    (com o resto vazio) é o caminho normal pra sessão que nunca chamou
    /assemble ainda - não é erro."""
    await _get_session_or_404(session, session_id)

    sections_result = await session.execute(
        select(SessionReportSection).where(SessionReportSection.session_id == session_id)
    )
    sections = [
        ReportSectionStatus(section_key=row.section_key, status=row.status, generated_text=row.generated_text)
        for row in sections_result.scalars().all()
    ]

    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    if report_row is None:
        return SuccessResponse(data=ReportDocumentResponse(has_report=False, sections=sections))

    tex_content: Optional[str] = None
    try:
        tex_bytes = await _storage(request).download(report_row.tex_object_key)
        tex_content = tex_bytes.decode("utf-8")
    except Exception as exc:
        logger.warning("report_document_tex_download_failed", session_id=session_id, error=str(exc))

    return SuccessResponse(
        data=ReportDocumentResponse(
            has_report=True,
            report_status=report_row.status,
            tex_object_key=report_row.tex_object_key,
            tex_content=tex_content,
            pdf_available=report_row.pdf_object_key is not None,
            sections=sections,
        )
    )


@router.get("/{session_id}/pdf", response_model=SuccessResponse[ReportPdfResponse])
async def get_report_pdf(
    session_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReportPdfResponse]:
    """Baixa o PDF já compilado (persistido por /compile-pdf) - usado pra
    'Visualizar PDF' funcionar ao reabrir uma sessão sem precisar recompilar."""
    await _get_session_or_404(session, session_id)

    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    if report_row is None or report_row.pdf_object_key is None:
        raise HTTPException(status_code=404, detail="Essa sessão ainda não tem um PDF compilado.")

    pdf_bytes = await _storage(request).download(report_row.pdf_object_key)
    return SuccessResponse(data=ReportPdfResponse(pdf_base64=base64.b64encode(pdf_bytes).decode("ascii")))


@router.get("/{session_id}/charts", response_model=SuccessResponse[ReportChartsResponse])
async def get_report_charts(
    session_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReportChartsResponse]:
    """Lista (com PNG em base64) todos os gráficos já gerados pra busca final
    dessa sessão - alimenta o painel lateral de imagens da tela de edição do
    `.tex`, pra o usuário ver o que está disponível pra referenciar/mover no
    corpo do documento (mesma fonte que /assemble usa pra embutir os
    gráficos por padrão, ver _CHART_CAPTIONS)."""
    await _get_session_or_404(session, session_id)

    charts_result = await session.execute(
        select(SessionChart)
        .join(SessionProbeQuery, SessionProbeQuery.id == SessionChart.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
    )
    storage = _storage(request)
    items: list[ReportChartItem] = []
    for chart in charts_result.scalars().all():
        if not _is_report_chart(chart):
            continue
        try:
            png_bytes = await storage.download(chart.object_key)
        except Exception as exc:
            logger.warning("report_chart_download_failed", session_id=session_id, object_key=chart.object_key, error=str(exc))
            continue
        items.append(
            ReportChartItem(
                filename=chart.object_key.rsplit("/", 1)[-1],
                image_base64=base64.b64encode(png_bytes).decode("ascii"),
                chart_type=chart.chart_type,
                document_type=chart.document_type,
                caption=_CHART_CAPTIONS[(chart.document_type, chart.chart_type)],
                origin="generated",
            )
        )

    for object_key in await _list_attachment_keys(storage, session_id):
        filename = object_key.rsplit("/", 1)[-1]
        try:
            data = await storage.download(object_key)
        except Exception as exc:
            logger.warning("report_attachment_download_failed", session_id=session_id, object_key=object_key, error=str(exc))
            continue
        items.append(
            ReportChartItem(
                filename=filename,
                image_base64=base64.b64encode(data).decode("ascii"),
                chart_type="attachment",
                document_type="attachment",
                caption=filename,
                origin="attachment",
            )
        )

    return SuccessResponse(data=ReportChartsResponse(charts=items))


@router.post("/{session_id}/attachments", response_model=SuccessResponse[ReportChartItem])
async def upload_report_attachment(
    session_id: int,
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReportChartItem]:
    """Sobe uma imagem avulsa (anexo) pro painel de imagens do editor do
    .tex - fica disponível pra inserir no documento e é enviada ao
    compilador junto dos gráficos (ver compile_report_pdf)."""
    await _get_session_or_404(session, session_id)
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=422, detail="Arquivo vazio.")
    if len(raw_bytes) > _ATTACHMENT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Imagem maior que 10 MB.")

    storage = _storage(request)
    taken = {key.rsplit("/", 1)[-1] for key in await _list_attachment_keys(storage, session_id)}
    filename = _attachment_filename(file.filename or "", taken)
    try:
        from PIL import Image

        Image.open(io.BytesIO(raw_bytes)).verify()
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Arquivo enviado não é uma imagem válida.") from exc

    await storage.upload(
        _attachments_prefix(session_id) + filename, raw_bytes, _ATTACHMENT_EXTENSIONS[filename.rsplit(".", 1)[-1]]
    )
    logger.info("report_attachment_uploaded", session_id=session_id, filename=filename)
    return SuccessResponse(
        data=ReportChartItem(
            filename=filename,
            image_base64=base64.b64encode(raw_bytes).decode("ascii"),
            chart_type="attachment",
            document_type="attachment",
            caption=filename,
            origin="attachment",
        )
    )


@router.delete("/{session_id}/attachments/{filename}", response_model=SuccessResponse[dict[str, str]])
async def delete_report_attachment(
    session_id: int,
    filename: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[dict[str, str]]:
    """Exclui um anexo - só anexos (nome "anexo-..."), nunca os gráficos
    gerados pelo sistema nem as figuras fixas da Metodologia."""
    await _get_session_or_404(session, session_id)
    if not _ATTACHMENT_FILENAME_RE.match(filename):
        raise HTTPException(status_code=422, detail="Só anexos enviados pelo usuário podem ser excluídos.")
    storage = _storage(request)
    object_key = _attachments_prefix(session_id) + filename
    if object_key not in await _list_attachment_keys(storage, session_id):
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    await storage.delete(object_key)
    logger.info("report_attachment_deleted", session_id=session_id, filename=filename)
    return SuccessResponse(data={"filename": filename})
