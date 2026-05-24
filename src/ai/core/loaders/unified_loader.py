"""统一文档加载器，基于 langchain_unstructured 的 UnstructuredLoader。"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from typing import Any

from .base import DocumentLoader, DocumentMetadata, LoadedDocument
from .config import unstructured_settings
from .errors import LoaderError

logger = logging.getLogger(__name__)


class UnifiedLoader(DocumentLoader):
    """统一文档加载器。

    使用 langchain_unstructured 的 UnstructuredLoader 作为底层引擎，
    支持 TXT, HTML, XML, JSON, MD, PDF, DOCX, CSV, TSV, PPTX, XLSX,
    EPUB, RTF, RST, ODT, 图片(OCR), EML, MSG 等格式。
    """

    def __init__(
        self,
        *,
        partition_via_api: bool | None = None,
        api_key: str | None = None,
        api_url: str | None = None,
        chunking_strategy: str | None = None,
        max_characters: int = 1000000,
        post_processors: list[Any] | None = None,
    ) -> None:
        """初始化统一加载器。

        Args:
            partition_via_api: 是否使用 API 模式，None 时根据 settings.mode 决定。
            api_key: Unstructured API Key。
            api_url: Unstructured API URL。
            chunking_strategy: 分块策略（默认不分块，留给上层处理）。
            max_characters: 最大字符数。
            post_processors: 后处理函数列表。
        """
        if partition_via_api is None:
            self._partition_via_api = unstructured_settings.mode == "api"
        else:
            self._partition_via_api = partition_via_api

        self._api_key = api_key
        self._api_url = api_url
        self._chunking_strategy = chunking_strategy
        self._max_characters = max_characters
        self._post_processors = post_processors

    def load(self, path: str | Path) -> LoadedDocument:
        """加载文档。

        Args:
            path: 文件路径。

        Returns:
            LoadedDocument: 已加载的文档对象。

        Raises:
            LoaderError: 加载失败时抛出。
        """
        file_path = Path(path)
        self._validate_file(file_path)

        try:
            docs = self._load_with_unstructured(file_path)
            return self._to_loaded_document(file_path, docs)
        except LoaderError:
            raise
        except Exception as e:
            raise LoaderError(
                f"文档加载失败: {e}", path=str(path), cause=e
            ) from e

    def _validate_file(self, file_path: Path) -> None:
        """校验文件存在性和大小。"""
        if not file_path.exists():
            raise LoaderError(f"文件不存在: {file_path}", path=str(file_path))
        if not file_path.is_file():
            raise LoaderError(f"不是文件: {file_path}", path=str(file_path))
        max_size = unstructured_settings.max_file_size
        if file_path.stat().st_size > max_size:
            raise LoaderError(
                f"文件过大: {file_path.stat().st_size} > {max_size}",
                path=str(file_path),
            )

    def _load_with_unstructured(self, file_path: Path) -> list[Any]:
        """使用 UnstructuredLoader 加载文件。"""
        try:
            from langchain_unstructured import UnstructuredLoader
        except ImportError as e:
            raise LoaderError(
                "langchain-unstructured 未安装，请运行: uv add langchain-unstructured",
                path=str(file_path),
                cause=e,
            ) from e

        try:
            from unstructured.cleaners.core import clean_extra_whitespace
        except ImportError:
            clean_extra_whitespace = None

        kwargs: dict[str, Any] = {
            "file_path": str(file_path),
            "max_characters": self._max_characters,
            "include_orig_elements": False,
        }

        if self._post_processors:
            kwargs["post_processors"] = self._post_processors
        elif clean_extra_whitespace is not None:
            kwargs["post_processors"] = [clean_extra_whitespace]

        if self._chunking_strategy:
            kwargs["chunking_strategy"] = self._chunking_strategy

        if self._partition_via_api:
            kwargs["partition_via_api"] = True
            api_key = self._api_key or unstructured_settings.api_key
            if not api_key:
                raise LoaderError(
                    "API 模式需要配置 UNSTRUCTURED_API_KEY",
                    path=str(file_path),
                )
            kwargs["api_key"] = api_key
            if self._api_url:
                kwargs["api_url"] = self._api_url
        else:
            kwargs["partition_via_api"] = False

        loader = UnstructuredLoader(**kwargs)
        return loader.load()

    def _to_loaded_document(
        self, file_path: Path, docs: list[Any]
    ) -> LoadedDocument:
        """将 LangChain Document 列表转为 LoadedDocument。"""
        content = "\n\n".join(
            doc.page_content for doc in docs if doc.page_content
        )

        first_meta = docs[0].metadata if docs else {}
        file_size = file_path.stat().st_size

        return LoadedDocument(
            content=content,
            metadata=DocumentMetadata(
                source_path=str(file_path.resolve()),
                title=first_meta.get("filename", file_path.name),
                mime_type=mimetypes.guess_type(file_path.name)[0],
                size_bytes=file_size,
                file_label=first_meta.get("filetype"),
                extra={
                    "page_count": len(docs),
                    "languages": first_meta.get("languages"),
                    "unstructured_metadata": {
                        k: v
                        for k, v in first_meta.items()
                        if k not in ("filename", "filetype", "languages")
                    },
                },
            ),
        )
