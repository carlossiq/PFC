"""
Main FastAPI application initialization and startup configuration.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.driving.http import (
    chat_router,
    config_router,
    health_router,
    inference_router,
    report_document_router,
    report_router,
    research_session,
    session_input,
)
from app.container import build_container, shutdown_container
from app.core.services.report_static_figures import ensure_static_figures_uploaded
from core.config import settings
from core.logging import configure_logging, get_logger
from db.init_db import init_db
from db.session import db_session
from app.adapters.driving.http.middleware.request_logging import (
    RequestLoggingMiddleware,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    try:
        db_session.initialize()
        logger.info("database_session_initialized")
    except Exception as exc:
        logger.error("database_session_initialization_failed", error=str(exc))
        raise

    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        debug=settings.debug,
    )

    try:
        await init_db()
        logger.info("database_tables_initialized")
    except Exception as exc:
        logger.error("database_initialization_failed", error=str(exc))
        raise

    # Sincroniza app_settings (banco) -> singleton `settings` ANTES de montar
    # o container - container.py lê settings.ops_consumer_key/scopus_api_key/
    # etc pra decidir quais adapters instanciar, então precisa já refletir o
    # banco (não só o .env) nesse ponto. Ver
    # app/core/services/settings_sync_service.py.
    try:
        from app.adapters.driven.persistence.config_repository_adapter import (
            AppSettingsRepositoryAdapter,
        )
        from app.core.services.settings_sync_service import SettingsSyncService

        async with db_session.async_session_maker() as session:
            await SettingsSyncService(AppSettingsRepositoryAdapter(session)).load_all_into_singleton()
        logger.info("app_settings_synced_into_singleton")
    except Exception as exc:
        logger.error("app_settings_sync_failed", error=str(exc))
        raise

    # build_container é assíncrono desde a migração de config pro banco -
    # precisa ler search_api_selection (só pode acontecer depois do banco
    # pronto acima). Nunca mais na importação do módulo (era assim antes).
    app.state.container = await build_container(settings)

    # MinIO fora do ar não deve impedir o app de subir - a persistência dos
    # gráficos gerados é melhor-esforço (ver ReportService), não um
    # requisito pro resto do app funcionar.
    try:
        await app.state.container["services"]["storage"].ensure_bucket()
        logger.info("minio_bucket_ready")
        await ensure_static_figures_uploaded(app.state.container["services"]["storage"])
    except Exception as exc:
        logger.warning("minio_bucket_ensure_failed", error=str(exc))

    yield

    await shutdown_container(app.state.container)

    try:
        await db_session.close()
    except Exception as exc:
        logger.error("database_session_close_failed", error=str(exc))
    finally:
        logger.info("application_shutdown", app_name=settings.app_name)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API for technology prospecting and analysis",
        debug=settings.debug,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Front e API em origens diferentes: sem isso o navegador esconde o
        # Content-Disposition do JS e o download do .zip do relatório perde
        # o nome ("REPTEC_001_2026.zip", ver /report/{id}/bundle).
        expose_headers=["Content-Disposition"],
    )

    # Request logging middleware (deve ser adicionado por último para ser primeiro na cadeia)
    app.add_middleware(RequestLoggingMiddleware)

    # Rotas v2 (hexágono) - app.state.container é montado dentro do
    # lifespan (build_container é assíncrono, precisa do banco pronto -
    # ver comentário em lifespan() acima), não aqui.
    routers = (
        chat_router.router,
        session_input.router,
        research_session.router,
        report_router.router,
        report_document_router.router,
        inference_router.router,
        config_router.router,
        health_router.router,  # infraestrutura
    )
    for router in routers:
        app.include_router(router, prefix=settings.api_prefix)

    logger.info(
        "routes_registered",
        routers=len(routers),
        endpoints=sum(1 for _ in app.routes),
    )

    return app


# Criar instância global da aplicação
app = create_app()
