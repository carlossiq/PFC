"""Schemas for the report-graphics generation endpoint (POST /report/{session_id}/graphics)."""

from typing import Optional

from pydantic import BaseModel, Field


class GeneratedChart(BaseModel):
    """Um PNG gerado pelo ReportService - sempre desenhado em memória e
    devolvido em `image_base64` (nada é salvo em disco). `object_key` vem
    preenchido quando o upload pro MinIO deu certo (ver SessionChart) -
    "melhor esforço": pode vir vazio mesmo numa curva S se o storage
    estiver fora do ar. `projection_years` só vem preenchido pras curvas S
    - quantos anos a parte tracejada projeta além do último ano observado
    (ver PatentSCurveRequest/ArticleSCurveRequest).
    """

    filename: str
    image_base64: Optional[str] = None
    object_key: Optional[str] = None
    chart: str
    document_type: str
    projection_years: Optional[int] = None


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
    # Quantidade de anos (não um ano absoluto) que a parte tracejada projeta
    # além do último ano observado - editável na UI (default 5), persistido
    # em SessionChart.projection_years pra reabrir/consultar sem regenerar
    # mostrar o mesmo valor escolhido da última vez.
    projection_years: int = Field(default=5, ge=1, le=50)


class ArticleSCurveRequest(BaseModel):
    """Equivalente a `PatentSCurveRequest`, pro lado artigos (Scopus) - o
    chamador fornece `articles_by_year` (mesmo dict que `/chat/final/search`
    já devolve pra fonte Scopus), sem depender de documentos persistidos no
    banco.
    """

    articles_by_year: dict[str, int]
    growth_threshold: float = 0.10
    saturation_threshold: float = 0.90
    projection_years: int = Field(default=5, ge=1, le=50)


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


class TopEntitiesRequest(BaseModel):
    """Corpo da requisição do gráfico de barra horizontal top-K de entidades.

    `entity_counts` é um dict nome->contagem já agregado pelo chamador (ex.:
    o campo `counts` de `depositants`/`institutions` que
    `POST /inference/final-search` devolve) - não depende de documentos
    persistidos no banco. `chart_type` é explícito (diferente de
    `Top10HeatmapRequest`, que fixa "top10_heatmap") porque mais de uma
    distribuição desse formato pode existir pro mesmo `document_type` (ex.:
    "top depositantes" e o heatmap de CPC são ambos do lado patente) - sem
    isso colidiriam na mesma chave de storage/SessionChart.
    """

    entity_counts: dict[str, int]
    title: str = "Top 10"
    document_type: str = "patent"
    chart_type: str
    top_k: int = Field(default=10, ge=1, le=50)


class TopEntitiesResponse(BaseModel):
    """Resultado da geração do gráfico de barra horizontal top-K."""

    chart: Optional[GeneratedChart] = None
    skipped_reason: Optional[str] = None


class YearlyVolumeRequest(BaseModel):
    """Corpo da requisição do gráfico de barras de documentos por ano.

    Generaliza `PatentYearlyVolumeRequest` pra qualquer `document_type`
    (patente OU artigo) - mesmo formato de dado (`yearly_counts`), só
    passa a aceitar o lado artigo também.
    """

    document_type: str = "patent"
    yearly_counts: dict[str, int]


class YearlyVolumeResponse(BaseModel):
    """Resultado da geração do gráfico de barras de documentos por ano."""

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


class ArticleSCurveResponse(BaseModel):
    """Resultado da geração da curva S de artigos - mesmo formato do
    `patent_s_curve_fit`/`charts` embutidos em `ReportGraphicsResponse`,
    mas isolado numa rota própria (`POST /report/{session_id}/article-s-curve`)
    porque, diferente da curva de patentes, esta não precisa rodar junto do
    resto do report da sessão (`generate_session_report`).
    """

    chart: Optional[GeneratedChart] = None
    fit: Optional[SCurveFit] = None
    skipped_reason: Optional[str] = None


class ReportGraphicsResponse(BaseModel):
    """Manifesto dos gráficos gerados (ou pulados por falta de dado) para uma sessão."""

    session_id: int
    patents_used: int
    articles_used: int
    charts: list[GeneratedChart] = []
    skipped: list[str] = []
    patent_s_curve_fit: Optional[SCurveFit] = None


class ExistingChartResponse(BaseModel):
    """Gráfico já persistido pra query final atual de uma fonte (ver
    SessionChart), sem regenerar - `chart=None` quando a sessão ainda não
    tem query final dessa fonte, nenhum gráfico desse tipo foi gerado ainda,
    ou o download do storage falhou (melhor-esforço: o chamador cai pro
    caminho de gerar de novo nesse caso)."""

    chart: Optional[GeneratedChart] = None
