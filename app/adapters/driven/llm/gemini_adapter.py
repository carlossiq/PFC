from __future__ import annotations

from typing import Any

from services.llm.gemini_service import GeminiLLMService
from app.core.domain.types import LLMRequest, LLMResponse
from app.adapters.driven.llm._converters import output_to_response, request_to_intake


class GeminiLLMAdapter:
    def __init__(self, service: GeminiLLMService) -> None:
        self._service = service

    @property
    def provider_name(self) -> str:
        return self._service.provider_name

    def is_available(self) -> bool:
        return self._service.is_available()

    async def process_intake(
        self,
        request: LLMRequest,
        system_prompt: str,
    ) -> LLMResponse:
        intake = request_to_intake(request)
        output = await self._service.process_intake(intake, system_prompt)
        return output_to_response(output)

    async def call_raw_json(
        self,
        prompt: str,
        user_input: str,
    ) -> dict[str, Any]:
        return await self._service.call_raw_json(prompt, user_input)
