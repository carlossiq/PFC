"""
Query builder schemas for constructing search queries from LLM output.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field

from schemas.llm import LLMOutput, OperatorEnum, SimpleFieldQuery, TermGroup, TextualFieldQuery


class TextualQueryClause(BaseModel):
    """
    Cláusula de busca construída para campos textuais.

    Representa uma consulta estruturada pronta para ser executada
    contra bases de dados ou engines de busca.
    """

    field: str = Field(
        ...,
        description="Nome do campo (TITLE, ABSTRACT, etc.)",
    )
    group_operator: OperatorEnum = Field(
        default=OperatorEnum.AND,
        description="Operador lógico entre grupos",
    )
    groups: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Grupos de termos estruturados",
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Converte cláusula para dicionário para serialização.
        """
        return {
            "field": self.field,
            "group_operator": self.group_operator.value,
            "groups": self.groups,
        }


class SimpleQueryClause(BaseModel):
    """
    Cláusula de busca para campos simples.

    Representa uma consulta simples (lista de valores) pronta para execução.
    """

    field: str = Field(
        ...,
        description="Nome do campo (IPC, CPC, AUTHORS, etc.)",
    )
    values: list[str] = Field(
        default_factory=list,
        description="Valores para busca",
    )
    operator: OperatorEnum = Field(
        default=OperatorEnum.OR,
        description="Operador lógico entre valores",
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Converte cláusula para dicionário para serialização.
        """
        return {
            "field": self.field,
            "values": self.values,
            "operator": self.operator.value,
        }


class QueryBuilderOutput(BaseModel):
    """
    Saída do construtor de consultas com cláusulas prontas para execução.

    Converte a saída do LLM em consultas estruturadas otimizadas para
    diferentes engines de busca.
    """

    textual_clauses: list[TextualQueryClause] = Field(
        default_factory=list,
        description="Cláusulas de busca para campos textuais",
    )
    simple_clauses: list[SimpleQueryClause] = Field(
        default_factory=list,
        description="Cláusulas de busca para campos simples",
    )
    query_count: int = Field(
        default=0,
        description="Número total de cláusulas de busca",
    )

    class Config:
        """Configuração do Pydantic."""

        json_schema_extra = {
            "example": {
                "textual_clauses": [
                    {
                        "field": "TITLE",
                        "group_operator": "AND",
                        "groups": [
                            {
                                "operator": "OR",
                                "terms": ["machine learning", "deep learning"],
                            }
                        ],
                    }
                ],
                "simple_clauses": [
                    {
                        "field": "IPC",
                        "values": ["G06F", "G06N"],
                        "operator": "OR",
                    }
                ],
                "query_count": 2,
            }
        }

    @staticmethod
    def from_llm_output(llm_output: LLMOutput) -> "QueryBuilderOutput":
        """
        Constrói QueryBuilderOutput a partir de LLMOutput.

        Mapeia campos do LLM output para cláusulas de consulta estruturadas.
        """
        textual_clauses = []
        simple_clauses = []

        # Processar campos textuais
        textual_fields = {
            "TITLE": llm_output.title,
            "ABSTRACT": llm_output.abstract,
            "CLAIMS": llm_output.claims,
            "DESCRIPTION": llm_output.description,
            "FULL_TEXT": llm_output.full_text,
        }

        for field_name, field_query in textual_fields.items():
            if not field_query.is_empty():
                clause = TextualQueryClause(
                    field=field_name,
                    group_operator=field_query.group_operator,
                    groups=[
                        {
                            "operator": group.operator.value,
                            "terms": group.terms,
                        }
                        for group in field_query.groups
                    ],
                )
                textual_clauses.append(clause)

        # Processar campos simples
        simple_fields = {
            "IPC": llm_output.ipc,
            "CPC": llm_output.cpc,
            "AUTHORS": llm_output.authors,
            "AFFILIATION": llm_output.affiliation,
            "APPLICANT": llm_output.applicant,
            "INVENTOR": llm_output.inventor,
            "FIELD_OF_STUDY": llm_output.field_of_study,
            "KEYWORDS": llm_output.keywords,
            "SOURCE_TITLE": llm_output.source_title,
            "YEAR": llm_output.year,
        }

        for field_name, field_query in simple_fields.items():
            if not field_query.is_empty():
                clause = SimpleQueryClause(
                    field=field_name,
                    values=field_query.values,
                    operator=OperatorEnum.OR,
                )
                simple_clauses.append(clause)

        return QueryBuilderOutput(
            textual_clauses=textual_clauses,
            simple_clauses=simple_clauses,
            query_count=len(textual_clauses) + len(simple_clauses),
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Converte output completo para dicionário para serialização.
        """
        return {
            "textual_clauses": [clause.to_dict() for clause in self.textual_clauses],
            "simple_clauses": [clause.to_dict() for clause in self.simple_clauses],
            "query_count": self.query_count,
        }
