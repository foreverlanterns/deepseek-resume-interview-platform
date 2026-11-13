"""简历上传、列表、详情与删除接口。"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.models.resume import Resume
from app.schemas.resume import ResumeDetail, ResumeSummary
from app.services.resume_files import (
    FileTooLargeError,
    InvalidFileContentError,
    UnsupportedFileTypeError,
)
from app.services.resumes import create_resume, delete_resume, get_resume, list_resumes

router = APIRouter(prefix="/resumes", tags=["resumes"])


def _to_detail(resume: Resume) -> ResumeDetail:
    summary = ResumeSummary.model_validate(resume)
    return ResumeDetail(
        **summary.model_dump(),
        mime_type=resume.mime_type,
        file_size=resume.file_size,
        sha256=resume.sha256,
        text_preview=(resume.extracted_text or "")[:800],
        error_message=resume.error_message,
    )


@router.post(
    "/upload",
    response_model=ResumeDetail,
    status_code=status.HTTP_201_CREATED,
    summary="上传并提取简历文本",
)
async def upload_resume(
    file: Annotated[UploadFile, File(description="PDF 或 DOCX 简历文件")],
    session: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> ResumeDetail:
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    data = await file.read(max_size_bytes + 1)
    if len(data) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"文件大小不能超过 {settings.max_upload_size_mb} MB",
        )

    try:
        resume = await create_resume(
            session,
            user_id=current_user.id,
            filename=file.filename,
            data=data,
            settings=settings,
        )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from None
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from None
    except InvalidFileContentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None

    return _to_detail(resume)


@router.get("", response_model=list[ResumeSummary], summary="当前用户的简历列表")
async def read_resumes(session: DbSession, current_user: CurrentUser) -> list[ResumeSummary]:
    resumes = await list_resumes(session, user_id=current_user.id)
    return [ResumeSummary.model_validate(resume) for resume in resumes]


@router.get("/{resume_id}", response_model=ResumeDetail, summary="简历详情与文本预览")
async def read_resume(
    resume_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
) -> ResumeDetail:
    resume = await get_resume(session, user_id=current_user.id, resume_id=resume_id)
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在",
        )
    return _to_detail(resume)


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="删除简历",
)
async def remove_resume(
    resume_id: uuid.UUID,
    session: DbSession,
    current_user: CurrentUser,
    settings: AppSettings,
) -> Response:
    deleted = await delete_resume(
        session,
        user_id=current_user.id,
        resume_id=resume_id,
        settings=settings,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="简历不存在",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
