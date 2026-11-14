"""模拟面试接口集成测试（假 Provider）。"""

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
    "basic_info": {"name": "张三", "email": "zhang@example.com", "headline": "后端开发工程师"},
    "summary": "3 年后端开发经验",
    "education": [{"school": "某某大学", "degree": "本科", "major": "计算机科学与技术"}],
    "work_experience": [
        {
            "company": "某科技公司",
            "title": "后端开发",
            "highlights": ["使用 Python 开发简历诊断平台"],
        }
    ],
    "projects": [
        {
            "name": "简历诊断平台",
            "role": "后端开发",
            "description": "基于 FastAPI 的平台",
            "highlights": ["实现 JWT 认证"],
            "tech_stack": ["Python", "FastAPI"],
        }
    ],
    "skills": [{"category": "编程语言", "items": ["Python", "FastAPI"]}],
    "certificates": [],
    "awards": [],
    "languages": [],
}

PLAN_DATA: dict[str, Any] = {
    "questions": [
        {
            "source": "resume",
            "source_ref": "某科技公司",
            "question": "请介绍你在某科技公司做过的后端项目，以及你负责的部分。",
            "intent": "验证项目深度与个人贡献",
        },
        {
            "source": "jd",
            "source_ref": "Docker",
            "question": "岗位要求 Docker，请说明你如何设计镜像与部署流程。",
            "intent": "验证容器化实践",
        },
        {
            "source": "behavioral",
            "source_ref": "通用行为题",
            "question": "请讲一次你和同事在技术方案上产生分歧的经历。",
            "intent": "验证沟通协作",
        },
    ]
}

EVAL_NO_FOLLOW_UP: dict[str, Any] = {
    "dimensions": [
        {"key": "relevance", "score": 80, "comment": "正面回答问题"},
        {"key": "correctness", "score": 70, "comment": "技术事实基本正确"},
        {"key": "structure", "score": 75, "comment": "结构清晰"},
        {"key": "evidence", "score": 60, "comment": "缺少量化结果"},
        {"key": "expression", "score": 85, "comment": "表达流畅"},
    ],
    "summary": "回答完整，但缺少可验证的结果。",
    "strengths": ["能讲清个人职责"],
    "weaknesses": ["缺少量化指标"],
    "follow_up": {"needed": False, "question": "", "intent": "", "reason": ""},
}

EVAL_FOLLOW_UP_DEEPER: dict[str, Any] = {
    **EVAL_NO_FOLLOW_UP,
    "follow_up": {
        "needed": True,
        "question": "如果并发量翻倍，你会先优化哪一部分？",
        "intent": "验证性能优化思路",
        "reason": "需要进一步验证",
    },
}

EVAL_FOLLOW_UP: dict[str, Any] = {
    **EVAL_NO_FOLLOW_UP,
    "follow_up": {
        "needed": True,
        "question": "这个项目的并发量大概多少？你如何验证选型有效？",
        "intent": "验证结果与验证方法",
        "reason": "回答缺少可验证数据",
    },
}

REPORT_DATA: dict[str, Any] = {
    "overview": "整体技术基础扎实，但回答普遍缺少量化结果。",
    "strengths": ["项目描述完整"],
    "weaknesses": ["缺少结果指标"],
    "improvements": ["每个项目准备一个量化结果"],
    "question_notes": [{"order_index": 1, "comment": "结构清晰，但缺少结果"}],
}


