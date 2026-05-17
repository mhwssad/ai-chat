"""Jinja2 Environment 工厂 — 提示词模板专用的 Jinja2 环境。

提供:
- FileSystemLoader 指向 data/prompts/，支持 {% include %} 和 {% extends %}
- 通过 @register_filter 装饰器注册自定义 filter，符合开闭原则
- 全局单例 prompt_env 供 manager.py 和 registry.py 使用
"""

from __future__ import annotations

import json
from collections.abc import Callable

from jinja2 import Environment, FileSystemLoader

from src.ai_chat.config.base_config import project_root

PROMPTS_DIR = project_root / "data" / "prompts"

# ── Filter 注册表 ────────────────────────────────────

_filter_registry: dict[str, Callable] = {}


def register_filter(name: str):
    """装饰器：将函数注册为 Jinja2 filter。

    用法::

        @register_filter("tojson")
        def _json_filter(value, **kwargs) -> str: ...
    """
    def decorator(fn: Callable) -> Callable:
        _filter_registry[name] = fn
        return fn
    return decorator


# ── 内置 Filter 定义 ─────────────────────────────────

@register_filter("truncate")
def _truncate_filter(value: str, length: int = 200, end: str = "...") -> str:
    """截断文本到指定长度。"""
    if len(value) <= length:
        return value
    return value[: length - len(end)] + end


@register_filter("tojson")
def _json_filter(value, indent: int | None = None, ensure_ascii: bool = False) -> str:
    """将对象序列化为 JSON 字符串。"""
    return json.dumps(value, indent=indent, ensure_ascii=ensure_ascii)


@register_filter("default")
def _default_filter(value, default_value: str = "") -> str:
    """变量为空时返回默认值。"""
    return value if value else default_value


@register_filter("date")
def _date_filter(value, fmt: str = "%Y-%m-%d") -> str:
    """日期格式化 — 支持 datetime 对象和 ISO 字符串。"""
    from datetime import datetime
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime(fmt)


@register_filter("upper")
def _upper_filter(value) -> str:
    """转大写。"""
    return value.upper() if value else ""


@register_filter("lower")
def _lower_filter(value) -> str:
    """转小写。"""
    return value.lower() if value else ""


@register_filter("strip")
def _strip_filter(value) -> str:
    """去除首尾空白。"""
    return value.strip() if value else ""


@register_filter("wordcount")
def _wordcount_filter(value) -> int:
    """统计词数。"""
    return len(value.split()) if value else 0


@register_filter("default_if_none")
def _default_if_none_filter(value, default_value: str = "") -> str:
    """仅 None 时返回默认值（区别于 default — 空字符串也保留）。"""
    return value if value is not None else default_value


# ── Environment 工厂 ─────────────────────────────────

def create_prompt_env() -> Environment:
    """创建提示词专用的 Jinja2 Environment。"""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    env.filters.update(_filter_registry)
    return env


# 全局单例
prompt_env = create_prompt_env()
