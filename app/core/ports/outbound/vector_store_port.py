from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class VectorStorePort(Protocol):
    async def add(
        self,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None: ...

    async def query(
        self,
        query_text: str,
        top_k: int,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]: ...

    async def clear(self) -> bool: ...

    def count(self) -> int: ...
