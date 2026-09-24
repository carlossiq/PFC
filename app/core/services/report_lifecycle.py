"""
Resumos numéricos dos gráficos do relatório e estágio do ciclo de vida da
tecnologia - funções puras.

- Os resumos são calculados das MESMAS contagens usadas pra desenhar cada
  PNG (ver ReportService) e persistidos em SessionChart.summary - é o que o
  LLM recebe pra comentar cada figura (em vez de dizer "a evolução temporal
  não está disponível" logo antes do gráfico de patentes por ano).
- O estágio (Emergente/Crescimento/Maturidade/Saturação) é decidido aqui,
  comparando o ano de referência com os pontos GP/MP/SP da curva S (Ernst,
  1997; Kucharavy e De Guio, 2011) - o LLM só redige, nunca decide.
"""

from __future__ import annotations

import math
from datetime import date
from typing import Any, Optional


def last_complete_year(today: Optional[date] = None) -> int:
    return (today or date.today()).year - 1


def complete_years_only(counts: dict[int, int], today: Optional[date] = None) -> dict[int, int]:
    """Descarta o ano corrente (e futuros): o ano ainda em andamento tem
    contagem parcial, derruba o último ponto e distorce a curva S - o
    REPTEC de 2023 usou dados até 2022."""
    limit = last_complete_year(today)
    return {year: count for year, count in counts.items() if year <= limit}


def _pt(number: float) -> str:
    return f"{number:,.0f}".replace(",", ".")


def yearly_summary(counts: dict[int, int]) -> dict[str, Any]:
    years = sorted(counts)
    peak_year = max(years, key=lambda y: (counts[y], y))
    return {
        "total": int(sum(counts.values())),
        "first_year": years[0],
        "last_year": years[-1],
        "peak_year": peak_year,
        "peak_value": int(counts[peak_year]),
        "last_value": int(counts[years[-1]]),
    }


def top_summary(counts: dict[str, int], top_k: int) -> dict[str, Any]:
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top_k]
    return {"top": [[name, int(count)] for name, count in ranked], "entities": len(counts)}


def _year_or_none(value: Any) -> Optional[int]:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(value) or math.isinf(value) else int(round(value))


def s_curve_summary(fit: dict[str, Any], counts: dict[int, int]) -> dict[str, Any]:
    return {
        "gp": _year_or_none(fit.get("gp_year")),
        "mp": _year_or_none(fit.get("mp_year")),
        "sp": _year_or_none(fit.get("sp_year")),
        "saturation_level": _pt(fit.get("K", 0)),
        "current_saturation_pct": round(float(fit.get("current_saturation", 0)) * 100, 1),
        "first_year": min(counts),
        "last_year": max(counts),
        "cumulative": int(sum(counts.values())),
    }


def lifecycle_stage(summary: dict[str, Any], reference_year: Optional[int] = None) -> Optional[str]:
    """Emergente (< GP), Crescimento (GP-MP), Maturidade (MP-SP) ou
    Saturação (>= SP), comparando o ano de referência (último ano
    completo) com os pontos da curva."""
    gp, mp, sp = summary.get("gp"), summary.get("mp"), summary.get("sp")
    if mp is None:
        return None
    year = reference_year or last_complete_year()
    if gp is not None and year < gp:
        return "Emergente"
    if year < mp:
        return "Crescimento"
    if sp is None or year < sp:
        return "Maturidade"
    return "Saturação"


def build_lifecycle(curves: dict[str, dict[str, Any]], reference_year: Optional[int] = None) -> dict[str, Any]:
    """{"article"/"patent": {stage, gp, mp, sp}, "overall_stage"} - o estágio
    geral da tecnologia é o da curva de PATENTES (interesse comercial), com
    a de artigos como fallback (decisão do usuário)."""
    result: dict[str, Any] = {}
    for key in ("article", "patent"):
        summary = curves.get(key)
        if not summary:
            continue
        stage = lifecycle_stage(summary, reference_year)
        if stage:
            result[key] = {"stage": stage, "gp": summary.get("gp"), "mp": summary.get("mp"), "sp": summary.get("sp")}
    overall = (result.get("patent") or result.get("article") or {}).get("stage")
    if overall:
        result["overall_stage"] = overall
    return result


def summary_text(chart_type: str, summary: dict[str, Any]) -> str:
    """Resumo em pt-BR pro prompt (números já no formato brasileiro)."""
    if not summary:
        return "sem dados numéricos"
    if chart_type == "yearly_volume":
        return (
            f"total de {_pt(summary['total'])} documentos entre {summary['first_year']} e {summary['last_year']}; "
            f"pico em {summary['peak_year']} com {_pt(summary['peak_value'])}; "
            f"{_pt(summary['last_value'])} em {summary['last_year']}"
        )
    if chart_type in ("top_depositants", "top_institutions", "top10_heatmap"):
        items = "; ".join(f"{name} ({_pt(count)})" for name, count in summary["top"])
        return f"em ordem decrescente: {items}"
    if chart_type == "s_curve":
        points = ", ".join(
            f"{label} = {summary[key]}" for label, key in (("GP", "gp"), ("MP", "mp"), ("SP", "sp")) if summary.get(key)
        )
        return (
            f"{_pt(summary['cumulative'])} documentos acumulados entre {summary['first_year']} e "
            f"{summary['last_year']}; {points}; saturação atual estimada em "
            f"{str(summary['current_saturation_pct']).replace('.', ',')}% do nível de saturação ({summary['saturation_level']})"
        )
    return "sem dados numéricos"
