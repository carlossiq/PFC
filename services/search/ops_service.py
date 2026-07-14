"""
Search service for European Patent Office (OPS) API with OAuth2.
"""

import asyncio
import json
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx

from core.config import settings
from core.logging import get_logger
from services.search.base import SearchError, SearchResult
from services.search.ops_token_manager import ops_token_manager

logger = get_logger(__name__)


class OPSToken:
    """
    Gerencia token OAuth2 do OPS.

    Armazena token e verifica expiração para auto-renovação.
    """

    def __init__(self, access_token: str, expires_in: int) -> None:
        """
        Inicializa com token de acesso.

        Args:
            access_token: Token de acesso OAuth2.
            expires_in: Tempo de expiração em segundos.
        """
        self.access_token = access_token
        self.expires_in = expires_in
        self.created_at = datetime.utcnow()

    @property
    def expiration_time(self) -> datetime:
        """
        Retorna data/hora de expiração.

        Returns:
            Datetime de expiração do token.
        """
        return self.created_at + timedelta(seconds=self.expires_in)

    def is_expired(self, buffer_seconds: int = 60) -> bool:
        """
        Verifica se token está expirado com buffer.

        Args:
            buffer_seconds: Segundos antes da expiração real para renovar.

        Returns:
            True se token está ou está prestes a expirar.
        """
        expiration_with_buffer = self.expiration_time - timedelta(seconds=buffer_seconds)
        return datetime.utcnow() >= expiration_with_buffer

    def to_dict(self) -> dict[str, Any]:
        """
        Converte token para dicionário.

        Returns:
            Dicionário com dados do token.
        """
        return {
            "access_token": self.access_token,
            "expires_in": self.expires_in,
            "created_at": self.created_at.isoformat(),
            "expiration_time": self.expiration_time.isoformat(),
        }


def _local_name(tag: str) -> str:
    """
    Extrai o nome local de uma tag, ignorando namespace.

    Args:
        tag: Tag completo (e.g., "{http://example.com}element" ou "element")

    Returns:
        Nome local da tag (e.g., "element")
    """
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _find_first_by_local_name(element: ET.Element, local_name: str) -> Optional[ET.Element]:
    """
    Encontra primeiro elemento filho por nome local, ignorando namespace.

    Args:
        element: Elemento pai
        local_name: Nome local da tag (sem namespace)

    Returns:
        Elemento encontrado ou None
    """
    for child in element:
        if _local_name(child.tag) == local_name:
            return child
    return None


def _extract_party_names_xml(party_elems: list[ET.Element], name_wrapper_tag: str) -> list[str]:
    """
    Extrai nomes de uma lista de elementos <applicant>/<inventor> da OPS
    (formato XML) - ver OPSService._extract_party_names (versão JSON) pro
    mesmo problema: cada parte aparece duas vezes (data-format "original" e
    "epodoc") e o nome vem aninhado num wrapper (<applicant-name>/
    <inventor-name>), não direto no elemento da parte.

    Args:
        party_elems: Elementos <applicant> ou <inventor> já encontrados.
        name_wrapper_tag: "applicant-name" ou "inventor-name".

    Returns:
        Lista de nomes, sem duplicar data-format.
    """
    names = []
    for party_elem in party_elems:
        if party_elem.attrib.get("data-format") not in (None, "original"):
            continue
        name_wrapper = _find_first_by_local_name(party_elem, name_wrapper_tag)
        name_elem = _find_first_by_local_name(name_wrapper, "name") if name_wrapper is not None else None
        if name_elem is not None and name_elem.text:
            names.append(name_elem.text)
    return names


def _find_all_by_local_name(element: ET.Element, local_name: str) -> list[ET.Element]:
    """
    Encontra todos elementos descendentes por nome local, ignorando namespace.

    Args:
        element: Elemento para buscar dentro
        local_name: Nome local da tag (sem namespace)

    Returns:
        Lista de elementos encontrados
    """
    results = []
    for descendant in element.iter():
        if _local_name(descendant.tag) == local_name:
            results.append(descendant)

    if len(results) == 0 or local_name in ["exchange-document", "document-id"]:
        logger.info(
            "find_all_by_local_name",
            local_name=local_name,
            count=len(results),
        )

    return results


