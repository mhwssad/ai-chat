"""提示词包 — 自动扫描 templates/ 目录、注册内置模板并暴露统一渲染 API。"""

import importlib
import pkgutil
from pathlib import Path

from .registry import (
    has_prompt,
    prompt_registry,
    register_prompt,
    render_messages,
    render_system_prompt,
)

# 1. 扫描 templates/ 目录下的 .jinja2 文件
from .registry import scan_templates

scan_templates(Path(__file__).parent)

# 2. 扫描 .py 模块（触发 @register_prompt 装饰器）
package_dir = Path(__file__).parent
for info in pkgutil.iter_modules([str(package_dir)]):
    importlib.import_module(f"{__name__}.{info.name}")

__all__ = [
    "has_prompt",
    "prompt_registry",
    "register_prompt",
    "render_messages",
    "render_system_prompt",
]
