"""
Search request and response schemas for the prospecting API.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from schemas.document import DocumentBatch, PatentDocument, PublicationDocument
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from schemas.query_builder import QueryBuilderOutput


class SearchRequest(BaseModel):
    """
    Requisição de busca de prospecção tecnológica.

    Contém os parâmetros de entrada do usuário que iniciam
    o pipeline completo de busca e análise.
    """

    intake: InputIntake = Field(
        ...,
        description="Parâmetros de entrada do usuário",
    )
    llm_output: Optional[LLMOutput] = Field(
        default=None,
        description="Saída do modelo LLM (opcional para submissão direta)",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "intake": {
                    "theme": "Machine Learning in Healthcare",
                    "objective": "Diagnostic AI systems",
                    "initial_keywords": ["deep learning", "medical imaging"],
                    "document_type": "both",
                },
            }
        }


class SearchMetadata(BaseModel):
    """
    Metadados da execução de busca.

    Rastreia informações sobre como a busca foi executada
    e seus resultados agregados.
    """

    search_id: str = Field(
        ...,
        description="Identificador único da busca",
    )
    run_id: str = Field(
        ...,
        description="Identificador único da requisição HTTP",
    )
    status: str = Field(
        default="completed",
        description="Status da busca (running, completed, failed)",
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de início da busca",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Data/hora de conclusão da busca",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Duração total da busca em segundos",
    )
    query_count: int = Field(
        default=0,
        description="Número de cláusulas de busca executadas",
    )
    total_documents_found: int = Field(
        default=0,
        description="Número total de documentos encontrados",
    )
    documents_returned: int = Field(
        default=0,
        description="Número de documentos retornados",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "search_id": "search_550e8400-e29b-41d4-a716",
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "completed",
                "started_at": "2024-03-29T10:30:00Z",
                "completed_at": "2024-03-29T10:35:15Z",
                "duration_seconds": 315.5,
                "query_count": 5,
                "total_documents_found": 1250,
                "documents_returned": 100,
            }
        }


class SearchResponse(BaseModel):
    """
    Resposta completa de uma busca de prospecção.

    Agrupa metadados da busca, saída do LLM, consultas construídas
    e documentos recuperados em uma resposta estruturada.
    """

    metadata: SearchMetadata = Field(
        ...,
        description="Metadados da busca",
    )
    intake: InputIntake = Field(
        ...,
        description="Parâmetros de entrada originais",
    )
    llm_output: Optional[LLMOutput] = Field(
        default=None,
        description="Saída do modelo LLM com consultas estruturadas",
    )
    query_builder_output: Optional[QueryBuilderOutput] = Field(
        default=None,
        description="Consultas construídas prontas para execução",
    )
    documents: list[PatentDocument | PublicationDocument] = Field(
        default_factory=list,
        description="Documentos recuperados",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "metadata": {
                    "search_id": "search_550e8400-e29b-41d4-a716",
                    "run_id": "550e8400-e29b-41d4-a716-446655440000",
                    "status": "completed",
                    "total_documents_found": 1250,
                    "documents_returned": 2,
                },
                "intake": {
                    "theme": "Machine Learning in Healthcare",
                },
                "documents": [],
            }
        }


class ProbeSearchRequest(BaseModel):
    """
    Requisição de busca de prova para testar LLM e queries.

    Permite submeter uma entrada mínima e receber apenas
    a estrutura de consultas sem executar a busca completa.
    """

    intake: InputIntake = Field(
        ...,
        description="Parâmetros de entrada do usuário",
    )
    skip_search: bool = Field(
        default=False,
        description="Se True, apenas retorna estrutura de consultas sem buscar documentos",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "intake": {
                    "theme": "Machine Learning",
                },
                "skip_search": True,
            }
        }


class ProbeSearchResponse(BaseModel):
    """
    Resposta de busca de prova.

    Retorna a estrutura de consultas LLM e queries construídas
    sem executar a busca contra bases de dados.
    """

    run_id: str = Field(
        ...,
        description="Identificador único da requisição",
    )
    intake: InputIntake = Field(
        ...,
        description="Parâmetros de entrada",
    )
    llm_output: LLMOutput = Field(
        ...,
        description="Saída estruturada do modelo LLM",
    )
    query_builder_output: QueryBuilderOutput = Field(
        ...,
        description="Consultas estruturadas prontas para execução",
    )
    active_fields: dict[str, bool] = Field(
        default_factory=dict,
        description="Campos com consultas ativas",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "intake": {
                    "theme": "Machine Learning",
                },
                "llm_output": {
                    "title": {
                        "group_operator": "AND",
                        "groups": [],
                    },
                },
                "query_builder_output": {
                    "textual_clauses": [],
                    "simple_clauses": [],
                    "query_count": 0,
                },
                "active_fields": {},
            }
        }
