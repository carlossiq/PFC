"""
Search services package for external API integrations.
"""

from services.search.base import SearchError, SearchResult
from services.search.lens_service import LensService
from services.search.ops_service import OPSService, OPSToken
from services.search.scopus_service import ScopusService

__all__ = [
    "SearchResult",
    "SearchError",
    "LensService",
    "OPSService",
    "OPSToken",
    "ScopusService",
]
