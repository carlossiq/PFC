from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from app.core.domain.types import SearchResult


@runtime_checkable
class PatentSearchPort(Protocol):
    @property
    def api_name(self) -> str: ...

    def is_available(self) -> bool: ...

    async def search(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult: ...


@runtime_checkable
class ScholarlySearchPort(Protocol):
    @property
    def api_name(self) -> str: ...

    def is_available(self) -> bool: ...

    async def search(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult: ...
