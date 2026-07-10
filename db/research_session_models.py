"""
Database models for the session-centric prospecting workflow.

research_session is the hub object for a prospecting run; session_input
captures the parameters used to configure it (the user's raw input, plus
any AI-refined variant chosen to move forward).
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
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
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="input")
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
