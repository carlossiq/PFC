"""
Database-related schemas for storage and retrieval.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchRecord(BaseModel):
    """
    Registro de uma busca armazenado em banco de dados.

    Permite rastreamento persistente de todas as buscas realizadas
    para análise, auditoria e histórico de usuários.
    """

    id: Optional[str] = Field(
        default=None,
        description="ID primária do registro",
    )
    search_id: str = Field(
        ...,
        description="Identificador único da busca",
    )
    run_id: str = Field(
        ...,
        description="Identificador único da requisição HTTP",
    )
    theme: str = Field(
        ...,
        description="Tema da busca",
    )
    objective: Optional[str] = Field(
        default=None,
        description="Objetivo da busca",
    )
    initial_keywords: Optional[list[str]] = Field(
        default=None,
        description="Palavras-chave iniciais",
    )
    llm_output_json: Optional[str] = Field(
        default=None,
        description="Saída do LLM serializada em JSON",
    )
    query_count: int = Field(
        default=0,
        description="Número de consultas geradas",
    )
    documents_found: int = Field(
        default=0,
        description="Total de documentos encontrados",
    )
    documents_stored: int = Field(
        default=0,
        description="Número de documentos armazenados",
    )
    status: str = Field(
        default="completed",
        description="Status final da busca",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Mensagem de erro se status=failed",
    )
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de início",
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="Data/hora de conclusão",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Duração da busca em segundos",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "search_id": "search_550e8400-e29b-41d4-a716",
                "run_id": "550e8400-e29b-41d4-a716-446655440000",
                "theme": "Machine Learning in Healthcare",
                "objective": "Diagnostic AI systems",
                "query_count": 5,
                "documents_found": 1250,
                "documents_stored": 100,
                "status": "completed",
                "duration_seconds": 315.5,
            }
        }


class DocumentRecord(BaseModel):
    """
    Registro de um documento armazenado em banco de dados.

    Mapeia dados estruturados de documentos para persistência
    com referência cruzada para buscas que os encontraram.
    """

    id: Optional[str] = Field(
        default=None,
        description="ID primária do registro",
    )
    document_id: str = Field(
        ...,
        description="Identificador único do documento",
    )
    search_id: str = Field(
        ...,
        description="Identificador da busca que encontrou o documento",
    )
    source: str = Field(
        ...,
        description="Fonte do documento",
    )
    document_type: str = Field(
        ...,
        description="Tipo de documento",
    )
    title: Optional[str] = Field(
        default=None,
        description="Título do documento",
    )
    metadata_json: Optional[str] = Field(
        default=None,
        description="Metadados completos serializados em JSON",
    )
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de relevância (0-1)",
    )
    indexed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de armazenamento",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "document_id": "US10123456B2",
                "search_id": "search_550e8400-e29b-41d4-a716",
                "source": "USPTO",
                "document_type": "patent",
                "title": "Machine Learning System",
                "relevance_score": 0.95,
                "indexed_at": "2024-03-29T10:35:00Z",
            }
        }


class QueryExecutionLog(BaseModel):
    """
    Log de execução de uma consulta contra base de dados.

    Rastreia performance e comportamento de cada consulta executada
    para otimização e debugging.
    """

    id: Optional[str] = Field(
        default=None,
        description="ID primária do registro",
    )
    search_id: str = Field(
        ...,
        description="Identificador da busca",
    )
    query_index: int = Field(
        ...,
        description="Índice da consulta dentro da busca",
    )
    field_name: str = Field(
        ...,
        description="Campo consultado",
    )
    query_type: str = Field(
        ...,
        description="Tipo de consulta (textual ou simple)",
    )
    query_string: Optional[str] = Field(
        default=None,
        description="String de consulta executada",
    )
    results_count: int = Field(
        default=0,
        description="Número de resultados",
    )
    execution_time_ms: Optional[float] = Field(
        default=None,
        ge=0,
        description="Tempo de execução em milissegundos",
    )
    status: str = Field(
        default="success",
        description="Status da execução",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Mensagem de erro se status=failed",
    )
    executed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de execução",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "search_id": "search_550e8400-e29b-41d4-a716",
                "query_index": 0,
                "field_name": "TITLE",
                "query_type": "textual",
                "results_count": 250,
                "execution_time_ms": 125.5,
                "status": "success",
            }
        }
