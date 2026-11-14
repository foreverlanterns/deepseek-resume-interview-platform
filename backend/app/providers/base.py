"""LLM Provider 协议与统一异常。"""

from __future__ import annotations

from typing import Any, Protocol


class ProviderError(Exception):
    """Provider 调用失败。"""


class ProviderNotConfiguredError(ProviderError):
    """缺少 API Key 等必要配置。"""


class ProviderRequestError(ProviderError):
    """网络、限流或 HTTP 错误。"""


class ProviderResponseError(ProviderError):
    """返回内容不是可解析的 JSON。"""


class JsonCompletionProvider(Protocol):
    """结构化 JSON 生成能力；便于测试时替换为假 Provider。"""

    model_name: str

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 8192,
        thinking: bool = False,
    ) -> dict[str, Any]: ...
