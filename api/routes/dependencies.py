"""
Dependency injection for FastAPI routes.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from db.session import db_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fornece sessão de banco de dados para rotas.

    Yield:
        AsyncSession para operações de banco de dados.
    """
    async with db_session.async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
