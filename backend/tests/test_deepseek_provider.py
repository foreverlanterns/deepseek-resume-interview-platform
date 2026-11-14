"""DeepSeek Provider 请求格式、重试与解析测试（不调用真实 API）。"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import Settings
from app.providers.base import (
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseError,
)
from app.providers.deepseek import DeepSeekProvider


def build_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "environment": "test",
        "secret_key": "test-secret-key-for-unit-tests-only",
        "deepseek_api_key": "test-api-key",
        "deepseek_base_url": "https://api.deepseek.com",
        "deepseek_model": "deepseek-flash",
        "deepseek_max_retries": 0,
        "deepseek_max_output_tokens": 8192,
    }
    values.update(overrides)
    return Settings(**values)


def success_response(content: str = '{"ok": true}') -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}]},
    )


async def test_missing_key_raises_without_request() -> None:
    provider = DeepSeekProvider(build_settings(deepseek_api_key=""))

    with pytest.raises(ProviderNotConfiguredError):
        await provider.complete_json(system_prompt="json", user_prompt="resume")


async def test_request_payload_uses_json_mode_and_disabled_thinking() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return success_response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(build_settings(), client=client)
        result = await provider.complete_json(
            system_prompt="只输出 json",
            user_prompt="简历文本",
            temperature=0.1,
        )

    assert result == {"ok": True}
    body = json.loads(captured[0].content)
    assert body["model"] == "deepseek-flash"
    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert body["temperature"] == 0.1
    assert body["stream"] is False
    assert captured[0].headers["Authorization"] == "Bearer test-api-key"


async def test_thinking_mode_omits_temperature() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return success_response()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(build_settings(), client=client)
        await provider.complete_json(
            system_prompt="json",
            user_prompt="resume",
            temperature=0.7,
            thinking=True,
        )

    body = json.loads(captured[0].content)
    assert body["thinking"] == {"type": "enabled"}
    assert "temperature" not in body


async def test_retries_on_server_error(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, json={"error": "temporary"})
        return success_response()

    monkeypatch.setattr("app.providers.deepseek.asyncio.sleep", AsyncMock())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(build_settings(deepseek_max_retries=1), client=client)
        result = await provider.complete_json(system_prompt="json", user_prompt="resume")

    assert result == {"ok": True}
    assert calls == 2


async def test_invalid_json_raises_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return success_response("这不是 JSON")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(build_settings(), client=client)
        with pytest.raises(ProviderResponseError):
            await provider.complete_json(system_prompt="json", user_prompt="resume")


async def test_blank_content_raises_response_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return success_response("   ")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(build_settings(), client=client)
        with pytest.raises(ProviderResponseError, match="空内容"):
            await provider.complete_json(system_prompt="json", user_prompt="resume")


async def test_client_error_is_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad request"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = DeepSeekProvider(build_settings(deepseek_max_retries=2), client=client)
        with pytest.raises(ProviderRequestError):
            await provider.complete_json(system_prompt="json", user_prompt="resume")

    assert calls == 1
