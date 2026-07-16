"""
Database models for the session-centric prospecting workflow.

research_session is the hub object for a prospecting run; session_input
captures the parameters used to configure it (the user's raw input, plus
any AI-refined variant chosen to move forward).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.config import settings

Base = declarative_base()


class ResearchSession(Base):
    """Objeto central de uma prospecção: guarda status e fontes escolhidas."""

    __tablename__ = "research_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[Optional[str]] = mapped_column(String(255))
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    patent_source: Mapped[Optional[str]] = mapped_column(String(50))
    scholarly_source: Mapped[Optional[str]] = mapped_column(String(50))
    relevance_threshold: Mapped[float] = mapped_column(
        Float, nullable=False, default=lambda: settings.relevance_threshold
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    inputs: Mapped[list["SessionInput"]] = relationship(
        "SessionInput",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    probe_queries: Mapped[list["SessionProbeQuery"]] = relationship(
        "SessionProbeQuery",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    ai_calls: Mapped[list["SessionAiCall"]] = relationship(
        "SessionAiCall",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class SessionInput(Base):
    """
    Parâmetros de uma sessão (era param_init). Auto-relacionada: a linha raiz
    (parent_id=None) é o input original do usuário; uma linha filha, se houver,
    é a variante gerada/refinada por IA escolhida para seguir adiante.
    """

    __tablename__ = "session_input"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("research_session.id"), nullable=False, index=True)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("session_input.id"), nullable=True)

    theme: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    area_of_study: Mapped[Optional[str]] = mapped_column(String(500))
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSON)
    year_from: Mapped[Optional[int]] = mapped_column()
    year_to: Mapped[Optional[int]] = mapped_column()
    iterations: Mapped[int] = mapped_column(nullable=False, default=0)

    session: Mapped["ResearchSession"] = relationship("ResearchSession", back_populates="inputs")
    parent: Mapped[Optional["SessionInput"]] = relationship("SessionInput", remote_side=[id])


class SessionProbeQuery(Base):
    """
    Query de exploração inicial (Step3) escolhida pelo usuário, uma por fonte
    (ops para patentes, scopus para artigos). Guarda a query final montada
    pela IA (ou reconstruída manualmente pelo usuário), os campos estruturados
    que a compõem, e quantas iterações de IA foram necessárias até chegar
    nela - reiniciadas sempre que o input de origem muda.

    Auto-relacionada como SessionInput: a linha de probe (tipo=None) é a
    query da Exploração Inicial; a query final escolhida (Escolha da Query
    Final) vira uma segunda linha, com parent_id apontando pra linha de
    probe da mesma fonte e tipo = "specific"|"balanced"|"generic" (a
    variante escolhida). `iterations` da linha de probe soma regeneração da
    própria query probe + reextração de termos (Amostragem de Termos é um
    substep da Exploração Inicial, sempre roda antes da query final
    existir); `iterations` da linha final é só a regeneração daquela
    variante - ver TermSampling.tsx/FinalExploration.tsx.
    """

    __tablename__ = "session_probe_query"
    __table_args__ = (
        UniqueConstraint("session_id", "fonte", "tipo", name="uq_session_probe_query_session_fonte_tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("research_session.id"), nullable=False, index=True)
    fonte: Mapped[str] = mapped_column(String(20), nullable=False)  # "ops" | "scopus"
    tipo: Mapped[Optional[str]] = mapped_column(String(20))  # None=probe | "specific"|"balanced"|"generic"
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("session_probe_query.id"), nullable=True)

    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[Optional[dict]] = mapped_column(JSON)
    year_from: Mapped[Optional[int]] = mapped_column()
    year_to: Mapped[Optional[int]] = mapped_column()
    complexity_score: Mapped[Optional[float]] = mapped_column()
    complexity_level: Mapped[Optional[str]] = mapped_column(String(50))
    result_count: Mapped[Optional[int]] = mapped_column()
    iterations: Mapped[int] = mapped_column(nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session: Mapped["ResearchSession"] = relationship("ResearchSession", back_populates="probe_queries")
    parent: Mapped[Optional["SessionProbeQuery"]] = relationship("SessionProbeQuery", remote_side=[id])
    patent_links: Mapped[list["ProbeQueryPatent"]] = relationship(
        "ProbeQueryPatent",
        back_populates="probe_query",
        cascade="all, delete-orphan",
    )
    article_links: Mapped[list["ProbeQueryArticle"]] = relationship(
        "ProbeQueryArticle",
        back_populates="probe_query",
        cascade="all, delete-orphan",
    )


class SessionAiCall(Base):
    """
    Log append-only de uma chamada de IA feita durante o wizard (refino de
    tema, especificação, geração de query probe/final, inclusive tentativas
    de "gerar outras" - nunca upsertado, sempre uma linha nova por chamada,
    pra manter o total de tokens/tempo gasto na sessão completo mesmo
    contando tentativas descartadas). Como as chamadas de IA acontecem antes
    da sessão existir (ver session_persistence.py), essas linhas só são
    inseridas quando o frontend reenvia o histórico acumulado junto de um
    save de progresso/finalização.
    """

    __tablename__ = "session_ai_call"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("research_session.id"), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False)
    input_tokens: Mapped[Optional[int]] = mapped_column()
    output_tokens: Mapped[Optional[int]] = mapped_column()
    total_tokens: Mapped[Optional[int]] = mapped_column()
    attempts: Mapped[int] = mapped_column(nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    session: Mapped["ResearchSession"] = relationship("ResearchSession", back_populates="ai_calls")


class Patent(Base):
    """
    Patente encontrada por uma ou mais probe queries (Resultados Iniciais).
    dedup_key identifica o documento em si (independe de qual query o achou),
    então a mesma patente encontrada por duas queries gera uma única linha
    aqui e duas linhas em probe_query_patent.
    """

    __tablename__ = "patent"

    id: Mapped[int] = mapped_column(primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_record_id: Mapped[Optional[str]] = mapped_column(String(255))

    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    publication_number: Mapped[Optional[str]] = mapped_column(String(100))
    application_number: Mapped[Optional[str]] = mapped_column(String(100))
    family_id: Mapped[Optional[str]] = mapped_column(String(100))
    applicants: Mapped[Optional[list[str]]] = mapped_column(JSON)
    inventors: Mapped[Optional[list[str]]] = mapped_column(JSON)
    ipc_codes: Mapped[Optional[list[str]]] = mapped_column(JSON)
    cpc_codes: Mapped[Optional[list[str]]] = mapped_column(JSON)
    filing_date: Mapped[Optional[str]] = mapped_column(String(10))
    publication_date: Mapped[Optional[str]] = mapped_column(String(10))
    grant_date: Mapped[Optional[str]] = mapped_column(String(10))
    year: Mapped[Optional[int]] = mapped_column()
    legal_status: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(10))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    query_links: Mapped[list["ProbeQueryPatent"]] = relationship(
        "ProbeQueryPatent",
        back_populates="patent",
        cascade="all, delete-orphan",
    )


class Article(Base):
    """Artigo encontrado por uma ou mais probe queries (Resultados Iniciais). Ver Patent para a lógica de dedup_key."""

    __tablename__ = "article"

    id: Mapped[int] = mapped_column(primary_key=True)
    dedup_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    source_record_id: Mapped[Optional[str]] = mapped_column(String(255))

    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text)
    doi: Mapped[Optional[str]] = mapped_column(String(255))
    authors: Mapped[Optional[list[str]]] = mapped_column(JSON)
    affiliations: Mapped[Optional[list[str]]] = mapped_column(JSON)
    affiliation_countries: Mapped[Optional[list[str]]] = mapped_column(JSON)
    journal_or_source: Mapped[Optional[str]] = mapped_column(String(500))
    volume: Mapped[Optional[str]] = mapped_column(String(50))
    issue: Mapped[Optional[str]] = mapped_column(String(50))
    pages: Mapped[Optional[str]] = mapped_column(String(50))
    publication_date: Mapped[Optional[str]] = mapped_column(String(10))
    year: Mapped[Optional[int]] = mapped_column()
    keywords: Mapped[Optional[list[str]]] = mapped_column(JSON)
    field_of_study: Mapped[Optional[list[str]]] = mapped_column(JSON)
    citations: Mapped[Optional[int]] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    query_links: Mapped[list["ProbeQueryArticle"]] = relationship(
        "ProbeQueryArticle",
        back_populates="article",
        cascade="all, delete-orphan",
    )


class ProbeQueryPatent(Base):
    """Associação N:N entre session_probe_query e patent, com o score de relevância daquele par especificamente."""

    __tablename__ = "probe_query_patent"
    __table_args__ = (
        UniqueConstraint("probe_query_id", "patent_id", name="uq_probe_query_patent_probe_query_id_patent_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    probe_query_id: Mapped[int] = mapped_column(ForeignKey("session_probe_query.id"), nullable=False, index=True)
    patent_id: Mapped[int] = mapped_column(ForeignKey("patent.id"), nullable=False, index=True)
    relevance_score: Mapped[Optional[float]] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    probe_query: Mapped["SessionProbeQuery"] = relationship("SessionProbeQuery", back_populates="patent_links")
    patent: Mapped["Patent"] = relationship("Patent", back_populates="query_links")


class ProbeQueryArticle(Base):
    """Associação N:N entre session_probe_query e article, com o score de relevância daquele par especificamente."""

    __tablename__ = "probe_query_article"
    __table_args__ = (
        UniqueConstraint("probe_query_id", "article_id", name="uq_probe_query_article_probe_query_id_article_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    probe_query_id: Mapped[int] = mapped_column(ForeignKey("session_probe_query.id"), nullable=False, index=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("article.id"), nullable=False, index=True)
    relevance_score: Mapped[Optional[float]] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    probe_query: Mapped["SessionProbeQuery"] = relationship("SessionProbeQuery", back_populates="article_links")
    article: Mapped["Article"] = relationship("Article", back_populates="query_links")
