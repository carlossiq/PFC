"""
Schemas for searching/listing research sessions and their session_input rows.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, field_validator

from schemas.session_input import SessionAiCallRow, SessionInputRow, SessionProbeQueryRow


class SessionReportSummary(BaseModel):
    """Estado do relatório REPTEC/AGITEC dessa sessão (ver SessionReport) -
    None em ResearchSessionSummary.report significa "nunca chamou /assemble
    ainda", não erro. Montado manualmente pelo router (não por
    model_validate direto), já que `has_pdf` não é um atributo do ORM."""

    status: str
    has_pdf: bool
    updated_at: datetime


class ResearchSessionSummary(BaseModel):
    """Sessão de pesquisa + todas as suas linhas de session_input (raiz e gerada),
    session_probe_query (query de patente/artigo escolhida no Step3) e
    session_ai_call (log de chamadas de IA feitas durante o wizard)."""

    id: int
    public_id: str
    name: Optional[str] = None
    completed: bool
    created_at: datetime
    completed_at: Optional[datetime] = None
    inputs: list[SessionInputRow]
    probe_queries: list[SessionProbeQueryRow] = []
    ai_calls: list[SessionAiCallRow] = []
    report: Optional[SessionReportSummary] = None

    class Config:
        from_attributes = True

    @field_validator("report", mode="before")
    @classmethod
    def _adapt_report(cls, value: Any) -> Any:
        """`ResearchSession.report` (SQLAlchemy relationship, ver
        db/research_session_models.py) não tem `has_pdf` como atributo -
        pydantic's from_attributes falharia tentando ler direto do ORM.
        None (sessão sem relatório ainda) passa direto."""
        if value is None or isinstance(value, (dict, SessionReportSummary)):
            return value
        return {
            "status": value.status,
            "has_pdf": value.pdf_object_key is not None,
            "updated_at": value.updated_at,
        }
