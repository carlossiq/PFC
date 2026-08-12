from typing import Optional

import pytest

from app.core.domain.types import SearchResult
from app.core.services.chat_service import ChatService
from core.config import Settings


def _svc() -> ChatService:
    return ChatService(llm=None, patent_pairs=[], scholarly_pairs=[], settings=Settings())


class FakeScopusAdapter:
    """
    Adapter fake pro Scopus - simula count()/fetch_results_page() sem rede,
    roteando por trecho da query (SUBJAREA/PUBYEAR) igual à API real faria.

    `year_data` mapeia year -> (total, {start: items}) - total_count é
    constante pra um ano/query, igual na API real, independente de `start`;
    só os itens retornados mudam por janela (start), usado pra testar
    `iteration`.
    """

    api_name = "scopus"

    def __init__(
        self,
        total_count: Optional[int],
        year_data: Optional[dict[int, tuple[int, dict[int, list[dict]]]]] = None,
        area_totals: Optional[dict[str, int]] = None,
        items_per_start: Optional[dict[int, list[dict]]] = None,
    ) -> None:
        self.total_count = total_count
        self.year_data = year_data or {}
        self.area_totals = area_totals or {}
        self.items_per_start = items_per_start or {}
        self.fetch_calls: list[tuple[str, int, int]] = []
        self.count_calls: list[str] = []

    async def count(self, query: dict, run_id=None) -> SearchResult:
        q = query.get("query", "")
        self.count_calls.append(q)
        if "SUBJAREA(" in q:
            for code, total in self.area_totals.items():
                if f"SUBJAREA({code})" in q:
                    return SearchResult(api_name="scopus", success=True, query=q, total_count=total)
            return SearchResult(api_name="scopus", success=True, query=q, total_count=0)
        return SearchResult(api_name="scopus", success=self.total_count is not None, query=q, total_count=self.total_count)

    async def fetch_results_page(self, query: dict, start: int = 0, count: int = 200, run_id=None) -> SearchResult:
        q = query.get("query", "")
        self.fetch_calls.append((q, start, count))
        for year, (total, items_by_start) in self.year_data.items():
            if f"PUBYEAR > {year - 1} AND PUBYEAR < {year + 1})" in q:
                items = items_by_start.get(start, [])
                return SearchResult(api_name="scopus", success=True, query=q, results=items, total_count=total)
        items = self.items_per_start.get(start, [])
        return SearchResult(api_name="scopus", success=True, query=q, results=items, total_count=self.total_count)


class FakeGenericAdapter:
    """
    Adapter fake sem fetch_biblio_page/fetch_results_page - cai no branch
    genérico de run_final_search (lens_patent/lens_scholarly/openalex),
    que só chama .search(query) sem paginação por range/ano.
    """

    def __init__(self, api_name: str, results: list[dict]) -> None:
        self.api_name = api_name
        self._results = results

    async def search(self, query: dict) -> SearchResult:
        return SearchResult(
            api_name=self.api_name, success=True, query=query.get("query", ""), results=self._results
        )


def _base_query() -> dict:
    return {"query": "TITLE-ABS-KEY(heart)", "view": "STANDARD"}


def test_fuzzy_group_institutions_merges_near_duplicates():
    svc = _svc()
    counts = {"Aarhus Universitet": 10, "AARHUS UNIVERSITET.": 4, "MIT": 5}

    grouped = svc._fuzzy_group_institutions(counts)

    assert grouped == {"Aarhus Universitet": 14, "MIT": 5}


def test_aggregate_scopus_final_items_groups_institutions_and_collects_titles():
    svc = _svc()
    items = [
        {"institutions": ["Aarhus Universitet"], "title": "t1"},
        {"institutions": ["AARHUS UNIVERSITET."], "title": "t2"},
        {"institutions": ["MIT", "Stanford"], "title": None},
    ]

    institutions, titles = svc._aggregate_scopus_final_items(items)

    assert institutions == {"Aarhus Universitet": 2, "MIT": 1, "Stanford": 1}
    assert titles == ["t1", "t2"]


@pytest.mark.asyncio
async def test_run_scopus_final_search_uses_range_strategy_when_total_is_small():
    svc = _svc()
    items = [
        {"institutions": ["Aarhus Universitet"], "title": "t1", "year": 2020},
        {"institutions": ["MIT"], "title": "t2", "year": 2021},
    ]
    adapter = FakeScopusAdapter(
        total_count=50,
        area_totals={"MEDI": 30, "ENGI": 10},
        items_per_start={0: items},
    )

    compiled = await svc._run_scopus_final_search(adapter, _base_query(), year_from=2020, year_to=2021)

    assert compiled["total_count"] == 50
    assert compiled["institutions"] == {"Aarhus Universitet": 1, "MIT": 1}
    assert compiled["title"] == ["t1", "t2"]
    assert compiled["articles_by_year"] == {2020: 1, 2021: 1}
    assert compiled["area_of_study"] == {"Medicine": 30, "Engineering": 10}
    assert compiled["strategy"] == "range"
    # range strategy: uma única página (50 < 200), sem paginação em bloco de ano.
    assert len(adapter.fetch_calls) == 1
    assert adapter.fetch_calls[0][1:] == (0, 200)


