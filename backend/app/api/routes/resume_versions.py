"""简历结构化解析与版本接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession, JsonProviderDep
from app.models.resume_version import ResumeVersion
from app.providers.base import ProviderNotConfiguredError
from app.schemas.resume_parse import ParsedResume
from app.schemas.resume_version import (
    CorrectionRequest,
    ResumeVersionDetail,
    ResumeVersionSummary,
)
from app.services.resume_versions import (
    ResumeNotParsableError,
    ResumeParseFailedError,
    ResumeVersionNotFoundError,
    create_correction_version,
    create_parsed_version,
    get_version,
    list_versions,
)
from app.services.resumes import get_resume

router = APIRouter(prefix="/resumes", tags=["resume-versions"])


def _to_summary(version: ResumeVersion) -> ResumeVersionSummary:
    return ResumeVersionSummary(
        version_no=version.version_no,
        status=version.status,
        model_name=version.model_name,
        prompt_version=version.prompt_version,
        parser_version=version.parser_version,
        base_version_no=version.base_version_no,
        has_corrections=version.corrected_data is not None,
        created_at=version.created_at,
    )


def _to_detail(version: ResumeVersion) -> ResumeVersionDetail:
    summary = _to_summary(version)
    parsed = ParsedResume.model_validate(version.parsed_data) if version.parsed_data else None
    corrected = (
        ParsedResume.model_validate(version.corrected_data) if version.corrected_data else None
    )
    return ResumeVersionDetail(
        **summary.model_dump(),
        parsed_data=parsed,
        corrected_data=corrected,
        effective_data=corrected or parsed,
        error_message=version.error_message,
    )


@router.post(
    "/{resume_id}/parse",
    response_model=ResumeVersionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="用 DeepSeek 解析简历文本并生成新版本",
)
async def parse_resume(
    resume_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    provider: JsonProviderDep,
) -> ResumeVersionDetail:
    try:
        version = await create_parsed_version(
            session,
            user_id=current_user.id,
            resume_id=resume_id,
            provider=provider,
        )
    except ResumeVersionNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "简历不存在") from None
    except ResumeNotParsableError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from None
    except ProviderNotConfiguredError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "DeepSeek API Key 未配置，暂时无法解析简历",
        ) from None
    except ResumeParseFailedError:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "简历结构化解析失败，请稍后重试",
        ) from None

    return _to_detail(version)


@router.get(
    "/{resume_id}/versions",
    response_model=list[ResumeVersionSummary],
    summary="简历结构化版本列表",
)
async def read_versions(
    resume_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> list[ResumeVersionSummary]:
    resume = await get_resume(session, user_id=current_user.id, resume_id=resume_id)
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "简历不存在")

    versions = await list_versions(
        session,
        user_id=current_user.id,
        resume_id=resume_id,
    )
    return [_to_summary(version) for version in versions]


@router.get(
    "/{resume_id}/versions/{version_no}",
    response_model=ResumeVersionDetail,
    summary="结构化版本详情",
)
async def read_version(
    resume_id: uuid.UUID,
    version_no: int,
    session: DbSession,
    current_user: CurrentUser,
) -> ResumeVersionDetail:
    version = await get_version(
        session,
        user_id=current_user.id,
        resume_id=resume_id,
        version_no=version_no,
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "版本不存在")
    return _to_detail(version)


@router.post(
    "/{resume_id}/versions/{version_no}/corrections",
    response_model=ResumeVersionDetail,
    status_code=status.HTTP_201_CREATED,
    summary="保存人工校正并生成新版本",
)
async def correct_version(
    resume_id: uuid.UUID,
    version_no: int,
    payload: CorrectionRequest,
    session: DbSession,
    current_user: CurrentUser,
) -> ResumeVersionDetail:
    try:
        version = await create_correction_version(
            session,
            user_id=current_user.id,
            resume_id=resume_id,
            base_version_no=version_no,
            data=payload.data,
        )
    except ResumeVersionNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "简历或版本不存在") from None
    return _to_detail(version)
