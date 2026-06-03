"""记忆管理面板 — 记忆列表、搜索、删除。"""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.theme import Icons
from src.ai.cli.utils.formatting import truncate, wrap_text
from src.ai.cli.utils.rich_components import create_styled_table

logger = logging.getLogger(__name__)


class MemoryTab(BaseTab):
    """记忆管理面板。

    展示记忆条目列表，支持搜索和删除操作。
    """

    name = "记忆"
    hotkey = "3"

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[dict[str, object]] = []

    def _load_data(self) -> None:
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
            name = str(entry["name"])
            desc = truncate(str(entry["description"]), max_len=width - 45)
            type_style = type_styles.get(mt, "muted")

            score_text = ""
            if entry.get("score") and entry["score"] > 0:  # type: ignore[operator]
                score_text = f"{entry['score']:.2f}"

            row_style = "reverse" if i == self._selected_index else ""
            table.add_row(
                Text(pointer, style="bold green" if i == self._selected_index else ""),
                Text(f"[{mt}]", style=type_style),
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
            self._search_query = ""
            self._selected_index = 0
            return True
        return False

    def _delete_selected(self) -> bool:
        """删除选中的记忆条目。"""
        if not self._entries or self._selected_index >= len(self._entries):
            return False

        entry = self._entries[self._selected_index]
        try:
            from src.ai.core.container import container

            svc = container.memory_container.memory_service()
            svc.delete(str(entry["name"]))
            self._selected_index = max(0, self._selected_index - 1)
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.debug("删除记忆失败: %s", e)
            return False

    def _rebuild_index(self) -> bool:
        """重建记忆索引。"""
        try:
            from src.ai.core.container import container

            svc = container.memory_container.memory_service()
            svc.rebuild_index()
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.debug("重建索引失败: %s", e)
            return False

    def get_footer_commands(self) -> list[tuple[str, str]]:
        """返回 Memory Tab 底部命令列表。"""
        return [("/", "搜索"), ("d", "删除"), ("r", "重建")]

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
            for line in wrap_text(content, width - 8):
                text.append(f"  {line}\n", style="value")

            if entry.get("score") and entry["score"] > 0:  # type: ignore[operator]
                text.append(f"\n  相关度: {entry['score']:.2f}\n", style="info")
                text.append(f"  匹配类型: {entry['match_type']}\n", style="info")

        return Panel(text, title="[title]记忆详情[/]", border_style="border")
