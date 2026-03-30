"""
Document and patent record schemas.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """
    Metadados comuns para todos os tipos de documentos.

    Armazena informações de identificação e controle de documentos
    em bases de dados.
    """

    document_id: str = Field(
        ...,
        description="Identificador único do documento",
    )
    source: str = Field(
        ...,
        description="Fonte do documento (USPTO, WIPO, etc.)",
    )
    document_type: str = Field(
        ...,
        description="Tipo de documento (patent, publication, etc.)",
    )
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de recuperação do documento",
    )
    language: str = Field(
        default="en",
        description="Idioma do documento",
    )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de confiança (0-1) da correspondência",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "document_id": "US10123456B2",
                "source": "USPTO",
                "document_type": "patent",
                "retrieved_at": "2024-03-29T10:30:00Z",
                "language": "en",
                "confidence_score": 0.95,
            }
        }


class PatentDocument(DocumentMetadata):
    """
    Esquema para documentos de patente.

    Representa informações estruturadas de um documento de patente
    com todos os campos relevantes.
    """

    title: Optional[str] = Field(
        default=None,
        description="Título da patente",
    )
    abstract: Optional[str] = Field(
        default=None,
        description="Resumo da patente",
    )
    claims: Optional[list[str]] = Field(
        default=None,
        description="Reivindicações da patente",
    )
    description: Optional[str] = Field(
        default=None,
        description="Descrição detalhada da patente",
    )
    full_text: Optional[str] = Field(
        default=None,
        description="Texto completo da patente",
    )
    ipc: Optional[list[str]] = Field(
        default=None,
        description="Classificações IPC",
    )
    cpc: Optional[list[str]] = Field(
        default=None,
        description="Classificações CPC",
    )
    inventors: Optional[list[str]] = Field(
        default=None,
        description="Lista de inventores",
    )
    applicants: Optional[list[str]] = Field(
        default=None,
        description="Lista de requerentes",
    )
    filing_date: Optional[str] = Field(
        default=None,
        description="Data de depósito",
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Data de publicação",
    )
    grant_date: Optional[str] = Field(
        default=None,
        description="Data de concessão",
    )
    priority_date: Optional[str] = Field(
        default=None,
        description="Data de prioridade",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "document_id": "US10123456B2",
                "source": "USPTO",
                "document_type": "patent",
                "retrieved_at": "2024-03-29T10:30:00Z",
                "language": "en",
                "confidence_score": 0.95,
                "title": "Machine Learning System",
                "abstract": "A system and method for...",
                "ipc": ["G06F"],
                "cpc": ["G06F17/18"],
                "inventors": ["John Doe", "Jane Smith"],
                "filing_date": "2020-01-15",
                "publication_date": "2021-06-22",
            }
        }


class PublicationDocument(DocumentMetadata):
    """
    Esquema para documentos de publicação acadêmica.

    Representa metadados estruturados de uma publicação científica
    de periódico ou conferência.
    """

    title: Optional[str] = Field(
        default=None,
        description="Título da publicação",
    )
    abstract: Optional[str] = Field(
        default=None,
        description="Resumo da publicação",
    )
    keywords: Optional[list[str]] = Field(
        default=None,
        description="Palavras-chave da publicação",
    )
    authors: Optional[list[str]] = Field(
        default=None,
        description="Lista de autores",
    )
    author_affiliations: Optional[list[str]] = Field(
        default=None,
        description="Afiliações dos autores",
    )
    publication_year: Optional[int] = Field(
        default=None,
        description="Ano de publicação",
    )
    journal_title: Optional[str] = Field(
        default=None,
        description="Título do periódico ou conferência",
    )
    volume: Optional[str] = Field(
        default=None,
        description="Volume da publicação",
    )
    issue: Optional[str] = Field(
        default=None,
        description="Número/edição da publicação",
    )
    pages: Optional[str] = Field(
        default=None,
        description="Páginas da publicação",
    )
    doi: Optional[str] = Field(
        default=None,
        description="DOI da publicação",
    )
    field_of_study: Optional[list[str]] = Field(
        default=None,
        description="Campos de estudo/áreas de pesquisa",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "document_id": "10.1234/example.doi",
                "source": "SCOPUS",
                "document_type": "publication",
                "retrieved_at": "2024-03-29T10:30:00Z",
                "language": "en",
                "confidence_score": 0.92,
                "title": "Deep Learning Applications",
                "abstract": "This paper discusses...",
                "authors": ["Dr. John Doe", "Dr. Jane Smith"],
                "publication_year": 2023,
                "journal_title": "IEEE Journal",
                "doi": "10.1234/example.doi",
            }
        }


class DocumentBatch(BaseModel):
    """
    Lote de documentos recuperados em uma busca.

    Agrupa múltiplos documentos com metadados de processamento.
    """

    documents: list[PatentDocument | PublicationDocument] = Field(
        default_factory=list,
        description="Documentos no lote",
    )
    total_count: int = Field(
        default=0,
        description="Número total de documentos",
    )
    batch_size: int = Field(
        default=0,
        description="Tamanho do lote atual",
    )
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data/hora de recuperação do lote",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "documents": [],
                "total_count": 0,
                "batch_size": 0,
                "retrieved_at": "2024-03-29T10:30:00Z",
            }
        }
