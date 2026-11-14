"""DeepSeek OpenAI 兼容接口 Provider。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.providers.base import (
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseError,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class DeepSeekProvider:
    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client
        self.model_name = settings.deepseek_model

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 8192,
        thinking: bool = False,
    ) -> dict[str, Any]:
        api_key = self._settings.deepseek_api_key.get_secret_value()
        if not api_key:
            raise ProviderNotConfiguredError("DeepSeek API Key 未配置")

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": min(max_tokens, self._settings.deepseek_max_output_tokens),
            "stream": False,
            "thinking": {"type": "enabled" if thinking else "disabled"},
        }
        if not thinking:
            payload["temperature"] = temperature

        max_retries = self._settings.deepseek_max_retries
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 2):
            try:
                response = await self._post(payload, api_key)
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt > max_retries:
                    break
                logger.warning("DeepSeek 请求异常，准备重试：attempt=%s", attempt)
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
                continue

            if response.status_code in RETRYABLE_STATUS:
                last_error = ProviderRequestError(
                    f"DeepSeek 服务暂时不可用（HTTP {response.status_code}）"
                )
                if attempt > max_retries:
                    break
                logger.warning(
                    "DeepSeek 返回可重试状态：status=%s attempt=%s",
                    response.status_code,
                    attempt,
                )
                await asyncio.sleep(min(2 ** (attempt - 1), 8))
                continue

            if response.status_code >= 400:
                raise ProviderRequestError(f"DeepSeek 请求失败（HTTP {response.status_code}）")

            return self._parse_content(response)

        raise ProviderRequestError("DeepSeek 请求失败，请稍后重试") from last_error

    async def _post(self, payload: dict[str, Any], api_key: str) -> httpx.Response:
        url = f"{self._settings.deepseek_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        timeout = self._settings.deepseek_timeout_seconds
        if self._client is not None:
            return await self._client.post(url, json=payload, headers=headers, timeout=timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.post(url, json=payload, headers=headers)

    @staticmethod
    def _parse_content(response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderResponseError("DeepSeek 返回结构异常") from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderResponseError("DeepSeek 返回空内容，请重试")

        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lstrip().lower().startswith("json"):
                text = text.lstrip()[4:]
            text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderResponseError("DeepSeek 返回的内容不是有效 JSON") from exc

        if not isinstance(data, dict):
            raise ProviderResponseError("DeepSeek 返回的 JSON 顶层必须是对象")
        return data
