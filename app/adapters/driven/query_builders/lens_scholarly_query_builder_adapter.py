from __future__ import annotations

from typing import Any, Optional

from app.adapters.driven.query_builders._converters import response_to_output
from app.core.domain.types import LLMResponse
from services.query_builders.lens_scholarly_query_builder import LensScholarlyQueryBuilder


class LensScholarlyQueryBuilderAdapter:
    def __init__(self, search_mode: str = "final", variant: Optional[str] = None) -> None:
        self._builder = LensScholarlyQueryBuilder(
            api_name="lens_scholarly",
            search_mode=search_mode,
            variant=variant,
        )

    @property
    def api_name(self) -> str:
        return "lens_scholarly"

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
