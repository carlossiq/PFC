from __future__ import annotations

from schemas.intake import InputIntake
from schemas.llm import LLMOutput, TextualFieldQuery
from app.core.domain.types import LLMRequest, LLMResponse, TermGroup, TextualQuery


def request_to_intake(request: LLMRequest) -> InputIntake:
    return InputIntake(
        theme=request.theme,
        description=request.description,
        area_of_study=request.area_of_study,
        keywords=request.keywords if request.keywords else None,
    )


def output_to_response(output: LLMOutput) -> LLMResponse:
    return LLMResponse(
        title=_textual(output.title),
        abstract=_textual(output.abstract),
        claims=_textual(output.claims),
        description=_textual(output.description),
        full_text=_textual(output.full_text),
        ipc=list(output.ipc.values),
        cpc=list(output.cpc.values),
        authors=list(output.authors.values),
        affiliation=list(output.affiliation.values),
        applicant=list(output.applicant.values),
        inventor=list(output.inventor.values),
        field_of_study=list(output.field_of_study.values),
        keywords=list(output.keywords.values),
        source_title=list(output.source_title.values),
        year=list(output.year.values),
    )


def _textual(field: TextualFieldQuery) -> TextualQuery:
    return TextualQuery(
        groups=[
            TermGroup(terms=list(g.terms), operator=g.operator.value)
            for g in field.groups
        ],
        group_operator=field.group_operator.value,
    )
