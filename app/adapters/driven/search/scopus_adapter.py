from __future__ import annotations

from typing import Any, Optional

from services.search.scopus_service import ScopusService
from app.core.domain.types import SearchResult
from app.adapters.driven.search._converters import to_domain


class ScopusAdapter:
    def __init__(self, service: ScopusService) -> None:
        self._service = service

    @property
    def api_name(self) -> str:
        return "scopus"

    def is_available(self) -> bool:
        return bool(self._service.api_key)

    async def search(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
        max_results: int = 500,
    ) -> SearchResult:
        result = await self._service.search(query, run_id, max_results=max_results)
        return to_domain(result)

    async def count(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        result = await self._service.count(query, run_id)
        return to_domain(result)

    async def fetch_results_page(
        self,
        query: dict[str, Any],
        start: int = 0,
        count: int = 200,
        run_id: Optional[str] = None,
    ) -> SearchResult:
        result = await self._service.fetch_results_page(query, start=start, count=count, run_id=run_id)
        return to_domain(result)
