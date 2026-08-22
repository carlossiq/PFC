from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class StoragePort(Protocol):
    async def upload(self, key: str, data: bytes, content_type: str) -> None: ...

    async def download(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...

    async def ensure_bucket(self) -> None: ...
