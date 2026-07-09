"""
Main FastAPI application initialization and startup configuration.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.adapters.driving.http import (
    chat_router,
    health_router,
    report_router,
    research_router,
    test_router,
)
from app.container import build_container, shutdown_container
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
    )

    # Request logging middleware (deve ser adicionado por último para ser primeiro na cadeia)
    app.add_middleware(RequestLoggingMiddleware)

    # Rotas v2 (hexágono)
    _container = build_container(settings)
    app.state.container = _container
    app.include_router(research_router.router, prefix=settings.api_prefix)
    app.include_router(report_router.router, prefix=settings.api_prefix)
    app.include_router(chat_router.router, prefix=settings.api_prefix)

    # Infraestrutura
    app.include_router(health_router.router, prefix=settings.api_prefix)
    app.include_router(test_router.router, prefix=settings.api_prefix)

    return app


# Criar instância global da aplicação
app = create_app()
