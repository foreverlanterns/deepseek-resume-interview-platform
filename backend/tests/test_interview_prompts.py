"""面试 Prompt 与结构归一化单元测试。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from app.schemas.resume_parse import ParsedResume
from app.services.interview_eval import (
    AnswerEvaluationAI,
    InterviewEvalError,
    normalize_evaluation,
    should_follow_up,
)
from app.services.interview_plan import (
    InterviewPlanError,
    PlanQuestionAI,
    jd_to_text,
    normalize_plan,
)
from app.services.interview_report import InterviewReportAI, ReportNoteAI, finalize_report

PARSED = ParsedResume.model_validate(
    {
        "basic_info": {"name": "张三"},
        "work_experience": [{"company": "某科技公司", "title": "后端开发"}],
        "projects": [{"name": "简历诊断平台", "tech_stack": ["Python"]}],
    }
)


def test_normalize_plan_downgrades_unverified_source_and_dedupes() -> None:
    questions = [
        PlanQuestionAI(
            source="resume",
            source_ref="某科技公司",
            question="请介绍你在某科技公司的项目。",
            intent="项目深度",
        ),
        PlanQuestionAI(
            source="resume",
            source_ref="不存在的公司",
            question="请介绍你在不存在的公司的项目。",
            intent="项目深度",
        ),
        PlanQuestionAI(
            source="jd",
            source_ref="Docker",
            question="岗位要求 Docker，你如何部署？",
            intent="容器化",
        ),
        PlanQuestionAI(
            source="resume",
            source_ref="某科技公司",
            question="请介绍你在某科技公司的项目。",
            intent="重复题",
        ),
    ]

    result = normalize_plan(
        questions,
        parsed=PARSED,
        jd_snapshot=None,
        resume_text="张三\n某科技公司 后端开发",
        requested=5,
    )

    assert len(result) == 3
    assert result[0]["source"] == "resume"
    assert result[1]["source"] == "behavioral"
    assert result[1]["source_ref"] == "通用行为题"
    assert result[2]["source"] == "behavioral"
    assert result[2]["source_verified"] is False


def test_normalize_plan_requires_three_questions() -> None:
    questions = [
        PlanQuestionAI(source="behavioral", question="请讲一次团队协作经历。", intent="协作"),
    ]

    with pytest.raises(InterviewPlanError):
        normalize_plan(
            questions,
            parsed=PARSED,
            jd_snapshot=None,
            resume_text="",
            requested=5,
        )


def test_jd_to_text_flattens_structured_fields() -> None:
    text = jd_to_text(
        {
            "title": "后端开发",
            "company": "某公司",
            "required_skills": ["Python", "Docker"],
            "keywords": ["PostgreSQL"],
        }
    )

    assert "后端开发" in text
    assert "Python" in text
    assert "PostgreSQL" in text


def _evaluation_payload(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "dimensions": [
            {"key": "relevance", "score": 80, "comment": "相关"},
            {"key": "correctness", "score": 70, "comment": "正确"},
            {"key": "structure", "score": 60, "comment": "结构一般"},
            {"key": "evidence", "score": 50, "comment": "缺少证据"},
            {"key": "expression", "score": 90, "comment": "表达清晰"},
        ],
        "summary": "整体一般",
        "strengths": ["表达清晰"],
        "weaknesses": ["证据不足"],
        "follow_up": {"needed": True, "question": "能给出具体指标吗？", "intent": "验证数据"},
    }
    data.update(overrides)
    return data


def test_normalize_evaluation_computes_overall_and_order() -> None:
    evaluation = normalize_evaluation(AnswerEvaluationAI.model_validate(_evaluation_payload()), 0)

    assert [item.key for item in evaluation.dimensions] == [
        "relevance",
        "correctness",
        "structure",
        "evidence",
        "expression",
    ]
    assert evaluation.overall_score == 70
    assert evaluation.dimensions[0].label == "相关性"


def test_normalize_evaluation_rejects_missing_dimension() -> None:
    data = _evaluation_payload()
    data["dimensions"] = data["dimensions"][:4]

    with pytest.raises(InterviewEvalError):
        normalize_evaluation(AnswerEvaluationAI.model_validate(data), 0)


def test_follow_up_only_below_level_two() -> None:
    payload = AnswerEvaluationAI.model_validate(_evaluation_payload())

    assert should_follow_up(payload, 0) is True
    assert should_follow_up(payload, 1) is True
    assert should_follow_up(payload, 2) is False


def test_finalize_report_fills_missing_notes() -> None:
    data = deepcopy(
        {
            "overview": "整体不错",
            "strengths": ["表达清晰"],
            "weaknesses": ["缺少数据"],
            "improvements": ["准备量化结果"],
            "question_notes": [ReportNoteAI(order_index=1, comment="结构清晰")],
        }
    )
    items = [
        {"order_index": 1, "question": "第一题"},
        {"order_index": 3, "question": "第三题"},
    ]

    report = finalize_report(InterviewReportAI.model_validate(data), items)

    assert [note.order_index for note in report.question_notes] == [1, 3]
    assert report.question_notes[1].comment.startswith("模型未单独点评")
    assert report.question_notes[0].question == "第一题"
