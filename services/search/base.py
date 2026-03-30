"""
Base class for search services.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SearchResult:
    """
    Resultado de uma busca em API externa.

    Encapsula dados de sucesso ou erro de uma busca.
    """

    api_name: str
    success: bool
    query: str
    results: list[dict[str, Any]] = field(default_factory=list)
    total_count: Optional[int] = None
    results_returned: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_seconds: float = 0.0
    run_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Converte resultado para dicionário.

        Returns:
            Dicionário com dados do resultado.
        """
        return {
            "api_name": self.api_name,
            "success": self.success,
            "query": self.query,
            "results": self.results,
            "total_count": self.total_count,
            "results_returned": self.results_returned,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "duration_seconds": self.duration_seconds,
            "run_id": self.run_id,
        }


@dataclass
class SearchError:
    """
    Informações estruturadas sobre erro em busca.

    Proporciona detalhes padronizados sobre o que falhou.
    """

    api_name: str
    error_code: str
    error_message: str
    is_retryable: bool
    run_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """
        Converte erro para dicionário.

        Returns:
            Dicionário com informações do erro.
        """
        return {
            "api_name": self.api_name,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "is_retryable": self.is_retryable,
            "run_id": self.run_id,
            "details": self.details,
        }
