"""
Database session and connection management.
"""

from typing import AsyncGenerator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


class DatabaseSession:
    """
    Gerenciador de sessão de banco de dados.

    Configura engine, pool de conexões e factory de sessões.
    """

    def __init__(self) -> None:
        """
        Inicializa o gerenciador de sessão.
        """
        self.engine: Optional[AsyncEngine] = None
        self.async_session_maker: Optional[sessionmaker] = None

    def initialize(self) -> None:
        """
        Inicializa engine e session factory.

        Configura pool de conexões baseado em ambiente.
        """
        # Construir URL de banco de dados
        db_url = self._build_db_url()

        logger.info("initializing_database", database_url=self._mask_password(db_url))

        # Criar engine assíncrono
        # TODO: Configurar pool_size e max_overflow baseado em load esperado
        # - Development: pool_size=5, max_overflow=10
        # - Production: pool_size=20, max_overflow=40
        # - High-concurrency: pool_size=50, max_overflow=100

        pool_class = QueuePool if settings.environment == "production" else NullPool
        pool_pre_ping = True  # Validate connections before using

        self.engine = create_async_engine(
            db_url,
            echo=settings.debug,
            poolclass=pool_class,
            pool_pre_ping=pool_pre_ping,
            future=True,
        )

        # Criar factory de sessões assíncronas
        self.async_session_maker = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

        logger.info("database_engine_initialized", environment=settings.environment)

    async def close(self) -> None:
        """
        Fecha engine e conexões.
        """
        if self.engine:
            await self.engine.dispose()
            logger.info("database_engine_closed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Fornece sessão de banco de dados como context manager.

        Yield:
            AsyncSession para uso na rota.
        """
        if not self.async_session_maker:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception as exc:
                await session.rollback()
                logger.error(f"Session error: {exc}")
                raise
            finally:
                await session.close()

    def _build_db_url(self) -> str:
        """
        Constrói URL de conexão PostgreSQL assíncrona.

        Returns:
            URL para PostgreSQL com driver asyncpg.
        """
        # TODO: Suportar outros bancos (MySQL, SQLite para dev)
        db_url = getattr(settings, "database_url", None)

        if not db_url:
            # Fallback para SQLite em memória para testes
            logger.warning("DATABASE_URL not set, using in-memory SQLite")
            return "sqlite+aiosqlite:///:memory:"

        # Substituir postgresql:// por postgresql+asyncpg://
        if db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+asyncpg://")
        elif db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql+asyncpg://")

        return db_url

    @staticmethod
    def _mask_password(url: str) -> str:
        """
        Mascara senha na URL para logging.

        Args:
            url: URL de banco de dados.

        Returns:
            URL com senha mascarada.
        """
        if "@" in url:
            before, after = url.split("@", 1)
            if ":" in before:
                prefix, _ = before.rsplit(":", 1)
                return f"{prefix}:***@{after}"
        return url


# Instância global
db_session = DatabaseSession()
