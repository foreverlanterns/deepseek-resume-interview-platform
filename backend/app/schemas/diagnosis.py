"""四维诊断请求与响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

DimensionKey = Literal["format", "completeness", "keyword", "jd_match"]
CheckStatus = Literal["pass", "partial", "fail"]
Verdict = Literal["met", "partial", "missing"]
SuggestionStatus = Literal["supported", "needs_user_input", "needs_review"]


class DimensionCheck(BaseModel):
    name: str
    label: str
    status: CheckStatus
    score: int
    max_score: int
    message: str


class KeywordHit(BaseModel):
    keyword: str
    source: Literal["required", "preferred", "keyword"]
    weight: int
    matched: bool


class KeywordReport(BaseModel):
    score: int
    matched_count: int
    total_count: int
    matched_weight: int
    total_weight: int
    hits: list[KeywordHit]


class RequirementMatch(BaseModel):
    requirement: str
    source: Literal["required", "preferred"]
    weight: int
    verdict: Verdict
    evidence: str | None
    reason: str


class JdMatchReport(BaseModel):
    score: int
    matched_count: int
    partial_count: int
    missing_count: int
    total: int
    matches: list[RequirementMatch]


class Suggestion(BaseModel):
    dimension: DimensionKey
    original_text: str
    issue: str
    suggestion: str
    rewritten_example: str
    reason: str
    fact_status: SuggestionStatus
    missing_facts: list[str] = Field(default_factory=list)
    original_text_verified: bool = False


class DiagnosisCreate(BaseModel):
    resume_id: uuid.UUID
    resume_version_no: int = Field(ge=1)
    jd_id: uuid.UUID


class DiagnosisSummary(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    resume_filename: str
    resume_version_no: int
    jd_id: uuid.UUID
    jd_title: str
    rubric_version: str
    total_score: float
    format_score: int
    completeness_score: int
    keyword_score: int
    jd_match_score: int
    created_at: datetime


class DiagnosisDetail(DiagnosisSummary):
    weights: dict[str, float]
    format_details: list[DimensionCheck]
    completeness_details: list[DimensionCheck]
    keyword_details: KeywordReport
    jd_match_details: JdMatchReport
    suggestions: list[Suggestion]
    summary: str
    model_name: str | None
    prompt_version: str | None