class FakeProvider:
    model_name = "fake-model"

    def __init__(self) -> None:
        self.queue: list[dict[str, Any]] = []
        self.calls = 0

    def push(self, data: dict[str, Any]) -> None:
        self.queue.append(deepcopy(data))

    async def complete_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        if not self.queue:
            raise AssertionError("FakeProvider 没有待返回的数据")
        return deepcopy(self.queue.pop(0))


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
        json={"email": email, "password": PASSWORD, "display_name": "面试用户"},
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
    with_jd: bool = True,
) -> tuple[uuid.UUID, uuid.UUID | None]:
    me = await client.get("/api/v1/auth/me", headers=bearer(token))
    user_id = uuid.UUID(me.json()["id"])

    resume = Resume(
        user_id=user_id,
        original_filename="resume.pdf",
        stored_path=f"{user_id}/{uuid.uuid4()}/original.pdf",
        mime_type="application/pdf",
        file_size=len(RESUME_TEXT.encode()),
        sha256="b" * 64,
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

    if not with_jd:
        return resume.id, None

    jd = await client.post(
        "/api/v1/jds",
        headers=bearer(token),
        json={
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


async def create_interview(
    client: AsyncClient,
    token: str,
    resume_id: uuid.UUID,
    *,
    jd_id: uuid.UUID | None = None,
    interview_type: str = "mixed",
    question_count: int = 3,
) -> Any:
    payload: dict[str, Any] = {
        "resume_id": str(resume_id),
        "resume_version_no": 1,
        "interview_type": interview_type,
        "question_count": question_count,
    }
    if jd_id is not None:
        payload["jd_id"] = str(jd_id)
    return await client.post("/api/v1/interviews", headers=bearer(token), json=payload)


async def submit(
    client: AsyncClient,
    token: str,
    interview_id: str,
    question_id: str,
    answer: str = "我负责后端接口设计，使用 FastAPI 和 PostgreSQL。",
) -> Any:
    return await client.post(
        f"/api/v1/interviews/{interview_id}/questions/{question_id}/answer",
        headers=bearer(token),
        json={"answer": answer},
    )


async def test_create_interview_builds_plan(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push(PLAN_DATA)
    token = await register_and_login(ai_client, "interview-create@example.com")
    resume_id, jd_id = await seed_target(ai_client, db_session, token)

    response = await create_interview(ai_client, token, resume_id, jd_id=jd_id)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["interview_type"] == "mixed"
    assert body["planned_question_count"] == 3
    assert body["question_count"] == 3
    assert body["answered_count"] == 0
    assert body["jd_title"] == "后端开发工程师"
    assert body["model_name"] == "fake-model"
    assert [item["source"] for item in body["questions"]] == ["resume", "jd", "behavioral"]
    assert body["questions"][0]["source_ref"] == "某科技公司"
    assert body["current_question_id"] == body["questions"][0]["id"]
    assert all(item["follow_up_level"] == 0 for item in body["questions"])

    history = await ai_client.get(
        "/api/v1/interviews",
        headers=bearer(token),
        params={"resume_id": str(resume_id)},
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["status"] == "ready"


async def test_unverified_source_is_downgraded(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    plan = deepcopy(PLAN_DATA)
    plan["questions"][0]["source_ref"] = "简历里不存在的公司"
    fake_provider.push(plan)
    token = await register_and_login(ai_client, "interview-source@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)

    response = await create_interview(ai_client, token, resume_id)

    assert response.status_code == 201
    question = response.json()["questions"][0]
    assert question["source"] == "behavioral"
    assert question["source_ref"] == "通用行为题"


async def test_answer_creates_single_follow_up(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push(PLAN_DATA)
    fake_provider.push(EVAL_FOLLOW_UP)
    token = await register_and_login(ai_client, "interview-follow@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)
    created = await create_interview(ai_client, token, resume_id)
    body = created.json()
    first = body["questions"][0]

    response = await submit(ai_client, token, body["id"], first["id"])

    assert response.status_code == 200
    detail = response.json()
    assert detail["status"] == "in_progress"
    assert detail["answered_count"] == 1
    assert detail["questions"][0]["score"] == 74.0
    assert detail["questions"][0]["evaluation"]["dimensions"][0]["label"] == "相关性"

    follow_up = detail["questions"][1]
    assert follow_up["follow_up_level"] == 1
    assert follow_up["parent_question_id"] == first["id"]
    assert follow_up["source"] == first["source"]
    assert follow_up["question"].startswith("这个项目的并发量")
    assert detail["current_question_id"] == follow_up["id"]
    assert detail["question_count"] == 4


async def test_follow_up_stops_at_two_levels(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push(PLAN_DATA)
    fake_provider.push(EVAL_FOLLOW_UP)
    fake_provider.push(EVAL_FOLLOW_UP_DEEPER)
    fake_provider.push(EVAL_FOLLOW_UP_DEEPER)
    token = await register_and_login(ai_client, "interview-depth@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)
    created = await create_interview(ai_client, token, resume_id)
    body = created.json()

    first = await submit(ai_client, token, body["id"], body["questions"][0]["id"])
    assert first.status_code == 200
    level_one = first.json()["questions"][1]
    assert level_one["follow_up_level"] == 1

    second = await submit(ai_client, token, body["id"], level_one["id"])
    assert second.status_code == 200
    level_two = second.json()["questions"][2]
    assert level_two["follow_up_level"] == 2

    third = await submit(ai_client, token, body["id"], level_two["id"])
    assert third.status_code == 200
    detail = third.json()
    assert all(item["follow_up_level"] <= 2 for item in detail["questions"])
    assert detail["question_count"] == 5
    assert detail["current_question_id"] == detail["questions"][3]["id"]


async def test_answer_all_questions_completes_interview(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push(PLAN_DATA)
    for _ in range(3):
        fake_provider.push(EVAL_NO_FOLLOW_UP)
    token = await register_and_login(ai_client, "interview-complete@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)
    created = await create_interview(ai_client, token, resume_id)
    body = created.json()

    for question in body["questions"]:
        response = await submit(ai_client, token, body["id"], question["id"])
        assert response.status_code == 200

    detail = response.json()
    assert detail["status"] == "completed"
    assert detail["answered_count"] == 3
    assert detail["current_question_id"] is None
    assert detail["total_score"] == 74.0
    assert detail["dimension_scores"]["relevance"] == 80.0
    assert detail["completed_at"] is not None

    again = await submit(ai_client, token, body["id"], body["questions"][0]["id"])
    assert again.status_code == 409


async def test_answer_out_of_order_returns_409(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push(PLAN_DATA)
    token = await register_and_login(ai_client, "interview-order@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)
    created = await create_interview(ai_client, token, resume_id)
    body = created.json()

    response = await submit(ai_client, token, body["id"], body["questions"][1]["id"])

    assert response.status_code == 409
    assert "顺序" in response.json()["detail"]


async def test_finish_and_generate_report(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push(PLAN_DATA)
    fake_provider.push(EVAL_NO_FOLLOW_UP)
    fake_provider.push(REPORT_DATA)
    token = await register_and_login(ai_client, "interview-report@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)
    created = await create_interview(ai_client, token, resume_id)
    body = created.json()

    early = await ai_client.post(
        f"/api/v1/interviews/{body['id']}/report",
        headers=bearer(token),
    )
    assert early.status_code == 409

    answer = await submit(ai_client, token, body["id"], body["questions"][0]["id"])
    assert answer.status_code == 200

    finished = await ai_client.post(
        f"/api/v1/interviews/{body['id']}/finish",
        headers=bearer(token),
    )
    assert finished.status_code == 200
    assert finished.json()["status"] == "completed"
    assert finished.json()["report"] is None

    report = await ai_client.post(
        f"/api/v1/interviews/{body['id']}/report",
        headers=bearer(token),
    )
    assert report.status_code == 200
    detail = report.json()
    assert detail["report"]["overview"].startswith("整体技术基础")
    assert detail["report"]["question_notes"][0]["order_index"] == 1
    assert detail["prompt_version"] == "interview_report_v1"

    calls = fake_provider.calls
    cached = await ai_client.post(
        f"/api/v1/interviews/{body['id']}/report",
        headers=bearer(token),
    )
    assert cached.status_code == 200
    assert fake_provider.calls == calls


async def test_cross_user_cannot_read_interview(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push(PLAN_DATA)
    owner = await register_and_login(ai_client, "interview-owner@example.com")
    other = await register_and_login(ai_client, "interview-other@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, owner, with_jd=False)
    created = await create_interview(ai_client, owner, resume_id)
    interview_id = created.json()["id"]

    detail = await ai_client.get(f"/api/v1/interviews/{interview_id}", headers=bearer(other))
    listing = await ai_client.get("/api/v1/interviews", headers=bearer(other))
    answer = await submit(
        ai_client,
        other,
        interview_id,
        created.json()["questions"][0]["id"],
    )

    assert detail.status_code == 404
    assert listing.json() == []
    assert answer.status_code == 404


async def test_jd_type_without_jd_returns_409(
    ai_client: AsyncClient,
    db_session: Any,
) -> None:
    token = await register_and_login(ai_client, "interview-jd-missing@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)

    response = await create_interview(
        ai_client,
        token,
        resume_id,
        interview_type="jd",
    )

    assert response.status_code == 409
    assert "岗位" in response.json()["detail"]


async def test_interview_without_key_returns_503(
    auth_client: AsyncClient,
    db_session: Any,
) -> None:
    token = await register_and_login(auth_client, "interview-nokey@example.com")
    resume_id, _ = await seed_target(auth_client, db_session, token, with_jd=False)

    response = await create_interview(auth_client, token, resume_id)

    assert response.status_code == 503
    assert "API Key" in response.json()["detail"]


async def test_invalid_plan_output_returns_502(
    ai_client: AsyncClient,
    db_session: Any,
    fake_provider: FakeProvider,
) -> None:
    fake_provider.push({"questions": "not-a-list"})
    fake_provider.push({"questions": "not-a-list"})
    token = await register_and_login(ai_client, "interview-invalid@example.com")
    resume_id, _ = await seed_target(ai_client, db_session, token, with_jd=False)

    response = await create_interview(ai_client, token, resume_id)

    assert response.status_code == 502
