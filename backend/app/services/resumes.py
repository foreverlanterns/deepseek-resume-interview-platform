"""简历上传、查询与删除业务逻辑。"""

from __future__ import annotations

import hashlib
import logging
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.models.resume import Resume
from app.services.resume_extraction import extract_text
from app.services.resume_files import validate_upload

logger = logging.getLogger(__name__)


async def create_resume(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    filename: str | None,
    data: bytes,
    settings: Settings,
) -> Resume:
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    validated = validate_upload(filename, data, max_size_bytes=max_size_bytes)

    resume_id = uuid.uuid4()
    relative_path = Path(str(user_id)) / str(resume_id) / f"original{validated.suffix}"
    absolute_path = settings.upload_path / relative_path

    await run_in_threadpool(absolute_path.parent.mkdir, parents=True, exist_ok=True)
    try:
        await run_in_threadpool(absolute_path.write_bytes, data)
    except Exception:
        await run_in_threadpool(shutil.rmtree, absolute_path.parent, True)
        raise

    extraction = await run_in_threadpool(extract_text, absolute_path, validated.suffix)

    resume = Resume(
        id=resume_id,
        user_id=user_id,
        original_filename=validated.filename,
        stored_path=relative_path.as_posix(),
        mime_type=validated.mime_type,
        file_size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        status=extraction.status,
        extracted_text=extraction.text or None,
        text_length=len(extraction.text),
        page_count=extraction.page_count,
        error_message=extraction.error_message,
    )
    session.add(resume)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        await run_in_threadpool(shutil.rmtree, absolute_path.parent, True)
        raise

    await session.refresh(resume)
    return resume


async def list_resumes(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int = 100,
) -> list[Resume]:
    result = await session.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_resume(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
) -> Resume | None:
    result = await session.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_resume(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    settings: Settings,
) -> bool:
    resume = await get_resume(session, user_id=user_id, resume_id=resume_id)
    if resume is None:
        return False

    absolute_path = (settings.upload_path / resume.stored_path).resolve()
    upload_root = settings.upload_path.resolve()

    await session.delete(resume)
    await session.commit()

    if absolute_path.is_relative_to(upload_root) and absolute_path.parent != upload_root:
        await run_in_threadpool(shutil.rmtree, absolute_path.parent, True)
    else:
        logger.warning("简历文件路径越界，已跳过删除：%s", resume.stored_path)

    return True
