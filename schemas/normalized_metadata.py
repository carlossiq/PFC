"""
Normalized metadata schemas for standardized document representation.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class StandardizedPatentMetadata(BaseModel):
    """
    Estrutura padronizada de metadados de patente.

    Absorve diferenças entre múltiplas APIs de patentes,
    apresentando interface unificada.
    """

    # Identificadores
    source: str = Field(
        ...,
        description="Fonte do documento (lens_patent, ops, wipo, etc.)",
    )
    source_record_id: str = Field(
        ...,
        description="ID do registro na fonte original",
    )
    dedup_key: str = Field(
        ...,
        description="Chave para deduplicação",
    )

    # Informações básicas
    title: str = Field(
        ...,
        description="Título da patente",
    )
    abstract: Optional[str] = Field(
        default=None,
        description="Resumo/abstract da patente",
    )

    # Identificadores únicos
    publication_number: str = Field(
        ...,
        description="Número de publicação",
    )
    application_number: Optional[str] = Field(
        default=None,
        description="Número de depósito/application",
    )
    family_id: Optional[str] = Field(
        default=None,
        description="ID da família de patentes",
    )

    # Atores
    applicants: list[str] = Field(
        default_factory=list,
        description="Lista de requerentes",
    )
    inventors: list[str] = Field(
        default_factory=list,
        description="Lista de inventores",
    )

    # Classificações
    ipc_codes: list[str] = Field(
        default_factory=list,
        description="Códigos IPC (International Patent Classification)",
    )
    cpc_codes: list[str] = Field(
        default_factory=list,
        description="Códigos CPC (Cooperative Patent Classification)",
    )

    # Datas
    filing_date: Optional[str] = Field(
        default=None,
        description="Data de depósito (YYYY-MM-DD)",
    )
    publication_date: Optional[str] = Field(
        default=None,
        description="Data de publicação (YYYY-MM-DD)",
    )
    grant_date: Optional[str] = Field(
        default=None,
        description="Data de concessão (YYYY-MM-DD)",
    )
    year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Ano da publicação",
    )

    # Status e metadados legais
    legal_status: Optional[str] = Field(
        default=None,
        description="Status legal (active, expired, abandoned, etc.)",
    )

    # Relevância
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de relevância (0-1)",
    )

    # Raw data
    raw_payload: Optional[dict[str, Any]] = Field(
        default=None,
        description="Payload original da API (para debug)",
    )

    # Metadados de processamento
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data de normalização",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "source": "lens_patent",
                "source_record_id": "US10123456B2",
                "dedup_key": "US10123456B2",
                "title": "Machine Learning System for Medical Diagnosis",
                "abstract": "A system and method for automated medical diagnosis using convolutional neural networks applied to radiological images...",
                "publication_number": "US10123456B2",
                "application_number": "US16123456",
                "family_id": "FAM-98765",
                "applicants": ["MedTech Corp", "University of Example"],
                "inventors": ["John Doe", "Jane Smith"],
                "ipc_codes": ["G06N3/08", "G16H50/20", "G06T7/00"],
                "cpc_codes": ["G06N3/084", "G16H50/20"],
                "filing_date": "2020-01-15",
                "publication_date": "2021-06-22",
                "grant_date": "2022-03-08",
                "year": 2021,
                "legal_status": "active",
                "relevance_score": 0.92,
            }
        }


class StandardizedScholarlyMetadata(BaseModel):
    """
    Estrutura padronizada de metadados de publicação acadêmica.

    Absorve diferenças entre múltiplas APIs de publicações,
    apresentando interface unificada.
    """

    # Identificadores
    source: str = Field(
        ...,
        description="Fonte do documento (scopus, lens_scholarly, etc.)",
    )
    source_record_id: str = Field(
        ...,
        description="ID do registro na fonte original",
    )
    dedup_key: str = Field(
        ...,
        description="Chave para deduplicação",
    )

    # Informações básicas
    title: str = Field(
        ...,
        description="Título da publicação",
    )
    abstract: Optional[str] = Field(
        default=None,
        description="Resumo/abstract",
    )

    # Identificadores únicos
    doi: Optional[str] = Field(
        default=None,
        description="Digital Object Identifier",
    )

    # Autores
    authors: list[str] = Field(
        default_factory=list,
        description="Lista de autores",
    )
    affiliations: list[str] = Field(
        default_factory=list,
        description="Afiliações dos autores",
    )

    # Publicação
    journal_or_source: Optional[str] = Field(
        default=None,
        description="Nome do periódico ou conferência",
    )
    volume: Optional[str] = Field(
        default=None,
        description="Volume",
    )
    issue: Optional[str] = Field(
        default=None,
        description="Edição/issue",
    )
    pages: Optional[str] = Field(
        default=None,
        description="Páginas",
    )

    # Datas
    publication_date: Optional[str] = Field(
        default=None,
        description="Data de publicação (YYYY-MM-DD)",
    )
    year: Optional[int] = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Ano de publicação",
    )

    # Conteúdo
    keywords: list[str] = Field(
        default_factory=list,
        description="Palavras-chave",
    )
    field_of_study: list[str] = Field(
        default_factory=list,
        description="Campos de estudo/áreas de pesquisa",
    )

    # Métricas
    citations: Optional[int] = Field(
        default=None,
        ge=0,
        description="Número de citações",
    )

    # Relevância
    relevance_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Score de relevância (0-1)",
    )

    # Raw data
    raw_payload: Optional[dict[str, Any]] = Field(
        default=None,
        description="Payload original da API (para debug)",
    )

    # Metadados de processamento
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Data de normalização",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "source": "scopus",
                "source_record_id": "2-s2.0-85123456789",
                "dedup_key": "10.1234/example",
                "title": "Deep Learning Applications in Healthcare",
                "abstract": "This paper discusses...",
                "doi": "10.1234/example",
                "authors": ["Dr. John Doe", "Dr. Jane Smith"],
                "affiliations": ["University of Example"],
                "journal_or_source": "IEEE Transactions",
                "publication_date": "2023-06-15",
                "year": 2023,
                "keywords": ["deep learning", "healthcare"],
                "field_of_study": ["Computer Science", "Medicine"],
                "citations": 42,
            }
        }
