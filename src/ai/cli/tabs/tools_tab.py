"""工具管理面板 — 工具列表、筛选、启用/禁用、测试执行。"""

import asyncio
import json
import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab, TabLayoutSpec
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import truncate, wrap_text
from src.ai.cli.utils.rich_components import create_styled_table

logger = logging.getLogger(__name__)


class ToolsTab(BaseTab):
    """工具管理面板。

    展示已注册工具列表，支持启用/禁用和测试执行。
    """

    name = "工具"
    hotkey = "3"
    layout = TabLayoutSpec(mode="resource")

    def __init__(self, *, thread_pool: Any, tool_service: Any) -> None:
        super().__init__(thread_pool)
        self._tool_service = tool_service
        self._cache_ttl = 5.0
        self._tools: list[dict[str, object]] = []
        self._show_all: bool = True
        self._test_result: str = ""
        self._test_running: bool = False

    def register_commands(self, router: Any, tab_index: int) -> None:
        router.register(tab_index, "e", self._toggle_selected)
        router.register(tab_index, "a", self._toggle_filter)
        router.register(tab_index, "t", self._test_selected)

    def _load_data(self) -> None:
        """加载工具列表。"""
        try:
            if self._search_query:
                self._tools = self._tool_service.search_tools(
                    self._search_query, enabled_only=not self._show_all
                )
            else:
                self._tools = self._tool_service.list_tools(
                    enabled_only=not self._show_all
                )
        except Exception as e:
            logger.debug("加载工具列表失败: %s", e)
            self._tools = []

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        self._clamp_selection(len(self._tools))

        # 标题信息
        filter_label = "全部" if self._show_all else "仅启用"
        if self._search_query:
            title_info = (
                f'搜索 "{self._search_query}" ({len(self._tools)} 个, {filter_label})'
            )
        else:
            title_info = f"工具列表 ({len(self._tools)} 个, {filter_label})"

        if not self._tools:
            text = Text()
            text.append(f"\n  {title_info}\n", style="subtitle")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append("  没有已注册的工具\n", style="muted")

            # 测试进行中
            if self._test_running:
                text.append("\n  测试中...\n", style="warning")
            if self._test_result:
                text.append("\n测试结果:\n", style="subtitle")
                for line in self._test_result.split("\n")[:8]:
                    text.append(f"  {line}\n", style="value")

            text.append("\n")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append(
                "  UP/DN 浏览 | E 启用/禁用 | A 切换筛选 | T 测试执行\n", style="muted"
            )
            return Panel(
                text, title=f"[title]{Icons.TAB_TOOLS} 工具[/]", border_style="border"
            )

        # 使用 Rich Table
        table = create_styled_table(
            title_info,
            [
                ("", "", 2),  # 指针
                ("状态", "center", 4),  # 状态图标
                ("名称", "bold", 20),
                ("来源", "muted", 10),
                ("描述", "", 30),
            ],
        )

        # 滚动支持
        visible_count = max(1, height - 10)
        scroll = self._get_scroll_offset(visible_count, len(self._tools))

        for i in range(scroll, min(scroll + visible_count, len(self._tools))):
            tool = self._tools[i]
            pointer = Icons.POINTER if i == self._selected_index else " "
            enabled = tool["enabled"]
            essential = tool["essential"]
            status_icon = Icons.ACTIVE if enabled else Icons.INACTIVE
            name = str(tool["name"])
            source = str(tool["source_type"])
            desc = truncate(str(tool["description"]), max_len=width - 50)

            # essential 标记
            if essential:
                desc_display = f"{desc} [warning][core][/]"
            else:
                desc_display = desc

            row_style = "reverse" if i == self._selected_index else ""
            table.add_row(
                Text(pointer, style="bold green" if i == self._selected_index else ""),
                Text(status_icon, style="active" if enabled else "inactive"),
                Text(name, style=row_style),
                Text(source),
                Text.from_markup(desc_display),
                style=row_style,
            )

        # 测试进行中
        if self._test_running:
            table.add_row("", "", Text("测试中...", style="warning"), "", "")

        # 测试结果
        if self._test_result:
            result_lines = self._test_result.split("\n")[:4]
            for line in result_lines:
                table.add_row("", "", Text(line, style="value"), "", "")

        return Panel(
            table,
            title=f"[title]{Icons.TAB_TOOLS} 工具[/]",
            border_style="border",
        )

    def handle_input(self, key: str) -> bool:
        if key == "up":
            self._move_selection(-1, len(self._tools))
            return True
        elif key == "down":
            self._move_selection(1, len(self._tools))
            return True
        elif key == "a":
            return self._toggle_filter()
        elif key == "e":
            return self._toggle_selected()
        elif key == "t":
            return self._test_selected()
        elif key == "escape":
            if self.is_searching:
                self.clear_search()
                return True
        return False

    def _toggle_selected(self) -> bool:
        """切换选中工具的启用/禁用状态。"""
        if not self._tools or self._selected_index >= len(self._tools):
            return False

        tool = self._tools[self._selected_index]
        if tool["essential"]:
            return False

        try:
            name = str(tool["name"])
            if tool["enabled"]:
                self._tool_service.disable_tool(name)
            else:
                self._tool_service.enable_tool(name)
            self._invalidate_cache()
            self._set_status("[success][OK] 工具状态已切换[/]")
            return True
        except Exception as e:
            logger.debug("切换工具状态失败: %s", e)
            self._set_status("[error][X] 工具状态切换失败[/]")
            return False

    def _toggle_filter(self) -> bool:
        self._show_all = not self._show_all
        self._selected_index = 0
        self._invalidate_cache()
        self._set_status("[info]工具筛选已切换[/]")
        return True

    def _test_selected(self) -> bool:
        """测试执行选中的工具（后台线程池执行）。"""
        if not self._tools or self._selected_index >= len(self._tools):
            return False
        if self._test_running:
            return False

        tool = self._tools[self._selected_index]
        tool_name = str(tool["name"])
        self._test_running = True
        self._test_result = ""

        def _run() -> None:
            try:
                async def _do():
                    return await self._tool_service.execute_tool(tool_name, {})

                result = asyncio.run(_do())
                result_str = str(result)
                if len(result_str) > 500:
                    result_str = result_str[:500] + "\n...(已截断)"
                self._test_result = result_str
            except Exception as e:
                self._test_result = f"执行失败: {e}"
            finally:
                self._test_running = False

        self._thread_pool.run_bg(_run)
        self._set_status("[info]工具测试已启动[/]")
        return True

    def get_footer_commands(self) -> list[tuple[str, str]]:
        """返回 Tools Tab 底部命令列表。"""
        return [("e", "启用/禁用"), ("a", "筛选"), ("t", "测试")]

    def get_tab_header_lines(self) -> list[str]:
        filter_label = "全部" if self._show_all else "仅启用"
        return [f"工具: {len(self._tools)}", f"筛选: {filter_label}"]

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
            for line in wrap_text(desc, max(10, width - 8)):
                text.append(f"  {line}\n", style="value")

            # JSON Schema 信息
            text.append("\n  参数 Schema:\n", style="subtitle")
            try:
                detail = self._tool_service.get_tool_detail(str(tool["name"]))
                schema_dict = detail.get("args_schema", {})
                if schema_dict:
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
