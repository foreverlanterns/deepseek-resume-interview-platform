"""四维诊断规则评分单元测试。"""

from __future__ import annotations

import uuid

from app.models.job_description import JobDescription
from app.schemas.diagnosis import RequirementMatch
from app.schemas.resume_parse import ParsedResume
from app.services.diagnosis_rules import (
    build_jd_match_report,
    build_requirements,
    completeness_checks,
    format_checks,
    keyword_report,
    rule_suggestions,
    weighted_total,
)

FULL_RESUME = ParsedResume.model_validate(
    {
        "basic_info": {
            "name": "张三",
            "phone": "13800000000",
            "email": "zhang@example.com",
            "location": "杭州",
            "headline": "后端开发工程师",
        },
        "summary": "3 年后端开发经验",
        "education": [
            {
                "school": "某某大学",
                "degree": "本科",
                "major": "计算机科学与技术",
                "start_date": "2020.09",
                "end_date": "2024.06",
                "details": ["主修数据库"],
            }
        ],
        "work_experience": [
            {
                "company": "某科技公司",
                "title": "后端开发",
                "start_date": "2024.07",
                "end_date": "至今",
                "location": "杭州",
                "highlights": ["使用 Python 开发简历诊断平台"],
            }
        ],
        "projects": [
            {
                "name": "简历诊断平台",
                "role": "后端开发",
                "start_date": "2025.03",
                "end_date": "2025.06",
                "description": "基于 FastAPI 的平台",
                "highlights": ["实现 JWT 认证"],
                "tech_stack": ["Python", "FastAPI"],
            }
        ],
        "skills": [{"category": "编程语言", "items": ["Python", "FastAPI"]}],
        "certificates": [{"name": "CET-6", "issuer": "教育部", "date": "2023.06"}],
        "awards": [],
        "languages": [{"name": "英语", "level": "CET-6"}],
    }
)


def make_jd() -> JobDescription:
    return JobDescription(
        user_id=uuid.uuid4(),
        title="后端开发工程师",
        required_skills=["Python", "Docker"],
        preferred_skills=["FastAPI"],
        keywords=["PostgreSQL"],
        responsibilities=["开发后端服务"],
        qualifications=[],
    )


def test_full_resume_scores_format_and_completeness_100() -> None:
    format_score = sum(item.score for item in format_checks(FULL_RESUME))
    completeness_score = sum(item.score for item in completeness_checks(FULL_RESUME))

    assert format_score == 100
    assert completeness_score == 100


def test_empty_resume_scores_zero_and_emits_rule_suggestions() -> None:
    empty = ParsedResume.model_validate({})
    format_items = format_checks(empty)
    completeness_items = completeness_checks(empty)

    assert sum(item.score for item in format_items) == 0
    assert sum(item.score for item in completeness_items) == 0
    assert len(rule_suggestions(format_items, completeness_items)) > 0


def test_keyword_report_uses_weighted_required_and_preferred() -> None:
    jd = make_jd()

    report = keyword_report(
        jd,
        "熟悉 Python、FastAPI 和 PostgreSQL，参与简历诊断平台开发。",
    )

    assert report.total_count == 4
    assert report.matched_count == 3
    assert report.total_weight == 6
    assert report.matched_weight == 4
    assert report.score == 67
    assert {hit.keyword for hit in report.hits if not hit.matched} == {"Docker"}


def test_jd_match_report_computes_weighted_verdicts() -> None:
    requirements = build_requirements(make_jd())
    matches = [
        RequirementMatch(
            requirement="Python",
            source="required",
            weight=2,
            verdict="met",
            evidence="使用 Python 开发平台",
            reason="有直接证据",
        ),
        RequirementMatch(
            requirement="Docker",
            source="required",
            weight=2,
            verdict="missing",
            evidence=None,
            reason="未出现",
        ),
        RequirementMatch(
            requirement="FastAPI",
            source="preferred",
            weight=1,
            verdict="partial",
            evidence="FastAPI 平台",
            reason="有部分证据",
        ),
    ]

    report = build_jd_match_report(matches, requirements)

    assert report.total == len(requirements)
    assert report.score == 50
    assert report.matched_count == 1
    assert report.partial_count == 1
    assert report.missing_count == 1


def test_weighted_total_uses_fixed_weights() -> None:
    assert weighted_total(80, 60, 50, 70) == 64.5
    assert weighted_total(100, 100, 100, 100) == 100.0
