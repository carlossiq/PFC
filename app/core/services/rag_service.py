from __future__ import annotations

import hashlib
import logging
from typing import Any, Optional

from app.core.ports.outbound.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 200
_MIN_CHUNK_LENGTH = 100


class RAGService:
    """
    RAG (Retrieval-Augmented Generation) usando VectorStorePort.

    Responsável por chunking, indexação e recuperação de documentos.
    """

    def __init__(self, vector_store: VectorStorePort) -> None:
        self._store = vector_store

    # ------------------------------------------------------------------
    # Chunking (puro Python)
    # ------------------------------------------------------------------

    def chunk_text(
        self,
        text: str,
        chunk_size: int = _CHUNK_SIZE,
        overlap: int = _CHUNK_OVERLAP,
    ) -> list[str]:
        if not text:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()
            if len(chunk) >= _MIN_CHUNK_LENGTH:
                chunks.append(chunk)
            start = end - overlap if end < len(text) else len(text)
        return chunks

    # ------------------------------------------------------------------
    # Indexação
    # ------------------------------------------------------------------

    async def index_documents(
        self,
        documents: list[dict[str, Any]],
        metadata_key: str = "source",
    ) -> int:
        all_ids: list[str] = []
        all_texts: list[str] = []
        all_metadatas: list[dict[str, Any]] = []

        for doc_idx, doc in enumerate(documents):
            text = doc.get("text", "")
            if not text:
                continue

            metadata = {k: v for k, v in doc.items() if k != "text"}
            metadata["source_index"] = str(doc_idx)

            for chunk_idx, chunk in enumerate(self.chunk_text(text)):
                chunk_id = hashlib.md5(
                    f"{doc_idx}_{chunk_idx}_{chunk}".encode()
                ).hexdigest()
                all_ids.append(chunk_id)
                all_texts.append(chunk)
                all_metadatas.append(metadata)

        if not all_ids:
            return 0

        await self._store.add(ids=all_ids, texts=all_texts, metadatas=all_metadatas)
        logger.info("documents_indexed chunks=%d docs=%d", len(all_ids), len(documents))
        return len(all_ids)

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------

    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        return await self._store.query(
            query_text=query_text,
            top_k=top_k,
            filter_metadata=filter_metadata,
        )

    async def get_context_for_section(
        self,
        section_name: str,
        section_description: str,
        top_k: int = 5,
    ) -> str:
        results = await self.query(
            query_text=f"{section_name}: {section_description}",
            top_k=top_k,
        )
        if not results:
            return ""

        parts = [f"## Contexto para {section_name}\n"]
        for result in results:
            relevance = result.get("relevance_score", 0)
            source = (result.get("metadata") or {}).get("source", "N/A")
            parts.append(f"**Relevância: {relevance:.1%}**")
            parts.append(f"Fonte: {source}")
            parts.append(result.get("text", ""))
            parts.append("")

        logger.info("section_context_retrieved section=%s chunks=%d", section_name, len(results))
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Administração
    # ------------------------------------------------------------------

    async def clear_collection(self) -> bool:
        result = await self._store.clear()
        logger.info("collection_cleared success=%s", result)
        return result

    def get_stats(self) -> dict[str, Any]:
        try:
            count = self._store.count()
            return {"document_count": count, "status": "healthy"}
        except Exception as exc:
            logger.error("get_stats_failed error=%s", exc)
            return {"status": "error", "error": str(exc)}
