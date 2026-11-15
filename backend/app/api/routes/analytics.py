"""成长分析接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.analytics import (
    AnalyticsOverview,
    DiagnosisTrendResponse,
    InterviewTrendResponse,
    WeaknessReport,
)
from app.services.analytics import (
    get_diagnosis_trends,
    get_interview_trends,
    get_overview,
    get_weaknesses,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview, summary="成长概览")
async def read_overview(
    session: DbSession,
    current_user: CurrentUser,
    resume_id: uuid.UUID | None = Query(default=None),
) -> AnalyticsOverview:
    return await get_overview(session, user_id=current_user.id, resume_id=resume_id)


@router.get(
    "/diagnoses",
    response_model=DiagnosisTrendResponse,
    summary="诊断趋势",
)
async def read_diagnosis_trends(
    session: DbSession,
    current_user: CurrentUser,
    resume_id: uuid.UUID | None = Query(default=None),
    jd_id: uuid.UUID | None = Query(default=None),
) -> DiagnosisTrendResponse:
    return await get_diagnosis_trends(
        session,
        user_id=current_user.id,
        resume_id=resume_id,
        jd_id=jd_id,
    )


@router.get(
    "/interviews",
    response_model=InterviewTrendResponse,
    summary="面试趋势",
)
async def read_interview_trends(
    session: DbSession,
    current_user: CurrentUser,
    resume_id: uuid.UUID | None = Query(default=None),
    jd_id: uuid.UUID | None = Query(default=None),
    interview_type: str | None = Query(default=None),
) -> InterviewTrendResponse:
    return await get_interview_trends(
        session,
        user_id=current_user.id,
        resume_id=resume_id,
        jd_id=jd_id,
        interview_type=interview_type,
    )


@router.get("/weaknesses", response_model=WeaknessReport, summary="弱项聚合")
async def read_weaknesses(
    session: DbSession,
    current_user: CurrentUser,
    resume_id: uuid.UUID | None = Query(default=None),
) -> WeaknessReport:
    return await get_weaknesses(session, user_id=current_user.id, resume_id=resume_id)
