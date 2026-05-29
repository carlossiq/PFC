from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from app.core.domain.types import Embedding


@runtime_checkable
class EmbeddingPort(Protocol):
    def embed_text(self, text: str) -> Optional[Embedding]: ...

    def embed_batch(
        self,
        texts: list[str],
        show_progress_bar: bool = False,
    ) -> list[Optional[Embedding]]: ...

    def embed_document(
        self,
        title: Optional[str] = None,
        abstract: Optional[str] = None,
        full_text: Optional[str] = None,
    ) -> Optional[Embedding]: ...

    def embed_documents_batch(
        self,
        documents: list[dict],
    ) -> list[Optional[Embedding]]: ...

    def get_embedding_dimension(self) -> Optional[int]: ...
