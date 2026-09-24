from typing import Optional

import pytest

from app.core.domain.types import SearchResult
from app.core.services.chat_service import ChatService
from core.config import Settings


def _svc() -> ChatService:
    return ChatService(llm_resolver=None, patent_pairs=[], scholarly_pairs=[], settings=Settings())


class FakeOpsAdapter:
    """
    Adapter fake pra OPS - simula search()/fetch_biblio_page() sem rede.

    `year_data` mapeia year -> (total, {start: items}) - total_count é
    constante pra um ano/query, igual na API real, independente de `start`;
    só os itens retornados mudam por janela (start), usado pra testar
    `iteration`.
    """

    api_name = "ops"

    def __init__(
        self,
        total_count: Optional[int],
        year_data: Optional[dict[int, tuple[int, dict[int, list[dict]]]]] = None,
        items_per_start: Optional[dict[int, list[dict]]] = None,
    ) -> None:
        self.total_count = total_count
        self.year_data = year_data or {}
        self.items_per_start = items_per_start or {}
        self.fetch_calls: list[tuple[int, int, tuple[int, int]]] = []

    async def search(self, query: dict, run_id=None) -> SearchResult:
        q = query.get("query", "")
        return SearchResult(api_name="ops", success=self.total_count is not None, query=q, total_count=self.total_count)

    async def fetch_biblio_page(
        self, query: dict, start: int = 1, page_size: int = 100, year_range=None, run_id=None
    ) -> SearchResult:
        self.fetch_calls.append((start, page_size, year_range))
        year = year_range[0] if year_range else None
        if year in self.year_data:
            total, items_by_start = self.year_data[year]
            items = items_by_start.get(start, [])
            return SearchResult(api_name="ops", success=True, query=query.get("query", ""), results=items, total_count=total)
        items = self.items_per_start.get(start, [])
        return SearchResult(api_name="ops", success=True, query=query.get("query", ""), results=items, total_count=self.total_count)


def _base_query() -> dict:
    return {"query": '(TITLE:"heart") AND (pd within "20200101 20201231")'}


# Itens no formato COMPLETO (OPSService._extract_biblio_fields, mesma
# extração da probe - ver ChatService._search_abstract_with_retry) - não
# mais o formato enxuto descontinuado (title/applicants/cpc/year). "year" é
# derivado de "publication_date" (formato "YYYYMMDD") por
# ChatService._ops_item_year, não uma chave própria do item.
def _item(
    title: str,
    applicants: list[str],
    cpc_classifications: list[str],
    publication_date: str,
    abstract: str = "Some abstract text.",
    inventors: Optional[list[str]] = None,
) -> dict:
    return {
        "invention_title": title,
        "abstract": abstract,
        "applicants": applicants,
        "inventors": inventors or [],
        "cpc_classifications": cpc_classifications,
        "ipc_classifications": [],
        "publication_date": publication_date,
        "docdb_id": "US.123456.A1",
        "family_id": "12345",
    }


@pytest.mark.asyncio
async def test_run_ops_final_search_uses_range_strategy_when_total_is_small():
    svc = _svc()
    items = [
        _item("t1", ["Acme Corp"], ["B64G 1/2222"], "20200615"),
        _item("t2", ["Globex Inc"], ["H02S 10/40"], "20210301"),
    ]
    adapter = FakeOpsAdapter(total_count=50, items_per_start={1: items})

    compiled = await svc._run_ops_final_search(adapter, _base_query(), year_from=2020, year_to=2021)

    assert compiled["total_count"] == 50
    assert compiled["strategy"] == "range"
    assert compiled["depositants"] == {"Acme Corp": 1, "Globex Inc": 1}
    assert compiled["cpc"] == {"B64G": 1, "H02S": 1}
    assert compiled["title"] == ["t1", "t2"]
    assert compiled["patents_by_year"] == {2020: 1, 2021: 1}
    assert compiled["raw_items"] == items
    # range strategy: uma única página (50 < 100), sem paginação por ano.
    assert len(adapter.fetch_calls) == 1
    assert adapter.fetch_calls[0][0] == 1


