"""
Database models for storing complete research/prospecting data.

Stores everything from initial user parameters through final reports,
including queries, results, metrics, and generated LaTeX.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

Base = declarative_base()


class Research(Base):
    """
    Pesquisa completa de prospecção tecnológica.

    Armazena todo o histórico de uma pesquisa desde os parâmetros
    iniciais do usuário até o relatório final em LaTeX.
    """

    __tablename__ = "research"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)
    research_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)  # UUID

    # Metadados da pesquisa
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default="ongoing",
        nullable=False,
        index=True,
    )  # ongoing, completed, archived

    # ===== PHASE 1: INITIAL USER INPUT =====
    user_input: Mapped[dict] = mapped_column(JSON, nullable=False)  # theme, description, area_of_study, keywords

    # ===== PHASE 2: REFINED PARAMETERS (POST LLM) =====
    refined_candidates: Mapped[Optional[list[dict]]] = mapped_column(JSON)  # 4 candidates from LLM
    chosen_candidate: Mapped[Optional[dict]] = mapped_column(JSON)  # User selected candidate

    # ===== PHASE 3: PROBE SEARCH =====
    probe_query: Mapped[Optional[dict]] = mapped_column(JSON)  # {"query": "...", "range": "...", "format": "..."}
    probe_api: Mapped[Optional[str]] = mapped_column(String(50))  # ops, scopus, lens_patent, lens_scholarly

    # ===== PHASE 4: TERM EXTRACTION =====
    extracted_terms: Mapped[Optional[list[dict]]] = mapped_column(JSON)  # [{"term": "...", "score": 0.5, ...}]
    extracted_terms_count: Mapped[Optional[int]] = mapped_column(Integer)

    # ===== PHASE 5: FINAL QUERIES =====
    final_query_specific: Mapped[Optional[dict]] = mapped_column(JSON)  # Complete query object
    final_query_balanced: Mapped[Optional[dict]] = mapped_column(JSON)
    final_query_generic: Mapped[Optional[dict]] = mapped_column(JSON)
    chosen_final_query: Mapped[Optional[str]] = mapped_column(String(50))  # specific, balanced, or generic

    # ===== PHASE 6: RESULTS =====
    patent_results_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    scholarly_results_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_results_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)

    # Relationships to results
    patent_documents: Mapped[list["ResearchPatentDocument"]] = relationship(
        "ResearchPatentDocument",
        back_populates="research",
        cascade="all, delete-orphan",
    )
    scholarly_documents: Mapped[list["ResearchScholarlyDocument"]] = relationship(
        "ResearchScholarlyDocument",
        back_populates="research",
        cascade="all, delete-orphan",
    )

    # ===== METRICS & GRAPHS DATA =====
    metrics: Mapped[Optional["ResearchMetrics"]] = relationship(
        "ResearchMetrics",
        back_populates="research",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # ===== GENERATED REPORT =====
    latex_content: Mapped[Optional[str]] = mapped_column(Text)  # Complete LaTeX document
    latex_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    report_url: Mapped[Optional[str]] = mapped_column(String(500))  # URL to generated PDF

    # ===== TIMING DATA =====
    timing: Mapped[dict] = mapped_column(JSON, default={})  # {"phase1": 0.5, "phase2": 1.2, ...}

    # ===== TOKEN USAGE DATA =====
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)  # Total tokens across all LLM calls
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)  # Total cost in USD
    token_usage: Mapped[list["ResearchTokenUsage"]] = relationship(
        "ResearchTokenUsage",
        cascade="all, delete-orphan",
        foreign_keys="ResearchTokenUsage.research_id",
    )

    # ===== METADATA =====
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
        index=True,
    )

    # Indices
    __table_args__ = (
        Index("idx_research_created", "created_at"),
        Index("idx_research_status", "status"),
        Index("idx_research_api", "probe_api"),
    )

    def __repr__(self) -> str:
        return f"<Research(id={self.research_id}, title={self.title[:50]}...)>"


class ResearchPatentDocument(Base):
    """
    Patente vinculada a uma pesquisa.

    Armazena documentos de patente encontrados durante a pesquisa,
    com metadados e scores de relevância.
    """

    __tablename__ = "research_patent_documents"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key
    research_id: Mapped[int] = mapped_column(ForeignKey("research.id"), nullable=False, index=True)
    research: Mapped["Research"] = relationship("Research", back_populates="patent_documents")

    # Identificadores
    publication_number: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # ops, uspto, lens_patent
    source_record_id: Mapped[str] = mapped_column(String(255))

    # Informações básicas
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)

    # Atores
    applicants: Mapped[Optional[list[str]]] = mapped_column(JSON)
    inventors: Mapped[Optional[list[str]]] = mapped_column(JSON)

    # Classificações
    ipc_codes: Mapped[Optional[list[str]]] = mapped_column(JSON)
    cpc_codes: Mapped[Optional[list[str]]] = mapped_column(JSON)

    # Datas
    filing_date: Mapped[Optional[str]] = mapped_column(String(10))  # YYYY-MM-DD
    publication_date: Mapped[Optional[str]] = mapped_column(String(10))
    grant_date: Mapped[Optional[str]] = mapped_column(String(10))
    year: Mapped[Optional[int]] = mapped_column(Integer, index=True)

    # Status
    legal_status: Mapped[Optional[str]] = mapped_column(String(255))

    # Relevância
    relevance_score: Mapped[Optional[float]] = mapped_column(Float)  # From search ranking
    query_variant: Mapped[Optional[str]] = mapped_column(String(50))  # specific, balanced, generic

    # Raw data
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_research_patent_doc", "research_id", "publication_number"),
        Index("idx_research_patent_year", "research_id", "year"),
    )

    def __repr__(self) -> str:
        return f"<ResearchPatentDocument(pub_num={self.publication_number})>"


class ResearchScholarlyDocument(Base):
    """
    Artigo/publicação acadêmica vinculada a uma pesquisa.

    Armazena documentos de artigos encontrados durante a pesquisa.
    """

    __tablename__ = "research_scholarly_documents"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key
    research_id: Mapped[int] = mapped_column(ForeignKey("research.id"), nullable=False, index=True)
    research: Mapped["Research"] = relationship("Research", back_populates="scholarly_documents")

    # Identificadores
    doi: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # scopus, lens_scholarly
    source_record_id: Mapped[str] = mapped_column(String(255))

    # Informações básicas
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)

    # Autores e afiliações
    authors: Mapped[Optional[list[str]]] = mapped_column(JSON)
    affiliations: Mapped[Optional[list[str]]] = mapped_column(JSON)

    # Publicação
    journal_or_source: Mapped[Optional[str]] = mapped_column(String(500))
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
    query_variant: Mapped[Optional[str]] = mapped_column(String(50))  # specific, balanced, generic

    # Raw data
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_research_scholarly_doc", "research_id", "doi"),
        Index("idx_research_scholarly_year", "research_id", "year"),
    )

    def __repr__(self) -> str:
        return f"<ResearchScholarlyDocument(doi={self.doi})>"


class ResearchMetrics(Base):
    """
    Métricas e dados agregados para gráficos de uma pesquisa.

    Armazena informações consolidadas para geração de gráficos
    no relatório de prospecção tecnológica.
    """

    __tablename__ = "research_metrics"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key
    research_id: Mapped[int] = mapped_column(ForeignKey("research.id"), nullable=False, unique=True)
    research: Mapped["Research"] = relationship("Research", back_populates="metrics")

    # ===== PATENTS METRICS =====
    patent_by_year: Mapped[Optional[dict]] = mapped_column(JSON)  # {"2020": 10, "2021": 15, ...}
    patent_by_applicant: Mapped[Optional[dict]] = mapped_column(JSON)  # {"Samsung": 5, "Apple": 3, ...}
    patent_by_ipc: Mapped[Optional[dict]] = mapped_column(JSON)  # {"H04L": 10, "G06F": 8, ...}
    patent_by_legal_status: Mapped[Optional[dict]] = mapped_column(JSON)  # {"granted": 20, "pending": 5, ...}
    patent_by_query_variant: Mapped[Optional[dict]] = mapped_column(JSON)  # {"specific": 5, "balanced": 10, ...}

    # ===== ARTICLES METRICS =====
    article_by_year: Mapped[Optional[dict]] = mapped_column(JSON)
    article_by_journal: Mapped[Optional[dict]] = mapped_column(JSON)  # {"Nature": 2, "Science": 1, ...}
    article_by_field: Mapped[Optional[dict]] = mapped_column(JSON)  # {"AI": 10, "ML": 8, ...}
    article_by_citations: Mapped[Optional[dict]] = mapped_column(JSON)  # Citation ranges: {"0-10": 5, "11-50": 10, ...}
    article_by_query_variant: Mapped[Optional[dict]] = mapped_column(JSON)

    # ===== TOP ENTITIES =====
    top_patent_applicants: Mapped[Optional[list[dict]]] = mapped_column(JSON)  # [{"name": "...", "count": 5, "patents": [...]}]
    top_patent_inventors: Mapped[Optional[list[dict]]] = mapped_column(JSON)
    top_article_authors: Mapped[Optional[list[dict]]] = mapped_column(JSON)  # [{"name": "...", "count": 3, "articles": [...]}]
    top_article_journals: Mapped[Optional[list[dict]]] = mapped_column(JSON)

    # ===== TRENDS =====
    patent_growth_trend: Mapped[Optional[dict]] = mapped_column(JSON)  # Growth rate by year
    article_growth_trend: Mapped[Optional[dict]] = mapped_column(JSON)

    # ===== COMPARISON =====
    query_variant_comparison: Mapped[Optional[dict]] = mapped_column(JSON)  # Compare results from 3 variants
    patent_vs_article_ratio: Mapped[Optional[dict]] = mapped_column(JSON)  # {"patents": 30, "articles": 20}

    # Metadata
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ResearchMetrics(research_id={self.research_id})>"


class ResearchPhase(Base):
    """
    Rastreamento de tempo para cada fase da pesquisa.

    Armazena informações de timing para análise de performance.
    """

    __tablename__ = "research_phases"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key
    research_id: Mapped[int] = mapped_column(ForeignKey("research.id"), nullable=False, index=True)

    # Phase info
    phase_name: Mapped[str] = mapped_column(String(100), nullable=False)  # refine, probe, extract, final, search
    description: Mapped[Optional[str]] = mapped_column(String(500))

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="completed")  # completed, failed, skipped

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    # Additional data
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)

    __table_args__ = (
        Index("idx_research_phase", "research_id", "phase_name"),
    )

    def __repr__(self) -> str:
        return f"<ResearchPhase(research_id={self.research_id}, phase={self.phase_name})>"


class ResearchTokenUsage(Base):
    """
    Rastreamento de tokens para cada chamada LLM.

    Armazena input/output tokens para análise de custo e otimização.
    Permite rastrear múltiplas chamadas da mesma fase (ex: refinar tema 3x).
    """

    __tablename__ = "research_token_usage"

    # Chave primária
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key
    research_id: Mapped[int] = mapped_column(ForeignKey("research.id"), nullable=False, index=True)

    # Call info
    phase_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    llm_call_type: Mapped[str] = mapped_column(String(100), nullable=False)
    # Exemplos: "generate_candidate_topics", "probe_search", "extract_terms", "generate_final_queries"
    call_number: Mapped[int] = mapped_column(Integer, default=1)  # 1st, 2nd, 3rd call to same phase

    # Model info
    model: Mapped[str] = mapped_column(String(50), nullable=False)  # gemini, gpt-4, claude, etc
    model_variant: Mapped[Optional[str]] = mapped_column(String(100))  # gemini-1.5-pro, gpt-4-turbo, etc

    # Token counts
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)

    # Cost info (USD)
    input_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    output_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)

    # API response metadata
    api_latency_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Response time in milliseconds
    status: Mapped[str] = mapped_column(String(50), default="success")  # success, failed, timeout

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Additional data
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)  # Any extra info (prompt size, etc)

    __table_args__ = (
        Index("idx_research_token_phase", "research_id", "phase_name"),
        Index("idx_research_token_type", "research_id", "llm_call_type"),
        Index("idx_research_token_created", "research_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ResearchTokenUsage(research_id={self.research_id}, phase={self.phase_name}, tokens={self.total_tokens})>"
