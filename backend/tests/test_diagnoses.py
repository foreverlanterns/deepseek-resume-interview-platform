"""四维诊断接口集成测试（假 Provider）。"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator
from copy import deepcopy
from typing import Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_json_provider
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion

PASSWORD = "StrongPass123"
RESUME_TEXT = "张三 后端开发工程师\n使用 Python 开发简历诊断平台\n熟悉 FastAPI 与 PostgreSQL。"

PARSED_DATA: dict[str, Any] = {
    "basic_info": {
        "name": "张三",
        "phone": "13800000000",
        "email": "zhang@example.com",
        "location": "杭州",
        "headline": "后端开发工程师",
    },
    "summary": "3 年后端开发经验",
    "education": [
        {
            "school": "某某大学",
            "degree": "本科",
            "major": "计算机科学与技术",
            "start_date": "2020.09",
            "end_date": "2024.06",
            "details": ["主修数据库"],
        }
    ],
    "work_experience": [
        {
            "company": "某科技公司",
            "title": "后端开发",
            "start_date": "2024.07",
            "end_date": "至今",
            "location": "杭州",
            "highlights": ["使用 Python 开发简历诊断平台"],
        }
    ],
    "projects": [
        {
            "name": "简历诊断平台",
            "role": "后端开发",
            "start_date": "2025.03",
            "end_date": "2025.06",
            "description": "基于 FastAPI 的平台",
            "highlights": ["实现 JWT 认证"],
            "tech_stack": ["Python", "FastAPI"],
        }
    ],
    "skills": [{"category": "编程语言", "items": ["Python", "FastAPI"]}],
    "certificates": [{"name": "CET-6", "issuer": "教育部", "date": "2023.06"}],
    "awards": [],
    "languages": [{"name": "英语", "level": "CET-6"}],
}

AI_DATA: dict[str, Any] = {
    "requirement_matches": [
        {
            "requirement": "Python",
            "verdict": "met",
            "evidence": "使用 Python 开发简历诊断平台",
            "reason": "项目经历有直接证据",
        },
        {
            "requirement": "Docker",
            "verdict": "missing",
            "evidence": None,
            "reason": "简历未出现 Docker 相关经历",
        },
        {
            "requirement": "FastAPI",
            "verdict": "partial",
            "evidence": "基于 FastAPI 的平台",
            "reason": "有部分相关证据",
        },
    ],
    "suggestions": [
        {
            "dimension": "jd_match",
            "original_text": "使用 Python 开发简历诊断平台",
            "issue": "未说明项目规模和个人职责",
            "suggestion": "补充项目规模与本人负责的模块",
            "rewritten_example": "使用 Python 开发简历诊断平台，负责后端接口设计",
            "reason": "让岗位要求的匹配证据更具体",
            "fact_status": "supported",
            "missing_facts": [],
        }
    ],
}


class FakeProvider:
    model_name = "fake-model"

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data if data is not None else deepcopy(AI_DATA)
        self.calls = 0

    async def complete_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        return deepcopy(self.data)


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


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register_and_login(client: AsyncClient, email: str) -> str:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "诊断用户"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


async def seed_target(
    client: AsyncClient,
    db_session: Any,
    token: str,
    *,
    jd_payload: dict[str, Any] | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    me = await client.get("/api/v1/auth/me", headers=bearer(token))
    user_id = uuid.UUID(me.json()["id"])

    resume = Resume(
        user_id=user_id,
        original_filename="resume.pdf",
        stored_path=f"{user_id}/{uuid.uuid4()}/original.pdf",
        mime_type="application/pdf",
        file_size=len(RESUME_TEXT.encode()),
        sha256="a" * 64,
        status="extracted",
        extracted_text=RESUME_TEXT,
        text_length=len(RESUME_TEXT),
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)

    version = ResumeVersion(
        user_id=user_id,
        resume_id=resume.id,
        version_no=1,
        status="parsed",
        parsed_data=deepcopy(PARSED_DATA),
        parser_version="resume_parser_v1",
        prompt_version="resume_parse_prompt_v1",
        model_name="deepseek-flash",
    )
    db_session.add(version)
    await db_session.commit()

    jd = await client.post(
        "/api/v1/jds",
        headers=bearer(token),
        json=jd_payload
        or {
            "title": "后端开发工程师",
            "company": "某科技公司",
            "raw_text": "负责后端服务开发，要求 Python、Docker、FastAPI。",
            "required_skills": ["Python", "Docker"],
            "preferred_skills": ["FastAPI"],
            "keywords": ["PostgreSQL"],
            "responsibilities": [],
            "qualifications": [],
        },
    )
    assert jd.status_code == 201
    return resume.id, uuid.UUID(jd.json()["id"])


async def create_diagnosis(
    client: AsyncClient,
    token: str,
    resume_id: uuid.UUID,
    jd_id: uuid.UUID,
) -> Any:
    return await client.post(
        "/api/v1/diagnoses",
        headers=bearer(token),
        json={
            "resume_id": str(resume_id),
            "resume_version_no": 1,
            "jd_id": str(jd_id),
        },
    )


async def test_create_diagnosis_computes_weighted_score(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    token = await register_and_login(ai_client, "score@example.com")
    resume_id, jd_id = await seed_target(ai_client, db_session, token)

    response = await create_diagnosis(ai_client, token, resume_id, jd_id)

    assert response.status_code == 201
    body = response.json()
    assert body["format_score"] == 100
    assert body["completeness_score"] == 100
    assert body["keyword_score"] == 67
    assert body["jd_match_score"] == 50
    assert body["total_score"] == 71.75
    assert body["rubric_version"] == "rubric_v1"
    assert abs(sum(body["weights"].values()) - 1.0) < 1e-9
    assert body["model_name"] == "fake-model"
    assert len(body["suggestions"]) == 1
    assert body["suggestions"][0]["fact_status"] == "supported"
    assert body["suggestions"][0]["original_text_verified"] is True
    assert len(body["jd_match_details"]["matches"]) == 3

    history = await ai_client.get(
        "/api/v1/diagnoses",
        headers=bearer(token),
        params={"resume_id": str(resume_id)},
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["jd_title"] == "后端开发工程师"

    detail = await ai_client.get(
        f"/api/v1/diagnoses/{body['id']}",
        headers=bearer(token),
    )
    assert detail.status_code == 200
    assert detail.json()["total_score"] == 71.75


async def test_cross_user_cannot_read_diagnosis(
    ai_client: AsyncClient,
    db_session: Any,
) -> None:
    owner = await register_and_login(ai_client, "diag-owner@example.com")
    other = await register_and_login(ai_client, "diag-other@example.com")
    resume_id, jd_id = await seed_target(ai_client, db_session, owner)
    created = await create_diagnosis(ai_client, owner, resume_id, jd_id)
    diagnosis_id = created.json()["id"]

    detail = await ai_client.get(
        f"/api/v1/diagnoses/{diagnosis_id}",
        headers=bearer(other),
    )
    listing = await ai_client.get("/api/v1/diagnoses", headers=bearer(other))

    assert detail.status_code == 404
    assert listing.json() == []


async def test_missing_version_returns_404(
    ai_client: AsyncClient,
    db_session: Any,
) -> None:
    token = await register_and_login(ai_client, "missing-version@example.com")
    resume_id, jd_id = await seed_target(ai_client, db_session, token)

    response = await ai_client.post(
        "/api/v1/diagnoses",
        headers=bearer(token),
        json={
            "resume_id": str(resume_id),
            "resume_version_no": 99,
            "jd_id": str(jd_id),
        },
    )

    assert response.status_code == 404


async def test_jd_without_requirements_returns_409(
    ai_client: AsyncClient,
    db_session: Any,
) -> None:
    token = await register_and_login(ai_client, "jd-empty@example.com")
    resume_id, jd_id = await seed_target(
        ai_client,
        db_session,
        token,
        jd_payload={"title": "只有原文的岗位", "raw_text": "负责后端开发。"},
    )

    response = await create_diagnosis(ai_client, token, resume_id, jd_id)

    assert response.status_code == 409
    assert "岗位" in response.json()["detail"]


async def test_diagnosis_without_key_returns_503(
    auth_client: AsyncClient,
    db_session: Any,
) -> None:
    token = await register_and_login(auth_client, "diag-nokey@example.com")
    resume_id, jd_id = await seed_target(auth_client, db_session, token)

    response = await create_diagnosis(auth_client, token, resume_id, jd_id)

    assert response.status_code == 503
    assert "API Key" in response.json()["detail"]


async def test_invalid_ai_output_returns_502(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.data = {"requirement_matches": "not-a-list"}
    token = await register_and_login(ai_client, "diag-invalid@example.com")
    resume_id, jd_id = await seed_target(ai_client, db_session, token)

    response = await create_diagnosis(ai_client, token, resume_id, jd_id)

    assert response.status_code == 502


async def test_unverified_suggestion_is_marked_for_review(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.data = deepcopy(AI_DATA)
    fake_provider.data["suggestions"] = [
        {
            "dimension": "jd_match",
            "original_text": "这段原文在简历中不存在",
            "issue": "缺少量化结果",
            "suggestion": "补充真实指标",
            "rewritten_example": "将接口性能提升 30%",
            "reason": "量化成果更有说服力",
            "fact_status": "supported",
            "missing_facts": [],
        }
    ]
    token = await register_and_login(ai_client, "diag-fact@example.com")
    resume_id, jd_id = await seed_target(ai_client, db_session, token)

    response = await create_diagnosis(ai_client, token, resume_id, jd_id)

    assert response.status_code == 201
    suggestion = response.json()["suggestions"][0]
    assert suggestion["original_text_verified"] is False
    assert suggestion["fact_status"] == "needs_review"
    assert suggestion["missing_facts"]