class OPSService:
    """
    Serviço de busca na API European Patent Office (OPS).

    Gerencia autenticação OAuth2, requisições CQL e tratamento
    de erros com retry logic.
    """

    # Configurações
    _OPS_API_URL = "https://ops.epo.org/3.2/rest-services"
    _OPS_TOKEN_URL = "https://ops.epo.org/auth/accesstoken"
    _MAX_RETRIES = 3
    _RETRY_DELAY_SECONDS = 2
    _TIMEOUT_SECONDS = 60

    def __init__(
        self,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
    ) -> None:
        """
        Inicializa o serviço OPS.

        Args:
            consumer_key: Consumer key OAuth2 (se None, tenta config).
            consumer_secret: Consumer secret OAuth2 (se None, tenta config).
        """
        self.consumer_key = consumer_key or getattr(settings, "ops_consumer_key", None)
        self.consumer_secret = consumer_secret or getattr(settings, "ops_consumer_secret", None)
        self.token: Optional[OPSToken] = None
        self.async_client = httpx.AsyncClient(timeout=self._TIMEOUT_SECONDS)
        self.sync_client = httpx.Client(timeout=self._TIMEOUT_SECONDS)

    async def search(
        self,
        query: dict[str, Any],
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Executa busca em OPS com CQL.

        Args:
            query: Query dict com 'query' (CQL string) e outros params.
            run_id: ID único da requisição para logging.

        Returns:
            SearchResult com dados de sucesso ou erro.
        """
        start_time = time.time()

        try:
            # Garantir token válido
            await self._ensure_valid_token(run_id)

            if not self.token:
                return SearchResult(
                    api_name="ops",
                    success=False,
                    query=query.get("query", ""),
                    error_code="NO_TOKEN",
                    error_message="Failed to obtain OPS authentication token",
                    duration_seconds=time.time() - start_time,
                    run_id=run_id,
                )

            # Executar busca com retry
            return await self._search_with_retry(query, run_id, start_time)

        except Exception as exc:
            duration = time.time() - start_time

            logger.error(
                "ops_search_error",
                error=str(exc),
                error_type=type(exc).__name__,
                run_id=run_id,
            )

            return SearchResult(
                api_name="ops",
                success=False,
                query=query.get("query", ""),
                error_code="UNKNOWN_ERROR",
                error_message=str(exc),
                duration_seconds=duration,
                run_id=run_id,
            )

    async def search_with_abstracts(
        self,
        query: dict[str, Any],
        top_k: int = 10,
        run_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Executa busca em OPS usando endpoint /search/biblio que já retorna dados bibliográficos completos.

        Muito mais eficiente que search + enrich, pois uma única requisição
        retorna todos os dados necessários (abstracts, títulos, etc).

        Args:
            query: Query dict com 'query' (CQL string).
            top_k: Número de resultados com abstracts a retornar (1-100).
            run_id: ID único da requisição para logging.

        Returns:
            SearchResult com dados de sucesso ou erro (incluindo abstracts).
        """
        start_time = time.time()

        try:
            # Garantir token válido
            await self._ensure_valid_token(run_id)

            if not self.token:
                return SearchResult(
                    api_name="ops",
                    success=False,
                    query=query.get("query", ""),
                    error_code="NO_TOKEN",
                    error_message="Failed to obtain OPS authentication token",
                    duration_seconds=time.time() - start_time,
                    run_id=run_id,
                )

            # Executar busca com retry usando endpoint /search/biblio
            return await self._search_abstract_with_retry(query, top_k, run_id, start_time)

        except Exception as exc:
            duration = time.time() - start_time

            logger.error(
                "ops_search_abstract_error",
                error=str(exc),
                error_type=type(exc).__name__,
                run_id=run_id,
            )

            return SearchResult(
                api_name="ops",
                success=False,
                query=query.get("query", ""),
                error_code="UNKNOWN_ERROR",
                error_message=str(exc),
                duration_seconds=duration,
                run_id=run_id,
            )

    async def _ensure_valid_token(self, run_id: Optional[str] = None) -> None:
        """
        Garante que token OAuth2 válido está disponível.

        Usa token manager centralizado para evitar renovações desnecessárias.

        Args:
            run_id: ID único da requisição para logging.
        """
        token = await ops_token_manager.get_valid_token()
        if token:
            # Atualizar referência local se token foi renovado
            self.token = ops_token_manager.token
        else:
            logger.error("ops_token_unavailable", run_id=run_id)
            self.token = None

    async def _get_new_token(self, run_id: Optional[str] = None) -> None:
        """
        Obtém novo token OAuth2 do OPS.

        Usa grant_type=client_credentials com autenticação Basic Auth.

        Args:
            run_id: ID único da requisição para logging.

        Raises:
            Exception: Se falhar em obter token.
        """
        if not self.consumer_key or not self.consumer_secret:
            raise ValueError("OPS consumer key and secret are required")

        try:
            # OPS espera application/x-www-form-urlencoded com grant_type=client_credentials
            response = await self.async_client.post(
                self._OPS_TOKEN_URL,
                auth=(self.consumer_key, self.consumer_secret),
                data={"grant_type": "client_credentials"},
                timeout=self._TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            # Extrair token (resposta é JSON)
            data = response.json()

            if "access_token" in data:
                access_token = data["access_token"]
                # Usar expires_in da resposta (em segundos) ou fallback para 1 hora
                expires_in = int(data.get("expires_in", 3600))

                self.token = OPSToken(access_token, expires_in)

                logger.info(
                    "ops_token_obtained",
                    expires_at=self.token.expiration_time.isoformat(),
                    token_type=data.get("token_type"),
                    run_id=run_id,
                )
            else:
                raise ValueError(f"No access_token in response: {data}")

        except Exception as exc:
            logger.error(
                "ops_token_error",
                error=str(exc),
                error_type=type(exc).__name__,
                run_id=run_id,
            )
            raise

    async def _search_with_retry(
        self,
        query: dict[str, Any],
        run_id: Optional[str],
        start_time: float,
    ) -> SearchResult:
        """
        Executa busca com retry logic.

        Args:
            query: Query dict.
            run_id: ID da requisição.
            start_time: Timestamp de início.

        Returns:
            SearchResult com dados ou erro.
        """
        retry_count = 0

        for attempt in range(self._MAX_RETRIES):
            try:
                logger.info(
                    "ops_search_attempt",
                    attempt=attempt + 1,
                    run_id=run_id,
                )

                # Construir URL
                url = f"{self._OPS_API_URL}/published-data/search"
                cql_query = query.get("query", "")

                # Fazer requisição
                # OPS bibliographic search: enviar CQL via parâmetro 'q'
                # Usar Accept header para negociar formato, não enviar "format" como parâmetro
                response = await self.async_client.get(
                    url,
                    params={"q": cql_query},
                    headers=self._get_headers(),
                    timeout=self._TIMEOUT_SECONDS,
                )

                response.raise_for_status()

                # Parsear resposta (pode ser JSON ou XML)
                # Tentar como JSON primeiro
                try:
                    data = response.json()
                    # Extrair do formato JSON-converted-from-XML
                    world_patent_data = data.get("ops:world-patent-data", {})
                    biblio_search = world_patent_data.get("ops:biblio-search", {})
                    total_count = biblio_search.get("@total-result-count")
                    if isinstance(total_count, str):
                        total_count = int(total_count)

                    # Extrair resultados — cada ops:publication-reference vira um item separado
                    search_result_raw = world_patent_data.get("ops:biblio-search", {}).get("ops:search-result", {})
                    if isinstance(search_result_raw, list):
                        search_result_raw = search_result_raw[0] if search_result_raw else {}

                    pub_refs = search_result_raw.get("ops:publication-reference", [])
                    if not isinstance(pub_refs, list):
                        pub_refs = [pub_refs] if pub_refs else []

                    results = [{"ops:publication-reference": ref} for ref in pub_refs]
                except (json.JSONDecodeError, ValueError):
                    # Se não for JSON, tentar XML
                    root = ET.fromstring(response.text)

                    biblio_search = root.find(
                        ".//{http://ops.epo.org}biblio-search"
                    )
                    total_count_str = biblio_search.get("total-result-count") if biblio_search is not None else None
                    total_count = int(total_count_str) if total_count_str else None

                    results = []
                    search_result = root.find(
                        ".//{http://ops.epo.org}search-result"
                    )
                    if search_result is not None:
                        for pub_ref in search_result.findall(
                            ".//{http://ops.epo.org}publication-reference"
                        ):
                            results.append(ET.tostring(pub_ref, encoding="unicode"))

                duration = time.time() - start_time

                logger.info(
                    "ops_search_success",
                    results_count=len(results),
                    total_count=total_count,
                    duration=duration,
                    run_id=run_id,
                )

                return SearchResult(
                    api_name="ops",
                    success=True,
                    query=cql_query,
                    results=results,
                    total_count=total_count,
                    results_returned=len(results),
                    retry_count=retry_count,
                    duration_seconds=duration,
                    run_id=run_id,
                )

            except httpx.HTTPStatusError as exc:
                retry_count = attempt
                duration = time.time() - start_time

                is_retryable = exc.response.status_code in [408, 429, 500, 502, 503, 504]

                logger.warning(
                    "ops_search_http_error",
                    status_code=exc.response.status_code,
                    attempt=attempt + 1,
                    is_retryable=is_retryable,
                    response_text=exc.response.text[:200],
                    run_id=run_id,
                )

                if not is_retryable or attempt == self._MAX_RETRIES - 1:
                    return SearchResult(
                        api_name="ops",
                        success=False,
                        query=query.get("query", ""),
                        error_code=f"HTTP_{exc.response.status_code}",
                        error_message=f"HTTP {exc.response.status_code}",
                        retry_count=retry_count,
                        duration_seconds=duration,
                        run_id=run_id,
                    )

                await asyncio.sleep(self._RETRY_DELAY_SECONDS * (attempt + 1))

            except httpx.TimeoutException as exc:
                retry_count = attempt
                duration = time.time() - start_time

                logger.warning(
                    "ops_search_timeout",
                    timeout_seconds=self._TIMEOUT_SECONDS,
                    attempt=attempt + 1,
                    error_type=type(exc).__name__,
                    run_id=run_id,
                )

                if attempt == self._MAX_RETRIES - 1:
                    return SearchResult(
                        api_name="ops",
                        success=False,
                        query=query.get("query", ""),
                        error_code="TIMEOUT",
                        error_message=f"Request timeout after {self._TIMEOUT_SECONDS}s (attempt {attempt + 1}/{self._MAX_RETRIES})",
                        retry_count=retry_count,
                        duration_seconds=duration,
                        run_id=run_id,
                    )

                await asyncio.sleep(self._RETRY_DELAY_SECONDS * (attempt + 1))

            except Exception as exc:
                duration = time.time() - start_time

                error_msg = str(exc) if str(exc) else f"{type(exc).__name__}: connection error"

                logger.error(
                    "ops_search_error",
                    error=error_msg,
                    error_type=type(exc).__name__,
                    response_text=response.text[:200] if 'response' in locals() else "N/A",
                    run_id=run_id,
                )

                return SearchResult(
                    api_name="ops",
                    success=False,
                    query=query.get("query", ""),
                    error_code="SEARCH_ERROR",
                    error_message=error_msg,
                    duration_seconds=duration,
                    run_id=run_id,
                )

        # Fallback
        duration = time.time() - start_time
        return SearchResult(
            api_name="ops",
            success=False,
            query=query.get("query", ""),
            error_code="MAX_RETRIES_EXCEEDED",
            error_message="Maximum retries exceeded",
            retry_count=self._MAX_RETRIES,
            duration_seconds=duration,
            run_id=run_id,
        )

    def _extract_biblio_fields_xml(self, exchange_doc_elem) -> dict[str, Any]:
        """
        Extrai campos bibliográficos estruturados de um elemento XML exchange-document.

        Versão para XML parsing (fallback).

        Args:
            exchange_doc_elem: Elemento XML do exchange-document

        Returns:
            Dict com campos estruturados
        """
        result = {
            # Priority 1: Essential fields
            "family_id": exchange_doc_elem.attrib.get("family-id"),
            "invention_title": None,
            "abstract": None,
            "publication_date": None,
            "priority_date": None,
            "applicants": [],
            "ipc_classifications": [],
            "cpc_classifications": [],
            # Priority 2: Important fields
            "country": None,
            "inventors": [],
            "docdb_id": None,
            # Priority 3: Complementary fields
            "kind": None,
            "application_reference": None,
        }

        try:
            # Extract invention-title (prefer English)
            invention_titles = _find_all_by_local_name(exchange_doc_elem, "invention-title")
            for title_elem in invention_titles:
                lang = title_elem.attrib.get("lang", "")
                title_text = title_elem.text or ""
                if lang == "en":
                    result["invention_title"] = title_text
                    break
                elif result["invention_title"] is None:
                    result["invention_title"] = title_text

            # Extract abstract (prefer English)
            abstract_elems = _find_all_by_local_name(exchange_doc_elem, "abstract")
            for abstract_elem in abstract_elems:
                lang = abstract_elem.attrib.get("lang")
                p_elems = _find_all_by_local_name(abstract_elem, "p")
                paragraphs = [p.text.strip() for p in p_elems if p.text]
                text = " ".join(paragraphs).strip()
                if text:
                    if lang == "en":
                        result["abstract"] = text
                        break
                    elif result["abstract"] is None:
                        result["abstract"] = text

            # Extract publication data from document-id
            all_doc_ids = _find_all_by_local_name(exchange_doc_elem, "document-id")
            for doc_id_elem in all_doc_ids:
                if doc_id_elem.get("document-id-type") == "docdb":
                    country_elem = _find_first_by_local_name(doc_id_elem, "country")
                    doc_number_elem = _find_first_by_local_name(doc_id_elem, "doc-number")
                    kind_elem = _find_first_by_local_name(doc_id_elem, "kind")
                    date_elem = _find_first_by_local_name(doc_id_elem, "date")

                    country = country_elem.text if country_elem is not None else None
                    doc_number = doc_number_elem.text if doc_number_elem is not None else None
                    kind = kind_elem.text if kind_elem is not None else None
                    publication_date = date_elem.text if date_elem is not None else None

                    result["country"] = country
                    result["kind"] = kind
                    result["publication_date"] = publication_date
                    result["docdb_id"] = f"{country}.{doc_number}.{kind}" if all([country, doc_number, kind]) else None
                    break

            # Extract applicants
            applicants_container = _find_first_by_local_name(exchange_doc_elem, "applicants")
            if applicants_container is not None:
                applicant_elems = _find_all_by_local_name(applicants_container, "applicant")
                result["applicants"] = _extract_party_names_xml(applicant_elems, "applicant-name")

            # Extract inventors
            inventors_container = _find_first_by_local_name(exchange_doc_elem, "inventors")
            if inventors_container is not None:
                inventor_elems = _find_all_by_local_name(inventors_container, "inventor")
                result["inventors"] = _extract_party_names_xml(inventor_elems, "inventor-name")

            # Extract IPC classifications
            ipc_container = _find_first_by_local_name(exchange_doc_elem, "classifications-ipcr")
            if ipc_container is not None:
                ipc_elems = _find_all_by_local_name(ipc_container, "classification-ipcr")
                for ipc_elem in ipc_elems:
                    text_elem = _find_first_by_local_name(ipc_elem, "text")
                    if text_elem is not None and text_elem.text:
                        result["ipc_classifications"].append(text_elem.text)

            # Extract CPC classifications
            cpc_container = _find_first_by_local_name(exchange_doc_elem, "classifications-cpc")
            if cpc_container is not None:
                cpc_elems = _find_all_by_local_name(cpc_container, "classification-cpc")
                for cpc_elem in cpc_elems:
                    text_elem = _find_first_by_local_name(cpc_elem, "text")
                    if text_elem is not None and text_elem.text:
                        result["cpc_classifications"].append(text_elem.text)

        except Exception:
            # Se há erro ao processar, retorna o que conseguiu extrair
            pass

        return result

    @staticmethod
    def _extract_party_names(entries: Any, name_key: str) -> list[str]:
        """
        Extrai nomes de uma lista de applicant/inventor da OPS (formato JSON).

        Cada parte aparece duas vezes na resposta - uma com "@data-format":
        "original" (nome legível, ex: "Shen, Hai Jun") e outra "epodoc" (nome
        normalizado/abreviado, ex: "SHEN HAI JUN [CN]") - sem filtrar isso a
        mesma pessoa/empresa apareceria duplicada. O nome também vem aninhado
        sob um wrapper ("applicant-name"/"inventor-name", o `name_key`), não
        direto no dict da parte.

        Args:
            entries: Valor de parties["applicants"]["applicant"] ou
                parties["inventors"]["inventor"] (dict único ou lista).
            name_key: "applicant-name" ou "inventor-name".

        Returns:
            Lista de nomes, sem duplicar data-format.
        """
        if not isinstance(entries, list):
            entries = [entries] if entries else []

        names = []
        for entry in entries:
            if not isinstance(entry, dict):
                if entry:
                    names.append(str(entry))
                continue
            if entry.get("@data-format") not in (None, "original"):
                continue
            name_wrapper = entry.get(name_key, {})
            name = name_wrapper.get("name", {}).get("$") if isinstance(name_wrapper, dict) else None
            if name:
                names.append(name)
        return names

    def _extract_biblio_fields(self, exchange_doc: dict) -> dict[str, Any]:
        """
        Extrai campos bibliográficos estruturados do exchange-document.

        Retorna apenas campos configurados (sem raw data).

        Args:
            exchange_doc: Documento do exchange-documents

        Returns:
            Dict com campos estruturados
        """
        result = {
            # Priority 1: Essential fields
            "family_id": exchange_doc.get("@family-id"),
            "invention_title": None,
            "abstract": None,
            "publication_date": None,
            "priority_date": None,
            "applicants": [],
            "ipc_classifications": [],
            "cpc_classifications": [],
            # Priority 2: Important fields
            "country": None,
            "inventors": [],
            "docdb_id": None,
            # Priority 3: Complementary fields
            "kind": None,
            "application_reference": None,
        }

        try:
            biblio_data = exchange_doc.get("bibliographic-data", {})

            # Extract invention-title (prefer English)
            invention_titles = biblio_data.get("invention-title", [])
            if not isinstance(invention_titles, list):
                invention_titles = [invention_titles] if invention_titles else []
            for title_item in invention_titles:
                if isinstance(title_item, dict):
                    lang = title_item.get("@lang", "")
                    title_text = title_item.get("$", "")
                    if lang == "en":
                        result["invention_title"] = title_text
                        break
                    elif result["invention_title"] is None:
                        result["invention_title"] = title_text

            # Extract abstract (prefer English)
            abstract_elems = exchange_doc.get("abstract", [])
            if not isinstance(abstract_elems, list):
                abstract_elems = [abstract_elems] if abstract_elems else []
            for abstract_elem in abstract_elems:
                lang = abstract_elem.get("@lang")
                p_elems = abstract_elem.get("p", [])
                if not isinstance(p_elems, list):
                    p_elems = [p_elems] if p_elems else []
                paragraphs = []
                for p_elem in p_elems:
                    if isinstance(p_elem, dict):
                        text = p_elem.get("$", "")
                    else:
                        text = str(p_elem)
                    if text:
                        paragraphs.append(text.strip())
                text = " ".join(paragraphs).strip()
                if text:
                    if lang == "en":
                        result["abstract"] = text
                        break
                    elif result["abstract"] is None:
                        result["abstract"] = text

            # Extract publication-reference data
            pub_ref = biblio_data.get("publication-reference", {})
            doc_ids = pub_ref.get("document-id", [])
            if not isinstance(doc_ids, list):
                doc_ids = [doc_ids] if doc_ids else []

            for doc_id in doc_ids:
                if doc_id.get("@document-id-type") == "docdb":
                    country = doc_id.get("country", {}).get("$")
                    doc_number = doc_id.get("doc-number", {}).get("$")
                    kind = doc_id.get("kind", {}).get("$")
                    publication_date = doc_id.get("date", {}).get("$")

                    result["country"] = country
                    result["kind"] = kind
                    result["publication_date"] = publication_date
                    result["docdb_id"] = f"{country}.{doc_number}.{kind}" if all([country, doc_number, kind]) else None
                    break

            # Extract priority-reference
            priority_ref = biblio_data.get("priority-reference", {})
            if priority_ref:
                # Can be a single dict or list
                if isinstance(priority_ref, list):
                    priority_ref = priority_ref[0] if priority_ref else {}
                doc_id = priority_ref.get("document-id", {})
                if isinstance(doc_id, list):
                    doc_id = doc_id[0] if doc_id else {}
                priority_date = doc_id.get("date", {}).get("$") if isinstance(doc_id, dict) else None
                result["priority_date"] = priority_date

            # Extract applicants/inventors (parties.applicants.applicant / parties.inventors.inventor)
            parties = biblio_data.get("parties", {})
            result["applicants"] = self._extract_party_names(
                parties.get("applicants", {}).get("applicant", []), "applicant-name"
            )
            result["inventors"] = self._extract_party_names(
                parties.get("inventors", {}).get("inventor", []), "inventor-name"
            )

            # Extract IPC classifications
            classifications = biblio_data.get("classifications-ipcr", {})
            if classifications:
                ipc_elems = classifications.get("classification-ipcr", [])
                if not isinstance(ipc_elems, list):
                    ipc_elems = [ipc_elems] if ipc_elems else []
                for ipc_elem in ipc_elems:
                    if isinstance(ipc_elem, dict):
                        text = ipc_elem.get("text", {}).get("$") if isinstance(ipc_elem.get("text"), dict) else ipc_elem.get("text")
                        if text:
                            result["ipc_classifications"].append(text)

            # Extract CPC classifications
            cpc_class = biblio_data.get("classifications-cpc", {})
            if cpc_class:
                cpc_elems = cpc_class.get("classification-cpc", [])
                if not isinstance(cpc_elems, list):
                    cpc_elems = [cpc_elems] if cpc_elems else []
                for cpc_elem in cpc_elems:
                    if isinstance(cpc_elem, dict):
                        text = cpc_elem.get("text", {}).get("$") if isinstance(cpc_elem.get("text"), dict) else cpc_elem.get("text")
                        if text:
                            result["cpc_classifications"].append(text)

            # Extract application-reference
            app_ref = biblio_data.get("application-reference", {})
            if app_ref:
                if isinstance(app_ref, list):
                    app_ref = app_ref[0] if app_ref else {}
                doc_id = app_ref.get("document-id", {})
                if isinstance(doc_id, list):
                    doc_id = doc_id[0] if doc_id else {}
                country = doc_id.get("country", {}).get("$") if isinstance(doc_id, dict) else None
                doc_number = doc_id.get("doc-number", {}).get("$") if isinstance(doc_id, dict) else None
                kind = doc_id.get("kind", {}).get("$") if isinstance(doc_id, dict) else None
                if country and doc_number:
                    result["application_reference"] = f"{country}{doc_number}" + (f".{kind}" if kind else "")

        except Exception:
            # Se há erro ao processar, retorna o que conseguiu extrair
            pass

        return result

    async def _search_abstract_with_retry(
        self,
        query: dict[str, Any],
        top_k: int,
        run_id: Optional[str],
        start_time: float,
    ) -> SearchResult:
        """
        Executa busca no endpoint /search/biblio com retry logic.

        Este endpoint retorna resultados já com dados bibliográficos (abstracts, títulos, etc),
        eliminando a necessidade de enriquecimento posterior. Usa header X-OPS-Range para controlar quantos.

        Args:
            query: Query dict com 'query' (CQL string).
            top_k: Número de resultados a retornar (1-100).
            run_id: ID da requisição para logging.
            start_time: Timestamp de início.

        Returns:
            SearchResult com dados ou erro.
        """
        retry_count = 0

        for attempt in range(self._MAX_RETRIES):
            try:
                logger.info(
                    "ops_search_abstract_attempt",
                    attempt=attempt + 1,
                    top_k=top_k,
                    run_id=run_id,
                )

                # Construir URL com /search/biblio em vez de /search
                url = f"{self._OPS_API_URL}/published-data/search/biblio"
                cql_query = query.get("query", "")

                # Header X-OPS-Range controla quantos resultados retornar
                # Formato: "1-{top_k}"
                headers = self._get_headers()
                headers["X-OPS-Range"] = f"1-{top_k}"

                response = await self.async_client.get(
                    url,
                    params={"q": cql_query},
                    headers=headers,
                    timeout=self._TIMEOUT_SECONDS,
                )

                response.raise_for_status()

                # Parsear resposta (XML ou JSON)
                results = []
                total_count = None

                try:
                    # Tentar JSON primeiro (OPS retorna JSON serializado de XML)
                    data = response.json()

                    # Parser para JSON serializado de XML do OPS
                    world_patent_data = data.get("ops:world-patent-data", {})
                    biblio_search = world_patent_data.get("ops:biblio-search", {})

                    # Extrair total count
                    total_count_str = biblio_search.get("@total-result-count")
                    if total_count_str:
                        total_count = int(total_count_str)

                    # Extrair search-result que contém os documentos
                    search_result = biblio_search.get("ops:search-result", {})

                    # search-result contém exchange-documents (pode ser list ou dict)
                    exchange_documents_container = search_result.get("exchange-documents", [])

                    if not isinstance(exchange_documents_container, list):
                        exchange_documents_container = [exchange_documents_container] if exchange_documents_container else []

                    results = []

                    for container in exchange_documents_container:
                        # Cada container tem um exchange-document dentro
                        exchange_doc = container.get("exchange-document", {})

                        if not exchange_doc:
                            continue

                        # Extrair campos estruturados usando helper
                        result = self._extract_biblio_fields(exchange_doc)
                        results.append(result)

                except (json.JSONDecodeError, ValueError) as json_error:
                    # Se JSON falhar, tentar como XML
                    logger.info("ops_search_abstract_response_format", format="xml_fallback", json_error=str(json_error))

                    try:
                        root = ET.fromstring(response.text)

                        # Diagnóstico detalhado
                        content_type = response.headers.get("content-type", "unknown")
                        unique_tags = set()
                        total_elements = 0
                        for elem in root.iter():
                            total_elements += 1
                            unique_tags.add(_local_name(elem.tag))

                        logger.info(
                            "ops_search_abstract_xml_root",
                            root_tag=root.tag,
                            root_local_name=_local_name(root.tag),
                            response_length=len(response.text),
                            content_type=content_type,
                            total_elements=total_elements,
                            response_sample=response.text[:1000],
                            unique_tags_found=sorted(list(unique_tags))[:10],
                        )

                        # Extrair total count (ignorando namespace)
                        biblio_search_elems = _find_all_by_local_name(root, "biblio-search")
                        total_count = None
                        if biblio_search_elems:
                            biblio_search = biblio_search_elems[0]
                            total_count_str = biblio_search.get("total-result-count")
                            total_count = int(total_count_str) if total_count_str else None
                            logger.info(
                                "ops_search_abstract_total_count",
                                total_count=total_count,
                            )

                        # Buscar todos exchange-document (ignorando namespace)
                        exchange_documents = _find_all_by_local_name(root, "exchange-document")

                        logger.info(
                            "ops_search_abstract_exchange_documents_found",
                            count=len(exchange_documents),
                        )

                        results = []

                        for idx, exchange_doc in enumerate(exchange_documents):
                            # Extrair campos estruturados usando helper XML
                            result = self._extract_biblio_fields_xml(exchange_doc)
                            results.append(result)

                        logger.info(
                            "ops_search_abstract_xml_parsed",
                            exchange_documents_found=len(exchange_documents),
                            results_count=len(results),
                            total_count=total_count,
                        )

                    except ET.ParseError as exc:
                        logger.error(
                            "ops_search_abstract_xml_parse_error",
                            error=str(exc),
                            response_sample=response.text[:500],
                        )
                        raise

                duration = time.time() - start_time

                logger.info(
                    "ops_search_abstract_success",
                    results_count=len(results),
                    total_count=total_count,
                    duration=duration,
                    run_id=run_id,
                )

                return SearchResult(
                    api_name="ops",
                    success=True,
                    query=cql_query,
                    results=results,
                    total_count=total_count,
                    results_returned=len(results),
                    retry_count=retry_count,
                    duration_seconds=duration,
                    run_id=run_id,
                )

            except httpx.HTTPStatusError as exc:
                retry_count = attempt
                duration = time.time() - start_time

                is_retryable = exc.response.status_code in [408, 429, 500, 502, 503, 504]

                logger.warning(
                    "ops_search_abstract_http_error",
                    status_code=exc.response.status_code,
                    attempt=attempt + 1,
                    is_retryable=is_retryable,
                    response_text=exc.response.text[:200],
                    run_id=run_id,
                )

                if not is_retryable or attempt == self._MAX_RETRIES - 1:
                    return SearchResult(
                        api_name="ops",
                        success=False,
                        query=query.get("query", ""),
                        error_code=f"HTTP_{exc.response.status_code}",
                        error_message=f"HTTP {exc.response.status_code}",
                        retry_count=retry_count,
                        duration_seconds=duration,
                        run_id=run_id,
                    )

                await asyncio.sleep(self._RETRY_DELAY_SECONDS * (attempt + 1))

            except httpx.TimeoutException as exc:
                retry_count = attempt
                duration = time.time() - start_time

                logger.warning(
                    "ops_search_abstract_timeout",
                    timeout_seconds=self._TIMEOUT_SECONDS,
                    attempt=attempt + 1,
                    run_id=run_id,
                )

                if attempt == self._MAX_RETRIES - 1:
                    return SearchResult(
                        api_name="ops",
                        success=False,
                        query=query.get("query", ""),
                        error_code="TIMEOUT",
                        error_message=f"Request timeout after {self._TIMEOUT_SECONDS}s (attempt {attempt + 1}/{self._MAX_RETRIES})",
                        retry_count=retry_count,
                        duration_seconds=duration,
                        run_id=run_id,
                    )

                await asyncio.sleep(self._RETRY_DELAY_SECONDS * (attempt + 1))

            except Exception as exc:
                duration = time.time() - start_time

                error_msg = str(exc) if str(exc) else f"{type(exc).__name__}: connection error"

                logger.error(
                    "ops_search_abstract_error",
                    error=error_msg,
                    error_type=type(exc).__name__,
                    response_text=response.text[:200] if 'response' in locals() else "N/A",
                    run_id=run_id,
                )

                return SearchResult(
                    api_name="ops",
                    success=False,
                    query=query.get("query", ""),
                    error_code="SEARCH_ERROR",
                    error_message=error_msg,
                    duration_seconds=duration,
                    run_id=run_id,
                )

        # Fallback
        duration = time.time() - start_time
        return SearchResult(
            api_name="ops",
            success=False,
            query=query.get("query", ""),
            error_code="MAX_RETRIES_EXCEEDED",
            error_message="Maximum retries exceeded",
            retry_count=self._MAX_RETRIES,
            duration_seconds=duration,
            run_id=run_id,
        )

    def _get_headers(self) -> dict[str, str]:
        """
        Constrói headers para requisição OPS.

        OPS espera: Authorization: Bearer <token>
        Accept: application/json (API responde com JSON corretamente)

        Returns:
            Dicionário com headers HTTP.
        """
        return {
            "Authorization": f"Bearer {self.token.access_token}" if self.token else "",
            "Accept": "application/json",
        }

    async def _fetch_biblio_data(
        self,
        country: str,
        doc_number: str,
        kind: str,
        run_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Fetch bibliographic data for a single patent using /biblio endpoint.

        Uses OPS API v3.2 with epodoc format for reliable data retrieval.

        Args:
            country: Country code (e.g., "US", "EP", "CN")
            doc_number: Document number (e.g., "12548680")
            kind: Kind code (e.g., "B1", "A1")
            run_id: ID for logging

        Returns:
            Dict with bibliographic data or None if failed
        """
        try:
            # Construct publication number in docdb format: country.doc-number.kind
            publication_number_docdb = f"{country}.{doc_number}.{kind}"

            # URL: Use API v3.2 with docdb format (not epodoc)
            # Format: /3.2/rest-services/published-data/publication/docdb/{country}.{doc-number}.{kind}/biblio
            url = f"https://ops.epo.org/3.2/rest-services/published-data/publication/docdb/{publication_number_docdb}/biblio"

            logger.info(
                "ops_fetch_biblio",
                publication_number_docdb=publication_number_docdb,
                run_id=run_id,
            )

            response = await self.async_client.get(
                url,
                headers=self._get_headers(),
                timeout=self._TIMEOUT_SECONDS,
            )

            response.raise_for_status()

            # Parse response
            data = response.json()
            return data

        except Exception as exc:
            error_msg = str(exc) if str(exc) else f"{type(exc).__name__}: unknown error"

            logger.error(
                "ops_fetch_biblio_failed",
                publication_number=f"{country}{doc_number}.{kind}",
                url=url,
                error=error_msg,
                error_type=type(exc).__name__,
                response_status=response.status_code if 'response' in locals() else "N/A",
                response_text=response.text[:200] if 'response' in locals() else "N/A",
                run_id=run_id,
            )
            return None

    def _extract_from_biblio(self, biblio_data: dict) -> dict[str, Any]:
        """
        Extract useful bibliographic information from OPS biblio response.

        Navigates nested structure to extract: title, abstract, inventors, applicants.

        Args:
            biblio_data: Full biblio data from _fetch_biblio_data

        Returns:
            Dict with extracted fields: title, abstract, inventors, applicants
        """
        result = {
            "title": None,
            "abstract": None,
            "inventors": [],
            "applicants": [],
        }

        try:
            wpd = biblio_data.get("ops:world-patent-data", {})
            ex_docs = wpd.get("exchange-documents", {})
            ex_doc = ex_docs.get("exchange-document", {})

            # Extract title
            biblio_data_section = ex_doc.get("bibliographic-data", {})
            invention_titles = biblio_data_section.get("invention-title", [])
            if invention_titles:
                # Take English title if available, otherwise first
                for title_item in invention_titles:
                    if title_item.get("@lang") == "en" or title_item.get("@lang", "").startswith("en"):
                        result["title"] = title_item.get("$", "")
                        break
                if not result["title"] and invention_titles:
                    result["title"] = invention_titles[0].get("$", "")

            # Extract abstract
            abstracts = ex_doc.get("abstract", [])
            if abstracts:
                abstract_text = ""
                for abstract_item in abstracts:
                    if abstract_item.get("@lang") == "en":
                        # Extract paragraphs
                        p_data = abstract_item.get("p")
                        if isinstance(p_data, dict):
                            abstract_text = p_data.get("$", "")
                        elif isinstance(p_data, list):
                            abstract_text = " ".join([p.get("$", "") if isinstance(p, dict) else str(p) for p in p_data])
                        break
                result["abstract"] = abstract_text if abstract_text else None

            # Extract inventors/applicants (mesma estrutura aninhada - ver _extract_party_names)
            parties = biblio_data_section.get("parties", {})
            result["inventors"] = self._extract_party_names(
                parties.get("inventors", {}).get("inventor", []), "inventor-name"
            )
            result["applicants"] = self._extract_party_names(
                parties.get("applicants", {}).get("applicant", []), "applicant-name"
            )

        except Exception:
            pass

        return result

    async def enrich_results_with_biblio(
        self,
        results: list[dict[str, Any]],
        max_results: int = 10,
        run_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Enrich search results with bibliographic data from OPS.

        Fetches full bibliographic data (title, abstract, inventors, applicants)
        for each result to enable term extraction with KeyBERT/SBERT.

        Args:
            results: List of publication-reference dicts from search
            max_results: Maximum number of results to enrich (e.g., probe_top_k=10)
            run_id: ID for logging

        Returns:
            List of enriched result dicts with bibliographic data
        """
        enriched_results = []

        # Ensure valid token before enrichment (may have expired during search)
        await self._ensure_valid_token(run_id)

        # Only enrich up to max_results
        results_to_process = results[:max_results]

        logger.info(
            "ops_enrich_results_start",
            total_results=len(results),
            to_enrich=len(results_to_process),
            run_id=run_id,
        )

        for idx, result in enumerate(results_to_process, 1):
            try:
                # Extract publication identifiers
                # Handle both formats: direct ops:publication-reference or wrapped in "raw"
                if isinstance(result, dict):
                    if "ops:publication-reference" in result:
                        pub_ref = result.get("ops:publication-reference")
                    elif "raw" in result and isinstance(result["raw"], dict):
                        pub_ref = result["raw"].get("ops:publication-reference", result)
                    else:
                        pub_ref = result
                else:
                    pub_ref = result

                # Handle list of publication references (take the first one)
                if isinstance(pub_ref, list):
                    if not pub_ref:
                        enriched_results.append({
                            "raw": result,
                            "publication_number": None,
                            "biblio": None,
                        })
                        continue
                    pub_ref = pub_ref[0]

                # Handle JSON dict format
                if isinstance(pub_ref, dict):
                    doc_id = pub_ref.get("document-id", {})
                    if isinstance(doc_id, dict):
                        country = doc_id.get("country", {}).get("$", "")
                        doc_number = doc_id.get("doc-number", {}).get("$", "")
                        kind = doc_id.get("kind", {}).get("$", "")
                    else:
                        enriched_results.append({
                            "raw": result,
                            "publication_number": None,
                            "biblio": None,
                        })
                        continue
                else:
                    # Skip if cannot parse
                    enriched_results.append({
                        "raw": result,
                        "publication_number": None,
                        "biblio": None,
                    })
                    continue

                if not all([country, doc_number, kind]):
                    enriched_results.append({
                        "raw": result,
                        "publication_number": None,
                        "biblio": None,
                    })
                    continue

                publication_number = f"{country}{doc_number}.{kind}"

                # Fetch full bibliographic data from OPS /biblio endpoint
                biblio_data = await self._fetch_biblio_data(
                    country, doc_number, kind, run_id
                )

                # Extract structured data from biblio
                extracted_biblio = None
                if biblio_data:
                    extracted_biblio = self._extract_from_biblio(biblio_data)

                # Keep original raw data, but avoid duplication if already wrapped
                raw_to_keep = result.get("raw", result) if "raw" in result and isinstance(result.get("raw"), dict) else result

                enriched_results.append({
                    "raw": raw_to_keep,
                    "publication_number": publication_number,
                    "biblio": extracted_biblio,
                })

            except Exception:
                enriched_results.append({
                    "raw": result,
                    "publication_number": None,
                    "biblio": None,
                })

        logger.info(
            "ops_enrich_results_complete",
            total_with_biblio=sum(1 for r in enriched_results if r.get("biblio")),
            total_with_abstracts=sum(1 for r in enriched_results if (r.get("biblio") or {}).get("abstract")),
            total_with_titles=sum(1 for r in enriched_results if (r.get("biblio") or {}).get("title")),
            total_with_pub_number=sum(1 for r in enriched_results if r.get("publication_number")),
            total=len(enriched_results),
            run_id=run_id,
        )

        return enriched_results

    async def close(self) -> None:
        """
        Fecha clientes httpx (síncrono e assíncrono).
        """
        self.sync_client.close()
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
