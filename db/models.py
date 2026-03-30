"""
Database models for scholarly documents, patents, and deduplication registries.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

Base = declarative_base()


class ScholarlyDocument(Base):
    """
    Modelo de publicação acadêmica no banco de dados.

    Armazena publicações científicas normalizadas com
    rastreamento de fonte e relevância.
    """

    __tablename__ = "scholarly_documents"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificadores
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)

    # Informações básicas
    title: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text)

    # Identificador único
    doi: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)

    # Autores e afiliações
    authors: Mapped[Optional[list[str]]] = mapped_column(JSON)  # Lista de nomes
    affiliations: Mapped[Optional[list[str]]] = mapped_column(JSON)  # Lista de afiliações

    # Publicação
    journal_or_source: Mapped[Optional[str]] = mapped_column(String(500), index=True)
    volume: Mapped[Optional[str]] = mapped_column(String(50))
    issue: Mapped[Optional[str]] = mapped_column(String(50))
    pages: Mapped[Optional[str]] = mapped_column(String(50))

    # Datas
    publication_date: Mapped[Optional[str]] = mapped_column(String(10))  # YYYY-MM-DD
    year: Mapped[Optional[int]] = mapped_column(Integer, index=True)

    # Conteúdo
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSON)
    field_of_study: Mapped[Optional[list[str]]] = mapped_column(JSON)

    # Métricas
    citations: Mapped[Optional[int]] = mapped_column(Integer)

    # Relevância
    relevance_score: Mapped[Optional[float]] = mapped_column(Float)

    # Metadados de processamento
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Raw payload (debug)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)

    # Índices compostos
    __table_args__ = (
        Index("idx_scholarly_source_record", "source", "source_record_id"),
        Index("idx_scholarly_year_relevance", "year", "relevance_score"),
        Index("idx_scholarly_source_year", "source", "year"),
    )

    def __repr__(self) -> str:
        """Representação em string."""
        return f"<ScholarlyDocument(id={self.id}, title={self.title[:50]}...)>"


class PatentDocument(Base):
    """
    Modelo de patente no banco de dados.

    Armazena patentes normalizadas com rastreamento
    de fonte, classificações e status legal.
    """

    __tablename__ = "patent_documents"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Identificadores
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_record_id: Mapped[str] = mapped_column(String(255), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)

    # Informações básicas
    title: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text)

    # Números de patente
    publication_number: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    application_number: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    family_id: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Atores
    applicants: Mapped[Optional[list[str]]] = mapped_column(JSON)  # Lista de requerentes
    inventors: Mapped[Optional[list[str]]] = mapped_column(JSON)  # Lista de inventores

    # Classificações
    ipc_codes: Mapped[Optional[list[str]]] = mapped_column(JSON)  # IPC classification
    cpc_codes: Mapped[Optional[list[str]]] = mapped_column(JSON)  # CPC classification

    # Datas
    filing_date: Mapped[Optional[str]] = mapped_column(String(10))  # YYYY-MM-DD
    publication_date: Mapped[Optional[str]] = mapped_column(String(10))  # YYYY-MM-DD
    grant_date: Mapped[Optional[str]] = mapped_column(String(10))  # YYYY-MM-DD
    year: Mapped[Optional[int]] = mapped_column(Integer, index=True)

    # Status
    legal_status: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    # Relevância
    relevance_score: Mapped[Optional[float]] = mapped_column(Float)

    # Metadados de processamento
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Raw payload (debug)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)

    # Índices compostos
    __table_args__ = (
        Index("idx_patent_source_record", "source", "source_record_id"),
        Index("idx_patent_year_relevance", "year", "relevance_score"),
        Index("idx_patent_source_year", "source", "year"),
        Index("idx_patent_applicants_year", "applicants", "year"),
    )

    def __repr__(self) -> str:
        """Representação em string."""
        return f"<PatentDocument(id={self.id}, publication_number={self.publication_number})>"


class ScholarlyDedupRegistry(Base):
    """
    Registro de deduplicação para publicações acadêmicas.

    Rastreia dedup_keys e fontes para identificar duplicatas
    de maneira eficiente sem consultar documento completo.
    """

    __tablename__ = "scholarly_dedup_registry"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Dedup
    dedup_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Rastreamento
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_record_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )  # Múltiplas fontes podem ter o mesmo doc

    # Metadados
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Índices
    __table_args__ = (
        Index("idx_scholarly_dedup_source", "source", "dedup_key"),
    )

    def __repr__(self) -> str:
        """Representação em string."""
        return f"<ScholarlyDedupRegistry(id={self.id}, dedup_key={self.dedup_key})>"


class PatentDedupRegistry(Base):
    """
    Registro de deduplicação para patentes.

    Rastreia dedup_keys e fontes para identificar duplicatas
    de maneira eficiente sem consultar documento completo.
    """

    __tablename__ = "patent_dedup_registry"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Dedup
    dedup_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Rastreamento
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_record_ids: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )  # Múltiplas fontes podem ter o mesmo doc

    # Metadados
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )

    # Índices
    __table_args__ = (
        Index("idx_patent_dedup_source", "source", "dedup_key"),
    )

    def __repr__(self) -> str:
        """Representação em string."""
        return f"<PatentDedupRegistry(id={self.id}, dedup_key={self.dedup_key})>"
