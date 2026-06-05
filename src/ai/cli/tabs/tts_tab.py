"""TTS 语音管理面板 — AI 合成音频的浏览、播放、删除。"""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.ai.cli.tabs import BaseTab, TabLayoutSpec
from src.ai.cli.utils.audio_player import AudioPlayer
from src.ai.cli.utils.rich_components import create_styled_table
from src.ai.cli.utils.theme import Icons

logger = logging.getLogger(__name__)


class TTSTab(BaseTab):
    """TTS 语音管理面板。

    展示 AI 合成的音频列表，支持播放、停止和删除。
    """

    name = "语音"
    hotkey = "9"
    layout = TabLayoutSpec(mode="media")

    def __init__(self, *, thread_pool: Any, tts_service: Any) -> None:
        super().__init__(thread_pool)
        self._tts_service = tts_service
        self._cache_ttl = 3.0
        self._audios: list[dict[str, object]] = []
        self._player = AudioPlayer()

    def register_commands(self, router: Any, tab_index: int) -> None:
        router.register(tab_index, "p", self._play_selected)
        router.register(tab_index, "s", self._stop_playback)
        router.register(tab_index, "d", self._request_delete_selected)

    def _load_data(self) -> None:
        """通过共享 TTSService 加载音频列表。"""
        try:
            audios = self._tts_service.list_audio()

            # 搜索过滤
            query = self._search_query.lower()
            if query:
                audios = [a for a in audios if query in str(a.get("filename", "")).lower()]

            self._audios = audios
        except Exception as e:
            logger.debug("加载音频列表失败: %s", e)
            self._audios = []

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
            name = str(audio.get("filename", audio.get("name", "")))
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
        # 优先使用 path，兼容新格式
        path = str(audio.get("path", ""))
        if not path:
            filename = str(audio.get("filename", ""))
            try:
                filepath, _ = self._tts_service.get_audio_path(filename)
                path = str(filepath)
            except Exception:
                return False
        return self._player.play(path)

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
        # 如果正在播放，先停止
        if self._player.is_playing:
            self._player.stop()

        filename = str(audio.get("filename", ""))
        try:
            self._tts_service.delete_audio(filename)
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
            filename = str(audio.get("filename", audio.get("name", "")))
            text.append(f"  文件名: {filename}\n", style="value")
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

    def get_tab_header_lines(self) -> list[str]:
        state = "播放中" if self._player.is_playing else "空闲"
        return [f"音频: {len(self._audios)}", f"播放: {state}"]

    def _request_delete_selected(self) -> None:
        if not self._audios or self._selected_index >= len(self._audios):
            self._set_status("[warning]无可删除的音频[/]")
            return
        audio = self._audios[self._selected_index]
        self._request_confirm(
            f'确认删除音频 "{audio.get("filename", "")}"？',
            self._confirm_delete_selected,
        )

    def _confirm_delete_selected(self) -> None:
        if self._delete_selected():
            self._set_status("[success][OK] 已删除音频[/]")
        else:
            self._set_status("[error][X] 删除音频失败[/]")


def _format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
