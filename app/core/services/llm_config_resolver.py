"""
Resolve qual LLMPort usar pra cada call site (theme_candidates/probe_query/
final_query/report_writing) - ver PLANO_MIGRACAO_CONFIG_BANCO.md § 2 e § 4.3.

Cacheado em memória por call_site (instanciar um client de IA - SDK, conexão
httpx - a cada chamada seria desperdício); invalidado quando o binding
daquele call site ou a config apontada por ele muda (ver invalidate/
invalidate_all, chamados pelos endpoints de escrita em config_router.py).
"""

from __future__ import annotations

from typing import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.driven.llm.provider_registry import build_llm_port
from app.adapters.driven.llm.text_generation_registry import build_text_generation_port
from app.core.ports.outbound.llm_port import LLMPort
from app.core.ports.outbound.text_generation_port import TextGenerationPort
from core.logging import get_logger

logger = get_logger(__name__)

CALL_SITES = ("theme_candidates", "probe_query", "final_query", "report_writing")


class LLMConfigResolver:
    """
    `resolve` serve os 3 call sites de query estruturada (LLMPort:
    process_intake/call_raw_json). `report_writing` usa um contrato
    diferente (TextGenerationPort: texto livre, sem JSON) - ver
    resolve_text_generation. Dois caches separados porque são dois
    protocolos diferentes, mesmo a config (LLMProviderConfig) sendo a
    mesma tabela pros dois casos.

    Recebe uma FACTORY de sessão (não uma sessão/repository já aberta): o
    resolver vive por todo o processo (é injetado uma vez no container),
    mas só precisa do banco no cache-miss (primeira resolução de cada call
    site, ou logo após invalidate) - abrir uma sessão nova a cada cache-miss
    evita depender de uma sessão de vida longa, que o SQLAlchemy async não
    suporta bem fora do escopo de uma request.
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory
        self._cache: dict[str, LLMPort] = {}
        self._text_generation_cache: dict[str, TextGenerationPort] = {}

    async def _resolve_config(self, call_site: str):
        from app.adapters.driven.persistence.config_repository_adapter import LLMConfigRepositoryAdapter

        async with self._session_factory() as session:
            repository = LLMConfigRepositoryAdapter(session)
            binding = await repository.get_binding(call_site)
            if binding is None:
                raise RuntimeError(f"No LLM binding configured for call_site={call_site!r}")

            config = await repository.get_config(binding.config_id)
            if config is None:
                raise RuntimeError(
                    f"call_site={call_site!r} points to missing LLMProviderConfig id={binding.config_id}"
                )
            return config

    async def resolve(self, call_site: str) -> LLMPort:
        cached = self._cache.get(call_site)
        if cached is not None:
            return cached

        config = await self._resolve_config(call_site)
        port = build_llm_port(config.provider_code, config.model, config.api_key, config.base_url)
        self._cache[call_site] = port
        logger.info("llm_resolver_built", call_site=call_site, provider=config.provider_code, model=config.model)
        return port

    async def resolve_text_generation(self, call_site: str) -> TextGenerationPort:
        cached = self._text_generation_cache.get(call_site)
        if cached is not None:
            return cached

        config = await self._resolve_config(call_site)
        port = build_text_generation_port(config.provider_code, config.model, config.api_key, config.base_url)
        self._text_generation_cache[call_site] = port
        logger.info(
            "llm_resolver_text_generation_built",
            call_site=call_site,
            provider=config.provider_code,
            model=config.model,
        )
        return port

    def invalidate(self, call_site: str) -> None:
        self._cache.pop(call_site, None)
        self._text_generation_cache.pop(call_site, None)

    def invalidate_all(self) -> None:
        self._cache.clear()
        self._text_generation_cache.clear()
