"""
Request schemas for API endpoints.

Define estruturas tipadas para request bodies complexos,
melhorando documentação no Swagger e validação de entrada.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchQuery(BaseModel):
    """Query estruturada para busca em APIs de patentes/artigos."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Query string (CQL para OPS)",
        example="(TITLE:(machine learning) OR ABSTRACT:(artificial intelligence)) AND (IPC:G06N) AND (PD>=20150101 AND PD<=20261231)",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "query": "(TITLE:(machine learning) OR ABSTRACT:(artificial intelligence)) AND (IPC:G06N) AND (PD>=20150101 AND PD<=20261231)",
            }
        }


class ProbeSearchRequest(BaseModel):
    """
    Request para execução de probe search com abstracts.

    Usa o endpoint /search/abstract do OPS que já retorna abstracts.
    """

    query: SearchQuery = Field(
        ...,
        description="Query para busca em CQL",
    )
    api: str = Field(
        ...,
        description="API a usar: ops",
        example="ops",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Número de resultados a retornar (1-100)",
        example=10,
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "query": {
                    "query": "(TITLE:(machine learning) OR ABSTRACT:(artificial intelligence)) AND (IPC:G06N)",
                },
                "api": "ops",
                "top_k": 10,
            }
        }


class ProbeEnrichRequest(BaseModel):
    """
    Request para enriquecimento de resultados de probe search.

    Toma resultados brutos e adiciona dados bibliográficos
    (título, abstract, inventors, applicants) aos top_k resultados.
    """

    results: list[dict[str, Any]] = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="Resultados brutos retornados por /probe/search",
    )
    api: str = Field(
        ...,
        description="API a usar (apenas 'ops' suporta enriquecimento)",
        example="ops",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Número de resultados a enriquecer (default 10)",
        example=10,
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "raw": {
                            "ops:publication-reference": {
                                "document-id": {
                                    "country": {"$": "CN"},
                                    "doc-number": {"$": "121789955"},
                                    "kind": {"$": "A"},
                                }
                            }
                        }
                    }
                ],
                "api": "ops",
                "top_k": 10,
            }
        }


class TermExtractionRequest(BaseModel):
    """
    Request para extração de termos relevantes.

    Extrai termos de uma lista de items (title + abstract) usando KeyBERT + TF-IDF,
    com pesos configuráveis (título 3.0, abstract 1.0 por padrão).
    Remove termos já presentes nos parâmetros originais.
    """

    items: list[dict[str, Any]] = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="Lista de items com title e abstract para extração de termos",
        example=[
            {
                "title": "Computer-aided diagnosis method based on deep learning",
                "abstract": "The invention discloses a computer-aided diagnosis method leveraging neural networks...",
            }
        ],
    )
    original_params: dict[str, Any] = Field(
        default={},
        description="Parâmetros originais da busca (theme, description, keywords) para filtrar termos",
    )
    top_k: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Número de termos relevantes a extrair",
        example=20,
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "title": "Deep learning for medical image analysis",
                        "abstract": "This paper presents a comprehensive review of deep learning techniques applied to medical imaging...",
                    },
                    {
                        "title": "Convolutional neural networks in healthcare",
                        "abstract": "CNNs have shown remarkable performance in various healthcare applications including diagnosis...",
                    },
                ],
                "original_params": {
                    "theme": "machine learning",
                    "keywords": ["deep learning"],
                },
                "top_k": 20,
            }
        }


class FinalSearchRequest(BaseModel):
    """Request para execução de busca final (produção)."""

    query: SearchQuery = Field(
        ...,
        description="Query final em CQL",
    )
    api: str = Field(
        ...,
        description="API a usar: ops",
        example="ops",
    )
    max_results: int = Field(
        default=500,
        ge=1,
        le=1000,
        description="Máximo de resultados a retornar",
        example=500,
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "query": {
                    "query": "(TITLE:(machine learning) OR ABSTRACT:(artificial intelligence)) AND (IPC:G06N) AND (PD>=20150101 AND PD<=20261231)",
                },
                "api": "ops",
                "max_results": 500,
            }
        }
