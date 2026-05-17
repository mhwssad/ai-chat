"""聊天模型提供商策略接口。"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import AsyncIterator
from typing import Iterator, Optional

from langchain_core.language_models import BaseChatModel

from src.ai_chat.config.logging_setup import get_logger
from src.ai_chat.llm.base import ModelProvider
from src.ai_chat.llm.models import ChatRequest, ChatResponse, extract_usage
from src.ai_chat.utils.cache import LRUCache

logger = get_logger(__name__)


class ChatProvider(ModelProvider):
    """聊天模型提供商策略。

    子类只需实现 _build_client() 方法，将通用参数映射到对应 SDK 的参数名。
    chat / stream / achat / astream / get_client / get_stream_client 均由基类提供。
    """

    @property
    def provider_type(self) -> str:
        return "chat"

    def _ensure_cache(self):
        """延迟初始化客户端缓存。"""
        if not hasattr(self, "_client_cache"):
            self._client_cache: LRUCache[tuple, BaseChatModel] = LRUCache(maxsize=32)

    # ── 内容规范化 ────────────────────────────────────────

    @staticmethod
    def _normalize_content(content) -> str:
        """将模型响应内容规范化为字符串。处理列表格式的多模态内容。"""
        if isinstance(content, list):
            return "".join(
                item if isinstance(item, str) else str(item.get("text", ""))
                for item in content
            )
        return str(content)

    # ── 客户端构建与缓存 ─────────────────────────────────

    @abstractmethod
    def _build_client(self, model_name: str, **kwargs) -> BaseChatModel:
        """创建 LangChain 客户端（子类实现）。

        kwargs 包含 temperature / max_tokens / stop / streaming 等参数，
        子类将它们映射到对应 SDK 的参数名。值为 None 的参数应忽略。

        Args:
            model_name: 目标模型名称
            **kwargs: 生成参数

        Returns:
            配置好的 BaseChatModel 实例
        """

    def _get_cached_client(self, model_name: str, **kwargs) -> BaseChatModel:
        """获取缓存的客户端，未命中时调用 _build_client() 创建并缓存。"""
        self._ensure_cache()
        cache_key = (
            model_name,
            tuple(sorted((k, v) for k, v in kwargs.items() if v is not None)),
        )
        cached = self._client_cache.get(cache_key)
        if cached is not None:
            logger.debug("客户端缓存命中: model=%s", model_name)
            return cached
        client = self._build_client(model_name, **kwargs)
        self._client_cache.put(cache_key, client)
        return client

    # ── 公开客户端接口 ───────────────────────────────────

    def get_client(self, model_name: str) -> BaseChatModel:
        """获取底层 LangChain 客户实例（供链/Agent 使用）。"""
        return self._get_cached_client(model_name)

    def get_stream_client(
        self,
        model_name: str,
        *,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[list[str]] = None,
    ) -> BaseChatModel:
        """获取带流式配置的 LangChain 客户实例。"""
        return self._get_cached_client(
            model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop,
            streaming=True,
        )

    def get_client_with_tools(self, model_name: str, tools: list) -> BaseChatModel:
        """获取绑定了工具的 LangChain 客户端。"""
        return self.get_client(model_name).bind_tools(tools)

    # ── 聊天与流式（基类默认实现） ───────────────────────

    def chat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """发起聊天请求（基类实现，通过 _build_client 缓存复用客户端）。"""
        logger.info(
            "聊天请求: model=%s, 消息数=%d, temperature=%.2f",
            model_name,
            len(request.messages),
            request.temperature,
        )
        client = self._get_cached_client(
            model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        result = client.invoke(request.messages)
        content = self._normalize_content(result.content)
        usage = extract_usage(result)
        logger.info("聊天响应: model=%s, 内容长度=%d", model_name, len(content))
        return ChatResponse(content=content, model=model_name, usage=usage)

    def stream(
        self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None
    ) -> Iterator[str]:
        """流式聊天，逐 token 返回文本片段。"""
        logger.info("流式请求: model=%s, 消息数=%d", model_name, len(request.messages))
        client = self.get_stream_client(
            model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=stop,
        )
        token_count = 0
        for chunk in client.stream(request.messages):
            if isinstance(chunk.content, str) and chunk.content:
                token_count += 1
                yield chunk.content
        logger.debug("流式完成: model=%s, 共 %d 个 chunk", model_name, token_count)

    # ── 异步实现（LangChain 原生异步） ────────────────────

    async def achat(self, request: ChatRequest, model_name: str) -> ChatResponse:
        """异步聊天 — 使用 LangChain 客户端原生异步。"""
        client = self._get_cached_client(
            model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        result = await client.ainvoke(request.messages)
        content = self._normalize_content(result.content)
        return ChatResponse(
            content=content,
            model=model_name,
            usage=extract_usage(result),
        )

    async def astream(
        self, request: ChatRequest, model_name: str, *, stop: Optional[list[str]] = None
    ) -> AsyncIterator[str]:
        """异步流式聊天 — 使用 LangChain 客户端原生异步。"""
        client = self._get_cached_client(
            model_name,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stop=stop,
        )
        async for chunk in client.astream(request.messages):
            if chunk.content and isinstance(chunk.content, str):
                yield chunk.content
