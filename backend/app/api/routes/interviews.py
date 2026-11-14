"""模拟面试接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, JsonProviderDep
from app.providers.base import ProviderNotConfiguredError
from app.schemas.interview import (
    InterviewAnswer,
    InterviewCreate,
    InterviewDetail,
    InterviewSummary,
)
from app.services.interviews import (
    InterviewFailedError,
    InterviewRow,
    InterviewStateError,
    InterviewTargetNotFoundError,
    answer_question,
    build_interview_report,
    create_interview,
    finish_interview,
    get_interview,
    list_interviews,
    load_questions,
    to_detail,
    to_summary,
)

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "面试记录、简历或岗位不存在")


def _provider_missing() -> HTTPException:
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "DeepSeek API Key 未配置，暂时无法使用智能面试功能",
    )


async def _detail(session: AsyncSession, row: InterviewRow, user_id: uuid.UUID) -> InterviewDetail:
    questions = await load_questions(
        session,
        interview_id=row.interview.id,
        user_id=user_id,
    )
    return to_detail(row, questions)


@router.post(
    "",
    response_model=InterviewDetail,
    status_code=status.HTTP_201_CREATED,
    summary="创建模拟面试",
)
async def create(
    payload: InterviewCreate,
    session: DbSession,
    current_user: CurrentUser,
    provider: JsonProviderDep,
) -> InterviewDetail:
    user_id = current_user.id
    try:
        row = await create_interview(
            session,
            user_id=user_id,
            payload=payload,
            provider=provider,
        )
    except InterviewTargetNotFoundError:
        raise _not_found() from None
    except InterviewStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except ProviderNotConfiguredError:
        raise _provider_missing() from None
    except InterviewFailedError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "面试题生成失败，请稍后重试",
        ) from None

    return await _detail(session, row, user_id)


@router.get("", response_model=list[InterviewSummary], summary="面试历史")
async def read_interviews(
    session: DbSession,
    current_user: CurrentUser,
    resume_id: uuid.UUID | None = Query(default=None),
) -> list[InterviewSummary]:
    rows = await list_interviews(
        session,
        user_id=current_user.id,
        resume_id=resume_id,
    )
    return [to_summary(row) for row in rows]


@router.get("/{interview_id}", response_model=InterviewDetail, summary="面试详情")
async def read_interview(
    interview_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> InterviewDetail:
    user_id = current_user.id
    row = await get_interview(
        session,
        user_id=user_id,
        interview_id=interview_id,
    )
    if row is None:
        raise _not_found()
    return await _detail(session, row, user_id)


@router.post(
    "/{interview_id}/questions/{question_id}/answer",
    response_model=InterviewDetail,
    summary="提交回答并获取评价",
)
async def submit_answer(
    interview_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: InterviewAnswer,
    session: DbSession,
    current_user: CurrentUser,
    provider: JsonProviderDep,
) -> InterviewDetail:
    user_id = current_user.id
    try:
        row = await answer_question(
            session,
            user_id=user_id,
            interview_id=interview_id,
            question_id=question_id,
            answer=payload.answer,
            provider=provider,
        )
    except InterviewTargetNotFoundError:
        raise _not_found() from None
    except InterviewStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except ProviderNotConfiguredError:
        raise _provider_missing() from None
    except InterviewFailedError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "回答评价失败，请稍后重试",
        ) from None

    return await _detail(session, row, user_id)


@router.post("/{interview_id}/finish", response_model=InterviewDetail, summary="结束面试")
async def finish(
    interview_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> InterviewDetail:
    user_id = current_user.id
    try:
        row = await finish_interview(
            session,
            user_id=user_id,
            interview_id=interview_id,
        )
    except InterviewTargetNotFoundError:
        raise _not_found() from None
    except InterviewStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None

    return await _detail(session, row, user_id)


@router.post(
    "/{interview_id}/report",
    response_model=InterviewDetail,
    summary="生成面试复盘报告",
)
async def generate_report(
    interview_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    provider: JsonProviderDep,
    force: bool = Query(default=False),
) -> InterviewDetail:
    user_id = current_user.id
    try:
        row = await build_interview_report(
            session,
            user_id=user_id,
            interview_id=interview_id,
            provider=provider,
            force=force,
        )
    except InterviewTargetNotFoundError:
        raise _not_found() from None
    except InterviewStateError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except ProviderNotConfiguredError:
        raise _provider_missing() from None
    except InterviewFailedError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "面试报告生成失败，请稍后重试",
        ) from None

    return await _detail(session, row, user_id)
