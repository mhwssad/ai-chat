"""路由工厂 — 根据模型名称或显式名称路由到对应提供商策略（聊天 + 嵌入）。"""

import threading
from typing import Optional

from src.ai_chat.llm.models import (
    ChatProvider, ChatRequest, ChatResponse,
    EmbeddingProvider,
    ModelNotSupportedException,
)


class ChatModelFactory:
    """聊天模型路由工厂（单例）。

    支持两种路由方式：
    - 按模型名称自动匹配（向后兼容）
    - 按显式注册名称直接查找（支持同一 provider 多实例）
    """

    _instance: "ChatModelFactory | None" = None
    _lock: threading.Lock = threading.Lock()

    _named: dict[str, ChatProvider]
    _unnamed: list[ChatProvider]

    def __new__(cls) -> "ChatModelFactory":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._named = {}
                    instance._unnamed = []
                    cls._instance = instance
        return cls._instance

    def register(self, provider: ChatProvider, *, name: Optional[str] = None) -> None:
        """注册一个提供商策略。传入 ``name`` 以支持按名称直接查找。"""
        if name:
            self._named[name] = provider
        else:
            self._unnamed.append(provider)

    def register_many(self, providers: list[ChatProvider]) -> None:
        """批量注册（无名称，按模型名路由）。"""
        self._unnamed.extend(providers)

    def get_provider(self, model_name: str, *, name: Optional[str] = None) -> ChatProvider:
        """根据模型名称或显式名称查找策略。

        - 传入 ``name`` 时直接从命名注册表查找。
        - 否则按 ``model_name`` 匹配（遍历无名注册表，再遍历命名注册表）。

        Raises:
            ModelNotSupportedException: 未找到匹配的策略。
        """
        if name:
            if name in self._named:
                return self._named[name]
            raise KeyError(f"未找到命名策略：'{name}'")

        # 无名注册表
        for provider in self._unnamed:
            if provider.supports_model(model_name):
                return provider
        # 命名注册表
        for provider in self._named.values():
            if provider.supports_model(model_name):
                return provider

        all_models = [m for p in self._unnamed for m in p.get_supported_models()]
        all_models += [m for p in self._named.values() for m in p.get_supported_models()]
        raise ModelNotSupportedException(model_name, all_models)

    def get_all_supported_models(self) -> list[str]:
        """返回所有已注册策略支持的模型名称列表。"""
        models = [m for p in self._unnamed for m in p.get_supported_models()]
        models += [m for p in self._named.values() for m in p.get_supported_models()]
        return models

    def chat(self, request: ChatRequest, model_name: str, *, name: Optional[str] = None) -> ChatResponse:
        """根据模型名称自动路由，发起聊天请求。"""
        provider = self.get_provider(model_name, name=name)
        return provider.chat(request, model_name)

    def get_client(self, model_name: str, *, name: Optional[str] = None):
        """根据模型名称自动路由，获取底层 LangChain 客户实例。"""
        provider = self.get_provider(model_name, name=name)
        return provider.get_client(model_name)


# ======================================================================
# 嵌入模型路由工厂
# ======================================================================

class EmbeddingModelFactory:
    """嵌入模型路由工厂（单例）。

    支持两种路由方式：
    - 按模型名称自动匹配（向后兼容）
    - 按显式注册名称直接查找（支持同一 provider 多实例）
    """

    _instance: "EmbeddingModelFactory | None" = None
    _lock: threading.Lock = threading.Lock()

    _named: dict[str, EmbeddingProvider]
    _unnamed: list[EmbeddingProvider]

    def __new__(cls) -> "EmbeddingModelFactory":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._named = {}
                    instance._unnamed = []
                    cls._instance = instance
        return cls._instance

    def register(self, provider: EmbeddingProvider, *, name: Optional[str] = None) -> None:
        """注册一个嵌入策略。传入 ``name`` 以支持按名称直接查找。"""
        if name:
            self._named[name] = provider
        else:
            self._unnamed.append(provider)

    def register_many(self, providers: list[EmbeddingProvider]) -> None:
        """批量注册（无名称，按模型名路由）。"""
        self._unnamed.extend(providers)

    def get_provider(self, model_name: str, *, name: Optional[str] = None) -> EmbeddingProvider:
        """根据模型名称或显式名称查找嵌入策略。"""
        if name:
            if name in self._named:
                return self._named[name]
            raise KeyError(f"未找到命名策略：'{name}'")

        for provider in self._unnamed:
            if provider.supports_model(model_name):
                return provider
        for provider in self._named.values():
            if provider.supports_model(model_name):
                return provider

        all_models = [m for p in self._unnamed for m in p.get_supported_models()]
        all_models += [m for p in self._named.values() for m in p.get_supported_models()]
        raise ModelNotSupportedException(model_name, all_models)

    def get_all_supported_models(self) -> list[str]:
        """返回所有已注册嵌入策略支持的模型名称列表。"""
        models = [m for p in self._unnamed for m in p.get_supported_models()]
        models += [m for p in self._named.values() for m in p.get_supported_models()]
        return models

    def embed(self, text: str, model_name: str, *, name: Optional[str] = None) -> list[float]:
        """根据模型名称自动路由，获取单段文本的嵌入向量。"""
        provider = self.get_provider(model_name, name=name)
        return provider.embed(text, model_name)

    def embed_batch(self, texts: list[str], model_name: str, *, name: Optional[str] = None) -> list[list[float]]:
        """根据模型名称自动路由，批量获取文本的嵌入向量。"""
        provider = self.get_provider(model_name, name=name)
        return provider.embed_batch(texts, model_name)


# ======================================================================
# 全局单例
# ======================================================================

chat_factory = ChatModelFactory()

embedding_factory = EmbeddingModelFactory()
