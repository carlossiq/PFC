"""
Search service for Scopus API with pagination.
"""

import asyncio
import time
from dataclasses import replace
from typing import Any, Optional

import httpx

from core.config import settings
from core.logging import get_logger
from services.search.base import SearchError, SearchResult

logger = get_logger(__name__)


def _extract_final_fields(entry: dict[str, Any]) -> dict[str, Any]:
    """
    Extração enxuta (title/institutions/year) usada só pela busca final (ver
    ScopusService.fetch_results_page) - dedicada, não a mesma usada pela
    probe (que devolve o entry inteiro pra enriquecimento via OpenAlex em
    ChatService._enrich_scopus_abstracts), pra não arriscar mudar o
    comportamento dela.

    "affilname" é o campo confirmado contra resposta real desta API key -
    diferente de "organization", usado sem confirmação em
    NormalizationService._extract_scopus_affiliations. "affiliation" vem
    como lista normalmente, mas a Scopus devolve um dict solto (não
    envolto em lista) quando há só 1 afiliação (mesma ressalva de
    NormalizationService._extract_scopus_affiliation_countries).
    """
    title = entry.get("dc:title")

    cover_date = entry.get("prism:coverDate") or ""
    year = int(cover_date[:4]) if cover_date[:4].isdigit() else None

    raw_affiliations = entry.get("affiliation")
    affiliation_list = raw_affiliations if isinstance(raw_affiliations, list) else [raw_affiliations] if raw_affiliations else []
    institutions = [
        aff["affilname"] for aff in affiliation_list if isinstance(aff, dict) and aff.get("affilname")
    ]

    return {"title": title, "institutions": institutions, "year": year}


