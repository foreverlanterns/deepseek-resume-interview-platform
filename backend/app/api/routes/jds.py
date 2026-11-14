"""岗位描述（JD）管理接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.job_description import JobDescription
from app.schemas.job_description import JobDescriptionPayload, JobDescriptionResponse

router = APIRouter(prefix="/jds", tags=["jds"])


async def _get_jd(
    session: DbSession,
    user_id: uuid.UUID,
    jd_id: uuid.UUID,
) -> JobDescription | None:
    result = await session.execute(
        select(JobDescription).where(
            JobDescription.id == jd_id,
            JobDescription.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


@router.post(
    "",
    response_model=JobDescriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建岗位描述",
)
async def create_jd(
    payload: JobDescriptionPayload,
    session: DbSession,
    current_user: CurrentUser,
) -> JobDescriptionResponse:
    jd = JobDescription(user_id=current_user.id, **payload.model_dump())
    session.add(jd)
    await session.commit()
    await session.refresh(jd)
    return JobDescriptionResponse.model_validate(jd)


@router.get("", response_model=list[JobDescriptionResponse], summary="岗位描述列表")
async def list_jds(
    session: DbSession,
    current_user: CurrentUser,
) -> list[JobDescriptionResponse]:
    result = await session.execute(
        select(JobDescription)
        .where(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc())
        .limit(100)
    )
    return [JobDescriptionResponse.model_validate(jd) for jd in result.scalars().all()]


@router.get("/{jd_id}", response_model=JobDescriptionResponse, summary="岗位描述详情")
async def read_jd(
    jd_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> JobDescriptionResponse:
    jd = await _get_jd(session, current_user.id, jd_id)
    if jd is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "岗位描述不存在")
    return JobDescriptionResponse.model_validate(jd)


@router.put("/{jd_id}", response_model=JobDescriptionResponse, summary="更新岗位描述")
async def update_jd(
    jd_id: uuid.UUID,
    payload: JobDescriptionPayload,
    session: DbSession,
    current_user: CurrentUser,
) -> JobDescriptionResponse:
    jd = await _get_jd(session, current_user.id, jd_id)
    if jd is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "岗位描述不存在")

    for key, value in payload.model_dump().items():
        setattr(jd, key, value)
    await session.commit()
    await session.refresh(jd)
    return JobDescriptionResponse.model_validate(jd)


@router.delete(
    "/{jd_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="删除岗位描述",
)
async def delete_jd(
    jd_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> Response:
    jd = await _get_jd(session, current_user.id, jd_id)
    if jd is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "岗位描述不存在")
    await session.delete(jd)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
