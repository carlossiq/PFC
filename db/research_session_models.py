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
    """

    __tablename__ = "session_probe_query"
    __table_args__ = (
        UniqueConstraint("session_id", "fonte", name="uq_session_probe_query_session_fonte"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("research_session.id"), nullable=False, index=True)
    fonte: Mapped[str] = mapped_column(String(20), nullable=False)  # "ops" | "scopus"

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
