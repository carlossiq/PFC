from __future__ import annotations

from services.db.repositories import DedupRegistry


class DedupRegistryAdapter:
    def __init__(self, repository: DedupRegistry) -> None:
        self._repo = repository

    async def register_scholarly(
        self,
        dedup_key: str,
        document_id: int,
        source: str,
        source_record_id: str,
    ) -> None:
        await self._repo.register_scholarly(dedup_key, document_id, source, source_record_id)

    async def register_patent(
        self,
        dedup_key: str,
        document_id: int,
        source: str,
        source_record_id: str,
    ) -> None:
        await self._repo.register_patent(dedup_key, document_id, source, source_record_id)

    async def exists_scholarly(self, dedup_key: str) -> bool:
        return await self._repo.exists_scholarly(dedup_key)

    async def exists_patent(self, dedup_key: str) -> bool:
        return await self._repo.exists_patent(dedup_key)
