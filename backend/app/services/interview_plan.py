"""模拟面试出题：Prompt、结构校验与来源核实。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.providers.base import (
    JsonCompletionProvider,
    ProviderError,
    ProviderNotConfiguredError,
)
from app.schemas.interview import InterviewType
from app.schemas.resume_parse import ParsedResume

logger = logging.getLogger(__name__)

INTERVIEW_PLAN_PROMPT_VERSION = "interview_plan_v1"
MAX_ATTEMPTS = 2
MAX_CONTEXT_CHARS = 80_000
BEHAVIORAL_REF = "通用行为题"

INTERVIEW_TYPE_LABELS: dict[str, str] = {
    "mixed": "综合面试",
    "resume": "简历深挖",
    "jd": "岗位匹配",
    "behavioral": "行为面试",
}

TYPE_MIX_HINTS: dict[str, str] = {
    "mixed": "简历题约 50%，岗位题约 30%，通用行为题约 20%",
    "resume": "以简历项目与工作经历深挖为主，至少 80% 为简历题",
    "jd": "以岗位要求逐条验证为主，至少 80% 为岗位题",
    "behavioral": "以通用行为题为主，至少 80% 为行为题",
}


class InterviewPlanError(Exception):
    """模型输出无法转换为合法面试计划。"""


class PlanQuestionAI(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    source: Literal["resume", "jd", "behavioral"] = "behavioral"
    source_ref: str = Field(default=BEHAVIORAL_REF, max_length=300)
    question: str = Field(min_length=4, max_length=500)
    intent: str = Field(default="", max_length=500)

    @field_validator("source", mode="before")
    @classmethod
    def normalize_source(cls, value: object) -> str:
        text = str(value).strip().lower()
        aliases = {
            "resume": "resume",
            "简历": "resume",
            "jd": "jd",
            "岗位": "jd",
            "job": "jd",
            "behavioral": "behavioral",
            "behavioural": "behavioral",
            "行为": "behavioral",
            "general": "behavioral",
        }
        return aliases.get(text, "behavioral")


class InterviewPlanAI(BaseModel):
    model_config = ConfigDict(extra="ignore")

    questions: list[PlanQuestionAI] = Field(default_factory=list)


SYSTEM_PROMPT = """你是资深技术面试官，负责根据候选人的简历和目标岗位设计结构化面试题。
只依据给定 JSON 中的事实出题，不得虚构候选人没有提供的公司、项目、技能或数据。

要求：
1. 生成指定数量的主问题，不包含追问。
2. 每道题必须标记来源：
   - "resume"：来自简历中的具体经历，source_ref 必须是简历中出现的公司、项目、学校或技能原文；
   - "jd"：来自岗位要求，source_ref 必须与岗位要求、技能或关键词原文一致；
   - "behavioral"：通用行为题，source_ref 固定为"通用行为题"。
3. 题目要验证真实能力，避免是非题和常识题；优先追问项目细节、技术取舍、结果与反思。
4. 按给定的面试类型控制题目比例。
5. 题目使用中文，单题不超过 120 字，必须能独立阅读，不依赖不存在的上下文。
6. intent 用一句话说明考察点。
7. 只输出 json 对象，不要输出 Markdown、解释或额外文字。

