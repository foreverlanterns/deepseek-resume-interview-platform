"""JD 匹配与修改示例的 LLM 输出解析。"""

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
from app.schemas.resume_parse import ParsedResume
from app.services.diagnosis_rules import RequirementSpec

logger = logging.getLogger(__name__)

DIAGNOSIS_PROMPT_VERSION = "diagnosis_prompt_v1"
MAX_ATTEMPTS = 2
MAX_CONTEXT_CHARS = 80_000


class DiagnosisParseError(Exception):
    """LLM 输出无法转换为合法诊断结构。"""


class RequirementMatchAI(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    requirement: str = Field(min_length=1)
    verdict: Literal["met", "partial", "missing"]
    evidence: str | None = None
    reason: str = ""

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, value: object) -> str:
        return str(value).strip().lower()


class SuggestionAI(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    dimension: Literal["jd_match"] = "jd_match"
    original_text: str = Field(min_length=1)
    issue: str = Field(min_length=1)
    suggestion: str = Field(min_length=1)
    rewritten_example: str = ""
    reason: str = ""
    fact_status: Literal["supported", "needs_user_input"] = "needs_user_input"
    missing_facts: list[str] = Field(default_factory=list)

    @field_validator("fact_status", mode="before")
    @classmethod
    def normalize_status(cls, value: object) -> str:
        return str(value).strip().lower()


class JdMatchAI(BaseModel):
    model_config = ConfigDict(extra="ignore")

    requirement_matches: list[RequirementMatchAI] = Field(default_factory=list)
    suggestions: list[SuggestionAI] = Field(default_factory=list)


SYSTEM_PROMPT = """你是严谨的简历-岗位匹配评估器。
只依据给定 JSON 中的简历事实和岗位要求判断，不得编造。

要求：
1. 为 requirements 中的每一条要求返回一条 requirement_matches，
   且 requirement 文本必须与输入完全一致。
2. verdict 只能是 "met"（有直接证据）、"partial"（部分相关）或 "missing"（没有证据）。
3. evidence 必须是简历中的原文摘录；没有证据时为 null，并在 reason 中说明缺什么。
4. 只能使用简历中出现的公司、学校、项目、技能、证书、数字和日期，不得推断或补全。
5. suggestions 提供 3—6 条修改示例，dimension 固定为 "jd_match"。
6. original_text 必须是简历中的逐字原文；rewritten_example 只能改写原文，
   不得添加新事实或新数字。
7. 如果改写需要简历中没有的事实，fact_status 设为 "needs_user_input"，
   并在 missing_facts 中列出需要用户补充的信息。
8. 只输出 json 对象，不要输出 Markdown、解释或额外文字。

输出 json 示例：
{
  "requirement_matches": [
    {
      "requirement": "Python",
      "verdict": "met",
      "evidence": "使用 Python 开发简历诊断平台",
      "reason": "项目经历中有直接使用证据"
    },
    {
      "requirement": "Docker",
      "verdict": "missing",
      "evidence": null,
      "reason": "简历未出现 Docker 相关经历"
    }
  ],
  "suggestions": [
    {
      "dimension": "jd_match",
      "original_text": "使用 Python 开发简历诊断平台",
      "issue": "未说明项目规模和本人贡献",
      "suggestion": "补充可验证的项目规模与个人职责",
      "rewritten_example": "使用 Python 开发简历诊断平台，负责后端接口与数据库设计",
      "reason": "让岗位要求的匹配证据更具体",
      "fact_status": "needs_user_input",
      "missing_facts": ["项目规模", "个人职责"]
    }
  ]
}"""


def build_user_prompt(requirements: list[RequirementSpec], parsed: ParsedResume) -> str:
    requirements_json = json.dumps(
        [
            {
                "requirement": spec.requirement,
                "source": spec.source,
                "weight": spec.weight,
            }
            for spec in requirements
        ],
        ensure_ascii=False,
    )
    resume_json = json.dumps(parsed.model_dump(mode="json"), ensure_ascii=False)
    if len(resume_json) > MAX_CONTEXT_CHARS:
        raise DiagnosisParseError("简历结构化数据过大，暂时无法进行匹配评估")

    return (
        "请对下面的岗位要求逐条评估简历，并输出 json。\n\n"
        f"岗位要求：\n{requirements_json}\n\n"
        f"简历事实：\n{resume_json}"
    )


async def parse_jd_match(
    requirements: list[RequirementSpec],
    parsed: ParsedResume,
    provider: JsonCompletionProvider,
) -> JdMatchAI:
    if not requirements:
        raise DiagnosisParseError("没有可评估的岗位要求")

    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            prompt = build_user_prompt(requirements, parsed)
            if last_error is not None:
                prompt += (
                    "\n\n注意：上一次输出未通过结构校验（"
                    f"{str(last_error)[:500]}"
                    "）。请重新输出完整 json，requirement 与输入逐字一致。"
                )
            data = await provider.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2 if attempt == 0 else 0.0,
            )
            return JdMatchAI.model_validate(data)
        except ProviderNotConfiguredError:
            raise
        except (ProviderError, ValidationError, DiagnosisParseError) as exc:
            last_error = exc
            logger.warning(
                "JD 匹配评估第 %s 次失败：%s",
                attempt + 1,
                type(exc).__name__,
            )

    raise DiagnosisParseError("模型输出未通过诊断结构校验") from last_error


def normalize_suggestion_facts(
    suggestions: list[SuggestionAI],
    resume_text: str,
) -> list[dict[str, Any]]:
    """校验原文摘录与新增数字，必要时降级为需要用户补充。"""
    normalized_resume = " ".join(resume_text.split())
    results: list[dict[str, Any]] = []

    for suggestion in suggestions:
        original = suggestion.original_text.strip()
        verified = bool(original) and (
            original in resume_text or " ".join(original.split()) in normalized_resume
        )
        missing = list(suggestion.missing_facts)
        fact_status = suggestion.fact_status

        if not verified:
            fact_status = "needs_review"
            missing.append("原文摘录未在简历中找到，请人工核对")

        original_numbers = set(re.findall(r"\d+(?:\.\d+)?%?", original))
        rewritten_numbers = set(re.findall(r"\d+(?:\.\d+)?%?", suggestion.rewritten_example))
        new_numbers = rewritten_numbers - original_numbers
        if new_numbers and fact_status == "supported":
            fact_status = "needs_user_input"
            missing.append("改写示例包含原文没有的量化数据，请补充真实数据")

        results.append(
            {
                "dimension": suggestion.dimension,
                "original_text": original,
                "issue": suggestion.issue,
                "suggestion": suggestion.suggestion,
                "rewritten_example": suggestion.rewritten_example,
                "reason": suggestion.reason,
                "fact_status": fact_status,
                "missing_facts": list(dict.fromkeys(missing)),
                "original_text_verified": verified,
            }
        )

    return results
