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
import zipfile
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driving.http.dependencies import get_db_session
from app.adapters.driving.http.report_router import _resolve_final_probe_query_id
from app.core.services.cpc_titles import describe_codes
from app.core.services.report_citations import references_for_text
from app.core.services.report_lifecycle import build_lifecycle, summary_text
from app.core.services.report_review import referenced_image_files
from app.core.services.report_writer_service import (
    RAGUnavailableError,
    ReportWriterService,
    SectionQualityError,
    escape_latex,
    latex_comment,
)
from app.core.services.report_cover_image import REPORT_COVER_IMAGE_FILENAME, REPORT_COVER_IMAGE_OBJECT_KEY
from app.core.services.report_figures import FIGURE_ORDER, FIGURE_SPECS, CatalogEntry, figure_id, place_figures
from app.core.services.report_form_validation import (
    admin_reference_error,
    bibliography_error,
    collect_errors,
    signer_error,
    text_field_error,
)
from app.core.services.report_latex_service import ReportLatexService
from app.core.services.report_static_figures import REPORT_STATIC_FIGURES
from config.prompts.report_static_sections import (
    DEFAULT_BIBLIOGRAPHY,
    DEFAULT_SIGNATURES,
    legacy_metodologia_to_paragraph,
    merge_bibliography,
    render_finalidade,
    render_local_data,
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
    ReviewLatexIssue,
    ReviewRequest,
    ReviewResponse,
    ReviewScopeItem,
    ReviewSuggestion,
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


def _is_report_chart(chart: SessionChart) -> bool:
    """Só os gráficos do catálogo do relatório (FIGURE_SPECS) - ver
    report_figures.py pro porquê de existirem outros em SessionChart."""
    return (chart.document_type, chart.chart_type) in FIGURE_SPECS


def _writer(request: Request) -> ReportWriterService:
    return request.app.state.container["services"]["report_writer"]


def _latex_svc(request: Request):
    return request.app.state.container["services"]["report_latex"]


def _storage(request: Request):
    return request.app.state.container["services"]["storage"]


def _review_svc(request: Request):
    return request.app.state.container["services"]["report_review"]


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
        # Inventores (pessoa), não depositantes (empresa) - viram a citação
        # (SOBRENOME et al., ano) do documento (ver report_citations.py).
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


def _pt_int(value: int) -> str:
    return f"{value:,}".replace(",", ".")


async def _report_charts(session: AsyncSession, session_id: int) -> list[SessionChart]:
    """Gráficos da busca final dessa sessão que fazem parte do relatório
    (FIGURE_SPECS), na ordem de apresentação."""
    result = await session.execute(
        select(SessionChart)
        .join(SessionProbeQuery, SessionProbeQuery.id == SessionChart.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
    )
    charts = [chart for chart in result.scalars().all() if _is_report_chart(chart)]
    order = {chart_type: idx for idx, chart_type in enumerate(FIGURE_ORDER)}
    return sorted(charts, key=lambda c: (order.get(c.chart_type, len(order)), c.document_type))


def _figure_facts(chart: SessionChart) -> dict[str, str]:
    spec = FIGURE_SPECS[(chart.document_type, chart.chart_type)]
    return {
        "id": figure_id(chart.document_type, chart.chart_type),
        "kind": "Quadro" if spec.kind == "quadro" else "Figura",
        "caption": spec.caption,
        "summary": summary_text(chart.chart_type, chart.summary or {}),
    }


def _build_section_data(
    section_key: str,
    theme_input: Optional[SessionInput],
    charts: list[SessionChart],
    patents: list[Patent],
    articles: list[Article],
    payload: Optional[SectionGenerateRequest],
) -> dict[str, Any]:
    """Fatos passados ao prompt da seção (ver formato em report_prompts.py) -
    tudo calculado aqui, a partir do que já está persistido: resumos
    numéricos gravados junto de cada gráfico (SessionChart.summary),
    estágio do ciclo de vida (curvas S), títulos oficiais CPC e documentos
    da busca final. `payload` (front) só contribui com os totais de
    resultados da busca, que não ficam no banco."""
    data: dict[str, Any] = {
        "area_of_study": (theme_input.area_of_study if theme_input else None) or "",
        "keywords": (theme_input.keywords if theme_input else None) or [],
    }
    if payload is not None and payload.article_count is not None:
        data["article_count"] = _pt_int(payload.article_count)
    if payload is not None and payload.patent_count is not None:
        data["patent_count"] = _pt_int(payload.patent_count)

    data["figures"] = [
        _figure_facts(chart) for chart in charts
        if FIGURE_SPECS[(chart.document_type, chart.chart_type)].section == section_key
    ]

    s_curves = {c.document_type: c.summary for c in charts if c.chart_type == "s_curve" and c.summary}
    data["lifecycle"] = build_lifecycle(s_curves)

    if section_key == "informacoes_tecnologicas":
        heatmap = next(
            (c for c in charts if c.document_type == "patent" and c.chart_type == "top10_heatmap" and c.summary), None
        )
        codes = [name for name, _ in heatmap.summary["top"]] if heatmap else list(payload.top_cpc_codes if payload else [])
        data["cpc_titles"] = describe_codes(codes)

    if section_key == "conclusao":
        if patents or articles:
            data["brazil"] = {
                "patents": sum(1 for p in patents if (p.country or "").upper() == "BR"),
                "articles": sum(1 for a in articles if "Brazil" in (a.affiliation_countries or [])),
            }
        lines = []
        if data.get("patent_count"):
            lines.append(f"- Total de patentes encontradas: {data['patent_count']}")
        if data.get("article_count"):
            lines.append(f"- Total de publicações científicas encontradas: {data['article_count']}")
        for chart in charts:
            facts = _figure_facts(chart)
            lines.append(f"- {facts['caption']} {facts['summary']}")
        data["results_digest"] = "\n".join(lines)
    return data


_SIGNATURE_ROLE_LABELS = {
    "elaborado_por": "Elaborado por",
    "revisado_por": "Revisado por",
    "aprovado_por": "Aprovado por",
}


def _raise_on_form_errors(errors: list[str]) -> None:
    if errors:
        raise HTTPException(status_code=422, detail=" ".join(errors))


def _signature_errors(payload: Optional[SignaturesInput]) -> list[str]:
    if payload is None:
        return []
    return collect_errors(
        signer_error(_SIGNATURE_ROLE_LABELS[field], block.nome, block.posto_funcao)
        for field in ("elaborado_por", "revisado_por", "aprovado_por")
        for block in getattr(payload, field)
    )


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
        theme_input = await _get_session_theme_input(session, session_id)
        rag_context, sources = await writer.build_rag_context(
            session_id, section_key, theme_input.theme if theme_input else ""
        )
    except RAGUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    row = await _get_or_create_section_row(session, session_id, section_key)
    row.rag_context = rag_context
    row.sources = sources
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

    Os fatos do prompt vêm de _build_section_data (resumos dos gráficos,
    estágio do ciclo de vida, CPC oficial); `payload` só traz os totais de
    resultados da busca final. 422 se o texto continuar com termos internos
    do pipeline depois de uma regeneração (SectionQualityError)."""
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
    charts = await _report_charts(session, session_id)
    data = _build_section_data(section_key, theme_input, charts, patents, articles, payload)

    writer = _writer(request)
    try:
        generated_text = await writer.generate_section_text(
            section_key, theme, row.rag_context, data, row.sources or []
        )
    except SectionQualityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
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
    _raise_on_form_errors(
        collect_errors(
            [
                *(admin_reference_error(ref) for ref in payload.referencias_administrativas),
                *(bibliography_error(ref) for ref in payload.referencias_bibliograficas_adicionais),
                text_field_error("Destinatário", payload.destinatario) if payload.destinatario else None,
                text_field_error("Objetivo", payload.objetivo, min_words=5) if payload.objetivo else None,
            ]
        )
        + _signature_errors(payload.assinaturas)
    )
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

    static_texts = [
        ("metodologia", metodologia_text),
        ("referencias_bibliograficas", "\n".join(bibliografia)),
    ]
    tema = payload.tema.strip() or (theme_input.theme if theme_input else "")
    if payload.destinatario.strip():
        static_texts.append(("finalidade", escape_latex(render_finalidade(tema, payload.destinatario))))
    # Objetivo escrito pelo usuário substitui a seção de IA (o front pula a
    # geração dela nesse caso).
    if payload.objetivo and payload.objetivo.strip():
        static_texts.append(("objetivo", escape_latex(payload.objetivo.strip())))
    for section_key, text in static_texts:
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

    all_keys = [*ReportWriterService.ai_section_keys(), "finalidade", "metodologia", "referencias_bibliograficas"]
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
    # Catálogo de figuras por seção de Resultados - cada uma entra no texto
    # onde o LLM pôs o marcador [[FIG:id]] (ou no fim da seção, ver
    # place_figures).
    catalogs: dict[str, list[CatalogEntry]] = {}
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

        spec = FIGURE_SPECS[(chart.document_type, chart.chart_type)]
        chart_object_keys.append(chart.object_key)
        catalogs.setdefault(spec.section, []).append(
            CatalogEntry(
                id=figure_id(chart.document_type, chart.chart_type),
                kind=spec.kind,
                caption=escape_latex(spec.caption),
                filename=chart.object_key.rsplit("/", 1)[-1],
            )
        )

    def _results_text(key: str) -> str:
        text, _ = place_figures(_text(key), catalogs.get(key, []), key)
        return text

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
    # Toda citação (SOBRENOME et al., ano) que sobrou no texto das seções
    # de IA ganha a entrada correspondente (ver report_citations.py).
    cited_refs: list[str] = []
    for key in ReportWriterService.ai_section_keys():
        section_row = sections_by_key.get(key)
        if section_row and section_row.generated_text and section_row.sources:
            cited_refs.extend(
                escape_latex(ref) for ref in references_for_text(section_row.generated_text, section_row.sources)
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
        "informacoes_cientificas": _results_text("informacoes_cientificas"),
        "informacoes_tecnologicas": _results_text("informacoes_tecnologicas"),
        "tendencias_ciclo_vida": _results_text("tendencias_ciclo_vida"),
        "conclusao": _text("conclusao"),
        "referencias_bibliograficas": merge_bibliography(
            [escape_latex(ref) for ref in DEFAULT_BIBLIOGRAPHY], stored_biblio_refs + cited_refs
        ),
        "assinaturas": _merge_signatures(payload.assinaturas),
        "local_data": escape_latex(render_local_data(payload.local, date.today())) if payload.local.strip() else None,
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
    _raise_on_form_errors(
        collect_errors(admin_reference_error(ref) for ref in payload.referencias_administrativas)
        + _signature_errors(payload.assinaturas)
    )
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


async def _collect_image_keys(session: AsyncSession, session_id: int, storage) -> list[str]:
    """Chaves no MinIO de todas as imagens que o .tex desta sessão pode
    referenciar - gráficos (recorte feito no /assemble), capa, figuras fixas
    da Metodologia e anexos. Usada pela compilação e pelo download do .zip."""
    charts_result = await session.execute(
        select(SessionChart)
        .join(SessionProbeQuery, SessionProbeQuery.id == SessionChart.probe_query_id)
        .where(SessionProbeQuery.session_id == session_id, SessionProbeQuery.tipo.isnot(None))
    )
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
    return image_object_keys


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

    storage = _storage(request)
    image_object_keys = await _collect_image_keys(session, session_id, storage)

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
    gráficos por padrão, ver report_figures.FIGURE_SPECS)."""
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
                caption=FIGURE_SPECS[(chart.document_type, chart.chart_type)].caption,
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


@router.post("/{session_id}/review", response_model=SuccessResponse[ReviewResponse])
async def review_report_tex(
    session_id: int,
    payload: ReviewRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> SuccessResponse[ReviewResponse]:
    """Revisão do .tex do editor: problemas de LaTeX (documento todo) e
    sugestões de ortografia/acentuação/concordância (LanguageTool e, se
    `include_ai`, IA) só nas seções geradas por IA e nas linhas editadas -
    ver report_review.py. Nunca altera o .tex: o front aplica o que o
    usuário aprovar."""
    await _get_session_or_404(session, session_id)
    storage = _storage(request)

    available_images = {chart.object_key.rsplit("/", 1)[-1] for chart in await _report_charts(session, session_id)}
    available_images |= {key.rsplit("/", 1)[-1] for key in await _list_attachment_keys(storage, session_id)}
    available_images |= set(REPORT_STATIC_FIGURES) | {REPORT_COVER_IMAGE_FILENAME}

    try:
        baseline: Optional[str] = (await storage.download(ReportLatexService.assembled_key(session_id))).decode("utf-8")
    except Exception:
        baseline = None

    result = await _review_svc(request).review(
        payload.tex_content,
        baseline,
        available_images,
        compile_log=payload.compile_log,
        include_ai=payload.include_ai,
    )
    return SuccessResponse(
        data=ReviewResponse(
            latex_issues=[ReviewLatexIssue(**issue.to_dict()) for issue in result.latex_issues],
            suggestions=[ReviewSuggestion(**suggestion.to_dict()) for suggestion in result.suggestions],
            scope=[ReviewScopeItem(start=r.start, end=r.end, section=r.section, reason=r.reason) for r in result.scope],
            warnings=result.warnings,
        )
    )


def _bundle_filename(report_row: Optional[SessionReport], session_id: int) -> str:
    """"REPTEC_001_2026.zip" quando a capa já foi montada (número/ano em
    assemble_payload); senão "relatorio_sessao_<id>.zip"."""
    assembled = (report_row.assemble_payload or {}) if report_row else {}
    numero = re.sub(r"[^0-9A-Za-z-]+", "", str(assembled.get("numero") or ""))
    ano = re.sub(r"[^0-9]+", "", str(assembled.get("ano") or ""))
    return f"REPTEC_{numero}_{ano}.zip" if numero and ano else f"relatorio_sessao_{session_id}.zip"


@router.post("/{session_id}/bundle")
async def download_report_bundle(
    session_id: int,
    request: Request,
    payload: Optional[CompilePdfRequest] = None,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """.zip com o .tex e as imagens que ele usa - pra compilar/editar fora
    do sistema (Overleaf, TeX local). `payload.tex_content` é o texto ATUAL
    do editor (com edições ainda não compiladas); sem ele, usa o último .tex
    salvo. Só entram as imagens referenciadas no documento (ver
    report_review.referenced_image_files)."""
    await _get_session_or_404(session, session_id)
    report_result = await session.execute(select(SessionReport).where(SessionReport.session_id == session_id))
    report_row = report_result.scalar_one_or_none()
    storage = _storage(request)

    if payload is not None and payload.tex_content is not None:
        tex_content = payload.tex_content
    elif report_row is not None:
        tex_content = (await storage.download(report_row.tex_object_key)).decode("utf-8")
    else:
        raise HTTPException(status_code=422, detail="Relatório ainda não montado - chame POST .../assemble primeiro.")

    wanted = referenced_image_files(tex_content)
    keys_by_name = {key.rsplit("/", 1)[-1]: key for key in await _collect_image_keys(session, session_id, storage)}

    buffer = io.BytesIO()
    missing: list[str] = []
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("main.tex", tex_content.encode("utf-8"))
        for filename in sorted(wanted):
            key = keys_by_name.get(filename)
            if key is None:
                missing.append(filename)
                continue
            try:
                archive.writestr(filename, await storage.download(key))
            except Exception as exc:
                logger.warning("report_bundle_image_download_failed", object_key=key, error=str(exc))
                missing.append(filename)
        if missing:
            archive.writestr(
                "LEIA-ME.txt",
                "Imagens referenciadas no main.tex que não foram encontradas no sistema:\n"
                + "\n".join(f"- {name}" for name in missing)
                + "\n",
            )

    logger.info("report_bundle_built", session_id=session_id, images=len(wanted) - len(missing), missing=len(missing))
    filename = _bundle_filename(report_row, session_id)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
