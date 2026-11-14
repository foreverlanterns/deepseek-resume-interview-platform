"""四维诊断业务逻辑。"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.diagnosis import Diagnosis
from app.models.job_description import JobDescription
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.providers.base import (
    JsonCompletionProvider,
    ProviderError,
    ProviderNotConfiguredError,
)
from app.schemas.diagnosis import (
    DiagnosisDetail,
    DiagnosisSummary,
    JdMatchReport,
    KeywordReport,
    RequirementMatch,
    Suggestion,
)
from app.schemas.resume_parse import ParsedResume
from app.services.diagnosis_parser import (
    DIAGNOSIS_PROMPT_VERSION,
    DiagnosisParseError,
    normalize_suggestion_facts,
    parse_jd_match,
)
from app.services.diagnosis_rules import (
    RUBRIC_VERSION,
    WEIGHTS,
    build_jd_match_report,
    build_requirements,
    build_summary,
    completeness_checks,
    format_checks,
    keyword_report,
    rule_suggestions,
    weighted_total,
)

logger = logging.getLogger(__name__)


class DiagnosisTargetNotFoundError(Exception):
    """简历、版本或 JD 不存在。"""


class ResumeVersionNotReadyError(Exception):
    """版本没有可诊断的结构化数据。"""


class JobDescriptionNoRequirementsError(Exception):
    """JD 没有可评估的要求。"""


class DiagnosisFailedError(Exception):
    """模型调用或输出校验失败。"""


@dataclass(frozen=True)
class DiagnosisRow:
    diagnosis: Diagnosis
    resume_filename: str
    jd_title: str


def _normalize(value: str) -> str:
    return value.strip().lower()


async def create_diagnosis(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID,
    resume_version_no: int,
    jd_id: uuid.UUID,
    provider: JsonCompletionProvider,
) -> DiagnosisRow:
    resume_result = await session.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    )
    resume = resume_result.scalar_one_or_none()
    version_result = await session.execute(
        select(ResumeVersion).where(
            ResumeVersion.user_id == user_id,
            ResumeVersion.resume_id == resume_id,
            ResumeVersion.version_no == resume_version_no,
        )
    )
    version = version_result.scalar_one_or_none()
    jd_result = await session.execute(
        select(JobDescription).where(
            JobDescription.id == jd_id,
            JobDescription.user_id == user_id,
        )
    )
    jd = jd_result.scalar_one_or_none()

    if resume is None or version is None or jd is None:
        raise DiagnosisTargetNotFoundError

    effective = version.corrected_data or version.parsed_data
    if not effective:
        raise ResumeVersionNotReadyError("该版本没有可诊断的结构化数据，请先完成解析或校正")

    parsed = ParsedResume.model_validate(effective)
    requirements = build_requirements(jd)
    if not requirements:
        raise JobDescriptionNoRequirementsError("请先补充岗位技能、关键词或任职资格")

    resume_text = resume.extracted_text or ""
    resume_filename = resume.original_filename
    jd_title = jd.title

    format_items = format_checks(parsed)
    completeness_items = completeness_checks(parsed)
    keyword_items = keyword_report(jd, resume_text)
    format_score = sum(item.score for item in format_items)
    completeness_score = sum(item.score for item in completeness_items)

    jd_snapshot = {
        "title": jd.title,
        "company": jd.company,
        "required_skills": list(jd.required_skills),
        "preferred_skills": list(jd.preferred_skills),
        "keywords": list(jd.keywords),
        "responsibilities": list(jd.responsibilities),
        "qualifications": list(jd.qualifications),
    }

    # 模型调用前释放只读事务，避免长时间 idle in transaction
    await session.rollback()

    try:
        ai_result = await parse_jd_match(requirements, parsed, provider)
    except ProviderNotConfiguredError:
        raise
    except (DiagnosisParseError, ProviderError) as exc:
        logger.warning("JD 匹配诊断失败：resume_id=%s jd_id=%s", resume_id, jd_id)
        raise DiagnosisFailedError(str(exc)) from exc

    ai_by_key = {_normalize(match.requirement): match for match in ai_result.requirement_matches}
    matches: list[RequirementMatch] = []
    for spec in requirements:
        ai_match = ai_by_key.get(_normalize(spec.requirement))
        if ai_match is None:
            continue
        matches.append(
            RequirementMatch(
                requirement=spec.requirement,
                source=spec.source,
                weight=spec.weight,
                verdict=ai_match.verdict,
                evidence=ai_match.evidence,
                reason=ai_match.reason or "模型未说明理由",
            )
        )

    jd_match_report = build_jd_match_report(matches, requirements)
    jd_match_score = jd_match_report.score

    ai_suggestions = [
        Suggestion.model_validate(item)
        for item in normalize_suggestion_facts(ai_result.suggestions, resume_text)
    ]
    suggestions = _merge_suggestions(
        ai_suggestions,
        rule_suggestions(format_items, completeness_items),
    )

    total = weighted_total(
        format_score,
        completeness_score,
        keyword_items.score,
        jd_match_score,
    )
    summary = build_summary(
        format_score,
        completeness_score,
        keyword_items.score,
        jd_match_score,
        total,
    )

    diagnosis = Diagnosis(
        user_id=user_id,
        resume_id=resume_id,
        resume_version_no=resume_version_no,
        jd_id=jd_id,
        jd_snapshot=jd_snapshot,
        rubric_version=RUBRIC_VERSION,
        weights=dict(WEIGHTS),
        format_score=format_score,
        completeness_score=completeness_score,
        keyword_score=keyword_items.score,
        jd_match_score=jd_match_score,
        total_score=Decimal(str(total)),
        format_details=[item.model_dump(mode="json") for item in format_items],
        completeness_details=[item.model_dump(mode="json") for item in completeness_items],
        keyword_details=keyword_items.model_dump(mode="json"),
        jd_match_details=jd_match_report.model_dump(mode="json"),
        suggestions=[item.model_dump(mode="json") for item in suggestions],
        summary=summary,
        model_name=provider.model_name,
        prompt_version=DIAGNOSIS_PROMPT_VERSION,
    )
    session.add(diagnosis)
    await session.commit()
    await session.refresh(diagnosis)

    return DiagnosisRow(
        diagnosis=diagnosis,
        resume_filename=resume_filename,
        jd_title=jd_title,
    )


def _merge_suggestions(
    ai_suggestions: list[Suggestion],
    rule_items: list[Suggestion],
) -> list[Suggestion]:
    merged: list[Suggestion] = []
    seen: set[tuple[str, str]] = set()
    for suggestion in [*ai_suggestions, *rule_items]:
        key = (suggestion.issue.strip(), suggestion.original_text.strip())
        if key in seen:
            continue
        seen.add(key)
        merged.append(suggestion)
        if len(merged) >= 8:
            break
    return merged


async def list_diagnoses(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    resume_id: uuid.UUID | None = None,
    jd_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[DiagnosisRow]:
    statement = (
        select(Diagnosis, Resume.original_filename, JobDescription.title)
        .join(Resume, Resume.id == Diagnosis.resume_id)
        .join(JobDescription, JobDescription.id == Diagnosis.jd_id)
        .where(Diagnosis.user_id == user_id)
        .order_by(Diagnosis.created_at.desc())
        .limit(limit)
    )
    if resume_id is not None:
        statement = statement.where(Diagnosis.resume_id == resume_id)
    if jd_id is not None:
        statement = statement.where(Diagnosis.jd_id == jd_id)

    result = await session.execute(statement)
    return [
        DiagnosisRow(diagnosis=row[0], resume_filename=row[1], jd_title=row[2])
        for row in result.all()
    ]


async def get_diagnosis(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    diagnosis_id: uuid.UUID,
) -> DiagnosisRow | None:
    result = await session.execute(
        select(Diagnosis, Resume.original_filename, JobDescription.title)
        .join(Resume, Resume.id == Diagnosis.resume_id)
        .join(JobDescription, JobDescription.id == Diagnosis.jd_id)
        .where(Diagnosis.id == diagnosis_id, Diagnosis.user_id == user_id)
    )
    row = result.first()
    if row is None:
        return None
    return DiagnosisRow(diagnosis=row[0], resume_filename=row[1], jd_title=row[2])


def to_summary(row: DiagnosisRow) -> DiagnosisSummary:
    diagnosis = row.diagnosis
    return DiagnosisSummary(
        id=diagnosis.id,
        resume_id=diagnosis.resume_id,
        resume_filename=row.resume_filename,
        resume_version_no=diagnosis.resume_version_no,
        jd_id=diagnosis.jd_id,
        jd_title=row.jd_title,
        rubric_version=diagnosis.rubric_version,
        total_score=float(diagnosis.total_score),
        format_score=diagnosis.format_score,
        completeness_score=diagnosis.completeness_score,
        keyword_score=diagnosis.keyword_score,
        jd_match_score=diagnosis.jd_match_score,
        created_at=diagnosis.created_at,
    )


def to_detail(row: DiagnosisRow) -> DiagnosisDetail:
    diagnosis = row.diagnosis
    summary = to_summary(row)
    return DiagnosisDetail(
        **summary.model_dump(),
        weights={key: float(value) for key, value in diagnosis.weights.items()},
        format_details=diagnosis.format_details,
        completeness_details=diagnosis.completeness_details,
        keyword_details=KeywordReport.model_validate(diagnosis.keyword_details),
        jd_match_details=JdMatchReport.model_validate(diagnosis.jd_match_details),
        suggestions=[Suggestion.model_validate(item) for item in diagnosis.suggestions],
        summary=diagnosis.summary,
        model_name=diagnosis.model_name,
        prompt_version=diagnosis.prompt_version,
    )
