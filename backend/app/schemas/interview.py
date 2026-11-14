"""模拟面试请求与响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

InterviewType = Literal["mixed", "resume", "jd", "behavioral"]
InterviewStatus = Literal["ready", "in_progress", "completed"]
QuestionSource = Literal["resume", "jd", "behavioral"]
EvaluationKey = Literal["relevance", "correctness", "structure", "evidence", "expression"]

DIMENSION_LABELS: dict[str, str] = {
    "relevance": "相关性",
    "correctness": "专业正确性",
    "structure": "结构",
    "evidence": "证据",
    "expression": "表达",
}
DIMENSION_ORDER: tuple[str, ...] = (
    "relevance",
    "correctness",
    "structure",
    "evidence",
    "expression",
)


class InterviewCreate(BaseModel):
    resume_id: uuid.UUID
    resume_version_no: int = Field(ge=1)
    jd_id: uuid.UUID | None = None
    interview_type: InterviewType = "mixed"
    question_count: int = Field(default=8, ge=3, le=12)


class EvaluationDimension(BaseModel):
    key: EvaluationKey
    label: str
    score: int = Field(ge=0, le=100)
    comment: str


class AnswerEvaluation(BaseModel):
    dimensions: list[EvaluationDimension]
    overall_score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class InterviewQuestionItem(BaseModel):
    id: uuid.UUID
    order_index: int
    source: QuestionSource
    source_ref: str
    question: str
    intent: str
    follow_up_level: int
    parent_question_id: uuid.UUID | None
    answer: str | None
    answered_at: datetime | None
    evaluation: AnswerEvaluation | None
    score: float | None


class ReportQuestionNote(BaseModel):
    order_index: int
    question: str
    comment: str


class InterviewReport(BaseModel):
    overview: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    question_notes: list[ReportQuestionNote] = Field(default_factory=list)


class InterviewSummary(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    resume_filename: str
    resume_version_no: int
    jd_id: uuid.UUID | None
    jd_title: str | None
    interview_type: InterviewType
    status: InterviewStatus
    planned_question_count: int
    question_count: int
    answered_count: int
    total_score: float | None
    rubric_version: str
    created_at: datetime
    completed_at: datetime | None


class InterviewDetail(InterviewSummary):
    questions: list[InterviewQuestionItem]
    current_question_id: uuid.UUID | None
    dimension_scores: dict[str, float]
    report: InterviewReport | None
    summary: str | None
    model_name: str | None
    prompt_version: str | None


class InterviewAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)
