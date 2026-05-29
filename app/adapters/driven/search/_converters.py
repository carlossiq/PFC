from __future__ import annotations

from services.search.base import SearchResult as _ServiceResult
from app.core.domain.types import SearchResult


def to_domain(r: _ServiceResult) -> SearchResult:
    return SearchResult(
        api_name=r.api_name,
        success=r.success,
        query=r.query,
        results=r.results,
        total_count=r.total_count,
        results_returned=r.results_returned,
        error_code=r.error_code,
        error_message=r.error_message,
        retry_count=r.retry_count,
        duration_seconds=r.duration_seconds,
        run_id=r.run_id,
    )
