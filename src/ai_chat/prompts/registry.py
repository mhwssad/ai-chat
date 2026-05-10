"""提示词注册表 — 支持装饰器注册和 Jinja2 文件自动扫描。"""

from pathlib import Path
from typing import Callable

from langchain_core.prompts import ChatPromptTemplate


class PromptRegistry:
    """提示词注册表，按名称注册/获取 ChatPromptTemplate。"""

    def __init__(self) -> None:
        self._registry: dict[str, ChatPromptTemplate] = {}

    def register(self, name: str, template: ChatPromptTemplate) -> None:
        """注册提示词模板。"""
        self._registry[name] = template

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


# ======================================================================
# 文件扫描 — 自动注册 templates/ 目录下的 .jinja2 文件
# ======================================================================

def scan_templates(package_dir: Path) -> None:
    """扫描 templates/ 目录下 .jinja2 文件，自动注册为 ChatPromptTemplate。

    文件名（不含扩展名）即为注册名称。
    """
    templates_dir = package_dir / "templates"
    if not templates_dir.exists():
        return
    for path in sorted(templates_dir.glob("*.jinja2")):
        name = path.stem
        content = path.read_text(encoding="utf-8")
        template = ChatPromptTemplate.from_template(content, template_format="jinja2")
        prompt_registry.register(name, template)
