from __future__ import annotations

from typing import Any

from app.adapters.driven.query_builders._converters import response_to_output
from app.core.domain.types import LLMResponse
from services.query_builders.scopus_query_builder import ScopusQueryBuilder


class ScopusQueryBuilderAdapter:
    def __init__(self, search_mode: str = "final") -> None:
        self._builder = ScopusQueryBuilder(
            api_name="scopus",
            search_mode=search_mode,
        )

    @property
    def api_name(self) -> str:
        return "scopus"

    def build_query(
        self,
        strategy: LLMResponse,
        year_from: int = 2015,
        year_to: int = 2024,
        search_mode: str = "final",
    ) -> dict[str, Any]:
        self._builder.search_mode = search_mode
        llm_output = response_to_output(strategy)
        return self._builder.build_query(
            llm_output=llm_output,
            year_from=year_from,
            year_to=year_to,
        )
