from __future__ import annotations

from typing import Any

from app.adapters.driven.query_builders._converters import response_to_output
from app.core.domain.types import LLMResponse
from services.query_builders.ops_query_builder import OPSQueryBuilder


class OPSQueryBuilderAdapter:
    def __init__(self, search_mode: str = "final") -> None:
        self._builder = OPSQueryBuilder(
            api_name="ops",
            search_mode=search_mode,
        )

    @property
    def api_name(self) -> str:
        return "ops"

    def build_query(
        self,
        strategy: LLMResponse,
        year_from: int = 2015,
        year_to: int = 2024,
        search_mode: str = "final",
    ) -> dict[str, Any]:
        llm_output = response_to_output(strategy)
        return self._builder.build_query(
            llm_output=llm_output,
            year_from=year_from,
            year_to=year_to,
        )
