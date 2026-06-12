"""系统提示段管理 — 支持缓存和按需失效。"""

from src.ai.config.logging_setup import get_logger

from src.ai.core.context.types import ContextSection

logger = get_logger(__name__)


class SystemPromptSections:
    """系统提示段管理器。

    对可缓存的段进行会话级缓存，不可缓存的段每次重新计算。
    支持按名称或全部清除缓存（/clear、/compact 时调用）。
    """

    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def resolve(self, sections: list[ContextSection]) -> str:
        """解析所有段，合并为系统提示。

        按 priority 排序（已在协调器中排序），使用缓存中的可缓存段。

        Args:
            sections: 按 priority 排序的上下文段列表。

        Returns:
            合并后的系统提示文本。
        """
        parts: list[str] = []
        for section in sections:
            if section.cacheable and section.name in self._cache:
                content = self._cache[section.name]
            else:
                content = section.content
                if section.cacheable:
                    self._cache[section.name] = content
            if content:
                parts.append(content)
        return "\n\n".join(parts)

    def invalidate(self, name: str) -> None:
        """清除指定段的缓存。

        Args:
            name: 段名称。
        """
        self._cache.pop(name, None)

    def invalidate_all(self) -> None:
        """清除全部缓存（/clear 或 /compact 时调用）。"""
        self._cache.clear()

    @property
    def cached_names(self) -> list[str]:
        """当前已缓存的段名称列表。"""
        return list(self._cache.keys())
