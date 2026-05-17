"""链式组合 — 顺序执行和条件路由。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Optional

from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


class SequentialChain:
    """顺序执行多个 Chain，前一个的输出作为后一个的输入。"""

    def __init__(
        self,
        chains: list,
        input_transforms: Optional[list] = None,
    ) -> None:
        """
        Args:
            chains: 按顺序执行的 Chain 实例列表。
            input_transforms: 可选的输入转换函数列表，用于将上一步输出映射为下一步输入。
        """
        if not chains:
            raise ValueError("chains 不能为空")
        self._chains = chains
        self._transforms = input_transforms or []

    def invoke(self, initial_input: str, **kwargs) -> str:
        """顺序执行所有 Chain。"""
        result = initial_input
        for i, chain in enumerate(self._chains):
            transform = self._transforms[i] if i < len(self._transforms) else None
            if transform:
                chain_input = transform(result)
            else:
                chain_input = result
            result = chain.invoke(chain_input, **kwargs)
            logger.debug("SequentialChain 步骤 %d/%d 完成", i + 1, len(self._chains))
        return result

    def stream(self, initial_input: str, **kwargs) -> Iterator[str]:
        """流式执行 — 只有最后一个 Chain 使用流式输出。"""
        result = initial_input
        for i, chain in enumerate(self._chains[:-1]):
            transform = self._transforms[i] if i < len(self._transforms) else None
            if transform:
                chain_input = transform(result)
            else:
                chain_input = result
            result = chain.invoke(chain_input, **kwargs)

        last = self._chains[-1]
        transform = self._transforms[-1] if self._transforms and len(self._transforms) >= len(self._chains) else None
        final_input = transform(result) if transform else result
        yield from last.stream(final_input, **kwargs)


class RouterChain:
    """条件路由 — 根据分类结果选择不同的 Chain。"""

    def __init__(
        self,
        classifier_chain: Any,
        route_map: dict[str, Any],
        default_chain: Optional[Any] = None,
    ) -> None:
        """
        Args:
            classifier_chain: 分类 Chain，返回路由键名。
            route_map: 路由键 → Chain 实例的映射。
            default_chain: 未匹配任何路由时的默认 Chain。
        """
        self._classifier = classifier_chain
        self._route_map = route_map
        self._default = default_chain

    def invoke(self, text: str, **kwargs) -> str:
        """分类后路由到对应 Chain 执行。"""
        route_key = self._classifier.invoke(text, **kwargs).strip()
        logger.debug("RouterChain 分类结果: '%s'", route_key)

        chain = self._route_map.get(route_key, self._default)
        if chain is None:
            available = list(self._route_map)
            raise ValueError(f"无匹配路由: '{route_key}'，可用路由: {available}")
        return chain.invoke(text, **kwargs)

    def stream(self, text: str, **kwargs) -> Iterator[str]:
        """分类后路由到对应 Chain 流式执行。"""
        route_key = self._classifier.invoke(text, **kwargs).strip()
        chain = self._route_map.get(route_key, self._default)
        if chain is None:
            raise ValueError(f"无匹配路由: '{route_key}'")
        yield from chain.stream(text, **kwargs)
