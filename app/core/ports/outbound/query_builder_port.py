from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.core.domain.types import LLMResponse


@runtime_checkable
class PatentQueryBuilderPort(Protocol):
    @property
    def api_name(self) -> str: ...

    def build_query(
        self,
        strategy: LLMResponse,
        year_from: int = 2015,
        year_to: int = 2024,
        search_mode: str = "final",
    ) -> dict[str, Any]: ...


@runtime_checkable
class ScholarlyQueryBuilderPort(Protocol):
    @property
    def api_name(self) -> str: ...

    def build_query(
        self,
        strategy: LLMResponse,
        year_from: int = 2015,
        year_to: int = 2024,
    ) -> dict[str, Any]: ...
