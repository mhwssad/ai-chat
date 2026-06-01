"""TTS 语音合成工具 — 调用模型子系统合成语音。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool


def create_text_to_speech_tool(model_service: Any) -> Any:
    """工厂函数：创建绑定了 model_service 的 text_to_speech 工具。"""

    @tool
    async def text_to_speech(
        text: str,
        voice: str = "alloy",
        speed: float = 1.0,
        output_format: str = "mp3",
    ) -> str:
        """将文本合成为语音并保存到本地。

        Args:
            text: 待合成的文本内容。
            voice: 语音名称。OpenAI 可选 alloy/echo/fable/onyx/nova/shimmer；
                   Edge TTS 可选 zh-CN-XiaoxiaoNeural 等。
            speed: 语速，1.0 为正常速度，范围 0.25-4.0。
            output_format: 输出格式，可选 "mp3"、"opus"、"aac"、"flac"、"wav"。
        """
        try:
            synthesizer = model_service.get_speech_synthesizer()
            audio_data = await synthesizer.synthesize(
                text=text,
                voice=voice,
                speed=speed,
                output_format=output_format,
            )

            # 获取输出目录
            config = model_service.tts_config
            output_dir = Path(config.output_dir) if config else Path("output/audio")
            output_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{uuid.uuid4().hex[:12]}.{audio_data.format}"
            filepath = output_dir / filename
            filepath.write_bytes(audio_data.audio_bytes)

            duration_info = ""
            if audio_data.duration_seconds is not None:
                duration_info = f"，时长 {audio_data.duration_seconds:.1f} 秒"

            return f"语音合成成功{duration_info}:\n  - {filepath}"
        except Exception as exc:
            return f"语音合成失败: {exc}"

    return text_to_speech


def register(model_service: Any) -> None:
    """注册 TTS 工具。"""
    tool_obj = create_text_to_speech_tool(model_service)
    register_tool(
        tool_obj,
        source_type="builtin",
        permissions=["external_service", "file_write"],
    )
