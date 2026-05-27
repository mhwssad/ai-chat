"""文档加载器模块。

采用职责链模式，各加载器自注册到 LoaderRegistry，ChainLoader 按优先级遍历执行。

示例::

    from src.ai.core.loaders import ChainLoader

    # 创建一次，反复使用
    loader = ChainLoader()

    # 加载单个文件
    docs = loader.load_file("report.pdf")

    # 加载目录下所有文件
    docs = loader.load_dir("data/documents/")

    # 批量加载
    docs = loader.load_batch(["a.pdf", "b.txt", "c.md"])

    # 注册自定义加载器
    from src.ai.core.loaders import loader_registry
    loader_registry.register(MyLoader, priority=150, name="my_loader")
"""

from src.ai.config.loader_settings import UnstructuredSettings, unstructured_settings
from src.ai.exception.loader_exception import (
    LoaderError,
    LoadPermissionError,
    UnsupportedFileTypeError,
)
from .base import LangchainAdapter, LoaderStrategy
from .chain_loader import ChainLoader
from .registry import LoaderRegistry, loader_registry

# 导入各加载器模块以触发自注册
from .unstructured_loader import UnstructuredLoader  # noqa: E402
from .ocr_loader import OcrImageLoader  # noqa: E402
from .text_loader import PlainTextLoader  # noqa: E402

__all__ = [
    # 基类
    "LoaderStrategy",
    "LangchainAdapter",
    # 注册表
    "LoaderRegistry",
    "loader_registry",
    # 编排器
    "ChainLoader",
    # 加载器
    "UnstructuredLoader",
    "OcrImageLoader",
    "PlainTextLoader",
    # 配置
    "UnstructuredSettings",
    "unstructured_settings",
    # 异常
    "LoaderError",
    "UnsupportedFileTypeError",
    "LoadPermissionError",
]
