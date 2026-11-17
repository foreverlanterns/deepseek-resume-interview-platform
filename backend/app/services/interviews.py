"""模拟面试业务编排。"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.providers.base import JsonCompletionProvider
from app.schemas.interview import (
    DIMENSION_ORDER,
    AnswerEvaluation,
    InterviewCreate,
    InterviewDetail,
    InterviewReport,
    InterviewSummary,
    InterviewType,
)
from app.schemas.resume_parse import ParsedResume
from app.services.interview_eval import FollowUpAI, InterviewEvalError, evaluate_answer
from app.services.interview_plan import (
    INTERVIEW_PLAN_PROMPT_VERSION,
    InterviewPlanError,
    generate_plan,
)
from app.services.interview_report import (
    INTERVIEW_REPORT_PROMPT_VERSION,
    InterviewReportError,
    generate_report,
)

logger = logging.getLogger(__name__)

RUBRIC_VERSION = "interview_rubric_v1"


class InterviewTargetNotFoundError(Exception):
    """简历、版本或岗位不存在。"""


class InterviewStateError(Exception):
    """当前状态不允许该操作。"""


class InterviewFailedError(Exception):
    """模型调用或结构校验失败。"""


@dataclass(frozen=True)
class InterviewRow:
    interview: Interview
    resume_filename: str
    question_count: int
    answered_count: int


def _jd_snapshot(jd: JobDescription | None) -> dict[str, Any] | None:
    if jd is None:
        return None
    return {
        "title": jd.title,
        "company": jd.company,
        "raw_text": jd.raw_text,
        "required_skills": list(jd.required_skills),
        "preferred_skills": list(jd.preferred_skills),
        "keywords": list(jd.keywords),
        "responsibilities": list(jd.responsibilities),
        "qualifications": list(jd.qualifications),
    }


def _jd_has_content(snapshot: dict[str, Any]) -> bool:
    return any(
        [
            snapshot.get("raw_text"),
            snapshot.get("required_skills"),
            snapshot.get("preferred_skills"),
            snapshot.get("keywords"),
            snapshot.get("responsibilities"),
            snapshot.get("qualifications"),
        ]
    )


async def load_questions(
    session: AsyncSession,
    *,
    interview_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[InterviewQuestion]:
    result = await session.execute(
        select(InterviewQuestion)
        .where(
            InterviewQuestion.interview_id == interview_id,
            InterviewQuestion.user_id == user_id,
        )
        .order_by(InterviewQuestion.order_index)
    )
    return list(result.scalars().all())


def _average_dimensions(questions: list[InterviewQuestion]) -> dict[str, float]:
    totals: dict[str, list[int]] = {key: [] for key in DIMENSION_ORDER}
    for question in questions:
        if not question.evaluation:
            continue
        dimensions = question.evaluation.get("dimensions") or []
        for item in dimensions:
            key = item.get("key")
            score = item.get("score")
            if key in totals and isinstance(score, int | float):
                totals[key].append(int(score))
    return {
        key: round(sum(values) / len(values), 1) if values else 0.0
        for key, values in totals.items()
    }


def _complete(interview: Interview, questions: list[InterviewQuestion]) -> None:
    answered = [question for question in questions if question.answer]
    if not answered:
        return
    scores = [float(question.score) for question in answered if question.score is not None]
    total = round(sum(scores) / len(scores), 2) if scores else 0.0
    interview.status = "completed"
    interview.total_score = Decimal(str(total))
    interview.dimension_scores = _average_dimensions(answered)
    interview.summary = f"共回答 {len(answered)} 题，平均分 {total:.1f}。"
    interview.completed_at = datetime.now(UTC)


async def create_interview(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: InterviewCreate,
    provider: JsonCompletionProvider,
) -> InterviewRow:
    resume_result = await session.execute(
        select(Resume).where(Resume.id == payload.resume_id, Resume.user_id == user_id)
    )
    resume = resume_result.scalar_one_or_none()
    version_result = await session.execute(
        select(ResumeVersion).where(
            ResumeVersion.user_id == user_id,
            ResumeVersion.resume_id == payload.resume_id,
            ResumeVersion.version_no == payload.resume_version_no,
        )
    )
    version = version_result.scalar_one_or_none()

    jd: JobDescription | None = None
    if payload.jd_id is not None:
        jd_result = await session.execute(
            select(JobDescription).where(
                JobDescription.id == payload.jd_id,
                JobDescription.user_id == user_id,
            )
        )
        jd = jd_result.scalar_one_or_none()

    if resume is None or version is None or (payload.jd_id is not None and jd is None):
        raise InterviewTargetNotFoundError

    if payload.interview_type == "jd" and jd is None:
        raise InterviewStateError("岗位匹配面试需要先选择目标岗位")

    effective = version.corrected_data or version.parsed_data
    if not effective:
        raise InterviewStateError("该版本没有结构化数据，请先完成解析或人工校正")

    parsed = ParsedResume.model_validate(effective)
    snapshot = _jd_snapshot(jd)
    if payload.interview_type == "jd" and snapshot is not None and not _jd_has_content(snapshot):
        raise InterviewStateError("目标岗位没有可用的要求内容，请补充技能、关键词或岗位原文")

    resume_text = resume.extracted_text or ""
    resume_filename = resume.original_filename
    interview_type: InterviewType = payload.interview_type

    # 模型调用前释放只读事务
    await session.rollback()

    try:
        plan = await generate_plan(
            parsed,
            snapshot,
            interview_type,
            payload.question_count,
            provider,
            resume_text=resume_text,
        )
    except InterviewPlanError as exc:
        logger.warning("面试出题失败：resume_id=%s", payload.resume_id)
        raise InterviewFailedError(str(exc)) from exc

    interview = Interview(
        user_id=user_id,
        resume_id=payload.resume_id,
        resume_version_no=payload.resume_version_no,
        jd_id=payload.jd_id,
        jd_snapshot=snapshot,
        interview_type=interview_type,
        status="ready",
        planned_question_count=len(plan),
        rubric_version=RUBRIC_VERSION,
        model_name=provider.model_name,
        prompt_version=INTERVIEW_PLAN_PROMPT_VERSION,
    )
    session.add(interview)
    await session.flush()

    questions = [
        InterviewQuestion(
            interview_id=interview.id,
            user_id=user_id,
            order_index=index,
            source=item["source"],
            source_ref=item["source_ref"],
            question=item["question"],
            intent=item["intent"],
            follow_up_level=0,
            parent_question_id=None,
        )
        for index, item in enumerate(plan, start=1)
    ]
    session.add_all(questions)
    await session.commit()
    await session.refresh(interview)

    return InterviewRow(
        interview=interview,
        resume_filename=resume_filename,
        question_count=len(questions),
        answered_count=0,
    )


async def list_interviews(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[InterviewRow]:
    question_count = (
        select(func.count(InterviewQuestion.id))
        .where(InterviewQuestion.interview_id == Interview.id)
        .correlate(Interview)
        .scalar_subquery()
    )
    answered_count = (
        select(func.count(InterviewQuestion.id))
        .where(
            InterviewQuestion.interview_id == Interview.id,
            InterviewQuestion.answer.is_not(None),
        )
        .correlate(Interview)
        .scalar_subquery()
    )

    statement = (
        select(Interview, Resume.original_filename, question_count, answered_count)
        .join(Resume, Resume.id == Interview.resume_id)
        .where(Interview.user_id == user_id)
        .order_by(Interview.created_at.desc())
        .limit(limit)
    )
    if resume_id is not None:
        statement = statement.where(Interview.resume_id == resume_id)

    result = await session.execute(statement)
    return [
        InterviewRow(
            interview=row[0],
            resume_filename=row[1],
            question_count=int(row[2] or 0),
            answered_count=int(row[3] or 0),
        )
        for row in result.all()
    ]


async def get_interview(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    interview_id: uuid.UUID,
) -> InterviewRow | None:
    result = await session.execute(
        select(Interview, Resume.original_filename)
        .join(Resume, Resume.id == Interview.resume_id)
        .where(Interview.id == interview_id, Interview.user_id == user_id)
    )
    row = result.first()
    if row is None:
        return None

    questions = await load_questions(session, interview_id=interview_id, user_id=user_id)
    return InterviewRow(
        interview=row[0],
        resume_filename=row[1],
        question_count=len(questions),
        answered_count=sum(1 for question in questions if question.answer),
    )


async def answer_question(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    interview_id: uuid.UUID,
    question_id: uuid.UUID,
    answer: str,
    provider: JsonCompletionProvider,
) -> InterviewRow:
    interview = await session.get(Interview, interview_id)
    if interview is None or interview.user_id != user_id:
        raise InterviewTargetNotFoundError
    if interview.status == "completed":
        raise InterviewStateError("本次面试已结束，不能继续作答")

    question = await session.get(InterviewQuestion, question_id)
    if question is None or question.interview_id != interview_id or question.user_id != user_id:
        raise InterviewTargetNotFoundError
    if question.answer is not None:
        raise InterviewStateError("该题已经作答，不能重复提交")

    questions = await load_questions(session, interview_id=interview_id, user_id=user_id)
    current = next((item for item in questions if item.answer is None), None)
    if current is None or current.id != question_id:
        raise InterviewStateError("请按顺序回答当前问题")

    resume = await session.get(Resume, interview.resume_id)
    version_result = await session.execute(
        select(ResumeVersion).where(
            ResumeVersion.user_id == user_id,
            ResumeVersion.resume_id == interview.resume_id,
            ResumeVersion.version_no == interview.resume_version_no,
        )
    )
    version = version_result.scalar_one_or_none()
    effective = (version.corrected_data or version.parsed_data) if version else None
    if resume is None or not effective:
        raise InterviewStateError("简历数据不完整，无法评价回答")

    parsed = ParsedResume.model_validate(effective)
    resume_filename = resume.original_filename
    answered = [item for item in questions if item.answer]
    history = [
        {
            "question": item.question,
            "answer": (item.answer or "")[:1500],
            "score": f"{float(item.score):.0f}" if item.score is not None else "",
        }
        for item in answered[-3:]
    ]

    snapshot = interview.jd_snapshot
    follow_up_level = question.follow_up_level
    source = question.source
    source_ref = question.source_ref
    question_text = question.question
    intent = question.intent

    await session.rollback()

    try:
        evaluation, follow_up = await evaluate_answer(
            parsed=parsed,
            jd_snapshot=snapshot,
            question=question_text,
            source=source,
            source_ref=source_ref,
            intent=intent,
            follow_up_level=follow_up_level,
            answer=answer.strip(),
            history=history,
            provider=provider,
        )
    except InterviewEvalError as exc:
        logger.warning("面试评价失败：interview_id=%s question_id=%s", interview_id, question_id)
        raise InterviewFailedError(str(exc)) from exc

    # 重新读取，避免模型调用期间状态变化
    interview = await session.get(Interview, interview_id)
    question = await session.get(InterviewQuestion, question_id)
    if interview is None or question is None or interview.user_id != user_id:
        raise InterviewTargetNotFoundError
    if question.answer is not None:
        raise InterviewStateError("该题已经作答，不能重复提交")

    question.answer = answer.strip()
    question.answered_at = datetime.now(UTC)
    question.evaluation = evaluation.model_dump(mode="json")
    question.score = Decimal(str(evaluation.overall_score))
    interview.status = "in_progress"

    follow_up_created = await _maybe_create_follow_up(
        session,
        interview=interview,
        question=question,
        follow_up=follow_up,
        user_id=user_id,
    )

    await session.flush()
    questions = await load_questions(session, interview_id=interview_id, user_id=user_id)

    if not follow_up_created and all(item.answer is not None for item in questions):
        _complete(interview, questions)

    answered_count = sum(1 for item in questions if item.answer)
    question_count = len(questions)

    await session.commit()
    await session.refresh(interview)

    return InterviewRow(
        interview=interview,
        resume_filename=resume_filename,
        question_count=question_count,
        answered_count=answered_count,
    )


async def _maybe_create_follow_up(
    session: AsyncSession,
    *,
    interview: Interview,
    question: InterviewQuestion,
    follow_up: FollowUpAI | None,
    user_id: uuid.UUID,
) -> bool:
    if follow_up is None or question.follow_up_level >= 2:
        return False

    text = follow_up.question.strip()
    if not text:
        return False

    normalized = "".join(text.split()).lower()
    existing = await load_questions(session, interview_id=interview.id, user_id=user_id)
    if any("".join(item.question.split()).lower() == normalized for item in existing):
        return False

    await session.execute(
        update(InterviewQuestion)
        .where(
            InterviewQuestion.interview_id == interview.id,
            InterviewQuestion.order_index > question.order_index,
        )
        .values(order_index=InterviewQuestion.order_index + 1)
    )

    session.add(
        InterviewQuestion(
            interview_id=interview.id,
            user_id=user_id,
            order_index=question.order_index + 1,
            source=question.source,
            source_ref=question.source_ref,
            question=text,
            intent=(follow_up.intent.strip() or question.intent)[:500],
            follow_up_level=question.follow_up_level + 1,
            parent_question_id=question.id,
        )
    )
    return True


async def finish_interview(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    interview_id: uuid.UUID,
) -> InterviewRow:
    interview = await session.get(Interview, interview_id)
    if interview is None or interview.user_id != user_id:
        raise InterviewTargetNotFoundError

    questions = await load_questions(session, interview_id=interview_id, user_id=user_id)
    if interview.status != "completed":
        if not any(item.answer for item in questions):
            raise InterviewStateError("至少回答一道题后才能结束面试")
        _complete(interview, questions)
        await session.commit()

    resume = await session.get(Resume, interview.resume_id)
    return InterviewRow(
        interview=interview,
        resume_filename=resume.original_filename if resume else "",
        question_count=len(questions),
        answered_count=sum(1 for item in questions if item.answer),
    )


async def build_interview_report(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    interview_id: uuid.UUID,
    provider: JsonCompletionProvider,
    force: bool = False,
) -> InterviewRow:
    interview = await session.get(Interview, interview_id)
    if interview is None or interview.user_id != user_id:
        raise InterviewTargetNotFoundError
    if interview.status != "completed":
        raise InterviewStateError("请先结束面试，再生成复盘报告")

    questions = await load_questions(session, interview_id=interview_id, user_id=user_id)
    answered = [item for item in questions if item.answer]
    if not answered:
        raise InterviewStateError("还没有可复盘的作答记录")

    resume = await session.get(Resume, interview.resume_id)
    version_result = await session.execute(
        select(ResumeVersion).where(
            ResumeVersion.user_id == user_id,
            ResumeVersion.resume_id == interview.resume_id,
            ResumeVersion.version_no == interview.resume_version_no,
        )
    )
    version = version_result.scalar_one_or_none()
    effective = (version.corrected_data or version.parsed_data) if version else None
    if resume is None or not effective:
        raise InterviewStateError("简历数据不完整，无法生成报告")

    if interview.report is not None and not force:
        return InterviewRow(
            interview=interview,
            resume_filename=resume.original_filename,
            question_count=len(questions),
            answered_count=len(answered),
        )

    parsed = ParsedResume.model_validate(effective)
    resume_filename = resume.original_filename
    total_score = float(interview.total_score or 0)
    dimension_scores = _average_dimensions(answered)

    items: list[dict[str, Any]] = []
    for item in answered:
        evaluation = item.evaluation or {}
        items.append(
            {
                "order_index": item.order_index,
                "source": item.source,
                "question": item.question,
                "answer": (item.answer or "")[:2000],
                "score": float(item.score or 0),
                "summary": evaluation.get("summary", ""),
                "dimensions": [
                    {"key": dimension.get("key"), "score": dimension.get("score")}
                    for dimension in evaluation.get("dimensions") or []
                ],
            }
        )

    snapshot = interview.jd_snapshot

    await session.rollback()

    try:
        report = await generate_report(
            parsed=parsed,
            jd_snapshot=snapshot,
            items=items,
            total_score=total_score,
            dimension_scores=dimension_scores,
            provider=provider,
        )
    except InterviewReportError as exc:
        logger.warning("面试报告生成失败：interview_id=%s", interview_id)
        raise InterviewFailedError(str(exc)) from exc

    interview = await session.get(Interview, interview_id)
    if interview is None or interview.user_id != user_id:
        raise InterviewTargetNotFoundError
    interview.report = report.model_dump(mode="json")
    interview.prompt_version = INTERVIEW_REPORT_PROMPT_VERSION
    await session.commit()
    await session.refresh(interview)

    return InterviewRow(
        interview=interview,
        resume_filename=resume_filename,
        question_count=len(questions),
        answered_count=len(answered),
    )


def to_summary(row: InterviewRow) -> InterviewSummary:
    interview = row.interview
    snapshot = interview.jd_snapshot or {}
    return InterviewSummary(
        id=interview.id,
        resume_id=interview.resume_id,
        resume_filename=row.resume_filename,
        resume_version_no=interview.resume_version_no,
        jd_id=interview.jd_id,
        jd_title=snapshot.get("title"),
        interview_type=interview.interview_type,  # type: ignore[arg-type]
        status=interview.status,  # type: ignore[arg-type]
        planned_question_count=interview.planned_question_count,
        question_count=row.question_count,
        answered_count=row.answered_count,
        total_score=float(interview.total_score) if interview.total_score is not None else None,
        rubric_version=interview.rubric_version,
        created_at=interview.created_at,
        completed_at=interview.completed_at,
    )


def to_detail(row: InterviewRow, questions: list[InterviewQuestion]) -> InterviewDetail:
    interview = row.interview
    summary = to_summary(row)
    answered = [item for item in questions if item.answer]
    current = (
        next((item for item in questions if item.answer is None), None)
        if interview.status != "completed"
        else None
    )
    dimension_scores = (
        {key: float(value) for key, value in interview.dimension_scores.items()}
        if interview.dimension_scores
        else _average_dimensions(answered)
    )

    return InterviewDetail(
        **summary.model_dump(),
        questions=[
            {
                "id": item.id,
                "order_index": item.order_index,
                "source": item.source,
                "source_ref": item.source_ref,
                "question": item.question,
                "intent": item.intent,
                "follow_up_level": item.follow_up_level,
                "parent_question_id": item.parent_question_id,
                "answer": item.answer,
                "answered_at": item.answered_at,
                "evaluation": (
                    AnswerEvaluation.model_validate(item.evaluation) if item.evaluation else None
                ),
                "score": float(item.score) if item.score is not None else None,
            }
            for item in questions
        ],
        current_question_id=current.id if current else None,
        dimension_scores=dimension_scores,
        report=InterviewReport.model_validate(interview.report) if interview.report else None,
        summary=interview.summary,
        model_name=interview.model_name,
        prompt_version=interview.prompt_version,
    )
