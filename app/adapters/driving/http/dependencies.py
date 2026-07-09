"""
FastAPI dependency injection for HTTP adapters.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from db.session import db_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with db_session.async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
