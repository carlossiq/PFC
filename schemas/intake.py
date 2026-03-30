"""
Input contract schemas for prospecting requests.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DocumentTypeEnum(str, Enum):
    """
    Enumeração de tipos de documentos suportados.
    """

    PATENT = "patent"
    PUBLICATION = "publication"
    BOTH = "both"


class InputIntake(BaseModel):
    """
    Contrato de entrada inicial para requisições de prospecção.

    Define os parâmetros de entrada do usuário que iniciam o pipeline
    de análise tecnológica.
    """

    theme: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Tema principal da prospecção tecnológica",
    )
    objective: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Objetivo específico da análise",
    )
    initial_keywords: Optional[list[str]] = Field(
        default=None,
        max_items=50,
        description="Palavras-chave iniciais para refinamento da busca",
    )
    document_type: DocumentTypeEnum = Field(
        default=DocumentTypeEnum.BOTH,
        description="Tipo de documentos a serem pesquisados",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "theme": "Machine Learning in Healthcare",
                "objective": "Identify emerging trends in diagnostic AI",
                "initial_keywords": ["deep learning", "medical imaging"],
                "document_type": "both",
            }
        }

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, value: str) -> str:
        """
        Valida e normaliza o tema.
        """
        return value.strip()

    @field_validator("objective", mode="before")
    @classmethod
    def validate_objective(cls, value: Optional[str]) -> Optional[str]:
        """
        Valida e normaliza o objetivo.
        """
        if value is not None:
            return value.strip() if value.strip() else None
        return None

    @field_validator("initial_keywords", mode="before")
    @classmethod
    def validate_keywords(cls, value: Optional[list[str]]) -> Optional[list[str]]:
        """
        Valida e normaliza palavras-chave, removendo duplicatas e vazios.
        """
        if value is None:
            return None

        normalized = [kw.strip() for kw in value if kw.strip()]
        return list(set(normalized)) if normalized else None

    @field_validator("document_type", mode="before")
    @classmethod
    def normalize_document_type(cls, value: str) -> str:
        """
        Normaliza o tipo de documento para 'both' sempre.
        """
        return DocumentTypeEnum.BOTH.value
