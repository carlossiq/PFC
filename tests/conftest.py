"""
Pytest configuration and shared fixtures.
"""

import os
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base
from db.session import DatabaseSession


@pytest.fixture(scope="session")
def event_loop():
    """
    Fornece event loop para testes async.
    """
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_session_maker():
    """
    Cria session maker para testes com banco em memória.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    yield async_session

    await engine.dispose()


@pytest.fixture
async def db_session(async_session_maker) -> AsyncGenerator[AsyncSession, None]:
    """
    Fornece sessão de banco para testes.
    """
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def test_mode_enabled(monkeypatch):
    """
    Ativa TEST_MODE para testes.
    """
    monkeypatch.setenv("TEST_MODE", "true")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
