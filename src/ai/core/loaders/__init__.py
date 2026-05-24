"""文档加载器模块。

提供统一的文档加载接口，基于 langchain_unstructured 的 UnstructuredLoader，
支持多种文件格式：TXT, HTML, XML, JSON, MD, PDF, DOCX, CSV, TSV,
PPTX, XLSX, EPUB, RTF, RST, ODT, 图片(OCR), EML, MSG 等。

示例:
    from src.ai.core.loaders import load_document, DocumentLoaderFactory

    doc = load_document("/path/to/file.md")
    factory = DocumentLoaderFactory()
    doc = factory.load("/path/to/file.pdf")
"""

from .base import (
    DocumentLoader,
    DocumentMetadata,
    LoadedDocument,
)
from .config import UnstructuredSettings, unstructured_settings
from .errors import LoaderError, LoadPermissionError, UnsupportedFileTypeError
from .factory import (
    DocumentLoaderFactory,
    get_document_loader_factory,
    load_document,
    load_documents,
)
from .unified_loader import UnifiedLoader

__all__ = [
    # 基础类和接口
    "DocumentLoader",
    "DocumentMetadata",
    "LoadedDocument",
    # 配置
    "UnstructuredSettings",
    "unstructured_settings",
    # 错误类
    "LoaderError",
    "UnsupportedFileTypeError",
    "LoadPermissionError",
    # 统一加载器
    "UnifiedLoader",
    # 工厂和便捷函数
    "DocumentLoaderFactory",
    "get_document_loader_factory",
    "load_document",
    "load_documents",
]
