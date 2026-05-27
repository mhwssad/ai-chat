"""工具层通用类型。"""

from dataclasses import dataclass
from typing import Literal

ToolSourceType = Literal["builtin", "mcp"]


@dataclass(frozen=True)
class ToolFilterContext:
    """工具过滤上下文，用于按权限和来源筛选工具。"""

    allowed_permissions: set[str] | None = None
    exclude_sources: set[ToolSourceType] | None = None
    tool_names: set[str] | None = None
