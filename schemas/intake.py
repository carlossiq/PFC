"""
Input contract schemas for prospecting requests.
"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InputIntake(BaseModel):
    """
    Contrato de entrada inicial para requisições de prospecção.

    Define os parâmetros de entrada do usuário que iniciam o pipeline
    de análise tecnológica. Todos os campos são passados para a LLM.
    """

    theme: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Tema principal da prospecção tecnológica (obrigatório)",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Descrição detalhada do tema e contexto da pesquisa",
    )
    area_of_study: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Área de estudo ou domínio específico (ex: Healthcare, Finance, Manufacturing, IPC/CPC classes, etc.)",
    )
    keywords: Optional[list[str]] = Field(
        default=None,
        max_items=50,
        description="Palavras-chave iniciais para refinamento da busca",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "theme": "Machine Learning in Healthcare",
                "description": "Identify emerging trends in diagnostic AI systems, focusing on deep learning applications",
                "area_of_study": "Healthcare",
                "keywords": ["deep learning", "medical imaging", "diagnostic AI"],
            }
        }

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        """Valida e normaliza o tema."""
        return value.strip()

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        """Valida e normaliza a descrição."""
        if value is not None:
            stripped = value.strip()
            return stripped if stripped else None
        return None

    @field_validator("area_of_study", mode="before")
    @classmethod
    def validate_area_of_study(cls, value: Optional[str]) -> Optional[str]:
        """Valida e normaliza a área de estudo."""
        if value is not None:
            stripped = value.strip()
            return stripped if stripped else None
        return None

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """
        Valida e normaliza palavras-chave, removendo duplicatas e vazios.
        """
        if value is None:
            return None

        normalized = [kw.strip() for kw in value if isinstance(kw, str) and kw.strip()]
        return list(set(normalized)) if normalized else None
