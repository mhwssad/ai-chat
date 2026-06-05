"""图像管理面板 — AI 生成图像的浏览、预览、删除。"""

from __future__ import annotations

import logging
import os
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab, TabLayoutSpec
from src.ai.cli.utils.image_renderer import ImageRenderer
from src.ai.cli.utils.rich_components import create_styled_table
from src.ai.cli.utils.theme import Icons

logger = logging.getLogger(__name__)


class ImageTab(BaseTab):
    """图像管理面板。

    展示 AI 生成的图像列表，支持预览、删除和外部打开。
    """

    name = "图像"
    hotkey = "8"
    layout = TabLayoutSpec(mode="media")

    def __init__(self, *, thread_pool: Any, image_service: Any) -> None:
        super().__init__(thread_pool)
        self._image_service = image_service
        self._cache_ttl = 3.0
        self._images: list[dict[str, object]] = []
        self._renderer = ImageRenderer()

    def register_commands(self, router: Any, tab_index: int) -> None:
        router.register(tab_index, "p", self._preview_selected)
        router.register(tab_index, "o", self._open_selected)
        router.register(tab_index, "d", self._request_delete_selected)

    def _load_data(self) -> None:
        """通过共享 ImageService 加载图像列表。"""
        try:
            images = self._image_service.list_images()

            # 搜索过滤
            query = self._search_query.lower()
            if query:
                images = [img for img in images if query in str(img.get("filename", "")).lower()]

            self._images = images
        except Exception as e:
            logger.debug("加载图像列表失败: %s", e)
            self._images = []

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
            name = str(img.get("filename", img.get("name", "")))
            size = _format_size(int(img["size_bytes"]))  # type: ignore[call-overload]
            created = img["created_at"].strftime("%Y-%m-%d %H:%M")  # type: ignore[attr-defined]

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
        filename = str(img.get("filename", ""))
        try:
            self._image_service.delete_image(filename)
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
        # 优先使用 path，兼容新格式
        path = str(img.get("path", ""))
        if not path:
            filename = str(img.get("filename", ""))
            try:
                path = str(self._image_service.get_image_path(filename))
            except Exception:
                return False

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
            filename = str(img.get("filename", img.get("name", "")))
            text.append(f"  文件名: {filename}\n", style="value")
            text.append(f"  格式: {img['format']}\n", style="value")
            text.append(
                f"  大小: {_format_size(int(img['size_bytes']))}\n",  # type: ignore[call-overload]
                style="value",
            )
            text.append(f"  创建时间: {img['created_at']}\n", style="value")  # type: ignore[attr-defined]

            # ASCII 预览
            text.append("\n  预览:\n", style="subtitle")
            try:
                img_path = str(img.get("path", ""))
                if not img_path:
                    try:
                        img_path = str(self._image_service.get_image_path(filename))
                    except Exception:
                        img_path = ""
                if img_path:
                    preview = self._renderer.render(
                        img_path,
                        width=max(10, width - 8),
                        height=min(15, height - 12),
                    )
                    text.append_text(preview)
                else:
                    text.append("  无法获取图像路径\n", style="muted")
            except Exception as e:
                text.append(f"  预览失败: {e}\n", style="error")

        return Panel(text, title="[title]图像详情[/]", border_style="border")

    def get_footer_commands(self) -> list[tuple[str, str]]:
        return [("p", "预览"), ("d", "删除"), ("o", "打开")]

    def get_tab_header_lines(self) -> list[str]:
        return [f"图像: {len(self._images)}", "模式: 媒体资源"]

    def _request_delete_selected(self) -> None:
        if not self._images or self._selected_index >= len(self._images):
            self._set_status("[warning]无可删除的图像[/]")
            return
        img = self._images[self._selected_index]
        self._request_confirm(
            f'确认删除图像 "{img.get("filename", "")}"？',
            self._confirm_delete_selected,
        )

    def _confirm_delete_selected(self) -> None:
        if self._delete_selected():
            self._set_status("[success][OK] 已删除图像[/]")
        else:
            self._set_status("[error][X] 删除图像失败[/]")


def _format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
