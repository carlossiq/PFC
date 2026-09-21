"""
Ollama (ou qualquer servidor compatível com a API de chat completions da
OpenAI) como provider de LLM completo - implementa o mesmo contrato de
AnthropicLLMService/GeminiLLMService (process_intake/call_raw_json), ao
contrário de services/ollama_service.py (mais antigo, só geração de texto
solta, usado por ReportWriterService via OpenAICompatibleAdapter).

Existe porque a partir da migração de configuração de IA pro banco (ver
PLANO_MIGRACAO_CONFIG_BANCO.md), qualquer um dos 4 call sites - inclusive os
de geração de query, antes só Gemini/Anthropic - pode ser atendido por um
servidor Ollama/compatível.
"""

import json
import time
from typing import Any, Optional

import httpx
from pydantic import ValidationError

from app.core.domain.types import LLMUsage
from core.logging import get_logger
from schemas.intake import InputIntake
from schemas.llm import LLMOutput
from services.llm.base import BaseLLMService, LLMJSONParseError

logger = get_logger(__name__)


class OllamaLLMService(BaseLLMService):
    """
    Serviço LLM genérico via endpoint `{base_url}/v1/chat/completions`
    (formato OpenAI chat completions) - cobre Ollama local, Ollama de
    intranet, ou qualquer outro servidor compatível.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout_seconds: int = 600,
    ) -> None:
        if not base_url:
            raise ValueError("Ollama base_url is required")

        super().__init__(api_key)
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.AsyncClient(timeout=timeout_seconds)
        self._is_available = True

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        return self._is_available

    async def process_intake(
        self,
        intake: InputIntake,
        system_prompt: str,
    ) -> tuple[LLMOutput, LLMUsage]:
        if not self.is_available():
            raise RuntimeError("Ollama service is not available")

        user_message = self._build_user_message(intake)

        try:
            response, usage = await self._call_llm(system_prompt, user_message)

            logger.info(
                "ollama_raw_response",
                theme=intake.theme,
                response_length=len(response),
                response_preview=response[:500] if response else "EMPTY",
            )

            json_output = self._extract_json(response)
            json_output_normalized = {k.lower(): v for k, v in json_output.items()}
            llm_output = LLMOutput(**json_output_normalized)

            logger.info(
                "ollama_processing_success",
                theme=intake.theme,
                has_queries=llm_output.has_any_queries(),
            )

            return llm_output, usage

        except ValidationError as exc:
            logger.error("ollama_validation_error", theme=intake.theme, error=str(exc))
            raise ValueError(f"Ollama output validation failed: {exc}")
        except Exception as exc:
            logger.error("ollama_processing_error", theme=intake.theme, error=str(exc))
            raise

    async def call_raw_json(
        self,
        prompt: str,
        user_input: str,
    ) -> tuple[dict[str, Any], LLMUsage]:
        if not self.is_available():
            raise RuntimeError("Ollama service is not available")

        try:
            response, usage = await self._call_llm(prompt, user_input)
            json_output = self._extract_json(response)
            return json_output, usage
        except Exception as exc:
            logger.error("ollama_raw_json_error", error=str(exc))
            raise

    def _build_user_message(self, intake: InputIntake) -> str:
        message = f"Theme: {intake.theme}\n"
        if intake.description:
            message += f"Description: {intake.description}\n"
        if intake.area_of_study:
            message += f"Area of Study: {intake.area_of_study}\n"
        if intake.keywords:
            message += f"Keywords: {', '.join(intake.keywords)}\n"
        return message

    async def _call_llm(self, system_prompt: str, user_message: str) -> tuple[str, LLMUsage]:
        try:
            start = time.perf_counter()
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            response = await self._client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            duration_ms = (time.perf_counter() - start) * 1000

            text = data["choices"][0]["message"]["content"]
            usage_data = data.get("usage", {})

            usage = LLMUsage(
                provider=self.provider_name,
                model=self.model,
                duration_ms=duration_ms,
                input_tokens=usage_data.get("prompt_tokens", 0),
                output_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            return text, usage

        except httpx.ConnectError as exc:
            logger.error("ollama_connect_error", base_url=self.base_url, error=str(exc))
            raise RuntimeError(f"Não foi possível conectar ao servidor Ollama em {self.base_url}.") from exc
        except Exception as exc:
            logger.error("ollama_call_failed", base_url=self.base_url, error=str(exc))
            raise

    @staticmethod
    def _extract_json(response: str) -> dict:
        if not response or not response.strip():
            raise ValueError("Empty response from Ollama")

        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as exc:
                    raise LLMJSONParseError(f"Invalid JSON in ```json block: {exc}", raw_response=response)

        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end > start:
                json_str = response[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as exc:
                    raise LLMJSONParseError(f"Invalid JSON in ``` block: {exc}", raw_response=response)

        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise LLMJSONParseError(
                f"Could not parse response as JSON: {exc}. Response preview: {response[:200]}",
                raw_response=response,
            )
