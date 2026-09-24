import httpx
import pytest

from services.search.scopus_service import ScopusService, extract_scopus_final_fields


def test_extract_scopus_final_fields_single_affiliation_as_bare_dict():
    entry = {
        "dc:title": "Solar cells in Aarhus",
        "prism:coverDate": "2020-05-01",
        "affiliation": {"affilname": "Aarhus Universitet"},
    }

    result = extract_scopus_final_fields(entry)

    assert result == {"title": "Solar cells in Aarhus", "institutions": ["Aarhus Universitet"], "year": 2020}


def test_extract_scopus_final_fields_multiple_affiliations_as_list():
    entry = {
        "dc:title": "Cross-institution study",
        "prism:coverDate": "2019-01-15",
        "affiliation": [{"affilname": "MIT"}, {"affilname": "Stanford"}],
    }

    result = extract_scopus_final_fields(entry)

    assert result["institutions"] == ["MIT", "Stanford"]
    assert result["year"] == 2019


def test_extract_scopus_final_fields_missing_affiliation_and_date():
    entry = {"dc:title": "No metadata"}

    result = extract_scopus_final_fields(entry)

    assert result == {"title": "No metadata", "institutions": [], "year": None}


def test_extract_scopus_final_fields_ignores_affiliation_without_affilname():
    entry = {
        "dc:title": "T",
        "prism:coverDate": "2021-01-01",
        "affiliation": [{"affiliation-country": "Denmark"}, {"affilname": "Aarhus Universitet"}],
    }

    result = extract_scopus_final_fields(entry)

    assert result["institutions"] == ["Aarhus Universitet"]


# ---- novas tentativas em erro de rede ----


@pytest.mark.asyncio
async def test_search_page_retries_transient_connect_error():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("All connection attempts failed", request=request)
        return httpx.Response(200, json={"search-results": {"opensearch:totalResults": "42", "entry": []}})

    svc = ScopusService(api_key="test")
    svc._RETRY_DELAY_SECONDS = 0
    svc.async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    result = await svc.count({"query": "TITLE(x)"})

    assert result.success is True
    assert result.total_count == 42
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_search_page_reports_network_error_after_retries():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("All connection attempts failed", request=request)

    svc = ScopusService(api_key="test")
    svc._RETRY_DELAY_SECONDS = 0
    svc.async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    result = await svc.count({"query": "TITLE(x)"})

    assert result.success is False
    assert result.error_code == "NETWORK_ERROR"
