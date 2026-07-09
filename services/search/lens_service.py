"""
Search service for Google Lens API (Patents and Scholarly).
"""

import asyncio
import time
from typing import Any, Literal, Optional

import httpx

from core.config import settings
from core.logging import get_logger
from services.search.base import SearchError, SearchResult

logger = get_logger(__name__)


class LensService:
    """
    Serviço de busca na API Google Lens.

    Gerencia requisições para Lens Patents e Lens Scholarly com
    tratamento de erros, retentativas e structured responses.
    """

    # Configurações
    _LENS_PATENT_URL = "https://api.lens.org/patent/search"
    _LENS_SCHOLARLY_URL = "https://api.lens.org/scholarly/search"
    _MAX_RETRIES = 3
    _RETRY_DELAY_SECONDS = 1
    _TIMEOUT_SECONDS = 30

    def __init__(self, api_token: Optional[str] = None) -> None:
        """
        Inicializa o serviço Lens.

        Args:
            api_token: Token de API do Lens (se None, tenta obter de config).
        """
        self.api_token = api_token or getattr(settings, "lens_api_token", None)
        self.client = httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS)

    async def search_patent(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Busca em Lens Patents.

        Args:
            query: Query payload (JSON) para Lens API.
            run_id: ID único da requisição para logging.

        Returns:
            SearchResult com dados de sucesso ou erro.
        """
        return await self._search(
            api_type="patent",
            url=self._LENS_PATENT_URL,
            query=query,
            run_id=run_id,
        )

    async def search_scholarly(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Busca em Lens Scholarly.

        Args:
            query: Query payload (JSON) para Lens API.
            run_id: ID único da requisição para logging.

        Returns:
            SearchResult com dados de sucesso ou erro.
        """
        return await self._search(
            api_type="scholarly",
            url=self._LENS_SCHOLARLY_URL,
            query=query,
            run_id=run_id,
        )

    async def _search(
        self,
        api_type: Literal["patent", "scholarly"],
        url: str,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Executa busca interna com retry logic.

        Args:
            api_type: Tipo de API (patent ou scholarly).
            url: URL da API.
            query: Query payload.
            run_id: ID único da requisição.

        Returns:
            SearchResult com dados ou erro.
        """
        start_time = time.time()
        retry_count = 0

        for attempt in range(self._MAX_RETRIES):
            try:
                logger.info(
                    "lens_search_attempt",
                    api_type=api_type,
                    attempt=attempt + 1,
                    run_id=run_id,
                )

                # Fazer requisição
                response = await self.client.post(
                    url,
                    json=query,
                    headers=self._get_headers(),
                    timeout=self._TIMEOUT_SECONDS,
                )

                # Validar status
                response.raise_for_status()

                # Extrair dados
                data = response.json()

                duration = time.time() - start_time

                # API retorna "data" e "total"
                results_list = data.get("data", [])
                total = data.get("total")

                logger.info(
                    "lens_search_success",
                    api_type=api_type,
                    results_count=len(results_list) if isinstance(results_list, list) else 0,
                    total_count=total,
                    duration=duration,
                    run_id=run_id,
                )

                return SearchResult(
                    api_name=f"lens_{api_type}",
                    success=True,
                    query=str(query),
                    results=results_list if isinstance(results_list, list) else [],
                    total_count=total,
                    results_returned=len(results_list) if isinstance(results_list, list) else 0,
                    retry_count=retry_count,
                    duration_seconds=duration,
                    run_id=run_id,
                )

            except httpx.HTTPStatusError as exc:
                retry_count = attempt
                duration = time.time() - start_time

                # Determinar se é retentável
                is_retryable = exc.response.status_code in [408, 429, 500, 502, 503, 504]

                logger.warning(
                    "lens_search_http_error",
                    api_type=api_type,
                    status_code=exc.response.status_code,
                    attempt=attempt + 1,
                    is_retryable=is_retryable,
                    run_id=run_id,
                )

                if not is_retryable or attempt == self._MAX_RETRIES - 1:
                    error = SearchError(
                        api_name=f"lens_{api_type}",
                        error_code=f"HTTP_{exc.response.status_code}",
                        error_message=f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}",
                        is_retryable=False,
                        run_id=run_id,
                    )

                    return SearchResult(
                        api_name=f"lens_{api_type}",
                        success=False,
                        query=str(query),
                        error_code=error.error_code,
                        error_message=error.error_message,
                        retry_count=retry_count,
                        duration_seconds=duration,
                        run_id=run_id,
                    )

                # Aguardar antes de retentarr
                await asyncio.sleep(self._RETRY_DELAY_SECONDS * (attempt + 1))

            except httpx.TimeoutException:
                retry_count = attempt
                duration = time.time() - start_time

                logger.warning(
                    "lens_search_timeout",
                    api_type=api_type,
                    attempt=attempt + 1,
                    run_id=run_id,
                )

                if attempt == self._MAX_RETRIES - 1:
                    return SearchResult(
                        api_name=f"lens_{api_type}",
                        success=False,
                        query=str(query),
                        error_code="TIMEOUT",
                        error_message="Request timeout",
                        retry_count=retry_count,
                        duration_seconds=duration,
                        run_id=run_id,
                    )

                await asyncio.sleep(self._RETRY_DELAY_SECONDS * (attempt + 1))

            except Exception as exc:
                duration = time.time() - start_time

                logger.error(
                    "lens_search_error",
                    api_type=api_type,
                    error=str(exc),
                    error_type=type(exc).__name__,
                    run_id=run_id,
                )

                return SearchResult(
                    api_name=f"lens_{api_type}",
                    success=False,
                    query=str(query),
                    error_code="UNKNOWN_ERROR",
                    error_message=str(exc),
                    retry_count=retry_count,
                    duration_seconds=duration,
                    run_id=run_id,
                )

        # Fallback se todas tentativas falharem
        duration = time.time() - start_time
        return SearchResult(
            api_name=f"lens_{api_type}",
            success=False,
            query=str(query),
            error_code="MAX_RETRIES_EXCEEDED",
            error_message="Maximum retries exceeded",
            retry_count=self._MAX_RETRIES,
            duration_seconds=duration,
            run_id=run_id,
        )

    def _get_headers(self) -> dict[str, str]:
        """
        Constrói headers para requisição Lens.

        Returns:
            Dicionário com headers HTTP.
        """
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        return headers

    async def close(self) -> None:
        """
        Fecha cliente httpx.
        """
        await self.client.aclose()

    async def __aenter__(self):
        """
        Context manager entry.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.
        """
        await self.close()
