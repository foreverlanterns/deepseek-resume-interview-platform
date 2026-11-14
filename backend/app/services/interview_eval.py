"""单题作答评价与追问决策。"""

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
from app.schemas.interview import (
    DIMENSION_LABELS,
    DIMENSION_ORDER,
    AnswerEvaluation,
    EvaluationDimension,
)
from app.schemas.resume_parse import ParsedResume
from app.services.interview_plan import jd_to_text

logger = logging.getLogger(__name__)

INTERVIEW_EVAL_PROMPT_VERSION = "interview_eval_v1"
MAX_ATTEMPTS = 2
MAX_CONTEXT_CHARS = 60_000
MAX_ANSWER_CHARS = 8_000
MAX_HISTORY_ITEMS = 3

EVALUATION_KEYS = set(DIMENSION_ORDER)


class InterviewEvalError(Exception):
    """模型输出无法转换为合法评价。"""


class DimensionScoreAI(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    key: str
    score: int = Field(ge=0, le=100)
    comment: str = Field(default="", max_length=1000)

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: object) -> str:
        return str(value).strip().lower()


class FollowUpAI(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    needed: bool = False
    question: str = Field(default="", max_length=500)
    intent: str = Field(default="", max_length=500)
    reason: str = Field(default="", max_length=500)

    @field_validator("needed", mode="before")
    @classmethod
    def normalize_needed(cls, value: object) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"true", "yes", "1", "是", "需要"}
        return bool(value)


class AnswerEvaluationAI(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dimensions: list[DimensionScoreAI] = Field(default_factory=list)
    summary: str = Field(default="", max_length=2000)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    follow_up: FollowUpAI = Field(default_factory=FollowUpAI)


SYSTEM_PROMPT = (
    "你是严格但公正的模拟面试评估官。针对候选人的回答，按五个维度打分（0-100）并给出依据。\n"
    "评分维度（key 必须使用英文）：\n"
    "- relevance 相关性：是否正面回答题目，是否跑题或答非所问\n"
    "- correctness 专业正确性：技术事实、概念、方法是否正确\n"
    "- structure 结构：是否有清晰的开头、分点和结论，是否使用 STAR 等结构\n"
    "- evidence 证据：是否用具体项目、数据、取舍和结果支撑观点\n"
    "- expression 表达：是否简洁、准确、有条理，是否回避关键问题\n"
    "\n"
    "要求：\n"
    "1. dimensions 必须包含且只包含上述五个 key，每项给 0-100 的整数，"
    "并在 comment 中引用回答原文或指出缺失点。\n"
    "2. 只依据本题回答与给定的简历/岗位背景评分，"
    "不得因为候选人没提到简历之外的事实而扣分。\n"
    "3. 回答明显跑题、空洞或与简历事实矛盾时应给低分，并在 weaknesses 中说明。\n"
    "4. 如果回答存在明显漏洞或值得深挖的具体点，follow_up.needed 设为 true，"
    "并给出一道只追问一个点的追问，不超过 80 字，不得重复原题。\n"
    "5. 追问层级最多两级：输入 follow_up_level 为 1 或 2 时，needed 必须为 false。\n"
    "6. summary 用 1-2 句话概括本题表现；strengths/weaknesses 各 0-3 条。\n"
    "7. 只输出 json 对象，不要输出 Markdown、解释或额外文字。\n"
    "\n"
    "输出 json 示例：\n"
    "{\n"
    '  "dimensions": [\n'
    '    {"key": "relevance", "score": 85, "comment": "正面回答了技术选型问题"},\n'
    '    {"key": "correctness", "score": 80, "comment": "对异步框架的理解基本正确"},\n'
    '    {"key": "structure", "score": 70, "comment": "先讲结论再讲原因，但缺少结果"},\n'
    '    {"key": "evidence", "score": 65, "comment": "提到项目但未说明并发量和收益"},\n'
    '    {"key": "expression", "score": 75, "comment": "表达流畅，偶有口头禅"}\n'
    "  ],\n"
    '  "summary": "技术判断基本正确，但缺少可验证的结果。",\n'
    '  "strengths": ["能说明选型理由"],\n'
    '  "weaknesses": ["缺少量化结果"],\n'
    '  "follow_up": {\n'
    '    "needed": true,\n'
    '    "question": "这个接口的并发量大概多少？你如何验证选型有效？",\n'
    '    "intent": "验证结果与验证方法",\n'
    '    "reason": "回答缺少可验证数据"\n'
    "  }\n"
    "}"
)


def build_user_prompt(
    *,
    parsed: ParsedResume,
    jd_snapshot: dict[str, Any] | None,
    question: str,
    source: str,
    source_ref: str,
    intent: str,
    follow_up_level: int,
    answer: str,
    history: list[dict[str, str]],
) -> str:
    resume_json = json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
    if len(resume_json) > MAX_CONTEXT_CHARS:
        raise InterviewEvalError("简历结构化数据过大，暂时无法评价")

    history_json = json.dumps(history, ensure_ascii=False)
    jd_text = jd_to_text(jd_snapshot) or "未提供岗位信息"

    return (
        "请评价候选人对当前问题的回答，并输出 json。\n\n"
        f"简历背景：\n{resume_json}\n\n"
        f"岗位背景：\n{jd_text}\n\n"
        f"当前问题：\n{question}\n"
        f"题目来源：{source} · {source_ref}\n"
        f"考察点：{intent or '未说明'}\n"
        f"追问层级：{follow_up_level}（0 为主问题，1 和 2 为追问）\n\n"
        f"此前问答（仅用于理解上下文）：\n{history_json}\n\n"
        f"候选人回答：\n{answer[:MAX_ANSWER_CHARS]}"
    )


def _clean_list(values: list[str], limit: int = 5) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text[:500])
        if len(cleaned) >= limit:
            break
    return cleaned


