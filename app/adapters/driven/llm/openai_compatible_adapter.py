from __future__ import annotations

from typing import Optional

import httpx

from core.logging import get_logger

logger = get_logger(__name__)


class OpenAICompatibleAdapter:
    """
    Implementa TextGenerationPort contra qualquer endpoint compatível com a
    API de chat completions da OpenAI (`POST {base_url}/v1/chat/completions`)
    - serve tanto o Ollama local (container `ollama` do docker-compose.yml,
    que expõe esse mesmo formato em /v1) quanto o LLM remoto da intranet
    (proxy tipo LiteLLM, autenticado por API key), sem nenhuma diferença de
    código: só `base_url`/`api_key`/`model` mudam, via settings.

    Não reaproveita services/ollama_service.py (API nativa do Ollama,
    `/api/generate`) - propositalmente, pra manter um único caminho de
    código pros dois ambientes (local e intranet) em vez de dois adapters.
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: Optional[str] = None,
        timeout_seconds: int = 300,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def generate(self, prompt: str, system: Optional[str] = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            response = await self._client.post(
                f"{self._base_url}/v1/chat/completions",
                headers=headers,
                json={"model": self._model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.ConnectError as exc:
            logger.error("text_generation_connect_error", base_url=self._base_url, error=str(exc))
            raise RuntimeError(f"Não foi possível conectar ao servidor de LLM em {self._base_url}.") from exc
        except Exception as exc:
            logger.error("text_generation_failed", base_url=self._base_url, model=self._model, error=str(exc))
            raise

    async def close(self) -> None:
        await self._client.aclose()
