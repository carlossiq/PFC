from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from schemas.normalized_metadata import (
    StandardizedPatentMetadata,
    StandardizedScholarlyMetadata,
)


@runtime_checkable
class ScholarlyRepositoryPort(Protocol):
    async def create(self, metadata: StandardizedScholarlyMetadata) -> str: ...

    async def get_by_dedup_key(
        self, dedup_key: str
    ) -> Optional[StandardizedScholarlyMetadata]: ...

    async def get_by_doi(self, doi: str) -> Optional[StandardizedScholarlyMetadata]: ...

    async def exists_dedup_key(self, dedup_key: str) -> bool: ...

    async def update(
        self,
        dedup_key: str,
        metadata: StandardizedScholarlyMetadata,
    ) -> Optional[StandardizedScholarlyMetadata]: ...

    async def get_by_source_and_year(
        self,
        source: str,
        year: int,
        limit: int = 100,
    ) -> list[StandardizedScholarlyMetadata]: ...


@runtime_checkable
class PatentRepositoryPort(Protocol):
    async def create(self, metadata: StandardizedPatentMetadata) -> str: ...

    async def get_by_dedup_key(
        self, dedup_key: str
    ) -> Optional[StandardizedPatentMetadata]: ...

    async def get_by_publication_number(
        self, publication_number: str
    ) -> Optional[StandardizedPatentMetadata]: ...

    async def exists_dedup_key(self, dedup_key: str) -> bool: ...

    async def update(
        self,
        dedup_key: str,
        metadata: StandardizedPatentMetadata,
    ) -> Optional[StandardizedPatentMetadata]: ...

    async def get_by_source_and_year(
        self,
        source: str,
        year: int,
        limit: int = 100,
    ) -> list[StandardizedPatentMetadata]: ...


@runtime_checkable
class DedupRegistryPort(Protocol):
    async def register_scholarly(
        self,
        dedup_key: str,
        document_id: int,
        source: str,
        source_record_id: str,
    ) -> None: ...

    async def register_patent(
        self,
        dedup_key: str,
        document_id: int,
        source: str,
        source_record_id: str,
    ) -> None: ...

    async def exists_scholarly(self, dedup_key: str) -> bool: ...

    async def exists_patent(self, dedup_key: str) -> bool: ...
