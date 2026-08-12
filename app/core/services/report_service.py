"""
Report chart generation for a research session's final-search documents.

Pure computation over plain dicts (year/applicants/inventors/... already
extracted from the ORM rows by the caller) - no DB/ORM access here, same
split as the rest of app/core/services: the driving adapter (report_router)
owns persistence, this module only owns the matplotlib/scipy/numpy/pandas
work and disk writes.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.colors as mcolors  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from app.core.services.s_curve import (  # noqa: E402
    SCurveFitError,
    fit_s_curve,
    logistic,
    project_s_curve,
)
from core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

# Papel fixo por elemento (não por rank) - azul para patente, aqua para
# artigo, violeta para a curva acumulada e laranja para a taxa de
# crescimento, consistentes em todos os gráficos. Ver dataviz skill.
_COLOR_PATENT = "#2a78d6"
_COLOR_ARTICLE = "#1baf7a"
_COLOR_CUMULATIVE = "#4a3aa7"
_COLOR_GROWTH = "#eb6834"
_COLOR_MARKER = "#d1495b"
_COLOR_TEXT = "#0b0b0b"
_COLOR_TEXT_MUTED = "#52514e"
_COLOR_GRID = "#e3e2dc"

_FIGSIZE_TIMELINE = (10, 5.5)
_FIGSIZE_SCURVE = (11.5, 5.5)
_FIGSIZE_BAR = (9, 6)
_DPI = 150
_TOP_K = 10
_CURVE_LINEWIDTH = 3.2
_PROJECTION_DASH = (0, (6, 4))

_DOCUMENT_LABELS = {"patent": "Patentes", "article": "Artigos"}

# Heatmap top-10 (grid 5x2 + legenda em gradiente) - reutilizado tanto para
# CPC de patentes quanto para área de estudo de artigos (ou qualquer outra
# distribuição label->contagem já agregada pelo chamador). Cores NUNCA são
# fixas: recalculadas a cada chamada a partir do min/max atual dos dados.
_HEATMAP_COLS = 5
_HEATMAP_TOP_K = 10
_HEATMAP_CMAP_NAME = "YlOrRd"
_DPI_HEATMAP = 200


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

        # a) curva S + evolução temporal (artigos). A curva S de patentes NÃO
        # é gerada aqui - ela vem de `generate_patent_s_curve`, a partir do
        # patents_by_year fornecido na requisição, não dos documentos do banco.
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

    def generate_patent_s_curve(
        self,
        session_id: int,
        patents_by_year: dict[str, int] | dict[int, int],
        growth_threshold: float = 0.10,
        saturation_threshold: float = 0.90,
        projection_end_year: Optional[int] = None,
    ) -> dict[str, Any]:
        """Ajusta e desenha a curva S (Fisher-Pry) de patentes a partir de
        uma contagem por ano já agregada e fornecida pelo chamador (ex.: o
        `patents_by_year` que `/chat/final/search` devolve para a fonte
        OPS) - não depende de documentos persistidos no banco.

        Returns:
            dict com "chart" (manifesto do PNG gerado, ou None se pulado),
            "fit" (dict de `fit_s_curve`, ou None se pulado) e
            "skipped_reason" (motivo textual se algo foi pulado, ou None).
        """
        session_dir = self.output_dir / f"session_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        yearly_counts = {int(year): int(count) for year, count in patents_by_year.items()}
        if len(yearly_counts) < 2:
            reason = (
                f"menos de 2 anos distintos com dados de patentes (recebido: {len(yearly_counts)})"
            )
            logger.warning("patent_s_curve_insufficient_data", session_id=session_id, reason=reason)
            return {"chart": None, "fit": None, "skipped_reason": reason}

        try:
            fit_result = fit_s_curve(yearly_counts, growth_threshold, saturation_threshold)
        except SCurveFitError as exc:
            logger.warning("patent_s_curve_fit_failed", session_id=session_id, error=str(exc))
            return {"chart": None, "fit": None, "skipped_reason": str(exc)}

        projection = None
        if projection_end_year is not None:
            projection = project_s_curve(fit_result, projection_end_year)

        path = self._render_s_curve_chart(yearly_counts, fit_result, projection, "patent", session_dir)

        return {
            "chart": {"filename": path.name, "path": str(path), "chart": "s_curve", "document_type": "patent"},
            "fit": fit_result,
            "skipped_reason": None,
        }

    def generate_patent_yearly_volume(
        self,
        session_id: int,
        patents_by_year: dict[str, int] | dict[int, int],
    ) -> dict[str, Any]:
        """Gera o gráfico de barras de patentes por ano, isolado da curva S.

        Antes esse volume era desenhado como barras sobrepostas ao eixo
        esquerdo do próprio gráfico da curva S; o novo estilo da curva S
        (Seção `_render_s_curve_chart`) usa esse eixo para a linha lisa de
        "Acumulado", então o volume por ano passa a ser um gráfico próprio,
        gerado por esta rota separada, a partir do mesmo `patents_by_year`
        que `/chat/final/search` já devolve para a fonte OPS - mesma fonte
        de dados de `generate_patent_s_curve`, sem os parâmetros de ajuste
        da curva, que não se aplicam aqui.

        Returns:
            dict com "chart" (manifesto do PNG gerado, ou None se pulado) e
            "skipped_reason" (motivo textual se pulado, ou None).
        """
        session_dir = self.output_dir / f"session_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        yearly_counts = {int(year): int(count) for year, count in patents_by_year.items()}
        if not yearly_counts:
            reason = "nenhum dado de patentes por ano fornecido"
            logger.warning("patent_yearly_volume_insufficient_data", session_id=session_id, reason=reason)
            return {"chart": None, "skipped_reason": reason}

        path = self._chart_yearly_volume(yearly_counts, "patent", session_dir)

        return {
            "chart": {
                "filename": path.name,
                "path": str(path),
                "chart": "yearly_volume",
                "document_type": "patent",
            },
            "skipped_reason": None,
        }

    def generate_top10_heatmap(
        self,
        session_id: int,
        top10: dict[str, int],
        title: str = "Top 10",
        document_type: str = "patent",
    ) -> dict[str, Any]:
        """Gera o heatmap top-10 (grid 5x2 + legenda em gradiente) de uma
        distribuição label->contagem já agregada pelo chamador - mesmo
        componente serve tanto para CPC de patentes (o dict `cpc` que
        `/chat/final/search` devolve para a fonte OPS) quanto para área de
        estudo de artigos ou qualquer outra distribuição desse formato, só
        mudando `title`/`document_type`.

        Returns:
            dict com "chart" (manifesto do PNG gerado, ou None se pulado) e
            "skipped_reason" (motivo textual se pulado, ou None).
        """
        session_dir = self.output_dir / f"session_{session_id}"
        session_dir.mkdir(parents=True, exist_ok=True)

        if not top10:
            reason = "nenhum dado de distribuição fornecido"
            logger.warning("top10_heatmap_insufficient_data", session_id=session_id, reason=reason)
            return {"chart": None, "skipped_reason": reason}

        items = sorted(top10.items(), key=lambda kv: kv[1], reverse=True)[:_HEATMAP_TOP_K]

        path = self._render_top10_heatmap(items, title, document_type, session_dir)

        return {
            "chart": {
                "filename": path.name,
                "path": str(path),
                "chart": "top10_heatmap",
                "document_type": document_type,
            },
            "skipped_reason": None,
        }

    def _chart_yearly_volume(
        self, yearly_counts: dict[int, int], document_type: str, out_dir: Path
    ) -> Path:
        """Desenha o gráfico de barras de volume de documentos por ano
        (contagem simples, sem ajuste nem acumulado)."""
        years_observed = sorted(yearly_counts)
        years = np.array(years_observed, dtype=float)
        yearly = np.array([yearly_counts[year] for year in years_observed], dtype=float)

        color = _COLOR_PATENT if document_type == "patent" else _COLOR_ARTICLE
        label = _DOCUMENT_LABELS[document_type]

        fig, ax = plt.subplots(figsize=_FIGSIZE_TIMELINE)
        ax.bar(years, yearly, color=color, width=0.7, zorder=2)
        ax.set_xlabel("Ano", color=_COLOR_TEXT)
        ax.set_ylabel(f"{label} por ano", color=_COLOR_TEXT)
        ax.tick_params(axis="both", colors=_COLOR_TEXT_MUTED)
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.grid(axis="y", color=_COLOR_GRID, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.set_title(f"{label} por Ano", color=_COLOR_TEXT, fontsize=13, loc="left")
        fig.tight_layout()

        path = out_dir / f"{document_type}_yearly_volume.png"
        fig.savefig(path, dpi=_DPI, facecolor="white")
        plt.close(fig)
        return path

    # ------------------------------------------------------------------
    # Heatmap top-10 (matplotlib puro - sem pandas)
    # ------------------------------------------------------------------

    @staticmethod
    def _heatmap_text_color(rgba: tuple[float, float, float, float]) -> str:
        """Luminância da cor de fundo decide se o texto fica branco ou preto -
        sem isso o número some em células muito escuras (vermelho) ou muito
        claras (quase branco)."""
        r, g, b = rgba[:3]
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "white" if luminance < 0.6 else "black"

    @staticmethod
    def _heatmap_compute_colors(
        values: list[float],
    ) -> tuple[list[tuple[float, float, float, float]], mcolors.Normalize, mcolors.Colormap]:
        """Recalcula a cor de cada célula a partir do min/max ATUAIS de
        `values` (nunca cores fixas por célula) - se o dataset mudar, a
        escala inteira (e toda cor derivada dela) muda junto."""
        cmap = plt.get_cmap(_HEATMAP_CMAP_NAME)
        norm = mcolors.Normalize(vmin=0, vmax=max(values) if values else 1)
        colors = [cmap(norm(value)) for value in values]
        return colors, norm, cmap

    @staticmethod
    def _format_heatmap_value(value: float) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:.1f}"

    def _add_heatmap_gradient_legend(
        self,
        ax: plt.Axes,
        cmap: mcolors.Colormap,
        norm: mcolors.Normalize,
        threshold: float,
    ) -> None:
        """Barra de gradiente horizontal - vermelho escuro (valor alto) na
        esquerda, branco (0) na direita: o INVERSO da leitura padrão de uma
        colorbar (baixo->alto), pra casar com a leitura visual do grid
        (célula mais "quente" = valor mais alto, sempre à esquerda da
        legenda)."""
        gradient = np.linspace(norm.vmax, norm.vmin, 256).reshape(1, -1)
        ax.imshow(gradient, aspect="auto", cmap=cmap, norm=norm, extent=(0, 1, 0, 1))
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.text(
            0.0, -0.55, f">{self._format_heatmap_value(threshold)}",
            transform=ax.transAxes, fontsize=9, color=_COLOR_TEXT, ha="left", va="top",
        )
        ax.text(
            1.0, -0.55, "0",
            transform=ax.transAxes, fontsize=9, color=_COLOR_TEXT, ha="right", va="top",
        )

    def _render_top10_heatmap(
        self,
        items: list[tuple[str, int]],
        title: str,
        document_type: str,
        out_dir: Path,
    ) -> Path:
        """Desenha o grid 5xN (bordas coladas, sem espaçamento) + legenda em
        gradiente abaixo. `items` já vem ordenado/limitado pelo chamador
        (`generate_top10_heatmap`); o grid comporta qualquer N <= 10, não só
        exatamente 10 (menos itens = menos linhas, não células vazias)."""
        labels = [label for label, _ in items]
        values = [float(value) for _, value in items]
        colors, norm, cmap = self._heatmap_compute_colors(values)

        cols = _HEATMAP_COLS
        rows = math.ceil(len(items) / cols)

        fig, (ax_grid, ax_legend) = plt.subplots(
            2,
            1,
            figsize=(cols * 2.1, rows * 2.1 + 1.1),
            gridspec_kw={"height_ratios": [rows * 2.1, 0.35], "hspace": 0.12},
        )
        fig.patch.set_facecolor("white")

        for i, (label, value, color) in enumerate(zip(labels, values, colors)):
            row, col = divmod(i, cols)
            y0 = rows - 1 - row
            ax_grid.add_patch(Rectangle((col, y0), 1, 1, facecolor=color, edgecolor=color, linewidth=0))
            text_color = self._heatmap_text_color(color)
            ax_grid.text(
                col + 0.5, y0 + 0.58, self._format_heatmap_value(value),
                ha="center", va="center", fontsize=22, fontweight="bold", color=text_color,
            )
            ax_grid.text(
                col + 0.5, y0 + 0.28, label,
                ha="center", va="center", fontsize=10, alpha=0.85, color=text_color,
            )

        ax_grid.set_xlim(0, cols)
        ax_grid.set_ylim(0, rows)
        ax_grid.set_aspect("equal")
        ax_grid.axis("off")
        ax_grid.set_title(title, color=_COLOR_TEXT, fontsize=13, loc="left")

        threshold = float(np.percentile(values, 90)) if values else 0.0
        self._add_heatmap_gradient_legend(ax_legend, cmap, norm, threshold)

        fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.16)

        path = out_dir / f"{document_type}_top10_heatmap.png"
        fig.savefig(path, dpi=_DPI_HEATMAP, facecolor="white")
        plt.close(fig)
        return path

    def _chart_s_curve(
        self, documents: list[dict[str, Any]], document_type: str, out_dir: Path
    ) -> Optional[Path]:
        counts = self._yearly_counts(documents)
        if counts is None or len(counts) < 2:
            return None

        yearly_counts = {int(year): int(count) for year, count in counts.items()}

        fit_result = None
        try:
            fit_result = fit_s_curve(yearly_counts)
        except SCurveFitError as exc:
            logger.warning("s_curve_fit_failed", document_type=document_type, error=str(exc))

        return self._render_s_curve_chart(yearly_counts, fit_result, None, document_type, out_dir)

    def _render_s_curve_chart(
        self,
        yearly_counts: dict[int, int],
        fit_result: Optional[dict[str, Any]],
        projection: Optional[dict[str, list[float]]],
        document_type: str,
        out_dir: Path,
    ) -> Path:
        """Desenha o PNG da curva S: acumulado e taxa de crescimento como
        curvas lisas (sem o gráfico de barras por ano, que agora é gerado à
        parte por `_chart_yearly_volume` / `generate_patent_yearly_volume`).

        Cada curva é sólida do primeiro ano observado até o último (dado
        real) e tracejada dali em diante, na parte projetada por
        `projection` (se fornecida). Os pontos de leitura GP/MP/SP, quando
        dentro do range desenhado, viram marcadores sobre a própria curva
        de acumulado, com o ano anotado ao lado - substituindo as antigas
        linhas verticais pontilhadas.

        Os dois eixos Y usam os valores do MESMO ajuste logístico já
        calculado por `fit_s_curve` (K, r, t0) e reamostrados em uma grade
        densa apenas para deixar o traço visualmente liso - nenhum dado ou
        cálculo novo é introduzido aqui além do já existente em
        `app.core.services.s_curve`.
        """
        years_observed = sorted(yearly_counts)
        first_year, last_year = years_observed[0], years_observed[-1]

        color = _COLOR_PATENT if document_type == "patent" else _COLOR_ARTICLE
        label = _DOCUMENT_LABELS[document_type]

        fig, ax1 = plt.subplots(figsize=_FIGSIZE_SCURVE)
        fig.patch.set_facecolor("white")
        ax1.set_facecolor("white")
        handles: list[Any] = []

        if fit_result is not None:
            K, r, t0 = fit_result["K"], fit_result["r"], fit_result["t0"]

            end_year = last_year
            if projection is not None and projection["years"]:
                end_year = max(last_year, projection["years"][-1])

            t_dense = np.linspace(first_year, end_year, 400)
            cumulative_dense = logistic(t_dense, K, r, t0)
            growth_dense = np.gradient(cumulative_dense, t_dense)

            observed_mask = t_dense <= last_year
            projected_mask = t_dense >= last_year

            (line_cumulative,) = ax1.plot(
                t_dense[observed_mask], cumulative_dense[observed_mask],
                color=_COLOR_CUMULATIVE, linewidth=_CURVE_LINEWIDTH, solid_capstyle="round",
                label="Acumulado",
            )
            if projected_mask.sum() > 1:
                ax1.plot(
                    t_dense[projected_mask], cumulative_dense[projected_mask],
                    color=_COLOR_CUMULATIVE, linewidth=_CURVE_LINEWIDTH, linestyle=_PROJECTION_DASH,
                    solid_capstyle="round",
                )
            handles.append(line_cumulative)
            ax1.set_ylabel("Acumulado", color=_COLOR_CUMULATIVE)
            ax1.tick_params(axis="y", colors=_COLOR_CUMULATIVE)
            ax1.spines["left"].set_color(_COLOR_CUMULATIVE)

            ax2 = ax1.twinx()
            (line_growth,) = ax2.plot(
                t_dense[observed_mask], growth_dense[observed_mask],
                color=_COLOR_GROWTH, linewidth=_CURVE_LINEWIDTH, solid_capstyle="round",
                label="Taxa de crescimento",
            )
            if projected_mask.sum() > 1:
                ax2.plot(
                    t_dense[projected_mask], growth_dense[projected_mask],
                    color=_COLOR_GROWTH, linewidth=_CURVE_LINEWIDTH, linestyle=_PROJECTION_DASH,
                    solid_capstyle="round",
                )
            handles.append(line_growth)
            ax2.set_ylabel("Taxa de crescimento (documentos/ano)", color=_COLOR_GROWTH)
            ax2.tick_params(axis="y", colors=_COLOR_GROWTH)
            ax2.spines["right"].set_color(_COLOR_GROWTH)
            ax2.spines["top"].set_visible(False)
            ax2.grid(False)

            # Marcadores de GP/MP/SP sobre a própria curva de acumulado, só
            # desenhados se caírem dentro do range visível (observado +
            # projeção), pra não esticar o eixo x quando o ajuste degenerar.
            for year_value, marker_label in (
                (fit_result["gp_year"], "GP"),
                (fit_result["mp_year"], "MP"),
                (fit_result["sp_year"], "SP"),
            ):
                if math.isfinite(year_value) and first_year <= year_value <= end_year:
                    y_value = logistic(year_value, K, r, t0)
                    ax1.scatter(
                        [year_value], [y_value], color=_COLOR_MARKER, s=64, zorder=5,
                        edgecolor="white", linewidth=1.2,
                    )
                    ax1.annotate(
                        f"{marker_label} · {int(round(year_value))}",
                        xy=(year_value, y_value), xytext=(6, 6), textcoords="offset points",
                        fontsize=8, color=_COLOR_TEXT, fontweight="bold",
                    )

            if not fit_result["fit_quality"]["reliable"]:
                ax1.text(
                    0.02, 0.98, f"⚠ Ajuste pouco confiável: {fit_result['fit_quality']['warning']}",
                    transform=ax1.transAxes, fontsize=7, color="#b23b3b", va="top", ha="left", wrap=True,
                    bbox=dict(boxstyle="round", facecolor="white", edgecolor="#b23b3b", alpha=0.85),
                )
        else:
            # Sem ajuste confiável: mostra só o acumulado real observado,
            # como linha lisa - sem taxa de crescimento (não há modelo do
            # qual derivá-la) nem marcadores de GP/MP/SP.
            yearly = np.array([yearly_counts[year] for year in years_observed], dtype=float)
            cumulative_observed = np.cumsum(yearly)
            (line_cumulative,) = ax1.plot(
                years_observed, cumulative_observed,
                color=_COLOR_CUMULATIVE, linewidth=_CURVE_LINEWIDTH, solid_capstyle="round",
                label="Acumulado (observado)",
            )
            handles.append(line_cumulative)
            ax1.set_ylabel("Acumulado", color=_COLOR_CUMULATIVE)
            ax1.tick_params(axis="y", colors=_COLOR_CUMULATIVE)
            ax1.spines["left"].set_color(_COLOR_CUMULATIVE)

        ax1.set_xlabel("Ano", color=_COLOR_TEXT)
        ax1.tick_params(axis="x", colors=_COLOR_TEXT_MUTED)
        ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax1.grid(False)
        ax1.spines["top"].set_visible(False)
        ax1.spines["right"].set_visible(False)

        ax1.legend(
            handles=handles, loc="center left", bbox_to_anchor=(1.14, 0.5),
            frameon=False, fontsize=9, handlelength=1.6,
        )
        ax1.set_title(f"Curva S e Evolução Temporal — {label}", color=_COLOR_TEXT, fontsize=13, loc="left")
        fig.subplots_adjust(left=0.09, right=0.78, top=0.9, bottom=0.12)

        path = out_dir / f"{document_type}_s_curve.png"
        # bbox_inches="tight" - a legenda fica fora da área dos eixos (à
        # direita), então sem isso o savefig corta o texto na borda da
        # figura em vez de expandir o canvas pra acomodá-la.
        fig.savefig(path, dpi=_DPI, facecolor="white", bbox_inches="tight")
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
