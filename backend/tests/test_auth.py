"""认证接口集成测试（使用独立 PostgreSQL 测试库）。"""

from __future__ import annotations

from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import verify_password
from app.models.user import User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

EMAIL = "student@example.com"
PASSWORD = "StrongPass123"


async def register(
    client: AsyncClient,
    *,
    email: str = EMAIL,
    password: str = PASSWORD,
    display_name: str | None = "小明",
) -> Response:
    return await client.post(
        REGISTER_URL,
        json={"email": email, "password": password, "display_name": display_name},
    )


async def login(client: AsyncClient, *, email: str = EMAIL, password: str = PASSWORD) -> Response:
    return await client.post(LOGIN_URL, json={"email": email, "password": password})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_register_normalizes_email_and_hides_password(
    auth_client: AsyncClient,
) -> None:
    response = await register(auth_client, email="Student@Example.COM", display_name=" 小明 ")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "student@example.com"
    assert body["display_name"] == "小明"
    assert body["is_active"] is True
    assert "password" not in body
    assert "password_hash" not in body
    assert body["id"]


async def test_register_duplicate_email_is_case_insensitive(
    auth_client: AsyncClient,
) -> None:
    assert (await register(auth_client)).status_code == 201

    response = await register(auth_client, email="STUDENT@example.com")

    assert response.status_code == 409
    assert response.json()["detail"] == "该邮箱已注册"


async def test_register_rejects_short_password(auth_client: AsyncClient) -> None:
    response = await register(auth_client, password="short")

    assert response.status_code == 422


async def test_register_rejects_invalid_email(auth_client: AsyncClient) -> None:
    response = await register(auth_client, email="not-an-email")

    assert response.status_code == 422


async def test_login_returns_token_and_me_returns_user(
    auth_client: AsyncClient,
    settings: Settings,
) -> None:
    await register(auth_client)

    response = await login(auth_client, email="STUDENT@example.com")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_expire_minutes * 60
    assert body["access_token"]

    me = await auth_client.get(ME_URL, headers=bearer(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == EMAIL


async def test_me_requires_token(auth_client: AsyncClient) -> None:
    response = await auth_client.get(ME_URL)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_rejects_invalid_token(auth_client: AsyncClient) -> None:
    response = await auth_client.get(ME_URL, headers=bearer("not-a-valid-token"))

    assert response.status_code == 401
    assert response.json()["detail"] == "无效的登录凭证"


async def test_login_rejects_wrong_password(auth_client: AsyncClient) -> None:
    await register(auth_client)

    response = await login(auth_client, password="WrongPass123")

    assert response.status_code == 401
    assert response.json()["detail"] == "邮箱或密码错误"


async def test_login_does_not_reveal_unknown_email(auth_client: AsyncClient) -> None:
    response = await login(auth_client, email="nobody@example.com")

    assert response.status_code == 401
    assert response.json()["detail"] == "邮箱或密码错误"


async def test_password_is_hashed_in_database(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await register(auth_client)

    result = await db_session.execute(select(User).where(User.email == EMAIL))
    user = result.scalar_one()

    assert user.password_hash != PASSWORD
    assert user.password_hash.startswith("$argon2")
    assert verify_password(PASSWORD, user.password_hash) is True


async def test_inactive_user_cannot_login(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await register(auth_client)

    result = await db_session.execute(select(User).where(User.email == EMAIL))
    user = result.scalar_one()
    user.is_active = False
    await db_session.commit()

    response = await login(auth_client)

    assert response.status_code == 401
    assert response.json()["detail"] == "邮箱或密码错误"
