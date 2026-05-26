"""
Main FastAPI application initialization and startup configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, health, reports, research, test
from api.routes.reports import initialize_services
from core.config import settings
from core.logging import configure_logging, get_logger
from db.init_db import init_db
from db.session import db_session
from middleware.request_logging import RequestLoggingMiddleware

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """
    Cria e configura a instância da aplicação FastAPI com middlewares,
    rotas e configurações de produção.

    Returns:
        Instância configurada da aplicação FastAPI.
    """
    # Inicializar logging
    configure_logging()

    # Inicializar banco de dados
    try:
        db_session.initialize()
        logger.info("database_session_initialized")
    except Exception as exc:
        logger.error("database_session_initialization_failed", error=str(exc))
        raise

    # Criar aplicação FastAPI
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API for technology prospecting and analysis",
        debug=settings.debug,
    )

    # Adicionar middlewares
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

    # Incluir rotas
    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(chat.router, prefix=settings.api_prefix)
    app.include_router(research.router, prefix=settings.api_prefix)
    app.include_router(reports.router, prefix=settings.api_prefix)
    app.include_router(test.router, prefix=settings.api_prefix)

    # Event handlers
    @app.on_event("startup")
    async def startup_event() -> None:
        """
        Handler executado ao iniciar a aplicação.
        """
        logger.info(
            "application_startup",
            app_name=settings.app_name,
            version=settings.app_version,
            environment=settings.environment,
            debug=settings.debug,
        )

        # Initialize database tables
        try:
            await init_db()
            logger.info("database_tables_initialized")
        except Exception as exc:
            logger.error("database_initialization_failed", error=str(exc))
            raise

        # Initialize report generation services (Ollama + RAG)
        try:
            success = await initialize_services()
            if success:
                logger.info("report_services_initialized")
            else:
                logger.warning("report_services_not_available")
        except Exception as exc:
            logger.warning("report_services_initialization_failed", error=str(exc))

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """
        Handler executado ao desligar a aplicação.
        """
        try:
            await db_session.close()
        except Exception as exc:
            logger.error("database_session_close_failed", error=str(exc))
        finally:
            logger.info("application_shutdown", app_name=settings.app_name)

    return app


# Criar instância global da aplicação
app = create_app()
