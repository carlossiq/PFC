"""
Schemas for finalizing a prospecting session's input parameters.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SessionInputRoot(BaseModel):
    """Input original do usuário (Step1), raiz da cadeia de session_input."""

    theme: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Tema principal da prospecção tecnológica (obrigatório)",
    )
    description: Optional[str] = Field(default=None, max_length=2000)
    area_of_study: Optional[str] = Field(default=None, max_length=500)
    keywords: Optional[list[str]] = Field(default=None, max_items=50)
    year_from: Optional[int] = Field(default=None)
    year_to: Optional[int] = Field(default=None)

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        return value.strip()

    @field_validator("description", "area_of_study", mode="before")
    @classmethod
    def validate_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            stripped = value.strip()
            return stripped if stripped else None
        return None

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        if value is None:
            return None
        normalized = [kw.strip() for kw in value if isinstance(kw, str) and kw.strip()]
        return list(set(normalized)) if normalized else None


class SessionInputGenerated(BaseModel):
    """Variante gerada/refinada por IA escolhida para seguir adiante."""

    theme: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)
    iterations: int = Field(default=0, ge=0)


class SessionInputFinalizeRequest(BaseModel):
    """Payload enviado ao finalizar a sessão: nome + input raiz + gerado (opcional)."""

    name: str = Field(..., min_length=1, max_length=255)
    root: SessionInputRoot
    generated: Optional[SessionInputGenerated] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return value.strip()


class SessionInputRow(BaseModel):
    """Representação persistida de uma linha session_input."""

    id: int
    session_id: int
    parent_id: Optional[int] = None
    theme: str
    description: Optional[str] = None
    area_of_study: Optional[str] = None
    keywords: Optional[list[str]] = None
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    iterations: int

    class Config:
        from_attributes = True


class SessionInputFinalizeResponse(BaseModel):
    """Resultado da finalização: sessão criada + linhas de input criadas."""

    session_id: int
    session_public_id: str
    session_name: str
    root: SessionInputRow
    generated: Optional[SessionInputRow] = None
