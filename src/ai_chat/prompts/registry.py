"""提示词注册表 — 内存注册 + 装饰器注册 + 统一渲染。"""

from typing import Callable

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate


class PromptRegistry:
    """提示词注册表，按名称注册/获取 ChatPromptTemplate。"""

    def __init__(self) -> None:
        self._registry: dict[str, ChatPromptTemplate] = {}

    def register(self, name: str, template: ChatPromptTemplate) -> None:
        """注册提示词模板。"""
        self._registry[name] = template

    def unregister(self, name: str) -> None:
        """移除已注册的提示词模板。"""
        if name in self._registry:
            del self._registry[name]

    def get(self, name: str) -> ChatPromptTemplate:
        """按名称获取提示词模板。"""
        if name not in self._registry:
            raise KeyError(f"未注册的提示词：'{name}'，已注册：{list(self._registry)}")
        return self._registry[name]

    def list_prompts(self) -> list[str]:
        """列出所有已注册的提示词名称。"""
        return list(self._registry)

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __len__(self) -> int:
        return len(self._registry)

    def __repr__(self) -> str:
        names = list(self._registry)
        return f"PromptRegistry({len(names)} prompts: {names})"

    # ── 批量操作 ───────────────────────────────────────

    def register_many(self, items: dict[str, ChatPromptTemplate]) -> int:
        """批量注册提示词模板，返回新注册数量。"""
        count = 0
        for name, template in items.items():
            if name not in self._registry:
                self._registry[name] = template
                count += 1
        return count

    def get_many(self, names: list[str]) -> dict[str, ChatPromptTemplate]:
        """批量获取提示词模板，跳过不存在的。"""
        return {n: self._registry[n] for n in names if n in self._registry}

    def unregister_many(self, names: list[str]) -> int:
        """批量移除提示词模板，返回实际移除数量。"""
        count = 0
        for name in names:
            if name in self._registry:
                del self._registry[name]
                count += 1
        return count


# ======================================================================
# 全局单例
# ======================================================================

prompt_registry = PromptRegistry()


# ======================================================================
# 装饰器 — Python 内定义复杂模板
# ======================================================================

def register_prompt(name: str):
    """函数装饰器：调用函数获取 ChatPromptTemplate 并注册。

    装饰后函数被替换为模板实例，变量名仍可当 ChatPromptTemplate 使用。

    用法::

        @register_prompt("chat")
        def chat_prompt():
            return ChatPromptTemplate.from_messages([...])

        # chat_prompt 现在是 ChatPromptTemplate 实例
    """
    def decorator(fn: Callable[[], ChatPromptTemplate]):
        template = fn()
        prompt_registry.register(name, template)
        return template
    return decorator


def has_prompt(prompt_key: str) -> bool:
    """判断提示词是否已注册。"""
    return prompt_key in prompt_registry


def render_messages(prompt_key: str, **context) -> list[BaseMessage]:
    """按名称渲染提示词消息列表。"""
    template = prompt_registry.get(prompt_key)
    missing = [name for name in template.input_variables if name not in context]
    if missing:
        raise KeyError(f"提示词 '{prompt_key}' 缺少必填变量：{missing}")
    return template.format_messages(**context)


def render_system_prompt(prompt_key: str, **context) -> str:
    """将单条 system 提示词渲染为纯文本。"""
    messages = render_messages(prompt_key, **context)
    if len(messages) != 1:
        raise ValueError(
            f"提示词 '{prompt_key}' 必须渲染为单条 system 消息，实际得到 {len(messages)} 条消息。"
        )
    message = messages[0]
    if not isinstance(message, SystemMessage):
        raise ValueError(
            f"提示词 '{prompt_key}' 必须渲染为 SystemMessage，实际得到 {type(message).__name__}。"
        )
    return message.content if isinstance(message.content, str) else str(message.content)
