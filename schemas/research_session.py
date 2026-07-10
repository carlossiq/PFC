"""
Schemas for searching/listing research sessions and their session_input rows.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from schemas.session_input import SessionInputRow


class ResearchSessionSummary(BaseModel):
    """Sessão de pesquisa + todas as suas linhas de session_input (raiz e gerada)."""

    id: int
    public_id: str
    name: Optional[str] = None
    status: str
    created_at: datetime
    inputs: list[SessionInputRow]

    class Config:
        from_attributes = True
