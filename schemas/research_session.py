"""
Schemas for searching/listing research sessions and their session_input rows.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from schemas.session_input import SessionAiCallRow, SessionInputRow, SessionProbeQueryRow


class ResearchSessionSummary(BaseModel):
    """Sessão de pesquisa + todas as suas linhas de session_input (raiz e gerada),
    session_probe_query (query de patente/artigo escolhida no Step3) e
    session_ai_call (log de chamadas de IA feitas durante o wizard)."""

    id: int
    public_id: str
    name: Optional[str] = None
    completed: bool
    created_at: datetime
    inputs: list[SessionInputRow]
    probe_queries: list[SessionProbeQueryRow] = []
    ai_calls: list[SessionAiCallRow] = []

    class Config:
        from_attributes = True
