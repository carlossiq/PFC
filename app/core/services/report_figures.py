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


def place_figures(text: str, catalog: list[CatalogEntry], section_key: Optional[str] = None) -> tuple[str, list[str]]:
    """Troca `[[REF:id]]` por `\\ref{...}` e `[[FIG:id]]` pelo bloco LaTeX
    da figura; devolve (texto, avisos).

    - id desconhecido: marcador removido (+ aviso);
    - figura posicionada mais de uma vez: só a primeira ocorrência fica;
    - figura do catálogo não posicionada (inclusive a que só tem
      [[REF:id]], sem [[FIG:id]]): vai pro fim da seção (+ aviso).
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
    for entry in leftovers:
        warnings.append(f"figura {entry.id} não posicionada no texto - inserida no fim da seção")
    if leftovers:
        result = result.rstrip() + "\n\n" + "\n\n".join(figure_latex(entry) for entry in leftovers)

    # Colapsa linhas em branco extras deixadas pelas trocas acima.
    result = re.sub(r"\n{3,}", "\n\n", result).strip()
    # Espaço antes de pontuação deixado por marcador removido ("texto .").
    result = re.sub(r"[ \t]+([.,;:])", r"\1", result)

    for warning in warnings:
        logger.warning("report_figure_placement", section=section_key, detail=warning)
    return result, warnings