class ScopusService:
    """
    Serviço de busca na API Scopus com suporte a paginação.

    Gerencia requisições e paginação automática com checks de relevância.
    """

    # Configurações
    _SCOPUS_API_URL = "https://api.elsevier.com/content/search/scopus"
    _MAX_RETRIES = 3
    _RETRY_DELAY_SECONDS = 2
    _TIMEOUT_SECONDS = 30
    _DEFAULT_RESULTS_PER_PAGE = 25
    # Teto de segurança pra paginação (nunca mais que isso, independente do
    # max_results pedido pelo chamador) - 40 páginas de 25 = 1000 resultados,
    # margem suficiente pro fetch com 3x de folga do final search (ver
    # ChatService.run_final_search) sem risco de loop indefinido.
    _MAX_PAGES = 40
    # Limite por requisição pra essa API key na busca final - usado só por
    # fetch_results_page/count, nunca por search(). Era 200 (valor nunca
    # confirmado contra a API de verdade); testado diretamente agora:
    # count=25 funciona, count=26 já devolve 400 INVALID_INPUT ("Exceeds
    # the maximum number allowed for the service level") - o teto real
    # dessa API key é o MESMO de _DEFAULT_RESULTS_PER_PAGE (25), não um
    # valor maior liberado especificamente pra busca final.
    _FINAL_SEARCH_PAGE_SIZE = 25

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Inicializa o serviço Scopus.

        Args:
            api_key: API key do Scopus (se None, tenta config).
        """
        self.api_key = api_key or getattr(settings, "scopus_api_key", None)
        self.async_client = httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS)

    async def search(
        self,
        query_params: dict[str, Any],
        run_id: Optional[str] = None,
        max_results: int = 500,
    ) -> SearchResult:
        """
        Executa busca em Scopus com paginação automática.

        Continua obtendo próximas páginas enquanto houver resultados
        potencialmente relevantes e não atingir limite.

        Args:
            query_params: Parâmetros de query para Scopus.
            run_id: ID único da requisição para logging.
            max_results: Número máximo de resultados a retornar.

        Returns:
            SearchResult com todos os resultados paginados.
        """
        start_time = time.time()
        all_results = []
        current_start = 0
        page_count = 0
        total_count: Optional[int] = None

        try:
            while page_count < self._MAX_PAGES and len(all_results) < max_results:
                page_count += 1

                logger.info(
                    "scopus_search_page",
                    page=page_count,
                    results_so_far=len(all_results),
                    run_id=run_id,
                )

                # Fazer requisição para página
                page_result = await self._search_page(
                    query_params=query_params,
                    start=current_start,
                    count=min(self._DEFAULT_RESULTS_PER_PAGE, max_results - len(all_results)),
                    run_id=run_id,
                )

                if not page_result.success:
                    # Erro em qualquer página - retornar o que temos + erro
                    duration = time.time() - start_time

                    if all_results:
                        # Retornar resultados obtidos até agora
                        logger.warning(
                            "scopus_search_partial_success",
                            results_count=len(all_results),
                            error_on_page=page_count,
                            duration=duration,
                            run_id=run_id,
                        )

                        return SearchResult(
                            api_name="scopus",
                            success=True,
                            query=query_params.get("query", ""),
                            results=all_results,
                            total_count=total_count,
                            results_returned=len(all_results),
                            duration_seconds=duration,
                            run_id=run_id,
                        )
                    else:
                        # Nenhum resultado obtido
                        logger.error(
                            "scopus_search_failed",
                            error=page_result.error_message,
                            run_id=run_id,
                        )

                        return page_result

                # Extrair dados da página
                page_results = page_result.results
                if not page_results:
                    # Sem mais resultados
                    logger.info(
                        "scopus_search_no_more_results",
                        total_pages=page_count,
                        total_results=len(all_results),
                        run_id=run_id,
                    )
                    break

                # Adicionar resultados
                all_results.extend(page_results)
                total_count = page_result.total_count

                # Verificar se deve continuar (relevância)
                if not self._should_continue_pagination(page_results):
                    logger.info(
                        "scopus_search_stopped_low_relevance",
                        pages_processed=page_count,
                        results_collected=len(all_results),
                        run_id=run_id,
                    )
                    break

                # Preparar próxima página
                current_start += self._DEFAULT_RESULTS_PER_PAGE

                # Limite de resultados
                if len(all_results) >= max_results:
                    all_results = all_results[:max_results]
                    break

            duration = time.time() - start_time

            logger.info(
                "scopus_search_complete",
                pages_processed=page_count,
                results_count=len(all_results),
                total_count=total_count,
                duration=duration,
                run_id=run_id,
            )

            return SearchResult(
                api_name="scopus",
                success=True,
                query=query_params.get("query", ""),
                results=all_results,
                total_count=total_count,
                results_returned=len(all_results),
                duration_seconds=duration,
                run_id=run_id,
            )

        except Exception as exc:
            duration = time.time() - start_time

            logger.error(
                "scopus_search_error",
                error=str(exc),
                error_type=type(exc).__name__,
                pages_processed=page_count,
                run_id=run_id,
            )

            if all_results:
                # Retornar o que temos
                return SearchResult(
                    api_name="scopus",
                    success=True,
                    query=query_params.get("query", ""),
                    results=all_results,
                    total_count=total_count,
                    results_returned=len(all_results),
                    duration_seconds=duration,
                    run_id=run_id,
                )

            return SearchResult(
                api_name="scopus",
                success=False,
                query=query_params.get("query", ""),
                error_code="SEARCH_ERROR",
                error_message=str(exc),
                duration_seconds=duration,
                run_id=run_id,
            )

    async def _search_page(
        self,
        query_params: dict[str, Any],
        start: int,
        count: int,
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Executa busca de uma página com retry.

        Args:
            query_params: Parâmetros de query.
            start: Index inicial dos resultados.
            count: Tamanho desta página - sempre capado a
                _DEFAULT_RESULTS_PER_PAGE, nunca o `count` bruto vindo do
                query builder (esse reflete o TOTAL desejado, ex:
                final_top_k=100, que excede o limite por requisição do
                service level da chave de API e devolve 400 "Exceeds the
                maximum number allowed for the service level").
            run_id: ID da requisição.

        Returns:
            SearchResult da página.
        """
        retry_count = 0

        for attempt in range(self._MAX_RETRIES):
            try:
                # Preparar parâmetros
                params = query_params.copy()
                params["start"] = start
                params["count"] = count

                logger.info(
                    "scopus_page_attempt",
                    attempt=attempt + 1,
                    start=start,
                    run_id=run_id,
                )

                # Fazer requisição
                response = await self.async_client.get(
                    self._SCOPUS_API_URL,
                    params=params,
                    headers=self._get_headers(),
                    timeout=self._TIMEOUT_SECONDS,
                )

                response.raise_for_status()

                data = response.json()

                # Extrair resultados
                # Quando não há nenhum match, a Scopus não devolve "entry": []
                # - devolve "entry": [{"error": "Result set was empty"}], um
                # placeholder com 1 item. Sem filtrar isso, a paginação (que só
                # olha len(page_results) > 0) achava que sempre tinha mais uma
                # página e repetia esse mesmo placeholder por até _MAX_PAGES
                # tentativas, poluindo os resultados com itens sem título/DOI.
                search_results = data.get("search-results", {})
                raw_results = search_results.get("entry", [])
                results = [r for r in raw_results if not r.get("error")]
                total_count = search_results.get("opensearch:totalResults")

                return SearchResult(
                    api_name="scopus",
                    success=True,
                    query=params.get("query", ""),
                    results=results,
                    total_count=int(total_count) if total_count else None,
                    results_returned=len(results),
                    retry_count=retry_count,
                    run_id=run_id,
                )

            except httpx.HTTPStatusError as exc:
                retry_count = attempt

                is_retryable = exc.response.status_code in [408, 429, 500, 502, 503, 504]

                logger.warning(
                    "scopus_page_http_error",
                    status_code=exc.response.status_code,
                    attempt=attempt + 1,
                    is_retryable=is_retryable,
                    run_id=run_id,
                )

                if not is_retryable or attempt == self._MAX_RETRIES - 1:
                    return SearchResult(
                        api_name="scopus",
                        success=False,
                        query=query_params.get("query", ""),
                        error_code=f"HTTP_{exc.response.status_code}",
                        error_message=f"HTTP {exc.response.status_code}",
                        retry_count=retry_count,
                        run_id=run_id,
                    )

                await asyncio.sleep(self._RETRY_DELAY_SECONDS * (attempt + 1))

            except Exception as exc:
                logger.error(
                    "scopus_page_error",
                    error=str(exc),
                    error_type=type(exc).__name__,
                    run_id=run_id,
                )

                return SearchResult(
                    api_name="scopus",
                    success=False,
                    query=query_params.get("query", ""),
                    error_code="PAGE_ERROR",
                    error_message=str(exc),
                    retry_count=retry_count,
                    run_id=run_id,
                )

        return SearchResult(
            api_name="scopus",
            success=False,
            query=query_params.get("query", ""),
            error_code="MAX_RETRIES_EXCEEDED",
            error_message="Maximum retries exceeded",
            retry_count=self._MAX_RETRIES,
            run_id=run_id,
        )

    async def count(
        self,
        query_params: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Requisição leve (count=1) só pra ler opensearch:totalResults, sem
        paginar - usada pela busca final (ver ChatService._run_scopus_final_search)
        pra decidir range vs ano ANTES de buscar de verdade, e pra contar
        cada área de estudo via SUBJAREA(CODE) (ver
        ChatService._run_scopus_area_of_study_counts). Não faz sentido
        aplicar _extract_final_fields aqui - o único dado que importa é
        total_count, e count=1 já limita a 1 item bruto na resposta.
        """
        return await self._search_page(query_params, start=0, count=1, run_id=run_id)

    async def fetch_results_page(
        self,
        query_params: dict[str, Any],
        start: int = 0,
        count: int = _FINAL_SEARCH_PAGE_SIZE,
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Busca UMA página de até _FINAL_SEARCH_PAGE_SIZE resultados já com a
        extração enxuta da busca final (title/institutions/year, ver
        _extract_final_fields) - mesma ideia de OPSService.search_biblio_page,
        adaptada: aqui a extração roda depois da resposta bruta (a Scopus já
        devolve JSON plano, sem o parsing XML/aninhado que a OPS precisa),
        não injetada no parser via extract_json_fn/extract_xml_fn.

        Diferente de search() (usado pela probe), que pagina automaticamente
        em blocos de _DEFAULT_RESULTS_PER_PAGE (25) - aqui o chamador
        controla start/count diretamente, sem paginação automática.
        """
        result = await self._search_page(query_params, start=start, count=count, run_id=run_id)
        if not result.success:
            return result
        return replace(result, results=[_extract_final_fields(entry) for entry in result.results])

    @staticmethod
    def _should_continue_pagination(page_results: list[dict[str, Any]]) -> bool:
        """
        Verifica se deve continuar paginação baseado em relevância.

        Heurística simples: continuar se houver resultados na página.
        TODO: Implementar checks de relevância mais sofisticados

        Args:
            page_results: Resultados da página.

        Returns:
            True se deve continuar, False caso contrário.
        """
        # TODO: Implementar análise de relevância baseada em:
        # - Citation count
        # - Publication date recency
        # - Author match scores
        # - Keyword match strength

        return len(page_results) > 0

    def _get_headers(self) -> dict[str, str]:
        """
        Constrói headers para requisição Scopus.

        Returns:
            Dicionário com headers HTTP.
        """
        headers = {
            "Accept": "application/json",
            "X-ELS-ResourceVersion": "allest",
        }

        if self.api_key:
            headers["X-ELS-APIKey"] = self.api_key

        return headers

    async def close(self) -> None:
        """
        Fecha cliente httpx.
        """
        await self.async_client.aclose()

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
