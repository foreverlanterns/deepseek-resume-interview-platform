"""结构化解析与版本接口集成测试（使用假 Provider）。"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator
from copy import deepcopy
from typing import Any

import pymupdf
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from app.api.deps import get_json_provider
from app.providers.base import ProviderNotConfiguredError

PASSWORD = "StrongPass123"
DEFAULT_TEXT = (
    "Zhang San\nBackend Engineer\nPython FastAPI PostgreSQL Docker\nEmail: zhang@example.com"
)

VALID_DATA: dict[str, Any] = {
    "basic_info": {
        "name": "张三",
        "email": "zhang@example.com",
        "headline": "后端开发工程师",
        "source_text": "张三 后端开发工程师",
    },
    "summary": "后端开发工程师",
    "education": [
        {
            "school": "某某大学",
            "degree": "本科",
            "major": "计算机科学与技术",
            "start_date": "2020.09",
            "end_date": "2024.06",
            "details": ["主修数据库"],
            "source_text": "2020.09-2024.06 某某大学 计算机科学与技术 本科",
        }
    ],
    "work_experience": [],
    "projects": [
        {
            "name": "简历诊断平台",
            "role": "后端开发",
            "tech_stack": ["Python", "FastAPI"],
            "highlights": ["实现 JWT 认证"],
            "source_text": "简历诊断平台 后端开发 Python FastAPI",
        }
    ],
    "skills": [{"category": "编程语言", "items": ["Python", "Java"]}],
    "certificates": [],
    "awards": [],
    "languages": [{"name": "英语", "level": "CET-6"}],
}


class FakeProvider:
    model_name = "fake-model"

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.data = data if data is not None else deepcopy(VALID_DATA)
        self.error = error
        self.calls = 0

    async def complete_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return deepcopy(self.data)


def make_pdf(text: str = DEFAULT_TEXT) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    y = 72
    if text:
        for line in text.split("\n"):
            page.insert_text((72, y), line, fontsize=12)
            y += 20
    data = document.tobytes()
    document.close()
    return data


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register_and_login(client: AsyncClient, email: str) -> str:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "测试用户"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


async def upload_pdf(
    client: AsyncClient,
    token: str,
    *,
    text: str = DEFAULT_TEXT,
    filename: str = "resume.pdf",
) -> str:
    response = await client.post(
        "/api/v1/resumes/upload",
        headers=bearer(token),
        files={"file": (filename, make_pdf(text), "application/pdf")},
    )
    assert response.status_code == 201
    return response.json()["id"]


async def parse_resume(client: AsyncClient, token: str, resume_id: str) -> Response:
    return await client.post(
        f"/api/v1/resumes/{resume_id}/parse",
        headers=bearer(token),
    )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def ai_auth_app(auth_app: FastAPI, fake_provider: FakeProvider) -> Iterator[FastAPI]:
    auth_app.dependency_overrides[get_json_provider] = lambda: fake_provider
    yield auth_app
    auth_app.dependency_overrides.pop(get_json_provider, None)


@pytest_asyncio.fixture
async def ai_client(ai_auth_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=ai_auth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_parse_without_configured_key_returns_503(
    auth_client: AsyncClient,
) -> None:
    token = await register_and_login(auth_client, "real-nokey@example.com")
    resume_id = await upload_pdf(auth_client, token)

    response = await parse_resume(auth_client, token, resume_id)

    assert response.status_code == 503
    assert "API Key" in response.json()["detail"]
    versions = await auth_client.get(
        f"/api/v1/resumes/{resume_id}/versions",
        headers=bearer(token),
    )
    assert versions.json() == []


async def test_parse_creates_structured_version(ai_client: AsyncClient) -> None:
    token = await register_and_login(ai_client, "parse@example.com")
    resume_id = await upload_pdf(ai_client, token)

    response = await parse_resume(ai_client, token, resume_id)

    assert response.status_code == 201
    body = response.json()
    assert body["version_no"] == 1
    assert body["status"] == "parsed"
    assert body["model_name"] == "fake-model"
    assert body["parsed_data"]["basic_info"]["name"] == "张三"
    assert body["effective_data"]["projects"][0]["name"] == "简历诊断平台"
    assert body["error_message"] is None

    versions = await ai_client.get(
        f"/api/v1/resumes/{resume_id}/versions",
        headers=bearer(token),
    )
    assert versions.status_code == 200
    assert [item["version_no"] for item in versions.json()] == [1]


async def test_parse_without_key_returns_503_and_no_version(
    ai_client: AsyncClient,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.error = ProviderNotConfiguredError("未配置 Key")
    token = await register_and_login(ai_client, "nokey@example.com")
    resume_id = await upload_pdf(ai_client, token)

    response = await parse_resume(ai_client, token, resume_id)

    assert response.status_code == 503
    assert "API Key" in response.json()["detail"]
    versions = await ai_client.get(
        f"/api/v1/resumes/{resume_id}/versions",
        headers=bearer(token),
    )
    assert versions.json() == []


async def test_parse_failure_records_failed_version(
    ai_client: AsyncClient,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.data = {"education": [{"degree": "本科"}]}
    token = await register_and_login(ai_client, "fail@example.com")
    resume_id = await upload_pdf(ai_client, token)

    response = await parse_resume(ai_client, token, resume_id)

    assert response.status_code == 502
    versions = await ai_client.get(
        f"/api/v1/resumes/{resume_id}/versions",
        headers=bearer(token),
    )
    body = versions.json()
    assert len(body) == 1
    assert body[0]["status"] == "failed"

    detail = await ai_client.get(
        f"/api/v1/resumes/{resume_id}/versions/1",
        headers=bearer(token),
    )
    assert detail.status_code == 200
    assert detail.json()["parsed_data"] is None
    assert detail.json()["error_message"]


async def test_parse_scanned_pdf_returns_409(ai_client: AsyncClient) -> None:
    token = await register_and_login(ai_client, "scan@example.com")
    resume_id = await upload_pdf(ai_client, token, text="")

    response = await parse_resume(ai_client, token, resume_id)

    assert response.status_code == 409
    assert "没有可用文本" in response.json()["detail"]


async def test_cross_user_cannot_parse(ai_client: AsyncClient) -> None:
    owner = await register_and_login(ai_client, "owner-parse@example.com")
    other = await register_and_login(ai_client, "other-parse@example.com")
    resume_id = await upload_pdf(ai_client, owner)

    response = await parse_resume(ai_client, other, resume_id)

    assert response.status_code == 404


async def test_correction_creates_new_version(ai_client: AsyncClient) -> None:
    token = await register_and_login(ai_client, "correct@example.com")
    resume_id = await upload_pdf(ai_client, token)
    parsed = await parse_resume(ai_client, token, resume_id)
    assert parsed.status_code == 201

    corrected_data = deepcopy(VALID_DATA)
    corrected_data["basic_info"]["name"] = "李四"
    corrected_data["summary"] = "人工校正后的摘要"

    response = await ai_client.post(
        f"/api/v1/resumes/{resume_id}/versions/1/corrections",
        headers=bearer(token),
        json={"data": corrected_data},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["version_no"] == 2
    assert body["status"] == "corrected"
    assert body["base_version_no"] == 1
    assert body["has_corrections"] is True
    assert body["parsed_data"]["basic_info"]["name"] == "张三"
    assert body["corrected_data"]["basic_info"]["name"] == "李四"
    assert body["effective_data"]["basic_info"]["name"] == "李四"

    versions = await ai_client.get(
        f"/api/v1/resumes/{resume_id}/versions",
        headers=bearer(token),
    )
    assert [item["version_no"] for item in versions.json()] == [2, 1]


async def test_correction_rejects_invalid_payload(ai_client: AsyncClient) -> None:
    token = await register_and_login(ai_client, "invalid-correct@example.com")
    resume_id = await upload_pdf(ai_client, token)
    await parse_resume(ai_client, token, resume_id)

    response = await ai_client.post(
        f"/api/v1/resumes/{resume_id}/versions/1/corrections",
        headers=bearer(token),
        json={"data": {"education": [{"degree": "本科"}]}},
    )

    assert response.status_code == 422


async def test_cross_user_cannot_read_or_correct_versions(ai_client: AsyncClient) -> None:
    owner = await register_and_login(ai_client, "owner-version@example.com")
    other = await register_and_login(ai_client, "other-version@example.com")
    resume_id = await upload_pdf(ai_client, owner)
    await parse_resume(ai_client, owner, resume_id)

    listing = await ai_client.get(
        f"/api/v1/resumes/{resume_id}/versions",
        headers=bearer(other),
    )
    detail = await ai_client.get(
        f"/api/v1/resumes/{resume_id}/versions/1",
        headers=bearer(other),
    )
    correction = await ai_client.post(
        f"/api/v1/resumes/{resume_id}/versions/1/corrections",
        headers=bearer(other),
        json={"data": deepcopy(VALID_DATA)},
    )

    assert listing.status_code == 404
    assert detail.status_code == 404
    assert correction.status_code == 404


async def test_versions_require_auth(ai_client: AsyncClient) -> None:
    resume_id = str(uuid.uuid4())

    response = await ai_client.get(f"/api/v1/resumes/{resume_id}/versions")

    assert response.status_code == 401
