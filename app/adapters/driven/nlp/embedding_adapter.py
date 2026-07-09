from __future__ import annotations

from typing import Optional

from services.nlp.embedding_service import EmbeddingService
from app.core.domain.types import Embedding


class EmbeddingAdapter:
    def __init__(self, service: EmbeddingService) -> None:
        self._service = service

    def embed_text(self, text: str) -> Optional[Embedding]:
        r = self._service.embed_text(text)
        return r.tolist() if r is not None else None

    def embed_batch(
        self,
        texts: list[str],
        show_progress_bar: bool = False,
    ) -> list[Optional[Embedding]]:
        return [
            r.tolist() if r is not None else None
            for r in self._service.embed_batch(texts, show_progress_bar)
        ]

    def embed_document(
        self,
        title: Optional[str] = None,
        abstract: Optional[str] = None,
        full_text: Optional[str] = None,
    ) -> Optional[Embedding]:
        r = self._service.embed_document(title=title, abstract=abstract, full_text=full_text)
        return r.tolist() if r is not None else None

    def embed_documents_batch(
        self,
        documents: list[dict],
    ) -> list[Optional[Embedding]]:
        return [
            r.tolist() if r is not None else None
            for r in self._service.embed_documents_batch(documents)
        ]

    def get_embedding_dimension(self) -> Optional[int]:
        return self._service.get_embedding_dimension()
