"""终端音频播放器 — 跨平台后台播放。"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class AudioPlayer:
    """跨平台音频播放器。

    自动检测可用后端，在后台线程中播放音频文件。
    支持的后端优先级：system > playsound > pygame > none。
    """

    def __init__(self) -> None:
        self._backend: str = self._detect_backend()
        self._process: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._playing: bool = False

    @property
    def is_playing(self) -> bool:
        """是否正在播放。"""
        return self._playing

    @property
    def backend(self) -> str:
        """当前使用的后端名称。"""
        return self._backend

    def _detect_backend(self) -> str:
        """检测可用的音频播放后端。

        Returns:
            后端名称: "system", "playsound", "pygame", "none"。
        """
        system = platform.system()

        if system == "Windows":
            # Windows 有 start 命令
            return "system"
        elif system == "Darwin":
            # macOS 有 afplay
            if shutil.which("afplay"):
                return "system"
        elif system == "Linux":
            # Linux 尝试 mpv / paplay / aplay
            for cmd in ("mpv", "paplay", "aplay"):
                if shutil.which(cmd):
                    return "system"

        # 尝试 playsound
        try:
            import playsound  # type: ignore[import-not-found]  # noqa: F401

            return "playsound"
        except ImportError:
            pass

        # 尝试 pygame
        try:
            import pygame  # type: ignore[import-not-found]  # noqa: F401

            return "pygame"
        except ImportError:
            pass

        return "none"

    def play(self, file_path: str | Path) -> bool:
        """在后台线程中播放音频文件。

        Args:
            file_path: 音频文件路径。

        Returns:
            True 表示开始播放，False 表示无法播放。
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning("音频文件不存在: %s", path)
            return False

        if self._backend == "none":
            logger.warning("无可用音频播放后端")
            return False

        # 停止当前播放
        self.stop()

        self._playing = True
        self._thread = threading.Thread(
            target=self._play_thread,
            args=(str(path),),
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        """停止当前播放。"""
        self._playing = False
        if self._process:
            try:
                self._process.terminate()
            except Exception:
                pass
            self._process = None

    def _play_thread(self, file_path: str) -> None:
        """播放线程入口。"""
        try:
            if self._backend == "system":
                self._play_system(file_path)
            elif self._backend == "playsound":
                self._play_playsound(file_path)
            elif self._backend == "pygame":
                self._play_pygame(file_path)
        except Exception as e:
            logger.debug("音频播放失败: %s", e)
        finally:
            self._playing = False

    def _play_system(self, file_path: str) -> None:
        """使用系统命令播放音频。

        - Windows: start 命令（使用默认播放器）
        - macOS: afplay
        - Linux: mpv / paplay / aplay

        Args:
            file_path: 音频文件路径。
        """
        system = platform.system()
        try:
            if system == "Windows":
                # 使用 start 命令在后台播放
                self._process = subprocess.Popen(
                    ["cmd", "/c", "start", "/b", "", file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._process.wait()
            elif system == "Darwin":
                self._process = subprocess.Popen(
                    ["afplay", file_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self._process.wait()
            elif system == "Linux":
                # 按优先级尝试
                for cmd in ("mpv", "paplay", "aplay"):
                    if shutil.which(cmd):
                        self._process = subprocess.Popen(
                            [cmd, file_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        self._process.wait()
                        break
        except Exception as e:
            logger.debug("系统音频播放失败: %s", e)

    @staticmethod
    def _play_playsound(file_path: str) -> None:
        """使用 playsound 库播放。"""
        from playsound import playsound  # type: ignore[import-not-found]

        playsound(file_path)

    @staticmethod
    def _play_pygame(file_path: str) -> None:
        """使用 pygame 播放。"""
        import pygame  # type: ignore[import-not-found]

        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            import time

            time.sleep(0.1)
        pygame.mixer.quit()
