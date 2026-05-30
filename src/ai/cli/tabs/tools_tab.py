"""工具管理面板 — 工具列表、筛选、启用/禁用、测试执行。"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import truncate


class ToolsTab(BaseTab):
    """工具管理面板。

    展示已注册工具列表，支持启用/禁用操作。
    """

    name = "工具"
    hotkey = "2"

    def __init__(self) -> None:
        super().__init__()
        self._tools: list[dict[str, object]] = []
        self._show_all: bool = True

    def _load_tools(self) -> None:
        """加载工具列表。"""
        try:
            from src.ai.core.container import container

            registry = container.tool_container.tool_registry()
            tools = registry.list(enabled_only=not self._show_all)
            self._tools = []
            for tool in tools:
                meta = registry.get_meta(tool.name)
                self._tools.append(
                    {
                        "name": tool.name,
                        "description": getattr(tool, "description", "") or "",
                        "source_type": meta.source_type,
                        "enabled": meta.enabled,
                        "essential": meta.essential,
                    }
                )
        except Exception:
            self._tools = []

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._load_tools()
        self._clamp_selection(len(self._tools))

        text = Text()

        # 标题行
        filter_label = "全部" if self._show_all else "仅启用"
        text.append(
            f"工具列表 ({len(self._tools)} 个, {filter_label})\n", style="subtitle"
        )
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        # 表头
        text.append("  状态  名称                    来源      描述\n", style="muted")
        text.append("  " + Icons.LINE * (width - 6) + "\n", style="muted")

        if not self._tools:
            text.append("  没有已注册的工具\n", style="muted")
        else:
            for i, tool in enumerate(self._tools):
                prefix = Icons.POINTER if i == self._selected_index else " "
                enabled = tool["enabled"]
                essential = tool["essential"]
                status_icon = Icons.ACTIVE if enabled else Icons.INACTIVE
                status_style = "active" if enabled else "inactive"

                name = str(tool["name"])
                source = str(tool["source_type"])
                desc = truncate(str(tool["description"]), max_len=width - 50)

                line_style = "selected" if i == self._selected_index else ""
                text.append(f" {prefix} ", style=line_style)
                text.append(f"{status_icon}", style=status_style)
                text.append(f"  {name:<24s}", style=line_style)
                text.append(f" {source:<10s}", style="muted")
                text.append(f" {desc}\n", style=line_style)

                if essential:
                    # 在下一行显示核心标记
                    pass

        # 底部操作提示
        text.append("\n", style="")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")
        text.append(
            "  ↑↓ 浏览 │ E 启用/禁用 │ A 切换筛选 │ T 测试执行\n", style="muted"
        )

        return Panel(
            text, title=f"[title]{Icons.TAB_TOOLS} 工具[/]", border_style="border"
        )

    def handle_input(self, key: str) -> bool:
        if key == "up":
            self._move_selection(-1, len(self._tools))
            return True
        elif key == "down":
            self._move_selection(1, len(self._tools))
            return True
        elif key == "a":
            self._show_all = not self._show_all
            self._selected_index = 0
            return True
        elif key == "e":
            self._toggle_selected()
            return True
        return False

    def _toggle_selected(self) -> None:
        """切换选中工具的启用/禁用状态。"""
        if not self._tools or self._selected_index >= len(self._tools):
            return

        tool = self._tools[self._selected_index]
        if tool["essential"]:
            return  # 核心工具不可禁用

        try:
            from src.ai.core.container import container

            registry = container.tool_container.tool_registry()
            meta = registry.get_meta(str(tool["name"]))
            meta.enabled = not meta.enabled
        except Exception:
            pass

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()

        if not self._tools or self._selected_index >= len(self._tools):
            text.append("  选择一个工具查看详情", style="muted")
        else:
            tool = self._tools[self._selected_index]
            text.append("工具详情\n\n", style="subtitle")
            text.append(f"  名称: {tool['name']}\n", style="value")
            text.append(f"  来源: {tool['source_type']}\n", style="value")
            text.append(
                f"  状态: {'启用' if tool['enabled'] else '禁用'}\n",
                style="active" if tool["enabled"] else "inactive",
            )
            text.append(
                f"  核心: {'是' if tool['essential'] else '否'}\n", style="value"
            )
            text.append("\n  描述:\n", style="subtitle")

            desc = str(tool["description"])
            # 自动换行
            line_width = width - 8
            for i in range(0, len(desc), line_width):
                text.append(f"  {desc[i : i + line_width]}\n", style="value")

            # JSON Schema 信息
            text.append("\n  参数 Schema:\n", style="subtitle")
            try:
                from src.ai.core.container import container

                registry = container.tool_container.tool_registry()
                base_tool = registry.get(str(tool["name"]))
                schema = base_tool.args_schema
                if schema:
                    import json

                    schema_dict = (
                        schema.model_json_schema()
                        if hasattr(schema, "model_json_schema")
                        else {}
                    )
                    schema_str = json.dumps(schema_dict, indent=2, ensure_ascii=False)
                    for line in schema_str.split("\n")[:15]:
                        text.append(f"  {line}\n", style="muted")
                    if len(schema_str.split("\n")) > 15:
                        text.append("  ...(已截断)\n", style="muted")
                else:
                    text.append("  无参数\n", style="muted")
            except Exception:
                text.append("  无法加载 Schema\n", style="muted")

        return Panel(text, title="[title]工具详情[/]", border_style="border")
