"""测试公共夹具：单元测试不触碰数据库，集成测试使用独立测试库。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 - 注册 ORM 模型
from app.core.config import Settings, get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        debug=True,
        secret_key="test-secret-key-for-unit-tests-only",
        database_url="postgresql+asyncpg://tester:secret@127.0.0.1:5432/resume_platform_test",
        test_database_url="",
        upload_dir=tmp_path / "uploads",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = get_settings().test_database_url
    if not url:
        pytest.skip("未配置 TEST_DATABASE_URL，跳过需要数据库的集成测试")
    database = make_url(url).database or ""
    if "test" not in database:
        pytest.fail(f"TEST_DATABASE_URL 必须指向测试数据库，当前库名：{database}")
    return url


@pytest_asyncio.fixture
async def db_engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    """每个测试重建表，保证用例之间完全隔离。"""
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture
def db_session_factory(db_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with db_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def auth_app(
    settings: Settings,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> Iterator[FastAPI]:
    application = create_app(settings)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with db_session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(auth_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
