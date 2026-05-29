from __future__ import annotations

from typing import Any, Optional

from services.search.ops_service import OPSService
from app.core.domain.types import SearchResult
from app.adapters.driven.search._converters import to_domain


class OPSAdapter:
    def __init__(self, service: OPSService) -> None:
        self._service = service

    @property
    def api_name(self) -> str:
        return "ops"

    def is_available(self) -> bool:
        return bool(self._service.consumer_key and self._service.consumer_secret)

    async def search(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        result = await self._service.search(query, run_id)
        return to_domain(result)
