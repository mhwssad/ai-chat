"""基于 RapidOCR 的图片文字识别加载器。"""

import mimetypes
from pathlib import Path

from langchain_core.documents import Document

from src.ai.config.loader_settings import OcrSettings
from src.ai.exception.loader_exception import LoaderError
from .base import LoaderStrategy


class OcrImageLoader(LoaderStrategy):
    """RapidOCR 图片文字识别加载器。

    支持的图片格式通过 OcrSettings.image_extensions 配置驱动。

    Args:
        settings: OCR 加载器配置。
    """

    priority = 200
    name = "ocr_image"

    def __init__(self, settings: OcrSettings) -> None:
        self._settings = settings

    def can_handle(self, file_path: Path) -> bool:
        """判断是否为支持的图片格式。"""
        return file_path.suffix.lower() in self._settings.image_extensions_set

    def _load_single(self, file_path: Path) -> list[Document]:
        """对图片执行 OCR。"""
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as e:
            raise LoaderError(
                "rapidocr-onnxruntime 未安装，请运行: uv add rapidocr-onnxruntime",
                path=str(file_path),
                cause=e,
            ) from e

        ocr = RapidOCR()
        result, _ = ocr(str(file_path))
        if not result:
            raise LoaderError(f"OCR 未识别到文本: {file_path}", path=str(file_path))

        lines = [item[1] for item in result]
        content = "\n".join(lines)
        mime_type = mimetypes.guess_type(file_path.name)[0]

        return [
            Document(
                page_content=content,
                metadata={
                    "source": str(file_path.resolve()),
                    "title": file_path.name,
                    "mime_type": mime_type,
                    "size_bytes": file_path.stat().st_size,
                    "file_label": "image-ocr",
                    "page_count": 1,
                    "ocr_engine": "rapidocr",
                    "ocr_line_count": len(lines),
                },
            )
        ]
