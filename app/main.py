"""
Main FastAPI application initialization and startup configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, intake, test
from core.config import settings
from core.logging import configure_logging, get_logger
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
    db_session.initialize()

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
    app.include_router(intake.router, prefix=settings.api_prefix)
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

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """
        Handler executado ao desligar a aplicação.
        """
        await db_session.close()
        logger.info("application_shutdown", app_name=settings.app_name)

    return app


# Criar instância global da aplicação
app = create_app()
