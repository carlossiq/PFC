from __future__ import annotations

from typing import Optional

from services.db.repositories import ScholarlyDocumentRepository
from schemas.normalized_metadata import StandardizedScholarlyMetadata
from app.adapters.driven.persistence._converters import scholarly_doc_to_metadata


class ScholarlyRepositoryAdapter:
    def __init__(self, repository: ScholarlyDocumentRepository) -> None:
        self._repo = repository

    async def create(self, metadata: StandardizedScholarlyMetadata) -> str:
        doc = await self._repo.create(metadata)
        return doc.dedup_key

    async def get_by_dedup_key(
        self, dedup_key: str
    ) -> Optional[StandardizedScholarlyMetadata]:
        doc = await self._repo.get_by_dedup_key(dedup_key)
        return scholarly_doc_to_metadata(doc) if doc is not None else None

    async def get_by_doi(self, doi: str) -> Optional[StandardizedScholarlyMetadata]:
        doc = await self._repo.get_by_doi(doi)
        return scholarly_doc_to_metadata(doc) if doc is not None else None

    async def exists_dedup_key(self, dedup_key: str) -> bool:
        return await self._repo.exists_dedup_key(dedup_key)

    async def update(
        self,
        dedup_key: str,
        metadata: StandardizedScholarlyMetadata,
    ) -> Optional[StandardizedScholarlyMetadata]:
        doc = await self._repo.update(dedup_key, metadata)
        return scholarly_doc_to_metadata(doc) if doc is not None else None

    async def get_by_source_and_year(
        self,
        source: str,
        year: int,
        limit: int = 100,
    ) -> list[StandardizedScholarlyMetadata]:
        docs = await self._repo.get_by_source_and_year(source, year, limit)
        return [scholarly_doc_to_metadata(doc) for doc in docs]
