"""TTS 语音管理面板 — AI 合成音频的浏览、播放、删除。"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab
from src.ai.cli.utils.audio_player import AudioPlayer
from src.ai.cli.utils.rich_components import create_styled_table
from src.ai.cli.utils.theme import Icons

logger = logging.getLogger(__name__)


class TTSTab(BaseTab):
    """TTS 语音管理面板。

    展示 AI 合成的音频列表，支持播放、停止和删除。
    """

    name = "语音"
    hotkey = "7"

    def __init__(self) -> None:
        super().__init__()
        self._cache_ttl = 3.0
        self._audios: list[dict[str, object]] = []
        self._player = AudioPlayer()

    def _load_data(self) -> None:
        """扫描 output/audio 目录，按修改时间排序。"""
        try:
            config = self._get_output_dir()
            output_dir = Path(config)
            if not output_dir.exists():
                self._audios = []
                return

            audios: list[dict[str, object]] = []
            for f in output_dir.iterdir():
                if f.is_file() and f.suffix.lower() in (
                    ".mp3",
                    ".wav",
                    ".opus",
                    ".aac",
                    ".flac",
                    ".ogg",
                ):
                    stat = f.stat()
                    audios.append(
                        {
                            "path": str(f),
                            "name": f.name,
                            "format": f.suffix.lstrip(".").upper(),
                            "size_bytes": stat.st_size,
                            "created_at": datetime.fromtimestamp(stat.st_mtime),
                        }
                    )

            # 按修改时间倒序
            audios.sort(key=lambda x: x["created_at"], reverse=True)  # type: ignore[return-value, arg-type]

            # 搜索过滤
            query = self._search_query.lower()
            if query:
                audios = [a for a in audios if query in str(a["name"]).lower()]

            self._audios = audios
        except Exception as e:
            logger.debug("加载音频列表失败: %s", e)
            self._audios = []

    @staticmethod
    def _get_output_dir() -> str:
        """获取音频输出目录。"""
        try:
            from src.ai.config.model_settings import TTSModelConfig

            config = TTSModelConfig()
            return config.output_dir
        except Exception:
            return "output/audio"

    def render_content(self, console: Console, width: int, height: int) -> Panel:
        self._ensure_cache()
        self._clamp_selection(len(self._audios))

        if self._search_query:
            title_info = f'搜索 "{self._search_query}" ({len(self._audios)} 个)'
        else:
            title_info = f"音频列表 ({len(self._audios)} 个)"

        if not self._audios:
            text = Text()
            text.append(f"\n  {title_info}\n", style="subtitle")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append("  没有已合成的音频\n", style="muted")
            text.append("\n  使用对话中的 TTS 工具合成语音\n", style="muted")
            text.append(Icons.LINE * (width - 4) + "\n", style="muted")
            text.append("  UP/DN 浏览 | P 播放 | S 停止 | D 删除\n", style="muted")
            return Panel(
                text, title=f"[title]{Icons.TAB_TTS} 语音[/]", border_style="border"
            )

        # 使用 Rich Table
        table = create_styled_table(
            title_info,
            [
                ("", "", 2),  # 指针
                ("播放", "center", 4),  # 播放状态
                ("格式", "center", 6),  # 格式
                ("文件名", "bold", 24),
                ("大小", "muted", 10),
                ("创建时间", "muted", 20),
            ],
        )

        # 滚动支持
        visible_count = max(1, height - 10)
        scroll = self._get_scroll_offset(visible_count, len(self._audios))

        for i in range(scroll, min(scroll + visible_count, len(self._audios))):
            audio = self._audios[i]
            pointer = Icons.POINTER if i == self._selected_index else " "

            # 播放状态图标
            is_currently_playing = self._player.is_playing and i == self._selected_index
            play_icon = Icons.RUNNING if is_currently_playing else " "

            fmt = str(audio["format"])
            name = str(audio["name"])
            size = _format_size(int(audio["size_bytes"]))  # type: ignore[call-overload]
            created = audio["created_at"].strftime("%Y-%m-%d %H:%M")  # type: ignore[attr-defined]

            row_style = "reverse" if i == self._selected_index else ""
            table.add_row(
                Text(pointer, style="bold green" if i == self._selected_index else ""),
                Text(play_icon, style="active" if is_currently_playing else ""),
                Text(f"[{fmt}]", style="info"),
                Text(name, style=row_style),
                Text(size),
                Text(created),
                style=row_style,
            )

        return Panel(
            table,
            title=f"[title]{Icons.TAB_TTS} 语音[/]",
            border_style="border",
        )

    def handle_input(self, key: str) -> bool:
        if key == "up":
            self._move_selection(-1, len(self._audios))
            return True
        elif key == "down":
            self._move_selection(1, len(self._audios))
            return True
        elif key == "p":
            return self._play_selected()
        elif key == "s":
            return self._stop_playback()
        elif key == "d":
            return self._delete_selected()
        elif key == "escape":
            if self.is_searching:
                self.clear_search()
                return True
        return False

    def _play_selected(self) -> bool:
        """播放选中的音频文件。"""
        if not self._audios or self._selected_index >= len(self._audios):
            return False

        audio = self._audios[self._selected_index]
        return self._player.play(str(audio["path"]))

    def _stop_playback(self) -> bool:
        """停止当前播放。"""
        if self._player.is_playing:
            self._player.stop()
            return True
        return False

    def _delete_selected(self) -> bool:
        """删除选中的音频文件。"""
        if not self._audios or self._selected_index >= len(self._audios):
            return False

        audio = self._audios[self._selected_index]
        # 如果正在播放该文件，先停止
        if self._player.is_playing:
            self._player.stop()

        path = Path(str(audio["path"]))
        try:
            path.unlink()
            self._invalidate_cache()
            return True
        except Exception as e:
            logger.debug("删除音频失败: %s", e)
            return False

    def get_detail_panel(self, console: Console, width: int, height: int) -> Panel:
        text = Text()

        if not self._audios or self._selected_index >= len(self._audios):
            text.append("  选择一个音频查看详情", style="muted")
        else:
            audio = self._audios[self._selected_index]
            text.append("音频详情\n\n", style="subtitle")
            text.append(f"  文件名: {audio['name']}\n", style="value")
            text.append(f"  格式: {audio['format']}\n", style="value")
            text.append(
                f"  大小: {_format_size(int(audio['size_bytes']))}\n",  # type: ignore[call-overload]
                style="value",
            )
            text.append(f"  创建时间: {audio['created_at']}\n", style="value")  # type: ignore[attr-defined]

            # 播放状态
            text.append("\n  播放状态:\n", style="subtitle")
            if self._player.is_playing:
                text.append("  [正在播放]\n", style="active")
            else:
                text.append("  [已停止]\n", style="muted")

            # 播放后端信息
            text.append(f"\n  播放后端: {self._player.backend}\n", style="muted")

        return Panel(text, title="[title]音频详情[/]", border_style="border")

    def get_footer_commands(self) -> list[tuple[str, str]]:
        return [("p", "播放"), ("s", "停止"), ("d", "删除")]


def _format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
