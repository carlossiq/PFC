from __future__ import annotations

import asyncio

from services.storage.minio_service import MinioService


class MinioStorageAdapter:
    def __init__(self, service: MinioService) -> None:
        self._service = service

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._service.upload_bytes, key, data, content_type)

    async def download(self, key: str) -> bytes:
        return await asyncio.to_thread(self._service.download_bytes, key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._service.delete_object, key)

    async def ensure_bucket(self) -> None:
        await asyncio.to_thread(self._service.ensure_bucket)
