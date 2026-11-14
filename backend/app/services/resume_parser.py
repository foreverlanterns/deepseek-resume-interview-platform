"""简历文本 → 结构化数据。"""

from __future__ import annotations

import logging

from pydantic import ValidationError

from app.providers.base import (
    JsonCompletionProvider,
    ProviderError,
    ProviderNotConfiguredError,
)
from app.schemas.resume_parse import ParsedResume

logger = logging.getLogger(__name__)

PARSER_VERSION = "resume_parser_v1"
PROMPT_VERSION = "resume_parse_prompt_v1"
MAX_INPUT_CHARS = 60_000
MAX_ATTEMPTS = 2


class ResumeParseError(Exception):
    """模型输出无法转换为合法结构。"""


SYSTEM_PROMPT = """你是严谨的简历信息抽取器。只提取简历原文中明确出现的事实，不得推断、补全或改写。

规则：
1. 缺失信息使用 null；列表缺失使用 []。不要编造姓名、公司、学校、日期、技能或数字。
2. 每条教育、工作、项目、证书、奖项都必须提供 source_text，逐字摘录对应原文，不要改写。
3. 日期保留原文写法，例如 "2023.09"、"2024-06"、"至今"；无法确定时用 null。
4. highlights 只放原文中的职责、行动或成果；不要把一句话拆成多条重复内容。
5. skills 按原文中的类别分组；原文没有分类时，category 用 "技能"。
6. 只输出 json 对象，不要输出 Markdown、解释或额外文字。

输出 json 结构示例：
{
  "basic_info": {
    "name": "张三",
    "phone": "13800000000",
    "email": "zhang@example.com",
    "location": "杭州",
    "headline": "后端开发工程师",
    "source_text": "张三 后端开发工程师 13800000000"
  },
  "summary": null,
  "education": [
    {
      "school": "某某大学",
      "degree": "本科",
      "major": "计算机科学与技术",
      "start_date": "2020.09",
      "end_date": "2024.06",
      "details": ["主修课程：数据结构、数据库"],
      "source_text": "2020.09-2024.06 某某大学 计算机科学与技术 本科"
    }
  ],
  "work_experience": [],
  "projects": [],
  "skills": [{"category": "编程语言", "items": ["Python", "Java"], "source_text": "Python、Java"}],
  "certificates": [],
  "awards": [],
  "languages": [{"name": "英语", "level": "CET-6"}]
}"""


def build_user_prompt(text: str, error_hint: str | None = None) -> str:
    clipped = text.strip()
    if len(clipped) > MAX_INPUT_CHARS:
        clipped = clipped[:MAX_INPUT_CHARS] + "\n...[简历文本过长，已截断]"

    prompt = f"请抽取以下简历文本，并严格按 json 结构输出：\n\n{clipped}"
    if error_hint:
        prompt += (
            "\n\n注意：上一次输出未通过结构校验（"
            f"{error_hint[:500]}"
            "）。请重新输出完整 json，严格遵守字段名与类型，不要输出解释。"
        )
    return prompt


async def parse_resume_text(text: str, provider: JsonCompletionProvider) -> ParsedResume:
    if len(text.strip()) < 20:
        raise ResumeParseError("简历文本过短，无法进行结构化抽取")

    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            data = await provider.complete_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(
                    text,
                    error_hint=str(last_error) if last_error else None,
                ),
                temperature=0.1 if attempt == 0 else 0.0,
            )
            return ParsedResume.model_validate(data)
        except ProviderNotConfiguredError:
            raise
        except (ProviderError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                "简历结构化抽取第 %s 次失败：%s",
                attempt + 1,
                type(exc).__name__,
            )

    raise ResumeParseError("模型输出未通过结构校验，请稍后重试") from last_error
