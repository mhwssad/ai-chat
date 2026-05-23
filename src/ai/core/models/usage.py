"""模型 usage/token 统计。"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from .types import ModelUsage


class UsageCalculator:
    """从不同 provider 响应中提取 token usage。"""

    def from_langchain_ai_message(self, message: AIMessage) -> ModelUsage:
        usage = getattr(message, "usage_metadata", None) or {}
        response_metadata = getattr(message, "response_metadata", None) or {}
        token_usage = response_metadata.get("token_usage") or {}
        return ModelUsage(
            input_tokens=self._get(usage, "input_tokens") or token_usage.get("prompt_tokens"),
            output_tokens=self._get(usage, "output_tokens") or token_usage.get("completion_tokens"),
            total_tokens=self._get(usage, "total_tokens") or token_usage.get("total_tokens"),
        )

    def from_openai_dict(self, data: dict[str, Any]) -> ModelUsage:
        usage = data.get("usage") or {}
        return ModelUsage(
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )

    @staticmethod
    def _get(data: Any, key: str) -> Any:
        if isinstance(data, dict):
            return data.get(key)
        return getattr(data, key, None)
