from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.domain.types import LLMRequest, LLMResponse, SearchResult
from app.core.services.research_service import ResearchService


def _make_service(**overrides):
    llm = MagicMock()
    llm.process_intake = AsyncMock(return_value=LLMResponse())

    embedding = MagicMock()
    embedding.embed_text = MagicMock(return_value=[1.0, 0.0])
    embedding.embed_document = MagicMock(return_value=[1.0, 0.0])

    patent_search = MagicMock()
    patent_search.api_name = "OPS"
    patent_search.search = AsyncMock(
        return_value=SearchResult("OPS", True, "", results=[])
    )
    patent_builder = MagicMock()
    patent_builder.build_query = MagicMock(return_value={"q": "patent"})

    scholarly_search = MagicMock()
    scholarly_search.api_name = "Scopus"
    scholarly_search.search = AsyncMock(
        return_value=SearchResult("Scopus", True, "", results=[])
    )
    scholarly_builder = MagicMock()
    scholarly_builder.build_query = MagicMock(return_value={"q": "scholarly"})

    defaults = dict(
        llm=llm,
        embedding=embedding,
        patent_pairs=[(patent_search, patent_builder)],
        scholarly_pairs=[(scholarly_search, scholarly_builder)],
        patent_repo=AsyncMock(),
        scholarly_repo=AsyncMock(),
        dedup_registry=AsyncMock(),
    )
    defaults.update(overrides)
    return ResearchService(**defaults), {
        "llm": llm,
        "embedding": embedding,
        "patent_search": patent_search,
        "patent_builder": patent_builder,
        "scholarly_search": scholarly_search,
        "scholarly_builder": scholarly_builder,
    }


# ---- generate_strategy ----

@pytest.mark.asyncio
async def test_generate_strategy_calls_llm():
    svc, mocks = _make_service()
    request = LLMRequest(theme="AI in Healthcare")
    result = await svc.generate_strategy(request, system_prompt="You are an expert.")
    mocks["llm"].process_intake.assert_called_once_with(
        request=request, system_prompt="You are an expert."
    )
    assert isinstance(result, LLMResponse)


# ---- probe_search ----

@pytest.mark.asyncio
async def test_probe_search_calls_builder_and_search():
    svc, mocks = _make_service()
    strategy = LLMResponse()
    pair = (mocks["patent_search"], mocks["patent_builder"])
    await svc.probe_search(strategy, pair, run_id="run-1")
    mocks["patent_builder"].build_query.assert_called_once()
    mocks["patent_search"].search.assert_called_once()


@pytest.mark.asyncio
async def test_probe_search_returns_search_result():
    svc, mocks = _make_service()
    strategy = LLMResponse()
    pair = (mocks["patent_search"], mocks["patent_builder"])
    result = await svc.probe_search(strategy, pair, run_id="run-1")
    assert isinstance(result, SearchResult)


# ---- filter_by_relevance ----

def test_filter_by_relevance_approves_above_threshold():
    svc, mocks = _make_service(relevance_threshold=0.5)
    # embed_text and embed_document both return [1.0, 0.0] → cosine similarity = 1.0
    doc = {"title": "AI", "abstract": "text"}
    approved, rejected = svc.filter_by_relevance("AI", [doc])
    assert len(approved) == 1
    assert len(rejected) == 0


def test_filter_by_relevance_rejects_below_threshold():
    svc, mocks = _make_service(relevance_threshold=0.5)
    # override embed_document to return orthogonal vector → similarity = 0.0
    mocks["embedding"].embed_document = MagicMock(return_value=[0.0, 1.0])
    doc = {"title": "Unrelated", "abstract": "text"}
    approved, rejected = svc.filter_by_relevance("AI", [doc])
    assert len(approved) == 0
    assert len(rejected) == 1


def test_filter_by_relevance_passes_all_when_theme_embed_fails():
    svc, mocks = _make_service()
    mocks["embedding"].embed_text = MagicMock(return_value=None)
    docs = [{"title": "A"}, {"title": "B"}]
    approved, rejected = svc.filter_by_relevance("AI", docs)
    assert len(approved) == 2
    assert len(rejected) == 0


# ---- deduplicate ----

def test_deduplicate_removes_patent_duplicates():
    svc, _ = _make_service()
    patents = [
        {"publication_number": "EP1"},
        {"publication_number": "EP1"},
    ]
    result = svc.deduplicate(patents, [])
    assert len(result["unique_patents"]) == 1


def test_deduplicate_removes_scholarly_duplicates():
    svc, _ = _make_service()
    scholarly = [
        {"doi": "10.1234/abc"},
        {"doi": "10.1234/abc"},
    ]
    result = svc.deduplicate([], scholarly)
    assert len(result["unique_scholarly"]) == 1


# ---- production_search ----

@pytest.mark.asyncio
async def test_production_search_aggregates_all_pairs():
    svc, _ = _make_service()
    strategy = LLMResponse()
    results = await svc.production_search(strategy, strategy, run_id="run-2")
    # 1 patent pair + 1 scholarly pair → 2 results
    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)
