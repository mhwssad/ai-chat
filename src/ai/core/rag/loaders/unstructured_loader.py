"""基于 langchain_unstructured 的文档加载器。"""

from src.ai.config.logging_setup import get_logger
import mimetypes
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from src.ai.config.loader_settings import UnstructuredSettings
from src.ai.exception.loader_exception import LoaderError
from .base import LoaderStrategy

logger = get_logger(__name__)


class UnstructuredLoader(LoaderStrategy):
    """基于 langchain_unstructured 的文档加载器。

    支持 TXT, HTML, XML, JSON, MD, PDF, DOCX, CSV, TSV, PPTX, XLSX,
    EPUB, RTF, RST, ODT, EML, MSG 等格式。
    当首选 strategy 失败时自动降级到 fast。

    Args:
        settings: UnstructuredSettings 配置实例。
        post_processors: 后处理函数列表，覆盖 settings 中的默认值。
    """

    priority = 100
    name = "unstructured"

    def __init__(
        self,
        settings: UnstructuredSettings,
        *,
        post_processors: list[Any] | None = None,
    ) -> None:
        self._settings = settings
        self._post_processors = post_processors

    def can_handle(self, file_path: Path) -> bool:
        """通用处理器，始终返回 True。"""
        return True

    def _load_single(self, file_path: Path) -> list[Document]:
        """使用 unstructured 加载文件。"""
        docs = self._load_with_unstructured(file_path)
        if docs is None:
            return []
        return docs

    def _load_with_unstructured(self, file_path: Path) -> list[Document] | None:
        """使用 UnstructuredLoader 加载文件。

        尝试用户指定的 strategy，若因系统依赖缺失失败则降级到 fast。

        Returns:
            Document 列表，或 None 表示 unstructured 无法处理该格式。
        """
        try:
            from langchain_unstructured import (
                UnstructuredLoader as _LCUnstructuredLoader,
            )
        except ImportError as e:
            raise LoaderError(
                "langchain-unstructured 未安装，请运行: uv add langchain-unstructured",
                path=str(file_path),
                cause=e,
            ) from e

        try:
            from unstructured.cleaners.core import clean_extra_whitespace
        except ImportError:
            clean_extra_whitespace = None  # type: ignore[assignment]

        kwargs: dict[str, Any] = {
            "file_path": str(file_path),
            "strategy": self._settings.strategy,
            "max_characters": self._settings.max_characters,
            "languages": self._settings.languages,
            "include_orig_elements": False,
        }

        if self._post_processors:
            kwargs["post_processors"] = self._post_processors
        elif clean_extra_whitespace is not None:
            kwargs["post_processors"] = [clean_extra_whitespace]

        chunking = self._settings.effective_chunking_strategy
        if chunking:
            kwargs["chunking_strategy"] = chunking

        if self._settings.use_api:
            kwargs["partition_via_api"] = True
            api_key = self._settings.api_key
            if not api_key:
                raise LoaderError(
                    "API 模式需要配置 UNSTRUCTURED_API_KEY",
                    path=str(file_path),
                )
            kwargs["api_key"] = api_key
            if self._settings.api_url:
                kwargs["api_url"] = self._settings.api_url
        else:
            kwargs["partition_via_api"] = False

        # 尝试首选 strategy
        try:
            loader = _LCUnstructuredLoader(**kwargs)
            return self._enrich_metadata(loader.load(), file_path)
        except (ValueError, TypeError):
            return None
        except Exception as e:
            if self._settings.strategy == "fast":
                raise
            logger.warning(
                "strategy=%s 失败 (%s: %s)，降级到 fast",
                self._settings.strategy,
                type(e).__name__,
                e,
            )

        # 降级到 fast
        kwargs["strategy"] = "fast"
        try:
            loader = _LCUnstructuredLoader(**kwargs)
            return self._enrich_metadata(loader.load(), file_path)
        except (ValueError, TypeError):
            return None

    def _enrich_metadata(self, docs: list[Document], file_path: Path) -> list[Document]:
        """为 langchain Document 补充项目所需的元数据字段。"""
        mime_type = mimetypes.guess_type(file_path.name)[0]
        file_size = file_path.stat().st_size

        for doc in docs:
            doc.metadata.setdefault("source", str(file_path.resolve()))
            doc.metadata.setdefault("title", file_path.name)
            doc.metadata["mime_type"] = mime_type
            doc.metadata["size_bytes"] = file_size

        return docs
