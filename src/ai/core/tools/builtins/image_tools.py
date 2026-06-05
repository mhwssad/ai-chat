"""图像生成工具 — 调用模型子系统生成图像。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from src.ai.core.tools.register import register_tool


def create_image_generate_tool(model_service: Any) -> Any:
    """工厂函数：创建绑定了 model_service 的 image_generate 工具。"""

    @tool
    async def image_generate(
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
    ) -> str:
        """根据提示词生成图像并保存到本地。

        Args:
            prompt: 图像描述提示词，应尽量详细描述期望的画面内容。
            size: 图像尺寸，可选 "1024x1024"、"1792x1024"、"1024x1792"。
            quality: 图像质量，可选 "standard"（标准）或 "hd"（高清）。
            style: 图像风格，可选 "vivid"（鲜艳）或 "natural"（自然）。
        """
        try:
            generator = model_service.get_image_generator()
            results = await generator.generate(
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
            )

            # 获取输出目录
            config = model_service.image_config
            output_dir = Path(config.output_dir) if config else Path("output/images")
            output_dir.mkdir(parents=True, exist_ok=True)

            saved_files: list[str] = []
            for i, img_data in enumerate(results):
                filename = f"{uuid.uuid4().hex[:12]}.{img_data.format}"
                filepath = output_dir / filename

                from src.ai.utils.thread_pool import get_thread_pool

                await get_thread_pool().run_io(
                    filepath.write_bytes, img_data.image_bytes
                )
                saved_files.append(str(filepath))

            return f"成功生成 {len(saved_files)} 张图像:\n" + "\n".join(
                f"  - {f}" for f in saved_files
            )
        except Exception as exc:
            return f"图像生成失败: {exc}"

    return image_generate


def register(model_service: Any) -> None:
    """注册图像生成工具。"""
    tool_obj = create_image_generate_tool(model_service)
    register_tool(
        tool_obj,
        source_type="builtin",
        permissions=["external_service", "file_write"],
    )
