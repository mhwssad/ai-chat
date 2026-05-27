"""上下文构建器 — 使用记忆策略构建 LLM 上下文。

替代原来的 context/builder.py + context/sources.py，
通过策略模式驱动上下文构建。
"""

import logging
from typing import TYPE_CHECKING

from src.ai.core.memory.strategies.base import BaseMemoryStrategy
from src.ai.core.memory.types import (
    ContextBuildRequest,
    ContextBuildResult,
)

if TYPE_CHECKING:
    from src.ai.core.memory.rag_encoder import RAGQueryEncoder

logger = logging.getLogger(__name__)


class ContextBuilder:
    """上下文构建器。

    使用配置的记忆策略构建上下文。
    合并原 context/builder.py 和 context/sources.py 的功能。
    """

    def __init__(
        self,
        strategy: BaseMemoryStrategy,
        rag_encoder: "RAGQueryEncoder | None" = None,
    ) -> None:
        self._strategy = strategy
        self._rag_encoder = rag_encoder

    @property
    def strategy(self) -> BaseMemoryStrategy:
        """当前使用的策略。"""
        return self._strategy

    @strategy.setter
    def strategy(self, strategy: BaseMemoryStrategy) -> None:
        self._strategy = strategy

    def build(self, request: ContextBuildRequest) -> ContextBuildResult:
        """构建最终的上下文消息列表（同步）。"""
        system_parts = self._collect_system_parts(request)
        merged_system = "\n\n".join(system_parts)
        max_tokens = self._calculate_token_budget(request)

        context_messages = self._strategy.build_context_messages(
            session_id=request.session_id,
            system_prompt=merged_system,
            max_tokens=max_tokens,
        )

        return self._finalize_result(request, context_messages, merged_system, max_tokens)

    async def abuild(self, request: ContextBuildRequest) -> ContextBuildResult:
        """构建上下文消息列表（异步，支持 RAG 优化检索和异步策略）。"""
        # 异步 RAG 检索（唯一与 build 不同的部分）
        rag_content = ""
        if request.enable_rag and self._rag_encoder:
            rag_content = await self._async_rag_search(request)

        system_parts = self._collect_system_parts(request, rag_override=rag_content)
        merged_system = "\n\n".join(system_parts)
        max_tokens = self._calculate_token_budget(request)

        context_messages = await self._strategy.abuild_context_messages(
            session_id=request.session_id,
            system_prompt=merged_system,
            max_tokens=max_tokens,
        )

        return self._finalize_result(request, context_messages, merged_system, max_tokens)

    # ── 公共方法（消除 build/abuild 重复） ──────────────────

    def _collect_system_parts(
        self,
        request: ContextBuildRequest,
        *,
        rag_override: str = "",
    ) -> list[str]:
        """收集各来源内容（按变动频率从低到高排序）。

        Args:
            request: 构建请求。
            rag_override: 异步 RAG 搜索结果，非空时替代 request.rag_content。
        """
        system_parts: list[str] = []

        # 系统提示词（最稳定，配置级）
        system_prompt = self._collect_system_prompt(request.custom_system_prompt)
        if system_prompt:
            system_parts.append(system_prompt)

        # 工具描述（相对稳定，工具配置变化不频繁）
        if request.enable_tools:
            tool_content = self._collect_tool_descriptions()
            if tool_content:
                system_parts.append(tool_content)

        # 记忆上下文（中等频率，用户记忆会更新）
        if request.enable_memory:
            memory_content = self._collect_memory_context(
                self._extract_last_user_message(request.messages),
                search_limit=request.memory_search_limit,
            )
            if memory_content:
                system_parts.append(memory_content)

        # RAG 检索结果（最不稳定，每次查询可能不同）
        rag_content = rag_override or request.rag_content
        if rag_content:
            system_parts.append(rag_content)

        return system_parts

    def _calculate_token_budget(self, request: ContextBuildRequest) -> int | None:
        """计算 token 预算（回退到 settings.llm 配置）。"""
        from src.ai.config.settings import settings as app_settings

        config = request.model_config
        context_window = getattr(config, "context_window", None) if config else None
        max_output = getattr(config, "max_output_tokens", None) if config else None
        context_window = context_window or app_settings.llm.max_input_tokens
        max_output = max_output or app_settings.llm.max_output_tokens
        if context_window:
            return max(context_window - max_output - request.safety_margin, 0)
        return None

    def _finalize_result(
        self,
        request: ContextBuildRequest,
        context_messages: list,
        merged_system: str,
        max_tokens: int | None,
    ) -> ContextBuildResult:
        """构建最终结果（同步/异步共用）。"""
        final_messages: list = list(context_messages)
        if request.messages:
            final_messages.extend(request.messages)

        return ContextBuildResult(
            messages=final_messages,
            system_message=merged_system,
            budget_enabled=max_tokens is not None,
            strategy_used=self._strategy.strategy_name,
        )

    async def _async_rag_search(self, request: ContextBuildRequest) -> str:
        """异步 RAG 优化检索。"""
        rag_query = request.rag_query or self._extract_last_user_message(
            request.messages
        )
        if not rag_query:
            return ""

        from src.ai.core.memory.types import RAGSearchConfig
        from src.ai.config.settings import settings as app_settings

        rag_config = RAGSearchConfig(
            enabled=True,
            top_k=request.rag_top_k,
            optimize_query=app_settings.memory.rag_optimize_query,
            merge_strategy=app_settings.memory.rag_merge_strategy,
        )
        rag_result = await self._rag_encoder.encode_and_search(
            rag_query,
            session_id=request.session_id,
            config=rag_config,
        )
        return rag_result.content

    # ── 来源收集（原 context/sources.py） ────────────────────

    @staticmethod
    def _collect_system_prompt(custom_prompt: str | None = None) -> str:
        """收集系统提示词。"""
        if custom_prompt:
            return custom_prompt

        try:
            from src.ai.core.prompts import PromptRenderRequest, prompt_service

            result = prompt_service.render(
                PromptRenderRequest(prompt_key="chat.system_prompt", variables={})
            )
            return result.content
        except Exception:
            logger.debug("DB 中未找到 chat.system_prompt 模板，使用内置默认")
            return ContextBuilder._default_system_prompt()

    @staticmethod
    def _default_system_prompt() -> str:
        """内置默认系统提示词。"""
        return (
            "你是一个智能助手，能够帮助用户完成各种任务。\n\n"
            "能力：\n"
            "- 回答问题、编写代码、分析文件\n"
            "- 调用工具执行文件读写、搜索、命令行等操作\n"
            "- 基于记忆系统记住用户偏好和项目上下文\n\n"
            "规则：\n"
            "- 优先使用工具完成需要实际操作的任务（读文件、搜索、执行命令等），不要凭空猜测\n"
            "- 工具调用失败时，向用户说明原因并提供替代方案\n"
            "- 涉及文件修改时，先读取确认再修改\n"
            "- 回答简洁准确，避免冗余"
        )

    @staticmethod
    def _collect_memory_context(
        query: str | None = None, *, search_limit: int = 5
    ) -> str:
        """收集记忆上下文。"""
        try:
            from src.ai.core.memory.service import memory_service

            system_context = memory_service.get_context_for_prompt()

            search_context = ""
            if query and query.strip():
                results = memory_service.search(query, limit=search_limit)
                if results:
                    lines = ["## 相关记忆", ""]
                    for r in results:
                        lines.append(f"- [{r.entry.memory_type}] {r.entry.description}")
                    search_context = "\n".join(lines)

            parts = [p for p in [system_context, search_context] if p]
            return "\n\n".join(parts)
        except Exception:
            logger.debug("记忆上下文收集失败", exc_info=True)
            return ""

    @staticmethod
    def _collect_tool_descriptions() -> str:
        """收集工具描述上下文。"""
        try:
            from src.ai.core.tools import tool_manager

            tools = tool_manager.list_tools(enabled_only=True)
            if not tools:
                return ""

            builtin_names = []
            mcp_names = []
            for tool in tools:
                meta = tool_manager._registry.get_meta(tool.name)
                if meta.source_type == "mcp":
                    mcp_names.append(tool.name)
                else:
                    builtin_names.append(tool.name)

            lines = ["## 工具使用指引", ""]
            if builtin_names:
                lines.append(f"内置工具: {', '.join(builtin_names)}")
            if mcp_names:
                lines.append(f"MCP 工具: {', '.join(mcp_names)}")
            lines.extend([
                "",
                "使用原则:",
                "- 需要读取文件、搜索代码、执行命令时，优先调用对应工具",
                "- 多步骤任务可以连续调用多个工具",
                "- 工具调用失败时分析原因，不要直接放弃",
            ])
            return "\n".join(lines)
        except Exception:
            logger.debug("工具描述收集失败", exc_info=True)
            return ""

    @staticmethod
    def _extract_last_user_message(messages: list) -> str:
        """从消息列表中提取最后一条用户消息。"""
        for msg in reversed(messages):
            if getattr(msg, "type", "") == "human":
                return msg.content
        return ""
