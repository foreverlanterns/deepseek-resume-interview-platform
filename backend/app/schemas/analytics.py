"""成长分析响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LatestScore(BaseModel):
    id: uuid.UUID
    total_score: float
    created_at: datetime
    resume_filename: str
    jd_title: str | None


class AnalyticsOverview(BaseModel):
    resume_count: int
    diagnosis_count: int
    interview_count: int
    completed_interview_count: int
    latest_diagnosis: LatestScore | None
    latest_interview: LatestScore | None


class DiagnosisPoint(BaseModel):
    id: uuid.UUID
    created_at: datetime
    resume_version_no: int
    total_score: float
    format_score: int
    completeness_score: int
    keyword_score: int
    jd_match_score: int


class DiagnosisTrendGroup(BaseModel):
    resume_id: uuid.UUID
    resume_filename: str
    jd_id: uuid.UUID
    jd_title: str
    rubric_version: str
    points: list[DiagnosisPoint]
    average_total: float
    best_total: float
    improvement: float


class DiagnosisTrendResponse(BaseModel):
    groups: list[DiagnosisTrendGroup]


class InterviewPoint(BaseModel):
    id: uuid.UUID
    created_at: datetime
    resume_version_no: int
    total_score: float
    question_count: int
    answered_count: int
    dimension_scores: dict[str, float] = Field(default_factory=dict)


class InterviewTrendGroup(BaseModel):
    resume_id: uuid.UUID
    resume_filename: str
    jd_id: uuid.UUID | None
    jd_title: str | None
    interview_type: str
    rubric_version: str
    points: list[InterviewPoint]
    average_total: float
    best_total: float
    improvement: float
    dimension_changes: dict[str, float] = Field(default_factory=dict)


class InterviewTrendResponse(BaseModel):
    groups: list[InterviewTrendGroup]


class KeywordGap(BaseModel):
    keyword: str
    count: int


class RequirementGap(BaseModel):
    requirement: str
    count: int


class DimensionAverage(BaseModel):
    key: str
    label: str
    average: float
    sample_count: int


class WeaknessReport(BaseModel):
    missing_keywords: list[KeywordGap]
    missing_requirements: list[RequirementGap]
    interview_dimensions: list[DimensionAverage]
    lowest_dimension: str | None
