"""记忆管理面板 — 记忆列表、搜索、删除。"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import truncate


class MemoryTab(BaseTab):
    """记忆管理面板。

    展示记忆条目列表，支持搜索和删除操作。
    """

    name = "记忆"
    hotkey = "3"

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[dict[str, object]] = []
        self._search_query: str = ""
        self._is_searching: bool = False

    def _load_entries(self) -> None:
        """加载记忆条目。"""
        try:
            from src.ai.core.container import container

            svc = container.memory_container.memory_service()
            if self._search_query:
                results = svc.search(self._search_query, limit=50)
                self._entries = []
                for r in results:
                    entry = r.entry
                    self._entries.append(
                        {
                            "name": entry.name,
                            "memory_type": entry.memory_type,
                            "description": entry.description,
                            "content": entry.content,
                            "score": r.score,
                            "match_type": r.match_type,
                        }
                    )
            else:
                entries = svc.list_entries()
                self._entries = []
                for entry in entries:
                    self._entries.append(
                        {
                            "name": entry.name,
                            "memory_type": entry.memory_type,
                            "description": entry.description,
                            "content": entry.content,
                            "score": 0.0,
                            "match_type": "",
                        }
                    )
        except Exception:
            self._entries = []

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._load_entries()
        self._clamp_selection(len(self._entries))

        text = Text()

        # 标题
        if self._search_query:
            text.append(
                f"搜索「{self._search_query}」({len(self._entries)} 条结果)\n",
                style="subtitle",
            )
        else:
            text.append(f"记忆列表 ({len(self._entries)} 条)\n", style="subtitle")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")

        # 表头
        text.append("  类型       名称                    描述\n", style="muted")
        text.append("  " + Icons.LINE * (width - 6) + "\n", style="muted")

        if not self._entries:
            if self._search_query:
                text.append(
                    f"  未找到与「{self._search_query}」相关的记忆\n", style="muted"
                )
            else:
                text.append("  暂无记忆条目\n", style="muted")
        else:
            for i, entry in enumerate(self._entries):
                prefix = Icons.POINTER if i == self._selected_index else " "
                mt = str(entry["memory_type"])
                name = str(entry["name"])
                desc = truncate(str(entry["description"]), max_len=width - 45)

                line_style = "selected" if i == self._selected_index else ""

                # 类型颜色
                type_styles = {
                    "user": "info",
                    "feedback": "warning",
                    "project": "active",
                    "reference": "highlight",
                }
                type_style = type_styles.get(mt, "muted")

                text.append(f" {prefix} ", style=line_style)
                text.append(f"[{mt}]", style=type_style)
                text.append(f" {name:<24s}", style=line_style)
                text.append(f" {desc}\n", style="muted")

                if entry.get("score") and entry["score"] > 0:
                    text.append(
                        f"      相关度: {entry['score']:.2f} ({entry['match_type']})\n",
                        style="muted",
                    )

        # 底部操作
        text.append("\n", style="")
        text.append(Icons.LINE * (width - 4) + "\n", style="muted")
        text.append(
            "  ↑↓ 浏览 │ / 搜索 │ D 删除 │ R 重建索引 │ Esc 清除搜索\n", style="muted"
        )

        return Panel(
            text, title=f"[title]{Icons.TAB_MEMORY} 记忆[/]", border_style="border"
        )

    def handle_input(self, key: str) -> bool:
        if key == "up":
            self._move_selection(-1, len(self._entries))
            return True
        elif key == "down":
            self._move_selection(1, len(self._entries))
            return True
        elif key == "d":
            self._delete_selected()
            return True
        elif key == "r":
            self._rebuild_index()
            return True
        elif key == "escape":
            self._search_query = ""
            self._selected_index = 0
            return True
        return False

    def set_search_query(self, query: str) -> None:
        """设置搜索关键词（由 Dashboard 调用）。"""
        self._search_query = query
        self._selected_index = 0

    def _delete_selected(self) -> None:
        """删除选中的记忆条目。"""
        if not self._entries or self._selected_index >= len(self._entries):
            return

        entry = self._entries[self._selected_index]
        try:
            from src.ai.core.container import container

            svc = container.memory_container.memory_service()
            svc.delete(str(entry["name"]))
            self._selected_index = max(0, self._selected_index - 1)
        except Exception:
            pass

    def _rebuild_index(self) -> None:
        """重建记忆索引。"""
        try:
            from src.ai.core.container import container

            svc = container.memory_container.memory_service()
            svc.rebuild_index()
        except Exception:
            pass

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()

        if not self._entries or self._selected_index >= len(self._entries):
            text.append("  选择一条记忆查看详情", style="muted")
        else:
            entry = self._entries[self._selected_index]
            text.append("记忆详情\n\n", style="subtitle")
            text.append(f"  名称: {entry['name']}\n", style="value")
            text.append(f"  类型: {entry['memory_type']}\n", style="value")
            text.append(f"  描述: {entry['description']}\n", style="value")
            text.append("\n  内容:\n", style="subtitle")

            content = str(entry["content"])
            line_width = width - 8
            for i in range(0, len(content), line_width):
                text.append(f"  {content[i : i + line_width]}\n", style="value")

            if entry.get("score") and entry["score"] > 0:
                text.append(f"\n  相关度: {entry['score']:.2f}\n", style="info")
                text.append(f"  匹配类型: {entry['match_type']}\n", style="info")

        return Panel(text, title="[title]记忆详情[/]", border_style="border")
