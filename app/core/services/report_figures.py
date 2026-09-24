"""
Figuras/quadros dos Resultados do relatório REPTEC (6.1-6.3) - catálogo e
posicionamento no texto.

O LLM escreve cada seção de Resultados com marcadores (ver
report_prompts.py): `[[REF:id]]` onde cita a figura ("Como mostra a Figura
[[REF:article_yearly_volume]], ...") e `[[FIG:id]]` sozinho numa linha logo
após o parágrafo que a discute. `place_figures` (função pura) troca os
marcadores pelo LaTeX na montagem do .tex - texto gerado antes dos
marcadores existirem simplesmente não tem nenhum, e todas as figuras caem
no fim da seção (mesmo comportamento de antes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from core.logging import get_logger

logger = get_logger(__name__)

FigureKind = Literal["figura", "quadro"]


@dataclass(frozen=True)
class FigureSpec:
    kind: FigureKind
    caption: str  # frase completa com ponto final, como no REPTEC
    section: str  # seção de IA onde a figura entra


# (document_type, chart_type) -> spec. É também a LISTA DE GRÁFICOS
# PERMITIDOS no relatório: SessionChart pode ter chart_type fora daqui (ex.:
# top_inventors/geographic_distribution do pipeline antigo) - esses nunca
# entram no .tex nem no painel de imagens do editor. A distribuição de
# classificações de patentes é tratada como CPC (pedido do usuário), mesmo
# sendo IPC na origem (a OPS não devolve CPC na busca final).
FIGURE_SPECS: dict[tuple[str, str], FigureSpec] = {
    ("article", "yearly_volume"): FigureSpec(
        "figura", "Histórico de publicações científicas (artigos por ano).", "informacoes_cientificas"
    ),
    ("article", "top_institutions"): FigureSpec(
        "figura", "Top 10 maiores instituições em quantidade de publicações científicas.", "informacoes_cientificas"
    ),
    ("article", "top10_heatmap"): FigureSpec(
        "quadro", "Áreas de estudo relacionadas às pesquisas científicas.", "informacoes_cientificas"
    ),
    ("patent", "yearly_volume"): FigureSpec(
        "figura", "Histórico de depósitos de patentes (patentes por ano).", "informacoes_tecnologicas"
    ),
    ("patent", "top_depositants"): FigureSpec(
        "figura", "Top 10 depositantes de patentes.", "informacoes_tecnologicas"
    ),
    ("patent", "top10_heatmap"): FigureSpec(
        "quadro", "10 classificações (CPC) mais encontradas.", "informacoes_tecnologicas"
    ),
    ("article", "s_curve"): FigureSpec(
        "figura", "Curva S relativa às informações científicas.", "tendencias_ciclo_vida"
    ),
    ("patent", "s_curve"): FigureSpec(
        "figura", "Curva S relativa às informações tecnológicas.", "tendencias_ciclo_vida"
    ),
}

# Ordem de apresentação dentro de cada seção quando a figura cai no fim
# (não posicionada pelo LLM) - a mesma do REPTEC: histórico, top, quadro.
FIGURE_ORDER = [
    "yearly_volume",
    "top_institutions",
    "top_depositants",
    "top10_heatmap",
    "s_curve",
]


def figure_id(document_type: str, chart_type: str) -> str:
    """Id estável de uma figura - o mesmo stem do PNG no MinIO
    (ex.: "article_yearly_volume")."""
    return f"{document_type}_{chart_type}"


@dataclass
class CatalogEntry:
    id: str
    kind: FigureKind
    caption: str  # já escapado pra LaTeX
    filename: str
    source: str = "O autor."
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def label(self) -> str:
        return f"{'quadro' if self.kind == 'quadro' else 'fig'}:{self.id}"


def sort_catalog(entries: list[CatalogEntry]) -> list[CatalogEntry]:
    def key(entry: CatalogEntry) -> tuple[int, str]:
        chart_type = entry.id.split("_", 1)[1] if "_" in entry.id else entry.id
        return (FIGURE_ORDER.index(chart_type) if chart_type in FIGURE_ORDER else len(FIGURE_ORDER), entry.id)

    return sorted(entries, key=key)


def figure_latex(entry: CatalogEntry) -> str:
    macro = r"\quadroimg" if entry.kind == "quadro" else r"\figura"
    return f"{macro}[{entry.source}]{{{entry.caption}\\label{{{entry.label}}}}}{{{entry.filename}}}"


# O texto chega aqui já escapado pra LaTeX (escape_latex transforma "_" em
# "\_"), então os ids nos marcadores podem vir com "\_".
_MARKER_RE = re.compile(r"\[\[(REF|FIG):\s*([A-Za-z0-9_\\]+?)\s*\]\]")


def _marker_id(raw: str) -> str:
    return raw.replace("\\_", "_")


# Artigo/contração antes do nome: "a Figura" <-> "o Quadro" etc.
_ARTICLE_FEM_TO_MASC = {"a": "o", "da": "do", "na": "no", "pela": "pelo", "à": "ao", "numa": "num", "uma": "um"}
_ARTICLE_MASC_TO_FEM = {v: k for k, v in _ARTICLE_FEM_TO_MASC.items()}


def _swap_article(article: str, mapping: dict[str, str]) -> str:
    swapped = mapping.get(article.lower())
    if swapped is None:
        return article
    return swapped[:1].upper() + swapped[1:] if article[:1].isupper() else swapped


def _fix_figure_word(text: str) -> str:
    """O LLM às vezes chama um Quadro de "Figura" (e vice-versa): a palavra
    antes do \\ref segue o tipo do rótulo (quadro:/fig:), com o artigo ou a
    contração anterior concordando ("a Figura" -> "o Quadro", "da" -> "do")."""
    def to_quadro(match: re.Match[str]) -> str:
        article = _swap_article(match.group(1), _ARTICLE_FEM_TO_MASC) if match.group(1) else ""
        word = "Quadro" if match.group(3) == "F" else "quadro"
        return f"{article}{match.group(2)}{word}{match.group(4)}"

    def to_figura(match: re.Match[str]) -> str:
        article = _swap_article(match.group(1), _ARTICLE_MASC_TO_FEM) if match.group(1) else ""
        word = "Figura" if match.group(3) == "Q" else "figura"
        return f"{article}{match.group(2)}{word}{match.group(4)}"

    fem = "|".join(sorted(_ARTICLE_FEM_TO_MASC, key=len, reverse=True))
    masc = "|".join(sorted(_ARTICLE_MASC_TO_FEM, key=len, reverse=True))
    text = re.sub(
        rf"(?:\b({fem})\b)?(\s*)\b([Ff])igura(\s*~?\s*\\ref\{{quadro:)", to_quadro, text, flags=re.IGNORECASE
    )
    return re.sub(
        rf"(?:\b({masc})\b)?(\s*)\b([Qq])uadro(\s*~?\s*\\ref\{{fig:)", to_figura, text, flags=re.IGNORECASE
    )


def place_figures(text: str, catalog: list[CatalogEntry], section_key: Optional[str] = None) -> tuple[str, list[str]]:
    """Troca `[[REF:id]]` por `\\ref{...}` e `[[FIG:id]]` pelo bloco LaTeX
    da figura; devolve (texto, avisos).

    - id desconhecido: marcador removido (+ aviso);
    - figura posicionada mais de uma vez: só a primeira ocorrência fica;
    - figura sem [[FIG:id]] mas CITADA no texto ([[REF:id]]/\\ref): entra
      logo depois do parágrafo que a cita pela primeira vez - o padrão do
      REPTEC (parágrafo que apresenta, figura, parágrafo que interpreta), em
      vez de todas empilhadas no fim da seção sem texto ao redor;
    - figura nunca citada: vai pro fim da seção (+ aviso).
    """
    by_id = {entry.id: entry for entry in catalog}
    warnings: list[str] = []
    placed: set[str] = set()

    # [[FIG:id]] vale como bloco próprio - o LLM às vezes cola no fim do
    # parágrafo em vez de deixar sozinho na linha; força quebra de parágrafo.
    def replace(match: re.Match[str]) -> str:
        kind, raw_id = match.group(1), _marker_id(match.group(2))
        entry = by_id.get(raw_id)
        if entry is None:
            warnings.append(f"id desconhecido no marcador {kind}:{raw_id}")
            return ""
        if kind == "REF":
            return f"\\ref{{{entry.label}}}"
        if raw_id in placed:
            warnings.append(f"figura {raw_id} posicionada mais de uma vez - mantida só a primeira")
            return ""
        placed.add(raw_id)
        return f"\n\n{figure_latex(entry)}\n\n"

    result = _MARKER_RE.sub(replace, text)

    leftovers = [entry for entry in sort_catalog(catalog) if entry.id not in placed]

    # Citadas mas não posicionadas: depois do parágrafo da 1ª citação.
    # Inserção de trás pra frente pra não deslocar as posições calculadas;
    # várias figuras citadas no mesmo parágrafo entram na ordem de citação.
    insertions: list[tuple[int, int, CatalogEntry]] = []
    uncited: list[CatalogEntry] = []
    for entry in leftovers:
        ref_pos = result.find(f"\\ref{{{entry.label}}}")
        if ref_pos == -1:
            uncited.append(entry)
            continue
        paragraph_end = result.find("\n\n", ref_pos)
        insertions.append((len(result) if paragraph_end == -1 else paragraph_end, ref_pos, entry))
        warnings.append(f"figura {entry.id} sem marcador [[FIG]] - inserida após o parágrafo que a cita")
    for position, _, entry in sorted(insertions, key=lambda item: (item[0], item[1]), reverse=True):
        result = result[:position] + f"\n\n{figure_latex(entry)}" + result[position:]

    for entry in uncited:
        warnings.append(f"figura {entry.id} não citada no texto - inserida no fim da seção")
    if uncited:
        result = result.rstrip() + "\n\n" + "\n\n".join(figure_latex(entry) for entry in uncited)

    result = _fix_figure_word(result)

    # Colapsa linhas em branco extras deixadas pelas trocas acima.
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    # Espaço antes de pontuação deixado por marcador removido ("texto .").
    result = re.sub(r"[ \t]+([.,;:])", r"\1", result)

    for warning in warnings:
        logger.warning("report_figure_placement", section=section_key, detail=warning)
    return result, warnings
