"""
Redação das seções de IA do relatório de prospecção (padrão REPTEC/AGITEC -
ver notes/REPTEC_001_2023_TETRA.pdf). Pura sobre dicts já extraídos pelo
chamador (mesmo padrão de app/core/services/report_service.py) - nenhum
acesso a ORM/banco aqui, e nenhuma chamada de rede além das duas portas
injetadas (RAGService/TextGenerationPort).

Só cobre as 7 seções redigidas por IA (Finalidade, Objetivo, Introdução,
Resultados - Informações Científicas/Tecnológicas/Tendências, Conclusão).
Metodologia, Referências e Referências Bibliográficas são fixas/locais (ver
config/prompts/report_static_sections.py) - nunca passam por aqui, pra
evitar citação inventada por LLM.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from config.prompts.report_prompts import REPORT_SYSTEM_PROMPT, get_section_prompt
from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)

# section_key -> (nome de exibição, descrição usada na busca RAG). As chaves
# batem exatamente com `section_type` de report_prompts.get_section_prompt.
AI_SECTIONS: dict[str, tuple[str, str]] = {
    "finalidade": (
        "Finalidade",
        "objetivo geral do estudo de prospecção tecnológica e para quem é destinado",
    ),
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
        "depósitos de patentes: volume, principais depositantes e classificações CPC/IPC",
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


def _is_latin_renderable(ch: str) -> bool:
    """O template (report_latex_template.py) compila com pdflatex usando
    fontenc T1 + Latin Modern - só cobre script latino (com acentos de
    qualquer idioma europeu, não só português) mais pontuação/dígitos/
    símbolos comuns. Qualquer caractere fora disso (CJK, cirílico, hangul,
    árabe etc.) faz o pdflatex parar com "Unicode character ... not set up
    for use with LaTeX." - e nomes de inventor/autor vindos da OPS/Scopus
    (usados nas citações "Fonte: ...", ver _build_source_citation) podem
    vir em qualquer script."""
    if ch.isascii():
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
        não pagar o custo de reindexar a cada seção). `patents`/`articles`
        são dicts com pelo menos `title`/`abstract` (extraídos pelo
        chamador a partir de Patent/Article, igual ao padrão de
        report_service.py) - `inventors`/`authors` e `year`, quando
        presentes, viram a citação em `metadata["source"]` de cada
        documento (ver _build_source_citation), permitindo o texto gerado
        citar o autor/inventor de onde tirou a informação."""
        if self._rag is None:
            raise RAGUnavailableError("ChromaDB indisponível - verifique o container 'chromadb'.")

        session_key = str(session_id)
        already_indexed = await self._rag.query(
            query_text="_",
            top_k=1,
            filter_metadata={"session_id": session_key},
        )
        if already_indexed:
            return

        documents: list[dict[str, Any]] = []
        for patent in patents:
            text = _title_abstract_text(patent)
            if text:
                doc = {"text": text, "session_id": session_key, "document_type": "patent"}
                source = _build_source_citation(patent.get("inventors"), patent.get("year"))
                if source:
                    doc["source"] = source
                documents.append(doc)
        for article in articles:
            text = _title_abstract_text(article)
            if text:
                doc = {"text": text, "session_id": session_key, "document_type": "article"}
                source = _build_source_citation(article.get("authors"), article.get("year"))
                if source:
                    doc["source"] = source
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

    async def build_rag_context(self, session_id: int, section_key: str) -> str:
        if self._rag is None:
            raise RAGUnavailableError("ChromaDB indisponível - verifique o container 'chromadb'.")
        if section_key not in AI_SECTIONS:
            raise ValueError(f"'{section_key}' não é uma seção de IA válida.")

        section_name, section_description = AI_SECTIONS[section_key]
        return await self._rag.get_context_for_section(
            section_name=section_name,
            section_description=section_description,
            top_k=self._settings.rag_top_k_per_section,
            filter_metadata={"session_id": str(session_id)},
        )

    # ------------------------------------------------------------------
    # Geração de texto
    # ------------------------------------------------------------------

    async def generate_section_text(
        self,
        section_key: str,
        theme: str,
        rag_context: str,
        data: dict[str, Any],
    ) -> str:
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
        raw_text = await text_generation.generate(prompt, system=REPORT_SYSTEM_PROMPT)
        cleaned_text = _strip_markdown_headings(raw_text)
        escaped_text = escape_latex(cleaned_text)
        return _convert_markdown_bold(escaped_text)


def _title_abstract_text(document: dict[str, Any]) -> Optional[str]:
    title = (document.get("title") or "").strip()
    abstract = (document.get("abstract") or "").strip()
    if not title and not abstract:
        return None
    if title and abstract:
        return f"{title}\n\n{abstract}"
    return title or abstract


def _build_source_citation(names: Optional[list[str]], year: Optional[int]) -> Optional[str]:
    """Citação curta no espírito ABNT ("SOBRENOME et al. (ano)") a partir
    dos autores/inventores de um documento indexado no RAG - alimenta
    `metadata["source"]` (ver ensure_session_indexed), que
    RAGService.get_context_for_section já formata como "Fonte: {source}"
    em cada trecho recuperado, e REPORT_SYSTEM_PROMPT (regra 6, ver
    config/prompts/report_prompts.py) já instrui a IA a citar essa fonte
    entre parênteses ao usar o trecho - o mecanismo de citação já existia
    ponta a ponta, só nunca recebeu um valor de verdade (sempre "N/A").

    Pega o primeiro nome da lista (autor/inventor, não depositante/empresa -
    ver chamadas em ensure_session_indexed) e extrai o que vem antes da
    primeira vírgula (convenção "Sobrenome, Nome" já usada nos nomes vindos
    da OPS/Scopus) - se não houver vírgula, usa o nome inteiro. Acrescenta
    "et al." se houver mais de um nome. `None` se não houver nome nenhum, ou
    se o sobrenome não sobrevive a _strip_unrenderable_chars (nome em
    CJK/cirílico/etc., comum em inventores de patentes internacionais) - o
    template só tipografa script latino (ver escape_latex), então uma
    citação nesses casos sairia só como "(ano)" sem nome nenhum; melhor não
    citar do que citar vazio. Nunca inventa autor."""
    if not names:
        return None
    first = names[0].strip()
    if not first:
        return None
    surname = first.split(",", 1)[0].strip().upper()
    if not surname:
        return None
    surname = _strip_unrenderable_chars(surname).strip()
    if not surname:
        return None
    label = f"{surname} et al." if len(names) > 1 else surname
    return f"{label} ({year})" if year else label
