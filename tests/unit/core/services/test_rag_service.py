from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.services.rag_service import RAGService


@pytest.fixture
def vector_store():
    store = MagicMock()
    store.add = AsyncMock()
    store.query = AsyncMock(return_value=[{"text": "result", "relevance_score": 0.9}])
    store.clear = AsyncMock(return_value=True)
    store.count = MagicMock(return_value=5)
    return store


@pytest.fixture
def svc(vector_store):
    return RAGService(vector_store)


# ---- index_documents ----

@pytest.mark.asyncio
async def test_index_documents_calls_store_add(svc, vector_store):
    docs = [{"text": "a" * 200}]
    await svc.index_documents(docs)
    vector_store.add.assert_called_once()
    _, kwargs = vector_store.add.call_args
    assert len(kwargs["ids"]) > 0
    assert len(kwargs["texts"]) > 0
    assert len(kwargs["metadatas"]) > 0


@pytest.mark.asyncio
async def test_index_documents_empty_text_skipped(svc, vector_store):
    count = await svc.index_documents([{"text": ""}])
    vector_store.add.assert_not_called()
    assert count == 0


@pytest.mark.asyncio
async def test_index_documents_returns_chunk_count(svc, vector_store):
    docs = [{"text": "x" * 2500}]
    count = await svc.index_documents(docs)
    assert count >= 2


# ---- query ----

@pytest.mark.asyncio
async def test_query_delegates_to_store(svc, vector_store):
    result = await svc.query("my query", top_k=3)
    vector_store.query.assert_called_once_with(
        query_text="my query",
        top_k=3,
        filter_metadata=None,
    )
    assert result == [{"text": "result", "relevance_score": 0.9}]


# ---- clear_collection ----

@pytest.mark.asyncio
async def test_clear_collection_delegates_to_store(svc, vector_store):
    result = await svc.clear_collection()
    vector_store.clear.assert_called_once()
    assert result is True


# ---- chunk_text ----

def test_chunk_text_empty_string(svc):
    assert svc.chunk_text("") == []


def test_chunk_text_short_text_below_min_length(svc):
    # 50 chars < _MIN_CHUNK_LENGTH (100)
    assert svc.chunk_text("a" * 50) == []


def test_chunk_text_long_text_produces_multiple_chunks(svc):
    chunks = svc.chunk_text("w" * 2500)
    assert len(chunks) >= 2
