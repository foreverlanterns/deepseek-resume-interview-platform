"""四维诊断接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, JsonProviderDep
from app.providers.base import ProviderNotConfiguredError
from app.schemas.diagnosis import (
    DiagnosisCreate,
    DiagnosisDetail,
    DiagnosisSummary,
)
from app.services.diagnoses import (
    DiagnosisFailedError,
    DiagnosisTargetNotFoundError,
    JobDescriptionNoRequirementsError,
    ResumeVersionNotReadyError,
    create_diagnosis,
    get_diagnosis,
    list_diagnoses,
    to_detail,
    to_summary,
)

router = APIRouter(prefix="/diagnoses", tags=["diagnoses"])


@router.post(
    "",
    response_model=DiagnosisDetail,
    status_code=status.HTTP_201_CREATED,
    summary="创建四维诊断",
)
async def create(
    payload: DiagnosisCreate,
    session: DbSession,
    current_user: CurrentUser,
    provider: JsonProviderDep,
) -> DiagnosisDetail:
    try:
        row = await create_diagnosis(
            session,
            user_id=current_user.id,
            resume_id=payload.resume_id,
            resume_version_no=payload.resume_version_no,
            jd_id=payload.jd_id,
            provider=provider,
        )
    except DiagnosisTargetNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "简历、版本或岗位描述不存在") from None
    except ResumeVersionNotReadyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except JobDescriptionNoRequirementsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except ProviderNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "DeepSeek API Key 未配置，暂时无法进行诊断",
        ) from None
    except DiagnosisFailedError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "诊断评估失败，请稍后重试",
        ) from None

    return to_detail(row)


@router.get("", response_model=list[DiagnosisSummary], summary="诊断历史")
async def read_diagnoses(
    session: DbSession,
    current_user: CurrentUser,
    resume_id: uuid.UUID | None = Query(default=None),
    jd_id: uuid.UUID | None = Query(default=None),
) -> list[DiagnosisSummary]:
    rows = await list_diagnoses(
        session,
        user_id=current_user.id,
        resume_id=resume_id,
        jd_id=jd_id,
    )
    return [to_summary(row) for row in rows]


@router.get("/{diagnosis_id}", response_model=DiagnosisDetail, summary="诊断详情")
async def read_diagnosis(
    diagnosis_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> DiagnosisDetail:
    row = await get_diagnosis(
        session,
        user_id=current_user.id,
        diagnosis_id=diagnosis_id,
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "诊断记录不存在")
    return to_detail(row)
