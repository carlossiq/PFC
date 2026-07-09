from __future__ import annotations

from typing import Optional

from services.db.repositories import PatentDocumentRepository
from schemas.normalized_metadata import StandardizedPatentMetadata
from app.adapters.driven.persistence._converters import patent_doc_to_metadata


class PatentRepositoryAdapter:
    def __init__(self, repository: PatentDocumentRepository) -> None:
        self._repo = repository

    async def create(self, metadata: StandardizedPatentMetadata) -> str:
        doc = await self._repo.create(metadata)
        return doc.dedup_key

    async def get_by_dedup_key(
        self, dedup_key: str
    ) -> Optional[StandardizedPatentMetadata]:
        doc = await self._repo.get_by_dedup_key(dedup_key)
        return patent_doc_to_metadata(doc) if doc is not None else None

    async def get_by_publication_number(
        self, publication_number: str
    ) -> Optional[StandardizedPatentMetadata]:
        doc = await self._repo.get_by_publication_number(publication_number)
        return patent_doc_to_metadata(doc) if doc is not None else None

    async def exists_dedup_key(self, dedup_key: str) -> bool:
        return await self._repo.exists_dedup_key(dedup_key)

    async def update(
        self,
        dedup_key: str,
        metadata: StandardizedPatentMetadata,
    ) -> Optional[StandardizedPatentMetadata]:
        doc = await self._repo.update(dedup_key, metadata)
        return patent_doc_to_metadata(doc) if doc is not None else None

    async def get_by_source_and_year(
        self,
        source: str,
        year: int,
        limit: int = 100,
    ) -> list[StandardizedPatentMetadata]:
        docs = await self._repo.get_by_source_and_year(source, year, limit)
        return [patent_doc_to_metadata(doc) for doc in docs]
