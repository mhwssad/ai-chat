"""提示词包 — 统一管理提示词（数据库持久化 + 内存注册表）。

加载流程:
1. registry.py — 内存注册表 + 渲染 API
2. models.py — 数据模型
3. store.py — SQLite 持久化
4. manager.py — PromptManager（初始化内置数据 + DB→注册表同步）
5. menu.py — CLI 菜单
"""

from .registry import (
    has_prompt,
    prompt_registry,
    register_prompt,
    render_messages,
    render_system_prompt,
)
from .models import PromptRecord, PromptCreateRequest, PromptTable
from .manager import PromptManager
from .jinja_env import prompt_env
from .menu import menu_prompts

__all__ = [
    "has_prompt",
    "prompt_registry",
    "register_prompt",
    "render_messages",
    "render_system_prompt",
    "PromptRecord",
    "PromptCreateRequest",
    "PromptTable",
    "PromptManager",
    "prompt_env",
    "menu_prompts",
]
