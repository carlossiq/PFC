from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.core.domain.types import LLMRequest, LLMResponse


@runtime_checkable
class LLMPort(Protocol):
    @property
    def provider_name(self) -> str: ...

    def is_available(self) -> bool: ...

    async def process_intake(
        self,
        request: LLMRequest,
        system_prompt: str,
    ) -> LLMResponse: ...

    async def call_raw_json(
        self,
        prompt: str,
        user_input: str,
    ) -> dict[str, Any]: ...
