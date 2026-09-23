from __future__ import annotations

from typing import Any

from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)


async def build_container(settings: Settings) -> dict[str, Any]:
    """
    Instancia todos os singletons (app-scoped) e retorna o container.

    Lê credenciais de `settings`; usa Mock/skip quando credenciais estão ausentes
    para que o servidor suba sem erro em qualquer ambiente.

    Assíncrono desde a migração de configuração pro banco
    (PLANO_MIGRACAO_CONFIG_BANCO.md): precisa ler `search_api_selection`
    antes de decidir qual adapter de patente/artigo montar. Por isso só pode
    ser chamado de dentro do lifespan do FastAPI, depois de
    `db_session.initialize()` + `init_db()` - nunca na importação do módulo
    (era assim antes; ver app/main.py).
    """
    _services_to_close: list = []

    # ------------------------------------------------------------------
    # LLM — resolver por call site (theme_candidates/probe_query/
    # final_query/report_writing), configurável no banco (llm_provider_configs
    # + llm_call_site_bindings) em vez de um único settings.llm_provider global.
    # ------------------------------------------------------------------
    from db.session import db_session
    from app.core.services.llm_config_resolver import LLMConfigResolver

    llm_resolver = LLMConfigResolver(session_factory=db_session.async_session_maker)

    # ------------------------------------------------------------------
    # Embedding
    # ------------------------------------------------------------------
    from services.nlp.embedding_service import EmbeddingService
    from app.adapters.driven.nlp.embedding_adapter import EmbeddingAdapter

    embedding = EmbeddingAdapter(EmbeddingService(model_name=settings.llm_keybert_model))

    # ------------------------------------------------------------------
    # Search adapters + query builder adapters - um único adapter por
    # família (patent/scholarly), decidido por search_api_selection (banco)
    # em vez dos antigos 5 booleans independentes (que permitiam OPS e Lens
    # Patent registrados ao mesmo tempo - ver PLANO_MIGRACAO_CONFIG_BANCO.md
    # § "search_api_selection"). Falta de credencial pro provider ativo =
    # família inteira fica sem adapter (loga aviso), não cai pro outro
    # provider da família silenciosamente.
    # ------------------------------------------------------------------
    patent_pairs: list[tuple[Any, Any]] = []
    scholarly_pairs: list[tuple[Any, Any]] = []

    async with db_session.async_session_maker() as session:
        from app.adapters.driven.persistence.config_repository_adapter import (
            SearchApiSelectionRepositoryAdapter,
        )

        search_api_repo = SearchApiSelectionRepositoryAdapter(session)
        patent_selection = await search_api_repo.get("patent")
        scholarly_selection = await search_api_repo.get("scholarly")

    patent_active = patent_selection.active_provider_code if patent_selection else "ops"
    scholarly_active = scholarly_selection.active_provider_code if scholarly_selection else "scopus"

    lens_service = None

    def _get_lens_service():
        nonlocal lens_service
        if lens_service is None:
            from services.search.lens_service import LensService

            lens_service = LensService(api_token=settings.lens_api_token)
            _services_to_close.append(lens_service)
        return lens_service

    if patent_active == "ops":
        if settings.ops_consumer_key and settings.ops_consumer_secret:
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
            logger.info("container_patent_api_active provider=ops")
        else:
            logger.warning("container_patent_api_skipped provider=ops reason=missing_credentials")
    elif patent_active == "lens_patent":
        if settings.lens_api_token:
            from app.adapters.driven.search.lens_patent_adapter import LensPatentAdapter
            from app.adapters.driven.query_builders.lens_patent_query_builder_adapter import (
                LensPatentQueryBuilderAdapter,
            )

            patent_pairs.append((LensPatentAdapter(_get_lens_service()), LensPatentQueryBuilderAdapter()))
            logger.info("container_patent_api_active provider=lens_patent")
        else:
            logger.warning("container_patent_api_skipped provider=lens_patent reason=missing_credentials")
    else:
        logger.warning("container_patent_api_unknown provider=%s", patent_active)

    if scholarly_active == "scopus":
        if settings.scopus_api_key:
            from services.search.scopus_service import ScopusService
            from app.adapters.driven.search.scopus_adapter import ScopusAdapter
            from app.adapters.driven.query_builders.scopus_query_builder_adapter import ScopusQueryBuilderAdapter

            scopus_service = ScopusService(api_key=settings.scopus_api_key)
            _services_to_close.append(scopus_service)
            scholarly_pairs.append((ScopusAdapter(scopus_service), ScopusQueryBuilderAdapter()))
            logger.info("container_scholarly_api_active provider=scopus")
        else:
            logger.warning("container_scholarly_api_skipped provider=scopus reason=missing_credentials")
    elif scholarly_active == "lens_scholarly":
        if settings.lens_api_token:
            from app.adapters.driven.search.lens_scholarly_adapter import LensScholarlyAdapter
            from app.adapters.driven.query_builders.lens_scholarly_query_builder_adapter import (
                LensScholarlyQueryBuilderAdapter,
            )

            scholarly_pairs.append(
                (LensScholarlyAdapter(_get_lens_service()), LensScholarlyQueryBuilderAdapter())
            )
            logger.info("container_scholarly_api_active provider=lens_scholarly")
        else:
            logger.warning("container_scholarly_api_skipped provider=lens_scholarly reason=missing_credentials")
    else:
        logger.warning("container_scholarly_api_unknown provider=%s", scholarly_active)

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
    # RAG (ChromaDB) - contexto por seção do relatório (ReportWriterService).
    # Best-effort: HttpClient conecta no __init__, então se o container
    # `chromadb` não estiver no ar, `rag_service` fica None (log de aviso)
    # em vez de derrubar a subida do app - mesmo espírito dos demais
    # serviços opcionais acima (Lens/OPS/Scopus). Nesse caso só a rota de
    # RAG por seção fica indisponível (503); o resto do app funciona normal.
    # ------------------------------------------------------------------
    from app.core.services.rag_service import RAGService
    from app.adapters.driven.storage.chroma_adapter import ChromaVectorStoreAdapter

    rag_service: Any = None
    try:
        vector_store = ChromaVectorStoreAdapter(
            host=settings.chroma_host,
            port=settings.chroma_port,
            embedding=embedding,
        )
        rag_service = RAGService(vector_store)
        logger.info("container_chromadb_connected host=%s port=%s", settings.chroma_host, settings.chroma_port)
    except Exception as exc:
        logger.warning("container_chromadb_unavailable error=%s", exc)

    # ------------------------------------------------------------------
    # Pure core services (sem dependências externas)
    # ------------------------------------------------------------------
    from app.core.services.dedup_service import DedupService
    from app.core.services.chat_service import ChatService
    from app.core.services.report_service import ReportService
    from app.core.services.report_writer_service import ReportWriterService
    from app.core.services.report_latex_service import ReportLatexService
    from app.core.services.statistical_inference_service import StatisticalInferenceService

    chat_service = ChatService(
        llm_resolver=llm_resolver,
        patent_pairs=patent_pairs,
        scholarly_pairs=scholarly_pairs,
        settings=settings,
        openalex=openalex_service,
    )
    report_service = ReportService(storage=storage_service)
    report_writer_service = ReportWriterService(
        rag=rag_service,
        llm_resolver=llm_resolver,
        settings=settings,
    )
    report_latex_service = ReportLatexService(
        storage=storage_service,
        latex_compiler_url=settings.latex_compiler_url,
    )
    _services_to_close.append(report_latex_service)
    inference_service = StatisticalInferenceService(
        chat_service=chat_service,
        embedding=embedding,
        settings=settings,
    )

    return {
        "llm_resolver": llm_resolver,
        "embedding": embedding,
        "patent_pairs": patent_pairs,
        "scholarly_pairs": scholarly_pairs,
        "services": {
            "dedup": DedupService(),
            "chat": chat_service,
            "report": report_service,
            "report_writer": report_writer_service,
            "report_latex": report_latex_service,
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


