"""统一错误类型体系 — 分类、结构与映射。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(str, Enum):
    """错误分类枚举。"""

    CONFIG = "config"
    MODEL_AUTH = "model_auth"
    MODEL_RATE_LIMIT = "model_rate_limit"
    MODEL_UNAVAILABLE = "model_unavailable"
    MODEL_NETWORK = "model_network"
    TOOL_EXECUTION = "tool_execution"
    TOOL_PERMISSION = "tool_permission"
    TOOL_TIMEOUT = "tool_timeout"
    STORAGE = "storage"
    MEMORY = "memory"
    AUDIT = "audit"
    UNKNOWN = "unknown"


@dataclass
class StructuredError:
    """结构化错误信息。"""

    category: ErrorCategory
    user_message: str
    technical_detail: str
    is_retryable: bool = False
    source_module: str = ""
    source_provider: str = ""

    def __str__(self) -> str:
        return self.user_message


# 异常类型到错误类别的映射规则
_CLASSIFICATION_RULES: list[tuple[type[Exception], ErrorCategory, bool]] = []


def register_classification(
    exc_type: type[Exception],
    category: ErrorCategory,
    is_retryable: bool = False,
) -> None:
    """注册异常类型到错误类别的映射规则。"""
    _CLASSIFICATION_RULES.append((exc_type, category, is_retryable))


def classify_exception(exc: Exception) -> StructuredError:
    """将异常分类为结构化错误。

    按注册顺序匹配，先注册的优先。未匹配时返回 UNKNOWN。
    """
    for exc_type, category, retryable in _CLASSIFICATION_RULES:
        if isinstance(exc, exc_type):
            return StructuredError(
                category=category,
                user_message=_user_message_for(category, exc),
                technical_detail=str(exc),
                is_retryable=retryable,
                source_module=getattr(exc, "__module__", ""),
                source_provider=_extract_provider(exc),
            )
    return StructuredError(
        category=ErrorCategory.UNKNOWN,
        user_message=f"未知错误：{exc}",
        technical_detail=str(exc),
        is_retryable=False,
        source_module=getattr(exc, "__module__", ""),
    )


def _user_message_for(category: ErrorCategory, exc: Exception) -> str:
    """根据错误类别生成用户友好消息。"""
    messages: dict[ErrorCategory, str] = {
        ErrorCategory.CONFIG: "配置错误，请检查设置。",
        ErrorCategory.MODEL_AUTH: "模型认证失败，请检查 API Key 配置。",
        ErrorCategory.MODEL_RATE_LIMIT: "模型请求频率超限，请稍后重试。",
        ErrorCategory.MODEL_UNAVAILABLE: "模型服务不可用，请稍后重试。",
        ErrorCategory.MODEL_NETWORK: "网络连接失败，请检查网络设置。",
        ErrorCategory.TOOL_EXECUTION: f"工具执行失败：{exc}",
        ErrorCategory.TOOL_PERMISSION: f"工具权限不足：{exc}",
        ErrorCategory.TOOL_TIMEOUT: f"工具执行超时：{exc}",
        ErrorCategory.STORAGE: "存储操作失败，请检查数据目录。",
        ErrorCategory.MEMORY: "会话记忆操作失败。",
        ErrorCategory.AUDIT: "审计记录写入失败。",
    }
    return messages.get(category, f"错误：{exc}")


def _extract_provider(exc: Exception) -> str:
    """从异常对象中提取供应商信息。"""
    for attr in ("provider", "provider_name", "llm_type"):
        val = getattr(exc, attr, None)
        if val:
            return str(val)
    return ""
