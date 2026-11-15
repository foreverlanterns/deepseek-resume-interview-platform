"""成长分析：只读聚合诊断与面试记录。"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnosis import Diagnosis
from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.resume import Resume
from app.schemas.analytics import (
    AnalyticsOverview,
    DiagnosisPoint,
    DiagnosisTrendGroup,
    DiagnosisTrendResponse,
    DimensionAverage,
    InterviewPoint,
    InterviewTrendGroup,
    InterviewTrendResponse,
    KeywordGap,
    LatestScore,
    RequirementGap,
    WeaknessReport,
)
from app.schemas.interview import DIMENSION_LABELS, DIMENSION_ORDER

MAX_ROWS = 300
TOP_GAPS = 10


def _snapshot_title(snapshot: dict[str, Any] | None) -> str | None:
    if not isinstance(snapshot, dict):
        return None
    title = snapshot.get("title")
    return str(title) if title else None


def _round(value: float, digits: int = 2) -> float:
    return round(float(value), digits)


async def _count(
    session: AsyncSession,
    model: type[Any],
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID | None,
    extra: list[Any] | None = None,
) -> int:
    statement = select(func.count()).select_from(model).where(model.user_id == user_id)
    if resume_id is not None:
        statement = statement.where(model.resume_id == resume_id)
    for condition in extra or []:
        statement = statement.where(condition)
    return int((await session.execute(statement)).scalar_one())


async def get_overview(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID | None = None,
) -> AnalyticsOverview:
    diagnosis_count = await _count(session, Diagnosis, user_id=user_id, resume_id=resume_id)
    interview_count = await _count(session, Interview, user_id=user_id, resume_id=resume_id)
    completed_count = await _count(
        session,
        Interview,
        user_id=user_id,
        resume_id=resume_id,
        extra=[Interview.status == "completed"],
    )

    resume_statement = select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
    if resume_id is not None:
        resume_statement = resume_statement.where(Resume.id == resume_id)
    resume_count = int((await session.execute(resume_statement)).scalar_one())

    diagnosis_statement = (
        select(Diagnosis, Resume.original_filename)
        .join(Resume, Resume.id == Diagnosis.resume_id)
        .where(Diagnosis.user_id == user_id)
        .order_by(Diagnosis.created_at.desc())
        .limit(1)
    )
    if resume_id is not None:
        diagnosis_statement = diagnosis_statement.where(Diagnosis.resume_id == resume_id)
    diagnosis_row = (await session.execute(diagnosis_statement)).first()

    interview_statement = (
        select(Interview, Resume.original_filename)
        .join(Resume, Resume.id == Interview.resume_id)
        .where(Interview.user_id == user_id, Interview.status == "completed")
        .order_by(Interview.created_at.desc())
        .limit(1)
    )
    if resume_id is not None:
        interview_statement = interview_statement.where(Interview.resume_id == resume_id)
    interview_row = (await session.execute(interview_statement)).first()

    latest_diagnosis = None
    if diagnosis_row is not None:
        diagnosis = diagnosis_row[0]
        latest_diagnosis = LatestScore(
            id=diagnosis.id,
            total_score=_round(float(diagnosis.total_score)),
            created_at=diagnosis.created_at,
            resume_filename=diagnosis_row[1],
            jd_title=_snapshot_title(diagnosis.jd_snapshot),
        )

    latest_interview = None
    if interview_row is not None and interview_row[0].total_score is not None:
        interview = interview_row[0]
        latest_interview = LatestScore(
            id=interview.id,
            total_score=_round(float(interview.total_score)),
            created_at=interview.created_at,
            resume_filename=interview_row[1],
            jd_title=_snapshot_title(interview.jd_snapshot),
        )

    return AnalyticsOverview(
        resume_count=resume_count,
        diagnosis_count=diagnosis_count,
        interview_count=interview_count,
        completed_interview_count=completed_count,
        latest_diagnosis=latest_diagnosis,
        latest_interview=latest_interview,
    )


async def get_diagnosis_trends(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID | None = None,
    jd_id: uuid.UUID | None = None,
) -> DiagnosisTrendResponse:
    statement = (
        select(Diagnosis, Resume.original_filename)
        .join(Resume, Resume.id == Diagnosis.resume_id)
        .where(Diagnosis.user_id == user_id)
        .order_by(Diagnosis.created_at)
        .limit(MAX_ROWS)
    )
    if resume_id is not None:
        statement = statement.where(Diagnosis.resume_id == resume_id)
    if jd_id is not None:
        statement = statement.where(Diagnosis.jd_id == jd_id)

    rows = (await session.execute(statement)).all()
    grouped: dict[tuple[uuid.UUID, uuid.UUID, str], list[Any]] = defaultdict(list)
    for diagnosis, filename in rows:
        key = (diagnosis.resume_id, diagnosis.jd_id, diagnosis.rubric_version)
        grouped[key].append((diagnosis, filename))

    groups: list[DiagnosisTrendGroup] = []
    for (group_resume_id, group_jd_id, rubric_version), items in grouped.items():
        points = [
            DiagnosisPoint(
                id=diagnosis.id,
                created_at=diagnosis.created_at,
                resume_version_no=diagnosis.resume_version_no,
                total_score=_round(float(diagnosis.total_score)),
                format_score=diagnosis.format_score,
                completeness_score=diagnosis.completeness_score,
                keyword_score=diagnosis.keyword_score,
                jd_match_score=diagnosis.jd_match_score,
            )
            for diagnosis, _ in items
        ]
        totals = [point.total_score for point in points]
        first = points[0]
        last = points[-1]
        groups.append(
            DiagnosisTrendGroup(
                resume_id=group_resume_id,
                resume_filename=items[0][1],
                jd_id=group_jd_id,
                jd_title=_snapshot_title(items[0][0].jd_snapshot) or "未命名岗位",
                rubric_version=rubric_version,
                points=points,
                average_total=_round(sum(totals) / len(totals)),
                best_total=_round(max(totals)),
                improvement=_round(last.total_score - first.total_score)
                if len(points) > 1
                else 0.0,
            )
        )

    groups.sort(key=lambda group: group.points[-1].created_at, reverse=True)
    return DiagnosisTrendResponse(groups=groups)


async def get_interview_trends(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID | None = None,
    jd_id: uuid.UUID | None = None,
    interview_type: str | None = None,
) -> InterviewTrendResponse:
    statement = (
        select(
            Interview,
            Resume.original_filename,
            select(func.count(InterviewQuestion.id))
            .where(InterviewQuestion.interview_id == Interview.id)
            .correlate(Interview)
            .scalar_subquery(),
            select(func.count(InterviewQuestion.id))
            .where(
                InterviewQuestion.interview_id == Interview.id,
                InterviewQuestion.answer.is_not(None),
            )
            .correlate(Interview)
            .scalar_subquery(),
        )
        .join(Resume, Resume.id == Interview.resume_id)
        .where(
            Interview.user_id == user_id,
            Interview.status == "completed",
            Interview.total_score.is_not(None),
        )
        .order_by(Interview.created_at)
        .limit(MAX_ROWS)
    )
    if resume_id is not None:
        statement = statement.where(Interview.resume_id == resume_id)
    if jd_id is not None:
        statement = statement.where(Interview.jd_id == jd_id)
    if interview_type is not None:
        statement = statement.where(Interview.interview_type == interview_type)

    rows = (await session.execute(statement)).all()
    grouped: dict[tuple[uuid.UUID, uuid.UUID | None, str, str], list[Any]] = defaultdict(list)
    for interview, filename, question_count, answered_count in rows:
        key = (
            interview.resume_id,
            interview.jd_id,
            interview.interview_type,
            interview.rubric_version,
        )
        grouped[key].append(
            (interview, filename, int(question_count or 0), int(answered_count or 0))
        )

    groups: list[InterviewTrendGroup] = []
    for (
        group_resume_id,
        group_jd_id,
        interview_type_value,
        rubric_version,
    ), items in grouped.items():
        points: list[InterviewPoint] = []
        for interview, _, question_count, answered_count in items:
            raw_scores = interview.dimension_scores or {}
            dimensions = {
                key: _round(float(raw_scores[key]), 1)
                for key in DIMENSION_ORDER
                if isinstance(raw_scores.get(key), int | float)
            }
            points.append(
                InterviewPoint(
                    id=interview.id,
                    created_at=interview.created_at,
                    resume_version_no=interview.resume_version_no,
                    total_score=_round(float(interview.total_score or 0)),
                    question_count=question_count,
                    answered_count=answered_count,
                    dimension_scores=dimensions,
                )
            )

        totals = [point.total_score for point in points]
        improvement = 0.0
        dimension_changes: dict[str, float] = {}
        if len(points) > 1:
            improvement = _round(points[-1].total_score - points[0].total_score)
            for key in DIMENSION_ORDER:
                first_value = points[0].dimension_scores.get(key)
                last_value = points[-1].dimension_scores.get(key)
                if first_value is not None and last_value is not None:
                    dimension_changes[key] = _round(last_value - first_value, 1)

        groups.append(
            InterviewTrendGroup(
                resume_id=group_resume_id,
                resume_filename=items[0][1],
                jd_id=group_jd_id,
                jd_title=_snapshot_title(items[0][0].jd_snapshot),
                interview_type=interview_type_value,
                rubric_version=rubric_version,
                points=points,
                average_total=_round(sum(totals) / len(totals)),
                best_total=_round(max(totals)),
                improvement=improvement,
                dimension_changes=dimension_changes,
            )
        )

    groups.sort(key=lambda group: group.points[-1].created_at, reverse=True)
    return InterviewTrendResponse(groups=groups)


async def get_weaknesses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID | None = None,
) -> WeaknessReport:
    diagnosis_statement = (
        select(Diagnosis)
        .where(Diagnosis.user_id == user_id)
        .order_by(Diagnosis.created_at.desc())
        .limit(MAX_ROWS)
    )
    if resume_id is not None:
        diagnosis_statement = diagnosis_statement.where(Diagnosis.resume_id == resume_id)
    diagnoses = (await session.execute(diagnosis_statement)).scalars().all()

    keyword_counter: Counter[str] = Counter()
    requirement_counter: Counter[str] = Counter()

    for diagnosis in diagnoses:
        keyword_details = diagnosis.keyword_details
        if isinstance(keyword_details, dict):
            for hit in keyword_details.get("hits") or []:
                if isinstance(hit, dict) and not hit.get("matched"):
                    keyword = str(hit.get("keyword") or "").strip()
                    if keyword:
                        keyword_counter[keyword] += 1

        jd_match_details = diagnosis.jd_match_details
        if isinstance(jd_match_details, dict):
            for match in jd_match_details.get("matches") or []:
                if not isinstance(match, dict):
                    continue
                if match.get("verdict") in {"missing", "partial"}:
                    requirement = str(match.get("requirement") or "").strip()
                    if requirement:
                        requirement_counter[requirement] += 1

    interview_statement = (
        select(Interview)
        .where(
            Interview.user_id == user_id,
            Interview.status == "completed",
            Interview.total_score.is_not(None),
        )
        .order_by(Interview.created_at.desc())
        .limit(MAX_ROWS)
    )
    if resume_id is not None:
        interview_statement = interview_statement.where(Interview.resume_id == resume_id)
    interviews = (await session.execute(interview_statement)).scalars().all()

    dimension_totals: dict[str, float] = defaultdict(float)
    dimension_counts: dict[str, int] = defaultdict(int)
    for interview in interviews:
        if not isinstance(interview.dimension_scores, dict):
            continue
        for key in DIMENSION_ORDER:
            value = interview.dimension_scores.get(key)
            if isinstance(value, int | float):
                dimension_totals[key] += float(value)
                dimension_counts[key] += 1

    dimensions = [
        DimensionAverage(
            key=key,
            label=DIMENSION_LABELS[key],
            average=_round(dimension_totals[key] / dimension_counts[key], 1),
            sample_count=dimension_counts[key],
        )
        for key in DIMENSION_ORDER
        if dimension_counts[key] > 0
    ]
    lowest = min(dimensions, key=lambda item: item.average) if dimensions else None

    return WeaknessReport(
        missing_keywords=[
            KeywordGap(keyword=keyword, count=count)
            for keyword, count in sorted(
                keyword_counter.items(), key=lambda item: (-item[1], item[0])
            )[:TOP_GAPS]
        ],
        missing_requirements=[
            RequirementGap(requirement=requirement, count=count)
            for requirement, count in sorted(
                requirement_counter.items(), key=lambda item: (-item[1], item[0])
            )[:TOP_GAPS]
        ],
        interview_dimensions=dimensions,
        lowest_dimension=lowest.key if lowest else None,
    )
