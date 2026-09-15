from __future__ import annotations

import asyncio
from typing import Any, Optional

import chromadb
from chromadb.api.types import EmbeddingFunction

from app.core.ports.outbound.embedding_port import EmbeddingPort
from core.logging import get_logger

logger = get_logger(__name__)

_COLLECTION_NAME = "report_rag"


class _EmbeddingPortFunction(EmbeddingFunction):
    """
    Adapta EmbeddingPort (sentence-transformers, já usado pelo KeyBERT) pro
    protocolo `EmbeddingFunction` do ChromaDB - corrige o bug do RAGService
    legado (services/rag_service.py), que nunca chamava os embeddings do
    Ollama de fato e usava o embedding default do Chroma. Rodando como
    função customizada, o embedding é sempre calculado no processo do
    backend (não dentro do container `chromadb`), então o RAG continua
    100% independente do LLM (Ollama/intranet) estar disponível.

    Herda de `EmbeddingFunction` (não só duck-typing) porque o ChromaDB
    chama `embed_query()` em toda consulta - método que só existe via essa
    herança (default: delega pra `__call__`, ver chromadb.api.types).
    """

    def __init__(self, embedding: EmbeddingPort) -> None:
        self._embedding = embedding

    @staticmethod
    def name() -> str:
        return "embedding-port"

    def __call__(self, input: list[str]) -> list[list[float]]:
        results = self._embedding.embed_batch(list(input))
        vectors: list[list[float]] = []
        for text, vector in zip(input, results):
            if vector is None:
                raise RuntimeError(
                    f"Falha ao gerar embedding para chunk de texto (len={len(text)}) - "
                    "modelo de embedding indisponível."
                )
            vectors.append(vector)
        return vectors


class ChromaVectorStoreAdapter:
    """
    Implementa VectorStorePort contra um container ChromaDB (HttpClient) -
    não embutido/PersistentClient em disco, pra ser seguro com múltiplos
    workers do backend (ver docker-compose.yml/`chromadb`). Coleção única
    `report_rag`; isolamento entre sessões é por metadata (`session_id`),
    não por coleção separada - ver ReportWriterService.
    """

    def __init__(self, host: str, port: int, embedding: EmbeddingPort) -> None:
        self._client = chromadb.HttpClient(host=host, port=port)
        self._embedding_function = _EmbeddingPortFunction(embedding)
        self._collection = self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    async def add(
        self,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        await asyncio.to_thread(
            self._collection.add,
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )

    async def query(
        self,
        query_text: str,
        top_k: int,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        results = await asyncio.to_thread(
            self._collection.query,
            query_texts=[query_text],
            n_results=top_k,
            where=filter_metadata,
        )

        documents = results.get("documents") or []
        if not documents or not documents[0]:
            return []

        formatted: list[dict[str, Any]] = []
        for idx, (doc, metadata, distance) in enumerate(
            zip(documents[0], results["metadatas"][0], results["distances"][0])
        ):
            formatted.append(
                {
                    "rank": idx + 1,
                    "text": doc,
                    "metadata": metadata,
                    "relevance_score": 1 - distance,
                }
            )
        return formatted

    async def clear(self) -> bool:
        try:
            await asyncio.to_thread(self._client.delete_collection, _COLLECTION_NAME)
            self._collection = await asyncio.to_thread(
                self._client.get_or_create_collection,
                name=_COLLECTION_NAME,
                embedding_function=self._embedding_function,
                metadata={"hnsw:space": "cosine"},
            )
            return True
        except Exception as exc:
            logger.error("chroma_clear_failed error=%s", exc)
            return False

    async def delete_by_metadata(self, filter_metadata: dict[str, Any]) -> None:
        await asyncio.to_thread(self._collection.delete, where=filter_metadata)

    def count(self) -> int:
        return self._collection.count()
