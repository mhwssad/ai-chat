"""批量处理链 — 并发执行多个输入。"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Optional

from src.ai_chat.config.logging_setup import get_logger

logger = get_logger(__name__)


@dataclass
class BatchResult:
    """单条批量处理结果。"""

    index: int
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None


class BatchChain:
    """批量处理链 — 接受一个 Chain 实例和输入列表，并发执行。

    支持同步和异步，可配置最大并发数。
    """

    def __init__(
        self,
        chain: Any,
        max_concurrency: int = 5,
    ) -> None:
        """
        Args:
            chain: 任何具有 invoke 方法的 Chain 实例。
            max_concurrency: 最大并发数。
        """
        if max_concurrency <= 0:
            raise ValueError("max_concurrency 必须大于 0")
        self._chain = chain
        self._max_concurrency = max_concurrency

    def invoke(self, inputs: list[dict]) -> list[BatchResult]:
        """同步批量执行。

        Args:
            inputs: 每个元素是传给 chain.invoke 的 kwargs 字典。
        """
        results: list[BatchResult] = [None] * len(inputs)  # type: ignore[list-item]

        def _process(index: int, kwargs: dict) -> BatchResult:
            try:
                output = self._chain.invoke(**kwargs)
                return BatchResult(index=index, success=True, output=output)
            except Exception as e:
                logger.warning("BatchChain 第 %d 条处理失败: %s", index, e)
                return BatchResult(index=index, success=False, error=str(e))

        with ThreadPoolExecutor(max_workers=self._max_concurrency) as executor:
            futures = [
                executor.submit(_process, i, kwargs)
                for i, kwargs in enumerate(inputs)
            ]
            for future in futures:
                result = future.result()
                results[result.index] = result

        logger.info("BatchChain 完成: %d/%d 成功",
                     sum(1 for r in results if r.success), len(results))
        return results

    async def ainvoke(self, inputs: list[dict]) -> list[BatchResult]:
        """异步批量执行。"""
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def _process(index: int, kwargs: dict) -> BatchResult:
            async with semaphore:
                try:
                    output = await self._chain.ainvoke(**kwargs)
                    return BatchResult(index=index, success=True, output=output)
                except Exception as e:
                    return BatchResult(index=index, success=False, error=str(e))

        tasks = [_process(i, kwargs) for i, kwargs in enumerate(inputs)]
        results = await asyncio.gather(*tasks)
        return list(results)
