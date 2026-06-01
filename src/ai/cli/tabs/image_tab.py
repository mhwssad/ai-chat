"""图像管理面板 — AI 生成图像的浏览、预览、删除。"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.image_renderer import ImageRenderer
from src.ai.cli.utils.rich_components import create_styled_table
from src.ai.cli.utils.theme import Icons

logger = logging.getLogger(__name__)


class ImageTab(BaseTab):
    """图像管理面板。

    展示 AI 生成的图像列表，支持预览、删除和外部打开。
    """

    name = "图像"
    hotkey = "6"

    def __init__(self) -> None:
        super().__init__()
        self._cache_ttl = 3.0
        self._images: list[dict[str, object]] = []
        self._renderer = ImageRenderer()

    def _load_data(self) -> None:
        """扫描 output/images 目录，按修改时间排序。"""
        try:
            config = self._get_output_dir()
            output_dir = Path(config)
            if not output_dir.exists():
                self._images = []
                return

            images: list[dict[str, object]] = []
            for f in output_dir.iterdir():
                if f.is_file() and f.suffix.lower() in (
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".gif",
                ):
                    stat = f.stat()
                    images.append(
                        {
                            "path": str(f),
                            "name": f.name,
                            "format": f.suffix.lstrip(".").upper(),
                            "size_bytes": stat.st_size,
                            "created_at": datetime.fromtimestamp(stat.st_mtime),
                        }
                    )

            # 按修改时间倒序
            images.sort(key=lambda x: x["created_at"], reverse=True)  # type: ignore[arg-type]

            # 搜索过滤
            query = self._search_query.lower()
            if query:
                images = [img for img in images if query in str(img["name"]).lower()]

            self._images = images
        except Exception as e:
            logger.debug("加载图像列表失败: %s", e)
            self._images = []

    @staticmethod
    def _get_output_dir() -> str:
        """获取图像输出目录。"""
        try:
            from src.ai.config.model_settings import ImageModelConfig

            config = ImageModelConfig()
            return config.output_dir
        except Exception:
            return "output/images"

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        self._clamp_selection(len(self._images))

        if self._search_query:
            title_info = f'搜索 "{self._search_query}" ({len(self._images)} 张)'
        else:
            title_info = f"图像列表 ({len(self._images)} 张)"

        if not self._images:
            text = Text()
            text.append(f"\n  {title_info}\n", style="subtitle")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append("  没有已生成的图像\n", style="muted")
            text.append("\n  使用对话中的图像生成工具创建图像\n", style="muted")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append("  UP/DN 浏览 | P 预览 | D 删除 | O 打开\n", style="muted")
            return Panel(
                text, title=f"[title]{Icons.TAB_IMAGE} 图像[/]", border_style="border"
            )

        # 使用 Rich Table
        table = create_styled_table(
            title_info,
            [
                ("", "", 2),  # 指针
                ("格式", "center", 6),  # 格式图标
                ("文件名", "bold", 24),
                ("大小", "muted", 10),
                ("创建时间", "muted", 20),
            ],
        )

        # 滚动支持
        visible_count = max(1, height - 10)
        scroll = self._get_scroll_offset(visible_count, len(self._images))

        for i in range(scroll, min(scroll + visible_count, len(self._images))):
            img = self._images[i]
            pointer = Icons.POINTER if i == self._selected_index else " "
            fmt = str(img["format"])
            name = str(img["name"])
            size = _format_size(int(img["size_bytes"]))  # type: ignore[arg-type]
            created = img["created_at"].strftime("%Y-%m-%d %H:%M")  # type: ignore[union-attr]

            row_style = "reverse" if i == self._selected_index else ""
            table.add_row(
                Text(pointer, style="bold green" if i == self._selected_index else ""),
                Text(f"[{fmt}]", style="info"),
                Text(name, style=row_style),
                Text(size),
                Text(created),
                style=row_style,
            )

        return Panel(
            table,
            title=f"[title]{Icons.TAB_IMAGE} 图像[/]",
            border_style="border",
        )

    def handle_input(self, key: str) -> bool:
        if key == "up":
            self._move_selection(-1, len(self._images))
            return True
        elif key == "down":
            self._move_selection(1, len(self._images))
            return True
        elif key == "p":
            return self._preview_selected()
        elif key == "d":
            return self._delete_selected()
        elif key == "o":
            return self._open_selected()
        elif key == "escape":
            if self.is_searching:
                self.clear_search()
                return True
        return False

    def _preview_selected(self) -> bool:
        """预览选中的图像（刷新详情面板）。"""
        if not self._images or self._selected_index >= len(self._images):
            return False
        # 预览通过 get_detail_panel 实现，无需额外操作
        return True

    def _delete_selected(self) -> bool:
        """删除选中的图像文件。"""
        if not self._images or self._selected_index >= len(self._images):
            return False

        img = self._images[self._selected_index]
        path = Path(str(img["path"]))
        try:
            path.unlink()
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.debug("删除图像失败: %s", e)
            return False

    def _open_selected(self) -> bool:
        """使用系统默认程序打开图像。"""
        if not self._images or self._selected_index >= len(self._images):
            return False

        img = self._images[self._selected_index]
        path = str(img["path"])
        try:
            import platform

            system = platform.system()
            if system == "Windows":
                os.startfile(path)  # type: ignore[attr-defined]
            elif system == "Darwin":
                import subprocess

                subprocess.Popen(["open", path])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", path])
            return True
        except Exception as e:
            logger.debug("打开图像失败: %s", e)
            return False

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()

        if not self._images or self._selected_index >= len(self._images):
            text.append("  选择一张图像查看详情", style="muted")
        else:
            img = self._images[self._selected_index]
            text.append("图像详情\n\n", style="subtitle")
            text.append(f"  文件名: {img['name']}\n", style="value")
            text.append(f"  格式: {img['format']}\n", style="value")
            text.append(
                f"  大小: {_format_size(int(img['size_bytes']))}\n", style="value"
            )  # type: ignore[arg-type]
            text.append(f"  创建时间: {img['created_at']}\n", style="value")  # type: ignore[union-attr]

            # ASCII 预览
            text.append("\n  预览:\n", style="subtitle")
            try:
                preview = self._renderer.render(
                    str(img["path"]),
                    width=max(10, width - 8),
                    height=min(15, height - 12),
                )
                text.append_text(preview)
            except Exception as e:
                text.append(f"  预览失败: {e}\n", style="error")

        return Panel(text, title="[title]图像详情[/]", border_style="border")

    def get_footer_commands(self) -> list[tuple[str, str]]:
        return [("p", "预览"), ("d", "删除"), ("o", "打开")]


def _format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
