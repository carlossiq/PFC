"""
Schemas for capturing Step1 (initial parameters) of the prospecting wizard.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ParamInitRequest(BaseModel):
    """Parâmetros iniciais enviados pelo Step1/Step2 do wizard."""

    tema: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Tema principal da prospecção tecnológica (obrigatório)",
    )
    descricao: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Descrição detalhada do tema e contexto da pesquisa",
    )
    area_estudo: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Área de estudo ou domínio específico",
    )
    keywords: Optional[list[str]] = Field(
        default=None,
        max_items=50,
        description="Palavras-chave iniciais para refinamento da busca",
    )

    @field_validator("tema")
    @classmethod
    def validate_tema(cls, value: str) -> str:
        """Valida e normaliza o tema."""
        return value.strip()

    @field_validator("descricao", "area_estudo", mode="before")
    @classmethod
    def validate_optional_text(cls, value: Optional[str]) -> Optional[str]:
        """Valida e normaliza campos textuais opcionais."""
        if value is not None:
            stripped = value.strip()
            return stripped if stripped else None
        return None

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """Valida e normaliza palavras-chave, removendo duplicatas e vazios."""
        if value is None:
            return None

        normalized = [kw.strip() for kw in value if isinstance(kw, str) and kw.strip()]
        return list(set(normalized)) if normalized else None


class ParamInitResponse(BaseModel):
    """Representação persistida de um PARAM_INIT."""

    id: int
    tema: str
    descricao: Optional[str] = None
    area_estudo: Optional[str] = None
    keywords: Optional[list[str]] = None

    class Config:
        """Configuração do Pydantic."""

        from_attributes = True
