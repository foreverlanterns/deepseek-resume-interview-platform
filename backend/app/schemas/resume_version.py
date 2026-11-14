"""简历结构化版本响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.schemas.resume_parse import ParsedResume

VersionStatusLiteral = Literal["parsed", "corrected", "failed"]


class ResumeVersionSummary(BaseModel):
    version_no: int
    status: VersionStatusLiteral
    model_name: str | None
    prompt_version: str | None
    parser_version: str | None
    base_version_no: int | None
    has_corrections: bool
    created_at: datetime


class ResumeVersionDetail(ResumeVersionSummary):
    parsed_data: ParsedResume | None
    corrected_data: ParsedResume | None
    effective_data: ParsedResume | None
    error_message: str | None


class CorrectionRequest(BaseModel):
    data: ParsedResume
