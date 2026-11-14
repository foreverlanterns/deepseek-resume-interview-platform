"""JD 管理接口测试。"""

from __future__ import annotations

from httpx import AsyncClient

PASSWORD = "StrongPass123"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register_and_login(client: AsyncClient, email: str) -> str:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "JD 用户"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def payload(title: str = "后端开发工程师") -> dict[str, object]:
    return {
        "title": title,
        "company": "某科技公司",
        "raw_text": "负责后端服务开发，要求熟悉 Python、FastAPI 和 PostgreSQL。",
        "required_skills": ["Python", "FastAPI"],
        "preferred_skills": ["Docker"],
        "keywords": ["PostgreSQL"],
        "responsibilities": ["开发后端服务"],
        "qualifications": ["本科及以上"],
    }


async def test_create_list_get_update_delete_jd(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "jd@example.com")

    created = await auth_client.post(
        "/api/v1/jds",
        headers=bearer(token),
        json=payload(),
    )
    assert created.status_code == 201
    body = created.json()
    jd_id = body["id"]
    assert body["title"] == "后端开发工程师"
    assert body["required_skills"] == ["Python", "FastAPI"]
    assert body["company"] == "某科技公司"

    listing = await auth_client.get("/api/v1/jds", headers=bearer(token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    detail = await auth_client.get(f"/api/v1/jds/{jd_id}", headers=bearer(token))
    assert detail.status_code == 200
    assert detail.json()["keywords"] == ["PostgreSQL"]

    updated = await auth_client.put(
        f"/api/v1/jds/{jd_id}",
        headers=bearer(token),
        json={**payload("高级后端开发工程师"), "required_skills": ["Python", "Go"]},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "高级后端开发工程师"
    assert updated.json()["required_skills"] == ["Python", "Go"]

    deleted = await auth_client.delete(f"/api/v1/jds/{jd_id}", headers=bearer(token))
    assert deleted.status_code == 204
    assert deleted.content == b""
    missing = await auth_client.get(f"/api/v1/jds/{jd_id}", headers=bearer(token))
    assert missing.status_code == 404


async def test_jd_is_isolated_by_user(auth_client: AsyncClient) -> None:
    owner = await register_and_login(auth_client, "jd-owner@example.com")
    other = await register_and_login(auth_client, "jd-other@example.com")
    created = await auth_client.post("/api/v1/jds", headers=bearer(owner), json=payload())
    jd_id = created.json()["id"]

    listing = await auth_client.get("/api/v1/jds", headers=bearer(other))
    detail = await auth_client.get(f"/api/v1/jds/{jd_id}", headers=bearer(other))
    update = await auth_client.put(
        f"/api/v1/jds/{jd_id}",
        headers=bearer(other),
        json=payload("篡改"),
    )
    delete = await auth_client.delete(f"/api/v1/jds/{jd_id}", headers=bearer(other))

    assert listing.json() == []
    assert detail.status_code == 404
    assert update.status_code == 404
    assert delete.status_code == 404


async def test_jd_rejects_empty_title(auth_client: AsyncClient) -> None:
    token = await register_and_login(auth_client, "jd-invalid@example.com")

    response = await auth_client.post(
        "/api/v1/jds",
        headers=bearer(token),
        json={**payload(), "title": ""},
    )

    assert response.status_code == 422


async def test_jd_requires_auth(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/jds")
    assert response.status_code == 401
