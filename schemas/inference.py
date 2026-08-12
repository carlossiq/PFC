"""
Schemas for the statistical-inference endpoint (POST /inference/final-search).

Enriquece o compilado agregado de uma busca final (OPS ou Scopus, ver
schemas/report.py e ChatService.run_final_search) pedindo mais iterações
até a amostra saturar (Chao1) ou o tempo acabar, e resume o resultado em
top-10 com estabilidade de ranking (bootstrap) + relevância semântica
(SBERT) - ver app/core/services/statistical_inference_service.py.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class StatisticalInferenceRequest(BaseModel):
    """
    Corpo da requisição de inferência estatística.

    `final_search_result` é o MESMO dict que `/chat/final/search` devolve
    em `data` (iteração 0) - precisa vir de lá porque é dessa amostra
    inicial que year_from/year_to são derivados (min/max das chaves de
    `patents_by_year`/`articles_by_year`) e porque é o ponto de partida da
    amostra acumulada, antes de pedir mais iterações. `query`/`api` são os
    mesmos usados pra gerar esse resultado - necessários pra poder rodar
    `run_final_search` de novo com `iteration` maior, se a amostra estiver
    insuficiente.
    """

    api: str = Field(
        ...,
        description="API de origem do final_search_result: 'ops' (patentes) ou 'scopus' (artigos)",
        example="ops",
    )
    query: dict[str, Any] = Field(
        ...,
        description="Mesmo dict de query usado na chamada original a /chat/final/search",
    )
    final_search_result: dict[str, Any] = Field(
        ...,
        description="O campo `data` devolvido por /chat/final/search (iteração 0) pra essa mesma query/api",
    )
    theme: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Tema inicial da pesquisa, usado pra calcular a relevância semântica (SBERT) com os títulos amostrados",
    )

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        """Valida e normaliza o tema."""
        return value.strip()

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "api": "ops",
                "query": {"query": '(TITLE:"heart") AND (pd within "20200101 20261231")'},
                "final_search_result": {
                    "depositants": {"Acme Corp": 5},
                    "cpc": {"A61B": 3},
                    "title": ["Cardiac monitor device"],
                    "patents_by_year": {"2020": 50, "2021": 60},
                    "strategy": "year",
                },
                "theme": "Wearable cardiac monitoring devices",
            }
        }


class Top10Block(BaseModel):
    """
    Top-10 de um campo (CPC, área de estudo, depositantes ou instituições),
    com a estabilidade de ranking (bootstrap) de cada entidade - fração das
    reamostragens em que ela permaneceu entre as 10 primeiras (0-1; quanto
    mais perto de 1, mais confiável é a posição dela no ranking).
    """

    top10: dict[str, float] = Field(
        ...,
        description="Nome da entidade/categoria -> estabilidade de ranking (bootstrap, 0-1)",
    )


class StatisticalInferenceResponse(BaseModel):
    """
    Resultado da inferência estatística: amostra enriquecida (se necessário
    e se deu tempo), resumida em top-10 por campo aplicável + relevância
    semântica média com o tema.

    Os campos de top-10/ano são condicionais ao `api`: patentes (ops)
    trazem `cpc`/`depositants`/`patents_by_year`; artigos (scopus) trazem
    `area_of_study`/`institutions`/`articles_by_year`. Os do outro tipo
    ficam `None`.
    """

    api: str
    score: float = Field(
        ...,
        description="Relevância semântica média (cosseno SBERT, 0-1) entre o tema e até N títulos amostrados",
    )
    iterations_used: int = Field(
        ...,
        description="Quantas iterações extras de run_final_search foram pedidas (0 = só a amostra original)",
    )
    elapsed_seconds: float = Field(
        ...,
        description="Tempo gasto no loop de enriquecimento da amostra",
    )
    stopped_reason: str = Field(
        ...,
        description="Por que o loop parou: 'saturated' | 'time_limit' | 'no_more_data' | 'fetch_error' | 'no_year_data'",
    )
    cpc: Optional[Top10Block] = None
    depositants: Optional[Top10Block] = None
    area_of_study: Optional[Top10Block] = None
    institutions: Optional[Top10Block] = None
    patents_by_year: Optional[dict[int, int]] = None
    articles_by_year: Optional[dict[int, int]] = None

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "api": "scopus",
                "score": 0.62,
                "iterations_used": 2,
                "elapsed_seconds": 8.4,
                "stopped_reason": "saturated",
                "area_of_study": {"top10": {"Medicine": 0.98, "Engineering": 0.81}},
                "institutions": {"top10": {"Aarhus Universitet": 0.65, "MIT": 0.9}},
                "articles_by_year": {"2020": 500, "2021": 600},
            }
        }
