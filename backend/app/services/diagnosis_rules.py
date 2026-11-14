"""四维诊断的确定性规则评分。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.models.job_description import JobDescription
from app.schemas.diagnosis import (
    DimensionCheck,
    JdMatchReport,
    KeywordHit,
    KeywordReport,
    RequirementMatch,
    Suggestion,
)
from app.schemas.resume_parse import ParsedResume

RUBRIC_VERSION = "rubric_v1"
WEIGHTS = {
    "format": 0.15,
    "completeness": 0.20,
    "keyword": 0.25,
    "jd_match": 0.40,
}

DATE_RE = re.compile(
    r"^\d{4}([./-]\d{1,2})?$|^\d{4}年\d{1,2}月$|^(至今|现在|present|now)$",
    re.IGNORECASE,
)


def _check(
    name: str,
    label: str,
    score: int,
    max_score: int,
    message: str,
) -> DimensionCheck:
    bounded = max(0, min(score, max_score))
    status: Literal["pass", "partial", "fail"]
    if bounded >= max_score:
        status = "pass"
    elif bounded > 0:
        status = "partial"
    else:
        status = "fail"
    return DimensionCheck(
        name=name,
        label=label,
        status=status,
        score=bounded,
        max_score=max_score,
        message=message,
    )


def format_checks(parsed: ParsedResume) -> list[DimensionCheck]:
    has_name = bool(parsed.basic_info.name)
    has_contact = bool(parsed.basic_info.email or parsed.basic_info.phone)
    contact_score = 20 if has_name and has_contact else 10 if has_name or has_contact else 0
    contact_message = "姓名与联系方式完整" if contact_score == 20 else "缺少姓名或邮箱/手机号"

    headline_score = 10 if parsed.basic_info.headline or parsed.summary else 0
    headline_message = "有一句话标题或个人简介" if headline_score else "缺少一句话标题或个人简介"

    education_score = 20 if any(item.school for item in parsed.education) else 0
    education_message = "有教育经历" if education_score else "未识别到教育经历"

    experience_score = 20 if parsed.work_experience or parsed.projects else 0
    experience_message = "有工作或项目经历" if experience_score else "未识别到工作或项目经历"

    skills_score = 15 if any(item.items for item in parsed.skills) else 0
    skills_message = "有技能清单" if skills_score else "未识别到技能清单"

    dates: list[str] = []
    for item in [*parsed.education, *parsed.work_experience, *parsed.projects]:
        for value in (item.start_date, item.end_date):
            if value:
                dates.append(value.strip())
    valid_dates = [value for value in dates if DATE_RE.match(value)]
    if len(valid_dates) >= 2:
        date_score = 15
        date_message = "日期格式基本一致"
    elif len(valid_dates) == 1:
        date_score = 8
        date_message = "日期信息不完整或格式不统一"
    else:
        date_score = 0
        date_message = "缺少可校验的起止日期"

    return [
        _check("contact", "联系方式", contact_score, 20, contact_message),
        _check("headline", "标题 / 简介", headline_score, 10, headline_message),
        _check("education", "教育经历", education_score, 20, education_message),
        _check("experience", "工作 / 项目", experience_score, 20, experience_message),
        _check("skills", "技能清单", skills_score, 15, skills_message),
        _check("dates", "日期一致性", date_score, 15, date_message),
    ]


def completeness_checks(parsed: ParsedResume) -> list[DimensionCheck]:
    basic_score = 0
    basic_score += 5 if parsed.basic_info.name else 0
    basic_score += 5 if parsed.basic_info.email or parsed.basic_info.phone else 0
    basic_score += 5 if parsed.basic_info.location else 0
    basic_score += 5 if parsed.basic_info.headline or parsed.summary else 0
    basic_message = "基本信息较完整" if basic_score == 20 else "基本信息有缺项"

    if parsed.education:
        field_score = sum(
            1 for item in parsed.education if item.degree and (item.start_date or item.end_date)
        )
        education_score = 10 + round(10 * field_score / len(parsed.education))
        education_message = (
            "教育经历字段较完整" if education_score == 20 else "教育经历缺少学历或时间"
        )
    else:
        education_score = 0
        education_message = "没有教育经历"

    if parsed.work_experience:
        work_score = 10 + (10 if any(item.highlights for item in parsed.work_experience) else 0)
        work_message = "工作经历含职责/成果" if work_score == 20 else "工作经历缺少职责/成果"
    elif parsed.projects:
        work_score = 10
        work_message = "没有工作经历，但有项目经历（部分计入）"
    else:
        work_score = 0
        work_message = "没有工作经历"

    if parsed.projects:
        project_score = 8
        project_score += 4 if any(item.highlights for item in parsed.projects) else 0
        project_score += 3 if any(item.tech_stack for item in parsed.projects) else 0
        project_message = "项目经历较完整" if project_score == 15 else "项目经历缺少成果或技术栈"
    else:
        project_score = 0
        project_message = "没有项目经历"

    if parsed.skills:
        skills_score = 8 + (7 if any(item.items for item in parsed.skills) else 0)
        skills_message = "技能分类与条目完整" if skills_score == 15 else "技能缺少具体条目"
    else:
        skills_score = 0
        skills_message = "没有技能清单"

    extra_categories = sum(
        1 for group in (parsed.certificates, parsed.awards, parsed.languages) if group
    )
    extra_score = 10 if extra_categories >= 2 else 5 if extra_categories == 1 else 0
    extra_message = "有证书/奖项/语言补充" if extra_score else "缺少证书、奖项或语言信息"

    return [
        _check("basic", "基本信息", basic_score, 20, basic_message),
        _check("education", "教育完整度", education_score, 20, education_message),
        _check("work", "工作完整度", work_score, 20, work_message),
        _check("projects", "项目完整度", project_score, 15, project_message),
        _check("skills", "技能完整度", skills_score, 15, skills_message),
        _check("extras", "补充信息", extra_score, 10, extra_message),
    ]


def _normalize(value: str) -> str:
    return value.strip().lower()


def _keyword_matches(keyword: str, text: str) -> bool:
    normalized = _normalize(keyword)
    if not normalized:
        return False
    if re.search(r"[a-z0-9]", normalized) and re.fullmatch(r"[a-z0-9+#.\- ]+", normalized):
        pattern = r"(?<![a-z0-9])" + re.escape(normalized) + r"(?![a-z0-9])"
        return re.search(pattern, text) is not None
    return normalized in text


def _keyword_targets(jd: JobDescription) -> list[tuple[str, str, int]]:
    targets: list[tuple[str, str, int]] = []
    seen: set[str] = set()

    def add(values: list[str], source: str, weight: int) -> None:
        for value in values:
            key = _normalize(value)
            if key and key not in seen:
                seen.add(key)
                targets.append((value.strip(), source, weight))

    add(jd.required_skills, "required", 2)
    add(jd.preferred_skills, "preferred", 1)
    add(jd.keywords, "keyword", 1)
    return targets


def keyword_report(jd: JobDescription, resume_text: str) -> KeywordReport:
    text = resume_text.lower()
    targets = _keyword_targets(jd)
    hits: list[KeywordHit] = []
    matched_weight = 0
    total_weight = 0

    for keyword, source, weight in targets:
        matched = _keyword_matches(keyword, text)
        total_weight += weight
        if matched:
            matched_weight += weight
        hits.append(
            KeywordHit(
                keyword=keyword,
                source=source,
                weight=weight,
                matched=matched,
            )
        )

    score = round(100 * matched_weight / total_weight) if total_weight else 0
    return KeywordReport(
        score=score,
        matched_count=sum(1 for hit in hits if hit.matched),
        total_count=len(hits),
        matched_weight=matched_weight,
        total_weight=total_weight,
        hits=hits,
    )


@dataclass(frozen=True)
class RequirementSpec:
    requirement: str
    source: Literal["required", "preferred"]
    weight: int


def build_requirements(jd: JobDescription) -> list[RequirementSpec]:
    specs: list[RequirementSpec] = []
    seen: set[str] = set()

    def add(values: list[str], source: Literal["required", "preferred"], weight: int) -> None:
        for value in values:
            key = _normalize(value)
            if key and key not in seen:
                seen.add(key)
                specs.append(
                    RequirementSpec(
                        requirement=value.strip(),
                        source=source,
                        weight=weight,
                    )
                )

    add(jd.required_skills, "required", 2)
    add(jd.qualifications, "required", 2)
    add(jd.preferred_skills, "preferred", 1)
    if not specs:
        add(jd.keywords, "required", 1)
    return specs[:12]


def build_jd_match_report(
    matches: list[RequirementMatch],
    requirements: list[RequirementSpec],
) -> JdMatchReport:
    by_key = {_normalize(match.requirement): match for match in matches}
    finalized: list[RequirementMatch] = []
    for spec in requirements:
        match = by_key.get(_normalize(spec.requirement))
        if match is None:
            match = RequirementMatch(
                requirement=spec.requirement,
                source=spec.source,
                weight=spec.weight,
                verdict="missing",
                evidence=None,
                reason="模型未返回该要求的匹配结果，按缺失处理",
            )
        else:
            match = match.model_copy(update={"source": spec.source, "weight": spec.weight})
        finalized.append(match)

    total_weight = sum(spec.weight for spec in requirements)
    points = sum(
        match.weight * {"met": 1.0, "partial": 0.5, "missing": 0.0}[match.verdict]
        for match in finalized
    )
    score = round(100 * points / total_weight) if total_weight else 0

    return JdMatchReport(
        score=score,
        matched_count=sum(1 for match in finalized if match.verdict == "met"),
        partial_count=sum(1 for match in finalized if match.verdict == "partial"),
        missing_count=sum(1 for match in finalized if match.verdict == "missing"),
        total=len(finalized),
        matches=finalized,
    )


def weighted_total(
    format_score: int,
    completeness_score: int,
    keyword_score: int,
    jd_match_score: int,
) -> float:
    return round(
        format_score * WEIGHTS["format"]
        + completeness_score * WEIGHTS["completeness"]
        + keyword_score * WEIGHTS["keyword"]
        + jd_match_score * WEIGHTS["jd_match"],
        2,
    )


def build_summary(
    format_score: int,
    completeness_score: int,
    keyword_score: int,
    jd_match_score: int,
    total: float,
) -> str:
    return (
        f"总分 {total:.2f}。格式 {format_score}、完整度 {completeness_score}、"
        f"关键词 {keyword_score}、JD 匹配 {jd_match_score}。"
        "优先补足缺失关键词与岗位要求对应的真实经历证据。"
    )


def rule_suggestions(
    format_items: list[DimensionCheck],
    completeness_items: list[DimensionCheck],
) -> list[Suggestion]:
    suggestions: list[Suggestion] = []
    checks = {item.name: item for item in format_items}
    completeness = {item.name: item for item in completeness_items}

    if checks["contact"].status == "fail":
        suggestions.append(
            Suggestion(
                dimension="format",
                original_text="(简历中未找到姓名或联系方式)",
                issue=checks["contact"].message,
                suggestion="补充姓名，并至少提供邮箱或手机号",
                rewritten_example="",
                reason="联系方式是简历筛选的第一道门槛",
                fact_status="needs_user_input",
                missing_facts=["姓名", "邮箱或手机号"],
            )
        )

    if completeness["education"].status == "fail":
        suggestions.append(
            Suggestion(
                dimension="completeness",
                original_text="(简历中未找到教育经历)",
                issue=completeness["education"].message,
                suggestion="补充学校、专业、学历与起止时间",
                rewritten_example="",
                reason="教育经历是完整度评分的重要部分",
                fact_status="needs_user_input",
                missing_facts=["学校", "专业", "学历", "起止时间"],
            )
        )

    if completeness["work"].status == "fail" and completeness["projects"].status == "fail":
        suggestions.append(
            Suggestion(
                dimension="completeness",
                original_text="(简历中未找到工作或项目经历)",
                issue="缺少工作或项目经历",
                suggestion="补充至少一段工作或项目经历，并写清职责与成果",
                rewritten_example="",
                reason="岗位匹配需要可验证的经历证据",
                fact_status="needs_user_input",
                missing_facts=["公司/项目名称", "职责", "成果"],
            )
        )

    if completeness["skills"].status == "fail":
        suggestions.append(
            Suggestion(
                dimension="completeness",
                original_text="(简历中未找到技能清单)",
                issue=completeness["skills"].message,
                suggestion="按分类补充技能清单，只写真实掌握的技能",
                rewritten_example="",
                reason="技能清单直接影响关键词与岗位匹配评分",
                fact_status="needs_user_input",
                missing_facts=["技能分类", "具体技能"],
            )
        )

    return suggestions[:3]
