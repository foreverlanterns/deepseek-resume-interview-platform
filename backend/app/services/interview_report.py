"""面试复盘报告生成。"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.providers.base import (
    JsonCompletionProvider,
    ProviderError,
    ProviderNotConfiguredError,
)
from app.schemas.interview import InterviewReport, ReportQuestionNote
from app.schemas.resume_parse import ParsedResume
from app.services.interview_plan import jd_to_text

logger = logging.getLogger(__name__)

INTERVIEW_REPORT_PROMPT_VERSION = "interview_report_v1"
MAX_ATTEMPTS = 2
MAX_CONTEXT_CHARS = 80_000


class InterviewReportError(Exception):
    """模型输出无法转换为合法报告。"""


class ReportNoteAI(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    order_index: int = Field(ge=1)
    comment: str = Field(default="", max_length=1000)


class InterviewReportAI(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overview: str = Field(default="", max_length=3000)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    question_notes: list[ReportNoteAI] = Field(default_factory=list)

    @field_validator("strengths", "weaknesses", "improvements", mode="before")
    @classmethod
    def ensure_list(cls, value: object) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return []


SYSTEM_PROMPT = (
    "你是面试复盘教练。基于完整的问答记录与逐题评分，输出中文复盘报告。\n"
    "只依据输入内容总结，不得编造候选人没有提供的经历或数据，不要修改分数。\n"
    "\n"
    "要求：\n"
    "1. overview 用 3-5 句话总结整体表现，指出最关键的 1-2 个问题。\n"
    "2. strengths/weaknesses 各 2-4 条，必须对应到具体题目或回答内容。\n"
    '3. improvements 给 3-5 条可执行建议，具体到"下次回答时怎么做"，不要空话。\n'
    "4. question_notes 为每道已答题目给一句点评，order_index 必须与输入完全一致。\n"
    "5. 只输出 json 对象，不要输出 Markdown、解释或额外文字。\n"
    "\n"
    "输出 json 示例：\n"
    "{\n"
    '  "overview": "整体技术基础扎实，能说明项目背景，但回答普遍缺少量化结果。",\n'
    '  "strengths": ["项目经历描述完整，能讲清个人职责"],\n'
    '  "weaknesses": ["多数回答没有说明结果指标", "不会的问题容易泛泛而谈"],\n'
    '  "improvements": ["每个项目准备一个可量化的结果指标", "回答前先给结论"],\n'
    '  "question_notes": [\n'
    '    {"order_index": 1, "question": "请介绍后端设计", "comment": "结构清晰"}\n'
    "  ]\n"
    "}"
)


def _clean_list(values: list[str], limit: int = 5) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text[:1000])
        if len(cleaned) >= limit:
            break
    return cleaned


def build_user_prompt(
    *,
    parsed: ParsedResume,
    jd_snapshot: dict[str, Any] | None,
    items: list[dict[str, Any]],
    total_score: float,
    dimension_scores: dict[str, float],
) -> str:
    resume_json = json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
    items_json = json.dumps(items, ensure_ascii=False)
    if len(resume_json) + len(items_json) > MAX_CONTEXT_CHARS:
        raise InterviewReportError("面试记录过大，暂时无法生成报告")

    return (
        "请根据下面的面试记录生成复盘报告，并输出 json。\n\n"
        f"简历背景：\n{resume_json}\n\n"
        f"岗位背景：\n{jd_to_text(jd_snapshot) or '未提供岗位信息'}\n\n"
        f"总分：{total_score}\n"
        f"五维平均分：{json.dumps(dimension_scores, ensure_ascii=False)}\n\n"
        f"问答与逐题评分：\n{items_json}"
    )


async def generate_report(
    *,
    parsed: ParsedResume,
    jd_snapshot: dict[str, Any] | None,
    items: list[dict[str, Any]],
    total_score: float,
    dimension_scores: dict[str, float],
    provider: JsonCompletionProvider,
) -> InterviewReport:
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            prompt = build_user_prompt(
                parsed=parsed,
                jd_snapshot=jd_snapshot,
                items=items,
                total_score=total_score,
                dimension_scores=dimension_scores,
            )
            if last_error is not None:
                prompt += (
                    "\n\n注意：上一次输出未通过校验（"
                    f"{str(last_error)[:500]}"
                    "）。请重新输出完整 json，question_notes 的 order_index 必须与输入一致。"
                )
            data = await provider.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.3 if attempt == 0 else 0.1,
                max_tokens=4096,
            )
            ai_report = InterviewReportAI.model_validate(data)
            return finalize_report(ai_report, items)
        except ProviderNotConfiguredError:
            raise
        except (ProviderError, ValidationError, InterviewReportError) as exc:
            last_error = exc
            logger.warning("面试报告第 %s 次失败：%s", attempt + 1, type(exc).__name__)

    raise InterviewReportError("模型输出未通过面试报告结构校验") from last_error


def finalize_report(
    ai_report: InterviewReportAI,
    items: list[dict[str, Any]],
) -> InterviewReport:
    questions = {int(item["order_index"]): str(item["question"]) for item in items}
    notes: list[ReportQuestionNote] = []
    seen: set[int] = set()

    for note in ai_report.question_notes:
        if note.order_index in questions and note.order_index not in seen:
            seen.add(note.order_index)
            notes.append(
                ReportQuestionNote(
                    order_index=note.order_index,
                    question=questions[note.order_index],
                    comment=note.comment.strip() or "未给出点评",
                )
            )

    for order_index, question in questions.items():
        if order_index not in seen:
            notes.append(
                ReportQuestionNote(
                    order_index=order_index,
                    question=question,
                    comment="模型未单独点评，请结合逐题评价查看",
                )
            )

    notes.sort(key=lambda item: item.order_index)

    return InterviewReport(
        overview=ai_report.overview.strip() or "本次面试已完成，暂无整体总结。",
        strengths=_clean_list(ai_report.strengths, 4),
        weaknesses=_clean_list(ai_report.weaknesses, 4),
        improvements=_clean_list(ai_report.improvements, 5),
        question_notes=notes,
    )
