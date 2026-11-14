"""结构化抽取服务测试（假 Provider，不调用真实 API）。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from app.providers.base import ProviderNotConfiguredError
from app.services.resume_parser import ResumeParseError, parse_resume_text

VALID_DATA: dict[str, Any] = {
    "basic_info": {
        "name": "张三",
        "email": "zhang@example.com",
        "source_text": "张三 zhang@example.com",
    },
    "summary": "后端开发工程师",
    "education": [
        {
            "school": "某某大学",
            "degree": "本科",
            "major": "计算机科学与技术",
            "start_date": "2020.09",
            "end_date": "2024.06",
            "details": ["主修数据库", "  ", "数据结构"],
            "source_text": "2020.09-2024.06 某某大学 计算机科学与技术 本科",
        }
    ],
    "work_experience": [],
    "projects": [
        {
            "name": "简历诊断平台",
            "role": "后端开发",
            "tech_stack": ["Python", "FastAPI"],
            "highlights": ["实现 JWT 认证", "实现 PDF 文本提取"],
            "source_text": "简历诊断平台 后端开发 Python FastAPI",
        }
    ],
    "skills": [
        {"category": "编程语言", "items": ["Python", "Java"], "source_text": "Python、Java"}
    ],
    "certificates": [],
    "awards": [],
    "languages": [{"name": "英语", "level": "CET-6"}],
}


class FakeProvider:
    model_name = "fake-model"

    def __init__(self, responses: list[Any]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    async def complete_json(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


async def test_parse_valid_resume_cleans_lists() -> None:
    provider = FakeProvider([deepcopy(VALID_DATA)])

    parsed = await parse_resume_text("这是一份足够长的简历文本，用于测试结构化抽取。", provider)

    assert parsed.basic_info.name == "张三"
    assert parsed.education[0].school == "某某大学"
    assert parsed.education[0].details == ["主修数据库", "数据结构"]
    assert parsed.projects[0].tech_stack == ["Python", "FastAPI"]
    assert parser_call_count(provider) == 1


async def test_invalid_schema_retries_once_with_repair_hint() -> None:
    invalid = {"education": [{"degree": "本科"}]}
    provider = FakeProvider([invalid, deepcopy(VALID_DATA)])

    parsed = await parse_resume_text("这是一份足够长的简历文本，用于测试结构化抽取。", provider)

    assert parsed.basic_info.name == "张三"
    assert parser_call_count(provider) == 2
    assert "未通过结构校验" in provider.calls[1]["user_prompt"]


async def test_invalid_schema_twice_raises() -> None:
    invalid = {"education": [{"degree": "本科"}]}
    provider = FakeProvider([invalid, invalid])

    with pytest.raises(ResumeParseError):
        await parse_resume_text("这是一份足够长的简历文本，用于测试结构化抽取。", provider)


async def test_not_configured_is_not_retried() -> None:
    provider = FakeProvider([ProviderNotConfiguredError("未配置 Key")])

    with pytest.raises(ProviderNotConfiguredError):
        await parse_resume_text("这是一份足够长的简历文本，用于测试结构化抽取。", provider)

    assert parser_call_count(provider) == 1


async def test_short_text_does_not_call_provider() -> None:
    provider = FakeProvider([deepcopy(VALID_DATA)])

    with pytest.raises(ResumeParseError, match="过短"):
        await parse_resume_text("太短", provider)

    assert parser_call_count(provider) == 0


def parser_call_count(provider: FakeProvider) -> int:
    return len(provider.calls)
