"""RAG 查询优化器 — 用 LLM 优化检索提示词，双路检索合并结果。"""

from __future__ import annotations

from src.ai.config.logging_setup import get_logger
from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel

from src.ai.utils.llm_utils import build_llm_chain
from src.ai.core.rag.types import RAGSearchConfig, RAGSearchResult

if TYPE_CHECKING:
    from src.ai.core.rag.service import RagService

logger = get_logger(__name__)

_OPTIMIZE_SYSTEM = """你是一个专业的搜索查询优化专家。你的任务是将用户的自然语言查询转换为高效的向量检索查询。

## 优化策略

1. **语义提取**：识别查询的核心意图和关键实体
2. **术语规范化**：
   - 口语 → 专业术语（例："那个东西" → 具体名词）
   - 模糊词 → 精确词（例："大概" → 删除）
   - 同义词 → 标准术语（例："设置" → "配置"）
3. **结构优化**：
   - 保留：主语 + 关键动作 + 对象
   - 删除：语气词、修饰语、重复表述
4. **长度控制**：15-40 字，过短丢失语义，过长引入噪声

## 输出规则

- 只输出优化后的查询文本
- 不要解释、不要引号、不要前缀
- 保持原始查询的语言（中文查询输出中文）

## 示例

用户：我想问一下之前那个关于数据库连接超时的问题是怎么解决的
输出：数据库连接超时解决方案

用户：帮我看看代码里有没有内存泄漏的情况
输出：代码内存泄漏检测

用户：那个 API 返回的数据格式好像不太对
输出：API 响应数据格式问题"""


class RAGQueryEncoder:
    """RAG 查询优化器。

    流程：
    1. 接收用户原始查询
    2. 用 LLM 生成优化后的检索查询
    3. 分别用原词和优化词检索 RAG 知识库
    4. 合并去重结果
    """

    def __init__(self, llm: BaseChatModel, rag_service: RagService) -> None:
        self._llm = llm
        self._optimize_chain = build_llm_chain(self._llm, _OPTIMIZE_SYSTEM, "{query}")
        self._rag_service = rag_service

    async def encode_and_search(
        self,
        query: str,
        *,
        session_id: str | None = None,
        config: RAGSearchConfig | None = None,
    ) -> RAGSearchResult:
        """优化查询并执行双路检索。"""
        if config is None:
            config = RAGSearchConfig()

        if not config.enabled or not query.strip():
            return RAGSearchResult(content="", original_query=query)

        rag = self._rag_service

        # 优先使用混合检索（向量 + BM25）
        search_fn = getattr(rag, "hybrid_search", rag.search)  # type: ignore[attr-defined]
        original_results = search_fn(query, session_id=session_id, top_k=config.top_k)  # type: ignore[misc]

        optimized_query = ""
        optimized_results = []
        if config.optimize_query:
            try:
                optimized_query = await self._optimize_chain.ainvoke({"query": query})
                if optimized_query and optimized_query.strip() != query.strip():
                    optimized_results = search_fn(  # type: ignore[misc]
                        optimized_query, session_id=session_id, top_k=config.top_k
                    )
            except Exception:
                logger.warning("查询优化失败，仅使用原词检索", exc_info=True)

        merged = self._merge_results(
            original_results, optimized_results, strategy=config.merge_strategy
        )

        content = self._format_context(merged)

        return RAGSearchResult(
            content=content,
            raw_results=merged,
            original_query=query,
            optimized_query=optimized_query,
        )

    @staticmethod
    def _merge_results(
        original: list,
        optimized: list,
        *,
        strategy: str = "deduplicate",
    ) -> list:
        """合并两路检索结果。"""
        if strategy == "deduplicate":
            seen_ids: set[str] = set()
            merged: list = []
            for r in original:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    merged.append(r)
            for r in optimized:
                if r.id not in seen_ids:
                    seen_ids.add(r.id)
                    merged.append(r)
            return merged

        if strategy == "interleave":
            result: list = []
            max_len = max(len(original), len(optimized))
            for i in range(max_len):
                if i < len(original):
                    result.append(original[i])
                if i < len(optimized):
                    result.append(optimized[i])
            return result

        return list(original) + list(optimized)

    @staticmethod
    def _format_context(results: list) -> str:
        """将检索结果格式化为上下文文本。"""
        if not results:
            return ""

        lines = ["## RAG 知识库检索结果", ""]
        for i, r in enumerate(results, 1):
            title = r.title or r.source_path
            lines.append(f"[{i}] {title}")
            lines.append(r.content[:500])
            lines.append("")
        return "\n".join(lines)