@pytest.mark.asyncio
async def test_run_ops_final_search_range_strategy_ignores_iteration():
    svc = _svc()
    items = [_item("t1", ["Acme Corp"], [], "20200101")]
    adapter_it0 = FakeOpsAdapter(total_count=50, items_per_start={1: items})
    adapter_it1 = FakeOpsAdapter(total_count=50, items_per_start={1: items})

    compiled_it0 = await svc._run_ops_final_search(adapter_it0, _base_query(), year_from=2020, year_to=2021)
    compiled_it1 = await svc._run_ops_final_search(
        adapter_it1, _base_query(), year_from=2020, year_to=2021, iteration=1
    )

    assert compiled_it0["strategy"] == compiled_it1["strategy"] == "range"
    assert compiled_it0["depositants"] == compiled_it1["depositants"]
    # mesmas chamadas HTTP (start=1) nos dois casos - iteration não muda nada na range.
    assert adapter_it0.fetch_calls == adapter_it1.fetch_calls


@pytest.mark.asyncio
async def test_run_ops_final_search_uses_year_strategy_when_total_is_large():
    svc = _svc()
    adapter = FakeOpsAdapter(
        total_count=5000,
        year_data={
            2019: (2000, {1: [_item("a", ["Acme Corp"], ["B64G 1/2222"], "20190101")]}),
            2020: (3000, {1: [_item("b", ["Globex Inc"], ["H02S 10/40"], "20200101")]}),
        },
    )

    compiled = await svc._run_ops_final_search(adapter, _base_query(), year_from=2019, year_to=2020)

    assert compiled["strategy"] == "year"
    assert compiled["patents_by_year"] == {2019: 2000, 2020: 3000}
    assert compiled["depositants"] == {"Acme Corp": 1, "Globex Inc": 1}
    assert compiled["cpc"] == {"B64G": 1, "H02S": 1}
    assert compiled["title"] == ["a", "b"]
    # ano strategy: uma requisição por ano (2), não por bloco de 100.
    assert len(adapter.fetch_calls) == 2
    assert all(start == 1 for start, _, _ in adapter.fetch_calls)


@pytest.mark.asyncio
async def test_run_ops_final_search_year_strategy_iteration_selects_next_window():
    svc = _svc()
    adapter = FakeOpsAdapter(
        total_count=5000,
        year_data={
            2020: (
                3000,
                {
                    1: [_item("page0", ["Acme Corp"], [], "20200101")],
                    101: [_item("page1", ["Globex Inc"], [], "20200101")],
                },
            ),
        },
    )

    compiled = await svc._run_ops_final_search(adapter, _base_query(), year_from=2020, year_to=2020, iteration=1)

    # total exato por ano não muda com a iteração - só os itens da amostra mudam.
    assert compiled["patents_by_year"] == {2020: 3000}
    assert compiled["depositants"] == {"Globex Inc": 1}
    assert compiled["title"] == ["page1"]
    assert len(adapter.fetch_calls) == 1
    assert adapter.fetch_calls[0][0] == 101


@pytest.mark.asyncio
async def test_run_ops_final_search_falls_back_when_total_count_unavailable():
    svc = _svc()
    adapter = FakeOpsAdapter(total_count=None)

    compiled = await svc._run_ops_final_search(adapter, _base_query(), year_from=2020, year_to=2020)

    assert compiled["total_count"] is None
    assert compiled["strategy"] == "range"
    assert compiled["patents_by_year"] == {}
    assert compiled["depositants"] == {}
    assert compiled["title"] == []
    assert compiled["raw_items"] == []
    assert len(adapter.fetch_calls) == 1


@pytest.mark.asyncio
async def test_run_final_search_ops_returns_aggregated_shape_with_strategy():
    svc = ChatService(
        llm_resolver=None,
        patent_pairs=[(FakeOpsAdapter(total_count=10, items_per_start={1: []}), None)],
        scholarly_pairs=[],
        settings=Settings(),
    )

    result = await svc.run_final_search(_base_query(), "ops", year_from=2020, year_to=2020)

    assert result["success"] is True
    assert result["api"] == "ops"
    assert set(result) == {
        "success", "api", "depositants", "cpc", "title", "patents_by_year", "strategy", "raw_items", "error",
        "total_count",  # total real da base (Quadro de busca), não o tamanho da amostra
    }
    assert "results" not in result
