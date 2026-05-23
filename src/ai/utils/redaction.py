"""审计数据脱敏 — 截断与敏感信息遮蔽。"""

from __future__ import annotations

import re

from src.ai.utils.strings import StringUtils

# API Key 常见前缀模式
_API_KEY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(sk-)[a-zA-Z0-9]{8,}", re.IGNORECASE),
    re.compile(r"(key-)[a-zA-Z0-9]{8,}", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[a-zA-Z0-9\-_.]{8,}", re.IGNORECASE),
    re.compile(r'(api[_-]?key\s*[=:]\s*)["\']?[a-zA-Z0-9]{8,}', re.IGNORECASE),
]

_REDACTED = r"\1***REDACTED***"


def redact_for_audit(text: str, max_length: int = 200) -> str:
    """截断并脱敏文本，用于审计日志。

    - 超过 max_length 的文本截断并追加省略号
    - 替换 API Key 格式的敏感信息
    """
    if not text:
        return ""

    result = text
    for pattern in _API_KEY_PATTERNS:
        result = pattern.sub(_REDACTED, result)

    return StringUtils.truncate(result, length=max_length)
