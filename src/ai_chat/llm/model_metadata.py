"""模型上下文窗口元数据 — 内置默认值 + 可配置覆盖。"""

import json
from typing import Optional

from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)

# 内置默认值: model_name -> context_window_tokens
MODEL_CONTEXT_SIZES: dict[str, int] = {
    # OpenAI
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    "o1": 200_000,
    "o1-mini": 128_000,
    # Claude
    "claude-sonnet-4-20250514": 200_000,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-opus-20240229": 200_000,
    "claude-3-haiku-20240307": 200_000,
    # Gemini
    "gemini-2.0-flash": 1_048_576,
    "gemini-1.5-pro": 2_097_152,
    "gemini-1.5-flash": 1_048_576,
    # Ollama（因具体模型而异，此处为常见默认值）
    "qwen2.5": 131_072,
    "qwen2.5:7b": 131_072,
    "qwen2.5:14b": 131_072,
    "llama3.1": 128_000,
    "llama3.1:8b": 128_000,
    "llama3.1:70b": 128_000,
    "mistral": 32_000,
    "gemma2": 8_192,
    "gemma2:9b": 8_192,
    "deepseek-r1": 128_000,
    "deepseek-r1:8b": 128_000,
    "phi4": 16_384,
    # MinMax
    "MiniMax-M2.7": 1_048_576,
    "minimax-m2.7": 1_048_576,
    # Qwen
    "qwen-turbo": 1_048_576,
}

DEFAULT_CONTEXT_SIZE: int = 8_192

# 覆盖缓存: (raw_json_string, parsed_dict)
_overrides_cache: tuple[str, dict[str, int]] = ("", {})


def _parse_overrides(raw: str) -> dict[str, int]:
    """解析并缓存 JSON 格式的模型上下文覆盖配置。"""
    global _overrides_cache
    if raw == _overrides_cache[0]:
        return _overrides_cache[1]
    try:
        parsed = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        logger.warning("MODEL_CONTEXT_OVERRIDES JSON 格式无效: %s", raw)
        parsed = {}
    _overrides_cache = (raw, parsed)
    return parsed


def get_model_context_size(model_name: str) -> int:
    """返回模型上下文窗口大小（token 数）。

    查找顺序:
    1. settings 中 MODEL_CONTEXT_OVERRIDES 的用户覆盖
    2. MODEL_CONTEXT_SIZES 内置默认值
    3. settings 中 model_default_context_size 全局默认

    Args:
        model_name: 模型名称

    Returns:
        上下文窗口 token 数
    """
    from src.ai_chat.config import settings

    # 1. 用户覆盖
    overrides = _parse_overrides(settings.model_context_overrides)
    if model_name in overrides:
        logger.debug("模型 '%s' 使用用户覆盖上下文大小: %d", model_name, overrides[model_name])
        return overrides[model_name]

    # 2. 内置默认值
    if model_name in MODEL_CONTEXT_SIZES:
        return MODEL_CONTEXT_SIZES[model_name]

    # 3. 全局默认
    default = getattr(settings, "model_default_context_size", DEFAULT_CONTEXT_SIZE)
    logger.info("模型 '%s' 未在内置表中找到，使用默认上下文大小: %d", model_name, default)
    return default
