"""简历上传与查询响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

ResumeStatusLiteral = Literal["uploaded", "extracting", "extracted", "needs_ocr", "failed"]


class ResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    status: ResumeStatusLiteral
    text_length: int
    page_count: int | None
    created_at: datetime


class ResumeDetail(ResumeSummary):
    mime_type: str
    file_size: int
    sha256: str
    text_preview: str
    error_message: str | None
