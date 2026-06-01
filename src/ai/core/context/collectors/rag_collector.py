"""RAG 检索收集器 — 收集 RAG 知识库检索结果。"""

import logging
from typing import TYPE_CHECKING

from src.ai.core.context.collector import ContextCollector
from src.ai.core.context.types import (
    ContextBuildRequest,
    ContextCollectorResult,
    ContextSection,
)

if TYPE_CHECKING:
    from src.ai.config.settings import Settings
    from src.ai.core.rag.encoder import RAGQueryEncoder

logger = logging.getLogger(__name__)


class RAGCollector(ContextCollector):
    """收集 RAG 检索结果。

    使用 RAGQueryEncoder 执行优化检索（原词 + LLM 优化词双路检索）。
    不缓存（每次查询结果不同）。

    Args:
        rag_encoder: RAG 查询优化器实例。
    """

    def __init__(
        self, rag_encoder: "RAGQueryEncoder | None", settings: "Settings"
    ) -> None:
        self._rag_encoder = rag_encoder
        self._settings = settings

    @property
    def name(self) -> str:
        return "rag"

    async def collect(self, request: ContextBuildRequest) -> ContextCollectorResult:
        if not request.enable_rag or self._rag_encoder is None:
            return ContextCollectorResult()

        rag_query = request.rag_query or self._extract_last_user_message(
            request.messages
        )
        if not rag_query:
            return ContextCollectorResult()

        try:
            from src.ai.core.rag.types import RAGSearchConfig

            rag_config = RAGSearchConfig(
                enabled=True,
                top_k=request.rag_top_k,
                optimize_query=self._settings.rag.rag_optimize_query,
                merge_strategy=self._settings.rag.rag_merge_strategy,
            )
            rag_result = await self._rag_encoder.encode_and_search(
                rag_query,
                session_id=request.session_id,
                config=rag_config,
            )

            if not rag_result.content:
                return ContextCollectorResult()

            section = ContextSection(
                name="rag",
                content=rag_result.content,
                priority=4,  # 最低优先级，最容易被裁剪
                cacheable=False,
            )
            return ContextCollectorResult(sections=[section])
        except Exception:
            logger.debug("RAG 检索失败", exc_info=True)
            return ContextCollectorResult()

    @staticmethod
    def _extract_last_user_message(messages: list) -> str:
        """从消息列表中提取最后一条用户消息。"""
        for msg in reversed(messages):
            if getattr(msg, "type", "") == "human":
                return msg.content
        return ""
