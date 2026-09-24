"""
Citações (AUTOR, ano) dos documentos recuperados pelo RAG e as entradas
correspondentes em Referências Bibliográficas - padrão do REPTEC: o texto
só cita "(SOBRENOME et al., 2020)", e toda citação tem entrada na seção 8.

Fluxo:
1. Indexação (ReportWriterService.ensure_session_indexed): cada documento
   ganha `citation` ("SILVA et al., 2020") e `reference` (entrada ABNT)
   nos metadados, via `build_citation`/`build_reference`.
2. RAG da seção: os documentos recuperados viram `sources` (persistido em
   session_report_section.sources) e o contexto enviado ao LLM traz a
   citação pronta de cada um.
3. Texto gerado: `filter_citations` remove citações que não correspondem a
   nenhum documento recuperado (inventadas ou mal formadas).
4. Montagem do .tex: `references_for_text` devolve só as entradas das
   citações que sobraram no texto final.

Tudo aqui trabalha com texto PURO (antes de escape_latex).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional


def _is_latin(text: str) -> bool:
    return all(not ch.isalpha() or "LATIN" in unicodedata.name(ch, "") for ch in text)


def _split_name(name: str) -> tuple[str, list[str]]:
    """(sobrenome, prenomes) de um nome de autor/inventor nos formatos que
    chegam da OPS/Scopus: "Shen, Hai Jun" (sobrenome antes da vírgula),
    "Pei G." (Scopus, sobrenome primeiro) ou "SHEN HAI JUN" (epodoc,
    sobrenome primeiro)."""
    name = " ".join(name.split())
    if "," in name:
        surname, _, rest = name.partition(",")
        return surname.strip(), rest.replace(".", " ").split()
    tokens = name.replace(".", " ").split()
    return (tokens[0], tokens[1:]) if tokens else ("", [])


def _clean_names(names: Optional[list[str]]) -> list[str]:
    return [n for n in (names or []) if isinstance(n, str) and n.strip() and _is_latin(n)]


def build_citation(names: Optional[list[str]], year: Optional[int]) -> Optional[str]:
    """"SILVA et al., 2020" / "SILVA, 2020" - None sem autor latino ou sem
    ano (melhor não citar do que citar incompleto; nunca inventa autor)."""
    clean = _clean_names(names)
    if not clean or not year:
        return None
    surname, _ = _split_name(clean[0])
    if not surname:
        return None
    label = surname.upper() + (" et al." if len(clean) > 1 else "")
    return f"{label}, {year}"


def _abnt_author(name: str) -> str:
    surname, given = _split_name(name)
    initials = " ".join(f"{g[0].upper()}." for g in given if g)
    return f"{surname.upper()}, {initials}" if initials else surname.upper()


def build_reference(document: dict[str, Any], document_type: str) -> Optional[str]:
    """Entrada ABNT simplificada a partir dos metadados disponíveis:
    artigo -> "SILVA, J. et al. Título. Periódico, 2020."
    patente -> "SILVA, J. et al. Título. Depositante: ACME. Patente, 2020."
    None quando não há como citar (ver build_citation)."""
    names = document.get("inventors") if document_type == "patent" else document.get("authors")
    clean = _clean_names(names)
    year = document.get("year")
    title = " ".join((document.get("title") or "").split()).rstrip(".")
    if not clean or not year or not title:
        return None
    author = _abnt_author(clean[0]) + (" et al" if len(clean) > 1 else "")
    parts = [f"{author.rstrip('.')}.", f"{title}."]
    if document_type == "patent":
        applicants = _clean_names(document.get("applicants"))
        if applicants:
            parts.append(f"Depositante: {applicants[0]}.")
        parts.append(f"Patente, {year}.")
    else:
        journal = " ".join((document.get("journal_or_source") or "").split())
        parts.append(f"{journal}, {year}." if journal else f"{year}.")
    return " ".join(parts)


def disambiguate(sources: list[dict[str, str]]) -> list[dict[str, str]]:
    """Mesma citação pra obras diferentes (mesmo sobrenome e ano) ganha
    letra no ano, como na ABNT: "SILVA et al., 2020a" / "2020b"."""
    by_citation: dict[str, list[dict[str, str]]] = {}
    for source in sources:
        by_citation.setdefault(source["citation"], []).append(source)
    result: list[dict[str, str]] = []
    for citation, group in by_citation.items():
        references = list(dict.fromkeys(s["reference"] for s in group))
        if len(references) == 1:
            result.append({"citation": citation, "reference": references[0]})
            continue
        for idx, reference in enumerate(references):
            letter = chr(ord("a") + idx)
            year = citation.rsplit(", ", 1)[-1]
            result.append({
                "citation": f"{citation}{letter}",
                "reference": re.sub(rf"{year}\.$", f"{year}{letter}.", reference),
            })
    return result


# Um item de citação "SOBRENOME[ et al.], 2020[a]" dentro de parênteses.
_CITATION_ITEM_RE = re.compile(r"^[A-ZÀ-Ý][A-ZÀ-Ý'´`\- ]*(?: et al\.)?, \d{4}[a-z]?$")
_PAREN_RE = re.compile(r"\s*\(([^()]*\d{4}[^()]*)\)")


def _normalize(citation: str) -> str:
    return " ".join(citation.split()).upper().replace(" ET AL.", " et al.")


def filter_citations(text: str, sources: list[dict[str, str]]) -> tuple[str, list[str]]:
    """Remove de cada parênteses de citação os itens que não correspondem a
    nenhuma fonte recuperada; parênteses que ficam vazios somem. Parênteses
    que não são citação (ex.: "(MP = 2011)", "(2015 e 2016)") ficam
    intactos. Devolve (texto, citações removidas)."""
    allowed = {_normalize(s["citation"]): s["citation"] for s in sources}
    removed: list[str] = []

    def replace(match: re.Match[str]) -> str:
        items = [item.strip() for item in match.group(1).split(";")]
        if not all(_CITATION_ITEM_RE.match(item) for item in items):
            return match.group(0)
        kept = []
        for item in items:
            canonical = allowed.get(_normalize(item))
            if canonical:
                kept.append(canonical)
            else:
                removed.append(item)
        return f" ({'; '.join(kept)})" if kept else ""

    return _PAREN_RE.sub(replace, text), removed


def references_for_text(text: str, sources: list[dict[str, str]]) -> list[str]:
    """Entradas (texto puro) das fontes cujas citações aparecem em `text`."""
    return [s["reference"] for s in sources if s["citation"] in text]
