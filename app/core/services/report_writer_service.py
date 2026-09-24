"""
Redação das seções de IA do relatório de prospecção (padrão REPTEC/AGITEC -
ver notes/REPTEC_001_2023_TETRA.pdf). Pura sobre dicts já extraídos pelo
chamador (mesmo padrão de app/core/services/report_service.py) - nenhum
acesso a ORM/banco aqui, e nenhuma chamada de rede além das duas portas
injetadas (RAGService/TextGenerationPort).

Só cobre as 6 seções redigidas por IA (Objetivo - quando o usuário não o
escreve -, Introdução, Resultados - Informações Científicas/Tecnológicas/
Tendências, Conclusão). Finalidade, Metodologia, Referências e Referências
Bibliográficas são fixas/locais (ver config/prompts/report_static_sections.py)
- nunca passam por aqui, pra evitar texto/citação inventados por LLM.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from app.core.services.report_citations import build_citation, build_reference, disambiguate, filter_citations
from app.core.services.report_text_quality import fix_number_formatting, find_text_issues
from config.prompts.report_prompts import REPORT_SYSTEM_PROMPT, get_section_prompt, retry_instruction
from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)

# section_key -> (nome de exibição, descrição usada na busca RAG). As chaves
# batem exatamente com `section_type` de report_prompts.get_section_prompt.
# Finalidade não é mais seção de IA: é uma frase fixa com tema + destinatário
# (ver report_static_sections.render_finalidade), como no REPTEC.
AI_SECTIONS: dict[str, tuple[str, str]] = {
    "objetivo": (
        "Objetivo",
        "objetivo específico, escopo temporal, geográfico e técnico desta prospecção",
    ),
    "introducao": (
        "Introdução",
        "contexto histórico, mercado, players e estado da arte da tecnologia",
    ),
    "informacoes_cientificas": (
        "Resultados - Informações Científicas",
        "produção científica: volume, principais periódicos, autores e instituições",
    ),
    "informacoes_tecnologicas": (
        "Resultados - Informações Tecnológicas",
        "depósitos de patentes: volume, principais depositantes e classificações CPC",
    ),
    "tendencias_ciclo_vida": (
        "Resultados - Tendências e Ciclo de Vida da Tecnologia",
        "estágio do ciclo de vida da tecnologia segundo a curva-S (GP/MP/SP)",
    ),
    "conclusao": (
        "Conclusão",
        "síntese do estágio de maturidade da tecnologia e recomendações",
    ),
}

_LATEX_ESCAPE_MAP = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "%": r"\%",
    "#": r"\#",
    "_": r"\_",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


# Ordinais (º/ª, categoria "Lo" e sem "LATIN" no nome Unicode) - usados em
# "Nº 115", "1º Ten", "3ª Seção"; o pdflatex com T1 renderiza normalmente.
# Sem isso eram removidos: "DIEx Nº 256" saía "DIEx N 256".
_LATIN_EXTRAS = {"º", "ª"}


def _is_latin_renderable(ch: str) -> bool:
    """O template (report_latex_template.py) compila com pdflatex usando
    fontenc T1 + Latin Modern - só cobre script latino (com acentos de
    qualquer idioma europeu, não só português) mais pontuação/dígitos/
    símbolos comuns. Qualquer caractere fora disso (CJK, cirílico, hangul,
    árabe etc.) faz o pdflatex parar com "Unicode character ... not set up
    for use with LaTeX." - e nomes de inventor/autor vindos da OPS/Scopus
    (usados nas citações "(SOBRENOME et al., ano)", ver report_citations.py) podem
    vir em qualquer script."""
    if ch.isascii() or ch in _LATIN_EXTRAS:
        return True
    category = unicodedata.category(ch)
    if category[0] in ("Z", "P", "N", "S"):  # espaço, pontuação, número, símbolo
        return True
    return "LATIN" in unicodedata.name(ch, "")


def _strip_unrenderable_chars(text: str) -> str:
    """Remove caracteres que o template não consegue tipografar (ver
    _is_latin_renderable) - roda ANTES do escape de caracteres especiais do
    LaTeX, pra não travar a montagem do .tex com um nome/trecho em script
    não-latino. Colapsa espaços duplos deixados pela remoção."""
    if not text:
        return text
    stripped = "".join(ch for ch in text if _is_latin_renderable(ch))
    return re.sub(r" {2,}", " ", stripped)


def escape_latex(text: str) -> str:
    """Escapa caracteres especiais do LaTeX num texto solto (ex.: devolvido
    por um LLM) - obrigatório antes de injetar no template, já que o texto
    gerado não é LaTeX válido por si só. Também descarta caracteres fora do
    script latino (ver _strip_unrenderable_chars) - sem isso, um nome de
    autor/inventor em CJK/cirílico/etc. (bem comum em citações de patentes
    internacionais) derruba a compilação do .tex inteiro."""
    if not text:
        return text
    text = _strip_unrenderable_chars(text)
    return "".join(_LATEX_ESCAPE_MAP.get(ch, ch) for ch in text)


def latex_comment(label: str) -> str:
    """Linha LaTeX comentada (%) pra um campo OPCIONAL que ficou vazio (ex.:
    revisado_por/aprovado_por sem assinante, quadro de busca sem uma das
    fontes) - some do PDF compilado, mas continua visível pra quem edita o
    .tex direto, indicando onde aquele dado entraria. Só usada pra campos
    opcionais: os obrigatórios (número/ano/referências administrativas/
    elaborado por) nunca chegam vazios aqui, porque o front bloqueia
    "Montar .tex" antes disso (ver ReportGeneration.tsx)."""
    return f"% {label}: não informado"


# REPORT_SYSTEM_PROMPT já instrui "não inclua título/cabeçalho da seção",
# mas LLMs (principalmente modelos locais menores, ver Ollama) ignoram isso
# com frequência e devolvem Markdown solto (cabeçalho "### Seção: X",
# "**negrito**") - sem tratar, escape_latex escapa cada "#"/"*" ao pé da
# letra e o PDF final mostra literalmente "\#\#\# Seção: X" ou "**texto**"
# em vez de título nenhum/negrito de verdade.
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,6}[ \t]*.*$\n?", re.MULTILINE)
_MARKDOWN_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _strip_markdown_headings(text: str) -> str:
    """Remove linhas que são só um cabeçalho Markdown - roda ANTES de
    escape_latex, enquanto o "#" ainda é um caractere literal (mais simples
    de casar aqui do que depois de virar "\\#")."""
    if not text:
        return text
    return _MARKDOWN_HEADING_RE.sub("", text).strip()


def _convert_markdown_bold(escaped_text: str) -> str:
    """Converte **negrito** (Markdown) pra `\\textbf{}` - roda DEPOIS de
    escape_latex: "*" nunca é escapado (não está em _LATEX_ESCAPE_MAP),
    sobrevive intacto até aqui, e o conteúdo entre os "**" já saiu
    devidamente escapado como texto normal - inserir `\\textbf{}` ao redor
    dele agora é seguro."""
    return _MARKDOWN_BOLD_RE.sub(r"\\textbf{\1}", escaped_text)


class RAGUnavailableError(RuntimeError):
    """Levantado quando o container ChromaDB não está acessível - ver
    app/container.py (rag_service fica None nesse caso)."""


class SectionQualityError(RuntimeError):
    """Texto gerado continuou com termos internos do pipeline ("[Informação
    não disponível]", "Relevância", "contexto fornecido"...) mesmo depois de
    uma regeneração - ver report_text_quality.find_text_issues."""


# Versão do formato dos metadados indexados no ChromaDB - sessões indexadas
# numa versão anterior (sem `citation`/`reference`) são reindexadas
# automaticamente na próxima seção (ver ensure_session_indexed).
_INDEX_VERSION = "2"

# Padrão da fração do score do documento mais relevante abaixo da qual um
# trecho é descartado - corta documentos periféricos (ex.: "artificial
# stone" num relatório sobre placas solares) que o top_k traria de qualquer
# jeito. Editável em Configurações (settings.rag_relative_min_relevance).
_RELATIVE_MIN_RELEVANCE = 0.75


class ReportWriterService:
    def __init__(self, rag: Any, llm_resolver: Any, settings: Settings) -> None:
        self._rag = rag
        # llm_resolver: LLMConfigResolver - resolve_text_generation("report_writing")
        # substitui o text_generation fixo injetado no boot (ver
        # PLANO_MIGRACAO_CONFIG_BANCO.md § 4.3).
        self._llm_resolver = llm_resolver
        self._settings = settings

    @staticmethod
    def ai_section_keys() -> list[str]:
        return list(AI_SECTIONS.keys())

    @staticmethod
    def is_ai_section(section_key: str) -> bool:
        return section_key in AI_SECTIONS

    # ------------------------------------------------------------------
    # Indexação (RAG)
    # ------------------------------------------------------------------

    async def ensure_session_indexed(
        self,
        session_id: int,
        patents: list[dict[str, Any]],
        articles: list[dict[str, Any]],
    ) -> None:
        """Indexa título+resumo dos documentos da busca final dessa sessão,
        se ainda não indexados (idempotente - checa antes de reindexar, pra
        não pagar o custo de reindexar a cada seção). Cada documento leva
        nos metadados a citação pronta ("SILVA et al., 2020") e a entrada
        ABNT correspondente (ver report_citations.py) - sessões indexadas
        antes disso (sem `index_version`) são reindexadas aqui."""
        if self._rag is None:
            raise RAGUnavailableError("ChromaDB indisponível - verifique o container 'chromadb'.")

        session_key = str(session_id)
        already_indexed = await self._rag.query(
            query_text="_",
            top_k=1,
            filter_metadata={"session_id": session_key},
        )
        if already_indexed:
            metadata = already_indexed[0].get("metadata") or {}
            if metadata.get("index_version") == _INDEX_VERSION:
                return
            await self._rag.clear_by_metadata({"session_id": session_key})

        documents: list[dict[str, Any]] = []
        for document_type, items in (("patent", patents), ("article", articles)):
            for item in items:
                text = _title_abstract_text(item)
                if not text:
                    continue
                doc = {
                    "text": text,
                    "session_id": session_key,
                    "document_type": document_type,
                    "index_version": _INDEX_VERSION,
                }
                names = item.get("inventors") if document_type == "patent" else item.get("authors")
                citation = build_citation(names, item.get("year"))
                reference = build_reference(item, document_type)
                if citation and reference:
                    doc["citation"] = citation
                    doc["reference"] = reference
                documents.append(doc)

        if not documents:
            logger.warning("report_rag_no_documents_to_index session_id=%d", session_id)
            return

        count = await self._rag.index_documents(documents)
        logger.info("report_rag_indexed session_id=%d chunks=%d", session_id, count)

    async def reindex_session(
        self,
        session_id: int,
        patents: list[dict[str, Any]],
        articles: list[dict[str, Any]],
    ) -> None:
        """Força reindexação (limpa os chunks dessa sessão primeiro) - usado
        se o usuário pedir pra regenerar o relatório do zero."""
        if self._rag is None:
            raise RAGUnavailableError("ChromaDB indisponível - verifique o container 'chromadb'.")
        await self._rag.clear_by_metadata({"session_id": str(session_id)})
        await self.ensure_session_indexed(session_id, patents, articles)

    async def build_rag_context(
        self, session_id: int, section_key: str, theme: str = ""
    ) -> tuple[str, list[dict[str, str]]]:
        """Recupera os trechos mais relevantes pra seção e devolve
        (contexto pro LLM, fontes citáveis). O tema entra na busca (sem ele
        a busca era só o nome da seção e trazia documentos periféricos);
        trechos bem menos relevantes que o melhor são descartados
        (settings.rag_relative_min_relevance). O contexto NÃO leva score de similaridade
        nem "Fonte: N/A" - o LLM tratava esses valores como dados."""
        if self._rag is None:
            raise RAGUnavailableError("ChromaDB indisponível - verifique o container 'chromadb'.")
        if section_key not in AI_SECTIONS:
            raise ValueError(f"'{section_key}' não é uma seção de IA válida.")

        section_name, section_description = AI_SECTIONS[section_key]
        query_text = f"{theme}. {section_name}: {section_description}" if theme else f"{section_name}: {section_description}"
        results = await self._rag.query(
            query_text=query_text,
            top_k=self._settings.rag_top_k_per_section,
            filter_metadata={"session_id": str(session_id)},
        )
        if not results:
            return "", []

        best = max(r.get("relevance_score", 0) for r in results)
        ratio = getattr(self._settings, "rag_relative_min_relevance", _RELATIVE_MIN_RELEVANCE)
        kept = [r for r in results if r.get("relevance_score", 0) >= best * ratio]

        raw_sources = [
            {"citation": m["citation"], "reference": m["reference"]}
            for m in ((r.get("metadata") or {}) for r in kept)
            if m.get("citation") and m.get("reference")
        ]
        sources = disambiguate(raw_sources)
        citation_by_reference = {s["reference"]: s["citation"] for s in sources}

        parts = [f"## Documentos recuperados sobre o tema ({section_name})\n"]
        for idx, result in enumerate(kept, 1):
            metadata = result.get("metadata") or {}
            citation = citation_by_reference.get(metadata.get("reference", ""))
            header = f"Documento {idx} - citar como ({citation})" if citation else f"Documento {idx} - sem autoria identificada (não citar)"
            parts.append(header)
            parts.append(result.get("text", ""))
            parts.append("")

        logger.info(
            "report_rag_context section=%s retrieved=%d kept=%d citable=%d",
            section_key, len(results), len(kept), len(sources),
        )
        return "\n".join(parts), sources

    # ------------------------------------------------------------------
    # Geração de texto
    # ------------------------------------------------------------------

    async def generate_section_text(
        self,
        section_key: str,
        theme: str,
        rag_context: str,
        data: dict[str, Any],
        sources: Optional[list[dict[str, str]]] = None,
    ) -> str:
        """Gera o texto da seção e o valida: números no formato pt-BR são
        corrigidos automaticamente; termos internos do pipeline ("[Informação
        não disponível]", "Relevância", "contexto fornecido"...) forçam UMA
        regeneração - se persistirem, levanta SectionQualityError. Citações
        que não correspondem a nenhuma fonte recuperada são removidas."""
        if section_key not in AI_SECTIONS:
            raise ValueError(f"'{section_key}' não é uma seção de IA válida.")

        section_name, _ = AI_SECTIONS[section_key]
        prompt = get_section_prompt(
            section_name=section_name,
            section_type=section_key,
            theme=theme,
            context=rag_context,
            data=data,
        )
        text_generation = await self._llm_resolver.resolve_text_generation("report_writing")

        issues: list[str] = []
        for attempt in (1, 2):
            attempt_prompt = prompt if attempt == 1 else prompt + retry_instruction(issues)
            raw_text = await text_generation.generate(attempt_prompt, system=REPORT_SYSTEM_PROMPT)
            text = _strip_markdown_headings(raw_text)
            text, removed = filter_citations(text, sources or [])
            if removed:
                logger.warning("report_citations_removed section=%s removed=%s", section_key, removed)
            text = fix_number_formatting(text)
            issues = find_text_issues(text)
            if not issues:
                break
            logger.warning("report_section_quality_issues section=%s attempt=%d issues=%s", section_key, attempt, issues)
        else:
            raise SectionQualityError(
                f"O texto gerado para '{section_name}' continuou com problemas após regenerar: "
                + "; ".join(issues)
            )

        escaped_text = escape_latex(text)
        return _convert_markdown_bold(escaped_text)


def _title_abstract_text(document: dict[str, Any]) -> Optional[str]:
    title = (document.get("title") or "").strip()
    abstract = (document.get("abstract") or "").strip()
    if not title and not abstract:
        return None
    if title and abstract:
        return f"{title}\n\n{abstract}"
    return title or abstract
