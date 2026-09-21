"""
Registry de providers de IA suportados pelo código - o ponto de extensão da
migração de configuração pro banco (ver PLANO_MIGRACAO_CONFIG_BANCO.md).

Por que um dict Python em vez de mais uma tabela de banco: suportar um
provider novo (ex: "OpenAI") sempre exige escrever uma classe adapter nova -
não tem como "configurar" isso só com dados. Então o "quais providers
existem" é uma decisão de código (Open/Closed: adicionar = 1 entrada aqui +
1 classe, sem tocar em LLMConfigResolver/schema/endpoints existentes); só a
INSTÂNCIA configurada (model/api_key/base_url) precisa viver no banco
(db.config_models.LLMProviderConfig).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.core.ports.outbound.llm_port import LLMPort


@dataclass(frozen=True)
class LLMProviderSpec:
    display_name: str
    requires_api_key: bool
    requires_base_url: bool
    factory: Callable[[str, str, str], LLMPort]  # (model, api_key, base_url) -> LLMPort


def _build_gemini(model: str, api_key: str, base_url: str) -> LLMPort:
    from services.llm.gemini_service import GeminiLLMService
    from app.adapters.driven.llm.gemini_adapter import GeminiLLMAdapter

    return GeminiLLMAdapter(GeminiLLMService(api_key=api_key, model=model))


def _build_anthropic(model: str, api_key: str, base_url: str) -> LLMPort:
    from services.llm.anthropic_service import AnthropicLLMService
    from app.adapters.driven.llm.anthropic_adapter import AnthropicLLMAdapter

    return AnthropicLLMAdapter(AnthropicLLMService(api_key=api_key, model=model))


def _build_ollama(model: str, api_key: str, base_url: str) -> LLMPort:
    from services.llm.ollama_service import OllamaLLMService
    from app.adapters.driven.llm.ollama_adapter import OllamaLLMAdapter
    from core.config import settings

    timeout_seconds = getattr(settings, "ollama_request_timeout_seconds", 600)
    return OllamaLLMAdapter(
        OllamaLLMService(base_url=base_url, model=model, api_key=api_key or None, timeout_seconds=timeout_seconds)
    )


LLM_PROVIDER_REGISTRY: dict[str, LLMProviderSpec] = {
    "gemini": LLMProviderSpec(
        display_name="Google Gemini",
        requires_api_key=True,
        requires_base_url=False,
        factory=_build_gemini,
    ),
    "anthropic": LLMProviderSpec(
        display_name="Anthropic Claude",
        requires_api_key=True,
        requires_base_url=False,
        factory=_build_anthropic,
    ),
    "ollama": LLMProviderSpec(
        display_name="Ollama / compatível OpenAI",
        requires_api_key=False,
        requires_base_url=True,
        factory=_build_ollama,
    ),
}


def build_llm_port(provider_code: str, model: str, api_key: str, base_url: str) -> LLMPort:
    spec = LLM_PROVIDER_REGISTRY.get(provider_code)
    if spec is None:
        raise ValueError(f"Unknown LLM provider_code: {provider_code!r}")
    return spec.factory(model, api_key, base_url)