输出 json 示例：
{
  "questions": [
    {
      "source": "resume",
      "source_ref": "某某科技公司",
      "question": "你在某某科技公司负责的简历诊断平台，后端为什么选择 FastAPI？",
      "intent": "验证技术选型的理解深度"
    },
    {
      "source": "jd",
      "source_ref": "Docker",
      "question": "岗位要求 Docker，请说明你如何设计镜像分层与部署流程。",
      "intent": "验证容器化实践经验"
    },
    {
      "source": "behavioral",
      "source_ref": "通用行为题",
      "question": "请讲一次你和同事在技术方案上产生分歧的经历，最后如何解决？",
      "intent": "验证沟通与协作能力"
    }
  ]
}"""


def jd_to_text(jd_snapshot: dict[str, Any] | None) -> str:
    if not jd_snapshot:
        return ""
    parts: list[str] = []
    for key in ("title", "company", "raw_text"):
        value = jd_snapshot.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    for key in (
        "required_skills",
        "preferred_skills",
        "keywords",
        "responsibilities",
        "qualifications",
    ):
        values = jd_snapshot.get(key) or []
        if isinstance(values, list):
            parts.extend(str(item).strip() for item in values if str(item).strip())
    return "\n".join(parts)


def build_plan_prompt(
    parsed: ParsedResume,
    jd_snapshot: dict[str, Any] | None,
    interview_type: InterviewType,
    question_count: int,
) -> str:
    resume_json = json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
    if len(resume_json) > MAX_CONTEXT_CHARS:
        raise InterviewPlanError("简历结构化数据过大，暂时无法生成面试题")

    jd_json = json.dumps(jd_snapshot, ensure_ascii=False) if jd_snapshot else "null"
    return (
        "请根据下面的简历与岗位信息设计面试题，并输出 json。\n\n"
        f"面试类型：{interview_type}（{INTERVIEW_TYPE_LABELS[interview_type]}）\n"
        f"题目比例要求：{TYPE_MIX_HINTS[interview_type]}\n"
        f"题目数量：{question_count}\n\n"
        f"简历事实：\n{resume_json}\n\n"
        f"目标岗位：\n{jd_json}"
    )


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def _source_exists(source_ref: str, *haystacks: str) -> bool:
    target = _normalize_text(source_ref)
    if not target:
        return False
    return any(target in _normalize_text(text) for text in haystacks if text)


def normalize_plan(
    questions: list[PlanQuestionAI],
    *,
    parsed: ParsedResume,
    jd_snapshot: dict[str, Any] | None,
    resume_text: str,
    requested: int,
) -> list[dict[str, Any]]:
    """核实来源、去重并裁剪题目数量。来源无法核实的题目降级为行为题。"""
    resume_json = json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
    jd_text = jd_to_text(jd_snapshot)

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in questions:
        key = _normalize_text(item.question)
        if not key or key in seen:
            continue
        seen.add(key)

        source = item.source
        source_ref = item.source_ref.strip() or BEHAVIORAL_REF
        verified = True

        if source == "resume":
            verified = _source_exists(source_ref, resume_text, resume_json)
        elif source == "jd":
            verified = bool(jd_snapshot) and _source_exists(source_ref, jd_text)

        if not verified:
            logger.info("面试题来源未核实，降级为行为题：%s", source_ref)
            source = "behavioral"
            source_ref = BEHAVIORAL_REF

        normalized.append(
            {
                "source": source,
                "source_ref": source_ref[:300],
                "question": item.question.strip(),
                "intent": (item.intent.strip() or "验证相关能力")[:500],
                "source_verified": verified,
            }
        )

        if len(normalized) >= requested:
            break

    if len(normalized) < 3:
        raise InterviewPlanError("有效面试题不足 3 道")

    return normalized


async def generate_plan(
    parsed: ParsedResume,
    jd_snapshot: dict[str, Any] | None,
    interview_type: InterviewType,
    question_count: int,
    provider: JsonCompletionProvider,
    *,
    resume_text: str,
) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            prompt = build_plan_prompt(parsed, jd_snapshot, interview_type, question_count)
            if last_error is not None:
                prompt += (
                    "\n\n注意：上一次输出未通过校验（"
                    f"{str(last_error)[:500]}"
                    "）。请重新输出完整 json，题目数量不少于 3 道，source 只能是 "
                    "resume / jd / behavioral。"
                )
            data = await provider.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.5 if attempt == 0 else 0.2,
            )
            plan = InterviewPlanAI.model_validate(data)
            return normalize_plan(
                plan.questions,
                parsed=parsed,
                jd_snapshot=jd_snapshot,
                resume_text=resume_text,
                requested=question_count,
            )
        except ProviderNotConfiguredError:
            raise
        except (ProviderError, ValidationError, InterviewPlanError) as exc:
            last_error = exc
            logger.warning("面试出题第 %s 次失败：%s", attempt + 1, type(exc).__name__)

    raise InterviewPlanError("模型输出未通过面试出题结构校验") from last_error
