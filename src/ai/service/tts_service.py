"""TTS 服务 — 语音合成、存储和管理。

共享服务层，API 统一使用。
"""

from __future__ import annotations

import base64
from src.ai.config.logging_setup import get_logger
import uuid
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.ai.exception.media_exception import MediaNotFoundError

if TYPE_CHECKING:
    from src.ai.utils.thread_pool import ThreadPoolManager

logger = get_logger(__name__)

_MIME_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".opus": "audio/opus",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
}

_AUDIO_EXTENSIONS = (".mp3", ".wav", ".opus", ".aac", ".flac", ".ogg")


def _validate_filename(filename: str) -> None:
    """校验文件名安全性，防止路径遍历攻击。

    Args:
        filename: 待校验的文件名。

    Raises:
        ValueError: 文件名包含非法字符。
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError(f"文件名包含非法字符: {filename}")


class TTSService:
    """TTS 语音合成服务。

    职责：
    1. 调用模型合成语音
    2. 安全地存储音频文件
    3. 列出、获取、删除音频
    """

    def __init__(
        self,
        *,
        model_service: Any,
        thread_pool: ThreadPoolManager | None = None,
    ) -> None:
        self._model_service = model_service
        self._thread_pool = thread_pool

    def _get_pool(self) -> ThreadPoolManager:
        """获取线程池实例。"""
        if self._thread_pool is None:
            from src.ai.utils.thread_pool import get_thread_pool

            self._thread_pool = get_thread_pool()
        return self._thread_pool

    def _get_output_dir(self) -> Path:
        """获取音频输出目录。"""
        config = self._model_service.tts_config
        output_dir = Path(config.output_dir) if config else Path("output/audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    async def synthesize(
        self,
        *,
        text: str,
        voice: str | None = None,
        speed: float | None = None,
        output_format: str | None = None,
    ) -> dict:
        """合成语音并保存到本地。

        Args:
            text: 待合成文本。
            voice: 语音角色。
            speed: 语速。
            output_format: 输出格式。

        Returns:
            包含 file、audio_base64、format、duration_seconds 的字典。
        """
        synthesizer = self._model_service.get_speech_synthesizer()
        audio_data = await synthesizer.synthesize(
            text=text,
            voice=voice,
            speed=speed,
            output_format=output_format,
        )

        output_dir = self._get_output_dir()
        filename = f"{uuid.uuid4().hex[:12]}.{audio_data.format}"
        filepath = output_dir / filename

        await self._get_pool().run_io(filepath.write_bytes, audio_data.audio_bytes)

        return {
            "file": str(filepath),
            "audio_base64": base64.b64encode(audio_data.audio_bytes).decode("ascii"),
            "format": audio_data.format,
            "duration_seconds": audio_data.duration_seconds,
        }

    def list_audio(self) -> list[dict]:
        """列出已合成的音频。

        Returns:
            音频元数据列表，按修改时间倒序排列。
        """
        output_dir = self._get_output_dir()
        if not output_dir.exists():
            return []

        result: list[dict] = []
        for f in sorted(
            output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS:
                stat = f.stat()
                result.append(
                    {
                        "filename": f.name,
                        "path": str(f),
                        "size_bytes": stat.st_size,
                        "format": f.suffix.lstrip(".").upper(),
                        "created_at": datetime.fromtimestamp(stat.st_mtime),
                    }
                )
        return result

    def get_audio_path(self, filename: str) -> tuple[Path, str]:
        """获取音频文件路径和 MIME 类型。

        Args:
            filename: 文件名。

        Returns:
            (文件路径, MIME 类型) 元组。

        Raises:
            ValueError: 文件名包含非法字符。
            MediaNotFoundError: 音频不存在。
        """
        _validate_filename(filename)
        output_dir = self._get_output_dir()
        filepath = output_dir / filename

        if not filepath.exists():
            raise MediaNotFoundError(
                f"音频不存在: {filename}",
                context={"filename": filename},
            )

        # 二次校验：resolve 后确认仍在 output_dir 内
        resolved = filepath.resolve()
        if not str(resolved).startswith(str(output_dir.resolve())):
            raise ValueError(f"文件路径不安全: {filename}")

        mime_type = _MIME_MAP.get(filepath.suffix.lower(), "application/octet-stream")
        return filepath, mime_type

    def delete_audio(self, filename: str) -> str:
        """删除指定音频。

        Args:
            filename: 文件名。

        Returns:
            删除成功消息。

        Raises:
            ValueError: 文件名包含非法字符。
            MediaNotFoundError: 音频不存在。
        """
        filepath, _ = self.get_audio_path(filename)
        filepath.unlink()
        return f"已删除: {filename}"

    # ── 异步包装 ──────────────────────────────────────────────

    async def alist_audio(self) -> list[dict]:
        """异步列出已合成的音频。"""
        return await self._get_pool().run_io(self.list_audio)

    async def adelete_audio(self, filename: str) -> str:
        """异步删除指定音频。"""
        return await self._get_pool().run_io(self.delete_audio, filename)