def normalize_evaluation(data: AnswerEvaluationAI, follow_up_level: int) -> AnswerEvaluation:
    by_key = {item.key: item for item in data.dimensions}
    missing = EVALUATION_KEYS - set(by_key)
    if missing:
        raise InterviewEvalError(f"评价缺少维度：{'、'.join(sorted(missing))}")

    dimensions: list[EvaluationDimension] = []
    for key in DIMENSION_ORDER:
        item = by_key[key]
        dimensions.append(
            EvaluationDimension(
                key=key,  # type: ignore[arg-type]
                label=DIMENSION_LABELS[key],
                score=int(item.score),
                comment=item.comment.strip() or "模型未给出依据",
            )
        )

    overall = round(sum(item.score for item in dimensions) / len(dimensions))
    return AnswerEvaluation(
        dimensions=dimensions,
        overall_score=max(0, min(100, overall)),
        summary=data.summary.strip() or "模型未给出总结",
        strengths=_clean_list(data.strengths),
        weaknesses=_clean_list(data.weaknesses),
    )


def should_follow_up(data: AnswerEvaluationAI, follow_up_level: int) -> bool:
    if follow_up_level >= 2:
        return False
    follow_up = data.follow_up
    return bool(follow_up.needed and follow_up.question.strip())


async def evaluate_answer(
    *,
    parsed: ParsedResume,
    jd_snapshot: dict[str, Any] | None,
    question: str,
    source: str,
    source_ref: str,
    intent: str,
    follow_up_level: int,
    answer: str,
    history: list[dict[str, str]],
    provider: JsonCompletionProvider,
) -> tuple[AnswerEvaluation, FollowUpAI | None]:
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            prompt = build_user_prompt(
                parsed=parsed,
                jd_snapshot=jd_snapshot,
                question=question,
                source=source,
                source_ref=source_ref,
                intent=intent,
                follow_up_level=follow_up_level,
                answer=answer,
                history=history,
            )
            if last_error is not None:
                prompt += (
                    "\n\n注意：上一次输出未通过校验（"
                    f"{str(last_error)[:500]}"
                    "）。请重新输出完整 json，dimensions 必须包含 relevance、"
                    "correctness、structure、evidence、expression 五个 key。"
                )
            data = await provider.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2 if attempt == 0 else 0.0,
                max_tokens=4096,
            )
            parsed_ai = AnswerEvaluationAI.model_validate(data)
            evaluation = normalize_evaluation(parsed_ai, follow_up_level)
            follow_up = (
                parsed_ai.follow_up if should_follow_up(parsed_ai, follow_up_level) else None
            )
            return evaluation, follow_up
        except ProviderNotConfiguredError:
            raise
        except (ProviderError, ValidationError, InterviewEvalError) as exc:
            last_error = exc
            logger.warning("面试评价第 %s 次失败：%s", attempt + 1, type(exc).__name__)

    raise InterviewEvalError("模型输出未通过面试评价结构校验") from last_error
