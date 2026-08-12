"""Schemas for the report-graphics generation endpoint (POST /report/{session_id}/graphics)."""

from typing import Optional

from pydantic import BaseModel


class GeneratedChart(BaseModel):
    """Um PNG gerado pelo ReportService."""

    filename: str
    path: str
    chart: str
    document_type: str


class PatentSCurveRequest(BaseModel):
    """Corpo da requisição da curva S de patentes.

    Substitui a derivação a partir de documentos persistidos no banco: o
    chamador fornece diretamente a contagem de patentes por ano (não
    acumulada) - normalmente o mesmo dict `patents_by_year` que
    `/chat/final/search` já devolve para a fonte OPS, permitindo gerar a
    curva imediatamente após a busca final, sem depender da sessão já ter
    sido persistida no banco.
    """

    patents_by_year: dict[str, int]
    growth_threshold: float = 0.10
    saturation_threshold: float = 0.90
    projection_end_year: Optional[int] = None


class PatentYearlyVolumeRequest(BaseModel):
    """Corpo da requisição do gráfico de barras de patentes por ano.

    Mesma fonte de dados de `PatentSCurveRequest.patents_by_year` (o dict
    que `/chat/final/search` já devolve para a fonte OPS) - sem os
    parâmetros de ajuste da curva S, que não se aplicam a este gráfico.
    """

    patents_by_year: dict[str, int]


class PatentYearlyVolumeResponse(BaseModel):
    """Resultado da geração do gráfico de barras de patentes por ano."""

    chart: Optional[GeneratedChart] = None
    skipped_reason: Optional[str] = None


class Top10HeatmapRequest(BaseModel):
    """Corpo da requisição do heatmap top-10.

    `top10` é um dict label->contagem já agregado pelo chamador (ex.: o
    dict `cpc` que `/chat/final/search` devolve para a fonte OPS, ou a
    distribuição de área de estudo de artigos) - o mesmo componente de
    heatmap serve para qualquer distribuição nesse formato, bastando trocar
    `title`/`document_type`.
    """

    top10: dict[str, int]
    title: str = "Top 10"
    document_type: str = "patent"


class Top10HeatmapResponse(BaseModel):
    """Resultado da geração do heatmap top-10."""

    chart: Optional[GeneratedChart] = None
    skipped_reason: Optional[str] = None


class SCurveFitQuality(BaseModel):
    """Diagnóstico de confiabilidade do ajuste da curva logística."""

    r_squared: float
    reliable: bool
    warning: Optional[str] = None


class SCurveFit(BaseModel):
    """Resultado do ajuste da curva logística de Fisher-Pry.

    K, r, t0 são os parâmetros do modelo N(t) = K / (1 + e^(-r*(t-t0))).
    gp_year/mp_year/sp_year são os anos dos pontos de Crescimento, Médio e
    Saturação (mp_year é sempre igual a t0). Ver `app.core.services.s_curve`
    para a explicação completa do modelo.
    """

    K: float
    r: float
    t0: float
    gp_year: float
    mp_year: float
    sp_year: float
    current_saturation: float
    years_observed: list[int]
    cumulative_observed: list[float]
    fit_quality: SCurveFitQuality


class ReportGraphicsResponse(BaseModel):
    """Manifesto dos gráficos gerados (ou pulados por falta de dado) para uma sessão."""

    session_id: int
    output_dir: str
    patents_used: int
    articles_used: int
    charts: list[GeneratedChart] = []
    skipped: list[str] = []
    patent_s_curve_fit: Optional[SCurveFit] = None
