from __future__ import annotations

import logging
from typing import Any

from core.config import Settings

logger = logging.getLogger(__name__)


def build_container(settings: Settings) -> dict[str, Any]:
    """
    Instancia todos os singletons (app-scoped) e retorna o container.

    Lê credenciais de `settings`; usa Mock/skip quando credenciais estão ausentes
    para que o servidor suba sem erro em qualquer ambiente.
    """
    _services_to_close: list = []

    # ------------------------------------------------------------------
    # LLM — seleção por settings.llm_provider
    # ------------------------------------------------------------------
    llm = _build_llm(settings)

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------
    from services.nlp.embedding_service import EmbeddingService
    from app.adapters.driven.nlp.embedding_adapter import EmbeddingAdapter

    embedding = EmbeddingAdapter(EmbeddingService(model_name=settings.llm_keybert_model))

    # ------------------------------------------------------------------
    # Search adapters + query builder adapters (feature-flagged)
    # ------------------------------------------------------------------
    patent_pairs: list[tuple[Any, Any]] = []
    scholarly_pairs: list[tuple[Any, Any]] = []

    # Lens (token único para patent e scholarly)
    if settings.lens_api_token and (settings.lens_patent_enabled or settings.lens_scholarly_enabled):
        from services.search.lens_service import LensService
        from app.adapters.driven.search.lens_patent_adapter import LensPatentAdapter
        from app.adapters.driven.search.lens_scholarly_adapter import LensScholarlyAdapter
        from app.adapters.driven.query_builders.lens_patent_query_builder_adapter import LensPatentQueryBuilderAdapter
        from app.adapters.driven.query_builders.lens_scholarly_query_builder_adapter import LensScholarlyQueryBuilderAdapter

        lens_service = LensService(api_token=settings.lens_api_token)
        _services_to_close.append(lens_service)

        if settings.lens_patent_enabled:
            patent_pairs.append((LensPatentAdapter(lens_service), LensPatentQueryBuilderAdapter()))
            logger.info("container_lens_patent_enabled")

        if settings.lens_scholarly_enabled:
            scholarly_pairs.append((LensScholarlyAdapter(lens_service), LensScholarlyQueryBuilderAdapter()))
            logger.info("container_lens_scholarly_enabled")
    else:
        logger.warning("container_lens_skipped lens_api_token=%s", bool(settings.lens_api_token))

    # OPS
    if settings.ops_enabled and settings.ops_consumer_key and settings.ops_consumer_secret:
        from services.search.ops_service import OPSService
        from app.adapters.driven.search.ops_adapter import OPSAdapter
        from app.adapters.driven.query_builders.ops_query_builder_adapter import OPSQueryBuilderAdapter

        from services.search.ops_token_manager import ops_token_manager

        ops_service = OPSService(
            consumer_key=settings.ops_consumer_key,
            consumer_secret=settings.ops_consumer_secret,
        )
        _services_to_close.append(ops_service)
        _services_to_close.append(ops_token_manager)
        patent_pairs.append((OPSAdapter(ops_service), OPSQueryBuilderAdapter()))
        logger.info("container_ops_enabled")
    else:
        logger.warning("container_ops_skipped ops_enabled=%s", settings.ops_enabled)

    # Scopus
    if settings.scopus_enabled and settings.scopus_api_key:
        from services.search.scopus_service import ScopusService
        from app.adapters.driven.search.scopus_adapter import ScopusAdapter
        from app.adapters.driven.query_builders.scopus_query_builder_adapter import ScopusQueryBuilderAdapter

        scopus_service = ScopusService(api_key=settings.scopus_api_key)
        _services_to_close.append(scopus_service)
        scholarly_pairs.append((ScopusAdapter(scopus_service), ScopusQueryBuilderAdapter()))
        logger.info("container_scopus_enabled")
    else:
        logger.warning("container_scopus_skipped scopus_enabled=%s", settings.scopus_enabled)

    # OpenAlex - complementa abstract que a Scopus Search API não devolve
    # pra essa API key (ver notes/pendencias.md). API pública, sem key.
    from services.search.openalex_service import OpenAlexService

    openalex_service = OpenAlexService()
    _services_to_close.append(openalex_service)

    # ------------------------------------------------------------------
    # Storage (MinIO) - armazenamento dos gráficos gerados pelo ReportService
    # ------------------------------------------------------------------
    from services.storage.minio_service import MinioService
    from app.adapters.driven.storage.minio_adapter import MinioStorageAdapter

    storage_service = MinioStorageAdapter(
        MinioService(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
    )

    # ------------------------------------------------------------------
    # Pure core services (sem dependências externas)
    # ------------------------------------------------------------------
    from app.core.services.dedup_service import DedupService
    from app.core.services.chat_service import ChatService
    from app.core.services.report_service import ReportService
    from app.core.services.statistical_inference_service import StatisticalInferenceService

    chat_service = ChatService(
        llm=llm,
        patent_pairs=patent_pairs,
        scholarly_pairs=scholarly_pairs,
        settings=settings,
        openalex=openalex_service,
    )
    report_service = ReportService(output_dir=settings.report_output_dir, storage=storage_service)
    inference_service = StatisticalInferenceService(
        chat_service=chat_service,
        embedding=embedding,
        settings=settings,
    )

    return {
        "llm": llm,
        "embedding": embedding,
        "patent_pairs": patent_pairs,
        "scholarly_pairs": scholarly_pairs,
        "services": {
            "dedup": DedupService(),
            "chat": chat_service,
            "report": report_service,
            "inference": inference_service,
            "storage": storage_service,
        },
        "_settings": settings,
        "_services_to_close": _services_to_close,
    }


async def shutdown_container(container: dict[str, Any]) -> None:
    for svc in container.get("_services_to_close", []):
        try:
            await svc.close()
            logger.info("container_service_closed", service=type(svc).__name__)
        except Exception as exc:
            logger.warning("container_service_close_failed",
                           service=type(svc).__name__, error=str(exc))


# ------------------------------------------------------------------
# Helpers privados
# ------------------------------------------------------------------

def _build_llm(settings: Settings):
    provider = (settings.llm_provider or "mock").lower()

    if provider == "anthropic" and settings.llm_anthropic_api_key:
        from services.llm.anthropic_service import AnthropicLLMService
        from app.adapters.driven.llm.anthropic_adapter import AnthropicLLMAdapter

        service = AnthropicLLMService(
            api_key=settings.llm_anthropic_api_key,
            model=settings.llm_anthropic_model,
        )
        logger.info("container_llm_provider=anthropic model=%s", settings.llm_anthropic_model)
        return AnthropicLLMAdapter(service)

    if provider == "gemini" and settings.llm_gemini_api_key:
        from services.llm.gemini_service import GeminiLLMService
        from app.adapters.driven.llm.gemini_adapter import GeminiLLMAdapter

        service = GeminiLLMService(
            api_key=settings.llm_gemini_api_key,
            model=settings.llm_gemini_model,
        )
        logger.info("container_llm_provider=gemini model=%s", settings.llm_gemini_model)
        return GeminiLLMAdapter(service)

    from services.llm.mock_service import MockLLMService
    from app.adapters.driven.llm.mock_adapter import MockLLMAdapter

    logger.warning("container_llm_provider=mock (provider=%s, keys_present=%s)",
                   provider, bool(settings.llm_anthropic_api_key or settings.llm_gemini_api_key))
    return MockLLMAdapter(MockLLMService())
