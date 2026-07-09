"""
LLM output contract schemas with validation rules.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class OperatorEnum(str, Enum):
    """
    Enumeração de operadores lógicos suportados.
    """

    AND = "AND"
    OR = "OR"


class TermGroup(BaseModel):
    """
    Agrupamento de termos com operador lógico.

    Representa um conjunto de termos conectados por um operador (AND/OR).
    """

    operator: OperatorEnum = Field(
        default=OperatorEnum.OR,
        description="Operador lógico (AND ou OR)",
    )
    terms: list[str] = Field(
        default_factory=list,
        description="Lista de termos do grupo",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "operator": "OR",
                "terms": ["machine learning", "deep learning", "neural networks"],
            }
        }

    @field_validator("terms", mode="before")
    @classmethod
    def normalize_terms(cls, value: list[str]) -> list[str]:
        """
        Normaliza termos removendo duplicatas, vazios e normalizando espaçamento.
        """
        if not value:
            return []

        normalized = [term.strip() for term in value if isinstance(term, str) and term.strip()]
        return list(set(normalized))

    @field_validator("operator", mode="before")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        """
        Valida que o operador é um valor permitido.
        """
        if isinstance(value, str):
            upper_value = value.upper()
            if upper_value in [op.value for op in OperatorEnum]:
                return upper_value
        raise ValueError(f"Operador deve ser AND ou OR, recebido: {value}")


class TextualFieldQuery(BaseModel):
    """
    Contrato para campos textuais em consultas LLM.

    Representa consultas estruturadas sobre campos textuais como TITLE,
    ABSTRACT, CLAIMS, etc., com grupos de termos conectados por operadores.
    """

    group_operator: OperatorEnum = Field(
        default=OperatorEnum.AND,
        description="Operador entre grupos (AND ou OR)",
    )
    groups: list[TermGroup] = Field(
        default_factory=list,
        description="Grupos de termos para busca textual",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "group_operator": "AND",
                "groups": [
                    {
                        "operator": "OR",
                        "terms": ["machine learning", "deep learning"],
                    },
                    {
                        "operator": "OR",
                        "terms": ["healthcare", "medical"],
                    },
                ],
            }
        }

    @field_validator("group_operator", mode="before")
    @classmethod
    def validate_group_operator(cls, value: str) -> str:
        """
        Valida que o operador de grupo é um valor permitido.
        """
        if isinstance(value, str):
            upper_value = value.upper()
            if upper_value in [op.value for op in OperatorEnum]:
                return upper_value
        raise ValueError(f"Operador de grupo deve ser AND ou OR, recebido: {value}")

    @field_validator("groups", mode="before")
    @classmethod
    def validate_and_filter_groups(cls, value: list) -> list[TermGroup]:
        """
        Valida e filtra grupos vazios, convertendo dicts para TermGroup.
        """
        if not value:
            return []

        groups = []
        for item in value:
            if isinstance(item, dict):
                group = TermGroup(**item)
            elif isinstance(item, TermGroup):
                group = item
            else:
                continue

            # Filtra grupos vazios
            if group.terms:
                groups.append(group)

        return groups

    def is_empty(self) -> bool:
        """
        Verifica se a consulta está vazia (sem grupos ou grupos sem termos).
        """
        return not self.groups or all(not group.terms for group in self.groups)


class SimpleFieldQuery(BaseModel):
    """
    Contrato para campos simples em consultas LLM.

    Representa consultas sobre campos simples como IPC, CPC, AUTHORS, etc.
    Campos simples são sempre listas de strings sem operadores lógicos.
    """

    values: list[str] = Field(
        default_factory=list,
        description="Lista de valores para busca simples",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "values": ["G06N3/08", "G16H50/20"],
            }
        }

    @field_validator("values", mode="before")
    @classmethod
    def normalize_values(cls, value: list[str]) -> list[str]:
        """
        Normaliza valores removendo duplicatas e vazios.
        """
        if not value:
            return []

        normalized = [v.strip() for v in value if isinstance(v, str) and v.strip()]
        return list(set(normalized))

    def is_empty(self) -> bool:
        """
        Verifica se a consulta está vazia.
        """
        return not self.values


class LLMOutput(BaseModel):
    """
    Contrato de saída do modelo LLM com campos de busca estruturados.

    Agrupa todas as consultas geradas pelo LLM, tanto para campos textuais
    quanto para campos simples, seguindo regras rigorosas de validação.
    """

    # Textual fields
    title: TextualFieldQuery = Field(
        default_factory=TextualFieldQuery,
        description="Consulta estruturada para campo TITLE",
    )
    abstract: TextualFieldQuery = Field(
        default_factory=TextualFieldQuery,
        description="Consulta estruturada para campo ABSTRACT",
    )
    claims: TextualFieldQuery = Field(
        default_factory=TextualFieldQuery,
        description="Consulta estruturada para campo CLAIMS",
    )
    description: TextualFieldQuery = Field(
        default_factory=TextualFieldQuery,
        description="Consulta estruturada para campo DESCRIPTION",
    )
    full_text: TextualFieldQuery = Field(
        default_factory=TextualFieldQuery,
        description="Consulta estruturada para campo FULL_TEXT",
    )

    # Simple fields
    ipc: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Códigos IPC (International Patent Classification)",
    )
    cpc: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Códigos CPC (Cooperative Patent Classification)",
    )
    authors: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Autores dos documentos",
    )
    affiliation: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Afiliações dos autores",
    )
    applicant: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Requerentes de patentes",
    )
    inventor: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Inventores",
    )
    field_of_study: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Campos de estudo",
    )
    keywords: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Palavras-chave dos documentos",
    )
    source_title: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Títulos de fontes de publicação",
    )
    year: SimpleFieldQuery = Field(
        default_factory=SimpleFieldQuery,
        description="Anos de publicação/patente",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "title": {
                    "group_operator": "AND",
                    "groups": [
                        {"operator": "OR", "terms": ["machine learning", "deep learning", "neural network"]},
                        {"operator": "OR", "terms": ["healthcare", "medical diagnosis", "clinical"]},
                    ],
                },
                "abstract": {
                    "group_operator": "AND",
                    "groups": [
                        {"operator": "OR", "terms": ["diagnostic system", "disease detection", "image segmentation"]},
                    ],
                },
                "claims": {
                    "group_operator": "AND",
                    "groups": [
                        {"operator": "OR", "terms": ["convolutional neural network", "image classification"]},
                    ],
                },
                "ipc": {"values": ["G06N3/08", "G16H50/20", "G06T7/00"]},
                "cpc": {"values": ["G06N3/084", "G16H50/20"]},
                "keywords": {"values": ["deep learning", "medical imaging", "CNN", "diagnosis"]},
            }
        }

    @field_validator("title", "abstract", "claims", "description", "full_text", mode="before")
    @classmethod
    def parse_textual_fields(cls, value) -> TextualFieldQuery:
        """
        Converte campos textuais para TextualFieldQuery se necessário.
        """
        if isinstance(value, dict):
            return TextualFieldQuery(**value)
        elif isinstance(value, TextualFieldQuery):
            return value
        elif value is None:
            return TextualFieldQuery()
        raise ValueError(f"Campo textual inválido: {value}")

    @field_validator("ipc", "cpc", "authors", "affiliation", "applicant", "inventor",
                     "field_of_study", "keywords", "source_title", "year", mode="before")
    @classmethod
    def parse_simple_fields(cls, value) -> SimpleFieldQuery:
        """
        Converte campos simples para SimpleFieldQuery se necessário.
        """
        if isinstance(value, dict):
            # Se for dict com 'values', usar como está
            if "values" in value:
                return SimpleFieldQuery(**value)
            # Se for dict com lista de valores, converter
            elif isinstance(value.get("values"), list):
                return SimpleFieldQuery(**value)
            else:
                return SimpleFieldQuery()
        elif isinstance(value, list):
            # Se for lista direta, converter para SimpleFieldQuery
            return SimpleFieldQuery(values=value)
        elif isinstance(value, SimpleFieldQuery):
            return value
        elif value is None:
            return SimpleFieldQuery()
        raise ValueError(f"Campo simples inválido: {value}")

    def get_active_fields(self) -> dict[str, bool]:
        """
        Retorna dicionário indicando quais campos têm consultas ativas (não vazias).
        """
        return {
            "title": not self.title.is_empty(),
            "abstract": not self.abstract.is_empty(),
            "claims": not self.claims.is_empty(),
            "description": not self.description.is_empty(),
            "full_text": not self.full_text.is_empty(),
            "ipc": not self.ipc.is_empty(),
            "cpc": not self.cpc.is_empty(),
            "authors": not self.authors.is_empty(),
            "affiliation": not self.affiliation.is_empty(),
            "applicant": not self.applicant.is_empty(),
            "inventor": not self.inventor.is_empty(),
            "field_of_study": not self.field_of_study.is_empty(),
            "keywords": not self.keywords.is_empty(),
            "source_title": not self.source_title.is_empty(),
            "year": not self.year.is_empty(),
        }

    def has_any_queries(self) -> bool:
        """
        Verifica se há pelo menos uma consulta ativa em qualquer campo.
        """
        return any(self.get_active_fields().values())
