"""健康检查接口测试。"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import FastAPI
from httpx import AsyncClient

from app.db.session import get_db


class FakeSession:
    """仅实现 execute，用于替代真实 AsyncSession。"""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.executed = 0

    async def execute(self, *args: object, **kwargs: object) -> None:
        self.executed += 1
        if self.error is not None:
            raise self.error
        return None


def override_db(app: FastAPI, session: FakeSession) -> None:
    async def _get_test_db() -> AsyncIterator[FakeSession]:
        yield session

    app.dependency_overrides[get_db] = _get_test_db


async def test_root_returns_entry_links(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["docs"] == "/docs"
    assert body["health"] == "/api/v1/health"


async def test_liveness_does_not_touch_database(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "test"
    assert "database" not in body


async def test_health_ok_with_database(app: FastAPI, client: AsyncClient) -> None:
    session = FakeSession()
    override_db(app, session)
    try:
        response = await client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["database_error"] is None
    assert session.executed == 1


async def test_health_degraded_when_database_unavailable(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    session = FakeSession(error=RuntimeError("connection refused"))
    override_db(app, session)
    try:
        response = await client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["database"] == "unavailable"
    assert body["database_error"].startswith("RuntimeError")


async def test_readiness_returns_503_when_database_unavailable(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    session = FakeSession(error=RuntimeError("connection refused"))
    override_db(app, session)
    try:
        response = await client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
