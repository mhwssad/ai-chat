"""Graph 公共基类 — 提供配置化、重试、sync/async 桥接、记忆管理和 chat 循环。"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from typing import Any, Optional, TypeVar

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm import llm_factory

logger = get_logger(__name__)

PromptContext = dict[str, Any]
T = TypeVar("T")


# ── 配置 ──────────────────────────────────────────────


@dataclass
class GraphConfig:
    """Agent 生成参数配置。"""

    temperature: float = 0.7
    max_tokens: Optional[int] = None
    max_retries: int = 2
    timeout: int = 60
    recursion_limit: int = 25


# ── 异常 ──────────────────────────────────────────────


class GraphError(Exception):
    """Graph 执行异常。"""


class GraphExecutionError(GraphError):
    """Graph 节点执行异常。"""


class GraphRoutingError(GraphError):
    """Graph 条件路由异常。"""


# ── 共享工具函数 ──────────────────────────────────────


def merge_context(
    base: Optional[PromptContext],
    override: Optional[PromptContext],
    final: Optional[PromptContext] = None,
) -> PromptContext:
    """三层字典合并：final > override > base。"""
    context: PromptContext = {}
    if base:
        context.update(base)
    if override:
        context.update(override)
    if final:
        context.update(final)
    return context


def extract_last_human_message(messages: list[BaseMessage]) -> str:
    """从消息列表中提取最后一条 HumanMessage 的文本内容。"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


def get_default_model() -> str:
    """从 settings 获取默认模型名称。"""
    from src.ai_chat.config import settings
    return settings.model_name


# ── 基类 ──────────────────────────────────────────────


class _BaseAgent:
    """Agent 公共基类 — 统一模型解析、记忆管理、sync/async 桥接、重试、chat 循环。

    子类只需实现：
    - ainvoke(message, history, **kwargs) -> str
    - astream(message, history) -> AsyncIterator[str]
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        config: Optional[GraphConfig] = None,
        memory: Optional[Any] = None,
        session_id: Optional[str] = None,
        memory_config: Optional[Any] = None,
    ) -> None:
        self._model_name = model_name or get_default_model()
        self._config = config or GraphConfig()
        self._memory = memory
        self._session_id = session_id

        # 如果没有外部 memory 但有 session_id，内部创建
        if memory is None and session_id is not None:
            self._init_internal_memory(session_id, memory_config)

    def _init_internal_memory(self, session_id: str, memory_config: Optional[Any] = None) -> None:
        """内部创建 ConversationMemory（MemoryAgent/UnifiedAgent 模式）。"""
        from src.ai_chat.memory import ConversationMemory
        self._memory = ConversationMemory(
            session_id=session_id,
            config=memory_config,
            model_name=self._model_name,
        )

    @property
    def session_id(self) -> str:
        if self._memory is not None:
            return self._memory.session_id
        return self._session_id or ""

    def _get_llm(self, model_name: Optional[str] = None) -> Any:
        """获取 LLM 客户端。"""
        name = model_name or self._model_name
        return llm_factory.get_client(name)

    # ── 记忆管理 ──────────────────────────────────────

    def _build_messages(
        self,
        message: str,
        history: Optional[list[BaseMessage]] = None,
    ) -> list[BaseMessage]:
        """构建消息列表（自动从 memory 加载历史）。"""
        if self._memory is not None:
            history = self._memory.load_history()
        messages = list(history) if history else []
        messages.append(HumanMessage(content=message))
        return messages

    def _save(self, message: str, ai_content: str) -> None:
        """保存交互到记忆。"""
        if self._memory is not None:
            self._memory.save_interaction(
                HumanMessage(content=message),
                AIMessage(content=ai_content),
            )

    # ── Sync/Async 桥接 ──────────────────────────────

    def _run_async(self, coro) -> Any:
        """在同步上下文中运行异步协程。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        else:
            loop = True

        if loop:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)

    def _run_async_iterator(self, async_gen: AsyncIterator[str]) -> Iterator[str]:
        """将异步迭代器桥接为同步迭代器。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        else:
            loop = True

        async def _collect():
            chunks = []
            async for chunk in async_gen:
                chunks.append(chunk)
            return chunks

        if loop:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                for chunk in pool.submit(asyncio.run, _collect()).result():
                    yield chunk
        else:
            for chunk in asyncio.run(_collect()):
                yield chunk

    # ── 重试 ─────────────────────────────────────────

    def _invoke_with_retry(self, fn: Callable, *args, **kwargs) -> Any:
        """带指数退避的重试包装。"""
        last_error = None
        for attempt in range(self._config.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self._config.max_retries:
                    wait = 0.5 * (2 ** attempt)
                    logger.warning(
                        "Agent 调用失败 (第 %d/%d 次), %.1fs 后重试: %s",
                        attempt + 1, self._config.max_retries + 1, wait, e,
                    )
                    time.sleep(wait)
        raise GraphExecutionError(
            f"Agent 调用失败，已重试 {self._config.max_retries} 次: {last_error}"
        ) from last_error

    # ── 同步入口 ──────────────────────────────────────

    def invoke(self, message: str, history: Optional[list[BaseMessage]] = None, **kwargs) -> str:
        """同步调用。"""
        return self._run_async(self.ainvoke(message, history, **kwargs))

    def stream(self, message: str, history: Optional[list[BaseMessage]] = None, **kwargs) -> Iterator[str]:
        """同步流式调用。"""
        yield from self._run_async_iterator(self.astream(message, history, **kwargs))

    # ── Chat 循环 ─────────────────────────────────────

    def chat(self) -> None:
        """交互式对话循环。"""
        if self._memory is not None:
            print(f"会话 ID: {self.session_id}")
        print("输入 'quit' 或 'exit' 退出\n")

        while True:
            user_input = input("你: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                print("再见！")
                break
            response = self.invoke(user_input)
            print(f"AI: {response}\n")

    # ── 会话管理 ──────────────────────────────────────

    def clear(self) -> None:
        """清除记忆。"""
        if self._memory is not None:
            self._memory.clear()

    def get_summary(self) -> Optional[str]:
        """获取会话摘要。"""
        if self._memory is not None:
            return self._memory.get_summary()
        return None

    def get_message_count(self) -> int:
        """获取消息数量。"""
        if self._memory is not None:
            return self._memory.get_message_count()
        return 0
