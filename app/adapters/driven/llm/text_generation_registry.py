"""
Registry equivalente a provider_registry.py, mas pro call site
"report_writing" (TextGenerationPort: generate(prompt, system) -> str, sem
JSON estruturado - ver app/core/ports/outbound/text_generation_port.py).

Existe separado de LLM_PROVIDER_REGISTRY porque nenhum dos 3 serviços de IA
(Gemini/Anthropic/Ollama) expõe hoje um método de texto livre - só
process_intake/call_raw_json (voltados a InputIntake). Os wrappers de
Gemini/Anthropic aqui são deliberadamente pequenos (chamada direta ao SDK)
em vez de reaproveitar GeminiLLMService/AnthropicLLMService, pra não forçar
esses serviços a servir dois contratos diferentes.
"""

from __future__ import annotations

from typing import Optional

from app.core.ports.outbound.text_generation_port import TextGenerationPort
from core.logging import get_logger

logger = get_logger(__name__)


class _GeminiTextGenerationAdapter:
    def __init__(self, model: str, api_key: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._client = genai.GenerativeModel(model)

    async def generate(self, prompt: str, system: Optional[str] = None, temperature: Optional[float] = None) -> str:
        import google.generativeai as genai

        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        config = genai.types.GenerationConfig(temperature=temperature) if temperature is not None else None
        response = await self._client.generate_content_async(full_prompt, generation_config=config)
        return (response.text or "").strip()


class _AnthropicTextGenerationAdapter:
    def __init__(self, model: str, api_key: str) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    async def generate(self, prompt: str, system: Optional[str] = None, temperature: Optional[float] = None) -> str:
        extra = {"temperature": temperature} if temperature is not None else {}
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system or "",
            messages=[{"role": "user", "content": prompt}],
            **extra,
        )
        return response.content[0].text


def build_text_generation_port(
    provider_code: str,
    model: str,
    api_key: str,
    base_url: str,
    timeout_seconds: Optional[int] = None,
) -> TextGenerationPort:
    if provider_code == "ollama":
        from app.adapters.driven.llm.openai_compatible_adapter import OpenAICompatibleAdapter
        from core.config import settings

        return OpenAICompatibleAdapter(
            base_url=base_url,
            model=model,
            api_key=api_key or None,
            timeout_seconds=timeout_seconds or getattr(settings, "ollama_request_timeout_seconds", 600),
        )
    if provider_code == "gemini":
        return _GeminiTextGenerationAdapter(model=model, api_key=api_key)
    if provider_code == "anthropic":
        return _AnthropicTextGenerationAdapter(model=model, api_key=api_key)

    raise ValueError(f"Unknown text-generation provider_code: {provider_code!r}")