@pytest.mark.asyncio
async def test_run_scopus_final_search_range_strategy_ignores_iteration():
    svc = _svc()
    items = [{"institutions": ["MIT"], "title": "t1", "year": 2020}]
    adapter_it0 = FakeScopusAdapter(total_count=50, items_per_start={0: items})
    adapter_it1 = FakeScopusAdapter(total_count=50, items_per_start={0: items})

    compiled_it0 = await svc._run_scopus_final_search(adapter_it0, _base_query(), year_from=2020, year_to=2021)
    compiled_it1 = await svc._run_scopus_final_search(
        adapter_it1, _base_query(), year_from=2020, year_to=2021, iteration=1
    )

    assert compiled_it0["strategy"] == compiled_it1["strategy"] == "range"
    assert compiled_it0["institutions"] == compiled_it1["institutions"]
    assert compiled_it0["title"] == compiled_it1["title"]
    # mesmas chamadas HTTP (start=0) nos dois casos - iteration não muda nada na range.
    assert adapter_it0.fetch_calls == adapter_it1.fetch_calls


@pytest.mark.asyncio
async def test_run_scopus_final_search_uses_year_strategy_when_total_is_large():
    svc = _svc()
    adapter = FakeScopusAdapter(
        total_count=5000,
        year_data={
            2019: (2000, {0: [{"institutions": ["MIT"], "title": "a", "year": 2019}]}),
            2020: (3000, {0: [{"institutions": ["Stanford"], "title": "b", "year": 2020}]}),
        },
    )

    compiled = await svc._run_scopus_final_search(adapter, _base_query(), year_from=2019, year_to=2020)

    assert compiled["strategy"] == "year"
    assert compiled["articles_by_year"] == {2019: 2000, 2020: 3000}
    assert compiled["institutions"] == {"MIT": 1, "Stanford": 1}
    assert compiled["title"] == ["a", "b"]
    # ano strategy: uma requisição por ano (2), não por bloco de 200.
    assert len(adapter.fetch_calls) == 2
    assert all(start == 0 for _, start, _ in adapter.fetch_calls)


@pytest.mark.asyncio
async def test_run_scopus_final_search_year_strategy_iteration_selects_next_window():
    svc = _svc()
    adapter = FakeScopusAdapter(
        total_count=5000,
        year_data={
            2020: (
                3000,
                {
                    0: [{"institutions": ["MIT"], "title": "page0", "year": 2020}],
                    200: [{"institutions": ["Stanford"], "title": "page1", "year": 2020}],
                },
            ),
        },
    )

    compiled = await svc._run_scopus_final_search(
        adapter, _base_query(), year_from=2020, year_to=2020, iteration=1
    )

    # total exato por ano não muda com a iteração - só os itens da amostra mudam.
    assert compiled["articles_by_year"] == {2020: 3000}
    assert compiled["institutions"] == {"Stanford": 1}
    assert compiled["title"] == ["page1"]
    assert len(adapter.fetch_calls) == 1
    assert adapter.fetch_calls[0][1:] == (200, 200)


@pytest.mark.asyncio
async def test_run_scopus_final_search_falls_back_when_total_count_unavailable():
    svc = _svc()
    adapter = FakeScopusAdapter(total_count=None, area_totals={})

    compiled = await svc._run_scopus_final_search(adapter, _base_query(), year_from=2020, year_to=2020)

    assert compiled["total_count"] is None
    assert compiled["strategy"] == "range"
    assert compiled["articles_by_year"] == {}
    assert compiled["institutions"] == {}
    assert compiled["title"] == []
    # 1 única requisição de range (max_requests=1), mesmo fallback da OPS.
    assert len(adapter.fetch_calls) == 1


@pytest.mark.asyncio
async def test_run_final_search_scopus_returns_aggregated_shape_not_raw_results():
    svc = ChatService(
        llm=None,
        patent_pairs=[],
        scholarly_pairs=[(FakeScopusAdapter(total_count=10, items_per_start={0: []}), None)],
        settings=Settings(),
    )

    result = await svc.run_final_search(_base_query(), "scopus", year_from=2020, year_to=2020)

    assert result["success"] is True
    assert result["api"] == "scopus"
    assert result["strategy"] in ("range", "year")
    assert set(result) == {
        "success", "api", "institutions", "area_of_study", "title", "articles_by_year", "strategy", "error",
    }
    assert "results" not in result
    assert "results_count" not in result


@pytest.mark.asyncio
async def test_run_final_search_generic_branch_no_longer_slices_results():
    many_items = [{"id": i} for i in range(300)]
    svc = ChatService(
        llm=None,
        patent_pairs=[],
        scholarly_pairs=[(FakeGenericAdapter("lens_scholarly", many_items), None)],
        settings=Settings(),
    )

    result = await svc.run_final_search(_base_query(), "lens_scholarly", year_from=2020, year_to=2020)

    assert result["success"] is True
    assert result["results_count"] == 300
    assert len(result["results"]) == 300
