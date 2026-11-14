"""简历结构化版本业务逻辑。"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume, ResumeStatus
from app.models.resume_version import ResumeVersion, ResumeVersionStatus
from app.providers.base import (
    JsonCompletionProvider,
    ProviderError,
    ProviderNotConfiguredError,
)
from app.schemas.resume_parse import ParsedResume
from app.services.resume_parser import (
    PARSER_VERSION,
    PROMPT_VERSION,
    ResumeParseError,
    parse_resume_text,
)

logger = logging.getLogger(__name__)


class ResumeNotParsableError(Exception):
    """简历没有可解析的文本。"""


class ResumeVersionNotFoundError(Exception):
    """版本不存在或不属于当前用户。"""


class ResumeParseFailedError(Exception):
    """模型调用或结构校验失败。"""


async def list_versions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
) -> list[ResumeVersion]:
    result = await session.execute(
        select(ResumeVersion)
        .where(ResumeVersion.user_id == user_id, ResumeVersion.resume_id == resume_id)
        .order_by(ResumeVersion.version_no.desc())
    )
    return list(result.scalars().all())


async def get_version(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    version_no: int,
) -> ResumeVersion | None:
    result = await session.execute(
        select(ResumeVersion).where(
            ResumeVersion.user_id == user_id,
            ResumeVersion.resume_id == resume_id,
            ResumeVersion.version_no == version_no,
        )
    )
    return result.scalar_one_or_none()


async def create_parsed_version(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    provider: JsonCompletionProvider,
) -> ResumeVersion:
    result = await session.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise ResumeVersionNotFoundError
    if resume.status != ResumeStatus.EXTRACTED.value or not resume.extracted_text:
        raise ResumeNotParsableError("当前简历没有可用文本，请先确认解析状态")

    text = resume.extracted_text
    # 模型调用可能持续数十秒，先结束只读事务，避免长时间 idle in transaction
    await session.rollback()

    try:
        parsed = await parse_resume_text(text, provider)
    except ProviderNotConfiguredError:
        raise
    except (ResumeParseError, ProviderError) as exc:
        logger.warning("简历结构化解析失败：resume_id=%s", resume_id)
        await _insert_version(
            session,
            user_id=user_id,
            resume_id=resume_id,
            status=ResumeVersionStatus.FAILED,
            parsed_data=None,
            corrected_data=None,
            base_version_no=None,
            parser_version=PARSER_VERSION,
            prompt_version=PROMPT_VERSION,
            model_name=provider.model_name,
            error_message=str(exc)[:500],
        )
        raise ResumeParseFailedError(str(exc)) from exc

    return await _insert_version(
        session,
        user_id=user_id,
        resume_id=resume_id,
        status=ResumeVersionStatus.PARSED,
        parsed_data=parsed.model_dump(mode="json"),
        corrected_data=None,
        base_version_no=None,
        parser_version=PARSER_VERSION,
        prompt_version=PROMPT_VERSION,
        model_name=provider.model_name,
        error_message=None,
    )


async def create_correction_version(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    base_version_no: int,
    data: ParsedResume,
) -> ResumeVersion:
    base = await get_version(
        session,
        user_id=user_id,
        resume_id=resume_id,
        version_no=base_version_no,
    )
    if base is None:
        raise ResumeVersionNotFoundError

    return await _insert_version(
        session,
        user_id=user_id,
        resume_id=resume_id,
        status=ResumeVersionStatus.CORRECTED,
        parsed_data=base.parsed_data,
        corrected_data=data.model_dump(mode="json"),
        base_version_no=base.version_no,
        parser_version="manual",
        prompt_version=base.prompt_version,
        model_name=base.model_name,
        error_message=None,
    )


async def _insert_version(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    status: ResumeVersionStatus,
    parsed_data: dict[str, Any] | None,
    corrected_data: dict[str, Any] | None,
    base_version_no: int | None,
    parser_version: str | None,
    prompt_version: str | None,
    model_name: str | None,
    error_message: str | None,
) -> ResumeVersion:
    # 锁定简历行，确保同一简历的 version_no 递增且不并发冲突
    result = await session.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id).with_for_update()
    )
    if result.scalar_one_or_none() is None:
        raise ResumeVersionNotFoundError

    max_version = await session.execute(
        select(func.coalesce(func.max(ResumeVersion.version_no), 0)).where(
            ResumeVersion.resume_id == resume_id
        )
    )
    version_no = int(max_version.scalar_one()) + 1

    version = ResumeVersion(
        user_id=user_id,
        resume_id=resume_id,
        version_no=version_no,
        status=status.value,
        parsed_data=parsed_data,
        corrected_data=corrected_data,
        base_version_no=base_version_no,
        parser_version=parser_version,
        prompt_version=prompt_version,
        model_name=model_name,
        error_message=error_message,
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version
