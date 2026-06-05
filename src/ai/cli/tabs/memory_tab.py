"""记忆管理面板 — 记忆列表、搜索、删除。"""

import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab, TabLayoutSpec, TabSummary
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import truncate, wrap_text
from src.ai.cli.utils.rich_components import create_styled_table

logger = logging.getLogger(__name__)


class MemoryTab(BaseTab):
    """记忆管理面板。

    展示记忆条目列表，支持搜索和删除操作。
    """

    name = "记忆"
    hotkey = "4"
    layout = TabLayoutSpec(mode="resource")

    def __init__(self, *, thread_pool: Any, memory_service: Any) -> None:
        super().__init__(thread_pool)
        self._memory_service = memory_service
        self._entries: list[dict[str, object]] = []

    def register_commands(self, router: Any, tab_index: int) -> None:
        router.register(tab_index, "d", self._request_delete_selected)
        router.register(tab_index, "r", self._rebuild_index)
        router.register(
            tab_index,
            "/",
            lambda: self._request_input("搜索关键词: ", self._search_memory),
        )

    def _load_data(self) -> None:
        """加载记忆条目。"""
        try:
            if self._search_query:
                results = self._memory_service.search(self._search_query, limit=50)
                self._entries = []
                for r in results:
                    entry = r.entry
                    self._entries.append(
                        {
                            "name": entry.name,
                            "memory_type": entry.memory_type,
                            "scope": entry.scope,
                            "source_type": entry.source_type,
                            "source_id": entry.source_id,
                            "status": entry.status,
                            "description": entry.description,
                            "content": entry.content,
                            "score": r.score,
                            "match_type": r.match_type,
                        }
                    )
            else:
                entries = self._memory_service.list_entries()
                self._entries = []
                for entry in entries:
                    self._entries.append(
                        {
                            "name": entry.name,
                            "memory_type": entry.memory_type,
                            "scope": entry.scope,
                            "source_type": entry.source_type,
                            "source_id": entry.source_id,
                            "status": entry.status,
                            "description": entry.description,
                            "content": entry.content,
                            "score": 0.0,
                            "match_type": "",
                        }
                    )
        except Exception:
            self._entries = []

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        self._clamp_selection(len(self._entries))

        # 标题
        if self._search_query:
            title_info = f'搜索 "{self._search_query}" ({len(self._entries)} 条结果)'
        else:
            title_info = f"记忆列表 ({len(self._entries)} 条)"

        if not self._entries:
            text = Text()
            text.append(f"\n  {title_info}\n", style="subtitle")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            if self._search_query:
                text.append(
                    f'  未找到与 "{self._search_query}" 相关的记忆\n', style="muted"
                )
            else:
                text.append("  暂无记忆条目\n", style="muted")
            text.append("\n")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append(
                "  UP/DN 浏览 | / 搜索 | D 删除 | R 重建索引 | Esc 清除搜索\n",
                style="muted",
            )
            return Panel(
                text, title=f"[title]{Icons.TAB_MEMORY} 记忆[/]", border_style="border"
            )

        # 使用 Rich Table
        table = create_styled_table(
            title_info,
            [
                ("", "", 2),  # 指针
                ("类型", "center", 8),  # 类型标签
                ("作用域", "center", 8),
                ("状态", "center", 8),
                ("名称", "bold", 20),
                ("描述", "", 25),
                ("相关度", "right", 8),
            ],
        )

        # 类型颜色映射
        type_styles = {
            "user": "info",
            "feedback": "warning",
            "project": "active",
            "reference": "highlight",
        }

        # 滚动支持
        visible_count = max(1, height - 8)
        scroll = self._get_scroll_offset(visible_count, len(self._entries))

        for i in range(scroll, min(scroll + visible_count, len(self._entries))):
            entry = self._entries[i]
            pointer = Icons.POINTER if i == self._selected_index else " "
            mt = str(entry["memory_type"])
            scope = str(entry.get("scope", "project"))
            status = str(entry.get("status", "active"))
            name = str(entry["name"])
            desc = truncate(str(entry["description"]), max_len=max(12, width - 60))
            type_style = type_styles.get(mt, "muted")
            status_style = "active" if status == "active" else "inactive"

            score_text = ""
            if entry.get("score") and entry["score"] > 0:  # type: ignore[operator]
                score_text = f"{entry['score']:.2f}"

            row_style = "reverse" if i == self._selected_index else ""
            table.add_row(
                Text(pointer, style="bold green" if i == self._selected_index else ""),
                Text(f"[{mt}]", style=type_style),
                Text(scope, style="muted"),
                Text(status, style=status_style),
                Text(name, style=row_style),
                Text(desc),
                Text(score_text, style="muted"),
                style=row_style,
            )

        return Panel(
            table,
            title=f"[title]{Icons.TAB_MEMORY} 记忆[/]",
            border_style="border",
        )

    def handle_input(self, key: str) -> bool:
        if key == "up":
            self._move_selection(-1, len(self._entries))
            return True
        elif key == "down":
            self._move_selection(1, len(self._entries))
            return True
        elif key == "d":
            return self._delete_selected()
        elif key == "r":
            return self._rebuild_index()
        elif key == "escape":
            if self.is_searching:
                self.clear_search()
            return True
        return False

    def _delete_selected(self) -> bool:
        """删除选中的记忆条目（后台线程执行）。"""
        if not self._entries or self._selected_index >= len(self._entries):
            return False

        entry = self._entries[self._selected_index]
        name = str(entry["name"])

        def _do_delete() -> None:
            try:
                self._memory_service.delete(name)
                self._selected_index = max(0, self._selected_index - 1)
                self._invalidate_cache()
            except Exception as e:
                logger.debug("删除记忆失败: %s", e)

        self._thread_pool.run_bg(_do_delete)
        return True

    def _rebuild_index(self) -> bool:
        """重建记忆索引（后台线程执行）。"""

        def _do_rebuild() -> None:
            try:
                self._memory_service.rebuild_index()
                self._invalidate_cache()
            except Exception as e:
                logger.debug("重建索引失败: %s", e)

        self._thread_pool.run_bg(_do_rebuild)
        self._set_status("[info]记忆索引重建已启动[/]")
        return True

    def get_footer_commands(self) -> list[tuple[str, str]]:
        """返回 Memory Tab 底部命令列表。"""
        return [("/", "搜索"), ("d", "删除"), ("r", "重建")]

    def get_tab_header_lines(self) -> list[str]:
        if self._search_query:
            return [f"搜索: {self._search_query}", f"结果: {len(self._entries)}"]
        return [f"记忆: {len(self._entries)}", "模式: 列表"]

    def get_summary(self) -> TabSummary:
        active = sum(1 for entry in self._entries if entry.get("status") == "active")
        if self._search_query:
            status = f"搜索: {self._search_query}"
            metrics = (("结果", str(len(self._entries))), ("active", str(active)))
        else:
            status = "模式: 列表"
            metrics = (("记忆", str(len(self._entries))), ("active", str(active)))
        return TabSummary(
            title=self.name,
            mode=self.layout.mode,
            status=status,
            metrics=metrics,
        )

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()

        if not self._entries or self._selected_index >= len(self._entries):
            text.append("  选择一条记忆查看详情", style="muted")
        else:
            entry = self._entries[self._selected_index]
            text.append("记忆详情\n\n", style="subtitle")
            text.append(f"  名称: {entry['name']}\n", style="value")
            text.append(f"  类型: {entry['memory_type']}\n", style="value")
            text.append(f"  作用域: {entry.get('scope', 'project')}\n", style="value")
            text.append(f"  状态: {entry.get('status', 'active')}\n", style="value")
            text.append(f"  来源: {entry.get('source_type', 'manual')}\n", style="value")
            if entry.get("source_id"):
                text.append(f"  来源 ID: {entry['source_id']}\n", style="muted")
            text.append(f"  描述: {entry['description']}\n", style="value")
            text.append("\n  内容:\n", style="subtitle")

            content = str(entry["content"])
            for line in wrap_text(content, width - 8):
                text.append(f"  {line}\n", style="value")

            if entry.get("score") and entry["score"] > 0:  # type: ignore[operator]
                text.append(f"\n  相关度: {entry['score']:.2f}\n", style="info")
                text.append(f"  匹配类型: {entry['match_type']}\n", style="info")

        return Panel(text, title="[title]记忆详情[/]", border_style="border")

    def _search_memory(self, query: str) -> None:
        self.set_search_query(query)
        self._set_status(f"[info]搜索记忆: {query}[/]")

    def _request_delete_selected(self) -> None:
        if not self._entries or self._selected_index >= len(self._entries):
            self._set_status("[warning]无可删除的记忆[/]")
            return
        entry = self._entries[self._selected_index]
        self._request_confirm(
            f'确认删除记忆 "{entry["name"]}"？',
            self._confirm_delete_selected,
        )

    def _confirm_delete_selected(self) -> None:
        if self._delete_selected():
            self._set_status("[success][OK] 已删除记忆[/]")
        else:
            self._set_status("[error][X] 删除记忆失败[/]")
