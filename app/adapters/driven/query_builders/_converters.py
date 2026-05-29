from __future__ import annotations

from app.core.domain.types import LLMResponse, TermGroup as DomainTermGroup, TextualQuery
from schemas.llm import LLMOutput, SimpleFieldQuery, TermGroup, TextualFieldQuery


def response_to_output(response: LLMResponse) -> LLMOutput:
    """Convert domain LLMResponse to schema LLMOutput for legacy query builders."""
    return LLMOutput(
        title=_to_textual(response.title),
        abstract=_to_textual(response.abstract),
        claims=_to_textual(response.claims),
        description=_to_textual(response.description),
        full_text=_to_textual(response.full_text),
        ipc=SimpleFieldQuery(values=list(response.ipc)),
        cpc=SimpleFieldQuery(values=list(response.cpc)),
        authors=SimpleFieldQuery(values=list(response.authors)),
        affiliation=SimpleFieldQuery(values=list(response.affiliation)),
        applicant=SimpleFieldQuery(values=list(response.applicant)),
        inventor=SimpleFieldQuery(values=list(response.inventor)),
        field_of_study=SimpleFieldQuery(values=list(response.field_of_study)),
        keywords=SimpleFieldQuery(values=list(response.keywords)),
        source_title=SimpleFieldQuery(values=list(response.source_title)),
        year=SimpleFieldQuery(values=list(response.year)),
    )


def _to_textual(q: TextualQuery) -> TextualFieldQuery:
    return TextualFieldQuery(
        group_operator=q.group_operator,
        groups=[
            TermGroup(terms=list(g.terms), operator=g.operator)
            for g in q.groups
        ],
    )
