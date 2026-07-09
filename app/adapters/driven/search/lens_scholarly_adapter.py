from __future__ import annotations

from typing import Any, Optional

from services.search.lens_service import LensService
from app.core.domain.types import SearchResult
from app.adapters.driven.search._converters import to_domain


class LensScholarlyAdapter:
    def __init__(self, service: LensService) -> None:
        self._service = service

    @property
    def api_name(self) -> str:
        return "lens_scholarly"

    def is_available(self) -> bool:
        return bool(self._service.api_token)

    async def search(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        result = await self._service.search_scholarly(query, run_id)
        return to_domain(result)
