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


# Unidade de contagem por tipo de documento (singular, plural) - sem ela o
# LLM chamava patentes de "publicações científicas" (o resumo dizia só
# "documentos").
_UNITS = {
    "patent": ("patente depositada", "patentes depositadas"),
    "article": ("publicação científica", "publicações científicas"),
}
_DEFAULT_UNIT = ("documento", "documentos")


def _count(value: int, document_type: Optional[str]) -> str:
    singular, plural = _UNITS.get(document_type or "", _DEFAULT_UNIT)
    return f"{_pt(value)} {singular if value == 1 else plural}"


def _pct(value: float) -> str:
    return str(value).replace(".", ",")


def summary_text(chart_type: str, summary: dict[str, Any], document_type: Optional[str] = None) -> str:
    """Resumo em pt-BR pro prompt (números já no formato brasileiro), com a
    unidade de cada número explícita: quantidades dizem de quê ("7 patentes
    depositadas"), anos dizem que são anos, acumulado diz que é acumulado e
    ranking vem numerado - um modelo pequeno confundia ano com quantidade
    ("pico de 2007 publicações") e invertia a ordem dos primeiros colocados."""
    if not summary:
        return "sem dados numéricos"
    if chart_type == "yearly_volume":
        return (
            f"total de {_count(summary['total'], document_type)} entre os anos de {summary['first_year']} e "
            f"{summary['last_year']}; maior valor anual (pico) no ano de {summary['peak_year']}, com "
            f"{_count(summary['peak_value'], document_type)} naquele ano; "
            f"{_count(summary['last_value'], document_type)} no último ano ({summary['last_year']})"
        )
    if chart_type in ("top_depositants", "top_institutions", "top10_heatmap"):
        items = "; ".join(
            f"{rank}º {name} ({_count(count, document_type)})" for rank, (name, count) in enumerate(summary["top"], 1)
        )
        leader = summary["top"][0][0] if summary["top"] else None
        lead = f"o 1º colocado (o que lidera) é {leader}; " if leader else ""
        return f"{lead}ranking em ordem decrescente: {items}"
    if chart_type == "s_curve":
        points = "; ".join(
            f"{label} no ano de {summary[key]}"
            for label, key in (
                ("ponto de crescimento (GP)", "gp"),
                ("ponto médio (MP)", "mp"),
                ("ponto de saturação (SP)", "sp"),
            )
            if summary.get(key)
        )
        pct = float(summary.get("current_saturation_pct") or 0)
        plateau = f"{summary['saturation_level']} {_UNITS.get(document_type or '', _DEFAULT_UNIT)[1]}"
        if pct > 100:
            saturation = (
                f"o total observado já SUPERA o platô estimado pela curva ({plateau}), "
                "ou seja, a curva está saturada (não informe percentual de saturação)"
            )
        else:
            saturation = (
                f"o total observado corresponde a {_pct(pct)}% do platô estimado pela curva "
                f"({plateau})"
            )
        return (
            f"ACUMULADO (soma de todos os anos, não é valor anual) de {_count(summary['cumulative'], document_type)} "
            f"entre os anos de {summary['first_year']} e {summary['last_year']}; {points} (GP/MP/SP são ANOS, "
            f"nunca quantidades); {saturation}"
        )
    return "sem dados numéricos"
