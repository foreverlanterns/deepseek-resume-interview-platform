"""成长分析接口集成测试。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from httpx import AsyncClient

from app.models.diagnosis import Diagnosis
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.resume import Resume

PASSWORD = "StrongPass123"


async def register_and_login(client: AsyncClient, email: str) -> tuple[str, str]:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": "成长用户"},
    )
    assert register.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    return login.json()["access_token"], me.json()["id"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def seed_resume(
    db_session: Any,
    user_id: str,
    filename: str = "resume.pdf",
) -> Resume:
    resume = Resume(
        user_id=uuid.UUID(user_id),
        original_filename=filename,
        stored_path=f"{user_id}/{uuid.uuid4()}/original.pdf",
        mime_type="application/pdf",
        file_size=100,
        sha256="d" * 64,
        status="extracted",
        extracted_text="张三 后端开发",
        text_length=8,
    )
    db_session.add(resume)
    await db_session.commit()
    await db_session.refresh(resume)
    return resume


async def seed_jd(client: AsyncClient, token: str, title: str) -> str:
    response = await client.post(
        "/api/v1/jds",
        headers=bearer(token),
        json={
            "title": title,
            "company": "某科技公司",
            "raw_text": "要求 Python、Docker。",
            "required_skills": ["Python", "Docker"],
            "preferred_skills": [],
            "keywords": [],
            "responsibilities": [],
            "qualifications": [],
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def keyword_details(missing: list[str]) -> dict[str, Any]:
    return {
        "score": 50,
        "matched_count": 0,
        "total_count": len(missing),
        "matched_weight": 0,
        "total_weight": len(missing),
        "hits": [
            {"keyword": keyword, "source": "required", "weight": 1, "matched": False}
            for keyword in missing
        ],
    }


def jd_match_details(missing: list[str], partial: list[str] | None = None) -> dict[str, Any]:
    partial = partial or []
    matches = [
        {
            "requirement": requirement,
            "source": "required",
            "weight": 1,
            "verdict": "missing",
            "evidence": None,
            "reason": "无证据",
        }
        for requirement in missing
    ] + [
        {
            "requirement": requirement,
            "source": "preferred",
            "weight": 1,
            "verdict": "partial",
            "evidence": "部分相关",
            "reason": "证据不足",
        }
        for requirement in partial
    ]
    return {
        "score": 0,
        "matched_count": 0,
        "partial_count": len(partial),
        "missing_count": len(missing),
        "total": len(matches),
        "matches": matches,
    }


def build_diagnosis(
    *,
    user_id: str,
    resume_id: uuid.UUID,
    jd_id: str,
    total: float,
    created_at: datetime,
    keyword_gaps: list[str] | None = None,
    requirement_gaps: list[str] | None = None,
    partial_gaps: list[str] | None = None,
    rubric: str = "rubric_v1",
    jd_title: str = "后端开发工程师",
) -> Diagnosis:
    return Diagnosis(
        user_id=uuid.UUID(user_id),
        resume_id=resume_id,
        resume_version_no=1,
        jd_id=uuid.UUID(jd_id),
        jd_snapshot={"title": jd_title, "company": "某科技公司"},
        rubric_version=rubric,
        weights={"format": 0.15, "completeness": 0.2, "keyword": 0.25, "jd_match": 0.4},
        format_score=80,
        completeness_score=80,
        keyword_score=60,
        jd_match_score=50,
        total_score=Decimal(str(total)),
        format_details=[],
        completeness_details=[],
        keyword_details=keyword_details(keyword_gaps or []),
        jd_match_details=jd_match_details(requirement_gaps or [], partial_gaps),
        suggestions=[],
        summary="测试诊断",
        model_name="fake-model",
        prompt_version="diagnosis_prompt_v1",
        created_at=created_at,
    )


async def add_diagnosis(db_session: Any, **kwargs: Any) -> Diagnosis:
    diagnosis = build_diagnosis(**kwargs)
    db_session.add(diagnosis)
    await db_session.commit()
    await db_session.refresh(diagnosis)
    return diagnosis


def build_interview(
    *,
    user_id: str,
    resume_id: uuid.UUID,
    jd_id: str | None,
    total: float | None,
    created_at: datetime,
    status: str = "completed",
    interview_type: str = "mixed",
    dimensions: dict[str, float] | None = None,
    jd_title: str = "后端开发工程师",
) -> Interview:
    return Interview(
        user_id=uuid.UUID(user_id),
        resume_id=resume_id,
        resume_version_no=1,
        jd_id=uuid.UUID(jd_id) if jd_id else None,
        jd_snapshot={"title": jd_title} if jd_id else None,
        interview_type=interview_type,
        status=status,
        planned_question_count=3,
        rubric_version="interview_rubric_v1",
        model_name="fake-model",
        prompt_version="interview_plan_v1",
        total_score=Decimal(str(total)) if total is not None else None,
        dimension_scores=dimensions,
        summary="测试面试" if status == "completed" else None,
        created_at=created_at,
        completed_at=created_at if status == "completed" else None,
    )


async def add_interview(
    db_session: Any,
    *,
    questions: int = 3,
    answered: int = 3,
    **kwargs: Any,
) -> Interview:
    interview = build_interview(**kwargs)
    db_session.add(interview)
    await db_session.flush()
    for index in range(1, questions + 1):
        db_session.add(
            InterviewQuestion(
                interview_id=interview.id,
                user_id=interview.user_id,
                order_index=index,
                source="behavioral",
                source_ref="通用行为题",
                question=f"第 {index} 题",
                intent="测试",
                follow_up_level=0,
                answer="回答" if index <= answered else None,
                answered_at=kwargs["created_at"] if index <= answered else None,
                score=Decimal("70") if index <= answered else None,
            )
        )
    await db_session.commit()
    await db_session.refresh(interview)
    return interview


async def test_empty_analytics(
    auth_client: AsyncClient,
) -> None:
    token, _ = await register_and_login(auth_client, "growth-empty@example.com")

    overview = await auth_client.get("/api/v1/analytics/overview", headers=bearer(token))
    diagnoses = await auth_client.get("/api/v1/analytics/diagnoses", headers=bearer(token))
    interviews = await auth_client.get("/api/v1/analytics/interviews", headers=bearer(token))
    weaknesses = await auth_client.get("/api/v1/analytics/weaknesses", headers=bearer(token))

    assert overview.status_code == 200
    body = overview.json()
    assert body["resume_count"] == 0
    assert body["diagnosis_count"] == 0
    assert body["latest_diagnosis"] is None
    assert diagnoses.json() == {"groups": []}
    assert interviews.json() == {"groups": []}
    weakness_body = weaknesses.json()
    assert weakness_body["missing_keywords"] == []
    assert weakness_body["interview_dimensions"] == []
    assert weakness_body["lowest_dimension"] is None


async def test_diagnosis_trends_group_by_jd_and_rubric(
    auth_client: AsyncClient,
    db_session: Any,
) -> None:
    token, user_id = await register_and_login(auth_client, "growth-diagnosis@example.com")
    resume = await seed_resume(db_session, user_id)
    jd_one = await seed_jd(auth_client, token, "后端开发工程师")
    jd_two = await seed_jd(auth_client, token, "数据开发工程师")

    await add_diagnosis(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_one,
        total=60,
        created_at=datetime(2026, 11, 1, tzinfo=UTC),
    )
    await add_diagnosis(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_one,
        total=72,
        created_at=datetime(2026, 11, 5, tzinfo=UTC),
    )
    await add_diagnosis(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_two,
        total=80,
        created_at=datetime(2026, 11, 6, tzinfo=UTC),
        jd_title="数据开发工程师",
    )
    await add_diagnosis(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_one,
        total=90,
        created_at=datetime(2026, 11, 7, tzinfo=UTC),
        rubric="rubric_v2",
    )

    response = await auth_client.get("/api/v1/analytics/diagnoses", headers=bearer(token))

    assert response.status_code == 200
    groups = response.json()["groups"]
    assert len(groups) == 3
    main = next(
        group
        for group in groups
        if group["jd_id"] == jd_one and group["rubric_version"] == "rubric_v1"
    )
    assert len(main["points"]) == 2
    assert [point["total_score"] for point in main["points"]] == [60.0, 72.0]
    assert main["improvement"] == 12.0
    assert main["average_total"] == 66.0
    assert main["best_total"] == 72.0
    assert main["jd_title"] == "后端开发工程师"

    filtered = await auth_client.get(
        "/api/v1/analytics/diagnoses",
        headers=bearer(token),
        params={"jd_id": jd_one},
    )
    assert len(filtered.json()["groups"]) == 2

    overview = await auth_client.get("/api/v1/analytics/overview", headers=bearer(token))
    assert overview.json()["diagnosis_count"] == 4
    assert overview.json()["latest_diagnosis"]["total_score"] == 90.0


async def test_interview_trends_only_completed(
    auth_client: AsyncClient,
    db_session: Any,
) -> None:
    token, user_id = await register_and_login(auth_client, "growth-interview@example.com")
    resume = await seed_resume(db_session, user_id)
    jd_id = await seed_jd(auth_client, token, "后端开发工程师")

    await add_interview(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=70,
        created_at=datetime(2026, 11, 1, tzinfo=UTC),
        dimensions={
            "relevance": 80,
            "correctness": 70,
            "structure": 70,
            "evidence": 60,
            "expression": 70,
        },
    )
    await add_interview(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=82,
        created_at=datetime(2026, 11, 5, tzinfo=UTC),
        dimensions={
            "relevance": 90,
            "correctness": 80,
            "structure": 80,
            "evidence": 75,
            "expression": 85,
        },
    )
    await add_interview(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=None,
        created_at=datetime(2026, 11, 6, tzinfo=UTC),
        status="ready",
        questions=0,
        answered=0,
    )
    await add_interview(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=90,
        created_at=datetime(2026, 11, 7, tzinfo=UTC),
        interview_type="jd",
        dimensions={
            "relevance": 90,
            "correctness": 90,
            "structure": 90,
            "evidence": 90,
            "expression": 90,
        },
    )

    response = await auth_client.get("/api/v1/analytics/interviews", headers=bearer(token))

    assert response.status_code == 200
    groups = response.json()["groups"]
    assert len(groups) == 2
    mixed = next(group for group in groups if group["interview_type"] == "mixed")
    assert len(mixed["points"]) == 2
    assert mixed["improvement"] == 12.0
    assert mixed["dimension_changes"]["relevance"] == 10.0
    assert mixed["points"][0]["question_count"] == 3
    assert mixed["points"][0]["answered_count"] == 3

    filtered = await auth_client.get(
        "/api/v1/analytics/interviews",
        headers=bearer(token),
        params={"interview_type": "jd"},
    )
    assert len(filtered.json()["groups"]) == 1
    assert filtered.json()["groups"][0]["points"][0]["total_score"] == 90.0


async def test_weakness_aggregation(
    auth_client: AsyncClient,
    db_session: Any,
) -> None:
    token, user_id = await register_and_login(auth_client, "growth-weak@example.com")
    resume = await seed_resume(db_session, user_id)
    jd_id = await seed_jd(auth_client, token, "后端开发工程师")

    await add_diagnosis(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=60,
        created_at=datetime(2026, 11, 1, tzinfo=UTC),
        keyword_gaps=["Docker"],
        requirement_gaps=["Docker"],
    )
    await add_diagnosis(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=65,
        created_at=datetime(2026, 11, 2, tzinfo=UTC),
        keyword_gaps=["Docker", "Kubernetes"],
        requirement_gaps=["Docker"],
        partial_gaps=["FastAPI"],
    )
    dimensions = {
        "relevance": 85,
        "correctness": 80,
        "structure": 75,
        "evidence": 55,
        "expression": 80,
    }
    await add_interview(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=75,
        created_at=datetime(2026, 11, 3, tzinfo=UTC),
        dimensions=dimensions,
    )
    await add_interview(
        db_session,
        user_id=user_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=78,
        created_at=datetime(2026, 11, 4, tzinfo=UTC),
        dimensions={**dimensions, "evidence": 65},
    )

    response = await auth_client.get("/api/v1/analytics/weaknesses", headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert body["missing_keywords"][0] == {"keyword": "Docker", "count": 2}
    assert body["missing_keywords"][1] == {"keyword": "Kubernetes", "count": 1}
    assert body["missing_requirements"][0] == {"requirement": "Docker", "count": 2}
    assert body["missing_requirements"][1] == {"requirement": "FastAPI", "count": 1}
    dimensions_out = {item["key"]: item for item in body["interview_dimensions"]}
    assert dimensions_out["evidence"]["average"] == 60.0
    assert dimensions_out["evidence"]["sample_count"] == 2
    assert body["lowest_dimension"] == "evidence"


async def test_analytics_cross_user_isolation(
    auth_client: AsyncClient,
    db_session: Any,
) -> None:
    owner_token, owner_id = await register_and_login(auth_client, "growth-owner@example.com")
    other_token, _ = await register_and_login(auth_client, "growth-other@example.com")
    resume = await seed_resume(db_session, owner_id)
    jd_id = await seed_jd(auth_client, owner_token, "后端开发工程师")
    await add_diagnosis(
        db_session,
        user_id=owner_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=80,
        created_at=datetime(2026, 11, 1, tzinfo=UTC),
        keyword_gaps=["Docker"],
    )
    await add_interview(
        db_session,
        user_id=owner_id,
        resume_id=resume.id,
        jd_id=jd_id,
        total=80,
        created_at=datetime(2026, 11, 2, tzinfo=UTC),
        dimensions={
            "relevance": 80,
            "correctness": 80,
            "structure": 80,
            "evidence": 80,
            "expression": 80,
        },
    )

    overview = await auth_client.get("/api/v1/analytics/overview", headers=bearer(other_token))
    diagnoses = await auth_client.get("/api/v1/analytics/diagnoses", headers=bearer(other_token))
    weaknesses = await auth_client.get("/api/v1/analytics/weaknesses", headers=bearer(other_token))

    assert overview.json()["resume_count"] == 0
    assert overview.json()["diagnosis_count"] == 0
    assert diagnoses.json() == {"groups": []}
    assert weaknesses.json()["missing_keywords"] == []


async def test_analytics_requires_auth(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/analytics/overview")
    assert response.status_code == 401
