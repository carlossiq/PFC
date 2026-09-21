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
from db.session import db_session

logger = get_logger(__name__)


async def init_db() -> None:
    """
    Inicializa o banco de dados criando todas as tabelas.

    Importa modelos de ambos os ficheiros (models.py e research_models.py)
    e cria as tabelas correspondentes usando engine existente de db_session.
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
        from db.config_models import (
            Base as ConfigBase,
            AppSetting,
            LLMCallSiteBinding,
            LLMProviderConfig,
            SearchApiSelection,
        )

        logger.info("database_init_starting", models_loaded=13)

        # Usar engine já inicializado em db_session
        if db_session.engine is None:
            raise RuntimeError("Database engine not initialized. Call db_session.initialize() first.")

        engine = db_session.engine

        # Criar tabelas do models.py
        async with engine.begin() as conn:
            logger.info("database_init_creating_existing_tables")
            await conn.run_sync(ModelsBase.metadata.create_all)

        # Criar tabelas do research_models.py
        async with engine.begin() as conn:
            logger.info("database_init_creating_research_tables")
            await conn.run_sync(ResearchBase.metadata.create_all)

        # Criar tabelas de configuração editável (config_models.py) - mesmo
        # padrão create_all de models.py/research_models.py (não Alembic),
        # seguido de um seed idempotente a partir dos valores hoje em
        # core/config.py (ver db/config_seed.py).
        async with engine.begin() as conn:
            logger.info("database_init_creating_config_tables")
            await conn.run_sync(ConfigBase.metadata.create_all)

        from db.config_seed import seed_all_config

        async with db_session.async_session_maker() as session:
            await seed_all_config(session)

        # research_session_models.py (research_session/session_input) é gerido
        # pelo Alembic, não pelo create_all daqui.

        logger.info(
            "database_init_completed",
            models_count=len(ModelsBase.metadata.tables)
            + len(ResearchBase.metadata.tables)
            + len(ConfigBase.metadata.tables),
        )

        print("\n[OK] Database initialized successfully!")
        print(f"[OK] Created {len(ModelsBase.metadata.tables)} tables from models.py")
        print(f"[OK] Created {len(ResearchBase.metadata.tables)} tables from research_models.py")
        print(f"[OK] Created {len(ConfigBase.metadata.tables)} tables from config_models.py")

    except Exception as exc:
        logger.error("database_init_error", error=str(exc))
        print(f"\n[ERROR] Database initialization failed: {exc}")
        raise



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
