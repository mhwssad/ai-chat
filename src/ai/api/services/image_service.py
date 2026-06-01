"""图像服务 — 图像生成、存储和管理。"""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import datetime
from pathlib import Path

from src.ai.exception.media_exception import MediaNotFoundError

logger = logging.getLogger(__name__)


def _validate_filename(filename: str) -> None:
    """校验文件名安全性，防止路径遍历攻击。

    Args:
        filename: 待校验的文件名。

    Raises:
        ValueError: 文件名包含非法字符。
    """
    if "/" in filename or "\\" in filename or ".." in filename:
        raise ValueError(f"文件名包含非法字符: {filename}")


class ImageService:
    """图像服务。

    职责：
    1. 调用模型生成图像
    2. 安全地存储图像文件
    3. 列出、获取、删除图像
    """

    def __init__(self, *, model_service: object) -> None:
        self._model_service = model_service

    def _get_output_dir(self) -> Path:
        """获取图像输出目录。"""
        config = self._model_service.image_config
        output_dir = Path(config.output_dir) if config else Path("output/images")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    async def generate(
        self,
        *,
        prompt: str,
        size: str | None = None,
        quality: str | None = None,
        style: str | None = None,
        n: int = 1,
    ) -> dict:
        """生成图像并保存到本地。

        Args:
            prompt: 图像描述。
            size: 图像尺寸。
            quality: 图像质量。
            style: 图像风格。
            n: 生成数量。

        Returns:
            包含 files、images、revised_prompts 的字典。
        """
        generator = self._model_service.get_image_generator()
        results = await generator.generate(
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=n,
        )

        output_dir = self._get_output_dir()
        files: list[str] = []
        images_b64: list[str] = []
        revised_prompts: list[str | None] = []

        for img_data in results:
            filename = f"{uuid.uuid4().hex[:12]}.{img_data.format}"
            filepath = output_dir / filename
            filepath.write_bytes(img_data.image_bytes)

            files.append(str(filepath))
            images_b64.append(base64.b64encode(img_data.image_bytes).decode("ascii"))
            revised_prompts.append(img_data.revised_prompt)

        return {
            "files": files,
            "images": images_b64,
            "revised_prompts": revised_prompts,
        }

    def list_images(self) -> list[dict]:
        """列出已生成的图像。

        Returns:
            图像元数据列表。
        """
        output_dir = self._get_output_dir()
        if not output_dir.exists():
            return []

        result: list[dict] = []
        for f in sorted(
            output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            if f.is_file() and f.suffix.lower() in (
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".gif",
            ):
                stat = f.stat()
                result.append(
                    {
                        "filename": f.name,
                        "size_bytes": stat.st_size,
                        "format": f.suffix.lstrip(".").upper(),
                        "created_at": datetime.fromtimestamp(stat.st_mtime),
                    }
                )
        return result

    def get_image_path(self, filename: str) -> Path:
        """获取图像文件路径。

        Args:
            filename: 文件名。

        Returns:
            图像文件的完整路径。

        Raises:
            ValueError: 文件名包含非法字符。
            MediaNotFoundError: 图像不存在。
        """
        _validate_filename(filename)
        output_dir = self._get_output_dir()
        filepath = output_dir / filename

        if not filepath.exists():
            raise MediaNotFoundError(
                f"图像不存在: {filename}",
                context={"filename": filename},
            )

        # 二次校验：resolve 后确认仍在 output_dir 内
        resolved = filepath.resolve()
        if not str(resolved).startswith(str(output_dir.resolve())):
            raise ValueError(f"文件路径不安全: {filename}")

        return filepath

    def delete_image(self, filename: str) -> str:
        """删除指定图像。

        Args:
            filename: 文件名。

        Returns:
            删除成功消息。

        Raises:
            ValueError: 文件名包含非法字符。
            MediaNotFoundError: 图像不存在。
        """
        filepath = self.get_image_path(filename)
        filepath.unlink()
        return f"已删除: {filename}"
