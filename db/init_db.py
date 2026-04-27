"""
Database initialization utility.

Handles table creation for both existing and research models.
Can be run as a standalone script or imported for application startup.
"""

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


async def init_db() -> None:
    """
    Inicializa o banco de dados criando todas as tabelas.

    Importa modelos de ambos os ficheiros (models.py e research_models.py)
    e cria as tabelas correspondentes.
    """
    try:
        # Importar os modelos para registar os metadados
        from db.models import Base as ModelsBase
        from db.models import PatentDedupRegistry, PatentDocument, ScholarlyDedupRegistry, ScholarlyDocument
        from db.research_models import (
            Base as ResearchBase,
            Research,
            ResearchMetrics,
            ResearchPatentDocument,
            ResearchPhase,
            ResearchScholarlyDocument,
        )

        logger.info("database_init_starting", models_loaded=9)

        # Construir URL do banco de dados
        db_url = _build_db_url()
        logger.info("database_init_url", url=_mask_password(db_url))

        # Criar engine para criar tabelas
        engine = create_async_engine(db_url, echo=settings.debug)

        # Criar tabelas do models.py
        async with engine.begin() as conn:
            logger.info("database_init_creating_existing_tables")
            await conn.run_sync(ModelsBase.metadata.create_all)

        # Criar tabelas do research_models.py
        async with engine.begin() as conn:
            logger.info("database_init_creating_research_tables")
            await conn.run_sync(ResearchBase.metadata.create_all)

        await engine.dispose()

        logger.info(
            "database_init_completed",
            models_count=len(ModelsBase.metadata.tables) + len(ResearchBase.metadata.tables),
        )

        print("\n[OK] Database initialized successfully!")
        print(f"[OK] Created {len(ModelsBase.metadata.tables)} tables from models.py")
        print(f"[OK] Created {len(ResearchBase.metadata.tables)} tables from research_models.py")

    except Exception as exc:
        logger.error("database_init_error", error=str(exc))
        print(f"\n[ERROR] Database initialization failed: {exc}")
        raise


def _build_db_url() -> str:
    """
    Constrói URL de conexão PostgreSQL assíncrona.

    Returns:
        URL para PostgreSQL com driver asyncpg.
    """
    db_url = getattr(settings, "database_url", None)

    if not db_url:
        logger.warning("DATABASE_URL not set, using in-memory SQLite")
        return "sqlite+aiosqlite:///:memory:"

    # Substituir postgresql:// por postgresql+asyncpg://
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://")
    elif db_url.startswith("postgres://"):
        return db_url.replace("postgres://", "postgresql+asyncpg://")

    return db_url


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


async def main() -> None:
    """
    Script principal para inicializar banco de dados.

    Uso: python -m db.init_db
    """
    print("\n" + "=" * 60)
    print("Database Initialization")
    print("=" * 60)

    try:
        await init_db()
        print("\n" + "=" * 60)
        print("Setup completed successfully!")
        print("=" * 60)
    except Exception as exc:
        print("\n" + "=" * 60)
        print(f"Setup failed: {exc}")
        print("=" * 60)
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
