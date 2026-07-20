"""
Report chart generation for a research session's final-search documents.

Pure computation over plain dicts (year/applicants/inventors/... already
extracted from the ORM rows by the caller) - no DB/ORM access here, same
split as the rest of app/core/services: the driving adapter (report_router)
owns persistence, this module only owns the matplotlib/scipy/numpy/pandas
work and disk writes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.optimize import curve_fit  # noqa: E402

from core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

# Papel fixo por elemento (não por rank) - azul para patente, aqua para
# artigo, violeta para a curva acumulada e laranja para a taxa de
# crescimento, consistentes em todos os gráficos. Ver dataviz skill.
_COLOR_PATENT = "#2a78d6"
_COLOR_ARTICLE = "#1baf7a"
_COLOR_CUMULATIVE = "#4a3aa7"
_COLOR_GROWTH = "#eb6834"
_COLOR_TEXT = "#0b0b0b"
_COLOR_TEXT_MUTED = "#52514e"
_COLOR_GRID = "#e3e2dc"

_FIGSIZE_TIMELINE = (10, 5.5)
_FIGSIZE_BAR = (9, 6)
_DPI = 150
_TOP_K = 10

_DOCUMENT_LABELS = {"patent": "Patentes", "article": "Artigos"}


class ReportService:
    """Gera os PNGs de report (curva S, top entidades, distribuições) para uma sessão."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_session_report(
        self,
        session_id: int,
        patents: list[dict[str, Any]],
        articles: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Gera todos os gráficos aplicáveis (pula os que não têm dado o
        suficiente) e devolve o manifesto de arquivos gerados."""
        session_dir = self.output_dir / f"session_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        charts: list[dict[str, str]] = []
        skipped: list[str] = []

        def _add(chart: str, document_type: str, path: Optional[Path]) -> None:
            if path is None:
                skipped.append(f"{document_type}:{chart}")
                return
            charts.append(
                {
                    "filename": path.name,
                    "path": str(path),
                    "chart": chart,
                    "document_type": document_type,
                }
            )

        # a) curva S + evolução temporal
        _add("s_curve", "patent", self._chart_s_curve(patents, "patent", session_dir))
        _add("s_curve", "article", self._chart_s_curve(articles, "article", session_dir))

        # b/c) top depositantes / inventores (só patente)
        _add(
            "top_applicants",
            "patent",
            self._chart_top_entities(
                patents, "applicants", True, "patent", "top_applicants", "Top Depositantes", session_dir
            ),
        )
        _add(
            "top_inventors",
            "patent",
            self._chart_top_entities(
                patents, "inventors", True, "patent", "top_inventors", "Top Inventores", session_dir
            ),
        )

        # d/e) top autores / periódicos (só artigo)
        _add(
            "top_authors",
            "article",
            self._chart_top_entities(
                articles, "authors", True, "article", "top_authors", "Top Autores", session_dir
            ),
        )
        _add(
            "top_journals",
            "article",
            self._chart_top_entities(
                articles,
                "journal_or_source",
                False,
                "article",
                "top_journals",
                "Top Periódicos",
                session_dir,
            ),
        )

        # f/g) distribuição CPC / IPC (só patente)
        _add(
            "cpc_distribution",
            "patent",
            self._chart_top_entities(
                patents, "cpc_codes", True, "patent", "cpc_distribution", "Distribuição por CPC", session_dir
            ),
        )
        _add(
            "ipc_distribution",
            "patent",
            self._chart_top_entities(
                patents, "ipc_codes", True, "patent", "ipc_distribution", "Distribuição por IPC", session_dir
            ),
        )

        # h) distribuição por área de estudo (só artigo)
        _add(
            "field_of_study_distribution",
            "article",
            self._chart_top_entities(
                articles,
                "field_of_study",
                True,
                "article",
                "field_of_study_distribution",
                "Distribuição por Área de Estudo",
                session_dir,
            ),
        )

        # i) distribuição geográfica (patente e artigo)
        _add(
            "geographic_distribution",
            "patent",
            self._chart_top_entities(
                patents,
                "country",
                False,
                "patent",
                "geographic_distribution",
                "Distribuição Geográfica",
                session_dir,
            ),
        )
        _add(
            "geographic_distribution",
            "article",
            self._chart_top_entities(
                articles,
                "affiliation_countries",
                True,
                "article",
                "geographic_distribution",
                "Distribuição Geográfica",
                session_dir,
            ),
        )

        logger.info(
            "report_charts_generated",
            session_id=session_id,
            patents_used=len(patents),
            articles_used=len(articles),
            charts_count=len(charts),
            skipped_count=len(skipped),
        )

        return {
            "session_id": session_id,
            "output_dir": str(session_dir),
            "patents_used": len(patents),
            "articles_used": len(articles),
            "charts": charts,
            "skipped": skipped,
        }

    # ------------------------------------------------------------------
    # Agregação (pandas)
    # ------------------------------------------------------------------

    @staticmethod
    def _yearly_counts(documents: list[dict[str, Any]]) -> Optional[pd.Series]:
        """Contagem por ano, reindexada no range completo (anos sem
        publicação entram como 0) - filtra nulos antes de agregar."""
        years = [int(doc["year"]) for doc in documents if doc.get("year")]
        if not years:
            return None
        counts = pd.Series(years).value_counts().sort_index()
        full_index = pd.RangeIndex(int(counts.index.min()), int(counts.index.max()) + 1)
        return counts.reindex(full_index, fill_value=0)

    @staticmethod
    def _ranked_counts(
        documents: list[dict[str, Any]], field: str, is_list: bool, top_k: int = _TOP_K
    ) -> Optional[pd.Series]:
        """Top-K valores mais frequentes de um campo (lista JSON ou escalar),
        em ordem ascendente (pra barh mostrar o maior no topo)."""
        if is_list:
            values = [
                str(v).strip()
                for doc in documents
                for v in (doc.get(field) or [])
                if v and str(v).strip()
            ]
        else:
            values = [str(doc[field]).strip() for doc in documents if doc.get(field) and str(doc[field]).strip()]

        if not values:
            return None

        counts = pd.Series(values).value_counts().head(top_k)
        return counts.iloc[::-1]

    # ------------------------------------------------------------------
    # Curva S / evolução temporal (numpy + scipy)
    # ------------------------------------------------------------------

    @staticmethod
    def _logistic(x: np.ndarray, capacity: float, growth: float, midpoint: float) -> np.ndarray:
        return capacity / (1 + np.exp(-growth * (x - midpoint)))

    def _chart_s_curve(
        self, documents: list[dict[str, Any]], document_type: str, out_dir: Path
    ) -> Optional[Path]:
        counts = self._yearly_counts(documents)
        if counts is None or len(counts) < 2:
            return None

        years = counts.index.to_numpy(dtype=float)
        yearly = counts.to_numpy(dtype=float)
        cumulative = np.cumsum(yearly)

        fitted = None
        growth_rate = None
        try:
            p0 = [max(cumulative[-1] * 1.1, 1.0), 0.5, float(np.median(years))]
            params, _ = curve_fit(self._logistic, years, cumulative, p0=p0, maxfev=5000)
            fitted = self._logistic(years, *params)
            growth_rate = np.gradient(fitted, years)
        except (RuntimeError, ValueError) as exc:
            logger.warning("s_curve_fit_failed", document_type=document_type, error=str(exc))

        color = _COLOR_PATENT if document_type == "patent" else _COLOR_ARTICLE
        label = _DOCUMENT_LABELS[document_type]

        fig, ax1 = plt.subplots(figsize=_FIGSIZE_TIMELINE)
        ax1.bar(years, yearly, color=color, alpha=0.85, width=0.7, label=f"{label} por ano", zorder=2)
        ax1.set_xlabel("Ano", color=_COLOR_TEXT)
        ax1.set_ylabel(f"{label} por ano", color=_COLOR_TEXT)
        ax1.tick_params(axis="both", colors=_COLOR_TEXT_MUTED)
        ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax1.grid(axis="y", color=_COLOR_GRID, linewidth=0.8, zorder=0)
        ax1.set_axisbelow(True)
        for spine in ("top",):
            ax1.spines[spine].set_visible(False)

        ax2 = ax1.twinx()
        ax2.plot(years, cumulative, color=_COLOR_CUMULATIVE, marker="o", markersize=4, linewidth=2, label="Acumulado")
        if fitted is not None:
            ax2.plot(
                years, fitted, color=_COLOR_CUMULATIVE, linestyle="--", linewidth=1.5, alpha=0.6,
                label="Curva S (ajuste logístico)",
            )
        ax2.set_ylabel("Acumulado", color=_COLOR_CUMULATIVE)
        ax2.tick_params(axis="y", colors=_COLOR_CUMULATIVE)
        ax2.spines["right"].set_color(_COLOR_CUMULATIVE)

        handles, labels = ax1.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        handles, labels = handles + h2, labels + l2

        if growth_rate is not None:
            ax3 = ax1.twinx()
            ax3.spines["right"].set_position(("axes", 1.15))
            ax3.plot(years, growth_rate, color=_COLOR_GROWTH, linestyle=":", linewidth=1.5, label="Taxa de crescimento")
            ax3.set_ylabel("Taxa de crescimento (documentos/ano)", color=_COLOR_GROWTH)
            ax3.tick_params(axis="y", colors=_COLOR_GROWTH)
            ax3.spines["right"].set_color(_COLOR_GROWTH)
            h3, l3 = ax3.get_legend_handles_labels()
            handles, labels = handles + h3, labels + l3

        ax1.legend(handles, labels, loc="upper left", frameon=False, fontsize=9)
        ax1.set_title(f"Curva S e Evolução Temporal — {label}", color=_COLOR_TEXT, fontsize=13, loc="left")
        fig.tight_layout()

        path = out_dir / f"{document_type}_s_curve.png"
        fig.savefig(path, dpi=_DPI, facecolor="white")
        plt.close(fig)
        return path

    # ------------------------------------------------------------------
    # Rankings / distribuições (pandas + matplotlib)
    # ------------------------------------------------------------------

    def _chart_top_entities(
        self,
        documents: list[dict[str, Any]],
        field: str,
        is_list: bool,
        document_type: str,
        chart_slug: str,
        title: str,
        out_dir: Path,
        top_k: int = _TOP_K,
    ) -> Optional[Path]:
        counts = self._ranked_counts(documents, field, is_list, top_k)
        if counts is None:
            return None

        color = _COLOR_PATENT if document_type == "patent" else _COLOR_ARTICLE
        label = _DOCUMENT_LABELS[document_type]

        fig, ax = plt.subplots(figsize=_FIGSIZE_BAR)
        bars = ax.barh(counts.index.astype(str), counts.to_numpy(), color=color, zorder=2)
        ax.bar_label(bars, padding=3, color=_COLOR_TEXT, fontsize=8)
        ax.set_xlabel(f"Nº de {label.lower()}", color=_COLOR_TEXT)
        ax.tick_params(axis="both", colors=_COLOR_TEXT_MUTED, labelsize=9)
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.grid(axis="x", color=_COLOR_GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.set_title(f"{title} — {label}", color=_COLOR_TEXT, fontsize=13, loc="left")
        fig.tight_layout()

        path = out_dir / f"{document_type}_{chart_slug}.png"
        fig.savefig(path, dpi=_DPI, facecolor="white")
        plt.close(fig)
        return path
